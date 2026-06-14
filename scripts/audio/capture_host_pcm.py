from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import numpy as np


SAMPLE_RATE = 16_000
FRAMES_PER_BLOCK = 320
DEFAULT_MIN_RMS_DBFS = -50.0


def select_input_device(
    devices: list[Any],
    hostapis: list[Any],
    *,
    device_name: str,
    hostapi_name: str,
) -> int:
    matches = [
        index
        for index, device in enumerate(devices)
        if str(device["name"]) == device_name
        and int(device["max_input_channels"]) > 0
        and str(hostapis[int(device["hostapi"])]["name"]) == hostapi_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one input named {device_name!r} on "
            f"{hostapi_name!r}, found {matches}"
        )
    return matches[0]


def summarize_pcm(samples: np.ndarray, wall_s: float) -> dict[str, object]:
    values = np.asarray(samples, dtype=np.int16).reshape(-1)
    normalized = values.astype(np.float64) / 32768.0
    duration_s = len(values) / SAMPLE_RATE
    peak = float(np.max(np.abs(normalized))) if len(values) else 0.0
    rms = float(np.sqrt(np.mean(normalized * normalized))) if len(values) else 0.0
    return {
        "sample_rate": SAMPLE_RATE,
        "frames_per_block": FRAMES_PER_BLOCK,
        "sample_count": len(values),
        "block_count": len(values) // FRAMES_PER_BLOCK,
        "audio_duration_s": duration_s,
        "capture_wall_s": wall_s,
        "audio_to_wall_ratio": duration_s / wall_s if wall_s > 0.0 else 0.0,
        "peak": peak,
        "peak_dbfs": 20.0 * math.log10(max(peak, 1e-12)),
        "rms": rms,
        "rms_dbfs": 20.0 * math.log10(max(rms, 1e-12)),
        "clipped_samples": int(np.count_nonzero(np.abs(values.astype(np.int32)) >= 32767)),
        "pcm_sha256": hashlib.sha256(values.astype("<i2").tobytes()).hexdigest(),
    }


def validate_capture(
    summary: dict[str, object],
    *,
    expected_block_count: int,
    min_rms_dbfs: float = DEFAULT_MIN_RMS_DBFS,
) -> list[str]:
    failures: list[str] = []
    expected_sample_count = expected_block_count * FRAMES_PER_BLOCK
    if int(summary["sample_count"]) != expected_sample_count:
        failures.append("sample_count")
    if int(summary["block_count"]) != expected_block_count:
        failures.append("block_count")
    if int(summary["clipped_samples"]) != 0:
        failures.append("clipping")
    if float(summary["rms_dbfs"]) < min_rms_dbfs:
        failures.append("useful_level")
    pcm_hash = str(summary["pcm_sha256"])
    if len(pcm_hash) != 64 or any(
        character not in "0123456789abcdef" for character in pcm_hash
    ):
        failures.append("pcm_sha256")
    return failures


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=20.0)
    parser.add_argument(
        "--device-name",
        default="Microfone (USB Audio Device)",
    )
    parser.add_argument("--hostapi", default="Windows WASAPI")
    parser.add_argument("--countdown", type=int, default=3)
    parser.add_argument(
        "--min-rms-dbfs",
        type=float,
        default=DEFAULT_MIN_RMS_DBFS,
    )
    parser.add_argument("--pcm-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    if args.duration <= 0.0:
        raise ValueError("duration must be positive")
    if args.pcm_output.exists() or args.summary_output.exists():
        raise FileExistsError("capture outputs already exist")
    block_count = int(round(args.duration * 50.0))
    sample_count = block_count * FRAMES_PER_BLOCK

    import sounddevice as sd

    devices = list(sd.query_devices())
    hostapis = list(sd.query_hostapis())
    device = select_input_device(
        devices,
        hostapis,
        device_name=args.device_name,
        hostapi_name=args.hostapi,
    )
    settings = sd.WasapiSettings(auto_convert=True)
    sd.check_input_settings(
        device=device,
        channels=1,
        dtype="int16",
        samplerate=SAMPLE_RATE,
        extra_settings=settings,
    )

    for remaining in range(max(0, args.countdown), 0, -1):
        print(f"Recording starts in {remaining}...", flush=True)
        time.sleep(1.0)
    print("Recording.", flush=True)
    started = time.perf_counter()
    samples = sd.rec(
        sample_count,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=device,
        blocking=True,
        extra_settings=settings,
    )
    wall_s = time.perf_counter() - started
    print("Recording complete.", flush=True)

    pcm = np.asarray(samples, dtype="<i2").reshape(-1)
    args.pcm_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    measurements = summarize_pcm(pcm, wall_s)
    failures = validate_capture(
        measurements,
        expected_block_count=block_count,
        min_rms_dbfs=args.min_rms_dbfs,
    )
    atomic_write_bytes(args.pcm_output, pcm.tobytes())
    summary = {
        "status": "completed",
        "valid": not failures,
        "failures": failures,
        "device_index": device,
        "device_name": args.device_name,
        "hostapi": args.hostapi,
        "minimum_rms_dbfs": args.min_rms_dbfs,
        **measurements,
    }
    atomic_write_json(args.summary_output, summary)
    if failures:
        raise SystemExit(
            "Capture completed but failed validation: " + ", ".join(failures)
        )


if __name__ == "__main__":
    main()
