"""openWakeWord wrapper (onnx backend) for continuous wake-word detection."""

import numpy as np
from openwakeword import Model

CHUNK_SAMPLES = 1280  # 80ms at 16kHz - openWakeWord's native frame size


class WakeWordDetector:
    def __init__(
        self,
        model_name: str = "hey_jarvis",
        threshold: float = 0.5,
        debounce_time: float = 1.5,
    ) -> None:
        self._model = Model(wakeword_models=[model_name], inference_framework="onnx")
        self._model_name = model_name
        self.threshold = threshold
        self._debounce_time = debounce_time

    def process_chunk(self, chunk: np.ndarray) -> float:
        """chunk: float32 mono numpy array, ideally CHUNK_SAMPLES samples.

        Returns the wake-word score for this frame (post-debounce, so repeated
        triggers within debounce_time are suppressed to 0).
        """
        pcm16 = (np.clip(chunk, -1.0, 1.0) * 32767.0).astype(np.int16)
        predictions = self._model.predict(
            pcm16,
            threshold={self._model_name: self.threshold},
            debounce_time=self._debounce_time,
        )
        return predictions.get(self._model_name, 0.0)

    def triggered(self, chunk: np.ndarray) -> bool:
        return self.process_chunk(chunk) >= self.threshold


__all__ = ["WakeWordDetector", "CHUNK_SAMPLES"]
