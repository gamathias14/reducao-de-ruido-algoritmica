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
    "ptc_endpoint_scheduling",
    SCRIPT_ROOT / "analyze_endpoint_scheduling.py",
)
TIMING = load_module(
    "ptc_capture_timing",
    SCRIPT_ROOT / "analyze_capture_timing.py",
)

EXPECTED_ORDER = [
    ("01-yield-control-a", "baseline", "yield"),
    ("02-spin-a", "mitigated", "spin"),
    ("03-spin-b", "mitigated", "spin"),
    ("04-yield-control-b", "baseline", "yield"),
]
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
            by_name["02-spin-a"][section][key]
            < by_name["01-yield-control-a"][section][key],
            by_name["03-spin-b"][section][key]
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
            by_name["02-spin-a"][section][key]
            <= by_name["01-yield-control-a"][section][key],
            by_name["03-spin-b"][section][key]
            <= by_name["04-yield-control-b"][section][key],
        )
    )


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
        for name in ("01-yield-control-a", "04-yield-control-b")
    )
    spin_phase_present = timing_complete and all(
        "poll_wait_spin" in timing_by_name[name]["schema"]["phases"]
        and "poll_wait_switch_to_thread"
        not in timing_by_name[name]["schema"]["phases"]
        for name in ("02-spin-a", "03-spin-b")
    )
    spin_wait_under_30ms = timing_complete and all(
        timing_by_name[name]["timing"]["phase_max_ms"].get(
            "poll_wait_spin",
            float("inf"),
        )
        <= TIMING.STALL_THRESHOLD_MS
        for name in ("02-spin-a", "03-spin-b")
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
    spin = summarize_group(scenarios, "mitigated")
    spin_scenarios = [
        by_name[name] for name in ("02-spin-a", "03-spin-b")
        if name in by_name
    ]
    spin_complete = (
        len(spin_scenarios) == 2
        and all(row["checks"]["pipeline_complete"] for row in spin_scenarios)
        and spin["dropped"] == 0
        and spin["write_errors"] == 0
    )
    zero_write_errors = (
        baseline["write_errors"] == 0 and spin["write_errors"] == 0
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
            spin["dropped"] <= baseline["dropped"],
            spin["write_errors"] <= baseline["write_errors"],
            underruns_reduced,
        )
    )
    spin_zero_underrun = (
        len(spin_scenarios) == 2
        and all(
            row["bridge"]["driver_underruns_source_window"] == 0
            for row in spin_scenarios
        )
    )
    confirmed = all(
        (
            complete_evidence,
            control_phase_preserved,
            spin_phase_present,
            spin_complete,
            zero_write_errors,
            spin_wait_under_30ms,
            capture_gaps_reduced,
            underruns_reduced,
            no_impact_regression,
        )
    )
    if not complete_evidence:
        classification = "capture_spin_evidence_incomplete"
    elif not confirmed:
        classification = "capture_spin_not_confirmed"
    elif spin_zero_underrun:
        classification = "capture_spin_completed_without_underruns"
    else:
        classification = "capture_spin_reduced_gaps_and_underruns"

    return {
        "status": "completed",
        "classification": classification,
        "scenarios": scenarios,
        "capture_timing": timing_by_name,
        "baseline": baseline,
        "spin": spin,
        "checks": {
            "complete_evidence": complete_evidence,
            "abba_order": order_ok,
            "fixed_configuration": configs_ok,
            "control_switch_phase_preserved": control_phase_preserved,
            "spin_phase_present": spin_phase_present,
            "spin_zero_drop": spin_complete,
            "zero_write_errors": zero_write_errors,
            "spin_wait_under_30ms": spin_wait_under_30ms,
            "capture_gaps_reduced_reproducibly": capture_gaps_reduced,
            "underruns_reduced_reproducibly": underruns_reduced,
            "no_writer_scheduler_transport_regression": (
                no_impact_regression
            ),
            "spin_zero_underrun": spin_zero_underrun,
            "spin_confirmed": confirmed,
            "listening_unlocked": confirmed and spin_zero_underrun,
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
        raise ValueError("capture spin gate requires four scenarios")
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
