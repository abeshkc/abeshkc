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

Intent classification rules (apply in this priority order):

PRIORITY 1 — SEARCH (highest priority):
  If the user's phrasing contains ANY retrieval verb — "find", "search", "look for",
  "show me", "show my", "can you find", "get me", "what are", "list" — classify as "search"
  REGARDLESS of what noun follows (even if it mentions "note", "meeting", "reminder").
  Put the full search phrase in search_query. Confidence should be ≥ 0.90.
  Examples:
    "find me meeting notes with yaseen"              → search, query="meeting notes yaseen"
    "search for reminders about DIEM"               → search, query="DIEM"
    "show my urgent reminders"                       → search, query="urgent reminders"
    "can you find notes about Lebanon"               → search, query="Lebanon"
    "look for my meeting with Yaseen"                → search, query="Yaseen meeting"

PRIORITY 2 — REMINDER / APPOINTMENT:
  Only if no retrieval verb is present. Words: "remind me", "set a reminder",
  "appointment", "schedule", "alert me".

PRIORITY 3 — MEETING NOTE:
  Only if no retrieval verb and no reminder keyword. Words: "meeting note",
  "note the meeting", "record this meeting".

PRIORITY 4 — NOTE:
  Only if none of the above. Words: "add a note", "write down", "jot", "note that".

Additional rules:
- datetime must contain ONLY the date/time expression (e.g. "tomorrow at 10pm").
  Never put the full transcription in datetime.
- details: extra context not captured by title/datetime.
- description: full body for notes and meeting notes.
- note_date: date of a note or meeting if mentioned.
- requires_confirmation=true only for delete/overwrite actions.
- confidence: 1.0=fully clear, 0.0=no idea.
- missing_fields: field names the user did not specify.
- importance — exactly one of "Low", "Normal", "High", "Urgent":
    "urgent"/"asap"/"emergency"/"critical" → "Urgent"
    "important"/"high priority"/"must"     → "High"
    "low priority"/"whenever"/"not urgent" → "Low"
    (default)                              → "Normal"
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
