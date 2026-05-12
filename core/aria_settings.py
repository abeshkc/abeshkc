"""Aria personality settings — persisted to ~/.noteremind/aria_settings.json."""
import json
from pathlib import Path

_PATH = Path.home() / ".noteremind" / "aria_settings.json"

DEFAULTS: dict = {
    "enable_periodic_updates": True,
    "update_interval_minutes": 10,
    "num_insights": 4,
    "include_note_analysis": True,
    "quiet_mode": False,
    "pause_updates": False,
    "enable_greeting": True,
}


def load() -> dict:
    if _PATH.exists():
        try:
            with open(_PATH, encoding="utf-8") as f:
                return {**DEFAULTS, **json.load(f)}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(settings: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
