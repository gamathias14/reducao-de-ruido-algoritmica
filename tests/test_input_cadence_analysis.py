from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_input_cadence_runs.py"
)
SPEC = importlib.util.spec_from_file_location("input_cadence_analysis", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InputCadenceAnalysisTests(unittest.TestCase):
    def test_classification_rejects_bad_duration_and_clock(self) -> None:
        classification = MODULE.classify(
            {
                "delivered_vs_stream_wall_ratio": 1.30,
                "frame_size_mismatch_count": 0,
                "status_counts": {},
                "callback_interval_ms_max": 60.0,
                "adc_delta_nonpositive_count": 1,
                "current_time_delta_nonpositive_count": 0,
            }
        )

        self.assertFalse(classification["time_preserving_within_2_percent"])
        self.assertFalse(classification["adc_timestamp_monotonic"])
        self.assertTrue(classification["framing_preserved"])

    def test_classification_accepts_temporally_clean_scenario(self) -> None:
        classification = MODULE.classify(
            {
                "delivered_vs_stream_wall_ratio": 1.001,
                "frame_size_mismatch_count": 0,
                "status_counts": {},
                "callback_interval_ms_max": 45.0,
                "adc_delta_nonpositive_count": 0,
                "current_time_delta_nonpositive_count": 0,
            }
        )

        self.assertTrue(all(classification.values()))


if __name__ == "__main__":
    unittest.main()
