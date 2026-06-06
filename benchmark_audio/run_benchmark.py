from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
from urllib.error import HTTPError, URLError
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pywt
from scipy import signal
from scipy.io import wavfile


SAMPLE_RATE = 16_000
DEFAULT_DURATION = 3.0
DEFAULT_SEED = 3527
ROOT = Path(__file__).resolve().parents[1]

FSDD_BASE_URL = (
    "https://raw.githubusercontent.com/Jakobovski/"
    "free-spoken-digit-dataset/master/recordings"
)
DEMO_SPEAKERS = ["jackson", "nicolas", "theo", "yweweler", "george"]
DEMO_DIGITS = list(range(10))


@dataclass(frozen=True)
class BenchmarkConfig:
    sample_rate: int = SAMPLE_RATE
    duration_s: float = DEFAULT_DURATION
    seed: int = DEFAULT_SEED
    snrs_db: tuple[int, ...] = (-5, 0, 5, 10)
    noise_names: tuple[str, ...] = ("white", "pink", "hum", "impulsive")
    n_fft: int = 512
    hop_length: int = 160
    noise_estimate_s: float = 0.25
    spectral_alpha: float = 1.2
    spectral_floor: float = 0.03
    wiener_floor: float = 0.05
    wavelet: str = "db4"
    wavelet_level: int = 5
    wavelet_mode: str = "soft"


def ensure_dirs(root: Path) -> dict[str, Path]:
    paths = {
        "raw": root / "dados" / "raw" / "fsdd",
        "demo_clean": root / "dados" / "demo" / "clean",
        "tables": root / "resultados" / "tabelas",
        "figures": root / "resultados" / "figuras",
        "audio": root / "resultados" / "audio",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def download_file(url: str, target: Path, retries: int = 4) -> None:
    if target.exists() and target.stat().st_size > 0:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "ptc3527-benchmark/0.1"})
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                target.write_bytes(response.read())
            return
        except (HTTPError, URLError, ConnectionResetError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Could not download {url}: {last_error}") from last_error


def prepare_demo_speech(paths: dict[str, Path], config: BenchmarkConfig) -> list[Path]:
    """Download tiny public speech files and concatenate each speaker to 3 s."""
    for speaker in DEMO_SPEAKERS:
        for digit in DEMO_DIGITS:
            name = f"{digit}_{speaker}_0.wav"
            download_file(f"{FSDD_BASE_URL}/{name}", paths["raw"] / name)

    prepared: list[Path] = []
    target_len = int(config.duration_s * config.sample_rate)
    for speaker in DEMO_SPEAKERS:
        chunks = [np.zeros(int(0.30 * config.sample_rate), dtype=np.float32)]
        for digit in DEMO_DIGITS:
            wav_path = paths["raw"] / f"{digit}_{speaker}_0.wav"
            chunks.append(read_wav_mono(wav_path, config.sample_rate))
            chunks.append(np.zeros(int(0.05 * config.sample_rate), dtype=np.float32))
        merged = np.concatenate(chunks)
        if len(merged) < target_len:
            repeats = math.ceil(target_len / len(merged))
            merged = np.tile(merged, repeats)
        merged = merged[:target_len]
        merged = normalize_peak(merged, peak=0.85)
        out = paths["demo_clean"] / f"speech_{speaker}.wav"
        write_wav(out, merged, config.sample_rate)
        prepared.append(out)
    return prepared


def normalize_peak(x: np.ndarray, peak: float = 0.95) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    max_abs = float(np.max(np.abs(x))) if x.size else 0.0
    if max_abs < 1e-12:
        return x.copy()
    return (x / max_abs * peak).astype(np.float32)


def read_wav_mono(path: Path, target_sr: int) -> np.ndarray:
    sr, data = wavfile.read(path)
    data = np.asarray(data)
    if data.ndim == 2:
        data = data.mean(axis=1)
    if np.issubdtype(data.dtype, np.integer):
        scale = float(np.iinfo(data.dtype).max)
        data = data.astype(np.float32) / scale
    else:
        data = data.astype(np.float32)
    if sr != target_sr:
        gcd = math.gcd(int(sr), int(target_sr))
        data = signal.resample_poly(data, target_sr // gcd, sr // gcd).astype(np.float32)
    return normalize_peak(data, peak=0.95)


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


def mix_at_snr(clean: np.ndarray, noise: np.ndarray, snr_db: float) -> tuple[np.ndarray, np.ndarray]:
    clean_rms = rms(clean)
    noise_rms = rms(noise)
    target_noise_rms = clean_rms / (10 ** (snr_db / 20.0))
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


def estimate_memory_kb(method: str, n_samples: int, config: BenchmarkConfig) -> float:
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
    if method.startswith("wavelet"):
        coeffs = pywt.wavedec(np.zeros(n_samples, dtype=np.float32), config.wavelet, level=config.wavelet_level)
        return float(sum(c.nbytes for c in coeffs) * 2 / 1024.0)
    return float(n_samples * np.dtype(np.float32).itemsize / 1024.0)


def stft_transform(x: np.ndarray, config: BenchmarkConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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


def istft_transform(zxx: np.ndarray, length: int, config: BenchmarkConfig) -> np.ndarray:
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


def spectral_subtraction(noisy: np.ndarray, config: BenchmarkConfig) -> np.ndarray:
    _, times, zxx = stft_transform(noisy, config)
    mag = np.abs(zxx)
    phase = np.exp(1j * np.angle(zxx))
    noise_cols = max(1, int(math.ceil(config.noise_estimate_s / (config.hop_length / config.sample_rate))))
    noise_mag = np.mean(mag[:, :noise_cols], axis=1, keepdims=True)
    clean_mag = np.maximum(mag - config.spectral_alpha * noise_mag, config.spectral_floor * mag)
    return istft_transform(clean_mag * phase, len(noisy), config)


def wiener_gain(noisy: np.ndarray, config: BenchmarkConfig) -> np.ndarray:
    _, _, zxx = stft_transform(noisy, config)
    power = np.abs(zxx) ** 2
    noise_cols = max(1, int(math.ceil(config.noise_estimate_s / (config.hop_length / config.sample_rate))))
    noise_power = np.mean(power[:, :noise_cols], axis=1, keepdims=True)
    speech_power = np.maximum(power - noise_power, 0.0)
    gain = speech_power / (speech_power + noise_power + 1e-12)
    gain = np.maximum(gain, config.wiener_floor)
    return istft_transform(gain * zxx, len(noisy), config)


def wavelet_denoise(noisy: np.ndarray, config: BenchmarkConfig) -> np.ndarray:
    max_level = pywt.dwt_max_level(len(noisy), pywt.Wavelet(config.wavelet).dec_len)
    level = min(config.wavelet_level, max_level)
    coeffs = pywt.wavedec(noisy, config.wavelet, level=level, mode="symmetric")
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745 if coeffs[-1].size else 0.0
    threshold = sigma * math.sqrt(2 * math.log(len(noisy)))
    denoised_coeffs = [coeffs[0]]
    for detail in coeffs[1:]:
        denoised_coeffs.append(pywt.threshold(detail, threshold, mode=config.wavelet_mode))
    out = pywt.waverec(denoised_coeffs, config.wavelet, mode="symmetric")
    if len(out) < len(noisy):
        out = np.pad(out, (0, len(noisy) - len(out)))
    return out[: len(noisy)].astype(np.float32)


def process_method(method: str, clean: np.ndarray, noisy: np.ndarray, config: BenchmarkConfig) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    if method == "noisy":
        processed = noisy.copy()
    elif method == "stft_subtraction":
        processed = spectral_subtraction(noisy, config)
    elif method == "stft_wiener":
        processed = wiener_gain(noisy, config)
    elif method == "wavelet_soft":
        processed = wavelet_denoise(noisy, config)
    else:
        raise ValueError(f"Unknown method: {method}")
    elapsed = time.perf_counter() - start
    return np.asarray(processed, dtype=np.float32), elapsed


def plot_metric_bars(summary: pd.DataFrame, figures_dir: Path) -> None:
    method_order = ["noisy", "stft_subtraction", "stft_wiener", "wavelet_soft"]
    labels = {
        "noisy": "Ruidoso",
        "stft_subtraction": "STFT subtracao",
        "stft_wiener": "STFT Wiener",
        "wavelet_soft": "Wavelet soft",
    }

    pivot = summary.pivot(index="snr_alvo_db", columns="metodo", values="melhoria_snr_media_db")
    pivot = pivot.reindex(columns=method_order)
    ax = pivot.rename(columns=labels).plot(kind="bar", figsize=(9, 5))
    ax.set_title("Melhoria media de SNR por metodo")
    ax.set_xlabel("SNR de entrada alvo (dB)")
    ax.set_ylabel("Melhoria de SNR (dB)")
    ax.legend(title="Metodo")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / "barras_melhoria_snr.png", dpi=180)
    plt.close()

    pivot_rtf = summary.pivot(index="snr_alvo_db", columns="metodo", values="rtf_medio")
    pivot_rtf = pivot_rtf.reindex(columns=method_order)
    ax = pivot_rtf.rename(columns=labels).plot(kind="bar", figsize=(9, 5))
    ax.set_title("Fator de tempo real medio por metodo")
    ax.set_xlabel("SNR de entrada alvo (dB)")
    ax.set_ylabel("RTF = tempo de processamento / duracao")
    ax.legend(title="Metodo")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / "barras_rtf.png", dpi=180)
    plt.close()


def plot_example(example: dict[str, np.ndarray], sample_rate: int, figures_dir: Path) -> None:
    names = [
        ("clean", "Limpa"),
        ("noisy", "Ruidosa"),
        ("stft_subtraction", "STFT subtracao"),
        ("wavelet_soft", "Wavelet soft"),
    ]
    t = np.arange(len(example["clean"])) / sample_rate
    fig, axes = plt.subplots(len(names), 1, figsize=(10, 7), sharex=True)
    for ax, (key, label) in zip(axes, names):
        ax.plot(t, example[key], linewidth=0.7)
        ax.set_title(label)
        ax.set_ylabel("Amplitude")
        ax.grid(alpha=0.25)
    axes[-1].set_xlabel("Tempo (s)")
    fig.suptitle("Exemplo de forma de onda")
    plt.tight_layout()
    plt.savefig(figures_dir / "exemplo_formas_onda.png", dpi=180)
    plt.close()

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, sharey=True)
    for ax, (key, label) in zip(axes.ravel(), names):
        _, _, _, im = ax.specgram(
            example[key],
            NFFT=512,
            Fs=sample_rate,
            noverlap=384,
            cmap="magma",
        )
        ax.set_title(label)
        ax.set_xlabel("Tempo (s)")
        ax.set_ylabel("Frequencia (Hz)")
    fig.colorbar(im, ax=axes.ravel().tolist(), label="Potencia (dB)")
    fig.suptitle("Exemplo de espectrograma")
    plt.savefig(figures_dir / "exemplo_espectrogramas.png", dpi=180, bbox_inches="tight")
    plt.close()


def hardware_viability_table(tables_dir: Path) -> pd.DataFrame:
    rows = [
        {
            "plataforma": "PC",
            "ram_flash": "GBs de RAM; armazenamento amplo",
            "ponto_flutuante": "Sim, alto desempenho",
            "audio_io": "Bibliotecas maduras e arquivos WAV",
            "portabilidade": "Referencia de validacao",
            "risco": "Baixo",
            "recomendacao": "Manter como ambiente de benchmark e geracao de referencia.",
        },
        {
            "plataforma": "Raspberry Pi",
            "ram_flash": "Centenas de MB a varios GB",
            "ponto_flutuante": "Sim",
            "audio_io": "Linux, USB audio e I2S disponiveis",
            "portabilidade": "Python/C++ viavel",
            "risco": "Medio",
            "recomendacao": "Primeira plataforma embarcada plausivel para tempo real.",
        },
        {
            "plataforma": "ESP32/ESP32-S3",
            "ram_flash": "Centenas de KB de SRAM; flash em MB",
            "ponto_flutuante": "Limitado; exige cuidado",
            "audio_io": "I2S disponivel em placas adequadas",
            "portabilidade": "Requer C/C++, buffers pequenos e simplificacao",
            "risco": "Alto",
            "recomendacao": "Avaliar depois de reduzir dependencias e memoria do metodo.",
        },
        {
            "plataforma": "Arduino Uno R3",
            "ram_flash": "2 KB SRAM; 32 KB flash",
            "ponto_flutuante": "Sem FPU",
            "audio_io": "ADC simples; sem I2S nativo",
            "portabilidade": "FFT/DWT para voz exige buffers e coeficientes grandes demais",
            "risco": "Muito alto",
            "recomendacao": "Impraticavel para STFT/Wavelet de voz em tempo real sem simplificacoes severas ou hardware externo.",
        },
    ]
    df = pd.DataFrame(rows)
    df.to_csv(tables_dir / "viabilidade_embarcada.csv", index=False, encoding="utf-8")
    return df


def latex_table_from_summary(summary: pd.DataFrame, path: Path) -> None:
    keep = summary[
        summary["metodo"].isin(["noisy", "stft_subtraction", "stft_wiener", "wavelet_soft"])
        & summary["snr_alvo_db"].isin([-5, 0, 5, 10])
    ].copy()
    keep["metodo"] = keep["metodo"].map(
        {
            "noisy": "Ruidoso",
            "stft_subtraction": "STFT subtracao",
            "stft_wiener": "STFT Wiener",
            "wavelet_soft": "Wavelet soft",
        }
    )
    keep = keep.sort_values(["snr_alvo_db", "metodo"])
    cols = [
        "snr_alvo_db",
        "metodo",
        "snr_saida_medio_db",
        "melhoria_snr_media_db",
        "si_sdr_medio_db",
        "rtf_medio",
    ]
    lines = [
        "\\begin{tabular}{rlrrrr}",
        "\\toprule",
        "SNR alvo (dB) & Metodo & SNR saida (dB) & Melhoria (dB) & SI-SDR (dB) & RTF \\\\",
        "\\midrule",
    ]
    for row in keep[cols].itertuples(index=False):
        lines.append(
            f"{int(row.snr_alvo_db)} & {row.metodo} & "
            f"{row.snr_saida_medio_db:.2f} & {row.melhoria_snr_media_db:.2f} & "
            f"{row.si_sdr_medio_db:.2f} & {row.rtf_medio:.4f} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run_benchmark(config: BenchmarkConfig, prepare_demo_data: bool) -> None:
    paths = ensure_dirs(ROOT)
    if prepare_demo_data:
        speech_paths = prepare_demo_speech(paths, config)
    else:
        speech_paths = sorted(paths["demo_clean"].glob("*.wav"))
        if not speech_paths:
            raise FileNotFoundError("No demo speech found. Run with --prepare-demo-data first.")

    rng = np.random.default_rng(config.seed)
    methods = ["noisy", "stft_subtraction", "stft_wiener", "wavelet_soft"]
    duration_samples = int(config.duration_s * config.sample_rate)
    rows = []
    example_signals: dict[str, np.ndarray] | None = None
    example_selected = False

    for speech_path in speech_paths:
        clean = read_wav_mono(speech_path, config.sample_rate)
        if len(clean) < duration_samples:
            clean = np.pad(clean, (0, duration_samples - len(clean)))
        clean = clean[:duration_samples]
        clean = normalize_peak(clean, peak=0.85)
        for noise_name in config.noise_names:
            base_noise = make_noise(noise_name, len(clean), config.sample_rate, rng)
            for target_snr in config.snrs_db:
                noisy, scaled_noise = mix_at_snr(clean, base_noise, target_snr)
                observed_input_snr = snr_db(clean, noisy)
                current_example: dict[str, np.ndarray] | None = None
                if (
                    not example_selected
                    and speech_path.stem == speech_paths[0].stem
                    and noise_name == config.noise_names[0]
                    and target_snr == config.snrs_db[1]
                ):
                    current_example = {"clean": clean, "noisy": noisy, "noise": scaled_noise}
                for method in methods:
                    processed, elapsed = process_method(method, clean, noisy, config)
                    output_snr = snr_db(clean, processed)
                    duration_s = len(clean) / config.sample_rate
                    rows.append(
                        {
                            "amostra": speech_path.stem,
                            "ruido": noise_name,
                            "snr_alvo_db": target_snr,
                            "snr_entrada_observado_db": observed_input_snr,
                            "metodo": method,
                            "snr_saida_db": output_snr,
                            "melhoria_snr_db": output_snr - observed_input_snr,
                            "mse": mse(clean, processed),
                            "si_sdr_db": si_sdr(clean, processed),
                            "tempo_processamento_s": elapsed,
                            "duracao_audio_s": duration_s,
                            "rtf": elapsed / duration_s,
                            "latencia_algoritmica_ms": (
                                0.0 if method == "noisy" else config.n_fft / config.sample_rate * 1000.0
                            ),
                            "memoria_aproximada_kb": estimate_memory_kb(method, len(clean), config),
                        }
                    )
                    if current_example is not None:
                        current_example[method] = processed
                if current_example is not None:
                    example_signals = current_example
                    example_selected = True

    metrics = pd.DataFrame(rows)
    metrics.to_csv(paths["tables"] / "metricas_por_condicao.csv", index=False, encoding="utf-8")
    summary = (
        metrics.groupby(["metodo", "snr_alvo_db"], as_index=False)
        .agg(
            snr_saida_medio_db=("snr_saida_db", "mean"),
            melhoria_snr_media_db=("melhoria_snr_db", "mean"),
            mse_medio=("mse", "mean"),
            si_sdr_medio_db=("si_sdr_db", "mean"),
            tempo_medio_s=("tempo_processamento_s", "mean"),
            rtf_medio=("rtf", "mean"),
            memoria_media_kb=("memoria_aproximada_kb", "mean"),
        )
        .sort_values(["snr_alvo_db", "metodo"])
    )
    summary.to_csv(paths["tables"] / "resumo_por_metodo_snr.csv", index=False, encoding="utf-8")
    latex_table_from_summary(summary, paths["tables"] / "resumo_resultados_latex.tex")
    hardware_viability_table(paths["tables"])
    plot_metric_bars(summary, paths["figures"])

    if example_signals is not None:
        plot_example(example_signals, config.sample_rate, paths["figures"])
        for key, data in example_signals.items():
            if key in {"clean", "noisy", "stft_subtraction", "stft_wiener", "wavelet_soft"}:
                write_wav(paths["audio"] / f"exemplo_{key}.wav", normalize_peak(data), config.sample_rate)

    metadata = {
        "config": asdict(config),
        "n_condicoes": int(len(metrics)),
        "n_amostras_fala": int(len(speech_paths)),
        "origem_fala": "Free Spoken Digit Dataset (FSDD)",
        "ruidos": "Gerados por script: branco, rosa, hum e impulsivo.",
    }
    (paths["tables"] / "metadata_benchmark.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark preliminar STFT/Wavelet para voz ruidosa.")
    parser.add_argument("--prepare-demo-data", action="store_true", help="Baixa e prepara amostras publicas pequenas.")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="Duracao de cada trecho em segundos.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Semente aleatoria.")
    parser.add_argument("--snrs", type=int, nargs="+", default=[-5, 0, 5, 10], help="SNRs de entrada em dB.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BenchmarkConfig(duration_s=args.duration, seed=args.seed, snrs_db=tuple(args.snrs))
    run_benchmark(config=config, prepare_demo_data=args.prepare_demo_data)


if __name__ == "__main__":
    main()
