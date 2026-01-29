"""
Phase Processor Module.

Implements phase manipulation techniques for audio enhancement:
- Phase inversion and coherent summation for amplitude enhancement
- Phase vocoder for time-stretching
- Phase unwrapping and reconstruction
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Optional, Tuple, List, Union
from dataclasses import dataclass

from claudio.core.fft_processor import FFTProcessor, STFTData, SpectralData


@dataclass
class PhaseCoherenceResult:
    """Result of phase coherence analysis."""

    enhanced_signal: np.ndarray
    coherence_map: np.ndarray  # Time-frequency coherence
    phase_alignment: np.ndarray  # Phase alignment quality
    gain_achieved: float  # Amplitude gain factor


class PhaseProcessor:
    """
    Phase manipulation processor for audio enhancement.

    Implements techniques for:
    - Coherent phase summation for constructive interference
    - Phase inversion for signal cancellation/enhancement
    - Phase vocoder operations
    - Multi-channel phase alignment
    """

    def __init__(
        self,
        n_fft: int = 2048,
        hop_length: Optional[int] = None,
    ):
        """
        Initialize PhaseProcessor.

        Args:
            n_fft: FFT size.
            hop_length: Hop length for STFT.
        """
        self.n_fft = n_fft
        self.hop_length = hop_length or n_fft // 4
        self.fft_processor = FFTProcessor(n_fft, hop_length)

    def coherent_summation(
        self,
        signals: List[np.ndarray],
        sample_rate: int,
        reference_idx: int = 0,
    ) -> PhaseCoherenceResult:
        """
        Perform coherent phase summation of multiple signals.

        Aligns phases of all signals to a reference and sums them
        constructively to achieve amplitude enhancement.

        Args:
            signals: List of input signals (same length).
            sample_rate: Sample rate.
            reference_idx: Index of reference signal for phase alignment.

        Returns:
            PhaseCoherenceResult with enhanced signal and metrics.
        """
        if len(signals) < 2:
            raise ValueError("At least 2 signals required for coherent summation")

        # Ensure all signals have same length
        min_length = min(len(s) for s in signals)
        signals = [s[:min_length] for s in signals]

        # Compute STFT for all signals
        stfts = [self.fft_processor.stft(s, sample_rate) for s in signals]
        reference_stft = stfts[reference_idx]

        n_freq, n_frames = reference_stft.complex_stft.shape
        n_signals = len(signals)

        # Initialize aligned STFT
        aligned_sum = np.zeros((n_freq, n_frames), dtype=complex)
        coherence_map = np.zeros((n_freq, n_frames))

        for frame in range(n_frames):
            for freq in range(n_freq):
                # Get reference phase
                ref_phase = reference_stft.phase[freq, frame]

                # Compute phase-aligned sum
                frame_sum = 0j
                phases = []

                for stft in stfts:
                    magnitude = stft.magnitude[freq, frame]
                    phase = stft.phase[freq, frame]

                    # Calculate phase difference
                    phase_diff = phase - ref_phase

                    # Align phase to reference
                    aligned = magnitude * np.exp(1j * ref_phase)
                    frame_sum += aligned
                    phases.append(phase)

                aligned_sum[freq, frame] = frame_sum

                # Compute coherence (phase consistency)
                if len(phases) > 1:
                    phase_std = np.std(np.unwrap(phases))
                    coherence_map[freq, frame] = np.exp(-phase_std)

        # Create aligned STFT data
        aligned_stft = STFTData(
            magnitude=np.abs(aligned_sum),
            phase=np.angle(aligned_sum),
            complex_stft=aligned_sum,
            frequencies=reference_stft.frequencies,
            times=reference_stft.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=reference_stft.window_type,
        )

        # Reconstruct enhanced signal
        enhanced_signal = self.fft_processor.istft(aligned_stft, length=min_length)

        # Calculate gain achieved
        original_power = np.mean(signals[reference_idx] ** 2)
        enhanced_power = np.mean(enhanced_signal ** 2)
        gain_achieved = np.sqrt(enhanced_power / (original_power + 1e-10))

        return PhaseCoherenceResult(
            enhanced_signal=enhanced_signal,
            coherence_map=coherence_map,
            phase_alignment=np.angle(aligned_sum),
            gain_achieved=gain_achieved,
        )

    def phase_inversion_enhancement(
        self,
        signal: np.ndarray,
        noise_estimate: np.ndarray,
        sample_rate: int,
        alpha: float = 1.0,
    ) -> np.ndarray:
        """
        Enhance signal using phase inversion of noise estimate.

        Inverts the phase of the noise component and adds it back
        to achieve noise cancellation through destructive interference.

        Args:
            signal: Input signal with noise.
            noise_estimate: Estimated noise component.
            sample_rate: Sample rate.
            alpha: Noise subtraction factor (0-2, default 1.0).

        Returns:
            Enhanced signal with reduced noise.
        """
        # Ensure same length
        min_length = min(len(signal), len(noise_estimate))
        signal = signal[:min_length]
        noise_estimate = noise_estimate[:min_length]

        # Compute STFTs
        signal_stft = self.fft_processor.stft(signal, sample_rate)
        noise_stft = self.fft_processor.stft(noise_estimate, sample_rate)

        # Invert noise phase (180 degree shift)
        inverted_noise = noise_stft.complex_stft * np.exp(1j * np.pi)

        # Subtract noise (add inverted)
        enhanced_stft = signal_stft.complex_stft + alpha * inverted_noise

        # Ensure no negative magnitudes (spectral floor)
        magnitude = np.maximum(np.abs(enhanced_stft), 1e-10)
        phase = np.angle(enhanced_stft)
        enhanced_stft = magnitude * np.exp(1j * phase)

        # Reconstruct
        enhanced_stft_data = STFTData(
            magnitude=magnitude,
            phase=phase,
            complex_stft=enhanced_stft,
            frequencies=signal_stft.frequencies,
            times=signal_stft.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=signal_stft.window_type,
        )

        return self.fft_processor.istft(enhanced_stft_data, length=min_length)

    def multi_source_phase_enhancement(
        self,
        mixed_signal: np.ndarray,
        sample_rate: int,
        n_iterations: int = 10,
        sparsity_weight: float = 0.1,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Enhance source separation using iterative phase reconstruction.

        Uses phase constraints and sparsity to improve separation quality.

        Args:
            mixed_signal: Mixed input signal.
            sample_rate: Sample rate.
            n_iterations: Number of phase reconstruction iterations.
            sparsity_weight: Weight for sparsity constraint.

        Returns:
            Tuple of (enhanced_signal, confidence_mask).
        """
        # Compute initial STFT
        stft_data = self.fft_processor.stft(mixed_signal, sample_rate)
        magnitude = stft_data.magnitude.copy()
        phase = stft_data.phase.copy()

        # Iterative phase reconstruction (Griffin-Lim style with modifications)
        for iteration in range(n_iterations):
            # Reconstruct with current phase
            complex_stft = magnitude * np.exp(1j * phase)

            # Create temporary STFTData for reconstruction
            temp_stft = STFTData(
                magnitude=magnitude,
                phase=phase,
                complex_stft=complex_stft,
                frequencies=stft_data.frequencies,
                times=stft_data.times,
                sample_rate=sample_rate,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                window_type=stft_data.window_type,
            )

            # ISTFT
            reconstructed = self.fft_processor.istft(temp_stft, length=len(mixed_signal))

            # STFT of reconstructed
            new_stft = self.fft_processor.stft(reconstructed, sample_rate)

            # Update phase from reconstruction
            phase = new_stft.phase

            # Apply sparsity enhancement (soft thresholding on magnitude)
            threshold = sparsity_weight * np.mean(magnitude)
            magnitude = np.maximum(magnitude - threshold, 0) * (magnitude > 0)

        # Final reconstruction
        complex_stft = magnitude * np.exp(1j * phase)
        final_stft = STFTData(
            magnitude=magnitude,
            phase=phase,
            complex_stft=complex_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        enhanced_signal = self.fft_processor.istft(final_stft, length=len(mixed_signal))

        # Compute confidence mask based on phase consistency
        confidence_mask = np.abs(np.cos(phase - stft_data.phase))

        return enhanced_signal, confidence_mask

    def instantaneous_frequency(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute instantaneous frequency from phase derivative.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            Tuple of (instantaneous_frequency, times) arrays.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Unwrap phase along time axis
        unwrapped_phase = np.unwrap(stft_data.phase, axis=1)

        # Compute phase derivative
        phase_derivative = np.diff(unwrapped_phase, axis=1)

        # Convert to instantaneous frequency
        # freq = (1 / 2*pi) * d(phase)/d(time)
        time_step = self.hop_length / sample_rate
        inst_freq = phase_derivative / (2 * np.pi * time_step)

        # Add base frequency to each bin
        inst_freq = inst_freq + stft_data.frequencies[:, np.newaxis]

        return inst_freq, stft_data.times[:-1]

    def phase_vocoder(
        self,
        signal: np.ndarray,
        sample_rate: int,
        time_stretch_ratio: float,
    ) -> np.ndarray:
        """
        Time-stretch signal using phase vocoder.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            time_stretch_ratio: Ratio for time stretching (>1 slower, <1 faster).

        Returns:
            Time-stretched signal.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        n_freq, n_frames = stft_data.complex_stft.shape
        new_n_frames = int(n_frames * time_stretch_ratio)

        # Phase accumulator
        phase_accumulator = np.zeros(n_freq)

        # Expected phase advance per frame
        expected_phase_advance = 2 * np.pi * stft_data.frequencies * self.hop_length / sample_rate

        # Interpolate magnitude and reconstruct phase
        new_magnitude = np.zeros((n_freq, new_n_frames))
        new_phase = np.zeros((n_freq, new_n_frames))

        for new_frame in range(new_n_frames):
            # Map to original frame position
            orig_pos = new_frame / time_stretch_ratio
            orig_frame = int(orig_pos)
            frac = orig_pos - orig_frame

            if orig_frame >= n_frames - 1:
                orig_frame = n_frames - 2
                frac = 1.0

            # Interpolate magnitude
            new_magnitude[:, new_frame] = (1 - frac) * stft_data.magnitude[:, orig_frame] + \
                                          frac * stft_data.magnitude[:, orig_frame + 1]

            if new_frame == 0:
                # Initialize with original phase
                phase_accumulator = stft_data.phase[:, 0]
            else:
                # Compute phase difference in original
                if orig_frame < n_frames - 1:
                    phase_diff = stft_data.phase[:, orig_frame + 1] - stft_data.phase[:, orig_frame]
                    # Unwrap
                    phase_diff = phase_diff - 2 * np.pi * np.round(
                        (phase_diff - expected_phase_advance) / (2 * np.pi)
                    )
                else:
                    phase_diff = expected_phase_advance

                # Accumulate phase
                phase_accumulator = phase_accumulator + phase_diff

            new_phase[:, new_frame] = phase_accumulator

        # Reconstruct complex STFT
        new_complex_stft = new_magnitude * np.exp(1j * new_phase)

        # Create new STFTData
        new_times = np.arange(new_n_frames) * self.hop_length / sample_rate

        new_stft_data = STFTData(
            magnitude=new_magnitude,
            phase=new_phase,
            complex_stft=new_complex_stft,
            frequencies=stft_data.frequencies,
            times=new_times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        # ISTFT
        stretched_signal = self.fft_processor.istft(new_stft_data)

        return stretched_signal

    def harmonic_phase_alignment(
        self,
        signal: np.ndarray,
        sample_rate: int,
        fundamental_freq: float,
        n_harmonics: int = 10,
    ) -> np.ndarray:
        """
        Align phases of harmonics for enhanced periodicity.

        Useful for improving clarity of tonal sounds.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            fundamental_freq: Fundamental frequency.
            n_harmonics: Number of harmonics to align.

        Returns:
            Signal with aligned harmonic phases.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        # Find frequency bins for harmonics
        harmonic_bins = []
        for h in range(1, n_harmonics + 1):
            target_freq = fundamental_freq * h
            bin_idx = np.argmin(np.abs(stft_data.frequencies - target_freq))
            harmonic_bins.append(bin_idx)

        # Align phases to fundamental
        aligned_stft = stft_data.complex_stft.copy()

        for frame in range(stft_data.num_frames):
            if harmonic_bins[0] < len(stft_data.frequencies):
                fundamental_phase = stft_data.phase[harmonic_bins[0], frame]

                for h, bin_idx in enumerate(harmonic_bins[1:], start=2):
                    if bin_idx < len(stft_data.frequencies):
                        # Expected phase relationship
                        expected_phase = h * fundamental_phase

                        # Current magnitude
                        magnitude = stft_data.magnitude[bin_idx, frame]

                        # Align phase
                        aligned_stft[bin_idx, frame] = magnitude * np.exp(1j * expected_phase)

        # Reconstruct
        aligned_stft_data = STFTData(
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

        return self.fft_processor.istft(aligned_stft_data, length=len(signal))

    def wiener_phase_filter(
        self,
        signal: np.ndarray,
        noise_power: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Apply Wiener filter with phase-aware processing.

        Args:
            signal: Input noisy signal.
            noise_power: Estimated noise power spectrum.
            sample_rate: Sample rate.

        Returns:
            Filtered signal.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)

        signal_power = stft_data.magnitude ** 2

        # Ensure noise_power has correct shape
        if noise_power.ndim == 1:
            noise_power = noise_power[:, np.newaxis]
        if noise_power.shape[0] != signal_power.shape[0]:
            # Interpolate noise power to match frequency bins
            noise_power = np.interp(
                np.arange(signal_power.shape[0]),
                np.linspace(0, signal_power.shape[0] - 1, len(noise_power)),
                noise_power.flatten()
            )[:, np.newaxis]

        # Wiener filter gain
        wiener_gain = np.maximum(signal_power - noise_power, 0) / (signal_power + 1e-10)

        # Apply gain while preserving phase
        filtered_stft = wiener_gain * stft_data.complex_stft

        # Reconstruct
        filtered_stft_data = STFTData(
            magnitude=np.abs(filtered_stft),
            phase=np.angle(filtered_stft),
            complex_stft=filtered_stft,
            frequencies=stft_data.frequencies,
            times=stft_data.times,
            sample_rate=sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            window_type=stft_data.window_type,
        )

        return self.fft_processor.istft(filtered_stft_data, length=len(signal))
