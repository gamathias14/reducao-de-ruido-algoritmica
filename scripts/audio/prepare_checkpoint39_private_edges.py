from __future__ import annotations

import argparse
import hashlib
import json
import math
import wave
from pathlib import Path

import numpy as np


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise ValueError(f"Esperado WAV mono PCM16: {path}")
        sample_rate = handle.getframerate()
        values = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    return sample_rate, values.astype(np.float32) / 32768.0


def write_wav(path: Path, sample_rate: int, samples: np.ndarray) -> None:
    pcm = np.rint(np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dbfs(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-12))


def edge_metrics(samples: np.ndarray, sample_rate: int) -> dict[str, float | int]:
    block_size = max(1, int(round(0.02 * sample_rate)))
    count = samples.size // block_size
    blocks = samples[: count * block_size].reshape(count, block_size)
    levels = np.sqrt(np.mean(np.square(blocks, dtype=np.float64), axis=1))
    active = np.flatnonzero(levels > 10.0 ** (-55.0 / 20.0))
    first_active_ms = None if not len(active) else int(active[0]) * 20
    last_active_ms = None if not len(active) else int(active[-1] + 1) * 20
    edge_frames = min(samples.size, sample_rate // 2)
    return {
        "duration_s": samples.size / sample_rate,
        "first_active_ms": first_active_ms,
        "last_active_ms": last_active_ms,
        "first_500ms_rms_dbfs": dbfs(
            float(np.sqrt(np.mean(np.square(samples[:edge_frames], dtype=np.float64))))
        ),
        "last_500ms_rms_dbfs": dbfs(
            float(np.sqrt(np.mean(np.square(samples[-edge_frames:], dtype=np.float64))))
        ),
        "peak": float(np.max(np.abs(samples))),
    }


def common_activity_cut(
    first: np.ndarray,
    second: np.ndarray,
    sample_rate: int,
    *,
    threshold_dbfs: float = -55.0,
    margin_ms: int = 100,
) -> tuple[int, int]:
    block_size = max(1, int(round(0.02 * sample_rate)))
    count = min(first.size, second.size) // block_size
    first_levels = np.sqrt(
        np.mean(
            np.square(first[: count * block_size].reshape(count, block_size)),
            dtype=np.float64,
            axis=1,
        )
    )
    second_levels = np.sqrt(
        np.mean(
            np.square(second[: count * block_size].reshape(count, block_size)),
            dtype=np.float64,
            axis=1,
        )
    )
    threshold = 10.0 ** (threshold_dbfs / 20.0)
    active = np.flatnonzero(
        (first_levels > threshold) & (second_levels > threshold)
    )
    if not len(active):
        raise ValueError("Nenhuma atividade encontrada no par privado.")
    margin = int(round(margin_ms * sample_rate / 1000.0))
    start = max(0, int(active[0]) * block_size - margin)
    stop = min(
        min(first.size, second.size),
        int(active[-1] + 1) * block_size + margin,
    )
    return start, stop


def apply_fade(samples: np.ndarray, sample_rate: int, fade_ms: int) -> np.ndarray:
    result = samples.copy()
    count = min(result.size // 2, int(round(fade_ms * sample_rate / 1000.0)))
    if count <= 0:
        return result
    phase = np.linspace(0.0, 0.5 * math.pi, count, endpoint=True)
    fade_in = np.square(np.sin(phase)).astype(np.float32)
    result[:count] *= fade_in
    result[-count:] *= fade_in[::-1]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--processed", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path, required=True)
    parser.add_argument("--fade-ms", type=int, default=80)
    args = parser.parse_args()

    raw_rate, raw = read_wav(args.raw)
    processed_rate, processed = read_wav(args.processed)
    if raw_rate != processed_rate:
        raise ValueError("Taxas do par privado divergem.")
    common = min(raw.size, processed.size)
    raw = raw[:common]
    processed = processed[:common]
    start, stop = common_activity_cut(raw, processed, raw_rate)
    raw_cut = raw[start:stop]
    processed_cut = processed[start:stop]
    raw_fade = apply_fade(raw_cut, raw_rate, args.fade_ms)
    processed_fade = apply_fade(processed_cut, raw_rate, args.fade_ms)

    args.private_output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "A_raw_common_cut.wav": raw_cut,
        "B_processed_common_cut.wav": processed_cut,
        "A_raw_common_cut_fade80.wav": raw_fade,
        "B_processed_common_cut_fade80.wav": processed_fade,
    }
    files = []
    for name, samples in outputs.items():
        path = args.private_output_dir / name
        write_wav(path, raw_rate, samples)
        files.append(
            {
                "name": name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "metrics": edge_metrics(samples, raw_rate),
            }
        )

    summary = {
        "privacy": "private_audio_outside_repository",
        "source_authorization": "checkpoint38_explicit_user_authorization",
        "new_voice_recording": False,
        "sample_rate_hz": raw_rate,
        "common_cut": {
            "start_sample": start,
            "stop_sample": stop,
            "start_ms": 1000.0 * start / raw_rate,
            "stop_ms": 1000.0 * stop / raw_rate,
            "margin_ms": 100,
            "threshold_dbfs": -55.0,
        },
        "fade_ms": args.fade_ms,
        "original_metrics": {
            "A_raw": edge_metrics(raw, raw_rate),
            "B_processed": edge_metrics(processed, raw_rate),
        },
        "files": files,
        "interpretation": (
            "Common cut and equal fade are private listening preparations only; "
            "original matrix metrics remain unmasked."
        ),
    }
    args.public_summary.parent.mkdir(parents=True, exist_ok=True)
    args.public_summary.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (args.private_output_dir / "private_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(args.public_summary)


if __name__ == "__main__":
    main()
