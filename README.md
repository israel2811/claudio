# Claudio - Forensic Audio Recovery & Analysis

**Claudio** is an advanced forensic audio processing application specialized in recovering attenuated voices below -35dB using phase coherence amplification and blind source separation techniques.

## Key Features

### Forensic Audio Recovery
- **Sub-threshold voice recovery**: Recover voices attenuated below -35dB
- **Phase coherence amplification**: Use wave physics for constructive interference
- **Iterative enhancement**: Multiple passes for maximum recovery
- **Frequency-selective processing**: Focus on voice frequency bands (80-8000Hz)

### Signal Processing
- **FFT/DFT Analysis**: Full spectral analysis with STFT
- **Phase Inversion & Summation**: Coherent phase manipulation for amplitude gain
- **Adaptive Noise Reduction**: Intelligent noise floor estimation
- **Multi-band Processing**: Separate enhancement per frequency band

### Voice Analysis
- **30+ Speaker Support**: Detect and separate up to 30 different voices
- **Speaker Diarization**: Identify who spoke when
- **Voice Activity Detection**: Find speech segments in any audio
- **Feature Extraction**: MFCCs, pitch, formants, spectral features

### Multilingual Transcription
- **10+ Languages**: Spanish, English, French, German, Russian, Portuguese, Italian, Chinese, Japanese, Korean, Arabic, Hindi, and more
- **Automatic Language Detection**: Detect language from audio
- **Word-level Timestamps**: Precise timing for each word
- **Multiple Interpretations**: Alternative transcriptions for uncertain content

### LLM Content Analysis
- **Message Extraction**: Extract words, phrases, paragraphs
- **Content Summarization**: Automatic summaries
- **Key Phrase Detection**: Important phrases highlighted
- **Multi-language Support**: Analyze content in any detected language

## Installation

```bash
# Clone repository
git clone https://github.com/your-org/claudio.git
cd claudio

# Install dependencies
pip install -e .

# Or install all dependencies
pip install -r requirements.txt
```

## Quick Start

### Desktop Application (Windows)

```bash
# Run desktop GUI
python run_desktop.py
```

### Web Application

```bash
# Run web interface
python run_web.py

# Opens at http://localhost:8501
```

### Command Line

```bash
# Forensic recovery (main feature)
claudio forensic audio.wav -o output/ --threshold -35 --max-voices 30

# Quick scan for attenuated content
claudio forensic audio.wav --no-transcribe

# Full analysis pipeline
claudio full-pipeline audio.wav -o analysis/ --max-speakers 30

# Transcribe audio
claudio transcribe audio.wav -l es,en,fr --model medium

# Source separation
claudio separate mixed.wav -n 5 -m hybrid
```

## How It Works

### Phase Coherence Amplification

The core technology uses the physics of wave interference:

1. **Phase Inversion**: Create a 180° phase-shifted copy of the signal
2. **Re-inversion**: Invert the inverted signal (back to original phase)
3. **Coherent Summation**: Sum signals that are now in-phase
4. **Constructive Interference**: Achieve amplitude gain (theoretical 2x per iteration)

```
Original Signal:    ~~~~
Phase Inverted:     ~~~~  (180° shift)
Re-inverted:        ~~~~  (back to 0°)
Sum:                ████  (doubled amplitude)
```

### Sub-Threshold Recovery Process

1. **Noise Floor Estimation**: Identify the noise level
2. **Voice Band Isolation**: Focus on 80-8000 Hz
3. **Phase Coherence Amplification**: Apply iterative enhancement
4. **Adaptive Gain**: Bring signals to audible levels
5. **Voice Detection**: Find speech segments
6. **Transcription**: Convert to text in multiple languages

## API Usage

### Forensic Recovery

```python
from claudio import ForensicAudioAnalyzer

# Initialize analyzer
analyzer = ForensicAudioAnalyzer(
    target_threshold_db=-35.0,  # Detection threshold
    max_voices=30,              # Maximum voices to detect
    aggressive_recovery=True,   # Use aggressive mode
)

# Analyze audio file
result = analyzer.analyze(
    "audio.wav",
    output_dir="output/",
    transcribe=True,
    languages=['es', 'en', 'fr', 'de', 'ru', 'pt'],
)

# Access results
print(f"Signal improvement: +{result.signal_improvement_db:.1f}dB")
print(f"Detected {len(result.detected_voice_segments)} voice segments")
print(f"Found {result.n_voices_detected} distinct voices")

# Get transcriptions
for seg_id, trans in result.transcriptions.items():
    print(f"Segment {seg_id} [{trans['language']}]: {trans['text']}")
```

### Phase Coherence Amplifier

```python
from claudio import PhaseCoherenceAmplifier

amplifier = PhaseCoherenceAmplifier()

# Amplify using iterative inversion and summation
amplified = amplifier.invert_and_sum(
    signal,
    sample_rate=16000,
    n_iterations=5,  # Each iteration adds ~3-6dB
)

# Or use adaptive amplification
result = amplifier.amplify(
    signal,
    sample_rate=16000,
    target_gain_db=30.0,
    frequency_range=(80, 4000),  # Focus on voice frequencies
)
```

### Sub-Threshold Recovery

```python
from claudio import SubThresholdRecovery, RecoveryConfig

config = RecoveryConfig(
    target_threshold_db=-35.0,
    n_iterations=15,
    phase_iterations=30,
    max_gain_db=60.0,
)

recovery = SubThresholdRecovery(config)
result = recovery.recover_with_multiple_passes(
    "audio.wav",
    n_passes=3,
)

print(f"Recovered signal with +{result.signal_improvement_db:.1f}dB improvement")
```

### Message Extraction

```python
from claudio import MessageExtractor

extractor = MessageExtractor(
    languages=['es', 'en', 'fr', 'de', 'ru', 'pt'],
    try_all_languages=True,
)

# Extract from forensic result
extraction = extractor.extract_from_forensic_result(forensic_result)

print(f"Extracted {extraction.total_words_extracted} words")
print(f"Languages: {extraction.languages_detected}")
print(f"Full transcript: {extraction.full_transcript}")

# Save results
extractor.save_extraction(extraction, "messages.txt", format="txt")
extractor.save_extraction(extraction, "messages.json", format="json")
```

## Supported Languages

| Language | Code | Language | Code |
|----------|------|----------|------|
| Spanish | es | Italian | it |
| English | en | Chinese | zh |
| French | fr | Japanese | ja |
| German | de | Korean | ko |
| Russian | ru | Arabic | ar |
| Portuguese | pt | Hindi | hi |

Plus 20+ additional languages supported by Whisper.

## Building Windows Executable

```bash
# Build standalone .exe
cd scripts
python build_windows.py

# Output: scripts/dist/Claudio.exe
```

## Project Structure

```
claudio/
├── src/claudio/
│   ├── core/                 # Audio I/O, FFT, Phase processing
│   ├── separation/           # BSS, ICA, Spectral separation
│   ├── analysis/             # VAD, Diarization, Features
│   ├── transcription/        # ASR, Language detection, LLM
│   ├── forensic/             # Sub-threshold recovery
│   │   ├── sub_threshold_recovery.py
│   │   ├── phase_coherence_amplifier.py
│   │   ├── attenuated_voice_detector.py
│   │   ├── forensic_analyzer.py
│   │   └── message_extractor.py
│   ├── gui/                  # Desktop application
│   ├── web/                  # Streamlit web app
│   └── cli/                  # Command line interface
├── run_desktop.py            # Launch desktop app
├── run_web.py                # Launch web app
└── scripts/                  # Build scripts
```

## Technical Details

### Recovery Algorithm

1. **Initial Analysis**
   - Load audio, estimate noise floor
   - Detect sub-threshold content

2. **Phase Coherence Amplification**
   - STFT decomposition
   - Per-bin phase manipulation
   - Coherent summation
   - ISTFT reconstruction

3. **Iterative Enhancement**
   - Griffin-Lim style phase reconstruction
   - Magnitude constraints
   - Sparsity promotion

4. **Voice-Specific Processing**
   - Formant frequency boosting (F1, F2, F3)
   - Harmonic enhancement
   - Spectral tilt correction

5. **Multi-Pass Recovery**
   - Progressive threshold lowering
   - Cumulative enhancement
   - Quality-based stopping

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- OpenAI Whisper for speech recognition
- SpeechBrain for neural embeddings
- librosa for audio analysis
- NumPy/SciPy for signal processing
