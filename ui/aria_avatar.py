"""Aria animated avatar — holographic AI orb with state-driven expressions."""
import math
import tkinter as tk

_SIZE  = 150
_CX = _CY = _SIZE // 2
_ORB_R = 52
_EYE_W = 14
_EYE_H = 7
_EYE_GAP = 22   # distance from centre to each eye
_EYE_Y   = -10  # eyes sit above orb centre


class AriaAvatar(tk.Canvas):
    """
    Canvas-drawn animated avatar.
    States: idle | listening | processing | thinking
    Call set_state(state) to switch.
    """

    def __init__(self, master, on_click=None, **kwargs):
        super().__init__(
            master,
            width=_SIZE, height=_SIZE,
            bg="#1a1e2a", highlightthickness=0,
            cursor="hand2",
        )
        self._on_click = on_click
        self._state    = "idle"
        self._phase    = 0       # 0-360, advances each frame
        self._blink_t  = 0       # ticks until next blink
        self._scan_x   = 0       # processing scan offset
        self._scan_dir = 1
        self._items    = {}      # name → canvas item id

        self._draw_static()
        if on_click:
            self.bind("<Button-1>", lambda e: on_click())
        self._animate()

    # ── public ───────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        """idle | listening | processing | thinking"""
        self._state = state

    # ── one-time drawing ─────────────────────────────────────────────────

    def _draw_static(self):
        i = self._items

        # Outer glow halo
        r = _ORB_R + 18
        i["halo"] = self.create_oval(
            _CX - r, _CY - r, _CX + r, _CY + r,
            outline="#162040", width=1, fill="",
        )

        # Orb layers (simulated radial gradient)
        for radius, color in [
            (_ORB_R,     "#0b1628"),
            (_ORB_R - 10, "#101e35"),
            (_ORB_R - 22, "#142440"),
            (_ORB_R - 34, "#1a2e52"),
        ]:
            self.create_oval(
                _CX - radius, _CY - radius,
                _CX + radius, _CY + radius,
                fill=color, outline="",
            )

        # Highlight glint (top-left, off-centre)
        self.create_oval(
            _CX - 28, _CY - 36,
            _CX - 10, _CY - 22,
            fill="#1e3d5e", outline="",
        )

        # Animated ring (start value; updated each frame)
        rr = _ORB_R + 7
        i["ring"] = self.create_arc(
            _CX - rr, _CY - rr, _CX + rr, _CY + rr,
            start=0, extent=320,
            outline="#2563eb", width=2, style="arc",
        )

        # Eye glow layers
        ey = _CY + _EYE_Y
        for side, ex in [("glow_l", _CX - _EYE_GAP), ("glow_r", _CX + _EYE_GAP)]:
            i[side] = self.create_oval(
                ex - _EYE_W // 2 - 4, ey - _EYE_H // 2 - 4,
                ex + _EYE_W // 2 + 4, ey + _EYE_H // 2 + 4,
                fill="#001e33", outline="",
            )

        # Eyes
        for side, ex in [("eye_l", _CX - _EYE_GAP), ("eye_r", _CX + _EYE_GAP)]:
            i[side] = self.create_oval(
                ex - _EYE_W // 2, ey - _EYE_H // 2,
                ex + _EYE_W // 2, ey + _EYE_H // 2,
                fill="#00d4ff", outline="",
            )

        # Processing scan line (hidden by default)
        i["scan"] = self.create_line(
            _CX - 18, _CY + _EYE_Y,
            _CX + 18, _CY + _EYE_Y,
            fill="#3B8ED0", width=2,
        )
        self.itemconfig(i["scan"], state="hidden")

        # Subtle mouth arc
        i["mouth"] = self.create_arc(
            _CX - 9, _CY + 14,
            _CX + 9, _CY + 22,
            start=200, extent=140,
            outline="#2563eb", width=1, style="arc",
        )

    # ── animation loop ───────────────────────────────────────────────────

    def _animate(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 4) % 360

        {
            "idle":       self._frame_idle,
            "listening":  self._frame_listening,
            "processing": self._frame_processing,
            "thinking":   self._frame_thinking,
        }.get(self._state, self._frame_idle)()

        self.after(50, self._animate)

    # ── per-state frames ─────────────────────────────────────────────────

    def _frame_idle(self):
        i = self._items
        pulse = 0.5 + 0.5 * math.sin(math.radians(self._phase))

        # Slow blue ring pulse
        alpha = int(38 + pulse * 55)
        ring_color = f"#{alpha:02x}{min(alpha + 28, 255):02x}eb"
        self.itemconfig(i["ring"], outline=ring_color,
                        extent=int(290 + pulse * 40), start=0)
        self.itemconfig(i["mouth"], outline="#2563eb")

        # Eyes normal
        self._show_eyes()
        self._set_eye_coords(_EYE_H)
        self.itemconfig(i["eye_l"], fill="#00d4ff")
        self.itemconfig(i["eye_r"], fill="#00d4ff")
        self.itemconfig(i["scan"],  state="hidden")

        # Blink every ~5 s
        self._blink_t += 1
        if self._blink_t > 100:
            self._blink_t = 0
            self._blink()

    def _frame_listening(self):
        i = self._items
        pulse = 0.5 + 0.5 * math.sin(math.radians(self._phase * 2))

        # Red/orange breathing ring
        rv = int(180 + pulse * 70)
        gv = int(35 + pulse * 25)
        self.itemconfig(i["ring"], outline=f"#{rv:02x}{gv:02x}20", extent=360, start=0)
        self.itemconfig(i["mouth"], outline="#e74c3c")

        # Wide, bright eyes
        h = int(_EYE_H * 1.6)
        self._show_eyes()
        self._set_eye_coords(h)
        bv = int(160 + pulse * 95)
        self.itemconfig(i["eye_l"], fill=f"#00{bv:02x}ff")
        self.itemconfig(i["eye_r"], fill=f"#00{bv:02x}ff")
        self.itemconfig(i["scan"],  state="hidden")

    def _frame_processing(self):
        i = self._items
        # Spinning blue arc
        self.itemconfig(i["ring"], outline="#3B8ED0", extent=90, start=self._phase)
        self.itemconfig(i["mouth"], outline="#3B8ED0")

        # Hide eyes; show scan line
        self.itemconfig(i["eye_l"],  state="hidden")
        self.itemconfig(i["eye_r"],  state="hidden")
        self.itemconfig(i["glow_l"], state="hidden")
        self.itemconfig(i["glow_r"], state="hidden")
        self.itemconfig(i["scan"],   state="normal")

        # Scan line sweeps left-right
        self._scan_x += self._scan_dir * 3
        if abs(self._scan_x) > 22:
            self._scan_dir *= -1
        cx = _CX + self._scan_x
        sy = _CY + _EYE_Y
        self.coords(i["scan"], cx - 16, sy, cx + 16, sy)

    def _frame_thinking(self):
        i = self._items
        pulse = 0.5 + 0.5 * math.sin(math.radians(self._phase))

        # Amber ring
        ov = int(140 + pulse * 60)
        self.itemconfig(i["ring"], outline=f"#{ov:02x}{int(ov * 0.45):02x}10",
                        extent=200, start=0)
        self.itemconfig(i["mouth"], outline="#e67e22")

        # Half-closed eyes
        h = max(2, int(_EYE_H * 0.38))
        self._show_eyes()
        self._set_eye_coords(h)
        self.itemconfig(i["eye_l"], fill="#0099bb")
        self.itemconfig(i["eye_r"], fill="#0099bb")
        self.itemconfig(i["scan"],  state="hidden")

    # ── helpers ───────────────────────────────────────────────────────────

    def _set_eye_coords(self, h: int):
        ey = _CY + _EYE_Y
        for side, ex in [("eye_l", _CX - _EYE_GAP), ("eye_r", _CX + _EYE_GAP)]:
            self.coords(
                self._items[side],
                ex - _EYE_W // 2, ey - h // 2,
                ex + _EYE_W // 2, ey + h // 2,
            )

    def _show_eyes(self):
        for key in ("eye_l", "eye_r", "glow_l", "glow_r"):
            self.itemconfig(self._items[key], state="normal")

    def _blink(self):
        """Quick 150 ms blink."""
        self._set_eye_coords(1)
        self.after(150, lambda: self._set_eye_coords(_EYE_H))
