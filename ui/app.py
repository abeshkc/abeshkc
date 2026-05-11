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
        self.geometry("1050x680")
        self.minsize(820, 520)
        self._build_sidebar()
        self._build_content()
        self.show_notes()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="NoteRemind",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(24, 32))

        self._btn_notes = ctk.CTkButton(
            self.sidebar, text="Notes", command=self.show_notes
        )
        self._btn_notes.pack(padx=12, pady=6, fill="x")

        self._btn_reminders = ctk.CTkButton(
            self.sidebar, text="Reminders", command=self.show_reminders
        )
        self._btn_reminders.pack(padx=12, pady=6, fill="x")

        self._btn_voice = ctk.CTkButton(
            self.sidebar, text="Voice", command=self.show_voice
        )
        self._btn_voice.pack(padx=12, pady=6, fill="x")

    def _build_content(self):
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)
        self.notes_view = NotesView(self.content)
        self.reminders_view = RemindersView(self.content)
        self.voice_panel = VoicePanel(self.content, on_action=self._refresh_all)

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

    def show_voice(self):
        self.notes_view.pack_forget()
        self.reminders_view.pack_forget()
        self.voice_panel.pack(fill="both", expand=True)

    def _refresh_all(self):
        self.notes_view.refresh()
        self.reminders_view.refresh()
