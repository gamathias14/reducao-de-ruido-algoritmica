from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from .denoise import DenoiseConfig
from .literature_harness import (
    adapter_registry,
    condition_manifest,
    evaluate_adapter,
    metadata_records,
    summarize_metrics,
)
from .run_benchmark import ROOT
from .run_refinement import (
    FINAL_NOISE_GROUPS,
    FINAL_SPEAKERS,
    VALIDATION_NOISE_GROUPS,
    VALIDATION_SPEAKERS,
    build_conditions,
    files_for_split,
    write_split_manifest,
)


DEFAULT_RESULTS_DIR = (
    "resultados/sysvad_checkpoint46_reopened/literature_benchmark"
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _build_split(split: str):
    clean_dir = ROOT / "dados" / "demo" / "clean_refinement"
    noise_dir = ROOT / "dados" / "demo" / "noise_demand"
    if split == "validation":
        speakers = VALIDATION_SPEAKERS
        noise_groups = VALIDATION_NOISE_GROUPS
    elif split == "final_operational":
        speakers = FINAL_SPEAKERS
        noise_groups = FINAL_NOISE_GROUPS
    else:
        raise ValueError(f"Split desconhecido: {split}")
    clean_files, noise_files = files_for_split(
        clean_dir,
        noise_dir,
        speakers,
        noise_groups,
    )
    conditions = build_conditions(
        split=split,
        clean_files=clean_files,
        noise_files=noise_files,
        config=DenoiseConfig(),
    )
    return clean_files, noise_files, conditions


def run(args: argparse.Namespace) -> None:
    results_root = Path(args.results_dir)
    if not results_root.is_absolute():
        results_root = ROOT / results_root
    tables_dir = results_root / "tabelas"
    tables_dir.mkdir(parents=True, exist_ok=True)

    registry = adapter_registry()
    unknown = sorted(set(args.systems) - set(registry))
    if unknown:
        raise ValueError(
            f"Sistemas ainda indisponiveis: {unknown}. "
            f"Disponiveis: {sorted(registry)}"
        )
    if args.split == "final_operational" and not args.allow_final:
        raise ValueError(
            "O split final operacional exige --allow-final depois da selecao "
            "congelada no split de validacao."
        )

    clean_files, noise_files, conditions = _build_split(args.split)
    manifest = condition_manifest(conditions)
    manifest.to_csv(
        tables_dir / f"{args.split}_mixture_manifest.csv",
        index=False,
        encoding="utf-8",
    )
    if args.split == "validation":
        final_clean, final_noise, _ = _build_split("final_operational")
        write_split_manifest(
            tables_dir / "split_manifest.csv",
            clean_files,
            noise_files,
            final_clean,
            final_noise,
        )

    started = time.perf_counter()
    metrics = pd.concat(
        [
            evaluate_adapter(registry[system_id], conditions)
            for system_id in args.systems
        ],
        ignore_index=True,
    )
    summary = summarize_metrics(metrics)
    metrics.to_csv(
        tables_dir / f"{args.split}_condition_metrics.csv",
        index=False,
        encoding="utf-8",
    )
    summary.to_csv(
        tables_dir / f"{args.split}_system_summary.csv",
        index=False,
        encoding="utf-8",
    )
    _write_json(tables_dir / "system_registry.json", metadata_records())
    _write_json(
        tables_dir / f"{args.split}_run_metadata.json",
        {
            "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
            "protocol": "checkpoint46r_literature_benchmark_v1",
            "split": args.split,
            "systems": list(args.systems),
            "condition_count": len(conditions),
            "canonical_sample_rate": 16_000,
            "private_audio_used": False,
            "audio_outputs_written": False,
            "vm_started": False,
            "selection_performed": args.split == "final_operational",
            "selection_basis": (
                "candidate_decision.json"
                if args.split == "final_operational"
                else None
            ),
            "elapsed_seconds": time.perf_counter() - started,
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Harness comum do benchmark de algoritmos do Checkpoint 46-R."
    )
    parser.add_argument(
        "--systems",
        nargs="+",
        default=["baseline_stft"],
        help="IDs de sistemas implementados no registry.",
    )
    parser.add_argument(
        "--split",
        choices=("validation", "final_operational"),
        default="validation",
    )
    parser.add_argument("--allow-final", action="store_true")
    parser.add_argument("--results-dir", default=DEFAULT_RESULTS_DIR)
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
