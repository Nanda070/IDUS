"""Speaker identification via SpeechBrain's pretrained ECAPA-TDNN embeddings.

Not full diarization - just "does this utterance's voice match an enrolled
person, and if so who". Good enough for "who's talking to IDUS right now".
"""

from pathlib import Path

import numpy as np
import torch
from speechbrain.inference.speaker import EncoderClassifier

MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
SAVE_DIR = Path(__file__).resolve().parent.parent / "config" / "models" / "spkrec-ecapa"
DEFAULT_THRESHOLD = 0.5


class SpeakerIdentifier:
    def __init__(self) -> None:
        self._classifier = EncoderClassifier.from_hparams(source=MODEL_SOURCE, savedir=str(SAVE_DIR))
        self._enrolled: dict[str, np.ndarray] = {}

    def _embed(self, audio: np.ndarray) -> np.ndarray:
        tensor = torch.from_numpy(audio.astype(np.float32)).unsqueeze(0)
        with torch.no_grad():
            embedding = self._classifier.encode_batch(tensor)
        return embedding.squeeze().numpy()

    def enroll(self, name: str, audio: np.ndarray) -> None:
        self._enrolled[name] = self._embed(audio)

    def load_enrolled(self, speakers: dict[str, bytes]) -> None:
        for name, blob in speakers.items():
            self._enrolled[name] = np.frombuffer(blob, dtype=np.float32)

    def embedding_bytes(self, name: str) -> bytes:
        return self._enrolled[name].astype(np.float32).tobytes()

    def identify(self, audio: np.ndarray, threshold: float = DEFAULT_THRESHOLD) -> tuple[str | None, float]:
        """Returns (name, score) - name is None if no enrolled speaker matches above threshold."""
        if not self._enrolled:
            return None, 0.0
        embedding = self._embed(audio)
        best_name, best_score = None, -1.0
        for name, ref in self._enrolled.items():
            score = float(np.dot(embedding, ref) / (np.linalg.norm(embedding) * np.linalg.norm(ref)))
            if score > best_score:
                best_name, best_score = name, score
        if best_score >= threshold:
            return best_name, best_score
        return None, best_score


__all__ = ["SpeakerIdentifier", "DEFAULT_THRESHOLD"]
