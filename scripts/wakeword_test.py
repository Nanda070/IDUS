"""Live console demo: prints when the 'hey jarvis' placeholder wake word triggers."""

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sounddevice as sd

from voice.wakeword import CHUNK_SAMPLES, WakeWordDetector

SAMPLE_RATE = 16_000
DURATION_S = 30


def main() -> None:
    print("Loading openWakeWord ('hey jarvis' placeholder model)...")
    detector = WakeWordDetector()

    def callback(indata, frames, time_info, status) -> None:
        if status:
            print(f"stream status: {status}")
        chunk = indata[:, 0].copy()
        score = detector.process_chunk(chunk)
        if score >= detector.threshold:
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] WAKE WORD DETECTED (score={score:.3f})")

    print(f"Listening for {DURATION_S}s - say 'Hey Jarvis' a couple of times...")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SAMPLES,
        callback=callback,
    ):
        sd.sleep(int(DURATION_S * 1000))

    print("Done.")


if __name__ == "__main__":
    main()
