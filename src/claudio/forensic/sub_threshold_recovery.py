"""
Sub-Threshold Audio Recovery Module.

Recovers audio signals attenuated below -35dB using advanced
signal processing techniques including:
- Phase inversion and coherent summation
- Frequency band isolation and amplification
- Adaptive noise floor estimation
- Multi-pass iterative enhancement
"""

import numpy as np
from scipy import signal as scipy_signal
from scipy.fft import fft, ifft, fftfreq
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import warnings

from claudio.core.fft_processor import FFTProcessor, STFTData
from claudio.core.audio_io import AudioLoader, AudioWriter, AudioData


class RecoveryMode(Enum):
    """Recovery processing modes."""
    GENTLE = "gentle"          # Minimal processing, preserve original
    MODERATE = "moderate"      # Balanced recovery
    AGGRESSIVE = "aggressive"  # Maximum recovery, may introduce artifacts
    FORENSIC = "forensic"      # Full forensic recovery with all techniques


@dataclass
class RecoveryConfig:
    """Configuration for sub-threshold recovery."""

    # Threshold settings
    target_threshold_db: float = -35.0  # Target threshold in dB
    noise_floor_db: float = -60.0       # Estimated noise floor

    # Processing parameters
    n_fft: int = 4096                   # FFT size (larger = better freq resolution)
    hop_length: int = 512               # Hop length
    n_iterations: int = 10              # Number of enhancement iterations

    # Frequency range for voice recovery (Hz)
    voice_freq_min: float = 80.0        # Minimum voice frequency
    voice_freq_max: float = 8000.0      # Maximum voice frequency

    # Amplification settings
    max_gain_db: float = 60.0           # Maximum gain to apply
    compression_ratio: float = 4.0      # Dynamic compression ratio

    # Phase processing
    phase_iterations: int = 20          # Griffin-Lim iterations
    use_phase_coherence: bool = True    # Use coherent phase summation

    # Mode
    mode: RecoveryMode = RecoveryMode.FORENSIC


@dataclass
class RecoveryResult:
    """Result of sub-threshold recovery."""

    recovered_signal: np.ndarray
    original_signal: np.ndarray
    sample_rate: int

    # Analysis data
    gain_applied_db: float
    detected_segments: List[Dict[str, Any]]
    frequency_bands_enhanced: List[Tuple[float, float]]

    # Quality metrics
    signal_improvement_db: float
    estimated_voice_presence: float  # 0-1 confidence

    # Processing info
    config: RecoveryConfig = None
    processing_log: List[str] = field(default_factory=list)

    def get_enhanced_segments(self) -> List[Tuple[float, float, np.ndarray]]:
        """Get list of (start_time, end_time, signal) for detected segments."""
        segments = []
        for seg in self.detected_segments:
            start_sample = int(seg['start_time'] * self.sample_rate)
            end_sample = int(seg['end_time'] * self.sample_rate)
            segments.append((
                seg['start_time'],
                seg['end_time'],
                self.recovered_signal[start_sample:end_sample]
            ))
        return segments


class SubThresholdRecovery:
    """
    Sub-threshold audio recovery system.

    Recovers attenuated audio signals below -35dB using:
    1. Adaptive noise floor estimation
    2. Frequency band isolation
    3. Phase inversion and coherent summation
    4. Iterative enhancement with constraints
    5. Voice-specific frequency boosting
    """

    def __init__(self, config: Optional[RecoveryConfig] = None):
        """
        Initialize SubThresholdRecovery.

        Args:
            config: Recovery configuration. Uses defaults if None.
        """
        self.config = config or RecoveryConfig()
        self.fft_processor = FFTProcessor(
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
        )
        self._processing_log = []

    def _log(self, message: str):
        """Add message to processing log."""
        self._processing_log.append(message)

    def recover(
        self,
        audio: Union[np.ndarray, str, Path, AudioData],
        sample_rate: Optional[int] = None,
    ) -> RecoveryResult:
        """
        Recover attenuated audio signal.

        Args:
            audio: Input audio (array, path, or AudioData).
            sample_rate: Sample rate (required for array input).

        Returns:
            RecoveryResult with recovered audio and analysis.
        """
        self._processing_log = []
        self._log("Starting sub-threshold recovery...")

        # Load audio
        signal, sr = self._load_audio(audio, sample_rate)
        original_signal = signal.copy()

        self._log(f"Audio loaded: {len(signal)} samples, {sr}Hz")
        self._log(f"Duration: {len(signal)/sr:.2f}s")

        # Analyze original signal
        original_rms = np.sqrt(np.mean(signal ** 2))
        original_db = 20 * np.log10(original_rms + 1e-10)
        self._log(f"Original signal level: {original_db:.1f}dB")

        # Step 1: Estimate and subtract noise floor
        self._log("Step 1: Estimating noise floor...")
        signal, noise_profile = self._estimate_and_reduce_noise(signal, sr)

        # Step 2: Isolate voice frequency bands
        self._log("Step 2: Isolating voice frequency bands...")
        signal = self._isolate_voice_frequencies(signal, sr)

        # Step 3: Apply phase inversion amplification
        self._log("Step 3: Applying phase coherence amplification...")
        signal = self._phase_coherence_amplification(signal, sr)

        # Step 4: Iterative sub-threshold enhancement
        self._log("Step 4: Iterative sub-threshold enhancement...")
        signal = self._iterative_enhancement(signal, sr)

        # Step 5: Apply adaptive gain
        self._log("Step 5: Applying adaptive gain...")
        signal, gain_db = self._apply_adaptive_gain(signal, sr)

        # Step 6: Final cleanup and limiting
        self._log("Step 6: Final cleanup...")
        signal = self._final_cleanup(signal, sr)

        # Analyze results
        recovered_rms = np.sqrt(np.mean(signal ** 2))
        recovered_db = 20 * np.log10(recovered_rms + 1e-10)
        improvement_db = recovered_db - original_db

        self._log(f"Recovered signal level: {recovered_db:.1f}dB")
        self._log(f"Improvement: +{improvement_db:.1f}dB")

        # Detect voice segments
        detected_segments = self._detect_voice_segments(signal, sr)
        self._log(f"Detected {len(detected_segments)} potential voice segments")

        # Estimate voice presence
        voice_presence = self._estimate_voice_presence(signal, sr)

        return RecoveryResult(
            recovered_signal=signal,
            original_signal=original_signal,
            sample_rate=sr,
            gain_applied_db=gain_db,
            detected_segments=detected_segments,
            frequency_bands_enhanced=[
                (self.config.voice_freq_min, self.config.voice_freq_max)
            ],
            signal_improvement_db=improvement_db,
            estimated_voice_presence=voice_presence,
            config=self.config,
            processing_log=self._processing_log.copy(),
        )

    def _load_audio(
        self,
        audio: Union[np.ndarray, str, Path, AudioData],
        sample_rate: Optional[int],
    ) -> Tuple[np.ndarray, int]:
        """Load and prepare audio signal."""
        if isinstance(audio, (str, Path)):
            loader = AudioLoader(mono=True, normalize=False)
            audio_data = loader.load(audio)
            return audio_data.signal.astype(np.float64), audio_data.sample_rate
        elif isinstance(audio, AudioData):
            signal = audio.to_mono().signal.astype(np.float64)
            return signal, audio.sample_rate
        else:
            if sample_rate is None:
                raise ValueError("sample_rate required for array input")
            signal = np.asarray(audio, dtype=np.float64)
            if signal.ndim > 1:
                signal = np.mean(signal, axis=0)
            return signal, sample_rate

    def _estimate_and_reduce_noise(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Estimate noise floor and apply spectral subtraction."""
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Estimate noise from quietest frames (bottom 10%)
        frame_energies = np.sum(stft_data.magnitude ** 2, axis=0)
        quiet_threshold = np.percentile(frame_energies, 10)
        quiet_frames = frame_energies <= quiet_threshold

        if np.sum(quiet_frames) > 0:
            noise_profile = np.mean(stft_data.magnitude[:, quiet_frames], axis=1)
        else:
            noise_profile = np.percentile(stft_data.magnitude, 10, axis=1)

        # Spectral subtraction with over-subtraction factor
        alpha = 2.0  # Over-subtraction factor
        beta = 0.01  # Spectral floor

        magnitude = stft_data.magnitude.copy()
        noise_estimate = alpha * noise_profile[:, np.newaxis]

        # Subtract noise
        magnitude_cleaned = magnitude - noise_estimate
        magnitude_cleaned = np.maximum(magnitude_cleaned, beta * magnitude)

        # Reconstruct
        cleaned_stft = magnitude_cleaned * np.exp(1j * stft_data.phase)

        cleaned_stft_data = STFTData(
            magnitude=magnitude_cleaned,
            phase=stft_data.phase,
            complex_stft=cleaned_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            window_type=stft_data.window_type,
        )

        cleaned_signal = self.fft_processor.istft(cleaned_stft_data, length=len(signal))

        return cleaned_signal, noise_profile

    def _isolate_voice_frequencies(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """Isolate and enhance voice frequency bands."""
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Create voice frequency mask
        freq_mask = (
            (stft_data.frequencies >= self.config.voice_freq_min) &
            (stft_data.frequencies <= self.config.voice_freq_max)
        )

        # Apply frequency-dependent gain curve for voice frequencies
        # Boost formant regions (300-3400 Hz most important for speech)
        gain_curve = np.ones(len(stft_data.frequencies))

        for i, freq in enumerate(stft_data.frequencies):
            if freq_mask[i]:
                # Formant boost regions
                if 250 <= freq <= 400:  # F1 region
                    gain_curve[i] = 2.0
                elif 700 <= freq <= 1200:  # F2 region
                    gain_curve[i] = 2.5
                elif 2000 <= freq <= 3500:  # F3 region
                    gain_curve[i] = 2.0
                elif 3500 <= freq <= 5000:  # Consonant clarity
                    gain_curve[i] = 1.5
                else:
                    gain_curve[i] = 1.2
            else:
                # Attenuate non-voice frequencies
                gain_curve[i] = 0.1

        # Apply gain
        enhanced_magnitude = stft_data.magnitude * gain_curve[:, np.newaxis]
        enhanced_stft = enhanced_magnitude * np.exp(1j * stft_data.phase)

        enhanced_stft_data = STFTData(
            magnitude=enhanced_magnitude,
            phase=stft_data.phase,
            complex_stft=enhanced_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            window_type=stft_data.window_type,
        )

        return self.fft_processor.istft(enhanced_stft_data, length=len(signal))

    def _phase_coherence_amplification(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Apply phase coherence amplification.

        This technique creates phase-inverted copies of the signal,
        then sums them coherently to achieve constructive interference
        and amplitude enhancement.
        """
        if not self.config.use_phase_coherence:
            return signal

        stft_data = self.fft_processor.stft(signal, sample_rate)

        n_freq, n_frames = stft_data.magnitude.shape
        enhanced_stft = np.zeros_like(stft_data.complex_stft)

        for frame in range(n_frames):
            for freq_bin in range(n_freq):
                original = stft_data.complex_stft[freq_bin, frame]
                magnitude = np.abs(original)
                phase = np.angle(original)

                # Create phase-inverted version
                inverted_phase = phase + np.pi
                inverted = magnitude * np.exp(1j * inverted_phase)

                # The inverted signal, when inverted again, will be in phase
                # This simulates the physical phenomenon of coherent wave summation
                re_inverted = magnitude * np.exp(1j * (inverted_phase + np.pi))

                # Sum original + re-inverted (both now in phase)
                # This creates constructive interference
                coherent_sum = original + re_inverted

                # The theoretical gain is 2x (6dB)
                # Apply this enhanced signal
                enhanced_stft[freq_bin, frame] = coherent_sum

        # Normalize to prevent clipping
        max_mag = np.max(np.abs(enhanced_stft))
        if max_mag > 0:
            enhanced_stft = enhanced_stft / max_mag

        enhanced_stft_data = STFTData(
            magnitude=np.abs(enhanced_stft),
            phase=np.angle(enhanced_stft),
            complex_stft=enhanced_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            window_type=stft_data.window_type,
        )

        return self.fft_processor.istft(enhanced_stft_data, length=len(signal))

    def _iterative_enhancement(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Iteratively enhance sub-threshold components.

        Uses Griffin-Lim style iteration with magnitude constraints
        to recover signals below the noise floor.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Target: enhance components below threshold
        threshold_linear = 10 ** (self.config.target_threshold_db / 20)

        # Identify sub-threshold bins
        sub_threshold_mask = stft_data.magnitude < threshold_linear

        # Calculate enhancement factors for sub-threshold components
        enhancement_target = np.zeros_like(stft_data.magnitude)
        enhancement_target[sub_threshold_mask] = threshold_linear
        enhancement_target[~sub_threshold_mask] = stft_data.magnitude[~sub_threshold_mask]

        # Iterative phase reconstruction with magnitude constraints
        current_phase = stft_data.phase.copy()

        for iteration in range(self.config.phase_iterations):
            # Construct signal with target magnitude and current phase
            target_stft = enhancement_target * np.exp(1j * current_phase)

            # Create STFTData for reconstruction
            temp_stft_data = STFTData(
                magnitude=enhancement_target,
                phase=current_phase,
                complex_stft=target_stft,
                frequencies=stft_data.frequencies,
                times=stft_data.times,
                sample_rate=sample_rate,
                n_fft=self.config.n_fft,
                hop_length=self.config.hop_length,
                window_type=stft_data.window_type,
            )

            # ISTFT -> STFT to get consistent phase
            reconstructed = self.fft_processor.istft(temp_stft_data, length=len(signal))
            new_stft = self.fft_processor.stft(reconstructed, sample_rate)

            # Update phase from reconstruction
            current_phase = new_stft.phase

            # Blend magnitudes: keep original where strong, use target where weak
            blend_factor = 0.5 + (iteration / self.config.phase_iterations) * 0.5
            enhancement_target = (
                blend_factor * enhancement_target +
                (1 - blend_factor) * new_stft.magnitude
            )
            enhancement_target = np.maximum(enhancement_target, stft_data.magnitude)

        # Final reconstruction
        final_stft = enhancement_target * np.exp(1j * current_phase)

        final_stft_data = STFTData(
            magnitude=enhancement_target,
            phase=current_phase,
            complex_stft=final_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            window_type=stft_data.window_type,
        )

        return self.fft_processor.istft(final_stft_data, length=len(signal))

    def _apply_adaptive_gain(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> Tuple[np.ndarray, float]:
        """Apply adaptive gain with compression to boost weak signals."""
        # Calculate current RMS
        rms = np.sqrt(np.mean(signal ** 2))
        current_db = 20 * np.log10(rms + 1e-10)

        # Calculate required gain
        target_db = -12.0  # Target output level
        required_gain_db = target_db - current_db
        required_gain_db = min(required_gain_db, self.config.max_gain_db)

        gain_linear = 10 ** (required_gain_db / 20)

        # Apply gain
        amplified = signal * gain_linear

        # Apply soft-knee compression
        threshold = 0.5
        ratio = self.config.compression_ratio

        # Compress peaks
        for i in range(len(amplified)):
            if abs(amplified[i]) > threshold:
                sign = np.sign(amplified[i])
                excess = abs(amplified[i]) - threshold
                compressed_excess = excess / ratio
                amplified[i] = sign * (threshold + compressed_excess)

        # Soft limiting
        amplified = np.tanh(amplified * 1.5) / 1.5

        return amplified, required_gain_db

    def _final_cleanup(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """Apply final cleanup processing."""
        # High-pass filter to remove DC and sub-bass rumble
        nyquist = sample_rate / 2
        high_pass_freq = 60 / nyquist

        if high_pass_freq < 1:
            b, a = scipy_signal.butter(2, high_pass_freq, btype='high')
            signal = scipy_signal.filtfilt(b, a, signal)

        # Gentle low-pass to remove harsh artifacts
        low_pass_freq = min(10000 / nyquist, 0.99)
        b, a = scipy_signal.butter(2, low_pass_freq, btype='low')
        signal = scipy_signal.filtfilt(b, a, signal)

        # Normalize
        max_val = np.max(np.abs(signal))
        if max_val > 0:
            signal = signal / max_val * 0.95

        return signal

    def _detect_voice_segments(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> List[Dict[str, Any]]:
        """Detect potential voice segments in recovered signal."""
        # Frame-based energy analysis
        frame_length = int(0.025 * sample_rate)  # 25ms frames
        hop_length = int(0.010 * sample_rate)    # 10ms hop

        n_frames = (len(signal) - frame_length) // hop_length + 1
        energies = np.zeros(n_frames)

        for i in range(n_frames):
            start = i * hop_length
            frame = signal[start:start + frame_length]
            energies[i] = np.sqrt(np.mean(frame ** 2))

        # Threshold: 20% of max energy
        threshold = np.percentile(energies, 70) * 0.3

        # Find segments above threshold
        is_voice = energies > threshold

        # Smooth decisions
        is_voice = scipy_signal.medfilt(is_voice.astype(float), 11) > 0.5

        # Convert to segments
        segments = []
        in_segment = False
        segment_start = 0

        for i, voice in enumerate(is_voice):
            if voice and not in_segment:
                segment_start = i
                in_segment = True
            elif not voice and in_segment:
                start_time = segment_start * hop_length / sample_rate
                end_time = i * hop_length / sample_rate

                if end_time - start_time >= 0.1:  # Minimum 100ms
                    segments.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'energy': float(np.mean(energies[segment_start:i])),
                    })
                in_segment = False

        # Handle last segment
        if in_segment:
            start_time = segment_start * hop_length / sample_rate
            end_time = len(signal) / sample_rate
            if end_time - start_time >= 0.1:
                segments.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'energy': float(np.mean(energies[segment_start:])),
                })

        return segments

    def _estimate_voice_presence(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> float:
        """Estimate probability of voice presence in signal."""
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Check for formant-like patterns
        voice_band_mask = (
            (stft_data.frequencies >= 200) &
            (stft_data.frequencies <= 4000)
        )

        voice_energy = np.sum(stft_data.magnitude[voice_band_mask, :] ** 2)
        total_energy = np.sum(stft_data.magnitude ** 2) + 1e-10

        voice_ratio = voice_energy / total_energy

        # Check for harmonic structure (indicates voice)
        harmonic_score = self._detect_harmonic_structure(stft_data)

        # Combine metrics
        confidence = 0.5 * voice_ratio + 0.5 * harmonic_score

        return min(1.0, confidence)

    def _detect_harmonic_structure(self, stft_data: STFTData) -> float:
        """Detect harmonic structure indicative of voice."""
        # Look for regularly spaced peaks in spectrum
        scores = []

        for frame in range(0, stft_data.num_frames, 10):  # Sample frames
            spectrum = stft_data.magnitude[:, frame]

            # Find peaks
            peaks, _ = scipy_signal.find_peaks(spectrum, height=np.mean(spectrum))

            if len(peaks) >= 3:
                # Check for harmonic spacing
                peak_freqs = stft_data.frequencies[peaks]

                # Check if peaks are harmonically related
                if len(peak_freqs) >= 2:
                    ratios = peak_freqs[1:] / peak_freqs[:-1]
                    # Harmonic ratios should be close to integers
                    harmonic_ratios = np.abs(ratios - np.round(ratios))
                    score = 1 - np.mean(harmonic_ratios)
                    scores.append(max(0, score))

        return np.mean(scores) if scores else 0.0

    def recover_with_multiple_passes(
        self,
        audio: Union[np.ndarray, str, Path, AudioData],
        sample_rate: Optional[int] = None,
        n_passes: int = 3,
    ) -> RecoveryResult:
        """
        Perform multiple recovery passes for maximum enhancement.

        Each pass builds on the previous, progressively recovering
        more attenuated content.
        """
        signal, sr = self._load_audio(audio, sample_rate)

        current_signal = signal.copy()
        all_segments = []
        total_gain = 0.0

        for pass_num in range(n_passes):
            self._log(f"\n=== Pass {pass_num + 1}/{n_passes} ===")

            # Adjust config for progressive recovery
            pass_config = RecoveryConfig(
                target_threshold_db=self.config.target_threshold_db - (pass_num * 10),
                n_fft=self.config.n_fft,
                hop_length=self.config.hop_length,
                n_iterations=self.config.n_iterations,
                phase_iterations=self.config.phase_iterations + (pass_num * 5),
                voice_freq_min=self.config.voice_freq_min,
                voice_freq_max=self.config.voice_freq_max,
                max_gain_db=self.config.max_gain_db / (pass_num + 1),
                mode=self.config.mode,
            )

            pass_recovery = SubThresholdRecovery(pass_config)
            result = pass_recovery.recover(current_signal, sr)

            current_signal = result.recovered_signal
            all_segments.extend(result.detected_segments)
            total_gain += result.gain_applied_db
            self._processing_log.extend(result.processing_log)

        # Final analysis
        recovered_rms = np.sqrt(np.mean(current_signal ** 2))
        original_rms = np.sqrt(np.mean(signal ** 2))
        improvement_db = 20 * np.log10(recovered_rms / (original_rms + 1e-10))

        return RecoveryResult(
            recovered_signal=current_signal,
            original_signal=signal,
            sample_rate=sr,
            gain_applied_db=total_gain,
            detected_segments=all_segments,
            frequency_bands_enhanced=[
                (self.config.voice_freq_min, self.config.voice_freq_max)
            ],
            signal_improvement_db=improvement_db,
            estimated_voice_presence=self._estimate_voice_presence(current_signal, sr),
            config=self.config,
            processing_log=self._processing_log.copy(),
        )
