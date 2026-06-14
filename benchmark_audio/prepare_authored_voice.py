from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy.io import wavfile

from .denoise import SAMPLE_RATE, audio_to_float_mono, resample_audio, rms


ROOT = Path(__file__).resolve().parents[1]
RECORDING_TYPES = ("raw_quiet", "raw_noise", "raw_live_noisy")
SESSION_IDS = ("session_a", "session_b")
AUTHORIZATION_LEVELS = ("local_only", "advisor_board", "public_excerpt")
RAW_MANIFEST_FIELDS = (
    "speaker_id",
    "session_id",
    "recording_type",
    "utterance_id",
    "source_path",
    "recorded_at",
    "device",
    "interface",
    "driver",
    "expected_sample_rate_hz",
    "expected_channels",
    "expected_bit_depth",
    "distance_cm",
    "gain_setting",
    "environment",
    "capture_processing",
    "authorization_level",
    "consent_record_id",
    "notes",
)
PREPARED_MANIFEST_FIELDS = RAW_MANIFEST_FIELDS + (
    "prepared_path",
    "source_sha256",
    "prepared_sha256",
    "original_sample_rate_hz",
    "original_channels",
    "original_bit_depth",
    "original_frames",
    "original_dtype",
    "prepared_sample_rate_hz",
    "prepared_channels",
    "prepared_bit_depth",
    "prepared_samples",
    "duration_s",
    "input_peak_abs",
    "input_peak_dbfs",
    "input_rms",
    "input_rms_dbfs",
    "dc_offset_removed",
    "clipped_samples",
    "clipping_detected",
    "silent_detected",
    "output_peak_abs",
    "output_rms",
    "preprocessing",
    "status",
    "warnings",
    "error",
)


@dataclass(frozen=True)
class PcmWavMetadata:
    sample_rate: int
    channels: int
    sample_width_bytes: int
    frames: int
    compression: str

    @property
    def bit_depth(self) -> int:
        return self.sample_width_bytes * 8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _dbfs(value: float) -> float:
    return float(20.0 * math.log10(max(value, 1e-12)))


def _optional_int(value: str) -> int | None:
    stripped = value.strip()
    return None if not stripped else int(stripped)


def inspect_pcm_wav(path: Path) -> PcmWavMetadata:
    try:
        with wave.open(str(path), "rb") as handle:
            metadata = PcmWavMetadata(
                sample_rate=handle.getframerate(),
                channels=handle.getnchannels(),
                sample_width_bytes=handle.getsampwidth(),
                frames=handle.getnframes(),
                compression=handle.getcomptype(),
            )
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError(f"WAV PCM invalido ou truncado: {path}: {exc}") from exc
    if metadata.compression != "NONE":
        raise ValueError(f"WAV comprimido nao suportado: {path}")
    if metadata.sample_rate <= 0 or metadata.channels <= 0:
        raise ValueError(f"Metadados WAV invalidos: {path}")
    if metadata.sample_width_bytes not in (1, 2, 3, 4):
        raise ValueError(
            f"Profundidade PCM nao suportada: {metadata.sample_width_bytes * 8} bits"
        )
    if metadata.frames <= 0:
        raise ValueError(f"WAV vazio: {path}")
    return metadata


def read_pcm_wav(path: Path) -> tuple[np.ndarray, PcmWavMetadata, str]:
    metadata = inspect_pcm_wav(path)
    try:
        sample_rate, raw = wavfile.read(path)
    except Exception as exc:
        raise ValueError(f"Nao foi possivel decodificar {path}: {exc}") from exc
    raw = np.asarray(raw)
    if raw.ndim not in (1, 2) or raw.shape[0] != metadata.frames:
        raise ValueError(f"Forma PCM inconsistente em {path}: {raw.shape}")
    if int(sample_rate) != metadata.sample_rate:
        raise ValueError(f"Taxa inconsistente entre cabecalho e decodificador: {path}")
    if not np.issubdtype(raw.dtype, np.integer):
        raise ValueError(f"Apenas WAV PCM inteiro e aceito: {path} ({raw.dtype})")
    return audio_to_float_mono(raw), metadata, str(raw.dtype)


def remove_dc(samples: np.ndarray) -> tuple[np.ndarray, float]:
    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    dc_offset = float(np.mean(values, dtype=np.float64))
    return (values - dc_offset).astype(np.float32), dc_offset


def analyze_audio(samples: np.ndarray) -> dict[str, float | int | bool]:
    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    if values.size == 0:
        raise ValueError("Audio vazio.")
    if not np.all(np.isfinite(values)):
        raise ValueError("Audio contem amostras nao finitas.")
    peak = float(np.max(np.abs(values)))
    rms_value = rms(values)
    clipped = int(np.sum(np.abs(values) >= (1.0 - 1.0 / 32768.0)))
    return {
        "peak_abs": peak,
        "peak_dbfs": _dbfs(peak),
        "rms": rms_value,
        "rms_dbfs": _dbfs(rms_value),
        "clipped_samples": clipped,
        "clipping_detected": clipped > 0,
        "silent_detected": rms_value <= 1e-4,
    }


def write_pcm16(path: Path, samples: np.ndarray) -> None:
    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("Derivado vazio ou nao finito.")
    pcm = np.clip(np.rint(np.clip(values, -1.0, 1.0) * 32768.0), -32768, 32767)
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, SAMPLE_RATE, pcm.astype(np.int16))


def read_raw_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in RAW_MANIFEST_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Manifesto sem colunas obrigatorias: {', '.join(missing)}")
        rows = [{field: (row.get(field) or "").strip() for field in RAW_MANIFEST_FIELDS} for row in reader]
    if not rows:
        raise ValueError("Manifesto bruto sem linhas.")
    return rows


def validate_manifest_row(row: dict[str, str]) -> None:
    speaker = row["speaker_id"]
    if len(speaker) != 5 or not speaker.startswith("spk") or not speaker[3:].isdigit():
        raise ValueError(f"speaker_id invalido: {speaker!r}; use spk01, spk02, ...")
    if row["session_id"] not in SESSION_IDS:
        raise ValueError(f"session_id invalido: {row['session_id']!r}")
    if row["recording_type"] not in RECORDING_TYPES:
        raise ValueError(f"recording_type invalido: {row['recording_type']!r}")
    if not row["utterance_id"]:
        raise ValueError("utterance_id vazio.")
    if not row["source_path"]:
        raise ValueError("source_path vazio.")
    if row["authorization_level"] not in AUTHORIZATION_LEVELS:
        raise ValueError(
            f"authorization_level invalido: {row['authorization_level']!r}"
        )
    if not row["consent_record_id"]:
        raise ValueError("consent_record_id vazio; registre a autorizacao antes da ingestao.")
    for field in ("expected_sample_rate_hz", "expected_channels", "expected_bit_depth"):
        try:
            value = _optional_int(row[field])
        except ValueError as exc:
            raise ValueError(f"{field} deve ser inteiro quando preenchido.") from exc
        if value is not None and value <= 0:
            raise ValueError(f"{field} deve ser positivo.")


def duration_warnings(recording_type: str, duration_s: float) -> list[str]:
    ranges = {
        "raw_quiet": (0.25, 35.0),
        "raw_noise": (30.0, 60.0),
        "raw_live_noisy": (10.0, 20.0),
    }
    minimum, maximum = ranges[recording_type]
    warnings: list[str] = []
    if duration_s < minimum:
        warnings.append("duration_below_protocol")
    if duration_s > maximum:
        warnings.append("duration_above_protocol")
    return warnings


def _prepared_target(row: dict[str, str], prepared_root: Path) -> Path:
    filename = f"{row['utterance_id']}.wav"
    return (
        prepared_root
        / row["speaker_id"]
        / row["session_id"]
        / row["recording_type"]
        / filename
    )


def _base_output_row(row: dict[str, str]) -> dict[str, object]:
    return {field: row.get(field, "") for field in RAW_MANIFEST_FIELDS}


def ingest_authored_voice(
    *,
    manifest_path: Path,
    raw_root: Path,
    prepared_root: Path,
    prepared_manifest_path: Path,
    quality_report_path: Path,
    root: Path = ROOT,
    overwrite: bool = False,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    manifest_path = manifest_path.resolve()
    raw_root = raw_root.resolve()
    prepared_root = prepared_root.resolve()
    rows = read_raw_manifest(manifest_path)

    identities: set[tuple[str, str, str, str]] = set()
    targets: list[Path] = []
    for row in rows:
        validate_manifest_row(row)
        identity = (
            row["speaker_id"],
            row["session_id"],
            row["recording_type"],
            row["utterance_id"],
        )
        if identity in identities:
            raise ValueError(f"Identidade duplicada no manifesto: {identity}")
        identities.add(identity)
        target = _prepared_target(row, prepared_root).resolve()
        if not _is_within(target, prepared_root):
            raise ValueError(f"Destino preparado fora da raiz permitida: {target}")
        targets.append(target)

    declared_outputs = [prepared_manifest_path.resolve(), quality_report_path.resolve()]
    if len(set(targets + declared_outputs)) != len(targets) + len(declared_outputs):
        raise ValueError("Caminhos de saida duplicados.")
    existing = [path for path in targets + declared_outputs if path.exists()]
    if existing and not overwrite:
        joined = ", ".join(str(path) for path in existing[:5])
        raise FileExistsError(f"Saida ja existe; use --overwrite: {joined}")

    output_rows: list[dict[str, object]] = []
    for row, target in zip(rows, targets):
        output = _base_output_row(row)
        source = Path(row["source_path"])
        if not source.is_absolute():
            source = root / source
        source = source.resolve()
        try:
            if not _is_within(source, raw_root):
                raise ValueError(f"source_path fora de raw_root: {source}")
            if not source.exists() or not source.is_file():
                raise FileNotFoundError(f"WAV bruto inexistente: {source}")

            mono, metadata, dtype = read_pcm_wav(source)
            input_analysis = analyze_audio(mono)
            duration_s = metadata.frames / metadata.sample_rate
            warnings = duration_warnings(row["recording_type"], duration_s)
            if input_analysis["clipping_detected"]:
                warnings.append("clipping_detected")
            if input_analysis["silent_detected"]:
                warnings.append("silence_detected")

            expected_values = {
                "expected_sample_rate_hz": metadata.sample_rate,
                "expected_channels": metadata.channels,
                "expected_bit_depth": metadata.bit_depth,
            }
            for field, actual in expected_values.items():
                expected = _optional_int(row[field])
                if expected is not None and expected != actual:
                    warnings.append(f"{field}_mismatch")

            without_dc, dc_offset = remove_dc(mono)
            prepared = resample_audio(without_dc, metadata.sample_rate, SAMPLE_RATE)
            output_analysis = analyze_audio(prepared)
            if output_analysis["clipping_detected"]:
                warnings.append("prepared_clipping_detected")
            write_pcm16(target, prepared)

            output.update(
                {
                    "prepared_path": relative_or_absolute(target, root),
                    "source_sha256": sha256_file(source),
                    "prepared_sha256": sha256_file(target),
                    "original_sample_rate_hz": metadata.sample_rate,
                    "original_channels": metadata.channels,
                    "original_bit_depth": metadata.bit_depth,
                    "original_frames": metadata.frames,
                    "original_dtype": dtype,
                    "prepared_sample_rate_hz": SAMPLE_RATE,
                    "prepared_channels": 1,
                    "prepared_bit_depth": 16,
                    "prepared_samples": len(prepared),
                    "duration_s": duration_s,
                    "input_peak_abs": input_analysis["peak_abs"],
                    "input_peak_dbfs": input_analysis["peak_dbfs"],
                    "input_rms": input_analysis["rms"],
                    "input_rms_dbfs": input_analysis["rms_dbfs"],
                    "dc_offset_removed": dc_offset,
                    "clipped_samples": input_analysis["clipped_samples"],
                    "clipping_detected": input_analysis["clipping_detected"],
                    "silent_detected": input_analysis["silent_detected"],
                    "output_peak_abs": output_analysis["peak_abs"],
                    "output_rms": output_analysis["rms"],
                    "preprocessing": (
                        "PCM decode; channel mean; DC removal; polyphase resampling "
                        "to mono 16 kHz; PCM16 write; no denoising or normalization"
                    ),
                    "status": "prepared_with_warnings" if warnings else "prepared",
                    "warnings": "|".join(warnings),
                    "error": "",
                }
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            output.update(
                {
                    "prepared_path": relative_or_absolute(target, root),
                    "status": "error",
                    "warnings": "",
                    "error": str(exc),
                }
            )
        output_rows.append(output)

    prepared_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with prepared_manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREPARED_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)

    summary = {
        "records": len(output_rows),
        "prepared": sum(row["status"] == "prepared" for row in output_rows),
        "prepared_with_warnings": sum(
            row["status"] == "prepared_with_warnings" for row in output_rows
        ),
        "errors": sum(row["status"] == "error" for row in output_rows),
        "clipping_detected": sum(
            str(row.get("clipping_detected", "")).lower() == "true"
            for row in output_rows
        ),
        "silence_detected": sum(
            str(row.get("silent_detected", "")).lower() == "true"
            for row in output_rows
        ),
    }
    report: dict[str, object] = {
        "schema_version": 1,
        "input_manifest": relative_or_absolute(manifest_path, root),
        "input_manifest_sha256": sha256_file(manifest_path),
        "raw_root": relative_or_absolute(raw_root, root),
        "prepared_root": relative_or_absolute(prepared_root, root),
        "prepared_manifest": relative_or_absolute(prepared_manifest_path, root),
        "target_sample_rate_hz": SAMPLE_RATE,
        "authorization_levels": list(AUTHORIZATION_LEVELS),
        "preprocessing_policy": (
            "Preserve raw files; decode PCM; average channels; remove DC; resample "
            "to 16 kHz; write PCM16; no denoising, gate, EQ, compression or normalization."
        ),
        "summary": summary,
        "issues": [
            {
                "speaker_id": row["speaker_id"],
                "session_id": row["session_id"],
                "recording_type": row["recording_type"],
                "utterance_id": row["utterance_id"],
                "status": row["status"],
                "warnings": row.get("warnings", ""),
                "error": row.get("error", ""),
            }
            for row in output_rows
            if row["status"] != "prepared"
        ],
    }
    quality_report_path.parent.mkdir(parents=True, exist_ok=True)
    quality_report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return output_rows, report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida e prepara gravacoes autorais privadas a partir de manifesto."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=ROOT / "dados" / "raw" / "authored_voice",
    )
    parser.add_argument(
        "--prepared-root",
        type=Path,
        default=ROOT / "dados" / "prepared" / "authored_voice",
    )
    parser.add_argument(
        "--prepared-manifest",
        type=Path,
        default=ROOT / "resultados" / "authored_voice" / "ingestion" / "prepared_manifest.csv",
    )
    parser.add_argument(
        "--quality-report",
        type=Path,
        default=ROOT / "resultados" / "authored_voice" / "ingestion" / "quality_report.json",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        _, report = ingest_authored_voice(
            manifest_path=args.manifest,
            raw_root=args.raw_root,
            prepared_root=args.prepared_root,
            prepared_manifest_path=args.prepared_manifest,
            quality_report_path=args.quality_report,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    summary = report["summary"]
    print(
        "Ingestao concluida: "
        f"{summary['prepared']} preparados, "
        f"{summary['prepared_with_warnings']} com avisos, "
        f"{summary['errors']} erros."
    )
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
