from __future__ import annotations

import time
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from realtime_audio.windows_realtime import (
    DiagnosticProgress,
    RealtimeBlockProcessor,
    RealtimeConfig,
    apply_pc_demo_preset,
    build_diagnostic_id_block,
    parse_args,
    summarize_timings,
)
from realtime_audio.ptc_pcm_bridge import (
    BridgePacedWriter,
    IOCTL_PTC_PCM_CONFIGURE,
    IOCTL_PTC_PCM_GET_STATS,
    IOCTL_PTC_PCM_RESET,
    IOCTL_PTC_PCM_WRITE,
    PTC_PCM_FRAMES_PER_BLOCK,
    PtcPcmBridgeClient,
    build_block_payload,
    build_config_payload,
    float32_to_pcm16,
)


class FakeBridgeBackend:
    def __init__(self) -> None:
        self.opened = False
        self.calls: list[tuple[int, bytes, int]] = []
        self.stats_payload = bytes(112)

    def open(self) -> None:
        self.opened = True

    def ioctl(self, code: int, input_data: bytes = b"", output_size: int = 0) -> bytes:
        self.calls.append((code, input_data, output_size))
        if code == IOCTL_PTC_PCM_GET_STATS:
            return self.stats_payload
        return b""

    def close(self) -> None:
        self.opened = False


class RealtimeBlockProcessorTests(unittest.TestCase):
    def test_bypass_preserves_block_shape_and_values(self) -> None:
        config = RealtimeConfig(method="bypass", block_ms=20.0)
        processor = RealtimeBlockProcessor(config)
        block = np.linspace(-0.5, 0.5, config.block_size, dtype=np.float32)

        output, timing = processor.process_block(block)

        self.assertEqual(output.shape, block.shape)
        self.assertTrue(np.allclose(output, block))
        self.assertEqual(timing["calibrating"], False)
        self.assertEqual(timing["warming_up"], False)

    def test_stft_calibration_then_processing_returns_finite_audio(self) -> None:
        config = RealtimeConfig(
            method="stft_subtraction",
            noise_mode="calibration",
            block_ms=20.0,
            calibration_ms=40.0,
            n_fft=256,
            hop_length=80,
        )
        processor = RealtimeBlockProcessor(config)
        rng = np.random.default_rng(3527)

        first = rng.normal(scale=0.02, size=config.block_size).astype(np.float32)
        second = rng.normal(scale=0.02, size=config.block_size).astype(np.float32)
        third = (0.2 + rng.normal(scale=0.02, size=config.block_size)).astype(np.float32)

        out1, timing1 = processor.process_block(first)
        out2, timing2 = processor.process_block(second)
        out3, timing3 = processor.process_block(third)

        self.assertTrue(timing1["calibrating"])
        self.assertTrue(timing2["calibrating"])
        self.assertFalse(timing3["calibrating"])
        self.assertEqual(out1.shape, first.shape)
        self.assertEqual(out2.shape, second.shape)
        self.assertEqual(out3.shape, third.shape)
        self.assertTrue(np.all(np.isfinite(out3)))

    def test_timing_summary_counts_budget_excesses_and_percentiles(self) -> None:
        timings = [
            {
                "processing_ms": 1.0,
                "rtf_block": 0.05,
                "state_memory_bytes": 100,
                "speech_probable": False,
                "warming_up": True,
            },
            {
                "processing_ms": 25.0,
                "rtf_block": 1.25,
                "state_memory_bytes": 120,
                "speech_probable": True,
                "warming_up": False,
            },
        ]

        summary = summarize_timings(timings)

        self.assertEqual(summary["blocks_over_budget"], 1)
        self.assertEqual(summary["state_memory_max_bytes"], 120)
        self.assertEqual(summary["warming_blocks"], 1)
        self.assertAlmostEqual(summary["speech_probable_fraction"], 0.5)
        self.assertGreaterEqual(summary["processing_p99_ms"], summary["processing_p95_ms"])

    def test_pc_demo_wired_applies_checkpoint_26_defaults(self) -> None:
        args = parse_args(["--pc-demo", "wired", "--duration", "30"])

        apply_pc_demo_preset(args)

        self.assertEqual(args.method, "stft_subtraction")
        self.assertEqual(args.noise_mode, "adaptive")
        self.assertEqual(args.block_ms, 20.0)
        self.assertEqual(args.input_device, "2")
        self.assertEqual(args.output_device, "8")
        self.assertTrue(args.no_save)
        self.assertFalse(args.input_only)
        self.assertFalse(args.self_test)
        self.assertIn("windows_realtime_wired", args.output_dir)

    def test_pc_demo_input_only_uses_physical_usb_microphone(self) -> None:
        args = parse_args(["--pc-demo", "input-only"])

        apply_pc_demo_preset(args)

        self.assertEqual(args.method, "stft_subtraction")
        self.assertEqual(args.input_device, "2")
        self.assertIsNone(args.output_device)
        self.assertTrue(args.input_only)
        self.assertTrue(args.no_save)
        self.assertIn("windows_realtime_longrun", args.output_dir)

    def test_virtual_mic_uses_checkpoint_34_queue_defaults(self) -> None:
        args = parse_args(["--virtual-mic"])

        self.assertEqual(args.bridge_target_depth, 2)
        self.assertEqual(args.bridge_user_queue, 4)
        self.assertEqual(args.bridge_poll_interval_ms, 2.0)
        self.assertEqual(args.bridge_drop_policy, "oldest")
        self.assertEqual(args.gain_smoothing, 0.0)

    def test_gain_smoothing_reaches_causal_processor(self) -> None:
        config = RealtimeConfig(
            method="stft_subtraction",
            gain_smoothing=0.8,
        )

        self.assertEqual(config.causal_config().gain_smoothing, 0.8)

    def test_diagnostic_id_source_is_reproducible_and_classified(self) -> None:
        gap, gap_class = build_diagnostic_id_block(0, 320, 16_000)
        noise_a, noise_class = build_diagnostic_id_block(25, 320, 16_000)
        noise_b, _ = build_diagnostic_id_block(25, 320, 16_000)
        active, active_class = build_diagnostic_id_block(75, 320, 16_000)

        self.assertEqual(gap_class, "gap")
        self.assertEqual(noise_class, "noise")
        self.assertEqual(active_class, "active")
        self.assertFalse(np.any(gap))
        self.assertTrue(np.array_equal(noise_a, noise_b))
        self.assertFalse(np.array_equal(noise_a, active))
        self.assertLessEqual(float(np.max(np.abs(active))), 0.151)

    def test_diagnostic_id_source_cli_is_opt_in(self) -> None:
        defaults = parse_args(["--virtual-mic"])
        enabled = parse_args(
            [
                "--virtual-mic",
                "--diagnostic-block-id-source",
                "--diagnostic-block-id-seed",
                "99",
            ]
        )
        self.assertFalse(defaults.diagnostic_block_id_source)
        self.assertTrue(enabled.diagnostic_block_id_source)
        self.assertEqual(enabled.diagnostic_block_id_seed, 99)

    def test_diagnostic_progress_writes_atomic_stage_and_callback_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            path = Path(temporary_dir) / "progress.json"
            progress = DiagnosticProgress(path, callback_write_interval=2)

            progress.mark("before_stream_create", input_device=33)
            progress.callback(10.0, has_status=False)
            progress.callback(10.02, has_status=True)
            progress.mark("duration_complete", duration_s=1.0)

            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["stage"], "duration_complete")
            self.assertEqual(state["input_device"], 33)
            self.assertEqual(state["callback_count"], 2)
            self.assertEqual(state["status_count"], 1)
            self.assertEqual(state["last_callback_monotonic_s"], 10.02)

    def test_progress_file_cli_is_optional(self) -> None:
        self.assertIsNone(parse_args(["--input-only"]).progress_file)
        args = parse_args(["--input-only", "--progress-file", "probe.json"])
        self.assertEqual(args.progress_file, "probe.json")

    def test_pcm_bridge_binary_contract_matches_checkpoint_32(self) -> None:
        block = np.linspace(-1.0, 1.0, PTC_PCM_FRAMES_PER_BLOCK, dtype=np.float32)

        config_payload = build_config_payload()
        block_payload = build_block_payload(7, block)

        self.assertEqual(len(config_payload), 24)
        self.assertEqual(len(block_payload), 664)
        self.assertEqual(float32_to_pcm16(block)[0], -32767)
        self.assertEqual(float32_to_pcm16(block)[-1], 32767)

    def test_pcm_bridge_client_configures_resets_and_sequences_blocks(self) -> None:
        backend = FakeBridgeBackend()
        client = PtcPcmBridgeClient(backend)
        block = np.zeros(PTC_PCM_FRAMES_PER_BLOCK, dtype=np.float32)

        client.open()
        client.write_block(block)
        client.write_block(block)
        stats = client.get_stats()
        client.close()

        self.assertEqual(
            [call[0] for call in backend.calls],
            [
                IOCTL_PTC_PCM_CONFIGURE,
                IOCTL_PTC_PCM_RESET,
                IOCTL_PTC_PCM_WRITE,
                IOCTL_PTC_PCM_WRITE,
                IOCTL_PTC_PCM_GET_STATS,
            ],
        )
        first_sequence = int.from_bytes(backend.calls[2][1][8:16], "little")
        second_sequence = int.from_bytes(backend.calls[3][1][8:16], "little")
        self.assertEqual((first_sequence, second_sequence), (0, 1))
        self.assertEqual(stats.struct_size, 0)
        self.assertFalse(backend.opened)

    def test_bridge_writer_drops_oldest_user_block_when_queue_is_full(self) -> None:
        writer = BridgePacedWriter(
            PtcPcmBridgeClient(FakeBridgeBackend()),
            user_queue_blocks=2,
        )
        first = np.full(PTC_PCM_FRAMES_PER_BLOCK, 0.1, dtype=np.float32)
        second = np.full(PTC_PCM_FRAMES_PER_BLOCK, 0.2, dtype=np.float32)
        third = np.full(PTC_PCM_FRAMES_PER_BLOCK, 0.3, dtype=np.float32)

        writer.submit(first)
        writer.submit(second)
        writer.submit(third)

        self.assertEqual(writer.user_dropped, 1)
        self.assertTrue(np.allclose(writer.blocks.get_nowait().samples, second))
        self.assertTrue(np.allclose(writer.blocks.get_nowait().samples, third))

    def test_bridge_writer_trace_keeps_source_index_for_drop(self) -> None:
        writer = BridgePacedWriter(
            PtcPcmBridgeClient(FakeBridgeBackend()),
            user_queue_blocks=1,
            record_events=True,
        )
        block = np.zeros(PTC_PCM_FRAMES_PER_BLOCK, dtype=np.float32)

        writer.submit(block, source_block_index=10)
        writer.submit(block, source_block_index=11)

        drops = [event for event in writer.events if event["event"] == "local_drop_oldest"]
        submissions = [
            event for event in writer.events if event["event"] == "submitted"
        ]
        self.assertEqual(drops[0]["source_block_index"], 10)
        self.assertEqual(
            [event["source_block_index"] for event in submissions],
            [10, 11],
        )
        self.assertTrue(submissions[1]["after_local_drop"])
        self.assertEqual(writer.metrics()["dropped_source_block_indices"], [10])

    def test_bridge_writer_can_drop_newest_without_reordering_queue(self) -> None:
        writer = BridgePacedWriter(
            PtcPcmBridgeClient(FakeBridgeBackend()),
            user_queue_blocks=1,
            record_events=True,
            drop_policy="newest",
        )
        first = np.full(PTC_PCM_FRAMES_PER_BLOCK, 0.1, dtype=np.float32)
        second = np.full(PTC_PCM_FRAMES_PER_BLOCK, 0.2, dtype=np.float32)

        writer.submit(first, source_block_index=10)
        writer.submit(second, source_block_index=11)

        remaining = writer.blocks.get_nowait()
        metrics = writer.metrics()
        self.assertTrue(np.array_equal(remaining.samples, first))
        self.assertEqual(metrics["user_queue_dropped_oldest"], 0)
        self.assertEqual(metrics["user_queue_dropped_newest"], 1)
        self.assertEqual(metrics["dropped_source_block_indices"], [11])
        self.assertEqual(
            [
                event["event"]
                for event in metrics["events"]
                if event["event"].startswith("local_drop")
            ],
            ["local_drop_newest"],
        )

    def test_bridge_writer_records_source_index_and_pcm_sequence_on_send(self) -> None:
        backend = FakeBridgeBackend()
        writer = BridgePacedWriter(
            PtcPcmBridgeClient(backend),
            target_driver_depth=2,
            user_queue_blocks=4,
            poll_interval_s=0.001,
            record_events=True,
        )
        writer.start()
        writer.submit(np.zeros(320, dtype=np.float32), source_block_index=42)
        deadline = time.monotonic() + 1.0
        while writer.sent < 1 and time.monotonic() < deadline:
            time.sleep(0.005)
        metrics = writer.stop()
        self.assertEqual(metrics["sent_source_block_indices"], [42])
        sent = [event for event in metrics["events"] if event["event"] == "sent"]
        self.assertEqual(sent[0]["source_block_index"], 42)
        self.assertEqual(sent[0]["pcm_sequence"], 0)

    def test_bridge_writer_reports_queue_residence_and_rates(self) -> None:
        writer = BridgePacedWriter(
            PtcPcmBridgeClient(FakeBridgeBackend()),
            target_driver_depth=1,
            user_queue_blocks=2,
        )
        block = np.zeros(PTC_PCM_FRAMES_PER_BLOCK, dtype=np.float32)

        writer.start()
        writer.submit(block)
        deadline = time.monotonic() + 1.0
        while writer.sent < 1 and time.monotonic() < deadline:
            time.sleep(0.005)
        metrics = writer.stop()

        self.assertEqual(metrics["submitted"], 1)
        self.assertEqual(metrics["sent"], 1)
        self.assertGreater(metrics["active_duration_s"], 0.0)
        self.assertGreater(metrics["submitted_rate_hz"], 0.0)
        self.assertGreaterEqual(metrics["user_queue_residence_ms_p95"], 0.0)
        self.assertGreaterEqual(metrics["bridge_buffer_latency_estimated_ms"], 0.0)
        self.assertEqual(metrics["thread_scheduling_requested"], "normal")
        self.assertTrue(metrics["thread_scheduling_applied"])
        self.assertEqual(metrics["poll_wait_strategy"], "sleep")

    def test_bridge_writer_rejects_unknown_thread_scheduling(self) -> None:
        with self.assertRaisesRegex(ValueError, "normal ou mmcss"):
            BridgePacedWriter(
                PtcPcmBridgeClient(FakeBridgeBackend()),
                thread_scheduling="realtime",
            )

    def test_bridge_writer_rejects_unknown_poll_wait_strategy(self) -> None:
        with self.assertRaisesRegex(ValueError, "sleep ou yield"):
            BridgePacedWriter(
                PtcPcmBridgeClient(FakeBridgeBackend()),
                poll_wait_strategy="timer",
            )


if __name__ == "__main__":
    unittest.main()
