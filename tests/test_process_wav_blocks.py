from __future__ import annotations

import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from benchmark_audio.causal import CausalProcessorConfig, CausalSTFTProcessor
from realtime_audio.process_wav_blocks import (
    CSV_FIELDS,
    block_samples_from_ms,
    main,
    process_samples_in_blocks,
    process_wav_file,
    read_wav_for_processing,
    sha256_file,
)


class ProcessWavBlocksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.sample_rate = 16_000
        rng = np.random.default_rng(3527)
        self.samples = rng.normal(scale=0.1, size=1_013).astype(np.float32)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_input(
        self,
        name: str = "input.wav",
        samples: np.ndarray | None = None,
        sample_rate: int | None = None,
    ) -> Path:
        path = self.root / name
        values = self.samples if samples is None else samples
        wavfile.write(
            path,
            sample_rate or self.sample_rate,
            np.round(np.clip(values, -1.0, 1.0) * 32767.0).astype(np.int16),
        )
        return path

    def _paths(self, stem: str = "run") -> tuple[Path, Path, Path]:
        return (
            self.root / f"{stem}.wav",
            self.root / f"{stem}.json",
            self.root / f"{stem}.csv",
        )

    def test_bypass_is_exact_before_pcm_write(self) -> None:
        output, rows = process_samples_in_blocks(
            self.samples,
            CausalProcessorConfig(method="bypass"),
            20.0,
        )

        self.assertTrue(np.array_equal(output, self.samples))
        self.assertEqual(rows[-1]["end_sample_exclusive"], len(self.samples))

    def test_length_and_last_short_block_are_preserved(self) -> None:
        for length in (960, 1_013):
            with self.subTest(length=length):
                samples = self.samples[:length]
                output, rows = process_samples_in_blocks(
                    samples,
                    CausalProcessorConfig(method="stft_subtraction"),
                    20.0,
                )
                self.assertEqual(len(output), length)
                self.assertEqual(rows[-1]["block_samples"], length % 320 or 320)

    def test_processing_is_deterministic_and_matches_direct_processor(self) -> None:
        config = CausalProcessorConfig(method="stft_subtraction")
        first, _ = process_samples_in_blocks(self.samples, config, 10.0)
        second, _ = process_samples_in_blocks(self.samples, config, 10.0)

        direct = CausalSTFTProcessor(config)
        direct_parts = []
        block_samples = block_samples_from_ms(10.0)
        for start in range(0, len(self.samples), block_samples):
            direct_parts.append(
                direct.process_block(self.samples[start : start + block_samples])[0]
            )

        self.assertTrue(np.array_equal(first, second))
        self.assertTrue(np.array_equal(first, np.concatenate(direct_parts)))

    def test_supported_block_sizes(self) -> None:
        for block_ms, expected in ((10.0, 160), (20.0, 320), (32.0, 512)):
            with self.subTest(block_ms=block_ms):
                output, rows = process_samples_in_blocks(
                    self.samples,
                    CausalProcessorConfig(method="stft_wiener"),
                    block_ms,
                )
                self.assertEqual(len(output), len(self.samples))
                self.assertEqual(rows[0]["block_samples"], expected)

    def test_stereo_resampling_preserves_amplitude_policy(self) -> None:
        source_rate = 8_000
        t = np.arange(800, dtype=np.float32) / source_rate
        left = 0.4 * np.sin(2 * np.pi * 300 * t)
        right = 0.2 * np.sin(2 * np.pi * 300 * t)
        stereo = np.stack([left, right], axis=1)
        path = self._write_input("stereo.wav", stereo, source_rate)

        samples, metadata = read_wav_for_processing(path)

        self.assertEqual(metadata.channels, 2)
        self.assertEqual(metadata.sample_rate, source_rate)
        self.assertEqual(len(samples), 1_600)
        self.assertLess(float(np.max(np.abs(samples))), 0.31)
        self.assertGreater(float(np.max(np.abs(samples))), 0.28)

    def test_invalid_missing_empty_and_truncated_inputs_fail(self) -> None:
        with self.assertRaises(FileNotFoundError):
            read_wav_for_processing(self.root / "missing.wav")

        empty = self.root / "empty.wav"
        wavfile.write(empty, self.sample_rate, np.zeros(0, dtype=np.int16))
        with self.assertRaises(ValueError):
            read_wav_for_processing(empty)

        truncated = self.root / "truncated.wav"
        truncated.write_bytes(b"RIFF\x00\x00")
        with self.assertRaises(ValueError):
            read_wav_for_processing(truncated)

    def test_outputs_refuse_overwrite_and_contain_complete_finite_metadata(self) -> None:
        input_path = self._write_input()
        output_path, json_path, csv_path = self._paths()
        config = CausalProcessorConfig(method="stft_subtraction")

        result = process_wav_file(
            input_path=input_path,
            output_path=output_path,
            metrics_json_path=json_path,
            blocks_csv_path=csv_path,
            config=config,
            block_ms=20.0,
        )
        with self.assertRaises(FileExistsError):
            process_wav_file(
                input_path=input_path,
                output_path=output_path,
                metrics_json_path=json_path,
                blocks_csv_path=csv_path,
                config=config,
                block_ms=20.0,
            )

        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["input"]["sha256"], sha256_file(input_path))
        self.assertEqual(data["output"]["sha256"], sha256_file(output_path))
        self.assertTrue(data["processing"]["length_preserved"])
        self.assertEqual(data["processing"]["processed_samples"], len(result.processed))
        self.assertTrue(math.isfinite(data["timing"]["processing_p99_ms"]))

        with csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(tuple(rows[0].keys()), CSV_FIELDS)
        self.assertEqual(len(rows), len(result.blocks))
        for row in rows:
            for field in (
                "processing_ms",
                "rtf_block",
                "input_peak",
                "output_peak",
                "noise_power_mean",
            ):
                self.assertTrue(math.isfinite(float(row[field])))

    def test_separate_file_runs_reset_state_and_keep_stable_hashes(self) -> None:
        input_path = self._write_input()
        first_paths = self._paths("first")
        second_paths = self._paths("second")
        config = CausalProcessorConfig(method="stft_subtraction")

        first = process_wav_file(
            input_path=input_path,
            output_path=first_paths[0],
            metrics_json_path=first_paths[1],
            blocks_csv_path=first_paths[2],
            config=config,
            block_ms=32.0,
        )
        second = process_wav_file(
            input_path=input_path,
            output_path=second_paths[0],
            metrics_json_path=second_paths[1],
            blocks_csv_path=second_paths[2],
            config=config,
            block_ms=32.0,
        )

        self.assertTrue(np.array_equal(first.processed, second.processed))
        self.assertEqual(sha256_file(first_paths[0]), sha256_file(second_paths[0]))
        self.assertEqual(first.metrics["input"]["sha256"], second.metrics["input"]["sha256"])
        self.assertEqual(first.metrics["causal_config"], second.metrics["causal_config"])

    def test_cli_returns_nonzero_for_invalid_input_and_overwrite(self) -> None:
        output_path, json_path, csv_path = self._paths()
        base_args = [
            "--input",
            str(self.root / "missing.wav"),
            "--output",
            str(output_path),
            "--metrics-json",
            str(json_path),
            "--blocks-csv",
            str(csv_path),
        ]
        self.assertNotEqual(main(base_args), 0)

        input_path = self._write_input()
        base_args[1] = str(input_path)
        self.assertEqual(main(base_args), 0)
        self.assertNotEqual(main(base_args), 0)


if __name__ == "__main__":
    unittest.main()
