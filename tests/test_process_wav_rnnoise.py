from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from realtime_audio.process_wav_rnnoise import (
    main,
    process_samples_rnnoise,
    process_wav,
)
from realtime_audio.rnnoise_processor import default_library_path


@unittest.skipUnless(default_library_path().is_file(), "DLL RNNoise nao compilada")
class ProcessWavRNNoiseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_preserves_length_with_short_last_block(self) -> None:
        rng = np.random.default_rng(3527)
        samples = rng.normal(scale=0.08, size=1_013).astype(np.float32)

        output, rows = process_samples_rnnoise(samples)

        self.assertEqual(len(output), len(samples))
        self.assertEqual(rows[-1]["block_samples"], 53)
        self.assertTrue(np.all(np.isfinite(output)))

    def test_file_cli_writes_audio_and_metrics(self) -> None:
        sample_rate = 8_000
        t = np.arange(sample_rate, dtype=np.float32) / sample_rate
        stereo = np.stack(
            [
                0.2 * np.sin(2 * np.pi * 300 * t),
                0.1 * np.sin(2 * np.pi * 300 * t),
            ],
            axis=1,
        )
        input_path = self.root / "input.wav"
        output_path = self.root / "output.wav"
        metrics_path = self.root / "output.json"
        wavfile.write(input_path, sample_rate, (stereo * 32767).astype(np.int16))

        metrics = process_wav(
            input_path=input_path,
            output_path=output_path,
            metrics_path=metrics_path,
        )
        output_rate, output = wavfile.read(output_path)
        saved_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        self.assertEqual(output_rate, 16_000)
        self.assertEqual(output.ndim, 1)
        self.assertEqual(len(output), 16_000)
        self.assertTrue(metrics["processing"]["length_preserved"])
        self.assertEqual(saved_metrics["processing"]["method"], "rnnoise")
        self.assertNotEqual(
            main(["--input", str(input_path), "--output", str(output_path)]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
