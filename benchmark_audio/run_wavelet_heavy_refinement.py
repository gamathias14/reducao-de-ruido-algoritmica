from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pywt

from .denoise import DenoiseConfig
from .run_benchmark import ROOT
from .run_refinement import (
    FINAL_NOISE_GROUPS,
    FINAL_SPEAKERS,
    VALIDATION_NOISE_GROUPS,
    VALIDATION_SPEAKERS,
    Candidate,
    Condition,
    build_conditions,
    evaluate_candidate,
    evaluate_comparison,
    files_for_split,
    summarize_comparison,
    summarize_overall,
    write_split_manifest,
)


SAMPLE_COUNT = 48_000


def _slug(value: object) -> str:
    return str(value).replace(".", "p")


def _valid_dwt_level(wavelet_name: str, level: int, n_samples: int = SAMPLE_COUNT) -> bool:
    wavelet = pywt.Wavelet(wavelet_name)
    return level <= pywt.dwt_max_level(n_samples, wavelet.dec_len)


def _valid_wpt_level(wavelet_name: str, level: int, n_samples: int = SAMPLE_COUNT) -> bool:
    wavelet = pywt.Wavelet(wavelet_name)
    return level <= pywt.dwt_max_level(n_samples, wavelet.dec_len)


def profile_values(profile: str) -> dict[str, tuple]:
    if profile == "quick":
        return {
            "dwt_wavelets": ("db4", "sym4"),
            "dwt_levels": (3,),
            "dwt_scales": (0.5, 1.0),
            "wpt_wavelets": ("db4", "sym4"),
            "wpt_levels": (3,),
            "frame_wavelets": ("db4", "sym4"),
            "frame_levels": (2,),
            "frame_lengths": (512,),
            "frame_hops": (256,),
            "quantiles": (0.20,),
            "floors": (0.05, 0.10),
            "smoothings": (0.0,),
        }
    if profile == "max":
        return {
            "dwt_wavelets": ("haar", "db2", "db4", "db6", "sym4", "sym6", "coif1", "coif3", "bior4.4"),
            "dwt_levels": (2, 3, 4, 5),
            "dwt_scales": (0.15, 0.25, 0.50, 0.75, 1.00, 1.25),
            "wpt_wavelets": ("haar", "db2", "db4", "db6", "sym4", "sym6", "coif1", "coif3", "bior4.4"),
            "wpt_levels": (2, 3, 4, 5),
            "frame_wavelets": ("haar", "db2", "db4", "db6", "sym4", "sym6", "coif1", "coif3"),
            "frame_levels": (2, 3, 4),
            "frame_lengths": (512, 1024),
            "frame_hops": ("half", "quarter"),
            "quantiles": (0.05, 0.10, 0.20, 0.35),
            "floors": (0.01, 0.02, 0.05, 0.10, 0.20),
            "smoothings": (0.0, 0.20),
        }
    return {
        "dwt_wavelets": ("haar", "db2", "db4", "db6", "sym4", "sym6", "coif1", "coif3", "bior4.4"),
        "dwt_levels": (2, 3, 4, 5),
        "dwt_scales": (0.25, 0.50, 0.75, 1.00, 1.25),
        "wpt_wavelets": ("haar", "db2", "db4", "db6", "sym4", "sym6", "coif1", "coif3", "bior4.4"),
        "wpt_levels": (2, 3, 4),
        "frame_wavelets": ("db2", "db4", "sym4", "sym6", "coif1", "coif3"),
        "frame_levels": (2, 3),
        "frame_lengths": (512, 1024),
        "frame_hops": ("half",),
        "quantiles": (0.10, 0.20, 0.35),
        "floors": (0.02, 0.05, 0.10, 0.20),
        "smoothings": (0.0, 0.20),
    }


def heavy_wavelet_candidates(profile: str = "focused") -> list[Candidate]:
    values = profile_values(profile)
    candidates: list[Candidate] = []

    for wavelet in values["dwt_wavelets"]:
        for level in values["dwt_levels"]:
            if not _valid_dwt_level(wavelet, int(level)):
                continue
            for mode in ("soft", "hard"):
                for strategy in ("global", "per_scale"):
                    for scale in values["dwt_scales"]:
                        config = DenoiseConfig(
                            wavelet=wavelet,
                            wavelet_level=int(level),
                            wavelet_mode=mode,
                            wavelet_threshold_strategy=strategy,
                            wavelet_threshold_scale=float(scale),
                        )
                        candidate_id = (
                            f"dwt_{_slug(wavelet)}_l{level}_{mode}_{strategy}"
                            f"_s{float(scale):g}"
                        )
                        candidates.append(Candidate(candidate_id, "dwt_wavelet_heavy", "wavelet_soft", config))

    for wavelet in values["wpt_wavelets"]:
        for level in values["wpt_levels"]:
            if not _valid_wpt_level(wavelet, int(level)):
                continue
            for tracking in ("global_quantile", "rolling_quantile"):
                smoothings = (0.0,) if tracking == "global_quantile" else values["smoothings"]
                for quantile in values["quantiles"]:
                    for floor in values["floors"]:
                        for smoothing in smoothings:
                            config = DenoiseConfig(
                                wpt_wavelet=wavelet,
                                wpt_level=int(level),
                                wpt_noise_tracking=tracking,
                                wpt_noise_quantile=float(quantile),
                                wpt_noise_window=31,
                                wpt_noise_smoothing=float(smoothing),
                                wpt_gain_floor=float(floor),
                            )
                            candidate_id = (
                                f"wpt_coeff_{_slug(wavelet)}_l{level}_{tracking}"
                                f"_q{float(quantile):g}_w31_f{float(floor):g}"
                                f"_sm{float(smoothing):g}"
                            )
                            candidates.append(
                                Candidate(
                                    candidate_id,
                                    "wpt_coeff_wiener",
                                    "wavelet_packet_wiener",
                                    config,
                                )
                            )

    for wavelet in values["frame_wavelets"]:
        for frame_length in values["frame_lengths"]:
            for level in values["frame_levels"]:
                if not _valid_wpt_level(wavelet, int(level), int(frame_length)):
                    continue
                for hop_spec in values["frame_hops"]:
                    hop = int(frame_length // 2) if hop_spec == "half" else int(frame_length // 4)
                    for tracking in ("global_quantile", "rolling_quantile"):
                        smoothings = (0.0,) if tracking == "global_quantile" else values["smoothings"]
                        for quantile in values["quantiles"]:
                            for floor in values["floors"]:
                                for smoothing in smoothings:
                                    config = DenoiseConfig(
                                        wpt_wavelet=wavelet,
                                        wpt_level=int(level),
                                        wpt_noise_tracking=tracking,
                                        wpt_noise_quantile=float(quantile),
                                        wpt_noise_window=31,
                                        wpt_noise_smoothing=float(smoothing),
                                        wpt_gain_floor=float(floor),
                                        wpt_frame_length=int(frame_length),
                                        wpt_frame_hop=hop,
                                    )
                                    candidate_id = (
                                        f"wpt_frame_{_slug(wavelet)}_l{level}_n{frame_length}_h{hop}"
                                        f"_{tracking}_q{float(quantile):g}_w31"
                                        f"_f{float(floor):g}_sm{float(smoothing):g}"
                                    )
                                    candidates.append(
                                        Candidate(
                                            candidate_id,
                                            "wpt_frame_wiener",
                                            "wavelet_packet_wiener_frames",
                                            config,
                                        )
                                    )
    return candidates


def select_screening_conditions(
    conditions: list[Condition],
    *,
    speaker_count: int,
    noises_per_group: int,
) -> list[Condition]:
    speakers = sorted({condition.speaker for condition in conditions})[:speaker_count]
    selected_noises: set[str] = set()
    for group in sorted({condition.noise_group for condition in conditions}):
        names = sorted({condition.noise_name for condition in conditions if condition.noise_group == group})
        selected_noises.update(names[:noises_per_group])
    return [
        condition
        for condition in conditions
        if condition.speaker in speakers and condition.noise_name in selected_noises
    ]


def add_selection_score(rows: pd.DataFrame) -> pd.DataFrame:
    scored = rows.copy()
    scored["selection_score"] = (
        scored["snr_improvement_mean_db"]
        + scored["si_sdr_improvement_mean_db"]
        + 0.25 * scored["snr_improvement_min_db"]
        - 2.0 * scored["snr_degradation_fraction"]
    )
    return scored


def evaluate_candidates(candidates: list[Candidate], conditions: list[Condition]) -> pd.DataFrame:
    rows = [evaluate_candidate(candidate, conditions) for candidate in candidates]
    return add_selection_score(pd.DataFrame(rows))


def select_for_full_validation(
    screening_rows: pd.DataFrame,
    candidates: list[Candidate],
    per_family: int,
) -> list[Candidate]:
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    selected_ids: list[str] = []
    for _, group in screening_rows.groupby("family", sort=True):
        by_score = group.sort_values("selection_score", ascending=False).head(per_family)
        by_snr = group.sort_values(
            ["snr_improvement_mean_db", "si_sdr_improvement_mean_db"],
            ascending=False,
        ).head(per_family)
        for candidate_id in list(by_score["candidate_id"]) + list(by_snr["candidate_id"]):
            if candidate_id not in selected_ids:
                selected_ids.append(candidate_id)
    return [candidate_by_id[candidate_id] for candidate_id in selected_ids]


def select_representatives(validation_rows: pd.DataFrame, candidates: list[Candidate]) -> pd.DataFrame:
    selected_rows = []
    for _, group in validation_rows.groupby("family", sort=True):
        by_score = group.sort_values("selection_score", ascending=False).iloc[0].copy()
        by_score["selection_reason"] = "robust_score"
        selected_rows.append(by_score)

        by_snr = group.sort_values(
            ["snr_improvement_mean_db", "si_sdr_improvement_mean_db"],
            ascending=False,
        ).iloc[0].copy()
        by_snr["selection_reason"] = "snr_mean"
        if by_snr["candidate_id"] != by_score["candidate_id"]:
            selected_rows.append(by_snr)

    selected = pd.DataFrame(selected_rows).sort_values(["family", "selection_reason"])
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    selected["method"] = selected["candidate_id"].map(lambda value: candidate_by_id[str(value)].method)
    return selected.reset_index(drop=True)


def candidate_from_id(candidate_id: str, candidates: list[Candidate]) -> Candidate:
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise KeyError(candidate_id)


def comparison_candidates(selected: pd.DataFrame, full_candidates: list[Candidate]) -> list[Candidate]:
    defaults = DenoiseConfig()
    references = [
        Candidate("noisy", "baseline", "noisy", defaults),
        Candidate(
            "subtraction_low_energy_offline",
            "stft_reference",
            "stft_subtraction",
            DenoiseConfig(noise_estimator="low_energy", noise_quantile=0.35, spectral_alpha=1.5, spectral_floor=0.02),
        ),
        Candidate(
            "wiener_low_energy_offline",
            "stft_reference",
            "stft_wiener",
            DenoiseConfig(noise_estimator="low_energy", noise_quantile=0.35, wiener_floor=0.05),
        ),
        Candidate("wavelet_default_db4_l5_soft", "dwt_reference", "wavelet_soft", defaults),
        Candidate(
            "wavelet_sym4_l3_hard_global_s0.5",
            "dwt_reference",
            "wavelet_soft",
            DenoiseConfig(
                wavelet="sym4",
                wavelet_level=3,
                wavelet_mode="hard",
                wavelet_threshold_strategy="global",
                wavelet_threshold_scale=0.5,
            ),
        ),
        Candidate(
            "wpt_initial_sym4_l3_rolling_q0.2_w31_f0.1",
            "wpt_reference",
            "wavelet_packet_wiener",
            DenoiseConfig(
                wpt_wavelet="sym4",
                wpt_level=3,
                wpt_noise_tracking="rolling_quantile",
                wpt_noise_quantile=0.20,
                wpt_noise_window=31,
                wpt_gain_floor=0.10,
            ),
        ),
    ]
    selected_candidates = [
        candidate_from_id(str(candidate_id), full_candidates)
        for candidate_id in selected["candidate_id"].drop_duplicates()
    ]
    known_ids = {candidate.candidate_id for candidate in references}
    references.extend(candidate for candidate in selected_candidates if candidate.candidate_id not in known_ids)
    return references


def run(args: argparse.Namespace) -> None:
    results_root = Path(args.results_dir)
    if not results_root.is_absolute():
        results_root = ROOT / results_root
    tables_dir = results_root / "tabelas"
    audio_dir = results_root / "audio"
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

    config = DenoiseConfig()
    validation_conditions = build_conditions(
        split="validation",
        clean_files=validation_clean,
        noise_files=validation_noise,
        config=config,
    )
    final_conditions = build_conditions(
        split="final",
        clean_files=final_clean,
        noise_files=final_noise,
        config=config,
    )
    screening_conditions = select_screening_conditions(
        validation_conditions,
        speaker_count=args.screening_speakers,
        noises_per_group=args.screening_noises_per_group,
    )

    started = time.perf_counter()
    candidates = heavy_wavelet_candidates(args.profile)
    screening_rows = evaluate_candidates(candidates, screening_conditions)
    screening_rows.to_csv(tables_dir / "screening_candidates.csv", index=False, encoding="utf-8")

    full_candidates = select_for_full_validation(
        screening_rows,
        candidates,
        per_family=args.full_per_family,
    )
    validation_rows = evaluate_candidates(full_candidates, validation_conditions)
    validation_rows.to_csv(tables_dir / "validation_candidates.csv", index=False, encoding="utf-8")

    selected = select_representatives(validation_rows, full_candidates)
    selected.to_csv(tables_dir / "selected_wavelet_configs.csv", index=False, encoding="utf-8")
    (tables_dir / "selected_wavelet_configs.json").write_text(
        json.dumps(selected.to_dict(orient="records"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    comparison = comparison_candidates(selected, full_candidates)
    validation_metrics = evaluate_comparison(comparison, validation_conditions)
    final_metrics = evaluate_comparison(comparison, final_conditions, output_audio_dir=audio_dir)
    all_metrics = pd.concat([validation_metrics, final_metrics], ignore_index=True)
    summary, by_noise = summarize_comparison(all_metrics)
    overall = summarize_overall(all_metrics)
    all_metrics.to_csv(tables_dir / "comparison_metrics.csv", index=False, encoding="utf-8")
    summary.to_csv(tables_dir / "comparison_summary.csv", index=False, encoding="utf-8")
    by_noise.to_csv(tables_dir / "comparison_by_noise.csv", index=False, encoding="utf-8")
    overall.to_csv(tables_dir / "comparison_overall.csv", index=False, encoding="utf-8")

    candidate_counts = screening_rows.groupby("family").size().to_dict()
    metadata = {
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "profile": args.profile,
        "speech_source": "Free Spoken Digit Dataset (FSDD), human speech",
        "noise_source": "DEMAND 16 kHz prepared snippets",
        "validation_speakers": list(VALIDATION_SPEAKERS),
        "final_speakers": list(FINAL_SPEAKERS),
        "validation_noise_groups": list(VALIDATION_NOISE_GROUPS),
        "final_noise_groups": list(FINAL_NOISE_GROUPS),
        "screening_conditions": len(screening_conditions),
        "validation_conditions": len(validation_conditions),
        "final_conditions": len(final_conditions),
        "candidate_count": len(candidates),
        "candidate_counts_by_family": {str(key): int(value) for key, value in candidate_counts.items()},
        "full_validation_candidate_count": len(full_candidates),
        "comparison_candidate_count": len(comparison),
        "selection_rule": (
            "Screening uses validation-only subset. Full validation keeps the union of top candidates "
            "by robust score and by mean SNR in each family. Representatives are selected by robust "
            "score and mean SNR; final split is evaluated only after selection."
        ),
        "robust_score": "snr_mean + si_sdr_mean + 0.25 * snr_min - 2.0 * degradation_fraction",
        "elapsed_s": time.perf_counter() - started,
        "default_config": asdict(config),
    }
    (tables_dir / "metadata_wavelet_heavy.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Busca pesada e isolada para DWT/WPT em DEMAND, sem usar o final para selecionar."
    )
    parser.add_argument(
        "--results-dir",
        default="resultados/wavelet_heavy_refinement",
        help="Diretorio novo para tabelas e exemplos da busca Wavelet pesada.",
    )
    parser.add_argument(
        "--profile",
        choices=("quick", "focused", "max"),
        default="focused",
        help="Tamanho da grade de triagem. 'focused' e pesado; 'max' pode demorar bastante.",
    )
    parser.add_argument(
        "--screening-speakers",
        type=int,
        default=1,
        help="Numero de falantes de validacao usados na triagem ampla.",
    )
    parser.add_argument(
        "--screening-noises-per-group",
        type=int,
        default=1,
        help="Numero de segmentos de ruido por grupo usados na triagem ampla.",
    )
    parser.add_argument(
        "--full-per-family",
        type=int,
        default=12,
        help="Top-N por familia e por criterio levado da triagem para validacao completa.",
    )
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
