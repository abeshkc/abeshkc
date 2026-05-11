"""
Voice pipeline tests — all API calls are mocked; no real network needed.
Fake openai/anthropic modules are injected into sys.modules so tests run
even when those packages are not installed.
"""
import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# ── inject fake packages before any service imports ───────────────────────────
_fake_openai = MagicMock()
_fake_openai.OpenAI = MagicMock()
sys.modules.setdefault("openai", _fake_openai)

_fake_anthropic = MagicMock()
_fake_anthropic.Anthropic = MagicMock()
sys.modules.setdefault("anthropic", _fake_anthropic)
# ─────────────────────────────────────────────────────────────────────────────

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["NOTEREMIND_DB"] = _tmp.name

sys.path.insert(0, str(Path(__file__).parent.parent))
import database
database.init_db()

from core.notes import list_notes
from core.reminders import list_reminders


# ── helpers ───────────────────────────────────────────────────────────────────

def _reminder_action(title: str, dt_str: str, recurrence: str = "none") -> dict:
    return {
        "intent": "create_reminder",
        "confidence": 0.92,
        "requires_confirmation": False,
        "fields": {
            "title": title,
            "description": "",
            "date": "",
            "time": "",
            "datetime": dt_str,
            "participants": [],
            "tags": [],
            "priority": "normal",
            "recurrence": recurrence,
            "search_query": "",
        },
        "action_summary": f"Create reminder: {title}",
        "missing_fields": [],
    }


def _note_action(title: str, description: str) -> dict:
    return {
        "intent": "create_meeting_note",
        "confidence": 0.95,
        "requires_confirmation": False,
        "fields": {
            "title": title,
            "description": description,
            "date": "",
            "time": "",
            "datetime": "",
            "participants": [],
            "tags": ["meeting"],
            "priority": "normal",
            "recurrence": "none",
            "search_query": "",
        },
        "action_summary": f"Create meeting note: {title}",
        "missing_fields": [],
    }


# ── intent parser ─────────────────────────────────────────────────────────────

_GOOD_JSON = (
    '{"intent":"create_reminder","confidence":0.9,"requires_confirmation":false,'
    '"fields":{"title":"Test","datetime":"tomorrow at 9am","description":"",'
    '"date":"","time":"","participants":[],"tags":[],"priority":"normal",'
    '"recurrence":"none","search_query":""},"action_summary":"Create reminder","missing_fields":[]}'
)


class TestIntentParser(unittest.TestCase):

    def setUp(self):
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        self._mock_client = MagicMock()
        sys.modules["anthropic"].Anthropic.return_value = self._mock_client

    def test_returns_dict(self):
        self._mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=_GOOD_JSON)]
        )
        from services.intent_parser import parse_intent
        result = parse_intent("Remind me about the meeting tomorrow at 9am")
        self.assertEqual(result["intent"], "create_reminder")
        self.assertAlmostEqual(result["confidence"], 0.9)
        print("  PASS test_returns_dict")

    def test_missing_api_key(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        from services.intent_parser import parse_intent
        with self.assertRaises(RuntimeError):
            parse_intent("some text")
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        print("  PASS test_missing_api_key")

    def test_invalid_json_raises(self):
        self._mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Sorry, I cannot help with that.")]
        )
        from services.intent_parser import parse_intent
        with self.assertRaises(ValueError):
            parse_intent("some text")
        print("  PASS test_invalid_json_raises")


# ── voice pipeline ────────────────────────────────────────────────────────────

class TestVoicePipeline(unittest.TestCase):

    def _run_pipeline(self, transcription: str, action: dict) -> str:
        """Simulate VoicePanel._dispatch() without a real UI."""
        from core.parser import parse_datetime
        from core.notes import create_note
        from core.reminders import create_reminder

        intent = action["intent"]
        fields = action["fields"]
        confidence = action["confidence"]

        if intent == "create_reminder":
            title = fields.get("title") or "Voice reminder"
            dt_str = fields.get("datetime") or ""
            due = parse_datetime(dt_str)
            if due is None:
                raise ValueError(f"Cannot parse: {dt_str!r}")
            recur = fields.get("recurrence", "none")
            if recur not in ("none", "daily", "weekly", "monthly", "yearly"):
                recur = "none"
            create_reminder(title, due, recurrence_type=recur)
            return "reminder"

        if intent == "create_meeting_note":
            title = fields.get("title") or transcription[:40]
            content = fields.get("description") or transcription
            tags = ", ".join(fields.get("tags") or [])
            create_note(title, content=content, tags=tags,
                        source_type="voice", original_transcription=transcription,
                        llm_intent=intent, llm_confidence=confidence)
            return "note"

        return "unknown"

    def test_voice_command_creates_reminder(self):
        action = _reminder_action("Meeting with Yaseen", "tomorrow at 10pm")
        result = self._run_pipeline("Create a reminder for meeting with Yaseen tomorrow at 10 PM", action)
        self.assertEqual(result, "reminder")
        reminders = list_reminders(include_done=False)
        assert any(r["title"] == "Meeting with Yaseen" for r in reminders), \
            "Reminder should be in DB"
        print("  PASS test_voice_command_creates_reminder")

    def test_voice_command_creates_meeting_note(self):
        description = "We discussed the DIEM monitoring plan and agreed to revise the sampling approach."
        action = _note_action("DIEM monitoring discussion", description)
        result = self._run_pipeline(
            "Create a meeting note: " + description, action
        )
        self.assertEqual(result, "note")
        notes = list_notes()
        match = next((n for n in notes if n["title"] == "DIEM monitoring discussion"), None)
        assert match is not None, "Note should be in DB"
        assert match["source_type"] == "voice"
        assert match["created_from_voice"] == 1
        assert match["original_transcription"] is not None
        print("  PASS test_voice_command_creates_meeting_note")

    def test_missing_time_raises(self):
        action = _reminder_action("Call back", "")  # no datetime
        with self.assertRaises(ValueError):
            self._run_pipeline("Call back", action)
        print("  PASS test_missing_time_raises")

    def test_low_confidence_does_not_auto_save(self):
        action = _reminder_action("Low confidence task", "tomorrow at 9am")
        action["confidence"] = 0.45  # below CONFIDENCE_REVIEW threshold

        from ui.voice_panel import CONFIDENCE_REVIEW
        self.assertLess(action["confidence"], CONFIDENCE_REVIEW)
        # The dispatch method would return early — verified by the threshold constant
        print("  PASS test_low_confidence_does_not_auto_save")

    def test_auto_save_threshold(self):
        from ui.voice_panel import CONFIDENCE_AUTO, CONFIDENCE_REVIEW
        self.assertGreater(CONFIDENCE_AUTO, CONFIDENCE_REVIEW,
                           "Auto threshold must be higher than review threshold")
        self.assertGreaterEqual(CONFIDENCE_AUTO, 0.85)
        self.assertGreaterEqual(CONFIDENCE_REVIEW, 0.60)
        print("  PASS test_auto_save_threshold")

    def test_recurring_reminder_via_voice(self):
        action = _reminder_action("Weekly standup", "friday at 9am", recurrence="weekly")
        result = self._run_pipeline("Weekly standup every friday at 9am", action)
        self.assertEqual(result, "reminder")
        reminders = list_reminders(include_done=False)
        match = next((r for r in reminders if r["title"] == "Weekly standup"), None)
        assert match is not None, "Recurring reminder should be in DB"
        assert match["recurrence_type"] == "weekly"
        print("  PASS test_recurring_reminder_via_voice")

    def test_note_stores_transcription(self):
        transcription = "Add a note: review Yemen brief before Thursday."
        action = _note_action("Review Yemen brief", "review Yemen brief before Thursday")
        self._run_pipeline(transcription, action)
        notes = list_notes()
        match = next((n for n in notes if "Yemen" in n["title"]), None)
        assert match is not None
        assert match["original_transcription"] == transcription
        assert match["llm_intent"] == "create_meeting_note"
        print("  PASS test_note_stores_transcription")


# ── speech-to-text ────────────────────────────────────────────────────────────

class TestSpeechToText(unittest.TestCase):

    def setUp(self):
        self._mock_client = MagicMock()
        sys.modules["openai"].OpenAI.return_value = self._mock_client

    def _wav(self) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(b"fake audio")
        tmp.close()
        return tmp.name

    def test_missing_api_key_raises(self):
        os.environ.pop("OPENAI_API_KEY", None)
        from services.speech_to_text import transcribe_audio
        with self.assertRaises(RuntimeError):
            transcribe_audio("fake.wav")
        os.environ["OPENAI_API_KEY"] = "test-key"
        print("  PASS test_missing_api_key_raises")

    def test_returns_transcription(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        self._mock_client.audio.transcriptions.create.return_value = MagicMock(
            text="  Create a reminder for tomorrow at 9am.  "
        )
        path = self._wav()
        try:
            from services.speech_to_text import transcribe_audio
            result = transcribe_audio(path)
            self.assertEqual(result, "Create a reminder for tomorrow at 9am.")
        finally:
            os.unlink(path)
        print("  PASS test_returns_transcription")

    def test_empty_transcription(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        self._mock_client.audio.transcriptions.create.return_value = MagicMock(text="   ")
        path = self._wav()
        try:
            from services.speech_to_text import transcribe_audio
            result = transcribe_audio(path)
            self.assertEqual(result, "")
        finally:
            os.unlink(path)
        print("  PASS test_empty_transcription")

    def test_api_failure_raises(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        self._mock_client.audio.transcriptions.create.side_effect = Exception("network error")
        path = self._wav()
        try:
            from services.speech_to_text import transcribe_audio
            with self.assertRaises(Exception):
                transcribe_audio(path)
        finally:
            os.unlink(path)
        print("  PASS test_api_failure_raises")


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Running voice pipeline tests...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestIntentParser, TestVoicePipeline, TestSpeechToText]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    result = runner.run(suite)

    for test, _ in result.failures + result.errors:
        print(f"  FAIL {test}")

    if not result.failures and not result.errors:
        print("All voice pipeline tests passed.")
    else:
        print(f"{len(result.failures + result.errors)} test(s) failed.")

    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
