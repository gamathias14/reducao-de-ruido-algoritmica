from __future__ import annotations

import argparse
import hashlib
import json
import time
import tracemalloc
from pathlib import Path

import numpy as np
import psutil

from realtime_audio.rnnoise_processor import (
    INPUT_BLOCK_SAMPLES,
    INPUT_SAMPLE_RATE,
    TOTAL_ALGORITHMIC_LATENCY_MS,
    default_library_path,
)
from realtime_audio.windows_realtime import RealtimeBlockProcessor, RealtimeConfig


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    ROOT
    / "resultados"
    / "sysvad_checkpoint46_reopened"
    / "rnnoise_host_prebridge"
    / "host_validation.json"
)


def _sha256(values: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray(values, dtype="<f4").tobytes(order="C")
    ).hexdigest()


def _process(blocks: list[np.ndarray]) -> np.ndarray:
    processor = RealtimeBlockProcessor(RealtimeConfig(method="rnnoise"))
    try:
        return np.concatenate(
            [processor.process_block(block)[0].copy() for block in blocks]
        )
    finally:
        processor.close()


def _test_blocks(count: int, seed: int = 3527) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [
        rng.normal(scale=0.08, size=INPUT_BLOCK_SAMPLES).astype(np.float32)
        for _ in range(count)
    ]


def _continuity_metrics() -> dict[str, float | int]:
    block_count = 250
    sample_count = block_count * INPUT_BLOCK_SAMPLES
    samples = np.arange(sample_count, dtype=np.float64)
    source = (
        0.12 * np.sin(2.0 * np.pi * 220.0 * samples / INPUT_SAMPLE_RATE)
        + 0.05 * np.sin(
            2.0 * np.pi * 730.0 * samples / INPUT_SAMPLE_RATE + 0.2
        )
    ).astype(np.float32)
    blocks = [
        source[start : start + INPUT_BLOCK_SAMPLES]
        for start in range(0, sample_count, INPUT_BLOCK_SAMPLES)
    ]
    output = _process(blocks)
    differences = np.abs(np.diff(output.astype(np.float64)))
    boundary_indices = (
        np.arange(1, block_count, dtype=np.int64) * INPUT_BLOCK_SAMPLES - 1
    )
    boundary = differences[boundary_indices]
    internal_mask = np.ones(differences.size, dtype=bool)
    internal_mask[boundary_indices] = False
    internal = differences[internal_mask]
    internal_p99 = float(np.percentile(internal, 99))
    threshold = max(0.10, 10.0 * internal_p99)
    return {
        "boundary_jump_max": float(np.max(boundary)),
        "boundary_jump_p99": float(np.percentile(boundary, 99)),
        "internal_jump_p99": internal_p99,
        "discontinuity_threshold": threshold,
        "boundary_discontinuities": int(np.sum(boundary > threshold)),
    }


def _long_run(duration_s: float) -> dict[str, float | int]:
    block_count = int(round(duration_s * INPUT_SAMPLE_RATE / INPUT_BLOCK_SAMPLES))
    config = RealtimeConfig(method="rnnoise")
    processor = RealtimeBlockProcessor(config)
    process = psutil.Process()
    silence = np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
    active_samples = np.arange(INPUT_BLOCK_SAMPLES, dtype=np.float64)
    active = (
        0.1
        * np.sin(2.0 * np.pi * 440.0 * active_samples / INPUT_SAMPLE_RATE)
    ).astype(np.float32)
    timings_ms = np.empty(block_count, dtype=np.float64)
    rss_start = int(process.memory_info().rss)
    rss_peak = rss_start
    tracemalloc.start()
    python_start, _ = tracemalloc.get_traced_memory()
    try:
        for index in range(block_count):
            block = active if index % 5 else silence
            started = time.perf_counter()
            output, _ = processor.process_block(block)
            timings_ms[index] = 1000.0 * (time.perf_counter() - started)
            if output.size != INPUT_BLOCK_SAMPLES or not np.all(np.isfinite(output)):
                raise RuntimeError(f"Saida invalida no bloco {index}.")
            if index % 100 == 0:
                rss_peak = max(rss_peak, int(process.memory_info().rss))
        python_end, python_peak = tracemalloc.get_traced_memory()
    finally:
        processor.close()
        tracemalloc.stop()
    rss_end = int(process.memory_info().rss)
    block_duration_ms = 1000.0 * INPUT_BLOCK_SAMPLES / INPUT_SAMPLE_RATE
    return {
        "audio_duration_s": duration_s,
        "blocks": block_count,
        "processing_mean_ms": float(np.mean(timings_ms)),
        "processing_p95_ms": float(np.percentile(timings_ms, 95)),
        "processing_p99_ms": float(np.percentile(timings_ms, 99)),
        "processing_worst_ms": float(np.max(timings_ms)),
        "rtf_mean": float(np.mean(timings_ms) / block_duration_ms),
        "rtf_p95": float(np.percentile(timings_ms, 95) / block_duration_ms),
        "rtf_p99": float(np.percentile(timings_ms, 99) / block_duration_ms),
        "rtf_worst": float(np.max(timings_ms) / block_duration_ms),
        "blocks_over_20ms": int(np.sum(timings_ms > block_duration_ms)),
        "rss_start_bytes": rss_start,
        "rss_end_bytes": rss_end,
        "rss_peak_bytes": rss_peak,
        "rss_growth_bytes": rss_end - rss_start,
        "python_traced_growth_bytes": int(python_end - python_start),
        "python_traced_peak_bytes": int(python_peak),
    }


def validate(duration_s: float) -> dict[str, object]:
    blocks = _test_blocks(100)
    deterministic_a = _process(blocks)
    deterministic_b = _process(blocks)
    prefix = blocks[:60]
    future_a = blocks[60:]
    future_b = [
        np.full(INPUT_BLOCK_SAMPLES, 0.35, dtype=np.float32)
        for _ in future_a
    ]
    causal_a = _process([*prefix, *future_a])
    causal_b = _process([*prefix, *future_b])
    prefix_samples = len(prefix) * INPUT_BLOCK_SAMPLES

    reset_processor = RealtimeBlockProcessor(RealtimeConfig(method="rnnoise"))
    try:
        reset_a = np.concatenate(
            [
                reset_processor.process_block(block)[0].copy()
                for block in blocks[:20]
            ]
        )
        reset_processor.reset()
        reset_b = np.concatenate(
            [
                reset_processor.process_block(block)[0].copy()
                for block in blocks[:20]
            ]
        )
    finally:
        reset_processor.close()

    closed_rejected = False
    closed_processor = RealtimeBlockProcessor(RealtimeConfig(method="rnnoise"))
    closed_processor.close()
    try:
        closed_processor.process_block(blocks[0])
    except RuntimeError:
        closed_rejected = True

    impulse = np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
    impulse[0] = 0.5
    impulse_output = _process(
        [impulse]
        + [np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32) for _ in range(29)]
    )
    impulse_peak = int(np.argmax(np.abs(impulse_output)))
    impulse_delay_ms = 1000.0 * impulse_peak / INPUT_SAMPLE_RATE

    continuity = _continuity_metrics()
    long_run = _long_run(duration_s)
    library_path = default_library_path()
    library_hash = hashlib.sha256(library_path.read_bytes()).hexdigest().upper()
    gates = {
        "deterministic": bool(np.array_equal(deterministic_a, deterministic_b)),
        "causal_prefix": bool(
            np.array_equal(
                causal_a[:prefix_samples],
                causal_b[:prefix_samples],
            )
        ),
        "reset_bit_exact": bool(np.array_equal(reset_a, reset_b)),
        "close_rejects_processing": closed_rejected,
        "impulse_delay_expected": 338 <= impulse_peak <= 344,
        "no_boundary_discontinuities": (
            continuity["boundary_discontinuities"] == 0
        ),
        "no_blocks_over_budget": long_run["blocks_over_20ms"] == 0,
        "rss_growth_below_4mb": long_run["rss_growth_bytes"] <= 4 * 1024 * 1024,
        "finite_and_length_preserved": True,
    }
    return {
        "protocol": "rnnoise_host_prebridge_v1",
        "vm_started": False,
        "bridge_opened": False,
        "capture_started": False,
        "sample_rate": INPUT_SAMPLE_RATE,
        "block_samples": INPUT_BLOCK_SAMPLES,
        "block_duration_ms": 20.0,
        "rnnoise_latency_ms": 20.0,
        "resampler_nominal_delay_ms": (
            TOTAL_ALGORITHMIC_LATENCY_MS - 20.0
        ),
        "total_algorithmic_latency_nominal_ms": TOTAL_ALGORITHMIC_LATENCY_MS,
        "impulse_peak_samples": impulse_peak,
        "impulse_delay_measured_ms": impulse_delay_ms,
        "library_path": str(library_path),
        "library_sha256": library_hash,
        "state_continuity": {
            "deterministic_output_sha256": _sha256(deterministic_a),
            "deterministic_repeat_sha256": _sha256(deterministic_b),
            "reset_output_sha256": _sha256(reset_a),
            "reset_repeat_sha256": _sha256(reset_b),
        },
        "continuity": continuity,
        "long_run": long_run,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida RNNoise persistente no host, antes da ponte e da VM."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=600.0,
        help="Duracao equivalente de audio para o ensaio prolongado.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = validate(args.duration)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["all_gates_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
