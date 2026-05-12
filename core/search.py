"""Combined search across notes and reminders — keyword-aware, relevance-ranked."""
import re
from core.notes import list_notes
from core.reminders import list_reminders

# Common words that carry no search signal
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
    "with", "about", "me", "my", "find", "search", "show", "get", "ones",
    "that", "are", "is", "was", "were", "related", "within", "notes",
    "reminders", "meetings", "meeting", "note", "reminder", "all",
}


def _keywords(query: str) -> list[str]:
    """Extract meaningful search keywords from a natural-language query."""
    words = re.findall(r"[a-z0-9]+", query.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _score(haystack: str, keywords: list[str]) -> int:
    """Count how many keywords appear in haystack (case-insensitive)."""
    h = haystack.lower()
    return sum(1 for kw in keywords if kw in h)


def search_all(query: str) -> list[dict]:
    """
    Return combined results from notes and reminders ranked by keyword relevance.
    Handles natural-language queries like "within the notes related to yaseen".
    """
    keywords = _keywords(query)
    if not keywords:
        return []

    results: list[dict] = []

    # Search all notes (no pre-filter — we score everything)
    for n in list_notes(""):
        haystack = " ".join([
            n.get("title") or "",
            n.get("content") or "",
            n.get("tags") or "",
            n.get("note_date") or "",
        ])
        score = _score(haystack, keywords)
        if score > 0:
            results.append({
                "type": "note",
                "id": n["id"],
                "title": n["title"] or "(untitled)",
                "snippet": (n.get("content") or "").strip()[:100],
                "date": (n.get("note_date") or n.get("updated_at", ""))[:10],
                "importance": n.get("importance", "Normal"),
                "tags": n.get("tags", ""),
                "_score": score,
            })

    # Search upcoming reminders
    for r in list_reminders(include_done=False):
        haystack = " ".join([r["title"], r.get("message") or ""])
        score = _score(haystack, keywords)
        if score > 0:
            results.append({
                "type": "reminder",
                "id": r["id"],
                "title": r["title"],
                "snippet": r.get("message") or "",
                "date": r.get("due_at", "")[:16],
                "importance": r.get("importance", "Normal"),
                "tags": "",
                "_score": score,
            })

    # Sort by relevance descending
    results.sort(key=lambda r: r["_score"], reverse=True)
    return results
