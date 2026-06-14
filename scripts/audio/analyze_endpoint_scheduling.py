from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def distribution(values: list[float], prefix: str) -> dict[str, float]:
    if not values:
        return {
            f"{prefix}_mean": 0.0,
            f"{prefix}_p95": 0.0,
            f"{prefix}_p99": 0.0,
            f"{prefix}_max": 0.0,
        }
    samples = np.asarray(values, dtype=np.float64)
    return {
        f"{prefix}_mean": float(np.mean(samples)),
        f"{prefix}_p95": float(np.percentile(samples, 95)),
        f"{prefix}_p99": float(np.percentile(samples, 99)),
        f"{prefix}_max": float(np.max(samples)),
    }


def gap_windows(
    rows: list[dict[str, Any]],
    *,
    qpc_key: str,
    interval_key: str,
    threshold_ms: float = 30.0,
) -> list[tuple[int, int]]:
    windows = []
    for row in rows:
        interval_ms = float(row[interval_key])
        if interval_ms <= threshold_ms:
            continue
        end_ns = int(row[qpc_key])
        windows.append((end_ns - round(interval_ms * 1e6), end_ns))
    return windows


def overlaps(
    window: tuple[int, int],
    candidates: list[tuple[int, int]],
    tolerance_ms: float = 5.0,
) -> bool:
    tolerance_ns = round(tolerance_ms * 1e6)
    start, end = window
    return any(
        start <= candidate_end + tolerance_ns
        and end >= candidate_start - tolerance_ns
        for candidate_start, candidate_end in candidates
    )


def analyze_scenario(
    run_scenario: Path,
    private_scenario: Path,
) -> dict[str, Any]:
    config = read_json(run_scenario / "scenario_config.json")
    server = read_json(run_scenario / "server.json")
    client = read_json(run_scenario / "client.json")
    scheduler = read_json(private_scenario / "scheduler.json")
    capture = read_csv(private_scenario / "capture_trace.csv")
    capture_poll = read_csv(private_scenario / "capture_poll_trace.csv")
    client_trace = read_json(run_scenario / "client_trace.json")
    bridge = client["bridge"]
    source_start_ns = int(client_trace[0]["receive_qpc_ns"])
    source_end_ns = int(client_trace[-1]["receive_qpc_ns"])
    driver_events = [
        row
        for row in bridge.get("events", [])
        if row.get("event") == "driver_stats"
    ]
    driver_events.sort(key=lambda row: int(row["qpc_ns"]))
    driver_before_source = [
        row
        for row in driver_events
        if int(row["qpc_ns"]) <= source_start_ns
    ]
    driver_through_source = [
        row
        for row in driver_events
        if int(row["qpc_ns"]) <= source_end_ns
    ]
    driver_window = [
        row
        for row in driver_events
        if source_start_ns < int(row["qpc_ns"]) <= source_end_ns
    ]
    driver_start = (
        driver_before_source[-1]
        if driver_before_source
        else (driver_window[0] if driver_window else None)
    )
    driver_end = driver_through_source[-1] if driver_through_source else None
    source_underruns = (
        max(
            0,
            int(driver_end["underruns"])
            - int(driver_start["underruns"]),
        )
        if driver_start is not None and driver_end is not None
        else 0
    )
    source_underrun_events = 0
    previous_underruns = (
        int(driver_start["underruns"])
        if driver_start is not None
        else 0
    )
    for row in driver_window:
        underruns = int(row["underruns"])
        if underruns > previous_underruns:
            source_underrun_events += 1
        previous_underruns = underruns

    def inside_source_window(
        row: dict[str, Any],
        interval_key: str,
    ) -> bool:
        end_ns = int(row["qpc_ns"])
        start_ns = end_ns - round(float(row[interval_key]) * 1e6)
        return source_start_ns <= start_ns and end_ns <= source_end_ns

    loops = [
        row
        for row in bridge["loop_samples"]
        if inside_source_window(row, "loop_interval_ms")
    ]
    scheduler_samples = [
        row
        for row in scheduler["samples"]
        if inside_source_window(row, "interval_ms")
    ]
    capture_poll = [
        row
        for row in capture_poll
        if inside_source_window(row, "poll_interval_ms")
    ]
    capture = [
        row
        for row in capture
        if source_start_ns <= int(row["qpc_ns"]) <= source_end_ns
    ]

    receive_windows = gap_windows(
        client_trace,
        qpc_key="receive_qpc_ns",
        interval_key="receive_interval_ms",
    )
    writer_windows = gap_windows(
        loops,
        qpc_key="qpc_ns",
        interval_key="loop_interval_ms",
    )
    scheduler_windows = gap_windows(
        scheduler_samples,
        qpc_key="qpc_ns",
        interval_key="interval_ms",
    )
    capture_poll_windows = gap_windows(
        capture_poll,
        qpc_key="qpc_ns",
        interval_key="poll_interval_ms",
    )
    background_windows = scheduler_windows + capture_poll_windows
    writer_background = sum(
        overlaps(window, background_windows) for window in writer_windows
    )
    writer_receive_stall = sum(
        overlaps(window, receive_windows) for window in writer_windows
    )
    receive_qpc = [
        int(row["receive_qpc_ns"])
        for row in client_trace
    ]
    writer_with_receive_activity = sum(
        any(start_ns < value < end_ns for value in receive_qpc)
        for start_ns, end_ns in writer_windows
    )

    capture_qpc = [int(row["qpc_ns"]) for row in capture]
    capture_packet_gaps = [
        (current - previous) / 1e6
        for previous, current in zip(capture_qpc, capture_qpc[1:])
    ]
    loop_intervals = [float(row["loop_interval_ms"]) for row in loops[1:]]
    stats_calls = [float(row["get_stats_ms"]) for row in loops]
    write_calls = [
        float(row["write_ms"])
        for row in loops
        if row["action"] == "sent"
    ]
    consumption_progress = []
    previous_consumed: int | None = None
    for row in loops:
        consumed = int(row.get("blocks_consumed", 0))
        if previous_consumed is None or consumed > previous_consumed:
            consumption_progress.append(row)
            previous_consumed = consumed
    consumption_intervals_ms = [
        (
            int(current["qpc_ns"])
            - int(previous["qpc_ns"])
        )
        / 1e6
        for previous, current in zip(
            consumption_progress,
            consumption_progress[1:],
        )
    ]
    consumed_delta = (
        0
        if not loops
        else int(loops[-1].get("blocks_consumed", 0))
        - int(loops[0].get("blocks_consumed", 0))
    )
    source_duration_s = (source_end_ns - source_start_ns) / 1e9
    final_stats = bridge["driver_stats"] or {}
    dropped = (
        int(bridge["user_queue_dropped_total"])
        + int(bridge["stop_timeout_dropped"])
    )
    pipeline_complete = (
        int(bridge["submitted"]) == 1000
        and int(bridge["sent"]) == 1000
        and dropped == 0
        and int(final_stats.get("blocks_accepted", 0)) == 1000
        and int(bridge["write_errors"]) == 0
    )

    result: dict[str, Any] = {
        "scenario": run_scenario.name,
        "group": config.get(
            "comparison_group",
            (
                "mitigated"
                if (
                    config.get("poll_wait_strategy") == "yield"
                    or config["writer_scheduling"] == "mmcss"
                )
                else "baseline"
            ),
        ),
        "config": config,
        "host": {
            "send_interval_ms_max": server["send_interval_ms_max"],
            "stalls_over_30ms": server["interval_stalls_over_30ms"],
            "stalls_over_100ms": server["interval_stalls_over_100ms"],
        },
        "guest_receive": {
            "receive_interval_ms_max": client["receive_interval_ms_max"],
            "stalls_over_30ms": client["interval_stalls_over_30ms"],
            "stalls_over_100ms": client["interval_stalls_over_100ms"],
        },
        "bridge": {
            "submitted": bridge["submitted"],
            "sent": bridge["sent"],
            "dropped": dropped,
            "write_errors": bridge["write_errors"],
            "thread_scheduling_requested": (
                bridge["thread_scheduling_requested"]
            ),
            "thread_scheduling_applied": bridge["thread_scheduling_applied"],
            "thread_scheduling_error": bridge["thread_scheduling_error"],
            "poll_wait_strategy": bridge.get(
                "poll_wait_strategy",
                "sleep",
            ),
            "writer_gaps_over_30ms": len(writer_windows),
            "writer_gaps_correlated_background": writer_background,
            "writer_gaps_correlated_receive_stall": writer_receive_stall,
            "writer_gaps_with_receive_activity": (
                writer_with_receive_activity
            ),
            "writer_gaps_unexplained": (
                len(writer_windows) - writer_background
            ),
            "get_stats_calls_over_5ms": sum(
                value > 5.0 for value in stats_calls
            ),
            "write_calls_over_5ms": sum(
                value > 5.0 for value in write_calls
            ),
            "driver_accepted": final_stats.get("blocks_accepted", 0),
            "driver_consumed": final_stats.get("blocks_consumed", 0),
            "driver_final_depth": final_stats.get("queue_depth_blocks", 0),
            "driver_underruns": final_stats.get("underruns", 0),
            "driver_underruns_source_window": source_underruns,
            "driver_underrun_events_source_window": (
                source_underrun_events
            ),
            "fresh_consumption_rate_hz": (
                consumed_delta / source_duration_s
                if source_duration_s > 0.0
                else 0.0
            ),
            "consumption_gap_ms_max": max(
                consumption_intervals_ms,
                default=0.0,
            ),
            "consumption_gaps_over_30ms": sum(
                value > 30.0 for value in consumption_intervals_ms
            ),
            "driver_depth_two_fraction": (
                sum(
                    int(row.get("driver_queue_depth", 0)) == 2
                    for row in loops
                )
                / len(loops)
                if loops
                else 0.0
            ),
            "user_queue_full_fraction": (
                sum(
                    int(row.get("user_queue_depth", 0)) == 4
                    for row in loops
                )
                / len(loops)
                if loops
                else 0.0
            ),
        },
        "capture": {
            "packet_gap_ms_max": max(capture_packet_gaps, default=0),
            "packet_gaps_over_30ms": sum(
                value > 30 for value in capture_packet_gaps
            ),
            "poll_gap_ms_max": max(
                (
                    float(row["poll_interval_ms"])
                    for row in capture_poll
                ),
                default=0.0,
            ),
            "poll_gaps_over_30ms": len(capture_poll_windows),
        },
        "scheduler_probe": {
            "interval_ms_max": scheduler["observed_interval_ms_max"],
            "gaps_over_30ms": scheduler["gaps_over_30ms"],
            "gaps_over_100ms": scheduler["gaps_over_100ms"],
        },
        "checks": {
            "client_completed": client["status"] == "completed",
            "server_completed": server["status"] == "completed",
            "scheduler_completed": scheduler["status"] == "completed",
            "thread_scheduling_applied": (
                bridge["thread_scheduling_applied"]
            ),
            "bridge_trace_available": bool(loops),
            "capture_trace_available": bool(capture),
            "capture_poll_trace_available": bool(capture_poll),
            "pipeline_complete": pipeline_complete,
        },
    }
    result["bridge"].update(distribution(loop_intervals, "loop_interval_ms"))
    result["bridge"].update(distribution(stats_calls, "get_stats_ms"))
    result["bridge"].update(distribution(write_calls, "write_ms"))
    return result


def group_summary(
    scenarios: list[dict[str, Any]],
    group: str,
) -> dict[str, Any]:
    selected = [row for row in scenarios if row["group"] == group]
    return {
        "scenario_count": len(selected),
        "submitted": sum(row["bridge"]["submitted"] for row in selected),
        "sent": sum(row["bridge"]["sent"] for row in selected),
        "dropped": sum(row["bridge"]["dropped"] for row in selected),
        "writer_gaps_over_30ms": sum(
            row["bridge"]["writer_gaps_over_30ms"] for row in selected
        ),
        "scheduler_gaps_over_30ms": sum(
            row["scheduler_probe"]["gaps_over_30ms"] for row in selected
        ),
        "capture_poll_gaps_over_30ms": sum(
            row["capture"]["poll_gaps_over_30ms"] for row in selected
        ),
        "driver_underruns_source_window": sum(
            row["bridge"]["driver_underruns_source_window"]
            for row in selected
        ),
        "complete_scenarios": sum(
            row["checks"]["pipeline_complete"] for row in selected
        ),
    }


def classify(
    scenarios: list[dict[str, Any]],
    baseline: dict[str, Any],
    mitigated: dict[str, Any],
    zero_drop_mitigation: bool,
) -> str:
    baseline_capture_wait = {
        row["config"].get("capture_poll_wait_strategy")
        for row in scenarios
        if row["group"] == "baseline"
    }
    mitigated_capture_wait = {
        row["config"].get("capture_poll_wait_strategy")
        for row in scenarios
        if row["group"] == "mitigated"
    }
    capture_yield_gate = (
        baseline_capture_wait == {"sleep"}
        and mitigated_capture_wait == {"yield"}
    )
    baseline_start_barrier = {
        bool(row["config"].get("capture_start_barrier", False))
        for row in scenarios
        if row["group"] == "baseline"
    }
    mitigated_start_barrier = {
        bool(row["config"].get("capture_start_barrier", False))
        for row in scenarios
        if row["group"] == "mitigated"
    }
    capture_start_barrier_gate = (
        baseline_start_barrier == {False}
        and mitigated_start_barrier == {True}
    )
    baseline_send_lead = {
        int(row["config"].get("send_lead_ms", 0))
        for row in scenarios
        if row["group"] == "baseline"
    }
    mitigated_send_lead = {
        int(row["config"].get("send_lead_ms", 0))
        for row in scenarios
        if row["group"] == "mitigated"
    }
    send_lead_gate = (
        baseline_send_lead == {0}
        and mitigated_send_lead == {10}
    )
    baseline_host_affinity = {
        row["config"].get("host_vm_affinity")
        for row in scenarios
        if row["group"] == "baseline"
    }
    mitigated_host_affinity = {
        row["config"].get("host_vm_affinity")
        for row in scenarios
        if row["group"] == "mitigated"
    }
    host_affinity_gate = (
        baseline_host_affinity == {"all"}
        and mitigated_host_affinity == {"performance"}
    )
    if host_affinity_gate:
        if (
            zero_drop_mitigation
            and mitigated["driver_underruns_source_window"] == 0
        ):
            return "performance_core_affinity_completed_without_underruns"
        if (
            zero_drop_mitigation
            and mitigated["driver_underruns_source_window"]
            < baseline["driver_underruns_source_window"]
        ):
            return (
                "performance_core_affinity_reduced_but_did_not_zero_underruns"
            )
        return "performance_core_affinity_not_confirmed"
    if send_lead_gate:
        if (
            zero_drop_mitigation
            and mitigated["driver_underruns_source_window"] == 0
        ):
            return "ten_ms_send_lead_completed_without_underruns"
        if (
            zero_drop_mitigation
            and mitigated["driver_underruns_source_window"]
            < baseline["driver_underruns_source_window"]
        ):
            return "ten_ms_send_lead_reduced_but_did_not_zero_underruns"
        return "ten_ms_send_lead_not_confirmed"
    if capture_start_barrier_gate:
        if (
            zero_drop_mitigation
            and mitigated["driver_underruns_source_window"] == 0
        ):
            return "capture_start_barrier_completed_without_underruns"
        if (
            zero_drop_mitigation
            and mitigated["driver_underruns_source_window"]
            < baseline["driver_underruns_source_window"]
        ):
            return "capture_start_barrier_reduced_but_did_not_zero_underruns"
        return "capture_start_barrier_not_confirmed"
    if capture_yield_gate:
        if zero_drop_mitigation:
            return "capture_poll_yield_completed_without_drops"
        if mitigated["dropped"] < baseline["dropped"]:
            return "capture_poll_yield_reduced_but_did_not_eliminate_drops"
        return "capture_poll_yield_did_not_reduce_drops"
    if zero_drop_mitigation:
        return "mitigation_completed_1000_blocks_without_drops"
    if (
        mitigated["dropped"] < baseline["dropped"]
        and all(
            row["bridge"]["driver_depth_two_fraction"] >= 0.8
            and row["bridge"]["fresh_consumption_rate_hz"] < 49.8
            for row in scenarios
            if row["group"] == "mitigated"
        )
    ):
        return "writer_wakeup_mitigated_consumer_cadence_deficit_remains"
    if mitigated["dropped"] < baseline["dropped"]:
        return "mitigation_reduced_but_did_not_eliminate_drops"
    return "mitigation_did_not_reduce_drops"


def analyze(
    run_root: Path,
    private_root: Path,
    output: Path,
) -> dict[str, Any]:
    run_scenarios = sorted(
        path for path in run_root.iterdir() if path.is_dir()
    )
    if len(run_scenarios) != 4:
        raise ValueError("scheduling diagnostic requires four scenarios")
    scenarios = [
        analyze_scenario(path, private_root / path.name)
        for path in run_scenarios
    ]
    baseline = group_summary(scenarios, "baseline")
    mitigated = group_summary(scenarios, "mitigated")
    complete_evidence = all(
        all(
            (
                checks["client_completed"],
                checks["server_completed"],
                checks["scheduler_completed"],
                checks["thread_scheduling_applied"],
                checks["bridge_trace_available"],
                checks["capture_trace_available"],
                checks["capture_poll_trace_available"],
            )
        )
        for checks in (row["checks"] for row in scenarios)
    )
    zero_drop_mitigation = (
        mitigated["scenario_count"] == 2
        and mitigated["complete_scenarios"] == 2
    )
    classification = classify(
        scenarios,
        baseline,
        mitigated,
        zero_drop_mitigation,
    )
    result = {
        "status": "completed",
        "classification": classification,
        "scenarios": scenarios,
        "baseline": baseline,
        "mitigated": mitigated,
        "checks": {
            "complete_evidence": complete_evidence,
            "mitigated_zero_drop": zero_drop_mitigation,
            "mitigated_zero_underrun": (
                mitigated["driver_underruns_source_window"] == 0
            ),
            "private_replay_unlocked": zero_drop_mitigation,
            "listening_unlocked": (
                zero_drop_mitigation
                and mitigated["driver_underruns_source_window"] == 0
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run_root, args.private_root, args.output)
    if not result["checks"]["complete_evidence"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
