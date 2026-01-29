"""
FFT/DFT Processor Module.

Implements spectral analysis using the Fast Fourier Transform (FFT)
and Short-Time Fourier Transform (STFT) for audio signal processing.
"""

import numpy as np
from scipy import signal as scipy_signal
from scipy.fft import fft, ifft, fftfreq
from typing import Optional, Tuple, Union, List
from dataclasses import dataclass
from enum import Enum


class WindowType(Enum):
    """Window function types for STFT."""
    HANN = "hann"
    HAMMING = "hamming"
    BLACKMAN = "blackman"
    KAISER = "kaiser"
    RECTANGULAR = "rectangular"
    BARTLETT = "bartlett"
    GAUSSIAN = "gaussian"


@dataclass
class SpectralData:
    """Container for spectral analysis results."""

    magnitude: np.ndarray  # Magnitude spectrum
    phase: np.ndarray  # Phase spectrum
    frequencies: np.ndarray  # Frequency bins
    complex_spectrum: np.ndarray  # Complex FFT output
    sample_rate: int
    n_fft: int

    @property
    def power_spectrum(self) -> np.ndarray:
        """Compute power spectrum (magnitude squared)."""
        return self.magnitude ** 2

    @property
    def power_db(self) -> np.ndarray:
        """Compute power spectrum in decibels."""
        return 20 * np.log10(self.magnitude + 1e-10)

    def get_frequency_band(
        self,
        low_freq: float,
        high_freq: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Extract magnitude for a specific frequency band."""
        mask = (self.frequencies >= low_freq) & (self.frequencies <= high_freq)
        return self.frequencies[mask], self.magnitude[mask]


@dataclass
class STFTData:
    """Container for Short-Time Fourier Transform results."""

    magnitude: np.ndarray  # Shape: (freq_bins, time_frames)
    phase: np.ndarray  # Shape: (freq_bins, time_frames)
    complex_stft: np.ndarray  # Complex STFT matrix
    frequencies: np.ndarray  # Frequency bins
    times: np.ndarray  # Time frames
    sample_rate: int
    n_fft: int
    hop_length: int
    window_type: str

    @property
    def spectrogram(self) -> np.ndarray:
        """Return magnitude spectrogram."""
        return self.magnitude

    @property
    def spectrogram_db(self) -> np.ndarray:
        """Return spectrogram in decibels."""
        return 20 * np.log10(self.magnitude + 1e-10)

    @property
    def power_spectrogram(self) -> np.ndarray:
        """Return power spectrogram."""
        return self.magnitude ** 2

    @property
    def num_frames(self) -> int:
        return self.complex_stft.shape[1]

    @property
    def num_freq_bins(self) -> int:
        return self.complex_stft.shape[0]


class FFTProcessor:
    """
    FFT/DFT processor for spectral analysis.

    Provides methods for computing FFT, STFT, and various spectral
    transformations used in audio analysis and source separation.
    """

    def __init__(
        self,
        n_fft: int = 2048,
        hop_length: Optional[int] = None,
        window_type: WindowType = WindowType.HANN,
        center: bool = True,
    ):
        """
        Initialize FFT processor.

        Args:
            n_fft: FFT size (window length).
            hop_length: Hop length for STFT. Default is n_fft // 4.
            window_type: Window function type.
            center: Center frames if True.
        """
        self.n_fft = n_fft
        self.hop_length = hop_length or n_fft // 4
        self.window_type = window_type
        self.center = center
        self._window = self._create_window()

    def _create_window(self, size: Optional[int] = None) -> np.ndarray:
        """Create window function."""
        n = size or self.n_fft

        if self.window_type == WindowType.HANN:
            return scipy_signal.windows.hann(n, sym=False)
        elif self.window_type == WindowType.HAMMING:
            return scipy_signal.windows.hamming(n, sym=False)
        elif self.window_type == WindowType.BLACKMAN:
            return scipy_signal.windows.blackman(n, sym=False)
        elif self.window_type == WindowType.KAISER:
            return scipy_signal.windows.kaiser(n, beta=14)
        elif self.window_type == WindowType.RECTANGULAR:
            return np.ones(n)
        elif self.window_type == WindowType.BARTLETT:
            return scipy_signal.windows.bartlett(n, sym=False)
        elif self.window_type == WindowType.GAUSSIAN:
            return scipy_signal.windows.gaussian(n, std=n / 6)
        else:
            return scipy_signal.windows.hann(n, sym=False)

    def fft(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_fft: Optional[int] = None,
    ) -> SpectralData:
        """
        Compute FFT of a signal.

        Args:
            signal: Input signal (1D array).
            sample_rate: Sample rate of the signal.
            n_fft: FFT size. Uses instance default if None.

        Returns:
            SpectralData object with spectral information.
        """
        n_fft = n_fft or self.n_fft

        # Zero-pad if needed
        if len(signal) < n_fft:
            signal = np.pad(signal, (0, n_fft - len(signal)))
        elif len(signal) > n_fft:
            signal = signal[:n_fft]

        # Apply window
        window = self._create_window(n_fft)
        windowed = signal * window

        # Compute FFT
        spectrum = fft(windowed, n_fft)

        # Get positive frequencies only
        n_positive = n_fft // 2 + 1
        spectrum_positive = spectrum[:n_positive]

        # Compute magnitude and phase
        magnitude = np.abs(spectrum_positive)
        phase = np.angle(spectrum_positive)

        # Compute frequency bins
        frequencies = fftfreq(n_fft, 1 / sample_rate)[:n_positive]

        return SpectralData(
            magnitude=magnitude,
            phase=phase,
            frequencies=frequencies,
            complex_spectrum=spectrum_positive,
            sample_rate=sample_rate,
            n_fft=n_fft,
        )

    def ifft(
        self,
        spectral_data: Union[SpectralData, np.ndarray],
        n_fft: Optional[int] = None,
    ) -> np.ndarray:
        """
        Compute inverse FFT.

        Args:
            spectral_data: SpectralData object or complex spectrum array.
            n_fft: FFT size.

        Returns:
            Reconstructed time-domain signal.
        """
        if isinstance(spectral_data, SpectralData):
            spectrum = spectral_data.complex_spectrum
            n_fft = spectral_data.n_fft
        else:
            spectrum = spectral_data
            n_fft = n_fft or self.n_fft

        # Reconstruct full spectrum with conjugate symmetry
        if len(spectrum) == n_fft // 2 + 1:
            full_spectrum = np.zeros(n_fft, dtype=complex)
            full_spectrum[:len(spectrum)] = spectrum
            full_spectrum[len(spectrum):] = np.conj(spectrum[-2:0:-1])
        else:
            full_spectrum = spectrum

        # Compute IFFT
        signal = ifft(full_spectrum, n_fft).real

        return signal

    def stft(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_fft: Optional[int] = None,
        hop_length: Optional[int] = None,
    ) -> STFTData:
        """
        Compute Short-Time Fourier Transform.

        Args:
            signal: Input signal (1D array).
            sample_rate: Sample rate of the signal.
            n_fft: FFT size. Uses instance default if None.
            hop_length: Hop length. Uses instance default if None.

        Returns:
            STFTData object with STFT results.
        """
        n_fft = n_fft or self.n_fft
        hop_length = hop_length or self.hop_length

        # Center padding if requested
        if self.center:
            signal = np.pad(signal, (n_fft // 2, n_fft // 2), mode='reflect')

        # Calculate number of frames
        n_frames = 1 + (len(signal) - n_fft) // hop_length

        # Initialize output
        n_freq_bins = n_fft // 2 + 1
        stft_matrix = np.zeros((n_freq_bins, n_frames), dtype=complex)

        window = self._create_window(n_fft)

        # Compute STFT frame by frame
        for i in range(n_frames):
            start = i * hop_length
            frame = signal[start:start + n_fft]

            if len(frame) < n_fft:
                frame = np.pad(frame, (0, n_fft - len(frame)))

            windowed_frame = frame * window
            spectrum = fft(windowed_frame, n_fft)
            stft_matrix[:, i] = spectrum[:n_freq_bins]

        # Compute magnitude and phase
        magnitude = np.abs(stft_matrix)
        phase = np.angle(stft_matrix)

        # Compute frequency and time axes
        frequencies = fftfreq(n_fft, 1 / sample_rate)[:n_freq_bins]
        times = np.arange(n_frames) * hop_length / sample_rate

        return STFTData(
            magnitude=magnitude,
            phase=phase,
            complex_stft=stft_matrix,
            frequencies=frequencies,
            times=times,
            sample_rate=sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            window_type=self.window_type.value,
        )

    def istft(
        self,
        stft_data: Union[STFTData, np.ndarray],
        hop_length: Optional[int] = None,
        n_fft: Optional[int] = None,
        length: Optional[int] = None,
    ) -> np.ndarray:
        """
        Compute inverse Short-Time Fourier Transform.

        Args:
            stft_data: STFTData object or complex STFT matrix.
            hop_length: Hop length.
            n_fft: FFT size.
            length: Desired output length.

        Returns:
            Reconstructed time-domain signal.
        """
        if isinstance(stft_data, STFTData):
            stft_matrix = stft_data.complex_stft
            hop_length = stft_data.hop_length
            n_fft = stft_data.n_fft
        else:
            stft_matrix = stft_data
            hop_length = hop_length or self.hop_length
            n_fft = n_fft or self.n_fft

        n_freq_bins, n_frames = stft_matrix.shape
        expected_signal_length = n_fft + (n_frames - 1) * hop_length

        # Initialize output
        signal = np.zeros(expected_signal_length)
        window_sum = np.zeros(expected_signal_length)

        window = self._create_window(n_fft)

        # Overlap-add synthesis
        for i in range(n_frames):
            start = i * hop_length

            # Reconstruct full spectrum
            frame_spectrum = np.zeros(n_fft, dtype=complex)
            frame_spectrum[:n_freq_bins] = stft_matrix[:, i]
            frame_spectrum[n_freq_bins:] = np.conj(stft_matrix[-2:0:-1, i])

            # IFFT
            frame = ifft(frame_spectrum, n_fft).real

            # Apply window and add
            signal[start:start + n_fft] += frame * window
            window_sum[start:start + n_fft] += window ** 2

        # Normalize by window sum (avoid division by zero)
        window_sum = np.maximum(window_sum, 1e-10)
        signal = signal / window_sum

        # Remove center padding if used
        if self.center:
            signal = signal[n_fft // 2:-n_fft // 2]

        # Trim to desired length
        if length is not None:
            signal = signal[:length]

        return signal

    def compute_mel_spectrogram(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_mels: int = 128,
        fmin: float = 0.0,
        fmax: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute Mel spectrogram.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            n_mels: Number of Mel bands.
            fmin: Minimum frequency.
            fmax: Maximum frequency (default: sample_rate / 2).

        Returns:
            Tuple of (mel_spectrogram, frequencies, times).
        """
        fmax = fmax or sample_rate / 2

        # Compute STFT
        stft_data = self.stft(signal, sample_rate)

        # Create Mel filterbank
        mel_filters = self._create_mel_filterbank(
            sample_rate, self.n_fft, n_mels, fmin, fmax
        )

        # Apply filterbank
        mel_spec = np.dot(mel_filters, stft_data.power_spectrogram)

        # Convert to dB
        mel_spec_db = 10 * np.log10(mel_spec + 1e-10)

        # Compute Mel frequency axis
        mel_freqs = self._hz_to_mel(np.linspace(fmin, fmax, n_mels))

        return mel_spec_db, mel_freqs, stft_data.times

    def _create_mel_filterbank(
        self,
        sample_rate: int,
        n_fft: int,
        n_mels: int,
        fmin: float,
        fmax: float,
    ) -> np.ndarray:
        """Create Mel filterbank matrix."""
        n_freq_bins = n_fft // 2 + 1

        # Convert to Mel scale
        mel_min = self._hz_to_mel(fmin)
        mel_max = self._hz_to_mel(fmax)

        # Create Mel points
        mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
        hz_points = self._mel_to_hz(mel_points)

        # Convert to FFT bins
        bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)

        # Create filterbank
        filterbank = np.zeros((n_mels, n_freq_bins))

        for i in range(n_mels):
            # Rising edge
            for j in range(bin_points[i], bin_points[i + 1]):
                filterbank[i, j] = (j - bin_points[i]) / (bin_points[i + 1] - bin_points[i])
            # Falling edge
            for j in range(bin_points[i + 1], bin_points[i + 2]):
                filterbank[i, j] = (bin_points[i + 2] - j) / (bin_points[i + 2] - bin_points[i + 1])

        return filterbank

    @staticmethod
    def _hz_to_mel(hz: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert Hz to Mel scale."""
        return 2595 * np.log10(1 + hz / 700)

    @staticmethod
    def _mel_to_hz(mel: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert Mel to Hz scale."""
        return 700 * (10 ** (mel / 2595) - 1)

    def analyze_harmonics(
        self,
        signal: np.ndarray,
        sample_rate: int,
        fundamental_freq: Optional[float] = None,
        n_harmonics: int = 10,
    ) -> List[Tuple[float, float, float]]:
        """
        Analyze harmonic content of a signal.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            fundamental_freq: Fundamental frequency (estimated if None).
            n_harmonics: Number of harmonics to analyze.

        Returns:
            List of (frequency, amplitude, phase) tuples for each harmonic.
        """
        spectral = self.fft(signal, sample_rate)

        # Estimate fundamental if not provided
        if fundamental_freq is None:
            # Find dominant frequency
            peak_idx = np.argmax(spectral.magnitude[1:]) + 1
            fundamental_freq = spectral.frequencies[peak_idx]

        harmonics = []
        for h in range(1, n_harmonics + 1):
            target_freq = fundamental_freq * h

            # Find closest frequency bin
            idx = np.argmin(np.abs(spectral.frequencies - target_freq))

            harmonics.append((
                spectral.frequencies[idx],
                spectral.magnitude[idx],
                spectral.phase[idx],
            ))

        return harmonics

    def band_pass_filter(
        self,
        signal: np.ndarray,
        sample_rate: int,
        low_freq: float,
        high_freq: float,
    ) -> np.ndarray:
        """
        Apply band-pass filter in frequency domain.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            low_freq: Low cutoff frequency.
            high_freq: High cutoff frequency.

        Returns:
            Filtered signal.
        """
        spectral = self.fft(signal, sample_rate, n_fft=len(signal))

        # Create mask
        mask = (spectral.frequencies >= low_freq) & (spectral.frequencies <= high_freq)

        # Apply mask
        filtered_spectrum = spectral.complex_spectrum * mask

        # Reconstruct
        return self.ifft(filtered_spectrum, n_fft=len(signal))
