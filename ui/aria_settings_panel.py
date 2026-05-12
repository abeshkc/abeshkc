"""Aria settings popup."""
import customtkinter as ctk
from core.aria_settings import load, save


class AriaSettingsPanel(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Aria Settings")
        self.geometry("420x420")
        self.resizable(False, False)
        self.grab_set()
        self._settings = load()
        self._vars: dict = {}
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Aria Personality Settings",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(20, 16))

        self._toggle("Enable periodic updates",    "enable_periodic_updates")
        self._toggle("Include note-text analysis", "include_note_analysis")
        self._toggle("Greeting on startup",        "enable_greeting")
        self._toggle("Quiet mode",                 "quiet_mode")
        self._toggle("Pause Aria updates",         "pause_updates")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=(10, 4))
        ctk.CTkLabel(row, text="Update interval (min):", anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._interval_var = ctk.StringVar(value=str(self._settings.get("update_interval_minutes", 10)))
        ctk.CTkOptionMenu(row, variable=self._interval_var,
                          values=["5", "10", "15", "30"],
                          width=80, font=ctk.CTkFont(size=13)).pack(side="right")

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=28, pady=(0, 16))
        ctk.CTkLabel(row2, text="Number of insights:", anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._num_var = ctk.StringVar(value=str(self._settings.get("num_insights", 4)))
        ctk.CTkOptionMenu(row2, variable=self._num_var,
                          values=["2", "3", "4"],
                          width=80, font=ctk.CTkFont(size=13)).pack(side="right")

        ctk.CTkButton(self, text="Save", font=ctk.CTkFont(size=13),
                      command=self._save).pack(pady=(4, 8))
        ctk.CTkButton(self, text="Cancel", font=ctk.CTkFont(size=13),
                      fg_color="transparent", border_width=1,
                      command=self.destroy).pack()

    def _toggle(self, label: str, key: str):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=4)
        var = ctk.BooleanVar(value=self._settings.get(key, True))
        self._vars[key] = var
        ctk.CTkSwitch(row, text=label, variable=var,
                      font=ctk.CTkFont(size=13)).pack(side="left")

    def _save(self):
        s = {k: v.get() for k, v in self._vars.items()}
        s["update_interval_minutes"] = int(self._interval_var.get())
        s["num_insights"] = int(self._num_var.get())
        save(s)
        self.destroy()
