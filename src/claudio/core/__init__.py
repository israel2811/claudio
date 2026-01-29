"""
Core audio processing modules.

- audio_io: Audio file loading and writing
- fft_processor: FFT/DFT-based spectral analysis
- phase_processor: Phase manipulation and coherent summation
"""

from claudio.core.audio_io import AudioLoader, AudioWriter
from claudio.core.fft_processor import FFTProcessor
from claudio.core.phase_processor import PhaseProcessor

__all__ = [
    "AudioLoader",
    "AudioWriter",
    "FFTProcessor",
    "PhaseProcessor",
]
