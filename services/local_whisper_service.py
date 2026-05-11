"""
Local Whisper transcription using faster-whisper.

Settings are read from environment variables (set them in .env):
  WHISPER_MODEL_SIZE   — tiny | base | small | medium   (default: base)
  WHISPER_DEVICE       — cpu | cuda                     (default: cpu)
  WHISPER_COMPUTE_TYPE — int8 | float16 | float32       (default: int8)
  WHISPER_LANGUAGE     — en | fr | ar | …  or leave blank for auto-detect
  WHISPER_MODEL_PATH   — local cache directory          (default: ~/.cache/huggingface)

The model is downloaded once on first use and cached on disk.
Audio is never sent anywhere — transcription runs entirely on this machine.
"""
import os

_model = None
_model_key: str | None = None


def _settings() -> dict:
    return {
        "model_size":   os.environ.get("WHISPER_MODEL_SIZE", "base"),
        "device":       os.environ.get("WHISPER_DEVICE", "cpu"),
        "compute_type": os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        "language":     os.environ.get("WHISPER_LANGUAGE") or None,
        "model_path":   os.environ.get("WHISPER_MODEL_PATH") or None,
    }


def _get_model(size: str, device: str, compute_type: str, model_path: str | None):
    global _model, _model_key
    key = f"{size}|{device}|{compute_type}|{model_path}"
    if _model is None or _model_key != key:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError(
                "faster-whisper is not installed.\n"
                "Run: pip install faster-whisper"
            )
        kwargs: dict = {"device": device, "compute_type": compute_type}
        if model_path:
            kwargs["download_root"] = model_path
        _model = WhisperModel(size, **kwargs)
        _model_key = key
    return _model


def transcribe(audio_path: str) -> str:
    """Transcribe a WAV file locally. Returns clean text string."""
    s = _settings()
    model = _get_model(s["model_size"], s["device"], s["compute_type"], s["model_path"])
    segments, _ = model.transcribe(
        audio_path,
        beam_size=5,
        language=s["language"],
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


def current_model_size() -> str:
    return os.environ.get("WHISPER_MODEL_SIZE", "base")
