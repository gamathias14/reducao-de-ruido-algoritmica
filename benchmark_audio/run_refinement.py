from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .denoise import (
    DenoiseConfig,
    mix_at_snr,
    normalize_peak,
    process_method,
    read_wav_mono,
    si_sdr,
    snr_db,
    write_wav,
)
from .run_benchmark import BenchmarkConfig, ROOT, ensure_dirs, prepare_demo_speech
from .run_benchmark import DEMO_DIGITS, FSDD_BASE_URL, download_file


VALIDATION_SPEAKERS = ("jackson", "nicolas", "theo")
FINAL_SPEAKERS = ("george", "lucas", "yweweler")
VALIDATION_NOISE_GROUPS = ("DKITCHEN", "OOFFICE")
FINAL_NOISE_GROUPS = ("PCAFETER", "STRAFFIC")
SNRS_DB = (-5, 0, 5, 10)
REFINEMENT_SPEAKERS = VALIDATION_SPEAKERS + FINAL_SPEAKERS


@dataclass(frozen=True)
class Condition:
    split: str
    speaker: str
    noise_name: str
    noise_group: str
    snr_target_db: int
    clean: np.ndarray
    noisy: np.ndarray
    input_snr_db: float
    input_si_sdr_db: float


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    family: str
    method: str
    config: DenoiseConfig


def remove_guaranteed_initial_silence(
    clean: np.ndarray,
    sample_rate: int,
    trim_s: float = 0.30,
) -> np.ndarray:
    trim = min(len(clean) - 1, max(0, int(round(trim_s * sample_rate))))
    trimmed = np.asarray(clean[trim:], dtype=np.float32)
    if trimmed.size == 0:
        return np.asarray(clean, dtype=np.float32).copy()
    if len(trimmed) < len(clean):
        repeats = math.ceil(len(clean) / len(trimmed))
        trimmed = np.tile(trimmed, repeats)
    return normalize_peak(trimmed[: len(clean)], peak=0.85)


def noise_group_from_path(path: Path) -> str:
    return path.stem.split("_", 1)[0].upper()


def files_for_split(
    clean_dir: Path,
    noise_dir: Path,
    speakers: Iterable[str],
    noise_groups: Iterable[str],
) -> tuple[list[Path], list[Path]]:
    speaker_set = set(speakers)
    group_set = set(noise_groups)
    clean_files = [
        path
        for path in sorted(clean_dir.glob("speech_*.wav"))
        if path.stem.removeprefix("speech_") in speaker_set
    ]
    noise_files = [
        path
        for path in sorted(noise_dir.glob("*.wav"))
        if noise_group_from_path(path) in group_set
    ]
    if len(clean_files) != len(speaker_set):
        found = {path.stem.removeprefix("speech_") for path in clean_files}
        raise FileNotFoundError(f"Faltam falantes preparados: {sorted(speaker_set - found)}")
    if not noise_files:
        raise FileNotFoundError(f"Nenhum ruido encontrado para grupos {sorted(group_set)}")
    return clean_files, noise_files


def prepare_refinement_speech(root: Path, results_root: Path) -> Path:
    paths = ensure_dirs(root, results_dir=results_root)
    prepare_demo_speech(paths, BenchmarkConfig(duration_s=3.0))
    refinement_dir = root / "dados" / "demo" / "clean_refinement"
    refinement_dir.mkdir(parents=True, exist_ok=True)

    for speaker in REFINEMENT_SPEAKERS:
        if speaker == "lucas":
            for digit in DEMO_DIGITS:
                name = f"{digit}_{speaker}_0.wav"
                download_file(f"{FSDD_BASE_URL}/{name}", paths["raw"] / name)
            chunks = [np.zeros(int(0.30 * 16_000), dtype=np.float32)]
            for digit in DEMO_DIGITS:
                chunks.append(read_wav_mono(paths["raw"] / f"{digit}_{speaker}_0.wav", 16_000))
                chunks.append(np.zeros(int(0.05 * 16_000), dtype=np.float32))
            merged = np.concatenate(chunks)
            if len(merged) < 48_000:
                merged = np.tile(merged, math.ceil(48_000 / len(merged)))
            prepared = normalize_peak(merged[:48_000], peak=0.85)
        else:
            prepared = read_wav_mono(paths["demo_clean"] / f"speech_{speaker}.wav", 16_000)
            prepared = normalize_peak(prepared[:48_000], peak=0.85)
        write_wav(refinement_dir / f"speech_{speaker}.wav", prepared, 16_000)
    return refinement_dir


def build_conditions(
    *,
    split: str,
    clean_files: list[Path],
    noise_files: list[Path],
    config: DenoiseConfig,
    snrs_db: tuple[int, ...] = SNRS_DB,
) -> list[Condition]:
    conditions: list[Condition] = []
    target_samples = 3 * config.sample_rate
    for clean_path in clean_files:
        speaker = clean_path.stem.removeprefix("speech_")
        clean = read_wav_mono(clean_path, config.sample_rate)[:target_samples]
        clean = remove_guaranteed_initial_silence(clean, config.sample_rate)
        for noise_path in noise_files:
            noise = read_wav_mono(noise_path, config.sample_rate)
            if len(noise) < len(clean):
                noise = np.tile(noise, math.ceil(len(clean) / max(len(noise), 1)))
            noise = normalize_peak(noise[: len(clean)])
            group = noise_group_from_path(noise_path)
            for target_snr in snrs_db:
                noisy, _ = mix_at_snr(clean, noise, target_snr)
                conditions.append(
                    Condition(
                        split=split,
                        speaker=speaker,
                        noise_name=noise_path.stem,
                        noise_group=group,
                        snr_target_db=target_snr,
                        clean=clean,
                        noisy=noisy,
                        input_snr_db=snr_db(clean, noisy),
                        input_si_sdr_db=si_sdr(clean, noisy),
                    )
                )
    return conditions


def stft_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    frame_pairs = ((256, 80), (512, 160))
    estimator_options = (("initial", 0.2), ("low_energy", 0.10), ("low_energy", 0.20), ("low_energy", 0.35))
    for n_fft, hop_length in frame_pairs:
        for estimator, quantile in estimator_options:
            for alpha in (1.0, 1.2, 1.5):
                for floor in (0.02, 0.05):
                    config = DenoiseConfig(
                        n_fft=n_fft,
                        hop_length=hop_length,
                        spectral_alpha=alpha,
                        spectral_floor=floor,
                        noise_estimator=estimator,
                        noise_quantile=quantile,
                    )
                    candidate_id = (
                        f"sub_n{n_fft}_h{hop_length}_{estimator}_q{quantile:g}"
                        f"_a{alpha:g}_f{floor:g}"
                    )
                    candidates.append(Candidate(candidate_id, "stft_subtraction", "stft_subtraction", config))

            for floor in (0.03, 0.05, 0.10):
                config = DenoiseConfig(
                    n_fft=n_fft,
                    hop_length=hop_length,
                    wiener_floor=floor,
                    noise_estimator=estimator,
                    noise_quantile=quantile,
                )
                candidate_id = (
                    f"wiener_n{n_fft}_h{hop_length}_{estimator}_q{quantile:g}_f{floor:g}"
                )
                candidates.append(Candidate(candidate_id, "stft_wiener", "stft_wiener", config))
    return candidates


def wavelet_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    for wavelet in ("db4", "sym4", "coif1"):
        for level in (3, 5):
            for mode in ("soft", "hard"):
                for strategy in ("global", "per_scale"):
                    for scale in (0.50, 0.75, 1.00):
                        config = DenoiseConfig(
                            wavelet=wavelet,
                            wavelet_level=level,
                            wavelet_mode=mode,
                            wavelet_threshold_strategy=strategy,
                            wavelet_threshold_scale=scale,
                        )
                        candidate_id = (
                            f"wavelet_{wavelet}_l{level}_{mode}_{strategy}_s{scale:g}"
                        )
                        candidates.append(Candidate(candidate_id, "wavelet", "wavelet_soft", config))
    return candidates


def wavelet_packet_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    for wavelet in ("db4", "sym4"):
        for level in (3, 4):
            for quantile in (0.10, 0.20, 0.35):
                for floor in (0.02, 0.05, 0.10):
                    config = DenoiseConfig(
                        wpt_wavelet=wavelet,
                        wpt_level=level,
                        wpt_noise_tracking="rolling_quantile",
                        wpt_noise_quantile=quantile,
                        wpt_noise_window=31,
                        wpt_gain_floor=floor,
                    )
                    candidate_id = (
                        f"wpt_wiener_{wavelet}_l{level}_rolling_q{quantile:g}"
                        f"_w31_f{floor:g}"
                    )
                    candidates.append(
                        Candidate(
                            candidate_id,
                            "wavelet_packet",
                            "wavelet_packet_wiener",
                            config,
                        )
                    )
    return candidates


def evaluate_candidate(candidate: Candidate, conditions: list[Condition]) -> dict[str, object]:
    improvements = []
    si_sdr_improvements = []
    elapsed_values = []
    for condition in conditions:
        processed, elapsed = process_method(candidate.method, condition.noisy, candidate.config)
        improvements.append(snr_db(condition.clean, processed) - condition.input_snr_db)
        si_sdr_improvements.append(si_sdr(condition.clean, processed) - condition.input_si_sdr_db)
        elapsed_values.append(elapsed)

    improvement = np.asarray(improvements, dtype=np.float64)
    si_sdr_improvement = np.asarray(si_sdr_improvements, dtype=np.float64)
    elapsed = np.asarray(elapsed_values, dtype=np.float64)
    row: dict[str, object] = {
        "candidate_id": candidate.candidate_id,
        "family": candidate.family,
        "method": candidate.method,
        "n_conditions": len(conditions),
        "snr_improvement_mean_db": float(np.mean(improvement)),
        "snr_improvement_std_db": float(np.std(improvement)),
        "snr_improvement_min_db": float(np.min(improvement)),
        "snr_degradation_fraction": float(np.mean(improvement < 0.0)),
        "si_sdr_improvement_mean_db": float(np.mean(si_sdr_improvement)),
        "processing_mean_ms": float(np.mean(elapsed) * 1000.0),
        "rtf_mean": float(np.mean(elapsed) / 3.0),
    }
    row.update(asdict(candidate.config))
    return row


def select_candidates(candidate_rows: pd.DataFrame) -> pd.DataFrame:
    selected_rows = []
    for family, group in candidate_rows.groupby("family", sort=True):
        ranked = group.sort_values(
            [
                "snr_improvement_mean_db",
                "si_sdr_improvement_mean_db",
                "snr_degradation_fraction",
                "rtf_mean",
            ],
            ascending=[False, False, True, True],
        )
        selected = ranked.iloc[0].copy()
        selected["selection_rank"] = 1
        selected_rows.append(selected)
    return pd.DataFrame(selected_rows).sort_values("family").reset_index(drop=True)


def candidate_from_row(row: pd.Series) -> Candidate:
    config_fields = DenoiseConfig.__dataclass_fields__
    config_values = {name: row[name] for name in config_fields}
    config_values["sample_rate"] = int(config_values["sample_rate"])
    config_values["n_fft"] = int(config_values["n_fft"])
    config_values["hop_length"] = int(config_values["hop_length"])
    config_values["wavelet_level"] = int(config_values["wavelet_level"])
    config_values["wpt_level"] = int(config_values["wpt_level"])
    config_values["wpt_noise_window"] = int(config_values["wpt_noise_window"])
    config_values["wpt_frame_length"] = int(config_values["wpt_frame_length"])
    config_values["wpt_frame_hop"] = int(config_values["wpt_frame_hop"])
    return Candidate(
        candidate_id=str(row["candidate_id"]),
        family=str(row["family"]),
        method=str(row["method"]),
        config=DenoiseConfig(**config_values),
    )


def comparison_candidates(selected: pd.DataFrame) -> list[Candidate]:
    defaults = DenoiseConfig()
    candidates = [
        Candidate("noisy", "baseline", "noisy", defaults),
        Candidate("stft_subtraction_default_initial", "stft_subtraction_default", "stft_subtraction", defaults),
        Candidate("stft_wiener_default_initial", "stft_wiener_default", "stft_wiener", defaults),
        Candidate("wavelet_default_db4_l5_soft", "wavelet_default", "wavelet_soft", defaults),
    ]
    candidates.extend(candidate_from_row(row) for _, row in selected.iterrows())
    return candidates


def evaluate_comparison(
    candidates: list[Candidate],
    conditions: list[Condition],
    output_audio_dir: Path | None = None,
) -> pd.DataFrame:
    rows = []
    example_saved = False
    for condition in conditions:
        save_example = (
            output_audio_dir is not None
            and not example_saved
            and condition.snr_target_db == 0
        )
        if save_example:
            output_audio_dir.mkdir(parents=True, exist_ok=True)
            write_wav(
                output_audio_dir / f"{condition.split}_{condition.noise_name}_0db_clean.wav",
                normalize_peak(condition.clean),
                16_000,
            )
            write_wav(
                output_audio_dir / f"{condition.split}_{condition.noise_name}_0db_noisy.wav",
                normalize_peak(condition.noisy),
                16_000,
            )

        for candidate in candidates:
            processed, elapsed = process_method(candidate.method, condition.noisy, candidate.config)
            output_snr = snr_db(condition.clean, processed)
            output_si_sdr = si_sdr(condition.clean, processed)
            rows.append(
                {
                    "split": condition.split,
                    "speaker": condition.speaker,
                    "noise": condition.noise_name,
                    "noise_group": condition.noise_group,
                    "snr_target_db": condition.snr_target_db,
                    "candidate_id": candidate.candidate_id,
                    "family": candidate.family,
                    "method": candidate.method,
                    "input_snr_db": condition.input_snr_db,
                    "output_snr_db": output_snr,
                    "snr_improvement_db": output_snr - condition.input_snr_db,
                    "input_si_sdr_db": condition.input_si_sdr_db,
                    "output_si_sdr_db": output_si_sdr,
                    "si_sdr_improvement_db": output_si_sdr - condition.input_si_sdr_db,
                    "processing_ms": elapsed * 1000.0,
                    "rtf": elapsed / 3.0,
                }
            )
            if save_example and candidate.candidate_id != "noisy":
                write_wav(
                    output_audio_dir
                    / f"{condition.split}_{condition.noise_name}_0db_{candidate.candidate_id}.wav",
                    normalize_peak(processed),
                    16_000,
                )
        if save_example:
            example_saved = True
    return pd.DataFrame(rows)


def summarize_comparison(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = (
        metrics.groupby(["split", "candidate_id", "family", "snr_target_db"], as_index=False)
        .agg(
            n_conditions=("snr_improvement_db", "size"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            snr_improvement_std_db=("snr_improvement_db", "std"),
            snr_improvement_min_db=("snr_improvement_db", "min"),
            snr_degradation_fraction=("snr_improvement_db", lambda values: float(np.mean(values < 0.0))),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            processing_mean_ms=("processing_ms", "mean"),
            rtf_mean=("rtf", "mean"),
        )
        .sort_values(["split", "snr_target_db", "family"])
    )
    by_noise = (
        metrics.groupby(["split", "noise_group", "candidate_id", "family"], as_index=False)
        .agg(
            n_conditions=("snr_improvement_db", "size"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            snr_improvement_std_db=("snr_improvement_db", "std"),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            rtf_mean=("rtf", "mean"),
        )
        .sort_values(["split", "noise_group", "family"])
    )
    return summary, by_noise


def summarize_overall(metrics: pd.DataFrame) -> pd.DataFrame:
    return (
        metrics.groupby(["split", "candidate_id", "family"], as_index=False)
        .agg(
            n_conditions=("snr_improvement_db", "size"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            snr_improvement_std_db=("snr_improvement_db", "std"),
            snr_improvement_min_db=("snr_improvement_db", "min"),
            snr_degradation_fraction=("snr_improvement_db", lambda values: float(np.mean(values < 0.0))),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            processing_mean_ms=("processing_ms", "mean"),
            processing_worst_ms=("processing_ms", "max"),
            rtf_mean=("rtf", "mean"),
            rtf_worst=("rtf", "max"),
        )
        .sort_values(["split", "family"])
    )


def write_split_manifest(
    path: Path,
    validation_clean: list[Path],
    validation_noise: list[Path],
    final_clean: list[Path],
    final_noise: list[Path],
) -> None:
    rows = []
    for split, paths, kind in (
        ("validation", validation_clean, "speech"),
        ("validation", validation_noise, "noise"),
        ("final", final_clean, "speech"),
        ("final", final_noise, "noise"),
    ):
        for item in paths:
            rows.append(
                {
                    "split": split,
                    "kind": kind,
                    "name": item.stem,
                    "group": noise_group_from_path(item) if kind == "noise" else item.stem.removeprefix("speech_"),
                    "path": str(item.resolve().relative_to(ROOT.resolve())),
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")


def run_refinement(args: argparse.Namespace) -> None:
    results_root = Path(args.results_dir)
    if not results_root.is_absolute():
        results_root = ROOT / results_root
    tables_dir = results_root / "tabelas"
    audio_dir = results_root / "audio"
    tables_dir.mkdir(parents=True, exist_ok=True)

    if args.prepare_speech:
        clean_dir = prepare_refinement_speech(ROOT, results_root)
    else:
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

    base_config = DenoiseConfig()
    validation_conditions = build_conditions(
        split="validation",
        clean_files=validation_clean,
        noise_files=validation_noise,
        config=base_config,
    )
    final_conditions = build_conditions(
        split="final",
        clean_files=final_clean,
        noise_files=final_noise,
        config=base_config,
    )

    started = time.perf_counter()
    candidates = stft_candidates() + wavelet_candidates()
    if args.include_wpt:
        candidates += wavelet_packet_candidates()
    candidate_rows = pd.DataFrame(
        [evaluate_candidate(candidate, validation_conditions) for candidate in candidates]
    )
    candidate_rows.to_csv(
        tables_dir / "validation_candidates.csv",
        index=False,
        encoding="utf-8",
    )
    selected = select_candidates(candidate_rows)
    selected.to_csv(tables_dir / "selected_configs.csv", index=False, encoding="utf-8")
    (tables_dir / "selected_configs.json").write_text(
        json.dumps(selected.to_dict(orient="records"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    comparison = comparison_candidates(selected)
    validation_metrics = evaluate_comparison(comparison, validation_conditions)
    final_metrics = evaluate_comparison(comparison, final_conditions, output_audio_dir=audio_dir)
    all_metrics = pd.concat([validation_metrics, final_metrics], ignore_index=True)
    summary, by_noise = summarize_comparison(all_metrics)
    overall = summarize_overall(all_metrics)
    all_metrics.to_csv(tables_dir / "comparison_metrics.csv", index=False, encoding="utf-8")
    summary.to_csv(tables_dir / "comparison_summary.csv", index=False, encoding="utf-8")
    by_noise.to_csv(tables_dir / "comparison_by_noise.csv", index=False, encoding="utf-8")
    overall.to_csv(tables_dir / "comparison_overall.csv", index=False, encoding="utf-8")

    metadata = {
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "speech_source": "Free Spoken Digit Dataset (FSDD), human speech",
        "noise_source": "DEMAND 16 kHz prepared snippets",
        "initial_silence_policy": "Fixed 0.30 s prefix removed before mixtures; no guaranteed initial silence.",
        "validation_speakers": list(VALIDATION_SPEAKERS),
        "final_speakers": list(FINAL_SPEAKERS),
        "validation_noise_groups": list(VALIDATION_NOISE_GROUPS),
        "final_noise_groups": list(FINAL_NOISE_GROUPS),
        "snrs_db": list(SNRS_DB),
        "validation_conditions": len(validation_conditions),
        "final_conditions": len(final_conditions),
        "candidate_count": len(candidates),
        "include_wpt": bool(args.include_wpt),
        "selection_rule": (
            "Within each family: maximize validation mean SNR improvement, then mean SI-SDR "
            "improvement, then minimize degradation fraction and RTF."
        ),
        "caveat": (
            "The final operational split is not historically blind because all four environments "
            "were inspected in the earlier exploratory DEMAND round; no final-split values were "
            "used by this script to choose parameters."
        ),
        "elapsed_s": time.perf_counter() - started,
    }
    (tables_dir / "metadata_refinement.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refinamento validacao/final para STFT e Wavelet em DEMAND sem silencio inicial."
        )
    )
    parser.add_argument(
        "--prepare-speech",
        action="store_true",
        help="Baixa/prepara os seis falantes FSDD antes do refinamento.",
    )
    parser.add_argument(
        "--results-dir",
        default="resultados/demand_refinement",
        help="Diretorio isolado para resultados do refinamento.",
    )
    parser.add_argument(
        "--include-wpt",
        action="store_true",
        help="Inclui candidatos Wavelet Packet + Wiener como familia separada.",
    )
    return parser.parse_args()


def main() -> None:
    run_refinement(parse_args())


if __name__ == "__main__":
    main()
