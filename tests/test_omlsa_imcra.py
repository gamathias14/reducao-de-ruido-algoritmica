from __future__ import annotations

import unittest

import numpy as np

from benchmark_audio.omlsa_imcra import (
    OMLSAIMCRAConfig,
    OMLSAIMCRAProcessor,
    OMLSAIMCRASpectralProcessor,
    _SubwindowMinimum,
)


class OMLSAIMCRATests(unittest.TestCase):
    def test_published_parameters_are_frozen(self) -> None:
        config = OMLSAIMCRAConfig()

        self.assertEqual(config.n_fft, 512)
        self.assertEqual(config.hop_length, 128)
        self.assertEqual(config.minimum_window_frames, 120)
        self.assertEqual(config.subwindow_frames, 15)
        self.assertEqual(config.subwindow_count, 8)
        self.assertAlmostEqual(config.minimum_gain_db, -25.0)
        self.assertAlmostEqual(config.decision_directed_alpha, 0.92)
        self.assertAlmostEqual(config.noise_bias, 1.47)

    def test_silence_stays_finite(self) -> None:
        processor = OMLSAIMCRASpectralProcessor()
        spectrum = np.zeros(257, dtype=np.complex128)

        for _ in range(200):
            output, diagnostics = processor.process_spectrum(spectrum)

        self.assertTrue(np.all(np.isfinite(output)))
        self.assertTrue(np.all(np.isfinite(processor.noise_power)))
        self.assertGreater(diagnostics["state_memory_bytes"], 0)

    def test_reset_makes_spectral_processing_deterministic(self) -> None:
        rng = np.random.default_rng(3527)
        frames = [
            rng.normal(size=257) + 1j * rng.normal(size=257)
            for _ in range(30)
        ]
        processor = OMLSAIMCRASpectralProcessor()

        first = [processor.process_spectrum(frame)[0] for frame in frames]
        processor.reset()
        second = [processor.process_spectrum(frame)[0] for frame in frames]

        self.assertTrue(np.array_equal(np.stack(first), np.stack(second)))

    def test_stationary_noise_estimate_converges_without_runaway(self) -> None:
        rng = np.random.default_rng(3527)
        processor = OMLSAIMCRASpectralProcessor()
        observed_powers = []

        for _ in range(500):
            spectrum = (
                rng.normal(size=257) + 1j * rng.normal(size=257)
            ) / np.sqrt(2.0)
            observed_powers.append(np.mean(np.square(np.abs(spectrum))))
            processor.process_spectrum(spectrum)

        expected = float(np.mean(observed_powers[-120:]))
        estimated = float(np.mean(processor.noise_power))

        self.assertGreater(estimated, expected * 0.5)
        self.assertLess(estimated, expected * 2.0)

    def test_conditional_gain_is_not_clipped_to_absence_gain(self) -> None:
        rng = np.random.default_rng(3527)
        processor = OMLSAIMCRASpectralProcessor()

        for _ in range(200):
            spectrum = (
                rng.normal(size=257) + 1j * rng.normal(size=257)
            ).astype(np.complex128)
            processor.process_spectrum(spectrum)

        self.assertGreater(float(np.min(processor.last_gain)), 0.0)
        self.assertTrue(np.all(np.isfinite(processor.last_gain)))

    def test_minimum_tracker_uses_current_and_u_minus_one_subwindows(self) -> None:
        config = OMLSAIMCRAConfig(
            n_fft=8,
            hop_length=2,
            minimum_window_frames=6,
            subwindow_frames=2,
        )
        tracker = _SubwindowMinimum(1, config)
        observed = []
        for value in (9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 10.0):
            observed.append(float(tracker.update(np.asarray([value]))[0]))

        self.assertEqual(observed[:6], [9.0, 8.0, 7.0, 6.0, 5.0, 4.0])
        self.assertEqual(observed[6], 4.0)
        self.assertEqual(len(tracker.completed), config.subwindow_count)

    def test_future_spectra_do_not_change_shared_prefix(self) -> None:
        rng = np.random.default_rng(3527)
        prefix = [
            rng.normal(size=257) + 1j * rng.normal(size=257)
            for _ in range(20)
        ]
        first = OMLSAIMCRASpectralProcessor()
        second = OMLSAIMCRASpectralProcessor()

        first_prefix = [first.process_spectrum(frame)[0] for frame in prefix]
        second_prefix = [second.process_spectrum(frame)[0] for frame in prefix]
        first.process_spectrum(np.ones(257, dtype=np.complex128))
        second.process_spectrum(-np.ones(257, dtype=np.complex128))

        self.assertTrue(
            np.array_equal(
                np.stack(first_prefix),
                np.stack(second_prefix),
            )
        )

    def test_file_processor_preserves_shape_and_is_deterministic(self) -> None:
        rng = np.random.default_rng(3527)
        audio = rng.normal(scale=0.05, size=4_801).astype(np.float32)
        processor = OMLSAIMCRAProcessor()

        first, first_diagnostics = processor.process(audio)
        second, _ = processor.process(audio)

        self.assertEqual(first.shape, audio.shape)
        self.assertTrue(np.all(np.isfinite(first)))
        self.assertTrue(np.array_equal(first, second))
        self.assertGreater(first_diagnostics["frame_count"], 0)


if __name__ == "__main__":
    unittest.main()
