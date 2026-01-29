"""
Speaker Diarization Module.

Identifies and segments different speakers in audio:
- Speaker embedding extraction
- Clustering-based diarization
- Neural network-based diarization (when available)
"""

import numpy as np
from scipy import signal as scipy_signal
from sklearn.cluster import AgglomerativeClustering, SpectralClustering, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional, List, Dict, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from claudio.analysis.voice_detector import VoiceDetector, VoiceSegment, VADResult
from claudio.analysis.feature_extraction import FeatureExtractor, AudioFeatures


class ClusteringMethod(Enum):
    """Speaker clustering methods."""
    AGGLOMERATIVE = "agglomerative"
    SPECTRAL = "spectral"
    KMEANS = "kmeans"


@dataclass
class SpeakerSegment:
    """A segment attributed to a specific speaker."""

    speaker_id: int
    start_time: float
    end_time: float
    start_sample: int
    end_sample: int
    confidence: float
    embedding: Optional[np.ndarray] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class SpeakerProfile:
    """Profile of a detected speaker."""

    speaker_id: int
    embedding: np.ndarray  # Representative embedding
    total_duration: float  # Total speaking time
    n_segments: int  # Number of segments
    metadata: Dict = field(default_factory=dict)


@dataclass
class DiarizationResult:
    """Result of speaker diarization."""

    segments: List[SpeakerSegment]
    speakers: List[SpeakerProfile]
    sample_rate: int
    n_speakers: int

    def get_speaker_segments(self, speaker_id: int) -> List[SpeakerSegment]:
        """Get all segments for a specific speaker."""
        return [s for s in self.segments if s.speaker_id == speaker_id]

    def get_timeline(self) -> List[Tuple[float, float, int]]:
        """Get timeline as list of (start, end, speaker_id) tuples."""
        return [(s.start_time, s.end_time, s.speaker_id) for s in self.segments]

    def extract_speaker_audio(
        self,
        signal: np.ndarray,
        speaker_id: int,
    ) -> np.ndarray:
        """Extract audio for a specific speaker."""
        segments = self.get_speaker_segments(speaker_id)
        parts = []
        for segment in segments:
            parts.append(signal[segment.start_sample:segment.end_sample])
        return np.concatenate(parts) if parts else np.array([])


class SpeakerDiarizer:
    """
    Speaker Diarization system.

    Identifies different speakers in audio and segments the audio
    by speaker. Supports up to 30+ speakers.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        n_speakers: Optional[int] = None,
        max_speakers: int = 30,
        clustering_method: ClusteringMethod = ClusteringMethod.AGGLOMERATIVE,
        use_neural_embeddings: bool = True,
    ):
        """
        Initialize SpeakerDiarizer.

        Args:
            sample_rate: Audio sample rate.
            n_speakers: Known number of speakers (None for auto-detect).
            max_speakers: Maximum number of speakers to detect.
            clustering_method: Method for speaker clustering.
            use_neural_embeddings: Use neural network embeddings if available.
        """
        self.sample_rate = sample_rate
        self.n_speakers = n_speakers
        self.max_speakers = max_speakers
        self.clustering_method = clustering_method
        self.use_neural_embeddings = use_neural_embeddings

        self.voice_detector = VoiceDetector(sample_rate=sample_rate)
        self.feature_extractor = FeatureExtractor(sample_rate=sample_rate)

        # Neural embedding model (lazy loaded)
        self._embedding_model = None

    def diarize(
        self,
        signal: np.ndarray,
        sample_rate: Optional[int] = None,
        n_speakers: Optional[int] = None,
        min_segment_duration: float = 0.5,
    ) -> DiarizationResult:
        """
        Perform speaker diarization.

        Args:
            signal: Input audio signal.
            sample_rate: Sample rate.
            n_speakers: Number of speakers (overrides instance setting).
            min_segment_duration: Minimum segment duration.

        Returns:
            DiarizationResult with speaker-attributed segments.
        """
        sr = sample_rate or self.sample_rate
        n_speakers = n_speakers or self.n_speakers

        # Resample if needed
        if sr != self.sample_rate:
            import librosa
            signal = librosa.resample(signal, orig_sr=sr, target_sr=self.sample_rate)
            sr = self.sample_rate

        # Step 1: Voice Activity Detection
        vad_result = self.voice_detector.detect_speech_turns(
            signal, sr, min_turn_duration=min_segment_duration
        )

        if not vad_result:
            return DiarizationResult(
                segments=[],
                speakers=[],
                sample_rate=sr,
                n_speakers=0,
            )

        # Step 2: Extract embeddings for each segment
        embeddings = []
        valid_segments = []

        for segment in vad_result:
            segment_signal = signal[segment.start_sample:segment.end_sample]

            if len(segment_signal) < sr * 0.3:  # Too short
                continue

            embedding = self._extract_embedding(segment_signal, sr)
            embeddings.append(embedding)
            valid_segments.append(segment)

        if len(embeddings) < 2:
            # Single segment or no valid segments
            speaker_segments = [
                SpeakerSegment(
                    speaker_id=0,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    start_sample=s.start_sample,
                    end_sample=s.end_sample,
                    confidence=s.confidence,
                    embedding=embeddings[i] if i < len(embeddings) else None,
                )
                for i, s in enumerate(valid_segments)
            ]
            speakers = [
                SpeakerProfile(
                    speaker_id=0,
                    embedding=embeddings[0] if embeddings else np.zeros(256),
                    total_duration=sum(s.duration for s in speaker_segments),
                    n_segments=len(speaker_segments),
                )
            ]
            return DiarizationResult(
                segments=speaker_segments,
                speakers=speakers,
                sample_rate=sr,
                n_speakers=1,
            )

        embeddings = np.array(embeddings)

        # Step 3: Cluster embeddings
        if n_speakers is None:
            n_speakers = self._estimate_n_speakers(embeddings)

        n_speakers = min(n_speakers, len(embeddings), self.max_speakers)

        labels = self._cluster_embeddings(embeddings, n_speakers)

        # Step 4: Create speaker segments
        speaker_segments = []
        for i, (segment, label) in enumerate(zip(valid_segments, labels)):
            speaker_segments.append(SpeakerSegment(
                speaker_id=int(label),
                start_time=segment.start_time,
                end_time=segment.end_time,
                start_sample=segment.start_sample,
                end_sample=segment.end_sample,
                confidence=segment.confidence,
                embedding=embeddings[i],
            ))

        # Step 5: Create speaker profiles
        speakers = self._create_speaker_profiles(speaker_segments, embeddings, labels)

        # Sort segments by time
        speaker_segments.sort(key=lambda x: x.start_time)

        return DiarizationResult(
            segments=speaker_segments,
            speakers=speakers,
            sample_rate=sr,
            n_speakers=n_speakers,
        )

    def _extract_embedding(
        self,
        segment_signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """Extract speaker embedding for a segment."""
        if self.use_neural_embeddings:
            try:
                return self._extract_neural_embedding(segment_signal, sample_rate)
            except Exception:
                pass

        # Fall back to acoustic feature-based embedding
        return self.feature_extractor.extract_speaker_embedding(segment_signal, sample_rate)

    def _extract_neural_embedding(
        self,
        segment_signal: np.ndarray,
        sample_rate: int,
    ) -> np.ndarray:
        """Extract embedding using neural network."""
        try:
            from speechbrain.inference.speaker import EncoderClassifier

            if self._embedding_model is None:
                self._embedding_model = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="pretrained_models/spkrec-ecapa-voxceleb",
                )

            import torch
            audio_tensor = torch.tensor(segment_signal).float().unsqueeze(0)
            embedding = self._embedding_model.encode_batch(audio_tensor)
            return embedding.squeeze().numpy()

        except ImportError:
            # Try pyannote
            try:
                from pyannote.audio import Model, Inference

                if self._embedding_model is None:
                    self._embedding_model = Model.from_pretrained(
                        "pyannote/embedding"
                    )

                inference = Inference(self._embedding_model, window="whole")
                embedding = inference({"waveform": segment_signal, "sample_rate": sample_rate})
                return embedding

            except Exception:
                raise

    def _estimate_n_speakers(
        self,
        embeddings: np.ndarray,
        max_speakers: Optional[int] = None,
    ) -> int:
        """Estimate number of speakers using elbow method or silhouette."""
        from sklearn.metrics import silhouette_score

        max_speakers = max_speakers or min(self.max_speakers, len(embeddings) - 1)
        max_speakers = max(2, min(max_speakers, len(embeddings) - 1))

        # Normalize embeddings
        scaler = StandardScaler()
        embeddings_scaled = scaler.fit_transform(embeddings)

        best_score = -1
        best_n = 2

        for n in range(2, max_speakers + 1):
            try:
                clustering = AgglomerativeClustering(
                    n_clusters=n,
                    metric='cosine',
                    linkage='average',
                )
                labels = clustering.fit_predict(embeddings_scaled)

                if len(set(labels)) > 1:
                    score = silhouette_score(embeddings_scaled, labels, metric='cosine')
                    if score > best_score:
                        best_score = score
                        best_n = n
            except Exception:
                continue

        return best_n

    def _cluster_embeddings(
        self,
        embeddings: np.ndarray,
        n_speakers: int,
    ) -> np.ndarray:
        """Cluster embeddings to assign speaker labels."""
        # Normalize embeddings
        scaler = StandardScaler()
        embeddings_scaled = scaler.fit_transform(embeddings)

        if self.clustering_method == ClusteringMethod.AGGLOMERATIVE:
            clustering = AgglomerativeClustering(
                n_clusters=n_speakers,
                metric='cosine',
                linkage='average',
            )
        elif self.clustering_method == ClusteringMethod.SPECTRAL:
            # Compute affinity matrix
            affinity = cosine_similarity(embeddings_scaled)
            affinity = (affinity + 1) / 2  # Scale to [0, 1]

            clustering = SpectralClustering(
                n_clusters=n_speakers,
                affinity='precomputed',
                random_state=42,
            )
            return clustering.fit_predict(affinity)
        elif self.clustering_method == ClusteringMethod.KMEANS:
            clustering = KMeans(
                n_clusters=n_speakers,
                random_state=42,
                n_init=10,
            )
        else:
            raise ValueError(f"Unknown clustering method: {self.clustering_method}")

        return clustering.fit_predict(embeddings_scaled)

    def _create_speaker_profiles(
        self,
        segments: List[SpeakerSegment],
        embeddings: np.ndarray,
        labels: np.ndarray,
    ) -> List[SpeakerProfile]:
        """Create speaker profiles from clustered segments."""
        unique_speakers = set(labels)
        profiles = []

        for speaker_id in unique_speakers:
            speaker_mask = labels == speaker_id
            speaker_embeddings = embeddings[speaker_mask]
            speaker_segments = [s for s, l in zip(segments, labels) if l == speaker_id]

            # Compute centroid embedding
            centroid = np.mean(speaker_embeddings, axis=0)

            profiles.append(SpeakerProfile(
                speaker_id=int(speaker_id),
                embedding=centroid,
                total_duration=sum(s.duration for s in speaker_segments),
                n_segments=len(speaker_segments),
            ))

        # Sort by total duration (main speaker first)
        profiles.sort(key=lambda x: x.total_duration, reverse=True)

        return profiles

    def identify_speaker(
        self,
        segment_signal: np.ndarray,
        known_profiles: List[SpeakerProfile],
        sample_rate: Optional[int] = None,
        threshold: float = 0.7,
    ) -> Tuple[Optional[int], float]:
        """
        Identify speaker from known profiles.

        Args:
            segment_signal: Audio segment to identify.
            known_profiles: List of known speaker profiles.
            sample_rate: Sample rate.
            threshold: Similarity threshold for identification.

        Returns:
            Tuple of (speaker_id, confidence). speaker_id is None if unknown.
        """
        sr = sample_rate or self.sample_rate
        embedding = self._extract_embedding(segment_signal, sr)

        best_match = None
        best_similarity = -1

        for profile in known_profiles:
            similarity = cosine_similarity(
                embedding.reshape(1, -1),
                profile.embedding.reshape(1, -1)
            )[0, 0]

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = profile.speaker_id

        if best_similarity >= threshold:
            return best_match, best_similarity
        else:
            return None, best_similarity

    def merge_short_segments(
        self,
        result: DiarizationResult,
        min_duration: float = 0.5,
    ) -> DiarizationResult:
        """
        Merge short segments with adjacent segments of same speaker.

        Args:
            result: Diarization result.
            min_duration: Minimum segment duration.

        Returns:
            DiarizationResult with merged segments.
        """
        if not result.segments:
            return result

        merged = []
        current = result.segments[0]

        for segment in result.segments[1:]:
            if (segment.speaker_id == current.speaker_id and
                segment.duration < min_duration):
                # Merge with current
                current = SpeakerSegment(
                    speaker_id=current.speaker_id,
                    start_time=current.start_time,
                    end_time=segment.end_time,
                    start_sample=current.start_sample,
                    end_sample=segment.end_sample,
                    confidence=(current.confidence + segment.confidence) / 2,
                    embedding=current.embedding,
                )
            else:
                merged.append(current)
                current = segment

        merged.append(current)

        return DiarizationResult(
            segments=merged,
            speakers=result.speakers,
            sample_rate=result.sample_rate,
            n_speakers=result.n_speakers,
        )

    def save_rttm(
        self,
        result: DiarizationResult,
        output_path: Union[str, Path],
        file_id: str = "audio",
    ) -> str:
        """
        Save diarization result in RTTM format.

        Args:
            result: Diarization result.
            output_path: Output file path.
            file_id: File identifier for RTTM.

        Returns:
            Path to saved file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for segment in result.segments:
                # RTTM format:
                # SPEAKER file_id channel start duration <NA> <NA> speaker_id <NA> <NA>
                line = (
                    f"SPEAKER {file_id} 1 {segment.start_time:.3f} "
                    f"{segment.duration:.3f} <NA> <NA> speaker_{segment.speaker_id} <NA> <NA>\n"
                )
                f.write(line)

        return str(output_path)
