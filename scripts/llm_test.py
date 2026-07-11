"""Quick text-only sanity check for brain.llm.Brain, no audio involved."""

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain
from tools.timer import completed_timers

PROMPTS = [
    "Какая сегодня погода в Баку?",
]


def main() -> None:
    brain = Brain()
    for prompt in PROMPTS:
        print(f"> {prompt}")
        start = time.monotonic()
        reply = brain.reply(prompt)
        elapsed = time.monotonic() - start
        print(f"< ({elapsed:.1f}s) {reply}\n")



if __name__ == "__main__":
    main()
