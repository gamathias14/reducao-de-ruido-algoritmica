from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_endpoint_vcpu.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_endpoint_vcpu",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_gate(path: Path, dropped: int, gaps: int) -> None:
    path.write_text(
        json.dumps(
            {
                "checks": {"complete_evidence": True},
                "mitigated": {
                    "submitted": 2000,
                    "sent": 2000 - dropped,
                    "dropped": dropped,
                    "writer_gaps_over_30ms": 3,
                    "scheduler_gaps_over_30ms": gaps,
                    "capture_poll_gaps_over_30ms": gaps + 2,
                    "driver_underruns_source_window": gaps + 4,
                    "complete_scenarios": 0,
                },
            }
        ),
        encoding="utf-8",
    )


class EndpointVcpuAnalysisTests(unittest.TestCase):
    def test_classifies_reduction_without_unlocking_replay(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = root / "control.json"
            experiment = root / "experiment.json"
            output = root / "result.json"
            write_gate(control, dropped=38, gaps=54)
            write_gate(experiment, dropped=11, gaps=11)

            result = MODULE.analyze(control, experiment, output)

        self.assertEqual(
            result["classification"],
            "three_vcpu_reduced_pauses_but_zero_drop_not_reached",
        )
        self.assertTrue(result["checks"]["experiment_improved"])
        self.assertFalse(result["checks"]["private_replay_unlocked"])
        self.assertAlmostEqual(
            result["reductions"]["dropped_fraction"],
            27 / 38,
        )


if __name__ == "__main__":
    unittest.main()
