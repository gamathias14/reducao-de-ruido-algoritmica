from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_capture_event.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_capture_event",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def scenario(
    name: str,
    group: str,
    strategy: str,
    *,
    capture_gaps: int,
    underruns: int,
    sent: int = 1000,
    dropped: int = 0,
    writer_gaps: int = 0,
    scheduler_gaps: int = 0,
) -> dict[str, Any]:
    return {
        "scenario": name,
        "group": group,
        "config": {
            "writer_scheduling": "normal",
            "poll_wait_strategy": "yield",
            "capture_poll_wait_strategy": strategy,
            "capture_start_barrier": True,
            "send_lead_ms": 0,
            "start_delay_ms": 0,
            "initial_burst_blocks": 2,
            "target_driver_depth": 2,
            "user_queue_blocks": 4,
            "poll_interval_ms": 2,
            "host_vm_priority": "Unchanged",
            "host_vm_affinity": "unchanged",
        },
        "host": {"stalls_over_30ms": 0},
        "guest_receive": {"stalls_over_30ms": 0},
        "bridge": {
            "submitted": 1000,
            "sent": sent,
            "dropped": dropped,
            "write_errors": 0,
            "writer_gaps_over_30ms": writer_gaps,
            "driver_underruns_source_window": underruns,
        },
        "capture": {
            "packet_gaps_over_30ms": capture_gaps,
            "poll_gaps_over_30ms": capture_gaps,
        },
        "scheduler_probe": {"gaps_over_30ms": scheduler_gaps},
        "checks": {
            "client_completed": True,
            "server_completed": True,
            "scheduler_completed": True,
            "thread_scheduling_applied": True,
            "bridge_trace_available": True,
            "capture_trace_available": True,
            "capture_poll_trace_available": True,
            "pipeline_complete": sent == 1000 and dropped == 0,
        },
    }


def timing(strategy: str, failures: int = 0) -> dict[str, Any]:
    phase = (
        "poll_wait_endpoint_event"
        if strategy == "event"
        else "poll_wait_switch_to_thread"
    )
    return {
        "schema": {"phases": [phase]},
        "timing": {
            "phase_max_ms": {phase: 20.1},
            "phase_failure_counts": (
                {phase: failures} if failures else {}
            ),
        },
        "checks": {"complete_schema": True},
    }


def accepted_inputs(
    *,
    event_underruns: tuple[int, int] = (0, 0),
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = [
        scenario(
            "01-yield-control-a",
            "baseline",
            "yield",
            capture_gaps=3,
            underruns=8,
            scheduler_gaps=2,
        ),
        scenario(
            "02-event-a",
            "mitigated",
            "event",
            capture_gaps=0,
            underruns=event_underruns[0],
        ),
        scenario(
            "03-event-b",
            "mitigated",
            "event",
            capture_gaps=1,
            underruns=event_underruns[1],
        ),
        scenario(
            "04-yield-control-b",
            "baseline",
            "yield",
            capture_gaps=4,
            underruns=6,
            scheduler_gaps=2,
        ),
    ]
    traces = {
        row["scenario"]: timing(
            row["config"]["capture_poll_wait_strategy"]
        )
        for row in rows
    }
    return rows, traces


class CaptureEventAnalysisTests(unittest.TestCase):
    def test_unlocks_only_with_zero_event_underruns(self) -> None:
        rows, traces = accepted_inputs()
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_event_completed_without_underruns",
        )
        self.assertTrue(result["checks"]["event_confirmed"])
        self.assertTrue(result["checks"]["listening_unlocked"])

    def test_keeps_listening_blocked_with_reduced_underruns(self) -> None:
        rows, traces = accepted_inputs(event_underruns=(2, 1))
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_event_reduced_gaps_and_underruns",
        )
        self.assertFalse(result["checks"]["listening_unlocked"])

    def test_rejects_event_wait_timeout(self) -> None:
        rows, traces = accepted_inputs()
        traces["02-event-a"] = timing("event", failures=1)
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_event_not_confirmed",
        )
        self.assertFalse(result["checks"]["event_wait_success"])

    def test_rejects_event_drop(self) -> None:
        rows, traces = accepted_inputs()
        rows[1]["bridge"]["sent"] = 999
        rows[1]["bridge"]["dropped"] = 1
        rows[1]["checks"]["pipeline_complete"] = False
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_event_not_confirmed",
        )
        self.assertFalse(result["checks"]["event_zero_drop"])

    def test_correlates_event_waits_with_scheduler_and_writer(self) -> None:
        with TemporaryDirectory() as temporary:
            scenario_root = Path(temporary)
            (scenario_root / "scheduler.json").write_text(
                json.dumps(
                    {
                        "samples": [
                            {"qpc_ns": 1_040_000_000, "interval_ms": 40.0}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (scenario_root / "client.json").write_text(
                json.dumps(
                    {
                        "bridge": {
                            "loop_samples": [
                                {
                                    "qpc_ns": 2_040_000_000,
                                    "loop_interval_ms": 40.0,
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            timing_result = {
                "timing": {
                    "long_events": [
                        {
                            "event_index": 1,
                            "phase": "poll_wait_endpoint_event",
                            "qpc_start_ns": 1_000_000_000,
                            "qpc_end_ns": 1_040_000_000,
                            "duration_ms": 40.0,
                        },
                        {
                            "event_index": 2,
                            "phase": "poll_wait_endpoint_event",
                            "qpc_start_ns": 3_000_000_000,
                            "qpc_end_ns": 3_040_000_000,
                            "duration_ms": 40.0,
                        },
                    ]
                }
            }
            result = MODULE.correlate_event_waits(
                scenario_root,
                timing_result,
            )

        self.assertEqual(result["scheduler_only"], 1)
        self.assertEqual(result["no_overlap"], 1)
        self.assertEqual(result["writer_only"], 0)


if __name__ == "__main__":
    unittest.main()
