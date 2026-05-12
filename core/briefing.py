"""Aria Insight Engine — rich contextual briefing from local database."""
import re
import random
from collections import Counter
from datetime import datetime, timedelta

# ── helpers ───────────────────────────────────────────────────────────────────

_ACTION_WORDS = [
    "follow up", "send", "review", "prepare", "buy", "call",
    "schedule", "contact", "submit", "complete", "finish",
    "need to", "have to", "should", "don't forget",
]

_TOPIC_STOP = {
    "The", "This", "That", "With", "From", "Your", "Have", "Next",
    "Week", "Meeting", "Note", "New", "For", "And", "But", "Also",
    "Will", "Was", "Were", "They", "Their", "When", "Where", "Which",
    "Then", "Than", "Into", "Out", "Back", "All", "Any", "Each",
    "Key", "Main", "Good", "Best", "First", "Last", "One", "Two",
    "Three", "Phase", "Step", "Item", "Team", "Plan", "Date",
}


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d %H:%M:%S")


def _days_ahead(n: int) -> str:
    return (datetime.now() + timedelta(days=n)).strftime("%Y-%m-%d %H:%M:%S")


# ── data gathering ────────────────────────────────────────────────────────────

def get_briefing_data() -> dict:
    """Gather comprehensive briefing stats from the local database."""
    from core.reminders import list_reminders, list_done_reminders
    from core.notes import list_notes

    now    = _now_str()
    today  = _today_str()
    h48    = _days_ahead(2)
    week_e = _days_ahead(7)
    week_s = _days_ago(7)
    prev_s = _days_ago(14)

    all_rem  = list_reminders(include_done=False)
    done_rem = list_done_reminders()
    notes    = list_notes("", sort_by="updated_at", ascending=False)

    overdue  = [r for r in all_rem if r["due_at"] < now]
    today_r  = [r for r in all_rem if r["due_at"].startswith(today) and r["due_at"] >= now]
    h48_r    = [r for r in all_rem if now < r["due_at"] <= h48]
    week_r   = [r for r in all_rem if now < r["due_at"] <= week_e]
    urgent   = [r for r in all_rem if r.get("importance") in ("High", "Urgent")]
    urgent_od = [r for r in overdue if r.get("importance") in ("High", "Urgent")]
    recurring = [r for r in all_rem if r.get("recurrence_type", "none") != "none"]

    # Oldest overdue
    oldest_od = min(overdue, key=lambda r: r["due_at"]) if overdue else None

    # Completed this week vs last week
    done_this_week = [r for r in done_rem if (r.get("completed_at") or "") >= week_s]
    done_prev_week = [r for r in done_rem if prev_s <= (r.get("completed_at") or "") < week_s]

    # Meeting notes (notes with "meeting" in tags or title)
    meeting_notes = [n for n in notes
                     if "meeting" in (n.get("tags") or "").lower()
                     or "meeting" in (n.get("title") or "").lower()]
    recent_meeting = [n for n in meeting_notes
                      if (n.get("updated_at") or "") >= week_s]

    return {
        "hour":              datetime.now().hour,
        "overdue":           overdue,
        "overdue_count":     len(overdue),
        "urgent_overdue":    urgent_od,
        "oldest_overdue":    oldest_od,
        "today_count":       len(today_r),
        "today_reminders":   today_r,
        "h48_reminders":     h48_r,
        "week_reminders":    week_r,
        "week_count":        len(week_r),
        "urgent":            urgent,
        "urgent_count":      len(urgent),
        "recurring":         recurring,
        "done_this_week":    done_this_week,
        "done_prev_week":    done_prev_week,
        "total_notes":       len(notes),
        "notes":             notes,
        "recent_note":       notes[0] if notes else None,
        "meeting_notes":     meeting_notes,
        "recent_meetings":   recent_meeting,
    }


# ── greeting ──────────────────────────────────────────────────────────────────

def generate_greeting(data: dict | None = None) -> str:
    """Generate a rich multi-point greeting from stored data."""
    if data is None:
        data = get_briefing_data()

    hour = data.get("hour", datetime.now().hour)
    if   hour < 12: sal = random.choice(["Good morning.", "Morning.", "Good morning — let's see what's on."])
    elif hour < 17: sal = random.choice(["Good afternoon.", "Afternoon.", "Hope your day's going well."])
    else:           sal = random.choice(["Good evening.", "Evening.", "Winding down for the day?"])

    parts = [sal]

    # Overdue — detailed
    od = data["overdue_count"]
    if od > 0:
        urg = len(data["urgent_overdue"])
        line = f"You have {od} overdue reminder{'s' if od > 1 else ''}"
        if urg:
            line += f", including {urg} marked urgent"
        line += "."
        parts.append(line)
        if data["oldest_overdue"]:
            days_old = (datetime.now() - datetime.strptime(
                data["oldest_overdue"]["due_at"], "%Y-%m-%d %H:%M:%S")).days
            parts.append(
                f"Oldest: \"{data['oldest_overdue']['title'][:32]}\" — {days_old} day{'s' if days_old != 1 else ''} overdue."
            )

    # Today
    elif data["today_count"] > 0:
        parts.append(f"{data['today_count']} reminder{'s' if data['today_count'] > 1 else ''} scheduled for today.")

    # Completed progress
    done_w = len(data["done_this_week"])
    done_p = len(data["done_prev_week"])
    if done_w > 0:
        if done_p > 0 and done_w > done_p:
            parts.append(f"You completed {done_w} tasks this week — more than last week. Nice progress.")
        else:
            parts.append(f"You completed {done_w} task{'s' if done_w != 1 else ''} this week.")

    # Recent meetings
    rm = len(data["recent_meetings"])
    if rm > 0:
        parts.append(f"You wrote {rm} meeting note{'s' if rm != 1 else ''} recently.")

    # Fallback
    if len(parts) == 1:
        parts.append(random.choice([
            "Everything looks clear. Ready when you are.",
            "No reminders pending. What's on your mind?",
            "All caught up. How can I help?",
        ]))

    return "\n".join(parts[:4])  # max 4 lines


# ── note text analysis ────────────────────────────────────────────────────────

def _find_actionable_notes(notes: list) -> list[dict]:
    """Surface notes containing action words (follow up, send, buy, etc.)."""
    found = []
    for note in notes[:25]:
        text = (note.get("content") or "").lower()
        for action in _ACTION_WORDS:
            if action in text:
                # Find the sentence
                for sentence in re.split(r"[.!\n]", text):
                    if action in sentence:
                        snippet = sentence.strip()[:72]
                        if len(snippet) > 12:
                            found.append({
                                "note_id":    note["id"],
                                "note_title": (note.get("title") or "")[:32],
                                "action":     action,
                                "snippet":    snippet,
                            })
                        break
                break  # one action per note
    return found[:4]


def _find_recurring_topics(notes: list) -> list[tuple[str, int]]:
    """Find proper-noun topics mentioned across multiple notes."""
    counts: Counter = Counter()
    for note in notes:
        text = f"{note.get('title', '')} {note.get('content', '')} {note.get('tags', '')}"
        words = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text)
        counts.update(w for w in words if w not in _TOPIC_STOP)
    return [(t, c) for t, c in counts.most_common(8) if c >= 2]


# ── insight card generator ────────────────────────────────────────────────────

_SEEN_TYPES: list[str] = []   # rolling window to reduce repetition


def get_insight_cards(data: dict | None = None,
                      max_cards: int = 4,
                      include_note_analysis: bool = True) -> list[dict]:
    """
    Generate prioritised insight cards for the Aria home panel.
    Each card: {icon, title, body, color, type, action_note_id?}
    Priority: overdue-urgent → due-soon → meetings → note-analysis → progress → encouragement
    """
    global _SEEN_TYPES
    if data is None:
        data = get_briefing_data()

    cards: list[dict] = []

    def add(card: dict) -> None:
        if len(cards) < max_cards:
            cards.append(card)

    # ── 1. Urgent overdue ────────────────────────────────────────────────
    if data["urgent_overdue"]:
        r = data["urgent_overdue"][0]
        days = max(0, (datetime.now() - datetime.strptime(r["due_at"], "%Y-%m-%d %H:%M:%S")).days)
        add({
            "icon": "⚠", "type": "urgent_overdue", "color": "#e74c3c",
            "title": f"Urgent Overdue — {r['title'][:30]}",
            "body":  f"{days} day{'s' if days != 1 else ''} past due. Needs immediate attention.",
            "review_id": r["id"], "review_type": "reminder",
        })

    # ── 2. All overdue summary ───────────────────────────────────────────
    if data["overdue_count"] > 0 and "overdue_summary" not in _SEEN_TYPES[-3:]:
        od = data["overdue"]
        titles = ", ".join(f'"{r["title"][:20]}"' for r in od[:2])
        suffix = f" +{len(od)-2} more" if len(od) > 2 else ""
        add({
            "icon": "📋", "type": "overdue_summary", "color": "#e74c3c",
            "title": f"{data['overdue_count']} Overdue Reminder{'s' if data['overdue_count'] > 1 else ''}",
            "body":  titles + suffix + ". Tap to review.",
        })

    # ── 3. Due in 48 hours ───────────────────────────────────────────────
    if data["h48_reminders"]:
        r = data["h48_reminders"][0]
        due_time = r["due_at"][11:16]
        due_date = r["due_at"][:10]
        add({
            "icon": "⏰", "type": "due_soon", "color": "#e67e22",
            "title": "Due Soon",
            "body":  f"{r['title'][:36]} — {due_date} at {due_time}",
            "review_id": r["id"], "review_type": "reminder",
        })

    # ── 4. Today's schedule ──────────────────────────────────────────────
    if data["today_reminders"] and "today_schedule" not in _SEEN_TYPES[-3:]:
        n   = data["today_count"]
        nxt = data["today_reminders"][0]
        add({
            "icon": "📅", "type": "today_schedule", "color": "#3B8ED0",
            "title": f"{n} Reminder{'s' if n > 1 else ''} Today",
            "body":  f"Next: {nxt['title'][:30]} at {nxt['due_at'][11:16]}",
        })

    # ── 5. Upcoming this week ────────────────────────────────────────────
    if data["week_count"] > 0 and not data["today_reminders"] and len(cards) < max_cards:
        add({
            "icon": "🗓", "type": "upcoming_week", "color": "#5d8dbb",
            "title": f"{data['week_count']} Coming This Week",
            "body":  f"Next: {data['week_reminders'][0]['title'][:34]}",
        })

    # ── 6. Recent meetings ───────────────────────────────────────────────
    if data["recent_meetings"] and len(cards) < max_cards:
        n = len(data["recent_meetings"])
        note = data["recent_meetings"][0]
        add({
            "icon": "🤝", "type": "recent_meetings", "color": "#27ae60",
            "title": f"{n} Recent Meeting Note{'s' if n > 1 else ''}",
            "body":  f"Latest: {note['title'][:36]}",
            "review_id": note["id"], "review_type": "note",
        })

    # ── 7. Note text analysis ────────────────────────────────────────────
    if include_note_analysis and len(cards) < max_cards:
        actionable = _find_actionable_notes(data["notes"])
        if actionable and "note_action" not in _SEEN_TYPES[-4:]:
            a = actionable[0]
            add({
                "icon": "💡", "type": "note_action", "color": "#e67e22",
                "title": f"Possible Follow-up — {a['note_title']}",
                "body":  f"\"{a['snippet']}...\"",
                "review_id": a["note_id"], "review_type": "note",
            })

    # ── 8. Recurring topic ───────────────────────────────────────────────
    if include_note_analysis and len(cards) < max_cards:
        topics = _find_recurring_topics(data["notes"])
        if topics and "topic_cluster" not in _SEEN_TYPES[-4:]:
            top_topic, count = topics[0]
            add({
                "icon": "🔁", "type": "topic_cluster", "color": "#5d8dbb",
                "title": f"Recurring Topic — {top_topic}",
                "body":  f"Mentioned across {count} notes. Worth reviewing?",
            })

    # ── 9. Progress comparison ───────────────────────────────────────────
    if len(cards) < max_cards:
        dw = len(data["done_this_week"])
        dp = len(data["done_prev_week"])
        if dw > 0 and "progress" not in _SEEN_TYPES[-4:]:
            if dp > 0:
                diff = dw - dp
                trend = f"{'↑' if diff > 0 else '↓' if diff < 0 else '='} {abs(diff)} vs last week"
            else:
                trend = "first week tracked"
            add({
                "icon": "✅", "type": "progress", "color": "#27ae60",
                "title": f"{dw} Task{'s' if dw != 1 else ''} Completed This Week",
                "body":  trend,
            })

    # ── 10. Recurring reminders notice ──────────────────────────────────
    if data["recurring"] and len(cards) < max_cards and "recurring" not in _SEEN_TYPES[-4:]:
        n = len(data["recurring"])
        r = data["recurring"][0]
        add({
            "icon": "↻", "type": "recurring", "color": "#5d8dbb",
            "title": f"{n} Recurring Reminder{'s' if n > 1 else ''}",
            "body":  f"e.g. {r['title'][:34]} ({r['recurrence_type']})",
        })

    # ── 11. All clear / encouragement ───────────────────────────────────
    if not cards:
        add({
            "icon": "✦", "type": "clear", "color": "#5d8dbb",
            "title": "All Clear",
            "body": random.choice([
                "Nothing pending. What would you like to work on?",
                "Your schedule looks open. Ready when you are.",
                "Everything's under control. How can I help?",
            ]),
        })

    # Track seen types for variety
    _SEEN_TYPES.extend(c["type"] for c in cards)
    if len(_SEEN_TYPES) > 20:
        _SEEN_TYPES = _SEEN_TYPES[-20:]

    return cards


# ── legacy helpers (kept for compatibility) ───────────────────────────────────

def generate_greeting_simple(data: dict | None = None) -> str:
    return generate_greeting(data)


def get_briefing_bullets(data: dict | None = None) -> list[str]:
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
