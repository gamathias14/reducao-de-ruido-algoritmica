from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from benchmark_audio.run_checkpoint46r_stft import (
    BASELINE_ID,
    apply_validation_gates,
    candidate_grid,
    pareto_candidate_ids,
    perceptual_metrics,
)


class Checkpoint46RSTFTTests(unittest.TestCase):
    def test_grid_contains_exactly_six_frozen_arms(self) -> None:
        candidates = candidate_grid()

        self.assertEqual(len(candidates), 6)
        self.assertEqual(
            {candidate.candidate_id for candidate in candidates},
            {
                "E0-S02",
                "E0-S05",
                "E0-W05",
                "E1-S02",
                "E1-S05",
                "E1-W05",
            },
        )
        baseline = next(
            candidate for candidate in candidates
            if candidate.candidate_id == BASELINE_ID
        )
        self.assertEqual(baseline.config.noise_quantile, 0.22)
        self.assertEqual(baseline.config.low_energy_alpha, 0.30)
        self.assertEqual(baseline.config.spectral_floor, 0.02)

    def test_perceptual_metrics_reward_exact_reference(self) -> None:
        rng = np.random.default_rng(3527)
        clean = rng.normal(scale=0.1, size=3_200).astype(np.float32)

        metrics = perceptual_metrics(clean, clean, clean)

        self.assertAlmostEqual(metrics["envelope_correlation"], 1.0)
        self.assertAlmostEqual(metrics["log_spectral_distance_mean_db"], 0.0)
        self.assertAlmostEqual(metrics["band_delta_input_2000_4000_db"], 0.0)
        self.assertAlmostEqual(metrics["band_delta_input_4000_8000_db"], 0.0)

    def test_gates_allow_quality_gain_without_snr_gain(self) -> None:
        summary = pd.DataFrame(
            [
                self._summary_row(BASELINE_ID),
                self._summary_row(
                    "E0-S05",
                    snr=1.01,
                    si_sdr=1.0,
                    tonal=9.5,
                    lsd=1.8,
                ),
            ]
        )

        decisions = apply_validation_gates(summary)
        candidate = decisions[decisions["candidate_id"] == "E0-S05"].iloc[0]

        self.assertTrue(candidate["eligible"])
        self.assertFalse(
            candidate["improvement_evidence"]["snr_gain_at_least_0_05db"]
        )
        self.assertTrue(
            candidate["improvement_evidence"]["tonal_reduction_at_least_2pct"]
        )

    def test_absolute_envelope_gate_is_not_impossible_for_public_baseline(self) -> None:
        baseline = self._summary_row(BASELINE_ID)
        baseline["envelope_correlation_mean"] = 0.94
        candidate = self._summary_row(
            "E0-S05",
            snr=1.1,
            tonal=9.5,
        )
        candidate["envelope_correlation_mean"] = 0.939
        decisions = apply_validation_gates(
            pd.DataFrame([baseline, candidate])
        )

        selected = decisions[decisions["candidate_id"] == "E0-S05"].iloc[0]

        self.assertTrue(
            selected["checks"][
                "envelope_absolute_gate_when_baseline_reaches_0_975"
            ]
        )
        self.assertTrue(selected["checks"]["envelope_loss_at_most_0_005"])

    def test_pareto_selection_excludes_dominated_candidate(self) -> None:
        summary = pd.DataFrame(
            [
                self._summary_row(BASELINE_ID),
                self._summary_row(
                    "strong",
                    snr=1.4,
                    si_sdr=1.3,
                    tonal=8.0,
                    lsd=1.5,
                ),
                self._summary_row(
                    "dominated",
                    snr=1.2,
                    si_sdr=1.1,
                    tonal=9.0,
                    lsd=1.8,
                ),
            ]
        )
        decisions = pd.DataFrame(
            [
                {
                    "candidate_id": BASELINE_ID,
                    "is_baseline": True,
                    "eligible": True,
                },
                {
                    "candidate_id": "strong",
                    "is_baseline": False,
                    "eligible": True,
                },
                {
                    "candidate_id": "dominated",
                    "is_baseline": False,
                    "eligible": True,
                },
            ]
        )

        selected = pareto_candidate_ids(summary, decisions)

        self.assertEqual(selected, ["strong"])

    @staticmethod
    def _summary_row(
        candidate_id: str,
        *,
        snr: float = 1.0,
        si_sdr: float = 1.0,
        tonal: float = 10.0,
        lsd: float = 2.0,
    ) -> dict[str, object]:
        return {
            "split": "validation",
            "candidate_id": candidate_id,
            "estimator_id": "E0",
            "gain_profile_id": "S02",
            "n_conditions": 10,
            "snr_improvement_mean_db": snr,
            "snr_improvement_std_db": 0.1,
            "snr_improvement_min_db": 0.1,
            "snr_degradation_fraction": 0.0,
            "si_sdr_improvement_mean_db": si_sdr,
            "tonal_peak_density_mean": tonal,
            "spectral_flatness_median": 0.1,
            "log_spectral_distance_mean_db": lsd,
            "envelope_correlation_mean": 0.99,
            "band_delta_input_2000_4000_mean_db": -0.2,
            "band_delta_input_4000_8000_mean_db": -0.2,
            "block_p99_max_ms": 1.0,
            "block_worst_max_ms": 2.0,
            "rtf_mean": 0.01,
            "state_memory_max_bytes": 1_024,
        }


if __name__ == "__main__":
    unittest.main()
