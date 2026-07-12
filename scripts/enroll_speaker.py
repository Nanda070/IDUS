"""Enroll a person's voice for speaker identification. Usage: uv run scripts\\enroll_speaker.py <name>"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import sounddevice as sd

from memory.store import save_speaker_embedding
from voice.speaker_id import SpeakerIdentifier

SAMPLE_RATE = 16000
DURATION_S = 6


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run scripts\\enroll_speaker.py <name>")
        sys.exit(1)
    name = sys.argv[1]

    print("Loading speaker embedding model...")
    identifier = SpeakerIdentifier()

    print(f"Recording {DURATION_S}s for '{name}' - speak naturally (a sentence or two)...")
    audio = sd.rec(int(DURATION_S * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    audio = audio[:, 0]
    peak = float(np.abs(audio).max())
    print(f"Recorded, peak={peak:.3f}")
    if peak < 0.01:
        print("WARNING: very quiet, enrollment may be unreliable.")

    identifier.enroll(name, audio)
    save_speaker_embedding(name, identifier.embedding_bytes(name))
    print(f"Enrolled '{name}'.")


if __name__ == "__main__":
    main()
