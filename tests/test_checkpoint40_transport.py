from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_checkpoint40_transport.py"
)
SPEC = importlib.util.spec_from_file_location("checkpoint40_transport", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Checkpoint40TransportTests(unittest.TestCase):
    def test_match_sent_blocks_recovers_inserted_zero_gap(self) -> None:
        rng = np.random.default_rng(3527)
        pre = rng.normal(size=(5, MODULE.BLOCK_SIZE)).astype(np.float32)
        endpoint = np.concatenate(
            [
                np.zeros(37, dtype=np.float32),
                pre[0],
                pre[1],
                np.zeros(93, dtype=np.float32),
                pre[2],
                pre[3],
                pre[4],
            ]
        )
        matches = MODULE.match_sent_blocks(
            pre,
            endpoint,
            [0, 1, 2, 3, 4],
            {index: "active" for index in range(5)},
        )

        self.assertTrue(all(match["preserved"] for match in matches))
        self.assertEqual(matches[0]["endpoint_start_sample"], 37)
        self.assertEqual(
            matches[2]["endpoint_start_sample"],
            37 + 2 * MODULE.BLOCK_SIZE + 93,
        )

    def test_zero_metrics_counts_long_runs_and_transitions(self) -> None:
        samples = np.concatenate(
            [
                np.ones(10, dtype=np.float32),
                np.zeros(MODULE.BLOCK_SIZE, dtype=np.float32),
                np.ones(10, dtype=np.float32),
            ]
        )
        metrics = MODULE.zero_metrics(samples)
        self.assertEqual(metrics["zero_signal_transitions"], 2)
        self.assertEqual(metrics["zero_runs_at_least_20ms"], 1)


if __name__ == "__main__":
    unittest.main()
