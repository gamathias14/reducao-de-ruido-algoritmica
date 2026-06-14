from __future__ import annotations

import argparse
import csv
import json
import math
import os
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from benchmark_audio.causal import CausalProcessorConfig, CausalSTFTProcessor
from benchmark_audio.denoise import (
    DenoiseConfig,
    process_method,
    write_wav,
)
from realtime_audio.block_metrics import summarize_block_timings
from realtime_audio.audio_continuity import analyze_blocks
from realtime_audio.ptc_pcm_bridge import (
    BridgePacedWriter,
    PTC_PCM_FRAMES_PER_BLOCK,
    PTC_PCM_SAMPLE_RATE,
    PtcPcmBridgeClient,
    WindowsBridgeBackend,
)
from realtime_audio.rnnoise_processor import (
    INPUT_BLOCK_SAMPLES as RNNOISE_INPUT_BLOCK_SAMPLES,
    INPUT_SAMPLE_RATE as RNNOISE_INPUT_SAMPLE_RATE,
    RNNoiseRealtimeProcessor,
    TOTAL_ALGORITHMIC_LATENCY_MS as RNNOISE_TOTAL_LATENCY_MS,
)


ROOT = Path(__file__).resolve().parents[1]
REALTIME_METHODS = (
    "bypass",
    "stft_subtraction",
    "stft_wiener",
    "wavelet_soft",
    "rnnoise",
)
NOISE_MODES = ("calibration", "adaptive", "rolling")
PC_DEMO_PRESETS = ("self-test", "input-only", "wired")
DIAGNOSTIC_SOURCE_CLASSES = ("gap", "noise", "active")


def build_diagnostic_id_block(
    block_index: int,
    block_size: int,
    sample_rate: int,
    *,
    seed: int = 3527,
) -> tuple[np.ndarray, str]:
    if block_index < 0:
        raise ValueError("Indice de bloco deve ser nao negativo.")
    if block_size <= 0 or sample_rate <= 0:
        raise ValueError("Tamanho de bloco e taxa devem ser positivos.")

    phase = block_index % 150
    if phase < 25 or phase >= 125:
        return np.zeros(block_size, dtype=np.float32), "gap"

    rng = np.random.default_rng(np.random.SeedSequence([seed, block_index]))
    marker = rng.choice(
        np.asarray([-1.0, 1.0], dtype=np.float32),
        size=block_size,
    )
    if phase < 75:
        return (0.035 * marker).astype(np.float32), "noise"

    absolute_samples = block_index * block_size + np.arange(block_size)
    time_s = absolute_samples.astype(np.float64) / sample_rate
    carrier = (
        0.070 * np.sin(2.0 * math.pi * 220.0 * time_s)
        + 0.040 * np.sin(2.0 * math.pi * 440.0 * time_s + 0.3)
        + 0.020 * np.sin(2.0 * math.pi * 880.0 * time_s + 0.7)
    )
    return (carrier + 0.020 * marker).astype(np.float32), "active"


class DiagnosticProgress:
    def __init__(self, path: str | Path | None, *, callback_write_interval: int = 25) -> None:
        self.path = Path(path) if path else None
        self.callback_write_interval = max(1, int(callback_write_interval))
        self._lock = threading.Lock()
        self._state: dict[str, object] = {
            "stage": "initialized",
            "callback_count": 0,
            "status_count": 0,
        }

    def mark(self, stage: str, **values: object) -> None:
        if self.path is None:
            return
        with self._lock:
            self._state.update(values)
            self._state["stage"] = stage
            self._state["updated_at"] = datetime.now().astimezone().isoformat()
            self._state["monotonic_s"] = time.perf_counter()
            self._write_locked()

    def callback(self, callback_s: float, *, has_status: bool) -> None:
        if self.path is None:
            return
        with self._lock:
            callback_count = int(self._state["callback_count"]) + 1
            status_count = int(self._state["status_count"]) + int(has_status)
            self._state.update(
                {
                    "stage": "stream_active",
                    "callback_count": callback_count,
                    "status_count": status_count,
                    "last_callback_monotonic_s": callback_s,
                    "updated_at": datetime.now().astimezone().isoformat(),
                    "monotonic_s": time.perf_counter(),
                }
            )
            if has_status or callback_count == 1 or callback_count % self.callback_write_interval == 0:
                self._write_locked()

    def _write_locked(self) -> None:
        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.path)


@dataclass(frozen=True)
class RealtimeConfig:
    sample_rate: int = 16_000
    block_ms: float = 20.0
    method: str = "bypass"
    noise_mode: str = "adaptive"
    calibration_ms: float = 250.0
    estimator_warmup_ms: float = 250.0
    estimator_history_ms: float = 500.0
    noise_quantile: float = 0.22
    energy_quantile: float = 0.20
    speech_threshold_db: float = 6.0
    low_energy_alpha: float = 0.30
    speech_alpha: float = 0.005
    n_fft: int = 512
    hop_length: int = 160
    spectral_alpha: float = 1.5
    spectral_floor: float = 0.02
    gain_smoothing: float = 0.0
    wiener_floor: float = 0.05
    wavelet: str = "db4"
    wavelet_level: int = 5
    wavelet_mode: str = "soft"

    @property
    def block_size(self) -> int:
        return max(1, int(round(self.sample_rate * self.block_ms / 1000.0)))

    @property
    def block_duration_s(self) -> float:
        return self.block_size / self.sample_rate

    @property
    def calibration_samples(self) -> int:
        if self.noise_mode != "calibration" or self.method not in {"stft_subtraction", "stft_wiener"}:
            return 0
        return max(0, int(round(self.sample_rate * self.calibration_ms / 1000.0)))

    def denoise_config(self) -> DenoiseConfig:
        return DenoiseConfig(
            sample_rate=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            noise_estimate_s=max(self.calibration_ms / 1000.0, self.block_duration_s),
            spectral_alpha=self.spectral_alpha,
            spectral_floor=self.spectral_floor,
            wiener_floor=self.wiener_floor,
            wavelet=self.wavelet,
            wavelet_level=self.wavelet_level,
            wavelet_mode=self.wavelet_mode,
        )

    def causal_config(self) -> CausalProcessorConfig:
        noise_mode = "adaptive" if self.noise_mode == "rolling" else self.noise_mode
        return CausalProcessorConfig(
            sample_rate=self.sample_rate,
            method=self.method,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            spectral_alpha=self.spectral_alpha,
            spectral_floor=self.spectral_floor,
            gain_smoothing=self.gain_smoothing,
            wiener_floor=self.wiener_floor,
            noise_mode=noise_mode,
            calibration_ms=self.calibration_ms,
            warmup_ms=self.estimator_warmup_ms,
            history_ms=self.estimator_history_ms,
            noise_quantile=self.noise_quantile,
            energy_quantile=self.energy_quantile,
            speech_threshold_db=self.speech_threshold_db,
            low_energy_alpha=self.low_energy_alpha,
            speech_alpha=self.speech_alpha,
        )


class RealtimeBlockProcessor:
    def __init__(self, config: RealtimeConfig) -> None:
        if config.method not in REALTIME_METHODS:
            raise ValueError(f"Metodo invalido: {config.method}")
        if config.noise_mode not in NOISE_MODES:
            raise ValueError(f"Modo de ruido invalido: {config.noise_mode}")
        if config.hop_length >= config.n_fft:
            raise ValueError("hop_length deve ser menor que n_fft.")
        if config.method == "rnnoise" and (
            config.sample_rate != RNNOISE_INPUT_SAMPLE_RATE
            or config.block_size != RNNOISE_INPUT_BLOCK_SAMPLES
        ):
            raise ValueError(
                "RNNoise realtime exige exatamente 16 kHz e blocos de 20 ms."
            )

        self.config = config
        self.denoise_config = config.denoise_config()
        self.context_samples = max(config.n_fft, config.block_size)
        self.history = np.zeros(self.context_samples, dtype=np.float32)
        self.causal_processor = (
            CausalSTFTProcessor(config.causal_config())
            if config.method in {"bypass", "stft_subtraction", "stft_wiener"}
            else None
        )
        self.rnnoise_processor = (
            RNNoiseRealtimeProcessor() if config.method == "rnnoise" else None
        )
        self.block_index = 0

    @property
    def calibration_active(self) -> bool:
        return bool(
            self.causal_processor is not None
            and self.config.noise_mode == "calibration"
            and not self.causal_processor.noise_estimator.ready
        )

    def reset(self) -> None:
        self.history = np.zeros(self.context_samples, dtype=np.float32)
        self.block_index = 0
        if self.causal_processor is not None:
            self.causal_processor.reset()
        if self.rnnoise_processor is not None:
            self.rnnoise_processor.reset()

    def close(self) -> None:
        if self.rnnoise_processor is not None:
            self.rnnoise_processor.close()

    def process_block(self, block: np.ndarray) -> tuple[np.ndarray, dict[str, float | int | bool]]:
        block = np.asarray(block, dtype=np.float32).reshape(-1)
        if block.size == 0:
            raise ValueError("Bloco vazio recebido.")

        started = time.perf_counter()
        input_peak = float(np.max(np.abs(block))) if block.size else 0.0
        if self.rnnoise_processor is not None:
            output, diagnostics = self.rnnoise_processor.process_block(block)
        elif self.causal_processor is not None:
            output, diagnostics = self.causal_processor.process_block(block)
        else:
            window = np.concatenate([self.history, block]).astype(np.float32)
            output_window, _ = process_method(self.config.method, window, self.denoise_config)
            output = output_window[-len(block) :].astype(np.float32)
            self.history = window[-self.context_samples :].astype(np.float32)
            diagnostics = {
                "warming_up": False,
                "estimator_ready": True,
                "speech_probable": False,
                "low_energy": False,
                "estimator_updates": 0,
                "noise_power_mean": 0.0,
                "state_memory_bytes": self.history.nbytes,
            }

        elapsed_s = time.perf_counter() - started
        output = np.asarray(output, dtype=np.float32).reshape(-1)
        np.nan_to_num(
            output,
            copy=False,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        np.clip(output, -1.0, 1.0, out=output)
        output_peak = float(np.max(np.abs(output))) if output.size else 0.0
        self.block_index += 1

        timing = {
            "block_index": self.block_index,
            "processing_ms": elapsed_s * 1000.0,
            "rtf_block": elapsed_s / self.config.block_duration_s,
            "input_peak": input_peak,
            "output_peak": output_peak,
            "calibrating": bool(
                diagnostics["warming_up"] and self.config.noise_mode == "calibration"
            ),
            "warming_up": bool(diagnostics["warming_up"]),
            "estimator_ready": bool(diagnostics["estimator_ready"]),
            "speech_probable": bool(diagnostics["speech_probable"]),
            "low_energy": bool(diagnostics["low_energy"]),
            "estimator_updates": int(diagnostics["estimator_updates"]),
            "noise_power_mean": float(diagnostics["noise_power_mean"]),
            "state_memory_bytes": int(diagnostics["state_memory_bytes"]),
        }
        return output, timing

def import_sounddevice() -> Any:
    try:
        import sounddevice as sd
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "A biblioteca sounddevice nao esta instalada. Rode: python -m pip install -r requirements.txt"
        ) from exc
    return sd


def parse_device(value: str | None) -> int | str | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return value


def summarize_timings(timings: list[dict[str, float | int | bool]]) -> dict[str, float | int]:
    return summarize_block_timings(timings)


def estimated_algorithmic_latency_ms(config: RealtimeConfig) -> float:
    if config.method == "bypass":
        return 0.0
    if config.method.startswith("stft"):
        return 1000.0 * config.n_fft / config.sample_rate
    if config.method == "rnnoise":
        return RNNOISE_TOTAL_LATENCY_MS
    return 1000.0 * config.block_size / config.sample_rate


def write_outputs(
    *,
    config: RealtimeConfig,
    timings: list[dict[str, float | int | bool]],
    input_blocks: list[np.ndarray],
    output_blocks: list[np.ndarray],
    status_counts: Counter[str],
    output_dir: Path,
    save_audio: bool,
    stream_latency_s: tuple[float, float] | None,
    label: str,
    extra_metrics: dict[str, object] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{label}_{config.method}_{config.block_ms:g}ms_{timestamp}"

    summary = summarize_timings(timings)
    stream_latency_ms = None
    if stream_latency_s is not None:
        stream_latency_ms = {
            "input_ms": stream_latency_s[0] * 1000.0,
            "output_ms": stream_latency_s[1] * 1000.0,
            "io_total_ms": (stream_latency_s[0] + stream_latency_s[1]) * 1000.0,
        }

    base_latency_ms = (
        estimated_algorithmic_latency_ms(config)
        + (stream_latency_ms["io_total_ms"] if stream_latency_ms is not None else 0.0)
    )
    bridge_latency_ms = 0.0
    if extra_metrics is not None:
        bridge_latency_ms = float(
            extra_metrics.get("bridge_buffer_latency_estimated_ms", 0.0)
        )

    metrics = {
        "label": label,
        "config": asdict(config),
        "summary": summary,
        "status_counts": dict(status_counts),
        "algorithmic_latency_estimated_ms": estimated_algorithmic_latency_ms(config),
        "stream_latency_ms": stream_latency_ms,
        "bridge_buffer_latency_estimated_ms": bridge_latency_ms,
        "total_latency_estimated_ms": base_latency_ms + bridge_latency_ms,
        "latency_estimate_scope": (
            "algoritmo + latencia reportada pelo stream + p95 de residencia "
            "na fila de usuario + p95 de profundidade da fila do driver"
        ),
        "notes": "Audio salvo localmente apenas como artefato curto de teste, nao como base publica do projeto.",
    }
    if extra_metrics is not None:
        metrics["bridge"] = extra_metrics
    if input_blocks:
        block_indices = [int(item["block_index"]) for item in timings]
        callback_times = [
            float(item["callback_monotonic_s"])
            for item in timings
            if "callback_monotonic_s" in item
        ]
        status_events = [
            bool(item.get("input_status", False))
            for item in timings
        ]
        continuity_kwargs: dict[str, object] = {
            "block_indices": block_indices,
            "status_events": status_events,
        }
        if len(callback_times) == len(input_blocks):
            continuity_kwargs["callback_times_s"] = callback_times
            continuity_kwargs["expected_interval_s"] = config.block_duration_s
        metrics["continuity"] = {
            "input": analyze_blocks(input_blocks, **continuity_kwargs),
            "pre_bridge_output": analyze_blocks(
                output_blocks,
                block_indices=block_indices,
            ),
        }

    paths: dict[str, str] = {}
    metrics_path = output_dir / f"{stem}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["metrics_json"] = str(metrics_path)

    csv_path = output_dir / f"{stem}_blocks.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "block_index",
            "source_class",
            "processing_ms",
            "rtf_block",
            "input_peak",
            "output_peak",
            "calibrating",
            "warming_up",
            "estimator_ready",
            "speech_probable",
            "low_energy",
            "estimator_updates",
            "noise_power_mean",
            "state_memory_bytes",
            "callback_monotonic_s",
            "callback_interval_ms",
            "input_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(timings)
    paths["blocks_csv"] = str(csv_path)

    if save_audio and input_blocks and output_blocks:
        input_audio = np.concatenate(input_blocks).astype(np.float32)
        output_audio = np.concatenate(output_blocks).astype(np.float32)
        input_path = output_dir / f"{stem}_input.wav"
        output_path = output_dir / f"{stem}_output.wav"
        write_wav(input_path, input_audio, config.sample_rate)
        write_wav(output_path, output_audio, config.sample_rate)
        paths["input_wav"] = str(input_path)
        paths["output_wav"] = str(output_path)

    return paths


def normalize_stream_latency(latency: Any) -> tuple[float, float]:
    if isinstance(latency, (tuple, list)) and len(latency) == 2:
        return float(latency[0]), float(latency[1])
    value = float(latency)
    return value, value


def run_self_test(args: argparse.Namespace, config: RealtimeConfig) -> dict[str, str]:
    processor = RealtimeBlockProcessor(config)
    rng = np.random.default_rng(3527)
    n_blocks = max(1, int(math.ceil(args.duration / config.block_duration_s)))
    input_blocks: list[np.ndarray] = []
    output_blocks: list[np.ndarray] = []
    timings: list[dict[str, float | int | bool]] = []

    try:
        for block_idx in range(n_blocks):
            t0 = block_idx * config.block_size / config.sample_rate
            t = t0 + np.arange(config.block_size, dtype=np.float32) / config.sample_rate
            noise = rng.normal(scale=0.05, size=config.block_size).astype(np.float32)
            if block_idx * config.block_size < config.calibration_samples:
                block = noise
            else:
                speech = 0.25 * np.sin(2 * np.pi * 440 * t)
                block = (speech + noise).astype(np.float32)
            output, timing = processor.process_block(block)
            input_blocks.append(block)
            output_blocks.append(output.copy())
            timings.append(timing)
    finally:
        processor.close()

    return write_outputs(
        config=config,
        timings=timings,
        input_blocks=input_blocks,
        output_blocks=output_blocks,
        status_counts=Counter(),
        output_dir=Path(args.output_dir),
        save_audio=not args.no_save,
        stream_latency_s=None,
        label="synthetic",
    )


def run_realtime(args: argparse.Namespace, config: RealtimeConfig) -> dict[str, str]:
    sd = import_sounddevice()
    processor = RealtimeBlockProcessor(config)
    input_blocks: list[np.ndarray] = []
    output_blocks: list[np.ndarray] = []
    timings: list[dict[str, float | int | bool]] = []
    status_counts: Counter[str] = Counter()

    def callback(indata: np.ndarray, outdata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        if status:
            status_counts[str(status)] += 1
        block = np.asarray(indata[:, 0], dtype=np.float32).copy()
        output, timing = processor.process_block(block)
        if len(output) != frames:
            output = np.resize(output, frames).astype(np.float32)
        outdata[:, 0] = output
        timings.append(timing)
        if not args.no_save:
            input_blocks.append(block)
            output_blocks.append(output.copy())

    input_device = parse_device(args.input_device)
    output_device = parse_device(args.output_device)
    try:
        with sd.Stream(
            samplerate=config.sample_rate,
            blocksize=config.block_size,
            channels=1,
            dtype="float32",
            device=(input_device, output_device),
            callback=callback,
        ) as stream:
            time.sleep(args.duration)
            stream_latency_s = normalize_stream_latency(stream.latency)
    finally:
        processor.close()

    return write_outputs(
        config=config,
        timings=timings,
        input_blocks=input_blocks,
        output_blocks=output_blocks,
        status_counts=status_counts,
        output_dir=Path(args.output_dir),
        save_audio=not args.no_save,
        stream_latency_s=stream_latency_s,
        label="windows",
    )


def run_input_only(args: argparse.Namespace, config: RealtimeConfig) -> dict[str, str]:
    progress = DiagnosticProgress(args.progress_file)
    progress.mark("before_sounddevice_import")
    sd = import_sounddevice()
    progress.mark("sounddevice_imported")
    processor = RealtimeBlockProcessor(config)
    input_blocks: list[np.ndarray] = []
    output_blocks: list[np.ndarray] = []
    timings: list[dict[str, float | int | bool]] = []
    status_counts: Counter[str] = Counter()
    last_callback_s: float | None = None

    def callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        nonlocal last_callback_s
        callback_s = time.perf_counter()
        if status:
            status_counts[str(status)] += 1
        if args.diagnostic_block_id_source:
            block, source_class = build_diagnostic_id_block(
                processor.block_index,
                config.block_size,
                config.sample_rate,
                seed=args.diagnostic_block_id_seed,
            )
        else:
            block = np.asarray(indata[:, 0], dtype=np.float32).copy()
            source_class = "captured"
        output, timing = processor.process_block(block)
        timing["source_class"] = source_class
        timing["callback_monotonic_s"] = callback_s
        timing["callback_interval_ms"] = (
            0.0 if last_callback_s is None else 1000.0 * (callback_s - last_callback_s)
        )
        timing["input_status"] = bool(status)
        last_callback_s = callback_s
        timings.append(timing)
        progress.callback(callback_s, has_status=bool(status))
        if not args.no_save:
            input_blocks.append(block)
            output_blocks.append(output.copy())

    input_device = parse_device(args.input_device)
    progress.mark("before_stream_create", input_device=input_device)
    try:
        with sd.InputStream(
            samplerate=config.sample_rate,
            blocksize=config.block_size,
            channels=1,
            dtype="float32",
            device=input_device,
            callback=callback,
        ) as stream:
            progress.mark("stream_entered", input_latency_s=float(stream.latency))
            time.sleep(args.duration)
            input_latency_s = float(stream.latency)
            progress.mark(
                "duration_complete",
                duration_s=args.duration,
                input_latency_s=input_latency_s,
            )
    finally:
        processor.close()
    progress.mark("stream_closed")

    paths = write_outputs(
        config=config,
        timings=timings,
        input_blocks=input_blocks,
        output_blocks=output_blocks,
        status_counts=status_counts,
        output_dir=Path(args.output_dir),
        save_audio=not args.no_save,
        stream_latency_s=(input_latency_s, 0.0),
        label="windows_input_only",
    )
    progress.mark("outputs_written", paths=paths)
    return paths


def run_virtual_mic(args: argparse.Namespace, config: RealtimeConfig) -> dict[str, str]:
    if config.sample_rate != PTC_PCM_SAMPLE_RATE or config.block_size != PTC_PCM_FRAMES_PER_BLOCK:
        raise ValueError("O virtual mic exige exatamente 16 kHz e blocos de 20 ms.")

    progress = DiagnosticProgress(args.progress_file)
    progress.mark("before_sounddevice_import")
    sd = import_sounddevice()
    progress.mark("sounddevice_imported")
    processor = RealtimeBlockProcessor(config)
    input_blocks: list[np.ndarray] = []
    output_blocks: list[np.ndarray] = []
    timings: list[dict[str, float | int | bool]] = []
    status_counts: Counter[str] = Counter()
    last_callback_s: float | None = None
    backend = WindowsBridgeBackend(device_path=args.bridge_path)
    writer = BridgePacedWriter(
        PtcPcmBridgeClient(backend),
        target_driver_depth=args.bridge_target_depth,
        user_queue_blocks=args.bridge_user_queue,
        poll_interval_s=args.bridge_poll_interval_ms / 1000.0,
        record_events=args.diagnostic_trace,
        drop_policy=args.bridge_drop_policy,
    )

    def callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        nonlocal last_callback_s
        callback_s = time.perf_counter()
        if status:
            status_counts[str(status)] += 1
        if args.diagnostic_block_id_source:
            block, source_class = build_diagnostic_id_block(
                processor.block_index,
                config.block_size,
                config.sample_rate,
                seed=args.diagnostic_block_id_seed,
            )
        else:
            block = np.asarray(indata[:, 0], dtype=np.float32).copy()
            source_class = "captured"
        output, timing = processor.process_block(block)
        timing["source_class"] = source_class
        timing["callback_monotonic_s"] = callback_s
        timing["callback_interval_ms"] = (
            0.0 if last_callback_s is None else 1000.0 * (callback_s - last_callback_s)
        )
        timing["input_status"] = bool(status)
        last_callback_s = callback_s
        timings.append(timing)
        progress.callback(callback_s, has_status=bool(status))
        writer.submit(output, source_block_index=int(timing["block_index"]))
        if not args.no_save:
            input_blocks.append(block)
            output_blocks.append(output.copy())

    input_device = parse_device(args.input_device)
    progress.mark("before_bridge_start", input_device=input_device)
    writer_started = False
    bridge_metrics: dict[str, object]
    try:
        writer.start()
        writer_started = True
        progress.mark("bridge_started")
        progress.mark("before_stream_create")
        with sd.InputStream(
            samplerate=config.sample_rate,
            blocksize=config.block_size,
            channels=1,
            dtype="float32",
            device=input_device,
            callback=callback,
        ) as stream:
            progress.mark("stream_entered", input_latency_s=float(stream.latency))
            time.sleep(args.duration)
            input_latency_s = float(stream.latency)
            progress.mark(
                "duration_complete",
                duration_s=args.duration,
                input_latency_s=input_latency_s,
            )
        progress.mark("stream_closed")
    finally:
        processor.close()
        bridge_metrics = writer.stop() if writer_started else {}
        progress.mark("bridge_stopped", bridge_metrics=bridge_metrics)

    paths = write_outputs(
        config=config,
        timings=timings,
        input_blocks=input_blocks,
        output_blocks=output_blocks,
        status_counts=status_counts,
        output_dir=Path(args.output_dir),
        save_audio=not args.no_save,
        stream_latency_s=(input_latency_s, 0.0),
        label="windows_virtual_mic",
        extra_metrics=bridge_metrics,
    )
    progress.mark("outputs_written", paths=paths)
    return paths


def build_config(args: argparse.Namespace) -> RealtimeConfig:
    spectral_alpha = args.aggressiveness if args.aggressiveness is not None else args.spectral_alpha
    return RealtimeConfig(
        sample_rate=args.sample_rate,
        block_ms=args.block_ms,
        method=args.method,
        noise_mode=args.noise_mode,
        calibration_ms=args.calibration_ms,
        estimator_warmup_ms=args.estimator_warmup_ms,
        estimator_history_ms=args.estimator_history_ms,
        noise_quantile=args.noise_quantile,
        energy_quantile=args.energy_quantile,
        speech_threshold_db=args.speech_threshold_db,
        low_energy_alpha=args.low_energy_alpha,
        speech_alpha=args.speech_alpha,
        n_fft=args.n_fft,
        hop_length=args.hop_length,
        spectral_alpha=spectral_alpha,
        spectral_floor=args.spectral_floor,
        gain_smoothing=args.gain_smoothing,
        wiener_floor=args.wiener_floor,
        wavelet=args.wavelet,
        wavelet_level=args.wavelet_level,
        wavelet_mode=args.wavelet_mode,
    )


def apply_pc_demo_preset(args: argparse.Namespace) -> argparse.Namespace:
    if args.pc_demo is None:
        return args

    args.method = "stft_subtraction"
    args.noise_mode = "adaptive"
    args.block_ms = 20.0
    args.no_save = True

    if args.pc_demo == "self-test":
        args.self_test = True
        args.input_only = False
        args.input_device = None
        args.output_device = None
        args.output_dir = str(ROOT / "resultados" / "windows_realtime_longrun")
    elif args.pc_demo == "input-only":
        args.self_test = False
        args.input_only = True
        args.input_device = "2"
        args.output_device = None
        args.output_dir = str(ROOT / "resultados" / "windows_realtime_longrun")
    elif args.pc_demo == "wired":
        args.self_test = False
        args.input_only = False
        args.input_device = "2"
        args.output_device = "8"
        args.output_dir = str(ROOT / "resultados" / "windows_realtime_wired")
    else:
        raise ValueError(f"Preset PC invalido: {args.pc_demo}")

    return args


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prototipo Windows de reducao de ruido em tempo real.")
    parser.add_argument(
        "--pc-demo",
        choices=PC_DEMO_PRESETS,
        help=(
            "Aplica presets oficiais da plataforma PC: self-test, input-only ou "
            "wired. Define metodo STFT adaptativo, bloco 20 ms, pasta de saida, "
            "dispositivos validados quando aplicavel e --no-save."
        ),
    )
    parser.add_argument("--list-devices", action="store_true", help="Lista dispositivos de audio via sounddevice.")
    parser.add_argument("--self-test", action="store_true", help="Roda processamento sintetico por blocos sem audio fisico.")
    parser.add_argument("--duration", type=float, default=10.0, help="Duracao do teste em segundos.")
    parser.add_argument("--sample-rate", type=int, default=16_000, help="Taxa de amostragem.")
    parser.add_argument("--block-ms", type=float, default=20.0, help="Tamanho do bloco em milissegundos.")
    parser.add_argument("--method", choices=REALTIME_METHODS, default="bypass", help="Metodo de processamento.")
    parser.add_argument("--noise-mode", choices=NOISE_MODES, default="adaptive", help="Estimativa causal de ruido STFT.")
    parser.add_argument("--calibration-ms", type=float, default=250.0, help="Duracao da calibracao inicial.")
    parser.add_argument("--estimator-warmup-ms", type=float, default=250.0, help="Aquecimento causal antes de aplicar supressao.")
    parser.add_argument("--estimator-history-ms", type=float, default=500.0, help="Janela passada do quantil espectral.")
    parser.add_argument("--noise-quantile", type=float, default=0.22, help="Quantil causal por bin.")
    parser.add_argument("--energy-quantile", type=float, default=0.20, help="Quantil causal da energia de fundo.")
    parser.add_argument("--speech-threshold-db", type=float, default=6.0, help="Margem sobre o piso para fala provavel.")
    parser.add_argument("--low-energy-alpha", type=float, default=0.30, help="EMA em quadros de baixa energia.")
    parser.add_argument("--speech-alpha", type=float, default=0.005, help="EMA lenta durante fala provavel.")
    parser.add_argument("--input-device", help="Indice ou nome do dispositivo de entrada.")
    parser.add_argument("--output-device", help="Indice ou nome do dispositivo de saida.")
    parser.add_argument("--input-only", action="store_true", help="Captura e processa sem enviar audio para saida.")
    parser.add_argument(
        "--virtual-mic",
        action="store_true",
        help="Envia a saida processada para a ponte PTC PCM do SYSVAD.",
    )
    parser.add_argument(
        "--bridge-path",
        help="Caminho explicito da interface PTC PCM; por padrao, descobre pelo GUID.",
    )
    parser.add_argument(
        "--bridge-target-depth",
        type=int,
        default=2,
        help="Profundidade maxima desejada na fila do driver antes de aguardar.",
    )
    parser.add_argument(
        "--bridge-user-queue",
        type=int,
        default=4,
        help="Capacidade da fila de usuario; em lotacao, descarta o bloco mais antigo.",
    )
    parser.add_argument(
        "--bridge-poll-interval-ms",
        type=float,
        default=2.0,
        help="Intervalo de polling da ponte em milissegundos.",
    )
    parser.add_argument(
        "--bridge-drop-policy",
        choices=("oldest", "newest"),
        default="oldest",
        help="Politica da fila local quando cheia; oldest preserva o padrao.",
    )
    parser.add_argument(
        "--diagnostic-trace",
        action="store_true",
        help="Registra eventos por bloco da fila local e da ponte.",
    )
    parser.add_argument(
        "--diagnostic-block-id-source",
        action="store_true",
        help=(
            "Substitui a amostra capturada por blocos deterministas identificaveis; "
            "mantem apenas a cadencia do callback MME."
        ),
    )
    parser.add_argument(
        "--diagnostic-block-id-seed",
        type=int,
        default=3527,
        help="Semente da fonte diagnostica identificavel por bloco.",
    )
    parser.add_argument(
        "--progress-file",
        help="Arquivo JSON atomico com o ultimo estagio e contadores do stream.",
    )
    parser.add_argument("--output-dir", default=str(ROOT / "resultados" / "realtime"), help="Pasta de logs e WAVs.")
    parser.add_argument("--no-save", action="store_true", help="Nao salva WAVs de entrada/saida.")
    parser.add_argument("--n-fft", type=int, default=512, help="Tamanho da FFT para STFT.")
    parser.add_argument("--hop-length", type=int, default=160, help="Salto da STFT em amostras.")
    parser.add_argument("--spectral-alpha", type=float, default=1.5, help="Alpha da subtracao espectral.")
    parser.add_argument("--aggressiveness", type=float, help="Atalho para ajustar o alpha da subtracao espectral.")
    parser.add_argument("--spectral-floor", type=float, default=0.02, help="Piso da subtracao espectral.")
    parser.add_argument(
        "--gain-smoothing",
        type=float,
        default=0.0,
        help="EMA causal do ganho espectral em [0, 1); zero preserva o baseline.",
    )
    parser.add_argument("--wiener-floor", type=float, default=0.05, help="Piso do ganho Wiener.")
    parser.add_argument("--wavelet", default="db4", help="Familia Wavelet.")
    parser.add_argument("--wavelet-level", type=int, default=5, help="Nivel Wavelet.")
    parser.add_argument("--wavelet-mode", choices=("soft", "hard"), default="soft", help="Modo de limiarizacao.")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.list_devices:
        sd = import_sounddevice()
        print(sd.query_devices())
        return

    args = apply_pc_demo_preset(args)
    config = build_config(args)
    if args.self_test:
        paths = run_self_test(args, config)
    elif args.virtual_mic:
        paths = run_virtual_mic(args, config)
    elif args.input_only:
        paths = run_input_only(args, config)
    else:
        paths = run_realtime(args, config)

    summary_path = paths.get("metrics_json", "")
    print(f"Teste concluido. Metricas: {summary_path}")


if __name__ == "__main__":
    main()
