"""
Claudio Desktop Application.

Full-featured GUI for forensic audio recovery and analysis.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
from pathlib import Path
from typing import Optional, Callable
import json
import os
import sys


class ClaudioApp:
    """
    Main Claudio Desktop Application.

    Provides a complete GUI for:
    - Loading audio files
    - Forensic audio recovery
    - Voice detection and separation
    - Multilingual transcription
    - Message extraction
    """

    def __init__(self):
        """Initialize the application."""
        self.root = tk.Tk()
        self.root.title("Claudio - Forensic Audio Analyzer")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # Set icon if available
        try:
            if sys.platform == 'win32':
                self.root.iconbitmap(default='')
        except Exception:
            pass

        # Configure style
        self.style = ttk.Style()
        self._configure_style()

        # State variables
        self.current_file: Optional[Path] = None
        self.processing = False
        self.result_queue = queue.Queue()

        # Build UI
        self._create_menu()
        self._create_main_layout()
        self._create_status_bar()

        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Check result queue periodically
        self._check_queue()

    def _configure_style(self):
        """Configure ttk styles."""
        self.style.theme_use('clam')

        # Colors
        bg_color = "#1e1e2e"
        fg_color = "#cdd6f4"
        accent_color = "#89b4fa"
        button_color = "#313244"

        self.root.configure(bg=bg_color)

        self.style.configure(".", background=bg_color, foreground=fg_color)
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        self.style.configure("TButton", background=button_color, foreground=fg_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground=accent_color)
        self.style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground=accent_color)
        self.style.configure("TProgressbar", troughcolor=button_color, background=accent_color)
        self.style.configure("TNotebook", background=bg_color)
        self.style.configure("TNotebook.Tab", background=button_color, foreground=fg_color, padding=[10, 5])

    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Audio...", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Export Results...", command=self._export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # Analysis menu
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)
        analysis_menu.add_command(label="Quick Scan", command=self._quick_scan)
        analysis_menu.add_command(label="Full Recovery", command=self._full_recovery)
        analysis_menu.add_separator()
        analysis_menu.add_command(label="Transcribe", command=self._transcribe)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self._open_file())

    def _create_main_layout(self):
        """Create main application layout."""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Controls
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        self._create_control_panel(left_panel)

        # Right panel - Results
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._create_results_panel(right_panel)

    def _create_control_panel(self, parent):
        """Create control panel."""
        # Title
        title_label = ttk.Label(parent, text="CLAUDIO", style="Title.TLabel")
        title_label.pack(pady=(0, 5))

        subtitle = ttk.Label(parent, text="Forensic Audio Analyzer")
        subtitle.pack(pady=(0, 20))

        # File section
        file_frame = ttk.LabelFrame(parent, text="Audio File", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_label = ttk.Label(file_frame, text="No file loaded", wraplength=250)
        self.file_label.pack(fill=tk.X)

        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.open_btn = ttk.Button(btn_frame, text="Open File", command=self._open_file)
        self.open_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        # Settings section
        settings_frame = ttk.LabelFrame(parent, text="Recovery Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Threshold
        ttk.Label(settings_frame, text="Detection Threshold (dB):").pack(anchor=tk.W)
        self.threshold_var = tk.StringVar(value="-35")
        threshold_entry = ttk.Entry(settings_frame, textvariable=self.threshold_var, width=10)
        threshold_entry.pack(anchor=tk.W, pady=(0, 10))

        # Max voices
        ttk.Label(settings_frame, text="Max Voices:").pack(anchor=tk.W)
        self.max_voices_var = tk.StringVar(value="30")
        voices_entry = ttk.Entry(settings_frame, textvariable=self.max_voices_var, width=10)
        voices_entry.pack(anchor=tk.W, pady=(0, 10))

        # Languages
        ttk.Label(settings_frame, text="Languages:").pack(anchor=tk.W)
        self.languages_var = tk.StringVar(value="es,en,fr,de,ru,pt")
        lang_entry = ttk.Entry(settings_frame, textvariable=self.languages_var)
        lang_entry.pack(fill=tk.X, pady=(0, 10))

        # Aggressive mode
        self.aggressive_var = tk.BooleanVar(value=True)
        aggressive_check = ttk.Checkbutton(
            settings_frame, text="Aggressive Recovery",
            variable=self.aggressive_var
        )
        aggressive_check.pack(anchor=tk.W)

        # Transcribe
        self.transcribe_var = tk.BooleanVar(value=True)
        transcribe_check = ttk.Checkbutton(
            settings_frame, text="Transcribe Messages",
            variable=self.transcribe_var
        )
        transcribe_check.pack(anchor=tk.W)

        # Action buttons
        action_frame = ttk.LabelFrame(parent, text="Actions", padding=10)
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.scan_btn = ttk.Button(
            action_frame, text="Quick Scan",
            command=self._quick_scan
        )
        self.scan_btn.pack(fill=tk.X, pady=(0, 5))

        self.recover_btn = ttk.Button(
            action_frame, text="Full Recovery",
            command=self._full_recovery
        )
        self.recover_btn.pack(fill=tk.X, pady=(0, 5))

        self.export_btn = ttk.Button(
            action_frame, text="Export Results",
            command=self._export_results
        )
        self.export_btn.pack(fill=tk.X)

        # Progress
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(10, 0))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var,
            mode='indeterminate'
        )
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(pady=(5, 0))

    def _create_results_panel(self, parent):
        """Create results panel with tabs."""
        # Notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Overview tab
        overview_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(overview_frame, text="Overview")
        self._create_overview_tab(overview_frame)

        # Segments tab
        segments_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(segments_frame, text="Voice Segments")
        self._create_segments_tab(segments_frame)

        # Transcription tab
        transcription_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(transcription_frame, text="Transcription")
        self._create_transcription_tab(transcription_frame)

        # Log tab
        log_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(log_frame, text="Processing Log")
        self._create_log_tab(log_frame)

    def _create_overview_tab(self, parent):
        """Create overview tab."""
        # Stats frame
        stats_frame = ttk.LabelFrame(parent, text="Analysis Results", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        # Stats grid
        self.stats_labels = {}
        stats = [
            ("file_name", "File:"),
            ("duration", "Duration:"),
            ("n_segments", "Voice Segments:"),
            ("n_voices", "Distinct Voices:"),
            ("noise_floor", "Noise Floor:"),
            ("improvement", "Signal Improvement:"),
            ("total_words", "Words Extracted:"),
            ("languages", "Languages:"),
        ]

        for i, (key, label) in enumerate(stats):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(stats_frame, text=label).grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            self.stats_labels[key] = ttk.Label(stats_frame, text="-")
            self.stats_labels[key].grid(row=row, column=col + 1, sticky=tk.W, padx=5, pady=2)

        # Summary
        summary_frame = ttk.LabelFrame(parent, text="Summary", padding=10)
        summary_frame.pack(fill=tk.BOTH, expand=True)

        self.summary_text = scrolledtext.ScrolledText(
            summary_frame, wrap=tk.WORD, height=10,
            bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4"
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True)

    def _create_segments_tab(self, parent):
        """Create segments tab."""
        # Treeview for segments
        columns = ("ID", "Start", "End", "Duration", "Level", "Voice", "Confidence")

        self.segments_tree = ttk.Treeview(parent, columns=columns, show="headings")

        for col in columns:
            self.segments_tree.heading(col, text=col)
            self.segments_tree.column(col, width=80)

        # Scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.segments_tree.yview)
        self.segments_tree.configure(yscrollcommand=scrollbar.set)

        self.segments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_transcription_tab(self, parent):
        """Create transcription tab."""
        self.transcription_text = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD,
            bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
            font=("Consolas", 11)
        )
        self.transcription_text.pack(fill=tk.BOTH, expand=True)

    def _create_log_tab(self, parent):
        """Create log tab."""
        self.log_text = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD,
            bg="#1e1e2e", fg="#94e2d5", insertbackground="#94e2d5",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_status_bar(self):
        """Create status bar."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(status_frame, text="Ready", padding=5)
        self.status_label.pack(side=tk.LEFT)

        version_label = ttk.Label(status_frame, text="v1.0.0", padding=5)
        version_label.pack(side=tk.RIGHT)

    def _open_file(self):
        """Open audio file dialog."""
        filetypes = [
            ("Audio Files", "*.wav *.mp3 *.flac *.ogg *.m4a *.aac"),
            ("WAV Files", "*.wav"),
            ("MP3 Files", "*.mp3"),
            ("All Files", "*.*"),
        ]

        filepath = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=filetypes
        )

        if filepath:
            self.current_file = Path(filepath)
            self.file_label.config(text=self.current_file.name)
            self._log_message(f"Loaded: {self.current_file}")
            self._update_status(f"Loaded: {self.current_file.name}")

    def _quick_scan(self):
        """Perform quick scan."""
        if not self.current_file:
            messagebox.showwarning("No File", "Please load an audio file first.")
            return

        if self.processing:
            return

        self._start_processing("Quick scan...")
        threading.Thread(target=self._run_quick_scan, daemon=True).start()

    def _run_quick_scan(self):
        """Run quick scan in background."""
        try:
            from claudio.forensic.forensic_analyzer import ForensicAudioAnalyzer

            analyzer = ForensicAudioAnalyzer(
                target_threshold_db=float(self.threshold_var.get()),
                max_voices=int(self.max_voices_var.get()),
            )

            result = analyzer.quick_analyze(str(self.current_file))
            self.result_queue.put(("quick_scan", result))

        except Exception as e:
            self.result_queue.put(("error", str(e)))

    def _full_recovery(self):
        """Perform full recovery."""
        if not self.current_file:
            messagebox.showwarning("No File", "Please load an audio file first.")
            return

        if self.processing:
            return

        # Select output directory
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return

        self._start_processing("Full recovery...")
        threading.Thread(
            target=self._run_full_recovery,
            args=(output_dir,),
            daemon=True
        ).start()

    def _run_full_recovery(self, output_dir):
        """Run full recovery in background."""
        try:
            from claudio.forensic.forensic_analyzer import ForensicAudioAnalyzer

            languages = [l.strip() for l in self.languages_var.get().split(',')]

            analyzer = ForensicAudioAnalyzer(
                target_threshold_db=float(self.threshold_var.get()),
                max_voices=int(self.max_voices_var.get()),
                aggressive_recovery=self.aggressive_var.get(),
            )

            result = analyzer.analyze(
                str(self.current_file),
                output_dir=output_dir,
                transcribe=self.transcribe_var.get(),
                languages=languages,
            )

            self.result_queue.put(("full_recovery", result))

        except Exception as e:
            import traceback
            self.result_queue.put(("error", f"{str(e)}\n{traceback.format_exc()}"))

    def _transcribe(self):
        """Transcribe current file."""
        if not self.current_file:
            messagebox.showwarning("No File", "Please load an audio file first.")
            return

        if self.processing:
            return

        self._start_processing("Transcribing...")
        threading.Thread(target=self._run_transcribe, daemon=True).start()

    def _run_transcribe(self):
        """Run transcription in background."""
        try:
            from claudio.transcription.transcriber import MultilingualTranscriber

            languages = [l.strip() for l in self.languages_var.get().split(',')]

            transcriber = MultilingualTranscriber()
            result = transcriber.transcribe(
                str(self.current_file),
                language=languages[0] if languages else None,
            )

            self.result_queue.put(("transcribe", result))

        except Exception as e:
            self.result_queue.put(("error", str(e)))

    def _export_results(self):
        """Export results to file."""
        filetypes = [
            ("JSON Files", "*.json"),
            ("Text Files", "*.txt"),
            ("All Files", "*.*"),
        ]

        filepath = filedialog.asksaveasfilename(
            title="Export Results",
            filetypes=filetypes,
            defaultextension=".json"
        )

        if filepath:
            # Get current content
            content = self.transcription_text.get("1.0", tk.END)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self._update_status(f"Exported to: {filepath}")

    def _start_processing(self, message: str):
        """Start processing mode."""
        self.processing = True
        self.progress_bar.start(10)
        self.progress_label.config(text=message)
        self._update_status(message)

        # Disable buttons
        self.scan_btn.config(state=tk.DISABLED)
        self.recover_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)

    def _stop_processing(self):
        """Stop processing mode."""
        self.processing = False
        self.progress_bar.stop()
        self.progress_var.set(0)
        self.progress_label.config(text="Ready")

        # Enable buttons
        self.scan_btn.config(state=tk.NORMAL)
        self.recover_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.NORMAL)

    def _check_queue(self):
        """Check result queue for updates."""
        try:
            while True:
                result_type, result = self.result_queue.get_nowait()

                if result_type == "error":
                    self._stop_processing()
                    messagebox.showerror("Error", result)
                    self._log_message(f"ERROR: {result}")

                elif result_type == "quick_scan":
                    self._stop_processing()
                    self._display_quick_scan(result)

                elif result_type == "full_recovery":
                    self._stop_processing()
                    self._display_full_recovery(result)

                elif result_type == "transcribe":
                    self._stop_processing()
                    self._display_transcription(result)

        except queue.Empty:
            pass

        self.root.after(100, self._check_queue)

    def _display_quick_scan(self, result):
        """Display quick scan results."""
        self.stats_labels["file_name"].config(text=self.current_file.name if self.current_file else "-")
        self.stats_labels["n_segments"].config(text=str(result.get('n_segments', 0)))
        self.stats_labels["n_voices"].config(text=str(result.get('n_distinct_voices', 0)))
        self.stats_labels["noise_floor"].config(text=f"{result.get('noise_floor_db', 0):.1f} dB")

        has_content = result.get('has_attenuated_content', False)

        summary = f"Quick Scan Results\n"
        summary += "=" * 40 + "\n\n"
        summary += f"Attenuated content detected: {'Yes' if has_content else 'No'}\n"
        summary += f"Number of segments: {result.get('n_segments', 0)}\n"
        summary += f"Distinct voices: {result.get('n_distinct_voices', 0)}\n"
        summary += f"Noise floor: {result.get('noise_floor_db', 0):.1f} dB\n"
        summary += f"Estimated attenuation: {result.get('estimated_attenuation_db', 0):.1f} dB\n"

        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", summary)

        # Clear and populate segments
        for item in self.segments_tree.get_children():
            self.segments_tree.delete(item)

        for i, seg in enumerate(result.get('segments', [])):
            self.segments_tree.insert("", tk.END, values=(
                i,
                f"{seg.get('start', 0):.2f}s",
                f"{seg.get('end', 0):.2f}s",
                f"{seg.get('end', 0) - seg.get('start', 0):.2f}s",
                f"{seg.get('level_db', 0):.1f} dB",
                seg.get('voice_type', '-'),
                "-"
            ))

        self._update_status("Quick scan complete")
        self._log_message("Quick scan completed successfully")

    def _display_full_recovery(self, result):
        """Display full recovery results."""
        self.stats_labels["file_name"].config(text=self.current_file.name if self.current_file else "-")
        self.stats_labels["duration"].config(text=f"{len(result.original_signal)/result.sample_rate:.2f}s")
        self.stats_labels["n_segments"].config(text=str(len(result.detected_voice_segments)))
        self.stats_labels["n_voices"].config(text=str(result.n_voices_detected))
        self.stats_labels["noise_floor"].config(text=f"{result.noise_floor_db:.1f} dB")
        self.stats_labels["improvement"].config(text=f"+{result.signal_improvement_db:.1f} dB")

        # Summary
        summary = "Full Recovery Results\n"
        summary += "=" * 40 + "\n\n"
        summary += f"Voice segments found: {len(result.detected_voice_segments)}\n"
        summary += f"Distinct voices: {result.n_voices_detected}\n"
        summary += f"Total voice duration: {result.total_voice_duration:.2f}s\n"
        summary += f"Signal improvement: +{result.signal_improvement_db:.1f} dB\n"
        summary += f"Gain applied: +{result.total_gain_applied_db:.1f} dB\n"

        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", summary)

        # Segments
        for item in self.segments_tree.get_children():
            self.segments_tree.delete(item)

        for seg in result.detected_voice_segments:
            self.segments_tree.insert("", tk.END, values=(
                seg.get('id', '-'),
                f"{seg.get('start_time', 0):.2f}s",
                f"{seg.get('end_time', 0):.2f}s",
                f"{seg.get('duration', 0):.2f}s",
                f"{seg.get('level_db', 0):.1f} dB",
                seg.get('voice_type', '-'),
                f"{seg.get('confidence', 0):.1%}"
            ))

        # Transcriptions
        self.transcription_text.delete("1.0", tk.END)

        if result.transcriptions:
            trans_text = "TRANSCRIPTION RESULTS\n"
            trans_text += "=" * 50 + "\n\n"

            for seg_id, trans in sorted(result.transcriptions.items()):
                trans_text += f"[Segment {seg_id}] ({trans.get('language', '?')})\n"
                trans_text += f"{trans.get('text', '')}\n"
                trans_text += "-" * 30 + "\n\n"

            self.transcription_text.insert("1.0", trans_text)

            # Update stats
            total_words = sum(len(t.get('text', '').split()) for t in result.transcriptions.values())
            languages = list(set(t.get('language', '') for t in result.transcriptions.values()))

            self.stats_labels["total_words"].config(text=str(total_words))
            self.stats_labels["languages"].config(text=", ".join(languages))

        # Log
        self.log_text.delete("1.0", tk.END)
        for msg in result.processing_log:
            self.log_text.insert(tk.END, msg + "\n")

        self._update_status("Full recovery complete")
        self._log_message("Full recovery completed successfully")

    def _display_transcription(self, result):
        """Display transcription results."""
        self.transcription_text.delete("1.0", tk.END)

        text = f"TRANSCRIPTION\n"
        text += f"Language: {result.language}\n"
        text += f"Duration: {result.duration:.2f}s\n"
        text += "=" * 50 + "\n\n"
        text += result.text

        self.transcription_text.insert("1.0", text)

        self._update_status("Transcription complete")

    def _log_message(self, message: str):
        """Add message to log."""
        self.log_text.insert(tk.END, f"[LOG] {message}\n")
        self.log_text.see(tk.END)

    def _update_status(self, message: str):
        """Update status bar."""
        self.status_label.config(text=message)

    def _show_about(self):
        """Show about dialog."""
        about_text = """
Claudio - Forensic Audio Analyzer
Version 1.0.0

Advanced audio analysis tool for:
• Recovering attenuated voices (<-35dB)
• Blind source separation
• Speaker diarization (30+ voices)
• Multilingual transcription (10+ languages)
• Phase coherence amplification

© 2024 Claudio Project
        """
        messagebox.showinfo("About Claudio", about_text.strip())

    def _on_close(self):
        """Handle window close."""
        if self.processing:
            if not messagebox.askyesno("Processing", "Analysis in progress. Exit anyway?"):
                return

        self.root.destroy()

    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    """Entry point for GUI application."""
    app = ClaudioApp()
    app.run()


if __name__ == "__main__":
    main()
