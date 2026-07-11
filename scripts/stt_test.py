"""Live console demo: VAD segments speech, faster-whisper transcribes each utterance."""

import queue
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice.stt import Transcriber
from voice.vad import CHUNK_SAMPLES, SAMPLE_RATE, SpeechSegmenter

DURATION_S = 45
PREROLL_CHUNKS = 8  # ~256ms of pre-speech padding at 512 samples/16kHz
MIN_UTTERANCE_S = 0.4


def main() -> None:
    print("Loading VAD + faster-whisper (small)...")
    segmenter = SpeechSegmenter()
    transcriber = Transcriber()

    utterance_queue: queue.Queue[np.ndarray] = queue.Queue()
    preroll: deque[np.ndarray] = deque(maxlen=PREROLL_CHUNKS)
    recording: list[np.ndarray] = []
    is_speaking = False

    def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        nonlocal is_speaking
        if status:
            print(f"stream status: {status}")
        chunk = indata[:, 0].copy()
        event = segmenter.process_chunk(chunk)

        if event == "start":
            is_speaking = True
            recording.clear()
            recording.extend(preroll)
            recording.append(chunk)
        elif is_speaking:
            recording.append(chunk)
        else:
            preroll.append(chunk)

        if event == "end" and is_speaking:
            is_speaking = False
            utterance_queue.put(np.concatenate(recording))
            recording.clear()

    print(f"Listening for {DURATION_S}s - say a few phrases (mixed RU/EN is fine), with pauses between them...")
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SAMPLES,
        callback=callback,
    ):
        deadline = time.monotonic() + DURATION_S
        while time.monotonic() < deadline:
            try:
                audio = utterance_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            ts = time.strftime("%H:%M:%S")
            duration = len(audio) / SAMPLE_RATE
            peak = float(np.abs(audio).max())
            if duration < MIN_UTTERANCE_S:
                print(f"[{ts}] (skipped {duration:.2f}s clip, peak={peak:.3f} - too short)")
                continue
            t0 = time.monotonic()
            text = transcriber.transcribe(audio)
            elapsed = time.monotonic() - t0
            print(f"[{ts}] ({duration:.2f}s clip, peak={peak:.3f}, stt={elapsed:.1f}s) > {text!r}")

    print("Done.")


if __name__ == "__main__":
    main()
