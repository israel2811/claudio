"""
Language Detection Module.

Detects the language of speech segments using:
- Audio-based language identification
- Text-based language detection (post-transcription)
- Hybrid approaches
"""

import numpy as np
from typing import Optional, List, Dict, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SupportedLanguage(Enum):
    """Supported languages for transcription and analysis."""

    # Primary languages (10+)
    SPANISH = "es"
    ENGLISH = "en"
    FRENCH = "fr"
    GERMAN = "de"
    RUSSIAN = "ru"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    HINDI = "hi"
    DUTCH = "nl"
    POLISH = "pl"
    TURKISH = "tr"
    VIETNAMESE = "vi"
    THAI = "th"
    INDONESIAN = "id"
    SWEDISH = "sv"
    NORWEGIAN = "no"

    @classmethod
    def from_code(cls, code: str) -> Optional["SupportedLanguage"]:
        """Get language from ISO code."""
        code = code.lower()[:2]
        for lang in cls:
            if lang.value == code:
                return lang
        return None

    @property
    def name_english(self) -> str:
        """Get English name of language."""
        names = {
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
        }
        return names.get(self.value, self.value)


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""

    language: SupportedLanguage
    language_code: str
    confidence: float
    all_probabilities: Dict[str, float]
    method: str  # "audio", "text", or "hybrid"

    @property
    def language_name(self) -> str:
        return self.language.name_english if self.language else "Unknown"


@dataclass
class SegmentLanguageResult:
    """Language detection for a segment."""

    start_time: float
    end_time: float
    language: SupportedLanguage
    confidence: float


class LanguageDetector:
    """
    Language detector for speech audio.

    Supports detection from:
    - Raw audio (using acoustic features)
    - Transcribed text
    - Hybrid audio + text
    """

    # Language-specific acoustic characteristics (simplified)
    LANGUAGE_FEATURES = {
        "es": {"syllable_rate": (5, 8), "pitch_range": (100, 300)},
        "en": {"syllable_rate": (4, 6), "pitch_range": (85, 280)},
        "fr": {"syllable_rate": (5, 8), "pitch_range": (100, 320)},
        "de": {"syllable_rate": (4, 6), "pitch_range": (80, 260)},
        "ru": {"syllable_rate": (4, 7), "pitch_range": (85, 270)},
        "pt": {"syllable_rate": (5, 8), "pitch_range": (100, 300)},
        "it": {"syllable_rate": (5, 8), "pitch_range": (100, 320)},
        "zh": {"syllable_rate": (4, 6), "pitch_range": (100, 400)},  # Tonal
        "ja": {"syllable_rate": (5, 8), "pitch_range": (100, 350)},
        "ko": {"syllable_rate": (4, 7), "pitch_range": (100, 330)},
    }

    def __init__(
        self,
        use_audio_model: bool = True,
        use_text_model: bool = True,
        default_language: str = "en",
    ):
        """
        Initialize LanguageDetector.

        Args:
            use_audio_model: Use audio-based detection.
            use_text_model: Use text-based detection.
            default_language: Default language when detection fails.
        """
        self.use_audio_model = use_audio_model
        self.use_text_model = use_text_model
        self.default_language = default_language

        self._audio_model = None
        self._text_detector = None

    def detect_from_audio(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> LanguageDetectionResult:
        """
        Detect language from audio signal.

        Args:
            signal: Audio signal.
            sample_rate: Sample rate.

        Returns:
            LanguageDetectionResult.
        """
        # Try neural model first
        if self.use_audio_model:
            try:
                return self._detect_audio_neural(signal, sample_rate)
            except Exception:
                pass

        # Fall back to acoustic features
        return self._detect_audio_acoustic(signal, sample_rate)

    def _detect_audio_neural(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> LanguageDetectionResult:
        """Use neural network for audio language detection."""
        try:
            from speechbrain.inference.classifiers import EncoderClassifier

            if self._audio_model is None:
                self._audio_model = EncoderClassifier.from_hparams(
                    source="speechbrain/lang-id-voxlingua107-ecapa",
                    savedir="pretrained_models/lang-id-voxlingua107-ecapa",
                )

            import torch
            audio_tensor = torch.tensor(signal).float().unsqueeze(0)

            # Resample to 16kHz if needed
            if sample_rate != 16000:
                import torchaudio
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                audio_tensor = resampler(audio_tensor)

            prediction = self._audio_model.classify_batch(audio_tensor)

            # Get probabilities
            probs = prediction[0].squeeze().numpy()
            labels = self._audio_model.hparams.label_encoder.decode_ndim(
                prediction[1].squeeze().numpy()
            )

            # Map to our supported languages
            all_probs = {}
            for label, prob in zip(labels, probs):
                lang_code = label[:2].lower()
                if lang_code not in all_probs:
                    all_probs[lang_code] = 0
                all_probs[lang_code] += prob

            # Get best match
            best_lang = max(all_probs, key=all_probs.get)
            best_prob = all_probs[best_lang]

            language = SupportedLanguage.from_code(best_lang)
            if language is None:
                language = SupportedLanguage.from_code(self.default_language)

            return LanguageDetectionResult(
                language=language,
                language_code=best_lang,
                confidence=float(best_prob),
                all_probabilities=all_probs,
                method="audio_neural",
            )

        except ImportError:
            raise RuntimeError("SpeechBrain not available for audio language detection")

    def _detect_audio_acoustic(
        self,
        signal: np.ndarray,
        sample_rate: int,
    ) -> LanguageDetectionResult:
        """Use acoustic features for language detection (fallback)."""
        from claudio.analysis.feature_extraction import FeatureExtractor

        extractor = FeatureExtractor(sample_rate=sample_rate)

        # Extract features
        pitch, confidence = extractor.extract_pitch(signal, sample_rate)
        energy = extractor.extract_energy(signal, sample_rate)

        # Filter valid pitch values
        valid_pitch = pitch[confidence > 0.5]
        if len(valid_pitch) == 0:
            valid_pitch = pitch[pitch > 0]

        if len(valid_pitch) == 0:
            # Can't detect, return default
            return LanguageDetectionResult(
                language=SupportedLanguage.from_code(self.default_language),
                language_code=self.default_language,
                confidence=0.1,
                all_probabilities={self.default_language: 0.1},
                method="acoustic_fallback",
            )

        # Compute statistics
        mean_pitch = np.mean(valid_pitch)
        pitch_range = np.percentile(valid_pitch, 90) - np.percentile(valid_pitch, 10)

        # Estimate syllable rate from energy peaks
        energy_smooth = np.convolve(energy, np.ones(5) / 5, mode='same')
        peaks = np.where(
            (energy_smooth[1:-1] > energy_smooth[:-2]) &
            (energy_smooth[1:-1] > energy_smooth[2:])
        )[0]
        duration = len(signal) / sample_rate
        syllable_rate = len(peaks) / duration if duration > 0 else 5

        # Score each language
        scores = {}
        for lang, features in self.LANGUAGE_FEATURES.items():
            sr_min, sr_max = features["syllable_rate"]
            pr_min, pr_max = features["pitch_range"]

            # Score based on how well features match
            sr_score = 1 - min(abs(syllable_rate - (sr_min + sr_max) / 2) / 5, 1)
            pr_score = 1 - min(abs(mean_pitch - (pr_min + pr_max) / 2) / 200, 1)

            scores[lang] = 0.5 * sr_score + 0.5 * pr_score

        # Normalize scores
        total = sum(scores.values())
        probs = {k: v / total for k, v in scores.items()}

        best_lang = max(probs, key=probs.get)
        language = SupportedLanguage.from_code(best_lang)

        return LanguageDetectionResult(
            language=language,
            language_code=best_lang,
            confidence=probs[best_lang],
            all_probabilities=probs,
            method="acoustic",
        )

    def detect_from_text(
        self,
        text: str,
    ) -> LanguageDetectionResult:
        """
        Detect language from transcribed text.

        Args:
            text: Transcribed text.

        Returns:
            LanguageDetectionResult.
        """
        if not text or len(text.strip()) < 3:
            return LanguageDetectionResult(
                language=SupportedLanguage.from_code(self.default_language),
                language_code=self.default_language,
                confidence=0.1,
                all_probabilities={self.default_language: 0.1},
                method="text_fallback",
            )

        try:
            from langdetect import detect_langs

            results = detect_langs(text)

            all_probs = {}
            for result in results:
                lang_code = result.lang[:2].lower()
                all_probs[lang_code] = result.prob

            best_lang = max(all_probs, key=all_probs.get)
            language = SupportedLanguage.from_code(best_lang)

            if language is None:
                language = SupportedLanguage.from_code(self.default_language)
                best_lang = self.default_language

            return LanguageDetectionResult(
                language=language,
                language_code=best_lang,
                confidence=all_probs[best_lang],
                all_probabilities=all_probs,
                method="text",
            )

        except Exception:
            # Fallback to simple heuristics
            return self._detect_text_heuristic(text)

    def _detect_text_heuristic(self, text: str) -> LanguageDetectionResult:
        """Simple heuristic-based text language detection."""
        text_lower = text.lower()

        # Character set detection
        scores = {}

        # Spanish indicators
        spanish_chars = sum(1 for c in text_lower if c in 'áéíóúñ¿¡')
        scores["es"] = spanish_chars / (len(text) + 1)

        # French indicators
        french_chars = sum(1 for c in text_lower if c in 'àâçéèêëîïôùûü')
        scores["fr"] = french_chars / (len(text) + 1)

        # German indicators
        german_chars = sum(1 for c in text_lower if c in 'äöüß')
        scores["de"] = german_chars / (len(text) + 1)

        # Russian (Cyrillic)
        cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        scores["ru"] = cyrillic / (len(text) + 1)

        # Chinese
        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        scores["zh"] = chinese / (len(text) + 1)

        # Japanese (Hiragana/Katakana)
        japanese = sum(1 for c in text if '\u3040' <= c <= '\u30ff')
        scores["ja"] = japanese / (len(text) + 1)

        # Korean (Hangul)
        korean = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        scores["ko"] = korean / (len(text) + 1)

        # Arabic
        arabic = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        scores["ar"] = arabic / (len(text) + 1)

        # Portuguese (similar to Spanish but with some differences)
        portuguese_chars = sum(1 for c in text_lower if c in 'ãõç')
        scores["pt"] = portuguese_chars / (len(text) + 1)

        # Default to English if no strong indicators
        scores["en"] = 0.1 if max(scores.values()) < 0.1 else 0

        # Normalize
        total = sum(scores.values()) + 0.001
        probs = {k: v / total for k, v in scores.items()}

        best_lang = max(probs, key=probs.get)
        language = SupportedLanguage.from_code(best_lang)

        return LanguageDetectionResult(
            language=language if language else SupportedLanguage.ENGLISH,
            language_code=best_lang,
            confidence=probs[best_lang],
            all_probabilities=probs,
            method="text_heuristic",
        )

    def detect_hybrid(
        self,
        signal: np.ndarray,
        sample_rate: int,
        text: Optional[str] = None,
    ) -> LanguageDetectionResult:
        """
        Hybrid language detection using both audio and text.

        Args:
            signal: Audio signal.
            sample_rate: Sample rate.
            text: Optional transcribed text.

        Returns:
            LanguageDetectionResult.
        """
        # Get audio-based result
        audio_result = self.detect_from_audio(signal, sample_rate)

        if text and len(text.strip()) > 10:
            # Get text-based result
            text_result = self.detect_from_text(text)

            # Combine probabilities
            combined_probs = {}
            all_langs = set(audio_result.all_probabilities.keys()) | set(text_result.all_probabilities.keys())

            for lang in all_langs:
                audio_prob = audio_result.all_probabilities.get(lang, 0)
                text_prob = text_result.all_probabilities.get(lang, 0)
                # Weight text more heavily as it's usually more accurate
                combined_probs[lang] = 0.3 * audio_prob + 0.7 * text_prob

            # Normalize
            total = sum(combined_probs.values())
            if total > 0:
                combined_probs = {k: v / total for k, v in combined_probs.items()}

            best_lang = max(combined_probs, key=combined_probs.get)
            language = SupportedLanguage.from_code(best_lang)

            return LanguageDetectionResult(
                language=language if language else SupportedLanguage.ENGLISH,
                language_code=best_lang,
                confidence=combined_probs[best_lang],
                all_probabilities=combined_probs,
                method="hybrid",
            )

        return audio_result

    def detect_segments(
        self,
        signal: np.ndarray,
        sample_rate: int,
        segment_duration: float = 5.0,
    ) -> List[SegmentLanguageResult]:
        """
        Detect language for each segment of audio.

        Useful for multilingual audio.

        Args:
            signal: Audio signal.
            sample_rate: Sample rate.
            segment_duration: Duration of each segment in seconds.

        Returns:
            List of SegmentLanguageResult.
        """
        segment_samples = int(segment_duration * sample_rate)
        n_segments = int(np.ceil(len(signal) / segment_samples))

        results = []
        for i in range(n_segments):
            start = i * segment_samples
            end = min((i + 1) * segment_samples, len(signal))
            segment = signal[start:end]

            if len(segment) < sample_rate * 0.5:  # Too short
                continue

            detection = self.detect_from_audio(segment, sample_rate)

            results.append(SegmentLanguageResult(
                start_time=start / sample_rate,
                end_time=end / sample_rate,
                language=detection.language,
                confidence=detection.confidence,
            ))

        return results
