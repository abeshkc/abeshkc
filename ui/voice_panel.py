import tkinter.messagebox as mb
import customtkinter as ctk
import threading

from services.audio_recorder import AudioRecorder, AUDIO_AVAILABLE
from services.speech_to_text import transcribe_audio
from services.intent_parser import parse_intent
from core.parser import parse_datetime
from core.notes import create_note
from core.reminders import create_reminder

CONFIDENCE_AUTO = 0.85    # auto-save without confirmation
CONFIDENCE_REVIEW = 0.60  # fill form and ask


class VoicePanel(ctk.CTkFrame):
    def __init__(self, master, on_action=None):
        super().__init__(master, fg_color="transparent")
        self._recorder = AudioRecorder()
        self._on_action = on_action  # called after any successful action
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Voice Input", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 6))

        # Privacy notice
        notice = ctk.CTkFrame(self, fg_color="#2a2a18", corner_radius=6)
        notice.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(
            notice,
            text="Audio is sent to OpenAI Whisper.  Transcribed text is sent to Claude API.",
            text_color="#ccaa00",
            font=ctk.CTkFont(size=11),
        ).pack(padx=12, pady=8)

        # Mic button + status
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 10))

        self._mic_btn = ctk.CTkButton(
            btn_row,
            text="  Start Recording",
            width=180,
            height=42,
            command=self._toggle,
        )
        self._mic_btn.pack(side="left")

        self._status = ctk.CTkLabel(btn_row, text="", text_color="gray", wraplength=420)
        self._status.pack(side="left", padx=(14, 0))

        # Transcription preview
        ctk.CTkLabel(self, text="Transcription:").pack(anchor="w", padx=16, pady=(4, 2))
        self._preview = ctk.CTkTextbox(self, height=64, wrap="word", state="disabled")
        self._preview.pack(fill="x", padx=16, pady=(0, 10))

        # Action result
        self._result_box = ctk.CTkFrame(self, corner_radius=6)
        self._result_box.pack(fill="x", padx=16, pady=(0, 16))
        self._result_lbl = ctk.CTkLabel(
            self._result_box, text="", wraplength=520, justify="left"
        )
        self._result_lbl.pack(anchor="w", padx=12, pady=10)

    # ── recording ────────────────────────────────────────────────────────

    def _toggle(self):
        if not AUDIO_AVAILABLE:
            mb.showerror(
                "Missing dependency",
                "Install audio packages:\n\npip install sounddevice scipy numpy",
            )
            return
        if self._recorder.is_recording:
            self._stop()
        else:
            self._start()

    def _start(self):
        try:
            self._recorder.start()
        except Exception as exc:
            self._set_status(f"Microphone error: {exc}", "#e74c3c")
            return
        self._mic_btn.configure(
            text="  Stop Recording", fg_color="#c0392b", hover_color="#922b21"
        )
        self._set_status("Recording…", "#e74c3c")
        self._set_preview("")
        self._set_result("")

    def _stop(self):
        self._mic_btn.configure(
            text="  Start Recording",
            fg_color=["#3B8ED0", "#1F6AA5"],
            hover_color=["#36719F", "#144870"],
        )
        self._set_status("Transcribing…", "gray")
        audio_path = self._recorder.stop()
        threading.Thread(target=self._pipeline, args=(audio_path,), daemon=True).start()

    # ── pipeline ─────────────────────────────────────────────────────────

    def _pipeline(self, audio_path: str):
        # 1. Whisper
        try:
            text = transcribe_audio(audio_path)
        except Exception as exc:
            self._ui(lambda: self._set_status(f"Transcription error: {exc}", "#e74c3c"))
            return
        finally:
            self._recorder.cleanup()

        if not text:
            self._ui(lambda: self._set_status("No speech detected.", "#e74c3c"))
            return

        self._ui(lambda: self._set_preview(text))
        self._ui(lambda: self._set_status("Parsing intent with Claude…", "gray"))

        # 2. Claude intent
        try:
            action = parse_intent(text)
        except Exception as exc:
            self._ui(lambda: self._set_status(f"Claude error: {exc}", "#e74c3c"))
            return

        self._ui(lambda: self._dispatch(text, action))

    def _dispatch(self, transcription: str, action: dict):
        confidence = float(action.get("confidence", 0.0))
        intent = action.get("intent", "unknown")
        fields = action.get("fields", {})
        summary = action.get("action_summary", intent)

        if intent == "unknown" or confidence < CONFIDENCE_REVIEW:
            self._set_status(
                f"Low confidence ({confidence:.0%}) — please act manually.",
                "#e67e22",
            )
            self._set_result(
                f'Heard: "{transcription}"\nIntent: {intent} ({confidence:.0%}) — too uncertain to act.'
            )
            return

        if intent == "search":
            query = fields.get("search_query") or transcription
            self._set_result(f'Search: "{query}"\nSwitch to the Notes tab and type that in the search box.')
            self._set_status("Voice search — use Notes tab.", "#e67e22")
            return

        needs_confirm = (
            action.get("requires_confirmation", False)
            or confidence < CONFIDENCE_AUTO
        )

        if needs_confirm:
            ok = mb.askyesno(
                "Confirm Voice Action",
                f"{summary}\n\nConfidence: {confidence:.0%}\n\nProceed?",
            )
            if not ok:
                self._set_status("Cancelled.", "gray")
                return

        try:
            msg = self._execute(intent, fields, transcription)
        except Exception as exc:
            self._set_status(f"Error: {exc}", "#e74c3c")
            return

        self._set_status(f"Done: {summary}", "#27ae60")
        self._set_result(msg)
        if self._on_action:
            self._on_action()

    def _execute(self, intent: str, fields: dict, transcription: str) -> str:
        if intent in ("create_reminder", "create_appointment"):
            return self._make_reminder(fields, transcription)
        if intent == "create_meeting_note":
            return self._make_note(fields, transcription)
        raise ValueError(f"Intent '{intent}' is not yet supported.")

    def _make_reminder(self, fields: dict, transcription: str) -> str:
        title = fields.get("title") or "Voice reminder"
        dt_str = (
            fields.get("datetime")
            or f"{fields.get('date', '')} {fields.get('time', '')}".strip()
        )
        due = parse_datetime(dt_str) if dt_str else None
        if due is None:
            raise ValueError(
                f"Could not parse date/time from: \"{dt_str or 'nothing provided'}\""
            )
        recur = fields.get("recurrence", "none")
        if recur not in ("none", "daily", "weekly", "monthly", "yearly"):
            recur = "none"
        create_reminder(
            title,
            due,
            message=fields.get("description", ""),
            recurrence_type=recur,
        )
        return f'Created reminder: "{title}" — {due.strftime("%A, %b %d at %H:%M")}'

    def _make_note(self, fields: dict, transcription: str) -> str:
        description = fields.get("description") or transcription
        title = fields.get("title") or _auto_title(description)
        tags = ", ".join(fields.get("tags") or [])
        create_note(
            title,
            content=description,
            tags=tags,
            source_type="voice",
            original_transcription=transcription,
            llm_intent="create_meeting_note",
        )
        return f'Created note: "{title}"'

    # ── helpers ───────────────────────────────────────────────────────────

    def _ui(self, fn):
        self.after(0, fn)

    def _set_status(self, msg: str, color: str = "gray"):
        self._status.configure(text=msg, text_color=color)

    def _set_preview(self, text: str):
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        if text:
            self._preview.insert("1.0", text)
        self._preview.configure(state="disabled")

    def _set_result(self, text: str):
        self._result_lbl.configure(text=text)


def _auto_title(text: str, max_words: int = 6) -> str:
    words = text.split()
    title = " ".join(words[:max_words]).rstrip(".,;:")
    return title + ("…" if len(words) > max_words else "")
