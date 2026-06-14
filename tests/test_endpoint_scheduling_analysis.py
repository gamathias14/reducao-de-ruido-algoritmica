from __future__ import annotations

import csv
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_endpoint_scheduling.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_endpoint_scheduling",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class EndpointSchedulingAnalysisTests(unittest.TestCase):
    def test_classifies_performance_core_affinity_gate(self) -> None:
        scenarios = [
            {
                "group": "baseline",
                "config": {"host_vm_affinity": "all"},
            },
            {
                "group": "mitigated",
                "config": {"host_vm_affinity": "performance"},
            },
        ]
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 0, "driver_underruns_source_window": 8},
                {"dropped": 0, "driver_underruns_source_window": 0},
                True,
            ),
            "performance_core_affinity_completed_without_underruns",
        )
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 0, "driver_underruns_source_window": 8},
                {"dropped": 1, "driver_underruns_source_window": 2},
                False,
            ),
            "performance_core_affinity_not_confirmed",
        )

    def test_classifies_ten_ms_send_lead_gate(self) -> None:
        scenarios = [
            {
                "group": "baseline",
                "config": {"send_lead_ms": 0},
            },
            {
                "group": "mitigated",
                "config": {"send_lead_ms": 10},
            },
        ]
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 0, "driver_underruns_source_window": 7},
                {"dropped": 0, "driver_underruns_source_window": 0},
                True,
            ),
            "ten_ms_send_lead_completed_without_underruns",
        )

    def test_classifies_capture_start_barrier_gate(self) -> None:
        scenarios = [
            {
                "group": "baseline",
                "config": {"capture_start_barrier": False},
            },
            {
                "group": "mitigated",
                "config": {"capture_start_barrier": True},
            },
        ]
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 0, "driver_underruns_source_window": 8},
                {"dropped": 0, "driver_underruns_source_window": 0},
                True,
            ),
            "capture_start_barrier_completed_without_underruns",
        )
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 0, "driver_underruns_source_window": 8},
                {"dropped": 0, "driver_underruns_source_window": 3},
                True,
            ),
            "capture_start_barrier_reduced_but_did_not_zero_underruns",
        )

    def test_classifies_capture_poll_yield_gate(self) -> None:
        scenarios = [
            {
                "group": "baseline",
                "config": {"capture_poll_wait_strategy": "sleep"},
            },
            {
                "group": "mitigated",
                "config": {"capture_poll_wait_strategy": "yield"},
            },
        ]
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 8},
                {"dropped": 0},
                True,
            ),
            "capture_poll_yield_completed_without_drops",
        )
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 8},
                {"dropped": 3},
                False,
            ),
            "capture_poll_yield_reduced_but_did_not_eliminate_drops",
        )
        self.assertEqual(
            MODULE.classify(
                scenarios,
                {"dropped": 8},
                {"dropped": 9},
                False,
            ),
            "capture_poll_yield_did_not_reduce_drops",
        )

    def test_accepts_zero_drop_mitigated_pair(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "run"
            private_root = root / "private"
            run_root.mkdir()
            private_root.mkdir()
            names = [
                ("01-baseline-a", "normal", 5),
                ("02-mitigated-a", "mmcss", 0),
                ("03-mitigated-b", "mmcss", 0),
                ("04-baseline-b", "normal", 4),
            ]
            for name, scheduling, dropped in names:
                run = run_root / name
                private = private_root / name
                run.mkdir()
                private.mkdir()
                write_json(
                    run / "scenario_config.json",
                    {
                        "writer_scheduling": scheduling,
                        "poll_wait_strategy": (
                            "yield" if scheduling == "mmcss" else "sleep"
                        ),
                        "comparison_group": (
                            "mitigated"
                            if scheduling == "mmcss"
                            else "baseline"
                        ),
                        "host_vm_priority": (
                            "High" if scheduling == "mmcss" else "Normal"
                        ),
                        "target_driver_depth": 2,
                        "user_queue_blocks": 4,
                        "poll_interval_ms": 2,
                    },
                )
                write_json(
                    run / "server.json",
                    {
                        "status": "completed",
                        "send_interval_ms_max": 20.5,
                        "interval_stalls_over_30ms": 0,
                        "interval_stalls_over_100ms": 0,
                    },
                )
                sent = 1000 - dropped
                write_json(
                    run / "client.json",
                    {
                        "status": "completed",
                        "receive_interval_ms_max": 40.0,
                        "interval_stalls_over_30ms": 1,
                        "interval_stalls_over_100ms": 0,
                        "bridge": {
                            "submitted": 1000,
                            "sent": sent,
                            "user_queue_dropped_total": dropped,
                            "stop_timeout_dropped": 0,
                            "write_errors": 0,
                            "thread_scheduling_requested": scheduling,
                            "thread_scheduling_applied": True,
                            "thread_scheduling_error": None,
                            "driver_stats": {
                                "blocks_accepted": sent,
                                "blocks_consumed": sent - 1,
                                "queue_depth_blocks": 0,
                                "underruns": 3,
                            },
                            "events": [
                                {
                                    "event": "driver_stats",
                                    "qpc_ns": 999_000_000,
                                    "blocks_consumed": 0,
                                    "underruns": 1,
                                    "queue_depth_blocks": 0,
                                },
                                {
                                    "event": "driver_stats",
                                    "qpc_ns": 1_020_000_000,
                                    "blocks_consumed": 1,
                                    "underruns": 2,
                                    "queue_depth_blocks": 0,
                                },
                                {
                                    "event": "driver_stats",
                                    "qpc_ns": 1_040_000_000,
                                    "blocks_consumed": 2,
                                    "underruns": 3,
                                    "queue_depth_blocks": 0,
                                },
                            ],
                            "loop_samples": [
                                {
                                    "qpc_ns": 1_000_000_000,
                                    "loop_interval_ms": 2.0,
                                    "get_stats_ms": 0.1,
                                    "write_ms": 0.1,
                                    "action": "sent",
                                },
                                {
                                    "qpc_ns": 1_040_000_000,
                                    "loop_interval_ms": 40.0,
                                    "get_stats_ms": 0.1,
                                    "write_ms": 0.0,
                                    "action": "driver_depth_wait",
                                },
                            ],
                        },
                    },
                )
                write_json(
                    run / "client_trace.json",
                    [
                        {
                            "receive_qpc_ns": 1_000_000_000,
                            "receive_interval_ms": 0.0,
                        },
                        {
                            "receive_qpc_ns": 1_040_000_000,
                            "receive_interval_ms": 40.0,
                        }
                    ],
                )
                write_json(
                    private / "scheduler.json",
                    {
                        "status": "completed",
                        "observed_interval_ms_max": 40.0,
                        "gaps_over_30ms": 1,
                        "gaps_over_100ms": 0,
                        "samples": [
                            {
                                "qpc_ns": 1_040_000_000,
                                "interval_ms": 40.0,
                            }
                        ],
                    },
                )
                write_csv(
                    private / "capture_trace.csv",
                    ["elapsed_ms", "qpc_ns"],
                    [
                        {"elapsed_ms": 20, "qpc_ns": 1_020_000_000},
                        {"elapsed_ms": 40, "qpc_ns": 1_040_000_000},
                    ],
                )
                write_csv(
                    private / "capture_poll_trace.csv",
                    ["qpc_ns", "poll_interval_ms"],
                    [
                        {
                            "qpc_ns": 1_002_000_000,
                            "poll_interval_ms": 2.0,
                        },
                        {
                            "qpc_ns": 1_040_000_000,
                            "poll_interval_ms": 38.0,
                        },
                    ],
                )

            result = MODULE.analyze(
                run_root,
                private_root,
                root / "result.json",
            )

        self.assertEqual(
            result["classification"],
            "mitigation_completed_1000_blocks_without_drops",
        )
        self.assertEqual(result["baseline"]["dropped"], 9)
        self.assertEqual(result["mitigated"]["dropped"], 0)
        self.assertTrue(result["checks"]["private_replay_unlocked"])
        self.assertEqual(
            result["baseline"]["driver_underruns_source_window"],
            4,
        )
        self.assertEqual(
            result["mitigated"]["driver_underruns_source_window"],
            4,
        )
        self.assertEqual(
            result["scenarios"][0]["bridge"][
                "writer_gaps_correlated_background"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()
