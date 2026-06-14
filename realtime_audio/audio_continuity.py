from __future__ import annotations

import argparse
import json
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ContinuityThresholds:
    sample_jump: float = 0.12
    boundary_jump: float = 0.12
    zero_epsilon: float = 1e-7
    repeated_tolerance: float = 1e-7
    long_zero_samples: int = 160
    callback_tolerance_fraction: float = 0.35


def _longest_true_run(mask: np.ndarray) -> int:
    longest = 0
    current = 0
    for value in mask:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def analyze_blocks(
    blocks: list[np.ndarray] | np.ndarray,
    *,
    block_indices: list[int] | None = None,
    callback_times_s: list[float] | None = None,
    expected_interval_s: float | None = None,
    status_events: list[bool] | None = None,
    thresholds: ContinuityThresholds | None = None,
) -> dict[str, object]:
    limits = thresholds or ContinuityThresholds()
    arrays = [np.asarray(block, dtype=np.float32).reshape(-1) for block in blocks]
    if any(block.size == 0 for block in arrays):
        raise ValueError("Os blocos não podem ser vazios.")

    count = len(arrays)
    indices = block_indices or list(range(count))
    if len(indices) != count:
        raise ValueError("block_indices deve ter o mesmo tamanho de blocks.")
    if callback_times_s is not None and len(callback_times_s) != count:
        raise ValueError("callback_times_s deve ter o mesmo tamanho de blocks.")
    if status_events is not None and len(status_events) != count:
        raise ValueError("status_events deve ter o mesmo tamanho de blocks.")

    rms = [
        float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))
        for block in arrays
    ]
    peaks = [float(np.max(np.abs(block))) for block in arrays]
    zero_blocks = [
        index
        for index, peak in zip(indices, peaks)
        if peak <= limits.zero_epsilon
    ]
    suspicious_zero_blocks: list[int] = []
    for position, index in enumerate(indices):
        if index not in zero_blocks:
            continue
        previous_active = position > 0 and peaks[position - 1] > limits.zero_epsilon
        next_active = position + 1 < count and peaks[position + 1] > limits.zero_epsilon
        if previous_active and next_active:
            suspicious_zero_blocks.append(index)

    excessive_sample_jumps: list[dict[str, float | int]] = []
    long_zero_runs: list[dict[str, int]] = []
    for index, block in zip(indices, arrays):
        differences = np.abs(np.diff(block))
        jump_count = int(np.count_nonzero(differences > limits.sample_jump))
        if jump_count:
            excessive_sample_jumps.append(
                {
                    "block_index": index,
                    "count": jump_count,
                    "maximum": float(np.max(differences)),
                }
            )
        longest = _longest_true_run(np.abs(block) <= limits.zero_epsilon)
        if longest >= limits.long_zero_samples:
            long_zero_runs.append(
                {"block_index": index, "longest_zero_run_samples": longest}
            )

    boundary_discontinuities: list[dict[str, float | int]] = []
    repeated_blocks: list[int] = []
    for position in range(1, count):
        jump = abs(float(arrays[position][0]) - float(arrays[position - 1][-1]))
        if jump > limits.boundary_jump:
            boundary_discontinuities.append(
                {
                    "previous_block_index": indices[position - 1],
                    "block_index": indices[position],
                    "jump": jump,
                }
            )
        if np.allclose(
            arrays[position],
            arrays[position - 1],
            rtol=0.0,
            atol=limits.repeated_tolerance,
        ):
            repeated_blocks.append(indices[position])

    missing_blocks: list[int] = []
    for previous, current in zip(indices, indices[1:]):
        if current > previous + 1:
            missing_blocks.extend(range(previous + 1, current))

    callback_intervals_ms: list[float] = []
    callback_cadence_outliers: list[dict[str, float | int]] = []
    if callback_times_s is not None and count > 1:
        intervals = np.diff(np.asarray(callback_times_s, dtype=np.float64))
        callback_intervals_ms = (intervals * 1000.0).tolist()
        if expected_interval_s is not None:
            tolerance = expected_interval_s * limits.callback_tolerance_fraction
            for position, interval in enumerate(intervals, start=1):
                if abs(float(interval) - expected_interval_s) > tolerance:
                    callback_cadence_outliers.append(
                        {
                            "block_index": indices[position],
                            "interval_ms": float(interval * 1000.0),
                        }
                    )

    expected_count = (
        indices[-1] - indices[0] + 1
        if indices
        else 0
    )
    return {
        "block_count_received": count,
        "block_count_expected_from_indices": expected_count,
        "missing_block_indices": missing_blocks,
        "zero_block_indices": zero_blocks,
        "suspicious_zero_block_indices": suspicious_zero_blocks,
        "long_zero_runs": long_zero_runs,
        "repeated_block_indices": repeated_blocks,
        "excessive_sample_jumps": excessive_sample_jumps,
        "boundary_discontinuities": boundary_discontinuities,
        "rms_per_block": rms,
        "peak_per_block": peaks,
        "callback_intervals_ms": callback_intervals_ms,
        "callback_cadence_outliers": callback_cadence_outliers,
        "status_event_block_indices": (
            []
            if status_events is None
            else [
                index
                for index, active in zip(indices, status_events)
                if active
            ]
        ),
        "thresholds": asdict(limits),
    }


def read_pcm16_wav(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as handle:
        if handle.getsampwidth() != 2:
            raise ValueError("O analisador WAV aceita apenas PCM de 16 bits.")
        sample_rate = handle.getframerate()
        channels = handle.getnchannels()
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    samples = samples.reshape(-1, channels)[:, 0]
    return sample_rate, (samples.astype(np.float32) / 32768.0)


def analyze_wav(path: Path, block_size: int = 320) -> dict[str, object]:
    sample_rate, samples = read_pcm16_wav(path)
    full_blocks = samples.size // block_size
    blocks = samples[: full_blocks * block_size].reshape(full_blocks, block_size)
    result = analyze_blocks(blocks)
    result.update(
        {
            "path": str(path),
            "sample_rate_hz": sample_rate,
            "block_size_samples": block_size,
            "trailing_samples": int(samples.size - full_blocks * block_size),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detecta descontinuidades objetivas em WAV PCM16."
    )
    parser.add_argument("wav", type=Path)
    parser.add_argument("--block-size", type=int, default=320)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze_wav(args.wav, args.block_size)
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output is None:
        print(payload)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(args.output)


if __name__ == "__main__":
    main()
