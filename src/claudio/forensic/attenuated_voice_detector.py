"""
Attenuated Voice Detector Module.

Specialized detection of voice signals that have been attenuated
below -35dB, potentially by silencing or attenuation technologies.
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from claudio.core.fft_processor import FFTProcessor, STFTData


@dataclass
class AttenuatedVoiceSegment:
    """A detected attenuated voice segment."""

    start_time: float
    end_time: float
    start_sample: int
    end_sample: int

    # Level analysis
    estimated_original_level_db: float
    current_level_db: float
    attenuation_db: float

    # Voice characteristics
    estimated_fundamental_freq: float
    formant_frequencies: List[float]
    confidence: float

    # Classification
    voice_type: str  # 'male', 'female', 'child', 'unknown'
    language_hints: List[str]

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class DetectionResult:
    """Result of attenuated voice detection."""

    segments: List[AttenuatedVoiceSegment]
    total_voice_duration: float
    n_distinct_voices: int
    overall_attenuation_estimate_db: float

    # Signal analysis
    noise_floor_db: float
    signal_floor_db: float
    dynamic_range_db: float

    # Voice map: time -> voice characteristics
    voice_activity_map: np.ndarray  # Shape: (n_frames,)
    voice_level_map: np.ndarray     # Shape: (n_frames,)


class AttenuatedVoiceDetector:
    """
    Detector for voices attenuated below normal hearing threshold.

    Designed to find voice signals that have been deliberately
    or accidentally attenuated to sub-audible levels (-35dB and below).
    """

    # Voice frequency characteristics
    VOICE_F0_RANGES = {
        'male': (80, 180),
        'female': (165, 300),
        'child': (250, 400),
    }

    FORMANT_RANGES = {
        'F1': (200, 1000),
        'F2': (700, 2500),
        'F3': (2000, 3500),
        'F4': (3000, 4500),
    }

    def __init__(
        self,
        sample_rate: int = 16000,
        n_fft: int = 4096,
        hop_length: int = 512,
        detection_threshold_db: float = -35.0,
    ):
        """
        Initialize AttenuatedVoiceDetector.

        Args:
            sample_rate: Target sample rate.
            n_fft: FFT size.
            hop_length: Hop length.
            detection_threshold_db: Threshold below which to search.
        """
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.detection_threshold_db = detection_threshold_db

        self.fft_processor = FFTProcessor(n_fft, hop_length)

    def detect(
        self,
        signal: np.ndarray,
        sample_rate: Optional[int] = None,
    ) -> DetectionResult:
        """
        Detect attenuated voice segments in signal.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.

        Returns:
            DetectionResult with detected segments.
        """
        sr = sample_rate or self.sample_rate

        # Resample if needed
        if sr != self.sample_rate:
            import librosa
            signal = librosa.resample(signal, orig_sr=sr, target_sr=self.sample_rate)
            sr = self.sample_rate

        # Analyze signal
        stft_data = self.fft_processor.stft(signal, sr)

        # Calculate noise floor
        noise_floor_db = self._estimate_noise_floor(stft_data)

        # Find sub-threshold voice activity
        voice_activity_map, voice_level_map = self._detect_sub_threshold_voice(
            stft_data, noise_floor_db
        )

        # Extract segments
        segments = self._extract_segments(
            signal, sr, stft_data, voice_activity_map, voice_level_map
        )

        # Estimate number of distinct voices
        n_voices = self._estimate_voice_count(segments)

        # Calculate overall metrics
        total_duration = sum(s.duration for s in segments)
        overall_attenuation = np.mean([s.attenuation_db for s in segments]) if segments else 0

        # Signal floor (lowest detected voice level)
        signal_floor_db = min([s.current_level_db for s in segments]) if segments else noise_floor_db

        return DetectionResult(
            segments=segments,
            total_voice_duration=total_duration,
            n_distinct_voices=n_voices,
            overall_attenuation_estimate_db=overall_attenuation,
            noise_floor_db=noise_floor_db,
            signal_floor_db=signal_floor_db,
            dynamic_range_db=0 - noise_floor_db,
            voice_activity_map=voice_activity_map,
            voice_level_map=voice_level_map,
        )

    def _estimate_noise_floor(self, stft_data: STFTData) -> float:
        """Estimate the noise floor of the signal."""
        # Use lowest 5% of frame energies
        frame_energies = np.sum(stft_data.magnitude ** 2, axis=0)
        noise_energy = np.percentile(frame_energies, 5)
        noise_db = 10 * np.log10(noise_energy + 1e-10)
        return float(noise_db)

    def _detect_sub_threshold_voice(
        self,
        stft_data: STFTData,
        noise_floor_db: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect voice activity in sub-threshold regions.

        Uses multiple features:
        1. Voice frequency band energy
        2. Harmonic structure
        3. Formant-like peaks
        4. Modulation patterns
        """
        n_frames = stft_data.num_frames
        voice_activity = np.zeros(n_frames)
        voice_level = np.zeros(n_frames)

        # Voice frequency mask (80-4000 Hz)
        voice_freq_mask = (
            (stft_data.frequencies >= 80) &
            (stft_data.frequencies <= 4000)
        )

        for frame in range(n_frames):
            spectrum = stft_data.magnitude[:, frame]
            voice_spectrum = spectrum[voice_freq_mask]

            # Calculate level
            frame_energy = np.sum(voice_spectrum ** 2)
            frame_db = 10 * np.log10(frame_energy + 1e-10)
            voice_level[frame] = frame_db

            # Only analyze sub-threshold frames
            if frame_db > self.detection_threshold_db:
                continue

            # Check for voice characteristics even in quiet signals

            # 1. Harmonic structure (voiced speech has harmonics)
            harmonic_score = self._check_harmonic_structure(spectrum, stft_data.frequencies)

            # 2. Formant-like peaks
            formant_score = self._check_formant_structure(spectrum, stft_data.frequencies)

            # 3. Spectral tilt (voice has characteristic tilt)
            tilt_score = self._check_spectral_tilt(voice_spectrum)

            # 4. Above noise floor
            snr_score = 1.0 if frame_db > noise_floor_db + 3 else 0.5

            # Combine scores
            total_score = (
                0.3 * harmonic_score +
                0.3 * formant_score +
                0.2 * tilt_score +
                0.2 * snr_score
            )

            voice_activity[frame] = total_score

        # Smooth voice activity
        kernel_size = max(3, int(0.1 * self.sample_rate / self.hop_length))
        if kernel_size % 2 == 0:
            kernel_size += 1
        voice_activity = scipy_signal.medfilt(voice_activity, kernel_size)

        return voice_activity, voice_level

    def _check_harmonic_structure(
        self,
        spectrum: np.ndarray,
        frequencies: np.ndarray,
    ) -> float:
        """Check for harmonic structure indicative of voiced speech."""
        # Focus on voice F0 range
        f0_mask = (frequencies >= 80) & (frequencies <= 400)
        f0_spectrum = spectrum[f0_mask]
        f0_freqs = frequencies[f0_mask]

        if len(f0_spectrum) < 10:
            return 0.0

        # Find peaks
        peaks, properties = scipy_signal.find_peaks(
            f0_spectrum,
            height=np.mean(f0_spectrum) * 0.5,
            distance=5
        )

        if len(peaks) < 2:
            return 0.0

        peak_freqs = f0_freqs[peaks]

        # Check if peaks are harmonically related
        if peak_freqs[0] > 0:
            ratios = peak_freqs[1:] / peak_freqs[0]
            integer_distances = np.abs(ratios - np.round(ratios))
            harmonic_score = 1 - np.mean(np.minimum(integer_distances, 0.5)) * 2
            return max(0, harmonic_score)

        return 0.0

    def _check_formant_structure(
        self,
        spectrum: np.ndarray,
        frequencies: np.ndarray,
    ) -> float:
        """Check for formant-like spectral peaks."""
        scores = []

        for formant_name, (f_low, f_high) in self.FORMANT_RANGES.items():
            mask = (frequencies >= f_low) & (frequencies <= f_high)
            formant_spectrum = spectrum[mask]

            if len(formant_spectrum) < 5:
                continue

            # Look for a clear peak in formant region
            peaks, properties = scipy_signal.find_peaks(
                formant_spectrum,
                height=np.mean(formant_spectrum) * 1.5
            )

            if len(peaks) > 0:
                # Peak prominence relative to surroundings
                peak_height = np.max(formant_spectrum[peaks])
                mean_height = np.mean(formant_spectrum)
                prominence = (peak_height - mean_height) / (mean_height + 1e-10)
                scores.append(min(1.0, prominence / 2))
            else:
                scores.append(0.0)

        return np.mean(scores) if scores else 0.0

    def _check_spectral_tilt(self, voice_spectrum: np.ndarray) -> float:
        """Check for voice-like spectral tilt (high frequencies attenuated)."""
        if len(voice_spectrum) < 10:
            return 0.0

        # Voice typically has -6 to -12 dB/octave tilt
        n_bins = len(voice_spectrum)
        low_energy = np.mean(voice_spectrum[:n_bins // 3] ** 2)
        high_energy = np.mean(voice_spectrum[2 * n_bins // 3:] ** 2)

        if low_energy > 0:
            ratio = high_energy / (low_energy + 1e-10)
            # Expected ratio for voice: 0.1 to 0.5
            if 0.05 < ratio < 0.7:
                return 1.0
            elif ratio < 0.05:
                return 0.5  # Too much tilt
            else:
                return 0.3  # Too little tilt

        return 0.0

    def _extract_segments(
        self,
        signal: np.ndarray,
        sample_rate: int,
        stft_data: STFTData,
        voice_activity: np.ndarray,
        voice_level: np.ndarray,
    ) -> List[AttenuatedVoiceSegment]:
        """Extract voice segments from activity map."""
        segments = []

        # Threshold voice activity
        threshold = 0.4
        is_voice = voice_activity > threshold

        # Find contiguous regions
        in_segment = False
        segment_start = 0

        for i, voice in enumerate(is_voice):
            if voice and not in_segment:
                segment_start = i
                in_segment = True
            elif not voice and in_segment:
                # End of segment
                segment = self._create_segment(
                    signal, sample_rate, stft_data,
                    segment_start, i, voice_level
                )
                if segment is not None:
                    segments.append(segment)
                in_segment = False

        # Handle last segment
        if in_segment:
            segment = self._create_segment(
                signal, sample_rate, stft_data,
                segment_start, len(is_voice), voice_level
            )
            if segment is not None:
                segments.append(segment)

        return segments

    def _create_segment(
        self,
        signal: np.ndarray,
        sample_rate: int,
        stft_data: STFTData,
        frame_start: int,
        frame_end: int,
        voice_level: np.ndarray,
    ) -> Optional[AttenuatedVoiceSegment]:
        """Create a segment from frame indices."""
        start_sample = frame_start * self.hop_length
        end_sample = min(frame_end * self.hop_length, len(signal))

        start_time = start_sample / sample_rate
        end_time = end_sample / sample_rate

        # Minimum duration: 50ms
        if end_time - start_time < 0.05:
            return None

        # Calculate levels
        segment_signal = signal[start_sample:end_sample]
        current_level_db = 20 * np.log10(np.sqrt(np.mean(segment_signal ** 2)) + 1e-10)

        # Estimate original level (voice typically -20 to -10 dB)
        estimated_original_db = -15.0
        attenuation_db = estimated_original_db - current_level_db

        # Analyze voice characteristics
        segment_spectrum = np.mean(
            stft_data.magnitude[:, frame_start:frame_end],
            axis=1
        )

        f0, voice_type = self._estimate_fundamental(segment_spectrum, stft_data.frequencies)
        formants = self._estimate_formants(segment_spectrum, stft_data.frequencies)

        # Confidence based on voice activity in segment
        confidence = float(np.mean(voice_level[frame_start:frame_end] > -50))

        return AttenuatedVoiceSegment(
            start_time=start_time,
            end_time=end_time,
            start_sample=start_sample,
            end_sample=end_sample,
            estimated_original_level_db=estimated_original_db,
            current_level_db=current_level_db,
            attenuation_db=attenuation_db,
            estimated_fundamental_freq=f0,
            formant_frequencies=formants,
            confidence=confidence,
            voice_type=voice_type,
            language_hints=[],
        )

    def _estimate_fundamental(
        self,
        spectrum: np.ndarray,
        frequencies: np.ndarray,
    ) -> Tuple[float, str]:
        """Estimate fundamental frequency and voice type."""
        # Search in F0 range
        f0_mask = (frequencies >= 60) & (frequencies <= 500)
        f0_spectrum = spectrum[f0_mask]
        f0_freqs = frequencies[f0_mask]

        if len(f0_spectrum) < 5:
            return 0.0, 'unknown'

        # Find dominant peak
        peak_idx = np.argmax(f0_spectrum)
        f0 = f0_freqs[peak_idx]

        # Classify voice type
        if 80 <= f0 <= 180:
            voice_type = 'male'
        elif 165 <= f0 <= 300:
            voice_type = 'female'
        elif 250 <= f0 <= 400:
            voice_type = 'child'
        else:
            voice_type = 'unknown'

        return float(f0), voice_type

    def _estimate_formants(
        self,
        spectrum: np.ndarray,
        frequencies: np.ndarray,
    ) -> List[float]:
        """Estimate formant frequencies."""
        formants = []

        for formant_name, (f_low, f_high) in self.FORMANT_RANGES.items():
            mask = (frequencies >= f_low) & (frequencies <= f_high)
            formant_spectrum = spectrum[mask]
            formant_freqs = frequencies[mask]

            if len(formant_spectrum) < 3:
                continue

            # Find highest peak
            peaks, _ = scipy_signal.find_peaks(formant_spectrum)
            if len(peaks) > 0:
                highest_peak = peaks[np.argmax(formant_spectrum[peaks])]
                formants.append(float(formant_freqs[highest_peak]))

        return formants

    def _estimate_voice_count(
        self,
        segments: List[AttenuatedVoiceSegment],
    ) -> int:
        """Estimate number of distinct voices."""
        if not segments:
            return 0

        # Cluster by F0 and formants
        f0_values = [s.estimated_fundamental_freq for s in segments if s.estimated_fundamental_freq > 0]

        if len(f0_values) < 2:
            return 1

        # Simple clustering by F0 ranges
        f0_array = np.array(f0_values)

        # Use histogram to find clusters
        hist, bin_edges = np.histogram(f0_array, bins='auto')

        # Count significant clusters
        threshold = max(hist) * 0.3
        n_clusters = np.sum(hist > threshold)

        return max(1, min(n_clusters, 30))  # Cap at 30

    def detect_with_enhancement(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> Tuple[DetectionResult, np.ndarray]:
        """
        Detect and enhance attenuated voices.

        Returns both detection results and enhanced signal.
        """
        from claudio.forensic.phase_coherence_amplifier import PhaseCoherenceAmplifier

        # First detection pass
        result = self.detect(signal, sample_rate)

        if not result.segments:
            return result, signal

        # Enhance detected regions
        amplifier = PhaseCoherenceAmplifier()
        enhanced = signal.copy()

        for segment in result.segments:
            segment_signal = signal[segment.start_sample:segment.end_sample]

            # Calculate required gain
            target_db = -20.0  # Target audible level
            required_gain = target_db - segment.current_level_db

            # Amplify segment
            amp_result = amplifier.amplify(
                segment_signal,
                sample_rate,
                target_gain_db=min(required_gain, 40),
                frequency_range=(80, 4000),
            )

            # Blend into output
            enhanced[segment.start_sample:segment.end_sample] = amp_result.amplified_signal

        return result, enhanced
