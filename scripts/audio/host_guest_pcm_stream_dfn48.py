from __future__ import annotations

import argparse
import hashlib
import json
import socket
import struct
import threading
import time
import wave
import zlib
from pathlib import Path
from typing import BinaryIO


PROTOCOL_MAGIC = b"PTCDFN3\0"
ACK_MAGIC = b"PTCDAK3\0"
UDP_HELLO_MAGIC = b"PTCUHLO\0"
PROTOCOL_VERSION = 1
SAMPLE_RATE = 48_000
FRAMES_PER_BLOCK = 480
SAMPLE_WIDTH_BYTES = 2
CHANNELS = 1
BYTES_PER_BLOCK = FRAMES_PER_BLOCK * SAMPLE_WIDTH_BYTES
BLOCK_DURATION_NS = 10_000_000
BLOCKS_PER_SECOND = 100

PREAMBLE = struct.Struct("<8sIIIIQ")
PACKET_HEADER = struct.Struct("<QQII")
ACK = struct.Struct("<8sQIIII")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def receive_exact(stream: BinaryIO | socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = (
            stream.recv(remaining)
            if isinstance(stream, socket.socket)
            else stream.read(remaining)
        )
        if not chunk:
            raise EOFError(f"stream ended with {remaining} bytes remaining")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pcm16_mono_48k(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        if channels != CHANNELS:
            raise ValueError(f"expected mono WAV, got {channels} channels")
        if sample_width != SAMPLE_WIDTH_BYTES:
            raise ValueError(
                f"expected PCM16 WAV, got {sample_width * 8} bit samples"
            )
        if sample_rate != SAMPLE_RATE:
            raise ValueError(f"expected 48 kHz WAV, got {sample_rate} Hz")
        if frame_count <= 0 or frame_count % FRAMES_PER_BLOCK:
            raise ValueError(
                "WAV frame count must be a positive whole number of "
                f"{FRAMES_PER_BLOCK}-sample blocks"
            )
        payload = wav.readframes(frame_count)
    expected_bytes = frame_count * SAMPLE_WIDTH_BYTES
    if len(payload) != expected_bytes:
        raise ValueError(
            f"WAV payload length mismatch: {len(payload)} != {expected_bytes}"
        )
    return payload, frame_count // FRAMES_PER_BLOCK


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
    return {
        "version": version,
        "sample_rate": sample_rate,
        "frames_per_block": frames,
        "bytes_per_block": payload_bytes,
        "block_count": block_count,
    }


def validate_contract(contract: dict[str, int]) -> int:
    framing_errors = 0
    if contract.get("sample_rate") != SAMPLE_RATE:
        framing_errors += 1
    if contract.get("frames_per_block") != FRAMES_PER_BLOCK:
        framing_errors += 1
    if contract.get("bytes_per_block") != BYTES_PER_BLOCK:
        framing_errors += 1
    return framing_errors


def build_packet(sequence: int, scheduled_offset_ns: int, pcm: bytes) -> bytes:
    if len(pcm) <= 0 or len(pcm) % BYTES_PER_BLOCK:
        raise ValueError(f"invalid PCM block size: {len(pcm)}")
    checksum = zlib.crc32(pcm) & 0xFFFFFFFF
    return (
        PACKET_HEADER.pack(sequence, scheduled_offset_ns, len(pcm), checksum)
        + pcm
    )


def read_packet(stream: BinaryIO | socket.socket) -> tuple[int, int, bytes, bool, bool]:
    header = receive_exact(stream, PACKET_HEADER.size)
    sequence, scheduled_offset_ns, payload_bytes, checksum = (
        PACKET_HEADER.unpack(header)
    )
    framing_error = payload_bytes <= 0 or payload_bytes % BYTES_PER_BLOCK != 0
    pcm = receive_exact(stream, payload_bytes)
    actual_checksum = zlib.crc32(pcm) & 0xFFFFFFFF
    crc_ok = actual_checksum == checksum
    return sequence, scheduled_offset_ns, pcm, crc_ok, framing_error


def read_packet_timed(
    stream: BinaryIO | socket.socket,
) -> tuple[int, int, bytes, bool, bool, dict[str, float]]:
    start_ns = time.perf_counter_ns()
    header = receive_exact(stream, PACKET_HEADER.size)
    header_ns = time.perf_counter_ns()
    sequence, scheduled_offset_ns, payload_bytes, checksum = (
        PACKET_HEADER.unpack(header)
    )
    framing_error = payload_bytes <= 0 or payload_bytes % BYTES_PER_BLOCK != 0
    pcm = receive_exact(stream, payload_bytes)
    payload_ns = time.perf_counter_ns()
    actual_checksum = zlib.crc32(pcm) & 0xFFFFFFFF
    crc_ns = time.perf_counter_ns()
    crc_ok = actual_checksum == checksum
    timings = {
        "packet_read_ms": (crc_ns - start_ns) / 1e6,
        "header_wait_ms": (header_ns - start_ns) / 1e6,
        "payload_read_ms": (payload_ns - header_ns) / 1e6,
        "crc_ms": (crc_ns - payload_ns) / 1e6,
    }
    return sequence, scheduled_offset_ns, pcm, crc_ok, framing_error, timings


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
    ordered = sorted(values)

    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * p / 100.0
        lower = int(rank)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = rank - lower
        return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction

    return {
        f"{prefix}_mean": sum(values) / len(values),
        f"{prefix}_p50": percentile(50),
        f"{prefix}_p95": percentile(95),
        f"{prefix}_p99": percentile(99),
        f"{prefix}_max": max(values),
    }


def cadence_summary(offsets_ms: list[float], intervals_ms: list[float]) -> dict[str, float | int]:
    audio_duration_s = len(offsets_ms) / BLOCKS_PER_SECOND
    covered_duration_s = (
        0.0
        if not offsets_ms
        else (offsets_ms[-1] + BLOCK_DURATION_NS / 1e6) / 1000.0
    )
    return {
        "block_rate_hz": 0.0 if audio_duration_s == 0.0 else len(offsets_ms) / audio_duration_s,
        "audio_duration_s": audio_duration_s,
        "covered_duration_s": covered_duration_s,
        "audio_to_covered_ratio": (
            0.0
            if covered_duration_s == 0.0
            else audio_duration_s / covered_duration_s
        ),
        "interval_stalls_over_20ms": sum(value > 20.0 for value in intervals_ms),
        "interval_stalls_over_50ms": sum(value > 50.0 for value in intervals_ms),
        "interval_stalls_over_100ms": sum(value > 100.0 for value in intervals_ms),
        "interval_bursts_under_5ms": sum(value < 5.0 for value in intervals_ms),
    }


class SchedulerMonitor:
    def __init__(self, interval_ms: float) -> None:
        self.interval_ms = interval_ms
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.samples: list[dict[str, float | int]] = []

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, object]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        intervals = [float(row["interval_ms"]) for row in self.samples]
        lateness = [float(row["lateness_ms"]) for row in self.samples]
        summary: dict[str, object] = {
            "interval_ms": self.interval_ms,
            "sample_count": len(self.samples),
            "gaps_over_10ms": sum(value > 10.0 for value in intervals),
            "gaps_over_30ms": sum(value > 30.0 for value in intervals),
            "gaps_over_100ms": sum(value > 100.0 for value in intervals),
        }
        summary.update(summarize_ms(intervals, "scheduler_interval_ms"))
        summary.update(summarize_ms(lateness, "scheduler_lateness_ms"))
        return summary

    def _run(self) -> None:
        interval_s = self.interval_ms / 1000.0
        interval_ns = int(self.interval_ms * 1_000_000)
        previous_ns = time.perf_counter_ns()
        index = 0
        while not self._stop.is_set():
            time.sleep(interval_s)
            current_ns = time.perf_counter_ns()
            interval_ms = (current_ns - previous_ns) / 1e6
            self.samples.append(
                {
                    "index": index,
                    "qpc_ns": current_ns,
                    "interval_ms": interval_ms,
                    "lateness_ms": max(
                        0.0,
                        (current_ns - previous_ns - interval_ns) / 1e6,
                    ),
                }
            )
            previous_ns = current_ns
            index += 1


def send_stream_packets(
    payload: bytes,
    block_count: int,
    blocks_per_packet: int,
    start_delay_ms: int,
    send_packet: object,
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float | int]]]:
    trace: list[dict[str, float | int | str]] = []
    packet_events: list[dict[str, float | int]] = []
    stream_start_ns = time.perf_counter_ns() + start_delay_ms * 1_000_000
    previous_send_ns: int | None = None
    for packet_sequence in range(0, block_count, blocks_per_packet):
        packet_block_count = min(
            blocks_per_packet,
            block_count - packet_sequence,
        )
        scheduled_offset_ns = packet_sequence * BLOCK_DURATION_NS
        deadline_ns = stream_start_ns + scheduled_offset_ns
        wait_until_ns(deadline_ns)
        start = packet_sequence * BYTES_PER_BLOCK
        end = start + packet_block_count * BYTES_PER_BLOCK
        pcm = payload[start:end]
        packet = build_packet(packet_sequence, scheduled_offset_ns, pcm)
        send_started_ns = time.perf_counter_ns()
        send_packet(packet)
        send_finished_ns = time.perf_counter_ns()
        send_interval_ms = (
            0.0
            if previous_send_ns is None
            else (send_started_ns - previous_send_ns) / 1e6
        )
        send_lateness_ms = (send_started_ns - deadline_ns) / 1e6
        send_call_ms = (send_finished_ns - send_started_ns) / 1e6
        packet_events.append(
            {
                "sequence": packet_sequence,
                "scheduled_offset_ms": scheduled_offset_ns / 1e6,
                "send_offset_ms": (send_started_ns - stream_start_ns) / 1e6,
                "send_lateness_ms": send_lateness_ms,
                "send_interval_ms": send_interval_ms,
                "send_call_ms": send_call_ms,
                "transport_blocks_in_packet": packet_block_count,
                "transport_payload_bytes": len(pcm),
            }
        )
        for batch_index in range(packet_block_count):
            sequence = packet_sequence + batch_index
            block_start = batch_index * BYTES_PER_BLOCK
            block = pcm[block_start : block_start + BYTES_PER_BLOCK]
            trace.append(
                {
                    "sequence": sequence,
                    "scheduled_offset_ms": (
                        sequence * BLOCK_DURATION_NS / 1e6
                    ),
                    "send_offset_ms": (
                        send_started_ns - stream_start_ns
                    ) / 1e6,
                    "send_lateness_ms": (
                        send_started_ns
                        - (stream_start_ns + sequence * BLOCK_DURATION_NS)
                    ) / 1e6,
                    "send_interval_ms": (
                        send_interval_ms if batch_index == 0 else 0.0
                    ),
                    "send_call_ms": (
                        send_call_ms if batch_index == 0 else 0.0
                    ),
                    "crc32": zlib.crc32(block) & 0xFFFFFFFF,
                    "transport_packet_sequence": packet_sequence,
                    "transport_batch_index": batch_index,
                    "transport_blocks_in_packet": packet_block_count,
                    "transport_payload_bytes": len(pcm),
                }
            )
        previous_send_ns = send_started_ns
    return trace, packet_events


def run_server(args: argparse.Namespace) -> dict[str, object]:
    payload, block_count = load_pcm16_mono_48k(args.source_wav)
    payload_hash = hashlib.sha256(payload).hexdigest()
    trace: list[dict[str, float | int | str]]
    packet_events: list[dict[str, float | int]]
    peer: tuple[str, int] | None = None
    accept_wait_s = 0.0
    udp_hello_wait_s: float | None = None
    ack_received = 0
    ack_lost = 0
    ack_sequence_errors = 0
    ack_crc_errors = 0
    ack_framing_errors = 0

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
            udp: socket.socket | None = None
            try:
                if args.transport == "udp":
                    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    udp.bind((args.bind, args.port))
                    udp.settimeout(args.socket_timeout)
                connection.sendall(build_preamble(block_count))
                if args.transport == "tcp":
                    trace, packet_events = send_stream_packets(
                        payload,
                        block_count,
                        args.blocks_per_packet,
                        args.start_delay_ms,
                        connection.sendall,
                    )
                else:
                    assert udp is not None
                    hello_started = time.perf_counter()
                    hello, udp_peer = udp.recvfrom(64)
                    udp_hello_wait_s = time.perf_counter() - hello_started
                    if hello != UDP_HELLO_MAGIC:
                        raise ValueError("invalid UDP receiver hello")
                    trace, packet_events = send_stream_packets(
                        payload,
                        block_count,
                        args.blocks_per_packet,
                        args.start_delay_ms,
                        lambda packet: udp.sendto(packet, udp_peer),
                    )
            finally:
                if udp is not None:
                    udp.close()
            ack_payload = receive_exact(connection, ACK.size)
            (
                ack_magic,
                ack_received,
                ack_lost,
                ack_sequence_errors,
                ack_crc_errors,
                ack_framing_errors,
            ) = ACK.unpack(ack_payload)
            if ack_magic != ACK_MAGIC:
                raise ValueError("invalid receiver ACK")

    intervals = [float(row["send_interval_ms"]) for row in trace[1:]]
    packet_intervals = [
        float(row["send_interval_ms"]) for row in packet_events[1:]
    ]
    offsets = [float(row["send_offset_ms"]) for row in trace]
    lateness = [float(row["send_lateness_ms"]) for row in trace]
    calls = [float(row["send_call_ms"]) for row in trace]
    summary: dict[str, object] = {
        "role": "server",
        "transport": args.transport,
        "peer": f"{peer[0]}:{peer[1]}" if peer is not None else "",
        "contract": {
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "format": "pcm_s16le",
            "frames_per_block": FRAMES_PER_BLOCK,
            "bytes_per_block": BYTES_PER_BLOCK,
            "block_duration_ms": BLOCK_DURATION_NS / 1e6,
            "blocks_per_second": BLOCKS_PER_SECOND,
            "transport_blocks_per_packet": args.blocks_per_packet,
            "transport_protocol": args.transport,
        },
        "source_wav": str(args.source_wav),
        "source_wav_sha256": sha256_file(args.source_wav),
        "payload_sha256": payload_hash,
        "accept_wait_s": accept_wait_s,
        "block_count": block_count,
        "sample_count": block_count * FRAMES_PER_BLOCK,
        "duration_s": block_count / BLOCKS_PER_SECOND,
        "transport_blocks_per_packet": args.blocks_per_packet,
        "transport_protocol": args.transport,
        "transport_packet_count": len(packet_events),
        "receiver_ack": {
            "received": ack_received,
            "lost_blocks": ack_lost,
            "sequence_errors": ack_sequence_errors,
            "crc_errors": ack_crc_errors,
            "framing_errors": ack_framing_errors,
        },
    }
    if udp_hello_wait_s is not None:
        summary["udp_hello_wait_s"] = udp_hello_wait_s
    summary.update(summarize_ms(intervals, "send_interval_ms"))
    summary.update(summarize_ms(packet_intervals, "packet_send_interval_ms"))
    summary.update(cadence_summary(offsets, intervals))
    summary.update(summarize_ms(lateness, "send_lateness_ms"))
    summary.update(summarize_ms(calls, "send_call_ms"))
    if args.trace:
        write_json(args.trace, trace)
    return summary


def run_client(args: argparse.Namespace) -> dict[str, object]:
    scheduler_monitor: SchedulerMonitor | None = None
    if args.scheduler_trace is not None:
        scheduler_monitor = SchedulerMonitor(args.scheduler_interval_ms)
        scheduler_monitor.start()

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

    rows: list[dict[str, float | int]] = []
    payload_hash = hashlib.sha256()
    received_blocks = 0
    lost_blocks = 0
    sequence_errors = 0
    crc_errors = 0
    framing_errors = 0
    previous_receive_ns: int | None = None
    first_receive_ns: int | None = None
    expected_sequence = 0
    packet_events: list[dict[str, float | int]] = []
    previous_packet_receive_ns: int | None = None

    wav = None
    if args.sink == "wav":
        if args.output_wav is None:
            raise ValueError("wav sink requires --output-wav")
        args.output_wav.parent.mkdir(parents=True, exist_ok=True)
    scheduler_summary: dict[str, object] | None = None
    try:
        with connection:
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            connection.settimeout(args.socket_timeout)
            contract = parse_preamble(receive_exact(connection, PREAMBLE.size))
            framing_errors += validate_contract(contract)
            if args.sink == "wav":
                assert args.output_wav is not None
                wav = wave.open(str(args.output_wav), "wb")
                wav.setnchannels(CHANNELS)
                wav.setsampwidth(SAMPLE_WIDTH_BYTES)
                wav.setframerate(SAMPLE_RATE)
            while expected_sequence < contract["block_count"]:
                (
                    packet_sequence,
                    scheduled_offset_ns,
                    pcm,
                    crc_ok,
                    framing_error,
                    packet_timings,
                ) = read_packet_timed(connection)
                receive_ns = time.perf_counter_ns()
                if first_receive_ns is None:
                    first_receive_ns = receive_ns
                packet_block_count = (
                    0 if framing_error else len(pcm) // BYTES_PER_BLOCK
                )
                packet_events.append(
                    {
                        "sequence": packet_sequence,
                        "receive_qpc_ns": receive_ns,
                        "receive_offset_ms": (
                            0.0
                            if first_receive_ns is None
                            else (receive_ns - first_receive_ns) / 1e6
                        ),
                        "receive_interval_ms": (
                            0.0
                            if previous_packet_receive_ns is None
                            else (receive_ns - previous_packet_receive_ns) / 1e6
                        ),
                        "transport_blocks_in_packet": packet_block_count,
                        "transport_payload_bytes": len(pcm),
                        **packet_timings,
                    }
                )
                previous_packet_receive_ns = receive_ns
                if packet_sequence != expected_sequence:
                    sequence_errors += 1
                    if packet_sequence > expected_sequence:
                        lost_blocks += packet_sequence - expected_sequence
                if not crc_ok:
                    crc_errors += max(1, packet_block_count)
                if framing_error:
                    framing_errors += 1
                    continue
                for batch_index in range(packet_block_count):
                    sequence = packet_sequence + batch_index
                    block_start = batch_index * BYTES_PER_BLOCK
                    block = pcm[block_start : block_start + BYTES_PER_BLOCK]
                    block_scheduled_offset_ns = (
                        scheduled_offset_ns + batch_index * BLOCK_DURATION_NS
                    )
                    if wav is not None:
                        wav.writeframes(block)
                    payload_hash.update(block)
                    received_blocks += 1
                    rows.append(
                        {
                            "sequence": sequence,
                            "scheduled_offset_ms": block_scheduled_offset_ns / 1e6,
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
                            "arrival_jitter_ms": (
                                0.0
                                if previous_receive_ns is None
                                else (receive_ns - previous_receive_ns) / 1e6
                                - BLOCK_DURATION_NS / 1e6
                            ),
                            "crc_ok": int(crc_ok),
                            "framing_error": int(framing_error),
                            "packet_read_ms": (
                                packet_timings["packet_read_ms"]
                                if batch_index == 0
                                else 0.0
                            ),
                            "header_wait_ms": (
                                packet_timings["header_wait_ms"]
                                if batch_index == 0
                                else 0.0
                            ),
                            "payload_read_ms": (
                                packet_timings["payload_read_ms"]
                                if batch_index == 0
                                else 0.0
                            ),
                            "crc_ms": (
                                packet_timings["crc_ms"]
                                if batch_index == 0
                                else 0.0
                            ),
                            "transport_packet_sequence": packet_sequence,
                            "transport_batch_index": batch_index,
                            "transport_blocks_in_packet": packet_block_count,
                            "transport_payload_bytes": len(pcm),
                        }
                    )
                    previous_receive_ns = receive_ns
                expected_sequence = packet_sequence + packet_block_count
            connection.sendall(
                ACK.pack(
                    ACK_MAGIC,
                    received_blocks,
                    lost_blocks,
                    sequence_errors,
                    crc_errors,
                    framing_errors,
                )
            )
    except Exception:
        raise
    finally:
        if wav is not None:
            wav.close()
        if scheduler_monitor is not None:
            scheduler_summary = scheduler_monitor.stop()

    intervals = [float(row["receive_interval_ms"]) for row in rows[1:]]
    packet_intervals = [
        float(row["receive_interval_ms"]) for row in packet_events[1:]
    ]
    offsets = [float(row["receive_offset_ms"]) for row in rows]
    jitter = [float(row["arrival_jitter_ms"]) for row in rows[1:]]
    phase_error = [
        float(row["receive_offset_ms"]) - float(row["scheduled_offset_ms"])
        for row in rows
    ]
    packet_read = [float(row["packet_read_ms"]) for row in rows]
    header_wait = [float(row["header_wait_ms"]) for row in rows]
    payload_read = [float(row["payload_read_ms"]) for row in rows]
    crc_times = [float(row["crc_ms"]) for row in rows]
    packet_header_wait = [
        float(row["header_wait_ms"]) for row in packet_events
    ]
    packet_payload_read = [
        float(row["payload_read_ms"]) for row in packet_events
    ]
    summary: dict[str, object] = {
        "role": "client",
        "transport": args.transport,
        "contract": {
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "format": "pcm_s16le",
            "frames_per_block": FRAMES_PER_BLOCK,
            "bytes_per_block": BYTES_PER_BLOCK,
            "block_duration_ms": BLOCK_DURATION_NS / 1e6,
            "blocks_per_second": BLOCKS_PER_SECOND,
            "transport_blocks_per_packet": args.blocks_per_packet,
            "transport_protocol": args.transport,
        },
        "expected_block_count": contract["block_count"],
        "block_count": received_blocks,
        "sample_count": received_blocks * FRAMES_PER_BLOCK,
        "duration_s": received_blocks / BLOCKS_PER_SECOND,
        "transport_blocks_per_packet": args.blocks_per_packet,
        "transport_protocol": args.transport,
        "observed_transport_packet_count": len(packet_events),
        "observed_max_blocks_per_packet": (
            max(
                int(row["transport_blocks_in_packet"])
                for row in packet_events
            )
            if packet_events
            else 0
        ),
        "lost_blocks": lost_blocks,
        "sequence_errors": sequence_errors,
        "crc_errors": crc_errors,
        "framing_errors": framing_errors,
        "received_payload_sha256": payload_hash.hexdigest(),
        "sink": args.sink,
        "receiver_queue": {
            "type": "none",
            "max_backlog_blocks": 0,
            "note": (
                "client hashes each TCP block in memory"
                if args.sink == "memory"
                else "client writes each TCP block directly to the WAV sink"
            ),
        },
    }
    if args.sink == "wav":
        assert args.output_wav is not None
        summary["reconstructed_wav"] = str(args.output_wav)
        summary["reconstructed_wav_sha256"] = sha256_file(args.output_wav)
    summary.update(summarize_ms(intervals, "receive_interval_ms"))
    summary.update(cadence_summary(offsets, intervals))
    summary.update(summarize_ms(jitter, "arrival_jitter_ms"))
    summary.update(summarize_ms(phase_error, "receive_phase_error_ms"))
    summary.update(summarize_ms(packet_read, "packet_read_ms"))
    summary.update(summarize_ms(header_wait, "header_wait_ms"))
    summary.update(summarize_ms(payload_read, "payload_read_ms"))
    summary.update(summarize_ms(crc_times, "crc_ms"))
    summary.update(summarize_ms(packet_intervals, "packet_receive_interval_ms"))
    summary.update(summarize_ms(packet_header_wait, "packet_header_wait_ms"))
    summary.update(summarize_ms(packet_payload_read, "packet_payload_read_ms"))
    if args.trace:
        write_json(args.trace, rows)
    if args.scheduler_trace and scheduler_monitor is not None:
        write_json(
            args.scheduler_trace,
            {
                "status": "completed",
                "summary": scheduler_summary,
                "samples": scheduler_monitor.samples,
            },
        )
    if scheduler_summary is not None:
        summary["scheduler_probe"] = scheduler_summary
    if args.hash_output:
        hash_result: dict[str, object] = {
            "status": "completed",
            "sink": args.sink,
            "payload_sha256": summary["received_payload_sha256"],
            "block_count": received_blocks,
            "sample_count": summary["sample_count"],
            "duration_s": summary["duration_s"],
            "transport_protocol": args.transport,
            "transport_blocks_per_packet": args.blocks_per_packet,
            "observed_transport_packet_count": len(packet_events),
        }
        if "reconstructed_wav_sha256" in summary:
            hash_result["reconstructed_wav_sha256"] = summary[
                "reconstructed_wav_sha256"
            ]
        write_json(args.hash_output, hash_result)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("server", "client"))
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--host", default="10.0.2.2")
    parser.add_argument("--port", type=int, default=35280)
    parser.add_argument("--source-wav", type=Path)
    parser.add_argument("--start-delay-ms", type=int, default=250)
    parser.add_argument("--accept-timeout", type=float, default=180.0)
    parser.add_argument("--connect-timeout", type=float, default=180.0)
    parser.add_argument("--socket-timeout", type=float, default=45.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--output-wav", type=Path)
    parser.add_argument("--sink", choices=("wav", "memory"), default="wav")
    parser.add_argument("--hash-output", type=Path)
    parser.add_argument("--scheduler-trace", type=Path)
    parser.add_argument("--scheduler-interval-ms", type=float, default=2.0)
    parser.add_argument("--blocks-per-packet", type=int, default=1)
    parser.add_argument("--transport", choices=("tcp", "udp"), default="tcp")
    args = parser.parse_args()
    if args.role == "server" and args.source_wav is None:
        parser.error("server requires --source-wav")
    if args.role == "client" and args.sink == "wav" and args.output_wav is None:
        parser.error("client with --sink wav requires --output-wav")
    if args.role == "client" and args.transport != "tcp":
        parser.error("the Python client currently supports only --transport tcp")
    if args.blocks_per_packet < 1 or args.blocks_per_packet > 16:
        parser.error("--blocks-per-packet must be between 1 and 16")
    return args


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
