"""
Blind Source Separation (BSS) Module.

Main interface for source separation combining multiple techniques:
- ICA-based separation
- Spectral separation (NMF, masking)
- Deep learning models (when available)
- Hybrid approaches
"""

import numpy as np
from typing import Optional, List, Union, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import warnings

from claudio.core.audio_io import AudioData, AudioLoader, AudioWriter
from claudio.core.fft_processor import FFTProcessor
from claudio.core.phase_processor import PhaseProcessor
from claudio.separation.ica import ICAProcessor, ICAMethod, ICAResult
from claudio.separation.spectral import SpectralSeparator, SpectralSeparationResult


class SeparationMethod(Enum):
    """Available separation methods."""
    ICA = "ica"
    NMF = "nmf"
    SPECTRAL_MASK = "spectral_mask"
    HYBRID = "hybrid"
    DEEP_LEARNING = "deep_learning"


@dataclass
class SeparationConfig:
    """Configuration for source separation."""

    method: SeparationMethod = SeparationMethod.HYBRID
    n_sources: int = 2
    n_fft: int = 2048
    hop_length: Optional[int] = None
    max_iterations: int = 500
    tolerance: float = 1e-6
    use_gpu: bool = False
    enhance_output: bool = True  # Apply phase enhancement
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeparatedSource:
    """A separated audio source."""

    signal: np.ndarray
    sample_rate: int
    source_id: int
    confidence: float  # Separation confidence (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_audio_data(self) -> AudioData:
        """Convert to AudioData object."""
        return AudioData(
            signal=self.signal,
            sample_rate=self.sample_rate,
            duration=len(self.signal) / self.sample_rate,
            channels=1,
        )


@dataclass
class SeparationResult:
    """Result of source separation."""

    sources: List[SeparatedSource]
    mixture: np.ndarray
    sample_rate: int
    method_used: SeparationMethod
    processing_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def n_sources(self) -> int:
        return len(self.sources)

    def get_source(self, idx: int) -> SeparatedSource:
        """Get source by index."""
        return self.sources[idx]

    def reconstruct(self) -> np.ndarray:
        """Reconstruct mixture from separated sources."""
        return sum(s.signal for s in self.sources)

    def reconstruction_error(self) -> float:
        """Compute reconstruction error (MSE)."""
        reconstructed = self.reconstruct()
        min_len = min(len(reconstructed), len(self.mixture))
        return np.mean((self.mixture[:min_len] - reconstructed[:min_len]) ** 2)


class BlindSourceSeparator:
    """
    Main Blind Source Separation interface.

    Combines multiple separation techniques for robust
    source separation from mixed audio signals.
    """

    def __init__(self, config: Optional[SeparationConfig] = None):
        """
        Initialize BlindSourceSeparator.

        Args:
            config: Separation configuration. Uses defaults if None.
        """
        self.config = config or SeparationConfig()
        self.hop_length = self.config.hop_length or self.config.n_fft // 4

        # Initialize processors
        self.fft_processor = FFTProcessor(
            n_fft=self.config.n_fft,
            hop_length=self.hop_length,
        )
        self.phase_processor = PhaseProcessor(
            n_fft=self.config.n_fft,
            hop_length=self.hop_length,
        )
        self.ica_processor = ICAProcessor(
            n_components=self.config.n_sources,
            max_iterations=self.config.max_iterations,
            tolerance=self.config.tolerance,
        )
        self.spectral_separator = SpectralSeparator(
            n_fft=self.config.n_fft,
            hop_length=self.hop_length,
            n_sources=self.config.n_sources,
        )

        # Deep learning model (lazy loaded)
        self._dl_model = None

    def separate(
        self,
        mixed_signal: Union[np.ndarray, AudioData, str, Path],
        sample_rate: Optional[int] = None,
        n_sources: Optional[int] = None,
        method: Optional[SeparationMethod] = None,
    ) -> SeparationResult:
        """
        Perform blind source separation.

        Args:
            mixed_signal: Mixed audio (array, AudioData, or file path).
            sample_rate: Sample rate (required if array input).
            n_sources: Override number of sources to separate.
            method: Override separation method.

        Returns:
            SeparationResult with separated sources.
        """
        # Handle input types
        if isinstance(mixed_signal, (str, Path)):
            loader = AudioLoader(mono=True, normalize=True)
            audio_data = loader.load(mixed_signal)
            signal = audio_data.signal
            sr = audio_data.sample_rate
        elif isinstance(mixed_signal, AudioData):
            signal = mixed_signal.to_mono().signal
            sr = mixed_signal.sample_rate
        else:
            signal = np.asarray(mixed_signal)
            if signal.ndim > 1:
                signal = np.mean(signal, axis=0)
            sr = sample_rate
            if sr is None:
                raise ValueError("sample_rate required for array input")

        n_sources = n_sources or self.config.n_sources
        method = method or self.config.method

        # Dispatch to appropriate method
        if method == SeparationMethod.ICA:
            return self._separate_ica(signal, sr, n_sources)
        elif method == SeparationMethod.NMF:
            return self._separate_nmf(signal, sr, n_sources)
        elif method == SeparationMethod.SPECTRAL_MASK:
            return self._separate_spectral_mask(signal, sr, n_sources)
        elif method == SeparationMethod.HYBRID:
            return self._separate_hybrid(signal, sr, n_sources)
        elif method == SeparationMethod.DEEP_LEARNING:
            return self._separate_deep_learning(signal, sr, n_sources)
        else:
            raise ValueError(f"Unknown separation method: {method}")

    def _separate_ica(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_sources: int,
    ) -> SeparationResult:
        """Separate using ICA."""
        # For single-channel, create pseudo-multichannel using time-delayed copies
        delays = [0] + [int(sample_rate * 0.001 * i) for i in range(1, n_sources)]
        multi_channel = np.zeros((n_sources, len(signal)))

        for i, delay in enumerate(delays):
            if delay == 0:
                multi_channel[i] = signal
            else:
                multi_channel[i, delay:] = signal[:-delay]

        # Apply ICA
        ica_processor = ICAProcessor(
            n_components=n_sources,
            method=ICAMethod.FASTICA,
            max_iterations=self.config.max_iterations,
            tolerance=self.config.tolerance,
        )

        ica_result = ica_processor.fit_transform(multi_channel)

        # Sort sources by variance
        ica_result = ica_processor.sort_sources_by_variance(ica_result)

        # Create separated sources
        sources = []
        for i in range(n_sources):
            source_signal = ica_result.sources[i]

            # Normalize
            source_signal = source_signal / (np.max(np.abs(source_signal)) + 1e-10)

            # Calculate confidence based on kurtosis (non-Gaussianity)
            kurtosis = abs(ica_processor.compute_kurtosis(ica_result.sources)[i])
            confidence = min(1.0, kurtosis / 10)

            sources.append(SeparatedSource(
                signal=source_signal,
                sample_rate=sample_rate,
                source_id=i,
                confidence=confidence,
                metadata={"method": "ica", "kurtosis": kurtosis},
            ))

        # Enhance if requested
        if self.config.enhance_output:
            sources = self._enhance_sources(sources, signal, sample_rate)

        return SeparationResult(
            sources=sources,
            mixture=signal,
            sample_rate=sample_rate,
            method_used=SeparationMethod.ICA,
            processing_info={
                "n_iterations": ica_result.n_iterations,
                "converged": ica_result.converged,
            },
        )

    def _separate_nmf(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_sources: int,
    ) -> SeparationResult:
        """Separate using NMF."""
        n_components = self.config.extra_params.get("nmf_components", 10)

        result = self.spectral_separator.separate_nmf(
            signal,
            sample_rate,
            n_components=n_components,
            n_sources=n_sources,
            max_iterations=self.config.max_iterations,
            tolerance=self.config.tolerance,
        )

        sources = []
        for i, source_signal in enumerate(result.sources):
            # Compute confidence from mask coverage
            mask = result.masks[i]
            confidence = np.mean(mask > 0.5)

            sources.append(SeparatedSource(
                signal=source_signal,
                sample_rate=sample_rate,
                source_id=i,
                confidence=confidence,
                metadata={"method": "nmf"},
            ))

        if self.config.enhance_output:
            sources = self._enhance_sources(sources, signal, sample_rate)

        return SeparationResult(
            sources=sources,
            mixture=signal,
            sample_rate=sample_rate,
            method_used=SeparationMethod.NMF,
            processing_info={
                "reconstruction_error": result.reconstruction_error,
            },
        )

    def _separate_spectral_mask(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_sources: int,
    ) -> SeparationResult:
        """Separate using spectral masking with Wiener filter."""
        result = self.spectral_separator.separate_wiener(
            signal,
            sample_rate,
            n_iterations=self.config.extra_params.get("wiener_iterations", 5),
        )

        sources = []
        for i, source_signal in enumerate(result.sources):
            mask = result.masks[i]
            confidence = np.mean(mask > 0.3)

            sources.append(SeparatedSource(
                signal=source_signal,
                sample_rate=sample_rate,
                source_id=i,
                confidence=confidence,
                metadata={"method": "spectral_mask"},
            ))

        if self.config.enhance_output:
            sources = self._enhance_sources(sources, signal, sample_rate)

        return SeparationResult(
            sources=sources,
            mixture=signal,
            sample_rate=sample_rate,
            method_used=SeparationMethod.SPECTRAL_MASK,
            processing_info={
                "reconstruction_error": result.reconstruction_error,
            },
        )

    def _separate_hybrid(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_sources: int,
    ) -> SeparationResult:
        """
        Hybrid separation combining multiple techniques.

        Uses ensemble of methods for more robust separation.
        """
        results = []

        # Try ICA
        try:
            ica_result = self._separate_ica(signal, sample_rate, n_sources)
            results.append(("ica", ica_result))
        except Exception as e:
            warnings.warn(f"ICA separation failed: {e}")

        # Try NMF
        try:
            nmf_result = self._separate_nmf(signal, sample_rate, n_sources)
            results.append(("nmf", nmf_result))
        except Exception as e:
            warnings.warn(f"NMF separation failed: {e}")

        # Try spectral masking
        try:
            spectral_result = self._separate_spectral_mask(signal, sample_rate, n_sources)
            results.append(("spectral", spectral_result))
        except Exception as e:
            warnings.warn(f"Spectral separation failed: {e}")

        if not results:
            raise RuntimeError("All separation methods failed")

        # Select best result based on reconstruction error
        best_method, best_result = min(
            results,
            key=lambda x: x[1].reconstruction_error() if hasattr(x[1], 'reconstruction_error') else float('inf')
        )

        # Update metadata
        for source in best_result.sources:
            source.metadata["hybrid_method"] = best_method

        return SeparationResult(
            sources=best_result.sources,
            mixture=signal,
            sample_rate=sample_rate,
            method_used=SeparationMethod.HYBRID,
            processing_info={
                "methods_tried": [m for m, _ in results],
                "best_method": best_method,
            },
        )

    def _separate_deep_learning(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_sources: int,
    ) -> SeparationResult:
        """
        Separate using deep learning models.

        Uses pre-trained models when available.
        """
        try:
            # Try to use SpeechBrain or similar
            from speechbrain.inference.separation import SepformerSeparation

            if self._dl_model is None:
                self._dl_model = SepformerSeparation.from_hparams(
                    source="speechbrain/sepformer-whamr",
                    savedir="pretrained_models/sepformer-whamr"
                )

            # Resample if needed (model expects 8kHz typically)
            import torchaudio
            import torch

            if sample_rate != 8000:
                resampler = torchaudio.transforms.Resample(sample_rate, 8000)
                signal_tensor = torch.tensor(signal).float().unsqueeze(0)
                signal_resampled = resampler(signal_tensor).squeeze().numpy()
                process_sr = 8000
            else:
                signal_resampled = signal
                process_sr = sample_rate

            # Separate
            est_sources = self._dl_model.separate_batch(
                torch.tensor(signal_resampled).float().unsqueeze(0)
            )
            est_sources = est_sources.squeeze().numpy()

            # Resample back if needed
            if sample_rate != 8000:
                resampler_back = torchaudio.transforms.Resample(8000, sample_rate)
                separated = []
                for i in range(est_sources.shape[0]):
                    source_tensor = torch.tensor(est_sources[i]).float().unsqueeze(0)
                    separated.append(resampler_back(source_tensor).squeeze().numpy())
                est_sources = np.array(separated)

            sources = []
            for i in range(min(n_sources, est_sources.shape[0])):
                sources.append(SeparatedSource(
                    signal=est_sources[i],
                    sample_rate=sample_rate,
                    source_id=i,
                    confidence=0.9,  # DL models typically have high confidence
                    metadata={"method": "deep_learning", "model": "sepformer"},
                ))

            return SeparationResult(
                sources=sources,
                mixture=signal,
                sample_rate=sample_rate,
                method_used=SeparationMethod.DEEP_LEARNING,
                processing_info={"model": "sepformer"},
            )

        except ImportError:
            warnings.warn("Deep learning models not available, falling back to hybrid")
            return self._separate_hybrid(signal, sample_rate, n_sources)

    def _enhance_sources(
        self,
        sources: List[SeparatedSource],
        mixture: np.ndarray,
        sample_rate: int,
    ) -> List[SeparatedSource]:
        """Apply phase-based enhancement to separated sources."""
        enhanced_sources = []

        for source in sources:
            # Apply phase reconstruction
            enhanced, _ = self.phase_processor.multi_source_phase_enhancement(
                source.signal,
                sample_rate,
                n_iterations=5,
            )

            enhanced_sources.append(SeparatedSource(
                signal=enhanced,
                sample_rate=source.sample_rate,
                source_id=source.source_id,
                confidence=source.confidence,
                metadata={**source.metadata, "enhanced": True},
            ))

        return enhanced_sources

    def separate_voices(
        self,
        mixed_signal: Union[np.ndarray, AudioData, str, Path],
        sample_rate: Optional[int] = None,
        max_voices: int = 30,
    ) -> SeparationResult:
        """
        Specialized separation for multiple voice sources.

        Optimized for separating up to 30 different voices.

        Args:
            mixed_signal: Mixed audio input.
            sample_rate: Sample rate.
            max_voices: Maximum number of voices to separate.

        Returns:
            SeparationResult with separated voice sources.
        """
        # Handle input
        if isinstance(mixed_signal, (str, Path)):
            loader = AudioLoader(mono=True, normalize=True)
            audio_data = loader.load(mixed_signal)
            signal = audio_data.signal
            sr = audio_data.sample_rate
        elif isinstance(mixed_signal, AudioData):
            signal = mixed_signal.to_mono().signal
            sr = mixed_signal.sample_rate
        else:
            signal = np.asarray(mixed_signal)
            if signal.ndim > 1:
                signal = np.mean(signal, axis=0)
            sr = sample_rate

        # Use higher NMF components for many voices
        components_per_voice = 3
        total_components = min(max_voices * components_per_voice, 90)

        # Estimate number of voices using spectral analysis
        estimated_voices = self._estimate_voice_count(signal, sr, max_voices)

        # Use NMF for many-source separation
        result = self.spectral_separator.separate_nmf(
            signal,
            sr,
            n_components=total_components,
            n_sources=estimated_voices,
            max_iterations=self.config.max_iterations * 2,  # More iterations for complex separation
        )

        sources = []
        for i, source_signal in enumerate(result.sources):
            mask = result.masks[i]
            confidence = np.mean(mask > 0.3)

            sources.append(SeparatedSource(
                signal=source_signal,
                sample_rate=sr,
                source_id=i,
                confidence=confidence,
                metadata={
                    "method": "nmf_voice",
                    "estimated_voice_id": i,
                },
            ))

        if self.config.enhance_output:
            sources = self._enhance_sources(sources, signal, sr)

        return SeparationResult(
            sources=sources,
            mixture=signal,
            sample_rate=sr,
            method_used=SeparationMethod.NMF,
            processing_info={
                "estimated_voices": estimated_voices,
                "max_voices": max_voices,
            },
        )

    def _estimate_voice_count(
        self,
        signal: np.ndarray,
        sample_rate: int,
        max_voices: int,
    ) -> int:
        """
        Estimate the number of distinct voices in the signal.

        Uses spectral clustering on voice activity regions.
        """
        from sklearn.cluster import DBSCAN

        # Compute STFT
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Focus on voice frequency range (100-4000 Hz)
        voice_freq_mask = (stft_data.frequencies >= 100) & (stft_data.frequencies <= 4000)
        voice_spec = stft_data.magnitude[voice_freq_mask, :]

        # Compute features for each frame
        n_frames = voice_spec.shape[1]
        features = []

        for t in range(n_frames):
            frame = voice_spec[:, t]
            if np.max(frame) > np.mean(stft_data.magnitude) * 0.5:  # Voice activity
                # Spectral centroid and spread as features
                freqs = stft_data.frequencies[voice_freq_mask]
                centroid = np.sum(freqs * frame) / (np.sum(frame) + 1e-10)
                spread = np.sqrt(np.sum(((freqs - centroid) ** 2) * frame) / (np.sum(frame) + 1e-10))
                features.append([centroid / 1000, spread / 500])  # Normalize

        if len(features) < 10:
            return 2  # Default to 2 sources

        features = np.array(features)

        # DBSCAN clustering
        clustering = DBSCAN(eps=0.3, min_samples=5).fit(features)
        n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)

        return min(max(n_clusters, 2), max_voices)

    def save_sources(
        self,
        result: SeparationResult,
        output_dir: Union[str, Path],
        format: str = ".wav",
        prefix: str = "source",
    ) -> List[str]:
        """
        Save separated sources to files.

        Args:
            result: Separation result.
            output_dir: Output directory.
            format: Output format (.wav, .flac, .mp3).
            prefix: Filename prefix.

        Returns:
            List of output file paths.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        writer = AudioWriter(sample_rate=result.sample_rate, normalize=True)
        output_paths = []

        for source in result.sources:
            filename = f"{prefix}_{source.source_id:03d}{format}"
            output_path = output_dir / filename
            writer.write(source.signal, output_path, source.sample_rate)
            output_paths.append(str(output_path))

        return output_paths
