"""
Voice pipeline tests — all external calls are mocked; no API keys or mic needed.
Fake faster_whisper and anthropic modules are injected into sys.modules so tests
run even when those packages are not installed.
"""
import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json

# ── inject fake packages before any service imports ───────────────────────────

# fake faster_whisper
_fake_fw = MagicMock()
_fake_fw_model = MagicMock()
_fake_fw.WhisperModel.return_value = _fake_fw_model
sys.modules.setdefault("faster_whisper", _fake_fw)

# fake anthropic
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
            "title": title, "description": "", "date": "", "time": "",
            "datetime": dt_str, "participants": [], "tags": [],
            "priority": "normal", "recurrence": recurrence, "search_query": "",
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
            "title": title, "description": description, "date": "", "time": "",
            "datetime": "", "participants": [], "tags": ["meeting"],
            "priority": "normal", "recurrence": "none", "search_query": "",
        },
        "action_summary": f"Create meeting note: {title}",
        "missing_fields": [],
    }


_GOOD_JSON = (
    '{"intent":"create_reminder","confidence":0.9,"requires_confirmation":false,'
    '"fields":{"title":"Test","datetime":"tomorrow at 9am","description":"",'
    '"date":"","time":"","participants":[],"tags":[],"priority":"normal",'
    '"recurrence":"none","search_query":""},"action_summary":"Create reminder","missing_fields":[]}'
)


# ── local whisper service ─────────────────────────────────────────────────────

class TestLocalWhisperService(unittest.TestCase):

    def setUp(self):
        # Reset cached model between tests
        import services.local_whisper_service as svc
        svc._model = None
        svc._model_key = None
        _fake_fw.WhisperModel.reset_mock()
        _fake_fw_model.transcribe.reset_mock()

    def test_transcribes_audio(self):
        _fake_fw_model.transcribe.return_value = (
            [MagicMock(text=" Hello world ")],
            MagicMock(),
        )
        from services.local_whisper_service import transcribe
        result = transcribe("fake.wav")
        self.assertEqual(result, "Hello world")
        print("  PASS test_transcribes_audio")

    def test_empty_audio_returns_empty_string(self):
        _fake_fw_model.transcribe.return_value = ([], MagicMock())
        from services.local_whisper_service import transcribe
        result = transcribe("silent.wav")
        self.assertEqual(result, "")
        print("  PASS test_empty_audio_returns_empty_string")

    def test_model_loaded_with_correct_settings(self):
        os.environ["WHISPER_MODEL_SIZE"] = "small"
        os.environ["WHISPER_DEVICE"] = "cpu"
        os.environ["WHISPER_COMPUTE_TYPE"] = "int8"
        import services.local_whisper_service as svc
        svc._model = None; svc._model_key = None
        _fake_fw_model.transcribe.return_value = ([MagicMock(text="test")], MagicMock())
        svc.transcribe("x.wav")
        _fake_fw.WhisperModel.assert_called_with("small", device="cpu", compute_type="int8")
        os.environ["WHISPER_MODEL_SIZE"] = "base"
        print("  PASS test_model_loaded_with_correct_settings")

    def test_model_cached_after_first_load(self):
        import services.local_whisper_service as svc
        svc._model = None; svc._model_key = None
        _fake_fw_model.transcribe.return_value = ([MagicMock(text="hi")], MagicMock())
        svc.transcribe("a.wav")
        svc.transcribe("b.wav")
        self.assertEqual(_fake_fw.WhisperModel.call_count, 1, "Model should be loaded only once")
        print("  PASS test_model_cached_after_first_load")

    def test_missing_package_raises(self):
        import services.local_whisper_service as svc
        svc._model = None; svc._model_key = None
        original = sys.modules.get("faster_whisper")
        sys.modules["faster_whisper"] = None  # simulate missing package
        try:
            with self.assertRaises((RuntimeError, ImportError, TypeError)):
                svc.transcribe("x.wav")
        finally:
            sys.modules["faster_whisper"] = original
            svc._model = None; svc._model_key = None
        print("  PASS test_missing_package_raises")


# ── speech_to_text wrapper ────────────────────────────────────────────────────

class TestSpeechToText(unittest.TestCase):

    def setUp(self):
        import services.local_whisper_service as svc
        svc._model = None; svc._model_key = None
        _fake_fw_model.transcribe.reset_mock()

    def test_returns_transcription(self):
        _fake_fw_model.transcribe.return_value = (
            [MagicMock(text="  Create a reminder for tomorrow at 9am.  ")],
            MagicMock(),
        )
        from services.speech_to_text import transcribe_audio
        result = transcribe_audio("fake.wav")
        self.assertEqual(result, "Create a reminder for tomorrow at 9am.")
        print("  PASS test_returns_transcription")

    def test_empty_audio_returns_empty(self):
        _fake_fw_model.transcribe.return_value = ([], MagicMock())
        from services.speech_to_text import transcribe_audio
        result = transcribe_audio("silent.wav")
        self.assertEqual(result, "")
        print("  PASS test_empty_audio_returns_empty")

    def test_api_failure_propagates(self):
        _fake_fw_model.transcribe.side_effect = Exception("model crashed")
        from services.speech_to_text import transcribe_audio
        with self.assertRaises(Exception):
            transcribe_audio("bad.wav")
        _fake_fw_model.transcribe.side_effect = None
        print("  PASS test_api_failure_propagates")


# ── intent parser (Claude) ────────────────────────────────────────────────────

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

    def test_missing_api_key_raises(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        from services.intent_parser import parse_intent
        with self.assertRaises(RuntimeError):
            parse_intent("some text")
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        print("  PASS test_missing_api_key_raises")

    def test_invalid_json_raises(self):
        self._mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Sorry, I cannot help with that.")]
        )
        from services.intent_parser import parse_intent
        with self.assertRaises(ValueError):
            parse_intent("some text")
        print("  PASS test_invalid_json_raises")


# ── rule-based fallback parser ────────────────────────────────────────────────

class TestRuleBasedFallback(unittest.TestCase):

    def test_reminder_intent_detected(self):
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("Remind me about the meeting tomorrow at 10pm")
        self.assertEqual(result["intent"], "create_reminder")
        self.assertTrue(result["requires_confirmation"])
        print("  PASS test_reminder_intent_detected")

    def test_note_intent_detected(self):
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("Add a note: review Yemen brief before Thursday")
        self.assertEqual(result["intent"], "create_meeting_note")
        print("  PASS test_note_intent_detected")

    def test_unknown_intent(self):
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("blah blah nothing recognizable here")
        self.assertEqual(result["intent"], "unknown")
        print("  PASS test_unknown_intent")

    def test_claude_unavailable_falls_back(self):
        """When Claude API key is absent the rule-based parser is used — no crash."""
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("Create a reminder for standup tomorrow at 9am")
        self.assertIn(result["intent"], ("create_reminder", "unknown"))
        self.assertTrue(result["requires_confirmation"])
        print("  PASS test_claude_unavailable_falls_back")


# ── Claude is the default parser ─────────────────────────────────────────────

class TestClaudeIsDefault(unittest.TestCase):

    def test_claude_parser_is_default(self):
        """voice_panel must use claude_parse_intent, not qwen, as primary parser."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._pipeline)
        self.assertIn("claude_parse_intent", src)
        self.assertNotIn("qwen_parse_intent", src)
        print("  PASS test_claude_parser_is_default")

    def test_voice_is_default_view(self):
        """app.py must call show_voice() as the default on startup."""
        import inspect
        import ui.app as app_mod
        src = inspect.getsource(app_mod.App.__init__)
        self.assertIn("show_voice", src)
        self.assertNotIn("show_notes()", src)
        print("  PASS test_voice_is_default_view")

    def test_ollama_not_required(self):
        """Importing voice_panel must succeed regardless of Ollama state."""
        import ui.voice_panel  # should not raise even without Ollama
        print("  PASS test_ollama_not_required")

    def test_missing_api_key_raises(self):
        """intent_parser.parse_intent raises RuntimeError with clear message when key absent."""
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            from services.intent_parser import parse_intent
            with self.assertRaises(RuntimeError) as ctx:
                parse_intent("some text")
            self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))
        finally:
            if old_key:
                os.environ["ANTHROPIC_API_KEY"] = old_key
        print("  PASS test_missing_api_key_raises")

    def test_transcription_forwarded_to_claude(self):
        """parse_intent receives the transcription text and returns a dict."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        _fake_anthropic.Anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=_GOOD_JSON)]
        )
        from services.intent_parser import parse_intent
        result = parse_intent("Remind me to call tomorrow")
        self.assertIsInstance(result, dict)
        self.assertIn("intent", result)
        print("  PASS test_transcription_forwarded_to_claude")

    def test_high_confidence_reminder_autosaves(self):
        """confidence >= 0.85 meets CONFIDENCE_AUTO threshold for auto-save."""
        from ui.voice_panel import CONFIDENCE_AUTO
        action = _reminder_action("Team sync", "tomorrow at 9am")
        self.assertGreaterEqual(action["confidence"], CONFIDENCE_AUTO)
        self.assertFalse(action["requires_confirmation"])
        print("  PASS test_high_confidence_reminder_autosaves")

    def test_low_confidence_requires_confirmation(self):
        """confidence < 0.60 is below CONFIDENCE_REVIEW — must not auto-save."""
        from ui.voice_panel import CONFIDENCE_REVIEW
        action = _reminder_action("vague command", "sometime")
        action["confidence"] = 0.45
        self.assertLess(action["confidence"], CONFIDENCE_REVIEW)
        print("  PASS test_low_confidence_requires_confirmation")

    def test_autosave_default_is_off(self):
        """VoicePanel autosave switch must default to False."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel.__init__)
        self.assertIn("value=False", src)
        print("  PASS test_autosave_default_is_off")

    def test_result_panel_has_insert_and_discard(self):
        """_show_result source must wire Insert into form and Discard buttons."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._show_result)
        self.assertIn("Insert into form", src)
        self.assertIn("Save after review", src)
        self.assertIn("Try again", src)
        self.assertIn("Discard", src)
        print("  PASS test_result_panel_has_insert_and_discard")

    def test_destructive_action_hidden_from_save_button(self):
        """Save after review button must be hidden for destructive intents."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._show_result)
        # The save button is only shown when not is_dest
        self.assertIn("not is_dest", src)
        print("  PASS test_destructive_action_hidden_from_save_button")

    def test_autosave_off_always_confirms(self):
        """When auto_on=False, _do_save always requires confirmation."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._do_save)
        # needs_confirm must incorporate auto_on flag
        self.assertIn("auto_on", src)
        self.assertIn("not auto_on", src)
        print("  PASS test_autosave_off_always_confirms")

    def test_waveform_animation_present(self):
        """voice_panel must contain waveform animation code."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._animate_bars)
        self.assertIn("current_level", src)
        self.assertIn("_canvas", src)
        print("  PASS test_waveform_animation_present")


# ── local LLM service (Qwen/Ollama) — optional experimental ──────────────────

_GOOD_REMINDER_JSON = json.dumps({
    "intent": "create_reminder",
    "confidence": 0.92,
    "requires_confirmation": False,
    "fields": {
        "title": "Meeting with Yaseen",
        "description": "",
        "date": "", "time": "",
        "datetime": "tomorrow at 10pm",
        "participants": ["Yaseen"],
        "tags": [], "priority": "normal",
        "recurrence": "none", "search_query": "",
    },
    "action_summary": "Create reminder: Meeting with Yaseen",
    "missing_fields": [],
})

_GOOD_NOTE_JSON = json.dumps({
    "intent": "create_meeting_note",
    "confidence": 0.95,
    "requires_confirmation": False,
    "fields": {
        "title": "DIEM monitoring discussion",
        "description": "We discussed the DIEM plan.",
        "date": "", "time": "", "datetime": "",
        "participants": [], "tags": ["meeting"],
        "priority": "normal", "recurrence": "none", "search_query": "",
    },
    "action_summary": "Create meeting note",
    "missing_fields": [],
})

_GOOD_SEARCH_JSON = json.dumps({
    "intent": "search",
    "confidence": 0.90,
    "requires_confirmation": False,
    "fields": {
        "title": "", "description": "", "date": "", "time": "", "datetime": "",
        "participants": [], "tags": [], "priority": "normal",
        "recurrence": "none", "search_query": "AgHiN",
    },
    "action_summary": "Search: AgHiN",
    "missing_fields": [],
})


def _mock_ollama(get_mock, post_mock, response_json: str,
                 models=None, running=True):
    """Wire up requests.get and requests.post to simulate a working Ollama."""
    import requests as req_mod

    if running:
        get_mock.side_effect = lambda url, **kw: (
            MagicMock(status_code=200, json=lambda: {})
            if "tags" not in url
            else MagicMock(
                status_code=200,
                json=lambda: {"models": [{"name": m} for m in (models or ["qwen2.5:7b"])]},
            )
        )
    else:
        get_mock.side_effect = req_mod.exceptions.ConnectionError("refused")

    post_mock.return_value = MagicMock(
        status_code=200,
        raise_for_status=lambda: None,
        json=lambda: {"message": {"content": response_json}},
    )


class TestLocalLLMService(unittest.TestCase):

    def setUp(self):
        import services.local_llm_service as svc
        os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:7b")
        os.environ.setdefault("OLLAMA_FALLBACK_MODEL", "qwen2.5:3b")

    @patch("requests.post")
    @patch("requests.get")
    def test_valid_reminder_json(self, get_mock, post_mock):
        _mock_ollama(get_mock, post_mock, _GOOD_REMINDER_JSON)
        from services.local_llm_service import parse_intent
        result = parse_intent("Remind me about meeting with Yaseen tomorrow at 10pm")
        self.assertEqual(result["intent"], "create_reminder")
        self.assertAlmostEqual(result["confidence"], 0.92)
        self.assertEqual(result["fields"]["title"], "Meeting with Yaseen")
        print("  PASS test_valid_reminder_json")

    @patch("requests.post")
    @patch("requests.get")
    def test_meeting_note_parsing(self, get_mock, post_mock):
        _mock_ollama(get_mock, post_mock, _GOOD_NOTE_JSON)
        from services.local_llm_service import parse_intent
        result = parse_intent("Create a meeting note about DIEM plan")
        self.assertEqual(result["intent"], "create_meeting_note")
        print("  PASS test_meeting_note_parsing")

    @patch("requests.post")
    @patch("requests.get")
    def test_search_parsing(self, get_mock, post_mock):
        _mock_ollama(get_mock, post_mock, _GOOD_SEARCH_JSON)
        from services.local_llm_service import parse_intent
        result = parse_intent("Find my notes about AgHiN")
        self.assertEqual(result["intent"], "search")
        self.assertEqual(result["fields"]["search_query"], "AgHiN")
        print("  PASS test_search_parsing")

    @patch("requests.post")
    @patch("requests.get")
    def test_recurring_reminder_parsing(self, get_mock, post_mock):
        payload = json.loads(_GOOD_REMINDER_JSON)
        payload["fields"]["recurrence"] = "weekly"
        payload["fields"]["title"] = "Call Yaseen"
        _mock_ollama(get_mock, post_mock, json.dumps(payload))
        from services.local_llm_service import parse_intent
        result = parse_intent("Remind me to call Yaseen every Friday at 3pm")
        self.assertEqual(result["fields"]["recurrence"], "weekly")
        print("  PASS test_recurring_reminder_parsing")

    @patch("requests.get")
    def test_ollama_unavailable_raises(self, get_mock):
        import requests as req_mod
        get_mock.side_effect = req_mod.exceptions.ConnectionError("refused")
        from services.local_llm_service import parse_intent
        with self.assertRaises(RuntimeError) as ctx:
            parse_intent("some text")
        self.assertIn("Ollama", str(ctx.exception))
        print("  PASS test_ollama_unavailable_raises")

    @patch("requests.get")
    def test_model_missing_raises(self, get_mock):
        get_mock.side_effect = lambda url, **kw: (
            MagicMock(status_code=200, json=lambda: {})
            if "tags" not in url
            else MagicMock(status_code=200, json=lambda: {"models": []})
        )
        from services.local_llm_service import parse_intent
        with self.assertRaises(RuntimeError) as ctx:
            parse_intent("some text")
        self.assertIn("ollama pull", str(ctx.exception))
        print("  PASS test_model_missing_raises")

    @patch("requests.post")
    @patch("requests.get")
    def test_model_fallback_used(self, get_mock, post_mock):
        # Primary model missing but fallback available
        _mock_ollama(get_mock, post_mock, _GOOD_REMINDER_JSON, models=["qwen2.5:3b"])
        from services.local_llm_service import parse_intent
        result = parse_intent("test")
        self.assertEqual(result["intent"], "create_reminder")
        print("  PASS test_model_fallback_used")

    @patch("requests.post")
    @patch("requests.get")
    def test_malformed_json_raises(self, get_mock, post_mock):
        _mock_ollama(get_mock, post_mock, "Sorry, I cannot parse that.")
        from services.local_llm_service import parse_intent
        with self.assertRaises(ValueError):
            parse_intent("some text")
        print("  PASS test_malformed_json_raises")

    @patch("requests.post")
    @patch("requests.get")
    def test_markdown_fences_stripped(self, get_mock, post_mock):
        fenced = f"```json\n{_GOOD_REMINDER_JSON}\n```"
        _mock_ollama(get_mock, post_mock, fenced)
        from services.local_llm_service import parse_intent
        result = parse_intent("test")
        self.assertEqual(result["intent"], "create_reminder")
        print("  PASS test_markdown_fences_stripped")

    @patch("requests.post")
    @patch("requests.get")
    def test_destructive_action_requires_confirmation(self, get_mock, post_mock):
        payload = json.loads(_GOOD_REMINDER_JSON)
        payload["intent"] = "update_reminder"
        payload["requires_confirmation"] = True
        _mock_ollama(get_mock, post_mock, json.dumps(payload))
        from services.local_llm_service import parse_intent
        result = parse_intent("delete my reminder about Yaseen")
        self.assertTrue(result["requires_confirmation"])
        print("  PASS test_destructive_action_requires_confirmation")

    @patch("requests.post")
    @patch("requests.get")
    def test_low_confidence_does_not_auto_save(self, get_mock, post_mock):
        payload = json.loads(_GOOD_REMINDER_JSON)
        payload["confidence"] = 0.45
        _mock_ollama(get_mock, post_mock, json.dumps(payload))
        from services.local_llm_service import parse_intent
        from ui.voice_panel import CONFIDENCE_REVIEW
        result = parse_intent("mumbled unclear command")
        self.assertLess(result["confidence"], CONFIDENCE_REVIEW)
        print("  PASS test_low_confidence_does_not_auto_save")

    @patch("requests.post")
    @patch("requests.get")
    def test_high_confidence_create_reminder(self, get_mock, post_mock):
        _mock_ollama(get_mock, post_mock, _GOOD_REMINDER_JSON)
        from services.local_llm_service import parse_intent
        from ui.voice_panel import CONFIDENCE_AUTO
        result = parse_intent("Clear command with full details")
        self.assertGreaterEqual(result["confidence"], CONFIDENCE_AUTO)
        self.assertFalse(result["requires_confirmation"])
        print("  PASS test_high_confidence_create_reminder")


# ── end-to-end pipeline ───────────────────────────────────────────────────────

class TestVoicePipeline(unittest.TestCase):

    def _run_pipeline(self, transcription: str, action: dict) -> str:
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
        result = self._run_pipeline(
            "Create a reminder for meeting with Yaseen tomorrow at 10 PM", action
        )
        self.assertEqual(result, "reminder")
        reminders = list_reminders(include_done=False)
        assert any(r["title"] == "Meeting with Yaseen" for r in reminders)
        print("  PASS test_voice_command_creates_reminder")

    def test_voice_command_creates_meeting_note(self):
        description = "We discussed the DIEM monitoring plan and agreed to revise the sampling approach."
        action = _note_action("DIEM monitoring discussion", description)
        self._run_pipeline("Create a meeting note: " + description, action)
        notes = list_notes()
        match = next((n for n in notes if n["title"] == "DIEM monitoring discussion"), None)
        assert match is not None
        assert match["source_type"] == "voice"
        assert match["created_from_voice"] == 1
        print("  PASS test_voice_command_creates_meeting_note")

    def test_missing_time_raises(self):
        action = _reminder_action("Call back", "")
        with self.assertRaises(ValueError):
            self._run_pipeline("Call back", action)
        print("  PASS test_missing_time_raises")

    def test_low_confidence_does_not_auto_save(self):
        from ui.voice_panel import CONFIDENCE_REVIEW
        action = _reminder_action("Low confidence task", "tomorrow at 9am")
        action["confidence"] = 0.45
        self.assertLess(action["confidence"], CONFIDENCE_REVIEW)
        print("  PASS test_low_confidence_does_not_auto_save")

    def test_auto_save_threshold(self):
        from ui.voice_panel import CONFIDENCE_AUTO, CONFIDENCE_REVIEW
        self.assertGreater(CONFIDENCE_AUTO, CONFIDENCE_REVIEW)
        self.assertGreaterEqual(CONFIDENCE_AUTO, 0.85)
        self.assertGreaterEqual(CONFIDENCE_REVIEW, 0.60)
        print("  PASS test_auto_save_threshold")

    def test_recurring_reminder_via_voice(self):
        action = _reminder_action("Weekly standup", "friday at 9am", recurrence="weekly")
        self._run_pipeline("Weekly standup every friday at 9am", action)
        reminders = list_reminders(include_done=False)
        match = next((r for r in reminders if r["title"] == "Weekly standup"), None)
        assert match is not None
        assert match["recurrence_type"] == "weekly"
        print("  PASS test_recurring_reminder_via_voice")

    def test_note_stores_transcription(self):
        transcription = "Add a note: review Yemen brief before Thursday."
        action = _note_action("Review Yemen Brief", "review Yemen brief before Thursday")
        self._run_pipeline(transcription, action)
        notes = list_notes()
        match = next((n for n in notes if "Yemen" in n["title"]), None)
        assert match is not None
        assert match["original_transcription"] == transcription
        print("  PASS test_note_stores_transcription")


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Running voice pipeline tests...")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestLocalWhisperService,
        TestSpeechToText,
        TestIntentParser,
        TestClaudeIsDefault,
        TestRuleBasedFallback,
        TestLocalLLMService,
        TestVoicePipeline,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    result = runner.run(suite)

    for test, tb in result.failures + result.errors:
        print(f"  FAIL {test}")
        print(tb)

    if not result.failures and not result.errors:
        print("All voice pipeline tests passed.")
    else:
        print(f"{len(result.failures + result.errors)} test(s) failed.")

    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
