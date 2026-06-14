from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_capture_spin.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_capture_spin",
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
            "sent": 1000,
            "dropped": 0,
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
            "pipeline_complete": True,
        },
    }


def timing(strategy: str, maximum_ms: float = 2.1) -> dict[str, Any]:
    phase = (
        "poll_wait_spin"
        if strategy == "spin"
        else "poll_wait_switch_to_thread"
    )
    return {
        "schema": {"phases": [phase]},
        "timing": {"phase_max_ms": {phase: maximum_ms}},
        "checks": {"complete_schema": True},
    }


def accepted_inputs(
    *,
    spin_underruns: tuple[int, int] = (0, 0),
    spin_scheduler_gaps: tuple[int, int] = (0, 0),
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
            "02-spin-a",
            "mitigated",
            "spin",
            capture_gaps=0,
            underruns=spin_underruns[0],
            scheduler_gaps=spin_scheduler_gaps[0],
        ),
        scenario(
            "03-spin-b",
            "mitigated",
            "spin",
            capture_gaps=1,
            underruns=spin_underruns[1],
            scheduler_gaps=spin_scheduler_gaps[1],
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


class CaptureSpinAnalysisTests(unittest.TestCase):
    def test_unlocks_listening_only_with_zero_spin_underruns(self) -> None:
        rows, traces = accepted_inputs()
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_spin_completed_without_underruns",
        )
        self.assertTrue(result["checks"]["spin_confirmed"])
        self.assertTrue(result["checks"]["listening_unlocked"])

    def test_confirms_reduction_but_keeps_listening_blocked(self) -> None:
        rows, traces = accepted_inputs(spin_underruns=(2, 1))
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_spin_reduced_gaps_and_underruns",
        )
        self.assertTrue(result["checks"]["spin_confirmed"])
        self.assertFalse(result["checks"]["listening_unlocked"])

    def test_rejects_one_sided_scheduler_regression(self) -> None:
        rows, traces = accepted_inputs(spin_scheduler_gaps=(3, 0))
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_spin_not_confirmed",
        )
        self.assertFalse(
            result["checks"]["no_writer_scheduler_transport_regression"]
        )

    def test_rejects_long_spin_wait(self) -> None:
        rows, traces = accepted_inputs()
        traces["02-spin-a"] = timing("spin", 31.0)
        result = MODULE.evaluate_gate(rows, traces)

        self.assertEqual(
            result["classification"],
            "capture_spin_not_confirmed",
        )
        self.assertFalse(result["checks"]["spin_wait_under_30ms"])


if __name__ == "__main__":
    unittest.main()
