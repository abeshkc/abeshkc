import calendar
from datetime import datetime, timedelta
from database import get_connection

RECURRENCE_TYPES  = ("none", "daily", "weekly", "monthly", "yearly")
IMPORTANCE_LEVELS = ("Low", "Normal", "High", "Urgent")

_IMPORTANCE_RANK = {"Low": 0, "Normal": 1, "High": 2, "Urgent": 3}


def _next_due(due_at: datetime, recurrence_type: str, interval: int) -> datetime:
    if recurrence_type == "daily":
        return due_at + timedelta(days=interval)
    if recurrence_type == "weekly":
        return due_at + timedelta(weeks=interval)
    if recurrence_type == "monthly":
        month = due_at.month - 1 + interval
        year  = due_at.year + month // 12
        month = month % 12 + 1
        day   = min(due_at.day, calendar.monthrange(year, month)[1])
        return due_at.replace(year=year, month=month, day=day)
    if recurrence_type == "yearly":
        return due_at.replace(year=due_at.year + interval)
    return due_at


def create_reminder(
    title: str,
    due_at: datetime,
    message: str = "",
    note_id: int | None = None,
    recurrence_type: str = "none",
    recurrence_interval: int = 1,
    recurrence_end_date: str | None = None,
    importance: str = "Normal",
    remind_before: str = "",
) -> int:
    importance = importance if importance in IMPORTANCE_LEVELS else "Normal"
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO reminders
               (title, due_at, message, note_id,
                recurrence_type, recurrence_interval, recurrence_end_date,
                importance, remind_before)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title.strip(),
                due_at.strftime("%Y-%m-%d %H:%M:%S"),
                message,
                note_id,
                recurrence_type,
                recurrence_interval,
                recurrence_end_date,
                importance,
                remind_before,
            ),
        )
        return cur.lastrowid


def mark_done(reminder_id: int) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "UPDATE reminders SET is_done=1, completed_at=? WHERE id=?",
            (now, reminder_id),
        )
        row = conn.execute(
            "SELECT * FROM reminders WHERE id=?", (reminder_id,)
        ).fetchone()

    if row and row["recurrence_type"] != "none":
        r = dict(row)
        due      = datetime.strptime(r["due_at"], "%Y-%m-%d %H:%M:%S")
        next_due = _next_due(due, r["recurrence_type"], r["recurrence_interval"])
        if r["recurrence_end_date"]:
            end = datetime.strptime(r["recurrence_end_date"], "%Y-%m-%d")
            if next_due > end:
                return
        create_reminder(
            title=r["title"],
            due_at=next_due,
            message=r["message"],
            note_id=r["note_id"],
            recurrence_type=r["recurrence_type"],
            recurrence_interval=r["recurrence_interval"],
            recurrence_end_date=r["recurrence_end_date"],
            importance=r.get("importance", "Normal"),
        )


def delete_reminder(reminder_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))


def list_reminders(
    include_done: bool = False,
    sort_by: str = "due_at",
    ascending: bool = True,
) -> list[dict]:
    with get_connection() as conn:
        where = "" if include_done else "WHERE is_done=0"
        rows = conn.execute(
            f"SELECT * FROM reminders {where}"
        ).fetchall()
    items = [dict(r) for r in rows]

    reverse = not ascending
    if sort_by == "importance":
        items.sort(key=lambda r: _IMPORTANCE_RANK.get(r.get("importance", "Normal"), 1),
                   reverse=reverse)
    elif sort_by == "title":
        items.sort(key=lambda r: r.get("title", "").lower(), reverse=reverse)
    elif sort_by == "created_at":
        items.sort(key=lambda r: r.get("created_at", ""), reverse=reverse)
    else:  # due_at (default)
        items.sort(key=lambda r: r.get("due_at", ""), reverse=reverse)
    return items


def list_done_reminders() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE is_done=1 ORDER BY completed_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_due_reminders() -> list[dict]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE is_done=0 AND due_at <= ?",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]


def count_overdue() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM reminders WHERE is_done=0 AND due_at < ?",
            (now,),
        ).fetchone()
        return row[0] if row else 0
