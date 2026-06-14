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
    / "analyze_endpoint_stall.py"
)
SPEC = importlib.util.spec_from_file_location("analyze_endpoint_stall", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EndpointStallAnalysisTests(unittest.TestCase):
    def test_classifies_stale_packets_after_driver_consumption_stalls(self) -> None:
        with TemporaryDirectory() as temporary:
            private_root = Path(temporary)
            scenario = private_root / "01-bypass-diagnostic"
            scenario.mkdir()
            client = {
                "status": "completed",
                "audio_duration_s": 1.0,
                "bridge": {
                    "submitted": 100,
                    "sent": 42,
                    "user_queue_dropped_total": 58,
                    "stop_timeout_dropped": 0,
                    "target_driver_depth": 2,
                },
            }
            (scenario / "client.json").write_text(json.dumps(client))
            fields = [
                "elapsed_ms",
                "packet_index",
                "captured_frames",
                "packet_hash",
                "bridge_stats_ok",
                "bridge_accepted",
                "bridge_consumed",
                "bridge_depth",
                "bridge_partial_bytes",
            ]
            with (scenario / "capture_trace.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for index in range(100):
                    consumed = min(index, 40)
                    writer.writerow(
                        {
                            "elapsed_ms": index * 20,
                            "packet_index": index + 1,
                            "captured_frames": (index + 1) * 320,
                            "packet_hash": "stale" if index >= 40 else str(index),
                            "bridge_stats_ok": 1,
                            "bridge_accepted": 42,
                            "bridge_consumed": consumed,
                            "bridge_depth": 2 if index >= 40 else 1,
                            "bridge_partial_bytes": 0,
                        }
                    )

            result = MODULE.analyze(private_root, private_root / "result.json")

        self.assertEqual(
            result["classification"],
            "wavert_dma_stalled_with_stale_packet_reuse",
        )
        self.assertTrue(result["checks"]["driver_queue_stalled"])
        self.assertTrue(result["checks"]["stale_packet_reuse"])

    def test_classifies_capture_window_that_ends_before_replay(self) -> None:
        with TemporaryDirectory() as temporary:
            private_root = Path(temporary)
            scenario = private_root / "01-bypass-diagnostic"
            scenario.mkdir()
            client = {
                "status": "completed",
                "audio_duration_s": 20.0,
                "bridge": {
                    "submitted": 1000,
                    "sent": 447,
                    "user_queue_dropped_total": 549,
                    "stop_timeout_dropped": 4,
                    "target_driver_depth": 2,
                },
            }
            (scenario / "client.json").write_text(json.dumps(client))
            fields = [
                "elapsed_ms", "packet_index", "captured_frames", "packet_hash",
                "bridge_stats_ok", "bridge_accepted", "bridge_consumed",
                "bridge_depth", "bridge_partial_bytes",
            ]
            with (scenario / "capture_trace.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for index in range(1200):
                    active = max(0, index - 750)
                    writer.writerow(
                        {
                            "elapsed_ms": index * 20,
                            "packet_index": index + 1,
                            "captured_frames": (index + 1) * 320,
                            "packet_hash": str(index),
                            "bridge_stats_ok": 1,
                            "bridge_accepted": min(active, 446),
                            "bridge_consumed": min(active, 445),
                            "bridge_depth": 1,
                            "bridge_partial_bytes": 0,
                        }
                    )

            result = MODULE.analyze(private_root, private_root / "result.json")

        self.assertEqual(
            result["classification"],
            "capture_window_ended_before_replay",
        )
        self.assertFalse(result["checks"]["capture_window_covers_source"])

    def test_classifies_transient_scheduling_pauses_with_queue_overflow(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary:
            private_root = Path(temporary)
            scenario = private_root / "01-bypass-diagnostic"
            scenario.mkdir()
            client = {
                "status": "completed",
                "audio_duration_s": 2.0,
                "receive_interval_ms_max": 125.0,
                "bridge": {
                    "submitted": 100,
                    "sent": 94,
                    "user_queue_dropped_total": 6,
                    "stop_timeout_dropped": 0,
                    "target_driver_depth": 2,
                },
            }
            (scenario / "client.json").write_text(json.dumps(client))
            fields = [
                "elapsed_ms", "packet_index", "captured_frames", "packet_hash",
                "bridge_stats_ok", "bridge_accepted", "bridge_consumed",
                "bridge_depth", "bridge_partial_bytes",
            ]
            elapsed = 0
            with (scenario / "capture_trace.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for index in range(130):
                    elapsed += 150 if index == 40 else 20
                    accepted = min(index, 94)
                    writer.writerow(
                        {
                            "elapsed_ms": elapsed,
                            "packet_index": index + 1,
                            "captured_frames": (index + 1) * 320,
                            "packet_hash": str(index),
                            "bridge_stats_ok": 1,
                            "bridge_accepted": accepted,
                            "bridge_consumed": max(0, accepted - 1),
                            "bridge_depth": 1,
                            "bridge_partial_bytes": 0,
                        }
                    )

            result = MODULE.analyze(private_root, private_root / "result.json")

        self.assertEqual(
            result["classification"],
            "transient_scheduling_pauses_with_queue_overflow",
        )
        self.assertTrue(result["checks"]["transient_scheduling_pauses"])


if __name__ == "__main__":
    unittest.main()
