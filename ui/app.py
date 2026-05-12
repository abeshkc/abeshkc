import tkinter as tk
import customtkinter as ctk
from ui.notes_view import NotesView
from ui.reminders_view import RemindersView
from ui.voice_panel import VoicePanel, _ToolTip

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_ARIA_ICON = "✦"   # four-pointed spark — "spark of intelligence"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aria — Your Personal Organizer")
        self.geometry("1140x730")
        self.minsize(900, 560)
        self._build_sidebar()
        self._build_content()
        self.show_voice()
        self.after(500, self.update_missed_badge)

    # ── sidebar ───────────────────────────────────────────────────────────

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=80, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Company logo placeholder
        logo_frame = ctk.CTkFrame(
            self.sidebar,
            width=48, height=48,
            corner_radius=12,
            fg_color="#2563eb",
        )
        logo_frame.pack(pady=(20, 10))
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(
            logo_frame,
            text="🏢",
            font=ctk.CTkFont(size=24),
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333344").pack(
            fill="x", padx=10, pady=(0, 8)
        )

        # Voice — primary, accent colour
        self._btn_voice = ctk.CTkButton(
            self.sidebar,
            text="🎙",
            command=self.show_voice,
            width=54, height=54,
            font=ctk.CTkFont(size=22),
            corner_radius=12,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        )
        self._btn_voice.pack(padx=10, pady=(0, 6))
        _ToolTip(self._btn_voice, "Your Personal Organizer")

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333344").pack(
            fill="x", padx=10, pady=(0, 8)
        )

        # Notes
        self._btn_notes = ctk.CTkButton(
            self.sidebar,
            text="📝",
            command=self.show_notes,
            width=54, height=54,
            font=ctk.CTkFont(size=22),
            corner_radius=12,
            fg_color="transparent",
            hover_color="#2b2b3b",
        )
        self._btn_notes.pack(padx=10, pady=(0, 6))
        _ToolTip(self._btn_notes, "Notes")

        # Reminders — with badge overlay
        rem_wrap = ctk.CTkFrame(self.sidebar, fg_color="transparent", width=54, height=54)
        rem_wrap.pack(padx=10, pady=(0, 6))
        rem_wrap.pack_propagate(False)

        self._btn_reminders = ctk.CTkButton(
            rem_wrap,
            text="🔔",
            command=self.show_reminders,
            width=54, height=54,
            font=ctk.CTkFont(size=22),
            corner_radius=12,
            fg_color="transparent",
            hover_color="#2b2b3b",
        )
        self._btn_reminders.place(x=0, y=0)
        _ToolTip(self._btn_reminders, "Reminders")

        # Badge label (hidden until there are missed reminders)
        self._badge_lbl = ctk.CTkLabel(
            rem_wrap,
            text="",
            fg_color="#e74c3c",
            text_color="white",
            width=18, height=18,
            corner_radius=9,
            font=ctk.CTkFont(size=9, weight="bold"),
        )

    # ── content ───────────────────────────────────────────────────────────

    def _build_content(self):
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)
        self.notes_view     = NotesView(self.content)
        self.reminders_view = RemindersView(self.content)
        self.voice_panel    = VoicePanel(
            self.content,
            on_action=self._refresh_all,
            on_fill_reminder=self._fill_reminder_form,
            on_fill_note=self._fill_note_form,
        )

    # ── navigation ────────────────────────────────────────────────────────

    def show_voice(self):
        self.notes_view.pack_forget()
        self.reminders_view.pack_forget()
        self.voice_panel.pack(fill="both", expand=True)

    def show_notes(self):
        self.reminders_view.pack_forget()
        self.voice_panel.pack_forget()
        self.notes_view.pack(fill="both", expand=True)
        self.notes_view.refresh()

    def show_reminders(self):
        self.notes_view.pack_forget()
        self.voice_panel.pack_forget()
        self.reminders_view.pack(fill="both", expand=True)
        self.reminders_view.refresh()
        self.update_missed_badge()

    # ── voice → form fill ─────────────────────────────────────────────────

    def _fill_reminder_form(self, fields: dict):
        self.show_reminders()
        self.reminders_view.fill_from_voice(fields)

    def _fill_note_form(self, fields: dict, transcription: str = ""):
        self.show_notes()
        self.notes_view.fill_from_voice(fields, transcription)

    # ── missed reminder badge ─────────────────────────────────────────────

    def update_missed_badge(self):
        try:
            from core.reminders import count_overdue
            missed = count_overdue()
        except Exception:
            missed = 0
        if missed > 0:
            self._badge_lbl.configure(text=str(min(missed, 99)))
            self._badge_lbl.place(x=36, y=2)   # top-right of 54px button
        else:
            self._badge_lbl.place_forget()

    # ── in-app reminder popup ─────────────────────────────────────────────

    def show_reminder_popup(self, reminder: dict):
        from ui.reminder_popup import ReminderPopup

        def on_done(rid: int):
            from core.reminders import mark_done
            mark_done(rid)
            self._refresh_all()
            self.update_missed_badge()

        try:
            ReminderPopup(self, reminder, on_done=on_done, on_open=self.show_reminders)
        except Exception as exc:
            print(f"[popup] {exc}")

    # ── shared ────────────────────────────────────────────────────────────

    def _refresh_all(self):
        self.notes_view.refresh()
        self.reminders_view.refresh()
        self.update_missed_badge()
