"""
Forensic Audio Analyzer Module.

Complete forensic analysis pipeline for recovering and analyzing
attenuated voice messages from audio files.
"""

import numpy as np
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
import warnings
import logging
import traceback

# Configure module logger
logger = logging.getLogger(__name__)


class ForensicAnalysisError(Exception):
    """Base exception for forensic analysis errors."""
    pass


class AudioLoadError(ForensicAnalysisError):
    """Error loading audio file."""
    pass


class RecoveryError(ForensicAnalysisError):
    """Error during signal recovery."""
    pass


class TranscriptionError(ForensicAnalysisError):
    """Error during transcription."""
    pass


def _safe_import_core():
    """Safely import core modules with error handling."""
    try:
        from claudio.core.audio_io import AudioLoader, AudioWriter, AudioData
        return AudioLoader, AudioWriter, AudioData
    except ImportError as e:
        logger.error(f"Failed to import core audio modules: {e}")
        raise ForensicAnalysisError(f"Core audio modules not available: {e}")


def _safe_import_forensic():
    """Safely import forensic modules with error handling."""
    try:
        from claudio.forensic.sub_threshold_recovery import SubThresholdRecovery, RecoveryConfig, RecoveryMode
        from claudio.forensic.phase_coherence_amplifier import PhaseCoherenceAmplifier, AmplificationMethod
        from claudio.forensic.attenuated_voice_detector import AttenuatedVoiceDetector
        return SubThresholdRecovery, RecoveryConfig, RecoveryMode, PhaseCoherenceAmplifier, AmplificationMethod, AttenuatedVoiceDetector
    except ImportError as e:
        logger.error(f"Failed to import forensic modules: {e}")
        raise ForensicAnalysisError(f"Forensic modules not available: {e}")


# Import with error handling
try:
    from claudio.core.audio_io import AudioLoader, AudioWriter, AudioData
    from claudio.forensic.sub_threshold_recovery import SubThresholdRecovery, RecoveryConfig, RecoveryMode
    from claudio.forensic.phase_coherence_amplifier import PhaseCoherenceAmplifier, AmplificationMethod
    from claudio.forensic.attenuated_voice_detector import AttenuatedVoiceDetector
except ImportError:
    # Will be imported on demand
    pass


@dataclass
class ForensicAnalysisResult:
    """Complete result of forensic audio analysis."""

    # Recovered audio
    recovered_signal: np.ndarray
    original_signal: np.ndarray
    sample_rate: int

    # Detection results
    detected_voice_segments: List[Dict[str, Any]]
    n_voices_detected: int
    total_voice_duration: float

    # Enhancement metrics
    total_gain_applied_db: float
    signal_improvement_db: float

    # Analysis
    noise_floor_db: float
    estimated_attenuation_db: float

    # Per-segment enhanced audio
    enhanced_segments: List[Dict[str, Any]] = field(default_factory=list)

    # Processing log
    processing_log: List[str] = field(default_factory=list)

    # Transcription (if performed)
    transcriptions: Optional[Dict[int, Dict[str, Any]]] = None


class ForensicAudioAnalyzer:
    """
    Complete forensic audio analysis system.

    Combines all forensic recovery techniques:
    1. Sub-threshold signal recovery
    2. Phase coherence amplification
    3. Attenuated voice detection
    4. Multi-pass enhancement
    5. Voice separation and transcription
    """

    def __init__(
        self,
        target_threshold_db: float = -35.0,
        max_voices: int = 30,
        sample_rate: int = 16000,
        aggressive_recovery: bool = True,
    ):
        """
        Initialize ForensicAudioAnalyzer.

        Args:
            target_threshold_db: Detection threshold in dB.
            max_voices: Maximum voices to detect.
            sample_rate: Target sample rate.
            aggressive_recovery: Use aggressive recovery mode.
        """
        self.target_threshold_db = target_threshold_db
        self.max_voices = max_voices
        self.sample_rate = sample_rate
        self.aggressive_recovery = aggressive_recovery

        self._processing_log = []

    def _log(self, message: str):
        """Add to processing log."""
        self._processing_log.append(message)

    def analyze(
        self,
        audio: Union[np.ndarray, str, Path, "AudioData"],
        sample_rate: Optional[int] = None,
        output_dir: Optional[Union[str, Path]] = None,
        transcribe: bool = True,
        languages: Optional[List[str]] = None,
    ) -> ForensicAnalysisResult:
        """
        Perform complete forensic analysis.

        Args:
            audio: Input audio.
            sample_rate: Sample rate (for array input).
            output_dir: Directory to save results.
            transcribe: Whether to transcribe recovered audio.
            languages: Languages to try for transcription.

        Returns:
            ForensicAnalysisResult with all analysis data.

        Raises:
            AudioLoadError: If audio cannot be loaded.
            RecoveryError: If signal recovery fails.
            ForensicAnalysisError: For other analysis errors.
        """
        self._processing_log = []
        self._log("=" * 50)
        self._log("FORENSIC AUDIO ANALYSIS")
        self._log("=" * 50)

        # Load audio with error handling
        try:
            signal, sr = self._load_audio(audio, sample_rate)
            original_signal = signal.copy()
        except Exception as e:
            error_msg = f"Failed to load audio: {e}"
            self._log(f"[ERROR] {error_msg}")
            logger.error(error_msg, exc_info=True)
            raise AudioLoadError(error_msg) from e

        # Validate signal
        if signal is None or len(signal) == 0:
            raise AudioLoadError("Empty or invalid audio signal")

        if not np.isfinite(signal).all():
            self._log("[WARNING] Audio contains non-finite values, cleaning...")
            signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)
            original_signal = signal.copy()

        self._log(f"Audio loaded: {len(signal)/sr:.2f}s at {sr}Hz")

        # Step 1: Initial analysis
        self._log("\n[Phase 1] Initial Analysis")
        try:
            rms = np.sqrt(np.mean(signal ** 2))
            initial_level_db = 20 * np.log10(rms + 1e-10)
            self._log(f"  Initial signal level: {initial_level_db:.1f}dB")
        except Exception as e:
            self._log(f"[WARNING] Could not compute initial level: {e}")
            initial_level_db = -60.0

        # Step 2: Attenuated voice detection
        self._log("\n[Phase 2] Attenuated Voice Detection")
        try:
            detector = AttenuatedVoiceDetector(
                sample_rate=sr,
                detection_threshold_db=self.target_threshold_db,
            )
            detection_result = detector.detect(signal, sr)
            self._log(f"  Noise floor: {detection_result.noise_floor_db:.1f}dB")
            self._log(f"  Detected {len(detection_result.segments)} potential voice segments")
            self._log(f"  Estimated {detection_result.n_distinct_voices} distinct voice(s)")
        except Exception as e:
            error_msg = f"Voice detection failed: {e}"
            self._log(f"[ERROR] {error_msg}")
            logger.error(error_msg, exc_info=True)
            raise RecoveryError(error_msg) from e

        # Step 3: Sub-threshold recovery
        self._log("\n[Phase 3] Sub-Threshold Recovery")
        try:
            recovery_config = RecoveryConfig(
                target_threshold_db=self.target_threshold_db,
                mode=RecoveryMode.FORENSIC if self.aggressive_recovery else RecoveryMode.MODERATE,
                n_iterations=15,
                phase_iterations=30,
                max_gain_db=60.0,
            )
            recovery = SubThresholdRecovery(recovery_config)
            recovery_result = recovery.recover_with_multiple_passes(signal, sr, n_passes=3)

            self._log(f"  Recovery gain: +{recovery_result.gain_applied_db:.1f}dB")
            self._log(f"  Signal improvement: +{recovery_result.signal_improvement_db:.1f}dB")
        except Exception as e:
            error_msg = f"Sub-threshold recovery failed: {e}"
            self._log(f"[ERROR] {error_msg}")
            logger.error(error_msg, exc_info=True)
            raise RecoveryError(error_msg) from e

        # Step 4: Phase coherence amplification
        self._log("\n[Phase 4] Phase Coherence Amplification")
        try:
            amplifier = PhaseCoherenceAmplifier(method=AmplificationMethod.ADAPTIVE)

            # Additional amplification for still-quiet segments
            enhanced_signal = recovery_result.recovered_signal.copy()

            segments_amplified = 0
            for segment in detection_result.segments:
                try:
                    if segment.current_level_db < -30:
                        seg_start = segment.start_sample
                        seg_end = segment.end_sample

                        # Bounds check
                        if seg_start >= 0 and seg_end <= len(enhanced_signal) and seg_end > seg_start:
                            segment_signal = enhanced_signal[seg_start:seg_end]

                            # Apply iterative inversion and sum
                            amplified_segment = amplifier.invert_and_sum(segment_signal, sr, n_iterations=5)

                            # Validate output
                            if amplified_segment is not None and len(amplified_segment) == len(segment_signal):
                                # Blend back
                                enhanced_signal[seg_start:seg_end] = amplified_segment
                                segments_amplified += 1
                except Exception as seg_e:
                    self._log(f"  [WARNING] Segment amplification failed: {seg_e}")
                    continue

            self._log(f"  Applied phase coherence amplification to {segments_amplified} segments")
        except Exception as e:
            self._log(f"[WARNING] Phase coherence amplification partially failed: {e}")
            # Continue with partially enhanced signal
            if 'enhanced_signal' not in locals():
                enhanced_signal = recovery_result.recovered_signal.copy()

        # Step 5: Final detection pass on enhanced signal
        self._log("\n[Phase 5] Final Voice Detection")
        try:
            final_detection = detector.detect(enhanced_signal, sr)
            self._log(f"  Final detected segments: {len(final_detection.segments)}")
        except Exception as e:
            self._log(f"[WARNING] Final detection failed, using initial detection: {e}")
            final_detection = detection_result

        # Step 6: Extract and save individual segments
        self._log("\n[Phase 6] Segment Extraction")
        enhanced_segments = []

        for i, segment in enumerate(final_detection.segments):
            try:
                seg_start = max(0, segment.start_sample)
                seg_end = min(len(enhanced_signal), segment.end_sample)

                if seg_end > seg_start:
                    seg_signal = enhanced_signal[seg_start:seg_end]

                    enhanced_segments.append({
                        'id': i,
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'duration': segment.duration,
                        'level_db': segment.current_level_db,
                        'voice_type': segment.voice_type,
                        'fundamental_freq': segment.estimated_fundamental_freq,
                        'confidence': segment.confidence,
                        'signal': seg_signal,
                    })
            except Exception as seg_e:
                self._log(f"  [WARNING] Failed to extract segment {i}: {seg_e}")
                continue

        self._log(f"  Extracted {len(enhanced_segments)} segments")

        # Step 7: Transcription (if requested)
        transcriptions = None
        if transcribe and enhanced_segments:
            self._log("\n[Phase 7] Transcription")
            try:
                transcriptions = self._transcribe_segments(
                    enhanced_segments, sr, languages or ['es', 'en', 'fr', 'de', 'ru', 'pt']
                )
            except Exception as e:
                self._log(f"[WARNING] Transcription failed: {e}")
                transcriptions = {}

        # Save results if output directory specified
        if output_dir:
            try:
                self._save_results(
                    output_dir, enhanced_signal, sr, enhanced_segments, transcriptions
                )
            except Exception as e:
                self._log(f"[WARNING] Failed to save some results: {e}")
                logger.warning(f"Failed to save results: {e}")

        # Calculate final metrics
        try:
            final_level_db = 20 * np.log10(np.sqrt(np.mean(enhanced_signal ** 2)) + 1e-10)
            total_improvement = final_level_db - initial_level_db
        except Exception as e:
            self._log(f"[WARNING] Could not compute final metrics: {e}")
            final_level_db = initial_level_db
            total_improvement = 0.0

        # Build segment info without numpy arrays (for serialization)
        segment_info = []
        for seg in enhanced_segments:
            info = {k: v for k, v in seg.items() if k != 'signal'}
            segment_info.append(info)

        return ForensicAnalysisResult(
            recovered_signal=enhanced_signal,
            original_signal=original_signal,
            sample_rate=sr,
            detected_voice_segments=segment_info,
            n_voices_detected=final_detection.n_distinct_voices,
            total_voice_duration=final_detection.total_voice_duration,
            total_gain_applied_db=recovery_result.gain_applied_db,
            signal_improvement_db=total_improvement,
            noise_floor_db=detection_result.noise_floor_db,
            estimated_attenuation_db=detection_result.overall_attenuation_estimate_db,
            enhanced_segments=enhanced_segments,
            processing_log=self._processing_log.copy(),
            transcriptions=transcriptions,
        )

    def _load_audio(
        self,
        audio: Union[np.ndarray, str, Path, "AudioData"],
        sample_rate: Optional[int],
    ) -> tuple:
        """Load and prepare audio with comprehensive error handling."""
        try:
            if isinstance(audio, (str, Path)):
                # Validate file exists
                audio_path = Path(audio)
                if not audio_path.exists():
                    raise AudioLoadError(f"Audio file not found: {audio_path}")

                if not audio_path.is_file():
                    raise AudioLoadError(f"Path is not a file: {audio_path}")

                # Check file size
                file_size = audio_path.stat().st_size
                if file_size == 0:
                    raise AudioLoadError("Audio file is empty")

                # Try to load audio
                try:
                    from claudio.core.audio_io import AudioLoader
                    loader = AudioLoader(target_sr=self.sample_rate, mono=True, normalize=False)
                    audio_data = loader.load(audio)
                    return audio_data.signal.astype(np.float64), audio_data.sample_rate
                except ImportError:
                    # Fallback to soundfile/librosa
                    try:
                        import soundfile as sf
                        signal, sr = sf.read(str(audio_path))
                        if signal.ndim > 1:
                            signal = np.mean(signal, axis=1)
                        return signal.astype(np.float64), sr
                    except ImportError:
                        import librosa
                        signal, sr = librosa.load(str(audio_path), sr=self.sample_rate, mono=True)
                        return signal.astype(np.float64), sr

            elif hasattr(audio, 'signal') and hasattr(audio, 'sample_rate'):
                # AudioData-like object
                try:
                    if hasattr(audio, 'to_mono'):
                        signal = audio.to_mono().signal.astype(np.float64)
                    else:
                        signal = np.asarray(audio.signal, dtype=np.float64)
                        if signal.ndim > 1:
                            signal = np.mean(signal, axis=0)
                    return signal, audio.sample_rate
                except Exception as e:
                    raise AudioLoadError(f"Failed to extract audio data: {e}")

            else:
                # Numpy array input
                if sample_rate is None:
                    raise AudioLoadError("sample_rate required for array input")

                signal = np.asarray(audio, dtype=np.float64)
                if signal.ndim > 1:
                    signal = np.mean(signal, axis=0)

                if len(signal) == 0:
                    raise AudioLoadError("Empty audio signal")

                return signal, sample_rate

        except AudioLoadError:
            raise
        except Exception as e:
            raise AudioLoadError(f"Unexpected error loading audio: {e}")

    def _transcribe_segments(
        self,
        segments: List[Dict[str, Any]],
        sample_rate: int,
        languages: List[str],
    ) -> Dict[int, Dict[str, Any]]:
        """Transcribe each segment."""
        try:
            from claudio.transcription.transcriber import MultilingualTranscriber

            transcriber = MultilingualTranscriber()
            transcriptions = {}

            for segment in segments:
                seg_id = segment['id']
                seg_signal = segment['signal']

                if len(seg_signal) < sample_rate * 0.3:  # Min 300ms
                    continue

                best_result = None
                best_confidence = 0

                for lang in languages:
                    try:
                        result = transcriber.transcribe(
                            seg_signal,
                            sample_rate=sample_rate,
                            language=lang,
                        )

                        # Check if we got meaningful text
                        if result.text and len(result.text.strip()) > 0:
                            confidence = result.language_confidence

                            if confidence > best_confidence:
                                best_confidence = confidence
                                best_result = {
                                    'text': result.text,
                                    'language': result.language,
                                    'confidence': confidence,
                                    'segments': [
                                        {
                                            'text': s.text,
                                            'start': s.start_time,
                                            'end': s.end_time,
                                        }
                                        for s in result.segments
                                    ],
                                }
                    except Exception as e:
                        continue

                if best_result:
                    transcriptions[seg_id] = best_result
                    self._log(f"  Segment {seg_id}: [{best_result['language']}] {best_result['text'][:50]}...")

            return transcriptions

        except ImportError:
            self._log("  Transcription skipped: whisper not available")
            return {}

    def _save_results(
        self,
        output_dir: Union[str, Path],
        enhanced_signal: np.ndarray,
        sample_rate: int,
        segments: List[Dict[str, Any]],
        transcriptions: Optional[Dict],
    ):
        """Save all results to output directory."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        writer = AudioWriter(sample_rate=sample_rate)

        # Save full enhanced audio
        full_path = output_dir / "recovered_full.wav"
        writer.write(enhanced_signal, full_path)
        self._log(f"\n[Output] Saved full audio: {full_path}")

        # Save individual segments
        segments_dir = output_dir / "segments"
        segments_dir.mkdir(exist_ok=True)

        for segment in segments:
            seg_path = segments_dir / f"segment_{segment['id']:03d}_{segment['start_time']:.2f}s.wav"
            writer.write(segment['signal'], seg_path)

        self._log(f"[Output] Saved {len(segments)} segments to {segments_dir}")

        # Save analysis report
        report = {
            'n_segments': len(segments),
            'total_voice_duration': sum(s['duration'] for s in segments),
            'segments': [{k: v for k, v in s.items() if k != 'signal'} for s in segments],
            'transcriptions': transcriptions or {},
            'processing_log': self._processing_log,
        }

        report_path = output_dir / "analysis_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        self._log(f"[Output] Saved report: {report_path}")

        # Save transcription text file
        if transcriptions:
            transcript_path = output_dir / "transcriptions.txt"
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write("FORENSIC AUDIO TRANSCRIPTION REPORT\n")
                f.write("=" * 50 + "\n\n")

                for seg_id, trans in sorted(transcriptions.items()):
                    segment = next((s for s in segments if s['id'] == seg_id), None)
                    if segment:
                        f.write(f"Segment {seg_id} [{segment['start_time']:.2f}s - {segment['end_time']:.2f}s]\n")
                        f.write(f"Language: {trans['language']} (confidence: {trans['confidence']:.2%})\n")
                        f.write(f"Voice type: {segment['voice_type']}\n")
                        f.write(f"Text: {trans['text']}\n")
                        f.write("-" * 40 + "\n\n")

            self._log(f"[Output] Saved transcriptions: {transcript_path}")

    def quick_analyze(
        self,
        audio: Union[np.ndarray, str, Path],
        sample_rate: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Quick analysis without full recovery.

        Returns basic information about potential attenuated content.

        Raises:
            AudioLoadError: If audio cannot be loaded.
            ForensicAnalysisError: For other analysis errors.
        """
        try:
            signal, sr = self._load_audio(audio, sample_rate)

            # Validate signal
            if signal is None or len(signal) == 0:
                return {
                    'has_attenuated_content': False,
                    'n_segments': 0,
                    'n_distinct_voices': 0,
                    'total_duration': 0.0,
                    'noise_floor_db': -96.0,
                    'estimated_attenuation_db': 0.0,
                    'segments': [],
                    'error': 'Empty or invalid audio',
                }

            detector = AttenuatedVoiceDetector(
                sample_rate=sr,
                detection_threshold_db=self.target_threshold_db,
            )
            result = detector.detect(signal, sr)

            return {
                'has_attenuated_content': len(result.segments) > 0,
                'n_segments': len(result.segments),
                'n_distinct_voices': result.n_distinct_voices,
                'total_duration': result.total_voice_duration,
                'noise_floor_db': result.noise_floor_db,
                'estimated_attenuation_db': result.overall_attenuation_estimate_db,
                'segments': [
                    {
                        'start': s.start_time,
                        'end': s.end_time,
                        'level_db': s.current_level_db,
                        'voice_type': s.voice_type,
                    }
                    for s in result.segments
                ],
            }

        except AudioLoadError:
            raise
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}", exc_info=True)
            raise ForensicAnalysisError(f"Quick analysis failed: {e}") from e
