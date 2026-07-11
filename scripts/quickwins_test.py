"""Sanity check for the quick-win features batch: shopping list, notes, translation, jokes, recipe."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brain.llm import Brain

PROMPTS = [
    "Добавь молоко и хлеб в список покупок",
    "Что у меня в списке покупок?",
    "Запиши заметку: не забыть купить подарок на день рождения другу",
    "Как будет 'доброе утро' по-английски?",
    "Расскажи короткую шутку",
    "Хочу приготовить омлет, расскажи как, по шагам",
]


def main() -> None:
    brain = Brain()
    for prompt in PROMPTS:
        print(f"> {prompt}")
        print(f"< {brain.reply(prompt)}\n")


if __name__ == "__main__":
    main()
