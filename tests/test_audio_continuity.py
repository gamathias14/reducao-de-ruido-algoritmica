from __future__ import annotations

import unittest

import numpy as np

from realtime_audio.audio_continuity import (
    ContinuityThresholds,
    analyze_blocks,
)


class AudioContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.block_size = 320
        time_s = np.arange(self.block_size * 6, dtype=np.float32) / 16_000.0
        signal = 0.2 * np.sin(2.0 * np.pi * 437.5 * time_s)
        self.blocks = [
            block.copy()
            for block in signal.reshape(-1, self.block_size)
        ]
        self.thresholds = ContinuityThresholds(
            sample_jump=0.15,
            boundary_jump=0.15,
            long_zero_samples=160,
        )

    def analyze(self, blocks, **kwargs):
        return analyze_blocks(blocks, thresholds=self.thresholds, **kwargs)

    def test_continuous_signal_has_no_transport_artifact(self) -> None:
        result = self.analyze(self.blocks)

        self.assertEqual(result["missing_block_indices"], [])
        self.assertEqual(result["suspicious_zero_block_indices"], [])
        self.assertEqual(result["repeated_block_indices"], [])
        self.assertEqual(result["boundary_discontinuities"], [])

    def test_zero_block_between_active_blocks_is_suspicious(self) -> None:
        blocks = [block.copy() for block in self.blocks]
        blocks[2].fill(0.0)

        result = self.analyze(blocks)

        self.assertIn(2, result["zero_block_indices"])
        self.assertIn(2, result["suspicious_zero_block_indices"])
        self.assertTrue(
            any(item["block_index"] == 2 for item in result["long_zero_runs"])
        )

    def test_removed_block_is_reported_by_index(self) -> None:
        result = self.analyze(
            self.blocks[:4],
            block_indices=[0, 1, 3, 4],
        )

        self.assertEqual(result["missing_block_indices"], [2])
        self.assertEqual(result["block_count_expected_from_indices"], 5)

    def test_repeated_block_is_reported(self) -> None:
        blocks = [block.copy() for block in self.blocks]
        blocks[3] = blocks[2].copy()

        result = self.analyze(blocks)

        self.assertIn(3, result["repeated_block_indices"])

    def test_amplitude_jump_is_reported(self) -> None:
        blocks = [block.copy() for block in self.blocks]
        blocks[3][0] = 0.9

        result = self.analyze(blocks)

        self.assertTrue(
            any(item["block_index"] == 3 for item in result["boundary_discontinuities"])
        )
        self.assertTrue(
            any(item["block_index"] == 3 for item in result["excessive_sample_jumps"])
        )

    def test_legitimate_silence_is_not_a_suspicious_pop(self) -> None:
        silence = [np.zeros(self.block_size, dtype=np.float32) for _ in range(4)]

        result = self.analyze(silence)

        self.assertEqual(result["zero_block_indices"], [0, 1, 2, 3])
        self.assertEqual(result["suspicious_zero_block_indices"], [])

    def test_callback_cadence_and_status_are_correlated_by_block(self) -> None:
        result = self.analyze(
            self.blocks[:4],
            callback_times_s=[0.00, 0.02, 0.07, 0.09],
            expected_interval_s=0.02,
            status_events=[False, False, True, False],
        )

        self.assertEqual(result["status_event_block_indices"], [2])
        self.assertEqual(result["callback_cadence_outliers"][0]["block_index"], 2)


if __name__ == "__main__":
    unittest.main()
