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
    / "analyze_capture_timing.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_capture_timing",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


FIELDS = [
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
]


def write_trace(path: Path, long_phase: str | None = None) -> None:
    rows = []
    start_ns = 1_000_000_000
    phases = sorted(
        MODULE.REQUIRED_PHASES.union({long_phase} if long_phase else set())
    )
    for index, phase in enumerate(phases, start=1):
        duration_ns = 40_000_000 if phase == long_phase else 100_000
        end_ns = start_ns + duration_ns
        rows.append(
            {
                "schema_version": 1,
                "event_index": index,
                "qpc_frequency_hz": 10_000_000,
                "poll_index": 1,
                "packet_index": 1,
                "phase": phase,
                "qpc_start_ns": start_ns,
                "qpc_end_ns": end_ns,
                "duration_ms": f"{duration_ns / 1e6:.6f}",
                "hresult": "0x00000000",
                "packet_frames": 320,
                "bytes": 640,
                "flags": 0,
            }
        )
        start_ns = end_ns
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class CaptureTimingAnalysisTests(unittest.TestCase):
    def test_classifies_wasapi_stall(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace, "get_buffer")
            result = MODULE.analyze_trace(trace)

        self.assertEqual(result["classification"], "stall_inside_wasapi")
        self.assertTrue(result["checks"]["complete_schema"])
        self.assertEqual(result["timing"]["dominant_phase"], "get_buffer")

    def test_classifies_inter_iteration_stall(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace, "inter_iteration")
            result = MODULE.analyze_trace(trace)

        self.assertEqual(
            result["classification"],
            "stall_between_capture_iterations",
        )

    def test_classifies_switch_to_thread_delay(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace, "poll_wait_switch_to_thread")
            result = MODULE.analyze_trace(trace)

        self.assertEqual(
            result["classification"],
            "capture_thread_delayed_inside_switch_to_thread",
        )

    def test_classifies_endpoint_event_delay(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace, "poll_wait_endpoint_event")
            result = MODULE.analyze_trace(trace)

        self.assertEqual(
            result["classification"],
            "capture_wait_delayed_before_endpoint_event_signal",
        )

    def test_counts_endpoint_event_wait_failures(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace)
            with trace.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows.append(
                {
                    **rows[0],
                    "event_index": len(rows) + 1,
                    "phase": "poll_wait_endpoint_event",
                    "hresult": "0x80070102",
                }
            )
            with trace.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            result = MODULE.analyze_trace(trace)

        self.assertEqual(
            result["timing"]["phase_failure_counts"],
            {"poll_wait_endpoint_event": 1},
        )

    def test_leaf_wait_phase_precedes_longer_aggregate_interval(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace)
            with trace.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows.extend(
                [
                    {
                        **rows[0],
                        "event_index": len(rows) + 1,
                        "phase": "inter_iteration",
                        "qpc_start_ns": 2_000_000_000,
                        "qpc_end_ns": 2_035_000_000,
                        "duration_ms": "35.000000",
                    },
                    {
                        **rows[0],
                        "event_index": len(rows) + 2,
                        "phase": "poll_wait_switch_to_thread",
                        "qpc_start_ns": 2_001_000_000,
                        "qpc_end_ns": 2_034_000_000,
                        "duration_ms": "33.000000",
                    },
                ]
            )
            with trace.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            result = MODULE.analyze_trace(trace)

        self.assertEqual(
            result["classification"],
            "capture_thread_delayed_inside_switch_to_thread",
        )

    def test_classifies_unattributed_iteration_stall(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace, "capture_iteration")
            result = MODULE.analyze_trace(trace)

        self.assertEqual(
            result["classification"],
            "stall_inside_unattributed_capture_iteration",
        )

    def test_post_capture_io_does_not_mask_loop_result(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace, "wave_file_write")
            result = MODULE.analyze_trace(trace)

        self.assertEqual(
            result["classification"],
            "no_capture_stall_observed",
        )

    def test_rejects_incomplete_schema(self) -> None:
        with TemporaryDirectory() as temporary:
            trace = Path(temporary) / "capture_timing_trace.csv"
            write_trace(trace)
            with trace.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows = [row for row in rows if row["phase"] != "release_buffer"]
            with trace.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            result = MODULE.analyze_trace(trace)

        self.assertFalse(result["checks"]["complete_schema"])
        self.assertIn(
            "release_buffer",
            result["schema"]["missing_required_phases"],
        )

    def test_gate_preserves_listening_block(self) -> None:
        with TemporaryDirectory() as temporary:
            private_root = Path(temporary)
            for name in ("01-timing-a", "02-timing-b"):
                scenario = private_root / name
                scenario.mkdir()
                write_trace(
                    scenario / "capture_timing_trace.csv",
                    "packet_trace_write",
                )
                (scenario / "scheduler.json").write_text(
                    json.dumps({"samples": []}),
                    encoding="utf-8",
                )
                (scenario / "client.json").write_text(
                    json.dumps({"bridge": {"loop_samples": []}}),
                    encoding="utf-8",
                )
            result = MODULE.analyze(
                private_root,
                private_root / "gate.json",
            )

        self.assertEqual(
            result["classification"],
            "stall_inside_capture_io",
        )
        self.assertTrue(result["checks"]["complete_evidence"])
        self.assertFalse(result["checks"]["listening_unlocked"])

    def test_classifies_process_specific_descheduling(self) -> None:
        with TemporaryDirectory() as temporary:
            private_root = Path(temporary)
            scenario = private_root / "01-timing"
            scenario.mkdir()
            write_trace(
                scenario / "capture_timing_trace.csv",
                "inter_iteration",
            )
            (scenario / "scheduler.json").write_text(
                json.dumps({"samples": []}),
                encoding="utf-8",
            )
            (scenario / "client.json").write_text(
                json.dumps({"bridge": {"loop_samples": []}}),
                encoding="utf-8",
            )
            result = MODULE.analyze(
                private_root,
                private_root / "gate.json",
            )

        self.assertEqual(
            result["classification"],
            "capture_process_specific_descheduling",
        )

    def test_gate_preserves_direct_switch_classification(self) -> None:
        with TemporaryDirectory() as temporary:
            private_root = Path(temporary)
            scenario = private_root / "01-timing"
            scenario.mkdir()
            write_trace(
                scenario / "capture_timing_trace.csv",
                "poll_wait_switch_to_thread",
            )
            (scenario / "scheduler.json").write_text(
                json.dumps({"samples": []}),
                encoding="utf-8",
            )
            (scenario / "client.json").write_text(
                json.dumps({"bridge": {"loop_samples": []}}),
                encoding="utf-8",
            )
            result = MODULE.analyze(
                private_root,
                private_root / "gate.json",
            )

        self.assertEqual(
            result["classification"],
            "capture_thread_delayed_inside_switch_to_thread",
        )


if __name__ == "__main__":
    unittest.main()
