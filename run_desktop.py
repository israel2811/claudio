#!/usr/bin/env python3
"""
Launch Claudio Desktop Application.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from claudio.gui.app import main

if __name__ == "__main__":
    main()
