from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

APP_ROOT = Path(r"C:\PTC3527\checkpoint35\app")
sys.path.insert(0, str(APP_ROOT))

from realtime_audio.windows_realtime import RealtimeBlockProcessor, RealtimeConfig


SAMPLE_RATE = 16_000
BLOCK_SIZE = 320
LEVELS = (3, 4, 5)


def source() -> np.ndarray:
    rng = np.random.default_rng(3527)
    count = 60 * BLOCK_SIZE
    time = np.arange(count, dtype=np.float64) / SAMPLE_RATE
    signal = (
        0.08 * np.sin(2.0 * np.pi * 440.0 * time)
        + 0.025 * np.sin(2.0 * np.pi * 1_370.0 * time)
        + rng.normal(scale=0.012, size=count)
    )
    signal[: 10 * BLOCK_SIZE] *= 0.15
    return signal.astype(np.float32)


def process(samples: np.ndarray, level: int) -> np.ndarray:
    processor = RealtimeBlockProcessor(
        RealtimeConfig(
            method="wavelet_soft",
            block_ms=20.0,
            n_fft=512,
            hop_length=160,
            wavelet="db4",
            wavelet_level=level,
            wavelet_mode="soft",
        )
    )
    outputs = []
    for start in range(0, samples.size, BLOCK_SIZE):
        output, _ = processor.process_block(samples[start : start + BLOCK_SIZE])
        if output.shape != (BLOCK_SIZE,) or not np.all(np.isfinite(output)):
            raise RuntimeError(f"Saida invalida no nivel {level}.")
        outputs.append(output)
    return np.concatenate(outputs)


def main() -> None:
    samples = source()
    summaries = {}
    outputs = {}
    for level in LEVELS:
        first = process(samples, level)
        second = process(samples, level)
        if not np.array_equal(first, second):
            raise RuntimeError(f"Wavelet nao deterministica no nivel {level}.")
        outputs[level] = first
        summaries[str(level)] = {
            "rms": float(np.sqrt(np.mean(np.square(first, dtype=np.float64)))),
            "peak": float(np.max(np.abs(first))),
        }

    if np.array_equal(outputs[LEVELS[0]], outputs[LEVELS[-1]]):
        raise RuntimeError("Os extremos de nivel nao alteraram a saida.")

    print(
        json.dumps(
            {
                "source": "deterministic_synthetic_no_voice",
                "blocks": samples.size // BLOCK_SIZE,
                "levels": summaries,
                "result": "CHECKPOINT43_VM_VALIDATION=OK",
            },
            sort_keys=True,
        )
    )
    print("CHECKPOINT43_VM_VALIDATION=OK")


if __name__ == "__main__":
    main()
