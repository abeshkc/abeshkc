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
- **Voice-first interface** — app opens on the Voice Assistant tab; speak to create reminders, notes, and appointments

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

### Voice-first workflow

The app opens on the **Voice Assistant** tab. Click 🎙 Start Recording, speak your command, then click Stop.

```
Microphone → Local Whisper (on-device) → Claude API (cloud) → review panel → form / database
```

After recording, the app shows:
- Detected intent and confidence score
- Extracted fields (title, date/time, recurrence, tags…)
- **Insert into form** — fills the Reminders or Notes form; you review and click Create/Save
- **Save after review** — saves after one confirmation dialog
- **Try again** / **Discard** to restart or clear

By default, **nothing is saved automatically** — you always review first.

### Auto-save setting

Toggle **"Auto-save high-confidence voice commands"** at the bottom of the Voice tab.

- **OFF (default):** always asks before saving
- **ON:** skips confirmation for ≥ 85 % confidence create actions (destructive actions still always confirm)

### API keys

Add your Anthropic API key to `.env`:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Audio never leaves your machine. The transcription text is sent to Claude for intent parsing.

If `ANTHROPIC_API_KEY` is missing, the Voice tab shows a clear warning and falls back to a limited rule-based parser automatically.

Ollama and Qwen are **not required**.

### Voice tab — first run

The first time you click **Start Recording**, faster-whisper downloads the selected model (~150 MB for `base`) from Hugging Face. This is a one-time download. Subsequent runs use the cached model.

**Model size guide:**

| Size | RAM | Speed | Accuracy |
|---|---|---|---|
| `tiny` | ~390 MB | fastest | basic |
| `base` | ~550 MB | fast | good (default) |
| `small` | ~1.2 GB | moderate | better |
| `medium` | ~3 GB | slow | best |

Set `WHISPER_MODEL_SIZE=small` in `.env` for better accuracy on accented or fast speech.

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
