"""Compare Silero-eugene against Piper's 3 male Russian voices, same phrase, back to back."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import sounddevice as sd
import torch
from piper import PiperVoice

VOICES_DIR = Path(__file__).resolve().parent.parent / "config" / "voices" / "piper"
TEXT = "Привет! Меня зовут Айдус, и я тебя прекрасно слышу."


def play(label: str, audio: np.ndarray, sample_rate: int) -> None:
    print(f"--- {label} ---")
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


def main() -> None:
    print("Loading Silero (eugene)...")
    silero_model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v5_5_ru",
        trust_repo=True,
    )
    audio = silero_model.apply_tts(text=TEXT, speaker="eugene", sample_rate=48000, put_accent=True, put_yo=True)
    play("Silero: eugene", audio.numpy(), 48000)

    for name in ["denis", "dmitri", "ruslan"]:
        print(f"Loading Piper ({name})...")
        voice = PiperVoice.load(str(VOICES_DIR / f"ru_RU-{name}-medium.onnx"))
        chunks = [c.audio_float_array for c in voice.synthesize(TEXT)]
        audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
        play(f"Piper: {name}", audio, voice.config.sample_rate)

    print("Done.")


if __name__ == "__main__":
    main()
