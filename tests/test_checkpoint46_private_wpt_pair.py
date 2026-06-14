from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.audio.evaluate_checkpoint41_gain_smoothing import write_pcm16
from scripts.audio.prepare_checkpoint46_private_wpt_pair import prepare_pair


class Checkpoint46PrivateWPTPairTests(unittest.TestCase):
    def test_pair_has_common_cut_without_fade_or_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.wav"
            reference_path = root / "reference.wav"
            private_dir = root / "private"
            public_output = root / "summary.json"
            samples = np.linspace(-0.2, 0.2, 1_280, dtype=np.float32)
            write_pcm16(raw_path, samples)
            write_pcm16(reference_path, samples[320:960])

            with (
                patch(
                    "scripts.audio.prepare_checkpoint46_private_wpt_pair.process_stft",
                    return_value=samples.copy(),
                ),
                patch(
                    "scripts.audio.prepare_checkpoint46_private_wpt_pair.process_wpt",
                    return_value=(samples * 0.75).astype(np.float32),
                ),
            ):
                summary = prepare_pair(
                    raw_full_path=raw_path,
                    baseline_reference_path=reference_path,
                    cut_start=320,
                    cut_stop=960,
                    private_output_dir=private_dir,
                    public_output=public_output,
                )

            self.assertEqual(summary["status"], "private_listening_pending")
            self.assertEqual(summary["pair"]["fade_ms"], 0)
            self.assertEqual(summary["pair"]["normalization"], "none")
            self.assertEqual(len(summary["pair"]["files"]), 2)
            for item in summary["pair"]["files"]:
                self.assertEqual(item["samples"], 640)
                path = private_dir / item["name"]
                with wave.open(str(path), "rb") as handle:
                    self.assertEqual(handle.getnframes(), 640)
                    self.assertEqual(handle.getframerate(), 16_000)
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertEqual(handle.getsampwidth(), 2)

            persisted = json.loads(public_output.read_text(encoding="utf-8"))
            self.assertTrue(persisted["human_listening_requested"])
            self.assertIsNone(persisted["human_decision"])

    def test_invalid_cut_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.wav"
            reference_path = root / "reference.wav"
            samples = np.zeros(640, dtype=np.float32)
            write_pcm16(raw_path, samples)
            write_pcm16(reference_path, samples)

            with self.assertRaisesRegex(ValueError, "Corte invalido"):
                prepare_pair(
                    raw_full_path=raw_path,
                    baseline_reference_path=reference_path,
                    cut_start=320,
                    cut_stop=960,
                    private_output_dir=root / "private",
                    public_output=root / "summary.json",
                )

    def test_completed_checkpoint_cannot_be_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw.wav"
            reference_path = root / "reference.wav"
            public_output = root / "summary.json"
            samples = np.zeros(640, dtype=np.float32)
            write_pcm16(raw_path, samples)
            write_pcm16(reference_path, samples)
            public_output.write_text(
                json.dumps({"status": "completed_wpt_rejected"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "ja foi concluido"):
                prepare_pair(
                    raw_full_path=raw_path,
                    baseline_reference_path=reference_path,
                    cut_start=0,
                    cut_stop=640,
                    private_output_dir=root / "private",
                    public_output=public_output,
                )


if __name__ == "__main__":
    unittest.main()
