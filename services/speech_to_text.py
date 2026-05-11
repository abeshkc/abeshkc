from pathlib import Path
from services.local_whisper_service import transcribe as _local_transcribe


def transcribe_audio(audio_path: str | Path) -> str:
    """Transcribe audio using the local faster-whisper model."""
    return _local_transcribe(str(audio_path))
