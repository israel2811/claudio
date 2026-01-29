"""
Audio I/O module for loading and saving audio files.

Supports multiple formats: WAV, MP3, FLAC, OGG, M4A, etc.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Union, List
from dataclasses import dataclass

import numpy as np
import soundfile as sf
import librosa
from pydub import AudioSegment


@dataclass
class AudioData:
    """Container for audio data with metadata."""

    signal: np.ndarray  # Shape: (channels, samples) or (samples,) for mono
    sample_rate: int
    duration: float  # Duration in seconds
    channels: int
    file_path: Optional[str] = None

    @property
    def is_mono(self) -> bool:
        return self.channels == 1

    @property
    def is_stereo(self) -> bool:
        return self.channels == 2

    @property
    def num_samples(self) -> int:
        if self.signal.ndim == 1:
            return len(self.signal)
        return self.signal.shape[1]

    def to_mono(self) -> "AudioData":
        """Convert to mono by averaging channels."""
        if self.is_mono:
            return self

        if self.signal.ndim == 1:
            mono_signal = self.signal
        else:
            mono_signal = np.mean(self.signal, axis=0)

        return AudioData(
            signal=mono_signal,
            sample_rate=self.sample_rate,
            duration=self.duration,
            channels=1,
            file_path=self.file_path,
        )

    def normalize(self, target_db: float = -3.0) -> "AudioData":
        """Normalize audio to target dB level."""
        max_amplitude = np.max(np.abs(self.signal))
        if max_amplitude > 0:
            target_amplitude = 10 ** (target_db / 20)
            normalized = self.signal * (target_amplitude / max_amplitude)
        else:
            normalized = self.signal

        return AudioData(
            signal=normalized,
            sample_rate=self.sample_rate,
            duration=self.duration,
            channels=self.channels,
            file_path=self.file_path,
        )


class AudioLoader:
    """
    Audio file loader supporting multiple formats.

    Handles format conversion, resampling, and channel manipulation.
    """

    SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.aiff'}

    def __init__(
        self,
        target_sr: Optional[int] = None,
        mono: bool = False,
        normalize: bool = False,
    ):
        """
        Initialize AudioLoader.

        Args:
            target_sr: Target sample rate for resampling. None keeps original.
            mono: Convert to mono if True.
            normalize: Normalize audio amplitude if True.
        """
        self.target_sr = target_sr
        self.mono = mono
        self.normalize = normalize

    def load(self, file_path: Union[str, Path]) -> AudioData:
        """
        Load audio file.

        Args:
            file_path: Path to audio file.

        Returns:
            AudioData object containing the audio signal and metadata.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {suffix}. Supported: {self.SUPPORTED_FORMATS}")

        # Try loading with soundfile first (better for WAV, FLAC)
        try:
            signal, sr = sf.read(str(file_path), always_2d=True)
            signal = signal.T  # Convert to (channels, samples)
        except Exception:
            # Fallback to librosa for other formats
            signal, sr = librosa.load(str(file_path), sr=None, mono=False)
            if signal.ndim == 1:
                signal = signal.reshape(1, -1)

        channels = signal.shape[0]

        # Resample if needed
        if self.target_sr is not None and sr != self.target_sr:
            resampled = []
            for ch in range(channels):
                resampled.append(
                    librosa.resample(signal[ch], orig_sr=sr, target_sr=self.target_sr)
                )
            signal = np.array(resampled)
            sr = self.target_sr

        duration = signal.shape[1] / sr

        audio_data = AudioData(
            signal=signal.squeeze() if channels == 1 else signal,
            sample_rate=sr,
            duration=duration,
            channels=channels,
            file_path=str(file_path),
        )

        # Convert to mono if requested
        if self.mono:
            audio_data = audio_data.to_mono()

        # Normalize if requested
        if self.normalize:
            audio_data = audio_data.normalize()

        return audio_data

    def load_multiple(self, file_paths: List[Union[str, Path]]) -> List[AudioData]:
        """Load multiple audio files."""
        return [self.load(fp) for fp in file_paths]

    def load_segment(
        self,
        file_path: Union[str, Path],
        start_time: float,
        end_time: float,
    ) -> AudioData:
        """
        Load a segment of an audio file.

        Args:
            file_path: Path to audio file.
            start_time: Start time in seconds.
            end_time: End time in seconds.

        Returns:
            AudioData object for the specified segment.
        """
        file_path = Path(file_path)

        # Load with librosa for offset/duration support
        duration = end_time - start_time
        signal, sr = librosa.load(
            str(file_path),
            sr=self.target_sr,
            mono=self.mono,
            offset=start_time,
            duration=duration,
        )

        if signal.ndim == 1:
            channels = 1
        else:
            channels = signal.shape[0]

        audio_data = AudioData(
            signal=signal,
            sample_rate=sr,
            duration=duration,
            channels=channels,
            file_path=str(file_path),
        )

        if self.normalize:
            audio_data = audio_data.normalize()

        return audio_data


class AudioWriter:
    """
    Audio file writer supporting multiple formats.
    """

    SUPPORTED_FORMATS = {'.wav', '.flac', '.ogg', '.mp3'}

    def __init__(
        self,
        sample_rate: int = 44100,
        bit_depth: int = 16,
        normalize: bool = True,
    ):
        """
        Initialize AudioWriter.

        Args:
            sample_rate: Output sample rate.
            bit_depth: Bit depth for output (16 or 24).
            normalize: Normalize before writing to prevent clipping.
        """
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.normalize = normalize

    def write(
        self,
        signal: Union[np.ndarray, AudioData],
        file_path: Union[str, Path],
        sample_rate: Optional[int] = None,
    ) -> str:
        """
        Write audio to file.

        Args:
            signal: Audio signal as numpy array or AudioData.
            file_path: Output file path.
            sample_rate: Sample rate (uses instance default if None).

        Returns:
            Path to written file.
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {suffix}. Supported: {self.SUPPORTED_FORMATS}")

        # Extract signal from AudioData if needed
        if isinstance(signal, AudioData):
            sr = sample_rate or signal.sample_rate
            data = signal.signal
        else:
            sr = sample_rate or self.sample_rate
            data = signal

        # Normalize if needed
        if self.normalize:
            max_val = np.max(np.abs(data))
            if max_val > 1.0:
                data = data / max_val * 0.99

        # Ensure correct shape for soundfile (samples, channels)
        if data.ndim == 1:
            write_data = data
        else:
            write_data = data.T

        # Determine subtype based on bit depth
        if suffix == '.wav':
            subtype = 'PCM_16' if self.bit_depth == 16 else 'PCM_24'
        elif suffix == '.flac':
            subtype = 'PCM_16' if self.bit_depth == 16 else 'PCM_24'
        else:
            subtype = None

        # Write file
        if suffix == '.mp3':
            # Use pydub for MP3 export
            audio_segment = self._numpy_to_audiosegment(write_data, sr)
            audio_segment.export(str(file_path), format='mp3')
        else:
            sf.write(str(file_path), write_data, sr, subtype=subtype)

        return str(file_path)

    def write_segments(
        self,
        segments: List[Tuple[np.ndarray, float, float]],
        output_dir: Union[str, Path],
        prefix: str = "segment",
        format: str = ".wav",
        sample_rate: Optional[int] = None,
    ) -> List[str]:
        """
        Write multiple audio segments to files.

        Args:
            segments: List of (signal, start_time, end_time) tuples.
            output_dir: Output directory.
            prefix: Filename prefix.
            format: Output format.
            sample_rate: Sample rate.

        Returns:
            List of output file paths.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_paths = []
        for i, (signal, start, end) in enumerate(segments):
            filename = f"{prefix}_{i:04d}_{start:.2f}s_{end:.2f}s{format}"
            output_path = output_dir / filename
            self.write(signal, output_path, sample_rate)
            output_paths.append(str(output_path))

        return output_paths

    def _numpy_to_audiosegment(self, data: np.ndarray, sr: int) -> AudioSegment:
        """Convert numpy array to pydub AudioSegment."""
        # Ensure data is in correct range for int16
        if data.dtype != np.int16:
            data = (data * 32767).astype(np.int16)

        if data.ndim == 1:
            channels = 1
        else:
            channels = data.shape[1] if data.shape[1] <= 2 else data.shape[0]

        return AudioSegment(
            data.tobytes(),
            frame_rate=sr,
            sample_width=2,
            channels=channels,
        )
