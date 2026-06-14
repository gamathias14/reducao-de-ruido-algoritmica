from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def analyze(private_root: Path, output: Path) -> dict[str, Any]:
    scenarios = sorted(
        path for path in private_root.iterdir() if path.is_dir()
    )
    if len(scenarios) != 1:
        raise ValueError("endpoint diagnostic requires exactly one scenario")
    root = scenarios[0]
    client = read_json(root / "client.json")
    with (root / "capture_trace.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "elapsed_ms",
        "packet_index",
        "captured_frames",
        "packet_hash",
        "bridge_stats_ok",
        "bridge_accepted",
        "bridge_consumed",
        "bridge_depth",
        "bridge_partial_bytes",
    }
    missing = required.difference(rows[0] if rows else {})
    if missing:
        raise ValueError(
            "capture trace lacks diagnostic columns: " + ", ".join(sorted(missing))
        )

    valid_stats = [
        row for row in rows if int(row["bridge_stats_ok"]) == 1
    ]
    hashes = Counter(row["packet_hash"] for row in rows)
    capture_times = [int(row["elapsed_ms"]) for row in rows]
    capture_gaps_ms = [
        current - previous
        for previous, current in zip(capture_times, capture_times[1:])
    ]
    max_capture_gap_ms = max(capture_gaps_ms, default=0)
    capture_gaps_over_30ms = sum(gap > 30 for gap in capture_gaps_ms)
    capture_gaps_over_100ms = sum(gap > 100 for gap in capture_gaps_ms)
    final = valid_stats[-1] if valid_stats else {}
    consumed = [int(row["bridge_consumed"]) for row in valid_stats]
    last_progress_index = 0
    for index in range(1, len(consumed)):
        if consumed[index] > consumed[last_progress_index]:
            last_progress_index = index
    packets_after_last_consume = (
        len(valid_stats) - last_progress_index - 1 if valid_stats else 0
    )
    final_depth = int(final.get("bridge_depth", 0))
    final_accepted = int(final.get("bridge_accepted", 0))
    final_consumed = int(final.get("bridge_consumed", 0))
    first_active = next(
        (
            row
            for row in valid_stats
            if int(row["bridge_accepted"]) > 0
        ),
        None,
    )
    capture_elapsed_ms = int(rows[-1]["elapsed_ms"]) if rows else 0
    first_activity_ms = (
        int(first_active["elapsed_ms"]) if first_active is not None else None
    )
    observed_overlap_ms = (
        capture_elapsed_ms - first_activity_ms
        if first_activity_ms is not None
        else 0
    )
    expected_source_ms = round(float(client.get("audio_duration_s", 0.0)) * 1000)
    capture_window_covers_source = (
        first_activity_ms is not None
        and observed_overlap_ms >= expected_source_ms - 500
    )
    client_dropped = (
        int(client["bridge"]["user_queue_dropped_total"])
        + int(client["bridge"].get("stop_timeout_dropped", 0))
    )
    pipeline_complete = (
        int(client["bridge"]["sent"]) == int(client["bridge"]["submitted"])
        and client_dropped == 0
        and final_consumed >= int(client["bridge"]["sent"]) - 1
    )
    repeated_packet_count = max(hashes.values(), default=0)
    capture_continued_after_stall = packets_after_last_consume >= 50
    driver_queue_stalled = (
        capture_continued_after_stall
        and final_depth >= int(client["bridge"]["target_driver_depth"])
        and final_accepted > final_consumed
    )
    transient_scheduling_pauses = (
        client_dropped > 0
        and not driver_queue_stalled
        and (
            max_capture_gap_ms > 100
            or float(client.get("receive_interval_ms_max", 0.0)) > 100.0
        )
    )

    if not capture_window_covers_source and client_dropped > 0:
        classification = "capture_window_ended_before_replay"
    elif pipeline_complete:
        classification = "endpoint_pipeline_complete"
    elif driver_queue_stalled:
        classification = "wavert_dma_stalled_with_stale_packet_reuse"
    elif transient_scheduling_pauses:
        classification = "transient_scheduling_pauses_with_queue_overflow"
    else:
        classification = "incomplete_endpoint_pipeline"

    result = {
        "status": "completed",
        "classification": classification,
        "scenario": root.name,
        "capture": {
            "packets": len(rows),
            "captured_frames": int(rows[-1]["captured_frames"]) if rows else 0,
            "elapsed_ms": capture_elapsed_ms,
            "first_bridge_activity_ms": first_activity_ms,
            "observed_source_overlap_ms": observed_overlap_ms,
            "expected_source_ms": expected_source_ms,
            "max_packet_gap_ms": max_capture_gap_ms,
            "packet_gaps_over_30ms": capture_gaps_over_30ms,
            "packet_gaps_over_100ms": capture_gaps_over_100ms,
            "bridge_stats_samples": len(valid_stats),
            "packets_after_last_consume": packets_after_last_consume,
            "most_repeated_packet_count": repeated_packet_count,
        },
        "bridge": {
            "client_submitted": client["bridge"]["submitted"],
            "client_sent": client["bridge"]["sent"],
            "client_dropped": client_dropped,
            "accepted": final_accepted,
            "consumed": final_consumed,
            "final_depth": final_depth,
            "final_partial_bytes": int(final.get("bridge_partial_bytes", 0)),
        },
        "checks": {
            "client_completed": client.get("status") == "completed",
            "capture_trace_nonempty": bool(rows),
            "bridge_stats_available": bool(valid_stats),
            "capture_continued_after_stall": capture_continued_after_stall,
            "driver_queue_stalled": driver_queue_stalled,
            "stale_packet_reuse": repeated_packet_count >= 50,
            "capture_window_covers_source": capture_window_covers_source,
            "pipeline_complete": pipeline_complete,
            "transient_scheduling_pauses": transient_scheduling_pauses,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.private_root, args.output)
    required = (
        result["checks"]["client_completed"]
        and result["checks"]["capture_trace_nonempty"]
        and result["checks"]["bridge_stats_available"]
    )
    if not required:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
