import tkinter.messagebox as mb
import customtkinter as ctk
from core.notes import list_notes, create_note, get_note, update_note, delete_note


class NotesView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._current_id: int | None = None
        self._build()

    def _build(self):
        # ── Left panel: search + note list ──────────────────────────────
        left = ctk.CTkFrame(self, width=270)
        left.pack(side="left", fill="y", padx=(8, 0), pady=8)
        left.pack_propagate(False)

        search_row = ctk.CTkFrame(left, fg_color="transparent")
        search_row.pack(fill="x", padx=8, pady=(8, 4))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(
            search_row, placeholder_text="Search notes...", textvariable=self._search_var
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(search_row, text="+", width=34, command=self._new_note).pack(
            side="left", padx=(4, 0)
        )

        self._list_frame = ctk.CTkScrollableFrame(left)
        self._list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # ── Right panel: editor ─────────────────────────────────────────
        right = ctk.CTkFrame(self)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(right, text="Title").pack(anchor="w", padx=14, pady=(14, 0))
        self._title_var = ctk.StringVar()
        ctk.CTkEntry(right, textvariable=self._title_var, placeholder_text="Note title").pack(
            fill="x", padx=14, pady=(2, 8)
        )

        ctk.CTkLabel(right, text="Content").pack(anchor="w", padx=14)
        self._content_box = ctk.CTkTextbox(right, wrap="word")
        self._content_box.pack(fill="both", expand=True, padx=14, pady=(2, 8))

        ctk.CTkLabel(right, text="Tags  (comma-separated)").pack(anchor="w", padx=14)
        self._tags_var = ctk.StringVar()
        ctk.CTkEntry(right, textvariable=self._tags_var, placeholder_text="work, idea, personal").pack(
            fill="x", padx=14, pady=(2, 8)
        )

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(btn_row, text="Save", command=self._save).pack(side="left")
        ctk.CTkButton(
            btn_row,
            text="Delete",
            fg_color="#c0392b",
            hover_color="#922b21",
            command=self._delete,
        ).pack(side="left", padx=(10, 0))
        self._save_label = ctk.CTkLabel(btn_row, text="", text_color="#27ae60")
        self._save_label.pack(side="left", padx=(12, 0))

    # ── public ────────────────────────────────────────────────────────────

    def fill_from_voice(self, fields: dict, transcription: str = ""):
        """Create a blank note, load it in the editor, fill fields (does not save)."""
        title       = fields.get("title") or "Voice note"
        description = fields.get("description") or transcription
        tags        = ", ".join(fields.get("tags") or [])
        nid  = create_note(title)
        self.refresh()
        from core.notes import get_note
        note = get_note(nid)
        if note:
            self._load_note(note)
        if description:
            self._content_box.delete("1.0", "end")
            self._content_box.insert("1.0", description)
        if tags:
            self._tags_var.set(tags)

    def refresh(self):
        notes = list_notes(self._search_var.get())
        for w in self._list_frame.winfo_children():
            w.destroy()
        for note in notes:
            ctk.CTkButton(
                self._list_frame,
                text=note["title"] or "(untitled)",
                anchor="w",
                fg_color="transparent",
                hover_color="#2b2b3b",
                command=lambda n=note: self._load_note(n),
            ).pack(fill="x", pady=2)

    # ── private ───────────────────────────────────────────────────────────

    def _load_note(self, note: dict):
        self._current_id = note["id"]
        self._title_var.set(note["title"])
        self._content_box.delete("1.0", "end")
        self._content_box.insert("1.0", note["content"])
        self._tags_var.set(note["tags"])

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
        self.refresh()
