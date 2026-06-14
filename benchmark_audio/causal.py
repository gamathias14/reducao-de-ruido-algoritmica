from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import signal

from .denoise import DenoiseConfig, istft_transform, stft_transform


CAUSAL_METHODS = ("bypass", "stft_subtraction", "stft_wiener")
NOISE_ESTIMATOR_MODES = ("calibration", "adaptive")


def _frames_within_duration(duration_ms: float, sample_rate: int, n_fft: int, hop_length: int) -> int:
    samples = max(n_fft, int(round(duration_ms * sample_rate / 1000.0)))
    return max(1, 1 + (samples - n_fft) // hop_length)


@dataclass(frozen=True)
class CausalNoiseConfig:
    """Parameters for a deterministic, causal noise-power estimator."""

    sample_rate: int = 16_000
    n_fft: int = 512
    hop_length: int = 160
    mode: str = "adaptive"
    calibration_ms: float = 250.0
    warmup_ms: float = 250.0
    history_ms: float = 500.0
    noise_quantile: float = 0.22
    energy_quantile: float = 0.20
    speech_threshold_db: float = 6.0
    low_energy_alpha: float = 0.30
    speech_alpha: float = 0.005
    epsilon: float = 1e-12

    @property
    def calibration_frames(self) -> int:
        return _frames_within_duration(
            self.calibration_ms,
            self.sample_rate,
            self.n_fft,
            self.hop_length,
        )

    @property
    def warmup_frames(self) -> int:
        return _frames_within_duration(
            self.warmup_ms,
            self.sample_rate,
            self.n_fft,
            self.hop_length,
        )

    @property
    def history_frames(self) -> int:
        hop_ms = 1_000.0 * self.hop_length / self.sample_rate
        return max(self.warmup_frames, int(math.ceil(self.history_ms / hop_ms)))

    def validate(self) -> None:
        if self.mode not in NOISE_ESTIMATOR_MODES:
            raise ValueError(f"Modo causal de ruido invalido: {self.mode}")
        if self.sample_rate <= 0 or self.n_fft <= 1 or self.hop_length <= 0:
            raise ValueError("Taxa, FFT e hop devem ser positivos.")
        if self.hop_length >= self.n_fft:
            raise ValueError("hop_length deve ser menor que n_fft.")
        if not 0.0 < self.noise_quantile <= 1.0:
            raise ValueError("noise_quantile deve estar em (0, 1].")
        if not 0.0 < self.energy_quantile <= 1.0:
            raise ValueError("energy_quantile deve estar em (0, 1].")
        if not 0.0 < self.low_energy_alpha <= 1.0:
            raise ValueError("low_energy_alpha deve estar em (0, 1].")
        if not 0.0 <= self.speech_alpha <= 1.0:
            raise ValueError("speech_alpha deve estar em [0, 1].")
        if self.epsilon <= 0.0:
            raise ValueError("epsilon deve ser positivo.")


class CausalNoiseEstimator:
    """Tracks noise power using only current and previously observed spectra."""

    def __init__(self, config: CausalNoiseConfig) -> None:
        config.validate()
        self.config = config
        self.n_bins = config.n_fft // 2 + 1
        self.reset()

    def reset(self) -> None:
        self._spectral_history = np.zeros(
            (self.config.history_frames, self.n_bins),
            dtype=np.float32,
        )
        self._energy_history = np.zeros(self.config.history_frames, dtype=np.float64)
        self._history_index = 0
        self._history_count = 0
        self._calibration_sum = np.zeros(self.n_bins, dtype=np.float64)
        self._estimate_power: np.ndarray | None = None
        self.frames_seen = 0
        self.last_speech_probable = False
        self.last_low_energy = True
        self.last_update_alpha = 0.0
        self.last_frame_energy = 0.0
        self.last_energy_floor = 0.0

    @property
    def ready(self) -> bool:
        if self._estimate_power is None:
            return False
        if self.config.mode == "calibration":
            return self.frames_seen >= self.config.calibration_frames
        return self.frames_seen >= self.config.warmup_frames

    @property
    def estimate_power(self) -> np.ndarray | None:
        if self._estimate_power is None:
            return None
        return self._estimate_power.reshape(-1, 1)

    @property
    def state_memory_bytes(self) -> int:
        estimate_bytes = 0 if self._estimate_power is None else self._estimate_power.nbytes
        return int(
            self._spectral_history.nbytes
            + self._energy_history.nbytes
            + self._calibration_sum.nbytes
            + estimate_bytes
        )

    def update(self, power_spectrum: np.ndarray) -> dict[str, float | int | bool]:
        values = np.asarray(power_spectrum, dtype=np.float64).reshape(-1)
        if values.shape != (self.n_bins,):
            raise ValueError(f"Espectro deve ter {self.n_bins} bins, recebeu {values.shape}.")
        values = np.nan_to_num(
            values,
            nan=self.config.epsilon,
            posinf=np.finfo(np.float32).max,
            neginf=self.config.epsilon,
        )
        values = np.maximum(values, self.config.epsilon)
        self.frames_seen += 1

        if self.config.mode == "calibration":
            self._update_calibration(values)
        else:
            self._update_adaptive(values)

        estimate_mean = (
            float(np.mean(self._estimate_power, dtype=np.float64))
            if self._estimate_power is not None
            else 0.0
        )
        return {
            "frames_seen": self.frames_seen,
            "ready": self.ready,
            "speech_probable": self.last_speech_probable,
            "low_energy": self.last_low_energy,
            "update_alpha": self.last_update_alpha,
            "frame_energy": self.last_frame_energy,
            "energy_floor": self.last_energy_floor,
            "noise_power_mean": estimate_mean,
        }

    def _update_calibration(self, values: np.ndarray) -> None:
        if self.frames_seen <= self.config.calibration_frames:
            self._calibration_sum += values
            divisor = min(self.frames_seen, self.config.calibration_frames)
            self._estimate_power = np.maximum(
                self._calibration_sum / divisor,
                self.config.epsilon,
            ).astype(np.float32)
        self.last_speech_probable = False
        self.last_low_energy = True
        self.last_update_alpha = 1.0 / min(self.frames_seen, self.config.calibration_frames)
        self.last_frame_energy = float(np.mean(values))
        self.last_energy_floor = self.last_frame_energy

    def _update_adaptive(self, values: np.ndarray) -> None:
        slot = self._history_index
        self._spectral_history[slot] = values.astype(np.float32)
        frame_energy = float(np.mean(values))
        self._energy_history[slot] = frame_energy
        self._history_index = (slot + 1) % self.config.history_frames
        self._history_count = min(self._history_count + 1, self.config.history_frames)

        spectra = self._spectral_history[: self._history_count]
        energies = self._energy_history[: self._history_count]
        candidate = np.quantile(spectra, self.config.noise_quantile, axis=0)
        energy_floor = float(np.quantile(energies, self.config.energy_quantile))
        speech_ratio = 10.0 ** (self.config.speech_threshold_db / 10.0)
        speech_probable = (
            self._history_count >= 3
            and frame_energy > max(energy_floor, self.config.epsilon) * speech_ratio
        )
        alpha = self.config.speech_alpha if speech_probable else self.config.low_energy_alpha

        if self._estimate_power is None:
            estimate = candidate
        else:
            estimate = (1.0 - alpha) * self._estimate_power + alpha * candidate
        self._estimate_power = np.maximum(estimate, self.config.epsilon).astype(np.float32)
        self.last_speech_probable = speech_probable
        self.last_low_energy = not speech_probable
        self.last_update_alpha = alpha
        self.last_frame_energy = frame_energy
        self.last_energy_floor = energy_floor


@dataclass(frozen=True)
class CausalProcessorConfig:
    sample_rate: int = 16_000
    method: str = "stft_subtraction"
    n_fft: int = 512
    hop_length: int = 160
    spectral_alpha: float = 1.5
    spectral_floor: float = 0.02
    gain_smoothing: float = 0.0
    wiener_floor: float = 0.05
    noise_mode: str = "adaptive"
    calibration_ms: float = 250.0
    warmup_ms: float = 250.0
    history_ms: float = 500.0
    noise_quantile: float = 0.22
    energy_quantile: float = 0.20
    speech_threshold_db: float = 6.0
    low_energy_alpha: float = 0.30
    speech_alpha: float = 0.005
    epsilon: float = 1e-12

    def noise_config(self) -> CausalNoiseConfig:
        return CausalNoiseConfig(
            sample_rate=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            mode=self.noise_mode,
            calibration_ms=self.calibration_ms,
            warmup_ms=self.warmup_ms,
            history_ms=self.history_ms,
            noise_quantile=self.noise_quantile,
            energy_quantile=self.energy_quantile,
            speech_threshold_db=self.speech_threshold_db,
            low_energy_alpha=self.low_energy_alpha,
            speech_alpha=self.speech_alpha,
            epsilon=self.epsilon,
        )

    def denoise_config(self) -> DenoiseConfig:
        return DenoiseConfig(
            sample_rate=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            spectral_alpha=self.spectral_alpha,
            spectral_floor=self.spectral_floor,
            wiener_floor=self.wiener_floor,
        )

    def validate(self) -> None:
        if self.method not in CAUSAL_METHODS:
            raise ValueError(f"Metodo causal invalido: {self.method}")
        if not 0.0 <= self.gain_smoothing < 1.0:
            raise ValueError("gain_smoothing deve estar em [0, 1).")
        self.noise_config().validate()


class CausalSTFTProcessor:
    """Block API shared by file playback and realtime capture."""

    def __init__(self, config: CausalProcessorConfig) -> None:
        config.validate()
        self.config = config
        self.denoise_config = config.denoise_config()
        self.noise_estimator = CausalNoiseEstimator(config.noise_config())
        self._analysis_window = signal.windows.hann(config.n_fft, sym=False).astype(np.float32)
        self._analysis_scale = max(float(np.sum(self._analysis_window)), config.epsilon)
        self.reset()

    def reset(self) -> None:
        self.history = np.zeros(self.config.n_fft, dtype=np.float32)
        self.analysis_buffer = np.zeros(0, dtype=np.float32)
        self._previous_gain: np.ndarray | None = None
        self.block_index = 0
        self.noise_estimator.reset()

    @property
    def state_memory_bytes(self) -> int:
        return int(
            self.history.nbytes
            + self.analysis_buffer.nbytes
            + self._analysis_window.nbytes
            + (0 if self._previous_gain is None else self._previous_gain.nbytes)
            + self.noise_estimator.state_memory_bytes
        )

    def _smooth_gain(self, gain: np.ndarray) -> np.ndarray:
        coefficient = self.config.gain_smoothing
        if coefficient <= 0.0:
            return gain
        smoothed = np.empty_like(gain)
        previous = self._previous_gain
        for frame_index in range(gain.shape[1]):
            current = gain[:, frame_index]
            if previous is None:
                previous = current
            else:
                previous = coefficient * previous + (1.0 - coefficient) * current
            smoothed[:, frame_index] = previous
        self._previous_gain = previous.astype(np.float32)
        return smoothed

    def process_block(self, block: np.ndarray) -> tuple[np.ndarray, dict[str, float | int | bool]]:
        block = np.asarray(block, dtype=np.float32).reshape(-1)
        if block.size == 0:
            raise ValueError("Bloco vazio recebido.")
        block = np.nan_to_num(block, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)
        ready_before = self.noise_estimator.ready

        if self.config.method == "bypass" or not ready_before:
            output = block.copy()
        else:
            window = np.concatenate([self.history, block]).astype(np.float32)
            output_window = self._process_window(window)
            output = output_window[-len(block) :].astype(np.float32)

        self._push_history(block)
        estimator_updates = self._update_estimator(block)
        self.block_index += 1
        output = np.nan_to_num(output, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

        diagnostics = {
            "block_index": self.block_index,
            "estimator_ready": self.noise_estimator.ready,
            "warming_up": self.config.method != "bypass" and not ready_before,
            "speech_probable": self.noise_estimator.last_speech_probable,
            "low_energy": self.noise_estimator.last_low_energy,
            "estimator_updates": estimator_updates,
            "noise_power_mean": (
                float(np.mean(self.noise_estimator.estimate_power))
                if self.noise_estimator.estimate_power is not None
                else 0.0
            ),
            "state_memory_bytes": self.state_memory_bytes,
        }
        return output, diagnostics

    def _push_history(self, block: np.ndarray) -> None:
        combined = np.concatenate([self.history, block]).astype(np.float32)
        self.history = combined[-self.config.n_fft :]

    def _update_estimator(self, block: np.ndarray) -> int:
        if self.config.method == "bypass":
            return 0
        self.analysis_buffer = np.concatenate([self.analysis_buffer, block]).astype(np.float32)
        updates = 0
        while len(self.analysis_buffer) >= self.config.n_fft:
            frame = self.analysis_buffer[: self.config.n_fft]
            spectrum = np.fft.rfft(frame * self._analysis_window) / self._analysis_scale
            power = np.maximum(np.abs(spectrum) ** 2, self.config.epsilon)
            self.noise_estimator.update(power)
            self.analysis_buffer = self.analysis_buffer[self.config.hop_length :]
            updates += 1
        return updates

    def _process_window(self, noisy: np.ndarray) -> np.ndarray:
        noise_power = self.noise_estimator.estimate_power
        if noise_power is None:
            return noisy.copy()
        _, _, zxx = stft_transform(noisy, self.denoise_config)
        if self.config.method == "stft_subtraction":
            magnitude = np.abs(zxx)
            phase = np.exp(1j * np.angle(zxx))
            noise_magnitude = np.sqrt(np.maximum(noise_power, self.config.epsilon))
            clean_magnitude = np.maximum(
                magnitude - self.config.spectral_alpha * noise_magnitude,
                self.config.spectral_floor * magnitude,
            )
            if self.config.gain_smoothing <= 0.0:
                processed = clean_magnitude * phase
            else:
                gain = np.divide(
                    clean_magnitude,
                    magnitude,
                    out=np.ones_like(clean_magnitude),
                    where=magnitude > self.config.epsilon,
                )
                processed = self._smooth_gain(gain) * zxx
        elif self.config.method == "stft_wiener":
            power = np.abs(zxx) ** 2
            speech_power = np.maximum(power - noise_power, 0.0)
            gain = speech_power / (speech_power + noise_power + self.config.epsilon)
            gain = np.maximum(gain, self.config.wiener_floor)
            processed = (
                gain * zxx
                if self.config.gain_smoothing <= 0.0
                else self._smooth_gain(gain) * zxx
            )
        else:
            return noisy.copy()
        return istft_transform(processed, len(noisy), self.denoise_config)
