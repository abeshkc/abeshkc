import os
import json

_SYSTEM = """\
You are an intent classifier for a personal planning and reminder app.
Given a voice command transcription, return ONLY a valid JSON object — no explanation, no markdown.

Schema:
{
  "intent": "create_reminder | create_meeting_note | create_appointment | search | update_reminder | unknown",
  "confidence": <float 0.0–1.0>,
  "requires_confirmation": <bool>,
  "fields": {
    "title": "",
    "description": "",
    "date": "",
    "time": "",
    "datetime": "",
    "participants": [],
    "tags": [],
    "priority": "normal",
    "importance": "Normal",
    "recurrence": "none",
    "search_query": "",
    "linked_note_title": "",
    "linked_note_id": null
  },
  "action_summary": "",
  "missing_fields": []
}

Rules:
- Set datetime as a natural language string the app can parse (e.g. "tomorrow at 10pm", "next friday at 2pm").
- Set requires_confirmation=true only for delete or overwrite actions.
- Set confidence based on how unambiguous the intent is (1.0 = fully clear, 0.0 = no idea).
- missing_fields lists field names the user did not specify (e.g. ["time"] if no time was given).
- importance must be exactly one of: "Low", "Normal", "High", "Urgent".
  Extract importance from phrasing:
    "urgent", "asap", "emergency", "critical"   → "Urgent"
    "important", "high priority", "must"         → "High"
    "low priority", "whenever", "not urgent"     → "Low"
    (default)                                    → "Normal"
- linked_note_title: fill if user references a note by name; otherwise leave empty.
- Return ONLY the JSON object. No other text.\
"""


def parse_intent(transcription: str) -> dict:
    """Send transcription to Claude and return structured intent JSON."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": _SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": transcription}],
    )

    raw = message.content[0].text.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned non-JSON response: {raw[:200]}") from e
