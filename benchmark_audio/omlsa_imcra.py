from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal
from scipy.special import exp1


@dataclass(frozen=True)
class OMLSAIMCRAConfig:
    """Parameters reported for 16 kHz in Cohen (2001, 2003)."""

    sample_rate: int = 16_000
    n_fft: int = 512
    hop_length: int = 128
    decision_directed_alpha: float = 0.92
    minimum_gain_db: float = -25.0
    frequency_half_width: int = 1
    temporal_smoothing: float = 0.90
    minimum_window_frames: int = 120
    subwindow_frames: int = 15
    minimum_bias: float = 1.66
    first_gamma_threshold: float = 4.6
    zeta_threshold: float = 1.67
    second_gamma_threshold: float = 3.0
    noise_smoothing: float = 0.85
    noise_bias: float = 1.47
    epsilon: float = 1e-12

    @property
    def minimum_gain(self) -> float:
        return 10.0 ** (self.minimum_gain_db / 20.0)

    @property
    def subwindow_count(self) -> int:
        return self.minimum_window_frames // self.subwindow_frames

    @property
    def algorithmic_latency_ms(self) -> float:
        return 1_000.0 * self.n_fft / self.sample_rate

    def validate(self) -> None:
        if self.sample_rate <= 0 or self.n_fft <= 1 or self.hop_length <= 0:
            raise ValueError("Taxa, FFT e hop devem ser positivos.")
        if self.hop_length >= self.n_fft:
            raise ValueError("hop_length deve ser menor que n_fft.")
        if not 0.0 < self.decision_directed_alpha < 1.0:
            raise ValueError("decision_directed_alpha deve estar em (0, 1).")
        if not 0.0 < self.temporal_smoothing < 1.0:
            raise ValueError("temporal_smoothing deve estar em (0, 1).")
        if not 0.0 < self.noise_smoothing < 1.0:
            raise ValueError("noise_smoothing deve estar em (0, 1).")
        if self.minimum_window_frames < self.subwindow_frames:
            raise ValueError("A janela de minimos deve cobrir uma subjanela.")
        if self.minimum_window_frames % self.subwindow_frames:
            raise ValueError("minimum_window_frames deve ser multiplo da subjanela.")
        if self.frequency_half_width != 1:
            raise ValueError("A implementacao fiel atual exige w=1.")
        if self.minimum_bias <= 0.0 or self.noise_bias <= 0.0:
            raise ValueError("Fatores de bias devem ser positivos.")
        if self.epsilon <= 0.0:
            raise ValueError("epsilon deve ser positivo.")


class _SubwindowMinimum:
    def __init__(self, n_bins: int, config: OMLSAIMCRAConfig) -> None:
        self.n_bins = n_bins
        self.subwindow_frames = config.subwindow_frames
        self.subwindow_count = config.subwindow_count
        self.reset()

    def reset(self) -> None:
        self.current = np.full(self.n_bins, np.inf, dtype=np.float64)
        self.completed: list[np.ndarray] = []
        self.frames_in_subwindow = 0

    def update(self, values: np.ndarray) -> np.ndarray:
        self.current = np.minimum(self.current, values)
        self.frames_in_subwindow += 1
        if self.frames_in_subwindow >= self.subwindow_frames:
            self.completed.append(self.current.copy())
            self.completed = self.completed[-self.subwindow_count :]
            result = np.min(np.stack(self.completed), axis=0)
            self.current.fill(np.inf)
            self.frames_in_subwindow = 0
            return result
        previous_count = max(0, self.subwindow_count - 1)
        previous = self.completed[-previous_count:] if previous_count else []
        if not previous:
            return self.current.copy()
        return np.minimum(
            self.current,
            np.min(np.stack(previous), axis=0),
        )

    @property
    def state_memory_bytes(self) -> int:
        return int(
            self.current.nbytes
            + sum(values.nbytes for values in self.completed)
        )


class OMLSAIMCRASpectralProcessor:
    """Sequential OM-LSA gain with the two-pass IMCRA noise estimator."""

    def __init__(self, config: OMLSAIMCRAConfig | None = None) -> None:
        self.config = config or OMLSAIMCRAConfig()
        self.config.validate()
        self.n_bins = self.config.n_fft // 2 + 1
        self._frequency_weights = np.asarray([0.25, 0.50, 0.25])
        self._first_minimum = _SubwindowMinimum(self.n_bins, self.config)
        self._second_minimum = _SubwindowMinimum(self.n_bins, self.config)
        self.reset()

    def reset(self) -> None:
        self.frame_index = 0
        self.noise_power: np.ndarray | None = None
        self._biased_noise_power: np.ndarray | None = None
        self._first_smoothed: np.ndarray | None = None
        self._second_smoothed: np.ndarray | None = None
        self._previous_gamma = np.ones(self.n_bins, dtype=np.float64)
        self._previous_conditional_gain = np.ones(
            self.n_bins,
            dtype=np.float64,
        )
        self.last_prior_snr = np.zeros(self.n_bins, dtype=np.float64)
        self.last_presence_probability = np.zeros(
            self.n_bins,
            dtype=np.float64,
        )
        self.last_absence_probability = np.ones(
            self.n_bins,
            dtype=np.float64,
        )
        self.last_gain = np.ones(self.n_bins, dtype=np.float64)
        self._first_minimum.reset()
        self._second_minimum.reset()

    @property
    def state_memory_bytes(self) -> int:
        arrays = (
            self.noise_power,
            self._biased_noise_power,
            self._first_smoothed,
            self._second_smoothed,
            self._previous_gamma,
            self._previous_conditional_gain,
            self.last_prior_snr,
            self.last_presence_probability,
            self.last_absence_probability,
            self.last_gain,
        )
        return int(
            sum(0 if value is None else value.nbytes for value in arrays)
            + self._first_minimum.state_memory_bytes
            + self._second_minimum.state_memory_bytes
        )

    def process_spectrum(
        self,
        spectrum: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, float | int]]:
        values = np.asarray(spectrum, dtype=np.complex128).reshape(-1)
        if values.shape != (self.n_bins,):
            raise ValueError(
                f"Espectro deve ter {self.n_bins} bins, recebeu {values.shape}."
            )
        power = np.maximum(np.square(np.abs(values)), self.config.epsilon)
        if self.noise_power is None:
            self._initialize(power)
            return values.copy(), self._diagnostics()

        gamma = np.maximum(
            power / np.maximum(self.noise_power, self.config.epsilon),
            self.config.epsilon,
        )
        prior_snr = (
            self.config.decision_directed_alpha
            * np.square(self._previous_conditional_gain)
            * self._previous_gamma
            + (1.0 - self.config.decision_directed_alpha)
            * np.maximum(gamma - 1.0, 0.0)
        )
        prior_snr = np.maximum(prior_snr, self.config.epsilon)
        nu = gamma * prior_snr / (1.0 + prior_snr)
        conditional_gain = (
            prior_snr
            / (1.0 + prior_snr)
            * np.exp(0.5 * exp1(np.maximum(nu, self.config.epsilon)))
        )
        conditional_gain = np.nan_to_num(
            conditional_gain,
            nan=self.config.epsilon,
            posinf=1.0,
            neginf=self.config.epsilon,
        )
        conditional_gain = np.maximum(
            conditional_gain,
            self.config.epsilon,
        )

        frequency_power = self._frequency_smooth(power)
        self._first_smoothed = (
            self.config.temporal_smoothing * self._first_smoothed
            + (1.0 - self.config.temporal_smoothing) * frequency_power
        )
        first_minimum = self._first_minimum.update(self._first_smoothed)
        denominator = np.maximum(
            self.config.minimum_bias * first_minimum,
            self.config.epsilon,
        )
        gamma_min = power / denominator
        zeta = self._first_smoothed / denominator
        noise_indicator = (
            (gamma_min < self.config.first_gamma_threshold)
            & (zeta < self.config.zeta_threshold)
        )

        selected_frequency_power = self._frequency_smooth_selected(
            power,
            noise_indicator,
            self._second_smoothed,
        )
        self._second_smoothed = (
            self.config.temporal_smoothing * self._second_smoothed
            + (1.0 - self.config.temporal_smoothing)
            * selected_frequency_power
        )
        second_minimum = self._second_minimum.update(self._second_smoothed)
        second_denominator = np.maximum(
            self.config.minimum_bias * second_minimum,
            self.config.epsilon,
        )
        second_gamma_min = power / second_denominator
        second_zeta = self._second_smoothed / second_denominator
        absence_probability = np.zeros(self.n_bins, dtype=np.float64)
        absence_probability[
            (second_gamma_min <= 1.0)
            & (second_zeta < self.config.zeta_threshold)
        ] = 1.0
        transition = (
            (second_gamma_min > 1.0)
            & (second_gamma_min < self.config.second_gamma_threshold)
            & (second_zeta < self.config.zeta_threshold)
        )
        absence_probability[transition] = (
            self.config.second_gamma_threshold
            - second_gamma_min[transition]
        ) / (self.config.second_gamma_threshold - 1.0)

        likelihood_term = (1.0 + prior_snr) * np.exp(-nu)
        presence_probability = np.empty(self.n_bins, dtype=np.float64)
        certain_absence = absence_probability >= 1.0 - 1e-12
        certain_presence = absence_probability <= 1e-12
        uncertain = ~(certain_absence | certain_presence)
        presence_probability[certain_absence] = 0.0
        presence_probability[certain_presence] = 1.0
        odds = absence_probability[uncertain] / (
            1.0 - absence_probability[uncertain]
        )
        presence_probability[uncertain] = 1.0 / (
            1.0 + odds * likelihood_term[uncertain]
        )
        presence_probability = np.clip(presence_probability, 0.0, 1.0)

        log_gain = (
            presence_probability
            * np.log(np.maximum(conditional_gain, self.config.epsilon))
            + (1.0 - presence_probability)
            * np.log(self.config.minimum_gain)
        )
        gain = np.nan_to_num(
            np.exp(log_gain),
            nan=self.config.epsilon,
            posinf=1.0,
            neginf=self.config.epsilon,
        )
        gain = np.maximum(gain, self.config.epsilon)
        enhanced = gain * values

        time_varying_alpha = (
            self.config.noise_smoothing
            + (1.0 - self.config.noise_smoothing)
            * presence_probability
        )
        self._biased_noise_power = (
            time_varying_alpha * self._biased_noise_power
            + (1.0 - time_varying_alpha) * power
        )
        self.noise_power = np.maximum(
            self.config.noise_bias * self._biased_noise_power,
            self.config.epsilon,
        )
        self._previous_gamma = gamma
        self._previous_conditional_gain = conditional_gain
        self.last_prior_snr = prior_snr
        self.last_presence_probability = presence_probability
        self.last_absence_probability = absence_probability
        self.last_gain = gain
        self.frame_index += 1
        return enhanced, self._diagnostics()

    def _initialize(self, power: np.ndarray) -> None:
        frequency_power = self._frequency_smooth(power)
        self.noise_power = power.copy()
        self._biased_noise_power = power.copy()
        self._first_smoothed = frequency_power.copy()
        self._second_smoothed = frequency_power.copy()
        self._first_minimum.update(self._first_smoothed)
        self._second_minimum.update(self._second_smoothed)
        self.frame_index = 1

    def _frequency_smooth(self, power: np.ndarray) -> np.ndarray:
        padded = np.pad(power, (1, 1), mode="edge")
        return np.convolve(
            padded,
            self._frequency_weights,
            mode="valid",
        )

    def _frequency_smooth_selected(
        self,
        power: np.ndarray,
        selected: np.ndarray,
        fallback: np.ndarray,
    ) -> np.ndarray:
        padded_power = np.pad(power, (1, 1), mode="edge")
        padded_selected = np.pad(selected.astype(np.float64), (1, 1), mode="edge")
        numerator = np.convolve(
            padded_power * padded_selected,
            self._frequency_weights,
            mode="valid",
        )
        denominator = np.convolve(
            padded_selected,
            self._frequency_weights,
            mode="valid",
        )
        return np.divide(
            numerator,
            denominator,
            out=fallback.copy(),
            where=denominator > self.config.epsilon,
        )

    def _diagnostics(self) -> dict[str, float | int]:
        return {
            "frame_index": self.frame_index,
            "noise_power_mean": float(np.mean(self.noise_power)),
            "prior_snr_mean": float(np.mean(self.last_prior_snr)),
            "presence_probability_mean": float(
                np.mean(self.last_presence_probability)
            ),
            "gain_mean": float(np.mean(self.last_gain)),
            "gain_min": float(np.min(self.last_gain)),
            "state_memory_bytes": self.state_memory_bytes,
        }


class OMLSAIMCRAProcessor:
    """File adapter using sequential causal spectral updates and WOLA."""

    def __init__(self, config: OMLSAIMCRAConfig | None = None) -> None:
        self.config = config or OMLSAIMCRAConfig()
        self.config.validate()
        self.spectral = OMLSAIMCRASpectralProcessor(self.config)
        self._window = signal.windows.hamming(
            self.config.n_fft,
            sym=False,
        ).astype(np.float64)

    @property
    def state_memory_bytes(self) -> int:
        return int(self._window.nbytes + self.spectral.state_memory_bytes)

    def reset(self) -> None:
        self.spectral.reset()

    def process(self, audio: np.ndarray) -> tuple[np.ndarray, dict[str, float | int]]:
        values = np.nan_to_num(
            np.asarray(audio, dtype=np.float32).reshape(-1),
            nan=0.0,
            posinf=1.0,
            neginf=-1.0,
        )
        if values.size == 0:
            return values.copy(), {
                "frame_count": 0,
                "state_memory_bytes": self.state_memory_bytes,
            }
        self.reset()
        pad = self.config.n_fft
        padded = np.pad(values.astype(np.float64), (pad, pad))
        frame_count = 1 + (
            len(padded) - self.config.n_fft
        ) // self.config.hop_length
        output = np.zeros_like(padded)
        normalization = np.zeros_like(padded)
        window_power = np.square(self._window)
        last_diagnostics: dict[str, float | int] = {}
        for frame_index in range(frame_count):
            start = frame_index * self.config.hop_length
            frame = padded[start : start + self.config.n_fft]
            if len(frame) < self.config.n_fft:
                break
            spectrum = np.fft.rfft(frame * self._window)
            enhanced, last_diagnostics = self.spectral.process_spectrum(
                spectrum
            )
            reconstructed = np.fft.irfft(
                enhanced,
                n=self.config.n_fft,
            )
            output[start : start + self.config.n_fft] += (
                reconstructed * self._window
            )
            normalization[start : start + self.config.n_fft] += window_power
        valid = normalization > self.config.epsilon
        output[valid] /= normalization[valid]
        output[~valid] = padded[~valid]
        restored = output[pad : pad + len(values)]
        return np.nan_to_num(
            restored,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        ).astype(np.float32), {
            "frame_count": self.spectral.frame_index,
            "state_memory_bytes": self.state_memory_bytes,
            **last_diagnostics,
        }
