from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .causal import CausalProcessorConfig
from .denoise import DenoiseConfig, si_sdr, snr_db
from .run_benchmark import ROOT
from .run_causal_estimator import BLOCK_SAMPLES, process_causal
from .run_refinement import (
    FINAL_NOISE_GROUPS,
    FINAL_SPEAKERS,
    VALIDATION_NOISE_GROUPS,
    VALIDATION_SPEAKERS,
    Condition,
    build_conditions,
    files_for_split,
    write_split_manifest,
)


BANDS_HZ = (
    ("2000_4000", 2_000.0, 4_000.0),
    ("4000_8000", 4_000.0, 8_001.0),
)
BASELINE_ID = "E0-S02"


@dataclass(frozen=True)
class SixArmCandidate:
    candidate_id: str
    estimator_id: str
    gain_profile_id: str
    config: CausalProcessorConfig


def candidate_grid() -> list[SixArmCandidate]:
    estimators = {
        "E0": {"noise_quantile": 0.22, "low_energy_alpha": 0.30},
        "E1": {"noise_quantile": 0.35, "low_energy_alpha": 0.40},
    }
    profiles = {
        "S02": {
            "method": "stft_subtraction",
            "spectral_alpha": 1.5,
            "spectral_floor": 0.02,
            "wiener_floor": 0.05,
        },
        "S05": {
            "method": "stft_subtraction",
            "spectral_alpha": 1.5,
            "spectral_floor": 0.05,
            "wiener_floor": 0.05,
        },
        "W05": {
            "method": "stft_wiener",
            "spectral_alpha": 1.5,
            "spectral_floor": 0.02,
            "wiener_floor": 0.05,
        },
    }
    candidates = []
    for estimator_id, estimator in estimators.items():
        for profile_id, profile in profiles.items():
            candidates.append(
                SixArmCandidate(
                    candidate_id=f"{estimator_id}-{profile_id}",
                    estimator_id=estimator_id,
                    gain_profile_id=profile_id,
                    config=CausalProcessorConfig(
                        method=str(profile["method"]),
                        n_fft=512,
                        hop_length=160,
                        spectral_alpha=float(profile["spectral_alpha"]),
                        spectral_floor=float(profile["spectral_floor"]),
                        wiener_floor=float(profile["wiener_floor"]),
                        noise_mode="adaptive",
                        warmup_ms=250.0,
                        history_ms=500.0,
                        noise_quantile=float(estimator["noise_quantile"]),
                        energy_quantile=0.20,
                        speech_threshold_db=6.0,
                        low_energy_alpha=float(estimator["low_energy_alpha"]),
                        speech_alpha=0.005,
                        gain_smoothing=0.0,
                    ),
                )
            )
    return candidates


def _active_blocks(clean: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    count = clean.size // BLOCK_SAMPLES
    blocks = clean[: count * BLOCK_SAMPLES].reshape(count, BLOCK_SAMPLES)
    levels = np.sqrt(np.mean(np.square(blocks, dtype=np.float64), axis=1))
    threshold = max(10.0 ** (-48.0 / 20.0), float(np.quantile(levels, 0.20)))
    active = levels > threshold
    if not np.any(active):
        active = np.ones(count, dtype=bool)
    return blocks, active


def perceptual_metrics(
    clean: np.ndarray,
    noisy: np.ndarray,
    output: np.ndarray,
    sample_rate: int = 16_000,
) -> dict[str, float]:
    clean_blocks, active = _active_blocks(clean)
    count = min(clean.size, noisy.size, output.size) // BLOCK_SAMPLES
    clean_blocks = clean_blocks[:count][active[:count]]
    noisy_blocks = noisy[: count * BLOCK_SAMPLES].reshape(
        count,
        BLOCK_SAMPLES,
    )[active[:count]]
    output_blocks = output[: count * BLOCK_SAMPLES].reshape(
        count,
        BLOCK_SAMPLES,
    )[active[:count]]
    window = np.hanning(BLOCK_SAMPLES)
    clean_spectrum = np.fft.rfft(clean_blocks.astype(np.float64) * window, axis=1)
    noisy_spectrum = np.fft.rfft(noisy_blocks.astype(np.float64) * window, axis=1)
    output_spectrum = np.fft.rfft(output_blocks.astype(np.float64) * window, axis=1)
    clean_power = np.maximum(np.square(np.abs(clean_spectrum)), 1e-24)
    noisy_power = np.maximum(np.square(np.abs(noisy_spectrum)), 1e-24)
    output_power = np.maximum(np.square(np.abs(output_spectrum)), 1e-24)

    median_power = np.median(output_power, axis=1, keepdims=True)
    tonal = output_power[:, 1:-1] > 10.0 * median_power
    tonal &= output_power[:, 1:-1] > output_power[:, :-2]
    tonal &= output_power[:, 1:-1] > output_power[:, 2:]
    flatness = np.exp(np.mean(np.log(output_power), axis=1)) / np.mean(
        output_power,
        axis=1,
    )

    frequencies = np.fft.rfftfreq(BLOCK_SAMPLES, 1.0 / sample_rate)
    speech_band = (frequencies >= 300.0) & (frequencies < 8_001.0)
    log_ratio_db = 10.0 * np.log10(
        output_power[:, speech_band] / clean_power[:, speech_band]
    )
    log_spectral_distance = np.sqrt(np.mean(np.square(log_ratio_db), axis=1))

    input_envelope = np.sqrt(
        np.mean(np.square(noisy_blocks, dtype=np.float64), axis=1)
    )
    output_envelope = np.sqrt(
        np.mean(np.square(output_blocks, dtype=np.float64), axis=1)
    )
    if np.std(input_envelope) <= 1e-12 or np.std(output_envelope) <= 1e-12:
        envelope_correlation = 1.0 if np.allclose(
            input_envelope,
            output_envelope,
        ) else 0.0
    else:
        envelope_correlation = float(
            np.corrcoef(input_envelope, output_envelope)[0, 1]
        )

    result = {
        "active_block_count": float(len(clean_blocks)),
        "tonal_peak_density_per_active_block": float(
            np.mean(np.sum(tonal, axis=1))
        ),
        "spectral_flatness_median": float(np.median(flatness)),
        "log_spectral_distance_mean_db": float(
            np.mean(log_spectral_distance)
        ),
        "envelope_correlation": envelope_correlation,
    }
    for name, low, high in BANDS_HZ:
        selected = (frequencies >= low) & (frequencies < high)
        output_energy = float(np.mean(output_power[:, selected]))
        input_energy = float(np.mean(noisy_power[:, selected]))
        result[f"band_delta_input_{name}_db"] = 10.0 * math.log10(
            max(output_energy, 1e-24) / max(input_energy, 1e-24)
        )
    return result


def evaluate_candidate(
    candidate: SixArmCandidate,
    conditions: list[Condition],
) -> pd.DataFrame:
    rows = []
    for condition in conditions:
        output, timing = process_causal(condition.noisy, candidate.config)
        output_snr = snr_db(condition.clean, output)
        output_si_sdr = si_sdr(condition.clean, output)
        rows.append(
            {
                "split": condition.split,
                "speaker": condition.speaker,
                "noise": condition.noise_name,
                "noise_group": condition.noise_group,
                "snr_target_db": condition.snr_target_db,
                "candidate_id": candidate.candidate_id,
                "estimator_id": candidate.estimator_id,
                "gain_profile_id": candidate.gain_profile_id,
                "input_snr_db": condition.input_snr_db,
                "output_snr_db": output_snr,
                "snr_improvement_db": output_snr - condition.input_snr_db,
                "input_si_sdr_db": condition.input_si_sdr_db,
                "output_si_sdr_db": output_si_sdr,
                "si_sdr_improvement_db": (
                    output_si_sdr - condition.input_si_sdr_db
                ),
                **perceptual_metrics(condition.clean, condition.noisy, output),
                **timing,
            }
        )
    return pd.DataFrame(rows)


def summarize(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.groupby(
            ["split", "candidate_id", "estimator_id", "gain_profile_id"],
            as_index=False,
        )
        .agg(
            n_conditions=("snr_improvement_db", "size"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            snr_improvement_std_db=("snr_improvement_db", "std"),
            snr_improvement_min_db=("snr_improvement_db", "min"),
            snr_degradation_fraction=(
                "snr_improvement_db",
                lambda values: float(np.mean(values < 0.0)),
            ),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            tonal_peak_density_mean=(
                "tonal_peak_density_per_active_block",
                "mean",
            ),
            spectral_flatness_median=("spectral_flatness_median", "median"),
            log_spectral_distance_mean_db=(
                "log_spectral_distance_mean_db",
                "mean",
            ),
            envelope_correlation_mean=("envelope_correlation", "mean"),
            band_delta_input_2000_4000_mean_db=(
                "band_delta_input_2000_4000_db",
                "mean",
            ),
            band_delta_input_4000_8000_mean_db=(
                "band_delta_input_4000_8000_db",
                "mean",
            ),
            block_p99_max_ms=("block_p99_ms", "max"),
            block_worst_max_ms=("block_worst_ms", "max"),
            rtf_mean=("rtf", "mean"),
            state_memory_max_bytes=("state_memory_bytes", "max"),
        )
        .sort_values(["split", "candidate_id"])
        .reset_index(drop=True)
    )


def apply_validation_gates(summary: pd.DataFrame) -> pd.DataFrame:
    validation = summary[summary["split"] == "validation"].copy()
    baseline_rows = validation[validation["candidate_id"] == BASELINE_ID]
    if len(baseline_rows) != 1:
        raise ValueError("Baseline de validacao ausente ou duplicado.")
    baseline = baseline_rows.iloc[0]

    decisions = []
    for _, row in validation.iterrows():
        tonal_change = (
            float(row["tonal_peak_density_mean"])
            / max(float(baseline["tonal_peak_density_mean"]), 1e-12)
            - 1.0
        )
        checks = {
            "degradation_fraction_not_worse": (
                float(row["snr_degradation_fraction"])
                <= float(baseline["snr_degradation_fraction"]) + 1e-12
            ),
            "si_sdr_loss_at_most_0_25db": (
                float(row["si_sdr_improvement_mean_db"])
                >= float(baseline["si_sdr_improvement_mean_db"]) - 0.25
            ),
            "band_2_4k_loss_at_most_0_75db": (
                float(row["band_delta_input_2000_4000_mean_db"])
                >= float(baseline["band_delta_input_2000_4000_mean_db"]) - 0.75
            ),
            "band_4_8k_loss_at_most_0_75db": (
                float(row["band_delta_input_4000_8000_mean_db"])
                >= float(baseline["band_delta_input_4000_8000_mean_db"]) - 0.75
            ),
            "envelope_absolute_gate_when_baseline_reaches_0_975": (
                float(baseline["envelope_correlation_mean"]) < 0.975
                or float(row["envelope_correlation_mean"]) >= 0.975
            ),
            "envelope_loss_at_most_0_005": (
                float(row["envelope_correlation_mean"])
                >= float(baseline["envelope_correlation_mean"]) - 0.005
            ),
            "tonal_density_increase_at_most_2pct": tonal_change <= 0.02,
            "block_worst_below_20ms": (
                float(row["block_worst_max_ms"]) < 20.0
            ),
        }
        improvement_evidence = {
            "snr_gain_at_least_0_05db": (
                float(row["snr_improvement_mean_db"])
                >= float(baseline["snr_improvement_mean_db"]) + 0.05
            ),
            "tonal_reduction_at_least_2pct": tonal_change <= -0.02,
            "log_spectral_distance_gain_at_least_0_05db": (
                float(row["log_spectral_distance_mean_db"])
                <= float(baseline["log_spectral_distance_mean_db"]) - 0.05
            ),
        }
        eligible = all(checks.values()) and any(improvement_evidence.values())
        if row["candidate_id"] == BASELINE_ID:
            eligible = True
        decisions.append(
            {
                "candidate_id": row["candidate_id"],
                "is_baseline": row["candidate_id"] == BASELINE_ID,
                "eligible": eligible,
                "tonal_density_change_fraction_vs_baseline": tonal_change,
                "checks": checks,
                "improvement_evidence": improvement_evidence,
            }
        )
    return pd.DataFrame(decisions)


def pareto_candidate_ids(
    summary: pd.DataFrame,
    decisions: pd.DataFrame,
    limit: int = 3,
) -> list[str]:
    eligible_ids = set(
        decisions.loc[
            decisions["eligible"] & ~decisions["is_baseline"],
            "candidate_id",
        ]
    )
    rows = summary[
        (summary["split"] == "validation")
        & summary["candidate_id"].isin(eligible_ids)
    ].copy()
    if rows.empty:
        return []
    objectives = np.column_stack(
        [
            rows["snr_improvement_mean_db"].to_numpy(float),
            rows["si_sdr_improvement_mean_db"].to_numpy(float),
            -rows["tonal_peak_density_mean"].to_numpy(float),
            -rows["log_spectral_distance_mean_db"].to_numpy(float),
        ]
    )
    dominated = np.zeros(len(rows), dtype=bool)
    for index in range(len(rows)):
        for other in range(len(rows)):
            if index == other:
                continue
            if np.all(objectives[other] >= objectives[index]) and np.any(
                objectives[other] > objectives[index]
            ):
                dominated[index] = True
                break
    frontier = rows.loc[~dominated].copy()
    if len(frontier) <= limit:
        return list(frontier.sort_values("candidate_id")["candidate_id"])

    selected: list[str] = []
    selectors = (
        ("snr_improvement_mean_db", False),
        ("si_sdr_improvement_mean_db", False),
        ("tonal_peak_density_mean", True),
        ("log_spectral_distance_mean_db", True),
    )
    for column, ascending in selectors:
        ranked = frontier.sort_values(
            [column, "candidate_id"],
            ascending=[ascending, True],
        )
        candidate_id = str(ranked.iloc[0]["candidate_id"])
        if candidate_id not in selected:
            selected.append(candidate_id)
        if len(selected) == limit:
            break
    return selected


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> None:
    results_root = Path(args.results_dir)
    if not results_root.is_absolute():
        results_root = ROOT / results_root
    tables_dir = results_root / "tabelas"
    tables_dir.mkdir(parents=True, exist_ok=True)

    clean_dir = ROOT / "dados" / "demo" / "clean_refinement"
    noise_dir = ROOT / "dados" / "demo" / "noise_demand"
    validation_clean, validation_noise = files_for_split(
        clean_dir,
        noise_dir,
        VALIDATION_SPEAKERS,
        VALIDATION_NOISE_GROUPS,
    )
    final_clean, final_noise = files_for_split(
        clean_dir,
        noise_dir,
        FINAL_SPEAKERS,
        FINAL_NOISE_GROUPS,
    )
    write_split_manifest(
        tables_dir / "split_manifest.csv",
        validation_clean,
        validation_noise,
        final_clean,
        final_noise,
    )
    validation_conditions = build_conditions(
        split="validation",
        clean_files=validation_clean,
        noise_files=validation_noise,
        config=DenoiseConfig(),
    )
    final_conditions = build_conditions(
        split="final_operational",
        clean_files=final_clean,
        noise_files=final_noise,
        config=DenoiseConfig(),
    )

    candidates = candidate_grid()
    started = time.perf_counter()
    validation_metrics = pd.concat(
        [
            evaluate_candidate(candidate, validation_conditions)
            for candidate in candidates
        ],
        ignore_index=True,
    )
    validation_summary = summarize(validation_metrics)
    decisions = apply_validation_gates(validation_summary)
    selected_ids = pareto_candidate_ids(
        validation_summary,
        decisions,
        limit=args.max_selected,
    )
    selected_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_id in {BASELINE_ID, *selected_ids}
    ]
    final_metrics = pd.concat(
        [
            evaluate_candidate(candidate, final_conditions)
            for candidate in selected_candidates
        ],
        ignore_index=True,
    )
    all_metrics = pd.concat(
        [validation_metrics, final_metrics],
        ignore_index=True,
    )
    overall = summarize(all_metrics)

    all_metrics.to_csv(
        tables_dir / "condition_metrics.csv",
        index=False,
        encoding="utf-8",
    )
    overall.to_csv(
        tables_dir / "candidate_summary.csv",
        index=False,
        encoding="utf-8",
    )
    decisions.to_csv(
        tables_dir / "validation_gates.csv",
        index=False,
        encoding="utf-8",
    )
    _write_json(
        tables_dir / "validation_gates.json",
        decisions.to_dict(orient="records"),
    )
    _write_json(
        tables_dir / "selected_candidates.json",
        [
            {
                "candidate_id": candidate.candidate_id,
                "estimator_id": candidate.estimator_id,
                "gain_profile_id": candidate.gain_profile_id,
                "config": asdict(candidate.config),
            }
            for candidate in selected_candidates
        ],
    )
    metadata = {
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "protocol": "checkpoint46r_six_arm_causal_stft",
        "candidate_count_validation": len(candidates),
        "selected_challenger_ids": selected_ids,
        "final_candidate_ids": [
            candidate.candidate_id for candidate in selected_candidates
        ],
        "validation_conditions": len(validation_conditions),
        "final_operational_conditions": len(final_conditions),
        "selection_split": "validation_only",
        "final_policy": (
            "Only the frozen baseline and Pareto-selected challengers are "
            "evaluated on the final operational split."
        ),
        "private_audio_used": False,
        "audio_outputs_written": False,
        "wpt_in_scope": False,
        "elapsed_s": time.perf_counter() - started,
    }
    _write_json(tables_dir / "metadata_checkpoint46r.json", metadata)
    decision = {
        "status": (
            "public_candidates_selected"
            if selected_ids
            else "stop_no_public_candidate"
        ),
        "baseline_id": BASELINE_ID,
        "selected_challenger_ids": selected_ids,
        "proceed_to_vm": bool(selected_ids),
        "proceed_to_private_audio": False,
        "reason": (
            "Candidates passed validation gates and Pareto selection."
            if selected_ids
            else "No challenger passed the public validation gates."
        ),
    }
    _write_json(results_root / "public_decision.json", decision)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Avalia os seis bracos causais STFT do Checkpoint 46-R."
    )
    parser.add_argument(
        "--results-dir",
        default="resultados/sysvad_checkpoint46_reopened/public_six_arm",
    )
    parser.add_argument("--max-selected", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
