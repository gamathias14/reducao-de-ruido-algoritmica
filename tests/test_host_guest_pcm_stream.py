from __future__ import annotations

import importlib.util
import io
import json
import socket
import threading
import time
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audio"
    / "host_guest_pcm_stream.py"
)
SPEC = importlib.util.spec_from_file_location("host_guest_pcm_stream", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HostGuestPcmStreamTests(unittest.TestCase):
    def test_preamble_round_trip_preserves_pcm_contract(self) -> None:
        contract = MODULE.parse_preamble(MODULE.build_preamble(1000))

        self.assertEqual(contract["block_count"], 1000)
        self.assertEqual(contract["sample_rate"], 16_000)
        self.assertEqual(contract["frames_per_block"], 320)

    def test_packet_round_trip_preserves_sequence_and_payload(self) -> None:
        pcm = MODULE.diagnostic_pcm_block(
            17,
            seed=3527,
            variant=0,
            prefix_blocks=500,
        )
        stream = io.BytesIO(MODULE.build_packet(17, 340_000_000, pcm))

        sequence, scheduled_ns, recovered = MODULE.read_packet(stream)

        self.assertEqual(sequence, 17)
        self.assertEqual(scheduled_ns, 340_000_000)
        self.assertEqual(recovered, pcm)

    def test_variants_have_identical_prefix_and_divergent_future(self) -> None:
        prefix_a = MODULE.diagnostic_pcm_block(
            499, seed=3527, variant=0, prefix_blocks=500
        )
        prefix_b = MODULE.diagnostic_pcm_block(
            499, seed=3527, variant=1, prefix_blocks=500
        )
        future_a = MODULE.diagnostic_pcm_block(
            525, seed=3527, variant=0, prefix_blocks=500
        )
        future_b = MODULE.diagnostic_pcm_block(
            525, seed=3527, variant=1, prefix_blocks=500
        )

        self.assertEqual(prefix_a, prefix_b)
        self.assertNotEqual(future_a, future_b)

    def test_corrupted_packet_is_rejected(self) -> None:
        pcm = MODULE.diagnostic_pcm_block(
            20, seed=3527, variant=0, prefix_blocks=500
        )
        packet = bytearray(MODULE.build_packet(20, 400_000_000, pcm))
        packet[-1] ^= 0x01

        with self.assertRaisesRegex(ValueError, "CRC mismatch"):
            MODULE.read_packet(io.BytesIO(packet))

    def test_ready_start_markers_gate_client_connection(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            ready = root / "client.ready"
            start = root / "client.start"
            released = threading.Event()

            def coordinate() -> None:
                MODULE.publish_ready(ready)
                MODULE.wait_for_start(start, 2.0)
                released.set()

            thread = threading.Thread(target=coordinate)
            thread.start()
            deadline = time.monotonic() + 1.0
            while not ready.is_file() and time.monotonic() < deadline:
                time.sleep(0.01)

            self.assertTrue(ready.is_file())
            self.assertFalse(released.is_set())
            start.write_text("start\n", encoding="ascii")
            thread.join(timeout=1.0)
            self.assertFalse(thread.is_alive())
            self.assertTrue(released.is_set())

    def test_local_tcp_stream_preserves_contract_and_cadence(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            server_args = Namespace(
                bind="127.0.0.1",
                port=port,
                duration=0.12,
                seed=3527,
                variant=0,
                prefix_blocks=3,
                start_delay_ms=20,
                initial_burst_blocks=0,
                accept_timeout=5.0,
                socket_timeout=5.0,
                trace=root / "server_trace.json",
            )
            client_args = Namespace(
                host="127.0.0.1",
                port=port,
                method="capture_only",
                prefix_blocks=3,
                connect_timeout=5.0,
                socket_timeout=5.0,
                trace=root / "client_trace.json",
            )
            result: dict[str, object] = {}

            def serve() -> None:
                result["server"] = MODULE.run_server(server_args)

            thread = threading.Thread(target=serve)
            thread.start()
            client = MODULE.run_client(client_args)
            thread.join(timeout=5.0)

            self.assertFalse(thread.is_alive())
            server = result["server"]
            self.assertEqual(client["block_count"], 6)
            self.assertEqual(client["sequence_errors"], 0)
            self.assertEqual(client["crc_errors"], 0)
            self.assertEqual(
                client["input_sha256"],
                server["input_sha256"],
            )
            self.assertAlmostEqual(client["audio_duration_s"], 0.12)
            self.assertLess(client["receive_interval_ms_p99"], 30.0)

    def test_cadence_summary_detects_stalls_and_bursts(self) -> None:
        summary = MODULE.summarize_cadence(
            [0.0, 20.0, 60.0, 65.0],
            [20.0, 40.0, 5.0],
        )

        self.assertEqual(summary["interval_stalls_over_30ms"], 1)
        self.assertEqual(summary["interval_bursts_under_10ms"], 1)
        self.assertAlmostEqual(summary["audio_duration_s"], 0.08)

    def test_initial_burst_keeps_scheduled_offsets_in_protocol(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            server_args = Namespace(
                bind="127.0.0.1",
                port=port,
                duration=0.08,
                seed=3527,
                variant=0,
                prefix_blocks=2,
                start_delay_ms=0,
                initial_burst_blocks=2,
                accept_timeout=5.0,
                socket_timeout=5.0,
                trace=root / "server_trace.json",
            )
            client_args = Namespace(
                host="127.0.0.1",
                port=port,
                method="capture_only",
                prefix_blocks=2,
                connect_timeout=5.0,
                socket_timeout=5.0,
                trace=None,
            )
            result: dict[str, object] = {}

            thread = threading.Thread(
                target=lambda: result.setdefault(
                    "server",
                    MODULE.run_server(server_args),
                )
            )
            thread.start()
            MODULE.run_client(client_args)
            thread.join(timeout=5.0)
            trace = json.loads(
                (root / "server_trace.json").read_text(encoding="utf-8")
            )

        self.assertLess(trace[1]["send_interval_ms"], 10.0)
        self.assertEqual(trace[1]["scheduled_offset_ms"], 20.0)
        self.assertGreater(trace[2]["send_interval_ms"], 20.0)

    def test_send_lead_preserves_scheduled_offsets(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            server_args = Namespace(
                bind="127.0.0.1",
                port=port,
                duration=0.08,
                seed=3527,
                variant=0,
                prefix_blocks=2,
                start_delay_ms=0,
                initial_burst_blocks=2,
                send_lead_ms=10,
                accept_timeout=5.0,
                socket_timeout=5.0,
                trace=root / "server_trace.json",
            )
            client_args = Namespace(
                host="127.0.0.1",
                port=port,
                method="capture_only",
                prefix_blocks=2,
                connect_timeout=5.0,
                socket_timeout=5.0,
                trace=None,
            )
            result: dict[str, object] = {}
            thread = threading.Thread(
                target=lambda: result.setdefault(
                    "server",
                    MODULE.run_server(server_args),
                )
            )
            thread.start()
            MODULE.run_client(client_args)
            thread.join(timeout=5.0)
            trace = json.loads(
                (root / "server_trace.json").read_text(encoding="utf-8")
            )

        self.assertEqual(trace[2]["scheduled_offset_ms"], 40.0)
        self.assertLess(trace[2]["send_offset_ms"], 36.0)
        self.assertEqual(result["server"]["send_lead_ms"], 10)

    def test_pcm_file_source_requires_whole_blocks(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid = root / "invalid.pcm"
            invalid.write_bytes(b"\0" * (MODULE.BYTES_PER_BLOCK + 1))
            args = Namespace(
                pcm_file=invalid,
                duration=20.0,
                bind="127.0.0.1",
                port=1,
                accept_timeout=0.01,
                trace=None,
            )

            with self.assertRaisesRegex(ValueError, "whole number of blocks"):
                MODULE.run_server(args)


if __name__ == "__main__":
    unittest.main()
