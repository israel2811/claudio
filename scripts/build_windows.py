#!/usr/bin/env python3
"""
Build script for creating Windows executable.

Creates a standalone .exe using PyInstaller.
"""

import os
import sys
import subprocess
from pathlib import Path


def build_executable():
    """Build Windows executable using PyInstaller."""
    # Get project root
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    # PyInstaller spec
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../src/claudio/gui/app.py'],
    pathex=['../src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'claudio',
        'claudio.core',
        'claudio.core.audio_io',
        'claudio.core.fft_processor',
        'claudio.core.phase_processor',
        'claudio.separation',
        'claudio.separation.bss',
        'claudio.separation.ica',
        'claudio.separation.spectral',
        'claudio.analysis',
        'claudio.analysis.voice_detector',
        'claudio.analysis.speaker_diarization',
        'claudio.analysis.feature_extraction',
        'claudio.transcription',
        'claudio.transcription.transcriber',
        'claudio.transcription.language_detector',
        'claudio.transcription.llm_analyzer',
        'claudio.forensic',
        'claudio.forensic.sub_threshold_recovery',
        'claudio.forensic.phase_coherence_amplifier',
        'claudio.forensic.attenuated_voice_detector',
        'claudio.forensic.forensic_analyzer',
        'claudio.forensic.message_extractor',
        'numpy',
        'scipy',
        'scipy.signal',
        'scipy.fft',
        'scipy.linalg',
        'sklearn',
        'sklearn.cluster',
        'librosa',
        'soundfile',
        'pydub',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Claudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''

    # Write spec file
    spec_path = project_root / "scripts" / "claudio.spec"
    with open(spec_path, 'w') as f:
        f.write(spec_content)

    print("=" * 50)
    print("Building Claudio Windows Executable")
    print("=" * 50)

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Build
    print("\nBuilding executable...")
    os.chdir(project_root / "scripts")

    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "claudio.spec"
    ])

    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("Build successful!")
        print(f"Executable: {project_root / 'scripts' / 'dist' / 'Claudio.exe'}")
        print("=" * 50)
    else:
        print("\nBuild failed!")
        sys.exit(1)


def create_installer():
    """Create NSIS installer (optional)."""
    nsis_script = '''
!include "MUI2.nsh"

Name "Claudio - Forensic Audio Analyzer"
OutFile "ClaudioSetup.exe"
InstallDir "$PROGRAMFILES\\Claudio"
RequestExecutionLevel admin

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Spanish"

Section "Install"
    SetOutPath "$INSTDIR"
    File /r "dist\\Claudio\\*.*"

    CreateShortCut "$DESKTOP\\Claudio.lnk" "$INSTDIR\\Claudio.exe"
    CreateDirectory "$SMPROGRAMS\\Claudio"
    CreateShortCut "$SMPROGRAMS\\Claudio\\Claudio.lnk" "$INSTDIR\\Claudio.exe"
    CreateShortCut "$SMPROGRAMS\\Claudio\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"

    WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    Delete "$DESKTOP\\Claudio.lnk"
    RMDir /r "$SMPROGRAMS\\Claudio"
SectionEnd
'''

    project_root = Path(__file__).parent.parent
    nsis_path = project_root / "scripts" / "installer.nsi"
    with open(nsis_path, 'w') as f:
        f.write(nsis_script)

    print(f"NSIS script created: {nsis_path}")
    print("To build installer, run: makensis installer.nsi")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Claudio for Windows")
    parser.add_argument("--installer", action="store_true", help="Also create installer script")
    args = parser.parse_args()

    build_executable()

    if args.installer:
        create_installer()
