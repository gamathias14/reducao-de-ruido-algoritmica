from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark_audio.causal import CausalProcessorConfig, CausalSTFTProcessor
from benchmark_audio.causal_wpt import CausalWPTConfig, CausalWPTProcessor


SAMPLE_RATE = 16_000
BLOCK_SIZE = 320


def db(value: float) -> float:
    return 10.0 * math.log10(max(value, 1e-24))


def make_signals(duration_s: float = 20.0) -> tuple[np.ndarray, np.ndarray]:
    count = int(round(duration_s * SAMPLE_RATE))
    time_axis = np.arange(count, dtype=np.float64) / SAMPLE_RATE
    syllable = np.maximum(
        0.0,
        np.sin(2.0 * np.pi * 2.8 * time_axis),
    ) ** 1.5
    slow = 0.65 + 0.35 * np.sin(2.0 * np.pi * 0.37 * time_axis) ** 2
    clean = slow * syllable * (
        0.12 * np.sin(2.0 * np.pi * 145.0 * time_axis)
        + 0.07 * np.sin(2.0 * np.pi * 290.0 * time_axis)
        + 0.035 * np.sin(2.0 * np.pi * 725.0 * time_axis)
        + 0.018 * np.sin(2.0 * np.pi * 2_300.0 * time_axis)
    )
    rng = np.random.default_rng(3527)
    white = rng.normal(size=count)
    colored = np.empty(count, dtype=np.float64)
    colored[0] = white[0]
    for index in range(1, count):
        colored[index] = 0.82 * colored[index - 1] + white[index]
    colored /= max(float(np.std(colored)), 1e-12)
    target_snr_db = 3.0
    clean_energy = float(np.mean(np.square(clean)))
    noise_energy = clean_energy / (10.0 ** (target_snr_db / 10.0))
    noise = colored * math.sqrt(noise_energy)
    return clean.astype(np.float32), (clean + noise).astype(np.float32)


def run_processor(
    samples: np.ndarray,
    processor: CausalSTFTProcessor | CausalWPTProcessor,
) -> tuple[np.ndarray, np.ndarray, int]:
    outputs = []
    timings_ms = []
    max_memory = 0
    for start in range(0, samples.size, BLOCK_SIZE):
        block = samples[start : start + BLOCK_SIZE]
        before = time.perf_counter()
        output, diagnostics = processor.process_block(block)
        timings_ms.append(1_000.0 * (time.perf_counter() - before))
        outputs.append(output)
        max_memory = max(max_memory, int(diagnostics["state_memory_bytes"]))
    return (
        np.concatenate(outputs).astype(np.float32),
        np.asarray(timings_ms, dtype=np.float64),
        max_memory,
    )


def signal_metrics(clean: np.ndarray, estimate: np.ndarray, skip_blocks: int) -> dict[str, float]:
    start = skip_blocks * BLOCK_SIZE
    clean64 = clean[start:].astype(np.float64)
    estimate64 = estimate[start:].astype(np.float64)
    residual = estimate64 - clean64
    clean_energy = float(np.sum(np.square(clean64)))
    residual_energy = float(np.sum(np.square(residual)))
    scale = float(np.dot(estimate64, clean64) / max(clean_energy, 1e-24))
    target = scale * clean64
    si_residual = estimate64 - target

    blocks = estimate[start : start + ((estimate.size - start) // BLOCK_SIZE) * BLOCK_SIZE]
    blocks = blocks.reshape(-1, BLOCK_SIZE)
    clean_blocks = clean[start : start + blocks.size].reshape(-1, BLOCK_SIZE)
    active = np.sqrt(np.mean(np.square(clean_blocks, dtype=np.float64), axis=1)) > 0.01
    selected = blocks[active]
    spectra = np.fft.rfft(selected.astype(np.float64) * np.hanning(BLOCK_SIZE), axis=1)
    power = np.maximum(np.square(np.abs(spectra)), 1e-24)
    median_power = np.median(power, axis=1, keepdims=True)
    tonal = power[:, 1:-1] > 10.0 * median_power
    tonal &= power[:, 1:-1] > power[:, :-2]
    tonal &= power[:, 1:-1] > power[:, 2:]
    flatness = np.exp(np.mean(np.log(power), axis=1)) / np.mean(power, axis=1)
    return {
        "snr_db": db(clean_energy / max(residual_energy, 1e-24)),
        "si_sdr_db": db(
            float(np.sum(np.square(target)))
            / max(float(np.sum(np.square(si_residual))), 1e-24)
        ),
        "tonal_peak_density_per_active_block": float(
            np.mean(np.sum(tonal, axis=1))
        ),
        "spectral_flatness_median": float(np.median(flatness)),
    }


def timing_metrics(timings_ms: np.ndarray, memory_bytes: int) -> dict[str, float | int]:
    return {
        "mean_ms": float(np.mean(timings_ms)),
        "p95_ms": float(np.percentile(timings_ms, 95)),
        "p99_ms": float(np.percentile(timings_ms, 99)),
        "max_ms": float(np.max(timings_ms)),
        "blocks_over_20ms": int(np.count_nonzero(timings_ms > 20.0)),
        "max_state_memory_bytes": memory_bytes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    clean, noisy = make_signals()
    wpt_config = CausalWPTConfig()
    baseline = CausalSTFTProcessor(
        CausalProcessorConfig(
            method="stft_subtraction",
            n_fft=512,
            hop_length=160,
            spectral_alpha=1.5,
            spectral_floor=0.02,
            noise_mode="adaptive",
        )
    )
    wpt = CausalWPTProcessor(wpt_config)
    baseline_output, baseline_timings, baseline_memory = run_processor(noisy, baseline)
    wpt_output, wpt_timings, wpt_memory = run_processor(noisy, wpt)
    skip_blocks = max(13, wpt_config.warmup_blocks)

    metrics = {
        "noisy": signal_metrics(clean, noisy, skip_blocks),
        "stft_subtraction": signal_metrics(clean, baseline_output, skip_blocks),
        "causal_wpt": signal_metrics(clean, wpt_output, skip_blocks),
    }
    timing = {
        "stft_subtraction": timing_metrics(baseline_timings, baseline_memory),
        "causal_wpt": timing_metrics(wpt_timings, wpt_memory),
    }
    decision_checks = {
        "causal_wpt_improves_snr_over_noisy": (
            metrics["causal_wpt"]["snr_db"] > metrics["noisy"]["snr_db"]
        ),
        "causal_wpt_improves_si_sdr_over_noisy": (
            metrics["causal_wpt"]["si_sdr_db"] > metrics["noisy"]["si_sdr_db"]
        ),
        "causal_wpt_p95_below_20ms": timing["causal_wpt"]["p95_ms"] < 20.0,
        "causal_wpt_no_blocks_over_20ms": (
            timing["causal_wpt"]["blocks_over_20ms"] == 0
        ),
        "causal_wpt_state_below_64kib": (
            timing["causal_wpt"]["max_state_memory_bytes"] < 64 * 1024
        ),
    }
    summary = {
        "source": "deterministic_synthetic_no_voice",
        "sample_rate_hz": SAMPLE_RATE,
        "block_size": BLOCK_SIZE,
        "duration_s": noisy.size / SAMPLE_RATE,
        "skip_blocks_for_quality_metrics": skip_blocks,
        "wpt_config": {
            "frame_length": wpt_config.frame_length,
            "wavelet": wpt_config.wavelet,
            "level": wpt_config.level,
            "warmup_blocks": wpt_config.warmup_blocks,
            "history_blocks": wpt_config.history_blocks,
            "noise_quantile": wpt_config.noise_quantile,
            "gain_floor": wpt_config.gain_floor,
            "algorithmic_context_ms": wpt_config.algorithmic_context_ms,
        },
        "quality": metrics,
        "timing": timing,
        "decision_checks": decision_checks,
        "eligible_for_private_voice_evaluation": all(decision_checks.values()),
        "private_audio_used": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
