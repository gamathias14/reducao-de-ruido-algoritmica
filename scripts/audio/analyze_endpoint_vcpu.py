from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def reduction(control: int, experiment: int) -> float:
    if control <= 0:
        return 0.0
    return (control - experiment) / control


def summarize(group: dict[str, Any]) -> dict[str, int]:
    keys = (
        "submitted",
        "sent",
        "dropped",
        "writer_gaps_over_30ms",
        "scheduler_gaps_over_30ms",
        "capture_poll_gaps_over_30ms",
        "driver_underruns_source_window",
        "complete_scenarios",
    )
    return {key: int(group.get(key, 0)) for key in keys}


def analyze(
    control_path: Path,
    experiment_path: Path,
    output_path: Path,
    *,
    control_vcpus: int = 4,
    experiment_vcpus: int = 3,
    rejected_vcpus: int = 2,
) -> dict[str, Any]:
    control_gate = read_json(control_path)
    experiment_gate = read_json(experiment_path)
    control = summarize(control_gate["mitigated"])
    experiment = summarize(experiment_gate["mitigated"])
    zero_drop = (
        experiment["submitted"] == 2000
        and experiment["dropped"] == 0
        and experiment["complete_scenarios"] == 2
    )
    improved = (
        experiment["dropped"] < control["dropped"]
        and experiment["scheduler_gaps_over_30ms"]
        < control["scheduler_gaps_over_30ms"]
        and experiment["capture_poll_gaps_over_30ms"]
        < control["capture_poll_gaps_over_30ms"]
    )
    if zero_drop:
        classification = "three_vcpu_completed_without_drops"
    elif improved:
        classification = (
            "three_vcpu_reduced_pauses_but_zero_drop_not_reached"
        )
    else:
        classification = "three_vcpu_not_confirmed_as_mitigation"
    result = {
        "status": "completed",
        "classification": classification,
        "control": {
            "vcpus": control_vcpus,
            "gate": str(control_path),
            "mitigated": control,
        },
        "experiment": {
            "vcpus": experiment_vcpus,
            "gate": str(experiment_path),
            "mitigated": experiment,
        },
        "rejected_configuration": {
            "vcpus": rejected_vcpus,
            "reason": (
                "guest_boot_did_not_reach_guest_additions_or_network"
            ),
        },
        "reductions": {
            "dropped_fraction": reduction(
                control["dropped"],
                experiment["dropped"],
            ),
            "scheduler_gaps_fraction": reduction(
                control["scheduler_gaps_over_30ms"],
                experiment["scheduler_gaps_over_30ms"],
            ),
            "capture_poll_gaps_fraction": reduction(
                control["capture_poll_gaps_over_30ms"],
                experiment["capture_poll_gaps_over_30ms"],
            ),
            "source_underruns_fraction": reduction(
                control["driver_underruns_source_window"],
                experiment["driver_underruns_source_window"],
            ),
        },
        "checks": {
            "complete_evidence": (
                bool(control_gate["checks"]["complete_evidence"])
                and bool(experiment_gate["checks"]["complete_evidence"])
            ),
            "experiment_improved": improved,
            "experiment_zero_drop": zero_drop,
            "private_replay_unlocked": zero_drop,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.control, args.experiment, args.output)
    if not result["checks"]["complete_evidence"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
