import customtkinter as ctk
from ui.notes_view import NotesView
from ui.reminders_view import RemindersView
from ui.voice_panel import VoicePanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NoteRemind")
        self.geometry("1120x720")
        self.minsize(880, 560)
        self._build_sidebar()
        self._build_content()
        self.show_voice()               # Voice is the default view
        self.after(500, self.update_missed_badge)  # check missed on start

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=172, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="NoteRemind",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(24, 16))

        # Voice — prominent, default
        self._btn_voice = ctk.CTkButton(
            self.sidebar,
            text="🎙  Voice",
            command=self.show_voice,
            height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        )
        self._btn_voice.pack(padx=12, pady=(0, 6), fill="x")

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#333344").pack(
            fill="x", padx=12, pady=(4, 10)
        )

        self._btn_notes = ctk.CTkButton(
            self.sidebar, text="Notes", command=self.show_notes
        )
        self._btn_notes.pack(padx=12, pady=6, fill="x")

        self._btn_reminders = ctk.CTkButton(
            self.sidebar, text="Reminders", command=self.show_reminders
        )
        self._btn_reminders.pack(padx=12, pady=6, fill="x")

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
            self._btn_reminders.configure(text=f"Reminders  🔴 {missed}")
        else:
            self._btn_reminders.configure(text="Reminders")

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
