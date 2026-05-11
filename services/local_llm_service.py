"""
Local LLM intent parsing via Ollama + Qwen.

Settings (set in .env):
  OLLAMA_BASE_URL        — default: http://localhost:11434
  OLLAMA_MODEL           — default: qwen2.5:7b
  OLLAMA_FALLBACK_MODEL  — default: qwen2.5:3b
  OLLAMA_TIMEOUT         — seconds, default: 30
"""
import os
import json
from datetime import datetime, timedelta


def _settings() -> dict:
    return {
        "base_url":       os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        "model":          os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
        "fallback_model": os.environ.get("OLLAMA_FALLBACK_MODEL", "qwen2.5:3b"),
        "timeout":        int(os.environ.get("OLLAMA_TIMEOUT", "30")),
    }


def is_ollama_running() -> bool:
    import requests
    s = _settings()
    try:
        r = requests.get(s["base_url"], timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def available_models() -> list[str]:
    import requests
    s = _settings()
    try:
        r = requests.get(f"{s['base_url']}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def _resolve_model(s: dict) -> str:
    """Return the best available model name, or raise with an install hint."""
    models = available_models()

    def _match(name: str) -> bool:
        base = name.split(":")[0]
        return any(m == name or m.startswith(base + ":") for m in models)

    if _match(s["model"]):
        return s["model"]
    if _match(s["fallback_model"]):
        return s["fallback_model"]

    raise RuntimeError(
        f"Model '{s['model']}' is not installed.\n"
        f"Run:  ollama pull {s['model']}\n"
        f"Or (lower RAM):  ollama pull {s['fallback_model']}"
    )


def _build_prompt(now: datetime) -> str:
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d (%A)")
    return f"""\
You are the local AI parser for a Windows planning and reminder app.
Convert the user's voice transcription into a structured JSON action.

Rules:
- Return ONLY valid JSON. No markdown, no explanation, no code fences.
- Current date: {now.strftime("%Y-%m-%d (%A)")}
- Current time: {now.strftime("%H:%M")}
- Tomorrow:     {tomorrow}
- Calculate weekday names (e.g. "next Friday") from today's date.
- For datetime field use natural language the app can parse, e.g. "tomorrow at 10pm".
- If date/time is missing, add the field name to missing_fields.
- confidence >= 0.85: intent clear, all required fields present.
- confidence 0.60–0.84: intent clear, some fields missing.
- confidence < 0.60: ambiguous.
- Set requires_confirmation=false for create/note/search actions.
- Set requires_confirmation=true only for delete or overwrite actions.

Return exactly this JSON structure:
{{
  "intent": "create_reminder | create_meeting_note | create_appointment | search | update_reminder | unknown",
  "confidence": 0.0,
  "requires_confirmation": false,
  "fields": {{
    "title": "",
    "description": "",
    "date": "",
    "time": "",
    "datetime": "",
    "participants": [],
    "tags": [],
    "priority": "normal",
    "recurrence": "none",
    "search_query": ""
  }},
  "action_summary": "",
  "missing_fields": []
}}\
"""


def parse_intent(transcription: str) -> dict:
    """Send transcription to Qwen via Ollama and return structured JSON."""
    import requests

    s = _settings()

    if not is_ollama_running():
        raise RuntimeError(
            "Local Qwen model is not available. Please start Ollama.\n"
            "Run:  ollama serve"
        )

    model = _resolve_model(s)
    system_prompt = _build_prompt(datetime.now())

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": transcription},
        ],
        "stream": False,
        "format": "json",
    }

    try:
        r = requests.post(
            f"{s['base_url']}/api/chat",
            json=payload,
            timeout=s["timeout"],
        )
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Ollama request timed out after {s['timeout']}s")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Cannot connect to Ollama. Is it running?")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP error: {e}")

    raw = r.json().get("message", {}).get("content", "").strip()

    # Strip markdown fences if the model added them despite instructions
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Qwen returned invalid JSON: {raw[:300]}") from e
