"""
Claudio - Advanced Audio Analysis and Blind Source Separation

A comprehensive audio processing library featuring:
- Blind Source Separation (BSS) using ICA and spectral methods
- FFT/DFT-based signal processing
- Phase coherence amplitude enhancement
- Multi-speaker voice detection and diarization (30+ speakers)
- Multilingual transcription (10+ languages)
- LLM integration for content analysis
"""

__version__ = "1.0.0"
__author__ = "Claudio Team"

from claudio.core.audio_io import AudioLoader, AudioWriter
from claudio.core.fft_processor import FFTProcessor
from claudio.core.phase_processor import PhaseProcessor
from claudio.separation.bss import BlindSourceSeparator
from claudio.separation.ica import ICAProcessor
from claudio.separation.spectral import SpectralSeparator
from claudio.analysis.voice_detector import VoiceDetector
from claudio.analysis.speaker_diarization import SpeakerDiarizer
from claudio.analysis.feature_extraction import FeatureExtractor
from claudio.transcription.transcriber import MultilingualTranscriber
from claudio.transcription.language_detector import LanguageDetector
from claudio.transcription.llm_analyzer import LLMAnalyzer

__all__ = [
    # Core
    "AudioLoader",
    "AudioWriter",
    "FFTProcessor",
    "PhaseProcessor",
    # Separation
    "BlindSourceSeparator",
    "ICAProcessor",
    "SpectralSeparator",
    # Analysis
    "VoiceDetector",
    "SpeakerDiarizer",
    "FeatureExtractor",
    # Transcription
    "MultilingualTranscriber",
    "LanguageDetector",
    "LLMAnalyzer",
]
