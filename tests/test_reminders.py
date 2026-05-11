import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["NOTEREMIND_DB"] = _tmp.name

sys.path.insert(0, str(Path(__file__).parent.parent))
import database
database.init_db()
from core.reminders import (
    create_reminder, list_reminders, list_done_reminders,
    mark_done, delete_reminder, get_due_reminders,
)


def test_create():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Test reminder", due, "a message")
    reminders = list_reminders()
    assert any(r["id"] == rid for r in reminders)
    print("  PASS test_create")


def test_mark_done():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Done test", due)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    assert not any(r["id"] == rid for r in pending)
    print("  PASS test_mark_done")


def test_delete():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Delete me", due)
    delete_reminder(rid)
    all_r = list_reminders(include_done=True)
    assert not any(r["id"] == rid for r in all_r)
    print("  PASS test_delete")


def test_due_reminders():
    past = datetime.now() - timedelta(minutes=5)
    rid = create_reminder("Overdue task", past)
    due = get_due_reminders()
    assert any(r["id"] == rid for r in due)
    print("  PASS test_due_reminders")


def test_future_not_due():
    future = datetime.now() + timedelta(hours=2)
    rid = create_reminder("Future task", future)
    due = get_due_reminders()
    assert not any(r["id"] == rid for r in due)
    print("  PASS test_future_not_due")


# ── Recurrence ────────────────────────────────────────────────────────────────

def test_recurring_daily():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Daily task", due, recurrence_type="daily", recurrence_interval=1)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    assert not any(r["id"] == rid for r in pending), "original should be marked done"
    assert any(r["title"] == "Daily task" and r["is_done"] == 0 for r in pending), \
        "next daily occurrence should exist"
    print("  PASS test_recurring_daily")


def test_recurring_weekly():
    due = datetime(2025, 6, 2, 10, 0, 0)  # Monday
    rid = create_reminder("Weekly task", due, recurrence_type="weekly", recurrence_interval=1)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    next_r = next((r for r in pending if r["title"] == "Weekly task" and r["is_done"] == 0), None)
    assert next_r is not None, "next weekly occurrence should exist"
    actual = datetime.strptime(next_r["due_at"], "%Y-%m-%d %H:%M:%S")
    assert actual == datetime(2025, 6, 9, 10, 0, 0), f"expected 2025-06-09, got {actual}"
    print("  PASS test_recurring_weekly")


def test_recurring_monthly():
    due = datetime(2025, 1, 15, 10, 0, 0)
    rid = create_reminder("Monthly task", due, recurrence_type="monthly", recurrence_interval=1)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    next_r = next((r for r in pending if r["title"] == "Monthly task" and r["is_done"] == 0), None)
    assert next_r is not None, "next monthly occurrence should exist"
    actual = datetime.strptime(next_r["due_at"], "%Y-%m-%d %H:%M:%S")
    assert actual == datetime(2025, 2, 15, 10, 0, 0), f"expected 2025-02-15, got {actual}"
    print("  PASS test_recurring_monthly")


def test_recurring_yearly():
    due = datetime(2025, 3, 10, 9, 0, 0)
    rid = create_reminder("Yearly task", due, recurrence_type="yearly", recurrence_interval=1)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    next_r = next((r for r in pending if r["title"] == "Yearly task" and r["is_done"] == 0), None)
    assert next_r is not None, "next yearly occurrence should exist"
    actual = datetime.strptime(next_r["due_at"], "%Y-%m-%d %H:%M:%S")
    assert actual == datetime(2026, 3, 10, 9, 0, 0), f"expected 2026-03-10, got {actual}"
    print("  PASS test_recurring_yearly")


def test_recurring_custom_interval():
    due = datetime(2025, 5, 1, 8, 0, 0)
    rid = create_reminder("Every 3 days", due, recurrence_type="daily", recurrence_interval=3)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    next_r = next((r for r in pending if r["title"] == "Every 3 days" and r["is_done"] == 0), None)
    assert next_r is not None, "next occurrence should exist"
    actual = datetime.strptime(next_r["due_at"], "%Y-%m-%d %H:%M:%S")
    assert actual == datetime(2025, 5, 4, 8, 0, 0), f"expected 2025-05-04, got {actual}"
    print("  PASS test_recurring_custom_interval")


def test_recurring_monthly_end_of_month():
    # Jan 31 + 1 month must clamp to Feb 28 (2025 is not a leap year)
    due = datetime(2025, 1, 31, 12, 0, 0)
    rid = create_reminder("Month edge", due, recurrence_type="monthly", recurrence_interval=1)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    next_r = next((r for r in pending if r["title"] == "Month edge" and r["is_done"] == 0), None)
    assert next_r is not None, "next monthly occurrence should exist"
    actual = datetime.strptime(next_r["due_at"], "%Y-%m-%d %H:%M:%S")
    assert actual == datetime(2025, 2, 28, 12, 0, 0), f"expected 2025-02-28, got {actual}"
    print("  PASS test_recurring_monthly_end_of_month")


def test_recurring_end_date_stops_series():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    due = datetime.now() - timedelta(hours=2)
    rid = create_reminder(
        "Expired series", due,
        recurrence_type="daily", recurrence_interval=1,
        recurrence_end_date=yesterday,
    )
    mark_done(rid)
    pending = list_reminders(include_done=False)
    assert not any(r["title"] == "Expired series" and r["is_done"] == 0 for r in pending), \
        "no new occurrence should be created after recurrence_end_date"
    print("  PASS test_recurring_end_date_stops_series")


def test_recurring_end_date_allows_within():
    far_future = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder(
        "Active series", due,
        recurrence_type="daily", recurrence_interval=1,
        recurrence_end_date=far_future,
    )
    mark_done(rid)
    pending = list_reminders(include_done=False)
    assert any(r["title"] == "Active series" and r["is_done"] == 0 for r in pending), \
        "new occurrence should be created when next due is within recurrence_end_date"
    print("  PASS test_recurring_end_date_allows_within")


def test_non_recurring_no_next_occurrence():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("One-time task", due, recurrence_type="none")
    mark_done(rid)
    pending = list_reminders(include_done=False)
    assert not any(r["title"] == "One-time task" and r["is_done"] == 0 for r in pending), \
        "non-recurring reminder must not spawn a new occurrence"
    print("  PASS test_non_recurring_no_next_occurrence")


# ── Done tab ──────────────────────────────────────────────────────────────────

def test_done_list():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Done list test", due)
    mark_done(rid)
    done = list_done_reminders()
    assert any(r["id"] == rid for r in done), "completed reminder should appear in done list"
    assert not any(r["id"] == rid for r in list_reminders(include_done=False)), \
        "completed reminder should not appear in upcoming list"
    print("  PASS test_done_list")


def test_done_list_multiple():
    due = datetime.now() + timedelta(hours=1)
    rid1 = create_reminder("Multi done A", due)
    rid2 = create_reminder("Multi done B", due)
    mark_done(rid1)
    mark_done(rid2)
    done_ids = {r["id"] for r in list_done_reminders()}
    assert rid1 in done_ids and rid2 in done_ids, "both completed reminders should be in done list"
    pending_ids = {r["id"] for r in list_reminders(include_done=False)}
    assert rid1 not in pending_ids and rid2 not in pending_ids, \
        "neither should appear in upcoming"
    print("  PASS test_done_list_multiple")


def test_completed_at_set():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Completed at test", due)
    mark_done(rid)
    done = list_done_reminders()
    r = next(x for x in done if x["id"] == rid)
    assert r["completed_at"] is not None, "completed_at should be set after marking done"
    print("  PASS test_completed_at_set")


def test_completed_at_is_recent_datetime():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Timestamp check", due)
    mark_done(rid)
    done = list_done_reminders()
    r = next(x for x in done if x["id"] == rid)
    parsed = datetime.strptime(r["completed_at"], "%Y-%m-%d %H:%M:%S")
    assert (datetime.now() - parsed).total_seconds() < 10, \
        "completed_at should be within the last 10 seconds"
    print("  PASS test_completed_at_is_recent_datetime")


def test_delete_not_in_done():
    # deleted reminders must not appear in done list (delete != mark done)
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Hard delete check", due)
    delete_reminder(rid)
    done_ids = {r["id"] for r in list_done_reminders()}
    all_ids = {r["id"] for r in list_reminders(include_done=True)}
    assert rid not in done_ids and rid not in all_ids, \
        "deleted reminder should not appear anywhere"
    print("  PASS test_delete_not_in_done")


if __name__ == "__main__":
    print("Running reminder tests...")
    # original
    test_create()
    test_mark_done()
    test_delete()
    test_due_reminders()
    test_future_not_due()
    # recurrence
    test_recurring_daily()
    test_recurring_weekly()
    test_recurring_monthly()
    test_recurring_yearly()
    test_recurring_custom_interval()
    test_recurring_monthly_end_of_month()
    test_recurring_end_date_stops_series()
    test_recurring_end_date_allows_within()
    test_non_recurring_no_next_occurrence()
    # done tab
    test_done_list()
    test_done_list_multiple()
    test_completed_at_set()
    test_completed_at_is_recent_datetime()
    test_delete_not_in_done()
    print("All reminder tests passed.")
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
