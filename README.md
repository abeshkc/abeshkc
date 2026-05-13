# Aria — AI-Powered Notes & Reminders

A local-first productivity desktop app for Windows featuring a conversational AI assistant (Aria) that understands voice and text commands to create, search, open, edit, and manage notes and reminders in natural language.

All data is stored locally in SQLite — no accounts, no cloud sync required.

---

## Project Objectives

- Build a fully local, privacy-respecting notes and reminders application for Windows
- Integrate a conversational AI layer (Aria) so users can interact with their data through natural speech or typed commands instead of forms
- Implement a complete voice pipeline: on-device speech recognition → cloud intent parsing → structured action execution
- Provide proactive AI insights that surface overdue tasks, upcoming deadlines, and actionable patterns without user prompting
- Support a full editing workflow: search → open → read → edit → save/close, entirely through voice or text

---

## Key Features

### Aria AI Assistant
- Holographic animated avatar with idle, listening, processing, and thinking states
- Voice input via on-device Whisper transcription (no audio ever sent to the cloud)
- Intent parsing via Claude API — extracts structured fields (title, datetime, importance, recurrence, tags) from free-form speech
- Typed command input as a full alternative to voice — same pipeline, same intents
- Compact **AriaBar** embedded in every view so users never leave the current screen to issue a command
- Confidence-based workflow: high-confidence commands auto-save; ambiguous commands route to a review panel

### Conversational Editing
Full create → search → open → edit → save/close workflow through natural language:

| Command | Effect |
|---|---|
| `"Find my notes about Stanford"` | AI search across notes and reminders |
| `"Open the note titled Stanford Engineering"` | Navigates to and opens the note in edit mode |
| `"Add this to the note: LLMs are fun"` | Appends text to the active note |
| `"Change the title to Stanford AI Notes"` | Updates the title field |
| `"Set importance to urgent"` | Updates importance level |
| `"Save and close"` | Saves the active item and clears the editor |
| `"Close this note"` | Warns on unsaved changes, then clears |

### Active Editing Context
Aria tracks which note or reminder is currently open and applies follow-up commands to it automatically:
- Editing banner shows current item title and unsaved-changes indicator
- Flash animation highlights content when Aria updates it
- Context propagates across all views via a shared `AriaContext` object

### Proactive AI Insights
Aria generates up to 11 insight card types without user prompting, refreshed every 60 minutes:
- Urgent overdue tasks, due-soon reminders, today's schedule
- Meeting note summaries, topic clusters, actionable note detection
- Weekly completion progress vs. prior week
- Recurring reminder tracking, all-clear confirmation

### Notes
- Create, edit, search, delete with title, content, tags, date, and importance
- Sort by updated date, created date, importance, or title
- Voice-created notes store the original transcription and parsed intent for reference

### Reminders
- Natural language time input ("tomorrow at 3pm", "in 2 hours", "friday 9am")
- Importance levels: Low / Normal / High / Urgent
- Recurring reminders: daily, weekly, monthly, yearly with custom intervals
- Remind-before alerts: 5 min, 15 min, 30 min, 1 hr, 3 hrs, 1 day
- Link reminders to notes
- Completed reminders move to a Done tab — data is never hard-deleted
- In-app popup + Windows toast notification on due

### AI Search
- Full-text search across both notes and reminders from a single query
- Accessible via voice command, typed command, or search bar
- Results display type, importance, date, and snippet; click to open directly in the editor

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.11+ | Application runtime |
| **UI Framework** | CustomTkinter (CTk) | Dark-mode desktop UI with modern widgets |
| **Database** | SQLite via `sqlite3` | Local-first data persistence |
| **Speech-to-Text** | faster-whisper (local) | On-device Whisper transcription — audio never leaves the machine |
| **Intent Parsing** | Anthropic Claude API (`claude-sonnet-4-6`) | Structured JSON intent extraction from natural language with prompt caching |
| **Notifications** | plyer | Windows toast notifications |
| **Audio Capture** | sounddevice + scipy + numpy | 16 kHz microphone recording with real-time waveform visualisation |
| **Animation** | tkinter Canvas | Aria avatar (holographic body, orbiting particles, blinking eyes) and waveform bars |

### AI / NLP Pipeline

```
Microphone
    │
    ▼
sounddevice (16 kHz WAV)
    │
    ▼
faster-whisper (on-device)  ←── no audio sent to cloud
    │  transcription text
    ▼
Claude API (claude-sonnet-4-6)
    │  structured JSON intent
    ▼
Intent Router
    ├── create_note / create_reminder / create_meeting_note
    ├── search / search_note / search_reminder
    ├── open_note / open_reminder
    ├── update_note / update_reminder
    ├── append_note / append_reminder
    └── save_active_item / close_active_item
    │
    ▼
UI action (fill form / open editor / append text / save / close)
```

Claude's system prompt uses **ephemeral prompt caching** to minimise API latency and cost on repeated calls.

If `ANTHROPIC_API_KEY` is not set, the pipeline automatically falls back to a regex rule-based parser so the app remains functional offline.

---

## Architecture

```
aria-notes/
├── main.py                      # Entry point — DB init, reminder daemon, UI launch
├── database.py                  # SQLite schema + migration (NOTEREMIND_DB env override)
├── notifications.py             # Windows toast via plyer
│
├── core/
│   ├── notes.py                 # Note CRUD (create, get, update, delete, list)
│   ├── reminders.py             # Reminder CRUD + recurrence logic + due-check
│   ├── parser.py                # Regex datetime parser ("tomorrow at 9pm", "in 2 hours")
│   ├── briefing.py              # Aria insights engine — 11 proactive card types
│   └── aria_settings.py         # Persistent Aria configuration (JSON)
│
├── services/
│   ├── intent_parser.py         # Claude API call — returns structured intent JSON
│   ├── audio_recorder.py        # Microphone capture via sounddevice
│   ├── speech_to_text.py        # Wrapper delegating to local Whisper
│   └── local_whisper_service.py # faster-whisper model loading + transcription
│
├── ui/
│   ├── app.py                   # Main window, sidebar navigation, callback routing
│   ├── aria_context.py          # Shared editing state (active note/reminder, dirty flag)
│   ├── aria_bar.py              # Compact Aria command bar — embedded in every view
│   ├── aria_avatar.py           # Animated holographic Aria avatar (Canvas)
│   ├── aria_settings_panel.py   # Aria settings modal
│   ├── voice_panel.py           # Full Aria voice/text panel with insights dashboard
│   ├── notes_view.py            # Notes list + editor with voice-edit methods
│   ├── reminders_view.py        # Reminders list + edit form with voice-edit methods
│   └── reminder_popup.py        # In-app reminder alert dialog
│
└── tests/
    ├── test_notes.py            # Note CRUD tests
    ├── test_reminders.py        # Reminder + recurrence tests
    ├── test_parser.py           # Datetime parser tests
    └── test_voice_pipeline.py   # Voice pipeline tests (all mocked — no API key needed)
```

---

## Database Schema

```sql
notes (
    id                    INTEGER PRIMARY KEY,
    title                 TEXT,
    content               TEXT,
    tags                  TEXT,
    created_at            TEXT,
    updated_at            TEXT,
    source_type           TEXT,   -- "manual" | "voice"
    original_transcription TEXT,  -- raw Whisper output for voice notes
    llm_intent            TEXT,   -- Claude-parsed intent
    llm_confidence        REAL,
    created_from_voice    INTEGER,
    importance            TEXT,   -- "Low" | "Normal" | "High" | "Urgent"
    note_date             TEXT
)

reminders (
    id                    INTEGER PRIMARY KEY,
    title                 TEXT,
    due_at                TEXT,
    message               TEXT,
    note_id               INTEGER,  -- FK → notes.id
    is_done               INTEGER,
    created_at            TEXT,
    recurrence_type       TEXT,     -- "none" | "daily" | "weekly" | "monthly" | "yearly"
    recurrence_interval   INTEGER,
    recurrence_end_date   TEXT,
    completed_at          TEXT,
    importance            TEXT,
    remind_before         TEXT      -- comma-separated minutes, e.g. "15,60,1440"
)
```

Schema migrations run automatically on startup via `ALTER TABLE` — existing databases are upgraded without data loss.

---

## Setup

**Requirements:** Python 3.11+, Windows (toast notifications), microphone (optional)

```powershell
# 1. Clone and install dependencies
git clone https://github.com/abeshkc/abeshkc.git
cd abeshkc
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env
# Open .env and add your Anthropic API key

# 3. Run
python main.py
```

### Environment Variables (`.env`)

```env
# Required for AI intent parsing
ANTHROPIC_API_KEY=your_key_here

# Whisper model size: tiny | base (default) | small | medium
WHISPER_MODEL_SIZE=base

# Device: cpu (default) | cuda
WHISPER_DEVICE=cpu
```

On first voice use, faster-whisper downloads the selected model (~150–550 MB) from Hugging Face. This is a one-time download.

| Model | RAM | Accuracy |
|---|---|---|
| `tiny` | ~390 MB | Basic |
| `base` | ~550 MB | Good (default) |
| `small` | ~1.2 GB | Better |
| `medium` | ~3 GB | Best |

---

## Running Tests

All tests are self-contained — no API keys or microphone needed.

```powershell
python tests/test_notes.py
python tests/test_reminders.py
python tests/test_parser.py
python tests/test_voice_pipeline.py   # fully mocked — no API key required
```

---

## Natural Language Time Input

| Input | Parsed as |
|---|---|
| `in 30 minutes` | 30 min from now |
| `in 2 hours` | 2 hours from now |
| `today at 14:30` | Today at 14:30 |
| `tomorrow at 3pm` | Next day at 15:00 |
| `friday at 9am` | Next Friday at 09:00 |
| `5pm` | Today at 17:00 (tomorrow if already past) |

---

## Voice & Typed Command Examples

```
"Find my notes about the budget"
"Open the note titled Stanford Engineering"
"Add this to the note: also review the Q2 figures"
"Change the title to Stanford AI Research"
"Set importance to urgent"
"Save"
"Save and close"

"Remind me to send the report tomorrow at 9am"
"Set a recurring weekly reminder to review the backlog"
"Find urgent reminders"
"Open the reminder about the dentist"
"Change the time to 5pm"
"Mark this as high priority"
```

---

## Privacy

- **Audio** is processed entirely on-device by faster-whisper. No audio is ever transmitted.
- **Transcription text** is sent to the Claude API for intent parsing.
- **All data** (notes, reminders) is stored locally in `~/.noteremind/data.db`.
- No account, login, or telemetry of any kind.
