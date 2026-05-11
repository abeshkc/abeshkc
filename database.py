import sqlite3
import os
from pathlib import Path


def _db_path() -> Path:
    override = os.environ.get("NOTEREMIND_DB")
    if override:
        return Path(override)
    return Path.home() / ".noteremind" / "data.db"


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                content     TEXT    NOT NULL DEFAULT '',
                tags        TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id             INTEGER REFERENCES notes(id) ON DELETE SET NULL,
                title               TEXT    NOT NULL,
                message             TEXT    NOT NULL DEFAULT '',
                due_at              TEXT    NOT NULL,
                is_done             INTEGER NOT NULL DEFAULT 0,
                created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
                recurrence_type     TEXT    NOT NULL DEFAULT 'none',
                recurrence_interval INTEGER NOT NULL DEFAULT 1,
                recurrence_end_date TEXT,
                completed_at        TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_reminders_due
                ON reminders(due_at, is_done);
        """)
    _migrate()


def _migrate() -> None:
    """Add columns introduced after the initial schema — safe to run on existing DBs."""
    new_columns = [
        # reminders — recurrence + done tracking
        "ALTER TABLE reminders ADD COLUMN recurrence_type TEXT NOT NULL DEFAULT 'none'",
        "ALTER TABLE reminders ADD COLUMN recurrence_interval INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE reminders ADD COLUMN recurrence_end_date TEXT",
        "ALTER TABLE reminders ADD COLUMN completed_at TEXT",
        # notes — voice / LLM metadata
        "ALTER TABLE notes ADD COLUMN source_type TEXT NOT NULL DEFAULT 'manual'",
        "ALTER TABLE notes ADD COLUMN original_transcription TEXT",
        "ALTER TABLE notes ADD COLUMN llm_intent TEXT",
        "ALTER TABLE notes ADD COLUMN llm_confidence REAL",
        "ALTER TABLE notes ADD COLUMN created_from_voice INTEGER NOT NULL DEFAULT 0",
        # importance (phase 3)
        "ALTER TABLE reminders ADD COLUMN importance TEXT NOT NULL DEFAULT 'Normal'",
        "ALTER TABLE notes     ADD COLUMN importance TEXT NOT NULL DEFAULT 'Normal'",
    ]
    with get_connection() as conn:
        for sql in new_columns:
            try:
                conn.execute(sql)
            except Exception:
                pass  # column already exists
