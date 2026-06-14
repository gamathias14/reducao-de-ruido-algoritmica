from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load analyzer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_ROOT = Path(__file__).resolve().parent
SCHEDULING = load_module(
    "ptc_endpoint_scheduling_event",
    SCRIPT_ROOT / "analyze_endpoint_scheduling.py",
)
TIMING = load_module(
    "ptc_capture_timing_event",
    SCRIPT_ROOT / "analyze_capture_timing.py",
)

EXPECTED_ORDER = [
    ("01-yield-control-a", "baseline", "yield"),
    ("02-event-a", "mitigated", "event"),
    ("03-event-b", "mitigated", "event"),
    ("04-yield-control-b", "baseline", "yield"),
]
EVENT_NAMES = ("02-event-a", "03-event-b")
CONTROL_NAMES = ("01-yield-control-a", "04-yield-control-b")
EVIDENCE_CHECKS = {
    "client_completed",
    "server_completed",
    "scheduler_completed",
    "thread_scheduling_applied",
    "bridge_trace_available",
    "capture_trace_available",
    "capture_poll_trace_available",
}


def summarize_group(
    scenarios: list[dict[str, Any]],
    group: str,
) -> dict[str, Any]:
    selected = [row for row in scenarios if row["group"] == group]
    return {
        **SCHEDULING.group_summary(scenarios, group),
        "host_send_gaps_over_30ms": sum(
            row["host"]["stalls_over_30ms"] for row in selected
        ),
        "guest_receive_gaps_over_30ms": sum(
            row["guest_receive"]["stalls_over_30ms"] for row in selected
        ),
        "capture_packet_gaps_over_30ms": sum(
            row["capture"]["packet_gaps_over_30ms"] for row in selected
        ),
        "write_errors": sum(
            row["bridge"]["write_errors"] for row in selected
        ),
    }


def fixed_config_ok(
    scenario: dict[str, Any],
    expected_strategy: str,
) -> bool:
    config = scenario["config"]
    return all(
        (
            config.get("writer_scheduling") == "normal",
            config.get("poll_wait_strategy") == "yield",
            config.get("capture_poll_wait_strategy") == expected_strategy,
            bool(config.get("capture_start_barrier")),
            int(config.get("send_lead_ms", 0)) == 0,
            int(config.get("start_delay_ms", 0)) == 0,
            int(config.get("initial_burst_blocks", -1)) == 2,
            int(config.get("target_driver_depth", -1)) == 2,
            int(config.get("user_queue_blocks", -1)) == 4,
            int(config.get("poll_interval_ms", -1)) == 2,
            config.get("host_vm_priority") == "Unchanged",
            config.get("host_vm_affinity") == "unchanged",
        )
    )


def paired_reduction(
    by_name: dict[str, dict[str, Any]],
    key_path: tuple[str, str],
) -> bool:
    section, key = key_path
    return all(
        (
            by_name["02-event-a"][section][key]
            < by_name["01-yield-control-a"][section][key],
            by_name["03-event-b"][section][key]
            < by_name["04-yield-control-b"][section][key],
        )
    )


def paired_not_increased(
    by_name: dict[str, dict[str, Any]],
    key_path: tuple[str, str],
) -> bool:
    section, key = key_path
    return all(
        (
            by_name["02-event-a"][section][key]
            <= by_name["01-yield-control-a"][section][key],
            by_name["03-event-b"][section][key]
            <= by_name["04-yield-control-b"][section][key],
        )
    )


def correlate_event_waits(
    scenario: Path,
    timing: dict[str, Any],
) -> dict[str, Any]:
    long_waits = [
        event
        for event in timing["timing"]["long_events"]
        if event["phase"] == "poll_wait_endpoint_event"
    ]
    scheduler = json.loads(
        (scenario / "scheduler.json").read_text(encoding="utf-8-sig")
    )
    client = json.loads(
        (scenario / "client.json").read_text(encoding="utf-8-sig")
    )
    scheduler_windows = TIMING.gap_windows(
        scheduler.get("samples", []),
        qpc_key="qpc_ns",
        interval_key="interval_ms",
    )
    writer_windows = TIMING.gap_windows(
        client.get("bridge", {}).get("loop_samples", []),
        qpc_key="qpc_ns",
        interval_key="loop_interval_ms",
    )
    rows = []
    for event in long_waits:
        scheduler_overlap = TIMING.overlaps(event, scheduler_windows)
        writer_overlap = TIMING.overlaps(event, writer_windows)
        rows.append(
            {
                "event_index": event["event_index"],
                "duration_ms": event["duration_ms"],
                "scheduler_gap_overlap": scheduler_overlap,
                "writer_gap_overlap": writer_overlap,
            }
        )
    return {
        "long_event_waits": len(rows),
        "scheduler_gap_count": len(scheduler_windows),
        "writer_gap_count": len(writer_windows),
        "both_overlap": sum(
            row["scheduler_gap_overlap"] and row["writer_gap_overlap"]
            for row in rows
        ),
        "scheduler_only": sum(
            row["scheduler_gap_overlap"] and not row["writer_gap_overlap"]
            for row in rows
        ),
        "writer_only": sum(
            row["writer_gap_overlap"] and not row["scheduler_gap_overlap"]
            for row in rows
        ),
        "no_overlap": sum(
            not row["scheduler_gap_overlap"]
            and not row["writer_gap_overlap"]
            for row in rows
        ),
        "events": rows,
    }


def evaluate_gate(
    scenarios: list[dict[str, Any]],
    timing_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_name = {row["scenario"]: row for row in scenarios}
    expected_names = [row[0] for row in EXPECTED_ORDER]
    order_ok = [row["scenario"] for row in scenarios] == expected_names
    configs_ok = order_ok and all(
        row["group"] == expected_group
        and fixed_config_ok(row, expected_strategy)
        for row, (_, expected_group, expected_strategy)
        in zip(scenarios, EXPECTED_ORDER)
    )
    timing_complete = (
        set(timing_by_name) == set(expected_names)
        and all(
            timing_by_name[name]["checks"]["complete_schema"]
            for name in expected_names
        )
    )
    control_phase_preserved = timing_complete and all(
        "poll_wait_switch_to_thread"
        in timing_by_name[name]["schema"]["phases"]
        and "poll_wait_endpoint_event"
        not in timing_by_name[name]["schema"]["phases"]
        for name in CONTROL_NAMES
    )
    event_phase_present = timing_complete and all(
        "poll_wait_endpoint_event"
        in timing_by_name[name]["schema"]["phases"]
        and "poll_wait_switch_to_thread"
        not in timing_by_name[name]["schema"]["phases"]
        for name in EVENT_NAMES
    )
    event_wait_success = timing_complete and all(
        timing_by_name[name]["timing"]["phase_failure_counts"].get(
            "poll_wait_endpoint_event",
            0,
        )
        == 0
        for name in EVENT_NAMES
    )
    complete_evidence = (
        len(scenarios) == 4
        and order_ok
        and configs_ok
        and timing_complete
        and all(
            all(row["checks"].get(key, False) for key in EVIDENCE_CHECKS)
            for row in scenarios
        )
    )
    baseline = summarize_group(scenarios, "baseline")
    event = summarize_group(scenarios, "mitigated")
    event_scenarios = [
        by_name[name] for name in EVENT_NAMES if name in by_name
    ]
    event_complete = (
        len(event_scenarios) == 2
        and all(row["checks"]["pipeline_complete"] for row in event_scenarios)
        and event["sent"] == 2000
        and event["dropped"] == 0
        and event["write_errors"] == 0
    )
    zero_write_errors = (
        baseline["write_errors"] == 0 and event["write_errors"] == 0
    )
    capture_gaps_reduced = order_ok and paired_reduction(
        by_name,
        ("capture", "poll_gaps_over_30ms"),
    )
    underruns_reduced = order_ok and paired_reduction(
        by_name,
        ("bridge", "driver_underruns_source_window"),
    )
    no_impact_regression = order_ok and all(
        (
            paired_not_increased(
                by_name,
                ("bridge", "writer_gaps_over_30ms"),
            ),
            paired_not_increased(
                by_name,
                ("scheduler_probe", "gaps_over_30ms"),
            ),
            paired_not_increased(
                by_name,
                ("host", "stalls_over_30ms"),
            ),
            paired_not_increased(
                by_name,
                ("guest_receive", "stalls_over_30ms"),
            ),
            event["dropped"] <= baseline["dropped"],
            event["write_errors"] <= baseline["write_errors"],
            underruns_reduced,
        )
    )
    event_zero_underrun = (
        len(event_scenarios) == 2
        and all(
            row["bridge"]["driver_underruns_source_window"] == 0
            for row in event_scenarios
        )
    )
    confirmed = all(
        (
            complete_evidence,
            control_phase_preserved,
            event_phase_present,
            event_wait_success,
            event_complete,
            zero_write_errors,
            capture_gaps_reduced,
            underruns_reduced,
            no_impact_regression,
        )
    )
    if not complete_evidence:
        classification = "capture_event_evidence_incomplete"
    elif not confirmed:
        classification = "capture_event_not_confirmed"
    elif event_zero_underrun:
        classification = "capture_event_completed_without_underruns"
    else:
        classification = "capture_event_reduced_gaps_and_underruns"

    return {
        "status": "completed",
        "classification": classification,
        "scenarios": scenarios,
        "capture_timing": timing_by_name,
        "baseline": baseline,
        "event": event,
        "checks": {
            "complete_evidence": complete_evidence,
            "abba_order": order_ok,
            "fixed_configuration": configs_ok,
            "control_switch_phase_preserved": control_phase_preserved,
            "event_phase_present": event_phase_present,
            "event_wait_success": event_wait_success,
            "event_zero_drop": event_complete,
            "zero_write_errors": zero_write_errors,
            "capture_gaps_reduced_reproducibly": capture_gaps_reduced,
            "underruns_reduced_reproducibly": underruns_reduced,
            "no_writer_scheduler_transport_regression": (
                no_impact_regression
            ),
            "event_zero_underrun": event_zero_underrun,
            "event_confirmed": confirmed,
            "listening_unlocked": confirmed and event_zero_underrun,
        },
    }


def analyze(
    run_root: Path,
    private_root: Path,
    output: Path,
) -> dict[str, Any]:
    run_scenarios = sorted(
        path for path in run_root.iterdir() if path.is_dir()
    )
    if len(run_scenarios) != 4:
        raise ValueError("capture event gate requires four scenarios")
    scenarios = [
        SCHEDULING.analyze_scenario(path, private_root / path.name)
        for path in run_scenarios
    ]
    timing_by_name = {
        path.name: TIMING.analyze_trace(
            private_root / path.name / "capture_timing_trace.csv"
        )
        for path in run_scenarios
    }
    for name in EVENT_NAMES:
        timing_by_name[name]["event_wait_correlation"] = (
            correlate_event_waits(private_root / name, timing_by_name[name])
        )
    result = evaluate_gate(scenarios, timing_by_name)
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
