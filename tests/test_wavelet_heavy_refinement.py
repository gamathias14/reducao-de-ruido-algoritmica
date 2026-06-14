from __future__ import annotations

import unittest

import pandas as pd

from benchmark_audio.run_refinement import Condition
from benchmark_audio.run_wavelet_heavy_refinement import (
    add_selection_score,
    heavy_wavelet_candidates,
    select_for_full_validation,
    select_screening_conditions,
)


class WaveletHeavyRefinementTests(unittest.TestCase):
    def test_quick_profile_contains_separate_wavelet_families(self) -> None:
        candidates = heavy_wavelet_candidates("quick")

        families = {candidate.family for candidate in candidates}
        self.assertIn("dwt_wavelet_heavy", families)
        self.assertIn("wpt_coeff_wiener", families)
        self.assertIn("wpt_frame_wiener", families)
        self.assertIn(
            "wavelet_packet_wiener_frames",
            {candidate.method for candidate in candidates},
        )

    def test_screening_conditions_stay_inside_validation_subset(self) -> None:
        conditions = [
            Condition(
                split="validation",
                speaker=speaker,
                noise_name=f"{group.lower()}_seg{index}",
                noise_group=group,
                snr_target_db=snr,
                clean=None,  # type: ignore[arg-type]
                noisy=None,  # type: ignore[arg-type]
                input_snr_db=0.0,
                input_si_sdr_db=0.0,
            )
            for speaker in ("a", "b")
            for group in ("G1", "G2")
            for index in (1, 2)
            for snr in (-5, 0)
        ]

        selected = select_screening_conditions(
            conditions,
            speaker_count=1,
            noises_per_group=1,
        )

        self.assertEqual({condition.speaker for condition in selected}, {"a"})
        self.assertEqual({condition.noise_name for condition in selected}, {"g1_seg1", "g2_seg1"})
        self.assertEqual(len(selected), 4)

    def test_selection_score_penalizes_negative_tail_and_degradation(self) -> None:
        rows = pd.DataFrame(
            [
                {
                    "candidate_id": "stable",
                    "family": "w",
                    "snr_improvement_mean_db": 0.8,
                    "si_sdr_improvement_mean_db": 0.5,
                    "snr_improvement_min_db": -0.1,
                    "snr_degradation_fraction": 0.0,
                },
                {
                    "candidate_id": "fragile",
                    "family": "w",
                    "snr_improvement_mean_db": 1.0,
                    "si_sdr_improvement_mean_db": -0.5,
                    "snr_improvement_min_db": -2.0,
                    "snr_degradation_fraction": 0.5,
                },
            ]
        )

        scored = add_selection_score(rows).set_index("candidate_id")

        self.assertGreater(scored.loc["stable", "selection_score"], scored.loc["fragile", "selection_score"])

    def test_full_validation_keeps_score_and_snr_candidates(self) -> None:
        candidates = heavy_wavelet_candidates("quick")
        rows = pd.DataFrame(
            [
                {
                    "candidate_id": candidates[0].candidate_id,
                    "family": candidates[0].family,
                    "selection_score": 0.0,
                    "snr_improvement_mean_db": 10.0,
                    "si_sdr_improvement_mean_db": 0.0,
                },
                {
                    "candidate_id": candidates[1].candidate_id,
                    "family": candidates[1].family,
                    "selection_score": 10.0,
                    "snr_improvement_mean_db": 0.0,
                    "si_sdr_improvement_mean_db": 0.0,
                },
            ]
        )

        selected = select_for_full_validation(rows, candidates, per_family=1)

        self.assertEqual(
            {candidate.candidate_id for candidate in selected},
            {candidates[0].candidate_id, candidates[1].candidate_id},
        )


if __name__ == "__main__":
    unittest.main()
