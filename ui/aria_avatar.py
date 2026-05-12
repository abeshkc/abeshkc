"""Aria full-form animated avatar — holographic AI figure with body."""
import math
import tkinter as tk

# Canvas dimensions
_W  = 220
_H  = 370

# Head
_HCX = 110
_HCY = 82
_HR  = 62

# Eyes
_EYE_W   = 15
_EYE_H   = 7
_EYE_GAP = 21
_EYE_Y   = _HCY - 9


class AriaAvatar(tk.Canvas):
    """
    Full-form Aria avatar with animated head + body.
    States: idle | listening | processing | thinking
    """

    def __init__(self, master, on_click=None, **kwargs):
        super().__init__(
            master, width=_W, height=_H,
            bg="#1a1e2a", highlightthickness=0,
            cursor="hand2",
        )
        self._on_click = on_click
        self._state    = "idle"
        self._phase    = 0
        self._blink_t  = 0
        self._scan_x   = 0
        self._scan_dir = 1
        # Particles: [angle, radius, speed]
        self._particles = [
            [i * 60, _HR + 16, 0.7 + i * 0.12]
            for i in range(6)
        ]
        self._items = {}
        self._draw()
        if on_click:
            self.bind("<Button-1>", lambda e: on_click())
        self._animate()

    # ── public ───────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        self._state = state

    # ── drawing ───────────────────────────────────────────────────────────

    def _draw(self):
        i = self._items

        # ── BODY ─────────────────────────────────────────────────────────

        # Full-body outer aura glow
        i["aura"] = self.create_oval(
            12, 128, 208, 362,
            fill="#09101e", outline="#131d30", width=1,
        )
        # Body main fill
        i["body"] = self.create_oval(
            38, 138, 182, 355,
            fill="#0c1525", outline="",
        )
        i["body_inner"] = self.create_oval(
            55, 152, 165, 338,
            fill="#0f1d33", outline="",
        )

        # Shoulder arcs
        i["sh_l"] = self.create_arc(
            5, 124, 128, 215,
            start=22, extent=88, outline="#1b3660", width=2, style="arc",
        )
        i["sh_r"] = self.create_arc(
            92, 124, 215, 215,
            start=70, extent=88, outline="#1b3660", width=2, style="arc",
        )

        # Chest core panel
        i["chest_bg"]  = self.create_oval(82, 170, 138, 215, fill="#0d1e36", outline="#162a48", width=1)
        i["chest_mid"] = self.create_oval(95, 182, 125, 204, fill="#152945", outline="")
        i["chest_glow"] = self.create_oval(103, 188, 117, 200, fill="#2563eb", outline="")

        # Hologram scan lines across body
        for idx, yp in enumerate([232, 252, 270, 287]):
            half = 62 - idx * 9
            i[f"hl{idx}"] = self.create_line(
                _HCX - half, yp, _HCX + half, yp,
                fill="#162a48", width=1,
            )

        # Subtle lower body taper
        i["lower"] = self.create_oval(62, 295, 158, 360, fill="#0b1422", outline="")

        # ── NECK ─────────────────────────────────────────────────────────
        i["neck"] = self.create_rectangle(
            103, _HCY + _HR - 4, 117, _HCY + _HR + 20,
            fill="#0e1c32", outline="",
        )
        i["neck_glow"] = self.create_rectangle(
            107, _HCY + _HR, 113, _HCY + _HR + 18,
            fill="#1a3456", outline="",
        )

        # ── HEAD ─────────────────────────────────────────────────────────

        # Halo ring
        rh = _HR + 20
        i["halo"] = self.create_oval(
            _HCX - rh, _HCY - rh, _HCX + rh, _HCY + rh,
            outline="#152240", width=1, fill="",
        )

        # Orb gradient (concentric circles, dark → slightly lighter)
        for radius, color in [
            (_HR,      "#0a1524"),
            (_HR - 11, "#0f1e33"),
            (_HR - 24, "#132440"),
            (_HR - 37, "#192e50"),
        ]:
            self.create_oval(
                _HCX - radius, _HCY - radius,
                _HCX + radius, _HCY + radius,
                fill=color, outline="",
            )

        # Highlight glint (top-left)
        self.create_oval(
            _HCX - 30, _HCY - 38,
            _HCX - 10, _HCY - 22,
            fill="#1d3d5c", outline="",
        )

        # Animated ring around head
        rr = _HR + 9
        i["ring"] = self.create_arc(
            _HCX - rr, _HCY - rr, _HCX + rr, _HCY + rr,
            start=0, extent=310, outline="#2563eb", width=2, style="arc",
        )

        # Eye glow layers
        ey = _EYE_Y
        for key, ex in [("glow_l", _HCX - _EYE_GAP), ("glow_r", _HCX + _EYE_GAP)]:
            i[key] = self.create_oval(
                ex - _EYE_W // 2 - 5, ey - _EYE_H // 2 - 5,
                ex + _EYE_W // 2 + 5, ey + _EYE_H // 2 + 5,
                fill="#001e30", outline="",
            )

        # Eyes
        for key, ex in [("eye_l", _HCX - _EYE_GAP), ("eye_r", _HCX + _EYE_GAP)]:
            i[key] = self.create_oval(
                ex - _EYE_W // 2, ey - _EYE_H // 2,
                ex + _EYE_W // 2, ey + _EYE_H // 2,
                fill="#00d4ff", outline="",
            )

        # Processing scan line
        i["scan"] = self.create_line(
            _HCX - 20, ey, _HCX + 20, ey,
            fill="#3B8ED0", width=2,
        )
        self.itemconfig(i["scan"], state="hidden")

        # Mouth arc
        i["mouth"] = self.create_arc(
            _HCX - 10, _HCY + 14, _HCX + 10, _HCY + 24,
            start=200, extent=140, outline="#2563eb", width=1, style="arc",
        )

        # ── PARTICLES ────────────────────────────────────────────────────
        i["parts"] = []
        for _ in self._particles:
            pid = self.create_oval(0, 0, 5, 5, fill="#152236", outline="")
            i["parts"].append(pid)

    # ── animation ─────────────────────────────────────────────────────────

    def _animate(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 4) % 360
        self._update_particles()
        {
            "idle":       self._frame_idle,
            "listening":  self._frame_listening,
            "processing": self._frame_processing,
            "thinking":   self._frame_thinking,
        }.get(self._state, self._frame_idle)()
        self.after(50, self._animate)

    def _update_particles(self):
        parts = self._items["parts"]
        for idx, (angle, radius, speed) in enumerate(self._particles):
            angle = (angle + speed) % 360
            self._particles[idx][0] = angle
            px = _HCX + radius * math.cos(math.radians(angle))
            py = _HCY + radius * math.sin(math.radians(angle))
            color = {
                "listening":  "#2a1010",
                "processing": "#0f2545",
                "thinking":   "#1a1a05",
            }.get(self._state, "#0f1e32")
            self.coords(parts[idx], px - 2, py - 2, px + 2, py + 2)
            self.itemconfig(parts[idx], fill=color)

    # ── per-state frames ─────────────────────────────────────────────────

    def _frame_idle(self):
        i = self._items
        p = 0.5 + 0.5 * math.sin(math.radians(self._phase))

        alpha = int(38 + p * 58)
        self.itemconfig(i["ring"],
                        outline=f"#{alpha:02x}{min(alpha + 30, 255):02x}eb",
                        extent=int(285 + p * 45), start=0)
        gv = int(30 + p * 55)
        self.itemconfig(i["chest_glow"], fill=f"#{20 + gv:02x}63eb")
        for idx in range(4):
            av = int(22 + p * 28)
            self.itemconfig(i[f"hl{idx}"], fill=f"#{av:02x}{av * 2:02x}5a")
        self.itemconfig(i["mouth"], outline="#2563eb")
        self._show_eyes()
        self._set_eye_coords(_EYE_H)
        self.itemconfig(i["eye_l"], fill="#00d4ff")
        self.itemconfig(i["eye_r"], fill="#00d4ff")
        self.itemconfig(i["scan"], state="hidden")
        self._blink_t += 1
        if self._blink_t > 100:
            self._blink_t = 0
            self._blink()

    def _frame_listening(self):
        i = self._items
        p = 0.5 + 0.5 * math.sin(math.radians(self._phase * 2))
        rv = int(175 + p * 75)
        gv = int(30 + p * 28)
        self.itemconfig(i["ring"], outline=f"#{rv:02x}{gv:02x}20", extent=360, start=0)
        self.itemconfig(i["chest_glow"], fill=f"#{rv:02x}2020")
        for idx in range(4):
            av = int(38 + p * 42)
            self.itemconfig(i[f"hl{idx}"], fill=f"#{av:02x}1010")
        self.itemconfig(i["mouth"], outline="#e74c3c")
        h = int(_EYE_H * 1.7)
        self._show_eyes()
        self._set_eye_coords(h)
        bv = int(155 + p * 100)
        self.itemconfig(i["eye_l"], fill=f"#00{bv:02x}ff")
        self.itemconfig(i["eye_r"], fill=f"#00{bv:02x}ff")
        self.itemconfig(i["scan"], state="hidden")

    def _frame_processing(self):
        i = self._items
        self.itemconfig(i["ring"], outline="#3B8ED0", extent=85, start=self._phase)
        self.itemconfig(i["chest_glow"], fill="#3B8ED0")
        self.itemconfig(i["mouth"], outline="#3B8ED0")
        for idx in range(4):
            self.itemconfig(i[f"hl{idx}"], fill="#1a4a7a")
        for key in ("eye_l", "eye_r", "glow_l", "glow_r"):
            self.itemconfig(i[key], state="hidden")
        self.itemconfig(i["scan"], state="normal")
        self._scan_x += self._scan_dir * 3
        if abs(self._scan_x) > 24:
            self._scan_dir *= -1
        cx = _HCX + self._scan_x
        self.coords(i["scan"], cx - 18, _EYE_Y, cx + 18, _EYE_Y)

    def _frame_thinking(self):
        i = self._items
        p = 0.5 + 0.5 * math.sin(math.radians(self._phase))
        ov = int(138 + p * 62)
        self.itemconfig(i["ring"],
                        outline=f"#{ov:02x}{int(ov * 0.44):02x}0e",
                        extent=195, start=0)
        self.itemconfig(i["chest_glow"], fill=f"#{ov:02x}{int(ov * 0.38):02x}10")
        self.itemconfig(i["mouth"], outline="#e67e22")
        h = max(2, int(_EYE_H * 0.36))
        self._show_eyes()
        self._set_eye_coords(h)
        self.itemconfig(i["eye_l"], fill="#0099bb")
        self.itemconfig(i["eye_r"], fill="#0099bb")
        self.itemconfig(i["scan"], state="hidden")

    # ── helpers ───────────────────────────────────────────────────────────

    def _set_eye_coords(self, h: int):
        ey = _EYE_Y
        for key, ex in [("eye_l", _HCX - _EYE_GAP), ("eye_r", _HCX + _EYE_GAP)]:
            self.coords(
                self._items[key],
                ex - _EYE_W // 2, ey - h // 2,
                ex + _EYE_W // 2, ey + h // 2,
            )

    def _show_eyes(self):
        for key in ("eye_l", "eye_r", "glow_l", "glow_r"):
            self.itemconfig(self._items[key], state="normal")

    def _blink(self):
        self._set_eye_coords(1)
        self.after(150, lambda: self._set_eye_coords(_EYE_H))
