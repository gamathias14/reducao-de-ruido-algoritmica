from __future__ import annotations

import ctypes
import os
from pathlib import Path

import numpy as np


INPUT_SAMPLE_RATE = 16_000
NATIVE_SAMPLE_RATE = 48_000
INPUT_BLOCK_SAMPLES = 320
NATIVE_FRAME_SAMPLES = 480
RNNOISE_LATENCY_MS = 20.0
RESAMPLER_TAPS = 63
RESAMPLER_DELAY_MS = (
    1000.0 * (RESAMPLER_TAPS - 1) / NATIVE_SAMPLE_RATE
)
TOTAL_ALGORITHMIC_LATENCY_MS = RNNOISE_LATENCY_MS + RESAMPLER_DELAY_MS


def default_library_path() -> Path:
    configured = os.environ.get("PTC3527_RNNOISE_DLL")
    if configured:
        return Path(configured)
    return (
        Path.home()
        / ".cache"
        / "ptc3527-benchmark"
        / "bin"
        / "ptc3527-rnnoise-v0.2.dll"
    )


class RNNoiseLibrary:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_library_path()
        if not self.path.is_file():
            raise FileNotFoundError(
                f"DLL RNNoise nao compilada: {self.path}. "
                "Execute scripts/native/Build-RNNoiseAdapter.ps1."
            )
        self.library = ctypes.CDLL(str(self.path))
        self.library.ptc3527_rnnoise_create.argtypes = []
        self.library.ptc3527_rnnoise_create.restype = ctypes.c_void_p
        self.library.ptc3527_rnnoise_reset.argtypes = [ctypes.c_void_p]
        self.library.ptc3527_rnnoise_reset.restype = ctypes.c_int
        self.library.ptc3527_rnnoise_destroy.argtypes = [ctypes.c_void_p]
        self.library.ptc3527_rnnoise_destroy.restype = None
        self.library.ptc3527_rnnoise_get_state_size.argtypes = []
        self.library.ptc3527_rnnoise_get_state_size.restype = ctypes.c_int
        self.library.ptc3527_rnnoise_get_input_size.argtypes = []
        self.library.ptc3527_rnnoise_get_input_size.restype = ctypes.c_int
        self.library.ptc3527_rnnoise_process.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        ]
        self.library.ptc3527_rnnoise_process.restype = ctypes.c_float
        self.state_size = int(self.library.ptc3527_rnnoise_get_state_size())
        self.input_size = int(self.library.ptc3527_rnnoise_get_input_size())
        if self.input_size != INPUT_BLOCK_SAMPLES or self.state_size <= 0:
            raise RuntimeError(
                "Wrapper RNNoise inesperado: "
                f"input_size={self.input_size}, state_size={self.state_size}."
            )

    def create_state(self) -> int:
        state = self.library.ptc3527_rnnoise_create()
        if not state:
            raise RuntimeError("RNNoise nao conseguiu criar o estado.")
        return int(state)

    def reset_state(self, state: int) -> None:
        result = int(
            self.library.ptc3527_rnnoise_reset(ctypes.c_void_p(state))
        )
        if result != 0:
            raise RuntimeError(f"Reset RNNoise falhou com codigo {result}.")

    def destroy_state(self, state: int | None) -> None:
        if state:
            self.library.ptc3527_rnnoise_destroy(ctypes.c_void_p(state))

    def process_block(
        self,
        state: int,
        output: np.ndarray,
        input_values: np.ndarray,
    ) -> float:
        result = float(
            self.library.ptc3527_rnnoise_process(
                ctypes.c_void_p(state),
                output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                input_values.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            )
        )
        if result < 0.0:
            raise RuntimeError(
                f"Processamento RNNoise falhou com codigo {result:g}."
            )
        return result


class RNNoiseRealtimeProcessor:
    def __init__(self, library_path: Path | None = None) -> None:
        self.native = RNNoiseLibrary(library_path)
        self.output = np.zeros(INPUT_BLOCK_SAMPLES, dtype=np.float32)
        self.state: int | None = self.native.create_state()
        self.block_index = 0

    @property
    def state_memory_bytes(self) -> int:
        return int(self.native.state_size + self.output.nbytes)

    @property
    def closed(self) -> bool:
        return self.state is None

    def reset(self) -> None:
        if self.state is None:
            self.state = self.native.create_state()
        else:
            self.native.reset_state(self.state)
        self.output.fill(0.0)
        self.block_index = 0

    def close(self) -> None:
        self.native.destroy_state(self.state)
        self.state = None

    def process_block(
        self,
        block: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, float | int | bool]]:
        if self.state is None:
            raise RuntimeError("Processador RNNoise esta fechado.")
        values = np.asarray(block, dtype=np.float32).reshape(-1)
        if values.size != INPUT_BLOCK_SAMPLES:
            raise ValueError(
                f"RNNoise exige blocos de {INPUT_BLOCK_SAMPLES} amostras, "
                f"recebeu {values.size}."
            )
        if not values.flags.c_contiguous:
            values = np.ascontiguousarray(values)
        vad_probability = self.native.process_block(
            self.state,
            self.output,
            values,
        )
        self.block_index += 1
        return self.output, {
            "warming_up": self.block_index == 1,
            "estimator_ready": True,
            "speech_probable": vad_probability >= 0.5,
            "low_energy": False,
            "estimator_updates": 0,
            "noise_power_mean": 0.0,
            "state_memory_bytes": self.state_memory_bytes,
            "vad_probability": vad_probability,
            "native_frames": 2,
        }

    def __enter__(self) -> "RNNoiseRealtimeProcessor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
