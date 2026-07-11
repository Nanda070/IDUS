"""Long-term memory tool - lets the LLM save facts about the user for future sessions."""

from memory.store import add_fact


def remember(fact: str) -> str:
    """
    Save a fact about the user or their preferences for future conversations
    (e.g. likes/dislikes, routines, names, recurring plans). Only call this when
    the user shares something worth remembering long-term, not for one-off requests.

    Args:
        fact: A short, self-contained statement, e.g. "Не любит помидоры".

    Returns:
        str: Confirmation that the fact was saved.
    """
    add_fact(fact)
    return "Запомнил."


__all__ = ["remember"]
