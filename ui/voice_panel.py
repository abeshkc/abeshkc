"""Voice-first assistant panel for Aria."""
import os
import re
import tkinter as tk
import tkinter.messagebox as mb
import customtkinter as ctk
import threading
import random

from services.audio_recorder import AudioRecorder, AUDIO_AVAILABLE
from services.speech_to_text import transcribe_audio
from services.intent_parser import parse_intent as claude_parse_intent
from core.parser import parse_datetime
from core.notes import create_note, IMPORTANCE_LEVELS
from core.reminders import create_reminder

CONFIDENCE_AUTO   = 0.85
CONFIDENCE_REVIEW = 0.60

_IMP_COLORS = {
    "Low": "#777777", "Normal": "#aaaaaa", "High": "#e67e22", "Urgent": "#e74c3c"
}
_INTENT_LABELS = {
    "create_reminder":     "Reminder",
    "create_appointment":  "Appointment",
    "create_meeting_note": "Meeting Note",
    "create_note":         "Note",
    "search":              "Search",
    "update_reminder":     "Update Reminder",
    "unknown":             "Unknown",
}

# Canvas mic dimensions
_CS    = 110   # canvas size (square)
_CX    = _CY = 55   # centre
_BR    = 38    # base circle radius

# Waveform bar settings
_NUM_BARS = 12
_BAR_W    = 12
_BAR_GAP  = 8
_CAN_H    = 52
_CAN_W    = _NUM_BARS * (_BAR_W + _BAR_GAP)


# ── simple tooltip ────────────────────────────────────────────────────────────

class _ToolTip:
    def __init__(self, widget, text: str):
        self._win = None
        widget.bind("<Enter>", lambda e: self._show(e, text))
        widget.bind("<Leave>", lambda e: self._hide())

    def _show(self, event, text):
        x = event.widget.winfo_rootx() + 14
        y = event.widget.winfo_rooty() + event.widget.winfo_height() + 4
        self._win = tk.Toplevel()
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(f"+{x}+{y}")
        tk.Label(self._win, text=text, bg="#1e1e2e", fg="#cccccc",
                 relief="flat", bd=1, padx=6, pady=3,
                 font=("Segoe UI", 10)).pack()

    def _hide(self):
        if self._win:
            self._win.destroy()
            self._win = None


# ── main panel ────────────────────────────────────────────────────────────────

class VoicePanel(ctk.CTkFrame):
    def __init__(self, master, on_action=None, on_fill_reminder=None, on_fill_note=None):
        super().__init__(master, fg_color="transparent")
        self._recorder         = AudioRecorder()
        self._on_action        = on_action
        self._on_fill_reminder = on_fill_reminder
        self._on_fill_note     = on_fill_note
        self._last_action: dict | None = None
        self._last_transcription: str  = ""
        self._autosave_var = ctk.BooleanVar(value=False)
        self._mic_state    = "idle"    # idle | recording | processing
        self._pulse_step   = 0
        self._ring_phase   = 0
        self._arc_angle    = 0
        self._build()
        self._animate_mic()

    # ── layout ────────────────────────────────────────────────────────────

    def _build(self):
        # ── App name + subtitle ──
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(20, 2))
        ctk.CTkLabel(
            hdr, text="✦  Aria",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#3B8ED0",
        ).pack(anchor="w")
        ctk.CTkLabel(
            hdr, text="Your Personal Organizer",
            text_color="#5d8dbb", font=ctk.CTkFont(size=14),
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            hdr,
            text='e.g. "Urgent reminder — meeting with Yaseen tomorrow at 10 PM"',
            text_color="gray", font=ctk.CTkFont(size=12),
        ).pack(anchor="w", pady=(4, 0))

        # ── Status banner ──
        has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        banner  = ctk.CTkFrame(self, fg_color="#1a1e2a", corner_radius=6)
        banner.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(
            banner,
            text=("🎤 Speech recognition: local Whisper  ·  🤖 Understanding: Claude AI"
                  if has_key else
                  "⚠  ANTHROPIC_API_KEY missing — add it to .env.  Rule-based fallback active."),
            text_color="#5d8dbb" if has_key else "#e07b3c",
            font=ctk.CTkFont(size=12),
        ).pack(padx=12, pady=7, anchor="w")

        # ── Mic icon canvas ──
        mic_outer = ctk.CTkFrame(self, fg_color="#1a1e2a", corner_radius=10)
        mic_outer.pack(pady=(18, 4))

        self._mic_canvas = tk.Canvas(
            mic_outer, width=_CS, height=_CS,
            bg="#1a1e2a", highlightthickness=0, cursor="hand2",
        )
        self._mic_canvas.pack(padx=16, pady=16)
        self._mic_canvas.bind("<Button-1>", lambda e: self._toggle())

        # Draw elements back-to-front
        # 3 expanding rings (recording)
        self._ring_ids = []
        for _ in range(3):
            rid = self._mic_canvas.create_oval(0, 0, 0, 0, outline="#e74c3c", width=2)
            self._ring_ids.append(rid)
        # Processing arc
        m = _CX - _BR - 10
        self._proc_arc = self._mic_canvas.create_arc(
            m, m, _CS - m, _CS - m,
            start=0, extent=110, outline="#3B8ED0", width=3, style="arc",
        )
        self._mic_canvas.itemconfig(self._proc_arc, state="hidden")
        # Base circle
        self._mic_bg = self._mic_canvas.create_oval(
            _CX - _BR, _CY - _BR, _CX + _BR, _CY + _BR,
            fill="#2563eb", outline="", width=0,
        )
        # Mic emoji
        self._mic_label = self._mic_canvas.create_text(
            _CX, _CY, text="🎙", font=("Segoe UI Emoji", 26),
        )
        _ToolTip(self._mic_canvas, "Press to start speaking")

        # ── Waveform bars ──
        wave_wrap = ctk.CTkFrame(self, fg_color="transparent")
        wave_wrap.pack(pady=(4, 6))
        self._wave_canvas = tk.Canvas(
            wave_wrap, width=_CAN_W, height=_CAN_H,
            bg="#1a1e2a", highlightthickness=0,
        )
        self._wave_canvas.pack()
        self._bar_ids: list[tuple] = []
        for i in range(_NUM_BARS):
            x1  = i * (_BAR_W + _BAR_GAP) + 2
            x2  = x1 + _BAR_W
            bid = self._wave_canvas.create_rectangle(
                x1, _CAN_H - 4, x2, _CAN_H, fill="#2d4a6b", width=0
            )
            self._bar_ids.append((bid, x1, x2))

        # ── Progress bar (hidden until processing) ──
        self._progress = ctk.CTkProgressBar(self, width=300, mode="indeterminate")

        # ── Status label ──
        self._status = ctk.CTkLabel(
            self, text="Ready — press the mic to speak",
            text_color="gray", font=ctk.CTkFont(size=13),
        )
        self._status.pack(pady=(0, 10))

        # ── Transcription preview ──
        ctk.CTkLabel(self, text="Transcription:", anchor="w",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=20, pady=(4, 2))
        self._preview = ctk.CTkTextbox(
            self, height=62, wrap="word", state="disabled",
            font=ctk.CTkFont(size=13),
        )
        self._preview.pack(fill="x", padx=20, pady=(0, 8))

        # ── Result panel (packed on demand) ──
        self._result_panel = ctk.CTkFrame(self, corner_radius=8)

        # ── Auto-save toggle ──
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=20, pady=(0, 16))
        ctk.CTkSwitch(
            bottom,
            text="Auto-save high-confidence voice commands",
            variable=self._autosave_var,
            font=ctk.CTkFont(size=12),
            onvalue=True, offvalue=False,
        ).pack(side="left")

    # ── recording ─────────────────────────────────────────────────────────

    def _toggle(self):
        if not AUDIO_AVAILABLE:
            mb.showerror("Missing dependency",
                         "Install audio packages:\n\npip install sounddevice scipy numpy")
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
        self._mic_state = "recording"
        self._set_status("Listening… speak now", "#e74c3c")
        self._set_preview("")
        self._animate_bars()

    def _stop(self):
        self._mic_state = "processing"
        self._set_status("Transcribing with local Whisper…", "gray")
        self._progress.pack(pady=(0, 6))
        self._progress.start()
        audio_path = self._recorder.stop()
        threading.Thread(target=self._pipeline, args=(audio_path,), daemon=True).start()

    def _re_enable_mic(self):
        self._progress.stop()
        self._progress.pack_forget()
        self._mic_state = "idle"

    # ── pipeline ──────────────────────────────────────────────────────────

    def _pipeline(self, audio_path: str):
        try:
            text = transcribe_audio(audio_path)
        except Exception as exc:
            self._ui(lambda: (
                self._set_status(f"Transcription error: {exc}", "#e74c3c"),
                self._re_enable_mic(),
            ))
            return
        finally:
            self._recorder.cleanup()

        if not text:
            self._ui(lambda: (
                self._set_status("No speech detected. Try again.", "#e67e22"),
                self._re_enable_mic(),
            ))
            return

        self._last_transcription = text
        self._ui(lambda: self._set_preview(text))

        if not os.environ.get("ANTHROPIC_API_KEY"):
            self._ui(lambda: self._set_status(
                "API key missing — using rule-based parser.", "#e74c3c"))
            action = _rule_based_intent(text)
        else:
            self._ui(lambda: self._set_status(
                "Understanding your request with Claude AI…", "gray"))
            try:
                action = claude_parse_intent(text)
            except RuntimeError as exc:
                err = str(exc)
                self._ui(lambda e=err: self._set_status(e, "#e74c3c"))
                action = _rule_based_intent(text)
            except Exception:
                self._ui(lambda: self._set_status(
                    "Claude error — using rule-based parser.", "#e67e22"))
                action = _rule_based_intent(text)

        self._last_action = action
        self._ui(lambda: self._set_status("Filling preview…", "gray"))
        self._ui(lambda: (self._re_enable_mic(), self._show_result(text, action)))

    # ── result panel ──────────────────────────────────────────────────────

    def _show_result(self, transcription: str, action: dict):
        for w in self._result_panel.winfo_children():
            w.destroy()

        intent     = action.get("intent", "unknown")
        confidence = float(action.get("confidence", 0.0))
        fields     = action.get("fields", {})
        missing    = action.get("missing_fields", [])
        is_dest    = (intent == "update_reminder" or
                      action.get("requires_confirmation", False))
        can_fill   = intent in ("create_reminder", "create_appointment",
                                "create_meeting_note", "create_note")

        label     = _INTENT_LABELS.get(intent, intent)
        imp       = fields.get("importance", "Normal")
        if imp not in ("Low", "Normal", "High", "Urgent"):
            imp = "Normal"
        imp_color  = _IMP_COLORS.get(imp, "gray")
        conf_color = ("#27ae60" if confidence >= CONFIDENCE_AUTO else
                      "#e67e22" if confidence >= CONFIDENCE_REVIEW else "#e74c3c")

        # Header
        top = ctk.CTkFrame(self._result_panel, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(top, text=f"Type: {label}",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkLabel(top, text=f"  {confidence:.0%} confidence",
                     text_color=conf_color, font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkLabel(top, text=f"  ● {imp}",
                     text_color=imp_color, font=ctk.CTkFont(size=13)).pack(side="left")

        # Field table (per intent type)
        rows: list[tuple[str, str]] = []
        if intent in ("create_reminder", "create_appointment"):
            rows += [
                ("Title",       fields.get("title", "")),
                ("When",        fields.get("datetime") or
                                f"{fields.get('date','')} {fields.get('time','')}".strip()),
                ("Details",     fields.get("details") or fields.get("description", "")),
                ("Repeat",      fields.get("recurrence", "none")),
            ]
        elif intent == "create_meeting_note":
            rows += [
                ("Title",        fields.get("title", "")),
                ("Meeting date", fields.get("note_date") or fields.get("datetime", "")),
                ("Details",      fields.get("details") or fields.get("description", "")),
            ]
            if fields.get("participants"):
                rows.append(("Participants", ", ".join(fields["participants"])))
        elif intent in ("create_note",):
            rows += [
                ("Title",     fields.get("title", "")),
                ("Date",      fields.get("note_date", "")),
                ("Details",   fields.get("details") or fields.get("description", "")),
            ]

        if fields.get("tags"):
            rows.append(("Tags", ", ".join(fields["tags"])))
        if fields.get("linked_note_title"):
            rows.append(("Linked note", fields["linked_note_title"]))
        if missing:
            rows.append(("⚠ Missing", ", ".join(missing)))
        rows.append(("Transcription", transcription))

        tbl = ctk.CTkFrame(self._result_panel, fg_color="transparent")
        tbl.pack(fill="x", padx=14, pady=(0, 8))
        for key, val in rows:
            if not val or str(val).strip() in ("", "none"):
                continue
            row_f = ctk.CTkFrame(tbl, fg_color="transparent")
            row_f.pack(fill="x", pady=1)
            ctk.CTkLabel(row_f, text=f"{key}:", width=108, anchor="e",
                         text_color="#888888",
                         font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(row_f, text=str(val), anchor="w",
                         font=ctk.CTkFont(size=12), wraplength=380).pack(
                side="left", fill="x")

        # Guidance
        if intent == "unknown" or confidence < CONFIDENCE_REVIEW:
            guide, gcol = "Low confidence — please rephrase or type manually.", "#e74c3c"
        else:
            guide = "Review the details above before saving."
            gcol  = "#27ae60" if confidence >= CONFIDENCE_AUTO else "#e67e22"
        ctk.CTkLabel(self._result_panel, text=guide, text_color=gcol,
                     font=ctk.CTkFont(size=13), wraplength=500).pack(
            anchor="w", padx=14, pady=(0, 10))

        # Buttons
        btn_row = ctk.CTkFrame(self._result_panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 14))

        if can_fill:
            ctk.CTkButton(
                btn_row, text="Insert into form", width=145,
                font=ctk.CTkFont(size=13),
                command=lambda: self._do_insert(intent, fields, transcription),
            ).pack(side="left", padx=(0, 8))

        if can_fill and not is_dest:
            ctk.CTkButton(
                btn_row, text="Save", width=80,
                font=ctk.CTkFont(size=13),
                fg_color="#1a7a3a", hover_color="#155c2b",
                command=lambda: self._do_save(intent, fields, transcription, action),
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Re-record", width=100,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=1,
            command=self._re_record,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Cancel", width=80,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=1, text_color="#e74c3c",
            command=self._cancel,
        ).pack(side="left")

        self._result_panel.pack(fill="x", padx=20, pady=(0, 12))
        self._set_status("Ready for review", "#27ae60")

    def _hide_result(self):
        self._result_panel.pack_forget()

    # ── button actions ────────────────────────────────────────────────────

    def _do_insert(self, intent: str, fields: dict, transcription: str):
        self._hide_result()
        if intent in ("create_reminder", "create_appointment"):
            if self._on_fill_reminder:
                self._on_fill_reminder(fields)
                self._set_status(
                    "Filled the reminder form — review and click Create Reminder.", "#27ae60")
            else:
                self._set_status("No reminder form available.", "#e74c3c")
        elif intent in ("create_meeting_note", "create_note"):
            if self._on_fill_note:
                self._on_fill_note(fields, transcription)
                self._set_status("Filled the note form — review and click Save.", "#27ae60")
            else:
                self._set_status("No note form available.", "#e74c3c")

    def _do_save(self, intent: str, fields: dict, transcription: str, action: dict):
        confidence    = float(action.get("confidence", 0.0))
        is_dest       = (intent == "update_reminder" or
                         action.get("requires_confirmation", False))
        auto_on       = self._autosave_var.get()
        needs_confirm = is_dest or not auto_on or confidence < CONFIDENCE_AUTO
        if needs_confirm:
            summary = action.get("action_summary", intent)
            if not mb.askyesno("Confirm Save",
                               f"{summary}\n\nConfidence: {confidence:.0%}\n\nSave now?"):
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

    def _re_record(self):
        self._hide_result()
        self._set_preview("")
        self._set_status("Ready — press the mic to speak again", "gray")
        self._start()

    def _cancel(self):
        self._hide_result()
        self._set_preview("")
        self._set_status("Cancelled.", "gray")

    # ── execution ─────────────────────────────────────────────────────────

    def _execute(self, intent: str, fields: dict, transcription: str) -> str:
        if intent in ("create_reminder", "create_appointment"):
            return self._make_reminder(fields, transcription)
        if intent in ("create_meeting_note", "create_note"):
            return self._make_note(fields, transcription)
        raise ValueError(f"Intent '{intent}' is not yet supported.")

    def _make_reminder(self, fields: dict, transcription: str) -> str:
        title   = fields.get("title") or "Voice reminder"
        dt_str  = (fields.get("datetime") or
                   f"{fields.get('date', '')} {fields.get('time', '')}".strip())
        due     = parse_datetime(dt_str) if dt_str else None
        if due is None:
            raise ValueError(
                f"Could not parse date/time from: \"{dt_str or 'nothing provided'}\""
            )
        recur   = fields.get("recurrence", "none")
        if recur not in ("none", "daily", "weekly", "monthly", "yearly"):
            recur = "none"
        details = fields.get("details") or fields.get("description", "")
        imp     = fields.get("importance", "Normal")
        create_reminder(title, due, message=details,
                        recurrence_type=recur, importance=imp)
        return f'"{title}" — {due.strftime("%A, %b %d at %H:%M")}'

    def _make_note(self, fields: dict, transcription: str) -> str:
        description = (fields.get("details") or fields.get("description") or transcription)
        title       = fields.get("title") or _auto_title(description)
        tags        = ", ".join(fields.get("tags") or [])
        imp         = fields.get("importance", "Normal")
        note_date   = fields.get("note_date", "")
        llm         = fields.get("intent", "create_note")
        create_note(title, content=description, tags=tags, source_type="voice",
                    original_transcription=transcription,
                    llm_intent=llm, importance=imp, note_date=note_date)
        return f'Note: "{title}"'

    # ── mic + waveform animation ──────────────────────────────────────────

    def _animate_mic(self):
        if not self.winfo_exists():
            return
        if self._mic_state == "idle":
            self._pulse_step += 1
            color = "#2563eb" if (self._pulse_step // 5) % 2 == 0 else "#1d4ed8"
            self._mic_canvas.itemconfig(self._mic_bg, fill=color)
            for rid in self._ring_ids:
                self._mic_canvas.coords(rid, 0, 0, 0, 0)
            self._mic_canvas.itemconfig(self._proc_arc, state="hidden")

        elif self._mic_state == "recording":
            self._ring_phase += 2
            level = self._recorder.current_level
            for i, rid in enumerate(self._ring_ids):
                phase = (self._ring_phase + i * 10) % 30
                r     = _BR + 10 + int(phase / 30 * 18)
                alpha = 1.0 - phase / 30
                rv    = int(alpha * 200 + (1 - alpha) * 40)
                self._mic_canvas.coords(rid, _CX-r, _CY-r, _CX+r, _CY+r)
                self._mic_canvas.itemconfig(rid, outline=f"#{rv:02x}1515")
            r_val = min(160 + int(level * 50), 210)
            self._mic_canvas.itemconfig(self._mic_bg, fill=f"#{r_val:02x}1818")
            self._mic_canvas.itemconfig(self._proc_arc, state="hidden")

        elif self._mic_state == "processing":
            for rid in self._ring_ids:
                self._mic_canvas.coords(rid, 0, 0, 0, 0)
            self._arc_angle = (self._arc_angle + 9) % 360
            self._mic_canvas.itemconfig(self._proc_arc,
                                        start=self._arc_angle, state="normal")
            self._mic_canvas.itemconfig(self._mic_bg, fill="#444455")

        self.after(50, self._animate_mic)

    def _animate_bars(self):
        if not self.winfo_exists():
            return
        if not self._recorder.is_recording:
            for bid, x1, x2 in self._bar_ids:
                self._wave_canvas.coords(bid, x1, _CAN_H - 4, x2, _CAN_H)
                self._wave_canvas.itemconfig(bid, fill="#2d4a6b")
            return
        level = self._recorder.current_level
        for bid, x1, x2 in self._bar_ids:
            noise = random.uniform(0.0, 0.4)
            h     = int(4 + min(level + noise, 1.0) * (_CAN_H - 6))
            h     = max(h, 4)
            inten = min(level + noise * 0.5, 1.0)
            r_    = min(30  + int(inten * 120), 220)
            g_    = min(100 + int(inten * 140), 240)
            b_    = max(200 - int(inten * 60),  100)
            self._wave_canvas.coords(bid, x1, _CAN_H - h, x2, _CAN_H)
            self._wave_canvas.itemconfig(bid, fill=f"#{r_:02x}{g_:02x}{b_:02x}")
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

def _extract_datetime_expr(text: str) -> str:
    """Extract only the time/date expression from natural language text."""
    t = text.lower()
    patterns = [
        r'in\s+\d+\s+(?:minutes?|hours?|days?)',
        r'(?:next\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        r'(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?',
        r'tomorrow(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?',
        r'today(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?',
        r'at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)',
        r'\d{1,2}(?::\d{2})?\s*(?:am|pm)',
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            return m.group(0).strip()
    return ""


def _rule_based_intent(text: str) -> dict:
    t = text.lower().strip()

    if any(w in t for w in ["remind", "reminder", "appointment", "schedule", "alert"]):
        intent = "create_reminder"
    elif any(w in t for w in ["meeting note", "meeting", "meeting with"]):
        intent = "create_meeting_note"
    elif any(w in t for w in ["note", "write", "jot", "record", "add a note"]):
        intent = "create_note"
    elif any(w in t for w in ["find", "search", "look for", "show me"]):
        intent = "search"
    else:
        intent = "unknown"

    importance = "Normal"
    if any(w in t for w in ["urgent", "asap", "emergency", "critical"]):
        importance = "Urgent"
    elif any(w in t for w in ["important", "high priority", "must"]):
        importance = "High"
    elif any(w in t for w in ["low priority", "whenever", "not urgent"]):
        importance = "Low"

    title = ""
    patterns = [
        r"remind(?:er)?\s+(?:for|about|me(?:\s+to)?)\s+(.+?)(?:\s+(?:tomorrow|today|at\s+\d|next|in\s+\d)|[.,]|$)",
        r"(?:note|write(?:\s+down)?|jot)[:\s]+(.+?)(?:\s+(?:before|tomorrow|today|at\s+\d)|[.,]|$)",
        r"(?:schedule|appointment|meeting)\s+(?:for\s+)?(.+?)(?:\s+(?:tomorrow|today|at\s+\d|next|in\s+\d)|[.,]|$)",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            title = m.group(1).strip().title()
            break
    if not title:
        title = _auto_title(text)

    dt_expr  = _extract_datetime_expr(text)
    missing  = [] if dt_expr else ["datetime"]

    return {
        "intent": intent,
        "confidence": 0.70,
        "requires_confirmation": True,
        "fields": {
            "title": title, "details": text, "description": text,
            "datetime": dt_expr, "date": "", "time": "",
            "note_date": "",
            "participants": [], "tags": [],
            "priority": "normal", "importance": importance,
            "recurrence": "none",
            "search_query": text if intent == "search" else "",
            "linked_note_title": "", "linked_note_id": None,
        },
        "action_summary": f"[Rule-based] {intent}: {title}",
        "missing_fields": missing,
    }


def _auto_title(text: str, max_words: int = 6) -> str:
    words = text.split()
    title = " ".join(words[:max_words]).rstrip(".,;:")
    return title + ("…" if len(words) > max_words else "")
