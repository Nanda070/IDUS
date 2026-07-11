"""Messaging tool - MOCK implementation.

Placeholder for Stage 14 (real Telegram/WhatsApp integration). Doesn't actually
send anything yet - just simulates the action so the agentic core's
confirmation flow has a real sensitive action to gate, and so the rest of the
pipeline (tool schema, confirmation UX) is already proven once the real
send API is wired in.
"""


def send_message(to: str, text: str) -> str:
    """
    Send a text message to a contact via messenger (currently a mock - does
    not actually send anything, real integration is future work).

    Args:
        to: Who to send the message to, e.g. "Максим" or a phone number.
        text: The message text to send.

    Returns:
        str: Confirmation that the (mock) message was sent.
    """
    print(f"[MOCK send_message] to={to!r} text={text!r}")
    return f"Сообщение для {to} отправлено (заглушка - реальной интеграции пока нет)."


__all__ = ["send_message"]
