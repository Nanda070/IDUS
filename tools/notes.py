"""Voice notes tool - dictate something, save it as text, look it up later."""

import datetime

from memory.store import add_note, list_notes


def save_note(text: str) -> str:
    """
    Save a quick note (dictated by the user) as text for later.

    Args:
        text: The note content.

    Returns:
        str: Confirmation that the note was saved.
    """
    add_note(text, datetime.datetime.now().isoformat())
    return "Записал."


def get_recent_notes() -> str:
    """
    Get the most recent saved notes.

    Returns:
        str: Recent notes with their date, or a message that there are none.
    """
    notes = list_notes()
    if not notes:
        return "Заметок пока нет."
    lines = []
    for ts, text in notes:
        date = ts[:10]
        lines.append(f"- ({date}) {text}")
    return "\n".join(lines)


__all__ = ["save_note", "get_recent_notes"]
