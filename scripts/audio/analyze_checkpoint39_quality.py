from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import wave
from pathlib import Path

import numpy as np


SAMPLE_RATE = 16_000
BLOCK_SIZE = 320
WINDOW_CLASSES = ("silence", "noise", "active")
BANDS_HZ = {
    "low_0_1k": (0.0, 1_000.0),
    "mid_1_4k": (1_000.0, 4_000.0),
    "high_4_8k": (4_000.0, 8_001.0),
}


def read_pcm16(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as handle:
        if (
            handle.getframerate() != SAMPLE_RATE
            or handle.getnchannels() != 1
            or handle.getsampwidth() != 2
        ):
            raise ValueError(f"Formato WAV inesperado: {path}")
        values = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    return values.astype(np.float32) / 32768.0


def dbfs(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-12))


def block_view(samples: np.ndarray) -> np.ndarray:
    count = samples.size // BLOCK_SIZE
    return samples[: count * BLOCK_SIZE].reshape(count, BLOCK_SIZE)


def block_rms(blocks: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean(np.square(blocks, dtype=np.float64), axis=1))


def classify_blocks(raw_blocks: np.ndarray) -> np.ndarray:
    levels = 20.0 * np.log10(np.maximum(block_rms(raw_blocks), 1e-12))
    labels = np.full(levels.shape, "noise", dtype=object)
    labels[levels <= -85.0] = "silence"
    labels[levels > -45.0] = "active"
    return labels


def align_endpoint(reference: np.ndarray, endpoint: np.ndarray) -> tuple[np.ndarray, int, float]:
    reference_blocks = block_view(reference)
    endpoint_blocks = block_view(endpoint)
    reference_envelope = block_rms(reference_blocks)
    endpoint_envelope = block_rms(endpoint_blocks)
    best_lag = 0
    best_score = -1.0
    max_lag = min(300, max(0, len(endpoint_envelope) - 10))
    for lag in range(-50, max_lag + 1):
        ref_start = max(0, -lag)
        endpoint_start = max(0, lag)
        count = min(
            len(reference_envelope) - ref_start,
            len(endpoint_envelope) - endpoint_start,
        )
        if count < 100:
            continue
        left = reference_envelope[ref_start : ref_start + count]
        right = endpoint_envelope[endpoint_start : endpoint_start + count]
        left = left - float(np.mean(left))
        right = right - float(np.mean(right))
        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        score = 0.0 if denominator <= 0.0 else float(np.dot(left, right) / denominator)
        if score > best_score:
            best_score = score
            best_lag = lag

    aligned = np.zeros(reference.size, dtype=np.float32)
    ref_start = max(0, -best_lag) * BLOCK_SIZE
    endpoint_start = max(0, best_lag) * BLOCK_SIZE
    count = min(reference.size - ref_start, endpoint.size - endpoint_start)
    if count > 0:
        aligned[ref_start : ref_start + count] = endpoint[
            endpoint_start : endpoint_start + count
        ]
    return aligned, best_lag, best_score


def edge_metrics(samples: np.ndarray) -> dict[str, float | int]:
    near_zero = np.abs(samples) <= (0.5 / 32768.0)
    leading = 0
    for value in near_zero:
        if not value:
            break
        leading += 1
    trailing = 0
    for value in near_zero[::-1]:
        if not value:
            break
        trailing += 1
    edge = min(samples.size, SAMPLE_RATE // 2)
    first_rms = float(np.sqrt(np.mean(np.square(samples[:edge], dtype=np.float64))))
    last_rms = float(np.sqrt(np.mean(np.square(samples[-edge:], dtype=np.float64))))
    return {
        "duration_s": samples.size / SAMPLE_RATE,
        "leading_digital_zero_ms": 1_000.0 * leading / SAMPLE_RATE,
        "trailing_digital_zero_ms": 1_000.0 * trailing / SAMPLE_RATE,
        "first_500ms_rms_dbfs": dbfs(first_rms),
        "last_500ms_rms_dbfs": dbfs(last_rms),
    }


def spectral_metrics(
    samples: np.ndarray,
    labels: np.ndarray,
) -> dict[str, dict[str, float | int]]:
    blocks = block_view(samples)
    count = min(len(blocks), len(labels))
    blocks = blocks[:count]
    labels = labels[:count]
    window = np.hanning(BLOCK_SIZE).astype(np.float64)
    frequencies = np.fft.rfftfreq(BLOCK_SIZE, 1.0 / SAMPLE_RATE)
    result: dict[str, dict[str, float | int]] = {}
    for label in WINDOW_CLASSES:
        selected = blocks[labels == label]
        if not len(selected):
            result[label] = {"block_count": 0}
            continue
        rms_values = block_rms(selected)
        spectra = np.fft.rfft(selected.astype(np.float64) * window, axis=1)
        powers = np.square(np.abs(spectra))
        total_spectral_power = np.maximum(np.sum(powers, axis=1), 1e-24)
        metrics: dict[str, float | int] = {
            "block_count": int(len(selected)),
            "rms_dbfs": dbfs(float(np.sqrt(np.mean(np.square(rms_values))))),
            "peak_dbfs": dbfs(float(np.max(np.abs(selected)))),
            "spectral_flatness_median": float(
                np.median(
                    np.exp(np.mean(np.log(np.maximum(powers, 1e-24)), axis=1))
                    / np.mean(np.maximum(powers, 1e-24), axis=1)
                )
            ),
        }
        total_time_power = np.square(rms_values)
        for name, (low, high) in BANDS_HZ.items():
            mask = (frequencies >= low) & (frequencies < high)
            fraction = np.sum(powers[:, mask], axis=1) / total_spectral_power
            band_rms = math.sqrt(float(np.mean(total_time_power * fraction)))
            metrics[f"{name}_rms_dbfs"] = dbfs(band_rms)
            metrics[f"{name}_power_fraction"] = float(np.mean(fraction))
        result[label] = metrics
    return result


def find_single(directory: Path, pattern: str) -> Path:
    matches = list(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"Esperado um arquivo {pattern} em {directory}, obtidos {matches}")
    return matches[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze_scenario(directory: Path) -> dict[str, object]:
    raw_path = find_single(directory, "*_input.wav")
    pre_path = find_single(directory, "*_output.wav")
    endpoint_path = find_single(directory, "endpoint.wav")
    metrics_path = find_single(directory, "*_metrics.json")
    raw = read_pcm16(raw_path)
    pre = read_pcm16(pre_path)
    endpoint = read_pcm16(endpoint_path)
    common = min(raw.size, pre.size)
    raw = raw[:common]
    pre = pre[:common]
    endpoint_aligned, lag_blocks, alignment_score = align_endpoint(pre, endpoint)
    labels = classify_blocks(block_view(raw))
    internal = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
    transport = internal.get("bridge", {}).copy()
    transport.pop("events", None)
    return {
        "name": directory.name,
        "method": internal["config"]["method"],
        "alignment": {
            "endpoint_lag_blocks": lag_blocks,
            "endpoint_lag_ms": lag_blocks * 20,
            "envelope_correlation": alignment_score,
            "interpretation": "comparison alignment only; not physical latency",
        },
        "edges_original": {
            "raw": edge_metrics(raw),
            "pre_bridge": edge_metrics(pre),
            "endpoint": edge_metrics(endpoint),
        },
        "edges_common_cut": {
            "raw": edge_metrics(raw),
            "pre_bridge": edge_metrics(pre),
            "endpoint": edge_metrics(endpoint_aligned),
        },
        "windows": {
            "raw": spectral_metrics(raw, labels),
            "pre_bridge": spectral_metrics(pre, labels),
            "endpoint": spectral_metrics(endpoint_aligned, labels),
        },
        "transport": transport,
        "files": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in (raw_path, pre_path, endpoint_path, metrics_path)
        ],
    }


def mean_delta(
    scenarios: list[dict[str, object]],
    method: str,
    window: str,
    metric: str,
    left: str,
    right: str,
) -> float:
    values = []
    for scenario in scenarios:
        if scenario["method"] != method:
            continue
        windows = scenario["windows"]
        values.append(
            float(windows[right][window][metric])
            - float(windows[left][window][metric])
        )
    return float(np.mean(values))


def build_conclusion(scenarios: list[dict[str, object]]) -> dict[str, object]:
    metric = "high_4_8k_rms_dbfs"
    pre_hiss = mean_delta(
        scenarios, "stft_subtraction", "noise", metric, "raw", "pre_bridge"
    )
    bridge_hiss = mean_delta(
        scenarios, "stft_subtraction", "noise", metric, "pre_bridge", "endpoint"
    )
    bypass_bridge_hiss = mean_delta(
        scenarios, "bypass", "noise", metric, "pre_bridge", "endpoint"
    )
    pre_noise = mean_delta(
        scenarios, "stft_subtraction", "noise", "rms_dbfs", "raw", "pre_bridge"
    )
    bridge_noise = mean_delta(
        scenarios, "stft_subtraction", "noise", "rms_dbfs", "pre_bridge", "endpoint"
    )

    if pre_hiss > 1.0 and bridge_hiss <= 1.0:
        hiss_boundary = "dsp_pre_bridge"
    elif bridge_hiss > max(1.0, bypass_bridge_hiss + 1.0):
        hiss_boundary = "bridge_or_endpoint"
    elif pre_hiss <= 1.0 and bridge_hiss <= 1.0:
        hiss_boundary = "no_absolute_high_band_increase_in_deterministic_matrix"
    else:
        hiss_boundary = "mixed_or_inconclusive"

    return {
        "hiss_boundary": hiss_boundary,
        "mean_deltas_db": {
            "stft_pre_bridge_high_4_8k_vs_raw": pre_hiss,
            "stft_endpoint_high_4_8k_vs_pre_bridge": bridge_hiss,
            "bypass_endpoint_high_4_8k_vs_pre_bridge": bypass_bridge_hiss,
            "stft_pre_bridge_total_noise_vs_raw": pre_noise,
            "stft_endpoint_total_noise_vs_pre_bridge": bridge_noise,
        },
        "limits": [
            "Deterministic source is not a substitute for perceptual validation.",
            "Envelope alignment is for comparison and is not physical latency.",
            "No DSP, driver, PCM protocol, queue depth, or estimator parameter was changed.",
        ],
    }


def write_csv(path: Path, scenarios: list[dict[str, object]]) -> None:
    fields = [
        "scenario",
        "method",
        "stage",
        "window",
        "block_count",
        "rms_dbfs",
        "high_4_8k_rms_dbfs",
        "high_4_8k_power_fraction",
        "spectral_flatness_median",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for scenario in scenarios:
            for stage, windows in scenario["windows"].items():
                for window, metrics in windows.items():
                    row = {
                        "scenario": scenario["name"],
                        "method": scenario["method"],
                        "stage": stage,
                        "window": window,
                    }
                    row.update({name: metrics.get(name) for name in fields if name in metrics})
                    writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    scenario_dirs = sorted(
        path
        for path in args.matrix_root.iterdir()
        if path.is_dir() and list(path.glob("*_input.wav"))
    )
    if not scenario_dirs:
        raise ValueError("Nenhum cenario da matriz foi encontrado.")
    scenarios = [analyze_scenario(path) for path in scenario_dirs]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "sample_rate_hz": SAMPLE_RATE,
        "block_ms": 20,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "conclusion": build_conclusion(scenarios),
    }
    (args.output_dir / "matrix_quality_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(args.output_dir / "matrix_quality_summary.csv", scenarios)
    print(args.output_dir / "matrix_quality_summary.json")


if __name__ == "__main__":
    main()
