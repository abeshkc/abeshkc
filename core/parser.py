import re
from datetime import datetime, timedelta


def parse_datetime(text: str) -> datetime | None:
    """Mock NLP parser — extracts a datetime from natural language text."""
    now = datetime.now().replace(second=0, microsecond=0)
    t = text.lower().strip()

    # "in X minutes / hours / days"
    m = re.search(r'\bin\s+(\d+)\s+(minute|hour|day)s?\b', t)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"minute": timedelta(minutes=n), "hour": timedelta(hours=n), "day": timedelta(days=n)}[unit]
        return now + delta

    # "tomorrow [at <time>]"
    if "tomorrow" in t:
        base = (now + timedelta(days=1)).replace(hour=9, minute=0)
        tp = _extract_time(t)
        return base.replace(hour=tp[0], minute=tp[1]) if tp else base

    # "today at <time>"
    if "today" in t:
        tp = _extract_time(t)
        return now.replace(hour=tp[0], minute=tp[1]) if tp else None

    # weekday name ("next friday", "friday", "this monday")
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for idx, name in enumerate(day_names):
        if name in t:
            days_ahead = (idx - now.weekday() + 7) % 7 or 7
            base = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0)
            tp = _extract_time(t)
            return base.replace(hour=tp[0], minute=tp[1]) if tp else base

    # bare time only — today if in the future, tomorrow otherwise
    tp = _extract_time(t)
    if tp:
        candidate = now.replace(hour=tp[0], minute=tp[1])
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    return None


def _extract_time(text: str) -> tuple[int, int] | None:
    # HH:MM [am/pm]  — must check am/pm suffix before returning
    m = re.search(r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', text)
    if m:
        h, minute, suffix = int(m.group(1)), int(m.group(2)), m.group(3)
        if suffix == "pm" and h < 12:
            h += 12
        elif suffix == "am" and h == 12:
            h = 0
        return min(h, 23), minute
    # bare H am / H pm
    m = re.search(r'\b(\d{1,2})\s*(am|pm)\b', text)
    if m:
        h = int(m.group(1))
        if m.group(2) == "pm" and h < 12:
            h += 12
        elif m.group(2) == "am" and h == 12:
            h = 0
        return min(h, 23), 0
    return None
