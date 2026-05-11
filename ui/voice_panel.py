"""Voice-first assistant panel for NoteRemind."""
import os
import re
import math
import random
import tkinter as tk
import tkinter.messagebox as mb
import customtkinter as ctk
import threading

from services.audio_recorder import AudioRecorder, AUDIO_AVAILABLE
from services.speech_to_text import transcribe_audio
from services.intent_parser import parse_intent as claude_parse_intent
from services.local_whisper_service import current_model_size
from core.parser import parse_datetime
from core.notes import create_note
from core.reminders import create_reminder

CONFIDENCE_AUTO   = 0.85
CONFIDENCE_REVIEW = 0.60

_INTENT_LABELS = {
    "create_reminder":     "Create Reminder",
    "create_appointment":  "Create Appointment",
    "create_meeting_note": "Create Meeting Note",
    "search":              "Search",
    "update_reminder":     "Update Reminder",
    "unknown":             "Unknown",
}

_NUM_BARS  = 12
_BAR_W     = 12
_BAR_GAP   = 8
_CANVAS_H  = 52
_CANVAS_W  = _NUM_BARS * (_BAR_W + _BAR_GAP)


class VoicePanel(ctk.CTkFrame):
    def __init__(self, master, on_action=None, on_fill_reminder=None, on_fill_note=None):
        super().__init__(master, fg_color="transparent")
        self._recorder        = AudioRecorder()
        self._on_action       = on_action
        self._on_fill_reminder = on_fill_reminder
        self._on_fill_note    = on_fill_note
        self._last_action: dict | None = None
        self._last_transcription: str  = ""
        self._autosave_var = ctk.BooleanVar(value=False)
        self._pulse_step   = 0
        self._build()
        self._idle_pulse()

    # ── layout ────────────────────────────────────────────────────────────

    def _build(self):
        # Title
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(20, 2))
        ctk.CTkLabel(
            hdr, text="🎙  Voice Assistant",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            hdr,
            text='Say things like:  "Create a reminder for meeting with Yaseen tomorrow at 10 PM"',
            text_color="gray", font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(3, 0))

        # API status banner
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        banner = ctk.CTkFrame(self, fg_color="#1a1e2a", corner_radius=6)
        banner.pack(fill="x", padx=20, pady=(12, 0))
        ctk.CTkLabel(
            banner,
            text=("STT: local Whisper  ·  Parser: Claude API  ·  Audio stays on your device"
                  if has_key else
                  "⚠  ANTHROPIC_API_KEY missing — add it to .env.  Falling back to rule-based parser."),
            text_color="#5d8dbb" if has_key else "#e07b3c",
            font=ctk.CTkFont(size=11),
        ).pack(padx=12, pady=7, anchor="w")

        # Waveform canvas
        wave_wrap = ctk.CTkFrame(self, fg_color="transparent")
        wave_wrap.pack(pady=(18, 6))
        self._canvas = tk.Canvas(
            wave_wrap, width=_CANVAS_W, height=_CANVAS_H,
            bg="#1a1e2a", highlightthickness=0,
        )
        self._canvas.pack()
        self._bar_ids: list[tuple] = []
        for i in range(_NUM_BARS):
            x1 = i * (_BAR_W + _BAR_GAP) + 2
            x2 = x1 + _BAR_W
            bid = self._canvas.create_rectangle(
                x1, _CANVAS_H - 4, x2, _CANVAS_H, fill="#2d4a6b", width=0
            )
            self._bar_ids.append((bid, x1, x2))

        # Mic button — centred
        self._mic_btn = ctk.CTkButton(
            self, text="🎙  Start Recording",
            width=210, height=54,
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=27,
            command=self._toggle,
        )
        self._mic_btn.pack(pady=(2, 6))

        # Status line
        self._status = ctk.CTkLabel(
            self, text="Ready — click to speak",
            text_color="gray", font=ctk.CTkFont(size=12),
        )
        self._status.pack(pady=(0, 10))

        # Transcription preview
        ctk.CTkLabel(self, text="Transcription:", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(4, 2))
        self._preview = ctk.CTkTextbox(
            self, height=64, wrap="word", state="disabled",
            font=ctk.CTkFont(size=12),
        )
        self._preview.pack(fill="x", padx=20, pady=(0, 8))

        # Result panel — packed on demand
        self._result_panel = ctk.CTkFrame(self, corner_radius=8)

        # Auto-save toggle pinned to bottom
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=20, pady=(0, 16))
        ctk.CTkSwitch(
            bottom,
            text="Auto-save high-confidence voice commands",
            variable=self._autosave_var,
            font=ctk.CTkFont(size=11),
            onvalue=True, offvalue=False,
        ).pack(side="left")

    # ── recording ─────────────────────────────────────────────────────────

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
        self._hide_result()
        try:
            self._recorder.start()
        except Exception as exc:
            self._set_status(f"Microphone error: {exc}", "#e74c3c")
            return
        self._mic_btn.configure(
            text="⏹  Stop Recording", fg_color="#c0392b", hover_color="#922b21"
        )
        self._set_status("🔴  Listening… speak now", "#e74c3c")
        self._set_preview("")
        self._animate_bars()

    def _stop(self):
        self._mic_btn.configure(
            text="🎙  Start Recording",
            fg_color=["#3B8ED0", "#1F6AA5"],
            hover_color=["#36719F", "#144870"],
        )
        self._set_status("Processing transcription…", "gray")
        audio_path = self._recorder.stop()
        threading.Thread(target=self._pipeline, args=(audio_path,), daemon=True).start()

    # ── pipeline ──────────────────────────────────────────────────────────

    def _pipeline(self, audio_path: str):
        try:
            text = transcribe_audio(audio_path)
        except Exception as exc:
            self._ui(lambda: self._set_status(f"Transcription error: {exc}", "#e74c3c"))
            return
        finally:
            self._recorder.cleanup()

        if not text:
            self._ui(lambda: self._set_status("No speech detected. Try again.", "#e67e22"))
            return

        self._last_transcription = text
        self._ui(lambda: self._set_preview(text))

        if not os.environ.get("ANTHROPIC_API_KEY"):
            self._ui(lambda: self._set_status(
                "ANTHROPIC_API_KEY missing — using rule-based parser.", "#e74c3c"
            ))
            action = _rule_based_intent(text)
        else:
            self._ui(lambda: self._set_status("Parsing with Claude API…", "gray"))
            try:
                action = claude_parse_intent(text)
            except RuntimeError as exc:
                err = str(exc)
                self._ui(lambda e=err: self._set_status(e, "#e74c3c"))
                action = _rule_based_intent(text)
            except Exception:
                self._ui(lambda: self._set_status(
                    "Claude API error — using rule-based parser.", "#e67e22"
                ))
                action = _rule_based_intent(text)

        self._last_action = action
        self._ui(lambda: self._show_result(text, action))

    # ── result panel ──────────────────────────────────────────────────────

    def _show_result(self, transcription: str, action: dict):
        for w in self._result_panel.winfo_children():
            w.destroy()

        intent      = action.get("intent", "unknown")
        confidence  = float(action.get("confidence", 0.0))
        fields      = action.get("fields", {})
        missing     = action.get("missing_fields", [])
        is_dest     = (intent == "update_reminder" or
                       action.get("requires_confirmation", False))
        can_fill    = intent in ("create_reminder", "create_appointment", "create_meeting_note")

        intent_label = _INTENT_LABELS.get(intent, intent)
        conf_color   = ("#27ae60" if confidence >= CONFIDENCE_AUTO else
                        "#e67e22" if confidence >= CONFIDENCE_REVIEW else "#e74c3c")

        # Intent + confidence
        row = ctk.CTkFrame(self._result_panel, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(row, text=f"Detected: {intent_label}",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkLabel(row, text=f"  {confidence:.0%} confidence",
                     text_color=conf_color,
                     font=ctk.CTkFont(size=12)).pack(side="left")

        # Extracted fields
        parts: list[str] = []
        for k in ("title", "datetime", "date", "time", "description", "recurrence"):
            v = (fields.get(k) or "").strip()
            if v and v != "none":
                parts.append(f"{k}: {v}")
        if fields.get("participants"):
            parts.append("participants: " + ", ".join(fields["participants"]))
        if fields.get("tags"):
            parts.append("tags: " + ", ".join(fields["tags"]))
        if missing:
            parts.append("⚠ missing: " + ", ".join(missing))
        if parts:
            ctk.CTkLabel(
                self._result_panel,
                text="  " + "\n  ".join(parts),
                justify="left", text_color="#999999",
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=14, pady=(0, 6))

        # Guidance message
        if intent == "unknown" or confidence < CONFIDENCE_REVIEW:
            guide       = "Low confidence — please rephrase or type manually."
            guide_color = "#e74c3c"
        else:
            guide       = "I filled the form — please review before saving."
            guide_color = "#27ae60" if confidence >= CONFIDENCE_AUTO else "#e67e22"
        ctk.CTkLabel(
            self._result_panel, text=guide, text_color=guide_color,
            font=ctk.CTkFont(size=12), wraplength=500,
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Action buttons
        btn_row = ctk.CTkFrame(self._result_panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 14))

        if can_fill:
            ctk.CTkButton(
                btn_row, text="Insert into form", width=145,
                command=lambda: self._do_insert(intent, fields, transcription),
            ).pack(side="left", padx=(0, 8))

        if can_fill and not is_dest:
            ctk.CTkButton(
                btn_row, text="Save after review", width=145,
                fg_color="#1a7a3a", hover_color="#155c2b",
                command=lambda: self._do_save(intent, fields, transcription, action),
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Try again", width=90,
            fg_color="transparent", border_width=1,
            command=self._try_again,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Discard", width=80,
            fg_color="transparent", border_width=1, text_color="#e74c3c",
            command=self._discard,
        ).pack(side="left")

        self._result_panel.pack(fill="x", padx=20, pady=(0, 12))
        self._set_status(f"Parsed: {intent_label}", "#aaaaaa")

    def _hide_result(self):
        self._result_panel.pack_forget()

    # ── button actions ────────────────────────────────────────────────────

    def _do_insert(self, intent: str, fields: dict, transcription: str):
        self._hide_result()
        if intent in ("create_reminder", "create_appointment"):
            if self._on_fill_reminder:
                self._on_fill_reminder(fields)
                self._set_status(
                    "Filled the reminder form — review and click Create Reminder.", "#27ae60"
                )
            else:
                self._set_status("No reminder form available.", "#e74c3c")
        elif intent == "create_meeting_note":
            if self._on_fill_note:
                self._on_fill_note(fields, transcription)
                self._set_status("Filled the note form — review and click Save.", "#27ae60")
            else:
                self._set_status("No note form available.", "#e74c3c")

    def _do_save(self, intent: str, fields: dict, transcription: str, action: dict):
        confidence  = float(action.get("confidence", 0.0))
        is_dest     = (intent == "update_reminder" or
                       action.get("requires_confirmation", False))
        auto_on     = self._autosave_var.get()

        # Destructive actions always confirm; non-auto-save always confirms
        needs_confirm = is_dest or not auto_on or confidence < CONFIDENCE_AUTO
        if needs_confirm:
            summary = action.get("action_summary", intent)
            if not mb.askyesno(
                "Confirm Save",
                f"{summary}\n\nConfidence: {confidence:.0%}\n\nSave now?",
            ):
                return

        try:
            msg = self._execute(intent, fields, transcription)
        except Exception as exc:
            self._set_status(f"Error: {exc}", "#e74c3c")
            return

        self._set_status(f"Saved: {msg}", "#27ae60")
        self._hide_result()
        if self._on_action:
            self._on_action()

    def _try_again(self):
        self._hide_result()
        self._set_preview("")
        self._set_status("Ready — click to speak", "gray")

    def _discard(self):
        self._hide_result()
        self._set_preview("")
        self._set_status("Discarded.", "gray")

    # ── execution ─────────────────────────────────────────────────────────

    def _execute(self, intent: str, fields: dict, transcription: str) -> str:
        if intent in ("create_reminder", "create_appointment"):
            return self._make_reminder(fields, transcription)
        if intent == "create_meeting_note":
            return self._make_note(fields, transcription)
        raise ValueError(f"Intent '{intent}' is not yet supported.")

    def _make_reminder(self, fields: dict, transcription: str) -> str:
        title  = fields.get("title") or "Voice reminder"
        dt_str = (fields.get("datetime") or
                  f"{fields.get('date', '')} {fields.get('time', '')}".strip())
        due    = parse_datetime(dt_str) if dt_str else None
        if due is None:
            raise ValueError(
                f"Could not parse date/time from: \"{dt_str or 'nothing provided'}\""
            )
        recur = fields.get("recurrence", "none")
        if recur not in ("none", "daily", "weekly", "monthly", "yearly"):
            recur = "none"
        create_reminder(title, due, message=fields.get("description", ""),
                        recurrence_type=recur)
        return f'"{title}" — {due.strftime("%A, %b %d at %H:%M")}'

    def _make_note(self, fields: dict, transcription: str) -> str:
        description = fields.get("description") or transcription
        title       = fields.get("title") or _auto_title(description)
        tags        = ", ".join(fields.get("tags") or [])
        create_note(title, content=description, tags=tags, source_type="voice",
                    original_transcription=transcription, llm_intent="create_meeting_note")
        return f'Note: "{title}"'

    # ── animation ─────────────────────────────────────────────────────────

    def _idle_pulse(self):
        if not self.winfo_exists():
            return
        if not self._recorder.is_recording:
            self._pulse_step += 1
            color = "#2563eb" if (self._pulse_step // 4) % 2 == 0 else "#3B8ED0"
            try:
                self._mic_btn.configure(fg_color=color)
            except Exception:
                pass
        self.after(500, self._idle_pulse)

    def _animate_bars(self):
        if not self.winfo_exists():
            return
        if not self._recorder.is_recording:
            for bid, x1, x2 in self._bar_ids:
                self._canvas.coords(bid, x1, _CANVAS_H - 4, x2, _CANVAS_H)
                self._canvas.itemconfig(bid, fill="#2d4a6b")
            return
        level = self._recorder.current_level
        for bid, x1, x2 in self._bar_ids:
            noise = random.uniform(0.0, 0.4)
            h     = int(4 + min(level + noise, 1.0) * (_CANVAS_H - 6))
            h     = max(h, 4)
            inten = min(level + noise * 0.5, 1.0)
            r     = min(30  + int(inten * 120), 220)
            g     = min(100 + int(inten * 140), 240)
            b     = max(200 - int(inten * 60),  100)
            self._canvas.coords(bid, x1, _CANVAS_H - h, x2, _CANVAS_H)
            self._canvas.itemconfig(bid, fill=f"#{r:02x}{g:02x}{b:02x}")
        self.after(80, self._animate_bars)

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


# ── rule-based fallback ───────────────────────────────────────────────────────

def _rule_based_intent(text: str) -> dict:
    """Keyword-based parser used when Claude API is not available."""
    t = text.lower().strip()

    if any(w in t for w in ["remind", "reminder", "appointment", "schedule", "alert"]):
        intent = "create_reminder"
    elif any(w in t for w in ["note", "write", "jot", "record", "meeting note", "add a note"]):
        intent = "create_meeting_note"
    elif any(w in t for w in ["find", "search", "look for", "show me"]):
        intent = "search"
    else:
        intent = "unknown"

    title = ""
    patterns = [
        r"remind(?:er)?\s+(?:for|about|me(?:\s+to)?)\s+(.+?)(?:\s+(?:tomorrow|today|at\s+\d|next|in\s+\d)|[.,]|$)",
        r"(?:note|write(?:\s+down)?|jot)[:\s]+(.+?)(?:\s+(?:before|tomorrow|today|at\s+\d)|[.,]|$)",
        r"(?:schedule|appointment)\s+(?:for\s+)?(.+?)(?:\s+(?:tomorrow|today|at\s+\d|next|in\s+\d)|[.,]|$)",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            title = m.group(1).strip().title()
            break
    if not title:
        title = _auto_title(text)

    return {
        "intent": intent,
        "confidence": 0.70,
        "requires_confirmation": True,
        "fields": {
            "title": title, "description": text,
            "datetime": text, "date": "", "time": "",
            "participants": [], "tags": [],
            "priority": "normal", "recurrence": "none",
            "search_query": text if intent == "search" else "",
        },
        "action_summary": f"[Rule-based] {intent}: {title}",
        "missing_fields": [],
    }


def _auto_title(text: str, max_words: int = 6) -> str:
    words = text.split()
    title = " ".join(words[:max_words]).rstrip(".,;:")
    return title + ("…" if len(words) > max_words else "")
