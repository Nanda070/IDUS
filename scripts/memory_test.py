"""Verify long-term memory survives across separate Brain instances (simulating a restart)."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain
from memory.store import list_facts


def main() -> None:
    print("Facts before:", list_facts())

    brain1 = Brain()
    print("> Запомни, что я не люблю помидоры.")
    print("<", brain1.reply("Запомни, что я не люблю помидоры."))

    print("\nFacts after remember call:", list_facts())

    # Fresh Brain instance = simulates a new jarvis_loop.py process starting up
    brain2 = Brain()
    print("\n(new Brain instance, simulating restart)")
    print("> Что ты знаешь о моих пищевых предпочтениях?")
    print("<", brain2.reply("Что ты знаешь о моих пищевых предпочтениях?"))


if __name__ == "__main__":
    main()
