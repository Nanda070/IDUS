"""Shopping list tool - add items by voice, check the list on your phone/screen later."""

from memory.store import add_shopping_item, clear_shopping_list, list_shopping_items


def add_to_shopping_list(item: str) -> str:
    """
    Add an item to the shopping list.

    Args:
        item: What to add, e.g. "молоко".

    Returns:
        str: Confirmation that the item was added.
    """
    add_shopping_item(item)
    return f"Добавил «{item}» в список покупок."


def get_shopping_list() -> str:
    """
    Get the current shopping list.

    Returns:
        str: The items on the list, or a message that it's empty.
    """
    items = list_shopping_items()
    if not items:
        return "Список покупок пуст."
    return "\n".join(f"- {item}" for _id, item in items)


def empty_shopping_list() -> str:
    """
    Clear the shopping list (e.g. after finishing shopping).

    Returns:
        str: Confirmation that the list was cleared.
    """
    clear_shopping_list()
    return "Список покупок очищен."


__all__ = ["add_to_shopping_list", "get_shopping_list", "empty_shopping_list"]
