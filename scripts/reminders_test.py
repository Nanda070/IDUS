"""Sanity check for the reminders tool + due-reminder polling logic."""

import datetime
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain
from memory.store import list_due_reminders, mark_reminder_done

PROMPTS = [
    "Напомни мне через 1 минуту попить воды",
    "Какие у меня есть напоминания?",
]


def main() -> None:
    brain = Brain()
    for prompt in PROMPTS:
        print(f"> {prompt}")
        print(f"< {brain.reply(prompt)}\n")

    print("Simulating time passing: checking with a due time 2 minutes in the future...")
    future = (datetime.datetime.now() + datetime.timedelta(minutes=2)).isoformat()
    due = list_due_reminders(future)
    print("Due reminders:", due)
    for reminder_id, text in due:
        mark_reminder_done(reminder_id)
        print(f"Would announce: 'Напоминаю: {text}'")


if __name__ == "__main__":
    main()
