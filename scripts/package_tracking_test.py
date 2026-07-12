"""Check whether the existing web_search tool gives a usable answer for package tracking."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain

PROMPTS = [
    "Отследи посылку с трек-номером RB123456785CN",
    "Где моя посылка от DHL, номер 1234567890?",
]


def main() -> None:
    brain = Brain()
    for prompt in PROMPTS:
        print(f"> {prompt}")
        print(f"< {brain.reply(prompt)}\n")


if __name__ == "__main__":
    main()
