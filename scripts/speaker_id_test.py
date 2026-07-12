"""Record a short clip and identify which enrolled speaker it matches (if any)."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import sounddevice as sd

from memory.store import load_speaker_embeddings
from voice.speaker_id import SpeakerIdentifier

SAMPLE_RATE = 16000
DURATION_S = 5


def main() -> None:
    print("Loading speaker embedding model...")
    identifier = SpeakerIdentifier()
    enrolled = load_speaker_embeddings()
    identifier.load_enrolled(enrolled)
    print(f"Enrolled speakers: {list(enrolled.keys())}")

    print(f"Recording {DURATION_S}s - speak...")
    audio = sd.rec(int(DURATION_S * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    audio = audio[:, 0]

    name, score = identifier.identify(audio)
    print(f"Identified: {name!r} (score={score:.3f})")


if __name__ == "__main__":
    main()
