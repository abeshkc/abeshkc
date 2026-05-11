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


def test_recurring_daily():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Daily task", due, recurrence_type="daily", recurrence_interval=1)
    mark_done(rid)
    pending = list_reminders(include_done=False)
    assert not any(r["id"] == rid for r in pending), "original should be marked done"
    assert any(r["title"] == "Daily task" and r["is_done"] == 0 for r in pending), \
        "next daily occurrence should exist"
    print("  PASS test_recurring_daily")


def test_done_list():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Done list test", due)
    mark_done(rid)
    done = list_done_reminders()
    assert any(r["id"] == rid for r in done), "completed reminder should appear in done list"
    assert not any(r["id"] == rid for r in list_reminders(include_done=False)), \
        "completed reminder should not appear in upcoming list"
    print("  PASS test_done_list")


def test_completed_at_set():
    due = datetime.now() + timedelta(hours=1)
    rid = create_reminder("Completed at test", due)
    mark_done(rid)
    done = list_done_reminders()
    r = next(x for x in done if x["id"] == rid)
    assert r["completed_at"] is not None, "completed_at should be set after marking done"
    print("  PASS test_completed_at_set")


if __name__ == "__main__":
    print("Running reminder tests...")
    test_create()
    test_mark_done()
    test_delete()
    test_due_reminders()
    test_future_not_due()
    test_recurring_daily()
    test_done_list()
    test_completed_at_set()
    print("All reminder tests passed.")
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
