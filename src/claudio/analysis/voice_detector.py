"""
Voice Activity Detection (VAD) Module.

Detects speech segments in audio using multiple approaches:
- Energy-based detection
- Spectral feature-based detection
- Neural network-based detection (when available)
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from claudio.core.fft_processor import FFTProcessor
from claudio.analysis.feature_extraction import FeatureExtractor


class VADMethod(Enum):
    """Voice Activity Detection methods."""
    ENERGY = "energy"
    SPECTRAL = "spectral"
    COMBINED = "combined"
    NEURAL = "neural"


@dataclass
class VoiceSegment:
    """A detected voice segment."""

    start_time: float  # Start time in seconds
    end_time: float  # End time in seconds
    start_sample: int
    end_sample: int
    confidence: float  # Detection confidence (0-1)
    energy: float  # Average energy

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class VADResult:
    """Result of Voice Activity Detection."""

    segments: List[VoiceSegment]
    frame_labels: np.ndarray  # Binary labels per frame
    frame_confidences: np.ndarray  # Confidence per frame
    sample_rate: int
    hop_length: int

    @property
    def total_speech_duration(self) -> float:
        return sum(s.duration for s in self.segments)

    @property
    def speech_ratio(self) -> float:
        total_duration = len(self.frame_labels) * self.hop_length / self.sample_rate
        return self.total_speech_duration / total_duration if total_duration > 0 else 0

    def get_speech_signal(self, signal: np.ndarray) -> np.ndarray:
        """Extract only speech portions from signal."""
        speech_parts = []
        for segment in self.segments:
            speech_parts.append(signal[segment.start_sample:segment.end_sample])
        return np.concatenate(speech_parts) if speech_parts else np.array([])


class VoiceDetector:
    """
    Voice Activity Detector for speech/non-speech classification.

    Supports multiple detection methods and can handle noisy environments.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        method: VADMethod = VADMethod.COMBINED,
        aggressiveness: int = 2,
    ):
        """
        Initialize VoiceDetector.

        Args:
            sample_rate: Audio sample rate.
            frame_duration_ms: Frame duration in milliseconds.
            method: Detection method to use.
            aggressiveness: Detection aggressiveness (0-3, higher = more aggressive).
        """
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.method = method
        self.aggressiveness = min(max(aggressiveness, 0), 3)

        self.frame_length = int(sample_rate * frame_duration_ms / 1000)
        self.hop_length = self.frame_length // 2

        self.fft_processor = FFTProcessor(
            n_fft=self.frame_length,
            hop_length=self.hop_length,
        )
        self.feature_extractor = FeatureExtractor(
            sample_rate=sample_rate,
            n_fft=self.frame_length,
            hop_length=self.hop_length,
        )

        # Aggressiveness thresholds
        self._energy_thresholds = [0.01, 0.02, 0.04, 0.08]
        self._zcr_thresholds = [0.3, 0.25, 0.2, 0.15]
        self._spectral_thresholds = [0.3, 0.4, 0.5, 0.6]

    def detect(
        self,
        signal: np.ndarray,
        sample_rate: Optional[int] = None,
        min_speech_duration: float = 0.1,
        min_silence_duration: float = 0.05,
    ) -> VADResult:
        """
        Detect voice activity in signal.

        Args:
            signal: Input audio signal.
            sample_rate: Sample rate (uses default if None).
            min_speech_duration: Minimum speech segment duration in seconds.
            min_silence_duration: Minimum silence duration for segment split.

        Returns:
            VADResult with detected segments.
        """
        sr = sample_rate or self.sample_rate

        # Resample if needed
        if sr != self.sample_rate:
            import librosa
            signal = librosa.resample(signal, orig_sr=sr, target_sr=self.sample_rate)
            sr = self.sample_rate

        # Detect based on method
        if self.method == VADMethod.ENERGY:
            frame_probs = self._detect_energy(signal)
        elif self.method == VADMethod.SPECTRAL:
            frame_probs = self._detect_spectral(signal)
        elif self.method == VADMethod.COMBINED:
            frame_probs = self._detect_combined(signal)
        elif self.method == VADMethod.NEURAL:
            frame_probs = self._detect_neural(signal)
        else:
            raise ValueError(f"Unknown VAD method: {self.method}")

        # Apply threshold
        threshold = self._spectral_thresholds[self.aggressiveness]
        frame_labels = (frame_probs > threshold).astype(int)

        # Smooth labels (median filter)
        kernel_size = max(3, int(0.1 * sr / self.hop_length))
        if kernel_size % 2 == 0:
            kernel_size += 1
        frame_labels = scipy_signal.medfilt(frame_labels, kernel_size)

        # Convert to segments
        segments = self._labels_to_segments(
            frame_labels,
            frame_probs,
            signal,
            sr,
            min_speech_duration,
            min_silence_duration,
        )

        return VADResult(
            segments=segments,
            frame_labels=frame_labels,
            frame_confidences=frame_probs,
            sample_rate=sr,
            hop_length=self.hop_length,
        )

    def _detect_energy(self, signal: np.ndarray) -> np.ndarray:
        """Energy-based VAD."""
        n_frames = 1 + (len(signal) - self.frame_length) // self.hop_length
        energy = np.zeros(n_frames)

        for i in range(n_frames):
            start = i * self.hop_length
            frame = signal[start:start + self.frame_length]
            energy[i] = np.sqrt(np.mean(frame ** 2))

        # Normalize energy
        if np.max(energy) > 0:
            energy = energy / np.max(energy)

        # Apply dynamic threshold
        threshold = self._energy_thresholds[self.aggressiveness]
        background_level = np.percentile(energy, 10)
        dynamic_threshold = max(threshold, background_level * 2)

        probs = np.clip((energy - dynamic_threshold) / (1 - dynamic_threshold + 1e-10), 0, 1)

        return probs

    def _detect_spectral(self, signal: np.ndarray) -> np.ndarray:
        """Spectral feature-based VAD."""
        # Compute spectral features
        centroid = self.feature_extractor.extract_spectral_centroid(signal, self.sample_rate)
        flatness = self.feature_extractor.extract_spectral_flatness(signal, self.sample_rate)
        energy = self.feature_extractor.extract_energy(signal, self.sample_rate)
        zcr = self.feature_extractor.extract_zero_crossing_rate(signal, self.sample_rate)

        # Normalize features
        n_frames = min(len(centroid), len(flatness), len(energy), len(zcr))
        centroid = centroid[:n_frames]
        flatness = flatness[:n_frames]
        energy = energy[:n_frames]
        zcr = zcr[:n_frames]

        # Normalize
        centroid = (centroid - np.min(centroid)) / (np.max(centroid) - np.min(centroid) + 1e-10)
        energy = energy / (np.max(energy) + 1e-10)

        # Voice characteristics:
        # - Higher spectral centroid (but not too high)
        # - Lower flatness (more tonal)
        # - Moderate ZCR
        # - Higher energy

        voice_score = (
            0.3 * energy +
            0.3 * (1 - flatness) +
            0.2 * (1 - np.abs(zcr - 0.1) * 5).clip(0, 1) +
            0.2 * ((centroid > 0.1) & (centroid < 0.7)).astype(float)
        )

        return voice_score

    def _detect_combined(self, signal: np.ndarray) -> np.ndarray:
        """Combined energy and spectral VAD."""
        energy_probs = self._detect_energy(signal)
        spectral_probs = self._detect_spectral(signal)

        # Ensure same length
        n_frames = min(len(energy_probs), len(spectral_probs))
        energy_probs = energy_probs[:n_frames]
        spectral_probs = spectral_probs[:n_frames]

        # Combine with weighted average
        combined = 0.4 * energy_probs + 0.6 * spectral_probs

        return combined

    def _detect_neural(self, signal: np.ndarray) -> np.ndarray:
        """Neural network-based VAD (falls back to combined if unavailable)."""
        try:
            # Try to use webrtcvad or silero-vad
            import torch

            # Try Silero VAD
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,
            )

            (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

            # Convert to tensor
            audio_tensor = torch.tensor(signal).float()
            if len(audio_tensor.shape) == 1:
                audio_tensor = audio_tensor.unsqueeze(0)

            # Get speech probabilities
            speech_probs = model(audio_tensor, self.sample_rate).squeeze().numpy()

            # Resample to match frame rate
            n_target_frames = 1 + (len(signal) - self.frame_length) // self.hop_length
            if len(speech_probs) != n_target_frames:
                from scipy.interpolate import interp1d
                x_old = np.linspace(0, 1, len(speech_probs))
                x_new = np.linspace(0, 1, n_target_frames)
                f = interp1d(x_old, speech_probs, kind='linear', fill_value='extrapolate')
                speech_probs = f(x_new)

            return speech_probs

        except Exception:
            # Fall back to combined method
            return self._detect_combined(signal)

    def _labels_to_segments(
        self,
        labels: np.ndarray,
        confidences: np.ndarray,
        signal: np.ndarray,
        sample_rate: int,
        min_speech_duration: float,
        min_silence_duration: float,
    ) -> List[VoiceSegment]:
        """Convert frame labels to VoiceSegment objects."""
        segments = []

        min_speech_frames = int(min_speech_duration * sample_rate / self.hop_length)
        min_silence_frames = int(min_silence_duration * sample_rate / self.hop_length)

        # Find contiguous speech regions
        in_speech = False
        speech_start = 0
        silence_count = 0

        for i, label in enumerate(labels):
            if label == 1:
                if not in_speech:
                    speech_start = i
                    in_speech = True
                silence_count = 0
            else:
                if in_speech:
                    silence_count += 1
                    if silence_count >= min_silence_frames:
                        # End of speech segment
                        speech_end = i - silence_count

                        if speech_end - speech_start >= min_speech_frames:
                            start_sample = speech_start * self.hop_length
                            end_sample = min(speech_end * self.hop_length, len(signal))

                            segment_signal = signal[start_sample:end_sample]
                            segment_energy = np.sqrt(np.mean(segment_signal ** 2))

                            segments.append(VoiceSegment(
                                start_time=start_sample / sample_rate,
                                end_time=end_sample / sample_rate,
                                start_sample=start_sample,
                                end_sample=end_sample,
                                confidence=float(np.mean(confidences[speech_start:speech_end])),
                                energy=float(segment_energy),
                            ))

                        in_speech = False
                        silence_count = 0

        # Handle last segment
        if in_speech:
            speech_end = len(labels)
            if speech_end - speech_start >= min_speech_frames:
                start_sample = speech_start * self.hop_length
                end_sample = min(speech_end * self.hop_length, len(signal))

                segment_signal = signal[start_sample:end_sample]
                segment_energy = np.sqrt(np.mean(segment_signal ** 2))

                segments.append(VoiceSegment(
                    start_time=start_sample / sample_rate,
                    end_time=end_sample / sample_rate,
                    start_sample=start_sample,
                    end_sample=end_sample,
                    confidence=float(np.mean(confidences[speech_start:speech_end])),
                    energy=float(segment_energy),
                ))

        return segments

    def detect_speech_turns(
        self,
        signal: np.ndarray,
        sample_rate: Optional[int] = None,
        min_turn_duration: float = 0.5,
        max_gap: float = 0.3,
    ) -> List[VoiceSegment]:
        """
        Detect speech turns (longer utterances) for diarization.

        Args:
            signal: Input signal.
            sample_rate: Sample rate.
            min_turn_duration: Minimum turn duration.
            max_gap: Maximum gap to merge segments.

        Returns:
            List of speech turn segments.
        """
        vad_result = self.detect(
            signal,
            sample_rate,
            min_speech_duration=0.1,
            min_silence_duration=0.05,
        )

        # Merge close segments
        merged_segments = []
        current_segment = None

        for segment in vad_result.segments:
            if current_segment is None:
                current_segment = segment
            else:
                gap = segment.start_time - current_segment.end_time
                if gap <= max_gap:
                    # Merge segments
                    current_segment = VoiceSegment(
                        start_time=current_segment.start_time,
                        end_time=segment.end_time,
                        start_sample=current_segment.start_sample,
                        end_sample=segment.end_sample,
                        confidence=(current_segment.confidence + segment.confidence) / 2,
                        energy=(current_segment.energy + segment.energy) / 2,
                    )
                else:
                    if current_segment.duration >= min_turn_duration:
                        merged_segments.append(current_segment)
                    current_segment = segment

        if current_segment is not None and current_segment.duration >= min_turn_duration:
            merged_segments.append(current_segment)

        return merged_segments
