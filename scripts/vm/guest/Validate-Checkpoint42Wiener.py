from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

APP_ROOT = Path(r"C:\PTC3527\checkpoint35\app")
sys.path.insert(0, str(APP_ROOT))

from benchmark_audio.causal import CausalProcessorConfig, CausalSTFTProcessor


SAMPLE_RATE = 16_000
BLOCK_SIZE = 320
FLOORS = (0.02, 0.05, 0.08, 0.10)


def source() -> np.ndarray:
    rng = np.random.default_rng(3527)
    count = 60 * BLOCK_SIZE
    time = np.arange(count, dtype=np.float64) / SAMPLE_RATE
    tone = 0.08 * np.sin(2.0 * np.pi * 440.0 * time)
    harmonic = 0.025 * np.sin(2.0 * np.pi * 1_370.0 * time)
    noise = rng.normal(scale=0.012, size=count)
    envelope = np.ones(count, dtype=np.float64)
    envelope[: 10 * BLOCK_SIZE] = 0.15
    return ((tone + harmonic) * envelope + noise).astype(np.float32)


def process(samples: np.ndarray, method: str, floor: float = 0.05) -> np.ndarray:
    processor = CausalSTFTProcessor(
        CausalProcessorConfig(
            method=method,
            n_fft=512,
            hop_length=160,
            spectral_alpha=1.5,
            spectral_floor=0.02,
            wiener_floor=floor,
            noise_mode="adaptive",
        )
    )
    blocks = []
    for start in range(0, samples.size, BLOCK_SIZE):
        output, _ = processor.process_block(samples[start : start + BLOCK_SIZE])
        if output.shape != (BLOCK_SIZE,) or not np.all(np.isfinite(output)):
            raise RuntimeError(f"Saida invalida para {method}, piso {floor}.")
        blocks.append(output)
    return np.concatenate(blocks)


def main() -> None:
    samples = source()
    baseline_first = process(samples, "stft_subtraction")
    baseline_second = process(samples, "stft_subtraction")
    if not np.array_equal(baseline_first, baseline_second):
        raise RuntimeError("Baseline nao deterministico.")

    summaries = {}
    outputs = {}
    for floor in FLOORS:
        first = process(samples, "stft_wiener", floor)
        second = process(samples, "stft_wiener", floor)
        if not np.array_equal(first, second):
            raise RuntimeError(f"Wiener nao deterministico no piso {floor}.")
        if np.array_equal(first, baseline_first):
            raise RuntimeError(f"Wiener indistinguivel do baseline no piso {floor}.")
        outputs[floor] = first
        summaries[str(floor)] = {
            "rms": float(np.sqrt(np.mean(np.square(first, dtype=np.float64)))),
            "peak": float(np.max(np.abs(first))),
        }

    if np.array_equal(outputs[FLOORS[0]], outputs[FLOORS[-1]]):
        raise RuntimeError("Os extremos de piso Wiener nao alteraram a saida.")

    print(
        json.dumps(
            {
                "source": "deterministic_synthetic_no_voice",
                "blocks": samples.size // BLOCK_SIZE,
                "floors": summaries,
                "result": "CHECKPOINT42_VM_VALIDATION=OK",
            },
            sort_keys=True,
        )
    )
    print("CHECKPOINT42_VM_VALIDATION=OK")


if __name__ == "__main__":
    main()
