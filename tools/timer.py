"""Timer tool - schedules a delayed announcement, polled by the main voice loop."""

import queue
import threading

completed_timers: "queue.Queue[str]" = queue.Queue()


def set_timer(seconds: int, label: str = "") -> str:
    """
    Set a timer that will announce itself out loud after the given number of seconds.

    Args:
        seconds: How many seconds from now the timer should go off.
        label: Optional short name for the timer, e.g. "pasta" or "tea".

    Returns:
        str: Confirmation that the timer was set.
    """
    def fire() -> None:
        message = f'Таймер "{label}" завершён!' if label else "Таймер завершён!"
        completed_timers.put(message)

    threading.Timer(seconds, fire).start()
    name = f' "{label}"' if label else ""
    return f"Таймер{name} на {seconds} секунд поставлен."
