from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pywt


@dataclass(frozen=True)
class CausalWPTConfig:
    sample_rate: int = 16_000
    block_size: int = 320
    frame_length: int = 640
    wavelet: str = "haar"
    level: int = 3
    warmup_blocks: int = 8
    history_blocks: int = 25
    noise_quantile: float = 0.20
    gain_floor: float = 0.20
    epsilon: float = 1e-12

    def validate(self) -> None:
        if self.sample_rate <= 0 or self.block_size <= 0:
            raise ValueError("Taxa e bloco devem ser positivos.")
        if self.frame_length < self.block_size:
            raise ValueError("frame_length deve ser maior ou igual ao bloco.")
        if self.level < 1:
            raise ValueError("level deve ser positivo.")
        if self.warmup_blocks < 1 or self.history_blocks < self.warmup_blocks:
            raise ValueError("Historico deve cobrir o aquecimento.")
        if not 0.0 < self.noise_quantile <= 1.0:
            raise ValueError("noise_quantile deve estar em (0, 1].")
        if not 0.0 <= self.gain_floor <= 1.0:
            raise ValueError("gain_floor deve estar em [0, 1].")
        if self.epsilon <= 0.0:
            raise ValueError("epsilon deve ser positivo.")
        wavelet = pywt.Wavelet(self.wavelet)
        max_level = pywt.dwt_max_level(self.frame_length, wavelet.dec_len)
        if self.level > max_level:
            raise ValueError(
                f"Nivel {self.level} excede o maximo {max_level} para o quadro."
            )

    @property
    def subband_count(self) -> int:
        return 2**self.level

    @property
    def algorithmic_context_ms(self) -> float:
        return 1_000.0 * self.frame_length / self.sample_rate


class CausalWPTProcessor:
    """Causal block WPT with past-only rolling subband noise estimates."""

    def __init__(self, config: CausalWPTConfig | None = None) -> None:
        self.config = config or CausalWPTConfig()
        self.config.validate()
        self._wavelet = pywt.Wavelet(self.config.wavelet)
        self.reset()

    def reset(self) -> None:
        self._sample_history = np.zeros(
            self.config.frame_length - self.config.block_size,
            dtype=np.float32,
        )
        self._power_history = np.zeros(
            (self.config.history_blocks, self.config.subband_count),
            dtype=np.float32,
        )
        self._history_index = 0
        self._history_count = 0
        self.block_index = 0
        self.last_noise_power = np.zeros(
            self.config.subband_count,
            dtype=np.float32,
        )
        self.last_gain = np.ones(self.config.subband_count, dtype=np.float32)

    @property
    def ready(self) -> bool:
        return self._history_count >= self.config.warmup_blocks

    @property
    def state_memory_bytes(self) -> int:
        return int(
            self._sample_history.nbytes
            + self._power_history.nbytes
            + self.last_noise_power.nbytes
            + self.last_gain.nbytes
        )

    def process_block(
        self,
        block: np.ndarray,
    ) -> tuple[np.ndarray, dict[str, float | int | bool]]:
        values = np.asarray(block, dtype=np.float32).reshape(-1)
        if values.size == 0:
            raise ValueError("Bloco vazio recebido.")
        if values.size > self.config.block_size:
            raise ValueError(
                f"Bloco excede {self.config.block_size} amostras: {values.size}."
            )
        values = np.nan_to_num(
            values,
            nan=0.0,
            posinf=1.0,
            neginf=-1.0,
        ).astype(np.float32)

        padded = values
        if values.size < self.config.block_size:
            padded = np.pad(values, (0, self.config.block_size - values.size))
        frame = np.concatenate([self._sample_history, padded]).astype(np.float32)
        nodes, powers = self._analyze(frame)
        ready_before = self.ready

        if ready_before:
            noise_power = np.quantile(
                self._power_history[: self._history_count],
                self.config.noise_quantile,
                axis=0,
            )
            noise_power = np.maximum(noise_power, self.config.epsilon)
            speech_power = np.maximum(powers - noise_power, 0.0)
            gain = speech_power / (speech_power + noise_power + self.config.epsilon)
            gain = np.clip(gain, self.config.gain_floor, 1.0)
            reconstructed = self._reconstruct(nodes, gain)
            output = reconstructed[-self.config.block_size :][: values.size]
            self.last_noise_power = noise_power.astype(np.float32)
            self.last_gain = gain.astype(np.float32)
        else:
            output = values.copy()
            self.last_noise_power.fill(0.0)
            self.last_gain.fill(1.0)

        self._sample_history = frame[-len(self._sample_history) :].astype(np.float32)
        self._push_power(powers)
        self.block_index += 1
        output = np.nan_to_num(
            output,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        ).astype(np.float32)
        diagnostics = {
            "block_index": self.block_index,
            "warming_up": not ready_before,
            "estimator_ready": self.ready,
            "history_blocks": self._history_count,
            "noise_power_mean": float(np.mean(self.last_noise_power)),
            "gain_mean": float(np.mean(self.last_gain)),
            "gain_min": float(np.min(self.last_gain)),
            "state_memory_bytes": self.state_memory_bytes,
            "algorithmic_context_ms": self.config.algorithmic_context_ms,
        }
        return output, diagnostics

    def _analyze(
        self,
        frame: np.ndarray,
    ) -> tuple[list[tuple[str, np.ndarray]], np.ndarray]:
        packet = pywt.WaveletPacket(
            data=frame,
            wavelet=self._wavelet,
            mode="symmetric",
            maxlevel=self.config.level,
        )
        nodes = [
            (node.path, np.asarray(node.data, dtype=np.float32))
            for node in packet.get_level(self.config.level, order="freq")
        ]
        powers = np.asarray(
            [
                float(np.mean(np.square(coeffs, dtype=np.float64)))
                for _, coeffs in nodes
            ],
            dtype=np.float32,
        )
        return nodes, np.maximum(powers, self.config.epsilon)

    def _reconstruct(
        self,
        nodes: list[tuple[str, np.ndarray]],
        gain: np.ndarray,
    ) -> np.ndarray:
        packet = pywt.WaveletPacket(
            data=None,
            wavelet=self._wavelet,
            mode="symmetric",
            maxlevel=self.config.level,
        )
        for index, (path, coeffs) in enumerate(nodes):
            packet[path] = (coeffs * gain[index]).astype(np.float32)
        output = packet.reconstruct(update=False)
        if output.size < self.config.frame_length:
            output = np.pad(output, (0, self.config.frame_length - output.size))
        return output[: self.config.frame_length].astype(np.float32)

    def _push_power(self, powers: np.ndarray) -> None:
        self._power_history[self._history_index] = powers
        self._history_index = (
            self._history_index + 1
        ) % self.config.history_blocks
        self._history_count = min(
            self._history_count + 1,
            self.config.history_blocks,
        )
