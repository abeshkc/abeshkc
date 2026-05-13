"""Shared editing context for Aria — passed by reference to all panels."""
from dataclasses import dataclass, field


@dataclass
class AriaContext:
    active_item_type:  str | None = None   # "note" | "reminder" | None
    active_item_id:    int | None = None
    active_item_title: str | None = None
    last_search_results: list = field(default_factory=list)
    unsaved_changes: bool = False

    def set_note(self, note_id: int, title: str) -> None:
        self.active_item_type  = "note"
        self.active_item_id    = note_id
        self.active_item_title = title
        self.unsaved_changes   = False

    def set_reminder(self, reminder_id: int, title: str) -> None:
        self.active_item_type  = "reminder"
        self.active_item_id    = reminder_id
        self.active_item_title = title
        self.unsaved_changes   = False

    def mark_dirty(self) -> None:
        self.unsaved_changes = True

    def clear(self) -> None:
        self.active_item_type  = None
        self.active_item_id    = None
        self.active_item_title = None
        self.unsaved_changes   = False
