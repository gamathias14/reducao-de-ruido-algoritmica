from __future__ import annotations

import time
import unittest

import numpy as np

from benchmark_audio.causal_wpt import CausalWPTConfig, CausalWPTProcessor


class CausalWPTProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = CausalWPTConfig(
            sample_rate=16_000,
            block_size=320,
            frame_length=640,
            wavelet="haar",
            level=3,
            warmup_blocks=4,
            history_blocks=12,
            noise_quantile=0.20,
            gain_floor=0.20,
        )
        self.rng = np.random.default_rng(3527)

    def blocks(self, count: int) -> list[np.ndarray]:
        return [
            self.rng.normal(scale=0.04, size=self.config.block_size).astype(np.float32)
            for _ in range(count)
        ]

    def test_preserves_shape_and_finiteness(self) -> None:
        processor = CausalWPTProcessor(self.config)
        for block in self.blocks(12):
            output, diagnostics = processor.process_block(block)
            self.assertEqual(output.shape, block.shape)
            self.assertTrue(np.all(np.isfinite(output)))
            self.assertGreater(diagnostics["state_memory_bytes"], 0)

    def test_reset_makes_processing_deterministic(self) -> None:
        processor = CausalWPTProcessor(self.config)
        blocks = self.blocks(12)
        first = [processor.process_block(block)[0] for block in blocks]
        processor.reset()
        second = [processor.process_block(block)[0] for block in blocks]
        self.assertTrue(np.array_equal(np.concatenate(first), np.concatenate(second)))

    def test_future_blocks_do_not_change_shared_prefix(self) -> None:
        first = CausalWPTProcessor(self.config)
        second = CausalWPTProcessor(self.config)
        prefix = self.blocks(10)
        first_prefix = [first.process_block(block)[0] for block in prefix]
        second_prefix = [second.process_block(block)[0] for block in prefix]
        first.process_block(np.ones(self.config.block_size, dtype=np.float32))
        second.process_block(-np.ones(self.config.block_size, dtype=np.float32))
        self.assertTrue(
            np.array_equal(np.concatenate(first_prefix), np.concatenate(second_prefix))
        )

    def test_warmup_is_bypass_and_current_power_updates_only_future(self) -> None:
        processor = CausalWPTProcessor(self.config)
        quiet = np.full(self.config.block_size, 0.01, dtype=np.float32)
        for _ in range(self.config.warmup_blocks):
            output, diagnostics = processor.process_block(quiet)
            self.assertTrue(np.array_equal(output, quiet))
            self.assertTrue(diagnostics["warming_up"])

        history_before = processor._power_history.copy()
        loud = np.full(self.config.block_size, 0.5, dtype=np.float32)
        _, diagnostics = processor.process_block(loud)
        expected = np.quantile(
            history_before[: self.config.warmup_blocks],
            self.config.noise_quantile,
            axis=0,
        )
        self.assertTrue(np.allclose(processor.last_noise_power, expected))
        self.assertFalse(diagnostics["warming_up"])

    def test_memory_is_bounded_after_long_run(self) -> None:
        processor = CausalWPTProcessor(self.config)
        initial = processor.state_memory_bytes
        for block in self.blocks(200):
            processor.process_block(block)
        self.assertEqual(processor.state_memory_bytes, initial)
        self.assertLess(processor.state_memory_bytes, 16 * 1024)

    def test_average_cost_stays_below_block_budget(self) -> None:
        processor = CausalWPTProcessor(self.config)
        blocks = self.blocks(80)
        started = time.perf_counter()
        for block in blocks:
            processor.process_block(block)
        average_ms = 1_000.0 * (time.perf_counter() - started) / len(blocks)
        self.assertLess(average_ms, 20.0)

    def test_partial_last_block_is_preserved(self) -> None:
        processor = CausalWPTProcessor(self.config)
        for block in self.blocks(self.config.warmup_blocks):
            processor.process_block(block)
        partial = self.rng.normal(scale=0.04, size=137).astype(np.float32)
        output, _ = processor.process_block(partial)
        self.assertEqual(output.shape, partial.shape)
        self.assertTrue(np.all(np.isfinite(output)))


if __name__ == "__main__":
    unittest.main()
