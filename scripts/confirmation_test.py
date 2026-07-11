"""Test the sensitive-tool confirmation flow: one run confirms, one cancels."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain


def run(label: str, confirmation_reply: str) -> None:
    print(f"=== {label} ===")
    brain = Brain()

    r1 = brain.reply("Напиши Максиму, что я опаздываю на 10 минут")
    print(f"> Напиши Максиму, что я опаздываю на 10 минут")
    print(f"< {r1}")
    print(f"  awaiting_confirmation={brain.awaiting_confirmation}")

    r2 = brain.reply(confirmation_reply)
    print(f"> {confirmation_reply}")
    print(f"< {r2}")
    print(f"  awaiting_confirmation={brain.awaiting_confirmation}")
    print()


if __name__ == "__main__":
    run("CONFIRM path", "да, отправляй")
    run("CANCEL path", "не, отмена")
