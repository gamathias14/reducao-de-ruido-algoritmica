from __future__ import annotations

import unittest

import numpy as np

from benchmark_audio.denoise import (
    DENOISE_METHODS,
    DenoiseConfig,
    estimate_noise_spectrum,
    mix_at_snr,
    process_method,
    snr_db,
)


class DenoiseSanityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = DenoiseConfig(
            sample_rate=16_000,
            n_fft=256,
            hop_length=80,
            noise_estimate_s=0.05,
            wavelet_level=3,
        )
        self.rng = np.random.default_rng(3527)
        t = np.arange(0, 0.25, 1 / self.config.sample_rate, dtype=np.float32)
        self.clean = (0.6 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        self.noise = self.rng.normal(scale=0.3, size=len(self.clean)).astype(np.float32)

    def test_mix_at_snr_reaches_requested_level(self) -> None:
        noisy, scaled_noise = mix_at_snr(self.clean, self.noise, snr_db_value=0.0)

        self.assertEqual(noisy.shape, self.clean.shape)
        self.assertEqual(scaled_noise.shape, self.clean.shape)
        self.assertAlmostEqual(snr_db(self.clean, noisy), 0.0, delta=0.05)

    def test_denoise_methods_return_finite_same_length_audio(self) -> None:
        noisy, _ = mix_at_snr(self.clean, self.noise, snr_db_value=0.0)

        for method in DENOISE_METHODS:
            with self.subTest(method=method):
                processed, elapsed = process_method(method, noisy, self.config)

                self.assertEqual(processed.dtype, np.float32)
                self.assertEqual(processed.shape, noisy.shape)
                self.assertGreaterEqual(elapsed, 0.0)
                self.assertTrue(np.all(np.isfinite(processed)))

    def test_noisy_method_is_exact_bypass(self) -> None:
        noisy, _ = mix_at_snr(self.clean, self.noise, snr_db_value=0.0)

        processed, _ = process_method("noisy", noisy, self.config)

        self.assertTrue(np.array_equal(processed, noisy.astype(np.float32)))

    def test_wavelet_packet_wiener_is_registered_separately(self) -> None:
        noisy, _ = mix_at_snr(self.clean, self.noise, snr_db_value=0.0)
        config = DenoiseConfig(
            sample_rate=16_000,
            wpt_wavelet="db4",
            wpt_level=3,
            wpt_noise_window=9,
            wpt_noise_quantile=0.2,
            wpt_gain_floor=0.05,
        )

        processed, elapsed = process_method("wavelet_packet_wiener", noisy, config)

        self.assertIn("wavelet_packet_wiener", DENOISE_METHODS)
        self.assertEqual(processed.dtype, np.float32)
        self.assertEqual(processed.shape, noisy.shape)
        self.assertGreaterEqual(elapsed, 0.0)
        self.assertTrue(np.all(np.isfinite(processed)))

    def test_low_energy_noise_estimator_prefers_quiet_frames(self) -> None:
        values = np.asarray(
            [
                [1.0, 0.1, 2.0, 0.2],
                [1.0, 0.1, 2.0, 0.2],
            ],
            dtype=np.float32,
        )
        config = DenoiseConfig(noise_estimator="low_energy", noise_quantile=0.5)

        estimate = estimate_noise_spectrum(values, config, power_domain=False)

        self.assertEqual(estimate.shape, (2, 1))
        self.assertTrue(np.allclose(estimate, 0.15, atol=1e-6))


if __name__ == "__main__":
    unittest.main()
