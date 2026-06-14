from __future__ import annotations

import unittest

import numpy as np

from realtime_audio.rnnoise_processor import (
    INPUT_BLOCK_SAMPLES,
    RNNoiseRealtimeProcessor,
    TOTAL_ALGORITHMIC_LATENCY_MS,
    default_library_path,
)
from realtime_audio.windows_realtime import (
    RealtimeBlockProcessor,
    RealtimeConfig,
    estimated_algorithmic_latency_ms,
    parse_args,
)


@unittest.skipUnless(default_library_path().is_file(), "DLL RNNoise nao compilada")
class RNNoiseRealtimeProcessorTests(unittest.TestCase):
    @staticmethod
    def _blocks(count: int = 12) -> list[np.ndarray]:
        rng = np.random.default_rng(904)
        return [
            rng.normal(scale=0.08, size=INPUT_BLOCK_SAMPLES).astype(np.float32)
            for _ in range(count)
        ]

    @staticmethod
    def _run(blocks: list[np.ndarray]) -> np.ndarray:
        with RNNoiseRealtimeProcessor() as processor:
            return np.concatenate(
                [processor.process_block(block)[0].copy() for block in blocks]
            )

    def test_preserves_block_length_and_reports_two_native_frames(self) -> None:
        with RNNoiseRealtimeProcessor() as processor:
            output, diagnostics = processor.process_block(
                np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
            )

        self.assertEqual(output.shape, (INPUT_BLOCK_SAMPLES,))
        self.assertEqual(diagnostics["native_frames"], 2)
        self.assertGreater(diagnostics["state_memory_bytes"], 32_688)
        self.assertTrue(np.all(np.isfinite(output)))

    def test_determinism_and_reset_are_bit_exact(self) -> None:
        blocks = self._blocks()
        expected = self._run(blocks)
        repeated = self._run(blocks)
        with RNNoiseRealtimeProcessor() as processor:
            first = np.concatenate(
                [processor.process_block(block)[0].copy() for block in blocks]
            )
            processor.reset()
            after_reset = np.concatenate(
                [processor.process_block(block)[0].copy() for block in blocks]
            )

        self.assertTrue(np.array_equal(expected, repeated))
        self.assertTrue(np.array_equal(first, after_reset))

    def test_future_blocks_do_not_change_prefix(self) -> None:
        prefix = self._blocks(8)
        future_a = self._blocks(4)
        future_b = [
            np.full(INPUT_BLOCK_SAMPLES, 0.4, dtype=np.float32)
            for _ in range(4)
        ]

        output_a = self._run([*prefix, *future_a])
        output_b = self._run([*prefix, *future_b])

        prefix_samples = len(prefix) * INPUT_BLOCK_SAMPLES
        self.assertTrue(
            np.array_equal(output_a[:prefix_samples], output_b[:prefix_samples])
        )

    def test_impulse_delay_includes_rnnoise_and_resamplers(self) -> None:
        impulse = np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
        impulse[0] = 0.5
        blocks = [impulse] + [
            np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32) for _ in range(29)
        ]

        output = self._run(blocks)
        peak_index = int(np.argmax(np.abs(output)))

        self.assertIn(peak_index, range(338, 345))
        self.assertAlmostEqual(
            1000.0 * peak_index / 16_000,
            TOTAL_ALGORITHMIC_LATENCY_MS,
            delta=0.15,
        )

    def test_close_rejects_processing(self) -> None:
        processor = RNNoiseRealtimeProcessor()
        processor.close()

        with self.assertRaisesRegex(RuntimeError, "fechado"):
            processor.process_block(
                np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
            )

    def test_realtime_block_processor_integration_and_cli(self) -> None:
        config = RealtimeConfig(method="rnnoise")
        processor = RealtimeBlockProcessor(config)
        try:
            output, timing = processor.process_block(
                np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
            )
        finally:
            processor.close()

        self.assertEqual(output.shape, (INPUT_BLOCK_SAMPLES,))
        self.assertGreater(timing["state_memory_bytes"], 32_688)
        self.assertEqual(parse_args(["--method", "rnnoise"]).method, "rnnoise")
        self.assertAlmostEqual(
            estimated_algorithmic_latency_ms(config),
            TOTAL_ALGORITHMIC_LATENCY_MS,
        )

    def test_realtime_contract_rejects_other_rate_or_block_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "16 kHz"):
            RealtimeBlockProcessor(
                RealtimeConfig(method="rnnoise", sample_rate=48_000)
            )
        with self.assertRaisesRegex(ValueError, "20 ms"):
            RealtimeBlockProcessor(
                RealtimeConfig(method="rnnoise", block_ms=10.0)
            )


if __name__ == "__main__":
    unittest.main()
