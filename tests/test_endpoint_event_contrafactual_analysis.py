from __future__ import annotations

import csv
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
    / "analyze_endpoint_event_contrafactual.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_endpoint_event_contrafactual",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


FIELDS = [
    "schema_version",
    "event_index",
    "endpoint_id",
    "wait_qpc_start",
    "wait_qpc_end",
    "wait_duration_ms",
    "wait_result",
    "signal_qpc",
    "previous_signal_qpc",
    "signal_interval_ms",
    "packets_drained",
    "frames_drained",
    "wasapi_flags",
    "reference_period_ms",
    "late_threshold_ms",
    "delay_periods",
]


def write_leg(
    root: Path,
    name: str,
    role: str,
    intervals: list[float],
    *,
    period_ms: float = 10.0,
    timeout: int = 0,
) -> None:
    path = root / name
    path.mkdir()
    endpoint_id = f"endpoint-{role}"
    rows = []
    qpc = 1_000_000
    missed = 0
    late_count = 0
    for index, interval in enumerate(intervals, start=1):
        start = qpc
        end = start + round(interval * 10_000)
        qpc = end
        late = interval > max(30.0, 2.5 * period_ms)
        late_count += int(late)
        if late:
            missed += max(0, round(interval / period_ms) - 1)
        rows.append(
            {
                "schema_version": 1,
                "event_index": index,
                "endpoint_id": endpoint_id,
                "wait_qpc_start": start,
                "wait_qpc_end": end,
                "wait_duration_ms": f"{interval:.6f}",
                "wait_result": (
                    "timeout" if index <= timeout else "signaled"
                ),
                "signal_qpc": end,
                "previous_signal_qpc": start,
                "signal_interval_ms": f"{interval:.6f}",
                "packets_drained": 1,
                "frames_drained": 480,
                "wasapi_flags": 0,
                "reference_period_ms": period_ms,
                "late_threshold_ms": max(30.0, 2.5 * period_ms),
                "delay_periods": interval / period_ms,
            }
        )
    with (path / "event_trace.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": "completed",
        "endpoint_role": role,
        "endpoint": {"id": endpoint_id, "friendly_name": role},
        "mix_format": {
            "format_tag": 3,
            "channels": 2,
            "sample_rate_hz": 48000,
            "bits_per_sample": 32,
            "valid_bits_per_sample": 32,
            "block_align": 8,
            "avg_bytes_per_second": 384000,
            "channel_mask": 3,
            "subformat": "float",
        },
        "device_period": {"default_ms": period_ms, "minimum_ms": 3.0},
        "buffer_frames": 960,
        "qpc_frequency_hz": 10_000_000,
        "duration_seconds": 40.0,
        "waits": len(rows),
        "signals": len(rows) - timeout,
        "timeouts": timeout,
        "wait_failures": 0,
        "packets_drained": len(rows),
        "frames_drained": len(rows) * 480,
        "silent_packets": 0,
        "discontinuities": 0,
        "timestamp_errors": 0,
        "wait_ms": {"mean": 10.0, "p95": 10.0, "p99": 10.0, "max": 10.0},
        "signal_interval_ms": {
            "mean": 10.0,
            "p95": 10.0,
            "p99": 10.0,
            "max": max(intervals),
            "median": 10.0,
        },
        "reference_period_ms": period_ms,
        "late_threshold_ms": max(30.0, 2.5 * period_ms),
        "late_signal_count": late_count,
        "missed_period_equivalents": missed,
    }
    (path / "summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    (path / "scheduler.json").write_text(
        json.dumps({"status": "completed", "samples": []}),
        encoding="utf-8",
    )


class EndpointEventContrafactualTests(unittest.TestCase):
    def build_matrix(
        self,
        root: Path,
        *,
        sysvad: list[float],
        hda: list[float],
    ) -> None:
        for name, role in MODULE.EXPECTED_ORDER:
            write_leg(root, name, role, sysvad if role == "sysvad" else hda)

    def test_classifies_sysvad_specific_only_with_two_clean_hda_legs(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_matrix(root, sysvad=[10.0, 80.0], hda=[10.0, 10.0])
            result = MODULE.analyze(root, root / "result.json")

        self.assertEqual(
            result["classification"],
            "sysvad_event_path_specific",
        )
        self.assertTrue(result["checks"]["hda_clean_both"])
        self.assertTrue(result["checks"]["sysvad_late_both"])

    def test_classifies_comparable_late_events_as_virtualbox_supported(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_matrix(
                root,
                sysvad=[10.0, 100.0],
                hda=[10.0, 80.0],
            )
            result = MODULE.analyze(root, root / "result.json")

        self.assertEqual(
            result["classification"],
            "virtualbox_event_timing_supported",
        )
        self.assertTrue(
            result["checks"]["comparable_order_of_magnitude"]
        )

    def test_keeps_single_hda_outlier_inconclusive(self) -> None:
        legs = [
            {
                "scenario": name,
                "endpoint_role": role,
                "late_signal_count": (
                    1 if role == "sysvad" or name.endswith("-a") else 0
                ),
                "timeouts": 0,
                "wait_failures": 0,
                "max_delay_periods": 8.0,
                "checks": {"complete": True},
            }
            for name, role in MODULE.EXPECTED_ORDER
        ]
        classification, _ = MODULE.classify(legs)
        self.assertEqual(classification, "mixed_or_inconclusive")

    def test_rejects_summary_trace_disagreement(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_matrix(root, sysvad=[10.0, 80.0], hda=[10.0, 10.0])
            path = root / "01-sysvad-shared-event-a" / "summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["late_signal_count"] = 0
            path.write_text(json.dumps(summary), encoding="utf-8")
            result = MODULE.analyze(root, root / "result.json")

        self.assertEqual(result["classification"], "mixed_or_inconclusive")
        self.assertFalse(result["checks"]["complete_evidence"])

    def test_rejects_signal_counter_disagreement(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_matrix(root, sysvad=[10.0, 80.0], hda=[10.0, 10.0])
            path = root / "02-hda-shared-event-a" / "summary.json"
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["signals"] -= 1
            path.write_text(json.dumps(summary), encoding="utf-8")
            result = MODULE.analyze(root, root / "result.json")

        self.assertFalse(result["checks"]["complete_evidence"])

    def test_period_normalization_avoids_absolute_duration_comparison(
        self,
    ) -> None:
        slow = [
            {"max_delay_periods": 4.0},
            {"max_delay_periods": 5.0},
        ]
        fast = [
            {"max_delay_periods": 8.0},
            {"max_delay_periods": 9.0},
        ]
        self.assertTrue(MODULE.comparable_order_of_magnitude(slow, fast))
        fast[1]["max_delay_periods"] = 30.0
        self.assertFalse(MODULE.comparable_order_of_magnitude(slow, fast))


if __name__ == "__main__":
    unittest.main()
