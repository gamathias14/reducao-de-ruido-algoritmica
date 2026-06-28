from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np

from realtime_audio.block_metrics import summarize_block_timings
from realtime_audio.process_wav_blocks import (
    read_wav_for_processing,
    sha256_file,
    write_pcm16,
)
from realtime_audio.rnnoise_processor import (
    INPUT_BLOCK_SAMPLES,
    INPUT_SAMPLE_RATE,
    TOTAL_ALGORITHMIC_LATENCY_MS,
    RNNoiseRealtimeProcessor,
    default_library_path,
)


BLOCK_MS = 20.0


def _startup_preroll_blocks(
    sample_count: int,
    startup_preroll_ms: float,
) -> int:
    if startup_preroll_ms < 0.0:
        raise ValueError("startup_preroll_ms nao pode ser negativo.")
    requested_blocks = int(round(startup_preroll_ms / BLOCK_MS))
    total_blocks = (sample_count + INPUT_BLOCK_SAMPLES - 1) // INPUT_BLOCK_SAMPLES
    return min(requested_blocks, max(0, total_blocks - 1))


def _apply_startup_fade(samples: np.ndarray, fade_in_ms: float) -> np.ndarray:
    if fade_in_ms < 0.0:
        raise ValueError("fade_in_ms nao pode ser negativo.")
    fade_samples = int(round(fade_in_ms * INPUT_SAMPLE_RATE / 1000.0))
    if fade_samples <= 1 or samples.size == 0:
        return samples
    n = min(fade_samples, len(samples))
    envelope = np.linspace(0.0, 1.0, n, dtype=np.float32) ** 2
    samples[:n] *= envelope
    return samples


def process_samples_rnnoise(
    samples: np.ndarray,
    *,
    startup_preroll_ms: float = 0.0,
    fade_in_ms: float = 0.0,
) -> tuple[np.ndarray, list[dict[str, float | int | bool]]]:
    values = np.asarray(samples, dtype=np.float32).reshape(-1)
    if values.size == 0:
        raise ValueError("Nao e possivel processar um sinal vazio.")
    if not np.all(np.isfinite(values)):
        raise ValueError("O sinal de entrada contem amostras nao finitas.")

    outputs: list[np.ndarray] = []
    rows: list[dict[str, float | int | bool]] = []
    preroll_blocks = _startup_preroll_blocks(len(values), startup_preroll_ms)
    with RNNoiseRealtimeProcessor() as processor:
        for preroll_index in range(preroll_blocks):
            start = preroll_index * INPUT_BLOCK_SAMPLES
            source = values[start : start + INPUT_BLOCK_SAMPLES]
            padded = np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
            padded[: len(source)] = source
            processor.process_block(padded)

        for block_index, start in enumerate(
            range(0, len(values), INPUT_BLOCK_SAMPLES)
        ):
            source = values[start : start + INPUT_BLOCK_SAMPLES]
            padded = np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
            padded[: len(source)] = source
            started = time.perf_counter()
            output, diagnostics = processor.process_block(padded)
            elapsed_s = time.perf_counter() - started
            outputs.append(output[: len(source)].copy())
            rows.append(
                {
                    "block_index": block_index,
                    "block_samples": len(source),
                    "processing_ms": elapsed_s * 1000.0,
                    "rtf_block": elapsed_s / (INPUT_BLOCK_SAMPLES / INPUT_SAMPLE_RATE),
                    "block_duration_ms": BLOCK_MS,
                    "warming_up": bool(diagnostics["warming_up"]),
                    "speech_probable": bool(diagnostics["speech_probable"]),
                    "state_memory_bytes": int(diagnostics["state_memory_bytes"]),
                }
            )
    processed = np.concatenate(outputs).astype(np.float32)
    processed = _apply_startup_fade(processed, fade_in_ms)
    if len(processed) != len(values):
        raise RuntimeError("O RNNoise nao preservou o comprimento do arquivo.")
    return processed, rows


def process_wav(
    *,
    input_path: Path,
    output_path: Path,
    metrics_path: Path,
    overwrite: bool = False,
    startup_preroll_ms: float = 0.0,
    fade_in_ms: float = 0.0,
    command_args: Sequence[str] | None = None,
) -> dict[str, object]:
    resolved_input = input_path.resolve()
    resolved_output = output_path.resolve()
    resolved_metrics = metrics_path.resolve()
    if resolved_input in (resolved_output, resolved_metrics):
        raise ValueError("As saidas nao podem sobrescrever o WAV de entrada.")
    if resolved_output == resolved_metrics:
        raise ValueError("O WAV e o JSON de saida devem usar caminhos diferentes.")
    existing = [path for path in (resolved_output, resolved_metrics) if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Saida ja existe; use --overwrite para substituir: "
            + ", ".join(str(path) for path in existing)
        )

    samples, input_metadata = read_wav_for_processing(input_path)
    started = time.perf_counter()
    processed, rows = process_samples_rnnoise(
        samples,
        startup_preroll_ms=startup_preroll_ms,
        fade_in_ms=fade_in_ms,
    )
    total_elapsed_s = time.perf_counter() - started
    startup_preroll_blocks = _startup_preroll_blocks(
        len(samples),
        startup_preroll_ms,
    )
    write_report = write_pcm16(output_path, processed)
    duration_s = len(samples) / INPUT_SAMPLE_RATE
    timing = summarize_block_timings(rows)
    timing["processing_total_ms"] = total_elapsed_s * 1000.0
    timing["rtf_total"] = total_elapsed_s / duration_s

    library_path = default_library_path()
    metrics: dict[str, object] = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command_args": list(command_args or []),
        "input": {
            "path": str(resolved_input),
            "sha256": sha256_file(input_path),
            **asdict(input_metadata),
        },
        "output": {
            "path": str(resolved_output),
            "sha256": sha256_file(output_path),
            "sample_rate": INPUT_SAMPLE_RATE,
            "channels": 1,
            "dtype": "int16",
        },
        "processing": {
            "method": "rnnoise",
            "block_ms": BLOCK_MS,
            "block_samples": INPUT_BLOCK_SAMPLES,
            "processed_samples": len(processed),
            "length_preserved": len(processed) == len(samples),
            "normalization_applied": False,
            "startup_preroll_ms": startup_preroll_ms,
            "startup_preroll_blocks": startup_preroll_blocks,
            "startup_preroll_output_discarded": startup_preroll_blocks > 0,
            "fade_in_ms": fade_in_ms,
            "algorithmic_latency_ms": TOTAL_ALGORITHMIC_LATENCY_MS,
            "last_block_zero_padded": len(samples) % INPUT_BLOCK_SAMPLES != 0,
            **write_report,
        },
        "native_library": {
            "path": str(library_path.resolve()),
            "sha256": sha256_file(library_path),
        },
        "timing": timing,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "notes": (
            "Demonstracao pre-ponte: mede o RNNoise causal por blocos e nao inclui "
            "microfone virtual, driver, dispositivo ou latencia fisica ponta a ponta."
        ),
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return metrics


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Processa um WAV pelo RNNoise causal persistente."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--metrics-json",
        type=Path,
        help="Padrao: mesmo caminho da saida com extensao .json.",
    )
    parser.add_argument(
        "--startup-preroll-ms",
        type=float,
        default=0.0,
        help=(
            "Aquece o estado RNNoise com os primeiros milissegundos reais "
            "do arquivo e descarta essa saida antes do passe principal."
        ),
    )
    parser.add_argument(
        "--fade-in-ms",
        type=float,
        default=0.0,
        help="Aplica fade-in quadratico curto na saida final.",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    metrics_path = args.metrics_json or args.output.with_suffix(".json")
    command_args = list(argv) if argv is not None else sys.argv[1:]
    try:
        metrics = process_wav(
            input_path=args.input,
            output_path=args.output,
            metrics_path=metrics_path,
            overwrite=args.overwrite,
            startup_preroll_ms=args.startup_preroll_ms,
            fade_in_ms=args.fade_in_ms,
            command_args=command_args,
        )
    except (FileNotFoundError, FileExistsError, ValueError, OSError, RuntimeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    print(
        "RNNoise concluido: "
        f"{metrics['processing']['processed_samples']} amostras, "
        f"RTF {metrics['timing']['rtf_total']:.4f}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
