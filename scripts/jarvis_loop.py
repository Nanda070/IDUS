"""IDUS voice loop.

Idle, listening for the "Hey Jarvis" wake word -> on trigger, VAD-gated
recording of a command -> transcribe with faster-whisper -> get a reply from
the local LLM (Ollama) -> speak it with Piper -> back to idle.
"""

import datetime
import queue
import sys
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import sounddevice as sd

from brain.llm import Brain
from brain.reflection import run_reflection
from memory.store import get_due_automation_rules, list_due_reminders, mark_automation_rule_run, mark_reminder_done
from voice.stt import Transcriber
from voice.tts import Speaker, is_cyrillic
from voice.vad import CHUNK_SAMPLES as VAD_CHUNK
from voice.vad import SAMPLE_RATE, SpeechSegmenter
from voice.wakeword import CHUNK_SAMPLES as WAKE_CHUNK
from voice.wakeword import WakeWordDetector

BASE_CHUNK = 256  # samples (16ms) - divides both VAD_CHUNK (512) and WAKE_CHUNK (1280)
MIN_UTTERANCE_S = 0.4
MAX_LISTEN_S = 8.0  # abort back to idle if no complete utterance within this long
REMINDER_CHECK_INTERVAL_S = 5.0
AUTOMATION_CHECK_INTERVAL_S = 20.0
REFLECTION_CHECK_INTERVAL_S = 300.0  # 5 min - cheap check, actual reflection runs once/day
REFLECTION_HOUR = 3  # run once after 3 AM if not already run today

STATE_IDLE = "idle"
STATE_LISTENING = "listening"


def main() -> None:
    print("Loading wake word + VAD + STT + TTS models, connecting to Ollama...")
    wake_detector = WakeWordDetector()
    segmenter = SpeechSegmenter()
    transcriber = Transcriber()
    speaker = Speaker()
    brain = Brain()

    state = STATE_IDLE
    wake_buf = np.zeros(0, dtype=np.float32)
    vad_buf = np.zeros(0, dtype=np.float32)
    recording: list[np.ndarray] = []
    listen_started_at = 0.0
    is_speaking = threading.Event()

    wake_events: queue.Queue[float] = queue.Queue()
    utterances: queue.Queue[np.ndarray] = queue.Queue()

    def enter_listening() -> None:
        nonlocal state, listen_started_at, vad_buf
        state = STATE_LISTENING
        listen_started_at = time.monotonic()
        segmenter.reset()
        recording.clear()
        vad_buf = np.zeros(0, dtype=np.float32)

    def enter_idle() -> None:
        nonlocal state, wake_buf
        state = STATE_IDLE
        wake_buf = np.zeros(0, dtype=np.float32)

    def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        nonlocal state, wake_buf, vad_buf
        if status:
            print(f"stream status: {status}")
        if is_speaking.is_set():
            return  # don't listen to our own TTS output
        chunk = indata[:, 0].copy()

        if state == STATE_IDLE:
            wake_buf = np.concatenate([wake_buf, chunk])
            while len(wake_buf) >= WAKE_CHUNK:
                frame, wake_buf = wake_buf[:WAKE_CHUNK], wake_buf[WAKE_CHUNK:]
                score = wake_detector.process_chunk(frame)
                if score >= wake_detector.threshold:
                    wake_events.put(score)
                    enter_listening()
                    break

        elif state == STATE_LISTENING:
            if time.monotonic() - listen_started_at > MAX_LISTEN_S:
                enter_idle()
                return
            vad_buf = np.concatenate([vad_buf, chunk])
            while len(vad_buf) >= VAD_CHUNK:
                frame, vad_buf = vad_buf[:VAD_CHUNK], vad_buf[VAD_CHUNK:]
                recording.append(frame)
                event = segmenter.process_chunk(frame)
                if event == "end":
                    utterances.put(np.concatenate(recording))
                    enter_idle()
                    break

    last_reminder_check = 0.0
    last_automation_check = 0.0

    def announce_due_reminders() -> None:
        nonlocal last_reminder_check
        now = time.monotonic()
        if now - last_reminder_check < REMINDER_CHECK_INTERVAL_S:
            return
        last_reminder_check = now
        if state != STATE_IDLE:
            return  # don't interrupt an active wake/listen/reply cycle
        due = list_due_reminders(datetime.datetime.now().isoformat())
        for reminder_id, text in due:
            mark_reminder_done(reminder_id)
            print(f"[reminder] {text!r}")
            is_speaking.set()
            try:
                speaker.speak(f"Напоминаю: {text}")
            finally:
                is_speaking.clear()

    def run_due_automations() -> None:
        nonlocal last_automation_check
        now = time.monotonic()
        if now - last_automation_check < AUTOMATION_CHECK_INTERVAL_S:
            return
        last_automation_check = now
        if state != STATE_IDLE:
            return  # don't interrupt an active wake/listen/reply cycle
        current_time = datetime.datetime.now().strftime("%H:%M")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        due = get_due_automation_rules(current_time, today)
        for rule_id, action in due:
            mark_automation_rule_run(rule_id, today)
            print(f"[automation] {action!r}")
            try:
                reply = brain.reply(action)
            except Exception as exc:
                print(f"(automation LLM error: {exc})")
                continue
            is_speaking.set()
            try:
                speaker.speak(reply)
            finally:
                is_speaking.clear()

    last_reflection_check = 0.0

    def run_reflection_if_due() -> None:
        nonlocal last_reflection_check
        now = time.monotonic()
        if now - last_reflection_check < REFLECTION_CHECK_INTERVAL_S:
            return
        last_reflection_check = now
        if datetime.datetime.now().hour < REFLECTION_HOUR:
            return
        try:
            summary = run_reflection()
        except Exception as exc:
            print(f"(reflection error: {exc})")
            return
        if summary:
            print(f"[reflection] {summary}")

    print("Listening for 'Hey Jarvis'... (Ctrl+C to stop)")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=BASE_CHUNK,
        callback=callback,
    ):
        try:
            while True:
                announce_due_reminders()
                run_due_automations()
                run_reflection_if_due()

                try:
                    score = wake_events.get(timeout=0.05)
                    print(f"[wake] Hey Jarvis detected (score={score:.3f}) - listening for a command...")
                except queue.Empty:
                    pass

                try:
                    audio = utterances.get(timeout=0.05)
                except queue.Empty:
                    continue

                duration = len(audio) / SAMPLE_RATE
                if duration < MIN_UTTERANCE_S:
                    print(f"(command clip too short: {duration:.2f}s - ignoring, back to idle)")
                    continue

                peak = float(np.abs(audio).max())
                stt_start = time.monotonic()
                text = transcriber.transcribe(audio)
                stt_elapsed = time.monotonic() - stt_start
                print(f"[you] ({duration:.2f}s, peak={peak:.3f}, stt={stt_elapsed:.1f}s) {text!r}")
                if not text:
                    print("(nothing recognized, back to idle)")
                    continue

                llm_start = time.monotonic()
                try:
                    reply = brain.reply(text)
                except Exception as exc:
                    print(f"(LLM error: {exc})")
                    reply = "Извини, не могу сейчас связаться с мозгом." if is_cyrillic(text) else "Sorry, I can't reach my brain right now."
                llm_elapsed = time.monotonic() - llm_start
                print(f"[idus] (llm={llm_elapsed:.1f}s) {reply!r}")

                synth_start = time.monotonic()
                tts_audio, tts_rate = speaker.synthesize(reply)
                synth_elapsed = time.monotonic() - synth_start
                time_to_speak = stt_elapsed + llm_elapsed + synth_elapsed
                print(f"[timing] time to first sound: {time_to_speak:.1f}s (stt={stt_elapsed:.1f}s llm={llm_elapsed:.1f}s synth={synth_elapsed:.1f}s)")

                is_speaking.set()
                try:
                    if tts_audio.size:
                        sd.play(tts_audio, samplerate=tts_rate)
                        sd.wait()
                finally:
                    is_speaking.clear()

                if brain.awaiting_confirmation:
                    print("[idus] awaiting confirmation - listening without wake word...")
                    enter_listening()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
