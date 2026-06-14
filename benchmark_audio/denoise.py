from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pywt
from scipy import signal
from scipy.io import wavfile


SAMPLE_RATE = 16_000
DENOISE_METHODS = (
    "noisy",
    "stft_subtraction",
    "stft_wiener",
    "wavelet_soft",
    "wavelet_packet_wiener",
    "wavelet_packet_wiener_frames",
)


@dataclass(frozen=True)
class DenoiseConfig:
    """Default parameters shared by the offline benchmark and streaming prototypes."""

    sample_rate: int = SAMPLE_RATE
    n_fft: int = 512
    hop_length: int = 160
    noise_estimate_s: float = 0.25
    spectral_alpha: float = 1.2
    spectral_floor: float = 0.03
    wiener_floor: float = 0.05
    noise_estimator: str = "initial"
    noise_quantile: float = 0.2
    wavelet: str = "db4"
    wavelet_level: int = 5
    wavelet_mode: str = "soft"
    wavelet_threshold_strategy: str = "global"
    wavelet_threshold_scale: float = 1.0
    wpt_wavelet: str = "db4"
    wpt_level: int = 3
    wpt_noise_tracking: str = "rolling_quantile"
    wpt_noise_quantile: float = 0.20
    wpt_noise_window: int = 31
    wpt_noise_smoothing: float = 0.0
    wpt_gain_floor: float = 0.05
    wpt_frame_length: int = 1024
    wpt_frame_hop: int = 256


def normalize_peak(x: np.ndarray, peak: float = 0.95) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    max_abs = float(np.max(np.abs(x))) if x.size else 0.0
    if max_abs < 1e-12:
        return x.copy()
    return (x / max_abs * peak).astype(np.float32)


def audio_to_float_mono(data: np.ndarray) -> np.ndarray:
    data = np.asarray(data)
    if data.ndim not in (1, 2):
        raise ValueError(f"Audio deve ter uma ou duas dimensoes, recebeu {data.shape}.")
    if data.dtype == np.uint8:
        data = (data.astype(np.float32) - 128.0) / 128.0
    elif np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        scale = float(max(abs(info.min), info.max))
        data = data.astype(np.float32) / scale
    else:
        data = data.astype(np.float32)
    if data.ndim == 2:
        data = data.mean(axis=1)
    return data.astype(np.float32)


def resample_audio(data: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    if source_sr <= 0 or target_sr <= 0:
        raise ValueError("Taxas de amostragem devem ser positivas.")
    values = np.asarray(data, dtype=np.float32).reshape(-1)
    if source_sr == target_sr:
        return values.copy()
    gcd = math.gcd(int(source_sr), int(target_sr))
    return signal.resample_poly(
        values,
        target_sr // gcd,
        source_sr // gcd,
    ).astype(np.float32)


def read_wav_mono(path: Path, target_sr: int, *, normalize: bool = True) -> np.ndarray:
    sr, data = wavfile.read(path)
    data = audio_to_float_mono(data)
    data = resample_audio(data, int(sr), target_sr)
    if normalize:
        return normalize_peak(data, peak=0.95)
    return data


def write_wav(path: Path, data: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = np.clip(data, -1.0, 1.0)
    wavfile.write(path, sample_rate, (safe * 32767).astype(np.int16))


def colored_noise(beta: float, n: int, rng: np.random.Generator) -> np.ndarray:
    freqs = np.fft.rfftfreq(n)
    spectrum = rng.normal(size=freqs.shape) + 1j * rng.normal(size=freqs.shape)
    scale = np.ones_like(freqs)
    scale[1:] = 1.0 / np.maximum(freqs[1:], 1.0 / n) ** (beta / 2.0)
    y = np.fft.irfft(spectrum * scale, n=n)
    return normalize_peak(y)


def make_noise(name: str, n: int, sample_rate: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / sample_rate
    if name == "white":
        noise = rng.normal(size=n)
    elif name == "pink":
        noise = colored_noise(beta=1.0, n=n, rng=rng)
    elif name == "hum":
        noise = (
            0.70 * np.sin(2 * np.pi * 60 * t)
            + 0.30 * np.sin(2 * np.pi * 120 * t)
            + 0.12 * rng.normal(size=n)
        )
    elif name == "impulsive":
        noise = 0.05 * rng.normal(size=n)
        idx = rng.choice(n, size=max(1, n // 700), replace=False)
        width = max(8, sample_rate // 700)
        pulse = signal.windows.hann(width * 2 + 1)
        for start in idx:
            lo = max(0, int(start) - width)
            hi = min(n, int(start) + width + 1)
            p_lo = width - (int(start) - lo)
            p_hi = p_lo + (hi - lo)
            noise[lo:hi] += rng.uniform(-1.0, 1.0) * pulse[p_lo:p_hi]
    else:
        raise ValueError(f"Noise type not supported: {name}")
    return normalize_peak(noise)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x), dtype=np.float64) + 1e-12))


def mix_at_snr(clean: np.ndarray, noise: np.ndarray, snr_db_value: float) -> tuple[np.ndarray, np.ndarray]:
    clean_rms = rms(clean)
    noise_rms = rms(noise)
    target_noise_rms = clean_rms / (10 ** (snr_db_value / 20.0))
    scaled_noise = noise * (target_noise_rms / max(noise_rms, 1e-12))
    mixed = clean + scaled_noise
    return mixed.astype(np.float32), scaled_noise.astype(np.float32)


def snr_db(reference: np.ndarray, estimate: np.ndarray) -> float:
    noise = reference - estimate
    return 10.0 * math.log10(
        (float(np.sum(reference.astype(np.float64) ** 2)) + 1e-12)
        / (float(np.sum(noise.astype(np.float64) ** 2)) + 1e-12)
    )


def mse(reference: np.ndarray, estimate: np.ndarray) -> float:
    return float(np.mean((reference.astype(np.float64) - estimate.astype(np.float64)) ** 2))


def si_sdr(reference: np.ndarray, estimate: np.ndarray) -> float:
    ref = reference.astype(np.float64) - np.mean(reference)
    est = estimate.astype(np.float64) - np.mean(estimate)
    scale = np.dot(est, ref) / (np.dot(ref, ref) + 1e-12)
    target = scale * ref
    residual = est - target
    return 10.0 * math.log10((np.sum(target**2) + 1e-12) / (np.sum(residual**2) + 1e-12))


def estimate_memory_kb(method: str, n_samples: int, config: DenoiseConfig) -> float:
    if method.startswith("stft"):
        _, _, zxx = signal.stft(
            np.zeros(n_samples, dtype=np.float32),
            fs=config.sample_rate,
            window="hann",
            nperseg=config.n_fft,
            noverlap=config.n_fft - config.hop_length,
            nfft=config.n_fft,
            boundary=None,
            padded=False,
        )
        return float(zxx.nbytes * 3 / 1024.0)
    if method in {"wavelet_packet_wiener", "wavelet_packet_wiener_frames"}:
        n_analysis = n_samples if method == "wavelet_packet_wiener" else config.wpt_frame_length
        level = min(
            config.wpt_level,
            pywt.dwt_max_level(n_analysis, pywt.Wavelet(config.wpt_wavelet).dec_len),
        )
        if level < 1:
            return float(n_samples * np.dtype(np.float32).itemsize / 1024.0)
        packet = pywt.WaveletPacket(
            data=np.zeros(n_analysis, dtype=np.float32),
            wavelet=config.wpt_wavelet,
            mode="symmetric",
            maxlevel=level,
        )
        coeff_bytes = sum(node.data.nbytes for node in packet.get_level(level, order="freq"))
        if method == "wavelet_packet_wiener_frames":
            hop = max(1, config.wpt_frame_hop)
            n_frames = max(1, int(math.ceil(max(n_samples - n_analysis, 0) / hop)) + 1)
            return float((coeff_bytes * n_frames * 2 + n_analysis * 3 * 4) / 1024.0)
        return float(coeff_bytes * 4 / 1024.0)
    if method.startswith("wavelet"):
        coeffs = pywt.wavedec(np.zeros(n_samples, dtype=np.float32), config.wavelet, level=config.wavelet_level)
        return float(sum(c.nbytes for c in coeffs) * 2 / 1024.0)
    return float(n_samples * np.dtype(np.float32).itemsize / 1024.0)


def stft_transform(x: np.ndarray, config: DenoiseConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return signal.stft(
        x,
        fs=config.sample_rate,
        window="hann",
        nperseg=config.n_fft,
        noverlap=config.n_fft - config.hop_length,
        nfft=config.n_fft,
        boundary="zeros",
        padded=True,
    )


def istft_transform(zxx: np.ndarray, length: int, config: DenoiseConfig) -> np.ndarray:
    _, out = signal.istft(
        zxx,
        fs=config.sample_rate,
        window="hann",
        nperseg=config.n_fft,
        noverlap=config.n_fft - config.hop_length,
        nfft=config.n_fft,
        boundary=True,
    )
    if len(out) < length:
        out = np.pad(out, (0, length - len(out)))
    return out[:length].astype(np.float32)


def spectral_subtraction(noisy: np.ndarray, config: DenoiseConfig) -> np.ndarray:
    _, _, zxx = stft_transform(noisy, config)
    mag = np.abs(zxx)
    phase = np.exp(1j * np.angle(zxx))
    noise_mag = estimate_noise_spectrum(mag, config, power_domain=False)
    clean_mag = np.maximum(mag - config.spectral_alpha * noise_mag, config.spectral_floor * mag)
    return istft_transform(clean_mag * phase, len(noisy), config)


def wiener_gain(noisy: np.ndarray, config: DenoiseConfig) -> np.ndarray:
    _, _, zxx = stft_transform(noisy, config)
    power = np.abs(zxx) ** 2
    noise_power = estimate_noise_spectrum(power, config, power_domain=True)
    speech_power = np.maximum(power - noise_power, 0.0)
    gain = speech_power / (speech_power + noise_power + 1e-12)
    gain = np.maximum(gain, config.wiener_floor)
    return istft_transform(gain * zxx, len(noisy), config)


def estimate_noise_spectrum(
    values: np.ndarray,
    config: DenoiseConfig,
    *,
    power_domain: bool,
) -> np.ndarray:
    if config.noise_estimator == "initial":
        noise_cols = max(
            1,
            int(math.ceil(config.noise_estimate_s / (config.hop_length / config.sample_rate))),
        )
        selected = values[:, :noise_cols]
    elif config.noise_estimator == "low_energy":
        quantile = float(np.clip(config.noise_quantile, 0.01, 1.0))
        frame_power = np.mean(values if power_domain else values**2, axis=0)
        n_select = max(1, int(math.ceil(quantile * values.shape[1])))
        indices = np.argpartition(frame_power, n_select - 1)[:n_select]
        selected = values[:, indices]
    else:
        raise ValueError(f"Estimador de ruido desconhecido: {config.noise_estimator}")
    return np.mean(selected, axis=1, keepdims=True)


def wavelet_denoise(noisy: np.ndarray, config: DenoiseConfig) -> np.ndarray:
    max_level = pywt.dwt_max_level(len(noisy), pywt.Wavelet(config.wavelet).dec_len)
    level = min(config.wavelet_level, max_level)
    coeffs = pywt.wavedec(noisy, config.wavelet, level=level, mode="symmetric")
    denoised_coeffs = [coeffs[0]]
    finest_sigma = np.median(np.abs(coeffs[-1])) / 0.6745 if coeffs[-1].size else 0.0
    for detail in coeffs[1:]:
        if config.wavelet_threshold_strategy == "global":
            sigma = finest_sigma
            threshold_length = len(noisy)
        elif config.wavelet_threshold_strategy == "per_scale":
            sigma = np.median(np.abs(detail)) / 0.6745 if detail.size else 0.0
            threshold_length = len(detail)
        else:
            raise ValueError(
                f"Estrategia de limiar Wavelet desconhecida: {config.wavelet_threshold_strategy}"
            )
        threshold = (
            config.wavelet_threshold_scale
            * sigma
            * math.sqrt(2 * math.log(max(threshold_length, 2)))
        )
        denoised_coeffs.append(pywt.threshold(detail, threshold, mode=config.wavelet_mode))
    out = pywt.waverec(denoised_coeffs, config.wavelet, mode="symmetric")
    if len(out) < len(noisy):
        out = np.pad(out, (0, len(noisy) - len(out)))
    return out[: len(noisy)].astype(np.float32)


def _rolling_quantile(values: np.ndarray, window: int, quantile: float) -> np.ndarray:
    window = max(1, int(window))
    if values.size == 0:
        return values.copy()
    if window == 1:
        return values.copy()
    padded = np.pad(values, (window - 1, 0), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, window_shape=window)
    return np.quantile(windows, quantile, axis=1)


def _smooth_series(values: np.ndarray, alpha: float) -> np.ndarray:
    alpha = float(np.clip(alpha, 0.0, 1.0))
    if values.size == 0 or alpha <= 0.0:
        return values.copy()
    smoothed = np.empty_like(values)
    smoothed[0] = values[0]
    for index in range(1, len(values)):
        smoothed[index] = (1.0 - alpha) * smoothed[index - 1] + alpha * values[index]
    return smoothed


def _estimate_wpt_noise_power(power: np.ndarray, config: DenoiseConfig) -> np.ndarray:
    quantile = float(np.clip(config.wpt_noise_quantile, 0.0, 1.0))
    if config.wpt_noise_tracking == "global_quantile":
        noise_power = np.full_like(power, np.quantile(power, quantile))
    elif config.wpt_noise_tracking == "rolling_quantile":
        noise_power = _rolling_quantile(power, config.wpt_noise_window, quantile)
    else:
        raise ValueError(f"Rastreamento WPT desconhecido: {config.wpt_noise_tracking}")
    return np.maximum(_smooth_series(noise_power, config.wpt_noise_smoothing), 1e-12)


def wavelet_packet_wiener_denoise(noisy: np.ndarray, config: DenoiseConfig) -> np.ndarray:
    noisy = np.nan_to_num(
        np.asarray(noisy, dtype=np.float32).reshape(-1),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    if noisy.size == 0:
        return noisy.copy()

    wavelet = pywt.Wavelet(config.wpt_wavelet)
    max_level = pywt.dwt_max_level(len(noisy), wavelet.dec_len)
    level = min(max(1, int(config.wpt_level)), max_level)
    if level < 1:
        return noisy.copy()

    packet = pywt.WaveletPacket(
        data=noisy,
        wavelet=wavelet,
        mode="symmetric",
        maxlevel=level,
    )
    denoised_packet = pywt.WaveletPacket(
        data=None,
        wavelet=wavelet,
        mode="symmetric",
        maxlevel=level,
    )
    gain_floor = float(np.clip(config.wpt_gain_floor, 0.0, 1.0))
    for node in packet.get_level(level, order="freq"):
        coeffs = np.asarray(node.data, dtype=np.float64)
        power = np.square(coeffs)
        noise_power = _estimate_wpt_noise_power(power, config)
        speech_power = np.maximum(power - noise_power, 0.0)
        gain = speech_power / (speech_power + noise_power + 1e-12)
        gain = np.clip(gain, gain_floor, 1.0)
        denoised_packet[node.path] = (coeffs * gain).astype(np.float32)

    out = denoised_packet.reconstruct(update=False)
    if len(out) < len(noisy):
        out = np.pad(out, (0, len(noisy) - len(out)))
    out = out[: len(noisy)]
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def _wpt_frame_noise_matrix(power: np.ndarray, config: DenoiseConfig) -> np.ndarray:
    quantile = float(np.clip(config.wpt_noise_quantile, 0.0, 1.0))
    if config.wpt_noise_tracking == "global_quantile":
        noise_power = np.quantile(power, quantile, axis=0, keepdims=True)
        noise_power = np.repeat(noise_power, power.shape[0], axis=0)
    elif config.wpt_noise_tracking == "rolling_quantile":
        columns = [
            _rolling_quantile(power[:, subband], config.wpt_noise_window, quantile)
            for subband in range(power.shape[1])
        ]
        noise_power = np.stack(columns, axis=1)
    else:
        raise ValueError(f"Rastreamento WPT desconhecido: {config.wpt_noise_tracking}")
    if config.wpt_noise_smoothing > 0.0:
        noise_power = np.stack(
            [
                _smooth_series(noise_power[:, subband], config.wpt_noise_smoothing)
                for subband in range(noise_power.shape[1])
            ],
            axis=1,
        )
    return np.maximum(noise_power, 1e-12)


def wavelet_packet_wiener_frame_denoise(noisy: np.ndarray, config: DenoiseConfig) -> np.ndarray:
    noisy = np.nan_to_num(
        np.asarray(noisy, dtype=np.float32).reshape(-1),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    if noisy.size == 0:
        return noisy.copy()

    frame_length = max(32, int(config.wpt_frame_length))
    hop = max(1, int(config.wpt_frame_hop))
    if hop > frame_length:
        raise ValueError("wpt_frame_hop deve ser menor ou igual a wpt_frame_length.")
    wavelet = pywt.Wavelet(config.wpt_wavelet)
    max_level = pywt.dwt_max_level(frame_length, wavelet.dec_len)
    level = min(max(1, int(config.wpt_level)), max_level)
    if level < 1:
        return noisy.copy()

    n_frames = max(1, int(math.ceil(max(len(noisy) - frame_length, 0) / hop)) + 1)
    padded_length = (n_frames - 1) * hop + frame_length
    padded = np.pad(noisy, (0, padded_length - len(noisy))).astype(np.float32)
    window = signal.windows.hann(frame_length, sym=False).astype(np.float32)
    if not np.any(window):
        window = np.ones(frame_length, dtype=np.float32)

    paths: list[str] | None = None
    coeffs_by_path: dict[str, list[np.ndarray]] = {}
    powers: list[list[float]] = []
    for frame_index in range(n_frames):
        start = frame_index * hop
        frame = padded[start : start + frame_length] * window
        packet = pywt.WaveletPacket(
            data=frame,
            wavelet=wavelet,
            mode="symmetric",
            maxlevel=level,
        )
        nodes = packet.get_level(level, order="freq")
        if paths is None:
            paths = [node.path for node in nodes]
            coeffs_by_path = {path: [] for path in paths}
        frame_powers: list[float] = []
        for node in nodes:
            coeffs = np.asarray(node.data, dtype=np.float64)
            coeffs_by_path[node.path].append(coeffs)
            frame_powers.append(float(np.mean(np.square(coeffs), dtype=np.float64)))
        powers.append(frame_powers)

    if paths is None:
        return noisy.copy()
    power = np.asarray(powers, dtype=np.float64)
    noise_power = _wpt_frame_noise_matrix(power, config)
    speech_power = np.maximum(power - noise_power, 0.0)
    gain = speech_power / (speech_power + noise_power + 1e-12)
    gain = np.clip(gain, float(np.clip(config.wpt_gain_floor, 0.0, 1.0)), 1.0)

    out = np.zeros(padded_length, dtype=np.float64)
    norm = np.zeros(padded_length, dtype=np.float64)
    synthesis_norm = np.square(window.astype(np.float64))
    for frame_index in range(n_frames):
        packet = pywt.WaveletPacket(
            data=None,
            wavelet=wavelet,
            mode="symmetric",
            maxlevel=level,
        )
        for subband_index, path in enumerate(paths):
            packet[path] = (coeffs_by_path[path][frame_index] * gain[frame_index, subband_index]).astype(
                np.float32
            )
        reconstructed = packet.reconstruct(update=False)[:frame_length]
        start = frame_index * hop
        out[start : start + frame_length] += reconstructed * window
        norm[start : start + frame_length] += synthesis_norm

    valid = norm > 1e-8
    out[valid] /= norm[valid]
    out[~valid] = padded[:padded_length][~valid]
    out = out[: len(noisy)]
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def process_method(method: str, noisy: np.ndarray, config: DenoiseConfig) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    if method == "noisy":
        processed = noisy.copy()
    elif method == "stft_subtraction":
        processed = spectral_subtraction(noisy, config)
    elif method == "stft_wiener":
        processed = wiener_gain(noisy, config)
    elif method == "wavelet_soft":
        processed = wavelet_denoise(noisy, config)
    elif method == "wavelet_packet_wiener":
        processed = wavelet_packet_wiener_denoise(noisy, config)
    elif method == "wavelet_packet_wiener_frames":
        processed = wavelet_packet_wiener_frame_denoise(noisy, config)
    else:
        raise ValueError(f"Unknown method: {method}")
    elapsed = time.perf_counter() - start
    return np.asarray(processed, dtype=np.float32), elapsed
