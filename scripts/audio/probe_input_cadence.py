from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any
from typing import Callable

import numpy as np


LOCAL_REPO_ROOT = Path(__file__).resolve().parents[2]
if (
    (LOCAL_REPO_ROOT / "realtime_audio").is_dir()
    and str(LOCAL_REPO_ROOT) not in sys.path
):
    sys.path.insert(0, str(LOCAL_REPO_ROOT))


def import_sounddevice() -> Any:
    try:
        import sounddevice as sd
    except ModuleNotFoundError as exc:
        raise RuntimeError("sounddevice is required for the cadence probe.") from exc
    return sd


def percentile(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), value))


def distribution(values: list[float], prefix: str) -> dict[str, float]:
    if not values:
        return {
            f"{prefix}_mean": 0.0,
            f"{prefix}_p50": 0.0,
            f"{prefix}_p95": 0.0,
            f"{prefix}_p99": 0.0,
            f"{prefix}_min": 0.0,
            f"{prefix}_max": 0.0,
        }
    samples = np.asarray(values, dtype=np.float64)
    return {
        f"{prefix}_mean": float(np.mean(samples)),
        f"{prefix}_p50": percentile(values, 50),
        f"{prefix}_p95": percentile(values, 95),
        f"{prefix}_p99": percentile(values, 99),
        f"{prefix}_min": float(np.min(samples)),
        f"{prefix}_max": float(np.max(samples)),
    }


def summarize_rows(
    rows: list[dict[str, float | int | str]],
    *,
    sample_rate: int,
    block_size: int,
    requested_duration_s: float,
    stream_wall_s: float,
) -> dict[str, object]:
    expected_interval_s = block_size / sample_rate
    intervals_ms = [
        float(row["callback_interval_ms"])
        for row in rows[1:]
    ]
    adc_deltas_ms = [
        float(row["adc_delta_ms"])
        for row in rows[1:]
        if math.isfinite(float(row["adc_delta_ms"]))
        and float(row["adc_delta_ms"]) > 0.0
    ]
    current_deltas_ms = [
        float(row["current_time_delta_ms"])
        for row in rows[1:]
        if math.isfinite(float(row["current_time_delta_ms"]))
        and float(row["current_time_delta_ms"]) > 0.0
    ]
    frame_counts = [int(row["frames"]) for row in rows]
    processing_ms = [
        float(row.get("processing_ms", 0.0))
        for row in rows
    ]
    total_frames = int(sum(frame_counts))
    delivered_audio_s = total_frames / sample_rate
    callback_span_s = (
        0.0
        if len(rows) < 2
        else float(rows[-1]["callback_monotonic_s"])
        - float(rows[0]["callback_monotonic_s"])
    )
    adc_values = [
        float(row["input_adc_time_s"])
        for row in rows
        if math.isfinite(float(row["input_adc_time_s"]))
        and float(row["input_adc_time_s"]) > 0.0
    ]
    adc_covered_s = (
        0.0
        if len(adc_values) < 2
        else adc_values[-1] - adc_values[0] + frame_counts[-1] / sample_rate
    )
    status_counts = Counter(
        str(row["status"])
        for row in rows
        if str(row["status"])
    )
    expected_interval_ms = expected_interval_s * 1000.0
    summary: dict[str, object] = {
        "callback_count": len(rows),
        "total_frames": total_frames,
        "delivered_audio_s": delivered_audio_s,
        "requested_duration_s": requested_duration_s,
        "stream_wall_s": stream_wall_s,
        "callback_span_s": callback_span_s,
        "adc_covered_s": adc_covered_s,
        "delivered_vs_requested_ratio": (
            delivered_audio_s / requested_duration_s
            if requested_duration_s > 0.0
            else 0.0
        ),
        "delivered_vs_stream_wall_ratio": (
            delivered_audio_s / stream_wall_s
            if stream_wall_s > 0.0
            else 0.0
        ),
        "adc_vs_callback_span_ratio": (
            adc_covered_s / (callback_span_s + expected_interval_s)
            if callback_span_s > 0.0
            else 0.0
        ),
        "expected_interval_ms": expected_interval_ms,
        "frame_size_mismatch_count": sum(
            frames != block_size for frames in frame_counts
        ),
        "callback_burst_count_under_half_interval": sum(
            value < expected_interval_ms * 0.5 for value in intervals_ms
        ),
        "callback_stall_count_over_double_interval": sum(
            value > expected_interval_ms * 2.0 for value in intervals_ms
        ),
        "status_counts": dict(status_counts),
        "adc_time_valid_count": len(adc_values),
        "processing_over_block_budget_count": sum(
            value > expected_interval_ms for value in processing_ms
        ),
        "adc_delta_nonpositive_count": sum(
            math.isfinite(float(row["adc_delta_ms"]))
            and float(row["adc_delta_ms"]) <= 0.0
            for row in rows[1:]
        ),
        "adc_delta_backward_count": sum(
            math.isfinite(float(row["adc_delta_ms"]))
            and float(row["adc_delta_ms"]) < 0.0
            for row in rows[1:]
        ),
        "adc_delta_repeated_count": sum(
            math.isfinite(float(row["adc_delta_ms"]))
            and float(row["adc_delta_ms"]) == 0.0
            for row in rows[1:]
        ),
        "current_time_delta_nonpositive_count": sum(
            math.isfinite(float(row["current_time_delta_ms"]))
            and float(row["current_time_delta_ms"]) <= 0.0
            for row in rows[1:]
        ),
        "current_time_delta_backward_count": sum(
            math.isfinite(float(row["current_time_delta_ms"]))
            and float(row["current_time_delta_ms"]) < 0.0
            for row in rows[1:]
        ),
        "current_time_delta_repeated_count": sum(
            math.isfinite(float(row["current_time_delta_ms"]))
            and float(row["current_time_delta_ms"]) == 0.0
            for row in rows[1:]
        ),
    }
    summary.update(distribution(intervals_ms, "callback_interval_ms"))
    summary.update(distribution(adc_deltas_ms, "adc_delta_ms"))
    summary.update(distribution(current_deltas_ms, "current_time_delta_ms"))
    summary.update(distribution(processing_ms, "processing_ms"))
    return summary


def enumerate_inputs(
    sd: Any,
    *,
    sample_rate: int,
    channels: int,
    dtype: str,
) -> dict[str, object]:
    hostapis = list(sd.query_hostapis())
    devices = list(sd.query_devices())
    inputs: list[dict[str, object]] = []
    for index, device in enumerate(devices):
        if int(device["max_input_channels"]) <= 0:
            continue
        support_error: str | None = None
        auto_convert_error: str | None = None
        try:
            sd.check_input_settings(
                device=index,
                channels=channels,
                dtype=dtype,
                samplerate=sample_rate,
            )
        except Exception as exc:
            support_error = f"{type(exc).__name__}: {exc}"
        hostapi_name = str(hostapis[int(device["hostapi"])]["name"])
        if hostapi_name == "Windows WASAPI":
            try:
                sd.check_input_settings(
                    device=index,
                    channels=channels,
                    dtype=dtype,
                    samplerate=sample_rate,
                    extra_settings=sd.WasapiSettings(auto_convert=True),
                )
            except Exception as exc:
                auto_convert_error = f"{type(exc).__name__}: {exc}"
        inputs.append(
            {
                "index": index,
                "name": str(device["name"]),
                "hostapi_index": int(device["hostapi"]),
                "hostapi": hostapi_name,
                "max_input_channels": int(device["max_input_channels"]),
                "default_samplerate": float(device["default_samplerate"]),
                "default_low_input_latency_s": float(
                    device["default_low_input_latency"]
                ),
                "default_high_input_latency_s": float(
                    device["default_high_input_latency"]
                ),
                "supports_requested_format": support_error is None,
                "support_error": support_error,
                "supports_requested_format_with_wasapi_auto_convert": (
                    hostapi_name == "Windows WASAPI"
                    and auto_convert_error is None
                ),
                "wasapi_auto_convert_support_error": auto_convert_error,
            }
        )
    return {
        "portaudio_version": list(sd.get_portaudio_version()),
        "requested_format": {
            "sample_rate": sample_rate,
            "channels": channels,
            "dtype": dtype,
        },
        "hostapis": [
            {
                "index": index,
                "name": str(hostapi["name"]),
                "device_count": sum(
                    int(device["hostapi"]) == index for device in devices
                ),
                "default_input_device": int(hostapi["default_input_device"]),
            }
            for index, hostapi in enumerate(hostapis)
        ],
        "inputs": inputs,
    }


def time_info_value(time_info: Any, name: str) -> float:
    try:
        return float(getattr(time_info, name))
    except (AttributeError, TypeError, ValueError):
        try:
            return float(time_info[name])
        except (KeyError, TypeError, ValueError):
            return math.nan


def run_probe(
    sd: Any,
    *,
    device: int,
    duration_s: float,
    sample_rate: int,
    block_size: int,
    channels: int,
    dtype: str,
    wasapi_auto_convert: bool = False,
    process_block: Callable[[np.ndarray], None] | None = None,
) -> tuple[list[dict[str, float | int | str]], dict[str, object]]:
    rows: list[dict[str, float | int | str]] = []
    row_lock = threading.Lock()
    previous_callback_s: float | None = None
    previous_adc_s: float | None = None
    previous_current_s: float | None = None

    def callback(
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: Any,
    ) -> None:
        nonlocal previous_callback_s, previous_adc_s, previous_current_s
        callback_s = time.perf_counter()
        adc_s = time_info_value(time_info, "inputBufferAdcTime")
        current_s = time_info_value(time_info, "currentTime")
        values = np.asarray(indata[:, 0], dtype=np.float32)
        processing_started = time.perf_counter()
        if process_block is not None:
            process_block(values)
        processing_ms = 1000.0 * (time.perf_counter() - processing_started)
        callback_interval_ms = (
            0.0
            if previous_callback_s is None
            else 1000.0 * (callback_s - previous_callback_s)
        )
        adc_delta_ms = (
            math.nan
            if previous_adc_s is None
            or not math.isfinite(adc_s)
            or not math.isfinite(previous_adc_s)
            else 1000.0 * (adc_s - previous_adc_s)
        )
        current_delta_ms = (
            math.nan
            if previous_current_s is None
            or not math.isfinite(current_s)
            or not math.isfinite(previous_current_s)
            else 1000.0 * (current_s - previous_current_s)
        )
        row = {
            "callback_index": len(rows) + 1,
            "frames": int(frames),
            "callback_monotonic_s": callback_s,
            "callback_interval_ms": callback_interval_ms,
            "input_adc_time_s": adc_s,
            "adc_delta_ms": adc_delta_ms,
            "current_time_s": current_s,
            "current_time_delta_ms": current_delta_ms,
            "adc_to_current_ms": (
                math.nan
                if not math.isfinite(adc_s) or not math.isfinite(current_s)
                else 1000.0 * (current_s - adc_s)
            ),
            "status": str(status) if status else "",
            "processing_ms": processing_ms,
            "input_peak": float(np.max(np.abs(values))) if values.size else 0.0,
            "input_rms": (
                float(np.sqrt(np.mean(np.square(values, dtype=np.float64))))
                if values.size
                else 0.0
            ),
        }
        with row_lock:
            rows.append(row)
        previous_callback_s = callback_s
        previous_adc_s = adc_s
        previous_current_s = current_s

    wall_started = time.perf_counter()
    extra_settings = (
        sd.WasapiSettings(auto_convert=True)
        if wasapi_auto_convert
        else None
    )
    with sd.InputStream(
        samplerate=sample_rate,
        blocksize=block_size,
        channels=channels,
        dtype=dtype,
        device=device,
        callback=callback,
        extra_settings=extra_settings,
    ) as stream:
        stream_started = time.perf_counter()
        time.sleep(duration_s)
        stream_wall_s = time.perf_counter() - stream_started
        stream_latency_s = float(stream.latency)
    wall_total_s = time.perf_counter() - wall_started
    summary = summarize_rows(
        rows,
        sample_rate=sample_rate,
        block_size=block_size,
        requested_duration_s=duration_s,
        stream_wall_s=stream_wall_s,
    )
    summary.update(
        {
            "device_index": device,
            "stream_latency_s": stream_latency_s,
            "open_and_close_wall_s": wall_total_s,
        }
    )
    return rows, summary


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "callback_index",
        "frames",
        "callback_monotonic_s",
        "callback_interval_ms",
        "input_adc_time_s",
        "adc_delta_ms",
        "current_time_s",
        "current_time_delta_ms",
        "adc_to_current_ms",
        "status",
        "processing_ms",
        "input_peak",
        "input_rms",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure physical input cadence without DSP or endpoint output."
    )
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--device", type=int)
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument("--sample-rate", type=int, default=16_000)
    parser.add_argument("--block-size", type=int, default=320)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--dtype", default="float32")
    parser.add_argument("--wasapi-auto-convert", action="store_true")
    parser.add_argument(
        "--method",
        choices=("capture_only", "bypass", "rnnoise"),
        default="capture_only",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sd = import_sounddevice()
    if args.list_devices:
        write_json(
            args.output,
            enumerate_inputs(
                sd,
                sample_rate=args.sample_rate,
                channels=args.channels,
                dtype=args.dtype,
            ),
        )
        return
    if args.device is None:
        raise SystemExit("--device is required unless --list-devices is used.")

    device = sd.query_devices(args.device)
    hostapi = sd.query_hostapis(int(device["hostapi"]))
    result: dict[str, object] = {
        "status": "failed",
        "probe_contract": {
            "sample_rate": args.sample_rate,
            "block_size": args.block_size,
            "block_duration_ms": 1000.0 * args.block_size / args.sample_rate,
            "channels": args.channels,
            "dtype": args.dtype,
            "dsp": args.method,
            "audio_saved": False,
            "wasapi_auto_convert": args.wasapi_auto_convert,
        },
        "device": {
            "index": args.device,
            "name": str(device["name"]),
            "hostapi": str(hostapi["name"]),
            "default_samplerate": float(device["default_samplerate"]),
        },
    }
    processor: Any | None = None
    try:
        process_block: Callable[[np.ndarray], None] | None = None
        if args.method != "capture_only":
            from realtime_audio.windows_realtime import (
                RealtimeBlockProcessor,
                RealtimeConfig,
            )

            processor = RealtimeBlockProcessor(
                RealtimeConfig(
                    sample_rate=args.sample_rate,
                    block_ms=1000.0 * args.block_size / args.sample_rate,
                    method=args.method,
                )
            )

            def process_block(values: np.ndarray) -> None:
                assert processor is not None
                processor.process_block(values)

        rows, summary = run_probe(
            sd,
            device=args.device,
            duration_s=args.duration,
            sample_rate=args.sample_rate,
            block_size=args.block_size,
            channels=args.channels,
            dtype=args.dtype,
            wasapi_auto_convert=args.wasapi_auto_convert,
            process_block=process_block,
        )
        result["status"] = "completed"
        result["summary"] = summary
        if args.csv is not None:
            write_csv(args.csv, rows)
            result["callback_csv"] = str(args.csv)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        write_json(args.output, result)
        raise
    finally:
        if processor is not None:
            processor.close()
    write_json(args.output, result)


if __name__ == "__main__":
    main()
