"""Sanity check for Memory 2.0: generate some conversation, force a reflection run, verify episode + new facts."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain
from brain.reflection import run_reflection
from memory.store import list_facts, list_recent_episodes

CONVO = [
    "Привет! Я сегодня весь день изучал Python и немного устал.",
    "Кстати, я обычно ложусь спать около полуночи, если что.",
    "Спасибо, увидимся позже.",
]


def main() -> None:
    brain = Brain()
    for msg in CONVO:
        print(f"> {msg}")
        print(f"< {brain.reply(msg)}\n")

    print("Facts before reflection:", list_facts())
    print("Running forced reflection...")
    summary = run_reflection(force=True)
    print(f"Episode summary: {summary!r}")
    print("Facts after reflection:", list_facts())
    print("Recent episodes:", list_recent_episodes())

    print("\nNew Brain instance (simulating restart) - check episode is in context:")
    brain2 = Brain()
    print(f"> Что ты помнишь обо мне и о вчерашнем дне?")
    print(f"< {brain2.reply('Что ты помнишь обо мне и о вчерашнем дне?')}")


if __name__ == "__main__":
    main()
