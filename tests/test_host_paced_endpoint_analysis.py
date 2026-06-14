from __future__ import annotations

import importlib.util
import json
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_host_paced_endpoint.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_host_paced_endpoint",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HostPacedEndpointAnalysisTests(unittest.TestCase):
    def write_scenario(
        self,
        root: Path,
        name: str,
        method: str,
        *,
        clipped: bool = False,
    ) -> None:
        scenario = root / name
        scenario.mkdir(parents=True)
        samples = np.full(24 * 16_000, 500, dtype="<i2")
        if clipped:
            samples[0] = 32767
        with wave.open(str(scenario / "endpoint.wav"), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16_000)
            handle.writeframes(samples.tobytes())
        client = {
            "status": "completed",
            "method": method,
            "block_count": 1_000,
            "sequence_errors": 0,
            "crc_errors": 0,
            "framing_errors": 0,
            "input_sha256": "paired-input",
            "output_float32_sha256": f"output-{method}",
            "processing_ms_p99": 2.0,
            "processing_ms_max": 4.0,
            "bridge": {
                "submitted": 1_000,
                "sent": 1_000,
                "user_queue_dropped_total": 0,
                "stop_timeout_dropped": 0,
                "write_errors": 0,
                "pending_user_blocks": 0,
                "target_driver_depth": 2,
                "user_queue_peak_blocks": 1,
                "bridge_buffer_latency_estimated_ms": 40.0,
            },
        }
        (scenario / "client.json").write_text(json.dumps(client))

    def test_accepts_paired_endpoint_captures_and_prepares_blind_files(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_scenario(
                root,
                "01-bypass-physical",
                "bypass",
            )
            self.write_scenario(
                root,
                "02-rnnoise-physical",
                "rnnoise",
            )

            result = MODULE.analyze(root, root / "gate.json")
            blind = MODULE.prepare_blind(root, result)

            self.assertEqual(result["status"], "accepted")
            self.assertTrue((blind / "A.wav").is_file())
            self.assertTrue((blind / "B.wav").is_file())
            self.assertTrue((blind / "key.json").is_file())

    def test_rejects_clipped_endpoint(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_scenario(
                root,
                "01-bypass-physical",
                "bypass",
                clipped=True,
            )
            self.write_scenario(
                root,
                "02-rnnoise-physical",
                "rnnoise",
            )

            result = MODULE.analyze(root, root / "gate.json")

        self.assertEqual(result["status"], "rejected")
        self.assertIn(
            "01-bypass-physical:endpoint_clipping",
            result["failures"],
        )


if __name__ == "__main__":
    unittest.main()
