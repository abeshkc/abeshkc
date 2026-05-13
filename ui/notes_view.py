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
    def __init__(self, master, context=None):
        super().__init__(master, fg_color="transparent")
        self._current_id: int | None = None
        self._sort_by  = "updated_at"
        self._sort_asc = False
        self._context  = context
        self._build()

    def _build(self):
        pane = tk.PanedWindow(
            self, orient="horizontal",
            sashwidth=5, sashrelief="flat",
            background="#3a3a4a", bd=0,
        )
        pane.pack(fill="both", expand=True, padx=8, pady=8)

        # ── LEFT: search + sort + list ────────────────────────────────────
        left = ctk.CTkFrame(pane, width=270)

        search_row = ctk.CTkFrame(left, fg_color="transparent")
        search_row.pack(fill="x", padx=8, pady=(8, 2))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkEntry(search_row, placeholder_text="🔍  Search notes…",
                     textvariable=self._search_var,
                     font=ctk.CTkFont(size=13)).pack(
            side="left", fill="x", expand=True)
        ctk.CTkButton(search_row, text="＋", width=36,
                      font=ctk.CTkFont(size=16),
                      command=self._new_note).pack(side="left", padx=(4, 0))

        sort_bar = ctk.CTkFrame(left, fg_color="transparent")
        sort_bar.pack(fill="x", padx=8, pady=(2, 4))
        ctk.CTkLabel(sort_bar, text="Sort:", font=ctk.CTkFont(size=12),
                     text_color="gray").pack(side="left", padx=(2, 2))
        self._sort_var = ctk.StringVar(value="Updated date")
        ctk.CTkOptionMenu(
            sort_bar, variable=self._sort_var, values=_SORT_OPTIONS,
            width=120, font=ctk.CTkFont(size=12),
            command=self._on_sort_change,
        ).pack(side="left")
        self._asc_btn = ctk.CTkButton(
            sort_bar, text="↓ Desc", width=72,
            fg_color="transparent", border_width=1,
            font=ctk.CTkFont(size=12),
            command=self._toggle_sort_dir,
        )
        self._asc_btn.pack(side="left", padx=(4, 0))

        self._list_frame = ctk.CTkScrollableFrame(left)
        self._list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        pane.add(left, minsize=190, stretch="never")

        # ── RIGHT: editor ──────────────────────────────────────────────────
        right = ctk.CTkFrame(pane)

        # Aria editing banner (shown when a note is open)
        self._edit_banner = ctk.CTkFrame(right, fg_color="#1a2540", corner_radius=6)
        self._banner_lbl  = ctk.CTkLabel(
            self._edit_banner, text="",
            font=ctk.CTkFont(size=12), text_color="#5d8dbb", anchor="w",
        )
        self._banner_lbl.pack(side="left", padx=10, pady=4)
        self._dirty_lbl = ctk.CTkLabel(
            self._edit_banner, text="",
            font=ctk.CTkFont(size=11), text_color="#e67e22",
        )
        self._dirty_lbl.pack(side="right", padx=10)

        ctk.CTkLabel(
            right, text="📝  New Note",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        ctk.CTkLabel(right, text="Title", anchor="w",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=14, pady=(0, 0))
        self._title_var = ctk.StringVar()
        ctk.CTkEntry(right, textvariable=self._title_var,
                     placeholder_text="Note title",
                     font=ctk.CTkFont(size=13)).pack(
            fill="x", padx=14, pady=(2, 8))

        # Tags + Date + Importance on same row — now at top
        meta = ctk.CTkFrame(right, fg_color="transparent")
        meta.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkLabel(meta, text="Tags:", width=44, anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._tags_var = ctk.StringVar()
        ctk.CTkEntry(meta, textvariable=self._tags_var,
                     placeholder_text="work, idea…",
                     font=ctk.CTkFont(size=13)).pack(
            side="left", fill="x", expand=True, padx=(4, 12))
        ctk.CTkLabel(meta, text="Date:", anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._note_date_var = ctk.StringVar()
        ctk.CTkEntry(meta, textvariable=self._note_date_var,
                     placeholder_text="today, 2026-05-10…",
                     width=130, font=ctk.CTkFont(size=13)).pack(
            side="left", padx=(4, 12))
        ctk.CTkLabel(meta, text="Importance:", anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._imp_var = ctk.StringVar(value="Normal")
        ctk.CTkOptionMenu(meta, variable=self._imp_var,
                          values=list(IMPORTANCE_LEVELS), width=110,
                          font=ctk.CTkFont(size=13)).pack(
            side="left", padx=(4, 0))

        ctk.CTkLabel(right, text="Content", anchor="w",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=14)
        self._content_box = ctk.CTkTextbox(right, wrap="word",
                                           font=ctk.CTkFont(size=13))
        self._content_box.pack(fill="both", expand=True, padx=14, pady=(2, 8))
        self._content_box.bind("<<Modified>>", self._mark_dirty)

        # Dirty tracking on text vars
        self._title_var.trace_add("write", self._mark_dirty)
        self._tags_var.trace_add("write", self._mark_dirty)
        self._note_date_var.trace_add("write", self._mark_dirty)
        self._imp_var.trace_add("write", self._mark_dirty)

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(btn_row, text="💾  Save",
                      font=ctk.CTkFont(size=13),
                      command=self._save).pack(side="left")
        ctk.CTkButton(btn_row, text="🗑  Delete",
                      font=ctk.CTkFont(size=13),
                      fg_color="#c0392b", hover_color="#922b21",
                      command=self._delete).pack(side="left", padx=(10, 0))
        self._save_label = ctk.CTkLabel(btn_row, text="",
                                        text_color="#27ae60",
                                        font=ctk.CTkFont(size=13))
        self._save_label.pack(side="left", padx=(12, 0))

        pane.add(right, minsize=380, stretch="always")

    # ── public ────────────────────────────────────────────────────────────

    def fill_from_voice(self, fields: dict, transcription: str = ""):
        title       = fields.get("title") or "Voice note"
        description = (fields.get("details") or fields.get("description") or transcription)
        tags        = ", ".join(fields.get("tags") or [])
        imp         = fields.get("importance", "Normal")
        note_date   = fields.get("note_date", "")
        nid  = create_note(title, importance=imp, note_date=note_date)
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
        if note_date:
            self._note_date_var.set(note_date)

    def refresh(self):
        notes = list_notes(self._search_var.get(),
                           sort_by=self._sort_by,
                           ascending=self._sort_asc)
        for w in self._list_frame.winfo_children():
            w.destroy()
        for note in notes:
            imp       = note.get("importance", "Normal")
            imp_color = _IMP_COLORS.get(imp, None)
            prefix    = f"[{imp[0]}] " if imp != "Normal" else ""
            btn = ctk.CTkButton(
                self._list_frame,
                text=f"{prefix}{note['title'] or '(untitled)'}",
                anchor="w",
                fg_color="transparent",
                hover_color="#2b2b3b",
                font=ctk.CTkFont(size=13),
                text_color=imp_color if imp_color and imp != "Normal" else None,
                command=lambda n=note: self._load_note(n),
            )
            btn.pack(fill="x", pady=2)

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
        self._content_box.edit_reset()
        self._tags_var.set(note["tags"])
        self._imp_var.set(note.get("importance", "Normal"))
        self._note_date_var.set(note.get("note_date") or "")
        if self._context:
            self._context.set_note(note["id"], note["title"])
        self._update_banner()

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
            note_date=self._note_date_var.get(),
        )
        if self._context:
            self._context.unsaved_changes = False
            self._context.active_item_title = self._title_var.get()
        self.refresh()
        self._save_label.configure(text="✓ Saved")
        self.after(2000, lambda: self._save_label.configure(text=""))
        self._update_banner()

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
        self._note_date_var.set("")
        if self._context:
            self._context.clear()
        self._update_banner()
        self.refresh()

    def _mark_dirty(self, *_):
        if self._current_id is not None and self._context:
            self._context.mark_dirty()
            self._update_banner()

    def _update_banner(self):
        if self._current_id is None:
            self._edit_banner.pack_forget()
            return
        self._edit_banner.pack(fill="x", padx=14, pady=(8, 4))
        title = self._title_var.get() or "(untitled)"
        self._banner_lbl.configure(text=f"✦  Editing: {title}")
        if self._context and self._context.unsaved_changes:
            self._dirty_lbl.configure(text="● unsaved")
        else:
            self._dirty_lbl.configure(text="")

    def _flash_content(self):
        try:
            self._content_box.configure(border_color="#2563eb", border_width=2)
            self.after(600, lambda: self._content_box.configure(
                border_color=["#979DA2", "#565B5E"], border_width=0))
        except Exception:
            pass

    # ── public voice-edit methods ────────────────────────────────────────────

    def open_note(self, note_id: int) -> None:
        note = get_note(note_id)
        if note:
            self._load_note(note)

    def voice_append(self, text: str) -> None:
        if self._current_id is None:
            return
        current = self._content_box.get("1.0", "end").rstrip()
        self._content_box.delete("1.0", "end")
        self._content_box.insert("1.0", current + ("\n\n" if current else "") + text)
        if self._context:
            self._context.mark_dirty()
        self._flash_content()
        self._update_banner()

    def voice_update_fields(self, fields: dict) -> None:
        if self._current_id is None:
            return
        if fields.get("title"):
            self._title_var.set(fields["title"])
        tags = fields.get("tags")
        if tags:
            self._tags_var.set(", ".join(tags) if isinstance(tags, list) else tags)
        if fields.get("importance") and fields["importance"] in IMPORTANCE_LEVELS:
            self._imp_var.set(fields["importance"])
        if fields.get("note_date"):
            self._note_date_var.set(fields["note_date"])
        if self._context:
            self._context.mark_dirty()
        self._flash_content()
        self._update_banner()

    def voice_save(self) -> str:
        if self._current_id is None:
            return "Nothing to save."
        self._save()
        return f'Saved "{self._title_var.get()}"'

    def voice_close(self, confirmed: bool = False) -> bool:
        if self._context and self._context.unsaved_changes and not confirmed:
            return False
        self._current_id = None
        self._title_var.set("")
        self._content_box.delete("1.0", "end")
        self._tags_var.set("")
        self._imp_var.set("Normal")
        self._note_date_var.set("")
        if self._context:
            self._context.clear()
        self._update_banner()
        return True
