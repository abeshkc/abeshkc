from database import get_connection

IMPORTANCE_LEVELS = ("Low", "Normal", "High", "Urgent")
_IMPORTANCE_RANK  = {"Low": 0, "Normal": 1, "High": 2, "Urgent": 3}


def create_note(
    title: str,
    content: str = "",
    tags: str = "",
    source_type: str = "manual",
    original_transcription: str | None = None,
    llm_intent: str | None = None,
    llm_confidence: float | None = None,
    importance: str = "Normal",
) -> int:
    importance = importance if importance in IMPORTANCE_LEVELS else "Normal"
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO notes
               (title, content, tags, source_type, original_transcription,
                llm_intent, llm_confidence, created_from_voice, importance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title.strip(), content, tags.strip(),
                source_type,
                original_transcription,
                llm_intent,
                llm_confidence,
                1 if source_type == "voice" else 0,
                importance,
            ),
        )
        return cur.lastrowid


def get_note(note_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return dict(row) if row else None


def update_note(
    note_id: int, title: str, content: str, tags: str,
    importance: str = "Normal",
) -> None:
    importance = importance if importance in IMPORTANCE_LEVELS else "Normal"
    with get_connection() as conn:
        conn.execute(
            "UPDATE notes SET title=?, content=?, tags=?, importance=?, "
            "updated_at=datetime('now') WHERE id=?",
            (title.strip(), content, tags.strip(), importance, note_id),
        )


def delete_note(note_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))


def list_notes(
    query: str = "",
    sort_by: str = "updated_at",
    ascending: bool = False,
) -> list[dict]:
    with get_connection() as conn:
        if query:
            like = f"%{query}%"
            rows = conn.execute(
                "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?",
                (like, like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM notes").fetchall()

    items   = [dict(r) for r in rows]
    reverse = not ascending
    if sort_by == "importance":
        items.sort(key=lambda n: _IMPORTANCE_RANK.get(n.get("importance", "Normal"), 1),
                   reverse=reverse)
    elif sort_by == "title":
        items.sort(key=lambda n: n.get("title", "").lower(), reverse=reverse)
    elif sort_by == "created_at":
        items.sort(key=lambda n: n.get("created_at", ""), reverse=reverse)
    else:  # updated_at (default)
        items.sort(key=lambda n: (n.get("updated_at", ""), n.get("id", 0)), reverse=reverse)
    return items
