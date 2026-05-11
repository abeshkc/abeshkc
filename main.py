import sys
import threading
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database import init_db
from core.reminders import get_due_reminders
from notifications import send
from ui.app import App


def _reminder_loop(app: App) -> None:
    """Check for due reminders every 60 s; show system + in-app notification once per session."""
    notified: set[int] = set()
    while True:
        try:
            for r in get_due_reminders():
                if r["id"] not in notified:
                    notified.add(r["id"])
                    send(r["title"], r.get("message", ""))
                    r_copy = dict(r)
                    app.after(0, lambda rem=r_copy: app.show_reminder_popup(rem))
            app.after(0, app.update_missed_badge)
        except Exception as exc:
            print(f"[reminder loop] {exc}", file=sys.stderr)
        time.sleep(60)


def main() -> None:
    init_db()
    app = App()
    threading.Thread(target=_reminder_loop, args=(app,), daemon=True).start()
    app.mainloop()


if __name__ == "__main__":
    main()
