import sys
import threading
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables being set manually

from database import init_db
from core.reminders import get_due_reminders, mark_done
from notifications import send
from ui.app import App


def _reminder_loop() -> None:
    while True:
        try:
            for r in get_due_reminders():
                send(r["title"], r["message"])
                mark_done(r["id"])
        except Exception as exc:
            print(f"[reminder loop] {exc}", file=sys.stderr)
        time.sleep(60)


def main() -> None:
    init_db()
    threading.Thread(target=_reminder_loop, daemon=True).start()
    App().mainloop()


if __name__ == "__main__":
    main()
