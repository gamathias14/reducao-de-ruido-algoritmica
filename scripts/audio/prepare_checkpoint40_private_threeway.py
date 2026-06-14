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
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    return sample_rate, samples.astype(np.float32) / 32768.0


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


def block_levels(samples: np.ndarray, block_size: int) -> np.ndarray:
    count = samples.size // block_size
    blocks = samples[: count * block_size].reshape(count, block_size)
    return np.sqrt(np.mean(np.square(blocks, dtype=np.float64), axis=1))


def common_activity_cut(
    signals: list[np.ndarray],
    sample_rate: int,
    *,
    threshold_dbfs: float = -55.0,
    margin_ms: int = 100,
) -> tuple[int, int]:
    block_size = int(round(0.02 * sample_rate))
    common = min(signal.size for signal in signals)
    levels = [
        block_levels(signal[:common], block_size)
        for signal in signals
    ]
    count = min(level.size for level in levels)
    threshold = 10.0 ** (threshold_dbfs / 20.0)
    active = np.ones(count, dtype=bool)
    for level in levels:
        active &= level[:count] > threshold
    indices = np.flatnonzero(active)
    if not len(indices):
        raise ValueError("Nenhuma atividade comum encontrada nos tres sinais.")
    margin = int(round(margin_ms * sample_rate / 1000.0))
    start = max(0, int(indices[0]) * block_size - margin)
    stop = min(
        common,
        int(indices[-1] + 1) * block_size + margin,
    )
    return start, stop


def metrics(samples: np.ndarray, sample_rate: int) -> dict[str, float | int | None]:
    block_size = int(round(0.02 * sample_rate))
    levels = block_levels(samples, block_size)
    active = np.flatnonzero(levels > 10.0 ** (-55.0 / 20.0))
    return {
        "duration_s": samples.size / sample_rate,
        "first_active_ms": None if not len(active) else int(active[0]) * 20,
        "last_active_ms": None if not len(active) else int(active[-1] + 1) * 20,
        "rms_dbfs": dbfs(
            float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
        ),
        "peak": float(np.max(np.abs(samples))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--pre-bridge", type=Path, required=True)
    parser.add_argument("--endpoint-aligned", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-summary", type=Path, required=True)
    args = parser.parse_args()

    loaded = [
        read_wav(args.raw),
        read_wav(args.pre_bridge),
        read_wav(args.endpoint_aligned),
    ]
    rates = {rate for rate, _ in loaded}
    if len(rates) != 1:
        raise ValueError(f"Taxas divergentes: {sorted(rates)}")
    sample_rate = rates.pop()
    signals = [samples for _, samples in loaded]
    common = min(signal.size for signal in signals)
    signals = [signal[:common] for signal in signals]
    start, stop = common_activity_cut(signals, sample_rate)

    args.private_output_dir.mkdir(parents=True, exist_ok=True)
    names = (
        "A_raw_common_cut.wav",
        "B_pre_bridge_common_cut.wav",
        "C_endpoint_common_cut.wav",
    )
    files = []
    for name, signal in zip(names, signals):
        output = args.private_output_dir / name
        cut = signal[start:stop]
        write_wav(output, sample_rate, cut)
        files.append(
            {
                "name": name,
                "bytes": output.stat().st_size,
                "sha256": sha256(output),
                "metrics": metrics(cut, sample_rate),
            }
        )

    summary = {
        "privacy": "private_audio_outside_repository",
        "source_authorization": "checkpoint38_explicit_user_authorization",
        "new_voice_recording": False,
        "sample_rate_hz": sample_rate,
        "alignment": {
            "raw_pre_bridge": "same_callback_block_timeline",
            "endpoint": (
                "checkpoint38_private_envelope_alignment_for_listening_only"
            ),
            "latency_interpretation": "not_a_physical_latency_measurement",
        },
        "common_cut": {
            "start_sample": start,
            "stop_sample": stop,
            "start_ms": 1000.0 * start / sample_rate,
            "stop_ms": 1000.0 * stop / sample_rate,
            "margin_ms": 100,
            "threshold_dbfs": -55.0,
            "requires_activity_in_all_three_signals": True,
        },
        "fade_ms": 0,
        "files": files,
        "listening_question": (
            "O chiado durante a fala ja aparece em B (pre-bridge), ou surge "
            "somente em C (endpoint)?"
        ),
    }
    args.public_summary.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    args.public_summary.write_text(text, encoding="utf-8")
    (args.private_output_dir / "private_manifest.json").write_text(
        text,
        encoding="utf-8",
    )
    print(args.public_summary)


if __name__ == "__main__":
    main()
