"""Silero VAD wrapper for streaming speech start/end detection."""

from collections.abc import Callable

import numpy as np
import torch
from silero_vad import VADIterator, load_silero_vad

SAMPLE_RATE = 16_000
CHUNK_SAMPLES = 512  # required by Silero VAD at 16kHz


class SpeechSegmenter:
    """Feeds fixed-size audio chunks to Silero VAD and reports speech start/end."""

    def __init__(
        self,
        threshold: float = 0.7,
        min_silence_duration_ms: int = 500,
        speech_pad_ms: int = 100,
    ) -> None:
        model = load_silero_vad(onnx=True)
        self._iterator = VADIterator(
            model,
            sampling_rate=SAMPLE_RATE,
            threshold=threshold,
            min_silence_duration_ms=min_silence_duration_ms,
            speech_pad_ms=speech_pad_ms,
        )

    def reset(self) -> None:
        self._iterator.reset_states()

    def process_chunk(self, chunk: np.ndarray) -> str | None:
        """chunk: float32 mono numpy array of exactly CHUNK_SAMPLES samples.

        Returns "start", "end", or None.
        """
        tensor = torch.from_numpy(chunk)
        result = self._iterator(tensor, return_seconds=True)
        if result is None:
            return None
        if "start" in result:
            return "start"
        if "end" in result:
            return "end"
        return None


def run_console_demo(duration_s: float, on_event: Callable[[str], None]) -> None:
    """Stream mic audio through the segmenter for duration_s, calling on_event on start/end."""
    import sounddevice as sd

    segmenter = SpeechSegmenter()

    def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            print(f"stream status: {status}")
        chunk = indata[:, 0].copy()
        event = segmenter.process_chunk(chunk)
        if event:
            on_event(event)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SAMPLES,
        callback=callback,
    ):
        sd.sleep(int(duration_s * 1000))
