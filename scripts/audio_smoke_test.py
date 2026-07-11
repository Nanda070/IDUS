"""List audio devices, record a few seconds from the default mic, and play it back."""

import sys

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
DURATION_S = 3
CHANNELS = 1


def main() -> None:
    print("=== Audio devices ===")
    print(sd.query_devices())

    default_input, default_output = sd.default.device
    print(f"\nDefault input device: {default_input} - {sd.query_devices(default_input)['name']}")
    print(f"Default output device: {default_output} - {sd.query_devices(default_output)['name']}")

    print(f"\nRecording for {DURATION_S}s - speak now...")
    recording = sd.rec(
        int(DURATION_S * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()

    peak = float(np.abs(recording).max())
    rms = float(np.sqrt(np.mean(recording**2)))
    print(f"\nRecorded {DURATION_S}s - peak level: {peak:.4f}, RMS: {rms:.4f}")
    if peak < 0.01:
        print("WARNING: signal is very quiet - check mic selection/volume.")

    print("Playing back...")
    sd.play(recording, samplerate=SAMPLE_RATE)
    sd.wait()
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
