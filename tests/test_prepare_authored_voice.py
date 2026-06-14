from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from benchmark_audio.prepare_authored_voice import (
    RAW_MANIFEST_FIELDS,
    ingest_authored_voice,
    inspect_pcm_wav,
    main,
    read_raw_manifest,
    sha256_file,
)


class AuthoredVoicePreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.raw_root = self.root / "dados" / "raw" / "authored_voice"
        self.prepared_root = self.root / "dados" / "prepared" / "authored_voice"
        self.results_root = self.root / "resultados" / "authored_voice" / "ingestion"
        self.raw_root.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _source_path(
        self,
        speaker: str = "spk01",
        session: str = "session_a",
        folder: str = "quiet",
        name: str = "quiet_001.wav",
    ) -> Path:
        path = self.raw_root / speaker / session / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _base_row(self, source: Path, **updates: str) -> dict[str, str]:
        row = {
            "speaker_id": "spk01",
            "session_id": "session_a",
            "recording_type": "raw_quiet",
            "utterance_id": source.stem,
            "source_path": str(source.relative_to(self.root)),
            "recorded_at": "2026-06-07T10:00:00-03:00",
            "device": "test microphone",
            "interface": "test interface",
            "driver": "test driver",
            "expected_sample_rate_hz": "",
            "expected_channels": "",
            "expected_bit_depth": "",
            "distance_cm": "15",
            "gain_setting": "fixed-test",
            "environment": "quiet test room",
            "capture_processing": "disabled",
            "authorization_level": "local_only",
            "consent_record_id": "consent_spk01_v1",
            "notes": "",
        }
        row.update(updates)
        return row

    def _write_manifest(
        self,
        rows: list[dict[str, str]],
        name: str = "raw_manifest.csv",
    ) -> Path:
        path = self.root / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RAW_MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _outputs(self, suffix: str = "") -> tuple[Path, Path]:
        return (
            self.results_root / f"prepared_manifest{suffix}.csv",
            self.results_root / f"quality_report{suffix}.json",
        )

    def _ingest(
        self,
        manifest: Path,
        suffix: str = "",
        overwrite: bool = False,
    ) -> tuple[list[dict[str, object]], dict[str, object]]:
        prepared_manifest, report = self._outputs(suffix)
        return ingest_authored_voice(
            manifest_path=manifest,
            raw_root=self.raw_root,
            prepared_root=self.prepared_root,
            prepared_manifest_path=prepared_manifest,
            quality_report_path=report,
            root=self.root,
            overwrite=overwrite,
        )

    def test_stereo_48khz_is_dc_removed_resampled_without_normalization(self) -> None:
        source = self._source_path()
        sample_rate = 48_000
        t = np.arange(sample_rate // 2, dtype=np.float32) / sample_rate
        left = 0.20 * np.sin(2 * np.pi * 300 * t) + 0.05
        right = 0.10 * np.sin(2 * np.pi * 300 * t) + 0.05
        stereo = np.stack([left, right], axis=1)
        wavfile.write(source, sample_rate, np.rint(stereo * 32767).astype(np.int16))
        source_hash = sha256_file(source)
        manifest = self._write_manifest(
            [
                self._base_row(
                    source,
                    expected_sample_rate_hz="48000",
                    expected_channels="2",
                    expected_bit_depth="16",
                )
            ]
        )

        rows, report = self._ingest(manifest)

        self.assertEqual(report["summary"]["prepared"], 1)
        self.assertEqual(rows[0]["status"], "prepared")
        prepared = self.root / str(rows[0]["prepared_path"])
        output_sr, output = wavfile.read(prepared)
        output_float = output.astype(np.float32) / 32768.0
        self.assertEqual(output_sr, 16_000)
        self.assertEqual(output.ndim, 1)
        self.assertEqual(len(output), 8_000)
        self.assertAlmostEqual(float(np.mean(output_float)), 0.0, delta=2e-4)
        self.assertGreater(float(np.max(np.abs(output_float))), 0.13)
        self.assertLess(float(np.max(np.abs(output_float))), 0.17)
        self.assertAlmostEqual(float(rows[0]["dc_offset_removed"]), 0.05, delta=2e-4)
        self.assertEqual(sha256_file(source), source_hash)

    def test_clipping_silence_and_duration_warnings_are_reported(self) -> None:
        clipped = self._source_path(name="clipped.wav")
        clipped_values = np.zeros(8_000, dtype=np.int16)
        clipped_values[10] = -32768
        clipped_values[20] = 32767
        wavfile.write(clipped, 16_000, clipped_values)

        silent = self._source_path(name="silent.wav")
        wavfile.write(silent, 16_000, np.zeros(8_000, dtype=np.int16))
        manifest = self._write_manifest(
            [
                self._base_row(clipped, utterance_id="clipped"),
                self._base_row(
                    silent,
                    utterance_id="silent_noise",
                    recording_type="raw_noise",
                ),
            ]
        )

        rows, report = self._ingest(manifest)

        self.assertEqual(report["summary"]["prepared_with_warnings"], 2)
        clipped_row, silent_row = rows
        self.assertTrue(clipped_row["clipping_detected"])
        self.assertIn("clipping_detected", clipped_row["warnings"])
        self.assertTrue(silent_row["silent_detected"])
        self.assertIn("silence_detected", silent_row["warnings"])
        self.assertIn("duration_below_protocol", silent_row["warnings"])

    def test_metadata_mismatch_is_warning_not_silent_correction(self) -> None:
        source = self._source_path()
        wavfile.write(source, 16_000, np.zeros(8_000, dtype=np.int16))
        manifest = self._write_manifest(
            [
                self._base_row(
                    source,
                    expected_sample_rate_hz="48000",
                    expected_channels="2",
                    expected_bit_depth="24",
                )
            ]
        )

        rows, _ = self._ingest(manifest)

        warnings = str(rows[0]["warnings"])
        self.assertIn("expected_sample_rate_hz_mismatch", warnings)
        self.assertIn("expected_channels_mismatch", warnings)
        self.assertIn("expected_bit_depth_mismatch", warnings)
        self.assertEqual(rows[0]["original_sample_rate_hz"], 16_000)

    def test_24bit_pcm_is_accepted_and_reported(self) -> None:
        source = self._source_path(name="pcm24.wav")
        values = np.asarray([-0.5, -0.25, 0.0, 0.25, 0.5] * 1_600)
        integers = np.clip(np.rint(values * (2**23 - 1)), -(2**23), 2**23 - 1).astype(
            np.int32
        )
        payload = b"".join(
            int(value & 0xFFFFFF).to_bytes(3, "little", signed=False)
            for value in integers
        )
        with wave.open(str(source), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(3)
            handle.setframerate(16_000)
            handle.writeframes(payload)
        manifest = self._write_manifest(
            [self._base_row(source, expected_bit_depth="24")]
        )

        rows, _ = self._ingest(manifest)

        self.assertEqual(inspect_pcm_wav(source).bit_depth, 24)
        self.assertEqual(rows[0]["original_bit_depth"], 24)
        self.assertEqual(rows[0]["status"], "prepared")

    def test_missing_consent_and_duplicate_identity_fail_before_writing(self) -> None:
        source = self._source_path()
        wavfile.write(source, 16_000, np.zeros(8_000, dtype=np.int16))
        missing_consent = self._write_manifest(
            [self._base_row(source, consent_record_id="")],
            "missing_consent.csv",
        )
        with self.assertRaisesRegex(ValueError, "consent_record_id"):
            self._ingest(missing_consent)

        row = self._base_row(source)
        duplicate = self._write_manifest([row, row], "duplicate.csv")
        with self.assertRaisesRegex(ValueError, "duplicada"):
            self._ingest(duplicate)

    def test_missing_truncated_and_outside_raw_root_are_recorded_as_errors(self) -> None:
        missing = self._source_path(name="missing.wav")
        truncated = self._source_path(name="truncated.wav")
        truncated.write_bytes(b"RIFF\x00\x00")
        outside = self.root / "outside.wav"
        wavfile.write(outside, 16_000, np.zeros(8_000, dtype=np.int16))
        manifest = self._write_manifest(
            [
                self._base_row(missing, utterance_id="missing"),
                self._base_row(truncated, utterance_id="truncated"),
                self._base_row(
                    outside,
                    utterance_id="outside",
                    source_path=str(outside),
                ),
            ]
        )

        rows, report = self._ingest(manifest)

        self.assertEqual(report["summary"]["errors"], 3)
        self.assertTrue(all(row["status"] == "error" for row in rows))
        self.assertIn("inexistente", str(rows[0]["error"]))
        self.assertIn("truncado", str(rows[1]["error"]))
        self.assertIn("fora de raw_root", str(rows[2]["error"]))

    def test_overwrite_refusal_and_deterministic_regeneration(self) -> None:
        source = self._source_path()
        t = np.arange(8_000, dtype=np.float32) / 16_000
        wavfile.write(
            source,
            16_000,
            np.rint(0.2 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16),
        )
        manifest = self._write_manifest([self._base_row(source)])

        rows, _ = self._ingest(manifest)
        prepared = self.root / str(rows[0]["prepared_path"])
        manifest_path, report_path = self._outputs()
        first_hashes = (
            sha256_file(prepared),
            sha256_file(manifest_path),
            sha256_file(report_path),
        )
        with self.assertRaises(FileExistsError):
            self._ingest(manifest)

        self._ingest(manifest, overwrite=True)
        second_hashes = (
            sha256_file(prepared),
            sha256_file(manifest_path),
            sha256_file(report_path),
        )
        self.assertEqual(first_hashes, second_hashes)

    def test_manifest_schema_and_cli_error_code(self) -> None:
        bad_manifest = self.root / "bad.csv"
        bad_manifest.write_text("speaker_id\nspk01\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "colunas obrigatorias"):
            read_raw_manifest(bad_manifest)

        prepared_manifest, report = self._outputs("_cli")
        exit_code = main(
            [
                "--manifest",
                str(bad_manifest),
                "--raw-root",
                str(self.raw_root),
                "--prepared-root",
                str(self.prepared_root),
                "--prepared-manifest",
                str(prepared_manifest),
                "--quality-report",
                str(report),
            ]
        )
        self.assertNotEqual(exit_code, 0)

    def test_report_json_is_finite_and_contains_no_real_name_field(self) -> None:
        source = self._source_path()
        wavfile.write(source, 16_000, np.zeros(8_000, dtype=np.int16))
        manifest = self._write_manifest([self._base_row(source)])

        rows, report = self._ingest(manifest)
        encoded = json.dumps(report, allow_nan=False)

        self.assertNotIn("real_name", encoded)
        self.assertEqual(rows[0]["speaker_id"], "spk01")
        self.assertEqual(
            rows[0]["source_sha256"],
            hashlib.sha256(source.read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
