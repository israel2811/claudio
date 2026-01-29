"""
Feature Extraction Module.

Extracts audio features for analysis, classification, and speaker identification:
- MFCCs (Mel-Frequency Cepstral Coefficients)
- Spectral features (centroid, bandwidth, rolloff)
- Prosodic features (pitch, energy)
- Voice quality features
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

from claudio.core.fft_processor import FFTProcessor


@dataclass
class AudioFeatures:
    """Container for extracted audio features."""

    mfccs: np.ndarray  # Shape: (n_mfcc, n_frames)
    mfcc_delta: Optional[np.ndarray] = None
    mfcc_delta2: Optional[np.ndarray] = None

    spectral_centroid: Optional[np.ndarray] = None
    spectral_bandwidth: Optional[np.ndarray] = None
    spectral_rolloff: Optional[np.ndarray] = None
    spectral_flatness: Optional[np.ndarray] = None
    spectral_contrast: Optional[np.ndarray] = None

    pitch: Optional[np.ndarray] = None
    pitch_confidence: Optional[np.ndarray] = None
    energy: Optional[np.ndarray] = None
    zero_crossing_rate: Optional[np.ndarray] = None

    formants: Optional[np.ndarray] = None  # Shape: (n_formants, n_frames)

    times: Optional[np.ndarray] = None
    sample_rate: int = 16000

    def to_feature_matrix(self, include_delta: bool = True) -> np.ndarray:
        """
        Combine all features into a single matrix.

        Args:
            include_delta: Include delta and delta-delta MFCCs.

        Returns:
            Feature matrix of shape (n_features, n_frames).
        """
        features = [self.mfccs]

        if include_delta and self.mfcc_delta is not None:
            features.append(self.mfcc_delta)
        if include_delta and self.mfcc_delta2 is not None:
            features.append(self.mfcc_delta2)

        if self.spectral_centroid is not None:
            features.append(self.spectral_centroid.reshape(1, -1))
        if self.spectral_bandwidth is not None:
            features.append(self.spectral_bandwidth.reshape(1, -1))
        if self.spectral_rolloff is not None:
            features.append(self.spectral_rolloff.reshape(1, -1))
        if self.spectral_flatness is not None:
            features.append(self.spectral_flatness.reshape(1, -1))
        if self.energy is not None:
            features.append(self.energy.reshape(1, -1))
        if self.zero_crossing_rate is not None:
            features.append(self.zero_crossing_rate.reshape(1, -1))

        # Ensure all features have same number of frames
        min_frames = min(f.shape[-1] for f in features)
        features = [f[..., :min_frames] for f in features]

        return np.vstack(features)

    def get_statistics(self) -> Dict[str, float]:
        """Compute statistics across all frames."""
        feature_matrix = self.to_feature_matrix()
        return {
            "mean": np.mean(feature_matrix, axis=1).tolist(),
            "std": np.std(feature_matrix, axis=1).tolist(),
            "min": np.min(feature_matrix, axis=1).tolist(),
            "max": np.max(feature_matrix, axis=1).tolist(),
        }


class FeatureExtractor:
    """
    Audio feature extractor for voice analysis.

    Extracts comprehensive features for speaker identification,
    emotion recognition, and speech analysis.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        n_fft: int = 512,
        hop_length: int = 160,
        n_mfcc: int = 13,
        n_mels: int = 40,
    ):
        """
        Initialize FeatureExtractor.

        Args:
            sample_rate: Target sample rate.
            n_fft: FFT window size.
            hop_length: Hop length in samples.
            n_mfcc: Number of MFCCs to extract.
            n_mels: Number of Mel bands.
        """
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mfcc = n_mfcc
        self.n_mels = n_mels

        self.fft_processor = FFTProcessor(n_fft, hop_length)

    def extract_all(
        self,
        signal: np.ndarray,
        sample_rate: Optional[int] = None,
        include_formants: bool = True,
    ) -> AudioFeatures:
        """
        Extract all audio features.

        Args:
            signal: Input signal.
            sample_rate: Sample rate (uses default if None).
            include_formants: Include formant extraction.

        Returns:
            AudioFeatures object with all features.
        """
        sr = sample_rate or self.sample_rate

        # Resample if needed
        if sr != self.sample_rate:
            import librosa
            signal = librosa.resample(signal, orig_sr=sr, target_sr=self.sample_rate)
            sr = self.sample_rate

        # Extract MFCCs
        mfccs = self.extract_mfccs(signal, sr)
        mfcc_delta = self._compute_delta(mfccs)
        mfcc_delta2 = self._compute_delta(mfcc_delta)

        # Extract spectral features
        spectral_centroid = self.extract_spectral_centroid(signal, sr)
        spectral_bandwidth = self.extract_spectral_bandwidth(signal, sr)
        spectral_rolloff = self.extract_spectral_rolloff(signal, sr)
        spectral_flatness = self.extract_spectral_flatness(signal, sr)

        # Extract prosodic features
        pitch, pitch_confidence = self.extract_pitch(signal, sr)
        energy = self.extract_energy(signal, sr)
        zcr = self.extract_zero_crossing_rate(signal, sr)

        # Extract formants
        formants = None
        if include_formants:
            formants = self.extract_formants(signal, sr)

        # Compute time axis
        n_frames = mfccs.shape[1]
        times = np.arange(n_frames) * self.hop_length / sr

        return AudioFeatures(
            mfccs=mfccs,
            mfcc_delta=mfcc_delta,
            mfcc_delta2=mfcc_delta2,
            spectral_centroid=spectral_centroid,
            spectral_bandwidth=spectral_bandwidth,
            spectral_rolloff=spectral_rolloff,
            spectral_flatness=spectral_flatness,
            pitch=pitch,
            pitch_confidence=pitch_confidence,
            energy=energy,
            zero_crossing_rate=zcr,
            formants=formants,
            times=times,
            sample_rate=sr,
        )

    def extract_mfccs(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_mfcc: Optional[int] = None,
    ) -> np.ndarray:
        """
        Extract Mel-Frequency Cepstral Coefficients.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            n_mfcc: Number of MFCCs (uses default if None).

        Returns:
            MFCCs array of shape (n_mfcc, n_frames).
        """
        n_mfcc = n_mfcc or self.n_mfcc

        # Compute mel spectrogram
        mel_spec, _, _ = self.fft_processor.compute_mel_spectrogram(
            signal, sample_rate, n_mels=self.n_mels
        )

        # Convert to linear power (from dB)
        mel_power = 10 ** (mel_spec / 10)

        # DCT to get MFCCs
        from scipy.fftpack import dct
        mfccs = dct(np.log(mel_power + 1e-10), type=2, axis=0, norm='ortho')[:n_mfcc]

        return mfccs

    def extract_spectral_centroid(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Extract spectral centroid (center of mass of spectrum).

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            Spectral centroid for each frame.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)
        magnitude = stft_data.magnitude
        frequencies = stft_data.frequencies

        # Compute centroid for each frame
        centroid = np.sum(frequencies[:, np.newaxis] * magnitude, axis=0) / (
            np.sum(magnitude, axis=0) + 1e-10
        )

        return centroid

    def extract_spectral_bandwidth(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Extract spectral bandwidth (spread around centroid).

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            Spectral bandwidth for each frame.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)
        magnitude = stft_data.magnitude
        frequencies = stft_data.frequencies

        # Compute centroid first
        centroid = np.sum(frequencies[:, np.newaxis] * magnitude, axis=0) / (
            np.sum(magnitude, axis=0) + 1e-10
        )

        # Compute bandwidth (second moment)
        deviation = frequencies[:, np.newaxis] - centroid
        bandwidth = np.sqrt(
            np.sum(deviation ** 2 * magnitude, axis=0) / (np.sum(magnitude, axis=0) + 1e-10)
        )

        return bandwidth

    def extract_spectral_rolloff(
        self,
        signal: np.ndarray,
        sample_rate: int,
        rolloff_percent: float = 0.85,
    ) -> np.ndarray:
        """
        Extract spectral rolloff frequency.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            rolloff_percent: Percentage of spectral energy.

        Returns:
            Rolloff frequency for each frame.
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)
        magnitude = stft_data.magnitude
        frequencies = stft_data.frequencies

        # Compute cumulative energy
        cumulative_energy = np.cumsum(magnitude, axis=0)
        total_energy = cumulative_energy[-1, :] + 1e-10

        # Find rolloff point
        threshold = rolloff_percent * total_energy
        rolloff_idx = np.argmax(cumulative_energy >= threshold, axis=0)

        # Convert to frequency
        rolloff = frequencies[rolloff_idx]

        return rolloff

    def extract_spectral_flatness(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Extract spectral flatness (tonality measure).

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            Spectral flatness for each frame (0=tonal, 1=noise-like).
        """
        stft_data = self.fft_processor.stft(signal, sample_rate)
        magnitude = stft_data.magnitude + 1e-10

        # Geometric mean / Arithmetic mean
        geometric_mean = np.exp(np.mean(np.log(magnitude), axis=0))
        arithmetic_mean = np.mean(magnitude, axis=0)

        flatness = geometric_mean / (arithmetic_mean + 1e-10)

        return flatness

    def extract_pitch(
        self,
        signal: np.ndarray,
        sample_rate: int,
        fmin: float = 50.0,
        fmax: float = 600.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract fundamental frequency (pitch) using autocorrelation.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            fmin: Minimum pitch frequency.
            fmax: Maximum pitch frequency.

        Returns:
            Tuple of (pitch_values, confidence).
        """
        # Frame parameters
        frame_length = self.n_fft
        hop_length = self.hop_length

        # Pitch period limits (in samples)
        min_period = int(sample_rate / fmax)
        max_period = int(sample_rate / fmin)

        # Number of frames
        n_frames = 1 + (len(signal) - frame_length) // hop_length

        pitch = np.zeros(n_frames)
        confidence = np.zeros(n_frames)

        for i in range(n_frames):
            start = i * hop_length
            frame = signal[start:start + frame_length]

            # Apply window
            frame = frame * np.hanning(len(frame))

            # Autocorrelation
            autocorr = np.correlate(frame, frame, mode='full')
            autocorr = autocorr[len(autocorr) // 2:]

            # Normalize
            autocorr = autocorr / (autocorr[0] + 1e-10)

            # Find peak in valid range
            if max_period < len(autocorr):
                search_region = autocorr[min_period:max_period]
                if len(search_region) > 0:
                    peak_idx = np.argmax(search_region) + min_period
                    pitch[i] = sample_rate / peak_idx
                    confidence[i] = autocorr[peak_idx]

        return pitch, confidence

    def extract_energy(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Extract frame energy (RMS).

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            Energy (RMS) for each frame.
        """
        frame_length = self.n_fft
        hop_length = self.hop_length

        n_frames = 1 + (len(signal) - frame_length) // hop_length
        energy = np.zeros(n_frames)

        for i in range(n_frames):
            start = i * hop_length
            frame = signal[start:start + frame_length]
            energy[i] = np.sqrt(np.mean(frame ** 2))

        return energy

    def extract_zero_crossing_rate(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Extract zero crossing rate.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            Zero crossing rate for each frame.
        """
        frame_length = self.n_fft
        hop_length = self.hop_length

        n_frames = 1 + (len(signal) - frame_length) // hop_length
        zcr = np.zeros(n_frames)

        for i in range(n_frames):
            start = i * hop_length
            frame = signal[start:start + frame_length]

            # Count sign changes
            signs = np.sign(frame)
            sign_changes = np.sum(np.abs(np.diff(signs)) > 0)
            zcr[i] = sign_changes / (len(frame) - 1)

        return zcr

    def extract_formants(
        self,
        signal: np.ndarray,
        sample_rate: int,
        n_formants: int = 4,
    ) -> np.ndarray:
        """
        Extract formant frequencies using LPC analysis.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            n_formants: Number of formants to extract.

        Returns:
            Formants array of shape (n_formants, n_frames).
        """
        frame_length = self.n_fft
        hop_length = self.hop_length
        lpc_order = 2 * n_formants + 2

        n_frames = 1 + (len(signal) - frame_length) // hop_length
        formants = np.zeros((n_formants, n_frames))

        for i in range(n_frames):
            start = i * hop_length
            frame = signal[start:start + frame_length]

            # Pre-emphasis
            frame = np.append(frame[0], frame[1:] - 0.97 * frame[:-1])

            # Apply window
            frame = frame * np.hamming(len(frame))

            # LPC analysis
            try:
                lpc_coeffs = self._lpc(frame, lpc_order)

                # Find roots of LPC polynomial
                roots = np.roots(lpc_coeffs)

                # Select roots with positive imaginary part (inside unit circle)
                valid_roots = roots[
                    (np.imag(roots) > 0) &
                    (np.abs(roots) < 1)
                ]

                # Convert to frequencies
                angles = np.angle(valid_roots)
                freqs = angles * sample_rate / (2 * np.pi)

                # Sort and select top formants
                freqs = np.sort(freqs[freqs > 50])[:n_formants]

                formants[:len(freqs), i] = freqs

            except Exception:
                pass  # Keep zeros on failure

        return formants

    def _lpc(self, signal: np.ndarray, order: int) -> np.ndarray:
        """
        Linear Predictive Coding using Levinson-Durbin recursion.

        Args:
            signal: Input signal.
            order: LPC order.

        Returns:
            LPC coefficients.
        """
        # Autocorrelation
        autocorr = np.correlate(signal, signal, mode='full')
        autocorr = autocorr[len(autocorr) // 2:len(autocorr) // 2 + order + 1]

        # Levinson-Durbin
        a = np.zeros(order + 1)
        a[0] = 1

        if autocorr[0] == 0:
            return a

        error = autocorr[0]

        for i in range(1, order + 1):
            # Compute reflection coefficient
            reflection = -np.sum(a[1:i] * autocorr[i-1:0:-1]) - autocorr[i]
            reflection = reflection / (error + 1e-10)

            # Update coefficients
            a_new = np.zeros(order + 1)
            a_new[0] = 1
            for j in range(1, i):
                a_new[j] = a[j] + reflection * a[i - j]
            a_new[i] = reflection

            a = a_new
            error = error * (1 - reflection ** 2)

            if error <= 0:
                break

        return a

    def _compute_delta(
        self,
        features: np.ndarray,
        window: int = 2,
    ) -> np.ndarray:
        """
        Compute delta (derivative) features.

        Args:
            features: Input features (n_features, n_frames).
            window: Delta window size.

        Returns:
            Delta features.
        """
        n_features, n_frames = features.shape
        delta = np.zeros_like(features)

        denominator = 2 * sum(i ** 2 for i in range(1, window + 1))

        for t in range(n_frames):
            numerator = np.zeros(n_features)
            for i in range(1, window + 1):
                t_plus = min(t + i, n_frames - 1)
                t_minus = max(t - i, 0)
                numerator += i * (features[:, t_plus] - features[:, t_minus])

            delta[:, t] = numerator / (denominator + 1e-10)

        return delta

    def extract_speaker_embedding(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """
        Extract speaker embedding (i-vector style).

        Simple embedding based on statistics of acoustic features.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            Speaker embedding vector.
        """
        # Extract features
        features = self.extract_all(signal, sample_rate, include_formants=False)
        feature_matrix = features.to_feature_matrix()

        # Compute statistics as embedding
        embedding = np.concatenate([
            np.mean(feature_matrix, axis=1),
            np.std(feature_matrix, axis=1),
            np.percentile(feature_matrix, 10, axis=1),
            np.percentile(feature_matrix, 90, axis=1),
        ])

        return embedding
