"""Live console demo: prints when Silero VAD detects speech start/end on the mic stream."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice.vad import run_console_demo

DURATION_S = 20


def main() -> None:
    print(f"Listening for {DURATION_S}s - speak a few times with pauses in between...")

    def on_event(event: str) -> None:
        ts = time.strftime("%H:%M:%S")
        label = "SPEECH START" if event == "start" else "SPEECH END"
        print(f"[{ts}] {label}")

    run_console_demo(DURATION_S, on_event)
    print("Done.")


if __name__ == "__main__":
    main()
