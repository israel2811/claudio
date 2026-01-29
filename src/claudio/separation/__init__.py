"""
Source Separation modules.

- bss: Blind Source Separation main interface
- ica: Independent Component Analysis
- spectral: Spectral-based separation methods
"""

from claudio.separation.bss import BlindSourceSeparator
from claudio.separation.ica import ICAProcessor
from claudio.separation.spectral import SpectralSeparator

__all__ = [
    "BlindSourceSeparator",
    "ICAProcessor",
    "SpectralSeparator",
]
