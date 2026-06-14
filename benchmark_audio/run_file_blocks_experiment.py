from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from realtime_audio.block_metrics import summarize_block_timings
from realtime_audio.process_wav_blocks import process_samples_in_blocks, sha256_file

from .causal import CausalProcessorConfig
from .denoise import DenoiseConfig, process_method, si_sdr, snr_db
from .run_benchmark import ROOT
from .run_refinement import build_conditions


SNRS_DB = (-5, 5)
BLOCKS_MS = (10.0, 20.0, 32.0)
CAUSAL_METHODS = ("bypass", "stft_subtraction", "stft_wiener")


def _causal_row(condition: object, method: str, block_ms: float) -> dict[str, object]:
    config = CausalProcessorConfig(method=method, noise_mode="adaptive")
    output, blocks = process_samples_in_blocks(condition.noisy, config, block_ms)
    timing = summarize_block_timings(blocks)
    processing_total_ms = float(sum(float(row["processing_ms"]) for row in blocks))
    duration_s = len(output) / config.sample_rate
    output_snr = snr_db(condition.clean, output)
    output_si_sdr = si_sdr(condition.clean, output)
    return {
        "speaker": condition.speaker,
        "noise": condition.noise_name,
        "noise_group": condition.noise_group,
        "snr_target_db": condition.snr_target_db,
        "candidate_id": f"{method}_causal_{block_ms:g}ms",
        "family": method,
        "execution_mode": "causal_blocks",
        "noise_mode": "adaptive",
        "block_ms": block_ms,
        "block_samples": int(round(block_ms * config.sample_rate / 1000.0)),
        "input_samples": len(condition.noisy),
        "output_samples": len(output),
        "length_preserved": len(output) == len(condition.noisy),
        "sample_index_offset": 0,
        "input_snr_db": condition.input_snr_db,
        "output_snr_db": output_snr,
        "snr_improvement_db": output_snr - condition.input_snr_db,
        "input_si_sdr_db": condition.input_si_sdr_db,
        "output_si_sdr_db": output_si_sdr,
        "si_sdr_improvement_db": output_si_sdr - condition.input_si_sdr_db,
        "processing_total_ms": processing_total_ms,
        "rtf_total": processing_total_ms / 1000.0 / duration_s,
        **timing,
    }


def _offline_row(condition: object, method: str) -> dict[str, object]:
    config = DenoiseConfig(
        noise_estimator="low_energy",
        noise_quantile=0.35,
        spectral_alpha=1.5,
        spectral_floor=0.02,
        wiener_floor=0.05,
    )
    output, elapsed_s = process_method(method, condition.noisy, config)
    elapsed_ms = elapsed_s * 1000.0
    output_snr = snr_db(condition.clean, output)
    output_si_sdr = si_sdr(condition.clean, output)
    return {
        "speaker": condition.speaker,
        "noise": condition.noise_name,
        "noise_group": condition.noise_group,
        "snr_target_db": condition.snr_target_db,
        "candidate_id": f"{method}_low_energy_offline",
        "family": method,
        "execution_mode": "offline_file",
        "noise_mode": "low_energy_full_file",
        "block_ms": 0.0,
        "block_samples": 0,
        "input_samples": len(condition.noisy),
        "output_samples": len(output),
        "length_preserved": len(output) == len(condition.noisy),
        "sample_index_offset": 0,
        "input_snr_db": condition.input_snr_db,
        "output_snr_db": output_snr,
        "snr_improvement_db": output_snr - condition.input_snr_db,
        "input_si_sdr_db": condition.input_si_sdr_db,
        "output_si_sdr_db": output_si_sdr,
        "si_sdr_improvement_db": output_si_sdr - condition.input_si_sdr_db,
        "processing_total_ms": elapsed_ms,
        "rtf_total": elapsed_s / (len(output) / config.sample_rate),
        "blocks": 1,
        "processing_mean_ms": elapsed_ms,
        "processing_worst_ms": elapsed_ms,
        "processing_std_ms": 0.0,
        "processing_p50_ms": elapsed_ms,
        "processing_p95_ms": elapsed_ms,
        "processing_p99_ms": elapsed_ms,
        "rtf_block_mean": elapsed_s / (len(output) / config.sample_rate),
        "rtf_block_worst": elapsed_s / (len(output) / config.sample_rate),
        "blocks_over_budget": 0,
        "state_memory_max_bytes": 0,
        "speech_probable_fraction": 0.0,
        "warming_blocks": 0,
    }


def run(results_dir: Path) -> None:
    clean_path = ROOT / "dados" / "demo" / "clean_refinement" / "speech_george.wav"
    noise_path = ROOT / "dados" / "demo" / "noise_demand" / "pcafeter_ch01_seg01.wav"
    if not clean_path.exists() or not noise_path.exists():
        raise FileNotFoundError(
            "Dados preparados ausentes. Rode o preparo FSDD/DEMAND antes da matriz PC-2."
        )

    conditions = build_conditions(
        split="pc2_file_blocks",
        clean_files=[clean_path],
        noise_files=[noise_path],
        config=DenoiseConfig(),
        snrs_db=SNRS_DB,
    )
    rows: list[dict[str, object]] = []
    started = time.perf_counter()
    for condition in conditions:
        for method in CAUSAL_METHODS:
            for block_ms in BLOCKS_MS:
                rows.append(_causal_row(condition, method, block_ms))
        for method in ("stft_subtraction", "stft_wiener"):
            rows.append(_offline_row(condition, method))

    tables_dir = results_dir / "tabelas"
    tables_dir.mkdir(parents=True, exist_ok=True)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(tables_dir / "comparison_metrics.csv", index=False, encoding="utf-8")

    summary = (
        metrics.groupby(
            ["candidate_id", "family", "execution_mode", "block_ms", "block_samples"],
            as_index=False,
        )
        .agg(
            n_conditions=("snr_improvement_db", "size"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            processing_mean_ms=("processing_mean_ms", "mean"),
            processing_p95_ms=("processing_p95_ms", "mean"),
            processing_p99_ms=("processing_p99_ms", "mean"),
            processing_worst_ms=("processing_worst_ms", "max"),
            rtf_total_mean=("rtf_total", "mean"),
            blocks_over_budget=("blocks_over_budget", "sum"),
            state_memory_max_bytes=("state_memory_max_bytes", "max"),
            all_lengths_preserved=("length_preserved", "all"),
            max_sample_index_offset=("sample_index_offset", "max"),
        )
        .sort_values(["family", "execution_mode", "block_ms"])
    )
    summary.to_csv(tables_dir / "comparison_summary.csv", index=False, encoding="utf-8")

    offline = metrics[metrics["execution_mode"] == "offline_file"][
        ["family", "snr_target_db", "snr_improvement_db", "si_sdr_improvement_db"]
    ].rename(
        columns={
            "snr_improvement_db": "offline_snr_improvement_db",
            "si_sdr_improvement_db": "offline_si_sdr_improvement_db",
        }
    )
    causal = metrics[
        (metrics["execution_mode"] == "causal_blocks")
        & metrics["family"].isin(("stft_subtraction", "stft_wiener"))
    ].copy()
    gaps = causal.merge(offline, on=["family", "snr_target_db"], how="inner")
    gaps["snr_gap_to_offline_db"] = (
        gaps["offline_snr_improvement_db"] - gaps["snr_improvement_db"]
    )
    gaps["si_sdr_gap_to_offline_db"] = (
        gaps["offline_si_sdr_improvement_db"] - gaps["si_sdr_improvement_db"]
    )
    gaps[
        [
            "family",
            "snr_target_db",
            "block_ms",
            "snr_improvement_db",
            "offline_snr_improvement_db",
            "snr_gap_to_offline_db",
            "si_sdr_improvement_db",
            "offline_si_sdr_improvement_db",
            "si_sdr_gap_to_offline_db",
        ]
    ].to_csv(tables_dir / "causal_offline_gap.csv", index=False, encoding="utf-8")

    metadata = {
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_s": time.perf_counter() - started,
        "speech": {
            "path": str(clean_path.relative_to(ROOT)),
            "sha256": sha256_file(clean_path),
            "source": "FSDD prepared public speech",
        },
        "noise": {
            "path": str(noise_path.relative_to(ROOT)),
            "sha256": sha256_file(noise_path),
            "source": "DEMAND PCAFETER prepared segment",
        },
        "snrs_db": list(SNRS_DB),
        "block_ms": list(BLOCKS_MS),
        "causal_methods": list(CAUSAL_METHODS),
        "offline_reference": (
            "Full-file low-energy estimator with quantile 0.35; non-causal upper "
            "operational reference."
        ),
        "causal_config": asdict(CausalProcessorConfig()),
        "selection_policy": "Frozen PC-1 parameters; no parameter search in PC-2.",
        "alignment_policy": (
            "All outputs preserve the processed sample count and sample-index offset zero."
        ),
        "private_data": "No authored or private audio used.",
    }
    (tables_dir / "metadata_file_blocks.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa a matriz reproduzivel PC-2 de processamento por blocos."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "resultados" / "file_blocks",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results_dir = args.results_dir
    if not results_dir.is_absolute():
        results_dir = ROOT / results_dir
    run(results_dir)
    print(f"Matriz PC-2 salva em {results_dir}")


if __name__ == "__main__":
    main()
