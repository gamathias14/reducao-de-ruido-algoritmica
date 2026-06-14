from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "capture_host_pcm.py"
)
SPEC = importlib.util.spec_from_file_location("capture_host_pcm", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CaptureHostPcmTests(unittest.TestCase):
    def test_selects_exact_device_and_hostapi(self) -> None:
        devices = [
            {"name": "Mic", "hostapi": 0, "max_input_channels": 1},
            {"name": "Mic", "hostapi": 1, "max_input_channels": 1},
        ]
        hostapis = [{"name": "MME"}, {"name": "WASAPI"}]

        selected = MODULE.select_input_device(
            devices,
            hostapis,
            device_name="Mic",
            hostapi_name="WASAPI",
        )

        self.assertEqual(selected, 1)

    def test_summary_preserves_exact_block_count(self) -> None:
        samples = np.zeros(1_000 * 320, dtype=np.int16)

        result = MODULE.summarize_pcm(samples, 20.0)

        self.assertEqual(result["sample_count"], 320_000)
        self.assertEqual(result["block_count"], 1_000)
        self.assertEqual(result["audio_duration_s"], 20.0)
        self.assertEqual(result["clipped_samples"], 0)

    def test_validation_accepts_useful_integral_capture(self) -> None:
        samples = np.full(1_000 * 320, 1_000, dtype=np.int16)
        summary = MODULE.summarize_pcm(samples, 20.0)

        failures = MODULE.validate_capture(
            summary,
            expected_block_count=1_000,
        )

        self.assertEqual(failures, [])

    def test_validation_rejects_silence_clipping_and_wrong_length(self) -> None:
        samples = np.zeros(999 * 320, dtype=np.int16)
        samples[0] = 32767
        summary = MODULE.summarize_pcm(samples, 20.0)

        failures = MODULE.validate_capture(
            summary,
            expected_block_count=1_000,
        )

        self.assertIn("sample_count", failures)
        self.assertIn("block_count", failures)
        self.assertIn("clipping", failures)
        self.assertIn("useful_level", failures)

    def test_atomic_writers_leave_complete_outputs(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            pcm_path = root / "capture.pcm"
            json_path = root / "capture.json"

            MODULE.atomic_write_bytes(pcm_path, b"\x01\x02")
            MODULE.atomic_write_json(json_path, {"status": "completed"})

            self.assertEqual(pcm_path.read_bytes(), b"\x01\x02")
            self.assertEqual(
                json.loads(json_path.read_text(encoding="utf-8")),
                {"status": "completed"},
            )
            self.assertFalse((root / "capture.pcm.tmp").exists())
            self.assertFalse((root / "capture.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
