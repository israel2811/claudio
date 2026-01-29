"""
Multilingual Transcription Module.

Transcribes speech to text in multiple languages using:
- OpenAI Whisper
- Faster-Whisper (optimized)
- Other ASR models as fallbacks
"""

import numpy as np
from typing import Optional, List, Dict, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import warnings


class TranscriptionModel(Enum):
    """Available transcription models."""
    WHISPER_TINY = "tiny"
    WHISPER_BASE = "base"
    WHISPER_SMALL = "small"
    WHISPER_MEDIUM = "medium"
    WHISPER_LARGE = "large"
    WHISPER_LARGE_V2 = "large-v2"
    WHISPER_LARGE_V3 = "large-v3"
    FASTER_WHISPER = "faster-whisper"


@dataclass
class TranscriptionSegment:
    """A segment of transcribed text."""

    text: str
    start_time: float
    end_time: float
    language: str
    confidence: float
    words: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class TranscriptionResult:
    """Result of speech transcription."""

    text: str  # Full transcription
    segments: List[TranscriptionSegment]
    language: str
    language_confidence: float
    duration: float
    model_used: str
    processing_time: float = 0.0

    def get_text_for_timerange(
        self,
        start_time: float,
        end_time: float,
    ) -> str:
        """Get transcription for a specific time range."""
        relevant_segments = [
            s for s in self.segments
            if s.start_time < end_time and s.end_time > start_time
        ]
        return " ".join(s.text for s in relevant_segments)

    def to_srt(self) -> str:
        """Convert to SRT subtitle format."""
        lines = []
        for i, segment in enumerate(self.segments, 1):
            start = self._format_timestamp(segment.start_time)
            end = self._format_timestamp(segment.end_time)
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(segment.text)
            lines.append("")
        return "\n".join(lines)

    def to_vtt(self) -> str:
        """Convert to WebVTT subtitle format."""
        lines = ["WEBVTT", ""]
        for segment in self.segments:
            start = self._format_timestamp(segment.start_time, vtt=True)
            end = self._format_timestamp(segment.end_time, vtt=True)
            lines.append(f"{start} --> {end}")
            lines.append(segment.text)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_timestamp(seconds: float, vtt: bool = False) -> str:
        """Format timestamp for subtitles."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)

        if vtt:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class MultilingualTranscriber:
    """
    Multilingual speech-to-text transcriber.

    Supports 10+ languages including:
    - Spanish, English, French, German, Russian
    - Portuguese, Italian, Chinese, Japanese, Korean
    - Arabic, Hindi, Dutch, Polish, Turkish, etc.
    """

    SUPPORTED_LANGUAGES = {
        "es": "Spanish",
        "en": "English",
        "fr": "French",
        "de": "German",
        "ru": "Russian",
        "pt": "Portuguese",
        "it": "Italian",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "ar": "Arabic",
        "hi": "Hindi",
        "nl": "Dutch",
        "pl": "Polish",
        "tr": "Turkish",
        "vi": "Vietnamese",
        "th": "Thai",
        "id": "Indonesian",
        "sv": "Swedish",
        "no": "Norwegian",
        "da": "Danish",
        "fi": "Finnish",
        "el": "Greek",
        "he": "Hebrew",
        "hu": "Hungarian",
        "cs": "Czech",
        "ro": "Romanian",
        "uk": "Ukrainian",
        "bg": "Bulgarian",
        "sk": "Slovak",
    }

    def __init__(
        self,
        model: TranscriptionModel = TranscriptionModel.WHISPER_MEDIUM,
        device: str = "auto",
        compute_type: str = "float16",
        language: Optional[str] = None,
    ):
        """
        Initialize MultilingualTranscriber.

        Args:
            model: Transcription model to use.
            device: Device to run on ("auto", "cpu", "cuda").
            compute_type: Compute precision ("float16", "int8", "float32").
            language: Force specific language (None for auto-detect).
        """
        self.model_type = model
        self.device = device
        self.compute_type = compute_type
        self.language = language

        self._model = None
        self._model_loaded = False

    def _load_model(self):
        """Lazy load the transcription model."""
        if self._model_loaded:
            return

        import time
        start_time = time.time()

        # Determine device
        if self.device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        else:
            device = self.device

        # Try faster-whisper first (more efficient)
        if self.model_type == TranscriptionModel.FASTER_WHISPER:
            try:
                from faster_whisper import WhisperModel
                model_name = "large-v3"
                self._model = WhisperModel(
                    model_name,
                    device=device,
                    compute_type=self.compute_type,
                )
                self._model_type = "faster_whisper"
                self._model_loaded = True
                return
            except ImportError:
                warnings.warn("faster-whisper not available, falling back to whisper")

        # Use standard whisper
        try:
            import whisper

            model_name = self.model_type.value
            if model_name == "faster-whisper":
                model_name = "large-v3"

            self._model = whisper.load_model(model_name, device=device)
            self._model_type = "whisper"
            self._model_loaded = True

        except ImportError:
            # Final fallback: try transformers
            try:
                from transformers import pipeline

                self._model = pipeline(
                    "automatic-speech-recognition",
                    model="openai/whisper-medium",
                    device=0 if device == "cuda" else -1,
                )
                self._model_type = "transformers"
                self._model_loaded = True

            except Exception as e:
                raise RuntimeError(f"Could not load any transcription model: {e}")

    def transcribe(
        self,
        audio: Union[np.ndarray, str, Path],
        sample_rate: int = 16000,
        language: Optional[str] = None,
        task: str = "transcribe",
        word_timestamps: bool = True,
        initial_prompt: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Args:
            audio: Audio signal or path to audio file.
            sample_rate: Sample rate (for array input).
            language: Language code (None for auto-detect).
            task: "transcribe" or "translate" (to English).
            word_timestamps: Include word-level timestamps.
            initial_prompt: Optional prompt to guide transcription.

        Returns:
            TranscriptionResult with transcribed text and metadata.
        """
        import time
        start_time = time.time()

        self._load_model()

        language = language or self.language

        # Handle input
        if isinstance(audio, (str, Path)):
            audio_path = str(audio)
            audio_array = None
        else:
            audio_array = audio
            audio_path = None

            # Resample to 16kHz if needed
            if sample_rate != 16000:
                import librosa
                audio_array = librosa.resample(
                    audio_array,
                    orig_sr=sample_rate,
                    target_sr=16000
                )

        # Transcribe based on model type
        if self._model_type == "faster_whisper":
            result = self._transcribe_faster_whisper(
                audio_array if audio_array is not None else audio_path,
                language,
                task,
                word_timestamps,
                initial_prompt,
            )
        elif self._model_type == "whisper":
            result = self._transcribe_whisper(
                audio_array if audio_array is not None else audio_path,
                language,
                task,
                word_timestamps,
                initial_prompt,
            )
        else:
            result = self._transcribe_transformers(
                audio_array if audio_array is not None else audio_path,
                language,
            )

        result.processing_time = time.time() - start_time
        return result

    def _transcribe_faster_whisper(
        self,
        audio: Union[np.ndarray, str],
        language: Optional[str],
        task: str,
        word_timestamps: bool,
        initial_prompt: Optional[str],
    ) -> TranscriptionResult:
        """Transcribe using faster-whisper."""
        segments_raw, info = self._model.transcribe(
            audio,
            language=language,
            task=task,
            word_timestamps=word_timestamps,
            initial_prompt=initial_prompt,
            vad_filter=True,
        )

        segments = []
        full_text = []

        for segment in segments_raw:
            words = []
            if word_timestamps and hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    words.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                    })

            segments.append(TranscriptionSegment(
                text=segment.text.strip(),
                start_time=segment.start,
                end_time=segment.end,
                language=info.language,
                confidence=segment.avg_logprob if hasattr(segment, 'avg_logprob') else 0.9,
                words=words,
            ))
            full_text.append(segment.text.strip())

        return TranscriptionResult(
            text=" ".join(full_text),
            segments=segments,
            language=info.language,
            language_confidence=info.language_probability,
            duration=info.duration,
            model_used="faster-whisper",
        )

    def _transcribe_whisper(
        self,
        audio: Union[np.ndarray, str],
        language: Optional[str],
        task: str,
        word_timestamps: bool,
        initial_prompt: Optional[str],
    ) -> TranscriptionResult:
        """Transcribe using OpenAI whisper."""
        options = {
            "task": task,
            "word_timestamps": word_timestamps,
        }

        if language:
            options["language"] = language
        if initial_prompt:
            options["initial_prompt"] = initial_prompt

        result = self._model.transcribe(audio, **options)

        segments = []
        for segment in result.get("segments", []):
            words = []
            if word_timestamps and "words" in segment:
                for word in segment["words"]:
                    words.append({
                        "word": word.get("word", ""),
                        "start": word.get("start", 0),
                        "end": word.get("end", 0),
                        "probability": word.get("probability", 0),
                    })

            segments.append(TranscriptionSegment(
                text=segment["text"].strip(),
                start_time=segment["start"],
                end_time=segment["end"],
                language=result.get("language", "en"),
                confidence=segment.get("avg_logprob", 0) if "avg_logprob" in segment else 0.9,
                words=words,
            ))

        # Calculate duration
        duration = segments[-1].end_time if segments else 0

        return TranscriptionResult(
            text=result["text"].strip(),
            segments=segments,
            language=result.get("language", "en"),
            language_confidence=0.9,  # Whisper doesn't provide this directly
            duration=duration,
            model_used=f"whisper-{self.model_type.value}",
        )

    def _transcribe_transformers(
        self,
        audio: Union[np.ndarray, str],
        language: Optional[str],
    ) -> TranscriptionResult:
        """Transcribe using Hugging Face transformers."""
        if isinstance(audio, str):
            import librosa
            audio, _ = librosa.load(audio, sr=16000)

        result = self._model(
            audio,
            generate_kwargs={"language": language} if language else {},
            return_timestamps=True,
        )

        segments = []
        if "chunks" in result:
            for chunk in result["chunks"]:
                segments.append(TranscriptionSegment(
                    text=chunk["text"].strip(),
                    start_time=chunk["timestamp"][0] or 0,
                    end_time=chunk["timestamp"][1] or 0,
                    language=language or "en",
                    confidence=0.9,
                ))

        duration = segments[-1].end_time if segments else 0

        return TranscriptionResult(
            text=result["text"].strip(),
            segments=segments,
            language=language or "en",
            language_confidence=0.9,
            duration=duration,
            model_used="transformers-whisper",
        )

    def transcribe_with_diarization(
        self,
        audio: Union[np.ndarray, str, Path],
        sample_rate: int = 16000,
        language: Optional[str] = None,
        n_speakers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe with speaker attribution.

        Args:
            audio: Audio input.
            sample_rate: Sample rate.
            language: Language code.
            n_speakers: Number of speakers.

        Returns:
            Dictionary with transcription and speaker information.
        """
        from claudio.analysis.speaker_diarization import SpeakerDiarizer

        # Load audio if path
        if isinstance(audio, (str, Path)):
            from claudio.core.audio_io import AudioLoader
            loader = AudioLoader(target_sr=16000, mono=True)
            audio_data = loader.load(audio)
            signal = audio_data.signal
            sr = audio_data.sample_rate
        else:
            signal = audio
            sr = sample_rate

        # Perform diarization
        diarizer = SpeakerDiarizer(sample_rate=sr, n_speakers=n_speakers)
        diarization = diarizer.diarize(signal, sr, n_speakers=n_speakers)

        # Transcribe full audio
        transcription = self.transcribe(signal, sr, language=language)

        # Match transcription segments to speakers
        speaker_texts = {i: [] for i in range(diarization.n_speakers)}

        for trans_segment in transcription.segments:
            # Find overlapping speaker segment
            best_speaker = 0
            best_overlap = 0

            for spk_segment in diarization.segments:
                overlap_start = max(trans_segment.start_time, spk_segment.start_time)
                overlap_end = min(trans_segment.end_time, spk_segment.end_time)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = spk_segment.speaker_id

            speaker_texts[best_speaker].append({
                "text": trans_segment.text,
                "start": trans_segment.start_time,
                "end": trans_segment.end_time,
            })

        return {
            "transcription": transcription,
            "diarization": diarization,
            "speaker_transcripts": speaker_texts,
            "n_speakers": diarization.n_speakers,
        }

    def batch_transcribe(
        self,
        audio_files: List[Union[str, Path]],
        language: Optional[str] = None,
        **kwargs,
    ) -> List[TranscriptionResult]:
        """
        Transcribe multiple audio files.

        Args:
            audio_files: List of audio file paths.
            language: Language code.
            **kwargs: Additional arguments for transcribe().

        Returns:
            List of TranscriptionResult objects.
        """
        results = []
        for audio_file in audio_files:
            try:
                result = self.transcribe(audio_file, language=language, **kwargs)
                results.append(result)
            except Exception as e:
                warnings.warn(f"Failed to transcribe {audio_file}: {e}")
                results.append(None)

        return results

    def save_transcription(
        self,
        result: TranscriptionResult,
        output_path: Union[str, Path],
        format: str = "txt",
    ) -> str:
        """
        Save transcription to file.

        Args:
            result: Transcription result.
            output_path: Output file path.
            format: Output format ("txt", "srt", "vtt", "json").

        Returns:
            Path to saved file.
        """
        import json

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "txt":
            content = result.text
        elif format == "srt":
            content = result.to_srt()
        elif format == "vtt":
            content = result.to_vtt()
        elif format == "json":
            content = json.dumps({
                "text": result.text,
                "language": result.language,
                "duration": result.duration,
                "segments": [
                    {
                        "text": s.text,
                        "start": s.start_time,
                        "end": s.end_time,
                        "confidence": s.confidence,
                    }
                    for s in result.segments
                ],
            }, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unknown format: {format}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(output_path)
