"""Compare a handful of English Silero v3_en speakers to pick a clear male voice by ear."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sounddevice as sd
import torch

CANDIDATES = ["en_1", "en_10", "en_25", "en_45", "en_67", "en_90"]
TEXT = "Hello, I am your assistant. This is a test of my voice."
SAMPLE_RATE = 48000


def main() -> None:
    print("Loading English model...")
    model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="en",
        speaker="v3_en",
        trust_repo=True,
    )
    for speaker in CANDIDATES:
        print(f"Speaking as {speaker}...")
        audio = model.apply_tts(text=TEXT, speaker=speaker, sample_rate=SAMPLE_RATE)
        sd.play(audio.numpy(), samplerate=SAMPLE_RATE)
        sd.wait()
    print("Done.")


if __name__ == "__main__":
    main()
