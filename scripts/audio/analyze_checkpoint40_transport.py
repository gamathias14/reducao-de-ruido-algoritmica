from __future__ import annotations

import argparse
import csv
import json
import math
import wave
from pathlib import Path

import numpy as np


SAMPLE_RATE = 16_000
BLOCK_SIZE = 320
ZERO_THRESHOLD = 0.5 / 32768.0


def read_pcm16(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as handle:
        if (
            handle.getframerate() != SAMPLE_RATE
            or handle.getnchannels() != 1
            or handle.getsampwidth() != 2
        ):
            raise ValueError(f"Formato WAV inesperado: {path}")
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    return samples.astype(np.float32) / 32768.0


def find_single(directory: Path, pattern: str) -> Path:
    matches = list(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"Esperado um {pattern} em {directory}, obtidos {matches}")
    return matches[0]


def normalized_correlations(reference: np.ndarray, signal: np.ndarray) -> np.ndarray:
    if signal.size < reference.size:
        return np.empty(0, dtype=np.float64)
    windows = np.lib.stride_tricks.sliding_window_view(signal, reference.size)
    reference64 = reference.astype(np.float64)
    windows64 = windows.astype(np.float64)
    numerator = windows64 @ reference64
    denominator = np.linalg.norm(reference64) * np.linalg.norm(windows64, axis=1)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator),
        where=denominator > 1e-15,
    )


def locate_first_block(reference: np.ndarray, endpoint: np.ndarray) -> tuple[int, float]:
    correlations = normalized_correlations(reference, endpoint)
    if not correlations.size:
        raise ValueError("Endpoint curto demais para localizar o primeiro bloco.")
    position = int(np.argmax(correlations))
    return position, float(correlations[position])


def match_sent_blocks(
    pre_blocks: np.ndarray | dict[int, np.ndarray],
    endpoint: np.ndarray,
    sent_indices: list[int],
    source_classes: dict[int, str],
    *,
    tracking_threshold: float = 0.72,
    preserved_threshold: float = 0.985,
    search_back_samples: int = 160,
    search_forward_samples: int = 1280,
) -> list[dict[str, object]]:
    def reference_block(source_index: int) -> np.ndarray:
        if isinstance(pre_blocks, dict):
            return pre_blocks[source_index]
        return pre_blocks[source_index]

    first_order = next(
        (
            order
            for order, source_index in enumerate(sent_indices)
            if source_classes.get(source_index) in {"noise", "active"}
        ),
        None,
    )
    if first_order is None:
        raise ValueError("Nenhum bloco identificavel foi enviado.")
    first_index = sent_indices[first_order]
    anchor, anchor_score = locate_first_block(reference_block(first_index), endpoint)
    predicted = anchor - first_order * BLOCK_SIZE
    matches: list[dict[str, object]] = []

    for order, source_index in enumerate(sent_indices):
        source_class = source_classes.get(source_index, "unknown")
        expected_start = predicted
        if source_class not in {"noise", "active"}:
            matches.append(
                {
                    "sent_order": order,
                    "source_block_index": source_index,
                    "source_class": source_class,
                    "endpoint_start_sample": None,
                    "correlation": None,
                    "preserved": False,
                    "reason": "unidentifiable_gap_block",
                }
            )
            predicted += BLOCK_SIZE
            continue

        search_start = max(0, expected_start - search_back_samples)
        search_stop = min(
            endpoint.size,
            expected_start + BLOCK_SIZE + search_forward_samples,
        )
        reference = reference_block(source_index)
        correlations = normalized_correlations(
            reference,
            endpoint[search_start:search_stop],
        )
        if not correlations.size:
            best_start = None
            best_score = 0.0
        else:
            relative = int(np.argmax(correlations))
            best_start = search_start + relative
            best_score = float(correlations[relative])

        if best_start is not None and best_score >= tracking_threshold:
            predicted = best_start + BLOCK_SIZE
            endpoint_block = endpoint[best_start : best_start + BLOCK_SIZE]
            reference64 = reference.astype(np.float64)
            endpoint64 = endpoint_block.astype(np.float64)
            denominator = float(np.dot(reference64, reference64))
            gain = (
                0.0
                if denominator <= 1e-15
                else float(np.dot(endpoint64, reference64) / denominator)
            )
            residual = endpoint64 - gain * reference64
            rmse = float(np.sqrt(np.mean(np.square(residual))))
            preserved = best_score >= preserved_threshold
            matches.append(
                {
                    "sent_order": order,
                    "source_block_index": source_index,
                    "source_class": source_class,
                    "endpoint_start_sample": best_start,
                    "correlation": best_score,
                    "gain": gain,
                    "sample_rmse_dbfs": 20.0 * math.log10(max(rmse, 1e-12)),
                    "sample_max_abs_error": float(np.max(np.abs(residual))),
                    "preserved": preserved,
                    "reason": (
                        "high_confidence_match"
                        if preserved
                        else "tracked_but_changed"
                    ),
                }
            )
        else:
            predicted += BLOCK_SIZE
            matches.append(
                {
                    "sent_order": order,
                    "source_block_index": source_index,
                    "source_class": source_class,
                    "endpoint_start_sample": best_start,
                    "correlation": best_score,
                    "preserved": False,
                    "reason": "not_recovered",
                }
            )

    if matches[first_order]["correlation"] != anchor_score:
        matches[first_order]["initial_anchor_correlation"] = anchor_score
    return matches


def spectral_summary(blocks: np.ndarray) -> dict[str, float | int]:
    if not len(blocks):
        return {"block_count": 0}
    window = np.hanning(BLOCK_SIZE)
    spectra = np.fft.rfft(blocks.astype(np.float64) * window, axis=1)
    powers = np.maximum(np.square(np.abs(spectra)), 1e-24)
    flatness = np.exp(np.mean(np.log(powers), axis=1)) / np.mean(powers, axis=1)
    median_power = np.median(powers, axis=1, keepdims=True)
    tonal = powers[:, 1:-1] > 10.0 * median_power
    tonal &= powers[:, 1:-1] > powers[:, :-2]
    tonal &= powers[:, 1:-1] > powers[:, 2:]
    psd = np.mean(powers, axis=0)
    frequencies = np.fft.rfftfreq(BLOCK_SIZE, 1.0 / SAMPLE_RATE)
    high = (frequencies >= 4_000.0) & (frequencies <= 8_000.0)
    return {
        "block_count": int(len(blocks)),
        "spectral_flatness_median": float(np.median(flatness)),
        "tonal_peak_density_per_block": float(np.mean(np.sum(tonal, axis=1))),
        "high_4_8k_power_fraction": float(
            np.sum(psd[high]) / max(float(np.sum(psd)), 1e-24)
        ),
    }


def zero_metrics(samples: np.ndarray) -> dict[str, float | int]:
    zero = np.abs(samples) <= ZERO_THRESHOLD
    transitions = int(np.count_nonzero(zero[1:] != zero[:-1])) if len(zero) > 1 else 0
    padded = np.concatenate(([False], zero, [False]))
    starts = np.flatnonzero(~padded[:-1] & padded[1:])
    stops = np.flatnonzero(padded[:-1] & ~padded[1:])
    runs = stops - starts
    return {
        "sample_count": int(samples.size),
        "zero_fraction": float(np.mean(zero)) if samples.size else 0.0,
        "zero_signal_transitions": transitions,
        "zero_run_count": int(len(runs)),
        "zero_runs_at_least_5ms": int(np.count_nonzero(runs >= 80)),
        "zero_runs_at_least_20ms": int(np.count_nonzero(runs >= BLOCK_SIZE)),
        "longest_zero_run_samples": int(np.max(runs)) if len(runs) else 0,
    }


def analyze_scenario(directory: Path) -> dict[str, object]:
    raw_path = find_single(directory, "*_input.wav")
    pre_path = find_single(directory, "*_output.wav")
    endpoint_path = find_single(directory, "endpoint.wav")
    metrics_path = find_single(directory, "*_metrics.json")
    blocks_path = find_single(directory, "*_blocks.csv")
    raw = read_pcm16(raw_path)
    pre = read_pcm16(pre_path)
    endpoint = read_pcm16(endpoint_path)
    raw_blocks = raw[: raw.size // BLOCK_SIZE * BLOCK_SIZE].reshape(-1, BLOCK_SIZE)
    pre_blocks = pre[: pre.size // BLOCK_SIZE * BLOCK_SIZE].reshape(-1, BLOCK_SIZE)
    internal = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
    bridge = internal["bridge"]
    sent_indices = [
        int(index)
        for index in bridge.get("sent_source_block_indices", [])
        if index is not None
    ]
    if not sent_indices:
        sent_indices = [
            int(event["source_block_index"])
            for event in bridge.get("events", [])
            if event.get("event") == "sent"
            and event.get("source_block_index") is not None
        ]
    with blocks_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    source_classes = {
        int(row["block_index"]): row.get("source_class", "")
        for row in rows
    }
    block_positions = {
        int(row["block_index"]): position
        for position, row in enumerate(rows)
        if position < len(pre_blocks)
    }
    pre_by_index = {
        source_index: pre_blocks[position]
        for source_index, position in block_positions.items()
    }
    matches = match_sent_blocks(
        pre_by_index,
        endpoint,
        sent_indices,
        source_classes,
    )
    preserved = [match for match in matches if match["preserved"]]
    by_class: dict[str, dict[str, float | int]] = {}
    for source_class in ("noise", "active"):
        submitted = sum(
            value == source_class for value in source_classes.values()
        )
        sent = sum(
            source_classes.get(index) == source_class for index in sent_indices
        )
        recovered = sum(
            match["source_class"] == source_class and match["preserved"]
            for match in matches
        )
        by_class[source_class] = {
            "submitted": submitted,
            "sent": sent,
            "locally_dropped": submitted - sent,
            "preserved_at_endpoint": recovered,
            "send_rate": sent / submitted if submitted else 0.0,
            "endpoint_preservation_rate": recovered / sent if sent else 0.0,
        }

    preserved_active_indices = [
        int(match["source_block_index"])
        for match in preserved
        if match["source_class"] == "active"
    ]
    all_active_indices = [
        source_index
        for source_index, source_class in source_classes.items()
        if source_class == "active" and source_index in block_positions
    ]
    endpoint_active = np.asarray(
        [
            endpoint[
                int(match["endpoint_start_sample"]) :
                int(match["endpoint_start_sample"]) + BLOCK_SIZE
            ]
            for match in preserved
            if match["source_class"] == "active"
        ],
        dtype=np.float32,
    )
    sample_errors = [
        match
        for match in preserved
        if match["source_class"] in {"noise", "active"}
    ]
    transport = {
        key: value
        for key, value in bridge.items()
        if key not in {
            "events",
            "sent_source_block_indices",
            "dropped_source_block_indices",
            "stop_dropped_source_block_indices",
        }
    }
    return {
        "name": directory.name,
        "method": internal["config"]["method"],
        "source_block_lists": {
            "sent": sent_indices,
            "dropped_oldest": bridge.get("dropped_source_block_indices", []),
            "dropped_on_stop": bridge.get(
                "stop_dropped_source_block_indices",
                [],
            ),
        },
        "preservation_by_class": by_class,
        "sample_comparison_preserved_only": {
            "block_count": len(sample_errors),
            "correlation_median": (
                float(np.median([item["correlation"] for item in sample_errors]))
                if sample_errors
                else 0.0
            ),
            "rmse_dbfs_median": (
                float(
                    np.median(
                        [item["sample_rmse_dbfs"] for item in sample_errors]
                    )
                )
                if sample_errors
                else -240.0
            ),
            "max_abs_error": (
                float(
                    np.max(
                        [item["sample_max_abs_error"] for item in sample_errors]
                    )
                )
                if sample_errors
                else 0.0
            ),
        },
        "active_spectral_metrics": {
            "raw": spectral_summary(
                np.asarray(
                    [
                        raw_blocks[block_positions[index]]
                        for index in all_active_indices
                        if index in block_positions
                    ],
                    dtype=np.float32,
                )
            ),
            "pre_bridge": spectral_summary(
                np.asarray(
                    [
                        pre_blocks[block_positions[index]]
                        for index in all_active_indices
                        if index in block_positions
                    ],
                    dtype=np.float32,
                )
            ),
            "endpoint_preserved": spectral_summary(endpoint_active),
            "endpoint_preserved_source_block_count": len(
                preserved_active_indices
            ),
        },
        "endpoint_zero_metrics": zero_metrics(endpoint),
        "transport": transport,
        "block_matches": matches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenario_dirs = sorted(
        path
        for path in args.matrix_root.iterdir()
        if path.is_dir() and list(path.glob("*_input.wav"))
    )
    scenarios = [analyze_scenario(path) for path in scenario_dirs]
    summary = {
        "sample_rate_hz": SAMPLE_RATE,
        "block_size": BLOCK_SIZE,
        "matching": {
            "tracking_correlation_threshold": 0.72,
            "preserved_correlation_threshold": 0.985,
            "sample_comparison_scope": "high_confidence_preserved_blocks_only",
        },
        "scenarios": scenarios,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
