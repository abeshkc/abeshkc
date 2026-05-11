import tkinter.messagebox as mb
import customtkinter as ctk
from datetime import datetime
from core.reminders import (
    create_reminder, list_reminders, list_done_reminders,
    mark_done, delete_reminder, RECURRENCE_TYPES,
)
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
        row3.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(row3, text="Repeat:", width=56, anchor="w").pack(side="left")
        self._recur_var = ctk.StringVar(value="none")
        ctk.CTkOptionMenu(
            row3, variable=self._recur_var, values=list(RECURRENCE_TYPES), width=120
        ).pack(side="left", padx=(6, 12))
        ctk.CTkLabel(row3, text="Every:", anchor="w").pack(side="left")
        self._interval_var = ctk.StringVar(value="1")
        ctk.CTkEntry(row3, textvariable=self._interval_var, width=40).pack(side="left", padx=(4, 0))

        row4 = ctk.CTkFrame(form, fg_color="transparent")
        row4.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(row4, text="Note:", width=56, anchor="w").pack(side="left")
        self._note_var = ctk.StringVar(value="None")
        self._note_menu = ctk.CTkOptionMenu(row4, variable=self._note_var, values=["None"])
        self._note_menu.pack(side="left", padx=(6, 0))

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(btn_row, text="Create Reminder", command=self._create).pack(side="left")
        self._status_label = ctk.CTkLabel(btn_row, text="")
        self._status_label.pack(side="left", padx=(14, 0))

        # ── Tabs: Upcoming / Done ────────────────────────────────────────
        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self._tabs.add("Upcoming")
        self._tabs.add("Done")

        self._upcoming_frame = ctk.CTkScrollableFrame(self._tabs.tab("Upcoming"))
        self._upcoming_frame.pack(fill="both", expand=True)

        self._done_frame = ctk.CTkScrollableFrame(self._tabs.tab("Done"))
        self._done_frame.pack(fill="both", expand=True)

    # ── public ────────────────────────────────────────────────────────────

    def refresh(self):
        self._notes = list_notes()
        note_options = ["None"] + [f"{n['id']}: {n['title']}" for n in self._notes]
        self._note_menu.configure(values=note_options)
        self._refresh_upcoming()
        self._refresh_done()

    # ── private ───────────────────────────────────────────────────────────

    def _refresh_upcoming(self):
        for w in self._upcoming_frame.winfo_children():
            w.destroy()
        reminders = list_reminders(include_done=False)
        if not reminders:
            ctk.CTkLabel(
                self._upcoming_frame, text="No upcoming reminders.", text_color="gray"
            ).pack(pady=24)
            return
        for r in reminders:
            self._render_upcoming_row(r)

    def _refresh_done(self):
        for w in self._done_frame.winfo_children():
            w.destroy()
        reminders = list_done_reminders()
        if not reminders:
            ctk.CTkLabel(
                self._done_frame, text="No completed reminders.", text_color="gray"
            ).pack(pady=24)
            return
        for r in reminders:
            self._render_done_row(r)

    def _render_upcoming_row(self, r: dict):
        row = ctk.CTkFrame(self._upcoming_frame)
        row.pack(fill="x", pady=3, padx=4)

        due_str = r["due_at"][:16]
        is_overdue = r["due_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = "#e74c3c" if is_overdue else "gray"

        label = r["title"]
        if r.get("recurrence_type", "none") != "none":
            label += f"  ↻ {r['recurrence_type']}"

        ctk.CTkLabel(
            row, text=f"  {label}", anchor="w", font=ctk.CTkFont(weight="bold")
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

    def _render_done_row(self, r: dict):
        row = ctk.CTkFrame(self._done_frame)
        row.pack(fill="x", pady=3, padx=4)

        completed = (r.get("completed_at") or "")[:16]
        ctk.CTkLabel(
            row, text=f"  {r['title']}", anchor="w",
            font=ctk.CTkFont(weight="bold"), text_color="gray"
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(row, text=f"Completed {completed}", text_color="gray").pack(
            side="left", padx=8
        )

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

        try:
            interval = max(1, int(self._interval_var.get()))
        except ValueError:
            interval = 1

        recur = self._recur_var.get()
        recur_line = (
            f"\nRepeat:  every {interval} {recur}"
            if recur != "none" else ""
        )

        confirmed = mb.askyesno(
            "Confirm Reminder",
            f"Create this reminder?\n\n"
            f"  Title:  {title}\n"
            f"  Due:    {due.strftime('%A, %b %d %Y at %H:%M')}"
            f"{recur_line}\n\n"
            f"Does this look right?",
        )
        if not confirmed:
            return

        note_id: int | None = None
        sel = self._note_var.get()
        if sel != "None":
            note_id = int(sel.split(":")[0])

        create_reminder(
            title, due, note_id=note_id,
            recurrence_type=recur,
            recurrence_interval=interval,
        )
        self._title_var.set("")
        self._when_var.set("")
        self._note_var.set("None")
        self._recur_var.set("none")
        self._interval_var.set("1")
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
