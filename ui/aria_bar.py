"""Compact Aria command bar — embeds in any view."""
import os
import threading
import customtkinter as ctk


class AriaBar(ctk.CTkFrame):
    """
    Minimal Aria text input: spark label + entry + submit button + status.
    Routes typed commands through parse_intent (Claude) or rule-based fallback,
    then calls on_intent(result_dict, transcription_text).
    """

    def __init__(self, master, on_intent, context=None, **kwargs):
        super().__init__(master, fg_color="#111520", corner_radius=8, **kwargs)
        self._on_intent = on_intent
        self._context   = context
        self._build()

    def _build(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)

        ctk.CTkLabel(row, text="✦", font=ctk.CTkFont(size=16),
                     text_color="#3B8ED0").pack(side="left", padx=(4, 6))

        self._entry_var = ctk.StringVar()
        self._entry = ctk.CTkEntry(
            row, textvariable=self._entry_var,
            placeholder_text="Ask Aria anything…",
            font=ctk.CTkFont(size=12),
        )
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", lambda e: self._submit())

        ctk.CTkButton(row, text="⏎", width=30, font=ctk.CTkFont(size=12),
                      command=self._submit).pack(side="left", padx=(4, 0))

        self._status = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=11), text_color="#5d8dbb", anchor="w",
        )
        self._status.pack(anchor="w", padx=14, pady=(0, 4))

    def _submit(self):
        text = self._entry_var.get().strip()
        if not text:
            return
        self._entry_var.set("")
        self._set_status("Understanding…", "#5d8dbb")
        threading.Thread(target=self._parse, args=(text,), daemon=True).start()

    def _parse(self, text: str):
        try:
            if os.environ.get("ANTHROPIC_API_KEY"):
                from services.intent_parser import parse_intent
                result = parse_intent(text)
            else:
                from ui.voice_panel import _rule_based_intent
                result = _rule_based_intent(text)
        except Exception as exc:
            self.after(0, lambda: self._set_status(f"Error: {exc}", "#e74c3c"))
            return
        self.after(0, lambda r=result, t=text: (
            self._set_status("", ""),
            self._on_intent(r, t),
        ))

    def _set_status(self, msg: str, color: str):
        self._status.configure(text=msg, text_color=color or "#5d8dbb")

    def set_context_label(self, text: str):
        self._entry.configure(placeholder_text=text or "Ask Aria anything…")
