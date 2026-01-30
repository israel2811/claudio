"""
Claudio - Advanced Forensic Audio Analysis and Blind Source Separation

A comprehensive forensic audio processing library featuring:
- Forensic recovery of attenuated voices (<-35dB)
- Phase coherence amplification for signal enhancement
- Blind Source Separation (BSS) using ICA and spectral methods
- FFT/DFT-based signal processing with phase manipulation
- Multi-speaker voice detection and diarization (30+ speakers)
- Multilingual transcription (10+ languages)
- LLM integration for content analysis
- Message extraction from recovered audio
"""

__version__ = "1.0.0"
__author__ = "Claudio Team"

# Core modules
from claudio.core.audio_io import AudioLoader, AudioWriter
from claudio.core.fft_processor import FFTProcessor
from claudio.core.phase_processor import PhaseProcessor

# Separation modules
from claudio.separation.bss import BlindSourceSeparator
from claudio.separation.ica import ICAProcessor
from claudio.separation.spectral import SpectralSeparator

# Analysis modules
from claudio.analysis.voice_detector import VoiceDetector
from claudio.analysis.speaker_diarization import SpeakerDiarizer
from claudio.analysis.feature_extraction import FeatureExtractor

# Transcription modules
from claudio.transcription.transcriber import MultilingualTranscriber
from claudio.transcription.language_detector import LanguageDetector
from claudio.transcription.llm_analyzer import LLMAnalyzer

# Forensic modules
from claudio.forensic.sub_threshold_recovery import SubThresholdRecovery
from claudio.forensic.phase_coherence_amplifier import PhaseCoherenceAmplifier
from claudio.forensic.attenuated_voice_detector import AttenuatedVoiceDetector
from claudio.forensic.forensic_analyzer import ForensicAudioAnalyzer
from claudio.forensic.message_extractor import MessageExtractor

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
    # Forensic
    "SubThresholdRecovery",
    "PhaseCoherenceAmplifier",
    "AttenuatedVoiceDetector",
    "ForensicAudioAnalyzer",
    "MessageExtractor",
]
