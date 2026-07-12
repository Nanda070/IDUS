"""IDUS remote access channel (Stage 11): Telegram bot.

Same Brain (LLM + tools + memory) as the voice loop, just a different I/O
channel - lets the user talk to IDUS from anywhere via Telegram, in text or
voice. Only responds to TELEGRAM_OWNER_ID so strangers can't reach it.

Note: runs as its own process with its own Brain instance, so it does NOT
share live in-conversation turn history with scripts/jarvis_loop.py (the room
voice assistant) - only the persisted long-term facts/reminders (SQLite) are
shared. Fine for v1: the two channels are used at different times in practice.
"""

import asyncio
import datetime
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import av
import numpy as np
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from brain.llm import Brain
from memory.store import (
    get_due_automation_rules_telegram,
    list_due_reminders_telegram,
    mark_automation_rule_telegram_run,
    mark_reminder_telegram_sent,
)
from voice.stt import Transcriber

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OWNER_ID = int(os.environ["TELEGRAM_OWNER_ID"])
DUE_ITEMS_CHECK_INTERVAL_S = 15


def decode_voice_file(path: Path, target_rate: int = 16000) -> np.ndarray:
    """Decode a Telegram voice note (ogg/opus) to a float32 mono array at target_rate."""
    container = av.open(str(path))
    stream = container.streams.audio[0]
    resampler = av.AudioResampler(format="flt", layout="mono", rate=target_rate)
    chunks = []
    for frame in container.decode(stream):
        for resampled in resampler.resample(frame):
            arr = resampled.to_ndarray()
            if arr.size:
                chunks.append(arr.flatten())
    container.close()
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32)


def _owner_only(handler):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is None or update.effective_user.id != OWNER_ID:
            return
        await handler(update, context)

    return wrapped


async def _reply_from_brain(update: Update, context: ContextTypes.DEFAULT_TYPE, brain: Brain, text: str) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        reply = await asyncio.to_thread(brain.reply, text)
    except Exception as exc:
        print(f"(brain error: {exc})")
        reply = "Извини, не могу сейчас связаться с мозгом."
    await update.message.reply_text(reply)


def build_app(brain: Brain, transcriber: Transcriber) -> Application:
    @_owner_only
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"[telegram:text] {update.message.text!r}")
        await _reply_from_brain(update, context, brain, update.message.text)

    @_owner_only
    async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        voice = update.message.voice
        tg_file = await context.bot.get_file(voice.file_id)
        with tempfile.TemporaryDirectory() as tmp:
            ogg_path = Path(tmp) / "voice.ogg"
            await tg_file.download_to_drive(ogg_path)
            audio = await asyncio.to_thread(decode_voice_file, ogg_path)

        text = await asyncio.to_thread(transcriber.transcribe, audio)
        print(f"[telegram:voice] {text!r}")
        if not text:
            await update.message.reply_text("Не расслышал - можешь написать текстом?")
            return
        await update.message.reply_text(f"Расслышал: {text}")
        await _reply_from_brain(update, context, brain, text)

    @_owner_only
    async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("На связи. Пиши или присылай голосовые.")

    async def check_due_items(context: ContextTypes.DEFAULT_TYPE) -> None:
        """Delivers due reminders/automations via Telegram - tracked independently
        from the voice loop's delivery (see memory/store.py's *_telegram columns),
        so being away from home doesn't mean missing them."""
        now_iso = datetime.datetime.now().isoformat()
        for reminder_id, text in await asyncio.to_thread(list_due_reminders_telegram, now_iso):
            await asyncio.to_thread(mark_reminder_telegram_sent, reminder_id)
            await context.bot.send_message(chat_id=OWNER_ID, text=f"Напоминаю: {text}")

        current_time = datetime.datetime.now().strftime("%H:%M")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        due_rules = await asyncio.to_thread(get_due_automation_rules_telegram, current_time, today)
        for rule_id, action in due_rules:
            await asyncio.to_thread(mark_automation_rule_telegram_run, rule_id, today)
            try:
                reply = await asyncio.to_thread(brain.reply, action)
            except Exception as exc:
                print(f"(automation error: {exc})")
                continue
            await context.bot.send_message(chat_id=OWNER_ID, text=reply)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.job_queue.run_repeating(check_due_items, interval=DUE_ITEMS_CHECK_INTERVAL_S, first=DUE_ITEMS_CHECK_INTERVAL_S)
    return app


def main() -> None:
    print("Loading brain + STT, starting Telegram bot...")
    brain = Brain()
    transcriber = Transcriber()
    app = build_app(brain, transcriber)
    print("Listening for Telegram messages... (Ctrl+C to stop)")
    app.run_polling()


if __name__ == "__main__":
    main()
