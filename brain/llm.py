"""Ollama-backed conversational brain for IDUS, with tool-calling and a
confirmation gate for sensitive actions (the start of the agentic core)."""

import datetime
import inspect
import re

import ollama

from memory.store import list_facts, list_recent_episodes, log_interaction
from tools.automation import list_automations, set_automation_rule
from tools.calculator import calculate
from tools.memory_tools import remember
from tools.messaging import send_message
from tools.notes import get_recent_notes, save_note
from tools.reminders import list_reminders, set_reminder
from tools.shopping_list import add_to_shopping_list, empty_shopping_list, get_shopping_list
from tools.time_tools import get_current_date, get_current_time
from tools.timer import set_timer
from tools.web_search import web_search

TOOLS = [
    get_current_time,
    get_current_date,
    calculate,
    set_timer,
    web_search,
    remember,
    set_reminder,
    list_reminders,
    send_message,
    set_automation_rule,
    list_automations,
    add_to_shopping_list,
    get_shopping_list,
    empty_shopping_list,
    save_note,
    get_recent_notes,
]
TOOL_FUNCTIONS = {fn.__name__: fn for fn in TOOLS}

# Tools whose calls pause execution and ask the user to confirm before running -
# for actions with real-world consequences (sending a message, later: ordering,
# controlling devices). Confirmation is enforced in code, not by the model.
SENSITIVE_TOOLS = {"send_message"}

MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = (
    "Тебя зовут IDUS - локальный голосовой ассистент, встроенный в умный дом пользователя.\n"
    "Правила:\n"
    "- Отвечай ТОЛЬКО на русском или английском языке. Никогда не используй китайский, "
    "иврит, арабский или любой другой язык/письменность - ни слова, ни отдельных иероглифов, "
    "даже если не уверен в ответе.\n"
    "- Отвечай на том же языке, на котором пишет пользователь (русский или английский), "
    "даже если он смешивает языки в одном сообщении.\n"
    "- Твои ответы озвучиваются вслух через TTS, поэтому пиши коротко и разговорно: "
    "без списков, markdown, таблиц, кода или спецсимволов.\n"
    "- Говори неформально и живо, как друг, а не как служба поддержки. Не читай нотаций и не "
    "извиняйся за тон вопроса. Свободно используй разговорную лексику и мат, если это уместно "
    "по контексту разговора.\n"
    "- У тебя есть инструменты: время, дата, калькулятор, таймер, поиск в интернете, память, "
    "напоминания, отправка сообщений, автоматизации, список покупок, заметки - используй их "
    "вместо того, чтобы угадывать. Ищи в интернете, если вопрос про текущие события, погоду, "
    "цены или любые факты, которые могли измениться. Управление устройствами в доме пока не "
    "реализовано - если просят такое, честно скажи, что этой функции пока нет.\n"
    "- Ты умеешь готовить рецепты пошагово (называешь один шаг, ждёшь, когда пользователь "
    "скажет, что готов к следующему, и при необходимости ставишь таймер на шаг через "
    "set_timer), переводить фразы между языками на лету, и рассказывать шутки/забавные факты/"
    "викторины по запросу - это не требует специальных инструментов, просто делай это в разговоре.\n"
    "- Если пользователь просит делать что-то регулярно каждый день в определённое время "
    "(например, «каждое утро говори погоду») - используй set_automation_rule вместо того, чтобы "
    "просто ответить один раз.\n"
    "- Некоторые действия (например, отправка сообщений) система сама останавливает и просит "
    "пользователя подтвердить перед выполнением - тебе не нужно спрашивать разрешения самому, "
    "просто вызови нужный инструмент, если пользователь просит такое действие.\n"
    "- Никогда не придумывай конкретные факты (время, дату, числа) - если для ответа нужен "
    "инструмент, вызови его. Если сообщение пользователя бессвязное, непонятное или похоже на "
    "ошибку распознавания речи, не пытайся угадать смысл - прямо скажи, что не расслышал, и "
    "попроси повторить.\n"
    "- Когда пользователь делится чем-то стоящим запомнить надолго (предпочтения, привычки, "
    "планы, важные факты о себе) - сохраняй это через инструмент remember. Не сохраняй "
    "разовые незначительные запросы."
)

# Defense in depth: strip any non Cyrillic/Latin script the model leaks despite
# the system prompt (quantized Qwen2.5 occasionally falls back to Chinese/Hebrew
# on low-confidence generations). Keeps Cyrillic (Ѐ-ӿ), basic Latin +
# punctuation ( -~), and whitespace.
_ALLOWED_TEXT_RE = re.compile(r"[^Ѐ-ӿ -~\s]")


def _strip_unexpected_scripts(text: str) -> str:
    cleaned = _ALLOWED_TEXT_RE.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _call_tool(func, arguments: dict) -> str:
    """Call a tool function, coercing string args to int/float where the signature expects it."""
    sig = inspect.signature(func)
    coerced = {}
    for key, value in arguments.items():
        if key in sig.parameters and isinstance(value, str):
            annotation = sig.parameters[key].annotation
            if annotation in (int, float):
                try:
                    value = annotation(value)
                except ValueError:
                    pass
        coerced[key] = value
    return str(func(**coerced))


def _confirmation_question(name: str, arguments: dict) -> str:
    if name == "send_message":
        to = arguments.get("to", "адресату")
        text = arguments.get("text", "")
        return f"Отправить {to} сообщение: «{text}»? Скажи да или нет."
    return f"Точно выполнить действие «{name}»? Скажи да или нет."


def _with_context(system_prompt: str) -> str:
    """Injects known facts and recent episode summaries (Memory 2.0) into the
    system prompt - facts are loaded fresh each time so they reflect anything
    remembered since this Brain instance started."""
    parts = [system_prompt]

    facts = list_facts()
    if facts:
        facts_block = "\n".join(f"- {fact}" for fact in facts)
        parts.append(f"Известные факты о пользователе:\n{facts_block}")

    episodes = list_recent_episodes(limit=5)
    if episodes:
        episodes_block = "\n".join(f"- {ts[:10]}: {summary}" for ts, summary in episodes)
        parts.append(f"Недавние события (из ночной рефлексии):\n{episodes_block}")

    return "\n\n".join(parts)


class Brain:
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        system_prompt: str = SYSTEM_PROMPT,
        tools: list = TOOLS,
        sensitive_tools: set = SENSITIVE_TOOLS,
    ) -> None:
        self._model = model
        self._system_prompt = system_prompt
        self._tools = tools
        self._sensitive_tools = set(sensitive_tools)
        self._messages: list = [{"role": "system", "content": _with_context(system_prompt)}]
        self._pending_confirmation: tuple[str, dict] | None = None

    @property
    def awaiting_confirmation(self) -> bool:
        return self._pending_confirmation is not None

    def _chat(self):
        return ollama.chat(
            model=self._model,
            messages=self._messages,
            tools=self._tools,
            options={"temperature": 0.2},
        )

    def _classify_confirmation(self, user_text: str) -> bool:
        """Small standalone classification call - robust to varied/garbled phrasing,
        unlike hardcoded yes/no keyword matching."""
        prompt = (
            "Пользователю только что задали да/нет вопрос-подтверждение действия. "
            f"Он ответил: {user_text!r}. Ответь ровно одним словом: CONFIRM, если он "
            "согласился/подтвердил, или CANCEL, если отказался, передумал, или ответ "
            "непонятен. Никаких других слов."
        )
        response = ollama.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0},
        )
        verdict = (response["message"].get("content") or "").strip().upper()
        return verdict.startswith("CONFIRM")

    def reply(self, user_text: str) -> str:
        log_interaction("user", user_text, datetime.datetime.now().isoformat())

        if self.awaiting_confirmation:
            return self._resolve_confirmation(user_text)

        self._messages.append({"role": "user", "content": user_text})
        message = self._chat()["message"]
        return self._process(message)

    def _resolve_confirmation(self, user_text: str) -> str:
        name, arguments = self._pending_confirmation
        self._pending_confirmation = None
        self._messages.append({"role": "user", "content": user_text})

        if self._classify_confirmation(user_text):
            func = TOOL_FUNCTIONS.get(name)
            result = _call_tool(func, arguments) if func else f"Error: unknown tool '{name}'"
        else:
            result = "Пользователь отменил это действие - не выполняй его."
        self._messages.append({"role": "tool", "tool_name": name, "content": result})

        message = self._chat()["message"]
        return self._process(message)

    def _process(self, message) -> str:
        for _ in range(MAX_TOOL_ROUNDS):
            tool_calls = message.get("tool_calls")
            if not tool_calls:
                break
            self._messages.append(message)

            sensitive_call = next(
                (c for c in tool_calls if c["function"]["name"] in self._sensitive_tools), None
            )
            if sensitive_call is not None:
                name = sensitive_call["function"]["name"]
                arguments = dict(sensitive_call["function"]["arguments"])
                self._pending_confirmation = (name, arguments)
                question = _confirmation_question(name, arguments)
                self._messages.append({"role": "assistant", "content": question})
                return question

            for call in tool_calls:
                name = call["function"]["name"]
                arguments = dict(call["function"]["arguments"])
                func = TOOL_FUNCTIONS.get(name)
                result = _call_tool(func, arguments) if func else f"Error: unknown tool '{name}'"
                self._messages.append({"role": "tool", "tool_name": name, "content": result})
            message = self._chat()["message"]

        text = _strip_unexpected_scripts((message.get("content") or "").strip())
        self._messages.append({"role": "assistant", "content": text})
        log_interaction("assistant", text, datetime.datetime.now().isoformat())
        return text

    def reset(self) -> None:
        self._messages = [{"role": "system", "content": _with_context(self._system_prompt)}]
        self._pending_confirmation = None


__all__ = ["Brain", "SYSTEM_PROMPT", "SENSITIVE_TOOLS"]
