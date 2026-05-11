import os
import json

_SYSTEM = """\
You are the intent classifier for Aria, a voice-first AI planning and reminder app.
Given a voice command transcription, return ONLY a valid JSON object — no explanation, no markdown.

Schema:
{
  "intent": "create_reminder | create_meeting_note | create_note | create_appointment | search | update_reminder | unknown",
  "confidence": <float 0.0–1.0>,
  "requires_confirmation": <bool>,
  "fields": {
    "title": "",
    "details": "",
    "description": "",
    "date": "",
    "time": "",
    "datetime": "",
    "note_date": "",
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
- datetime must contain ONLY the date/time expression (e.g. "tomorrow at 10pm", "next friday at 2pm").
  Never put the full transcription in datetime.
- details contains extra context or descriptive speech that is NOT the title or date/time
  (e.g. "about the DIEM brief", "in conference room B", "bring the laptop").
- description contains the full note body for meeting notes and plain notes.
- note_date: the date of a note or meeting, if mentioned (natural language or ISO).
- Set requires_confirmation=true only for delete or overwrite actions.
- Set confidence based on how unambiguous the intent is (1.0 = fully clear, 0.0 = no idea).
- missing_fields lists field names the user did not specify.
- importance must be exactly one of: "Low", "Normal", "High", "Urgent".
  Extract from phrasing:
    "urgent", "asap", "emergency", "critical"  → "Urgent"
    "important", "high priority", "must"        → "High"
    "low priority", "whenever", "not urgent"    → "Low"
    (default)                                   → "Normal"
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
