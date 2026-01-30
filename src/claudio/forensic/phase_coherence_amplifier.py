"""
Phase Coherence Amplifier Module.

Implements advanced phase manipulation techniques for amplitude enhancement:
- Coherent phase summation for constructive interference
- Multi-band phase alignment
- Frequency-selective phase inversion
- Harmonic phase locking
"""

import numpy as np
from scipy import signal as scipy_signal
from scipy.fft import fft, ifft
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from claudio.core.fft_processor import FFTProcessor, STFTData


class AmplificationMethod(Enum):
    """Phase-based amplification methods."""
    COHERENT_SUM = "coherent_sum"           # Basic coherent summation
    MULTI_COPY = "multi_copy"               # Multiple phase-shifted copies
    HARMONIC_LOCK = "harmonic_lock"         # Harmonic phase alignment
    FREQUENCY_SELECTIVE = "freq_selective"  # Per-frequency band
    ADAPTIVE = "adaptive"                   # Adaptive based on content


@dataclass
class AmplificationResult:
    """Result of phase coherence amplification."""

    amplified_signal: np.ndarray
    original_signal: np.ndarray
    sample_rate: int

    # Metrics
    gain_achieved_db: float
    phase_coherence_score: float  # 0-1, how coherent the phases are
    frequency_gains: Dict[str, float]  # Gain per frequency band

    # Details
    method_used: AmplificationMethod
    n_copies_summed: int


class PhaseCoherenceAmplifier:
    """
    Phase coherence amplification system.

    Uses the physics of wave interference to achieve amplitude enhancement:
    - When two waves are in phase, they sum constructively (2x amplitude)
    - When waves are out of phase by 180°, they cancel (destructive)

    This module creates controlled phase relationships to maximize
    constructive interference and amplify weak signals.
    """

    def __init__(
        self,
        n_fft: int = 4096,
        hop_length: int = 512,
        method: AmplificationMethod = AmplificationMethod.ADAPTIVE,
    ):
        """
        Initialize PhaseCoherenceAmplifier.

        Args:
            n_fft: FFT size.
            hop_length: Hop length for STFT.
            method: Amplification method to use.
        """
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.method = method
        self.fft_processor = FFTProcessor(n_fft, hop_length)

    def amplify(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_gain_db: float = 20.0,
        frequency_range: Optional[Tuple[float, float]] = None,
    ) -> AmplificationResult:
        """
        Amplify signal using phase coherence techniques.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            target_gain_db: Target gain in dB.
            frequency_range: Optional (min_freq, max_freq) to focus on.

        Returns:
            AmplificationResult with amplified signal.
        """
        original_signal = signal.copy()

        if self.method == AmplificationMethod.COHERENT_SUM:
            result = self._coherent_summation(signal, sample_rate, target_gain_db)
        elif self.method == AmplificationMethod.MULTI_COPY:
            result = self._multi_copy_summation(signal, sample_rate, target_gain_db)
        elif self.method == AmplificationMethod.HARMONIC_LOCK:
            result = self._harmonic_phase_lock(signal, sample_rate, target_gain_db)
        elif self.method == AmplificationMethod.FREQUENCY_SELECTIVE:
            result = self._frequency_selective_amplification(
                signal, sample_rate, target_gain_db, frequency_range
            )
        else:  # ADAPTIVE
            result = self._adaptive_amplification(
                signal, sample_rate, target_gain_db, frequency_range
            )

        # Calculate actual gain
        original_rms = np.sqrt(np.mean(original_signal ** 2))
        amplified_rms = np.sqrt(np.mean(result['signal'] ** 2))
        gain_db = 20 * np.log10(amplified_rms / (original_rms + 1e-10))

        return AmplificationResult(
            amplified_signal=result['signal'],
            original_signal=original_signal,
            sample_rate=sample_rate,
            gain_achieved_db=gain_db,
            phase_coherence_score=result['coherence'],
            frequency_gains=result.get('freq_gains', {}),
            method_used=self.method,
            n_copies_summed=result.get('n_copies', 2),
        )

    def _coherent_summation(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_gain_db: float,
    ) -> Dict[str, Any]:
        """
        Basic coherent summation.

        Creates a phase-inverted copy, inverts it again, and sums
        for constructive interference.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Calculate number of copies needed for target gain
        # Each doubling adds ~6dB
        n_copies = max(2, int(2 ** (target_gain_db / 6)))
        n_copies = min(n_copies, 16)  # Limit to prevent artifacts

        # Create summed STFT
        summed_stft = np.zeros_like(stft_data.complex_stft)

        for copy in range(n_copies):
            # All copies aligned to same phase for constructive interference
            aligned_copy = stft_data.magnitude * np.exp(1j * stft_data.phase)
            summed_stft += aligned_copy

        # Normalize
        summed_stft = summed_stft / n_copies

        # Apply gain to compensate for normalization
        gain_factor = n_copies ** 0.5  # sqrt for energy preservation
        summed_stft = summed_stft * gain_factor

        # Reconstruct
        result_stft_data = STFTData(
            magnitude=np.abs(summed_stft),
            phase=np.angle(summed_stft),
            complex_stft=summed_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        amplified = self.fft_processor.istft(result_stft_data, length=len(signal))

        # Calculate phase coherence
        coherence = self._calculate_phase_coherence(stft_data)

        return {
            'signal': amplified,
            'coherence': coherence,
            'n_copies': n_copies,
        }

    def _multi_copy_summation(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_gain_db: float,
    ) -> Dict[str, Any]:
        """
        Create multiple time-shifted copies and sum with phase alignment.

        This simulates multiple microphones capturing the same source,
        then aligning and summing for enhanced SNR.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        n_copies = max(4, int(2 ** (target_gain_db / 6)))
        n_copies = min(n_copies, 32)

        # Create copies with small time shifts (simulating different paths)
        copies_stft = []
        shift_samples = int(0.001 * sample_rate)  # 1ms shifts

        for i in range(n_copies):
            # Time shift in frequency domain (phase rotation)
            shift = (i - n_copies // 2) * shift_samples
            phase_shift = 2 * np.pi * stft_data.frequencies * shift / sample_rate

            shifted_phase = stft_data.phase + phase_shift[:, np.newaxis]
            shifted_stft = stft_data.magnitude * np.exp(1j * shifted_phase)
            copies_stft.append(shifted_stft)

        # Align phases to reference (first copy)
        aligned_stft = np.zeros_like(stft_data.complex_stft)
        reference_phase = np.angle(copies_stft[0])

        for copy_stft in copies_stft:
            magnitude = np.abs(copy_stft)
            # Align to reference phase
            aligned = magnitude * np.exp(1j * reference_phase)
            aligned_stft += aligned

        # Normalize and apply gain
        aligned_stft = aligned_stft / n_copies
        gain_factor = np.sqrt(n_copies)
        aligned_stft = aligned_stft * gain_factor

        # Reconstruct
        result_stft_data = STFTData(
            magnitude=np.abs(aligned_stft),
            phase=np.angle(aligned_stft),
            complex_stft=aligned_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        amplified = self.fft_processor.istft(result_stft_data, length=len(signal))

        return {
            'signal': amplified,
            'coherence': self._calculate_phase_coherence(stft_data),
            'n_copies': n_copies,
        }

    def _harmonic_phase_lock(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_gain_db: float,
    ) -> Dict[str, Any]:
        """
        Align phases of harmonic frequencies for enhanced periodicity.

        For voice signals, harmonics should have specific phase relationships.
        Aligning them creates constructive interference at harmonic frequencies.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Estimate fundamental frequency range (voice: 80-300Hz)
        voice_f0_min = 80
        voice_f0_max = 300

        enhanced_stft = stft_data.complex_stft.copy()

        for frame in range(stft_data.num_frames):
            spectrum = stft_data.magnitude[:, frame]

            # Find potential fundamental in voice range
            f0_bin_min = int(voice_f0_min * self.n_fft / sample_rate)
            f0_bin_max = int(voice_f0_max * self.n_fft / sample_rate)

            if f0_bin_max <= f0_bin_min:
                continue

            f0_region = spectrum[f0_bin_min:f0_bin_max]
            if len(f0_region) == 0:
                continue

            f0_bin = f0_bin_min + np.argmax(f0_region)
            f0_phase = stft_data.phase[f0_bin, frame]

            # Align harmonics to fundamental phase
            n_harmonics = min(20, len(spectrum) // (f0_bin + 1))

            for h in range(2, n_harmonics + 1):
                harmonic_bin = f0_bin * h
                if harmonic_bin >= len(spectrum):
                    break

                # Expected phase for perfect harmonic
                expected_phase = h * f0_phase

                # Align to expected phase while preserving magnitude
                magnitude = spectrum[harmonic_bin]
                enhanced_stft[harmonic_bin, frame] = magnitude * np.exp(1j * expected_phase)

        # Apply gain
        gain_linear = 10 ** (target_gain_db / 40)  # Half gain to prevent clipping
        enhanced_stft = enhanced_stft * gain_linear

        # Reconstruct
        result_stft_data = STFTData(
            magnitude=np.abs(enhanced_stft),
            phase=np.angle(enhanced_stft),
            complex_stft=enhanced_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        amplified = self.fft_processor.istft(result_stft_data, length=len(signal))

        return {
            'signal': amplified,
            'coherence': self._calculate_phase_coherence(stft_data),
            'n_copies': 1,
        }

    def _frequency_selective_amplification(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_gain_db: float,
        frequency_range: Optional[Tuple[float, float]],
    ) -> Dict[str, Any]:
        """
        Apply different amplification levels to different frequency bands.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Define frequency bands
        bands = {
            'sub_bass': (20, 60),
            'bass': (60, 250),
            'low_mid': (250, 500),
            'mid': (500, 2000),
            'high_mid': (2000, 4000),
            'presence': (4000, 6000),
            'brilliance': (6000, 20000),
        }

        # Voice-focused gains (boost voice frequencies)
        band_gains_db = {
            'sub_bass': -20,      # Attenuate
            'bass': 5,            # Slight boost (chest voice)
            'low_mid': 15,        # Boost (fundamental)
            'mid': target_gain_db,  # Full boost (formants)
            'high_mid': target_gain_db * 0.8,  # Boost (clarity)
            'presence': 10,       # Boost (articulation)
            'brilliance': -10,    # Attenuate (reduce hiss)
        }

        # If frequency range specified, focus there
        if frequency_range:
            for band_name, (low, high) in bands.items():
                if not (low < frequency_range[1] and high > frequency_range[0]):
                    band_gains_db[band_name] = -40  # Heavy attenuation

        enhanced_stft = stft_data.complex_stft.copy()
        freq_gains = {}

        for band_name, (low_freq, high_freq) in bands.items():
            gain_db = band_gains_db[band_name]
            gain_linear = 10 ** (gain_db / 20)

            freq_mask = (
                (stft_data.frequencies >= low_freq) &
                (stft_data.frequencies < high_freq)
            )

            # Apply coherent summation to this band
            band_stft = enhanced_stft[freq_mask, :]

            # Align phases within band
            if np.any(freq_mask):
                reference_phase = np.angle(band_stft[0, :]) if band_stft.shape[0] > 0 else 0
                magnitude = np.abs(band_stft)
                aligned = magnitude * np.exp(1j * reference_phase)

                # Apply gain
                enhanced_stft[freq_mask, :] = aligned * gain_linear

            freq_gains[band_name] = gain_db

        # Reconstruct
        result_stft_data = STFTData(
            magnitude=np.abs(enhanced_stft),
            phase=np.angle(enhanced_stft),
            complex_stft=enhanced_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        amplified = self.fft_processor.istft(result_stft_data, length=len(signal))

        # Normalize
        max_val = np.max(np.abs(amplified))
        if max_val > 1:
            amplified = amplified / max_val * 0.95

        return {
            'signal': amplified,
            'coherence': self._calculate_phase_coherence(stft_data),
            'n_copies': 1,
            'freq_gains': freq_gains,
        }

    def _adaptive_amplification(
        self,
        signal: np.ndarray,
        sample_rate: int,
        target_gain_db: float,
        frequency_range: Optional[Tuple[float, float]],
    ) -> Dict[str, Any]:
        """
        Adaptively choose best amplification method based on signal content.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Analyze signal characteristics
        has_harmonics = self._detect_harmonic_content(stft_data)
        spectral_flatness = self._calculate_spectral_flatness(stft_data)

        # Choose method based on content
        if has_harmonics > 0.5:
            # Voice-like content - use harmonic locking
            result = self._harmonic_phase_lock(signal, sample_rate, target_gain_db)
            method_boost = self._multi_copy_summation(
                result['signal'], sample_rate, target_gain_db * 0.5
            )
            result['signal'] = method_boost['signal']
        elif spectral_flatness > 0.7:
            # Noise-like content - use multi-copy
            result = self._multi_copy_summation(signal, sample_rate, target_gain_db)
        else:
            # Mixed content - use frequency selective
            result = self._frequency_selective_amplification(
                signal, sample_rate, target_gain_db, frequency_range
            )

        return result

    def _calculate_phase_coherence(self, stft_data: STFTData) -> float:
        """Calculate overall phase coherence of signal."""
        # Phase coherence: how consistent phases are across time
        phase_diff = np.diff(stft_data.phase, axis=1)

        # Wrap to [-pi, pi]
        phase_diff = np.angle(np.exp(1j * phase_diff))

        # Coherence is inverse of phase variance
        phase_variance = np.var(phase_diff)
        coherence = np.exp(-phase_variance)

        return float(coherence)

    def _detect_harmonic_content(self, stft_data: STFTData) -> float:
        """Detect amount of harmonic content (voice-like)."""
        scores = []

        for frame in range(0, stft_data.num_frames, max(1, stft_data.num_frames // 20)):
            spectrum = stft_data.magnitude[:, frame]

            # Find peaks
            peaks, _ = scipy_signal.find_peaks(spectrum, height=np.mean(spectrum) * 2)

            if len(peaks) >= 3:
                peak_freqs = stft_data.frequencies[peaks]
                if len(peak_freqs) >= 2 and peak_freqs[0] > 0:
                    # Check harmonic spacing
                    ratios = peak_freqs[1:] / peak_freqs[0]
                    integer_ratios = np.abs(ratios - np.round(ratios))
                    harmonic_score = 1 - np.mean(np.minimum(integer_ratios, 0.5)) * 2
                    scores.append(harmonic_score)

        return np.mean(scores) if scores else 0.0

    def _calculate_spectral_flatness(self, stft_data: STFTData) -> float:
        """Calculate spectral flatness (noise vs tonal)."""
        flatness_values = []

        for frame in range(stft_data.num_frames):
            spectrum = stft_data.magnitude[:, frame] + 1e-10

            geometric_mean = np.exp(np.mean(np.log(spectrum)))
            arithmetic_mean = np.mean(spectrum)

            flatness = geometric_mean / (arithmetic_mean + 1e-10)
            flatness_values.append(flatness)

        return float(np.mean(flatness_values))

    def invert_and_sum(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_iterations: int = 5,
    ) -> np.ndarray:
        """
        Iteratively invert and sum for progressive amplification.

        Each iteration:
        1. Create phase-inverted copy
        2. Invert the inverted copy (back to original phase)
        3. Sum with original for constructive interference
        4. Repeat for progressive gain

        Theoretical gain: 2^n where n = iterations (6dB per iteration)
        """
        current = signal.copy()

        for i in range(n_iterations):
            stft_data = self.fft_processor.stft(current, sample_rate)

            # Create phase-inverted version
            inverted_stft = stft_data.magnitude * np.exp(1j * (stft_data.phase + np.pi))

            # Invert back (now in phase with original)
            reinverted_stft = np.abs(inverted_stft) * np.exp(1j * (np.angle(inverted_stft) + np.pi))

            # Sum (constructive interference)
            summed_stft = stft_data.complex_stft + reinverted_stft

            # Normalize to prevent clipping
            summed_stft = summed_stft / 2 * 1.5  # Net gain of 1.5x per iteration

            result_stft_data = STFTData(
                magnitude=np.abs(summed_stft),
                phase=np.angle(summed_stft),
                complex_stft=summed_stft,
                frequencies=stft_data.frequencies,
                times=stft_data.times,
                sample_rate=sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                window_type=stft_data.window_type,
            )

            current = self.fft_processor.istft(result_stft_data, length=len(signal))

            # Prevent clipping
            max_val = np.max(np.abs(current))
            if max_val > 0.99:
                current = current / max_val * 0.95

        return current
