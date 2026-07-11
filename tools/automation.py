"""Automation engine tool - daily time-triggered rules the LLM can set up.

Not a hardcoded "morning briefing" - a general mechanism. A rule is just a
time of day + a natural-language instruction that gets fed back through the
brain when triggered, exactly as if the user had said it.
"""

from memory.store import add_automation_rule, list_automation_rules


def set_automation_rule(time_of_day: str, action: str) -> str:
    """
    Set up a recurring daily automation: at the given time, IDUS will act on
    the instruction automatically, without the user asking.

    Args:
        time_of_day: 24h time the rule fires, e.g. "08:00".
        action: What IDUS should do/say at that time, as a natural-language
            instruction, e.g. "скажи какая погода и какие новости".

    Returns:
        str: Confirmation that the rule was saved.
    """
    add_automation_rule(time_of_day, action)
    return f"Готово, каждый день в {time_of_day} буду делать: {action}."


def list_automations() -> str:
    """
    List all recurring daily automations that are currently set up.

    Returns:
        str: The rules with their time and action, or a message that there are none.
    """
    rules = list_automation_rules()
    if not rules:
        return "Нет настроенных автоматизаций."
    lines = [f"- в {t}: {a}" + ("" if enabled else " (выключено)") for _rid, t, a, enabled in rules]
    return "\n".join(lines)


__all__ = ["set_automation_rule", "list_automations"]
