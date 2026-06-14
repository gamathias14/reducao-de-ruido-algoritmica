from __future__ import annotations

import unittest

import numpy as np

from benchmark_audio.causal import (
    CausalNoiseConfig,
    CausalNoiseEstimator,
    CausalProcessorConfig,
    CausalSTFTProcessor,
)


class CausalNoiseEstimatorTests(unittest.TestCase):
    def test_silence_is_finite_and_numerically_protected(self) -> None:
        estimator = CausalNoiseEstimator(
            CausalNoiseConfig(n_fft=32, hop_length=8, warmup_ms=2.0, history_ms=8.0)
        )

        for _ in range(8):
            diagnostics = estimator.update(np.zeros(17, dtype=np.float32))

        self.assertTrue(diagnostics["ready"])
        self.assertTrue(np.all(np.isfinite(estimator.estimate_power)))
        self.assertTrue(np.all(estimator.estimate_power > 0.0))

    def test_calibration_freezes_after_initial_frames(self) -> None:
        config = CausalNoiseConfig(
            sample_rate=1_000,
            n_fft=16,
            hop_length=4,
            mode="calibration",
            calibration_ms=24.0,
        )
        estimator = CausalNoiseEstimator(config)
        for _ in range(config.calibration_frames):
            estimator.update(np.ones(9, dtype=np.float32))
        frozen = estimator.estimate_power.copy()

        for _ in range(10):
            estimator.update(np.full(9, 100.0, dtype=np.float32))

        self.assertTrue(estimator.ready)
        self.assertTrue(np.allclose(estimator.estimate_power, frozen))

    def test_continuous_speech_uses_slow_update(self) -> None:
        config = CausalNoiseConfig(
            sample_rate=1_000,
            n_fft=16,
            hop_length=4,
            warmup_ms=24.0,
            history_ms=80.0,
            speech_threshold_db=3.0,
            low_energy_alpha=0.3,
            speech_alpha=0.0,
        )
        estimator = CausalNoiseEstimator(config)
        noise = np.ones(9, dtype=np.float32)
        for _ in range(config.warmup_frames):
            estimator.update(noise)
        before = estimator.estimate_power.copy()

        speech = np.ones(9, dtype=np.float32)
        speech[2:5] = 100.0
        diagnostics = estimator.update(speech)

        self.assertTrue(diagnostics["speech_probable"])
        self.assertEqual(diagnostics["update_alpha"], 0.0)
        self.assertTrue(np.allclose(estimator.estimate_power, before))

    def test_noise_step_is_tracked_after_old_history_expires(self) -> None:
        config = CausalNoiseConfig(
            sample_rate=1_000,
            n_fft=16,
            hop_length=4,
            warmup_ms=24.0,
            history_ms=40.0,
            noise_quantile=0.2,
            speech_threshold_db=20.0,
            low_energy_alpha=0.5,
        )
        estimator = CausalNoiseEstimator(config)
        for _ in range(config.history_frames):
            estimator.update(np.ones(9, dtype=np.float32))
        before = float(np.mean(estimator.estimate_power))

        for _ in range(config.history_frames * 2):
            estimator.update(np.full(9, 9.0, dtype=np.float32))
        after = float(np.mean(estimator.estimate_power))

        self.assertGreater(after, before * 4.0)


class CausalSTFTProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = CausalProcessorConfig(
            sample_rate=1_000,
            method="stft_subtraction",
            n_fft=32,
            hop_length=8,
            warmup_ms=48.0,
            history_ms=96.0,
            noise_quantile=0.2,
        )

    def test_short_blocks_keep_shape_and_finite_output(self) -> None:
        processor = CausalSTFTProcessor(self.config)
        rng = np.random.default_rng(3527)

        for size in (1, 3, 5, 7, 11):
            block = rng.normal(scale=0.05, size=size).astype(np.float32)
            output, diagnostics = processor.process_block(block)
            self.assertEqual(output.shape, block.shape)
            self.assertTrue(np.all(np.isfinite(output)))
            self.assertGreater(diagnostics["state_memory_bytes"], 0)

    def test_bypass_is_exact_even_above_unit_amplitude(self) -> None:
        processor = CausalSTFTProcessor(
            CausalProcessorConfig(
                sample_rate=1_000,
                method="bypass",
                n_fft=32,
                hop_length=8,
            )
        )
        block = np.linspace(-1.5, 1.5, 20, dtype=np.float32)

        output, _ = processor.process_block(block)

        self.assertTrue(np.array_equal(output, block))

    def test_reset_makes_processing_deterministic(self) -> None:
        processor = CausalSTFTProcessor(self.config)
        rng = np.random.default_rng(3527)
        blocks = [rng.normal(scale=0.05, size=20).astype(np.float32) for _ in range(12)]

        first = [processor.process_block(block)[0] for block in blocks]
        processor.reset()
        second = [processor.process_block(block)[0] for block in blocks]

        self.assertTrue(np.array_equal(np.concatenate(first), np.concatenate(second)))

    def test_different_future_blocks_do_not_change_shared_prefix(self) -> None:
        first_processor = CausalSTFTProcessor(self.config)
        second_processor = CausalSTFTProcessor(self.config)
        rng = np.random.default_rng(3527)
        prefix = [rng.normal(scale=0.05, size=20).astype(np.float32) for _ in range(10)]

        first_prefix = [first_processor.process_block(block)[0] for block in prefix]
        second_prefix = [second_processor.process_block(block)[0] for block in prefix]
        first_processor.process_block(np.ones(20, dtype=np.float32))
        second_processor.process_block(-np.ones(20, dtype=np.float32))

        self.assertTrue(
            np.array_equal(np.concatenate(first_prefix), np.concatenate(second_prefix))
        )

    def test_gain_smoothing_is_causal_and_resettable(self) -> None:
        config = CausalProcessorConfig(
            sample_rate=1_000,
            method="stft_subtraction",
            n_fft=32,
            hop_length=8,
            warmup_ms=48.0,
            history_ms=96.0,
            gain_smoothing=0.8,
        )
        processor = CausalSTFTProcessor(config)
        rng = np.random.default_rng(3527)
        blocks = [rng.normal(scale=0.05, size=20).astype(np.float32) for _ in range(12)]

        first = [processor.process_block(block)[0] for block in blocks]
        processor.reset()
        second = [processor.process_block(block)[0] for block in blocks]

        self.assertTrue(np.array_equal(np.concatenate(first), np.concatenate(second)))

    def test_invalid_gain_smoothing_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CausalSTFTProcessor(
                CausalProcessorConfig(gain_smoothing=1.0)
            )


if __name__ == "__main__":
    unittest.main()
