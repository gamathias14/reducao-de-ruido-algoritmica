from __future__ import annotations

import ctypes
import os
import queue
import struct
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Protocol

import numpy as np


PTC_PCM_PROTOCOL_VERSION = 1
PTC_PCM_SAMPLE_RATE = 16_000
PTC_PCM_CHANNELS = 1
PTC_PCM_BITS_PER_SAMPLE = 16
PTC_PCM_FRAMES_PER_BLOCK = 320
PTC_PCM_BYTES_PER_BLOCK = 640
PTC_PCM_QUEUE_CAPACITY_BLOCKS = 50
PTC_PCM_INTERFACE_GUID = uuid.UUID("e9342d3d-0b9a-4c94-a786-46d97a44a1a2")

FILE_DEVICE_UNKNOWN = 0x22
METHOD_BUFFERED = 0
FILE_READ_ACCESS = 0x0001
FILE_WRITE_ACCESS = 0x0002


def _ctl_code(function: int) -> int:
    access = FILE_READ_ACCESS | FILE_WRITE_ACCESS
    return (
        (FILE_DEVICE_UNKNOWN << 16)
        | (access << 14)
        | (function << 2)
        | METHOD_BUFFERED
    )


IOCTL_PTC_PCM_CONFIGURE = _ctl_code(0x800)
IOCTL_PTC_PCM_WRITE = _ctl_code(0x801)
IOCTL_PTC_PCM_GET_STATS = _ctl_code(0x802)
IOCTL_PTC_PCM_RESET = _ctl_code(0x803)

_CONFIG_STRUCT = struct.Struct("<IIIHHII")
_BLOCK_STRUCT = struct.Struct("<IIQII320h")
_STATS_STRUCT = struct.Struct("<8I10Q")


@dataclass(frozen=True)
class PtcPcmStats:
    version: int
    struct_size: int
    configured: int
    producer_connected: int
    queue_depth_blocks: int
    queue_capacity_blocks: int
    consumer_partial_bytes: int
    reserved: int
    blocks_accepted: int
    blocks_dropped: int
    blocks_consumed: int
    bytes_accepted: int
    bytes_consumed: int
    underruns: int
    overruns: int
    rejected_requests: int
    sequence_errors: int
    last_accepted_sequence: int

    @classmethod
    def from_bytes(cls, payload: bytes) -> "PtcPcmStats":
        if len(payload) != _STATS_STRUCT.size:
            raise ValueError(
                f"Estatisticas devem ter {_STATS_STRUCT.size} bytes, receberam {len(payload)}."
            )
        return cls(*_STATS_STRUCT.unpack(payload))


@dataclass(frozen=True)
class _QueuedBlock:
    samples: np.ndarray
    submitted_at_s: float
    source_block_index: int | None = None


@dataclass
class _ThreadSchedulingState:
    requested: str
    applied: bool = False
    error: str | None = None
    mmcss_handle: int | None = None


def _apply_thread_scheduling(mode: str) -> _ThreadSchedulingState:
    state = _ThreadSchedulingState(requested=mode)
    if mode == "normal":
        state.applied = True
        return state
    if os.name != "nt":
        state.error = "MMCSS scheduling requires Windows."
        return state
    try:
        avrt = ctypes.WinDLL("Avrt", use_last_error=True)
        avrt.AvSetMmThreadCharacteristicsW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        avrt.AvSetMmThreadCharacteristicsW.restype = ctypes.c_void_p
        avrt.AvSetMmThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
        avrt.AvSetMmThreadPriority.restype = ctypes.c_int
        task_index = ctypes.c_ulong()
        handle = avrt.AvSetMmThreadCharacteristicsW(
            "Pro Audio",
            ctypes.byref(task_index),
        )
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        if not avrt.AvSetMmThreadPriority(handle, 2):
            error = ctypes.get_last_error()
            avrt.AvRevertMmThreadCharacteristics(handle)
            raise ctypes.WinError(error)
        state.applied = True
        state.mmcss_handle = int(handle)
    except Exception as exc:
        state.error = f"{type(exc).__name__}: {exc}"
    return state


def _restore_thread_scheduling(state: _ThreadSchedulingState) -> None:
    if state.mmcss_handle is None or os.name != "nt":
        return
    avrt = ctypes.WinDLL("Avrt", use_last_error=True)
    avrt.AvRevertMmThreadCharacteristics.argtypes = [ctypes.c_void_p]
    avrt.AvRevertMmThreadCharacteristics.restype = ctypes.c_int
    avrt.AvRevertMmThreadCharacteristics(
        ctypes.c_void_p(state.mmcss_handle)
    )


def build_config_payload() -> bytes:
    return _CONFIG_STRUCT.pack(
        PTC_PCM_PROTOCOL_VERSION,
        _CONFIG_STRUCT.size,
        PTC_PCM_SAMPLE_RATE,
        PTC_PCM_CHANNELS,
        PTC_PCM_BITS_PER_SAMPLE,
        PTC_PCM_FRAMES_PER_BLOCK,
        PTC_PCM_QUEUE_CAPACITY_BLOCKS,
    )


def float32_to_pcm16(block: np.ndarray) -> np.ndarray:
    values = np.asarray(block, dtype=np.float32).reshape(-1)
    if values.size != PTC_PCM_FRAMES_PER_BLOCK:
        raise ValueError(
            f"Bloco deve ter {PTC_PCM_FRAMES_PER_BLOCK} frames, recebeu {values.size}."
        )
    values = np.nan_to_num(values, nan=0.0, posinf=1.0, neginf=-1.0)
    values = np.clip(values, -1.0, 1.0)
    return np.rint(values * 32767.0).astype("<i2")


def build_block_payload(sequence: int, block: np.ndarray) -> bytes:
    if sequence < 0:
        raise ValueError("Sequencia deve ser nao negativa.")
    samples = float32_to_pcm16(block)
    return _BLOCK_STRUCT.pack(
        PTC_PCM_PROTOCOL_VERSION,
        _BLOCK_STRUCT.size,
        sequence,
        PTC_PCM_BYTES_PER_BLOCK,
        0,
        *samples.tolist(),
    )


class BridgeBackend(Protocol):
    def open(self) -> None: ...

    def ioctl(self, code: int, input_data: bytes = b"", output_size: int = 0) -> bytes: ...

    def close(self) -> None: ...


class _Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> "_Guid":
        fields = value.fields
        return cls(
            fields[0],
            fields[1],
            fields[2],
            (ctypes.c_ubyte * 8)(
                fields[3],
                fields[4],
                *value.bytes[10:],
            ),
        )


class WindowsBridgeBackend:
    def __init__(self, device_path: str | None = None) -> None:
        self.device_path = device_path
        self.handle: int | None = None

    def _require_windows(self) -> None:
        if os.name != "nt":
            raise RuntimeError("A ponte PTC PCM so pode ser aberta no Windows.")

    def _discover_device_path(self) -> str:
        self._require_windows()
        cfgmgr32 = ctypes.WinDLL("CfgMgr32", use_last_error=True)
        cfgmgr32.CM_Get_Device_Interface_List_SizeW.argtypes = [
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(_Guid),
            ctypes.c_wchar_p,
            ctypes.c_ulong,
        ]
        cfgmgr32.CM_Get_Device_Interface_List_SizeW.restype = ctypes.c_ulong
        cfgmgr32.CM_Get_Device_Interface_ListW.argtypes = [
            ctypes.POINTER(_Guid),
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        cfgmgr32.CM_Get_Device_Interface_ListW.restype = ctypes.c_ulong
        guid = _Guid.from_uuid(PTC_PCM_INTERFACE_GUID)
        size = ctypes.c_ulong()
        present = 0
        status = cfgmgr32.CM_Get_Device_Interface_List_SizeW(
            ctypes.byref(size),
            ctypes.byref(guid),
            None,
            present,
        )
        if status != 0 or size.value <= 1:
            raise OSError(status, "Interface PTC PCM nao encontrada.")

        buffer = ctypes.create_unicode_buffer(size.value)
        status = cfgmgr32.CM_Get_Device_Interface_ListW(
            ctypes.byref(guid),
            None,
            buffer,
            size.value,
            present,
        )
        if status != 0:
            raise OSError(status, "Falha ao enumerar a interface PTC PCM.")
        path = buffer.value
        if not path:
            raise FileNotFoundError("Interface PTC PCM nao encontrada.")
        return path

    def open(self) -> None:
        self._require_windows()
        if self.handle is not None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_void_p,
        ]
        kernel32.CreateFileW.restype = ctypes.c_void_p
        path = self.device_path or self._discover_device_path()
        handle = kernel32.CreateFileW(
            path,
            0x80000000 | 0x40000000,
            0x00000001 | 0x00000002,
            None,
            3,
            0x00000080,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle == invalid_handle:
            error = ctypes.get_last_error()
            raise ctypes.WinError(error)
        self.device_path = path
        self.handle = handle

    def ioctl(self, code: int, input_data: bytes = b"", output_size: int = 0) -> bytes:
        if self.handle is None:
            raise RuntimeError("Ponte PTC PCM nao esta aberta.")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.DeviceIoControl.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.c_void_p,
        ]
        kernel32.DeviceIoControl.restype = ctypes.c_int
        input_buffer = ctypes.create_string_buffer(input_data) if input_data else None
        output_buffer = ctypes.create_string_buffer(output_size) if output_size else None
        returned = ctypes.c_ulong()
        ok = kernel32.DeviceIoControl(
            self.handle,
            code,
            input_buffer,
            len(input_data),
            output_buffer,
            output_size,
            ctypes.byref(returned),
            None,
        )
        if not ok:
            error = ctypes.get_last_error()
            raise ctypes.WinError(error)
        if output_buffer is None:
            return b""
        return output_buffer.raw[: returned.value]

    def close(self) -> None:
        if self.handle is None:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        kernel32.CloseHandle(self.handle)
        self.handle = None


class PtcPcmBridgeClient:
    def __init__(self, backend: BridgeBackend | None = None) -> None:
        self.backend = backend or WindowsBridgeBackend()
        self.sequence = 0

    def open(self) -> None:
        self.backend.open()
        self.backend.ioctl(IOCTL_PTC_PCM_CONFIGURE, build_config_payload())
        self.backend.ioctl(IOCTL_PTC_PCM_RESET)
        self.sequence = 0

    def write_block(self, block: np.ndarray) -> None:
        payload = build_block_payload(self.sequence, block)
        self.backend.ioctl(IOCTL_PTC_PCM_WRITE, payload)
        self.sequence += 1

    def get_stats(self) -> PtcPcmStats:
        payload = self.backend.ioctl(
            IOCTL_PTC_PCM_GET_STATS,
            output_size=_STATS_STRUCT.size,
        )
        return PtcPcmStats.from_bytes(payload)

    def close(self) -> None:
        self.backend.close()

    def __enter__(self) -> "PtcPcmBridgeClient":
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class BridgePacedWriter:
    def __init__(
        self,
        client: PtcPcmBridgeClient,
        *,
        target_driver_depth: int = 2,
        user_queue_blocks: int = 4,
        poll_interval_s: float = 0.002,
        record_events: bool = False,
        drop_policy: str = "oldest",
        thread_scheduling: str = "normal",
        poll_wait_strategy: str = "sleep",
    ) -> None:
        if not 1 <= target_driver_depth < PTC_PCM_QUEUE_CAPACITY_BLOCKS:
            raise ValueError("Profundidade alvo do driver fora da faixa valida.")
        if user_queue_blocks <= 0:
            raise ValueError("Fila de usuario deve ter capacidade positiva.")
        if drop_policy not in {"oldest", "newest"}:
            raise ValueError("Politica de descarte deve ser oldest ou newest.")
        if thread_scheduling not in {"normal", "mmcss"}:
            raise ValueError("Agendamento deve ser normal ou mmcss.")
        if poll_wait_strategy not in {"sleep", "yield"}:
            raise ValueError("Espera de polling deve ser sleep ou yield.")
        self.client = client
        self.target_driver_depth = target_driver_depth
        self.poll_interval_s = poll_interval_s
        self.record_events = record_events
        self.drop_policy = drop_policy
        self.thread_scheduling = thread_scheduling
        self.poll_wait_strategy = poll_wait_strategy
        self.blocks: queue.Queue[_QueuedBlock] = queue.Queue(maxsize=user_queue_blocks)
        self.stop_event = threading.Event()
        self.abort_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.submitted = 0
        self.sent = 0
        self.user_dropped = 0
        self.user_dropped_oldest = 0
        self.user_dropped_newest = 0
        self.stop_dropped = 0
        self.write_errors = 0
        self.last_stats: PtcPcmStats | None = None
        self.last_error: str | None = None
        self.first_submit_at_s: float | None = None
        self.last_submit_at_s: float | None = None
        self.stopped_at_s: float | None = None
        self.user_queue_peak_blocks = 0
        self.sent_residence_ms: list[float] = []
        self.dropped_residence_ms: list[float] = []
        self.driver_depth_samples: list[int] = []
        self.events: list[dict[str, object]] = []
        self.loop_samples: list[dict[str, object]] = []
        self.thread_scheduling_applied = False
        self.thread_scheduling_error: str | None = None
        self.sent_source_block_indices: list[int | None] = []
        self.dropped_source_block_indices: list[int | None] = []
        self.stop_dropped_source_block_indices: list[int | None] = []
        self._last_event_driver_stats: tuple[int, int, int, int] | None = None

    def start(self) -> None:
        if self.thread is not None:
            raise RuntimeError("Escritor da ponte ja foi iniciado.")
        self.client.open()
        self.thread = threading.Thread(target=self._run, name="ptc-pcm-writer", daemon=True)
        self.thread.start()

    def submit(
        self,
        block: np.ndarray,
        *,
        source_block_index: int | None = None,
    ) -> None:
        values = np.asarray(block, dtype=np.float32).reshape(-1).copy()
        if values.size != PTC_PCM_FRAMES_PER_BLOCK:
            raise ValueError(
                f"Bloco deve ter {PTC_PCM_FRAMES_PER_BLOCK} frames, recebeu {values.size}."
            )
        now = time.perf_counter()
        queued = _QueuedBlock(
            samples=values,
            submitted_at_s=now,
            source_block_index=source_block_index,
        )
        if self.first_submit_at_s is None:
            self.first_submit_at_s = now
        self.last_submit_at_s = now
        self.submitted += 1
        try:
            self.blocks.put_nowait(queued)
            self.user_queue_peak_blocks = max(
                self.user_queue_peak_blocks, self.blocks.qsize()
            )
            if self.record_events:
                self.events.append(
                    {
                        "event": "submitted",
                        "source_block_index": source_block_index,
                        "monotonic_s": now,
                        "qpc_ns": time.perf_counter_ns(),
                        "user_queue_depth": self.blocks.qsize(),
                    }
                )
            return
        except queue.Full:
            pass
        if self.drop_policy == "newest":
            self.user_dropped += 1
            self.user_dropped_newest += 1
            self.dropped_source_block_indices.append(queued.source_block_index)
            self.dropped_residence_ms.append(0.0)
            if self.record_events:
                self.events.append(
                    {
                        "event": "local_drop_newest",
                        "source_block_index": queued.source_block_index,
                        "monotonic_s": now,
                        "qpc_ns": time.perf_counter_ns(),
                        "user_queue_depth": self.blocks.qsize(),
                    }
                )
            return
        try:
            dropped = self.blocks.get_nowait()
            self.user_dropped += 1
            self.user_dropped_oldest += 1
            self.dropped_source_block_indices.append(dropped.source_block_index)
            self.dropped_residence_ms.append(
                1000.0 * (now - dropped.submitted_at_s)
            )
            if self.record_events:
                self.events.append(
                    {
                        "event": "local_drop_oldest",
                        "source_block_index": dropped.source_block_index,
                        "monotonic_s": now,
                        "qpc_ns": time.perf_counter_ns(),
                        "user_queue_depth": self.blocks.qsize(),
                    }
                )
        except queue.Empty:
            pass
        self.blocks.put_nowait(queued)
        self.user_queue_peak_blocks = max(
            self.user_queue_peak_blocks, self.blocks.qsize()
        )
        if self.record_events:
            self.events.append(
                {
                    "event": "submitted",
                    "source_block_index": source_block_index,
                    "monotonic_s": now,
                    "qpc_ns": time.perf_counter_ns(),
                    "user_queue_depth": self.blocks.qsize(),
                    "after_local_drop": True,
                }
            )

    def _run(self) -> None:
        scheduling = _apply_thread_scheduling(self.thread_scheduling)
        self.thread_scheduling_applied = scheduling.applied
        self.thread_scheduling_error = scheduling.error
        previous_loop_ns: int | None = None
        try:
            while (
                not self.abort_event.is_set()
                and (not self.stop_event.is_set() or not self.blocks.empty())
            ):
                loop_started_ns = time.perf_counter_ns()
                loop_interval_ms = (
                    0.0
                    if previous_loop_ns is None
                    else (loop_started_ns - previous_loop_ns) / 1e6
                )
                previous_loop_ns = loop_started_ns
                stats_started_ns = time.perf_counter_ns()
                stats = self.client.get_stats()
                stats_finished_ns = time.perf_counter_ns()
                self.last_stats = stats
                self.driver_depth_samples.append(stats.queue_depth_blocks)
                event_stats = (
                    stats.blocks_consumed,
                    stats.underruns,
                    stats.overruns,
                    stats.queue_depth_blocks,
                )
                if self.record_events and event_stats != self._last_event_driver_stats:
                    self.events.append(
                        {
                            "event": "driver_stats",
                            "monotonic_s": time.perf_counter(),
                            "qpc_ns": stats_finished_ns,
                            "blocks_consumed": stats.blocks_consumed,
                            "underruns": stats.underruns,
                            "overruns": stats.overruns,
                            "queue_depth_blocks": stats.queue_depth_blocks,
                        }
                    )
                    self._last_event_driver_stats = event_stats
                action = "driver_depth_wait"
                queue_wait_ms = 0.0
                write_ms = 0.0
                poll_wait_ms = 0.0
                if stats.queue_depth_blocks >= self.target_driver_depth:
                    wait_started_ns = time.perf_counter_ns()
                    if self.poll_wait_strategy == "sleep":
                        time.sleep(self.poll_interval_s)
                    else:
                        deadline_ns = (
                            wait_started_ns
                            + round(self.poll_interval_s * 1e9)
                        )
                        while time.perf_counter_ns() < deadline_ns:
                            time.sleep(0)
                    poll_wait_ms = (
                        time.perf_counter_ns() - wait_started_ns
                    ) / 1e6
                else:
                    queue_started_ns = time.perf_counter_ns()
                    try:
                        queued = self.blocks.get(timeout=self.poll_interval_s)
                    except queue.Empty:
                        action = "user_queue_empty"
                    else:
                        write_started_ns = time.perf_counter_ns()
                        queue_wait_ms = (
                            write_started_ns - queue_started_ns
                        ) / 1e6
                        self.client.write_block(queued.samples)
                        write_finished_ns = time.perf_counter_ns()
                        write_ms = (
                            write_finished_ns - write_started_ns
                        ) / 1e6
                        action = "sent"
                        pcm_sequence = self.client.sequence - 1
                        self.sent += 1
                        self.sent_source_block_indices.append(
                            queued.source_block_index
                        )
                        sent_at_s = time.perf_counter()
                        residence_ms = 1000.0 * (
                            sent_at_s - queued.submitted_at_s
                        )
                        self.sent_residence_ms.append(residence_ms)
                        if self.record_events:
                            self.events.append(
                                {
                                    "event": "sent",
                                    "source_block_index": (
                                        queued.source_block_index
                                    ),
                                    "pcm_sequence": pcm_sequence,
                                    "monotonic_s": sent_at_s,
                                    "qpc_ns": write_finished_ns,
                                    "residence_ms": residence_ms,
                                    "driver_queue_depth_before_send": (
                                        stats.queue_depth_blocks
                                    ),
                                }
                            )
                if self.record_events:
                    self.loop_samples.append(
                        {
                            "qpc_ns": loop_started_ns,
                            "loop_interval_ms": loop_interval_ms,
                            "get_stats_ms": (
                                stats_finished_ns - stats_started_ns
                            ) / 1e6,
                            "queue_wait_ms": queue_wait_ms,
                            "poll_wait_ms": poll_wait_ms,
                            "write_ms": write_ms,
                            "action": action,
                            "driver_queue_depth": (
                                stats.queue_depth_blocks
                            ),
                            "blocks_consumed": stats.blocks_consumed,
                            "user_queue_depth": self.blocks.qsize(),
                        }
                    )
        except Exception as exc:
            self.write_errors += 1
            self.last_error = str(exc)
            self.stop_event.set()
        finally:
            _restore_thread_scheduling(scheduling)

    def stop(self, drain_timeout_s: float = 2.0) -> dict[str, object]:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=drain_timeout_s)
            if self.thread.is_alive():
                self.abort_event.set()
                while True:
                    try:
                        dropped = self.blocks.get_nowait()
                    except queue.Empty:
                        break
                    self.stop_dropped += 1
                    self.stop_dropped_source_block_indices.append(
                        dropped.source_block_index
                    )
                    self.dropped_residence_ms.append(
                        1000.0 * (time.perf_counter() - dropped.submitted_at_s)
                    )
                    if self.record_events:
                        self.events.append(
                            {
                                "event": "stop_timeout_drop",
                                "source_block_index": dropped.source_block_index,
                                "monotonic_s": time.perf_counter(),
                                "qpc_ns": time.perf_counter_ns(),
                                "user_queue_depth": self.blocks.qsize(),
                            }
                        )
                self.thread.join(timeout=max(0.1, 5.0 * self.poll_interval_s))
                if self.thread.is_alive() and self.last_error is None:
                    self.last_error = "Thread da ponte nao encerrou apos o timeout."
        self.stopped_at_s = time.perf_counter()
        try:
            self.last_stats = self.client.get_stats()
        except Exception as exc:
            if self.last_error is None:
                self.last_error = str(exc)
        finally:
            self.client.close()
        return self.metrics()

    @staticmethod
    def _distribution(values: list[float], prefix: str) -> dict[str, float]:
        if not values:
            return {
                f"{prefix}_mean": 0.0,
                f"{prefix}_p95": 0.0,
                f"{prefix}_max": 0.0,
            }
        samples = np.asarray(values, dtype=np.float64)
        return {
            f"{prefix}_mean": float(np.mean(samples)),
            f"{prefix}_p95": float(np.percentile(samples, 95)),
            f"{prefix}_max": float(np.max(samples)),
        }

    def metrics(self) -> dict[str, object]:
        duration_s = 0.0
        if self.first_submit_at_s is not None:
            end_s = self.stopped_at_s or self.last_submit_at_s or time.perf_counter()
            duration_s = max(0.0, end_s - self.first_submit_at_s)

        driver_depth = self._distribution(
            [float(value) for value in self.driver_depth_samples],
            "driver_queue_depth_blocks",
        )
        sent_residence = self._distribution(
            self.sent_residence_ms, "user_queue_residence_ms"
        )
        dropped_residence = self._distribution(
            self.dropped_residence_ms, "dropped_block_age_ms"
        )
        bridge_latency_ms = (
            sent_residence["user_queue_residence_ms_p95"]
            + driver_depth["driver_queue_depth_blocks_p95"]
            * 1000.0
            * PTC_PCM_FRAMES_PER_BLOCK
            / PTC_PCM_SAMPLE_RATE
        )

        metrics: dict[str, object] = {
            "submitted": self.submitted,
            "sent": self.sent,
            "user_queue_dropped_oldest": self.user_dropped_oldest,
            "user_queue_dropped_newest": self.user_dropped_newest,
            "user_queue_dropped_total": self.user_dropped,
            "drop_policy": self.drop_policy,
            "stop_timeout_dropped": self.stop_dropped,
            "write_errors": self.write_errors,
            "pending_user_blocks": self.blocks.qsize(),
            "user_queue_peak_blocks": self.user_queue_peak_blocks,
            "target_driver_depth": self.target_driver_depth,
            "poll_wait_strategy": self.poll_wait_strategy,
            "thread_scheduling_requested": self.thread_scheduling,
            "thread_scheduling_applied": self.thread_scheduling_applied,
            "thread_scheduling_error": self.thread_scheduling_error,
            "active_duration_s": duration_s,
            "submitted_rate_hz": self.submitted / duration_s if duration_s > 0 else 0.0,
            "sent_rate_hz": self.sent / duration_s if duration_s > 0 else 0.0,
            "bridge_buffer_latency_estimated_ms": bridge_latency_ms,
            "last_error": self.last_error,
            "sent_source_block_indices": self.sent_source_block_indices.copy(),
            "dropped_source_block_indices": (
                self.dropped_source_block_indices.copy()
            ),
            "stop_dropped_source_block_indices": (
                self.stop_dropped_source_block_indices.copy()
            ),
            "driver_stats": (
                None if self.last_stats is None else self.last_stats.__dict__.copy()
            ),
            "events": self.events.copy() if self.record_events else [],
            "loop_samples": (
                self.loop_samples.copy() if self.record_events else []
            ),
        }
        metrics.update(sent_residence)
        metrics.update(dropped_residence)
        metrics.update(driver_depth)
        return metrics
