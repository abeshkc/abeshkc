"""In-app popup dialog shown when a reminder becomes due."""
import customtkinter as ctk

_IMP_COLORS = {
    "Low": "#777777", "Normal": "#aaaaaa", "High": "#e67e22", "Urgent": "#e74c3c"
}


class ReminderPopup(ctk.CTkToplevel):
    """
    Non-blocking Toplevel that appears when a reminder fires.

    Callbacks:
      on_done(reminder_id)   — called when user marks done
      on_open()              — called when user clicks Open Reminder
    """
    def __init__(self, parent, reminder: dict,
                 on_done=None, on_open=None):
        super().__init__(parent)
        self._reminder = reminder
        self._on_done  = on_done
        self._on_open  = on_open
        self.title("⏰  Reminder Due")
        self.geometry("420x320")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self._build()
        self.lift()
        self.focus_force()

    def _build(self):
        r   = self._reminder
        imp = r.get("importance", "Normal")

        # Title bar
        top = ctk.CTkFrame(self, fg_color="#1a1e2a", corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(
            top, text=f"⏰  {r['title']}",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            top, text=f"Importance: {imp}",
            text_color=_IMP_COLORS.get(imp, "gray"),
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        def _field(key: str, val: str):
            if not val or val.strip() in ("", "none", "0"):
                return
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{key}:", width=96, anchor="e",
                         text_color="#888888",
                         font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=val, anchor="w",
                         font=ctk.CTkFont(size=11),
                         wraplength=270).pack(side="left")

        _field("Due", r.get("due_at", "")[:16])
        _field("Description", r.get("message", ""))
        recur = r.get("recurrence_type", "none")
        if recur and recur != "none":
            _field("Repeats", recur)

        # Buttons
        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(btn, text="Mark Done", width=110,
                      fg_color="#1a7a3a", hover_color="#155c2b",
                      command=self._mark_done).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn, text="Snooze 5 min", width=110,
                      command=lambda: self._snooze(5)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn, text="Snooze 15 min", width=115,
                      command=lambda: self._snooze(15)).pack(side="left", padx=(0, 6))

        btn2 = ctk.CTkFrame(self, fg_color="transparent")
        btn2.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(btn2, text="Open Reminder", width=130,
                      fg_color="transparent", border_width=1,
                      command=self._open).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn2, text="Dismiss", width=90,
                      fg_color="transparent", border_width=1,
                      text_color="#e74c3c",
                      command=self.destroy).pack(side="left")

    # ── actions ───────────────────────────────────────────────────────────

    def _mark_done(self):
        if self._on_done:
            self._on_done(self._reminder["id"])
        self.destroy()

    def _snooze(self, minutes: int):
        delay_ms = minutes * 60 * 1000
        # Re-show popup after snooze period
        self.after(delay_ms, lambda: self._reshow())
        self.destroy()

    def _reshow(self):
        # Re-create popup on the parent window
        try:
            parent = self.master
            ReminderPopup(parent, self._reminder,
                          on_done=self._on_done, on_open=self._on_open)
        except Exception:
            pass

    def _open(self):
        if self._on_open:
            self._on_open()
        self.destroy()
