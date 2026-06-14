from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "analyze_host_guest_pcm_matrix.py"
)
SPEC = importlib.util.spec_from_file_location(
    "analyze_host_guest_pcm_matrix",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HostGuestPcmMatrixAnalysisTests(unittest.TestCase):
    def write_matrix(self, root: Path, *, corrupt_pair: bool = False) -> None:
        for name, method, variant in MODULE.SCENARIOS:
            scenario = root / name
            scenario.mkdir()
            input_hash = f"input-{variant}"
            if corrupt_pair and name == "02-rnnoise-v0":
                input_hash = "wrong"
            server = {
                "status": "completed",
                "variant": variant,
                "block_count": 1000,
                "input_sha256": input_hash,
                "receiver_ack": {
                    "received": 1000,
                    "sequence_errors": 0,
                },
                "audio_to_covered_ratio": 1.0,
                "interval_stalls_over_100ms": 0,
                "send_interval_ms_p99": 20.1,
                "send_interval_ms_max": 21.0,
            }
            client = {
                "status": "completed",
                "method": method,
                "block_count": 1000,
                "input_sha256": input_hash,
                "output_float32_sha256": f"output-{name}",
                "output_prefix_float32_sha256": f"prefix-{method}",
                "sequence_errors": 0,
                "crc_errors": 0,
                "framing_errors": 0,
                "audio_to_covered_ratio": 1.0,
                "interval_stalls_over_100ms": 0,
                "receive_interval_ms_p99": 20.2,
                "receive_interval_ms_max": 22.0,
                "interval_stalls_over_30ms": 0,
                "interval_bursts_under_10ms": 0,
                "processing_ms_p99": 2.0,
                "processing_ms_max": 4.0,
                "processing_over_20ms": 0,
            }
            (scenario / "server.json").write_text(json.dumps(server))
            (scenario / "client.json").write_text(json.dumps(client))

    def write_physical_pair(self, root: Path) -> None:
        for name, method, variant in MODULE.PHYSICAL_SCENARIOS:
            scenario = root / name
            scenario.mkdir()
            server = {
                "status": "completed",
                "variant": variant,
                "block_count": 1000,
                "input_sha256": "physical-input",
                "receiver_ack": {
                    "received": 1000,
                    "sequence_errors": 0,
                },
                "audio_to_covered_ratio": 1.0,
                "interval_stalls_over_100ms": 0,
            }
            client = {
                "status": "completed",
                "method": method,
                "block_count": 1000,
                "input_sha256": "physical-input",
                "output_float32_sha256": f"output-{method}",
                "output_prefix_float32_sha256": f"prefix-{method}",
                "sequence_errors": 0,
                "crc_errors": 0,
                "framing_errors": 0,
                "audio_to_covered_ratio": 1.0,
                "interval_stalls_over_100ms": 0,
            }
            (scenario / "server.json").write_text(json.dumps(server))
            (scenario / "client.json").write_text(json.dumps(client))

    def test_accepts_integral_paired_causal_matrix(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_matrix(root)

            result = MODULE.analyze(root)

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["failures"], [])

    def test_rejects_unpaired_input(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_matrix(root, corrupt_pair=True)

            result = MODULE.analyze(root)

        self.assertEqual(result["status"], "rejected")
        self.assertIn("paired_input_v0", result["failures"])

    def test_accepts_paired_physical_input(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_physical_pair(root)

            result = MODULE.analyze(root, mode="physical")

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["mode"], "physical")


if __name__ == "__main__":
    unittest.main()
