from __future__ import annotations

import unittest

import numpy as np

from scripts.audio.play_controlled_signal import build_signal


class ControlledSignalTests(unittest.TestCase):
    def test_continuous_signal_has_no_zero_interval_and_respects_peak(self) -> None:
        signal = build_signal(2.0, 48_000, 0.1, mode="continuous")

        self.assertEqual(signal.shape, (96_000, 2))
        self.assertAlmostEqual(float(np.max(np.abs(signal))), 0.1, places=6)
        frame_energy = np.abs(signal[:, 0])
        self.assertGreater(float(np.percentile(frame_energy, 5)), 1e-4)

    def test_invalid_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_signal(1.0, 48_000, 0.1, mode="desconhecido")

    def test_quality_matrix_is_deterministic_and_segmented(self) -> None:
        first = build_signal(10.0, 48_000, 0.1, mode="quality-matrix")
        second = build_signal(10.0, 48_000, 0.1, mode="quality-matrix")

        np.testing.assert_array_equal(first, second)
        self.assertLessEqual(float(np.max(np.abs(first))), 0.1)
        self.assertGreater(float(np.max(np.abs(first))), 0.07)
        silence_rms = float(np.sqrt(np.mean(np.square(first[: 48_000, 0]))))
        noise_rms = float(
            np.sqrt(np.mean(np.square(first[120_000:168_000, 0])))
        )
        active_rms = float(
            np.sqrt(np.mean(np.square(first[240_000:336_000, 0])))
        )
        self.assertLess(silence_rms, 1e-8)
        self.assertGreater(noise_rms, 1e-4)
        self.assertGreater(active_rms, noise_rms * 10.0)


if __name__ == "__main__":
    unittest.main()
