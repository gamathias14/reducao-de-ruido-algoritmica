from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .causal import CausalProcessorConfig, CausalSTFTProcessor
from .denoise import DenoiseConfig, process_method, si_sdr, snr_db
from .run_benchmark import ROOT
from .run_refinement import (
    FINAL_NOISE_GROUPS,
    FINAL_SPEAKERS,
    VALIDATION_NOISE_GROUPS,
    VALIDATION_SPEAKERS,
    Condition,
    build_conditions,
    files_for_split,
)


BLOCK_MS = 20.0
BLOCK_SAMPLES = 320


@dataclass(frozen=True)
class CausalCandidate:
    candidate_id: str
    config: CausalProcessorConfig


def process_causal(
    noisy: np.ndarray,
    config: CausalProcessorConfig,
    block_samples: int = BLOCK_SAMPLES,
) -> tuple[np.ndarray, dict[str, float | int]]:
    processor = CausalSTFTProcessor(config)
    outputs: list[np.ndarray] = []
    elapsed_ms: list[float] = []
    state_memory_bytes = 0
    speech_blocks = 0
    warming_blocks = 0
    for start in range(0, len(noisy), block_samples):
        block = noisy[start : start + block_samples]
        started = time.perf_counter()
        output, diagnostics = processor.process_block(block)
        elapsed_ms.append((time.perf_counter() - started) * 1_000.0)
        outputs.append(output)
        state_memory_bytes = max(state_memory_bytes, int(diagnostics["state_memory_bytes"]))
        speech_blocks += int(bool(diagnostics["speech_probable"]))
        warming_blocks += int(bool(diagnostics["warming_up"]))

    values = np.asarray(elapsed_ms, dtype=np.float64)
    output = np.concatenate(outputs).astype(np.float32)[: len(noisy)]
    return output, {
        "block_count": len(values),
        "block_mean_ms": float(np.mean(values)),
        "block_p95_ms": float(np.percentile(values, 95)),
        "block_p99_ms": float(np.percentile(values, 99)),
        "block_worst_ms": float(np.max(values)),
        "processing_ms": float(np.sum(values)),
        "rtf": float(np.sum(values) / 1_000.0 / (len(noisy) / config.sample_rate)),
        "state_memory_bytes": state_memory_bytes,
        "speech_block_fraction": speech_blocks / max(len(values), 1),
        "warming_blocks": warming_blocks,
    }


def candidate_grid() -> list[CausalCandidate]:
    candidates = [
        CausalCandidate(
            "causal_calibration_250ms",
            CausalProcessorConfig(
                method="stft_subtraction",
                noise_mode="calibration",
                calibration_ms=250.0,
            ),
        )
    ]
    for history_ms in (500.0, 1_000.0):
        for quantile in (0.10, 0.20, 0.22, 0.25, 0.35):
            for low_energy_alpha in (0.20, 0.30):
                candidate_id = (
                    f"causal_adaptive_h{history_ms:g}_q{quantile:g}"
                    f"_a{low_energy_alpha:g}_t6"
                )
                candidates.append(
                    CausalCandidate(
                        candidate_id,
                        CausalProcessorConfig(
                            method="stft_subtraction",
                            noise_mode="adaptive",
                            warmup_ms=250.0,
                            history_ms=history_ms,
                            noise_quantile=quantile,
                            energy_quantile=0.20,
                            speech_threshold_db=6.0,
                            low_energy_alpha=low_energy_alpha,
                            speech_alpha=0.005,
                        ),
                    )
                )
    return candidates


def evaluate_causal_candidate(
    candidate: CausalCandidate,
    conditions: list[Condition],
) -> dict[str, object]:
    snr_improvements: list[float] = []
    si_sdr_improvements: list[float] = []
    rtfs: list[float] = []
    block_p99: list[float] = []
    memory: list[int] = []
    for condition in conditions:
        processed, timing = process_causal(condition.noisy, candidate.config)
        snr_improvements.append(
            snr_db(condition.clean, processed) - condition.input_snr_db
        )
        si_sdr_improvements.append(
            si_sdr(condition.clean, processed) - condition.input_si_sdr_db
        )
        rtfs.append(float(timing["rtf"]))
        block_p99.append(float(timing["block_p99_ms"]))
        memory.append(int(timing["state_memory_bytes"]))

    snr_values = np.asarray(snr_improvements, dtype=np.float64)
    row: dict[str, object] = {
        "candidate_id": candidate.candidate_id,
        "estimator_type": candidate.config.noise_mode,
        "n_conditions": len(conditions),
        "snr_improvement_mean_db": float(np.mean(snr_values)),
        "snr_improvement_std_db": float(np.std(snr_values)),
        "snr_improvement_min_db": float(np.min(snr_values)),
        "snr_degradation_fraction": float(np.mean(snr_values < 0.0)),
        "si_sdr_improvement_mean_db": float(np.mean(si_sdr_improvements)),
        "rtf_mean": float(np.mean(rtfs)),
        "block_p99_mean_ms": float(np.mean(block_p99)),
        "state_memory_max_bytes": int(max(memory)),
    }
    row.update(asdict(candidate.config))
    return row


def select_adaptive(candidates: pd.DataFrame) -> pd.Series:
    adaptive = candidates[candidates["estimator_type"] == "adaptive"].copy()
    ranked = adaptive.sort_values(
        [
            "snr_degradation_fraction",
            "snr_improvement_mean_db",
            "si_sdr_improvement_mean_db",
            "rtf_mean",
        ],
        ascending=[True, False, False, True],
    )
    return ranked.iloc[0]


def selected_config(row: pd.Series, method: str) -> CausalProcessorConfig:
    fields = CausalProcessorConfig.__dataclass_fields__
    values = {name: row[name] for name in fields}
    values["sample_rate"] = int(values["sample_rate"])
    values["n_fft"] = int(values["n_fft"])
    values["hop_length"] = int(values["hop_length"])
    values["method"] = method
    if method == "stft_wiener":
        values["spectral_alpha"] = 1.2
        values["spectral_floor"] = 0.03
    return CausalProcessorConfig(**values)


def comparison_specs(selected: pd.Series) -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "bypass",
            "family": "baseline",
            "execution_mode": "causal_blocks",
            "causal_config": CausalProcessorConfig(method="bypass"),
        },
        {
            "candidate_id": "subtraction_initial_legacy",
            "family": "stft_subtraction",
            "execution_mode": "offline_file",
            "method": "stft_subtraction",
            "offline_config": DenoiseConfig(),
        },
        {
            "candidate_id": "subtraction_low_energy_offline",
            "family": "stft_subtraction",
            "execution_mode": "offline_file",
            "method": "stft_subtraction",
            "offline_config": DenoiseConfig(
                noise_estimator="low_energy",
                noise_quantile=0.35,
                spectral_alpha=1.5,
                spectral_floor=0.02,
            ),
        },
        {
            "candidate_id": "subtraction_calibration_causal",
            "family": "stft_subtraction",
            "execution_mode": "causal_blocks",
            "causal_config": CausalProcessorConfig(
                method="stft_subtraction",
                noise_mode="calibration",
                calibration_ms=250.0,
            ),
        },
        {
            "candidate_id": "subtraction_adaptive_causal",
            "family": "stft_subtraction",
            "execution_mode": "causal_blocks",
            "causal_config": selected_config(selected, "stft_subtraction"),
        },
        {
            "candidate_id": "wiener_initial_legacy",
            "family": "stft_wiener",
            "execution_mode": "offline_file",
            "method": "stft_wiener",
            "offline_config": DenoiseConfig(),
        },
        {
            "candidate_id": "wiener_low_energy_offline",
            "family": "stft_wiener",
            "execution_mode": "offline_file",
            "method": "stft_wiener",
            "offline_config": DenoiseConfig(
                noise_estimator="low_energy",
                noise_quantile=0.35,
                wiener_floor=0.05,
            ),
        },
        {
            "candidate_id": "wiener_adaptive_causal",
            "family": "stft_wiener",
            "execution_mode": "causal_blocks",
            "causal_config": selected_config(selected, "stft_wiener"),
        },
    ]


def evaluate_comparison(
    specs: list[dict[str, object]],
    conditions: list[Condition],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for condition in conditions:
        for spec in specs:
            if spec["execution_mode"] == "causal_blocks":
                processed, timing = process_causal(
                    condition.noisy,
                    spec["causal_config"],
                )
            else:
                processed, elapsed = process_method(
                    spec["method"],
                    condition.noisy,
                    spec["offline_config"],
                )
                elapsed_ms = elapsed * 1_000.0
                timing = {
                    "block_count": 1,
                    "block_mean_ms": elapsed_ms,
                    "block_p95_ms": elapsed_ms,
                    "block_p99_ms": elapsed_ms,
                    "block_worst_ms": elapsed_ms,
                    "processing_ms": elapsed_ms,
                    "rtf": elapsed / (len(condition.noisy) / 16_000),
                    "state_memory_bytes": 0,
                    "speech_block_fraction": 0.0,
                    "warming_blocks": 0,
                }
            output_snr = snr_db(condition.clean, processed)
            output_si_sdr = si_sdr(condition.clean, processed)
            rows.append(
                {
                    "split": condition.split,
                    "speaker": condition.speaker,
                    "noise": condition.noise_name,
                    "noise_group": condition.noise_group,
                    "snr_target_db": condition.snr_target_db,
                    "candidate_id": spec["candidate_id"],
                    "family": spec["family"],
                    "execution_mode": spec["execution_mode"],
                    "input_snr_db": condition.input_snr_db,
                    "output_snr_db": output_snr,
                    "snr_improvement_db": output_snr - condition.input_snr_db,
                    "input_si_sdr_db": condition.input_si_sdr_db,
                    "output_si_sdr_db": output_si_sdr,
                    "si_sdr_improvement_db": output_si_sdr - condition.input_si_sdr_db,
                    **timing,
                }
            )
    return pd.DataFrame(rows)


def summarize_comparison(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.groupby(
            ["split", "candidate_id", "family", "execution_mode"],
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
            rtf_mean=("rtf", "mean"),
            block_mean_ms=("block_mean_ms", "mean"),
            block_p95_ms=("block_p95_ms", "mean"),
            block_p99_ms=("block_p99_ms", "mean"),
            block_worst_ms=("block_worst_ms", "max"),
            state_memory_max_bytes=("state_memory_bytes", "max"),
        )
        .sort_values(["split", "family", "candidate_id"])
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

    started = time.perf_counter()
    candidates = pd.DataFrame(
        [
            evaluate_causal_candidate(candidate, validation_conditions)
            for candidate in candidate_grid()
        ]
    )
    candidates.to_csv(
        tables_dir / "validation_candidates.csv",
        index=False,
        encoding="utf-8",
    )
    selected = select_adaptive(candidates)
    (tables_dir / "selected_config.json").write_text(
        json.dumps(selected.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    specs = comparison_specs(selected)
    comparison = evaluate_comparison(
        specs,
        validation_conditions + final_conditions,
    )
    summary = summarize_comparison(comparison)
    comparison.to_csv(
        tables_dir / "comparison_metrics.csv",
        index=False,
        encoding="utf-8",
    )
    summary.to_csv(
        tables_dir / "comparison_overall.csv",
        index=False,
        encoding="utf-8",
    )
    metadata = {
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "block_ms": BLOCK_MS,
        "block_samples": BLOCK_SAMPLES,
        "candidate_count": len(candidates),
        "selection_split": "validation only",
        "selection_rule": (
            "Among adaptive candidates: minimize SNR degradation fraction, then maximize "
            "mean SNR improvement, mean SI-SDR improvement, and finally minimize RTF."
        ),
        "validation_speakers": list(VALIDATION_SPEAKERS),
        "validation_noise_groups": list(VALIDATION_NOISE_GROUPS),
        "final_operational_speakers": list(FINAL_SPEAKERS),
        "final_operational_noise_groups": list(FINAL_NOISE_GROUPS),
        "future_data_policy": (
            "No authored Session B or historically blind future recording was used. "
            "The existing final operational split was evaluated only after selection."
        ),
        "causality": (
            "Each output block uses estimator state from prior blocks; spectra from the "
            "current block update state only for subsequent blocks."
        ),
        "elapsed_s": time.perf_counter() - started,
    }
    (tables_dir / "metadata_causal.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seleciona e compara o estimador causal de ruido no conjunto de desenvolvimento."
    )
    parser.add_argument(
        "--results-dir",
        default="resultados/causal_estimator",
        help="Diretorio isolado para tabelas da etapa PC-1.",
    )
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
