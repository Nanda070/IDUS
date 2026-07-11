"""Reminder tool - persisted in SQLite so due reminders survive process restarts."""

import datetime

from memory.store import add_reminder, list_pending_reminders


def set_reminder(text: str, minutes_from_now: int) -> str:
    """
    Remind the user about something after a given number of minutes, even across
    a restart of the assistant (unlike set_timer, which is for short-lived
    countdowns and does not survive a restart).

    Args:
        text: What to remind the user about, e.g. "купить хлеб".
        minutes_from_now: How many minutes from now the reminder is due.

    Returns:
        str: Confirmation that the reminder was saved.
    """
    due_at = datetime.datetime.now() + datetime.timedelta(minutes=minutes_from_now)
    add_reminder(text, due_at.isoformat())
    return f"Напомню про «{text}» через {minutes_from_now} мин."


def list_reminders() -> str:
    """
    List all reminders that haven't gone off yet.

    Returns:
        str: The pending reminders with their due time, or a message that there are none.
    """
    pending = list_pending_reminders()
    if not pending:
        return "Нет активных напоминаний."
    lines = []
    for _id, text, due_at in pending:
        due = datetime.datetime.fromisoformat(due_at)
        lines.append(f"- {text} (в {due.strftime('%Y-%m-%d %H:%M')})")
    return "\n".join(lines)


__all__ = ["set_reminder", "list_reminders"]
