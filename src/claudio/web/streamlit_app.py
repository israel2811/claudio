"""
Claudio Web Application.

Streamlit-based web interface for forensic audio analysis.
"""

import streamlit as st
import numpy as np
from pathlib import Path
import tempfile
import json
import io
import os
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def load_css():
    """Load custom CSS styling."""
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #89b4fa;
        text-align: center;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #a6adc8;
        text-align: center;
        margin-top: 0;
    }
    .metric-card {
        background-color: #313244;
        border-radius: 10px;
        padding: 15px;
        margin: 5px 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #89b4fa;
    }
    .metric-label {
        color: #a6adc8;
        font-size: 0.9rem;
    }
    .segment-card {
        background-color: #313244;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        border-left: 4px solid #89b4fa;
    }
    .stProgress > div > div > div > div {
        background-color: #89b4fa;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Claudio - Forensic Audio Analyzer",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    load_css()

    # Header
    st.markdown('<h1 class="main-header">🎵 CLAUDIO</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Forensic Audio Recovery & Analysis</p>', unsafe_allow_html=True)
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        st.subheader("Recovery Parameters")
        threshold_db = st.slider(
            "Detection Threshold (dB)",
            min_value=-80, max_value=-10, value=-35,
            help="Signals below this level will be targeted for recovery"
        )

        max_voices = st.slider(
            "Maximum Voices",
            min_value=1, max_value=50, value=30,
            help="Maximum number of distinct voices to detect"
        )

        st.subheader("Languages")
        languages = st.multiselect(
            "Transcription Languages",
            options=['es', 'en', 'fr', 'de', 'ru', 'pt', 'it', 'zh', 'ja', 'ko', 'ar', 'hi'],
            default=['es', 'en', 'fr', 'de', 'ru', 'pt'],
            help="Languages to try for transcription"
        )

        st.subheader("Options")
        aggressive_mode = st.checkbox("Aggressive Recovery", value=True)
        enable_transcription = st.checkbox("Enable Transcription", value=True)

        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        **Claudio** recovers and analyzes
        attenuated audio signals (<-35dB)
        using advanced phase coherence
        techniques.

        Features:
        - Voice recovery from silence
        - 30+ speaker detection
        - 10+ language support
        - Phase amplification
        """)

    # Main content
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("📁 Upload Audio")

        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'flac', 'ogg', 'm4a'],
            help="Supported formats: WAV, MP3, FLAC, OGG, M4A"
        )

        if uploaded_file:
            st.success(f"Loaded: {uploaded_file.name}")
            st.audio(uploaded_file, format=f'audio/{uploaded_file.type.split("/")[-1]}')

            # File info
            file_size = len(uploaded_file.getvalue()) / 1024 / 1024
            st.info(f"File size: {file_size:.2f} MB")

    with col2:
        st.header("🔬 Analysis")

        if uploaded_file:
            analysis_type = st.radio(
                "Select Analysis Type",
                ["Quick Scan", "Full Recovery"],
                horizontal=True
            )

            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                with st.spinner("Processing audio..."):
                    try:
                        result = run_analysis(
                            uploaded_file,
                            threshold_db,
                            max_voices,
                            languages,
                            aggressive_mode,
                            enable_transcription,
                            full_recovery=(analysis_type == "Full Recovery")
                        )

                        st.session_state['result'] = result
                        st.success("Analysis complete!")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        else:
            st.info("👆 Upload an audio file to begin analysis")

    # Results section
    st.markdown("---")

    if 'result' in st.session_state:
        result = st.session_state['result']
        display_results(result)


def run_analysis(uploaded_file, threshold_db, max_voices, languages, aggressive, transcribe, full_recovery):
    """Run analysis on uploaded file."""
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        from claudio.forensic.forensic_analyzer import ForensicAudioAnalyzer

        analyzer = ForensicAudioAnalyzer(
            target_threshold_db=threshold_db,
            max_voices=max_voices,
            aggressive_recovery=aggressive,
        )

        if full_recovery:
            with tempfile.TemporaryDirectory() as tmp_dir:
                result = analyzer.analyze(
                    tmp_path,
                    output_dir=tmp_dir,
                    transcribe=transcribe,
                    languages=languages,
                )

                # Read output files
                result_dict = {
                    'type': 'full',
                    'n_segments': len(result.detected_voice_segments),
                    'n_voices': result.n_voices_detected,
                    'total_duration': result.total_voice_duration,
                    'improvement_db': result.signal_improvement_db,
                    'noise_floor_db': result.noise_floor_db,
                    'segments': result.detected_voice_segments,
                    'transcriptions': result.transcriptions,
                    'processing_log': result.processing_log,
                    'recovered_signal': result.recovered_signal,
                    'sample_rate': result.sample_rate,
                }
        else:
            quick_result = analyzer.quick_analyze(tmp_path)
            result_dict = {
                'type': 'quick',
                **quick_result
            }

        return result_dict

    finally:
        os.unlink(tmp_path)


def display_results(result):
    """Display analysis results."""
    st.header("📊 Results")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    if result['type'] == 'full':
        with col1:
            st.metric("Voice Segments", result['n_segments'])
        with col2:
            st.metric("Distinct Voices", result['n_voices'])
        with col3:
            st.metric("Improvement", f"+{result['improvement_db']:.1f} dB")
        with col4:
            st.metric("Noise Floor", f"{result['noise_floor_db']:.1f} dB")
    else:
        with col1:
            st.metric("Segments Found", result.get('n_segments', 0))
        with col2:
            st.metric("Distinct Voices", result.get('n_distinct_voices', 0))
        with col3:
            st.metric("Attenuation", f"{result.get('estimated_attenuation_db', 0):.1f} dB")
        with col4:
            st.metric("Has Content", "Yes" if result.get('has_attenuated_content') else "No")

    # Tabs
    if result['type'] == 'full':
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Segments", "🗣️ Transcription", "📈 Recovered Audio", "📋 Log"
        ])

        with tab1:
            display_segments(result.get('segments', []))

        with tab2:
            display_transcription(result.get('transcriptions', {}))

        with tab3:
            display_audio(result.get('recovered_signal'), result.get('sample_rate'))

        with tab4:
            display_log(result.get('processing_log', []))

    else:
        display_segments(result.get('segments', []))


def display_segments(segments):
    """Display voice segments."""
    if not segments:
        st.info("No segments detected")
        return

    st.subheader(f"Detected Segments ({len(segments)})")

    for i, seg in enumerate(segments):
        with st.expander(f"Segment {i+1} - {seg.get('start_time', 0):.2f}s to {seg.get('end_time', 0):.2f}s"):
            cols = st.columns(4)
            with cols[0]:
                st.write(f"**Duration:** {seg.get('duration', 0):.2f}s")
            with cols[1]:
                st.write(f"**Level:** {seg.get('level_db', 0):.1f} dB")
            with cols[2]:
                st.write(f"**Voice Type:** {seg.get('voice_type', 'unknown')}")
            with cols[3]:
                st.write(f"**Confidence:** {seg.get('confidence', 0):.1%}")


def display_transcription(transcriptions):
    """Display transcriptions."""
    if not transcriptions:
        st.info("No transcriptions available")
        return

    st.subheader("Transcriptions")

    full_text = []
    for seg_id, trans in sorted(transcriptions.items()):
        lang = trans.get('language', '?')
        text = trans.get('text', '')
        conf = trans.get('confidence', 0)

        st.markdown(f"""
        <div class="segment-card">
            <strong>Segment {seg_id}</strong> [{lang}] (confidence: {conf:.1%})<br>
            {text}
        </div>
        """, unsafe_allow_html=True)

        full_text.append(text)

    # Export button
    st.markdown("---")
    full_transcript = "\n\n".join(full_text)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download as TXT",
            full_transcript,
            file_name="transcription.txt",
            mime="text/plain"
        )
    with col2:
        json_data = json.dumps(transcriptions, indent=2, ensure_ascii=False)
        st.download_button(
            "📥 Download as JSON",
            json_data,
            file_name="transcription.json",
            mime="application/json"
        )


def display_audio(signal, sample_rate):
    """Display recovered audio."""
    if signal is None or sample_rate is None:
        st.info("No recovered audio available")
        return

    st.subheader("Recovered Audio")

    # Convert to audio bytes
    try:
        import soundfile as sf

        # Normalize
        if np.max(np.abs(signal)) > 0:
            signal = signal / np.max(np.abs(signal)) * 0.9

        # Write to buffer
        buffer = io.BytesIO()
        sf.write(buffer, signal, sample_rate, format='WAV')
        buffer.seek(0)

        st.audio(buffer, format='audio/wav')

        # Download button
        st.download_button(
            "📥 Download Recovered Audio",
            buffer.getvalue(),
            file_name="recovered_audio.wav",
            mime="audio/wav"
        )

    except Exception as e:
        st.error(f"Could not render audio: {e}")


def display_log(log):
    """Display processing log."""
    st.subheader("Processing Log")

    if not log:
        st.info("No log entries")
        return

    log_text = "\n".join(log)
    st.code(log_text, language=None)


if __name__ == "__main__":
    main()
