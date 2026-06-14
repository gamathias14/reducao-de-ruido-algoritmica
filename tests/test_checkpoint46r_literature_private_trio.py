from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.audio.evaluate_checkpoint41_gain_smoothing import write_pcm16
from scripts.audio.prepare_checkpoint46r_literature_private_trio import (
    prepare_trio,
)


class LiteraturePrivateTrioTests(unittest.TestCase):
    def test_trio_is_blind_and_preserves_common_cut(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            private = root / "private"
            public = root / "summary.json"
            samples = np.linspace(-0.2, 0.2, 3_200, dtype=np.float32)
            write_pcm16(source, samples)
            processed = {
                "baseline_stft": samples,
                "omlsa_imcra": samples * 0.8,
                "rnnoise": samples * 0.6,
            }

            with patch(
                "scripts.audio.prepare_checkpoint46r_literature_private_trio._process_full",
                return_value=processed,
            ):
                summary = prepare_trio(
                    source_path=source,
                    cut_start=320,
                    cut_stop=2_880,
                    private_output_dir=private,
                    public_output=public,
                )

            self.assertEqual(summary["status"], "private_listening_pending")
            self.assertEqual(len(summary["files"]), 3)
            self.assertEqual(
                {item["blind_label"] for item in summary["files"]},
                {"A", "B", "C"},
            )
            self.assertTrue((private / "blind_key.json").is_file())
            self.assertTrue((private / "ratings.csv").is_file())
            self.assertNotIn("mapping", public.read_text(encoding="utf-8"))
            self.assertTrue(
                all(item["samples"] == 2_560 for item in summary["files"])
            )

    def test_nonempty_private_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            private = root / "private"
            private.mkdir()
            (private / "existing.txt").write_text("keep", encoding="utf-8")
            write_pcm16(source, np.zeros(640, dtype=np.float32))

            with self.assertRaisesRegex(FileExistsError, "nao vazio"):
                prepare_trio(
                    source_path=source,
                    cut_start=0,
                    cut_stop=320,
                    private_output_dir=private,
                    public_output=root / "summary.json",
                )


if __name__ == "__main__":
    unittest.main()
