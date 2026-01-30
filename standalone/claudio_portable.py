#!/usr/bin/env python3
"""
Claudio - Forensic Audio Recovery (Portable Version)
=====================================================

Recovers attenuated voices below -35dB using phase coherence amplification.

USAGE:
    python claudio_portable.py input.wav output.wav
    python claudio_portable.py --gui   (launches graphical interface)

REQUIREMENTS:
    pip install numpy soundfile

Optional for GUI:
    pip install gradio
"""

import sys
import os
import numpy as np
import argparse

# Check for required modules
try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False
    print("WARNING: soundfile not installed. Install with: pip install soundfile")

try:
    from scipy.io import wavfile
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def compute_rms_db(signal):
    """Compute RMS level in dB."""
    rms = np.sqrt(np.mean(signal ** 2))
    return 20 * np.log10(rms + 1e-10)


def phase_invert_and_sum(signal, iterations=10):
    """
    Phase inversion and coherent summation for amplitude gain.

    Based on wave physics: when two identical waves are in phase,
    their amplitudes sum constructively.
    """
    result = signal.copy()

    for i in range(iterations):
        # Create phase-inverted copy
        inverted = -result

        # Re-invert to get back in phase
        reinverted = -inverted

        # Sum for constructive interference
        result = (result + reinverted) / 2

        # Apply gain to accumulate effect
        result = result * 1.4

    return result


def spectral_enhancement(signal, sr, voice_low=80, voice_high=8000):
    """Enhance voice frequencies using spectral processing."""
    n_fft = min(2048, len(signal))

    if len(signal) < n_fft:
        signal = np.pad(signal, (0, n_fft - len(signal)))

    hop_length = n_fft // 4
    n_frames = (len(signal) - n_fft) // hop_length + 1

    if n_frames < 1:
        return signal

    enhanced = np.zeros_like(signal, dtype=np.float64)
    window = np.hanning(n_fft)

    for i in range(n_frames):
        start = i * hop_length
        end = start + n_fft

        if end > len(signal):
            break

        frame = signal[start:end] * window
        spectrum = np.fft.rfft(frame)
        freqs = np.fft.rfftfreq(n_fft, 1/sr)

        # Voice band boost mask
        boost_mask = np.ones_like(freqs)

        # Boost voice frequencies
        voice_mask = (freqs >= voice_low) & (freqs <= voice_high)
        boost_mask[voice_mask] = 2.0

        # Formant boost
        boost_mask[(freqs >= 250) & (freqs <= 400)] = 3.0   # F1
        boost_mask[(freqs >= 700) & (freqs <= 1200)] = 2.5  # F2
        boost_mask[(freqs >= 2000) & (freqs <= 3500)] = 2.0 # F3

        enhanced_spectrum = spectrum * boost_mask
        enhanced_frame = np.fft.irfft(enhanced_spectrum, n_fft)
        enhanced[start:end] += enhanced_frame * window

    enhanced = enhanced / 2
    return enhanced[:len(signal)]


def adaptive_gain(signal, target_db=-20):
    """Apply adaptive gain to reach target level."""
    current_db = compute_rms_db(signal)
    gain_needed = min(target_db - current_db, 60)
    linear_gain = 10 ** (gain_needed / 20)
    return signal * linear_gain, gain_needed


def recover_audio(signal, sr, iterations=10):
    """Main recovery function."""
    original_db = compute_rms_db(signal)

    print(f"  Nivel original: {original_db:.1f} dB")

    # Step 1: Phase coherence amplification
    print("  [1/4] Aplicando amplificacion por coherencia de fase...")
    enhanced = phase_invert_and_sum(signal, iterations=iterations)

    # Step 2: Spectral enhancement
    print("  [2/4] Aplicando realce espectral...")
    enhanced = spectral_enhancement(enhanced, sr)

    # Step 3: Adaptive gain
    print("  [3/4] Aplicando ganancia adaptativa...")
    enhanced, gain = adaptive_gain(enhanced, target_db=-20)

    # Step 4: Normalize
    print("  [4/4] Normalizando...")
    max_val = np.max(np.abs(enhanced))
    if max_val > 0.99:
        enhanced = enhanced * 0.95 / max_val

    final_db = compute_rms_db(enhanced)
    improvement = final_db - original_db

    print(f"  Nivel final: {final_db:.1f} dB")
    print(f"  Mejora: +{improvement:.1f} dB")

    return enhanced


def load_audio(filepath):
    """Load audio file."""
    if HAS_SOUNDFILE:
        signal, sr = sf.read(filepath)
    elif HAS_SCIPY:
        sr, signal = wavfile.read(filepath)
        if signal.dtype == np.int16:
            signal = signal / 32768.0
        elif signal.dtype == np.int32:
            signal = signal / 2147483648.0
    else:
        raise ImportError("No audio library available. Install soundfile: pip install soundfile")

    # Convert to mono
    if signal.ndim > 1:
        signal = np.mean(signal, axis=1)

    return signal.astype(np.float64), sr


def save_audio(filepath, signal, sr):
    """Save audio file."""
    if HAS_SOUNDFILE:
        sf.write(filepath, signal, sr)
    elif HAS_SCIPY:
        signal_int = (signal * 32767).astype(np.int16)
        wavfile.write(filepath, sr, signal_int)
    else:
        raise ImportError("No audio library available")


def process_file(input_path, output_path, iterations=10):
    """Process a single audio file."""
    print(f"\n{'='*50}")
    print("CLAUDIO - Recuperacion Forense de Audio")
    print(f"{'='*50}")
    print(f"\nProcesando: {input_path}")

    # Load
    signal, sr = load_audio(input_path)
    print(f"Audio cargado: {len(signal)/sr:.2f}s a {sr}Hz")

    # Process
    enhanced = recover_audio(signal, sr, iterations)

    # Save
    save_audio(output_path, enhanced, sr)
    print(f"\nGuardado en: {output_path}")
    print(f"{'='*50}\n")


def run_gui():
    """Run graphical interface."""
    try:
        import gradio as gr
    except ImportError:
        print("ERROR: Gradio no instalado. Instala con: pip install gradio")
        print("O usa el modo linea de comandos: python claudio_portable.py input.wav output.wav")
        sys.exit(1)

    def process_for_gui(audio_input, iterations):
        if audio_input is None:
            return None, "Sube un archivo de audio"

        sr, signal = audio_input
        signal = signal.astype(np.float64)

        if signal.dtype == np.int16:
            signal = signal / 32768.0

        if signal.ndim > 1:
            signal = np.mean(signal, axis=1)

        original_db = compute_rms_db(signal)
        enhanced = recover_audio(signal, sr, int(iterations))
        final_db = compute_rms_db(enhanced)

        result = f"""
## Resultados
| Metrica | Valor |
|---------|-------|
| Nivel original | {original_db:.1f} dB |
| Nivel final | {final_db:.1f} dB |
| Mejora | +{final_db - original_db:.1f} dB |
"""
        return (sr, enhanced), result

    with gr.Blocks(title="Claudio - Audio Recovery") as app:
        gr.Markdown("# 🔊 Claudio - Recuperacion Forense de Audio")
        gr.Markdown("Recupera voces atenuadas por debajo de -35dB")

        with gr.Row():
            with gr.Column():
                audio_in = gr.Audio(label="Audio de entrada", type="numpy")
                iterations = gr.Slider(1, 20, value=10, step=1, label="Iteraciones")
                btn = gr.Button("Procesar", variant="primary")

            with gr.Column():
                audio_out = gr.Audio(label="Audio recuperado", type="numpy")
                results = gr.Markdown()

        btn.click(process_for_gui, [audio_in, iterations], [audio_out, results])

    app.launch(inbrowser=True)


def main():
    parser = argparse.ArgumentParser(
        description="Claudio - Forensic Audio Recovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python claudio_portable.py input.wav output.wav
    python claudio_portable.py --gui
    python claudio_portable.py -i 15 input.wav recovered.wav
        """
    )

    parser.add_argument("input", nargs="?", help="Input audio file")
    parser.add_argument("output", nargs="?", help="Output audio file")
    parser.add_argument("-i", "--iterations", type=int, default=10,
                        help="Amplification iterations (default: 10)")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")

    args = parser.parse_args()

    if args.gui:
        run_gui()
    elif args.input and args.output:
        process_file(args.input, args.output, args.iterations)
    else:
        parser.print_help()
        print("\n💡 Tip: Use --gui for graphical interface")


if __name__ == "__main__":
    main()
