import tkinter as tk
import tkinter.messagebox as mb
import customtkinter as ctk
from datetime import datetime
from core.reminders import (
    create_reminder, list_reminders, list_done_reminders,
    mark_done, delete_reminder, RECURRENCE_TYPES, IMPORTANCE_LEVELS,
)
from core.notes import list_notes
from core.parser import parse_datetime

_IMP_COLORS = {
    "Low": "#777777", "Normal": "#aaaaaa", "High": "#e67e22", "Urgent": "#e74c3c"
}

_SORT_OPTIONS = ["Due date", "Importance", "Created date", "Title"]
_SORT_KEYS    = {"Due date": "due_at", "Importance": "importance",
                 "Created date": "created_at", "Title": "title"}


class RemindersView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._notes: list[dict] = []
        self._sort_by  = "due_at"
        self._sort_asc = True
        self._build()

    def _build(self):
        # Resizable split: form top, lists bottom
        pane = tk.PanedWindow(
            self, orient="vertical",
            sashwidth=5, sashrelief="flat",
            background="#3a3a4a", bd=0,
        )
        pane.pack(fill="both", expand=True)

        # ── TOP: create form ──────────────────────────────────────────────
        form_frame = ctk.CTkFrame(pane, corner_radius=0, fg_color="transparent")

        form = ctk.CTkFrame(form_frame)
        form.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            form, text="New Reminder", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=14, pady=(12, 8))

        def _row(parent):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=14, pady=(0, 6))
            return f

        row1 = _row(form)
        ctk.CTkLabel(row1, text="Title:", width=72, anchor="w").pack(side="left")
        self._title_var = ctk.StringVar()
        ctk.CTkEntry(row1, textvariable=self._title_var,
                     placeholder_text="Reminder title").pack(
            side="left", fill="x", expand=True, padx=(6, 0))

        row2 = _row(form)
        ctk.CTkLabel(row2, text="When:", width=72, anchor="w").pack(side="left")
        self._when_var = ctk.StringVar()
        ctk.CTkEntry(row2, textvariable=self._when_var,
                     placeholder_text='"tomorrow at 3pm",  "in 2 hours",  "friday 9am"').pack(
            side="left", fill="x", expand=True, padx=(6, 0))

        row3 = _row(form)
        ctk.CTkLabel(row3, text="Importance:", width=72, anchor="w").pack(side="left")
        self._imp_var = ctk.StringVar(value="Normal")
        ctk.CTkOptionMenu(row3, variable=self._imp_var,
                          values=list(IMPORTANCE_LEVELS), width=110).pack(
            side="left", padx=(6, 16))
        ctk.CTkLabel(row3, text="Repeat:", anchor="w").pack(side="left")
        self._recur_var = ctk.StringVar(value="none")
        ctk.CTkOptionMenu(row3, variable=self._recur_var,
                          values=list(RECURRENCE_TYPES), width=100).pack(
            side="left", padx=(6, 12))
        ctk.CTkLabel(row3, text="Every:", anchor="w").pack(side="left")
        self._interval_var = ctk.StringVar(value="1")
        ctk.CTkEntry(row3, textvariable=self._interval_var, width=40).pack(
            side="left", padx=(4, 0))

        row4 = _row(form)
        ctk.CTkLabel(row4, text="Note:", width=72, anchor="w").pack(side="left")
        self._note_var  = ctk.StringVar(value="None")
        self._note_menu = ctk.CTkOptionMenu(row4, variable=self._note_var, values=["None"])
        self._note_menu.pack(side="left", padx=(6, 0))

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(btn_row, text="Create Reminder", command=self._create).pack(side="left")
        self._status_label = ctk.CTkLabel(btn_row, text="")
        self._status_label.pack(side="left", padx=(14, 0))

        pane.add(form_frame, minsize=220, stretch="never")

        # ── BOTTOM: tabs (Upcoming / Done) + sort ─────────────────────────
        list_frame = ctk.CTkFrame(pane, corner_radius=0, fg_color="transparent")

        # Sort controls
        sort_bar = ctk.CTkFrame(list_frame, fg_color="transparent")
        sort_bar.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(sort_bar, text="Sort:", font=ctk.CTkFont(size=11),
                     text_color="gray").pack(side="left", padx=(4, 4))
        self._sort_var = ctk.StringVar(value="Due date")
        ctk.CTkOptionMenu(
            sort_bar, variable=self._sort_var, values=_SORT_OPTIONS,
            width=120, command=self._on_sort_change,
        ).pack(side="left")
        self._asc_btn = ctk.CTkButton(
            sort_bar, text="↑ Asc", width=70,
            fg_color="transparent", border_width=1,
            font=ctk.CTkFont(size=11),
            command=self._toggle_sort_dir,
        )
        self._asc_btn.pack(side="left", padx=(6, 0))

        self._tabs = ctk.CTkTabview(list_frame)
        self._tabs.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self._tabs.add("Upcoming")
        self._tabs.add("Done")

        self._upcoming_frame = ctk.CTkScrollableFrame(self._tabs.tab("Upcoming"))
        self._upcoming_frame.pack(fill="both", expand=True)

        self._done_frame = ctk.CTkScrollableFrame(self._tabs.tab("Done"))
        self._done_frame.pack(fill="both", expand=True)

        pane.add(list_frame, minsize=180, stretch="always")

    # ── public ────────────────────────────────────────────────────────────

    def fill_from_voice(self, fields: dict):
        title  = fields.get("title", "").strip()
        dt_str = (fields.get("datetime") or
                  f"{fields.get('date', '')} {fields.get('time', '')}".strip())
        recur  = fields.get("recurrence", "none")
        imp    = fields.get("importance", "Normal")
        if title:
            self._title_var.set(title)
        if dt_str:
            self._when_var.set(dt_str)
        if recur and recur in list(RECURRENCE_TYPES):
            self._recur_var.set(recur)
        if imp and imp in IMPORTANCE_LEVELS:
            self._imp_var.set(imp)
        self._status("Filled from voice — review and click Create Reminder.", "#5d8dbb")

    def refresh(self):
        self._notes = list_notes()
        note_options = ["None"] + [f"{n['id']}: {n['title']}" for n in self._notes]
        self._note_menu.configure(values=note_options)
        self._refresh_upcoming()
        self._refresh_done()

    # ── sort controls ─────────────────────────────────────────────────────

    def _on_sort_change(self, _=None):
        label = self._sort_var.get()
        self._sort_by = _SORT_KEYS.get(label, "due_at")
        self._refresh_upcoming()

    def _toggle_sort_dir(self):
        self._sort_asc = not self._sort_asc
        self._asc_btn.configure(text="↑ Asc" if self._sort_asc else "↓ Desc")
        self._refresh_upcoming()

    # ── private ───────────────────────────────────────────────────────────

    def _refresh_upcoming(self):
        for w in self._upcoming_frame.winfo_children():
            w.destroy()
        reminders = list_reminders(include_done=False,
                                   sort_by=self._sort_by,
                                   ascending=self._sort_asc)
        if not reminders:
            ctk.CTkLabel(self._upcoming_frame, text="No upcoming reminders.",
                         text_color="gray").pack(pady=24)
            return
        for r in reminders:
            self._render_upcoming_row(r)

    def _refresh_done(self):
        for w in self._done_frame.winfo_children():
            w.destroy()
        reminders = list_done_reminders()
        if not reminders:
            ctk.CTkLabel(self._done_frame, text="No completed reminders.",
                         text_color="gray").pack(pady=24)
            return
        for r in reminders:
            self._render_done_row(r)

    def _render_upcoming_row(self, r: dict):
        row = ctk.CTkFrame(self._upcoming_frame)
        row.pack(fill="x", pady=3, padx=4)

        due_str   = r["due_at"][:16]
        is_overdue = r["due_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_color = "#e74c3c" if is_overdue else "gray"

        label = r["title"]
        if r.get("recurrence_type", "none") != "none":
            label += f"  ↻ {r['recurrence_type']}"

        imp       = r.get("importance", "Normal")
        imp_color = _IMP_COLORS.get(imp, "gray")

        ctk.CTkLabel(row, text=f"  {label}", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(
            side="left", fill="x", expand=True, padx=(4, 0))
        if imp != "Normal":
            ctk.CTkLabel(row, text=imp, text_color=imp_color,
                         font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
        ctk.CTkLabel(row, text=due_str, text_color=date_color).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Done", width=60,
                      command=lambda rid=r["id"]: self._done(rid)).pack(
            side="left", padx=(0, 4))
        ctk.CTkButton(row, text="X", width=32,
                      fg_color="#c0392b", hover_color="#922b21",
                      command=lambda rid=r["id"], rt=r["title"]: self._delete_r(rid, rt),
                      ).pack(side="left", padx=(0, 6))

    def _render_done_row(self, r: dict):
        row = ctk.CTkFrame(self._done_frame)
        row.pack(fill="x", pady=3, padx=4)
        completed = (r.get("completed_at") or "")[:16]
        ctk.CTkLabel(row, text=f"  {r['title']}", anchor="w",
                     font=ctk.CTkFont(weight="bold"), text_color="gray").pack(
            side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(row, text=f"Completed {completed}", text_color="gray").pack(
            side="left", padx=8)

    def _create(self):
        title     = self._title_var.get().strip()
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
        recur     = self._recur_var.get()
        imp       = self._imp_var.get()
        recur_line = (f"\nRepeat:  every {interval} {recur}" if recur != "none" else "")
        confirmed  = mb.askyesno(
            "Confirm Reminder",
            f"Create this reminder?\n\n"
            f"  Title:      {title}\n"
            f"  Due:        {due.strftime('%A, %b %d %Y at %H:%M')}\n"
            f"  Importance: {imp}"
            f"{recur_line}\n\nDoes this look right?",
        )
        if not confirmed:
            return
        note_id: int | None = None
        sel = self._note_var.get()
        if sel != "None":
            note_id = int(sel.split(":")[0])
        create_reminder(
            title, due, note_id=note_id,
            recurrence_type=recur, recurrence_interval=interval,
            importance=imp,
        )
        self._title_var.set("")
        self._when_var.set("")
        self._note_var.set("None")
        self._recur_var.set("none")
        self._interval_var.set("1")
        self._imp_var.set("Normal")
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
