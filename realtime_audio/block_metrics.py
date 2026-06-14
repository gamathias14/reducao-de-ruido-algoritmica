from __future__ import annotations

import math

import numpy as np


def summarize_block_timings(
    timings: list[dict[str, float | int | bool]],
) -> dict[str, float | int]:
    values = np.asarray(
        [float(row["processing_ms"]) for row in timings],
        dtype=np.float64,
    )
    rtf = np.asarray(
        [float(row["rtf_block"]) for row in timings],
        dtype=np.float64,
    )
    if values.size == 0:
        return {
            "blocks": 0,
            "processing_mean_ms": 0.0,
            "processing_worst_ms": 0.0,
            "processing_std_ms": 0.0,
            "processing_p50_ms": 0.0,
            "processing_p95_ms": 0.0,
            "processing_p99_ms": 0.0,
            "rtf_block_mean": 0.0,
            "rtf_block_worst": 0.0,
            "blocks_over_budget": 0,
            "state_memory_max_bytes": 0,
            "speech_probable_fraction": 0.0,
            "warming_blocks": 0,
        }

    block_budget_ms = np.asarray(
        [
            float(row.get("block_duration_ms", 0.0))
            or (
                float(row["processing_ms"]) / max(float(row["rtf_block"]), 1e-12)
                if float(row["processing_ms"]) > 0.0
                else math.inf
            )
            for row in timings
        ],
        dtype=np.float64,
    )
    return {
        "blocks": int(values.size),
        "processing_mean_ms": float(np.mean(values)),
        "processing_worst_ms": float(np.max(values)),
        "processing_std_ms": float(np.std(values)),
        "processing_p50_ms": float(np.percentile(values, 50)),
        "processing_p95_ms": float(np.percentile(values, 95)),
        "processing_p99_ms": float(np.percentile(values, 99)),
        "rtf_block_mean": float(np.mean(rtf)),
        "rtf_block_worst": float(np.max(rtf)),
        "blocks_over_budget": int(np.sum(values > block_budget_ms)),
        "state_memory_max_bytes": int(
            max(int(row.get("state_memory_bytes", 0)) for row in timings)
        ),
        "speech_probable_fraction": float(
            np.mean([bool(row.get("speech_probable", False)) for row in timings])
        ),
        "warming_blocks": int(
            np.sum([bool(row.get("warming_up", False)) for row in timings])
        ),
    }
