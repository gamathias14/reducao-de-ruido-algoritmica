from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
import wave
from pathlib import Path
from typing import Any

import numpy as np


SCENARIOS = (
    ("01-bypass-physical", "bypass"),
    ("02-rnnoise-physical", "rnnoise"),
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inspect_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frame_count = handle.getnframes()
        payload = handle.readframes(frame_count)
    if channels != 1 or sample_width != 2 or sample_rate != 16_000:
        raise ValueError(f"unexpected endpoint WAV format: {path}")
    samples = np.frombuffer(payload, dtype="<i2")
    normalized = samples.astype(np.float64) / 32768.0
    return {
        "path": str(path),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_count": int(samples.size),
        "duration_s": samples.size / sample_rate,
        "peak": float(np.max(np.abs(normalized))) if samples.size else 0.0,
        "rms": (
            float(np.sqrt(np.mean(normalized * normalized)))
            if samples.size
            else 0.0
        ),
        "clipped_samples": int(
            np.count_nonzero(np.abs(samples.astype(np.int32)) >= 32767)
        ),
        "wav_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def analyze(private_root: Path, output: Path) -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    for scenario, method in SCENARIOS:
        root = private_root / scenario
        client = read_json(root / "client.json")
        wav = inspect_wav(root / "endpoint.wav")
        bridge = client.get("bridge", {})
        checks = {
            "client_completed": client.get("status") == "completed",
            "method": client.get("method") == method,
            "block_count": client.get("block_count") == 1_000,
            "sequence": client.get("sequence_errors") == 0,
            "crc": client.get("crc_errors") == 0,
            "framing": client.get("framing_errors") == 0,
            "bridge_submitted": bridge.get("submitted") == 1_000,
            "bridge_sent": bridge.get("sent") == 1_000,
            "bridge_drops": bridge.get("user_queue_dropped_total") == 0,
            "bridge_stop_drops": bridge.get("stop_timeout_dropped") == 0,
            "bridge_writes": bridge.get("write_errors") == 0,
            "endpoint_duration": wav["duration_s"] >= 23.5,
            "endpoint_nonzero": wav["rms"] > 0.0,
            "endpoint_clipping": wav["clipped_samples"] == 0,
        }
        failures.extend(
            f"{scenario}:{name}"
            for name, passed in checks.items()
            if not passed
        )
        rows.append(
            {
                "scenario": scenario,
                "method": method,
                "input_sha256": client.get("input_sha256"),
                "output_sha256": client.get("output_float32_sha256"),
                "processing_p99_ms": client.get("processing_ms_p99"),
                "processing_max_ms": client.get("processing_ms_max"),
                "bridge": {
                    key: bridge.get(key)
                    for key in (
                        "submitted",
                        "sent",
                        "user_queue_dropped_total",
                        "stop_timeout_dropped",
                        "write_errors",
                        "pending_user_blocks",
                        "target_driver_depth",
                        "user_queue_peak_blocks",
                        "bridge_buffer_latency_estimated_ms",
                    )
                },
                "endpoint": wav,
                "checks": checks,
            }
        )

    if rows[0]["input_sha256"] != rows[1]["input_sha256"]:
        failures.append("paired_input_hash")
    if rows[0]["endpoint"]["sample_count"] != rows[1]["endpoint"]["sample_count"]:
        failures.append("paired_endpoint_length")

    result = {
        "status": "accepted" if not failures else "rejected",
        "failures": failures,
        "contract": {
            "sample_rate": 16_000,
            "frames_per_block": 320,
            "pcm_v1_changed": False,
            "driver_depth": 2,
            "local_queue": 4,
        },
        "scenarios": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return result


def prepare_blind(private_root: Path, result: dict[str, Any]) -> Path:
    if result["status"] != "accepted":
        raise ValueError("endpoint gate must pass before blind preparation")
    blind_root = private_root / "blind"
    if blind_root.exists():
        raise FileExistsError(f"blind directory already exists: {blind_root}")
    blind_root.mkdir(parents=True)
    labels = ["A", "B"]
    if secrets.randbits(1):
        labels.reverse()
    mapping: dict[str, str] = {}
    for (scenario, method), label in zip(SCENARIOS, labels):
        source = private_root / scenario / "endpoint.wav"
        destination = blind_root / f"{label}.wav"
        shutil.copyfile(source, destination)
        mapping[label] = method
    key = {
        "status": "sealed",
        "mapping": mapping,
        "source": "paired_endpoint_capture",
    }
    (blind_root / "key.json").write_text(
        json.dumps(key, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return blind_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-blind", action="store_true")
    args = parser.parse_args()
    result = analyze(args.private_root, args.output)
    if result["status"] != "accepted":
        raise SystemExit(1)
    if args.prepare_blind:
        prepare_blind(args.private_root, result)


if __name__ == "__main__":
    main()
