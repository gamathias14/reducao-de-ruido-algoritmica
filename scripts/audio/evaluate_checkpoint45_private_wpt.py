from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark_audio.causal_wpt import CausalWPTConfig, CausalWPTProcessor
from scripts.audio.evaluate_checkpoint41_gain_smoothing import (
    BLOCK_SIZE,
    SAMPLE_RATE,
    active_mask,
    compare_signals,
    metrics,
    read_pcm16,
    sha256,
)
from scripts.audio.evaluate_checkpoint42_wiener import process as process_stft


def process_wpt(samples: np.ndarray) -> np.ndarray:
    processor = CausalWPTProcessor(CausalWPTConfig())
    outputs = []
    for start in range(0, samples.size, BLOCK_SIZE):
        outputs.append(processor.process_block(samples[start : start + BLOCK_SIZE])[0])
    return np.concatenate(outputs).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-full", type=Path, required=True)
    parser.add_argument("--baseline-reference", type=Path, required=True)
    parser.add_argument("--cut-start", type=int, required=True)
    parser.add_argument("--cut-stop", type=int, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    args = parser.parse_args()

    raw_full = read_pcm16(args.raw_full)
    baseline_reference = read_pcm16(args.baseline_reference)
    raw_cut = raw_full[args.cut_start : args.cut_stop]
    active = active_mask(raw_cut)
    baseline_full = process_stft(raw_full, "stft_subtraction")
    wpt_full = process_wpt(raw_full)
    baseline_cut = baseline_full[args.cut_start : args.cut_stop]
    wpt_cut = wpt_full[args.cut_start : args.cut_stop]
    baseline_metrics = metrics(raw_cut, baseline_cut, active)
    wpt_metrics = metrics(raw_cut, wpt_cut, active)

    baseline_tonal = float(baseline_metrics["tonal_peak_density_per_block"])
    wpt_tonal = float(wpt_metrics["tonal_peak_density_per_block"])
    tonal_reduction = (baseline_tonal - wpt_tonal) / baseline_tonal
    band_change = {
        name: float(wpt_metrics["band_delta_from_raw_db"][name])
        - float(baseline_metrics["band_delta_from_raw_db"][name])
        for name in baseline_metrics["band_delta_from_raw_db"]
    }
    checks = {
        "tonal_reduction_at_least_10pct": tonal_reduction >= 0.10,
        "extra_4_8k_loss_at_most_1db": band_change["4000_8000"] >= -1.0,
        "extra_2_4k_loss_at_most_1db": band_change["2000_4000"] >= -1.0,
        "envelope_correlation_at_least_0_97": (
            float(wpt_metrics["envelope_correlation"]) >= 0.97
        ),
        "active_energy_loss_at_most_3db": (
            float(wpt_metrics["active_energy_ratio_db"]) >= -3.0
        ),
        "snr_against_raw_at_least_12db": (
            float(wpt_metrics["snr_against_raw_db"]) >= 12.0
        ),
        "no_band_relaxed_over_0_75db": max(band_change.values()) <= 0.75,
    }
    eligible = all(checks.values())
    config = CausalWPTConfig()
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
        "configuration_frozen_before_private_evaluation": {
            "frame_length": config.frame_length,
            "block_size": config.block_size,
            "wavelet": config.wavelet,
            "level": config.level,
            "warmup_blocks": config.warmup_blocks,
            "history_blocks": config.history_blocks,
            "noise_quantile": config.noise_quantile,
            "gain_floor": config.gain_floor,
        },
        "baseline": baseline_metrics,
        "causal_wpt": wpt_metrics,
        "comparison": {
            "tonal_peak_reduction_fraction": tonal_reduction,
            "spectral_flatness_ratio_vs_baseline": (
                float(wpt_metrics["spectral_flatness_median"])
                / float(baseline_metrics["spectral_flatness_median"])
            ),
            "band_change_vs_baseline_db": band_change,
            "checks": checks,
            "eligible_for_perceptual_pair": eligible,
        },
        "baseline_reference_comparison": compare_signals(
            baseline_reference,
            baseline_cut,
        ),
        "private_pair_prepared": False,
        "private_files": [],
        "human_listening_requested": False,
        "end_to_end_run": False,
    }
    args.private_output_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(summary, indent=2, ensure_ascii=False)
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.write_text(encoded, encoding="utf-8")
    (args.private_output_dir / "private_manifest.json").write_text(
        encoded,
        encoding="utf-8",
    )
    print(args.public_output)


if __name__ == "__main__":
    main()
