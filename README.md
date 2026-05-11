# NoteRemind

A local-first notes and reminders app for Windows.  
All data lives in SQLite at `~/.noteremind/data.db` — no cloud, no accounts.

---

## Features (Phase 1 MVP)

- Create, edit, search, and delete notes with tags
- Create reminders using plain English time input
- Background thread fires Windows toast notifications when reminders are due
- Link reminders to notes
- Overdue reminders highlighted in red
- Deletion confirmation dialog for notes and reminders (prevents accidental loss)
- Recurring reminders — daily, weekly, monthly, yearly (with custom interval); marking done auto-schedules the next occurrence
- Done tab — completed reminders move to a separate tab with `completed_at` timestamp; data is never deleted
- **Voice tab** — speak a command, Whisper transcribes it, Claude parses intent and autonomously creates reminders or meeting notes

---

## Setup (Windows)

**Requirements:** Python 3.11+

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy the env template and add your API keys
copy .env.example .env
# Edit .env and set OPENAI_API_KEY and ANTHROPIC_API_KEY

# 3. Run the app
python main.py
```

### API Keys

| Key | Used for | Required? |
|---|---|---|
| `OPENAI_API_KEY` | Whisper speech-to-text | Only for Voice tab |
| `ANTHROPIC_API_KEY` | Claude intent parsing | Only for Voice tab |

The app runs fully without both keys — they are only needed when you use the **Voice** tab.

### Microphone permissions

Windows should prompt for mic access the first time you click **Start Recording**.  
If recording silently fails, check **Settings → Privacy → Microphone** and ensure the app has access.

---

## Natural Language Time Input

| You type | Parsed as |
|----------|-----------|
| `in 30 minutes` | 30 min from now |
| `in 2 hours` | 2 hours from now |
| `today at 14:30` | Today at 14:30 |
| `tomorrow at 3pm` | Next day at 15:00 |
| `friday at 9am` | Next Friday at 09:00 |
| `5pm` | Today/tomorrow at 17:00 |

---

## Demo Workflow

1. Run `python main.py`
2. Click **Notes** → `+` → type a title and content → **Save**
3. Click **Reminders** → fill in title + "in 5 minutes" → **Create Reminder**
4. A Windows toast notification fires in 5 minutes
5. The reminder turns red if overdue; click **Done** to dismiss it

---

## Running Tests

Each file is self-contained and runnable directly:

```powershell
py tests/test_notes.py
py tests/test_reminders.py
py tests/test_parser.py
py tests/test_voice_pipeline.py   # no API keys needed — fully mocked
```

---

## Project Structure

```
.
├── main.py                  # entry point
├── database.py              # SQLite init (NOTEREMIND_DB env var overrides path)
├── notifications.py         # Windows toast via plyer
├── requirements.txt
├── core/
│   ├── notes.py             # note CRUD
│   ├── reminders.py         # reminder CRUD + due-check
│   └── parser.py            # mock NLP datetime parser (regex)
├── ui/
│   ├── app.py               # CTk main window + sidebar
│   ├── notes_view.py        # notes list + editor
│   └── reminders_view.py    # reminder form + list
└── tests/
    ├── test_notes.py
    ├── test_reminders.py
    └── test_parser.py
```

---

## Database Schema

```sql
notes      (id, title, content, tags, created_at, updated_at,
            source_type, original_transcription, llm_intent, llm_confidence, created_from_voice)
reminders  (id, note_id, title, message, due_at, is_done, created_at,
            recurrence_type, recurrence_interval, recurrence_end_date, completed_at)
```

`source_type` — `manual` (default) or `voice`.  
`original_transcription` — raw Whisper text stored with voice-created notes.  
`recurrence_type` — `none | daily | weekly | monthly | yearly`.  
`completed_at` — set when a reminder is marked done; rows are never hard-deleted.  
Migration is automatic — existing databases are upgraded on first run via `ALTER TABLE`.

---

## Roadmap

**Phase 2 (planned)**
- Claude API for full natural language understanding
- Voice dictation input
- File attachments
- Calendar view for reminders

**Phase 3 (planned)**
- Semantic search with local embeddings
- Recurring reminders
- Meeting summary generation
