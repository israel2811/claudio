"""
Forensic Audio Recovery Module.

Specialized module for recovering attenuated voices below -35dB threshold
using coherent phase summation and frequency inversion techniques.
"""

from claudio.forensic.sub_threshold_recovery import SubThresholdRecovery
from claudio.forensic.phase_coherence_amplifier import PhaseCoherenceAmplifier
from claudio.forensic.attenuated_voice_detector import AttenuatedVoiceDetector
from claudio.forensic.forensic_analyzer import ForensicAudioAnalyzer
from claudio.forensic.message_extractor import MessageExtractor

__all__ = [
    "SubThresholdRecovery",
    "PhaseCoherenceAmplifier",
    "AttenuatedVoiceDetector",
    "ForensicAudioAnalyzer",
    "MessageExtractor",
]
