from __future__ import annotations

import json
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np

from realtime_audio.virtual_mic_control import (
    ControlSettings,
    ENDPOINT_AVAILABLE,
    ENDPOINT_DISCONNECTED,
    InputDevice,
    STATE_ACTIVE,
    STATE_ERROR,
    STATE_STOPPED,
    UserPreferences,
    VirtualMicController,
    load_preferences,
    save_preferences,
)


class FakeWriter:
    def __init__(self, *, start_error: Exception | None = None) -> None:
        self.start_error = start_error
        self.last_error: str | None = None
        self.started = False
        self.stopped = 0
        self.sent = 0
        self.user_dropped = 0
        self.stop_dropped = 0
        self.write_errors = 0
        self.last_stats = SimpleNamespace(
            underruns=3,
            overruns=1,
        )

    def start(self) -> None:
        if self.start_error:
            raise self.start_error
        self.started = True

    def submit(self, block: np.ndarray) -> None:
        if not self.started:
            raise RuntimeError("writer não iniciado")
        self.sent += 1

    def stop(self) -> dict[str, object]:
        self.stopped += 1
        return self.metrics()

    def metrics(self) -> dict[str, object]:
        return {
            "sent": self.sent,
            "user_queue_dropped_oldest": self.user_dropped,
            "stop_timeout_dropped": self.stop_dropped,
            "write_errors": self.write_errors,
            "bridge_buffer_latency_estimated_ms": 110.0,
            "driver_stats": {
                "underruns": self.last_stats.underruns,
                "overruns": self.last_stats.overruns,
            },
        }


class FakeStream:
    def __init__(self, callback, *, callback_error: Exception | None = None) -> None:
        self.callback = callback
        self.callback_error = callback_error
        self.latency = 0.04
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "FakeStream":
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def _run(self) -> None:
        if self.callback_error:
            bad_block = np.zeros((0, 1), dtype=np.float32)
            self.callback(bad_block, 320, None, None)
            return
        phase = np.arange(320, dtype=np.float32) / 16_000.0
        block = (0.2 * np.sin(2.0 * np.pi * 440.0 * phase)).reshape(-1, 1)
        while not self.stop_event.is_set():
            self.callback(block, 320, None, None)
            time.sleep(0.005)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)


class FakeAudioBackend:
    def __init__(
        self,
        *,
        open_error: Exception | None = None,
        callback_error: Exception | None = None,
    ) -> None:
        self.open_error = open_error
        self.callback_error = callback_error

    def list_input_devices(self) -> list[InputDevice]:
        return [InputDevice(7, "Entrada de teste", "Fake API")]

    def open_input_stream(
        self,
        *,
        sample_rate: int,
        block_size: int,
        input_device: int | str | None,
        callback,
    ) -> FakeStream:
        self.last_open = (sample_rate, block_size, input_device)
        if self.open_error:
            raise self.open_error
        return FakeStream(callback, callback_error=self.callback_error)


def wait_for_state(
    controller: VirtualMicController,
    expected: set[str],
    timeout_s: float = 2.0,
) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = controller.snapshot().state
        if state in expected:
            return state
        time.sleep(0.01)
    return controller.snapshot().state


class VirtualMicControllerTests(unittest.TestCase):
    def test_start_stop_repeated_stop_and_metrics(self) -> None:
        writer = FakeWriter()
        controller = VirtualMicController(
            audio_backend=FakeAudioBackend(),
            writer_factory=lambda: writer,
            endpoint_probe=lambda: None,
        )

        controller.start(ControlSettings(input_device=7))
        self.assertEqual(wait_for_state(controller, {STATE_ACTIVE}), STATE_ACTIVE)

        deadline = time.monotonic() + 1.0
        while controller.snapshot().processed_blocks < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        active = controller.snapshot()
        self.assertGreater(active.level_peak, 0.0)
        self.assertGreater(active.level_rms, 0.0)
        self.assertGreaterEqual(active.sent_blocks, 2)
        self.assertEqual(active.underruns, 3)
        self.assertEqual(active.overruns, 1)
        self.assertAlmostEqual(active.estimated_latency_ms or 0.0, 182.0)

        controller.stop(wait=True)
        controller.stop(wait=True)

        self.assertEqual(controller.snapshot().state, STATE_STOPPED)
        self.assertFalse(controller.worker_alive)
        self.assertEqual(writer.stopped, 1)

    def test_bridge_open_error_becomes_error_state(self) -> None:
        writer = FakeWriter(start_error=OSError("ponte indisponível"))
        controller = VirtualMicController(
            audio_backend=FakeAudioBackend(),
            writer_factory=lambda: writer,
        )

        controller.start(ControlSettings(input_device=7))

        self.assertEqual(wait_for_state(controller, {STATE_ERROR}), STATE_ERROR)
        self.assertIn("ponte indisponível", controller.snapshot().message)
        self.assertTrue(controller.wait(1.0))

    def test_capture_open_error_closes_writer_and_becomes_error(self) -> None:
        writer = FakeWriter()
        controller = VirtualMicController(
            audio_backend=FakeAudioBackend(open_error=RuntimeError("captura falhou")),
            writer_factory=lambda: writer,
        )

        controller.start(ControlSettings(input_device=7))

        self.assertEqual(wait_for_state(controller, {STATE_ERROR}), STATE_ERROR)
        self.assertIn("captura falhou", controller.snapshot().message)
        self.assertTrue(controller.wait(1.0))
        self.assertEqual(writer.stopped, 1)

    def test_stop_during_processing_waits_for_worker(self) -> None:
        controller = VirtualMicController(
            audio_backend=FakeAudioBackend(),
            writer_factory=FakeWriter,
        )
        controller.start(ControlSettings(input_device=7, aggressiveness=1.8))
        self.assertEqual(wait_for_state(controller, {STATE_ACTIVE}), STATE_ACTIVE)

        controller.stop()

        self.assertTrue(controller.wait(1.0))
        self.assertEqual(controller.snapshot().state, STATE_STOPPED)

    def test_endpoint_probe_reports_available_and_disconnected(self) -> None:
        available = VirtualMicController(
            audio_backend=FakeAudioBackend(),
            writer_factory=FakeWriter,
            endpoint_probe=lambda: None,
        )
        disconnected = VirtualMicController(
            audio_backend=FakeAudioBackend(),
            writer_factory=FakeWriter,
            endpoint_probe=lambda: (_ for _ in ()).throw(FileNotFoundError()),
        )

        self.assertEqual(available.refresh_endpoint_status(), ENDPOINT_AVAILABLE)
        self.assertEqual(
            disconnected.refresh_endpoint_status(),
            ENDPOINT_DISCONNECTED,
        )

    def test_preferences_roundtrip_and_corrupted_fallback(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "virtual_mic_ui.json"
            expected = UserPreferences(input_device=9, aggressiveness=1.8)

            save_preferences(expected, path)
            loaded = load_preferences(path)

            self.assertEqual(loaded.preferences, expected)
            self.assertIsNone(loaded.warning)

            path.write_text("{configuração quebrada", encoding="utf-8")
            corrupted = load_preferences(path)

            self.assertEqual(corrupted.preferences, UserPreferences())
            self.assertIsNotNone(corrupted.warning)

    def test_preferences_json_keeps_utf8_and_expected_fields(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "virtual_mic_ui.json"
            save_preferences(UserPreferences("Microfone físico", 1.5), path)

            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["input_device"], "Microfone físico")
            self.assertEqual(payload["aggressiveness"], 1.5)


if __name__ == "__main__":
    unittest.main()
