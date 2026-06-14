from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "probe_input_cadence.py"
)
SPEC = importlib.util.spec_from_file_location("input_cadence_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InputCadenceProbeTests(unittest.TestCase):
    def test_summary_separates_callback_and_adc_cadence(self) -> None:
        rows = [
            {
                "frames": 320,
                "callback_monotonic_s": 1.000,
                "callback_interval_ms": 0.0,
                "input_adc_time_s": 10.000,
                "adc_delta_ms": float("nan"),
                "current_time_delta_ms": float("nan"),
                "status": "",
                "processing_ms": 0.1,
            },
            {
                "frames": 320,
                "callback_monotonic_s": 1.001,
                "callback_interval_ms": 1.0,
                "input_adc_time_s": 10.020,
                "adc_delta_ms": 20.0,
                "current_time_delta_ms": 20.0,
                "status": "",
                "processing_ms": 0.2,
            },
            {
                "frames": 320,
                "callback_monotonic_s": 1.041,
                "callback_interval_ms": 40.0,
                "input_adc_time_s": 10.040,
                "adc_delta_ms": 20.0,
                "current_time_delta_ms": 20.0,
                "status": "input overflow",
                "processing_ms": 21.0,
            },
        ]

        summary = MODULE.summarize_rows(
            rows,
            sample_rate=16_000,
            block_size=320,
            requested_duration_s=0.06,
            stream_wall_s=0.06,
        )

        self.assertEqual(summary["callback_count"], 3)
        self.assertAlmostEqual(summary["delivered_audio_s"], 0.06)
        self.assertEqual(summary["callback_burst_count_under_half_interval"], 1)
        self.assertEqual(summary["callback_stall_count_over_double_interval"], 0)
        self.assertAlmostEqual(summary["adc_delta_ms_mean"], 20.0)
        self.assertEqual(summary["status_counts"], {"input overflow": 1})
        self.assertEqual(summary["adc_delta_nonpositive_count"], 0)
        self.assertEqual(summary["processing_over_block_budget_count"], 1)

    def test_summary_detects_frame_mismatch_and_invalid_adc_clock(self) -> None:
        rows = [
            {
                "frames": 160,
                "callback_monotonic_s": 2.0,
                "callback_interval_ms": 0.0,
                "input_adc_time_s": 0.0,
                "adc_delta_ms": float("nan"),
                "current_time_delta_ms": float("nan"),
                "status": "",
            }
        ]

        summary = MODULE.summarize_rows(
            rows,
            sample_rate=16_000,
            block_size=320,
            requested_duration_s=0.02,
            stream_wall_s=0.02,
        )

        self.assertEqual(summary["frame_size_mismatch_count"], 1)
        self.assertEqual(summary["adc_time_valid_count"], 0)
        self.assertAlmostEqual(summary["delivered_audio_s"], 0.01)

    def test_summary_keeps_backward_and_repeated_clock_events_visible(self) -> None:
        rows = [
            {
                "frames": 320,
                "callback_monotonic_s": 1.0,
                "callback_interval_ms": 0.0,
                "input_adc_time_s": 1.0,
                "adc_delta_ms": float("nan"),
                "current_time_delta_ms": float("nan"),
                "status": "",
            },
            {
                "frames": 320,
                "callback_monotonic_s": 1.02,
                "callback_interval_ms": 20.0,
                "input_adc_time_s": 1.0,
                "adc_delta_ms": 0.0,
                "current_time_delta_ms": 0.0,
                "status": "",
            },
            {
                "frames": 320,
                "callback_monotonic_s": 1.04,
                "callback_interval_ms": 20.0,
                "input_adc_time_s": 0.98,
                "adc_delta_ms": -20.0,
                "current_time_delta_ms": -1.0,
                "status": "",
            },
        ]

        summary = MODULE.summarize_rows(
            rows,
            sample_rate=16_000,
            block_size=320,
            requested_duration_s=0.06,
            stream_wall_s=0.06,
        )

        self.assertEqual(summary["adc_delta_nonpositive_count"], 2)
        self.assertEqual(summary["adc_delta_backward_count"], 1)
        self.assertEqual(summary["adc_delta_repeated_count"], 1)
        self.assertEqual(summary["current_time_delta_nonpositive_count"], 2)


if __name__ == "__main__":
    unittest.main()
