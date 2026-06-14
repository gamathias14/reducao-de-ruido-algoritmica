from __future__ import annotations

import hashlib
import importlib.util
import math
import os
import re
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd
import psutil

from .causal import CausalProcessorConfig
from .denoise import resample_audio, si_sdr, snr_db
from .omlsa_imcra import OMLSAIMCRAConfig, OMLSAIMCRAProcessor
from .run_causal_estimator import process_causal
from .run_checkpoint46r_stft import perceptual_metrics
from .run_refinement import Condition


CANONICAL_SAMPLE_RATE = 16_000
BASELINE_SYSTEM_ID = "baseline_stft"


@dataclass(frozen=True)
class AdapterMetadata:
    system_id: str
    display_name: str
    implementation: str
    version: str
    license_spdx: str
    native_sample_rate: int
    api_frame_samples: int | None
    analysis_window_samples: int | None
    analysis_hop_samples: int | None
    lookahead_samples: int | None
    algorithmic_latency_ms: float | None
    causal: bool
    backend: str
    source_url: str
    source_revision: str
    available: bool = True
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdapterResult:
    audio: np.ndarray
    processing_seconds: float
    state_memory_bytes: int | None = None
    peak_rss_bytes: int | None = None
    diagnostics: dict[str, object] = field(default_factory=dict)


class DenoiserAdapter(Protocol):
    @property
    def metadata(self) -> AdapterMetadata:
        ...

    def process(self, noisy: np.ndarray, sample_rate: int) -> AdapterResult:
        ...


class FrozenBaselineAdapter:
    def __init__(self) -> None:
        self.config = CausalProcessorConfig(
            sample_rate=CANONICAL_SAMPLE_RATE,
            method="stft_subtraction",
            n_fft=512,
            hop_length=160,
            spectral_alpha=1.5,
            spectral_floor=0.02,
            gain_smoothing=0.0,
            noise_mode="adaptive",
            warmup_ms=250.0,
            history_ms=500.0,
            noise_quantile=0.22,
            energy_quantile=0.20,
            speech_threshold_db=6.0,
            low_energy_alpha=0.30,
            speech_alpha=0.005,
        )
        self._metadata = AdapterMetadata(
            system_id=BASELINE_SYSTEM_ID,
            display_name="Baseline STFT causal congelado",
            implementation="benchmark_audio.causal.CausalSTFTProcessor",
            version="checkpoint46r-e0-s02",
            license_spdx="Project-local",
            native_sample_rate=CANONICAL_SAMPLE_RATE,
            api_frame_samples=320,
            analysis_window_samples=512,
            analysis_hop_samples=160,
            lookahead_samples=0,
            algorithmic_latency_ms=32.0,
            causal=True,
            backend="python-in-process",
            source_url="local://benchmark_audio/causal.py",
            source_revision="working-tree-checkpoint46r",
            notes=(
                "Processamento em blocos externos de 20 ms.",
                "STFT 512/160 e estimador adaptativo q=0.22/EMA=0.30.",
            ),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._metadata

    def process(self, noisy: np.ndarray, sample_rate: int) -> AdapterResult:
        if sample_rate != self.config.sample_rate:
            raise ValueError(
                f"Baseline exige {self.config.sample_rate} Hz, recebeu {sample_rate} Hz."
            )
        audio, timing = process_causal(noisy, self.config)
        return AdapterResult(
            audio=audio,
            processing_seconds=float(timing["processing_ms"]) / 1_000.0,
            state_memory_bytes=int(timing["state_memory_bytes"]),
            diagnostics=timing,
        )


class OMLSAIMCRAAdapter:
    def __init__(self) -> None:
        self.config = OMLSAIMCRAConfig()
        self.processor = OMLSAIMCRAProcessor(self.config)
        self._metadata = AdapterMetadata(
            system_id="omlsa_imcra",
            display_name="OM-LSA + IMCRA",
            implementation="benchmark_audio.omlsa_imcra.OMLSAIMCRAProcessor",
            version="cohen-2001-2003-v1",
            license_spdx="Project-local",
            native_sample_rate=self.config.sample_rate,
            api_frame_samples=self.config.hop_length,
            analysis_window_samples=self.config.n_fft,
            analysis_hop_samples=self.config.hop_length,
            lookahead_samples=0,
            algorithmic_latency_ms=self.config.algorithmic_latency_ms,
            causal=True,
            backend="python-in-process",
            source_url=(
                "https://israelcohen.com/wp-content/uploads/2018/05/"
                "SAP_Sep2003.pdf"
            ),
            source_revision="Cohen-2001-OMLSA; Cohen-2003-IMCRA",
            notes=(
                "Parametros da Tabela I do IMCRA para 16 kHz.",
                "Hamming 512/128; piso OM-LSA de -25 dB.",
                "Atualizacao espectral sequencial, sem acesso a quadros futuros.",
            ),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._metadata

    def process(self, noisy: np.ndarray, sample_rate: int) -> AdapterResult:
        if sample_rate != self.config.sample_rate:
            raise ValueError(
                f"OM-LSA/IMCRA exige {self.config.sample_rate} Hz, "
                f"recebeu {sample_rate} Hz."
            )
        started = time.perf_counter()
        audio, diagnostics = self.processor.process(noisy)
        elapsed = time.perf_counter() - started
        return AdapterResult(
            audio=audio,
            processing_seconds=elapsed,
            state_memory_bytes=int(diagnostics["state_memory_bytes"]),
            diagnostics=diagnostics,
        )


class RNNoiseAdapter:
    def __init__(self, executable: Path | None = None) -> None:
        configured = os.environ.get("PTC3527_RNNOISE_EXE")
        self.executable = executable or (
            Path(configured)
            if configured
            else Path.home()
            / ".cache"
            / "ptc3527-benchmark"
            / "bin"
            / "ptc3527-rnnoise-v0.2.exe"
        )
        self._metadata = AdapterMetadata(
            system_id="rnnoise",
            display_name="RNNoise 0.2",
            implementation="xiph/rnnoise C API via ptc3527 native adapter",
            version="0.2",
            license_spdx="BSD-3-Clause",
            native_sample_rate=48_000,
            api_frame_samples=480,
            analysis_window_samples=960,
            analysis_hop_samples=480,
            lookahead_samples=960,
            algorithmic_latency_ms=20.0,
            causal=True,
            backend="native-subprocess",
            source_url="https://github.com/xiph/rnnoise",
            source_revision="904a876dce1f9ab8860c0a5000ed151f9f6eef58",
            available=self.executable.is_file(),
            notes=(
                "Modelo oficial 0b50c45.",
                "SHA-256 do arquivo do modelo: "
                "4AC81C5C0884EC4BD5907026AAAE16209B7B76CD9D7F71AF582094A2F98F4B43.",
                "Exemplo oficial descarta um quadro; impulso mediu outro quadro.",
                "Metricas removem o atraso residual; latencia total mantida.",
            ),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._metadata

    def process(self, noisy: np.ndarray, sample_rate: int) -> AdapterResult:
        if sample_rate != self.metadata.native_sample_rate:
            raise ValueError(
                f"RNNoise exige {self.metadata.native_sample_rate} Hz, "
                f"recebeu {sample_rate} Hz."
            )
        if not self.executable.is_file():
            raise FileNotFoundError(
                f"Adaptador RNNoise nao compilado: {self.executable}"
            )
        values = np.asarray(noisy, dtype="<f4").reshape(-1)
        process = subprocess.Popen(
            [str(self.executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        peak_rss = [0]
        stop = threading.Event()
        try:
            peak_rss[0] = int(psutil.Process(process.pid).memory_info().rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        def monitor() -> None:
            try:
                child = psutil.Process(process.pid)
                while not stop.wait(0.002):
                    peak_rss[0] = max(
                        peak_rss[0],
                        int(child.memory_info().rss),
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        started = time.perf_counter()
        stdout, stderr = process.communicate(values.tobytes(order="C"))
        elapsed = time.perf_counter() - started
        stop.set()
        thread.join(timeout=1.0)
        if process.returncode != 0:
            raise RuntimeError(
                f"RNNoise falhou ({process.returncode}): "
                f"{stderr.decode('utf-8', errors='replace')}"
            )
        output = np.frombuffer(stdout, dtype="<f4").copy()
        residual_delay = self.metadata.api_frame_samples or 0
        if residual_delay:
            output = np.pad(output[residual_delay:], (0, residual_delay))
        if len(output) < len(values):
            output = np.pad(output, (0, len(values) - len(output)))
        output = output[: len(values)].astype(np.float32)
        diagnostics_text = stderr.decode("utf-8", errors="replace")
        state_match = re.search(r"state_size=(\d+)", diagnostics_text)
        frame_match = re.search(r"frame_size=(\d+)", diagnostics_text)
        state_size = int(state_match.group(1)) if state_match else None
        return AdapterResult(
            audio=output,
            processing_seconds=elapsed,
            state_memory_bytes=state_size,
            peak_rss_bytes=peak_rss[0] or None,
            diagnostics={
                "frame_size": (
                    int(frame_match.group(1)) if frame_match else None
                ),
                "alignment_trim_samples": residual_delay,
                "native_stderr": diagnostics_text.strip(),
            },
        )


class WebRTCAPMNSAdapter:
    def __init__(self, executable: Path | None = None) -> None:
        configured = os.environ.get("PTC3527_WEBRTC_APM_EXE")
        self.executable = executable or (
            Path(configured)
            if configured
            else Path.home()
            / ".cache"
            / "ptc3527-benchmark"
            / "bin"
            / "ptc3527-webrtc-apm-ns.exe"
        )
        self._metadata = AdapterMetadata(
            system_id="webrtc_apm_ns",
            display_name="WebRTC APM Noise Suppression",
            implementation=(
                "WebRTC BuiltinAudioProcessingBuilder via ptc3527 native adapter"
            ),
            version="main-2026-06-13-default-moderate",
            license_spdx="BSD-3-Clause",
            native_sample_rate=16_000,
            api_frame_samples=160,
            analysis_window_samples=256,
            analysis_hop_samples=160,
            lookahead_samples=96,
            algorithmic_latency_ms=6.0,
            causal=True,
            backend="native-subprocess",
            source_url="https://webrtc.googlesource.com/src/",
            source_revision="eb79ac6e330baa0a6d26c53d522f9ed57495edb7",
            available=self.executable.is_file(),
            notes=(
                "Somente NS habilitado no nivel padrao moderate.",
                "AEC, AGC e HPF permanecem desligados.",
                "API float mono em quadros de 10 ms a 16 kHz.",
                "FFT 256/160; impulso mediu atraso constante de 96 amostras.",
                "Metricas removem o atraso; latencia real permanece registrada.",
                "SHA-256 do executavel: "
                "D2FCB649518676BC0BD5951F1392F6BEB27023CEE97F5648D79AB5A572EB889C.",
            ),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._metadata

    def process(self, noisy: np.ndarray, sample_rate: int) -> AdapterResult:
        if sample_rate != self.metadata.native_sample_rate:
            raise ValueError(
                f"WebRTC APM exige {self.metadata.native_sample_rate} Hz, "
                f"recebeu {sample_rate} Hz."
            )
        if not self.executable.is_file():
            raise FileNotFoundError(
                f"Adaptador WebRTC APM nao compilado: {self.executable}"
            )
        values = np.asarray(noisy, dtype="<f4").reshape(-1)
        process = subprocess.Popen(
            [str(self.executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        peak_rss = [0]
        stop = threading.Event()
        try:
            peak_rss[0] = int(psutil.Process(process.pid).memory_info().rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        def monitor() -> None:
            try:
                child = psutil.Process(process.pid)
                while not stop.wait(0.002):
                    peak_rss[0] = max(
                        peak_rss[0],
                        int(child.memory_info().rss),
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        started = time.perf_counter()
        stdout, stderr = process.communicate(values.tobytes(order="C"))
        elapsed = time.perf_counter() - started
        stop.set()
        thread.join(timeout=1.0)
        if process.returncode != 0:
            raise RuntimeError(
                f"WebRTC APM falhou ({process.returncode}): "
                f"{stderr.decode('utf-8', errors='replace')}"
            )
        output = np.frombuffer(stdout, dtype="<f4").copy()
        delay = self.metadata.lookahead_samples or 0
        if delay:
            output = np.pad(output[delay:], (0, delay))
        if len(output) < len(values):
            output = np.pad(output, (0, len(values) - len(output)))
        output = output[: len(values)].astype(np.float32)
        diagnostics_text = stderr.decode("utf-8", errors="replace")
        frame_match = re.search(r"frame_size=(\d+)", diagnostics_text)
        return AdapterResult(
            audio=output,
            processing_seconds=elapsed,
            peak_rss_bytes=peak_rss[0] or None,
            diagnostics={
                "frame_size": (
                    int(frame_match.group(1)) if frame_match else None
                ),
                "alignment_trim_samples": delay,
                "native_stderr": diagnostics_text.strip(),
            },
        )


class DeepFilterNetAdapter:
    def __init__(
        self,
        python_executable: Path | None = None,
        model_dir: Path | None = None,
    ) -> None:
        configured_python = os.environ.get("PTC3527_DEEPFILTERNET_PYTHON")
        configured_model = os.environ.get("PTC3527_DEEPFILTERNET_MODEL")
        cache_root = Path.home() / ".cache" / "ptc3527-benchmark"
        self.python_executable = python_executable or (
            Path(configured_python)
            if configured_python
            else cache_root
            / "deepfilternet-0.5.6-venv"
            / "Scripts"
            / "python.exe"
        )
        self.model_dir = model_dir or (
            Path(configured_model)
            if configured_model
            else cache_root
            / "deepfilternet-v0.5.6"
            / "DeepFilterNet3"
        )
        self.script = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "native"
            / "deepfilternet_adapter.py"
        )
        available = (
            self.python_executable.is_file()
            and self.model_dir.is_dir()
            and self.script.is_file()
        )
        self._metadata = AdapterMetadata(
            system_id="deepfilternet",
            display_name="DeepFilterNet3",
            implementation="DeepFilterNet 0.5.6 PyTorch/DeepFilterLib adapter",
            version="0.5.6-DeepFilterNet3",
            license_spdx="MIT OR Apache-2.0",
            native_sample_rate=48_000,
            api_frame_samples=480,
            analysis_window_samples=960,
            analysis_hop_samples=480,
            lookahead_samples=1_440,
            algorithmic_latency_ms=30.0,
            causal=True,
            backend="python-subprocess",
            source_url="https://github.com/Rikorose/DeepFilterNet",
            source_revision="978576aa8400552a4ce9730838c635aa30db5e61",
            available=available,
            notes=(
                "Modelo DeepFilterNet3 oficial da tag v0.5.6.",
                "Arquivo do modelo SHA-256: "
                "49C52EDC8947AE1F9BF50D81530BEAF3A2C3245AEAF34B6F31FF535CD22284D2.",
                "Checkpoint SHA-256: "
                "23B92884F63CCF54BB026014604625AB231657B6480DF65DB4095C4C171E6003.",
                "DeepFilterLib SHA-256: "
                "67D03591503315F7F5D5FA43B44CBBE504DB3D2FC557B0AF8C4D41F40ABD271C.",
                "Atraso causal: STFT 480 + dois hops de lookahead.",
                "Metricas removem 1440 amostras; latencia real permanece registrada.",
            ),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._metadata

    def process(self, noisy: np.ndarray, sample_rate: int) -> AdapterResult:
        if sample_rate != self.metadata.native_sample_rate:
            raise ValueError(
                f"DeepFilterNet exige {self.metadata.native_sample_rate} Hz, "
                f"recebeu {sample_rate} Hz."
            )
        if not self.metadata.available:
            raise FileNotFoundError(
                "Ambiente DeepFilterNet indisponivel: "
                f"{self.python_executable}, {self.model_dir}, {self.script}"
            )
        values = np.asarray(noisy, dtype="<f4").reshape(-1)
        environment = os.environ.copy()
        environment["PTC3527_DEEPFILTERNET_MODEL"] = str(self.model_dir)
        process = subprocess.Popen(
            [str(self.python_executable), str(self.script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        peak_rss = [0]
        stop = threading.Event()

        def monitor() -> None:
            try:
                child = psutil.Process(process.pid)
                while not stop.wait(0.002):
                    processes = [child, *child.children(recursive=True)]
                    rss = 0
                    for monitored in processes:
                        try:
                            rss += int(monitored.memory_info().rss)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    peak_rss[0] = max(
                        peak_rss[0],
                        rss,
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        started = time.perf_counter()
        stdout, stderr = process.communicate(values.tobytes(order="C"))
        wall_seconds = time.perf_counter() - started
        stop.set()
        thread.join(timeout=1.0)
        diagnostics_text = stderr.decode("utf-8", errors="replace")
        if process.returncode != 0:
            raise RuntimeError(
                f"DeepFilterNet falhou ({process.returncode}): "
                f"{diagnostics_text}"
            )
        output = np.frombuffer(stdout, dtype="<f4").copy()
        delay = self.metadata.lookahead_samples or 0
        if delay:
            output = np.pad(output[delay:], (0, delay))
        if len(output) < len(values):
            output = np.pad(output, (0, len(values) - len(output)))
        output = output[: len(values)].astype(np.float32)
        processing_match = re.search(
            r"processing_seconds=([0-9.]+)", diagnostics_text
        )
        init_match = re.search(r"init_seconds=([0-9.]+)", diagnostics_text)
        processing_seconds = (
            float(processing_match.group(1))
            if processing_match
            else wall_seconds
        )
        return AdapterResult(
            audio=output,
            processing_seconds=processing_seconds,
            peak_rss_bytes=peak_rss[0] or None,
            diagnostics={
                "alignment_trim_samples": delay,
                "init_seconds": (
                    float(init_match.group(1)) if init_match else None
                ),
                "subprocess_wall_seconds": wall_seconds,
                "native_stderr": diagnostics_text.strip(),
            },
        )


def planned_systems() -> list[AdapterMetadata]:
    return [
        FrozenBaselineAdapter().metadata,
        OMLSAIMCRAAdapter().metadata,
        RNNoiseAdapter().metadata,
        WebRTCAPMNSAdapter().metadata,
        DeepFilterNetAdapter().metadata,
        AdapterMetadata(
            system_id="speexdsp_reserve",
            display_name="SpeexDSP preprocess",
            implementation="xiph/speexdsp",
            version="reserve",
            license_spdx="BSD-3-Clause",
            native_sample_rate=16_000,
            api_frame_samples=320,
            analysis_window_samples=None,
            analysis_hop_samples=320,
            lookahead_samples=None,
            algorithmic_latency_ms=None,
            causal=True,
            backend="native-subprocess",
            source_url="https://gitlab.xiph.org/xiph/speexdsp",
            source_revision="not-pinned",
            available=False,
            notes=("Reserva; nao integra a primeira bateria.",),
        ),
    ]


def adapter_registry() -> dict[str, DenoiserAdapter]:
    baseline = FrozenBaselineAdapter()
    omlsa_imcra = OMLSAIMCRAAdapter()
    adapters: dict[str, DenoiserAdapter] = {
        baseline.metadata.system_id: baseline,
        omlsa_imcra.metadata.system_id: omlsa_imcra,
    }
    rnnoise = RNNoiseAdapter()
    if rnnoise.metadata.available:
        adapters[rnnoise.metadata.system_id] = rnnoise
    webrtc_apm = WebRTCAPMNSAdapter()
    if webrtc_apm.metadata.available:
        adapters[webrtc_apm.metadata.system_id] = webrtc_apm
    deepfilternet = DeepFilterNetAdapter()
    if deepfilternet.metadata.available:
        adapters[deepfilternet.metadata.system_id] = deepfilternet
    return adapters


def audio_sha256(audio: np.ndarray) -> str:
    values = np.asarray(audio, dtype="<f4").reshape(-1)
    return hashlib.sha256(values.tobytes(order="C")).hexdigest()


def condition_id(condition: Condition) -> str:
    return (
        f"{condition.split}__{condition.speaker}__{condition.noise_name}"
        f"__{condition.snr_target_db:+d}db"
    )


def condition_manifest(conditions: list[Condition]) -> pd.DataFrame:
    rows = []
    for condition in conditions:
        rows.append(
            {
                "condition_id": condition_id(condition),
                "split": condition.split,
                "speaker": condition.speaker,
                "noise": condition.noise_name,
                "noise_group": condition.noise_group,
                "snr_target_db": condition.snr_target_db,
                "sample_rate": CANONICAL_SAMPLE_RATE,
                "sample_count": len(condition.noisy),
                "clean_sha256_f32le": audio_sha256(condition.clean),
                "noisy_sha256_f32le": audio_sha256(condition.noisy),
                "input_snr_db": condition.input_snr_db,
                "input_si_sdr_db": condition.input_si_sdr_db,
            }
        )
    return pd.DataFrame(rows)


def canonical_roundtrip(
    audio: np.ndarray,
    native_sample_rate: int,
    canonical_sample_rate: int = CANONICAL_SAMPLE_RATE,
) -> np.ndarray:
    native = resample_audio(audio, canonical_sample_rate, native_sample_rate)
    restored = resample_audio(native, native_sample_rate, canonical_sample_rate)
    if len(restored) < len(audio):
        restored = np.pad(restored, (0, len(audio) - len(restored)))
    return restored[: len(audio)].astype(np.float32)


def _stoi(clean: np.ndarray, output: np.ndarray, sample_rate: int) -> float | None:
    if importlib.util.find_spec("pystoi") is None:
        return None
    from pystoi import stoi

    return float(stoi(clean, output, sample_rate, extended=False))


def evaluate_adapter(
    adapter: DenoiserAdapter,
    conditions: list[Condition],
) -> pd.DataFrame:
    rows = []
    metadata = adapter.metadata
    for condition in conditions:
        started = time.perf_counter()
        resample_started = time.perf_counter()
        native_input = resample_audio(
            condition.noisy,
            CANONICAL_SAMPLE_RATE,
            metadata.native_sample_rate,
        )
        input_resampling_seconds = time.perf_counter() - resample_started
        result = adapter.process(native_input, metadata.native_sample_rate)
        native_output = np.asarray(result.audio, dtype=np.float32).reshape(-1)
        if native_output.shape != native_input.shape:
            raise ValueError(
                f"{metadata.system_id} alterou comprimento nativo em "
                f"{condition_id(condition)}: "
                f"{native_output.shape} != {native_input.shape}."
            )
        resample_started = time.perf_counter()
        output = resample_audio(
            native_output,
            metadata.native_sample_rate,
            CANONICAL_SAMPLE_RATE,
        )
        output_resampling_seconds = time.perf_counter() - resample_started
        if len(output) < len(condition.noisy):
            output = np.pad(output, (0, len(condition.noisy) - len(output)))
        output = output[: len(condition.noisy)].astype(np.float32)
        wall_seconds = time.perf_counter() - started
        if output.shape != condition.noisy.shape:
            raise ValueError(
                f"{metadata.system_id} alterou comprimento em "
                f"{condition_id(condition)}: {output.shape} != {condition.noisy.shape}."
            )
        if not np.all(np.isfinite(output)):
            raise ValueError(
                f"{metadata.system_id} produziu valores nao finitos em "
                f"{condition_id(condition)}."
            )
        output_snr = snr_db(condition.clean, output)
        output_si_sdr = si_sdr(condition.clean, output)
        input_stoi = _stoi(
            condition.clean,
            condition.noisy,
            CANONICAL_SAMPLE_RATE,
        )
        output_stoi = _stoi(
            condition.clean,
            output,
            CANONICAL_SAMPLE_RATE,
        )
        duration_seconds = len(output) / CANONICAL_SAMPLE_RATE
        perceptual = perceptual_metrics(
            condition.clean,
            condition.noisy,
            output,
            CANONICAL_SAMPLE_RATE,
        )
        rows.append(
            {
                "condition_id": condition_id(condition),
                "split": condition.split,
                "speaker": condition.speaker,
                "noise": condition.noise_name,
                "noise_group": condition.noise_group,
                "snr_target_db": condition.snr_target_db,
                "system_id": metadata.system_id,
                "input_sha256_f32le": audio_sha256(condition.noisy),
                "output_sha256_f32le": audio_sha256(output),
                "input_snr_db": condition.input_snr_db,
                "output_snr_db": output_snr,
                "snr_improvement_db": output_snr - condition.input_snr_db,
                "input_si_sdr_db": condition.input_si_sdr_db,
                "output_si_sdr_db": output_si_sdr,
                "si_sdr_improvement_db": (
                    output_si_sdr - condition.input_si_sdr_db
                ),
                "input_stoi": input_stoi,
                "output_stoi": output_stoi,
                "stoi_improvement": (
                    None
                    if input_stoi is None or output_stoi is None
                    else output_stoi - input_stoi
                ),
                **perceptual,
                "processing_seconds": result.processing_seconds,
                "input_resampling_seconds": input_resampling_seconds,
                "output_resampling_seconds": output_resampling_seconds,
                "wall_seconds": wall_seconds,
                "rtf_processing": result.processing_seconds
                / max(duration_seconds, 1e-12),
                "rtf_wall": wall_seconds / max(duration_seconds, 1e-12),
                "state_memory_bytes": result.state_memory_bytes,
                "peak_rss_bytes": result.peak_rss_bytes,
                "algorithmic_latency_ms": metadata.algorithmic_latency_ms,
            }
        )
    return pd.DataFrame(rows)


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    def nullable_mean(values: pd.Series) -> float:
        numeric = pd.to_numeric(values, errors="coerce")
        return float(numeric.mean()) if numeric.notna().any() else math.nan

    return (
        metrics.groupby(["split", "system_id"], as_index=False)
        .agg(
            n_conditions=("condition_id", "size"),
            snr_improvement_mean_db=("snr_improvement_db", "mean"),
            snr_improvement_min_db=("snr_improvement_db", "min"),
            snr_degradation_fraction=(
                "snr_improvement_db",
                lambda values: float(np.mean(values < 0.0)),
            ),
            si_sdr_improvement_mean_db=("si_sdr_improvement_db", "mean"),
            input_stoi_mean=("input_stoi", nullable_mean),
            output_stoi_mean=("output_stoi", nullable_mean),
            stoi_improvement_mean=("stoi_improvement", nullable_mean),
            tonal_peak_density_mean=(
                "tonal_peak_density_per_active_block",
                "mean",
            ),
            spectral_flatness_median=("spectral_flatness_median", "median"),
            log_spectral_distance_mean_db=(
                "log_spectral_distance_mean_db",
                "mean",
            ),
            envelope_correlation_mean=("envelope_correlation", "mean"),
            band_delta_input_2000_4000_mean_db=(
                "band_delta_input_2000_4000_db",
                "mean",
            ),
            band_delta_input_4000_8000_mean_db=(
                "band_delta_input_4000_8000_db",
                "mean",
            ),
            rtf_processing_mean=("rtf_processing", "mean"),
            rtf_wall_mean=("rtf_wall", "mean"),
            input_resampling_seconds_mean=(
                "input_resampling_seconds",
                "mean",
            ),
            output_resampling_seconds_mean=(
                "output_resampling_seconds",
                "mean",
            ),
            state_memory_max_bytes=("state_memory_bytes", "max"),
            peak_rss_max_bytes=("peak_rss_bytes", "max"),
            algorithmic_latency_ms=("algorithmic_latency_ms", "max"),
        )
        .sort_values(["split", "system_id"])
        .reset_index(drop=True)
    )


def metadata_records() -> list[dict[str, object]]:
    return [asdict(item) for item in planned_systems()]
