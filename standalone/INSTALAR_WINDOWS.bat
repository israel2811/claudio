@echo off
echo ========================================
echo  CLAUDIO - Instalador para Windows
echo  Recuperacion Forense de Audio
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado.
    echo Por favor descarga Python desde: https://www.python.org/downloads/
    echo Asegurate de marcar "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo [1/3] Python encontrado!
echo.

:: Install dependencies
echo [2/3] Instalando dependencias...
pip install numpy soundfile gradio --quiet

if errorlevel 1 (
    echo ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo.
echo [3/3] Instalacion completada!
echo.
echo ========================================
echo  Para usar Claudio:
echo.
echo  1. Interfaz grafica:
echo     python claudio_portable.py --gui
echo.
echo  2. Linea de comandos:
echo     python claudio_portable.py audio.wav salida.wav
echo ========================================
echo.

:: Ask to launch
set /p launch="Deseas abrir la interfaz grafica ahora? (s/n): "
if /i "%launch%"=="s" (
    python claudio_portable.py --gui
)

pause
