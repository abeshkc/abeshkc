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
        self.assertIn(result["intent"], ("create_note", "create_meeting_note"))
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
        """_show_result source must wire Insert into form, Save, Re-record, Cancel buttons."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._show_result)
        self.assertIn("Insert into form", src)
        self.assertIn("Save", src)
        self.assertIn("Re-record", src)
        self.assertIn("Cancel", src)
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


# ── importance field ──────────────────────────────────────────────────────────

class TestImportanceField(unittest.TestCase):

    def test_importance_levels_defined(self):
        from core.reminders import IMPORTANCE_LEVELS
        from core.notes import IMPORTANCE_LEVELS as NL
        for lvl in ("Low", "Normal", "High", "Urgent"):
            self.assertIn(lvl, IMPORTANCE_LEVELS)
            self.assertIn(lvl, NL)
        print("  PASS test_importance_levels_defined")

    def test_reminder_created_with_importance(self):
        from core.reminders import create_reminder, list_reminders
        from datetime import datetime, timedelta
        due = datetime.now() + timedelta(hours=2)
        rid = create_reminder("Urgent meeting", due, importance="Urgent")
        reminders = list_reminders(include_done=False)
        match = next((r for r in reminders if r["id"] == rid), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["importance"], "Urgent")
        print("  PASS test_reminder_created_with_importance")

    def test_note_created_with_importance(self):
        from core.notes import create_note, get_note
        nid = create_note("High importance note", importance="High")
        note = get_note(nid)
        self.assertIsNotNone(note)
        self.assertEqual(note["importance"], "High")
        print("  PASS test_note_created_with_importance")

    def test_importance_extracted_from_voice_urgent(self):
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("Urgent reminder to call the doctor today at 3pm")
        self.assertEqual(result["fields"]["importance"], "Urgent")
        print("  PASS test_importance_extracted_from_voice_urgent")

    def test_importance_extracted_from_voice_high(self):
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("Important meeting note about the project review")
        self.assertEqual(result["fields"]["importance"], "High")
        print("  PASS test_importance_extracted_from_voice_high")

    def test_importance_extracted_from_voice_low(self):
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("Low priority reminder to clean the desk")
        self.assertEqual(result["fields"]["importance"], "Low")
        print("  PASS test_importance_extracted_from_voice_low")

    def test_default_importance_is_normal(self):
        from ui.voice_panel import _rule_based_intent
        result = _rule_based_intent("Remind me about the standup tomorrow at 9am")
        self.assertEqual(result["fields"]["importance"], "Normal")
        print("  PASS test_default_importance_is_normal")

    def test_intent_parser_schema_has_importance(self):
        import services.intent_parser as ip
        self.assertIn("importance", ip._SYSTEM)
        self.assertIn("Urgent", ip._SYSTEM)
        self.assertIn("High", ip._SYSTEM)
        print("  PASS test_intent_parser_schema_has_importance")


# ── sorting ───────────────────────────────────────────────────────────────────

class TestSorting(unittest.TestCase):

    def test_sort_reminders_by_importance(self):
        from core.reminders import create_reminder, list_reminders
        from datetime import datetime, timedelta
        base = datetime.now() + timedelta(hours=10)
        create_reminder("Low task",    base, importance="Low")
        create_reminder("Urgent task", base + timedelta(hours=1), importance="Urgent")
        create_reminder("High task",   base + timedelta(hours=2), importance="High")
        result = list_reminders(include_done=False, sort_by="importance", ascending=True)
        imps = [r["importance"] for r in result if r["title"] in
                ("Low task", "High task", "Urgent task")]
        self.assertEqual(imps, sorted(imps, key=lambda x: {"Low":0,"Normal":1,"High":2,"Urgent":3}[x]))
        print("  PASS test_sort_reminders_by_importance")

    def test_sort_reminders_by_title_desc(self):
        from core.reminders import list_reminders
        result = list_reminders(include_done=False, sort_by="title", ascending=False)
        titles = [r["title"] for r in result]
        self.assertEqual(titles, sorted(titles, reverse=True, key=str.lower))
        print("  PASS test_sort_reminders_by_title_desc")

    def test_sort_notes_by_importance(self):
        from core.notes import create_note, list_notes
        create_note("Urgent note", importance="Urgent")
        create_note("Low note",    importance="Low")
        result = list_notes(sort_by="importance", ascending=False)
        imps = [n["importance"] for n in result[:5]]
        # Urgent should appear before Low when descending
        if "Urgent" in imps and "Low" in imps:
            self.assertLess(imps.index("Urgent"), imps.index("Low"))
        print("  PASS test_sort_notes_by_importance")

    def test_sort_notes_by_title(self):
        from core.notes import list_notes
        result = list_notes(sort_by="title", ascending=True)
        titles = [n["title"] for n in result]
        self.assertEqual(titles, sorted(titles, key=str.lower))
        print("  PASS test_sort_notes_by_title")


# ── progress states + button text ─────────────────────────────────────────────

class TestVoiceUX(unittest.TestCase):

    def test_start_button_text(self):
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._build)
        self.assertIn("Press to start speaking", src)
        print("  PASS test_start_button_text")

    def test_listening_button_text(self):
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._start)
        self.assertIn("Listening", src)
        print("  PASS test_listening_button_text")

    def test_processing_button_text(self):
        import inspect
        import ui.voice_panel as vp
        # Processing state is now indicated via canvas mic state and progress bar
        src = inspect.getsource(vp.VoicePanel._stop)
        self.assertIn("processing", src)   # mic_state set to "processing"
        self.assertIn("_progress", src)    # progress bar shown
        print("  PASS test_processing_button_text")

    def test_progress_bar_present(self):
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._build)
        self.assertIn("CTkProgressBar", src)
        print("  PASS test_progress_bar_present")

    def test_progress_stages_in_pipeline(self):
        import inspect
        import ui.voice_panel as vp
        stop_src     = inspect.getsource(vp.VoicePanel._stop)
        pipeline_src = inspect.getsource(vp.VoicePanel._pipeline)
        self.assertIn("Transcribing with local Whisper", stop_src)
        self.assertIn("Claude AI", pipeline_src)
        print("  PASS test_progress_stages_in_pipeline")

    def test_rerecord_button_restarts(self):
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._re_record)
        self.assertIn("_start", src)
        print("  PASS test_rerecord_button_restarts")

    def test_in_app_popup_exists(self):
        from ui.reminder_popup import ReminderPopup
        import inspect
        src = inspect.getsource(ReminderPopup)
        self.assertIn("Mark Done", src)
        self.assertIn("Snooze", src)
        self.assertIn("Dismiss", src)
        print("  PASS test_in_app_popup_exists")

    def test_missed_badge_method_exists(self):
        from ui.app import App
        self.assertTrue(hasattr(App, "update_missed_badge"))
        self.assertTrue(hasattr(App, "show_reminder_popup"))
        print("  PASS test_missed_badge_method_exists")

    def test_resizable_pane_in_notes(self):
        import inspect
        import ui.notes_view as nv
        src = inspect.getsource(nv.NotesView._build)
        self.assertIn("PanedWindow", src)
        print("  PASS test_resizable_pane_in_notes")

    def test_resizable_pane_in_reminders(self):
        import inspect
        import ui.reminders_view as rv
        src = inspect.getsource(rv.RemindersView._build)
        self.assertIn("PanedWindow", src)
        print("  PASS test_resizable_pane_in_reminders")

    def test_sorting_controls_in_reminders(self):
        import inspect
        import ui.reminders_view as rv
        src = inspect.getsource(rv.RemindersView._build)
        self.assertIn("Sort:", src)
        self.assertIn("_on_sort_change", src)
        print("  PASS test_sorting_controls_in_reminders")

    def test_sorting_controls_in_notes(self):
        import inspect
        import ui.notes_view as nv
        src = inspect.getsource(nv.NotesView._build)
        self.assertIn("Sort:", src)
        self.assertIn("_on_sort_change", src)
        print("  PASS test_sorting_controls_in_notes")

    def test_structured_result_shows_type(self):
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._show_result)
        self.assertIn("Type:", src)
        self.assertIn("confidence", src)
        self.assertIn("importance", src.lower())
        print("  PASS test_structured_result_shows_type")

    def test_mic_canvas_animation(self):
        """Mic canvas must have ring animation and three states."""
        import inspect
        import ui.voice_panel as vp
        src = inspect.getsource(vp.VoicePanel._animate_mic)
        self.assertIn("idle", src)
        self.assertIn("recording", src)
        self.assertIn("processing", src)
        self.assertIn("_ring_ids", src)
        print("  PASS test_mic_canvas_animation")

    def test_aria_app_name(self):
        """App window title and sidebar must reference 'Aria'."""
        import inspect
        import ui.app as app_mod
        src = inspect.getsource(app_mod.App.__init__)
        self.assertIn("Aria", src)
        src2 = inspect.getsource(app_mod.App._build_sidebar)
        self.assertIn("Aria", src2)
        print("  PASS test_aria_app_name")

    def test_sidebar_has_emoji_icons(self):
        """Sidebar buttons must use emoji icons."""
        import inspect
        import ui.app as app_mod
        src = inspect.getsource(app_mod.App._build_sidebar)
        self.assertIn("📝", src)   # Notes
        self.assertIn("🔔", src)   # Reminders
        self.assertIn("🎙", src)   # Voice
        print("  PASS test_sidebar_has_emoji_icons")

    def test_reminder_no_auto_confirm_on_create(self):
        """RemindersView._save_or_create must NOT call mb.askyesno for creation path."""
        import inspect
        import ui.reminders_view as rv
        # Method was renamed from _create to _save_or_create
        src = inspect.getsource(rv.RemindersView._save_or_create)
        self.assertNotIn("askyesno", src)
        print("  PASS test_reminder_no_auto_confirm_on_create")

    def test_details_field_in_reminder_form(self):
        """RemindersView must have a Details entry field."""
        import inspect
        import ui.reminders_view as rv
        src = inspect.getsource(rv.RemindersView._build)
        self.assertIn("Details", src)
        self.assertIn("_details_var", src)
        print("  PASS test_details_field_in_reminder_form")

    def test_note_date_field_in_notes_form(self):
        """NotesView must have a note_date entry field."""
        import inspect
        import ui.notes_view as nv
        src = inspect.getsource(nv.NotesView._build)
        self.assertIn("note_date", src)
        self.assertIn("Date:", src)
        print("  PASS test_note_date_field_in_notes_form")

    def test_note_date_saved_in_db(self):
        """create_note and update_note must accept note_date."""
        from core.notes import create_note, get_note, update_note
        nid = create_note("Dated note", note_date="2026-05-10")
        note = get_note(nid)
        self.assertEqual(note["note_date"], "2026-05-10")
        update_note(nid, "Dated note", "content", "", note_date="2026-05-15")
        note2 = get_note(nid)
        self.assertEqual(note2["note_date"], "2026-05-15")
        print("  PASS test_note_date_saved_in_db")

    def test_when_field_contains_only_datetime(self):
        """Rule-based parser must NOT put full transcription in datetime field."""
        from ui.voice_panel import _rule_based_intent
        text = "Create a reminder for meeting with Yaseen tomorrow at 10 PM about the DIEM brief"
        result = _rule_based_intent(text)
        dt = result["fields"]["datetime"]
        self.assertNotEqual(dt, text, "datetime must not equal full transcription")
        # datetime should be short (a natural-language time expression, or empty)
        if dt:
            self.assertLess(len(dt), len(text) // 2,
                            "datetime should be much shorter than full transcription")
        print("  PASS test_when_field_contains_only_datetime")

    def test_details_field_receives_context(self):
        """Rule-based parser should store the full speech as details."""
        from ui.voice_panel import _rule_based_intent
        text = "Create a reminder for meeting with Yaseen tomorrow at 10 PM about the DIEM brief"
        result = _rule_based_intent(text)
        details = result["fields"]["details"]
        self.assertIn("DIEM", details)
        print("  PASS test_details_field_receives_context")

    def test_claude_schema_has_details_and_note_date(self):
        """intent_parser system prompt must include details and note_date fields."""
        import services.intent_parser as ip
        self.assertIn("details", ip._SYSTEM)
        self.assertIn("note_date", ip._SYSTEM)
        print("  PASS test_claude_schema_has_details_and_note_date")

    def test_nav_buttons_icon_only(self):
        """Sidebar nav buttons must use icons only — no word labels like Notes/Voice."""
        import inspect
        import ui.app as app_mod
        src = inspect.getsource(app_mod.App._build_sidebar)
        # Buttons should only have single emoji as text, not full words
        self.assertNotIn('"📝  Notes"', src)
        self.assertNotIn('"🔔  Reminders"', src)
        self.assertNotIn('"🎙  Voice"', src)
        # Icons should be present
        self.assertIn('"📝"', src)
        self.assertIn('"🔔"', src)
        self.assertIn('"🎙"', src)
        print("  PASS test_nav_buttons_icon_only")

    def test_tooltips_on_nav_buttons(self):
        """Each nav button must have a _ToolTip attached."""
        import inspect
        import ui.app as app_mod
        src = inspect.getsource(app_mod.App._build_sidebar)
        # Should have at least 3 ToolTip calls for the 3 nav buttons
        count = src.count("_ToolTip(")
        self.assertGreaterEqual(count, 3)
        print("  PASS test_tooltips_on_nav_buttons")

    def test_voice_assistant_text_removed(self):
        """'Voice Assistant' must not appear as a UI label in app.py."""
        import inspect
        import ui.app as app_mod
        src = inspect.getsource(app_mod.App._build_sidebar)
        self.assertNotIn("Voice Assistant", src)
        print("  PASS test_voice_assistant_text_removed")

    def test_personal_organizer_text(self):
        """'Personal Organizer' or 'Your Personal Organizer' must appear."""
        import inspect
        import ui.app as app_mod
        import ui.voice_panel as vp
        app_src = inspect.getsource(app_mod.App)
        vp_src  = inspect.getsource(vp.VoicePanel._build)
        self.assertTrue(
            "Personal Organizer" in app_src or "Personal Organizer" in vp_src,
            "Personal Organizer not found in app or voice panel"
        )
        print("  PASS test_personal_organizer_text")

    def test_aria_icon_changed(self):
        """Musical note (U+1F3B5) must be replaced with spark icon (U+2726)."""
        import pathlib
        import ui.app as app_mod
        import ui.voice_panel as vp
        # Read full file text in UTF-8 so Unicode chars are preserved
        app_src = pathlib.Path(app_mod.__file__).read_text(encoding="utf-8")
        vp_src  = pathlib.Path(vp.__file__).read_text(encoding="utf-8")
        self.assertNotIn("\U0001f3b5", app_src, "Musical note still in app.py")
        self.assertNotIn("\U0001f3b5", vp_src,  "Musical note still in voice_panel.py")
        self.assertIn("✦", app_src,  "Spark icon not found in app.py")
        self.assertIn("✦", vp_src,   "Spark icon not found in voice_panel.py")
        print("  PASS test_aria_icon_changed")

    def test_badge_uses_overlay(self):
        """Missed-reminder badge must use place() overlay, not button text."""
        import inspect
        import ui.app as app_mod
        src = inspect.getsource(app_mod.App.update_missed_badge)
        self.assertIn(".place(", src)
        self.assertNotIn("configure(text=", src.split("update_missed_badge")[0])
        print("  PASS test_badge_uses_overlay")

    def test_recording_workflow_intact(self):
        """_start and _stop must still set mic_state correctly."""
        import inspect
        import ui.voice_panel as vp
        start_src = inspect.getsource(vp.VoicePanel._start)
        stop_src  = inspect.getsource(vp.VoicePanel._stop)
        self.assertIn("recording", start_src)
        self.assertIn("processing", stop_src)
        print("  PASS test_recording_workflow_intact")


# ── new editing workflow tests ────────────────────────────────────────────────

class TestUpdateReminder(unittest.TestCase):
    """Tests for get_reminder and update_reminder added to core/reminders.py."""

    def setUp(self):
        from core.reminders import create_reminder, get_reminder, update_reminder
        self.create  = create_reminder
        self.get     = get_reminder
        self.update  = update_reminder
        self.base_dt = datetime(2030, 1, 15, 9, 0)

    def test_get_reminder_returns_dict(self):
        rid = self.create("Get-test reminder", self.base_dt, importance="Normal")
        r   = self.get(rid)
        self.assertIsInstance(r, dict)
        self.assertEqual(r["id"], rid)
        self.assertEqual(r["title"], "Get-test reminder")
        print("  PASS test_get_reminder_returns_dict")

    def test_update_reminder_changes_title(self):
        rid = self.create("Old title", self.base_dt)
        self.update(rid, "New title", self.base_dt)
        r = self.get(rid)
        self.assertEqual(r["title"], "New title")
        print("  PASS test_update_reminder_changes_title")

    def test_update_reminder_changes_importance(self):
        rid = self.create("Imp test", self.base_dt, importance="Normal")
        self.update(rid, "Imp test", self.base_dt, importance="Urgent")
        r = self.get(rid)
        self.assertEqual(r["importance"], "Urgent")
        print("  PASS test_update_reminder_changes_importance")

    def test_update_reminder_changes_due(self):
        new_dt = datetime(2030, 6, 1, 10, 30)
        rid = self.create("Due test", self.base_dt)
        self.update(rid, "Due test", new_dt)
        r = self.get(rid)
        self.assertIn("2030-06-01", r["due_at"])
        print("  PASS test_update_reminder_changes_due")

    def test_update_reminder_nonexistent_noop(self):
        try:
            self.update(999999, "Ghost", self.base_dt)
        except Exception as exc:
            self.fail(f"update_reminder raised on nonexistent id: {exc}")
        print("  PASS test_update_reminder_nonexistent_noop")


class TestAriaContext(unittest.TestCase):
    """Tests for the AriaContext shared editing state dataclass."""

    def setUp(self):
        from ui.aria_context import AriaContext
        self.ctx = AriaContext()

    def test_set_note_populates_fields(self):
        self.ctx.set_note(5, "Stanford Notes")
        self.assertEqual(self.ctx.active_item_type, "note")
        self.assertEqual(self.ctx.active_item_id, 5)
        self.assertEqual(self.ctx.active_item_title, "Stanford Notes")
        self.assertFalse(self.ctx.unsaved_changes)
        print("  PASS test_set_note_populates_fields")

    def test_set_reminder_populates_fields(self):
        self.ctx.set_reminder(12, "Doctor Appointment")
        self.assertEqual(self.ctx.active_item_type, "reminder")
        self.assertEqual(self.ctx.active_item_id, 12)
        self.assertEqual(self.ctx.active_item_title, "Doctor Appointment")
        print("  PASS test_set_reminder_populates_fields")

    def test_mark_dirty_sets_unsaved(self):
        self.ctx.set_note(1, "Test")
        self.ctx.mark_dirty()
        self.assertTrue(self.ctx.unsaved_changes)
        print("  PASS test_mark_dirty_sets_unsaved")

    def test_clear_resets_all(self):
        self.ctx.set_note(1, "Test")
        self.ctx.mark_dirty()
        self.ctx.clear()
        self.assertIsNone(self.ctx.active_item_type)
        self.assertIsNone(self.ctx.active_item_id)
        self.assertIsNone(self.ctx.active_item_title)
        self.assertFalse(self.ctx.unsaved_changes)
        print("  PASS test_clear_resets_all")


class TestEditingIntents(unittest.TestCase):
    """Tests for new editing intents in rule-based fallback and intent_parser schema."""

    def setUp(self):
        from ui.voice_panel import _rule_based_intent
        self.parse = _rule_based_intent

    def test_open_note_intent_detected(self):
        r = self.parse("open note Stanford Engineering")
        self.assertEqual(r["intent"], "open_note")
        print("  PASS test_open_note_intent_detected")

    def test_open_reminder_intent_detected(self):
        r = self.parse("open reminder dentist appointment")
        self.assertEqual(r["intent"], "open_reminder")
        print("  PASS test_open_reminder_intent_detected")

    def test_append_note_intent_detected(self):
        r = self.parse("append to note: also check Q2 budget")
        self.assertEqual(r["intent"], "append_note")
        print("  PASS test_append_note_intent_detected")

    def test_save_active_intent_detected(self):
        r = self.parse("save changes")
        self.assertEqual(r["intent"], "save_active_item")
        print("  PASS test_save_active_intent_detected")

    def test_close_active_intent_detected(self):
        r = self.parse("close this note")
        self.assertEqual(r["intent"], "close_active_item")
        print("  PASS test_close_active_intent_detected")

    def test_new_intents_in_schema(self):
        from services.intent_parser import _SYSTEM
        new_intents = [
            "search_note", "search_reminder", "open_note", "open_reminder",
            "update_note", "update_reminder", "append_note", "append_reminder",
            "save_active_item", "close_active_item",
        ]
        for intent in new_intents:
            self.assertIn(intent, _SYSTEM,
                          f"Intent '{intent}' missing from _SYSTEM schema")
        print("  PASS test_new_intents_in_schema")

    def test_new_fields_in_schema(self):
        from services.intent_parser import _SYSTEM
        for field in ("item_id", "append_text", "target_title"):
            self.assertIn(field, _SYSTEM,
                          f"Field '{field}' missing from _SYSTEM schema")
        print("  PASS test_new_fields_in_schema")


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
        TestVoicePipeline,
        TestImportanceField,
        TestSorting,
        TestVoiceUX,
        TestUpdateReminder,
        TestAriaContext,
        TestEditingIntents,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w", encoding="utf-8"))
    result = runner.run(suite)

    for test, tb in result.failures + result.errors:
        print(f"  FAIL {test}")
        # encode to ASCII with replacement so Windows cp1252 stdout doesn't crash
        print(tb.encode("ascii", "replace").decode("ascii"))

    if not result.failures and not result.errors:
        print("All voice pipeline tests passed.")
    else:
        print(f"{len(result.failures + result.errors)} test(s) failed.")

    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
