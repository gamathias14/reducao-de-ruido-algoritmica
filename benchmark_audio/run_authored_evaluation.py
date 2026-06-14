from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from realtime_audio.block_metrics import summarize_block_timings
from realtime_audio.process_wav_blocks import process_samples_in_blocks, sha256_file

from .causal import CausalProcessorConfig
from .denoise import (
    DenoiseConfig,
    mix_at_snr,
    mse,
    process_method,
    read_wav_mono,
    rms,
    si_sdr,
    snr_db,
)
from .prepare_authored_voice import RECORDING_TYPES, SESSION_IDS
from .run_benchmark import ROOT


DEFAULT_SNRS_DB = (-5.0, 0.0, 5.0, 10.0)
DEFAULT_BLOCK_MS = 20.0
USABLE_STATUSES = ("prepared", "prepared_with_warnings")
REQUIRED_MANIFEST_FIELDS = (
    "speaker_id",
    "session_id",
    "recording_type",
    "utterance_id",
    "prepared_path",
    "prepared_sha256",
    "authorization_level",
    "status",
    "warnings",
)


@dataclass(frozen=True)
class PreparedRecording:
    speaker_id: str
    session_id: str
    recording_type: str
    utterance_id: str
    path: Path
    prepared_sha256: str
    authorization_level: str
    status: str
    warnings: str

    @property
    def recording_id(self) -> str:
        return (
            f"{self.speaker_id}_{self.session_id}_"
            f"{self.recording_type}_{self.utterance_id}"
        )


@dataclass(frozen=True)
class MethodSpec:
    candidate_id: str
    family: str
    execution_mode: str
    causal_config: CausalProcessorConfig | None = None
    offline_method: str | None = None
    offline_config: DenoiseConfig | None = None


def relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _resolve_manifest_path(value: str, root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def read_prepared_manifest(
    manifest_path: Path,
    *,
    root: Path = ROOT,
    allow_warnings: bool = False,
) -> list[PreparedRecording]:
    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [
            field
            for field in REQUIRED_MANIFEST_FIELDS
            if field not in (reader.fieldnames or [])
        ]
        if missing:
            raise ValueError(
                "Manifesto preparado sem colunas obrigatorias: "
                + ", ".join(missing)
            )
        rows = list(reader)

    recordings: list[PreparedRecording] = []
    rejected_warnings: list[str] = []
    for row in rows:
        status = (row.get("status") or "").strip()
        if status not in USABLE_STATUSES:
            continue
        warnings = (row.get("warnings") or "").strip()
        if status == "prepared_with_warnings" and warnings and not allow_warnings:
            rejected_warnings.append(row.get("utterance_id", ""))
            continue
        recording_type = (row.get("recording_type") or "").strip()
        if recording_type not in RECORDING_TYPES:
            raise ValueError(f"recording_type invalido: {recording_type!r}")
        session_id = (row.get("session_id") or "").strip()
        if session_id not in SESSION_IDS:
            raise ValueError(f"session_id invalido: {session_id!r}")

        path = _resolve_manifest_path(row["prepared_path"].strip(), root)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"WAV preparado inexistente: {path}")
        expected_hash = (row.get("prepared_sha256") or "").strip()
        if expected_hash and sha256_file(path) != expected_hash:
            raise ValueError(f"SHA-256 divergente para {path}")
        recordings.append(
            PreparedRecording(
                speaker_id=(row.get("speaker_id") or "").strip(),
                session_id=session_id,
                recording_type=recording_type,
                utterance_id=(row.get("utterance_id") or "").strip(),
                path=path,
                prepared_sha256=expected_hash,
                authorization_level=(row.get("authorization_level") or "").strip(),
                status=status,
                warnings=warnings,
            )
        )

    if rejected_warnings:
        raise ValueError(
            "Ha gravacoes preparadas com avisos; revise ou use --allow-warnings: "
            + ", ".join(sorted(rejected_warnings)[:10])
        )
    if not recordings:
        raise ValueError("Nenhuma gravacao preparada utilizavel encontrada.")
    return recordings


def method_specs() -> list[MethodSpec]:
    return [
        MethodSpec(
            candidate_id="bypass",
            family="baseline",
            execution_mode="causal_blocks",
            causal_config=CausalProcessorConfig(method="bypass"),
        ),
        MethodSpec(
            candidate_id="subtraction_adaptive_causal",
            family="stft_subtraction",
            execution_mode="causal_blocks",
            causal_config=CausalProcessorConfig(method="stft_subtraction"),
        ),
        MethodSpec(
            candidate_id="wiener_adaptive_causal",
            family="stft_wiener",
            execution_mode="causal_blocks",
            causal_config=CausalProcessorConfig(method="stft_wiener"),
        ),
        MethodSpec(
            candidate_id="subtraction_low_energy_offline",
            family="stft_subtraction",
            execution_mode="offline_file",
            offline_method="stft_subtraction",
            offline_config=DenoiseConfig(
                noise_estimator="low_energy",
                noise_quantile=0.35,
                spectral_alpha=1.5,
                spectral_floor=0.02,
            ),
        ),
        MethodSpec(
            candidate_id="wiener_low_energy_offline",
            family="stft_wiener",
            execution_mode="offline_file",
            offline_method="stft_wiener",
            offline_config=DenoiseConfig(
                noise_estimator="low_energy",
                noise_quantile=0.35,
                wiener_floor=0.05,
            ),
        ),
        MethodSpec(
            candidate_id="wavelet_refined_offline",
            family="wavelet",
            execution_mode="offline_file",
            offline_method="wavelet_soft",
            offline_config=DenoiseConfig(
                wavelet="sym4",
                wavelet_level=3,
                wavelet_mode="hard",
                wavelet_threshold_strategy="global",
                wavelet_threshold_scale=0.50,
            ),
        ),
    ]


def _load_audio(recording: PreparedRecording) -> np.ndarray:
    values = read_wav_mono(recording.path, 16_000, normalize=False)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError(f"Audio preparado invalido: {recording.path}")
    if rms(values) <= 1e-4:
        raise ValueError(f"Audio preparado silencioso demais: {recording.path}")
    return values.astype(np.float32)


def _repeat_to_length(values: np.ndarray, length: int) -> np.ndarray:
    if len(values) >= length:
        return values[:length].astype(np.float32)
    repeats = math.ceil(length / max(len(values), 1))
    return np.tile(values, repeats)[:length].astype(np.float32)


def _limit_clean_per_speaker(
    recordings: Iterable[PreparedRecording],
    limit: int,
) -> list[PreparedRecording]:
    selected: list[PreparedRecording] = []
    by_speaker: dict[str, list[PreparedRecording]] = {}
    for recording in sorted(recordings, key=lambda item: (item.speaker_id, item.utterance_id)):
        by_speaker.setdefault(recording.speaker_id, []).append(recording)
    for speaker in sorted(by_speaker):
        items = by_speaker[speaker]
        selected.extend(items if limit <= 0 else items[:limit])
    return selected


def _select_by_session_and_type(
    recordings: list[PreparedRecording],
    session_id: str,
    recording_type: str,
) -> list[PreparedRecording]:
    return [
        recording
        for recording in recordings
        if recording.session_id == session_id
        and recording.recording_type == recording_type
    ]


def _process_with_spec(
    samples: np.ndarray,
    spec: MethodSpec,
    block_ms: float,
) -> tuple[np.ndarray, dict[str, float | int]]:
    if spec.execution_mode == "causal_blocks":
        if spec.causal_config is None:
            raise ValueError(f"Metodo causal sem configuracao: {spec.candidate_id}")
        output, blocks = process_samples_in_blocks(
            samples,
            spec.causal_config,
            block_ms,
        )
        timing = summarize_block_timings(blocks)
        processing_total_ms = float(sum(float(row["processing_ms"]) for row in blocks))
        timing["processing_total_ms"] = processing_total_ms
        timing["rtf_total"] = processing_total_ms / 1000.0 / (len(samples) / 16_000)
        return output, timing

    if spec.offline_method is None or spec.offline_config is None:
        raise ValueError(f"Metodo offline sem configuracao: {spec.candidate_id}")
    output, elapsed_s = process_method(spec.offline_method, samples, spec.offline_config)
    elapsed_ms = elapsed_s * 1000.0
    return output, {
        "blocks": 1,
        "processing_mean_ms": elapsed_ms,
        "processing_worst_ms": elapsed_ms,
        "processing_std_ms": 0.0,
        "processing_p50_ms": elapsed_ms,
        "processing_p95_ms": elapsed_ms,
        "processing_p99_ms": elapsed_ms,
        "rtf_block_mean": elapsed_s / (len(samples) / 16_000),
        "rtf_block_worst": elapsed_s / (len(samples) / 16_000),
        "blocks_over_budget": 0,
        "state_memory_max_bytes": 0,
        "speech_probable_fraction": 0.0,
        "warming_blocks": 0,
        "processing_total_ms": elapsed_ms,
        "rtf_total": elapsed_s / (len(samples) / 16_000),
    }


def evaluate_controlled_mixtures(
    *,
    clean_recordings: list[PreparedRecording],
    noise_recordings: list[PreparedRecording],
    snrs_db: Sequence[float],
    specs: list[MethodSpec],
    block_ms: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    audio_cache: dict[Path, np.ndarray] = {}
    for clean_recording in clean_recordings:
        clean = audio_cache.setdefault(clean_recording.path, _load_audio(clean_recording))
        for noise_recording in noise_recordings:
            noise = audio_cache.setdefault(noise_recording.path, _load_audio(noise_recording))
            noise = _repeat_to_length(noise, len(clean))
            for target_snr in snrs_db:
                noisy, scaled_noise = mix_at_snr(clean, noise, float(target_snr))
                input_snr = snr_db(clean, noisy)
                input_si_sdr = si_sdr(clean, noisy)
                condition_id = (
                    f"{clean_recording.recording_id}__"
                    f"{noise_recording.recording_id}__{target_snr:g}db"
                )
                for spec in specs:
                    output, timing = _process_with_spec(noisy, spec, block_ms)
                    output_snr = snr_db(clean, output)
                    output_si_sdr = si_sdr(clean, output)
                    snr_improvement = output_snr - input_snr
                    rows.append(
                        {
                            "condition_id": condition_id,
                            "speaker_id": clean_recording.speaker_id,
                            "clean_utterance_id": clean_recording.utterance_id,
                            "noise_speaker_id": noise_recording.speaker_id,
                            "noise_utterance_id": noise_recording.utterance_id,
                            "session_id": clean_recording.session_id,
                            "snr_target_db": float(target_snr),
                            "candidate_id": spec.candidate_id,
                            "family": spec.family,
                            "execution_mode": spec.execution_mode,
                            "block_ms": block_ms if spec.execution_mode == "causal_blocks" else 0.0,
                            "clean_samples": len(clean),
                            "noise_samples_used": len(scaled_noise),
                            "output_samples": len(output),
                            "length_preserved": len(output) == len(noisy),
                            "input_snr_db": input_snr,
                            "output_snr_db": output_snr,
                            "snr_improvement_db": snr_improvement,
                            "snr_degraded": bool(snr_improvement < 0.0),
                            "input_si_sdr_db": input_si_sdr,
                            "output_si_sdr_db": output_si_sdr,
                            "si_sdr_improvement_db": output_si_sdr - input_si_sdr,
                            "mse": mse(clean, output),
                            "clean_authorization_level": clean_recording.authorization_level,
                            "noise_authorization_level": noise_recording.authorization_level,
                            **timing,
                        }
                    )
    return pd.DataFrame(rows)


def evaluate_operational_live_noisy(
    *,
    live_recordings: list[PreparedRecording],
    specs: list[MethodSpec],
    block_ms: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for recording in sorted(live_recordings, key=lambda item: item.recording_id):
        samples = _load_audio(recording)
        input_rms = rms(samples)
        input_peak = float(np.max(np.abs(samples)))
        for spec in specs:
            output, timing = _process_with_spec(samples, spec, block_ms)
            output_rms = rms(output)
            rows.append(
                {
                    "recording_id": recording.recording_id,
                    "speaker_id": recording.speaker_id,
                    "session_id": recording.session_id,
                    "utterance_id": recording.utterance_id,
                    "candidate_id": spec.candidate_id,
                    "family": spec.family,
                    "execution_mode": spec.execution_mode,
                    "block_ms": block_ms if spec.execution_mode == "causal_blocks" else 0.0,
                    "input_samples": len(samples),
                    "output_samples": len(output),
                    "length_preserved": len(output) == len(samples),
                    "input_peak_abs": input_peak,
                    "output_peak_abs": float(np.max(np.abs(output))),
                    "input_rms": input_rms,
                    "output_rms": output_rms,
                    "rms_delta_db": 20.0 * math.log10(
                        max(output_rms, 1e-12) / max(input_rms, 1e-12)
                    ),
                    "paired_reference_available": False,
                    "snr_or_si_sdr_policy": (
                        "Nao calcular SNR ou SI-SDR pareadas para raw_live_noisy "
                        "sem referencia limpa sincronizada."
                    ),
                    "authorization_level": recording.authorization_level,
                    **timing,
                }
            )
    return pd.DataFrame(rows)


def summarize_controlled(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary = (
        metrics.groupby(
            ["candidate_id", "family", "execution_mode", "snr_target_db"],
            as_index=False,
        )
        .agg(
            n_conditions=("snr_improvement_db", "size"),
            speakers=("speaker_id", "nunique"),
            noise_recordings=("noise_utterance_id", "nunique"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            snr_improvement_std_db=("snr_improvement_db", "std"),
            snr_improvement_min_db=("snr_improvement_db", "min"),
            snr_degradation_fraction=("snr_degraded", lambda values: float(np.mean(values))),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            mse_mean=("mse", "mean"),
            rtf_total_mean=("rtf_total", "mean"),
            processing_p95_ms=("processing_p95_ms", "mean"),
            processing_p99_ms=("processing_p99_ms", "mean"),
            processing_worst_ms=("processing_worst_ms", "max"),
            blocks_over_budget=("blocks_over_budget", "sum"),
            state_memory_max_bytes=("state_memory_max_bytes", "max"),
            all_lengths_preserved=("length_preserved", "all"),
        )
        .sort_values(["snr_target_db", "family", "candidate_id"])
    )
    by_speaker_noise = (
        metrics.groupby(
            [
                "speaker_id",
                "noise_utterance_id",
                "candidate_id",
                "family",
                "execution_mode",
            ],
            as_index=False,
        )
        .agg(
            n_conditions=("snr_improvement_db", "size"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            snr_degradation_fraction=("snr_degraded", lambda values: float(np.mean(values))),
            rtf_total_mean=("rtf_total", "mean"),
        )
        .sort_values(["speaker_id", "noise_utterance_id", "family", "candidate_id"])
    )
    return summary, by_speaker_noise


def _write_optional_dataframe(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


def run_authored_evaluation(
    *,
    prepared_manifest: Path,
    results_dir: Path,
    session_id: str,
    snrs_db: Sequence[float] = DEFAULT_SNRS_DB,
    block_ms: float = DEFAULT_BLOCK_MS,
    max_clean_per_speaker: int = 3,
    max_noises: int = 2,
    allow_warnings: bool = False,
    root: Path = ROOT,
) -> dict[str, Any]:
    if session_id not in SESSION_IDS:
        raise ValueError(f"Sessao invalida: {session_id}")
    started = time.perf_counter()
    recordings = read_prepared_manifest(
        prepared_manifest,
        root=root,
        allow_warnings=allow_warnings,
    )
    session_recordings = [
        recording for recording in recordings if recording.session_id == session_id
    ]
    if not session_recordings:
        raise ValueError(f"Nenhuma gravacao preparada para {session_id}.")

    clean_recordings = _limit_clean_per_speaker(
        _select_by_session_and_type(session_recordings, session_id, "raw_quiet"),
        max_clean_per_speaker,
    )
    noise_recordings = sorted(
        _select_by_session_and_type(session_recordings, session_id, "raw_noise"),
        key=lambda item: item.recording_id,
    )
    if max_noises > 0:
        noise_recordings = noise_recordings[:max_noises]
    live_recordings = _select_by_session_and_type(
        session_recordings,
        session_id,
        "raw_live_noisy",
    )
    if not clean_recordings:
        raise ValueError(f"Nenhuma gravacao raw_quiet utilizavel em {session_id}.")
    if not noise_recordings:
        raise ValueError(f"Nenhuma gravacao raw_noise utilizavel em {session_id}.")

    specs = method_specs()
    tables_dir = results_dir / "tabelas"
    tables_dir.mkdir(parents=True, exist_ok=True)
    controlled = evaluate_controlled_mixtures(
        clean_recordings=clean_recordings,
        noise_recordings=noise_recordings,
        snrs_db=snrs_db,
        specs=specs,
        block_ms=block_ms,
    )
    summary, by_speaker_noise = summarize_controlled(controlled)
    operational = evaluate_operational_live_noisy(
        live_recordings=live_recordings,
        specs=specs,
        block_ms=block_ms,
    )

    controlled_path = tables_dir / "controlled_metrics.csv"
    summary_path = tables_dir / "controlled_summary.csv"
    by_speaker_noise_path = tables_dir / "controlled_by_speaker_noise.csv"
    operational_path = tables_dir / "operational_live_noisy_metrics.csv"
    _write_optional_dataframe(controlled_path, controlled)
    _write_optional_dataframe(summary_path, summary)
    _write_optional_dataframe(by_speaker_noise_path, by_speaker_noise)
    _write_optional_dataframe(operational_path, operational)

    metadata = {
        "created_at_local": datetime.now().isoformat(timespec="seconds"),
        "elapsed_s": time.perf_counter() - started,
        "prepared_manifest": relative_or_absolute(prepared_manifest, root),
        "prepared_manifest_sha256": sha256_file(prepared_manifest),
        "session_id": session_id,
        "snrs_db": [float(value) for value in snrs_db],
        "block_ms": block_ms,
        "max_clean_per_speaker": max_clean_per_speaker,
        "max_noises": max_noises,
        "allow_warnings": allow_warnings,
        "counts": {
            "usable_recordings_total": len(recordings),
            "session_recordings": len(session_recordings),
            "clean_recordings_used": len(clean_recordings),
            "noise_recordings_used": len(noise_recordings),
            "live_noisy_recordings_used": len(live_recordings),
            "controlled_rows": len(controlled),
            "operational_rows": len(operational),
        },
        "methods": [
            {
                "candidate_id": spec.candidate_id,
                "family": spec.family,
                "execution_mode": spec.execution_mode,
                "causal_config": (
                    asdict(spec.causal_config)
                    if spec.causal_config is not None
                    else None
                ),
                "offline_method": spec.offline_method,
                "offline_config": (
                    asdict(spec.offline_config)
                    if spec.offline_config is not None
                    else None
                ),
            }
            for spec in specs
        ],
        "policy": {
            "parameter_freeze": (
                "Usa parametros congelados da PC-1/PC-2; nao faz busca nem "
                "ajuste na Sessao B."
            ),
            "paired_metrics": (
                "SNR, SI-SDR e MSE sao calculados somente em misturas controladas "
                "raw_quiet + ruido conhecido."
            ),
            "live_noisy_metrics": (
                "raw_live_noisy recebe apenas estatisticas operacionais; nao ha "
                "SNR/SI-SDR pareadas sem referencia limpa."
            ),
            "privacy": (
                "A CLI nao salva audio processado por padrao; grava apenas CSV/JSON "
                "com metricas e identificadores codificados."
            ),
        },
        "outputs": {
            "controlled_metrics": relative_or_absolute(controlled_path, root),
            "controlled_summary": relative_or_absolute(summary_path, root),
            "controlled_by_speaker_noise": relative_or_absolute(by_speaker_noise_path, root),
            "operational_live_noisy_metrics": relative_or_absolute(operational_path, root),
        },
    }
    metadata_path = tables_dir / "metadata_authored_evaluation.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    metadata["outputs"]["metadata"] = relative_or_absolute(metadata_path, root)
    return metadata


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Avalia gravacoes autorais preparadas com parametros causais congelados."
    )
    parser.add_argument("--prepared-manifest", required=True, type=Path)
    parser.add_argument("--results-dir", default=ROOT / "resultados" / "authored_voice" / "evaluation", type=Path)
    parser.add_argument("--session", choices=SESSION_IDS, default="session_b")
    parser.add_argument("--snrs", nargs="+", type=float, default=list(DEFAULT_SNRS_DB))
    parser.add_argument("--block-ms", type=float, default=DEFAULT_BLOCK_MS)
    parser.add_argument("--max-clean-per-speaker", type=int, default=3)
    parser.add_argument("--max-noises", type=int, default=2)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    results_dir = args.results_dir
    if not results_dir.is_absolute():
        results_dir = ROOT / results_dir
    prepared_manifest = args.prepared_manifest
    if not prepared_manifest.is_absolute():
        prepared_manifest = ROOT / prepared_manifest
    try:
        metadata = run_authored_evaluation(
            prepared_manifest=prepared_manifest,
            results_dir=results_dir,
            session_id=args.session,
            snrs_db=args.snrs,
            block_ms=args.block_ms,
            max_clean_per_speaker=args.max_clean_per_speaker,
            max_noises=args.max_noises,
            allow_warnings=args.allow_warnings,
            root=ROOT,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Erro: {exc}")
        return 2
    print(
        "Avaliacao autoral concluida: "
        f"{metadata['counts']['controlled_rows']} linhas pareadas, "
        f"{metadata['counts']['operational_rows']} linhas operacionais."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
