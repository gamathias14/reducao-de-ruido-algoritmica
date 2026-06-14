from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
STALL_THRESHOLD_MS = 30.0
REQUIRED_PHASES = {
    "inter_iteration",
    "poll_wait",
    "get_next_packet_size",
    "get_buffer",
    "pcm_memory_write",
    "packet_analysis",
    "packet_trace_write",
    "release_buffer",
    "poll_bridge_stats",
    "poll_trace_write",
    "capture_iteration",
    "wave_file_write",
    "timing_trace_write",
}
WASAPI_PHASES = {
    "get_next_packet_size",
    "get_buffer",
    "release_buffer",
}
IO_PHASES = {
    "packet_trace_write",
    "poll_trace_write",
}
AGGREGATE_PHASES = {"capture_iteration", "poll_wait"}
POST_CAPTURE_PHASES = {"wave_file_write", "timing_trace_write"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def analyze_trace(path: Path) -> dict[str, Any]:
    rows = read_rows(path)
    if not rows:
        raise ValueError("capture timing trace is empty")

    required_columns = {
        "schema_version",
        "event_index",
        "qpc_frequency_hz",
        "poll_index",
        "packet_index",
        "phase",
        "qpc_start_ns",
        "qpc_end_ns",
        "duration_ms",
        "hresult",
        "packet_frames",
        "bytes",
        "flags",
    }
    missing = required_columns.difference(rows[0])
    if missing:
        raise ValueError(
            "capture timing trace lacks columns: "
            + ", ".join(sorted(missing))
        )

    versions = {int(row["schema_version"]) for row in rows}
    frequencies = {int(row["qpc_frequency_hz"]) for row in rows}
    phases = {row["phase"] for row in rows}
    event_indices = [int(row["event_index"]) for row in rows]
    invalid_spans = []
    duration_mismatches = []
    for row in rows:
        start_ns = int(row["qpc_start_ns"])
        end_ns = int(row["qpc_end_ns"])
        duration_ms = float(row["duration_ms"])
        if end_ns < start_ns:
            invalid_spans.append(int(row["event_index"]))
            continue
        calculated_ms = (end_ns - start_ns) / 1e6
        if abs(calculated_ms - duration_ms) > 0.001:
            duration_mismatches.append(int(row["event_index"]))

    long_events = [
        {
            "event_index": int(row["event_index"]),
            "poll_index": int(row["poll_index"]),
            "packet_index": int(row["packet_index"]),
            "phase": row["phase"],
            "qpc_start_ns": int(row["qpc_start_ns"]),
            "qpc_end_ns": int(row["qpc_end_ns"]),
            "duration_ms": float(row["duration_ms"]),
            "hresult": row["hresult"],
        }
        for row in rows
        if float(row["duration_ms"]) > STALL_THRESHOLD_MS
    ]
    phase_max_ms: dict[str, float] = {}
    phase_failure_counts: Counter[str] = Counter()
    for row in rows:
        phase = row["phase"]
        phase_max_ms[phase] = max(
            phase_max_ms.get(phase, 0.0),
            float(row["duration_ms"]),
        )
        if int(row["hresult"], 16) != 0:
            phase_failure_counts[phase] += 1

    long_phase_counts = Counter(row["phase"] for row in long_events)
    leaf_long_events = [
        row
        for row in long_events
        if (
            row["phase"] not in AGGREGATE_PHASES
            and row["phase"] not in POST_CAPTURE_PHASES
            and row["phase"] != "inter_iteration"
        )
    ]
    inter_iteration_long_events = [
        row for row in long_events if row["phase"] == "inter_iteration"
    ]
    aggregate_long_events = [
        row for row in long_events if row["phase"] in AGGREGATE_PHASES
    ]
    dominant_event = (
        max(leaf_long_events, key=lambda row: row["duration_ms"])
        if leaf_long_events
        else (
            max(
                inter_iteration_long_events,
                key=lambda row: row["duration_ms"],
            )
            if inter_iteration_long_events
            else (
                max(aggregate_long_events, key=lambda row: row["duration_ms"])
                if aggregate_long_events
                else None
            )
        )
    )
    dominant_phase = (
        dominant_event["phase"]
        if dominant_event is not None
        else None
    )
    if dominant_phase in WASAPI_PHASES:
        classification = "stall_inside_wasapi"
    elif dominant_phase in IO_PHASES:
        classification = "stall_inside_capture_io"
    elif dominant_phase == "inter_iteration":
        classification = "stall_between_capture_iterations"
    elif dominant_phase == "poll_wait_switch_to_thread":
        classification = "capture_thread_delayed_inside_switch_to_thread"
    elif dominant_phase == "poll_wait_sleep":
        classification = "capture_thread_delayed_inside_sleep"
    elif dominant_phase == "poll_wait_spin":
        classification = "capture_thread_delayed_inside_spin"
    elif dominant_phase == "poll_wait_endpoint_event":
        classification = "capture_wait_delayed_before_endpoint_event_signal"
    elif dominant_phase in {"pcm_memory_write", "packet_analysis"}:
        classification = "stall_inside_capture_process_work"
    elif dominant_phase == "capture_iteration":
        classification = "stall_inside_unattributed_capture_iteration"
    else:
        classification = "no_capture_stall_observed"

    complete_schema = (
        versions == {SCHEMA_VERSION}
        and len(frequencies) == 1
        and next(iter(frequencies), 0) > 0
        and event_indices == list(range(1, len(rows) + 1))
        and not invalid_spans
        and not duration_mismatches
        and REQUIRED_PHASES.issubset(phases)
    )
    return {
        "status": "completed",
        "classification": classification,
        "schema": {
            "version": next(iter(versions)) if len(versions) == 1 else None,
            "qpc_frequency_hz": (
                next(iter(frequencies)) if len(frequencies) == 1 else None
            ),
            "events": len(rows),
            "phases": sorted(phases),
            "missing_required_phases": sorted(REQUIRED_PHASES.difference(phases)),
        },
        "timing": {
            "stall_threshold_ms": STALL_THRESHOLD_MS,
            "long_event_count": len(long_events),
            "long_phase_counts": dict(sorted(long_phase_counts.items())),
            "dominant_phase": dominant_phase,
            "dominant_event": dominant_event,
            "phase_max_ms": dict(sorted(phase_max_ms.items())),
            "phase_failure_counts": dict(
                sorted(phase_failure_counts.items())
            ),
            "long_events": long_events,
        },
        "checks": {
            "complete_schema": complete_schema,
            "monotonic_event_index": (
                event_indices == list(range(1, len(rows) + 1))
            ),
            "valid_qpc_spans": not invalid_spans,
            "duration_matches_qpc": not duration_mismatches,
            "required_phases_present": REQUIRED_PHASES.issubset(phases),
        },
    }


def gap_windows(
    rows: list[dict[str, Any]],
    *,
    qpc_key: str,
    interval_key: str,
) -> list[tuple[int, int]]:
    windows = []
    for row in rows:
        interval_ms = float(row[interval_key])
        if interval_ms <= STALL_THRESHOLD_MS:
            continue
        end_ns = int(row[qpc_key])
        windows.append((end_ns - round(interval_ms * 1e6), end_ns))
    return windows


def overlaps(
    event: dict[str, Any],
    windows: list[tuple[int, int]],
    tolerance_ms: float = 5.0,
) -> bool:
    tolerance_ns = round(tolerance_ms * 1e6)
    start_ns = int(event["qpc_start_ns"])
    end_ns = int(event["qpc_end_ns"])
    return any(
        start_ns <= candidate_end + tolerance_ns
        and end_ns >= candidate_start - tolerance_ns
        for candidate_start, candidate_end in windows
    )


def correlate_inter_iteration_stall(
    scenario: Path,
    result: dict[str, Any],
) -> None:
    dominant = result["timing"]["dominant_event"]
    if dominant is None or dominant["phase"] not in {
        "inter_iteration",
        "poll_wait_switch_to_thread",
        "poll_wait_sleep",
    }:
        return
    inter_iteration_events = [
        event
        for event in result["timing"]["long_events"]
        if event["phase"] == "inter_iteration"
    ]
    if not inter_iteration_events:
        return

    scheduler = json.loads(
        (scenario / "scheduler.json").read_text(encoding="utf-8-sig")
    )
    client = json.loads(
        (scenario / "client.json").read_text(encoding="utf-8-sig")
    )
    scheduler_windows = gap_windows(
        scheduler.get("samples", []),
        qpc_key="qpc_ns",
        interval_key="interval_ms",
    )
    writer_windows = gap_windows(
        client.get("bridge", {}).get("loop_samples", []),
        qpc_key="qpc_ns",
        interval_key="loop_interval_ms",
    )
    correlations = [
        {
            "event_index": event["event_index"],
            "duration_ms": event["duration_ms"],
            "scheduler_gap_overlap": overlaps(event, scheduler_windows),
            "writer_gap_overlap": overlaps(event, writer_windows),
        }
        for event in inter_iteration_events
    ]
    shared_count = sum(
        row["scheduler_gap_overlap"] or row["writer_gap_overlap"]
        for row in correlations
    )
    specific_count = len(correlations) - shared_count
    result["correlation"] = {
        "scheduler_gap_count": len(scheduler_windows),
        "writer_gap_count": len(writer_windows),
        "shared_inter_iteration_stalls": shared_count,
        "process_specific_inter_iteration_stalls": specific_count,
        "events": correlations,
    }
    if dominant["phase"] != "inter_iteration":
        return
    if shared_count and specific_count:
        result["classification"] = "mixed_capture_scheduling_delays"
    elif shared_count:
        result["classification"] = "shared_guest_scheduling_delay"
    else:
        result["classification"] = "capture_process_specific_descheduling"


def analyze(private_root: Path, output: Path) -> dict[str, Any]:
    scenarios = sorted(path for path in private_root.iterdir() if path.is_dir())
    if not scenarios:
        raise ValueError("capture timing gate requires at least one scenario")

    results = []
    for scenario in scenarios:
        trace_path = scenario / "capture_timing_trace.csv"
        result = analyze_trace(trace_path)
        result["scenario"] = scenario.name
        correlate_inter_iteration_stall(scenario, result)
        results.append(result)

    complete_evidence = all(
        row["checks"]["complete_schema"] for row in results
    )
    observed_classifications = {
        row["classification"]
        for row in results
        if row["classification"] != "no_capture_stall_observed"
    }
    if not complete_evidence:
        classification = "capture_timing_trace_incomplete"
    elif len(observed_classifications) == 1:
        classification = next(iter(observed_classifications))
    elif len(observed_classifications) > 1:
        classification = "mixed_capture_stall_phases"
    else:
        classification = "no_capture_stall_observed"

    gate = {
        "status": "completed",
        "classification": classification,
        "scenarios": results,
        "checks": {
            "complete_evidence": complete_evidence,
            "root_cause_phase_observed": bool(observed_classifications),
            "listening_unlocked": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(gate, indent=2), encoding="utf-8")
    return gate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.private_root, args.output)
    if not result["checks"]["complete_evidence"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
