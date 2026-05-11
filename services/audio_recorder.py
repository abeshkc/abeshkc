import os
import threading
import tempfile

try:
    import sounddevice as sd
    import numpy as np
    import scipy.io.wavfile as wav
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

SAMPLE_RATE = 16_000  # Whisper works best at 16 kHz


class AudioRecorder:
    def __init__(self):
        self._frames: list = []
        self._recording = False
        self._thread: threading.Thread | None = None
        self._tmp_path: str | None = None
        self._last_chunk = None  # updated on each read; used for amplitude

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def current_level(self) -> float:
        """RMS amplitude of the latest audio chunk, normalised 0.0–1.0."""
        chunk = self._last_chunk
        if chunk is None or not AUDIO_AVAILABLE:
            return 0.0
        try:
            import numpy as np
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
            return min(rms / 6000.0, 1.0)
        except Exception:
            return 0.0

    def start(self) -> None:
        if not AUDIO_AVAILABLE:
            raise RuntimeError(
                "sounddevice or scipy not installed.\nRun: pip install sounddevice scipy numpy"
            )
        self._frames = []
        self._recording = True
        self._thread = threading.Thread(target=self._record, daemon=True)
        self._thread.start()

    def stop(self) -> str:
        """Stop recording and return path to saved WAV file."""
        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)
        return self._save()

    def cleanup(self) -> None:
        """Delete the temporary WAV file unless VOICE_DEBUG=1."""
        if os.environ.get("VOICE_DEBUG") == "1":
            return
        if self._tmp_path and os.path.exists(self._tmp_path):
            try:
                os.unlink(self._tmp_path)
            except OSError:
                pass
            self._tmp_path = None

    # ── private ──────────────────────────────────────────────────────────

    def _record(self) -> None:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
            while self._recording:
                chunk, _ = stream.read(1024)
                c = chunk.copy()
                self._frames.append(c)
                self._last_chunk = c

    def _save(self) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        self._tmp_path = tmp.name
        if self._frames:
            import numpy as np
            import scipy.io.wavfile as wav_io
            audio = np.concatenate(self._frames, axis=0)
            wav_io.write(self._tmp_path, SAMPLE_RATE, audio)
        return self._tmp_path
