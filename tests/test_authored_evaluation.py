from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import wavfile

from benchmark_audio.run_authored_evaluation import (
    REQUIRED_MANIFEST_FIELDS,
    read_prepared_manifest,
    run_authored_evaluation,
)
from realtime_audio.process_wav_blocks import sha256_file


class AuthoredEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.prepared_root = self.root / "dados" / "prepared" / "authored_voice"
        self.results_dir = self.root / "resultados" / "authored_voice" / "evaluation"
        self.manifest = self.root / "prepared_manifest.csv"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_wav(
        self,
        speaker: str,
        session: str,
        kind: str,
        utterance: str,
        samples: np.ndarray,
    ) -> Path:
        path = self.prepared_root / speaker / session / kind / f"{utterance}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        wavfile.write(
            path,
            16_000,
            np.round(np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16),
        )
        return path

    def _row(
        self,
        *,
        speaker: str,
        session: str,
        kind: str,
        utterance: str,
        path: Path,
        status: str = "prepared",
        warnings: str = "",
    ) -> dict[str, str]:
        return {
            "speaker_id": speaker,
            "session_id": session,
            "recording_type": kind,
            "utterance_id": utterance,
            "prepared_path": str(path.relative_to(self.root)),
            "prepared_sha256": sha256_file(path),
            "authorization_level": "local_only",
            "status": status,
            "warnings": warnings,
        }

    def _write_manifest(self, rows: list[dict[str, str]]) -> None:
        with self.manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def _make_rows(self) -> list[dict[str, str]]:
        sample_rate = 16_000
        t = np.arange(8_000, dtype=np.float32) / sample_rate
        clean_a = 0.24 * np.sin(2 * np.pi * 220 * t).astype(np.float32)
        clean_b = 0.18 * np.sin(2 * np.pi * 330 * t).astype(np.float32)
        noise = np.random.default_rng(3527).normal(scale=0.04, size=t.shape).astype(np.float32)
        live = (clean_a + noise).astype(np.float32)

        paths = {
            "quiet_a": self._write_wav("spk01", "session_b", "raw_quiet", "quiet_a", clean_a),
            "quiet_b": self._write_wav("spk02", "session_b", "raw_quiet", "quiet_b", clean_b),
            "noise": self._write_wav("spk01", "session_b", "raw_noise", "noise_a", noise),
            "live": self._write_wav("spk01", "session_b", "raw_live_noisy", "live_a", live),
        }
        return [
            self._row(
                speaker="spk01",
                session="session_b",
                kind="raw_quiet",
                utterance="quiet_a",
                path=paths["quiet_a"],
            ),
            self._row(
                speaker="spk02",
                session="session_b",
                kind="raw_quiet",
                utterance="quiet_b",
                path=paths["quiet_b"],
            ),
            self._row(
                speaker="spk01",
                session="session_b",
                kind="raw_noise",
                utterance="noise_a",
                path=paths["noise"],
            ),
            self._row(
                speaker="spk01",
                session="session_b",
                kind="raw_live_noisy",
                utterance="live_a",
                path=paths["live"],
            ),
        ]

    def test_authored_evaluation_writes_metrics_and_keeps_bypass_neutral(self) -> None:
        self._write_manifest(self._make_rows())

        metadata = run_authored_evaluation(
            prepared_manifest=self.manifest,
            results_dir=self.results_dir,
            session_id="session_b",
            snrs_db=(-5.0, 5.0),
            max_clean_per_speaker=1,
            max_noises=1,
            root=self.root,
        )

        self.assertEqual(metadata["counts"]["controlled_rows"], 24)
        self.assertEqual(metadata["counts"]["operational_rows"], 6)
        controlled = pd.read_csv(
            self.results_dir / "tabelas" / "controlled_metrics.csv"
        )
        bypass = controlled[controlled["candidate_id"] == "bypass"]
        self.assertTrue(np.allclose(bypass["snr_improvement_db"], 0.0, atol=1e-6))
        self.assertTrue(controlled["length_preserved"].all())

        summary_path = self.results_dir / "tabelas" / "controlled_summary.csv"
        metadata_path = self.results_dir / "tabelas" / "metadata_authored_evaluation.json"
        self.assertTrue(summary_path.exists())
        encoded = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertIn("paired_metrics", encoded["policy"])

    def test_warnings_require_explicit_allowance(self) -> None:
        rows = self._make_rows()
        rows[0]["status"] = "prepared_with_warnings"
        rows[0]["warnings"] = "clipping_detected"
        self._write_manifest(rows)

        with self.assertRaisesRegex(ValueError, "allow-warnings"):
            read_prepared_manifest(self.manifest, root=self.root)

        loaded = read_prepared_manifest(
            self.manifest,
            root=self.root,
            allow_warnings=True,
        )
        self.assertEqual(len(loaded), 4)


if __name__ == "__main__":
    unittest.main()
