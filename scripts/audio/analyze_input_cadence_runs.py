from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_input_cadence import summarize_rows


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def classify(summary: dict[str, object]) -> dict[str, bool]:
    ratio = float(summary["delivered_vs_stream_wall_ratio"])
    status_counts = dict(summary["status_counts"])
    return {
        "time_preserving_within_2_percent": 0.98 <= ratio <= 1.02,
        "framing_preserved": int(summary["frame_size_mismatch_count"]) == 0,
        "no_portaudio_status": not status_counts,
        "no_callback_pause_over_200_ms": (
            float(summary["callback_interval_ms_max"]) <= 200.0
        ),
        "adc_timestamp_monotonic": (
            int(summary["adc_delta_nonpositive_count"]) == 0
        ),
        "current_timestamp_monotonic": (
            int(summary["current_time_delta_nonpositive_count"]) == 0
        ),
    }


def analyze_run(root: Path) -> dict[str, object]:
    manifest = read_json(root / "matrix_manifest.json")
    duration_s = float(manifest["duration_seconds"])
    sample_rate = int(manifest["sample_rate"])
    block_size = int(manifest["block_size"])
    scenarios: list[dict[str, object]] = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        cadence_path = directory / "cadence.json"
        callback_path = directory / "callbacks.csv"
        if not cadence_path.is_file() or not callback_path.is_file():
            continue
        cadence = read_json(cadence_path)
        rows = read_rows(callback_path)
        method = str(cadence["probe_contract"]["dsp"])
        if method == "none":
            method = "capture_only"
        original_summary = dict(cadence["summary"])
        summary = summarize_rows(
            rows,
            sample_rate=sample_rate,
            block_size=block_size,
            requested_duration_s=duration_s,
            stream_wall_s=float(original_summary["stream_wall_s"]),
        )
        summary["stream_latency_s"] = float(original_summary["stream_latency_s"])
        summary["open_and_close_wall_s"] = float(
            original_summary["open_and_close_wall_s"]
        )
        scenarios.append(
            {
                "name": directory.name,
                "backend": cadence["device"]["hostapi"],
                "device_name": cadence["device"]["name"],
                "method": method,
                "wasapi_auto_convert": cadence["probe_contract"][
                    "wasapi_auto_convert"
                ],
                "summary": summary,
                "classification": classify(summary),
            }
        )
    mode = manifest.get("mode")
    if mode is None:
        mode = (
            "backend"
            if all(
                scenario["method"] == "capture_only"
                for scenario in scenarios
            )
            else "workload"
        )
    return {
        "root": str(root),
        "mode": mode,
        "duration_seconds": duration_s,
        "sample_rate": sample_rate,
        "block_size": block_size,
        "audio_saved": manifest["audio_saved"],
        "scenarios": scenarios,
    }


def backend_decisions(runs: list[dict[str, object]]) -> dict[str, object]:
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for run in runs:
        for scenario in run["scenarios"]:
            grouped[str(scenario["backend"])].append(scenario)

    decisions: dict[str, object] = {}
    for backend, scenarios in sorted(grouped.items()):
        classifications = [
            dict(scenario["classification"])
            for scenario in scenarios
        ]
        workload = [
            scenario
            for scenario in scenarios
            if scenario["method"] in {"bypass", "rnnoise"}
        ]
        decisions[backend] = {
            "scenario_count": len(scenarios),
            "workload_scenario_count": len(workload),
            "all_time_preserving_within_2_percent": all(
                value["time_preserving_within_2_percent"]
                for value in classifications
            ),
            "all_callbacks_below_200_ms": all(
                value["no_callback_pause_over_200_ms"]
                for value in classifications
            ),
            "all_portaudio_timestamps_monotonic": all(
                value["adc_timestamp_monotonic"]
                and value["current_timestamp_monotonic"]
                for value in classifications
            ),
            "eligible_for_bridge_followup": bool(workload)
            and all(
                value["time_preserving_within_2_percent"]
                and value["framing_preserved"]
                and value["no_portaudio_status"]
                and value["no_callback_pause_over_200_ms"]
                for value in (
                    dict(scenario["classification"])
                    for scenario in workload
                )
            ),
        }
    return decisions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_roots", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    runs = [analyze_run(path) for path in args.run_roots]
    result = {
        "contract": {
            "capture_only_first": True,
            "pipeline_modified": False,
            "driver_modified": False,
            "pcm_protocol_modified": False,
            "driver_target_depth_modified": False,
            "local_queue_modified": False,
            "audio_saved": False,
        },
        "runs": runs,
        "backend_decisions": backend_decisions(runs),
        "decision": (
            "no_backend_is_eligible_for_bridge_followup; "
            "keep_rnnoise_non_default_and_endpoint_listening_blocked"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
