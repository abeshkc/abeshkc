import tkinter as tk
import tkinter.messagebox as mb
import customtkinter as ctk
from core.notes import (
    list_notes, create_note, get_note, update_note, delete_note, IMPORTANCE_LEVELS,
)

_IMP_COLORS = {
    "Low": "#777777", "Normal": "#aaaaaa", "High": "#e67e22", "Urgent": "#e74c3c"
}
_SORT_OPTIONS = ["Updated date", "Created date", "Importance", "Title"]
_SORT_KEYS    = {"Updated date": "updated_at", "Created date": "created_at",
                 "Importance": "importance", "Title": "title"}


class NotesView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._current_id: int | None = None
        self._sort_by  = "updated_at"
        self._sort_asc = False
        self._build()

    def _build(self):
        # Resizable horizontal split: list | editor
        pane = tk.PanedWindow(
            self, orient="horizontal",
            sashwidth=5, sashrelief="flat",
            background="#3a3a4a", bd=0,
        )
        pane.pack(fill="both", expand=True, padx=8, pady=8)

        # ── LEFT: search + sort + note list ──────────────────────────────
        left = ctk.CTkFrame(pane, width=260)

        search_row = ctk.CTkFrame(left, fg_color="transparent")
        search_row.pack(fill="x", padx=8, pady=(8, 2))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(search_row, placeholder_text="Search notes…",
                     textvariable=self._search_var).pack(
            side="left", fill="x", expand=True)
        ctk.CTkButton(search_row, text="+", width=34,
                      command=self._new_note).pack(side="left", padx=(4, 0))

        # Sort bar
        sort_bar = ctk.CTkFrame(left, fg_color="transparent")
        sort_bar.pack(fill="x", padx=8, pady=(2, 4))
        ctk.CTkLabel(sort_bar, text="Sort:", font=ctk.CTkFont(size=11),
                     text_color="gray").pack(side="left", padx=(2, 2))
        self._sort_var = ctk.StringVar(value="Updated date")
        ctk.CTkOptionMenu(
            sort_bar, variable=self._sort_var, values=_SORT_OPTIONS,
            width=116, command=self._on_sort_change,
        ).pack(side="left")
        self._asc_btn = ctk.CTkButton(
            sort_bar, text="↓ Desc", width=68,
            fg_color="transparent", border_width=1,
            font=ctk.CTkFont(size=11),
            command=self._toggle_sort_dir,
        )
        self._asc_btn.pack(side="left", padx=(4, 0))

        self._list_frame = ctk.CTkScrollableFrame(left)
        self._list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        pane.add(left, minsize=180, stretch="never")

        # ── RIGHT: editor ─────────────────────────────────────────────────
        right = ctk.CTkFrame(pane)

        ctk.CTkLabel(right, text="Title").pack(anchor="w", padx=14, pady=(14, 0))
        self._title_var = ctk.StringVar()
        ctk.CTkEntry(right, textvariable=self._title_var,
                     placeholder_text="Note title").pack(
            fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(right, text="Content").pack(anchor="w", padx=14)
        self._content_box = ctk.CTkTextbox(right, wrap="word")
        self._content_box.pack(fill="both", expand=True, padx=14, pady=(2, 8))

        # Tags + importance on same row
        meta_row = ctk.CTkFrame(right, fg_color="transparent")
        meta_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(meta_row, text="Tags:", width=60, anchor="w").pack(side="left")
        self._tags_var = ctk.StringVar()
        ctk.CTkEntry(meta_row, textvariable=self._tags_var,
                     placeholder_text="work, idea, personal").pack(
            side="left", fill="x", expand=True, padx=(4, 12))
        ctk.CTkLabel(meta_row, text="Importance:", anchor="w").pack(side="left")
        self._imp_var = ctk.StringVar(value="Normal")
        ctk.CTkOptionMenu(meta_row, variable=self._imp_var,
                          values=list(IMPORTANCE_LEVELS), width=110).pack(
            side="left", padx=(4, 0))

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(btn_row, text="Save", command=self._save).pack(side="left")
        ctk.CTkButton(btn_row, text="Delete",
                      fg_color="#c0392b", hover_color="#922b21",
                      command=self._delete).pack(side="left", padx=(10, 0))
        self._save_label = ctk.CTkLabel(btn_row, text="", text_color="#27ae60")
        self._save_label.pack(side="left", padx=(12, 0))

        pane.add(right, minsize=380, stretch="always")

    # ── public ────────────────────────────────────────────────────────────

    def fill_from_voice(self, fields: dict, transcription: str = ""):
        title       = fields.get("title") or "Voice note"
        description = fields.get("description") or transcription
        tags        = ", ".join(fields.get("tags") or [])
        imp         = fields.get("importance", "Normal")
        nid = create_note(title, importance=imp)
        self.refresh()
        note = get_note(nid)
        if note:
            self._load_note(note)
        if description:
            self._content_box.delete("1.0", "end")
            self._content_box.insert("1.0", description)
        if tags:
            self._tags_var.set(tags)
        if imp and imp in IMPORTANCE_LEVELS:
            self._imp_var.set(imp)

    def refresh(self):
        notes = list_notes(self._search_var.get(),
                           sort_by=self._sort_by,
                           ascending=self._sort_asc)
        for w in self._list_frame.winfo_children():
            w.destroy()
        for note in notes:
            imp       = note.get("importance", "Normal")
            imp_color = _IMP_COLORS.get(imp, "gray")
            prefix    = f"[{imp[0]}] " if imp != "Normal" else ""
            ctk.CTkButton(
                self._list_frame,
                text=f"{prefix}{note['title'] or '(untitled)'}",
                anchor="w",
                fg_color="transparent",
                hover_color="#2b2b3b",
                text_color=imp_color if imp != "Normal" else None,
                command=lambda n=note: self._load_note(n),
            ).pack(fill="x", pady=2)

    # ── sort ─────────────────────────────────────────────────────────────

    def _on_sort_change(self, _=None):
        self._sort_by = _SORT_KEYS.get(self._sort_var.get(), "updated_at")
        self.refresh()

    def _toggle_sort_dir(self):
        self._sort_asc = not self._sort_asc
        self._asc_btn.configure(text="↑ Asc" if self._sort_asc else "↓ Desc")
        self.refresh()

    # ── private ───────────────────────────────────────────────────────────

    def _load_note(self, note: dict):
        self._current_id = note["id"]
        self._title_var.set(note["title"])
        self._content_box.delete("1.0", "end")
        self._content_box.insert("1.0", note["content"])
        self._tags_var.set(note["tags"])
        self._imp_var.set(note.get("importance", "Normal"))

    def _new_note(self):
        nid = create_note("New Note")
        self.refresh()
        note = get_note(nid)
        if note:
            self._load_note(note)

    def _save(self):
        if self._current_id is None:
            return
        update_note(
            self._current_id,
            self._title_var.get(),
            self._content_box.get("1.0", "end").rstrip(),
            self._tags_var.get(),
            importance=self._imp_var.get(),
        )
        self.refresh()
        self._save_label.configure(text="Saved")
        self.after(2000, lambda: self._save_label.configure(text=""))

    def _delete(self):
        if self._current_id is None:
            return
        title = self._title_var.get() or "(untitled)"
        if not mb.askyesno(
            "Delete Note",
            f'Are you sure you want to delete "{title}"?\n\nThis cannot be undone.',
        ):
            return
        delete_note(self._current_id)
        self._current_id = None
        self._title_var.set("")
        self._content_box.delete("1.0", "end")
        self._tags_var.set("")
        self._imp_var.set("Normal")
        self.refresh()
