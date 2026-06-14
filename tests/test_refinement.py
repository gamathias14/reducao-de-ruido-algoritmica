from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from benchmark_audio.run_refinement import (
    FINAL_NOISE_GROUPS,
    FINAL_SPEAKERS,
    VALIDATION_NOISE_GROUPS,
    VALIDATION_SPEAKERS,
    remove_guaranteed_initial_silence,
    select_candidates,
    wavelet_packet_candidates,
)


class RefinementProtocolTests(unittest.TestCase):
    def test_validation_and_final_groups_are_disjoint(self) -> None:
        self.assertTrue(set(VALIDATION_SPEAKERS).isdisjoint(FINAL_SPEAKERS))
        self.assertTrue(set(VALIDATION_NOISE_GROUPS).isdisjoint(FINAL_NOISE_GROUPS))

    def test_remove_initial_silence_preserves_length_and_starts_with_signal(self) -> None:
        sample_rate = 100
        clean = np.concatenate(
            [
                np.zeros(30, dtype=np.float32),
                np.linspace(0.1, 0.8, 70, dtype=np.float32),
            ]
        )

        result = remove_guaranteed_initial_silence(clean, sample_rate, trim_s=0.30)

        self.assertEqual(result.shape, clean.shape)
        self.assertGreater(abs(float(result[0])), 0.0)
        self.assertTrue(np.all(np.isfinite(result)))

    def test_candidate_selection_is_independent_by_family(self) -> None:
        rows = pd.DataFrame(
            [
                {
                    "candidate_id": "a1",
                    "family": "a",
                    "snr_improvement_mean_db": 1.0,
                    "si_sdr_improvement_mean_db": 1.0,
                    "snr_degradation_fraction": 0.0,
                    "rtf_mean": 0.1,
                },
                {
                    "candidate_id": "a2",
                    "family": "a",
                    "snr_improvement_mean_db": 2.0,
                    "si_sdr_improvement_mean_db": 0.0,
                    "snr_degradation_fraction": 0.0,
                    "rtf_mean": 0.2,
                },
                {
                    "candidate_id": "b1",
                    "family": "b",
                    "snr_improvement_mean_db": 3.0,
                    "si_sdr_improvement_mean_db": 1.0,
                    "snr_degradation_fraction": 0.0,
                    "rtf_mean": 0.1,
                },
            ]
        )

        selected = select_candidates(rows)

        self.assertEqual(set(selected["candidate_id"]), {"a2", "b1"})

    def test_wavelet_packet_candidates_use_separate_family_and_method(self) -> None:
        candidates = wavelet_packet_candidates()

        self.assertGreater(len(candidates), 0)
        self.assertEqual({candidate.family for candidate in candidates}, {"wavelet_packet"})
        self.assertEqual(
            {candidate.method for candidate in candidates},
            {"wavelet_packet_wiener"},
        )
        self.assertTrue(
            all(candidate.candidate_id.startswith("wpt_wiener_") for candidate in candidates)
        )


if __name__ == "__main__":
    unittest.main()
