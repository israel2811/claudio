# Claudio - Advanced Audio Analysis & Blind Source Separation

Claudio is a comprehensive audio processing library for blind source separation, speaker diarization, and multilingual transcription with LLM-based content analysis.

## Features

- **Blind Source Separation (BSS)**: Separate mixed audio into individual sources using:
  - Independent Component Analysis (ICA) - FastICA, Infomax, Natural Gradient
  - Non-negative Matrix Factorization (NMF)
  - Spectral masking techniques (Wiener filtering, binary masks)
  - Deep learning models (SpeechBrain, when available)

- **FFT/DFT Processing**:
  - Short-Time Fourier Transform (STFT) analysis
  - Phase manipulation and coherent summation
  - Amplitude enhancement via phase inversion
  - Spectral feature extraction

- **Speaker Diarization**:
  - Support for 30+ speakers
  - Neural embedding extraction (ECAPA-TDNN)
  - Clustering-based speaker identification
  - RTTM output format

- **Multilingual Transcription**:
  - 10+ languages: Spanish, English, French, German, Russian, Portuguese, Italian, Chinese, Japanese, Korean, Arabic, Hindi, and more
  - Whisper and Faster-Whisper integration
  - Word-level timestamps
  - SRT/VTT subtitle export

- **LLM Content Analysis**:
  - Content summarization
  - Key phrase extraction
  - Topic classification
  - Sentiment analysis
  - Support for local models, OpenAI, and Anthropic

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/claudio.git
cd claudio

# Install with pip
pip install -e .

# Or install with all optional dependencies
pip install -e ".[dev,gpu]"
```

### Requirements

- Python 3.9+
- NumPy, SciPy, scikit-learn
- PyTorch and torchaudio
- librosa, soundfile, pydub
- OpenAI Whisper or faster-whisper
- (Optional) SpeechBrain for neural embeddings
- (Optional) pyannote.audio for advanced diarization

## Quick Start

### Command Line Interface

```bash
# Separate audio sources
claudio separate audio.wav -n 3 -m hybrid -o output/

# Speaker diarization
claudio diarize meeting.wav --max-speakers 10 -o diarized/

# Transcribe audio
claudio transcribe audio.wav -l es --model medium -f srt

# Full analysis pipeline
claudio full-pipeline audio.wav -o analysis/ --max-speakers 5

# Get system info
claudio info
```

### Python API

```python
from claudio import (
    AudioLoader,
    BlindSourceSeparator,
    SpeakerDiarizer,
    MultilingualTranscriber,
    LLMAnalyzer,
)

# Load audio
loader = AudioLoader(mono=True, normalize=True)
audio = loader.load("mixed_audio.wav")

# Separate sources
separator = BlindSourceSeparator()
result = separator.separate(audio, n_sources=3)

for i, source in enumerate(result.sources):
    print(f"Source {i}: confidence={source.confidence:.2%}")

# Speaker diarization
diarizer = SpeakerDiarizer(max_speakers=30)
diarization = diarizer.diarize(audio.signal, audio.sample_rate)

print(f"Detected {diarization.n_speakers} speakers")
for segment in diarization.segments:
    print(f"Speaker {segment.speaker_id}: {segment.start_time:.2f}s - {segment.end_time:.2f}s")

# Transcribe
transcriber = MultilingualTranscriber(model="medium")
transcription = transcriber.transcribe("audio.wav", language="es")

print(f"Language: {transcription.language}")
print(f"Text: {transcription.text}")

# Save as subtitles
transcriber.save_transcription(transcription, "output.srt", format="srt")

# Analyze content with LLM
analyzer = LLMAnalyzer(provider="local")
analysis = analyzer.analyze(transcription)

print(f"Summary: {analysis.summary}")
print(f"Topics: {analysis.topics}")
print(f"Sentiment: {analysis.sentiment}")
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

## Architecture

```
claudio/
├── core/
│   ├── audio_io.py         # Audio loading/saving
│   ├── fft_processor.py    # FFT/STFT processing
│   └── phase_processor.py  # Phase manipulation
├── separation/
│   ├── bss.py              # Main BSS interface
│   ├── ica.py              # ICA algorithms
│   └── spectral.py         # Spectral separation
├── analysis/
│   ├── voice_detector.py   # VAD
│   ├── speaker_diarization.py  # Speaker segmentation
│   └── feature_extraction.py   # Audio features
├── transcription/
│   ├── transcriber.py      # Multilingual ASR
│   ├── language_detector.py # Language detection
│   └── llm_analyzer.py     # LLM analysis
└── cli/
    └── main.py             # CLI interface
```

## Algorithms

### Blind Source Separation

1. **ICA (Independent Component Analysis)**
   - Separates statistically independent sources
   - Best for sources with different statistical distributions

2. **NMF (Non-negative Matrix Factorization)**
   - Decomposes spectrogram into basis and activation matrices
   - Good for separating harmonic sources

3. **Spectral Masking**
   - Wiener filtering for soft separation
   - Binary masking for hard separation
   - Ideal Ratio Mask (IRM) for optimal separation

### Phase Enhancement

- **Coherent Phase Summation**: Aligns phases of multiple signals for constructive interference
- **Phase Inversion**: Cancels noise through destructive interference
- **Griffin-Lim**: Iterative phase reconstruction

## Configuration

```python
from claudio.separation.bss import SeparationConfig, SeparationMethod

config = SeparationConfig(
    method=SeparationMethod.HYBRID,
    n_sources=5,
    n_fft=2048,
    hop_length=512,
    max_iterations=500,
    tolerance=1e-6,
    enhance_output=True,
)

separator = BlindSourceSeparator(config)
```

## API Reference

### BlindSourceSeparator

```python
class BlindSourceSeparator:
    def separate(
        self,
        mixed_signal: Union[np.ndarray, AudioData, str, Path],
        sample_rate: Optional[int] = None,
        n_sources: Optional[int] = None,
        method: Optional[SeparationMethod] = None,
    ) -> SeparationResult:
        """Perform blind source separation."""

    def separate_voices(
        self,
        mixed_signal: Union[np.ndarray, AudioData, str, Path],
        sample_rate: Optional[int] = None,
        max_voices: int = 30,
    ) -> SeparationResult:
        """Specialized separation for multiple voices."""
```

### MultilingualTranscriber

```python
class MultilingualTranscriber:
    def transcribe(
        self,
        audio: Union[np.ndarray, str, Path],
        sample_rate: int = 16000,
        language: Optional[str] = None,
        task: str = "transcribe",
        word_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe audio to text."""

    def transcribe_with_diarization(
        self,
        audio: Union[np.ndarray, str, Path],
        sample_rate: int = 16000,
        language: Optional[str] = None,
        n_speakers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Transcribe with speaker attribution."""
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## Acknowledgments

- OpenAI Whisper for speech recognition
- SpeechBrain for neural audio processing
- pyannote.audio for speaker diarization
- librosa for audio analysis
