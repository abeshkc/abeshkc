def send(title: str, message: str = "") -> None:
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message or title,
            app_name="NoteRemind",
            timeout=10,
        )
    except Exception:
        print(f"[REMINDER] {title}: {message}")
