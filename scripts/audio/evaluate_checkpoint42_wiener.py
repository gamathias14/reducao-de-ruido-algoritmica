from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark_audio.causal import CausalProcessorConfig, CausalSTFTProcessor
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


def process(samples: np.ndarray, method: str, wiener_floor: float = 0.05) -> np.ndarray:
    processor = CausalSTFTProcessor(
        CausalProcessorConfig(
            sample_rate=SAMPLE_RATE,
            method=method,
            n_fft=512,
            hop_length=160,
            spectral_alpha=1.5,
            spectral_floor=0.02,
            gain_smoothing=0.0,
            wiener_floor=wiener_floor,
            noise_mode="adaptive",
        )
    )
    outputs = []
    for start in range(0, samples.size, BLOCK_SIZE):
        outputs.append(processor.process_block(samples[start : start + BLOCK_SIZE])[0])
    return np.concatenate(outputs).astype(np.float32)


def candidate_decision(
    baseline: dict[str, object],
    candidate: dict[str, object],
    wiener_floor: float,
) -> dict[str, object]:
    baseline_tonal = float(baseline["tonal_peak_density_per_block"])
    candidate_tonal = float(candidate["tonal_peak_density_per_block"])
    tonal_reduction = (baseline_tonal - candidate_tonal) / max(baseline_tonal, 1e-12)

    baseline_flatness = float(baseline["spectral_flatness_median"])
    candidate_flatness = float(candidate["spectral_flatness_median"])
    flatness_ratio = candidate_flatness / max(baseline_flatness, 1e-24)

    baseline_high = float(baseline["band_delta_from_raw_db"]["4000_8000"])
    candidate_high = float(candidate["band_delta_from_raw_db"]["4000_8000"])
    extra_high_change = candidate_high - baseline_high

    baseline_energy = float(baseline["active_energy_ratio_db"])
    candidate_energy = float(candidate["active_energy_ratio_db"])
    energy_change = candidate_energy - baseline_energy

    band_relaxation = {
        name: float(candidate["band_delta_from_raw_db"][name])
        - float(baseline["band_delta_from_raw_db"][name])
        for name in baseline["band_delta_from_raw_db"]
    }
    max_band_relaxation = max(band_relaxation.values())

    checks = {
        "tonal_reduction_at_least_10pct": tonal_reduction >= 0.10,
        "flatness_improves_at_least_5pct": flatness_ratio >= 1.05,
        "extra_4_8k_loss_at_most_1db": extra_high_change >= -1.0,
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
        "wiener_floor": wiener_floor,
        "tonal_peak_reduction_fraction": tonal_reduction,
        "spectral_flatness_ratio_vs_baseline": flatness_ratio,
        "extra_4_8k_change_vs_baseline_db": extra_high_change,
        "active_energy_change_vs_baseline_db": energy_change,
        "band_relaxation_vs_baseline_db": band_relaxation,
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
        "--wiener-floor",
        type=float,
        nargs="+",
        default=[0.02, 0.05, 0.08, 0.10],
    )
    args = parser.parse_args()

    floors = list(dict.fromkeys(args.wiener_floor))
    if not floors or any(value <= 0.0 or value > 0.15 for value in floors):
        raise ValueError("Use pisos Wiener conservadores no intervalo (0, 0.15].")
    if not 0 <= args.cut_start < args.cut_stop:
        raise ValueError("Intervalo de corte invalido.")

    raw_full = read_pcm16(args.raw_full)
    baseline_reference = read_pcm16(args.baseline_reference)
    if args.cut_stop > raw_full.size:
        raise ValueError("O corte excede a tomada integral.")

    raw_cut = raw_full[args.cut_start : args.cut_stop]
    active = active_mask(raw_cut)
    baseline_full = process(raw_full, "stft_subtraction")
    baseline_cut = baseline_full[args.cut_start : args.cut_stop]
    baseline_metrics = metrics(raw_cut, baseline_cut, active)

    wiener_full = {
        floor: process(raw_full, "stft_wiener", floor)
        for floor in floors
    }
    wiener_cut = {
        floor: samples[args.cut_start : args.cut_stop]
        for floor, samples in wiener_full.items()
    }
    variant_metrics = {
        str(floor): metrics(raw_cut, samples, active)
        for floor, samples in wiener_cut.items()
    }
    decisions = [
        candidate_decision(baseline_metrics, variant_metrics[str(floor)], floor)
        for floor in floors
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
        selected_floor = float(selected["wiener_floor"])
        outputs = {
            "A_subtraction_baseline_common_cut.wav": baseline_cut,
            "B_wiener_common_cut.wav": wiener_cut[selected_floor],
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
        "comparison": "frozen_spectral_subtraction_vs_existing_causal_wiener",
        "frozen": {
            "sample_rate_hz": SAMPLE_RATE,
            "block_size": BLOCK_SIZE,
            "n_fft": 512,
            "hop_length": 160,
            "spectral_alpha": 1.5,
            "spectral_floor": 0.02,
            "gain_smoothing": 0.0,
            "noise_estimator": "adaptive",
        },
        "varied_parameter": {
            "name": "wiener_floor",
            "values": floors,
            "allowed_range": "(0, 0.15]",
        },
        "active_detection": {
            "scope": "raw_common_cut",
            "rule": "max(-48 dBFS, q20 block RMS + 6 dB)",
            "block_count": int(np.count_nonzero(active)),
        },
        "baseline": baseline_metrics,
        "wiener_variants": variant_metrics,
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
