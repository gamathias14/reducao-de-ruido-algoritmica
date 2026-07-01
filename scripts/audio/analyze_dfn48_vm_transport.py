from __future__ import annotations

import argparse
import bisect
import json
import math
import wave
from pathlib import Path
from typing import Any


SAMPLE_RATE = 48_000
FRAMES_PER_BLOCK = 480
BYTES_PER_BLOCK = 960
BLOCK_DURATION_MS = 10.0
BLOCKS_PER_SECOND = 100


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def warn(condition: bool, name: str, warnings: list[str]) -> None:
    if not condition:
        warnings.append(name)


def transport_blocks_per_packet(payload: dict[str, Any]) -> int:
    contract = payload.get("contract", {})
    return int(
        payload.get(
            "transport_blocks_per_packet",
            contract.get("transport_blocks_per_packet", 1),
        )
    )


def transport_protocol(payload: dict[str, Any]) -> str:
    contract = payload.get("contract", {})
    return str(
        payload.get(
            "transport_protocol",
            payload.get("transport", contract.get("transport_protocol", "tcp")),
        )
    )


def wav_info(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as wav:
        return {
            "channels": wav.getnchannels(),
            "sample_width_bytes": wav.getsampwidth(),
            "sample_rate": wav.getframerate(),
            "frame_count": wav.getnframes(),
            "duration_s": wav.getnframes() / wav.getframerate(),
        }


def simulate_jitter_buffers(
    root: Path,
    expected_blocks: int,
    buffer_blocks: list[int],
) -> dict[str, Any] | None:
    client_trace_path = root / "client_trace.json"
    if not client_trace_path.is_file():
        return None

    rows = read_json(client_trace_path)
    by_sequence = {
        int(row["sequence"]): row
        for row in rows
        if int(row.get("framing_error", 0)) == 0
    }
    receive_offsets = sorted(float(row["receive_offset_ms"]) for row in rows)
    phase_errors = [
        float(row["receive_offset_ms"]) - float(row["scheduled_offset_ms"])
        for row in rows
    ]
    max_phase_error_ms = max(phase_errors) if phase_errors else 0.0
    min_phase_error_ms = min(phase_errors) if phase_errors else 0.0
    required_blocks = max(0, math.ceil(max_phase_error_ms / BLOCK_DURATION_MS))

    simulations = []
    for blocks in buffer_blocks:
        if blocks < 0:
            continue
        buffer_ms = blocks * BLOCK_DURATION_MS
        underflows = 0
        first_underflow_sequence: int | None = None
        max_lateness_after_buffer_ms = 0.0
        min_depth_before_consume: int | None = None
        max_depth_before_consume = 0
        depth_sum = 0
        checked = 0

        for sequence in range(expected_blocks):
            playout_offset_ms = sequence * BLOCK_DURATION_MS + buffer_ms
            arrivals_by_playout = bisect.bisect_right(
                receive_offsets,
                playout_offset_ms,
            )
            depth_before_consume = max(0, arrivals_by_playout - sequence)
            min_depth_before_consume = (
                depth_before_consume
                if min_depth_before_consume is None
                else min(min_depth_before_consume, depth_before_consume)
            )
            max_depth_before_consume = max(
                max_depth_before_consume,
                depth_before_consume,
            )
            depth_sum += depth_before_consume
            checked += 1

            row = by_sequence.get(sequence)
            if row is None:
                underflows += 1
                if first_underflow_sequence is None:
                    first_underflow_sequence = sequence
                continue
            lateness_after_buffer_ms = (
                float(row["receive_offset_ms"]) - playout_offset_ms
            )
            if lateness_after_buffer_ms > 0.0:
                underflows += 1
                if first_underflow_sequence is None:
                    first_underflow_sequence = sequence
                max_lateness_after_buffer_ms = max(
                    max_lateness_after_buffer_ms,
                    lateness_after_buffer_ms,
                )

        simulations.append(
            {
                "buffer_blocks": blocks,
                "buffer_ms": buffer_ms,
                "checked_blocks": checked,
                "underflows": underflows,
                "underflow_rate": (
                    0.0 if checked == 0 else underflows / checked
                ),
                "first_underflow_sequence": first_underflow_sequence,
                "max_lateness_after_buffer_ms": max_lateness_after_buffer_ms,
                "min_depth_before_consume_blocks": (
                    min_depth_before_consume
                    if min_depth_before_consume is not None
                    else 0
                ),
                "mean_depth_before_consume_blocks": (
                    0.0 if checked == 0 else depth_sum / checked
                ),
                "max_depth_before_consume_blocks": max_depth_before_consume,
            }
        )

    absorbing = [
        row["buffer_blocks"]
        for row in simulations
        if int(row["underflows"]) == 0
    ]

    return {
        "source": "client_trace_receive_offsets",
        "model": (
            "posthoc ordered playout simulation; playout starts "
            "buffer_ms after first received block"
        ),
        "expected_blocks": expected_blocks,
        "observed_blocks": len(by_sequence),
        "max_phase_error_ms": max_phase_error_ms,
        "min_phase_error_ms": min_phase_error_ms,
        "minimum_observed_absorbing_buffer_blocks": (
            min(absorbing) if absorbing else None
        ),
        "minimum_observed_absorbing_buffer_ms": (
            min(absorbing) * BLOCK_DURATION_MS if absorbing else None
        ),
        "minimum_required_blocks_from_max_phase_error": required_blocks,
        "simulations": simulations,
    }


def correlate_scheduler_gaps(root: Path) -> dict[str, Any] | None:
    client_trace_path = root / "client_trace.json"
    scheduler_trace_path = root / "scheduler_trace.json"
    if not client_trace_path.is_file() or not scheduler_trace_path.is_file():
        return None

    client_rows = read_json(client_trace_path)
    scheduler_payload = read_json(scheduler_trace_path)
    scheduler_samples = scheduler_payload.get("samples", [])
    receive_stalls = []
    previous_qpc = None
    for row in client_rows:
        qpc = int(row["receive_qpc_ns"])
        if previous_qpc is not None:
            interval_ms = float(row["receive_interval_ms"])
            if interval_ms > 50.0:
                receive_stalls.append(
                    {
                        "sequence": row["sequence"],
                        "start_qpc_ns": previous_qpc,
                        "end_qpc_ns": qpc,
                        "receive_interval_ms": interval_ms,
                    }
                )
        previous_qpc = qpc

    correlated = 0
    details = []
    for stall in receive_stalls:
        overlapping = [
            sample
            for sample in scheduler_samples
            if stall["start_qpc_ns"] <= int(sample["qpc_ns"]) <= stall["end_qpc_ns"]
            and float(sample["interval_ms"]) > 30.0
        ]
        if overlapping:
            correlated += 1
        details.append(
            {
                "sequence": stall["sequence"],
                "receive_interval_ms": stall["receive_interval_ms"],
                "scheduler_gap_count_over_30ms": len(overlapping),
                "scheduler_gap_max_ms": (
                    max(float(sample["interval_ms"]) for sample in overlapping)
                    if overlapping
                    else 0.0
                ),
            }
        )

    return {
        "scheduler_trace_present": True,
        "receive_stalls_over_50ms": len(receive_stalls),
        "receive_stalls_with_scheduler_gap_over_30ms": correlated,
        "receive_stalls_without_scheduler_gap_over_30ms": (
            len(receive_stalls) - correlated
        ),
        "scheduler_summary": scheduler_payload.get("summary"),
        "details": details,
    }


def correlate_transport_jitter(root: Path) -> dict[str, Any] | None:
    server_trace_path = root / "server_trace.json"
    client_trace_path = root / "client_trace.json"
    scheduler_trace_path = root / "scheduler_trace.json"
    if not server_trace_path.is_file() or not client_trace_path.is_file():
        return None

    server_rows = read_json(server_trace_path)
    client_rows = read_json(client_trace_path)
    scheduler_samples: list[dict[str, Any]] = []
    if scheduler_trace_path.is_file():
        scheduler_payload = read_json(scheduler_trace_path)
        scheduler_samples = scheduler_payload.get("samples", [])
    server_by_sequence = {
        int(row["sequence"]): row
        for row in server_rows
    }

    stalls = []
    previous_qpc = None
    for row in client_rows:
        sequence = int(row["sequence"])
        qpc = int(row["receive_qpc_ns"])
        if previous_qpc is not None:
            receive_interval_ms = float(row["receive_interval_ms"])
            if receive_interval_ms > 50.0:
                server_row = server_by_sequence.get(sequence, {})
                server_send_interval_ms = float(
                    server_row.get("send_interval_ms", 0.0)
                )
                server_send_lateness_ms = float(
                    server_row.get("send_lateness_ms", 0.0)
                )
                server_send_call_ms = float(
                    server_row.get("send_call_ms", 0.0)
                )
                client_header_wait_ms = float(
                    row.get("header_wait_ms", receive_interval_ms)
                )
                client_payload_read_ms = float(row.get("payload_read_ms", 0.0))
                client_crc_ms = float(row.get("crc_ms", 0.0))
                client_pre_read_gap_ms = float(
                    row.get(
                        "pre_read_gap_ms",
                        max(
                            0.0,
                            receive_interval_ms
                            - client_header_wait_ms
                            - client_payload_read_ms
                            - client_crc_ms,
                        ),
                    )
                )
                scheduler_overlaps = [
                    sample
                    for sample in scheduler_samples
                    if previous_qpc <= int(sample["qpc_ns"]) <= qpc
                    and float(sample["interval_ms"]) > 30.0
                ]
                blocks_in_packet = int(
                    server_row.get("transport_blocks_in_packet", 1)
                )
                expected_send_interval_ms = (
                    BLOCK_DURATION_MS * max(1, blocks_in_packet)
                )
                host_send_gap = (
                    server_send_interval_ms
                    > expected_send_interval_ms + 20.0
                    or server_send_lateness_ms > 30.0
                )
                scheduler_gap = bool(scheduler_overlaps)
                if host_send_gap and scheduler_gap:
                    classification = "host_send_and_guest_scheduler"
                elif host_send_gap:
                    classification = "host_send_correlated"
                elif scheduler_gap:
                    classification = "guest_scheduler_correlated"
                elif (
                    client_pre_read_gap_ms > 30.0
                    and client_header_wait_ms < 10.0
                ):
                    classification = "client_receiver_thread_pre_recv_gap"
                else:
                    classification = "unaccounted_receive_or_nat"
                stalls.append(
                    {
                        "sequence": sequence,
                        "receive_interval_ms": receive_interval_ms,
                        "server_send_interval_ms": server_send_interval_ms,
                        "server_send_lateness_ms": server_send_lateness_ms,
                        "server_send_call_ms": server_send_call_ms,
                        "expected_server_send_interval_ms": (
                            expected_send_interval_ms
                        ),
                        "client_header_wait_ms": client_header_wait_ms,
                        "client_pre_read_gap_ms": client_pre_read_gap_ms,
                        "client_payload_read_ms": client_payload_read_ms,
                        "client_crc_ms": client_crc_ms,
                        "scheduler_gap_count_over_30ms": len(scheduler_overlaps),
                        "scheduler_gap_max_ms": (
                            max(
                                float(sample["interval_ms"])
                                for sample in scheduler_overlaps
                            )
                            if scheduler_overlaps
                            else 0.0
                        ),
                        "classification": classification,
                    }
                )
        previous_qpc = qpc

    by_class: dict[str, int] = {}
    for stall in stalls:
        classification = str(stall["classification"])
        by_class[classification] = by_class.get(classification, 0) + 1

    server_stalls = []
    for row in server_rows[1:]:
        blocks_in_packet = int(row.get("transport_blocks_in_packet", 1))
        expected_send_interval_ms = BLOCK_DURATION_MS * max(1, blocks_in_packet)
        if (
            float(row.get("send_interval_ms", 0.0))
            > expected_send_interval_ms + 20.0
        ):
            server_stalls.append(row)
    client_stall_sequences = {int(row["sequence"]) for row in stalls}
    server_only = [
        int(row["sequence"])
        for row in server_stalls
        if int(row["sequence"]) not in client_stall_sequences
    ]

    return {
        "server_trace_present": True,
        "client_trace_present": True,
        "scheduler_trace_present": scheduler_trace_path.is_file(),
        "receive_stalls_over_50ms": len(stalls),
        "server_send_stalls_over_50ms": len(server_stalls),
        "server_send_stalls_without_receive_stall_over_50ms": len(server_only),
        "class_counts": by_class,
        "stalls": stalls,
        "server_only_stall_sequences": server_only[:50],
    }


def analyze(
    root: Path,
    expected_duration_s: float,
    jitter_buffer_blocks: list[int],
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    server = read_json(root / "server.json")
    client = read_json(root / "client.json")
    hash_result = read_json(root / "received_payload_hash.json")
    jitter_diagnosis = correlate_scheduler_gaps(root)
    transport_jitter = correlate_transport_jitter(root)
    sink = str(client.get("sink", "wav"))
    server_blocks_per_packet = transport_blocks_per_packet(server)
    client_blocks_per_packet = transport_blocks_per_packet(client)
    server_transport_protocol = transport_protocol(server)
    client_transport_protocol = transport_protocol(client)
    reconstructed_wav = root / "received.wav"
    wav = wav_info(reconstructed_wav) if reconstructed_wav.is_file() else None
    expected_blocks = int(round(expected_duration_s * BLOCKS_PER_SECOND))
    expected_samples = int(round(expected_duration_s * SAMPLE_RATE))
    jitter_buffer_diagnosis = simulate_jitter_buffers(
        root,
        expected_blocks,
        jitter_buffer_blocks,
    )

    check(server.get("status") == "completed", "server_status", failures)
    check(client.get("status") == "completed", "client_status", failures)
    for prefix, payload in (("server", server), ("client", client)):
        contract = payload.get("contract", {})
        check(
            contract.get("sample_rate") == SAMPLE_RATE,
            f"{prefix}_sample_rate",
            failures,
        )
        check(
            contract.get("frames_per_block") == FRAMES_PER_BLOCK,
            f"{prefix}_frames_per_block",
            failures,
        )
        check(
            contract.get("bytes_per_block") == BYTES_PER_BLOCK,
            f"{prefix}_bytes_per_block",
            failures,
        )
        check(
            contract.get("format") == "pcm_s16le",
            f"{prefix}_pcm_format",
            failures,
        )
        check(
            contract.get("blocks_per_second") == BLOCKS_PER_SECOND,
            f"{prefix}_blocks_per_second",
            failures,
        )
    check(
        server_blocks_per_packet == client_blocks_per_packet,
        "transport_blocks_per_packet_match",
        failures,
    )
    check(
        server_transport_protocol == client_transport_protocol,
        "transport_protocol_match",
        failures,
    )

    check(server.get("block_count") == expected_blocks, "server_block_count", failures)
    check(client.get("block_count") == expected_blocks, "client_block_count", failures)
    check(client.get("expected_block_count") == expected_blocks, "client_expected_blocks", failures)
    check(server.get("sample_count") == expected_samples, "server_sample_count", failures)
    check(client.get("sample_count") == expected_samples, "client_sample_count", failures)
    check(client.get("lost_blocks") == 0, "lost_blocks", failures)
    check(client.get("sequence_errors") == 0, "sequence_errors", failures)
    check(client.get("crc_errors") == 0, "crc_errors", failures)
    check(client.get("framing_errors") == 0, "framing_errors", failures)
    check(
        server.get("receiver_ack", {}).get("received") == expected_blocks,
        "ack_received",
        failures,
    )
    check(
        server.get("receiver_ack", {}).get("lost_blocks") == 0,
        "ack_lost_blocks",
        failures,
    )
    check(
        server.get("receiver_ack", {}).get("sequence_errors") == 0,
        "ack_sequence_errors",
        failures,
    )
    check(
        server.get("receiver_ack", {}).get("crc_errors") == 0,
        "ack_crc_errors",
        failures,
    )
    check(
        server.get("receiver_ack", {}).get("framing_errors") == 0,
        "ack_framing_errors",
        failures,
    )
    check(
        server.get("payload_sha256") == client.get("received_payload_sha256"),
        "payload_hash_match",
        failures,
    )
    check(
        hash_result.get("payload_sha256") == client.get("received_payload_sha256"),
        "hash_artifact_match",
        failures,
    )
    if sink == "wav":
        check(wav is not None, "wav_exists", failures)
        if wav is not None:
            check(wav["channels"] == 1, "wav_channels", failures)
            check(wav["sample_width_bytes"] == 2, "wav_sample_width", failures)
            check(wav["sample_rate"] == SAMPLE_RATE, "wav_sample_rate", failures)
            check(wav["frame_count"] == expected_samples, "wav_frame_count", failures)
            check(
                abs(float(wav["duration_s"]) - expected_duration_s) <= 0.0005,
                "wav_duration",
                failures,
            )
    else:
        check(sink == "memory", "known_sink", failures)

    expected_packet_interval_ms = BLOCK_DURATION_MS * client_blocks_per_packet
    if client_blocks_per_packet == 1:
        warn(
            float(server.get("send_interval_ms_p99", 999.0)) <= 12.0,
            "server_send_p99_over_12ms",
            warnings,
        )
        warn(
            float(server.get("send_interval_ms_max", 999.0)) <= 30.0,
            "server_send_max_over_30ms",
            warnings,
        )
        warn(
            float(client.get("receive_interval_ms_p99", 999.0)) <= 20.0,
            "client_receive_p99_over_20ms",
            warnings,
        )
    else:
        warn(
            float(server.get("packet_send_interval_ms_p99", 999.0))
            <= expected_packet_interval_ms + 12.0,
            "server_packet_send_p99_high",
            warnings,
        )
        warn(
            float(server.get("packet_send_interval_ms_max", 999.0))
            <= expected_packet_interval_ms + 30.0,
            "server_packet_send_max_high",
            warnings,
        )
        warn(
            float(client.get("packet_receive_interval_ms_p99", 999.0))
            <= expected_packet_interval_ms + 20.0,
            "client_packet_receive_p99_high",
            warnings,
        )
    warn(
        int(client.get("interval_stalls_over_100ms", 1)) == 0,
        "client_receive_stall_over_100ms",
        warnings,
    )
    warn(
        0.98 <= float(client.get("audio_to_covered_ratio", 0.0)) <= 1.02,
        "client_audio_to_covered_ratio_outside_2pct",
        warnings,
    )
    warn(
        client_blocks_per_packet == 1,
        "batched_transport_diagnostic_not_realtime_gate",
        warnings,
    )
    warn(
        client_transport_protocol == "tcp",
        "udp_transport_diagnostic_not_realtime_gate",
        warnings,
    )
    receiver_queue = client.get("receiver_queue") or {}
    queue_type = str(receiver_queue.get("type", "none"))
    if queue_type == "ring_buffer_diagnostic":
        warn(False, "ring_buffer_diagnostic_not_realtime_gate", warnings)
        warn(
            int(receiver_queue.get("producer_overflow_drops", 0)) == 0,
            "ring_buffer_overflow_drops",
            warnings,
        )
        warn(
            int(receiver_queue.get("consumer_recoveries", 0)) == 0,
            "ring_buffer_recoveries",
            warnings,
        )
        warn(
            int(receiver_queue.get("consumer_underflows", 0)) == 0,
            "ring_buffer_underflows",
            warnings,
        )
        warn(
            int(receiver_queue.get("consumer_resyncs", 0)) == 0,
            "ring_buffer_consumer_resyncs",
            warnings,
        )
        capacity_blocks = int(receiver_queue.get("capacity_blocks", 0))
        max_depth = int(receiver_queue.get("max_depth_before_consume_blocks", 0))
        if capacity_blocks > 0:
            warn(
                max_depth < capacity_blocks,
                "ring_buffer_reached_latency_cap",
                warnings,
            )

    status = "accepted"
    if failures:
        status = "rejected"
    elif warnings:
        status = "check"

    return {
        "status": status,
        "phase": "VM-DFN3-TRANSPORT-48K",
        "contract": {
            "sample_rate": SAMPLE_RATE,
            "channels": 1,
            "format": "pcm_s16le",
            "frames_per_block": FRAMES_PER_BLOCK,
            "block_duration_ms": BLOCK_DURATION_MS,
            "blocks_per_second": BLOCKS_PER_SECOND,
            "transport_blocks_per_packet": client_blocks_per_packet,
            "transport_protocol": client_transport_protocol,
        },
        "expected_duration_s": expected_duration_s,
        "expected_blocks": expected_blocks,
        "expected_samples": expected_samples,
        "failures": failures,
        "warnings": warnings,
        "payload_sha256": client.get("received_payload_sha256"),
        "source_payload_sha256": server.get("payload_sha256"),
        "reconstructed_wav": (
            {
                **wav,
                "sha256": client.get("reconstructed_wav_sha256"),
            }
            if wav is not None
            else {
                "sink": sink,
                "present": False,
                "note": "memory sink validates payload hash without WAV output",
            }
        ),
        "timing": {
            "server_send_interval_ms_p99": server.get("send_interval_ms_p99"),
            "server_send_interval_ms_max": server.get("send_interval_ms_max"),
            "server_send_lateness_ms_p99": server.get("send_lateness_ms_p99"),
            "server_send_lateness_ms_max": server.get("send_lateness_ms_max"),
            "client_receive_interval_ms_p99": client.get("receive_interval_ms_p99"),
            "client_receive_interval_ms_max": client.get("receive_interval_ms_max"),
            "client_arrival_jitter_ms_p99": client.get("arrival_jitter_ms_p99"),
            "client_arrival_jitter_ms_max": client.get("arrival_jitter_ms_max"),
            "client_interval_stalls_over_20ms": client.get("interval_stalls_over_20ms"),
            "client_interval_stalls_over_50ms": client.get("interval_stalls_over_50ms"),
            "client_interval_stalls_over_100ms": client.get("interval_stalls_over_100ms"),
            "client_interval_bursts_under_5ms": client.get("interval_bursts_under_5ms"),
            "client_header_wait_ms_p99": client.get("header_wait_ms_p99"),
            "client_header_wait_ms_max": client.get("header_wait_ms_max"),
            "client_pre_read_gap_ms_p99": client.get("pre_read_gap_ms_p99"),
            "client_pre_read_gap_ms_max": client.get("pre_read_gap_ms_max"),
            "client_payload_read_ms_p99": client.get("payload_read_ms_p99"),
            "client_payload_read_ms_max": client.get("payload_read_ms_max"),
            "client_crc_ms_p99": client.get("crc_ms_p99"),
            "client_crc_ms_max": client.get("crc_ms_max"),
            "client_packet_receive_interval_ms_p99": client.get(
                "packet_receive_interval_ms_p99"
            ),
            "client_packet_receive_interval_ms_max": client.get(
                "packet_receive_interval_ms_max"
            ),
            "client_packet_header_wait_ms_p99": client.get(
                "packet_header_wait_ms_p99"
            ),
            "client_packet_header_wait_ms_max": client.get(
                "packet_header_wait_ms_max"
            ),
            "server_packet_send_interval_ms_p99": server.get(
                "packet_send_interval_ms_p99"
            ),
            "server_packet_send_interval_ms_max": server.get(
                "packet_send_interval_ms_max"
            ),
            "ring_playout_latency_ms_p99": client.get("ring_playout_latency_ms_p99"),
            "ring_playout_latency_ms_max": client.get("ring_playout_latency_ms_max"),
            "consumer_deadline_lateness_ms_p99": client.get(
                "consumer_deadline_lateness_ms_p99"
            ),
            "consumer_deadline_lateness_ms_max": client.get(
                "consumer_deadline_lateness_ms_max"
            ),
            "ring_consumer_resyncs": receiver_queue.get("consumer_resyncs"),
            "ring_consumer_resync_lateness_threshold_ms": receiver_queue.get(
                "consumer_resync_lateness_threshold_ms"
            ),
        },
        "integrity": {
            "lost_blocks": client.get("lost_blocks"),
            "sequence_errors": client.get("sequence_errors"),
            "crc_errors": client.get("crc_errors"),
            "framing_errors": client.get("framing_errors"),
            "receiver_ack": server.get("receiver_ack"),
        },
        "queue": client.get("receiver_queue"),
        "jitter_diagnosis": jitter_diagnosis,
        "transport_jitter_correlation": transport_jitter,
        "jitter_buffer_diagnosis": jitter_buffer_diagnosis,
    }


def parse_int_list(value: str) -> list[int]:
    result = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        parsed = int(item)
        if parsed < 0:
            raise argparse.ArgumentTypeError(
                "jitter buffer block counts must be non-negative"
            )
        result.append(parsed)
    if not result:
        raise argparse.ArgumentTypeError("at least one block count is required")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--expected-duration", type=float, default=60.0)
    parser.add_argument(
        "--jitter-buffer-blocks",
        type=parse_int_list,
        default=[1, 2, 4, 6, 8, 12, 16],
        help=(
            "comma-separated diagnostic playout buffer sizes in DFN48 blocks; "
            "default: 1,2,4,6,8,12,16"
        ),
    )
    args = parser.parse_args()

    result = analyze(
        args.root,
        args.expected_duration,
        args.jitter_buffer_blocks,
    )
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if args.summary_output:
        args.summary_output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if result["status"] == "rejected":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
