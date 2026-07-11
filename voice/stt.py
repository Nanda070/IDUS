"""faster-whisper wrapper for transcribing VAD-segmented audio."""

import numpy as np
from faster_whisper import WhisperModel

from voice.vad import SAMPLE_RATE


def _normalize(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Peak-normalize quiet audio - low-amplitude input starves Whisper of dynamic
    range and makes it far more prone to language/content hallucination."""
    peak = float(np.abs(audio).max())
    if peak < 1e-4:
        return audio
    return audio * (target_peak / peak)



# Biases decoding toward the assistant's own vocabulary (commands, names used
# around the house, tool-related words) - helps with near-homophone mixups
# like "Максиму" (dative name) vs "максимум" (regular word) that plain
# acoustic matching alone gets wrong. Whisper treats this as preceding
# transcript context, not an instruction, so it reads as a natural sentence.
DEFAULT_INITIAL_PROMPT = (
    "Привет, Айдус. Включи свет, напомни мне, поставь таймер, найди в интернете, "
    "какая погода, сколько сейчас времени, напиши Максиму и Владу сообщение."
)


class Transcriber:
    def __init__(self, model_size: str = "small", device: str = "cpu", compute_type: str = "int8") -> None:
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(
        self,
        audio: np.ndarray,
        language: str | None = "ru",
        no_speech_threshold: float = 0.6,
        initial_prompt: str | None = DEFAULT_INITIAL_PROMPT,
    ) -> str:
        """audio: float32 mono numpy array at SAMPLE_RATE (16kHz).

        language defaults to "ru" - with auto-detect (None), whisper's language ID
        on short/quiet clips was flailing wildly (French/Chinese/Portuguese output
        for Russian speech). Pass language=None to re-enable auto-detect once
        input quality/model size make that reliable.

        initial_prompt biases decoding toward the assistant's own vocabulary -
        pass None to disable.

        Segments whisper itself flags as likely non-speech (no_speech_prob above
        threshold) are dropped - small Whisper models hallucinate fluent but wrong
        text on silence/noise-only clips.
        """
        audio = _normalize(audio)
        segments, _info = self._model.transcribe(
            audio,
            language=language,
            beam_size=5,
            condition_on_previous_text=False,
            vad_filter=True,
            initial_prompt=initial_prompt,
        )
        kept = [s.text.strip() for s in segments if s.no_speech_prob < no_speech_threshold]
        return " ".join(kept).strip()


__all__ = ["Transcriber", "SAMPLE_RATE"]
