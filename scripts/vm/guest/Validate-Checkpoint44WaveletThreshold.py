from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

APP_ROOT = Path(r"C:\PTC3527\checkpoint35\app")
sys.path.insert(0, str(APP_ROOT))

from benchmark_audio.denoise import DenoiseConfig, process_method


SAMPLE_RATE = 16_000
BLOCK_SIZE = 320
SCALES = (0.10, 0.25, 0.50, 0.75)


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


def process(samples: np.ndarray, scale: float) -> np.ndarray:
    config = DenoiseConfig(
        wavelet="db4",
        wavelet_level=3,
        wavelet_mode="soft",
        wavelet_threshold_strategy="global",
        wavelet_threshold_scale=scale,
    )
    history = np.zeros(512, dtype=np.float32)
    outputs = []
    for start in range(0, samples.size, BLOCK_SIZE):
        block = samples[start : start + BLOCK_SIZE]
        window = np.concatenate([history, block]).astype(np.float32)
        output_window, _ = process_method("wavelet_soft", window, config)
        output = np.nan_to_num(
            output_window[-len(block) :],
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        ).astype(np.float32)
        if output.shape != (BLOCK_SIZE,) or not np.all(np.isfinite(output)):
            raise RuntimeError(f"Saida invalida na escala {scale}.")
        outputs.append(output)
        history = window[-512:].astype(np.float32)
    return np.concatenate(outputs)


def main() -> None:
    samples = source()
    summaries = {}
    outputs = {}
    for scale in SCALES:
        first = process(samples, scale)
        second = process(samples, scale)
        if not np.array_equal(first, second):
            raise RuntimeError(f"Wavelet nao deterministica na escala {scale}.")
        outputs[scale] = first
        summaries[str(scale)] = {
            "rms": float(np.sqrt(np.mean(np.square(first, dtype=np.float64)))),
            "peak": float(np.max(np.abs(first))),
        }

    if np.array_equal(outputs[SCALES[0]], outputs[SCALES[-1]]):
        raise RuntimeError("Os extremos de escala nao alteraram a saida.")

    print(
        json.dumps(
            {
                "source": "deterministic_synthetic_no_voice",
                "blocks": samples.size // BLOCK_SIZE,
                "scales": summaries,
                "result": "CHECKPOINT44_VM_VALIDATION=OK",
            },
            sort_keys=True,
        )
    )
    print("CHECKPOINT44_VM_VALIDATION=OK")


if __name__ == "__main__":
    main()
