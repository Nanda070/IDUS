"""Time and date built-in tools for the LLM."""

import datetime


def get_current_time() -> str:
    """
    Get the current time in the user's local timezone.

    Returns:
        str: The current time, e.g. "14:32".
    """
    return datetime.datetime.now().strftime("%H:%M")


def get_current_date() -> str:
    """
    Get today's date.

    Returns:
        str: Today's date, e.g. "2026-07-11 (Saturday)".
    """
    return datetime.datetime.now().strftime("%Y-%m-%d (%A)")
