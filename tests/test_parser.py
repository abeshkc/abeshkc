import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.parser import parse_datetime


def _close(dt1: datetime, dt2: datetime, minutes: int = 2) -> bool:
    return abs((dt1 - dt2).total_seconds()) < minutes * 60


def test_in_minutes():
    result = parse_datetime("in 30 minutes")
    expected = datetime.now() + timedelta(minutes=30)
    assert result is not None and _close(result, expected), f"Got: {result}"
    print("  PASS test_in_minutes")


def test_in_hours():
    result = parse_datetime("in 2 hours")
    expected = datetime.now() + timedelta(hours=2)
    assert result is not None and _close(result, expected), f"Got: {result}"
    print("  PASS test_in_hours")


def test_in_days():
    result = parse_datetime("in 3 days")
    expected = datetime.now() + timedelta(days=3)
    assert result is not None and _close(result, expected, minutes=5), f"Got: {result}"
    print("  PASS test_in_days")


def test_tomorrow_with_time():
    result = parse_datetime("tomorrow at 3pm")
    assert result is not None
    assert result.hour == 15
    assert result.date() == (datetime.now() + timedelta(days=1)).date(), f"Got: {result}"
    print("  PASS test_tomorrow_with_time")


def test_tomorrow_no_time():
    result = parse_datetime("remind me tomorrow")
    assert result is not None
    assert result.date() == (datetime.now() + timedelta(days=1)).date()
    assert result.hour == 9
    print("  PASS test_tomorrow_no_time")


def test_weekday():
    result = parse_datetime("friday at 9am")
    assert result is not None
    assert result.weekday() == 4, f"Expected Friday (4), got weekday {result.weekday()}"
    assert result.hour == 9
    print("  PASS test_weekday")


def test_bare_time_am_pm():
    result = parse_datetime("5pm")
    assert result is not None
    assert result.hour == 17, f"Got hour: {result.hour}"
    print("  PASS test_bare_time_am_pm")


def test_hh_mm():
    result = parse_datetime("at 14:30")
    assert result is not None
    assert result.hour == 14
    assert result.minute == 30
    print("  PASS test_hh_mm")


def test_today_hhmm_pm():
    # regression: "today at 2:30 pm" was parsed as 02:30 (AM) instead of 14:30
    result = parse_datetime("today at 2:30 pm")
    assert result is not None
    assert result.hour == 14, f"Expected hour 14, got {result.hour}"
    assert result.minute == 30, f"Expected minute 30, got {result.minute}"
    print("  PASS test_today_hhmm_pm")


def test_today_hhmm_am():
    result = parse_datetime("today at 10:15 am")
    assert result is not None
    assert result.hour == 10, f"Expected hour 10, got {result.hour}"
    assert result.minute == 15
    print("  PASS test_today_hhmm_am")


def test_tomorrow_hhmm_pm():
    result = parse_datetime("tomorrow at 1:45 pm")
    assert result is not None
    assert result.hour == 13, f"Expected hour 13, got {result.hour}"
    assert result.minute == 45
    assert result.date() == (datetime.now() + timedelta(days=1)).date()
    print("  PASS test_tomorrow_hhmm_pm")


def test_invalid():
    result = parse_datetime("no date in this sentence at all")
    assert result is None, f"Expected None, got: {result}"
    print("  PASS test_invalid")


if __name__ == "__main__":
    print("Running parser tests...")
    test_in_minutes()
    test_in_hours()
    test_in_days()
    test_tomorrow_with_time()
    test_tomorrow_no_time()
    test_weekday()
    test_bare_time_am_pm()
    test_hh_mm()
    test_today_hhmm_pm()
    test_today_hhmm_am()
    test_tomorrow_hhmm_pm()
    test_invalid()
    print("All parser tests passed.")
