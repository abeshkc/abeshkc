import tkinter as tk
import customtkinter as ctk
from ui.notes_view import NotesView
from ui.reminders_view import RemindersView
from ui.voice_panel import VoicePanel, _ToolTip
from ui.aria_context import AriaContext
from ui.aria_bar import AriaBar

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_ARIA_ICON = "✦"   # four-pointed spark — "spark of intelligence"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aria — Your Personal Organizer")
        self.geometry("1140x730")
        self.minsize(900, 560)
        self._ctx = AriaContext()
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
        self.notes_view     = NotesView(self.content, context=self._ctx)
        self.reminders_view = RemindersView(self.content, context=self._ctx)
        self.voice_panel    = VoicePanel(
            self.content,
            on_action=self._handle_action,
            on_fill_reminder=self._fill_reminder_form,
            on_fill_note=self._fill_note_form,
            on_open_note=self._open_note,
            on_open_reminder=self._open_reminder,
            context=self._ctx,
        )
        # Inject compact AriaBar into notes and reminders views
        self._notes_aria_bar = AriaBar(
            self.notes_view,
            on_intent=self._dispatch_aria_intent,
            context=self._ctx,
        )
        self._notes_aria_bar.pack(side="bottom", fill="x", padx=8, pady=(0, 4))
        self._reminders_aria_bar = AriaBar(
            self.reminders_view,
            on_intent=self._dispatch_aria_intent,
            context=self._ctx,
        )
        self._reminders_aria_bar.pack(side="bottom", fill="x", padx=8, pady=(0, 4))

    # ── navigation ────────────────────────────────────────────────────────

    def show_voice(self):
        self.notes_view.pack_forget()
        self.reminders_view.pack_forget()
        self.voice_panel.pack(fill="both", expand=True)
        self.voice_panel.refresh_dashboard()

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

    def _fill_reminder_form(self, fields: dict, mode: str = "fill"):
        if mode == "update_fields":
            self.show_reminders()
            if self._ctx.active_item_id:
                self.reminders_view.fill_from_voice_edit(self._ctx.active_item_id, fields)
        elif mode == "append":
            self.show_reminders()
            if self._ctx.active_item_id:
                self.reminders_view.fill_from_voice_edit(self._ctx.active_item_id, fields)
        else:
            self.show_reminders()
            self.reminders_view.fill_from_voice(fields)

    def _fill_note_form(self, fields: dict, transcription: str = "", mode: str = "fill"):
        if mode == "update_fields":
            self.show_notes()
            self.notes_view.voice_update_fields(fields)
        elif mode == "append":
            self.show_notes()
            self.notes_view.voice_append(fields.get("append_text") or transcription)
        else:
            self.show_notes()
            self.notes_view.fill_from_voice(fields, transcription)

    # ── open existing items ────────────────────────────────────────────────

    def _open_note(self, note_id: int):
        self.show_notes()
        self.notes_view.open_note(note_id)
        self._update_aria_bar_placeholders()

    def _open_reminder(self, reminder_id: int):
        self.show_reminders()
        self.reminders_view.open_reminder(reminder_id)
        self._update_aria_bar_placeholders()

    def _open_note_by_fields(self, fields: dict):
        item_id = fields.get("item_id")
        target  = fields.get("target_title") or fields.get("title", "")
        if item_id:
            self._open_note(int(item_id))
        elif target:
            from core.notes import list_notes
            matches = list_notes(target)
            if matches:
                self._open_note(matches[0]["id"])

    def _open_reminder_by_fields(self, fields: dict):
        item_id = fields.get("item_id")
        target  = fields.get("target_title") or fields.get("title", "")
        if item_id:
            self._open_reminder(int(item_id))
        elif target:
            from core.reminders import list_reminders
            matches = [r for r in list_reminders() if target.lower() in r["title"].lower()]
            if matches:
                self._open_reminder(matches[0]["id"])

    # ── AriaBar intent dispatch ────────────────────────────────────────────

    def _dispatch_aria_intent(self, action: dict, transcription: str):
        intent = action.get("intent", "unknown")
        fields = action.get("fields", {})

        if intent in ("search", "search_note", "search_reminder"):
            query = fields.get("search_query", transcription)
            self.show_voice()
            self.voice_panel._do_voice_search(query)
        elif intent == "open_note":
            self._open_note_by_fields(fields)
        elif intent == "open_reminder":
            self._open_reminder_by_fields(fields)
        elif intent == "save_active_item":
            self._handle_action("save_active")
        elif intent == "close_active_item":
            self._handle_action("close_active")
        elif intent in ("update_note", "append_note"):
            self._fill_note_form(
                fields, transcription,
                mode="update_fields" if intent == "update_note" else "append",
            )
        elif intent in ("update_reminder", "append_reminder"):
            self._fill_reminder_form(
                fields,
                mode="update_fields" if intent == "update_reminder" else "append",
            )
        elif intent in ("create_reminder", "create_appointment"):
            self._fill_reminder_form(fields)
        elif intent in ("create_note", "create_meeting_note"):
            self._fill_note_form(fields, transcription)

        self._update_aria_bar_placeholders()

    def _update_aria_bar_placeholders(self):
        title = self._ctx.active_item_title
        label = f"Editing: {title} — ask Aria…" if title else "Ask Aria anything…"
        self._notes_aria_bar.set_context_label(label)
        self._reminders_aria_bar.set_context_label(label)

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

    def _handle_action(self, action: str = "refresh"):
        if action == "save_active":
            if self._ctx.active_item_type == "note":
                self.notes_view.voice_save()
            elif self._ctx.active_item_type == "reminder":
                self.reminders_view.voice_save()
        elif action == "close_active":
            if self._ctx.active_item_type == "note":
                self.notes_view.voice_close(confirmed=True)
            elif self._ctx.active_item_type == "reminder":
                self.reminders_view.voice_close(confirmed=True)
            self._ctx.clear()
            self._update_aria_bar_placeholders()
        self.notes_view.refresh()
        self.reminders_view.refresh()
        self.update_missed_badge()

    def _refresh_all(self):
        self._handle_action("refresh")
