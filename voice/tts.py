"""Silero TTS wrapper with RU/EN voice selection by script detection.

Swapped from Piper - Silero's v5.5 Russian model has automated stress marking
and question-intonation detection, which sounds noticeably more natural/lively
than Piper's flatter delivery. RU uses the multi-speaker v5.5 model (male
voices: aidar, eugene). EN uses the v3_en multi-accent model (speakers en_0..
en_117, no gender labels - picked by ear, see scripts/silero_en_voices.py).
"""

import re

import numpy as np
import torch

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")

RU_SAMPLE_RATE = 48000
EN_SAMPLE_RATE = 48000


def is_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC_RE.search(text))


class Speaker:
    def __init__(self, ru_speaker: str = "eugene", en_speaker: str = "en_90") -> None:
        self._ru_speaker = ru_speaker
        self._en_speaker = en_speaker
        device = torch.device("cpu")

        self._ru_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v5_5_ru",
            trust_repo=True,
        )
        self._ru_model.to(device)

        self._en_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="en",
            speaker="v3_en",
            trust_repo=True,
        )
        self._en_model.to(device)

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        """Returns (float32 mono audio, sample_rate) for the given text."""
        if not text.strip():
            return np.zeros(0, dtype=np.float32), RU_SAMPLE_RATE
        if is_cyrillic(text):
            audio = self._ru_model.apply_tts(
                text=text,
                speaker=self._ru_speaker,
                sample_rate=RU_SAMPLE_RATE,
                put_accent=True,
                put_yo=True,
            )
            return audio.numpy(), RU_SAMPLE_RATE
        audio = self._en_model.apply_tts(text=text, speaker=self._en_speaker, sample_rate=EN_SAMPLE_RATE)
        return audio.numpy(), EN_SAMPLE_RATE

    def speak(self, text: str) -> None:
        import sounddevice as sd

        audio, sample_rate = self.synthesize(text)
        if audio.size == 0:
            return
        sd.play(audio, samplerate=sample_rate)
        sd.wait()


__all__ = ["Speaker", "is_cyrillic"]
