from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np

from realtime_audio.ptc_pcm_bridge import (
    BridgePacedWriter,
    PtcPcmBridgeClient,
    WindowsBridgeBackend,
)
from realtime_audio.windows_realtime import (
    RealtimeBlockProcessor,
    RealtimeConfig,
    estimated_algorithmic_latency_ms,
)


STATE_STOPPED = "stopped"
STATE_STARTING = "starting"
STATE_ACTIVE = "active"
STATE_STOPPING = "stopping"
STATE_ERROR = "error"

ENDPOINT_UNKNOWN = "unknown"
ENDPOINT_AVAILABLE = "available"
ENDPOINT_ACTIVE = "active"
ENDPOINT_DISCONNECTED = "disconnected"
ENDPOINT_BUSY = "busy"
ENDPOINT_ERROR = "error"

BRIDGE_TARGET_DEPTH = 2
BRIDGE_USER_QUEUE = 4


@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str
    host_api: str

    @property
    def label(self) -> str:
        return f"{self.index}: {self.name} [{self.host_api}]"


@dataclass(frozen=True)
class ControlSettings:
    input_device: int | str | None = None
    aggressiveness: float = 1.5


@dataclass(frozen=True)
class UserPreferences:
    input_device: int | str | None = None
    aggressiveness: float = 1.5


@dataclass(frozen=True)
class PreferencesLoadResult:
    preferences: UserPreferences
    warning: str | None = None


@dataclass(frozen=True)
class ServiceSnapshot:
    state: str = STATE_STOPPED
    endpoint_status: str = ENDPOINT_UNKNOWN
    message: str = "Parado."
    level_peak: float = 0.0
    level_rms: float = 0.0
    processed_blocks: int = 0
    sent_blocks: int = 0
    local_drops: int = 0
    underruns: int = 0
    overruns: int = 0
    write_errors: int = 0
    input_status_events: int = 0
    estimated_latency_ms: float | None = None


class InputStream(Protocol):
    latency: float

    def __enter__(self) -> "InputStream": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class AudioBackend(Protocol):
    def list_input_devices(self) -> list[InputDevice]: ...

    def open_input_stream(
        self,
        *,
        sample_rate: int,
        block_size: int,
        input_device: int | str | None,
        callback: Callable[[np.ndarray, int, Any, Any], None],
    ) -> InputStream: ...


class SoundDeviceAudioBackend:
    def __init__(self) -> None:
        from realtime_audio.windows_realtime import import_sounddevice

        self.sd = import_sounddevice()

    def list_input_devices(self) -> list[InputDevice]:
        devices = self.sd.query_devices()
        host_apis = self.sd.query_hostapis()
        result: list[InputDevice] = []
        for index, device in enumerate(devices):
            if int(device["max_input_channels"]) <= 0:
                continue
            host_api_index = int(device["hostapi"])
            host_api = str(host_apis[host_api_index]["name"])
            result.append(
                InputDevice(
                    index=index,
                    name=str(device["name"]),
                    host_api=host_api,
                )
            )
        return result

    def open_input_stream(
        self,
        *,
        sample_rate: int,
        block_size: int,
        input_device: int | str | None,
        callback: Callable[[np.ndarray, int, Any, Any], None],
    ) -> InputStream:
        return self.sd.InputStream(
            samplerate=sample_rate,
            blocksize=block_size,
            channels=1,
            dtype="float32",
            device=input_device,
            callback=callback,
        )


def default_preferences_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        root = Path(local_app_data)
    else:
        root = Path.home() / "AppData" / "Local"
    return root / "PTC3527" / "virtual_mic_ui.json"


def load_preferences(path: Path | None = None) -> PreferencesLoadResult:
    config_path = path or default_preferences_path()
    if not config_path.exists():
        return PreferencesLoadResult(UserPreferences())
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        input_device = payload.get("input_device")
        if input_device is not None and not isinstance(input_device, (int, str)):
            raise ValueError("input_device inválido")
        aggressiveness = float(payload.get("aggressiveness", 1.5))
        if not math.isfinite(aggressiveness) or aggressiveness <= 0.0:
            raise ValueError("aggressiveness inválida")
        return PreferencesLoadResult(
            UserPreferences(
                input_device=input_device,
                aggressiveness=aggressiveness,
            )
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return PreferencesLoadResult(
            UserPreferences(),
            f"Configuração inválida ignorada: {exc}",
        )


def save_preferences(
    preferences: UserPreferences,
    path: Path | None = None,
) -> Path:
    config_path = path or default_preferences_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_suffix(config_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(asdict(preferences), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary_path, config_path)
    return config_path


def _default_writer_factory() -> BridgePacedWriter:
    return BridgePacedWriter(
        PtcPcmBridgeClient(WindowsBridgeBackend()),
        target_driver_depth=BRIDGE_TARGET_DEPTH,
        user_queue_blocks=BRIDGE_USER_QUEUE,
    )


def _default_endpoint_probe() -> None:
    backend = WindowsBridgeBackend()
    backend.open()
    backend.close()


class VirtualMicController:
    def __init__(
        self,
        *,
        audio_backend: AudioBackend | None = None,
        writer_factory: Callable[[], BridgePacedWriter] | None = None,
        endpoint_probe: Callable[[], None] | None = None,
        processor_factory: Callable[[RealtimeConfig], RealtimeBlockProcessor] | None = None,
    ) -> None:
        self.audio_backend = audio_backend or SoundDeviceAudioBackend()
        self.writer_factory = writer_factory or _default_writer_factory
        self.endpoint_probe = endpoint_probe or _default_endpoint_probe
        self.processor_factory = processor_factory or RealtimeBlockProcessor

        self._lock = threading.Lock()
        self._state = STATE_STOPPED
        self._endpoint_status = ENDPOINT_UNKNOWN
        self._message = "Parado."
        self._level_peak = 0.0
        self._level_rms = 0.0
        self._processed_blocks = 0
        self._input_status_events = 0
        self._input_latency_ms = 0.0
        self._settings = ControlSettings()
        self._writer: BridgePacedWriter | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._runtime_error: str | None = None
        self._final_bridge_metrics: dict[str, object] = {}

    def list_input_devices(self) -> list[InputDevice]:
        return self.audio_backend.list_input_devices()

    @property
    def worker_alive(self) -> bool:
        thread = self._thread
        return bool(thread is not None and thread.is_alive())

    def refresh_endpoint_status(self) -> str:
        with self._lock:
            if self._state in {STATE_STARTING, STATE_ACTIVE, STATE_STOPPING}:
                return self._endpoint_status
        try:
            self.endpoint_probe()
            status = ENDPOINT_AVAILABLE
            message = "Endpoint virtual disponível."
        except OSError as exc:
            if getattr(exc, "winerror", None) == 170:
                status = ENDPOINT_BUSY
                message = "Endpoint virtual ocupado por outro produtor."
            else:
                status = ENDPOINT_DISCONNECTED
                message = "Endpoint virtual não encontrado."
        except Exception as exc:
            status = ENDPOINT_ERROR
            message = f"Falha ao consultar o endpoint: {exc}"
        with self._lock:
            self._endpoint_status = status
            if self._state in {STATE_STOPPED, STATE_ERROR}:
                self._message = message
        return status

    def start(self, settings: ControlSettings) -> ServiceSnapshot:
        if not math.isfinite(settings.aggressiveness) or settings.aggressiveness <= 0.0:
            raise ValueError("A agressividade deve ser um número positivo.")
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("O microfone virtual já está iniciando ou ativo.")
            self._settings = settings
            self._state = STATE_STARTING
            self._endpoint_status = ENDPOINT_UNKNOWN
            self._message = "Iniciando captura, DSP e ponte..."
            self._level_peak = 0.0
            self._level_rms = 0.0
            self._processed_blocks = 0
            self._input_status_events = 0
            self._input_latency_ms = 0.0
            self._writer = None
            self._runtime_error = None
            self._final_bridge_metrics = {}
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="ptc-virtual-mic-controller",
                daemon=True,
            )
            self._thread.start()
        return self.snapshot()

    def stop(self, *, wait: bool = False, timeout_s: float = 3.0) -> ServiceSnapshot:
        with self._lock:
            if self._state in {STATE_STARTING, STATE_ACTIVE}:
                self._state = STATE_STOPPING
                self._message = "Parando captura e drenando a ponte..."
            self._stop_event.set()
            thread = self._thread
        if wait and thread is not None:
            thread.join(timeout=max(0.0, timeout_s))
        return self.snapshot()

    def wait(self, timeout_s: float) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout=max(0.0, timeout_s))
        return not thread.is_alive()

    def _record_runtime_error(self, exc: BaseException) -> None:
        message = str(exc) or exc.__class__.__name__
        with self._lock:
            if self._runtime_error is None:
                self._runtime_error = message
                self._state = STATE_ERROR
                self._message = message
        self._stop_event.set()

    def _audio_callback(
        self,
        processor: RealtimeBlockProcessor,
        writer: BridgePacedWriter,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: Any,
    ) -> None:
        del time_info
        try:
            if status:
                with self._lock:
                    self._input_status_events += 1
            block = np.asarray(indata[:, 0], dtype=np.float32).copy()
            if block.size != frames:
                block = np.resize(block, frames).astype(np.float32)
            output, _ = processor.process_block(block)
            writer.submit(output)
            peak = float(np.max(np.abs(block))) if block.size else 0.0
            rms = float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0
            with self._lock:
                self._processed_blocks += 1
                self._level_peak = max(peak, 0.80 * self._level_peak)
                self._level_rms = 0.85 * self._level_rms + 0.15 * rms
        except Exception as exc:
            self._record_runtime_error(exc)

    def _run(self) -> None:
        writer: BridgePacedWriter | None = None
        processor: RealtimeBlockProcessor | None = None
        bridge_metrics: dict[str, object] = {}
        try:
            config = RealtimeConfig(
                sample_rate=16_000,
                block_ms=20.0,
                method="stft_subtraction",
                noise_mode="adaptive",
                spectral_alpha=self._settings.aggressiveness,
            )
            processor = self.processor_factory(config)
            writer = self.writer_factory()
            with self._lock:
                self._writer = writer
            writer.start()
            stream = self.audio_backend.open_input_stream(
                sample_rate=config.sample_rate,
                block_size=config.block_size,
                input_device=self._settings.input_device,
                callback=lambda indata, frames, time_info, status: self._audio_callback(
                    processor,
                    writer,
                    indata,
                    frames,
                    time_info,
                    status,
                ),
            )
            with stream:
                with self._lock:
                    self._input_latency_ms = float(stream.latency) * 1000.0
                    if self._stop_event.is_set():
                        self._state = STATE_STOPPING
                        self._message = "Parando captura e drenando a ponte..."
                    else:
                        self._state = STATE_ACTIVE
                        self._endpoint_status = ENDPOINT_ACTIVE
                        self._message = "Microfone virtual ativo."
                while not self._stop_event.wait(0.05):
                    if writer.last_error:
                        raise RuntimeError(writer.last_error)
        except Exception as exc:
            self._record_runtime_error(exc)
        finally:
            if processor is not None:
                try:
                    processor.close()
                except Exception as exc:
                    self._record_runtime_error(exc)
            if writer is not None:
                try:
                    bridge_metrics = writer.stop()
                except Exception as exc:
                    self._record_runtime_error(exc)
            with self._lock:
                self._final_bridge_metrics = bridge_metrics
                self._writer = None
                if self._runtime_error is None:
                    self._state = STATE_STOPPED
                    self._endpoint_status = ENDPOINT_AVAILABLE
                    self._message = "Parado."
                else:
                    self._state = STATE_ERROR
                    self._endpoint_status = ENDPOINT_ERROR
                    self._message = self._runtime_error

    def _bridge_metrics(self) -> dict[str, object]:
        with self._lock:
            writer = self._writer
            final_metrics = self._final_bridge_metrics.copy()
        if writer is None:
            return final_metrics
        try:
            return writer.metrics()
        except Exception:
            return final_metrics

    def snapshot(self) -> ServiceSnapshot:
        bridge = self._bridge_metrics()
        driver_stats = bridge.get("driver_stats")
        if not isinstance(driver_stats, dict):
            driver_stats = {}
        bridge_latency_ms = float(
            bridge.get("bridge_buffer_latency_estimated_ms", 0.0) or 0.0
        )
        with self._lock:
            state = self._state
            endpoint_status = self._endpoint_status
            message = self._message
            level_peak = self._level_peak
            level_rms = self._level_rms
            processed_blocks = self._processed_blocks
            input_status_events = self._input_status_events
            input_latency_ms = self._input_latency_ms
            settings = self._settings
        latency_ms: float | None = None
        if processed_blocks or state in {STATE_STARTING, STATE_ACTIVE, STATE_STOPPING}:
            config = RealtimeConfig(
                method="stft_subtraction",
                noise_mode="adaptive",
                spectral_alpha=settings.aggressiveness,
            )
            latency_ms = (
                estimated_algorithmic_latency_ms(config)
                + input_latency_ms
                + bridge_latency_ms
            )
        return ServiceSnapshot(
            state=state,
            endpoint_status=endpoint_status,
            message=message,
            level_peak=level_peak,
            level_rms=level_rms,
            processed_blocks=processed_blocks,
            sent_blocks=int(bridge.get("sent", 0) or 0),
            local_drops=int(bridge.get("user_queue_dropped_oldest", 0) or 0)
            + int(bridge.get("stop_timeout_dropped", 0) or 0),
            underruns=int(driver_stats.get("underruns", 0) or 0),
            overruns=int(driver_stats.get("overruns", 0) or 0),
            write_errors=int(bridge.get("write_errors", 0) or 0),
            input_status_events=input_status_events,
            estimated_latency_ms=latency_ms,
        )
