"""
Claudio CLI - Advanced Audio Analysis and Source Separation Tool.

Main command-line interface for processing audio files with:
- Blind Source Separation
- Speaker Diarization
- Multilingual Transcription
- LLM-based Content Analysis
"""

import sys
from pathlib import Path
from typing import Optional, List
import json

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich import print as rprint

console = Console()


def print_banner():
    """Print application banner."""
    banner = """
 ██████╗██╗      █████╗ ██╗   ██╗██████╗ ██╗ ██████╗
██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗
██║     ██║     ███████║██║   ██║██║  ██║██║██║   ██║
██║     ██║     ██╔══██║██║   ██║██║  ██║██║██║   ██║
╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝
 ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝
    Audio Analysis & Blind Source Separation
    """
    console.print(banner, style="bold cyan")


@click.group()
@click.version_option(version="1.0.0")
def main():
    """
    Claudio - Advanced Audio Analysis Tool.

    Performs blind source separation, speaker diarization,
    and multilingual transcription with LLM analysis.
    """
    pass


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-n", "--n-sources", type=int, default=2, help="Number of sources to separate")
@click.option("-m", "--method", type=click.Choice(["ica", "nmf", "hybrid", "deep"]), default="hybrid")
@click.option("--enhance/--no-enhance", default=True, help="Apply phase enhancement")
@click.option("-f", "--format", type=click.Choice(["wav", "flac", "mp3"]), default="wav")
def separate(
    input_file: str,
    output: Optional[str],
    n_sources: int,
    method: str,
    enhance: bool,
    format: str,
):
    """
    Separate audio sources using blind source separation.

    Separates mixed audio into individual source signals using
    ICA, NMF, or hybrid methods.
    """
    print_banner()

    from claudio.core.audio_io import AudioLoader
    from claudio.separation.bss import BlindSourceSeparator, SeparationConfig, SeparationMethod

    method_map = {
        "ica": SeparationMethod.ICA,
        "nmf": SeparationMethod.NMF,
        "hybrid": SeparationMethod.HYBRID,
        "deep": SeparationMethod.DEEP_LEARNING,
    }

    input_path = Path(input_file)
    output_dir = Path(output) if output else input_path.parent / f"{input_path.stem}_separated"

    console.print(f"\n[bold]Input:[/bold] {input_file}")
    console.print(f"[bold]Output:[/bold] {output_dir}")
    console.print(f"[bold]Sources:[/bold] {n_sources}")
    console.print(f"[bold]Method:[/bold] {method}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        # Load audio
        task = progress.add_task("Loading audio...", total=None)
        loader = AudioLoader(mono=True, normalize=True)
        audio = loader.load(input_file)
        progress.update(task, completed=True)

        # Configure separator
        config = SeparationConfig(
            method=method_map[method],
            n_sources=n_sources,
            enhance_output=enhance,
        )

        # Separate
        task = progress.add_task("Separating sources...", total=None)
        separator = BlindSourceSeparator(config)
        result = separator.separate(audio)
        progress.update(task, completed=True)

        # Save results
        task = progress.add_task("Saving results...", total=None)
        output_paths = separator.save_sources(result, output_dir, format=f".{format}")
        progress.update(task, completed=True)

    # Display results
    console.print("\n[bold green]Separation complete![/bold green]\n")

    table = Table(title="Separated Sources")
    table.add_column("Source", style="cyan")
    table.add_column("Confidence", style="magenta")
    table.add_column("File", style="green")

    for i, (source, path) in enumerate(zip(result.sources, output_paths)):
        table.add_row(
            f"Source {i + 1}",
            f"{source.confidence:.2%}",
            path,
        )

    console.print(table)
    console.print(f"\n[dim]Reconstruction error: {result.reconstruction_error():.6f}[/dim]")


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-n", "--n-speakers", type=int, help="Number of speakers (auto-detect if not set)")
@click.option("--max-speakers", type=int, default=30, help="Maximum speakers to detect")
@click.option("--save-audio/--no-save-audio", default=True, help="Save separated speaker audio")
def diarize(
    input_file: str,
    output: Optional[str],
    n_speakers: Optional[int],
    max_speakers: int,
    save_audio: bool,
):
    """
    Perform speaker diarization on audio.

    Identifies different speakers and segments the audio
    by who is speaking when.
    """
    print_banner()

    from claudio.core.audio_io import AudioLoader, AudioWriter
    from claudio.analysis.speaker_diarization import SpeakerDiarizer

    input_path = Path(input_file)
    output_dir = Path(output) if output else input_path.parent / f"{input_path.stem}_diarized"
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Input:[/bold] {input_file}")
    console.print(f"[bold]Output:[/bold] {output_dir}")
    if n_speakers:
        console.print(f"[bold]Expected speakers:[/bold] {n_speakers}")
    console.print(f"[bold]Max speakers:[/bold] {max_speakers}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        # Load audio
        task = progress.add_task("Loading audio...", total=None)
        loader = AudioLoader(target_sr=16000, mono=True, normalize=True)
        audio = loader.load(input_file)
        progress.update(task, completed=True)

        # Diarize
        task = progress.add_task("Analyzing speakers...", total=None)
        diarizer = SpeakerDiarizer(
            sample_rate=audio.sample_rate,
            n_speakers=n_speakers,
            max_speakers=max_speakers,
        )
        result = diarizer.diarize(audio.signal, audio.sample_rate, n_speakers=n_speakers)
        progress.update(task, completed=True)

        # Save RTTM
        task = progress.add_task("Saving results...", total=None)
        rttm_path = output_dir / f"{input_path.stem}.rttm"
        diarizer.save_rttm(result, rttm_path, file_id=input_path.stem)

        # Save speaker audio if requested
        if save_audio:
            writer = AudioWriter(sample_rate=audio.sample_rate)
            for speaker in result.speakers:
                speaker_audio = result.extract_speaker_audio(audio.signal, speaker.speaker_id)
                if len(speaker_audio) > 0:
                    speaker_path = output_dir / f"speaker_{speaker.speaker_id:02d}.wav"
                    writer.write(speaker_audio, speaker_path)

        progress.update(task, completed=True)

    # Display results
    console.print(f"\n[bold green]Diarization complete![/bold green]")
    console.print(f"[bold]Detected {result.n_speakers} speaker(s)[/bold]\n")

    table = Table(title="Speaker Summary")
    table.add_column("Speaker", style="cyan")
    table.add_column("Duration", style="magenta")
    table.add_column("Segments", style="green")

    for speaker in result.speakers:
        table.add_row(
            f"Speaker {speaker.speaker_id}",
            f"{speaker.total_duration:.2f}s",
            str(speaker.n_segments),
        )

    console.print(table)

    # Timeline
    console.print("\n[bold]Timeline:[/bold]")
    for segment in result.segments[:10]:  # Show first 10
        console.print(
            f"  [{segment.start_time:.2f}s - {segment.end_time:.2f}s] "
            f"Speaker {segment.speaker_id}"
        )
    if len(result.segments) > 10:
        console.print(f"  ... and {len(result.segments) - 10} more segments")

    console.print(f"\n[dim]RTTM saved to: {rttm_path}[/dim]")


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output file or directory")
@click.option("-l", "--language", help="Language code (auto-detect if not set)")
@click.option("--model", type=click.Choice(["tiny", "base", "small", "medium", "large", "large-v3"]), default="medium")
@click.option("-f", "--format", type=click.Choice(["txt", "srt", "vtt", "json"]), default="txt")
@click.option("--diarize/--no-diarize", default=False, help="Include speaker diarization")
@click.option("--n-speakers", type=int, help="Number of speakers for diarization")
def transcribe(
    input_file: str,
    output: Optional[str],
    language: Optional[str],
    model: str,
    format: str,
    diarize: bool,
    n_speakers: Optional[int],
):
    """
    Transcribe audio to text.

    Supports 10+ languages including Spanish, English, French,
    German, Russian, Portuguese, Chinese, Japanese, Korean, etc.
    """
    print_banner()

    from claudio.transcription.transcriber import MultilingualTranscriber, TranscriptionModel
    from claudio.transcription.language_detector import LanguageDetector

    model_map = {
        "tiny": TranscriptionModel.WHISPER_TINY,
        "base": TranscriptionModel.WHISPER_BASE,
        "small": TranscriptionModel.WHISPER_SMALL,
        "medium": TranscriptionModel.WHISPER_MEDIUM,
        "large": TranscriptionModel.WHISPER_LARGE,
        "large-v3": TranscriptionModel.WHISPER_LARGE_V3,
    }

    input_path = Path(input_file)
    if output:
        output_path = Path(output)
    else:
        output_path = input_path.parent / f"{input_path.stem}.{format}"

    console.print(f"\n[bold]Input:[/bold] {input_file}")
    console.print(f"[bold]Output:[/bold] {output_path}")
    console.print(f"[bold]Model:[/bold] whisper-{model}")
    if language:
        console.print(f"[bold]Language:[/bold] {language}")
    console.print("")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        # Initialize transcriber
        task = progress.add_task("Loading model...", total=None)
        transcriber = MultilingualTranscriber(
            model=model_map[model],
            language=language,
        )
        progress.update(task, completed=True)

        if diarize:
            # Transcribe with diarization
            task = progress.add_task("Transcribing with diarization...", total=None)
            result_dict = transcriber.transcribe_with_diarization(
                input_file,
                language=language,
                n_speakers=n_speakers,
            )
            result = result_dict["transcription"]
            speaker_texts = result_dict["speaker_transcripts"]
            n_detected_speakers = result_dict["n_speakers"]
            progress.update(task, completed=True)
        else:
            # Regular transcription
            task = progress.add_task("Transcribing...", total=None)
            result = transcriber.transcribe(input_file, language=language)
            speaker_texts = None
            n_detected_speakers = None
            progress.update(task, completed=True)

        # Save result
        task = progress.add_task("Saving...", total=None)
        transcriber.save_transcription(result, output_path, format=format)
        progress.update(task, completed=True)

    # Display results
    console.print(f"\n[bold green]Transcription complete![/bold green]\n")

    console.print(Panel(
        result.text[:500] + ("..." if len(result.text) > 500 else ""),
        title="Transcription",
        border_style="blue",
    ))

    console.print(f"\n[bold]Language:[/bold] {result.language}")
    console.print(f"[bold]Duration:[/bold] {result.duration:.2f}s")
    console.print(f"[bold]Segments:[/bold] {len(result.segments)}")

    if diarize and speaker_texts:
        console.print(f"\n[bold]Speakers detected:[/bold] {n_detected_speakers}")
        for speaker_id, texts in speaker_texts.items():
            if texts:
                console.print(f"\n[cyan]Speaker {speaker_id}:[/cyan]")
                full_text = " ".join(t["text"] for t in texts[:3])
                console.print(f"  {full_text[:200]}...")

    console.print(f"\n[dim]Saved to: {output_path}[/dim]")


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output JSON file")
@click.option("--provider", type=click.Choice(["local", "openai", "anthropic"]), default="local")
@click.option("--api-key", envvar="LLM_API_KEY", help="API key for cloud providers")
@click.option("--transcribe/--no-transcribe", default=True, help="Transcribe before analysis")
@click.option("-l", "--language", help="Language for transcription")
def analyze(
    input_file: str,
    output: Optional[str],
    provider: str,
    api_key: Optional[str],
    transcribe: bool,
    language: Optional[str],
):
    """
    Analyze audio content using LLM.

    Extracts summaries, key phrases, topics, sentiment,
    and other insights from audio content.
    """
    print_banner()

    from claudio.transcription.transcriber import MultilingualTranscriber
    from claudio.transcription.llm_analyzer import LLMAnalyzer, LLMProvider

    provider_map = {
        "local": LLMProvider.LOCAL,
        "openai": LLMProvider.OPENAI,
        "anthropic": LLMProvider.ANTHROPIC,
    }

    input_path = Path(input_file)
    output_path = Path(output) if output else input_path.parent / f"{input_path.stem}_analysis.json"

    console.print(f"\n[bold]Input:[/bold] {input_file}")
    console.print(f"[bold]Output:[/bold] {output_path}")
    console.print(f"[bold]Provider:[/bold] {provider}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        text_content = None

        if transcribe:
            # Transcribe first
            task = progress.add_task("Transcribing...", total=None)
            transcriber = MultilingualTranscriber()
            transcription = transcriber.transcribe(input_file, language=language)
            text_content = transcription.text
            detected_language = transcription.language
            progress.update(task, completed=True)
        else:
            # Assume text file
            with open(input_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
            detected_language = language or "en"

        # Analyze
        task = progress.add_task("Analyzing with LLM...", total=None)
        analyzer = LLMAnalyzer(
            provider=provider_map[provider],
            api_key=api_key,
        )
        result = analyzer.analyze(text_content, "full_analysis")
        progress.update(task, completed=True)

        # Save
        task = progress.add_task("Saving...", total=None)
        output_data = {
            "input_file": str(input_path),
            "language": detected_language,
            "summary": result.summary,
            "key_phrases": result.key_phrases,
            "topics": result.topics,
            "sentiment": result.sentiment,
            "entities": result.entities,
        }

        if transcribe:
            output_data["transcription"] = text_content

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        progress.update(task, completed=True)

    # Display results
    console.print(f"\n[bold green]Analysis complete![/bold green]\n")

    if result.summary:
        console.print(Panel(result.summary, title="Summary", border_style="blue"))

    if result.key_phrases:
        console.print("\n[bold]Key Phrases:[/bold]")
        for phrase in result.key_phrases[:10]:
            console.print(f"  - {phrase}")

    if result.topics:
        console.print("\n[bold]Topics:[/bold]")
        for topic in result.topics:
            console.print(f"  - {topic}")

    if result.sentiment:
        console.print("\n[bold]Sentiment:[/bold]")
        for key, value in result.sentiment.items():
            console.print(f"  {key}: {value:.2%}")

    console.print(f"\n[dim]Full analysis saved to: {output_path}[/dim]")


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("--max-speakers", type=int, default=30)
@click.option("--language", "-l", help="Language for transcription")
@click.option("--analyze/--no-analyze", default=True, help="Perform LLM analysis")
def full_pipeline(
    input_file: str,
    output: Optional[str],
    max_speakers: int,
    language: Optional[str],
    analyze: bool,
):
    """
    Run full audio analysis pipeline.

    Performs source separation, diarization, transcription,
    and LLM analysis in one command.
    """
    print_banner()

    from claudio.core.audio_io import AudioLoader, AudioWriter
    from claudio.separation.bss import BlindSourceSeparator, SeparationConfig
    from claudio.analysis.speaker_diarization import SpeakerDiarizer
    from claudio.transcription.transcriber import MultilingualTranscriber
    from claudio.transcription.llm_analyzer import LLMAnalyzer, LLMProvider

    input_path = Path(input_file)
    output_dir = Path(output) if output else input_path.parent / f"{input_path.stem}_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Input:[/bold] {input_file}")
    console.print(f"[bold]Output:[/bold] {output_dir}")
    console.print(f"[bold]Max speakers:[/bold] {max_speakers}\n")

    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        # 1. Load audio
        task = progress.add_task("[1/5] Loading audio...", total=None)
        loader = AudioLoader(target_sr=16000, mono=True, normalize=True)
        audio = loader.load(input_file)
        results["duration"] = audio.duration
        progress.update(task, completed=True)

        # 2. Speaker diarization
        task = progress.add_task("[2/5] Analyzing speakers...", total=None)
        diarizer = SpeakerDiarizer(sample_rate=audio.sample_rate, max_speakers=max_speakers)
        diarization = diarizer.diarize(audio.signal, audio.sample_rate)
        results["n_speakers"] = diarization.n_speakers
        progress.update(task, completed=True)

        # 3. Save speaker audio
        task = progress.add_task("[3/5] Extracting speaker audio...", total=None)
        writer = AudioWriter(sample_rate=audio.sample_rate)
        speaker_files = {}
        for speaker in diarization.speakers:
            speaker_audio = diarization.extract_speaker_audio(audio.signal, speaker.speaker_id)
            if len(speaker_audio) > audio.sample_rate * 0.5:  # At least 0.5s
                speaker_path = output_dir / f"speaker_{speaker.speaker_id:02d}.wav"
                writer.write(speaker_audio, speaker_path)
                speaker_files[speaker.speaker_id] = str(speaker_path)
        progress.update(task, completed=True)

        # 4. Transcribe each speaker
        task = progress.add_task("[4/5] Transcribing speakers...", total=None)
        transcriber = MultilingualTranscriber(language=language)
        speaker_transcripts = {}
        for speaker_id, speaker_file in speaker_files.items():
            try:
                transcription = transcriber.transcribe(speaker_file, language=language)
                speaker_transcripts[speaker_id] = {
                    "text": transcription.text,
                    "language": transcription.language,
                    "duration": transcription.duration,
                }
            except Exception as e:
                speaker_transcripts[speaker_id] = {"error": str(e)}
        results["transcripts"] = speaker_transcripts
        progress.update(task, completed=True)

        # 5. LLM Analysis
        if analyze:
            task = progress.add_task("[5/5] Analyzing content...", total=None)
            analyzer = LLMAnalyzer(provider=LLMProvider.LOCAL)

            # Analyze each speaker
            speaker_analysis = {}
            for speaker_id, transcript in speaker_transcripts.items():
                if "text" in transcript and len(transcript["text"]) > 20:
                    analysis = analyzer.analyze(transcript["text"])
                    speaker_analysis[speaker_id] = {
                        "summary": analysis.summary,
                        "key_phrases": analysis.key_phrases,
                        "topics": analysis.topics,
                        "sentiment": analysis.sentiment,
                    }
            results["analysis"] = speaker_analysis
            progress.update(task, completed=True)
        else:
            progress.add_task("[5/5] Skipping analysis...", total=None)

    # Save complete results
    results_path = output_dir / "results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    # Save RTTM
    rttm_path = output_dir / f"{input_path.stem}.rttm"
    diarizer.save_rttm(diarization, rttm_path)

    # Display results
    console.print(f"\n[bold green]Pipeline complete![/bold green]\n")

    console.print(f"[bold]Duration:[/bold] {results['duration']:.2f}s")
    console.print(f"[bold]Speakers detected:[/bold] {results['n_speakers']}\n")

    table = Table(title="Speaker Analysis")
    table.add_column("Speaker", style="cyan")
    table.add_column("Duration", style="magenta")
    table.add_column("Language", style="green")
    table.add_column("Summary", style="white")

    for speaker in diarization.speakers:
        sid = speaker.speaker_id
        transcript = speaker_transcripts.get(sid, {})
        analysis = results.get("analysis", {}).get(sid, {})

        summary = analysis.get("summary", transcript.get("text", "")[:50])
        if summary and len(summary) > 50:
            summary = summary[:50] + "..."

        table.add_row(
            f"Speaker {sid}",
            f"{speaker.total_duration:.1f}s",
            transcript.get("language", "?"),
            summary or "-",
        )

    console.print(table)

    console.print(f"\n[bold]Output files:[/bold]")
    console.print(f"  Results: {results_path}")
    console.print(f"  RTTM: {rttm_path}")
    for sid, path in speaker_files.items():
        console.print(f"  Speaker {sid}: {path}")


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-t", "--threshold", type=float, default=-35.0, help="Detection threshold in dB")
@click.option("--max-voices", type=int, default=30, help="Maximum voices to detect")
@click.option("-l", "--languages", default="es,en,fr,de,ru,pt", help="Languages for transcription")
@click.option("--aggressive/--no-aggressive", default=True, help="Aggressive recovery mode")
@click.option("--transcribe/--no-transcribe", default=True, help="Transcribe recovered audio")
def forensic(
    input_file: str,
    output: Optional[str],
    threshold: float,
    max_voices: int,
    languages: str,
    aggressive: bool,
    transcribe: bool,
):
    """
    Forensic audio recovery for attenuated voices.

    Recovers voices attenuated below -35dB using phase coherence
    amplification and iterative enhancement techniques.
    """
    print_banner()

    from claudio.forensic.forensic_analyzer import ForensicAudioAnalyzer

    input_path = Path(input_file)
    output_dir = Path(output) if output else input_path.parent / f"{input_path.stem}_forensic"
    output_dir.mkdir(parents=True, exist_ok=True)

    lang_list = [l.strip() for l in languages.split(',')]

    console.print(f"\n[bold]FORENSIC AUDIO RECOVERY[/bold]")
    console.print(f"[bold]Input:[/bold] {input_file}")
    console.print(f"[bold]Output:[/bold] {output_dir}")
    console.print(f"[bold]Threshold:[/bold] {threshold} dB")
    console.print(f"[bold]Max voices:[/bold] {max_voices}")
    console.print(f"[bold]Languages:[/bold] {', '.join(lang_list)}\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Running forensic analysis...", total=None)

        analyzer = ForensicAudioAnalyzer(
            target_threshold_db=threshold,
            max_voices=max_voices,
            aggressive_recovery=aggressive,
        )

        result = analyzer.analyze(
            str(input_file),
            output_dir=str(output_dir),
            transcribe=transcribe,
            languages=lang_list,
        )

        progress.update(task, completed=True)

    # Display results
    console.print(f"\n[bold green]Forensic Recovery Complete![/bold green]\n")

    console.print(Panel(
        f"[cyan]Signal Improvement:[/cyan] +{result.signal_improvement_db:.1f} dB\n"
        f"[cyan]Voice Segments:[/cyan] {len(result.detected_voice_segments)}\n"
        f"[cyan]Distinct Voices:[/cyan] {result.n_voices_detected}\n"
        f"[cyan]Total Voice Duration:[/cyan] {result.total_voice_duration:.2f}s\n"
        f"[cyan]Noise Floor:[/cyan] {result.noise_floor_db:.1f} dB",
        title="Recovery Results",
        border_style="green",
    ))

    # Show segments
    if result.detected_voice_segments:
        table = Table(title="Detected Voice Segments")
        table.add_column("ID", style="cyan")
        table.add_column("Time", style="magenta")
        table.add_column("Duration", style="green")
        table.add_column("Level", style="yellow")
        table.add_column("Voice", style="blue")

        for seg in result.detected_voice_segments[:15]:
            table.add_row(
                str(seg.get('id', '-')),
                f"{seg.get('start_time', 0):.2f}s",
                f"{seg.get('duration', 0):.2f}s",
                f"{seg.get('level_db', 0):.1f} dB",
                seg.get('voice_type', '-'),
            )

        if len(result.detected_voice_segments) > 15:
            table.add_row("...", "...", "...", "...", "...")

        console.print(table)

    # Show transcriptions
    if result.transcriptions:
        console.print("\n[bold]Transcriptions:[/bold]\n")
        for seg_id, trans in list(result.transcriptions.items())[:5]:
            console.print(f"[cyan]Segment {seg_id}[/cyan] [{trans.get('language', '?')}]:")
            text = trans.get('text', '')
            if len(text) > 100:
                text = text[:100] + "..."
            console.print(f"  {text}\n")

    console.print(f"\n[bold]Output files saved to:[/bold] {output_dir}")

    # Show processing log summary
    console.print(f"\n[dim]Processing completed with {len(result.processing_log)} log entries[/dim]")


@main.command()
def info():
    """Show system information and available features."""
    print_banner()

    import platform

    console.print("\n[bold]System Information[/bold]\n")

    info_table = Table(show_header=False)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="green")

    info_table.add_row("Python", platform.python_version())
    info_table.add_row("Platform", platform.platform())

    # Check for optional dependencies
    deps = {
        "numpy": None,
        "scipy": None,
        "torch": None,
        "torchaudio": None,
        "whisper": None,
        "faster_whisper": None,
        "speechbrain": None,
        "pyannote.audio": None,
        "transformers": None,
    }

    for dep in deps:
        try:
            mod = __import__(dep.replace(".", "_"))
            deps[dep] = getattr(mod, "__version__", "installed")
        except ImportError:
            deps[dep] = "not installed"

    console.print(info_table)

    console.print("\n[bold]Dependencies[/bold]\n")

    dep_table = Table()
    dep_table.add_column("Package", style="cyan")
    dep_table.add_column("Status", style="green")

    for dep, version in deps.items():
        status = f"[green]{version}[/green]" if version != "not installed" else "[red]not installed[/red]"
        dep_table.add_row(dep, status)

    console.print(dep_table)

    console.print("\n[bold]Supported Languages[/bold]\n")
    languages = [
        "Spanish (es)", "English (en)", "French (fr)", "German (de)",
        "Russian (ru)", "Portuguese (pt)", "Italian (it)", "Chinese (zh)",
        "Japanese (ja)", "Korean (ko)", "Arabic (ar)", "Hindi (hi)",
        "+ 20 more languages"
    ]
    for lang in languages:
        console.print(f"  - {lang}")


if __name__ == "__main__":
    main()
