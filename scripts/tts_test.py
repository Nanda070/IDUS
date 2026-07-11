"""Synthesize and play a Russian and an English phrase to sanity-check Silero TTS."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice.tts import Speaker

PHRASES = [
    "Привет! Меня зовут Айдус, и я тебя прекрасно слышу.",
    "Hello! My name is IDUS, and I can hear you just fine.",
]


def main() -> None:
    print("Loading Silero TTS voices (ru + en)...")
    speaker = Speaker()
    for phrase in PHRASES:
        print(f"Speaking: {phrase!r}")
        speaker.speak(phrase)
    print("Done.")


if __name__ == "__main__":
    main()
