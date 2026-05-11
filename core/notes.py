from database import get_connection


def create_note(
    title: str,
    content: str = "",
    tags: str = "",
    source_type: str = "manual",
    original_transcription: str | None = None,
    llm_intent: str | None = None,
    llm_confidence: float | None = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO notes
               (title, content, tags, source_type, original_transcription,
                llm_intent, llm_confidence, created_from_voice)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title.strip(), content, tags.strip(),
                source_type,
                original_transcription,
                llm_intent,
                llm_confidence,
                1 if source_type == "voice" else 0,
            ),
        )
        return cur.lastrowid


def get_note(note_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return dict(row) if row else None


def update_note(note_id: int, title: str, content: str, tags: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE notes SET title=?, content=?, tags=?, updated_at=datetime('now') WHERE id=?",
            (title.strip(), content, tags.strip(), note_id),
        )


def delete_note(note_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))


def list_notes(query: str = "") -> list[dict]:
    with get_connection() as conn:
        if query:
            like = f"%{query}%"
            rows = conn.execute(
                "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? ORDER BY updated_at DESC, id DESC",
                (like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [dict(r) for r in rows]
