from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any


EXPECTED_ORDER = [
    ("01-sysvad-shared-event-a", "sysvad"),
    ("02-hda-shared-event-a", "hda"),
    ("03-hda-shared-event-b", "hda"),
    ("04-sysvad-shared-event-b", "sysvad"),
]
TRACE_SCHEMA_VERSION = 1
SUMMARY_SCHEMA_VERSION = 1


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_trace(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def analyze_leg(path: Path, expected_endpoint: str) -> dict[str, Any]:
    summary_path = path / "summary.json"
    trace_path = path / "event_trace.csv"
    scheduler_path = path / "scheduler.json"
    if not summary_path.exists() or not trace_path.exists():
        return {
            "scenario": path.name,
            "endpoint_role": expected_endpoint,
            "status": "incomplete",
            "checks": {"complete": False},
        }

    summary = load_json(summary_path)
    rows = load_trace(trace_path)
    required_columns = {
        "schema_version",
        "event_index",
        "endpoint_id",
        "wait_qpc_start",
        "wait_qpc_end",
        "wait_duration_ms",
        "wait_result",
        "signal_qpc",
        "previous_signal_qpc",
        "signal_interval_ms",
        "packets_drained",
        "frames_drained",
        "wasapi_flags",
        "reference_period_ms",
        "late_threshold_ms",
        "delay_periods",
    }
    columns_ok = bool(rows) and required_columns.issubset(rows[0])
    indices = [int(row["event_index"]) for row in rows] if rows else []
    trace_versions = (
        {int(row["schema_version"]) for row in rows} if rows else set()
    )
    endpoint_ids = {row["endpoint_id"] for row in rows} if rows else set()
    qpc_spans_ok = all(
        int(row["wait_qpc_end"]) >= int(row["wait_qpc_start"])
        for row in rows
    )
    durations_ok = all(
        abs(
            (
                int(row["wait_qpc_end"]) - int(row["wait_qpc_start"])
            )
            * 1000.0
            / float(summary["qpc_frequency_hz"])
            - float(row["wait_duration_ms"])
        )
        <= 0.002
        for row in rows
    )
    intervals = [
        float(row["signal_interval_ms"])
        for row in rows
        if row["wait_result"] == "signaled"
        and float(row["signal_interval_ms"]) > 0.0
    ]
    reference_period_ms = float(summary["reference_period_ms"])
    late_threshold_ms = max(30.0, 2.5 * reference_period_ms)
    late_rows = [
        row
        for row in rows
        if row["wait_result"] == "signaled"
        and float(row["signal_interval_ms"]) > late_threshold_ms
    ]
    result_counts = {
        "signaled": sum(row["wait_result"] == "signaled" for row in rows),
        "timeout": sum(row["wait_result"] == "timeout" for row in rows),
        "failed": sum(row["wait_result"] == "failed" for row in rows),
    }
    packets_recomputed = sum(int(row["packets_drained"]) for row in rows)
    frames_recomputed = sum(int(row["frames_drained"]) for row in rows)
    delay_periods_ok = all(
        (
            float(row["signal_interval_ms"]) == 0.0
            and float(row["delay_periods"]) == 0.0
        )
        or abs(
            float(row["delay_periods"])
            - float(row["signal_interval_ms"]) / reference_period_ms
        )
        <= 0.001
        for row in rows
    )
    scheduler = (
        load_json(scheduler_path)
        if scheduler_path.exists()
        else {"status": "missing", "samples": []}
    )
    scheduler_gaps = [
        row
        for row in scheduler.get("samples", [])
        if float(row["interval_ms"]) > 30.0
    ]
    scheduler_windows = [
        (
            int(row["qpc_ns"]) - round(float(row["interval_ms"]) * 1e6),
            int(row["qpc_ns"]),
        )
        for row in scheduler_gaps
    ]
    qpc_frequency = float(summary["qpc_frequency_hz"])
    late_scheduler_overlap = 0
    for row in late_rows:
        wait_start_ns = round(
            int(row["wait_qpc_start"]) * 1e9 / qpc_frequency
        )
        wait_end_ns = round(
            int(row["wait_qpc_end"]) * 1e9 / qpc_frequency
        )
        if any(
            wait_start_ns <= candidate_end + 5_000_000
            and wait_end_ns >= candidate_start - 5_000_000
            for candidate_start, candidate_end in scheduler_windows
        ):
            late_scheduler_overlap += 1
    observed_median = statistics.median(intervals) if intervals else None
    calculated_missed = sum(
        max(
            0,
            round(float(row["signal_interval_ms"]) / reference_period_ms)
            - 1,
        )
        for row in late_rows
    )
    summary_consistent = all(
        (
            int(summary["schema_version"]) == SUMMARY_SCHEMA_VERSION,
            summary["status"] == "completed",
            summary["endpoint_role"] == expected_endpoint,
            int(summary["waits"]) == len(rows),
            int(summary["signals"]) == result_counts["signaled"],
            int(summary["timeouts"]) == result_counts["timeout"],
            int(summary["wait_failures"]) == result_counts["failed"],
            int(summary["packets_drained"]) == packets_recomputed,
            int(summary["frames_drained"]) == frames_recomputed,
            int(summary["late_signal_count"]) == len(late_rows),
            int(summary["missed_period_equivalents"]) == calculated_missed,
            abs(float(summary["late_threshold_ms"]) - late_threshold_ms)
            <= 0.001,
        )
    )
    complete = all(
        (
            columns_ok,
            trace_versions == {TRACE_SCHEMA_VERSION},
            indices == list(range(1, len(rows) + 1)),
            endpoint_ids == {summary["endpoint"]["id"]},
            qpc_spans_ok,
            durations_ok,
            delay_periods_ok,
            summary_consistent,
            reference_period_ms > 0.0,
            int(summary["qpc_frequency_hz"]) > 0,
            scheduler.get("status") == "completed",
        )
    )
    return {
        "scenario": path.name,
        "endpoint_role": expected_endpoint,
        "status": "completed" if complete else "invalid",
        "endpoint": summary["endpoint"],
        "mix_format": summary["mix_format"],
        "device_period": summary["device_period"],
        "buffer_frames": summary["buffer_frames"],
        "qpc_frequency_hz": summary["qpc_frequency_hz"],
        "duration_seconds": summary["duration_seconds"],
        "waits": summary["waits"],
        "signals": summary["signals"],
        "timeouts": summary["timeouts"],
        "wait_failures": summary["wait_failures"],
        "packets_drained": summary["packets_drained"],
        "frames_drained": summary["frames_drained"],
        "silent_packets": summary["silent_packets"],
        "discontinuities": summary["discontinuities"],
        "timestamp_errors": summary["timestamp_errors"],
        "wait_ms": summary["wait_ms"],
        "signal_interval_ms": {
            **summary["signal_interval_ms"],
            "observed_median_recomputed": observed_median,
        },
        "reference_period_ms": reference_period_ms,
        "late_threshold_ms": late_threshold_ms,
        "late_signal_count": len(late_rows),
        "missed_period_equivalents": calculated_missed,
        "max_delay_periods": max(
            (float(row["delay_periods"]) for row in rows),
            default=0.0,
        ),
        "scheduler_gaps_over_30ms": len(scheduler_gaps),
        "late_signals_scheduler_overlap": late_scheduler_overlap,
        "late_signals_without_scheduler_overlap": (
            len(late_rows) - late_scheduler_overlap
        ),
        "checks": {
            "complete": complete,
            "trace_columns": columns_ok,
            "trace_version": trace_versions == {TRACE_SCHEMA_VERSION},
            "contiguous_event_index": (
                indices == list(range(1, len(rows) + 1))
            ),
            "single_exact_endpoint_id": (
                endpoint_ids == {summary["endpoint"]["id"]}
            ),
            "valid_qpc_spans": qpc_spans_ok,
            "durations_match_qpc": durations_ok,
            "summary_consistent": summary_consistent,
            "delay_periods_consistent": delay_periods_ok,
            "scheduler_complete": scheduler.get("status") == "completed",
        },
    }


def comparable_order_of_magnitude(
    sysvad: list[dict[str, Any]],
    hda: list[dict[str, Any]],
) -> bool:
    sysvad_max = max(row["max_delay_periods"] for row in sysvad)
    hda_max = max(row["max_delay_periods"] for row in hda)
    if sysvad_max <= 0.0 or hda_max <= 0.0:
        return False
    ratio = max(sysvad_max, hda_max) / min(sysvad_max, hda_max)
    return ratio <= 4.0


def classify(legs: list[dict[str, Any]]) -> tuple[str, dict[str, bool]]:
    complete = (
        len(legs) == 4
        and all(row["checks"]["complete"] for row in legs)
        and [
            (row["scenario"], row["endpoint_role"]) for row in legs
        ]
        == EXPECTED_ORDER
    )
    if not complete:
        return "mixed_or_inconclusive", {
            "complete_evidence": False,
            "hda_clean_both": False,
            "sysvad_late_both": False,
            "hda_late_both": False,
            "comparable_order_of_magnitude": False,
        }

    sysvad = [row for row in legs if row["endpoint_role"] == "sysvad"]
    hda = [row for row in legs if row["endpoint_role"] == "hda"]
    hda_clean_both = all(
        row["timeouts"] == 0
        and row["wait_failures"] == 0
        and row["late_signal_count"] == 0
        for row in hda
    )
    sysvad_late_both = all(row["late_signal_count"] > 0 for row in sysvad)
    hda_late_both = all(row["late_signal_count"] > 0 for row in hda)
    comparable = comparable_order_of_magnitude(sysvad, hda)
    if hda_clean_both and sysvad_late_both:
        classification = "sysvad_event_path_specific"
    elif hda_late_both and sysvad_late_both and comparable:
        classification = "virtualbox_event_timing_supported"
    else:
        classification = "mixed_or_inconclusive"
    return classification, {
        "complete_evidence": complete,
        "hda_clean_both": hda_clean_both,
        "sysvad_late_both": sysvad_late_both,
        "hda_late_both": hda_late_both,
        "comparable_order_of_magnitude": comparable,
    }


def analyze(root: Path, output: Path) -> dict[str, Any]:
    legs = []
    for name, endpoint_role in EXPECTED_ORDER:
        path = root / name
        if not path.is_dir():
            legs.append(
                {
                    "scenario": name,
                    "endpoint_role": endpoint_role,
                    "status": "incomplete",
                    "checks": {"complete": False},
                }
            )
            continue
        legs.append(analyze_leg(path, endpoint_role))
    classification, checks = classify(legs)
    result = {
        "status": "completed",
        "classification": classification,
        "criteria": {
            "late_signal": "interval_ms > max(30, 2.5 * reference_period_ms)",
            "missed_period_equivalents": (
                "sum(max(0, round(interval/reference_period)-1)) "
                "over late signals"
            ),
            "comparison_normalized_by_period": True,
        },
        "legs": legs,
        "checks": checks,
        "listening_unlocked": False,
        "driver_correctness_claimed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.root, args.output)


if __name__ == "__main__":
    main()
