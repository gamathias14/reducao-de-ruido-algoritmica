from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark_audio.denoise import DenoiseConfig, process_method
from scripts.audio.evaluate_checkpoint41_gain_smoothing import (
    BLOCK_SIZE,
    SAMPLE_RATE,
    active_mask,
    compare_signals,
    metrics,
    read_pcm16,
    sha256,
    write_pcm16,
)
from scripts.audio.evaluate_checkpoint42_wiener import process as process_stft


def process_wavelet(samples: np.ndarray, threshold_scale: float) -> np.ndarray:
    config = DenoiseConfig(
        sample_rate=SAMPLE_RATE,
        n_fft=512,
        hop_length=160,
        wavelet="db4",
        wavelet_level=3,
        wavelet_mode="soft",
        wavelet_threshold_strategy="global",
        wavelet_threshold_scale=threshold_scale,
    )
    history = np.zeros(512, dtype=np.float32)
    outputs = []
    for start in range(0, samples.size, BLOCK_SIZE):
        block = samples[start : start + BLOCK_SIZE]
        window = np.concatenate([history, block]).astype(np.float32)
        output_window, _ = process_method("wavelet_soft", window, config)
        output = output_window[-len(block) :].astype(np.float32)
        outputs.append(np.nan_to_num(output, nan=0.0, posinf=0.0, neginf=0.0))
        history = window[-512:].astype(np.float32)
    return np.concatenate(outputs).astype(np.float32)


def candidate_decision(
    baseline: dict[str, object],
    candidate: dict[str, object],
    threshold_scale: float,
) -> dict[str, object]:
    baseline_tonal = float(baseline["tonal_peak_density_per_block"])
    candidate_tonal = float(candidate["tonal_peak_density_per_block"])
    tonal_reduction = (baseline_tonal - candidate_tonal) / max(baseline_tonal, 1e-12)

    baseline_flatness = float(baseline["spectral_flatness_median"])
    candidate_flatness = float(candidate["spectral_flatness_median"])
    flatness_ratio = candidate_flatness / max(baseline_flatness, 1e-24)

    baseline_energy = float(baseline["active_energy_ratio_db"])
    candidate_energy = float(candidate["active_energy_ratio_db"])
    energy_change = candidate_energy - baseline_energy

    band_change = {
        name: float(candidate["band_delta_from_raw_db"][name])
        - float(baseline["band_delta_from_raw_db"][name])
        for name in baseline["band_delta_from_raw_db"]
    }
    extra_high_change = band_change["4000_8000"]
    max_band_relaxation = max(band_change.values())

    checks = {
        "tonal_reduction_at_least_10pct": tonal_reduction >= 0.10,
        "flatness_not_reduced_over_5pct": flatness_ratio >= 0.95,
        "extra_4_8k_loss_at_most_1db": extra_high_change >= -1.0,
        "extra_2_4k_loss_at_most_1db": band_change["2000_4000"] >= -1.0,
        "envelope_correlation_at_least_0_97": (
            float(candidate["envelope_correlation"]) >= 0.97
        ),
        "active_energy_loss_at_most_3db": candidate_energy >= -3.0,
        "snr_against_raw_at_least_12db": (
            float(candidate["snr_against_raw_db"]) >= 12.0
        ),
        "active_energy_not_relaxed_over_0_5db": energy_change <= 0.5,
        "no_band_relaxed_over_0_75db": max_band_relaxation <= 0.75,
    }
    return {
        "wavelet_threshold_scale": threshold_scale,
        "tonal_peak_reduction_fraction": tonal_reduction,
        "spectral_flatness_ratio_vs_baseline": flatness_ratio,
        "active_energy_change_vs_baseline_db": energy_change,
        "band_change_vs_baseline_db": band_change,
        "max_band_relaxation_vs_baseline_db": max_band_relaxation,
        "checks": checks,
        "objective_gate": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-full", type=Path, required=True)
    parser.add_argument("--baseline-reference", type=Path, required=True)
    parser.add_argument("--cut-start", type=int, required=True)
    parser.add_argument("--cut-stop", type=int, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument(
        "--threshold-scale",
        type=float,
        nargs="+",
        default=[0.10, 0.25, 0.50, 0.75],
    )
    args = parser.parse_args()

    scales = list(dict.fromkeys(args.threshold_scale))
    if not scales or any(value <= 0.0 or value >= 1.0 for value in scales):
        raise ValueError("Use escalas Wavelet no intervalo aberto (0, 1).")
    if not 0 <= args.cut_start < args.cut_stop:
        raise ValueError("Intervalo de corte invalido.")

    raw_full = read_pcm16(args.raw_full)
    baseline_reference = read_pcm16(args.baseline_reference)
    if args.cut_stop > raw_full.size:
        raise ValueError("O corte excede a tomada integral.")

    raw_cut = raw_full[args.cut_start : args.cut_stop]
    active = active_mask(raw_cut)
    baseline_full = process_stft(raw_full, "stft_subtraction")
    baseline_cut = baseline_full[args.cut_start : args.cut_stop]
    baseline_metrics = metrics(raw_cut, baseline_cut, active)

    wavelet_full = {
        scale: process_wavelet(raw_full, scale)
        for scale in scales
    }
    wavelet_cut = {
        scale: samples[args.cut_start : args.cut_stop]
        for scale, samples in wavelet_full.items()
    }
    variant_metrics = {
        str(scale): metrics(raw_cut, samples, active)
        for scale, samples in wavelet_cut.items()
    }
    decisions = [
        candidate_decision(baseline_metrics, variant_metrics[str(scale)], scale)
        for scale in scales
    ]
    eligible = [item for item in decisions if item["objective_gate"]]
    selected = (
        max(
            eligible,
            key=lambda item: (
                item["tonal_peak_reduction_fraction"],
                item["spectral_flatness_ratio_vs_baseline"],
            ),
        )
        if eligible
        else None
    )

    private_files = []
    args.private_output_dir.mkdir(parents=True, exist_ok=True)
    if selected is not None:
        selected_scale = float(selected["wavelet_threshold_scale"])
        outputs = {
            "A_subtraction_baseline_common_cut.wav": baseline_cut,
            "B_wavelet_threshold_common_cut.wav": wavelet_cut[selected_scale],
        }
        for name, samples in outputs.items():
            path = args.private_output_dir / name
            write_pcm16(path, samples)
            private_files.append(
                {"name": name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            )

    summary = {
        "privacy": "private_audio_outside_repository",
        "source_authorization": "checkpoint38_explicit_user_authorization",
        "new_voice_recording": False,
        "private_audio_location": str(args.private_output_dir),
        "sources": {
            "raw_full_sha256": sha256(args.raw_full),
            "baseline_reference_sha256": sha256(args.baseline_reference),
            "cut_start_sample": args.cut_start,
            "cut_stop_sample": args.cut_stop,
            "cut_duration_s": (args.cut_stop - args.cut_start) / SAMPLE_RATE,
        },
        "comparison": "frozen_spectral_subtraction_vs_causal_wavelet_threshold_scale",
        "frozen": {
            "sample_rate_hz": SAMPLE_RATE,
            "block_size": BLOCK_SIZE,
            "wavelet": "db4",
            "wavelet_level": 3,
            "wavelet_mode": "soft",
            "wavelet_threshold_strategy": "global",
            "causal_history_samples": 512,
            "wavelet_window_samples": 832,
        },
        "deployment": "offline_only_not_exposed_in_realtime_config",
        "varied_parameter": {
            "name": "wavelet_threshold_scale",
            "values": scales,
            "allowed_range": "(0, 1)",
        },
        "active_detection": {
            "scope": "raw_common_cut",
            "rule": "max(-48 dBFS, q20 block RMS + 6 dB)",
            "block_count": int(np.count_nonzero(active)),
        },
        "baseline": baseline_metrics,
        "wavelet_variants": variant_metrics,
        "candidate_decisions": decisions,
        "selected": selected,
        "baseline_reference_comparison": {
            "reference": "checkpoint40_B_pre_bridge_common_cut",
            "comparison": compare_signals(baseline_reference, baseline_cut),
        },
        "private_pair_prepared": selected is not None,
        "private_files": private_files,
        "end_to_end_run": False,
        "human_listening_requested": selected is not None,
    }
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(summary, indent=2, ensure_ascii=False)
    args.public_output.write_text(encoded, encoding="utf-8")
    (args.private_output_dir / "private_manifest.json").write_text(
        encoded,
        encoding="utf-8",
    )
    print(args.public_output)


if __name__ == "__main__":
    main()
