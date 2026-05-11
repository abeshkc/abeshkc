# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: NoteRemind

Local-first notes + reminders app for Windows. Stack: Python 3.11+ · CustomTkinter · SQLite.

### Running

```powershell
pip install -r requirements.txt
python main.py
```

### Architecture

| File | Role |
|---|---|
| `main.py` | Entry point — inits DB, starts background reminder thread, opens UI |
| `database.py` | SQLite setup; reads `NOTEREMIND_DB` env var to override DB path (used in tests) |
| `notifications.py` | Windows toast via plyer |
| `core/notes.py` | Note CRUD |
| `core/reminders.py` | Reminder CRUD + `get_due_reminders()` |
| `core/parser.py` | Mock NLP datetime parser (regex) — replace with Claude API in Phase 2 |
| `ui/app.py` | CTk main window + sidebar navigation |
| `ui/notes_view.py` | Notes list + editor panel |
| `ui/reminders_view.py` | Reminder create form + list |

### Tests

Run each file directly — no pytest needed:

```powershell
python tests/test_notes.py
python tests/test_reminders.py
python tests/test_parser.py
```

### Database

SQLite at `~/.noteremind/data.db`. Tables: `notes`, `reminders`.  
Set `NOTEREMIND_DB=<path>` to point at a different file (tests use temp files this way).

## Git / GitHub — always commit and push

**Every session, every change — commit and push. No exceptions.**

- After every code change, run `git add -A`, commit with a descriptive message, and push to `origin master`
- A `Stop` hook in `.claude/settings.json` does this automatically after each Claude response
- If the hook hasn't fired or a manual commit is needed: `git add -A && git commit -m "<description>" && git push origin master`
- Never leave a session with uncommitted changes — the goal is that GitHub always reflects the current state

Remote: `https://github.com/abeshkc/abeshkc.git` — branch `master`.
