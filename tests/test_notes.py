import sys
import os
import tempfile
from pathlib import Path

# Set temp DB before any app imports
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["NOTEREMIND_DB"] = _tmp.name

sys.path.insert(0, str(Path(__file__).parent.parent))
import database
database.init_db()
from core.notes import create_note, get_note, update_note, delete_note, list_notes


def test_create_and_get():
    nid = create_note("Hello", "World", "test")
    note = get_note(nid)
    assert note is not None
    assert note["title"] == "Hello"
    assert note["content"] == "World"
    assert note["tags"] == "test"
    print("  PASS test_create_and_get")


def test_update():
    nid = create_note("Old Title")
    update_note(nid, "New Title", "New content", "tag1")
    note = get_note(nid)
    assert note["title"] == "New Title"
    assert note["content"] == "New content"
    print("  PASS test_update")


def test_delete():
    nid = create_note("To delete")
    delete_note(nid)
    assert get_note(nid) is None
    print("  PASS test_delete")


def test_search():
    create_note("Python tips", "Use list comprehensions", "python")
    create_note("JavaScript tips", "Use arrow functions", "js")
    results = list_notes("Python")
    assert any("Python" in r["title"] for r in results)
    assert not any("JavaScript" in r["title"] for r in results if "Python" not in r["title"])
    print("  PASS test_search")


def test_list_newest_first():
    nid1 = create_note("First note")
    nid2 = create_note("Second note")
    notes = list_notes()
    ids = [n["id"] for n in notes]
    assert ids.index(nid2) < ids.index(nid1)
    print("  PASS test_list_newest_first")


if __name__ == "__main__":
    print("Running note tests...")
    test_create_and_get()
    test_update()
    test_delete()
    test_search()
    test_list_newest_first()
    print("All note tests passed.")
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
