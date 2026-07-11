"""Sanity check for the automation engine: set a rule, verify it becomes due, verify it only fires once/day."""

import datetime
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain
from memory.store import get_due_automation_rules, mark_automation_rule_run

PROMPT = "Каждый день в 7:00 говори мне какая погода на сегодня"


def main() -> None:
    brain = Brain()
    print(f"> {PROMPT}")
    print(f"< {brain.reply(PROMPT)}\n")

    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    due = get_due_automation_rules(current_time, today)
    print(f"Due now ({current_time}, {today}): {due}")

    for rule_id, action in due:
        mark_automation_rule_run(rule_id, today)

    due_again = get_due_automation_rules(current_time, today)
    print(f"Due again same day (should be empty for the rule just run): {due_again}")


if __name__ == "__main__":
    main()
