from __future__ import annotations

import argparse
import ctypes
import csv
import hashlib
import json
import math
import struct
import sys
import time
import wave
from collections import deque
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from realtime_audio.ptc_pcm_bridge import (
    IOCTL_PTC_PCM_CONFIGURE,
    IOCTL_PTC_PCM_GET_STATS,
    IOCTL_PTC_PCM_RESET,
    IOCTL_PTC_PCM_WRITE,
    PTC_PCM_BYTES_PER_BLOCK,
    PTC_PCM_CHANNELS,
    PTC_PCM_FRAMES_PER_BLOCK,
    PTC_PCM_QUEUE_CAPACITY_BLOCKS,
    PTC_PCM_SAMPLE_RATE,
    PtcPcmBridgeClient,
    BridgePacedWriter,
)


DEFAULT_INPUT = (
    ROOT
    / "tmp"
    / "dfn_native"
    / "wasapi_worker_bench"
    / "results"
    / "b3_mixed_60s_worker"
    / "output_full_raw48.wav"
)
DEFAULT_OUTPUT_DIR = ROOT / "resultados" / "dfn3_pcm_bridge_simulator"
DFN3_SAMPLE_RATE = 48_000
DFN3_FRAME_SAMPLES = 480
DFN3_FRAMES_PER_BRIDGE_BLOCK = 2
BRIDGE_BLOCK_MS = 1000.0 * PTC_PCM_FRAMES_PER_BLOCK / PTC_PCM_SAMPLE_RATE
STATS_STRUCT = struct.Struct("<8I10Q")


class WindowsTimingScope:
    def __init__(self, *, process_priority: str, thread_priority: str, period_ms: int) -> None:
        self.process_priority = process_priority
        self.thread_priority = thread_priority
        self.period_ms = period_ms
        self.time_period_applied = False
        self.process_priority_applied = False
        self.thread_priority_applied = False
        self.errors: list[str] = []

    def __enter__(self) -> "WindowsTimingScope":
        if sys.platform != "win32":
            return self
        try:
            winmm = ctypes.WinDLL("winmm", use_last_error=True)
            if self.period_ms > 0 and winmm.timeBeginPeriod(self.period_ms) == 0:
                self.time_period_applied = True
        except Exception as exc:
            self.errors.append(f"timeBeginPeriod: {type(exc).__name__}: {exc}")
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCurrentProcess.argtypes = []
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            kernel32.GetCurrentThread.argtypes = []
            kernel32.GetCurrentThread.restype = ctypes.c_void_p
            kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            kernel32.SetPriorityClass.restype = ctypes.c_int
            kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
            kernel32.SetThreadPriority.restype = ctypes.c_int
            if self.process_priority == "high":
                HIGH_PRIORITY_CLASS = 0x00000080
                ok = kernel32.SetPriorityClass(
                    kernel32.GetCurrentProcess(),
                    HIGH_PRIORITY_CLASS,
                )
                self.process_priority_applied = bool(ok)
                if not ok:
                    self.errors.append(f"SetPriorityClass failed: {ctypes.get_last_error()}")
            else:
                self.process_priority_applied = True
            if self.thread_priority == "highest":
                THREAD_PRIORITY_HIGHEST = 2
                ok = kernel32.SetThreadPriority(
                    kernel32.GetCurrentThread(),
                    THREAD_PRIORITY_HIGHEST,
                )
                self.thread_priority_applied = bool(ok)
                if not ok:
                    self.errors.append(f"SetThreadPriority failed: {ctypes.get_last_error()}")
            else:
                self.thread_priority_applied = True
        except Exception as exc:
            self.errors.append(f"priority: {type(exc).__name__}: {exc}")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if sys.platform != "win32" or not self.time_period_applied:
            return
        try:
            ctypes.WinDLL("winmm", use_last_error=True).timeEndPeriod(self.period_ms)
        except Exception:
            pass

    def metrics(self) -> dict[str, object]:
        return {
            "time_period_ms": self.period_ms,
            "time_period_applied": self.time_period_applied,
            "process_priority": self.process_priority,
            "process_priority_applied": self.process_priority_applied,
            "submit_thread_priority": self.thread_priority,
            "submit_thread_priority_applied": self.thread_priority_applied,
            "errors": self.errors,
        }


def read_pcm16_mono_wav(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frames = handle.getnframes()
        payload = handle.readframes(frames)
    if channels != 1 or sample_width != 2:
        raise ValueError(
            f"Expected mono PCM16 WAV, got channels={channels}, width={sample_width}."
        )
    samples = np.frombuffer(payload, dtype="<i2").astype(np.float32) / 32768.0
    return sample_rate, samples


def write_pcm16_mono_wav(path: Path, sample_rate: int, blocks: Iterable[np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(np.asarray(block, dtype="<i2").tobytes() for block in blocks)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(payload)


def downsample_48k_to_16k_blocks(samples48: np.ndarray) -> list[np.ndarray]:
    source = np.asarray(samples48, dtype=np.float32).reshape(-1)
    block48 = DFN3_FRAME_SAMPLES * DFN3_FRAMES_PER_BRIDGE_BLOCK
    remainder = source.size % block48
    if remainder:
        source = np.pad(source, (0, block48 - remainder))

    blocks: list[np.ndarray] = []
    for offset in range(0, source.size, block48):
        chunk = source[offset : offset + block48]
        # The simulator gate is about pacing/contract, not final audio quality.
        # Averaging each group of three samples gives a deterministic 48k -> 16k
        # conversion without adding another DSP dependency to this bridge test.
        block16 = chunk.reshape(PTC_PCM_FRAMES_PER_BLOCK, 3).mean(axis=1)
        blocks.append(np.asarray(block16, dtype=np.float32))
    return blocks


def float_blocks_to_pcm16_bytes(blocks: Iterable[np.ndarray]) -> bytes:
    payload = bytearray()
    for block in blocks:
        values = np.asarray(block, dtype=np.float32).reshape(-1)
        values = np.nan_to_num(values, nan=0.0, posinf=1.0, neginf=-1.0)
        values = np.clip(values, -1.0, 1.0)
        payload.extend(np.rint(values * 32767.0).astype("<i2").tobytes())
    return bytes(payload)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


class SimulatedPcmBridgeBackend:
    def __init__(
        self,
        *,
        consumer_start_depth: int = 2,
        consume_interval_s: float = BRIDGE_BLOCK_MS / 1000.0,
    ) -> None:
        self.consumer_start_depth = max(1, consumer_start_depth)
        self.consume_interval_s = consume_interval_s
        self.opened = False
        self.configured = False
        self.producer_connected = False
        self.queue: deque[bytes] = deque()
        self.consumer_started = False
        self.next_consume_s: float | None = None
        self.blocks_accepted = 0
        self.blocks_dropped = 0
        self.blocks_consumed = 0
        self.bytes_accepted = 0
        self.bytes_consumed = 0
        self.underruns = 0
        self.overruns = 0
        self.rejected_requests = 0
        self.sequence_errors = 0
        self.last_accepted_sequence = 0
        self.expected_sequence = 0
        self.accepted_payload = bytearray()
        self.consumed_payload = bytearray()
        self.depth_samples: list[int] = []
        self.consume_intervals_ms: list[float] = []
        self.consumer_lateness_ms: list[float] = []
        self._last_consume_s: float | None = None

    def open(self) -> None:
        self.opened = True
        self.producer_connected = True

    def close(self) -> None:
        self._advance_consumer(time.perf_counter())
        self.producer_connected = False
        self.opened = False

    def ioctl(self, code: int, input_data: bytes = b"", output_size: int = 0) -> bytes:
        now = time.perf_counter()
        self._advance_consumer(now)
        if code == IOCTL_PTC_PCM_CONFIGURE:
            self._configure(input_data)
            return b""
        if code == IOCTL_PTC_PCM_RESET:
            self._reset()
            return b""
        if code == IOCTL_PTC_PCM_WRITE:
            self._write(input_data, now)
            return b""
        if code == IOCTL_PTC_PCM_GET_STATS:
            return self._stats_payload()
        self.rejected_requests += 1
        return b""

    def _configure(self, payload: bytes) -> None:
        if len(payload) != 24:
            self.rejected_requests += 1
            return
        (
            version,
            _struct_size,
            sample_rate,
            channels,
            bits_per_sample,
            frames_per_block,
            capacity,
        ) = struct.unpack("<IIIHHII", payload)
        ok = (
            version == 1
            and sample_rate == PTC_PCM_SAMPLE_RATE
            and channels == PTC_PCM_CHANNELS
            and bits_per_sample == 16
            and frames_per_block == PTC_PCM_FRAMES_PER_BLOCK
            and capacity == PTC_PCM_QUEUE_CAPACITY_BLOCKS
        )
        self.configured = ok
        if not ok:
            self.rejected_requests += 1

    def _reset(self) -> None:
        self.queue.clear()
        self.consumer_started = False
        self.next_consume_s = None
        self.blocks_accepted = 0
        self.blocks_dropped = 0
        self.blocks_consumed = 0
        self.bytes_accepted = 0
        self.bytes_consumed = 0
        self.underruns = 0
        self.overruns = 0
        self.rejected_requests = 0
        self.sequence_errors = 0
        self.last_accepted_sequence = 0
        self.expected_sequence = 0
        self.accepted_payload.clear()
        self.consumed_payload.clear()
        self.depth_samples.clear()
        self.consume_intervals_ms.clear()
        self.consumer_lateness_ms.clear()
        self._last_consume_s = None

    def _write(self, payload: bytes, now: float) -> None:
        if not self.configured or len(payload) != 664:
            self.rejected_requests += 1
            return
        version, _struct_size, sequence, payload_bytes, _flags = struct.unpack(
            "<IIQII", payload[:24]
        )
        if version != 1 or payload_bytes != PTC_PCM_BYTES_PER_BLOCK:
            self.rejected_requests += 1
            return
        if sequence != self.expected_sequence:
            self.sequence_errors += 1
            self.expected_sequence = sequence + 1
        else:
            self.expected_sequence += 1
        pcm = payload[24:]
        if len(self.queue) >= PTC_PCM_QUEUE_CAPACITY_BLOCKS:
            self.overruns += 1
            self.blocks_dropped += 1
            return
        self.queue.append(pcm)
        self.accepted_payload.extend(pcm)
        self.blocks_accepted += 1
        self.bytes_accepted += len(pcm)
        self.last_accepted_sequence = sequence
        if not self.consumer_started and len(self.queue) >= self.consumer_start_depth:
            self.consumer_started = True
            self.next_consume_s = now + self.consume_interval_s
        self.depth_samples.append(len(self.queue))

    def _advance_consumer(self, now: float) -> None:
        if not self.consumer_started or self.next_consume_s is None:
            return
        while self.next_consume_s <= now:
            lateness_ms = max(0.0, 1000.0 * (now - self.next_consume_s))
            if self.queue:
                pcm = self.queue.popleft()
                self.consumed_payload.extend(pcm)
                self.blocks_consumed += 1
                self.bytes_consumed += len(pcm)
                if self._last_consume_s is not None:
                    self.consume_intervals_ms.append(
                        1000.0 * (self.next_consume_s - self._last_consume_s)
                    )
                self._last_consume_s = self.next_consume_s
                self.consumer_lateness_ms.append(lateness_ms)
            else:
                self.underruns += 1
            self.depth_samples.append(len(self.queue))
            self.next_consume_s += self.consume_interval_s

    def _stats_payload(self) -> bytes:
        return STATS_STRUCT.pack(
            1,
            STATS_STRUCT.size,
            1 if self.configured else 0,
            1 if self.producer_connected else 0,
            len(self.queue),
            PTC_PCM_QUEUE_CAPACITY_BLOCKS,
            0,
            0,
            self.blocks_accepted,
            self.blocks_dropped,
            self.blocks_consumed,
            self.bytes_accepted,
            self.bytes_consumed,
            self.underruns,
            self.overruns,
            self.rejected_requests,
            self.sequence_errors,
            self.last_accepted_sequence,
        )

    def metrics(self) -> dict[str, object]:
        return {
            "blocks_accepted": self.blocks_accepted,
            "blocks_dropped": self.blocks_dropped,
            "blocks_consumed": self.blocks_consumed,
            "queue_depth_blocks": len(self.queue),
            "queue_capacity_blocks": PTC_PCM_QUEUE_CAPACITY_BLOCKS,
            "bytes_accepted": self.bytes_accepted,
            "bytes_consumed": self.bytes_consumed,
            "underruns": self.underruns,
            "overruns": self.overruns,
            "rejected_requests": self.rejected_requests,
            "sequence_errors": self.sequence_errors,
            "last_accepted_sequence": self.last_accepted_sequence,
            "queue_depth_min": min(self.depth_samples) if self.depth_samples else 0,
            "queue_depth_mean": (
                float(np.mean(self.depth_samples)) if self.depth_samples else 0.0
            ),
            "queue_depth_p95": percentile([float(v) for v in self.depth_samples], 0.95),
            "queue_depth_max": max(self.depth_samples) if self.depth_samples else 0,
            "consumer_interval_p99_ms": percentile(self.consume_intervals_ms, 0.99),
            "consumer_interval_max_ms": (
                max(self.consume_intervals_ms) if self.consume_intervals_ms else 0.0
            ),
            "consumer_lateness_p99_ms": percentile(self.consumer_lateness_ms, 0.99),
            "consumer_lateness_max_ms": (
                max(self.consumer_lateness_ms) if self.consumer_lateness_ms else 0.0
            ),
            "accepted_payload_sha256": hashlib.sha256(self.accepted_payload).hexdigest(),
            "consumed_payload_sha256": hashlib.sha256(self.consumed_payload).hexdigest(),
        }


def pace_until(deadline_s: float) -> None:
    while True:
        remaining = deadline_s - time.perf_counter()
        if remaining <= 0:
            return
        if remaining > 0.003:
            time.sleep(remaining - 0.001)
        else:
            time.sleep(0)


def run(args: argparse.Namespace) -> dict[str, object]:
    sample_rate, samples48 = read_pcm16_mono_wav(args.input)
    if sample_rate != DFN3_SAMPLE_RATE:
        raise ValueError(f"Expected 48 kHz DFN3 output, got {sample_rate} Hz.")
    blocks = downsample_48k_to_16k_blocks(samples48)
    if args.max_blocks is not None:
        blocks = blocks[: args.max_blocks]
        samples48 = samples48[: args.max_blocks * DFN3_FRAME_SAMPLES * DFN3_FRAMES_PER_BRIDGE_BLOCK]
    bridge_payload = float_blocks_to_pcm16_bytes(blocks)
    expected_blocks = len(blocks)

    with WindowsTimingScope(
        process_priority=args.process_priority,
        thread_priority=args.submit_thread_priority,
        period_ms=args.time_period_ms,
    ) as timing_scope:
        backend = SimulatedPcmBridgeBackend(consumer_start_depth=args.bridge_target_depth)
        writer = BridgePacedWriter(
            PtcPcmBridgeClient(backend),
            target_driver_depth=args.bridge_target_depth,
            user_queue_blocks=args.bridge_user_queue,
            poll_interval_s=args.bridge_poll_interval_ms / 1000.0,
            record_events=args.trace,
            drop_policy=args.bridge_drop_policy,
            thread_scheduling=args.writer_thread_scheduling,
            poll_wait_strategy=args.bridge_poll_wait_strategy,
        )

        submit_rows: list[dict[str, float | int]] = []
        submit_intervals_ms: list[float] = []
        writer.start()
        start_s = time.perf_counter()
        last_submit_s: float | None = None
        for index, block in enumerate(blocks):
            deadline_s = start_s + index * (BRIDGE_BLOCK_MS / 1000.0)
            pace_until(deadline_s)
            before_s = time.perf_counter()
            writer.submit(block, source_block_index=index)
            after_s = time.perf_counter()
            if last_submit_s is not None:
                submit_intervals_ms.append(1000.0 * (before_s - last_submit_s))
            last_submit_s = before_s
            submit_rows.append(
                {
                    "block_index": index,
                    "target_elapsed_ms": index * BRIDGE_BLOCK_MS,
                    "submit_elapsed_ms": 1000.0 * (before_s - start_s),
                    "submit_call_ms": 1000.0 * (after_s - before_s),
                }
            )

        send_deadline = time.monotonic() + args.drain_timeout_s
        while writer.sent < expected_blocks and time.monotonic() < send_deadline:
            time.sleep(0.002)
        writer_metrics = writer.stop(drain_timeout_s=args.drain_timeout_s)
        backend_metrics = backend.metrics()
        timing_metrics = timing_scope.metrics()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    submitted_csv = args.output_dir / "submitted_blocks.csv"
    with submitted_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "block_index",
            "target_elapsed_ms",
            "submit_elapsed_ms",
            "submit_call_ms",
        ]
        csv_writer = csv.DictWriter(handle, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(submit_rows)

    write_pcm16_mono_wav(
        args.output_dir / "bridge_input_pcm16_16k.wav",
        PTC_PCM_SAMPLE_RATE,
        [
            np.frombuffer(
                bridge_payload[i : i + PTC_PCM_BYTES_PER_BLOCK],
                dtype="<i2",
            )
            for i in range(0, len(bridge_payload), PTC_PCM_BYTES_PER_BLOCK)
        ],
    )

    submit_interval_p99 = percentile(submit_intervals_ms, 0.99)
    submit_interval_max = max(submit_intervals_ms) if submit_intervals_ms else 0.0
    accepted_hash = backend_metrics["accepted_payload_sha256"]
    bridge_hash = hashlib.sha256(bridge_payload).hexdigest()
    gate_reasons = []
    if expected_blocks != int(round(len(samples48) / (DFN3_SAMPLE_RATE * 0.02))):
        gate_reasons.append("unexpected_block_count")
    if writer_metrics["submitted"] != expected_blocks:
        gate_reasons.append("submitted_count_mismatch")
    if writer_metrics["sent"] != expected_blocks:
        gate_reasons.append("sent_count_mismatch")
    if writer_metrics["user_queue_dropped_total"] != 0:
        gate_reasons.append("user_queue_drops")
    if writer_metrics["write_errors"] != 0 or writer_metrics["last_error"]:
        gate_reasons.append("writer_error")
    if backend_metrics["blocks_accepted"] != expected_blocks:
        gate_reasons.append("backend_accept_count_mismatch")
    for key in ("blocks_dropped", "underruns", "overruns", "rejected_requests", "sequence_errors"):
        if backend_metrics[key] != 0:
            gate_reasons.append(key)
    if accepted_hash != bridge_hash:
        gate_reasons.append("accepted_hash_mismatch")
    if submit_interval_p99 > args.submit_p99_limit_ms:
        gate_reasons.append("submit_interval_p99_over_limit")
    if submit_interval_max > args.submit_max_limit_ms:
        gate_reasons.append("submit_interval_max_over_limit")

    status = "PASS" if not gate_reasons else "CHECK"
    summary: dict[str, object] = {
        "phase": "R13_DFN3_PCM_BRIDGE_SIMULATOR",
        "status": status,
        "gate_reasons": gate_reasons,
        "input": str(args.input),
        "output_dir": str(args.output_dir),
        "dfn3_sample_rate": DFN3_SAMPLE_RATE,
        "dfn3_frame_samples": DFN3_FRAME_SAMPLES,
        "bridge_sample_rate": PTC_PCM_SAMPLE_RATE,
        "bridge_frames_per_block": PTC_PCM_FRAMES_PER_BLOCK,
        "bridge_block_ms": BRIDGE_BLOCK_MS,
        "expected_bridge_blocks": expected_blocks,
        "source_duration_s": float(len(samples48) / DFN3_SAMPLE_RATE),
        "source_payload_sha256": hashlib.sha256(
            np.rint(np.clip(samples48, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        ).hexdigest(),
        "bridge_payload_sha256": bridge_hash,
        "submit_interval_p99_ms": submit_interval_p99,
        "submit_interval_max_ms": submit_interval_max,
        "submit_call_p99_ms": percentile(
            [float(row["submit_call_ms"]) for row in submit_rows],
            0.99,
        ),
        "submit_call_max_ms": max(
            [float(row["submit_call_ms"]) for row in submit_rows],
            default=0.0,
        ),
        "timing_scope": timing_metrics,
        "writer": writer_metrics,
        "backend": backend_metrics,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Feed DFN3 48 kHz output into a user-mode PCM bridge v1 simulator."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bridge-target-depth", type=int, default=2)
    parser.add_argument("--bridge-user-queue", type=int, default=4)
    parser.add_argument("--bridge-poll-interval-ms", type=float, default=2.0)
    parser.add_argument("--bridge-drop-policy", choices=["oldest", "newest"], default="oldest")
    parser.add_argument("--bridge-poll-wait-strategy", choices=["sleep", "yield"], default="sleep")
    parser.add_argument("--writer-thread-scheduling", choices=["normal", "mmcss"], default="mmcss")
    parser.add_argument("--process-priority", choices=["normal", "high"], default="high")
    parser.add_argument("--submit-thread-priority", choices=["normal", "highest"], default="highest")
    parser.add_argument("--time-period-ms", type=int, default=1)
    parser.add_argument("--submit-p99-limit-ms", type=float, default=25.0)
    parser.add_argument("--submit-max-limit-ms", type=float, default=100.0)
    parser.add_argument("--drain-timeout-s", type=float, default=5.0)
    parser.add_argument("--max-blocks", type=int, default=None)
    parser.add_argument("--trace", action="store_true")
    return parser.parse_args()


def main() -> int:
    summary = run(parse_args())
    backend = summary["backend"]
    writer = summary["writer"]
    print(
        "{status} | blocks={blocks} | sent={sent} | accepted={accepted} | "
        "underruns={underruns} | depth_p95={depth_p95:.3f} | submit_p99={submit_p99:.3f} ms".format(
            status=summary["status"],
            blocks=summary["expected_bridge_blocks"],
            sent=writer["sent"],
            accepted=backend["blocks_accepted"],
            underruns=backend["underruns"],
            depth_p95=backend["queue_depth_p95"],
            submit_p99=summary["submit_interval_p99_ms"],
        )
    )
    print(f"summary: {summary['output_dir']}\\summary.json")
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
