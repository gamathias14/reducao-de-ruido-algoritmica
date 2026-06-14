from __future__ import annotations

import argparse
import hashlib
import json
import math
import socket
import struct
import sys
import time
import zlib
from pathlib import Path
from typing import BinaryIO

import numpy as np


PROTOCOL_MAGIC = b"PTCPCM2\0"
ACK_MAGIC = b"PTCACK2\0"
PROTOCOL_VERSION = 1
SAMPLE_RATE = 16_000
FRAMES_PER_BLOCK = 320
BYTES_PER_BLOCK = FRAMES_PER_BLOCK * 2
BLOCK_DURATION_NS = 20_000_000
PREAMBLE = struct.Struct("<8sIIIII")
PACKET_HEADER = struct.Struct("<QQII")
ACK = struct.Struct("<8sQII")

LOCAL_REPO_ROOT = Path(__file__).resolve().parents[2]
if (
    (LOCAL_REPO_ROOT / "realtime_audio").is_dir()
    and str(LOCAL_REPO_ROOT) not in sys.path
):
    sys.path.insert(0, str(LOCAL_REPO_ROOT))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def publish_ready(path: Path | None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("ready\n", encoding="ascii")
    temporary.replace(path)


def wait_for_start(path: Path | None, timeout_s: float) -> None:
    if path is None:
        return
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.05)
    raise TimeoutError(f"start marker was not created: {path}")


def receive_exact(stream: BinaryIO | socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.recv(remaining) if isinstance(stream, socket.socket) else stream.read(remaining)
        if not chunk:
            raise EOFError(f"stream ended with {remaining} bytes remaining")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def build_preamble(block_count: int) -> bytes:
    if block_count <= 0:
        raise ValueError("block_count must be positive")
    return PREAMBLE.pack(
        PROTOCOL_MAGIC,
        PROTOCOL_VERSION,
        SAMPLE_RATE,
        FRAMES_PER_BLOCK,
        BYTES_PER_BLOCK,
        block_count,
    )


def parse_preamble(payload: bytes) -> dict[str, int]:
    if len(payload) != PREAMBLE.size:
        raise ValueError("invalid preamble size")
    magic, version, sample_rate, frames, payload_bytes, block_count = (
        PREAMBLE.unpack(payload)
    )
    if magic != PROTOCOL_MAGIC or version != PROTOCOL_VERSION:
        raise ValueError("invalid protocol preamble")
    if (
        sample_rate != SAMPLE_RATE
        or frames != FRAMES_PER_BLOCK
        or payload_bytes != BYTES_PER_BLOCK
    ):
        raise ValueError("unexpected PCM contract")
    return {
        "version": version,
        "sample_rate": sample_rate,
        "frames_per_block": frames,
        "bytes_per_block": payload_bytes,
        "block_count": block_count,
    }


def build_packet(sequence: int, scheduled_offset_ns: int, pcm: bytes) -> bytes:
    if len(pcm) != BYTES_PER_BLOCK:
        raise ValueError("invalid PCM block size")
    checksum = zlib.crc32(pcm) & 0xFFFFFFFF
    return PACKET_HEADER.pack(
        sequence,
        scheduled_offset_ns,
        len(pcm),
        checksum,
    ) + pcm


def read_packet(stream: BinaryIO | socket.socket) -> tuple[int, int, bytes]:
    header = receive_exact(stream, PACKET_HEADER.size)
    sequence, scheduled_offset_ns, payload_bytes, checksum = (
        PACKET_HEADER.unpack(header)
    )
    if payload_bytes != BYTES_PER_BLOCK:
        raise ValueError(f"unexpected payload size: {payload_bytes}")
    pcm = receive_exact(stream, payload_bytes)
    actual_checksum = zlib.crc32(pcm) & 0xFFFFFFFF
    if actual_checksum != checksum:
        raise ValueError(
            f"CRC mismatch for sequence {sequence}: "
            f"{actual_checksum} != {checksum}"
        )
    return sequence, scheduled_offset_ns, pcm


def diagnostic_pcm_block(
    sequence: int,
    *,
    seed: int,
    variant: int,
    prefix_blocks: int,
) -> bytes:
    effective_seed = seed
    if sequence >= prefix_blocks:
        effective_seed += 10_000 * variant
    phase = sequence % 150
    if phase < 25 or phase >= 125:
        values = np.zeros(FRAMES_PER_BLOCK, dtype=np.float32)
    else:
        rng = np.random.default_rng(
            np.random.SeedSequence([effective_seed, sequence])
        )
        marker = rng.choice(
            np.asarray([-1.0, 1.0], dtype=np.float32),
            size=FRAMES_PER_BLOCK,
        )
        if phase < 75:
            values = 0.035 * marker
        else:
            absolute = sequence * FRAMES_PER_BLOCK + np.arange(
                FRAMES_PER_BLOCK
            )
            time_s = absolute.astype(np.float64) / SAMPLE_RATE
            carrier = (
                0.070 * np.sin(2.0 * math.pi * 220.0 * time_s)
                + 0.040 * np.sin(2.0 * math.pi * 440.0 * time_s + 0.3)
                + 0.020 * np.sin(2.0 * math.pi * 880.0 * time_s + 0.7)
            )
            values = carrier + 0.020 * marker
    pcm = np.rint(np.clip(values, -1.0, 1.0) * 32767.0).astype("<i2")
    return pcm.tobytes()


def wait_until_ns(deadline_ns: int) -> None:
    while True:
        remaining_ns = deadline_ns - time.perf_counter_ns()
        if remaining_ns <= 0:
            return
        if remaining_ns > 2_000_000:
            time.sleep((remaining_ns - 1_000_000) / 1_000_000_000.0)


def summarize_ms(values: list[float], prefix: str) -> dict[str, float]:
    if not values:
        return {
            f"{prefix}_mean": 0.0,
            f"{prefix}_p50": 0.0,
            f"{prefix}_p95": 0.0,
            f"{prefix}_p99": 0.0,
            f"{prefix}_max": 0.0,
        }
    samples = np.asarray(values, dtype=np.float64)
    return {
        f"{prefix}_mean": float(np.mean(samples)),
        f"{prefix}_p50": float(np.percentile(samples, 50)),
        f"{prefix}_p95": float(np.percentile(samples, 95)),
        f"{prefix}_p99": float(np.percentile(samples, 99)),
        f"{prefix}_max": float(np.max(samples)),
    }


def summarize_cadence(
    offsets_ms: list[float],
    intervals_ms: list[float],
) -> dict[str, float | int]:
    audio_duration_s = len(offsets_ms) * BLOCK_DURATION_NS / 1e9
    covered_duration_s = (
        0.0
        if not offsets_ms
        else (offsets_ms[-1] + BLOCK_DURATION_NS / 1e6) / 1000.0
    )
    return {
        "audio_duration_s": audio_duration_s,
        "covered_duration_s": covered_duration_s,
        "audio_to_covered_ratio": (
            0.0
            if covered_duration_s == 0.0
            else audio_duration_s / covered_duration_s
        ),
        "interval_stalls_over_30ms": sum(
            value > 30.0 for value in intervals_ms
        ),
        "interval_stalls_over_100ms": sum(
            value > 100.0 for value in intervals_ms
        ),
        "interval_bursts_under_10ms": sum(
            value < 10.0 for value in intervals_ms
        ),
    }


def run_server(args: argparse.Namespace) -> dict[str, object]:
    pcm_source: bytes | None = None
    source = "synthetic"
    pcm_file = getattr(args, "pcm_file", None)
    if pcm_file is not None:
        pcm_source = pcm_file.read_bytes()
        if not pcm_source or len(pcm_source) % BYTES_PER_BLOCK:
            raise ValueError(
                "PCM file must contain a positive whole number of blocks"
            )
        block_count = len(pcm_source) // BYTES_PER_BLOCK
        duration_s = block_count / 50.0
        source = "pcm_file"
    else:
        block_count = int(round(args.duration * 50.0))
        duration_s = args.duration
    send_lead_ms = int(getattr(args, "send_lead_ms", 0))
    if not 0 <= send_lead_ms < BLOCK_DURATION_NS // 1_000_000:
        raise ValueError("send lead must be between 0 and 19 ms")
    send_lead_ns = send_lead_ms * 1_000_000
    trace: list[dict[str, float | int]] = []
    input_hash = hashlib.sha256()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((args.bind, args.port))
        listener.listen(1)
        listener.settimeout(args.accept_timeout)
        accepted_at = time.perf_counter()
        connection, peer = listener.accept()
        accept_wait_s = time.perf_counter() - accepted_at
        with connection:
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            connection.settimeout(args.socket_timeout)
            connection.sendall(build_preamble(block_count))
            stream_start_ns = time.perf_counter_ns() + args.start_delay_ms * 1_000_000
            initial_burst_blocks = min(
                block_count,
                max(0, getattr(args, "initial_burst_blocks", 0)),
            )
            previous_send_ns: int | None = None
            for sequence in range(block_count):
                scheduled_offset_ns = sequence * BLOCK_DURATION_NS
                deadline_ns = (
                    stream_start_ns
                    if sequence < initial_burst_blocks
                    else (
                        stream_start_ns
                        + max(0, scheduled_offset_ns - send_lead_ns)
                    )
                )
                wait_until_ns(deadline_ns)
                if pcm_source is None:
                    pcm = diagnostic_pcm_block(
                        sequence,
                        seed=args.seed,
                        variant=args.variant,
                        prefix_blocks=args.prefix_blocks,
                    )
                else:
                    start = sequence * BYTES_PER_BLOCK
                    pcm = pcm_source[start : start + BYTES_PER_BLOCK]
                send_started_ns = time.perf_counter_ns()
                connection.sendall(
                    build_packet(sequence, scheduled_offset_ns, pcm)
                )
                send_finished_ns = time.perf_counter_ns()
                input_hash.update(pcm)
                trace.append(
                    {
                        "sequence": sequence,
                        "scheduled_offset_ms": scheduled_offset_ns / 1e6,
                        "send_offset_ms": (
                            send_started_ns - stream_start_ns
                        )
                        / 1e6,
                        "send_lateness_ms": (
                            send_started_ns - deadline_ns
                        )
                        / 1e6,
                        "send_interval_ms": (
                            0.0
                            if previous_send_ns is None
                            else (send_started_ns - previous_send_ns) / 1e6
                        ),
                        "send_call_ms": (
                            send_finished_ns - send_started_ns
                        )
                        / 1e6,
                    }
                )
                previous_send_ns = send_started_ns
            ack_payload = receive_exact(connection, ACK.size)
            ack_magic, ack_received, ack_sequence_errors, ack_crc_errors = (
                ACK.unpack(ack_payload)
            )
            if ack_magic != ACK_MAGIC:
                raise ValueError("invalid receiver ACK")

    intervals = [
        float(row["send_interval_ms"])
        for row in trace[1:]
    ]
    offsets = [float(row["send_offset_ms"]) for row in trace]
    lateness = [float(row["send_lateness_ms"]) for row in trace]
    calls = [float(row["send_call_ms"]) for row in trace]
    summary: dict[str, object] = {
        "role": "server",
        "source": source,
        "peer": f"{peer[0]}:{peer[1]}",
        "accept_wait_s": accept_wait_s,
        "duration_s": duration_s,
        "block_count": block_count,
        "sample_count": block_count * FRAMES_PER_BLOCK,
        "sample_rate": SAMPLE_RATE,
        "frames_per_block": FRAMES_PER_BLOCK,
        "variant": args.variant,
        "prefix_blocks": args.prefix_blocks,
        "start_delay_ms": args.start_delay_ms,
        "initial_burst_blocks": initial_burst_blocks,
        "send_lead_ms": send_lead_ms,
        "input_sha256": input_hash.hexdigest(),
        "receiver_ack": {
            "received": ack_received,
            "sequence_errors": ack_sequence_errors,
            "crc_errors": ack_crc_errors,
        },
    }
    summary.update(summarize_ms(intervals, "send_interval_ms"))
    summary.update(summarize_cadence(offsets, intervals))
    summary.update(summarize_ms(lateness, "send_lateness_ms"))
    summary.update(summarize_ms(calls, "send_call_ms"))
    if args.trace:
        write_json(args.trace, trace)
    return summary


def pcm16_to_float32(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


def run_client(args: argparse.Namespace) -> dict[str, object]:
    processor = None
    if args.method != "capture_only":
        from realtime_audio.windows_realtime import (
            RealtimeBlockProcessor,
            RealtimeConfig,
        )

        processor = RealtimeBlockProcessor(
            RealtimeConfig(method=args.method)
        )
    bridge_writer = None
    bridge_metrics: dict[str, object] | None = None
    if getattr(args, "bridge", False):
        from realtime_audio.ptc_pcm_bridge import (
            BridgePacedWriter,
            PtcPcmBridgeClient,
            WindowsBridgeBackend,
        )

        bridge_writer = BridgePacedWriter(
            PtcPcmBridgeClient(
                WindowsBridgeBackend(
                    device_path=getattr(args, "bridge_path", None)
                )
            ),
            target_driver_depth=args.bridge_target_depth,
            user_queue_blocks=args.bridge_user_queue,
            poll_interval_s=args.bridge_poll_interval_ms / 1000.0,
            record_events=args.bridge_trace,
            drop_policy="oldest",
            thread_scheduling=args.bridge_thread_scheduling,
            poll_wait_strategy=args.bridge_poll_wait_strategy,
        )
        bridge_writer.start()

    publish_ready(getattr(args, "ready_file", None))
    wait_for_start(
        getattr(args, "start_file", None),
        getattr(args, "start_wait_timeout", 60.0),
    )

    deadline = time.monotonic() + args.connect_timeout
    connection: socket.socket | None = None
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            connection = socket.create_connection(
                (args.host, args.port),
                timeout=args.socket_timeout,
            )
            break
        except OSError as exc:
            last_error = exc
            time.sleep(0.25)
    if connection is None:
        raise TimeoutError(f"could not connect to host: {last_error}")

    sequence_errors = 0
    crc_errors = 0
    rows: list[dict[str, float | int]] = []
    input_hash = hashlib.sha256()
    output_hash = hashlib.sha256()
    input_prefix_hash = hashlib.sha256()
    output_prefix_hash = hashlib.sha256()
    previous_receive_ns: int | None = None
    try:
        with connection:
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            connection.settimeout(args.socket_timeout)
            contract = parse_preamble(receive_exact(connection, PREAMBLE.size))
            first_receive_ns: int | None = None
            expected_sequence = 0
            for _ in range(contract["block_count"]):
                try:
                    sequence, scheduled_offset_ns, pcm = read_packet(connection)
                except ValueError:
                    crc_errors += 1
                    raise
                receive_ns = time.perf_counter_ns()
                if first_receive_ns is None:
                    first_receive_ns = receive_ns
                if sequence != expected_sequence:
                    sequence_errors += 1
                expected_sequence = sequence + 1
                input_hash.update(pcm)
                block = pcm16_to_float32(pcm)
                processing_started_ns = time.perf_counter_ns()
                if processor is None:
                    output = block
                else:
                    output, _ = processor.process_block(block)
                processing_ms = (
                    time.perf_counter_ns() - processing_started_ns
                ) / 1e6
                if bridge_writer is not None:
                    bridge_writer.submit(
                        output,
                        source_block_index=sequence,
                    )
                output_bytes = np.asarray(output, dtype="<f4").tobytes()
                output_hash.update(output_bytes)
                if sequence < args.prefix_blocks:
                    input_prefix_hash.update(pcm)
                    output_prefix_hash.update(output_bytes)
                rows.append(
                    {
                        "sequence": sequence,
                        "scheduled_offset_ms": scheduled_offset_ns / 1e6,
                        "receive_qpc_ns": receive_ns,
                        "receive_offset_ms": (
                            0.0
                            if first_receive_ns is None
                            else (receive_ns - first_receive_ns) / 1e6
                        ),
                        "receive_interval_ms": (
                            0.0
                            if previous_receive_ns is None
                            else (receive_ns - previous_receive_ns) / 1e6
                        ),
                        "processing_ms": processing_ms,
                    }
                )
                previous_receive_ns = receive_ns
            connection.sendall(
                ACK.pack(
                    ACK_MAGIC,
                    len(rows),
                    sequence_errors,
                    crc_errors,
                )
            )
    finally:
        if bridge_writer is not None:
            bridge_metrics = bridge_writer.stop(drain_timeout_s=5.0)
        if processor is not None:
            processor.close()

    intervals = [
        float(row["receive_interval_ms"])
        for row in rows[1:]
    ]
    offsets = [float(row["receive_offset_ms"]) for row in rows]
    phase_error = [
        float(row["receive_offset_ms"]) - float(row["scheduled_offset_ms"])
        for row in rows
    ]
    processing = [float(row["processing_ms"]) for row in rows]
    summary: dict[str, object] = {
        "role": "client",
        "method": args.method,
        "block_count": len(rows),
        "sample_count": len(rows) * FRAMES_PER_BLOCK,
        "expected_block_count": contract["block_count"],
        "sequence_errors": sequence_errors,
        "crc_errors": crc_errors,
        "framing_errors": int(
            contract["frames_per_block"] != FRAMES_PER_BLOCK
        ),
        "input_sha256": input_hash.hexdigest(),
        "output_float32_sha256": output_hash.hexdigest(),
        "input_prefix_sha256": input_prefix_hash.hexdigest(),
        "output_prefix_float32_sha256": output_prefix_hash.hexdigest(),
        "prefix_blocks": args.prefix_blocks,
    }
    summary.update(summarize_ms(intervals, "receive_interval_ms"))
    summary.update(summarize_cadence(offsets, intervals))
    summary.update(summarize_ms(phase_error, "receive_phase_error_ms"))
    summary.update(summarize_ms(processing, "processing_ms"))
    summary["processing_over_20ms"] = sum(value > 20.0 for value in processing)
    if bridge_metrics is not None:
        summary["bridge"] = bridge_metrics
    if args.trace:
        write_json(args.trace, rows)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("server", "client"))
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--host", default="10.0.2.2")
    parser.add_argument("--port", type=int, default=35270)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--pcm-file", type=Path)
    parser.add_argument("--seed", type=int, default=3527)
    parser.add_argument("--variant", type=int, choices=(0, 1), default=0)
    parser.add_argument("--prefix-blocks", type=int, default=500)
    parser.add_argument(
        "--method",
        choices=("capture_only", "bypass", "rnnoise"),
        default="capture_only",
    )
    parser.add_argument("--bridge", action="store_true")
    parser.add_argument("--bridge-path")
    parser.add_argument("--bridge-target-depth", type=int, default=2)
    parser.add_argument("--bridge-user-queue", type=int, default=4)
    parser.add_argument("--bridge-poll-interval-ms", type=float, default=2.0)
    parser.add_argument(
        "--bridge-thread-scheduling",
        choices=("normal", "mmcss"),
        default="normal",
    )
    parser.add_argument(
        "--bridge-poll-wait-strategy",
        choices=("sleep", "yield"),
        default="sleep",
    )
    parser.add_argument("--bridge-trace", action="store_true")
    parser.add_argument("--start-delay-ms", type=int, default=250)
    parser.add_argument("--initial-burst-blocks", type=int, default=0)
    parser.add_argument("--send-lead-ms", type=int, default=0)
    parser.add_argument("--accept-timeout", type=float, default=60.0)
    parser.add_argument("--connect-timeout", type=float, default=60.0)
    parser.add_argument("--socket-timeout", type=float, default=30.0)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--start-file", type=Path)
    parser.add_argument("--start-wait-timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result: dict[str, object] = {"status": "failed", "role": args.role}
    try:
        summary = run_server(args) if args.role == "server" else run_client(args)
        result = {"status": "completed", **summary}
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        write_json(args.output, result)
        raise
    write_json(args.output, result)


if __name__ == "__main__":
    main()
