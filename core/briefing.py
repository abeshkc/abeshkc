"""Aria engagement engine — generates greetings and daily briefing from local data."""
import random
from datetime import datetime, timedelta


def get_briefing_data() -> dict:
    """Gather daily briefing stats from stored data."""
    from core.reminders import list_reminders
    from core.notes import list_notes

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")
    week_end = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    all_rem = list_reminders(include_done=False)
    overdue  = [r for r in all_rem if r["due_at"] < now_str]
    today    = [r for r in all_rem if r["due_at"].startswith(today_str)]
    this_week = [r for r in all_rem if now_str < r["due_at"] <= week_end]
    urgent   = [r for r in all_rem if r.get("importance") in ("High", "Urgent")]

    notes = list_notes("", sort_by="updated_at", ascending=False)
    recent_note = notes[0] if notes else None

    return {
        "overdue_count":  len(overdue),
        "today_count":    len(today),
        "week_count":     len(this_week),
        "urgent_count":   len(urgent),
        "total_reminders": len(all_rem),
        "total_notes":    len(notes),
        "recent_note":    recent_note,
        "hour":           now.hour,
    }


def generate_greeting(data: dict | None = None) -> str:
    """Return a warm, contextual greeting string (max 2 sentences)."""
    if data is None:
        data = get_briefing_data()

    hour = data.get("hour", datetime.now().hour)
    if hour < 12:
        salutation = random.choice([
            "Good morning.", "Morning — let's get started.", "Good morning.",
        ])
    elif hour < 17:
        salutation = random.choice([
            "Good afternoon.", "Afternoon.", "Hope the day's going well.",
        ])
    else:
        salutation = random.choice([
            "Good evening.", "Evening.", "Winding down?",
        ])

    lines = [salutation]

    if data["overdue_count"] > 0:
        n = data["overdue_count"]
        lines.append(random.choice([
            f"You have {n} overdue reminder{'s' if n > 1 else ''} waiting.",
            f"{n} item{'s' if n > 1 else ''} past due — worth checking.",
        ]))
    elif data["today_count"] > 0:
        n = data["today_count"]
        lines.append(f"{n} reminder{'s' if n > 1 else ''} scheduled for today.")
    elif data["week_count"] > 0:
        n = data["week_count"]
        lines.append(f"{n} thing{'s' if n > 1 else ''} coming up this week.")
    elif data["total_notes"] > 0 and data["recent_note"]:
        title = (data["recent_note"]["title"] or "")[:28]
        if title:
            lines.append(f"Last note: \"{title}\".")
    else:
        lines.append(random.choice([
            "Everything looks clear — ready when you are.",
            "Nothing pending. What's on your mind?",
            "All caught up. How can I help?",
        ]))

    return "\n".join(lines[:2])


def get_briefing_bullets(data: dict | None = None) -> list[str]:
    """Return short bullet-point items for the Daily Briefing panel."""
    if data is None:
        data = get_briefing_data()

    bullets: list[str] = []

    if data["overdue_count"] > 0:
        bullets.append(f"⚠  {data['overdue_count']} overdue")
    if data["today_count"] > 0:
        bullets.append(f"📅  {data['today_count']} today")
    elif data["week_count"] > 0:
        bullets.append(f"📅  {data['week_count']} this week")
    if data["urgent_count"] > 0:
        bullets.append(f"🔴  {data['urgent_count']} urgent")
    if data["recent_note"]:
        title = (data["recent_note"]["title"] or "")[:22]
        if title:
            bullets.append(f"📝  {title}")
    if not bullets:
        bullets.append("✓  All clear")

    return bullets


def get_insight_cards() -> list[dict]:
    """
    Generate proactive insight cards for the Aria home screen.
    Each card: {"icon", "title", "body", "color", "type"}
    Called every 10 minutes to surface relevant info.
    """
    from core.reminders import list_reminders, list_done_reminders
    from core.notes import list_notes

    now      = datetime.now()
    now_str  = now.strftime("%Y-%m-%d %H:%M:%S")
    today    = now.strftime("%Y-%m-%d")
    week_end = (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    all_rem   = list_reminders(include_done=False)
    done_rem  = list_done_reminders()
    overdue   = [r for r in all_rem if r["due_at"] < now_str]
    today_rem = [r for r in all_rem if r["due_at"].startswith(today)]
    urgent    = [r for r in all_rem if r.get("importance") in ("High", "Urgent")]
    upcoming  = [r for r in all_rem if now_str < r["due_at"] <= week_end]
    notes     = list_notes("", sort_by="updated_at", ascending=False)

    cards: list[dict] = []

    # Overdue items — most important
    if overdue:
        n = len(overdue)
        titles = ", ".join(r["title"] for r in overdue[:2])
        suffix = f" and {n - 2} more" if n > 2 else ""
        cards.append({
            "icon":  "⚠",
            "title": f"{n} Overdue Reminder{'s' if n > 1 else ''}",
            "body":  titles + suffix,
            "color": "#e74c3c",
            "type":  "overdue",
        })

    # Today's schedule
    if today_rem:
        n = len(today_rem)
        nxt = today_rem[0]
        due_time = nxt["due_at"][11:16]
        cards.append({
            "icon":  "📅",
            "title": f"{n} Reminder{'s' if n > 1 else ''} Today",
            "body":  f"Next: {nxt['title']} at {due_time}",
            "color": "#3B8ED0",
            "type":  "today",
        })

    # Urgent items (not overdue)
    non_overdue_urgent = [r for r in urgent if r["due_at"] >= now_str]
    if non_overdue_urgent:
        r = non_overdue_urgent[0]
        cards.append({
            "icon":  "🔴",
            "title": "Urgent Item",
            "body":  f"{r['title']} — due {r['due_at'][:10]}",
            "color": "#e67e22",
            "type":  "urgent",
        })

    # Upcoming this week
    if upcoming and not today_rem:
        n = len(upcoming)
        nxt = upcoming[0]
        due_date = nxt["due_at"][:10]
        cards.append({
            "icon":  "🗓",
            "title": f"{n} Coming This Week",
            "body":  f"Next: {nxt['title']} on {due_date}",
            "color": "#5d8dbb",
            "type":  "upcoming",
        })

    # Recent notes
    if notes:
        n = notes[0]
        snippet = (n.get("content") or "")[:60].strip()
        cards.append({
            "icon":  "📝",
            "title": f"Last Note — {n['title'][:28] or '(untitled)'}",
            "body":  snippet if snippet else "No content.",
            "color": "#27ae60",
            "type":  "note",
        })

    # Done this week (encouragement)
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    done_week  = [r for r in done_rem
                  if r.get("completed_at", "") >= week_start]
    if done_week:
        n = len(done_week)
        cards.append({
            "icon":  "✅",
            "title": f"{n} Completed This Week",
            "body":  random.choice([
                "Nice progress — keep it up.",
                "Great work staying on track.",
                "You're on a roll.",
            ]),
            "color": "#27ae60",
            "type":  "done",
        })

    # All clear
    if not cards:
        cards.append({
            "icon":  "✦",
            "title": "All Clear",
            "body":  random.choice([
                "Nothing pending. What would you like to work on?",
                "Your schedule is open. Ready when you are.",
            ]),
            "color": "#5d8dbb",
            "type":  "clear",
        })

    return cards
