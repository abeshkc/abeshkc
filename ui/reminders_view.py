import tkinter.messagebox as mb
import customtkinter as ctk
from datetime import datetime
from core.reminders import create_reminder, list_reminders, mark_done, delete_reminder
from core.notes import list_notes
from core.parser import parse_datetime


class RemindersView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._notes: list[dict] = []
        self._build()

    def _build(self):
        # ── Create form ──────────────────────────────────────────────────
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            form, text="New Reminder", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=14, pady=(12, 8))

        row1 = ctk.CTkFrame(form, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(row1, text="Title:", width=56, anchor="w").pack(side="left")
        self._title_var = ctk.StringVar()
        ctk.CTkEntry(row1, textvariable=self._title_var, placeholder_text="Reminder title").pack(
            side="left", fill="x", expand=True, padx=(6, 0)
        )

        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(row2, text="When:", width=56, anchor="w").pack(side="left")
        self._when_var = ctk.StringVar()
        ctk.CTkEntry(
            row2,
            textvariable=self._when_var,
            placeholder_text='"tomorrow at 3pm",  "in 2 hours",  "friday 9am"',
        ).pack(side="left", fill="x", expand=True, padx=(6, 0))

        row3 = ctk.CTkFrame(form, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(row3, text="Note:", width=56, anchor="w").pack(side="left")
        self._note_var = ctk.StringVar(value="None")
        self._note_menu = ctk.CTkOptionMenu(row3, variable=self._note_var, values=["None"])
        self._note_menu.pack(side="left", padx=(6, 0))

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(btn_row, text="Create Reminder", command=self._create).pack(side="left")
        self._status_label = ctk.CTkLabel(btn_row, text="")
        self._status_label.pack(side="left", padx=(14, 0))

        # ── Reminder list ────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Upcoming Reminders", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=16, pady=(6, 0))

        self._list_frame = ctk.CTkScrollableFrame(self)
        self._list_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    # ── public ────────────────────────────────────────────────────────────

    def refresh(self):
        self._notes = list_notes()
        note_options = ["None"] + [f"{n['id']}: {n['title']}" for n in self._notes]
        self._note_menu.configure(values=note_options)

        for w in self._list_frame.winfo_children():
            w.destroy()

        reminders = list_reminders(include_done=False)
        if not reminders:
            ctk.CTkLabel(
                self._list_frame, text="No upcoming reminders.", text_color="gray"
            ).pack(pady=24)
            return
        for r in reminders:
            self._render_row(r)

    # ── private ───────────────────────────────────────────────────────────

    def _render_row(self, r: dict):
        row = ctk.CTkFrame(self._list_frame)
        row.pack(fill="x", pady=3, padx=4)

        due_str = r["due_at"][:16]  # "YYYY-MM-DD HH:MM"
        is_overdue = r["due_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = "#e74c3c" if is_overdue else "gray"

        ctk.CTkLabel(
            row, text=f"  {r['title']}", anchor="w", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(row, text=due_str, text_color=color).pack(side="left", padx=8)
        ctk.CTkButton(
            row, text="Done", width=60, command=lambda rid=r["id"]: self._done(rid)
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            row,
            text="X",
            width=32,
            fg_color="#c0392b",
            hover_color="#922b21",
            command=lambda rid=r["id"], rtitle=r["title"]: self._delete_r(rid, rtitle),
        ).pack(side="left", padx=(0, 6))

    def _create(self):
        title = self._title_var.get().strip()
        when_text = self._when_var.get().strip()

        if not title:
            self._status("Title is required.", "#e74c3c")
            return
        if not when_text:
            self._status("'When' is required.", "#e74c3c")
            return

        due = parse_datetime(when_text)
        if due is None:
            self._status(f"Couldn't parse: \"{when_text}\"", "#e74c3c")
            return

        note_id: int | None = None
        sel = self._note_var.get()
        if sel != "None":
            note_id = int(sel.split(":")[0])

        create_reminder(title, due, note_id=note_id)
        self._title_var.set("")
        self._when_var.set("")
        self._note_var.set("None")
        self._status(f"Set for {due.strftime('%b %d at %H:%M')}", "#27ae60")
        self.refresh()

    def _done(self, rid: int):
        mark_done(rid)
        self.refresh()

    def _delete_r(self, rid: int, title: str = ""):
        if not mb.askyesno(
            "Delete Reminder",
            f'Are you sure you want to delete "{title}"?\n\nThis cannot be undone.',
        ):
            return
        delete_reminder(rid)
        self.refresh()

    def _status(self, msg: str, color: str = "#27ae60"):
        self._status_label.configure(text=msg, text_color=color)
        self.after(3000, lambda: self._status_label.configure(text=""))
