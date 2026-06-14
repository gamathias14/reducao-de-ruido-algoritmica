from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from scipy.io import wavfile

from benchmark_audio.causal import (
    CAUSAL_METHODS,
    NOISE_ESTIMATOR_MODES,
    CausalProcessorConfig,
    CausalSTFTProcessor,
)
from benchmark_audio.denoise import audio_to_float_mono, resample_audio
from realtime_audio.block_metrics import summarize_block_timings


TARGET_SAMPLE_RATE = 16_000
SUPPORTED_BLOCK_MS = (10.0, 20.0, 32.0)
CSV_FIELDS = (
    "block_index",
    "start_sample",
    "end_sample_exclusive",
    "block_samples",
    "processing_ms",
    "rtf_block",
    "input_peak",
    "output_peak",
    "warming_up",
    "estimator_ready",
    "speech_probable",
    "low_energy",
    "estimator_updates",
    "noise_power_mean",
    "state_memory_bytes",
)


@dataclass(frozen=True)
class WavMetadata:
    sample_rate: int
    channels: int
    sample_count_per_channel: int
    dtype: str
    sample_width_bits: int


@dataclass
class WavProcessingResult:
    processed: np.ndarray
    blocks: list[dict[str, float | int | bool]]
    metrics: dict[str, object]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def block_samples_from_ms(block_ms: float, sample_rate: int = TARGET_SAMPLE_RATE) -> int:
    if block_ms not in SUPPORTED_BLOCK_MS:
        supported = ", ".join(f"{value:g}" for value in SUPPORTED_BLOCK_MS)
        raise ValueError(f"Bloco invalido: {block_ms:g} ms. Use {supported} ms.")
    exact = block_ms * sample_rate / 1000.0
    rounded = int(round(exact))
    if abs(exact - rounded) > 1e-9:
        raise ValueError("O tamanho de bloco nao produz numero inteiro de amostras.")
    return rounded


def read_wav_for_processing(
    path: Path,
    target_sample_rate: int = TARGET_SAMPLE_RATE,
) -> tuple[np.ndarray, WavMetadata]:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Arquivo WAV inexistente: {path}")
    if not path.is_file():
        raise ValueError(f"O caminho de entrada nao e um arquivo: {path}")
    try:
        sample_rate, raw = wavfile.read(path)
    except Exception as exc:
        raise ValueError(f"Nao foi possivel ler o WAV {path}: {exc}") from exc

    raw = np.asarray(raw)
    if raw.ndim not in (1, 2):
        raise ValueError(f"WAV com formato de canais invalido: {raw.shape}")
    channels = 1 if raw.ndim == 1 else int(raw.shape[1])
    sample_count = int(raw.shape[0])
    if sample_count == 0:
        raise ValueError(f"O WAV de entrada esta vazio: {path}")
    if int(sample_rate) <= 0:
        raise ValueError(f"Taxa de amostragem invalida no WAV: {sample_rate}")

    metadata = WavMetadata(
        sample_rate=int(sample_rate),
        channels=channels,
        sample_count_per_channel=sample_count,
        dtype=str(raw.dtype),
        sample_width_bits=int(raw.dtype.itemsize * 8),
    )
    mono = audio_to_float_mono(raw)
    processed = resample_audio(mono, int(sample_rate), target_sample_rate)
    if processed.size == 0:
        raise ValueError(f"O WAV ficou vazio apos conversao: {path}")
    if not np.all(np.isfinite(processed)):
        raise ValueError(f"O WAV contem amostras nao finitas: {path}")
    return processed.astype(np.float32), metadata


def process_samples_in_blocks(
    samples: np.ndarray,
    config: CausalProcessorConfig,
    block_ms: float,
    *,
    clock: Callable[[], float] = time.perf_counter,
) -> tuple[np.ndarray, list[dict[str, float | int | bool]]]:
    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    if values.size == 0:
        raise ValueError("Nao e possivel processar um sinal vazio.")
    if not np.all(np.isfinite(values)):
        raise ValueError("O sinal de entrada contem amostras nao finitas.")
    if config.sample_rate != TARGET_SAMPLE_RATE:
        raise ValueError(f"A configuracao deve usar {TARGET_SAMPLE_RATE} Hz.")

    block_samples = block_samples_from_ms(block_ms, config.sample_rate)
    processor = CausalSTFTProcessor(config)
    outputs: list[np.ndarray] = []
    rows: list[dict[str, float | int | bool]] = []
    for block_index, start in enumerate(range(0, len(values), block_samples)):
        block = values[start : start + block_samples]
        started = clock()
        output, diagnostics = processor.process_block(block)
        elapsed_s = max(0.0, clock() - started)
        block_duration_s = len(block) / config.sample_rate
        outputs.append(output)
        rows.append(
            {
                "block_index": block_index,
                "start_sample": start,
                "end_sample_exclusive": start + len(block),
                "block_samples": len(block),
                "processing_ms": elapsed_s * 1000.0,
                "rtf_block": elapsed_s / block_duration_s,
                "input_peak": float(np.max(np.abs(block))),
                "output_peak": float(np.max(np.abs(output))),
                "warming_up": bool(diagnostics["warming_up"]),
                "estimator_ready": bool(diagnostics["estimator_ready"]),
                "speech_probable": bool(diagnostics["speech_probable"]),
                "low_energy": bool(diagnostics["low_energy"]),
                "estimator_updates": int(diagnostics["estimator_updates"]),
                "noise_power_mean": float(diagnostics["noise_power_mean"]),
                "state_memory_bytes": int(diagnostics["state_memory_bytes"]),
            }
        )
    processed = np.concatenate(outputs).astype(np.float32)
    if len(processed) != len(values):
        raise RuntimeError("O processador causal nao preservou o comprimento.")
    return processed, rows


def write_pcm16(path: Path, samples: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    non_finite = int(np.sum(~np.isfinite(values)))
    if non_finite:
        raise ValueError("A saida contem amostras nao finitas.")
    out_of_range = int(np.sum((values < -1.0) | (values > 1.0)))
    clipped = np.clip(values, -1.0, 1.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(np.rint(clipped * 32768.0), -32768, 32767).astype(np.int16)
    wavfile.write(path, TARGET_SAMPLE_RATE, pcm)
    return {
        "peak_before_pcm_write": float(np.max(np.abs(values))),
        "peak_after_clip": float(np.max(np.abs(clipped))),
        "samples_out_of_range_before_write": out_of_range,
        "non_finite_samples_before_write": non_finite,
    }


def _dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("numpy", "scipy"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def _ensure_output_paths(
    paths: Sequence[Path],
    input_path: Path,
    overwrite: bool,
) -> None:
    resolved_input = input_path.resolve()
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Saida WAV, CSV e JSON devem usar caminhos diferentes.")
    if resolved_input in resolved:
        raise ValueError("Nenhuma saida pode sobrescrever o WAV de entrada.")
    existing = [path for path in resolved if path.exists()]
    if existing and not overwrite:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Saida ja existe; use --overwrite para substituir: {joined}"
        )


def process_wav_file(
    *,
    input_path: Path,
    output_path: Path,
    metrics_json_path: Path,
    blocks_csv_path: Path,
    config: CausalProcessorConfig,
    block_ms: float,
    overwrite: bool = False,
    command_args: Sequence[str] | None = None,
) -> WavProcessingResult:
    _ensure_output_paths(
        (output_path, metrics_json_path, blocks_csv_path),
        input_path,
        overwrite,
    )
    input_samples, input_metadata = read_wav_for_processing(input_path)
    started = time.perf_counter()
    processed, blocks = process_samples_in_blocks(input_samples, config, block_ms)
    total_elapsed_s = time.perf_counter() - started

    write_report = write_pcm16(output_path, processed)
    blocks_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with blocks_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(blocks)

    summary = summarize_block_timings(blocks)
    duration_s = len(input_samples) / config.sample_rate
    summary["processing_total_ms"] = total_elapsed_s * 1000.0
    summary["rtf_total"] = total_elapsed_s / duration_s
    metrics: dict[str, object] = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command_args": list(command_args or []),
        "input": {
            "path": str(input_path.resolve()),
            "sha256": sha256_file(input_path),
            **asdict(input_metadata),
        },
        "output": {
            "path": str(output_path.resolve()),
            "sha256": sha256_file(output_path),
            "sample_rate": config.sample_rate,
            "channels": 1,
            "dtype": "int16",
            "sample_width_bits": 16,
        },
        "blocks_csv": {
            "path": str(blocks_csv_path.resolve()),
            "sha256": sha256_file(blocks_csv_path),
            "columns": list(CSV_FIELDS),
        },
        "processing": {
            "method": config.method,
            "noise_mode": config.noise_mode,
            "block_ms": block_ms,
            "block_samples": block_samples_from_ms(block_ms, config.sample_rate),
            "processed_samples": len(input_samples),
            "duration_s": duration_s,
            "length_preserved": len(processed) == len(input_samples),
            "file_alignment": (
                "sample-index aligned after mono/resampling conversion; no delay "
                "samples are inserted or removed"
            ),
            "algorithmic_latency_estimated_ms": (
                0.0
                if config.method == "bypass"
                else 1000.0 * config.n_fft / config.sample_rate
            ),
            "normalization_applied": False,
            "input_peak": float(np.max(np.abs(input_samples))),
            "output_peak_before_pcm_write": float(np.max(np.abs(processed))),
            "input_samples_out_of_range": int(
                np.sum((input_samples < -1.0) | (input_samples > 1.0))
            ),
            **write_report,
        },
        "causal_config": asdict(config),
        "timing": summary,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dependencies": _dependency_versions(),
        },
        "notes": (
            "Tempo de arquivo mede custo computacional offline por blocos; nao inclui "
            "driver, dispositivo ou latencia fisica de audio."
        ),
    }
    metrics_json_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_json_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return WavProcessingResult(processed=processed, blocks=blocks, metrics=metrics)


def build_config(args: argparse.Namespace) -> CausalProcessorConfig:
    return CausalProcessorConfig(
        sample_rate=TARGET_SAMPLE_RATE,
        method=args.method,
        noise_mode=args.noise_mode,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Processa WAV mono/estereo em blocos com o nucleo causal da captura Windows."
    )
    parser.add_argument("--input", required=True, type=Path, help="WAV de entrada.")
    parser.add_argument("--output", required=True, type=Path, help="WAV PCM16 de saida.")
    parser.add_argument("--method", choices=CAUSAL_METHODS, default="stft_subtraction")
    parser.add_argument(
        "--noise-mode",
        choices=NOISE_ESTIMATOR_MODES,
        default="adaptive",
        help="adaptive e o modo principal; calibration e baseline explicito.",
    )
    parser.add_argument(
        "--block-ms",
        type=float,
        choices=SUPPORTED_BLOCK_MS,
        default=20.0,
    )
    parser.add_argument("--metrics-json", required=True, type=Path)
    parser.add_argument("--blocks-csv", required=True, type=Path)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite substituir as tres saidas declaradas.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    command_args = list(argv) if argv is not None else sys.argv[1:]
    try:
        result = process_wav_file(
            input_path=args.input,
            output_path=args.output,
            metrics_json_path=args.metrics_json,
            blocks_csv_path=args.blocks_csv,
            config=build_config(args),
            block_ms=args.block_ms,
            overwrite=args.overwrite,
            command_args=command_args,
        )
    except (FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    print(
        f"Processamento concluido: {len(result.processed)} amostras, "
        f"{len(result.blocks)} blocos."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
