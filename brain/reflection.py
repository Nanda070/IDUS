"""Nightly reflection - summarizes the day's interactions into an episode and
extracts new durable facts the model noticed along the way.

Not a tool the LLM calls itself - a scheduled background job (see
scripts/jarvis_loop.py's run_nightly_reflection_if_due), same idea as a person
journaling before bed and updating what they've learned about a friend.
"""

import datetime
import re

import ollama

from memory.store import (
    add_episode,
    add_fact,
    get_interactions_since,
    get_reflection_last_run,
    list_facts,
    set_reflection_last_run,
)

MODEL = "qwen2.5:7b"
LOOKBACK_HOURS = 20
FACT_PREFIX = "ФАКТ:"
# Matches "ФАКТ: ..." anywhere in a line, not just at the very start - the model
# doesn't reliably avoid list numbering ("2. ФАКТ: ...") despite instructions,
# so a strict startswith() check silently dropped real facts.
_FACT_PATTERN = re.compile(re.escape(FACT_PREFIX) + r"\s*(.+)")


def run_reflection(force: bool = False) -> str | None:
    """Returns the new episode summary, or None if reflection didn't run
    (already ran today, or nothing happened) or wasn't due to run."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if not force and get_reflection_last_run() == today:
        return None

    since = (datetime.datetime.now() - datetime.timedelta(hours=LOOKBACK_HOURS)).isoformat()
    interactions = get_interactions_since(since)
    if not interactions:
        set_reflection_last_run(today)
        return None

    transcript = "\n".join(f"{role}: {content}" for _ts, role, content in interactions)
    known_facts = "\n".join(list_facts()) or "(пока ничего не известно)"

    prompt = (
        "Вот переписка пользователя с голосовым ассистентом IDUS за последний день:\n\n"
        f"{transcript}\n\n"
        f"Уже известные факты о пользователе:\n{known_facts}\n\n"
        "Сделай две вещи:\n"
        "1. Напиши очень короткое резюме дня (1-2 предложения на русском) - чем пользователь "
        "занимался или интересовался, по мнению переписки.\n"
        f"2. Если из переписки видны НОВЫЕ устойчивые факты о пользователе (предпочтения, "
        f"привычки, распорядок), которых нет в списке известных - перечисли их, каждый на "
        f"отдельной строке, начиная строго с '{FACT_PREFIX} '. Если новых фактов нет - не пиши "
        "такие строки вообще."
    )
    response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}], options={"temperature": 0.3})
    content = (response["message"].get("content") or "").strip()

    summary_lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _FACT_PATTERN.search(line)
        if match:
            fact = match.group(1).strip()
            if fact:
                add_fact(fact)
        else:
            summary_lines.append(line)

    summary = " ".join(summary_lines).strip() or "Ничего примечательного за день не произошло."
    add_episode(summary, datetime.datetime.now().isoformat())
    set_reflection_last_run(today)
    return summary


__all__ = ["run_reflection"]
