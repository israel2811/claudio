"""
Message Extractor Module.

Extracts and deciphers messages (words, phrases, paragraphs) from
recovered audio in multiple languages.
"""

import numpy as np
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json


class MessageConfidence(Enum):
    """Confidence levels for extracted messages."""
    HIGH = "high"        # >80% confidence
    MEDIUM = "medium"    # 50-80% confidence
    LOW = "low"          # 20-50% confidence
    UNCERTAIN = "uncertain"  # <20% confidence


@dataclass
class ExtractedMessage:
    """A single extracted message."""

    text: str
    language: str
    start_time: float
    end_time: float

    # Confidence
    confidence: float
    confidence_level: MessageConfidence

    # Source info
    speaker_id: Optional[int] = None
    voice_type: str = "unknown"

    # Analysis
    word_count: int = 0
    detected_entities: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None

    # Alternative interpretations
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Complete message extraction result."""

    messages: List[ExtractedMessage]
    total_words_extracted: int
    languages_detected: List[str]
    n_speakers: int

    # Full transcript
    full_transcript: str
    full_transcript_by_speaker: Dict[int, str]

    # Summary
    summary: Optional[str] = None
    key_phrases: List[str] = field(default_factory=list)


class MessageExtractor:
    """
    Message extractor for forensic audio recovery.

    Attempts to extract all possible messages (words, phrases, paragraphs)
    from recovered audio in multiple languages.
    """

    SUPPORTED_LANGUAGES = [
        'es',  # Spanish
        'en',  # English
        'fr',  # French
        'de',  # German
        'ru',  # Russian
        'pt',  # Portuguese
        'it',  # Italian
        'zh',  # Chinese
        'ja',  # Japanese
        'ko',  # Korean
        'ar',  # Arabic
        'hi',  # Hindi
        'nl',  # Dutch
        'pl',  # Polish
        'tr',  # Turkish
    ]

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        min_confidence: float = 0.2,
        try_all_languages: bool = True,
    ):
        """
        Initialize MessageExtractor.

        Args:
            languages: Languages to try (default: top 10).
            min_confidence: Minimum confidence to include message.
            try_all_languages: Try all supported languages.
        """
        self.languages = languages or self.SUPPORTED_LANGUAGES[:10]
        self.min_confidence = min_confidence
        self.try_all_languages = try_all_languages

        self._transcriber = None
        self._analyzer = None

    def _get_transcriber(self):
        """Lazy load transcriber."""
        if self._transcriber is None:
            try:
                from claudio.transcription.transcriber import MultilingualTranscriber
                self._transcriber = MultilingualTranscriber()
            except ImportError:
                raise RuntimeError("Transcription module not available")
        return self._transcriber

    def _get_analyzer(self):
        """Lazy load LLM analyzer."""
        if self._analyzer is None:
            try:
                from claudio.transcription.llm_analyzer import LLMAnalyzer, LLMProvider
                self._analyzer = LLMAnalyzer(provider=LLMProvider.LOCAL)
            except ImportError:
                self._analyzer = None
        return self._analyzer

    def extract(
        self,
        audio_segments: List[Dict[str, Any]],
        sample_rate: int,
        speaker_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> ExtractionResult:
        """
        Extract messages from audio segments.

        Args:
            audio_segments: List of {'signal': np.ndarray, 'start_time': float, ...}
            sample_rate: Sample rate.
            speaker_segments: Optional speaker diarization info.

        Returns:
            ExtractionResult with all extracted messages.
        """
        messages = []
        languages_detected = set()
        full_transcript_parts = []
        speaker_transcripts = {}

        transcriber = self._get_transcriber()

        for i, segment in enumerate(audio_segments):
            signal = segment.get('signal')
            if signal is None or len(signal) < sample_rate * 0.2:
                continue

            start_time = segment.get('start_time', 0)
            end_time = segment.get('end_time', len(signal) / sample_rate)
            voice_type = segment.get('voice_type', 'unknown')
            speaker_id = segment.get('speaker_id', i)

            # Try transcription in multiple languages
            segment_messages = self._transcribe_segment(
                signal, sample_rate, start_time, end_time,
                voice_type, speaker_id
            )

            for msg in segment_messages:
                if msg.confidence >= self.min_confidence:
                    messages.append(msg)
                    languages_detected.add(msg.language)
                    full_transcript_parts.append(msg.text)

                    if speaker_id not in speaker_transcripts:
                        speaker_transcripts[speaker_id] = []
                    speaker_transcripts[speaker_id].append(msg.text)

        # Sort messages by time
        messages.sort(key=lambda m: m.start_time)

        # Build full transcripts
        full_transcript = " ".join(full_transcript_parts)
        full_by_speaker = {
            spk: " ".join(texts)
            for spk, texts in speaker_transcripts.items()
        }

        # Count words
        total_words = sum(m.word_count for m in messages)

        # Count speakers
        n_speakers = len(set(m.speaker_id for m in messages if m.speaker_id is not None))

        # Generate summary if analyzer available
        summary = None
        key_phrases = []

        analyzer = self._get_analyzer()
        if analyzer and full_transcript:
            try:
                analysis = analyzer.extract_key_information(full_transcript)
                summary = analysis.get('summary')
                key_phrases = analysis.get('key_phrases', [])
            except Exception:
                pass

        return ExtractionResult(
            messages=messages,
            total_words_extracted=total_words,
            languages_detected=list(languages_detected),
            n_speakers=max(1, n_speakers),
            full_transcript=full_transcript,
            full_transcript_by_speaker=full_by_speaker,
            summary=summary,
            key_phrases=key_phrases,
        )

    def _transcribe_segment(
        self,
        signal: np.ndarray,
        sample_rate: int,
        start_time: float,
        end_time: float,
        voice_type: str,
        speaker_id: int,
    ) -> List[ExtractedMessage]:
        """Transcribe a single segment in multiple languages."""
        messages = []
        transcriber = self._get_transcriber()

        # Determine which languages to try
        if self.try_all_languages:
            languages_to_try = self.languages
        else:
            # Try to detect language first
            try:
                from claudio.transcription.language_detector import LanguageDetector
                detector = LanguageDetector()
                detection = detector.detect_from_audio(signal, sample_rate)
                # Try detected language first, then others
                detected = detection.language_code
                languages_to_try = [detected] + [l for l in self.languages if l != detected][:5]
            except Exception:
                languages_to_try = self.languages[:5]

        best_results = {}

        for lang in languages_to_try:
            try:
                result = transcriber.transcribe(
                    signal,
                    sample_rate=sample_rate,
                    language=lang,
                    word_timestamps=True,
                )

                if result.text and len(result.text.strip()) > 0:
                    # Calculate confidence
                    confidence = result.language_confidence

                    # Store result
                    best_results[lang] = {
                        'text': result.text.strip(),
                        'confidence': confidence,
                        'segments': result.segments,
                    }

            except Exception:
                continue

        if not best_results:
            return []

        # Find best result
        best_lang = max(best_results, key=lambda k: best_results[k]['confidence'])
        best = best_results[best_lang]

        # Determine confidence level
        conf = best['confidence']
        if conf >= 0.8:
            conf_level = MessageConfidence.HIGH
        elif conf >= 0.5:
            conf_level = MessageConfidence.MEDIUM
        elif conf >= 0.2:
            conf_level = MessageConfidence.LOW
        else:
            conf_level = MessageConfidence.UNCERTAIN

        # Build alternatives list
        alternatives = [
            {'language': lang, 'text': data['text'], 'confidence': data['confidence']}
            for lang, data in best_results.items()
            if lang != best_lang
        ]

        # Count words
        word_count = len(best['text'].split())

        message = ExtractedMessage(
            text=best['text'],
            language=best_lang,
            start_time=start_time,
            end_time=end_time,
            confidence=conf,
            confidence_level=conf_level,
            speaker_id=speaker_id,
            voice_type=voice_type,
            word_count=word_count,
            alternatives=alternatives,
        )

        messages.append(message)

        return messages

    def extract_from_forensic_result(
        self,
        forensic_result: Any,
    ) -> ExtractionResult:
        """
        Extract messages from a ForensicAnalysisResult.

        Args:
            forensic_result: Result from ForensicAudioAnalyzer.

        Returns:
            ExtractionResult with all messages.
        """
        segments = []

        for seg in forensic_result.enhanced_segments:
            segments.append({
                'signal': seg['signal'],
                'start_time': seg['start_time'],
                'end_time': seg['end_time'],
                'voice_type': seg.get('voice_type', 'unknown'),
                'speaker_id': seg.get('id', 0),
            })

        return self.extract(segments, forensic_result.sample_rate)

    def save_extraction(
        self,
        result: ExtractionResult,
        output_path: Union[str, Path],
        format: str = "txt",
    ) -> str:
        """
        Save extraction results to file.

        Args:
            result: Extraction result.
            output_path: Output file path.
            format: Output format (txt, json, srt).

        Returns:
            Path to saved file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "txt":
            content = self._format_txt(result)
        elif format == "json":
            content = self._format_json(result)
        elif format == "srt":
            content = self._format_srt(result)
        else:
            raise ValueError(f"Unknown format: {format}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(output_path)

    def _format_txt(self, result: ExtractionResult) -> str:
        """Format as plain text."""
        lines = [
            "FORENSIC AUDIO MESSAGE EXTRACTION",
            "=" * 50,
            "",
            f"Total messages: {len(result.messages)}",
            f"Total words: {result.total_words_extracted}",
            f"Languages: {', '.join(result.languages_detected)}",
            f"Speakers: {result.n_speakers}",
            "",
            "-" * 50,
            "MESSAGES",
            "-" * 50,
            "",
        ]

        for msg in result.messages:
            lines.append(f"[{msg.start_time:.2f}s - {msg.end_time:.2f}s]")
            lines.append(f"Speaker: {msg.speaker_id}, Language: {msg.language}")
            lines.append(f"Confidence: {msg.confidence:.1%} ({msg.confidence_level.value})")
            lines.append(f"Text: {msg.text}")

            if msg.alternatives:
                lines.append("Alternatives:")
                for alt in msg.alternatives[:3]:
                    lines.append(f"  [{alt['language']}] {alt['text'][:50]}...")

            lines.append("")

        if result.summary:
            lines.extend([
                "-" * 50,
                "SUMMARY",
                "-" * 50,
                result.summary,
                "",
            ])

        if result.key_phrases:
            lines.extend([
                "KEY PHRASES:",
                ", ".join(result.key_phrases),
            ])

        return "\n".join(lines)

    def _format_json(self, result: ExtractionResult) -> str:
        """Format as JSON."""
        data = {
            'total_messages': len(result.messages),
            'total_words': result.total_words_extracted,
            'languages': result.languages_detected,
            'n_speakers': result.n_speakers,
            'full_transcript': result.full_transcript,
            'summary': result.summary,
            'key_phrases': result.key_phrases,
            'messages': [
                {
                    'text': m.text,
                    'language': m.language,
                    'start_time': m.start_time,
                    'end_time': m.end_time,
                    'confidence': m.confidence,
                    'confidence_level': m.confidence_level.value,
                    'speaker_id': m.speaker_id,
                    'voice_type': m.voice_type,
                    'word_count': m.word_count,
                    'alternatives': m.alternatives,
                }
                for m in result.messages
            ],
            'transcript_by_speaker': result.full_transcript_by_speaker,
        }

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_srt(self, result: ExtractionResult) -> str:
        """Format as SRT subtitles."""
        lines = []

        for i, msg in enumerate(result.messages, 1):
            start = self._format_srt_time(msg.start_time)
            end = self._format_srt_time(msg.end_time)

            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(f"[{msg.language}] {msg.text}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Format time for SRT."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
