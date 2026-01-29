"""
Spectral Separation Module.

Implements frequency-domain source separation methods:
- Non-negative Matrix Factorization (NMF)
- Binary Time-Frequency Masking
- Soft Masking techniques
- Ideal Ratio Masking (IRM)
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Optional, Tuple, List, Union
from dataclasses import dataclass
from enum import Enum

from claudio.core.fft_processor import FFTProcessor, STFTData


class MaskType(Enum):
    """Types of time-frequency masks."""
    BINARY = "binary"
    SOFT = "soft"
    WIENER = "wiener"
    IDEAL_RATIO = "ideal_ratio"
    PHASE_SENSITIVE = "phase_sensitive"


@dataclass
class SpectralSeparationResult:
    """Result of spectral source separation."""

    sources: List[np.ndarray]  # List of separated source signals
    masks: List[np.ndarray]  # Time-frequency masks for each source
    residual: Optional[np.ndarray]  # Residual signal (if any)
    reconstruction_error: float  # Error in reconstruction


@dataclass
class NMFResult:
    """Result of NMF decomposition."""

    W: np.ndarray  # Basis matrix (frequency patterns)
    H: np.ndarray  # Activation matrix (temporal patterns)
    reconstruction: np.ndarray  # Reconstructed spectrogram
    cost_history: List[float]  # Cost function history
    n_iterations: int


class SpectralSeparator:
    """
    Spectral-domain source separator.

    Uses frequency-domain representations and various masking
    techniques to separate mixed audio sources.
    """

    def __init__(
        self,
        n_fft: int = 2048,
        hop_length: Optional[int] = None,
        n_sources: int = 2,
    ):
        """
        Initialize SpectralSeparator.

        Args:
            n_fft: FFT size.
            hop_length: Hop length for STFT.
            n_sources: Expected number of sources.
        """
        self.n_fft = n_fft
        self.hop_length = hop_length or n_fft // 4
        self.n_sources = n_sources
        self.fft_processor = FFTProcessor(n_fft, hop_length)

    def separate_nmf(
        self,
        mixed_signal: np.ndarray,
        sample_rate: int,
        n_components: int = 10,
        n_sources: Optional[int] = None,
        max_iterations: int = 500,
        tolerance: float = 1e-6,
    ) -> SpectralSeparationResult:
        """
        Separate sources using Non-negative Matrix Factorization.

        Decomposes the magnitude spectrogram V ≈ W * H where:
        - W: Basis spectra (frequency patterns)
        - H: Activation patterns (temporal patterns)

        Args:
            mixed_signal: Mixed audio signal.
            sample_rate: Sample rate.
            n_components: Number of NMF components per source.
            n_sources: Number of sources to extract.
            max_iterations: Maximum iterations.
            tolerance: Convergence tolerance.

        Returns:
            SpectralSeparationResult with separated sources.
        """
        n_sources = n_sources or self.n_sources
        total_components = n_components * n_sources

        # Compute STFT
        stft_data = self.fft_processor.stft(mixed_signal, sample_rate)
        V = stft_data.magnitude + 1e-10  # Add small constant for stability

        # Run NMF
        nmf_result = self._nmf(V, total_components, max_iterations, tolerance)

        # Cluster components into sources
        sources_list = []
        masks_list = []

        components_per_source = total_components // n_sources

        for s in range(n_sources):
            start_idx = s * components_per_source
            end_idx = start_idx + components_per_source

            # Get source-specific basis and activations
            W_source = nmf_result.W[:, start_idx:end_idx]
            H_source = nmf_result.H[start_idx:end_idx, :]

            # Reconstruct source spectrogram
            source_spectrogram = np.dot(W_source, H_source)

            # Create soft mask (Wiener-like)
            mask = source_spectrogram / (nmf_result.reconstruction + 1e-10)
            mask = np.clip(mask, 0, 1)

            # Apply mask to complex STFT
            masked_stft = mask * stft_data.complex_stft

            # Create STFTData for reconstruction
            source_stft_data = STFTData(
                magnitude=np.abs(masked_stft),
                phase=np.angle(masked_stft),
                complex_stft=masked_stft,
                frequencies=stft_data.frequencies,
                times=stft_data.times,
                sample_rate=sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                window_type=stft_data.window_type,
            )

            # Reconstruct source signal
            source_signal = self.fft_processor.istft(
                source_stft_data, length=len(mixed_signal)
            )

            sources_list.append(source_signal)
            masks_list.append(mask)

        # Compute residual
        reconstructed = sum(sources_list)
        residual = mixed_signal[:len(reconstructed)] - reconstructed

        # Compute reconstruction error
        reconstruction_error = np.mean((mixed_signal[:len(reconstructed)] - reconstructed) ** 2)

        return SpectralSeparationResult(
            sources=sources_list,
            masks=masks_list,
            residual=residual,
            reconstruction_error=reconstruction_error,
        )

    def _nmf(
        self,
        V: np.ndarray,
        n_components: int,
        max_iterations: int,
        tolerance: float,
    ) -> NMFResult:
        """
        Non-negative Matrix Factorization using multiplicative updates.

        Args:
            V: Input magnitude spectrogram.
            n_components: Number of components.
            max_iterations: Maximum iterations.
            tolerance: Convergence tolerance.

        Returns:
            NMFResult with decomposition.
        """
        n_freq, n_frames = V.shape

        # Initialize W and H randomly (non-negative)
        np.random.seed(42)
        W = np.random.rand(n_freq, n_components) + 1e-10
        H = np.random.rand(n_components, n_frames) + 1e-10

        cost_history = []

        for iteration in range(max_iterations):
            # Compute reconstruction
            WH = np.dot(W, H) + 1e-10

            # Compute cost (Frobenius norm)
            cost = np.sum((V - WH) ** 2)
            cost_history.append(cost)

            # Check convergence
            if iteration > 0:
                relative_change = abs(cost_history[-2] - cost) / (cost_history[-2] + 1e-10)
                if relative_change < tolerance:
                    break

            # Multiplicative updates (Euclidean distance)
            # H update
            H = H * (np.dot(W.T, V)) / (np.dot(W.T, WH) + 1e-10)

            # Recompute WH
            WH = np.dot(W, H) + 1e-10

            # W update
            W = W * (np.dot(V, H.T)) / (np.dot(WH, H.T) + 1e-10)

        # Final reconstruction
        reconstruction = np.dot(W, H)

        return NMFResult(
            W=W,
            H=H,
            reconstruction=reconstruction,
            cost_history=cost_history,
            n_iterations=iteration + 1,
        )

    def separate_binary_mask(
        self,
        mixed_signal: np.ndarray,
        sample_rate: int,
        reference_signals: Optional[List[np.ndarray]] = None,
        threshold: float = 0.5,
    ) -> SpectralSeparationResult:
        """
        Separate sources using binary time-frequency masking.

        Args:
            mixed_signal: Mixed audio signal.
            sample_rate: Sample rate.
            reference_signals: Optional reference signals for mask computation.
            threshold: Threshold for binary mask.

        Returns:
            SpectralSeparationResult with separated sources.
        """
        stft_data = self.fft_processor.stft(mixed_signal, sample_rate)

        if reference_signals is not None:
            # Use reference signals to compute masks
            ref_stfts = [
                self.fft_processor.stft(ref, sample_rate)
                for ref in reference_signals
            ]

            masks_list = []
            for ref_stft in ref_stfts:
                # Binary mask: 1 where reference dominates
                total_mag = sum(r.magnitude for r in ref_stfts) + 1e-10
                mask = (ref_stft.magnitude / total_mag > threshold).astype(float)
                masks_list.append(mask)
        else:
            # Estimate masks using clustering
            masks_list = self._estimate_masks_clustering(stft_data, self.n_sources)

        # Apply masks and reconstruct
        sources_list = []
        for mask in masks_list:
            masked_stft = mask * stft_data.complex_stft

            source_stft_data = STFTData(
                magnitude=np.abs(masked_stft),
                phase=np.angle(masked_stft),
                complex_stft=masked_stft,
                frequencies=stft_data.frequencies,
                times=stft_data.times,
                sample_rate=sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                window_type=stft_data.window_type,
            )

            source_signal = self.fft_processor.istft(
                source_stft_data, length=len(mixed_signal)
            )
            sources_list.append(source_signal)

        reconstructed = sum(sources_list)
        residual = mixed_signal[:len(reconstructed)] - reconstructed
        reconstruction_error = np.mean(residual ** 2)

        return SpectralSeparationResult(
            sources=sources_list,
            masks=masks_list,
            residual=residual,
            reconstruction_error=reconstruction_error,
        )

    def separate_wiener(
        self,
        mixed_signal: np.ndarray,
        sample_rate: int,
        source_spectrograms: Optional[List[np.ndarray]] = None,
        n_iterations: int = 5,
    ) -> SpectralSeparationResult:
        """
        Separate sources using Wiener filtering.

        Args:
            mixed_signal: Mixed audio signal.
            sample_rate: Sample rate.
            source_spectrograms: Optional estimated source spectrograms.
            n_iterations: Number of EM iterations.

        Returns:
            SpectralSeparationResult with separated sources.
        """
        stft_data = self.fft_processor.stft(mixed_signal, sample_rate)
        mixture_spec = stft_data.magnitude ** 2  # Power spectrogram

        n_freq, n_frames = mixture_spec.shape

        if source_spectrograms is None:
            # Initialize with random spectrograms
            source_specs = [
                np.random.rand(n_freq, n_frames) * mixture_spec / self.n_sources
                for _ in range(self.n_sources)
            ]
        else:
            source_specs = [spec ** 2 for spec in source_spectrograms]

        # EM iterations for Wiener filter refinement
        for _ in range(n_iterations):
            # E-step: Compute Wiener masks
            total_spec = sum(source_specs) + 1e-10

            masks = [spec / total_spec for spec in source_specs]

            # M-step: Update source spectrograms
            source_specs = [mask * mixture_spec for mask in masks]

        # Apply masks to complex STFT
        sources_list = []
        masks_list = []

        for i, mask in enumerate(masks):
            # Convert power mask to amplitude mask
            amp_mask = np.sqrt(np.clip(mask, 0, 1))

            masked_stft = amp_mask * stft_data.complex_stft

            source_stft_data = STFTData(
                magnitude=np.abs(masked_stft),
                phase=np.angle(masked_stft),
                complex_stft=masked_stft,
                frequencies=stft_data.frequencies,
                times=stft_data.times,
                sample_rate=sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                window_type=stft_data.window_type,
            )

            source_signal = self.fft_processor.istft(
                source_stft_data, length=len(mixed_signal)
            )

            sources_list.append(source_signal)
            masks_list.append(amp_mask)

        reconstructed = sum(sources_list)
        residual = mixed_signal[:len(reconstructed)] - reconstructed
        reconstruction_error = np.mean(residual ** 2)

        return SpectralSeparationResult(
            sources=sources_list,
            masks=masks_list,
            residual=residual,
            reconstruction_error=reconstruction_error,
        )

    def _estimate_masks_clustering(
        self,
        stft_data: STFTData,
        n_sources: int,
    ) -> List[np.ndarray]:
        """
        Estimate masks using k-means clustering on spectral features.

        Args:
            stft_data: STFT of mixture.
            n_sources: Number of sources.

        Returns:
            List of estimated masks.
        """
        from sklearn.cluster import KMeans

        n_freq, n_frames = stft_data.magnitude.shape

        # Create feature vectors for each time-frequency bin
        # Features: magnitude, phase, frequency bin index
        features = np.zeros((n_freq * n_frames, 3))

        for f in range(n_freq):
            for t in range(n_frames):
                idx = f * n_frames + t
                features[idx, 0] = stft_data.magnitude[f, t]
                features[idx, 1] = stft_data.phase[f, t]
                features[idx, 2] = f / n_freq  # Normalized frequency

        # Normalize features
        features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-10)

        # K-means clustering
        kmeans = KMeans(n_clusters=n_sources, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features)

        # Convert labels to masks
        masks = []
        for s in range(n_sources):
            mask = (labels == s).reshape(n_freq, n_frames).astype(float)
            masks.append(mask)

        return masks

    def harmonic_percussive_separation(
        self,
        signal: np.ndarray,
        sample_rate: int,
        kernel_size: Tuple[int, int] = (31, 31),
        margin: float = 1.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Separate signal into harmonic and percussive components.

        Uses median filtering on the spectrogram.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            kernel_size: Kernel size for median filtering (harmonic, percussive).
            margin: Separation margin.

        Returns:
            Tuple of (harmonic_signal, percussive_signal).
        """
        from scipy.ndimage import median_filter

        stft_data = self.fft_processor.stft(signal, sample_rate)
        S = stft_data.magnitude

        # Median filtering
        # Horizontal (time) median -> percussive mask
        # Vertical (frequency) median -> harmonic mask
        S_harmonic = median_filter(S, size=(kernel_size[0], 1))
        S_percussive = median_filter(S, size=(1, kernel_size[1]))

        # Soft masks with margin
        mask_harmonic = (S_harmonic / (S_harmonic + S_percussive + 1e-10)) ** margin
        mask_percussive = (S_percussive / (S_harmonic + S_percussive + 1e-10)) ** margin

        # Apply masks
        harmonic_stft = mask_harmonic * stft_data.complex_stft
        percussive_stft = mask_percussive * stft_data.complex_stft

        # Reconstruct
        harmonic_stft_data = STFTData(
            magnitude=np.abs(harmonic_stft),
            phase=np.angle(harmonic_stft),
            complex_stft=harmonic_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        percussive_stft_data = STFTData(
            magnitude=np.abs(percussive_stft),
            phase=np.angle(percussive_stft),
            complex_stft=percussive_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        harmonic_signal = self.fft_processor.istft(harmonic_stft_data, length=len(signal))
        percussive_signal = self.fft_processor.istft(percussive_stft_data, length=len(signal))

        return harmonic_signal, percussive_signal

    def vocal_separation(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_components: int = 16,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Attempt to separate vocals from instrumental.

        Uses repetition-based separation (REPET-like algorithm).

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            n_components: Number of NMF components.

        Returns:
            Tuple of (vocals, instrumental).
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)
        S = stft_data.magnitude

        # Compute self-similarity matrix
        S_norm = S / (np.linalg.norm(S, axis=0, keepdims=True) + 1e-10)
        similarity = np.dot(S_norm.T, S_norm)

        # Find repeating patterns (background/instrumental)
        # Use median of similarity for each frame
        median_sim = np.median(similarity, axis=1)

        # Frames with high median similarity are likely instrumental
        threshold = np.percentile(median_sim, 50)
        repeating_mask = median_sim > threshold

        # Create soft mask for repeating (instrumental) content
        n_frames = S.shape[1]
        background_mask = np.zeros_like(S)

        for t in range(n_frames):
            if repeating_mask[t]:
                # This frame is part of repeating pattern
                # Find similar frames and average
                similar_frames = np.where(similarity[t] > threshold)[0]
                if len(similar_frames) > 0:
                    background_mask[:, t] = np.median(S[:, similar_frames], axis=1)

        # Normalize mask
        background_mask = background_mask / (S + 1e-10)
        background_mask = np.clip(background_mask, 0, 1)

        # Foreground (vocals) mask is complement
        foreground_mask = 1 - background_mask

        # Apply masks
        vocal_stft = foreground_mask * stft_data.complex_stft
        instrumental_stft = background_mask * stft_data.complex_stft

        # Reconstruct
        vocal_stft_data = STFTData(
            magnitude=np.abs(vocal_stft),
            phase=np.angle(vocal_stft),
            complex_stft=vocal_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        instrumental_stft_data = STFTData(
            magnitude=np.abs(instrumental_stft),
            phase=np.angle(instrumental_stft),
            complex_stft=instrumental_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        vocals = self.fft_processor.istft(vocal_stft_data, length=len(signal))
        instrumental = self.fft_processor.istft(instrumental_stft_data, length=len(signal))

        return vocals, instrumental
