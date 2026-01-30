#!/usr/bin/env python3
"""
Launch Claudio Web Application.

Runs Streamlit server on localhost:8501
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Launch Streamlit web application."""
    app_path = Path(__file__).parent / "src" / "claudio" / "web" / "streamlit_app.py"

    print("=" * 50)
    print("Starting Claudio Web Application")
    print("=" * 50)
    print(f"\nOpen your browser at: http://localhost:8501")
    print("Press Ctrl+C to stop the server\n")

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ])


if __name__ == "__main__":
    main()
