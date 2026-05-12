"""Combined search across notes and reminders."""
from core.notes import list_notes
from core.reminders import list_reminders


def search_all(query: str) -> list[dict]:
    """Return combined results from notes and reminders matching query."""
    q = query.lower().strip()
    if not q:
        return []

    results: list[dict] = []

    for n in list_notes(q):
        results.append({
            "type": "note",
            "id": n["id"],
            "title": n["title"] or "(untitled)",
            "snippet": (n.get("content") or "")[:100].strip(),
            "date": (n.get("note_date") or n.get("updated_at", ""))[:10],
            "importance": n.get("importance", "Normal"),
            "tags": n.get("tags", ""),
        })

    for r in list_reminders(include_done=False):
        haystack = (r["title"] + " " + (r.get("message") or "")).lower()
        if q in haystack:
            results.append({
                "type": "reminder",
                "id": r["id"],
                "title": r["title"],
                "snippet": r.get("message") or "",
                "date": r.get("due_at", "")[:16],
                "importance": r.get("importance", "Normal"),
                "tags": "",
            })

    return results
