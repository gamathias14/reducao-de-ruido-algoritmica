from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
import csv
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

from benchmark_audio.prepare_environmental_noise import (
    DEFAULT_DEMAND_SUBSET,
    DemandArchive,
    file_md5,
    prepare_demand_noise,
    select_channel_member,
    selected_archives,
)
from benchmark_audio.run_benchmark import BenchmarkConfig, run_benchmark


class EnvironmentalNoisePreparationTests(unittest.TestCase):
    def test_default_demand_subset_is_known(self) -> None:
        archives = selected_archives(None)

        self.assertEqual([archive.code for archive in archives], list(DEFAULT_DEMAND_SUBSET))

    def test_channel_member_selection_prefers_requested_channel(self) -> None:
        members = ["DEMAND/TCAR/ch02.wav", "DEMAND/TCAR/ch01.wav", "DEMAND/TCAR/ch03.wav"]

        self.assertEqual(select_channel_member(members, channel=2), "DEMAND/TCAR/ch02.wav")

    def test_prepare_demand_noise_uses_existing_zip_without_download(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_dir = root / "dados" / "external" / "demand"
            raw_dir.mkdir(parents=True)
            archive_path = raw_dir / "DKITCHEN_16k.zip"

            samples = (0.2 * np.sin(2 * np.pi * 220 * np.arange(3200) / 16_000)).astype(np.float32)
            wav_buffer = io.BytesIO()
            wavfile.write(wav_buffer, 16_000, (samples * 32767).astype(np.int16))
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("DKITCHEN/ch01.wav", wav_buffer.getvalue())

            fake_archive = DemandArchive(
                code="DKITCHEN",
                category="domestic",
                description="kitchen",
                filename="DKITCHEN_16k.zip",
                size_bytes=archive_path.stat().st_size,
                md5=file_md5(archive_path),
            )
            with patch("benchmark_audio.prepare_environmental_noise.DEMAND_16K_ARCHIVES", (fake_archive,)):
                rows = prepare_demand_noise(
                    root=root,
                    environments=("DKITCHEN",),
                    channel=1,
                    segment_duration_s=0.1,
                    max_segments_per_env=2,
                    download=False,
                )

            prepared_rows = [row for row in rows if row["status"] == "prepared"]
            self.assertEqual(len(prepared_rows), 2)
            for row in prepared_rows:
                self.assertTrue((root / str(row["output_wav"])).exists())

    def test_benchmark_accepts_local_noise_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clean_dir = root / "dados" / "demo" / "clean"
            noise_dir = root / "dados" / "demo" / "noise_demand"
            clean_dir.mkdir(parents=True)
            noise_dir.mkdir(parents=True)

            t = np.arange(0, 0.20, 1 / 16_000, dtype=np.float32)
            clean = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
            noise = np.random.default_rng(3527).normal(scale=0.1, size=len(t)).astype(np.float32)
            wavfile.write(clean_dir / "speech_test.wav", 16_000, (clean * 32767).astype(np.int16))
            wavfile.write(noise_dir / "demand_test.wav", 16_000, (noise * 32767).astype(np.int16))

            config = BenchmarkConfig(
                duration_s=0.10,
                snrs_db=(0,),
                noise_names=(),
                n_fft=256,
                hop_length=80,
                wavelet_level=3,
            )
            default_tables = root / "resultados" / "tabelas"
            default_tables.mkdir(parents=True)
            sentinel = default_tables / "sentinel.txt"
            sentinel.write_text("preserve", encoding="utf-8")
            demand_results = root / "resultados" / "demand"
            with patch("benchmark_audio.run_benchmark.ROOT", root):
                run_benchmark(
                    config=config,
                    prepare_demo_data=False,
                    noise_dir=noise_dir,
                    max_noises=1,
                    results_dir=demand_results,
                )

            metrics_path = demand_results / "tabelas" / "metricas_por_condicao.csv"
            with metrics_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 4)
            self.assertEqual({row["ruido"] for row in rows}, {"demand_test"})
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
