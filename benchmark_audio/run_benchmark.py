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
from scipy import signal

from .denoise import (
    DenoiseConfig,
    SAMPLE_RATE,
    estimate_memory_kb,
    make_noise,
    mix_at_snr,
    mse,
    normalize_peak,
    process_method,
    read_wav_mono,
    si_sdr,
    snr_db,
    write_wav,
)


DEFAULT_DURATION = 3.0
DEFAULT_SEED = 3527
ROOT = Path(__file__).resolve().parents[1]

FSDD_BASE_URL = (
    "https://raw.githubusercontent.com/Jakobovski/"
    "free-spoken-digit-dataset/master/recordings"
)
DEMO_SPEAKERS = ["jackson", "nicolas", "theo", "yweweler", "george"]
DEMO_DIGITS = list(range(10))
BENCHMARK_METHODS = ("noisy", "stft_subtraction", "stft_wiener", "wavelet_soft")
METHOD_ORDER = list(BENCHMARK_METHODS)
METHOD_LABELS = {
    "noisy": "Ruidoso",
    "stft_subtraction": "STFT subtracao",
    "stft_wiener": "STFT Wiener",
    "wavelet_soft": "Wavelet soft",
}
EXAMPLE_SIGNAL_ORDER = ["clean", "noisy", "stft_subtraction", "stft_wiener", "wavelet_soft"]


@dataclass(frozen=True)
class BenchmarkConfig(DenoiseConfig):
    duration_s: float = DEFAULT_DURATION
    seed: int = DEFAULT_SEED
    snrs_db: tuple[int, ...] = (-5, 0, 5, 10)
    noise_names: tuple[str, ...] = ("white", "pink", "hum", "impulsive")


def ensure_dirs(root: Path, results_dir: Path | None = None) -> dict[str, Path]:
    results_root = results_dir or root / "resultados"
    if not results_root.is_absolute():
        results_root = root / results_root
    paths = {
        "raw": root / "dados" / "raw" / "fsdd",
        "demo_clean": root / "dados" / "demo" / "clean",
        "tables": results_root / "tabelas",
        "figures": results_root / "figuras",
        "audio": results_root / "audio",
        "pgfplots": results_root / "pgfplots",
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


def collect_noise_files(noise_dir: Path, max_noises: int | None = None) -> list[Path]:
    files = sorted(path for path in noise_dir.glob("*.wav") if path.is_file())
    if max_noises is not None:
        files = files[:max_noises]
    if not files:
        raise FileNotFoundError(f"Nenhum WAV de ruido encontrado em {noise_dir}")
    return files


def noise_segment_from_file(
    noise_path: Path,
    duration_samples: int,
    config: BenchmarkConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    noise = read_wav_mono(noise_path, config.sample_rate)
    if len(noise) < duration_samples:
        repeats = math.ceil(duration_samples / max(len(noise), 1))
        noise = np.tile(noise, repeats)
    if len(noise) > duration_samples:
        max_start = len(noise) - duration_samples
        start = int(rng.integers(0, max_start + 1))
        noise = noise[start : start + duration_samples]
    else:
        noise = noise[:duration_samples]
    return normalize_peak(noise)


def export_summary_for_pgfplots(summary: pd.DataFrame, pgfplots_dir: Path) -> None:
    improvement = summary.pivot(
        index="snr_alvo_db",
        columns="metodo",
        values="melhoria_snr_media_db",
    ).reindex(columns=METHOD_ORDER)
    improvement.reset_index().to_csv(
        pgfplots_dir / "melhoria_snr.csv",
        index=False,
        encoding="utf-8",
        float_format="%.8g",
    )

    rtf = (
        summary.groupby("metodo", as_index=False)
        .agg(rtf_medio=("rtf_medio", "mean"))
        .set_index("metodo")
        .reindex(METHOD_ORDER)
        .reset_index()
    )
    rtf["metodo_rotulo"] = rtf["metodo"].map(METHOD_LABELS)
    rtf["rtf_medio_x1000"] = rtf["rtf_medio"] * 1000.0
    rtf.to_csv(
        pgfplots_dir / "rtf_por_metodo.csv",
        index=False,
        encoding="utf-8",
        float_format="%.8g",
    )


def export_waveforms_for_pgfplots(
    example: dict[str, np.ndarray],
    sample_rate: int,
    pgfplots_dir: Path,
    max_points: int = 650,
) -> None:
    available = [key for key in EXAMPLE_SIGNAL_ORDER if key in example]
    if not available:
        return

    n_samples = min(len(example[key]) for key in available)
    step = max(1, math.ceil(n_samples / max_points))
    idx = np.arange(0, n_samples, step, dtype=int)
    if idx[-1] != n_samples - 1:
        idx = np.append(idx, n_samples - 1)

    data: dict[str, np.ndarray] = {"tempo_s": idx / sample_rate}
    offsets = {
        "clean": 3.0,
        "noisy": 1.0,
        "stft_subtraction": -1.0,
        "stft_wiener": -3.0,
        "wavelet_soft": -5.0,
    }
    for key in available:
        values = np.asarray(example[key][:n_samples], dtype=np.float32)[idx]
        data[key] = values
        data[f"{key}_empilhado"] = values + offsets[key]

    pd.DataFrame(data).to_csv(
        pgfplots_dir / "formas_onda_exemplo.csv",
        index=False,
        encoding="utf-8",
        float_format="%.8g",
    )


def reduced_spectrogram(
    x: np.ndarray,
    sample_rate: int,
    n_time: int = 40,
    n_freq: int = 48,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    freqs, times, spec = signal.spectrogram(
        x,
        fs=sample_rate,
        window="hann",
        nperseg=512,
        noverlap=384,
        mode="magnitude",
        scaling="spectrum",
    )
    freq_idx = np.unique(np.round(np.linspace(0, len(freqs) - 1, n_freq)).astype(int))
    time_idx = np.unique(np.round(np.linspace(0, len(times) - 1, n_time)).astype(int))
    selected = spec[np.ix_(freq_idx, time_idx)]
    power_db = 20.0 * np.log10(selected + 1e-10)
    return freqs[freq_idx], times[time_idx], power_db


def export_spectrograms_for_pgfplots(
    example: dict[str, np.ndarray],
    sample_rate: int,
    pgfplots_dir: Path,
) -> None:
    selected_methods = ["clean", "noisy", "stft_subtraction", "wavelet_soft"]
    spectrograms: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    global_peak = -np.inf

    for key in selected_methods:
        if key not in example:
            continue
        freqs, times, power_db = reduced_spectrogram(example[key], sample_rate)
        spectrograms[key] = (freqs, times, power_db)
        global_peak = max(global_peak, float(np.max(power_db)))

    if not spectrograms:
        return

    db_floor = -70.0
    mesh_cols = 0
    mesh_rows = 0
    manifest_rows = []
    for key, (freqs, times, power_db) in spectrograms.items():
        relative = np.clip(power_db - global_peak, db_floor, 0.0)
        mesh_cols = len(times)
        mesh_rows = len(freqs)
        rows = []
        for f_idx, freq_hz in enumerate(freqs):
            for t_idx, time_s in enumerate(times):
                rows.append(
                    {
                        "tempo_s": float(time_s),
                        "freq_khz": float(freq_hz / 1000.0),
                        "potencia_db_rel": float(relative[f_idx, t_idx]),
                    }
                )
        filename = f"espectrograma_{key}.csv"
        pd.DataFrame(rows).to_csv(
            pgfplots_dir / filename,
            index=False,
            encoding="utf-8",
            float_format="%.8g",
        )
        manifest_rows.append(
            {
                "metodo": key,
                "metodo_rotulo": METHOD_LABELS.get(key, "Fala limpa"),
                "arquivo": filename,
                "n_tempos": mesh_cols,
                "n_frequencias": mesh_rows,
                "piso_db_rel": db_floor,
            }
        )

    pd.DataFrame(manifest_rows).to_csv(
        pgfplots_dir / "espectrogramas_manifesto.csv",
        index=False,
        encoding="utf-8",
    )
    (pgfplots_dir / "parametros_espectrograma.tex").write_text(
        "\n".join(
            [
                f"\\newcommand{{\\pgfSpectrogramCols}}{{{mesh_cols}}}",
                f"\\newcommand{{\\pgfSpectrogramRows}}{{{mesh_rows}}}",
                f"\\newcommand{{\\pgfSpectrogramDbMin}}{{{int(db_floor)}}}",
                "\\newcommand{\\pgfSpectrogramDbMax}{0}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_pgfplots_readme(pgfplots_dir: Path, config: BenchmarkConfig) -> None:
    lines = [
        "# Dados leves para graficos nativos em LaTeX",
        "",
        "Esta pasta e gerada por `python -m benchmark_audio.run_benchmark` ou pelo modo",
        "`python -m benchmark_audio.run_benchmark --export-pgfplots-only`.",
        "",
        "O Python calcula metricas, sinais decimados e matrizes reduzidas; o PDF final monta os graficos com `pgfplots` e `tikzpicture`.",
        "",
        "Arquivos principais:",
        "",
        "- `melhoria_snr.csv`: barras agrupadas de melhoria media de SNR por SNR alvo e metodo.",
        "- `rtf_por_metodo.csv`: RTF medio por metodo, tambem em escala `rtf_medio_x1000` para leitura no eixo vertical.",
        "- `formas_onda_exemplo.csv`: exemplo temporal decimado, com sinais originais e versoes empilhadas para plotagem.",
        "- `espectrograma_*.csv`: matrizes reduzidas de espectrograma, em dB relativo ao pico global do exemplo.",
        "- `parametros_espectrograma.tex`: macros com dimensoes da malha usada por `matrix plot*`.",
        "- `espectrogramas_manifesto.csv`: metadados dos espectrogramas exportados.",
        "",
        "Parametros do benchmark associado:",
        "",
        f"- taxa de amostragem: {config.sample_rate} Hz;",
        f"- duracao: {config.duration_s:.2f} s;",
        f"- semente: {config.seed};",
        f"- STFT: `n_fft={config.n_fft}`, `hop_length={config.hop_length}`;",
        f"- Wavelet: `{config.wavelet}`, nivel {config.wavelet_level}, limiarizacao `{config.wavelet_mode}`.",
        "",
        "Os espectrogramas sao reduzidos de proposito para manter a compilacao LaTeX confortavel.",
        "Eles servem como visualizacao preliminar, nao como substituto dos CSVs completos de metricas.",
        "",
    ]
    (pgfplots_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def load_example_audio_for_pgfplots(audio_dir: Path, sample_rate: int) -> dict[str, np.ndarray]:
    example = {}
    for key in EXAMPLE_SIGNAL_ORDER:
        path = audio_dir / f"exemplo_{key}.wav"
        if path.exists():
            example[key] = read_wav_mono(path, sample_rate)
    return example


def export_pgfplots_assets(
    summary: pd.DataFrame,
    example: dict[str, np.ndarray] | None,
    config: BenchmarkConfig,
    paths: dict[str, Path],
) -> None:
    pgfplots_dir = paths["pgfplots"]
    pgfplots_dir.mkdir(parents=True, exist_ok=True)
    export_summary_for_pgfplots(summary, pgfplots_dir)
    if example:
        export_waveforms_for_pgfplots(example, config.sample_rate, pgfplots_dir)
        export_spectrograms_for_pgfplots(example, config.sample_rate, pgfplots_dir)
    write_pgfplots_readme(pgfplots_dir, config)


def export_pgfplots_from_existing(config: BenchmarkConfig, results_dir: Path | None = None) -> None:
    paths = ensure_dirs(ROOT, results_dir=results_dir)
    summary_path = paths["tables"] / "resumo_por_metodo_snr.csv"
    if not summary_path.exists():
        raise FileNotFoundError("Resumo nao encontrado. Rode o benchmark completo primeiro.")
    summary = pd.read_csv(summary_path)
    example = load_example_audio_for_pgfplots(paths["audio"], config.sample_rate)
    export_pgfplots_assets(summary, example, config, paths)


def plot_metric_bars(summary: pd.DataFrame, figures_dir: Path) -> None:
    pivot = summary.pivot(index="snr_alvo_db", columns="metodo", values="melhoria_snr_media_db")
    pivot = pivot.reindex(columns=METHOD_ORDER)
    ax = pivot.rename(columns=METHOD_LABELS).plot(kind="bar", figsize=(9, 5))
    ax.set_title("Melhoria media de SNR por metodo")
    ax.set_xlabel("SNR de entrada alvo (dB)")
    ax.set_ylabel("Melhoria de SNR (dB)")
    ax.legend(title="Metodo")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(figures_dir / "barras_melhoria_snr.png", dpi=180)
    plt.close()

    pivot_rtf = summary.pivot(index="snr_alvo_db", columns="metodo", values="rtf_medio")
    pivot_rtf = pivot_rtf.reindex(columns=METHOD_ORDER)
    ax = pivot_rtf.rename(columns=METHOD_LABELS).plot(kind="bar", figsize=(9, 5))
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


def run_benchmark(
    config: BenchmarkConfig,
    prepare_demo_data: bool,
    noise_dir: Path | None = None,
    max_noises: int | None = None,
    results_dir: Path | None = None,
) -> None:
    paths = ensure_dirs(ROOT, results_dir=results_dir)
    if prepare_demo_data:
        speech_paths = prepare_demo_speech(paths, config)
    else:
        speech_paths = sorted(paths["demo_clean"].glob("*.wav"))
        if not speech_paths:
            raise FileNotFoundError("No demo speech found. Run with --prepare-demo-data first.")

    rng = np.random.default_rng(config.seed)
    methods = list(BENCHMARK_METHODS)
    duration_samples = int(config.duration_s * config.sample_rate)
    if not config.snrs_db:
        raise ValueError("At least one SNR value is required.")
    if noise_dir is not None:
        noise_items: list[str | Path] = collect_noise_files(noise_dir, max_noises=max_noises)
    elif not config.noise_names:
        raise ValueError("At least one noise type is required.")
    else:
        noise_items = list(config.noise_names)
    first_noise_item = noise_items[0]
    example_noise_name = first_noise_item.stem if isinstance(first_noise_item, Path) else first_noise_item
    example_target_snr = config.snrs_db[1] if len(config.snrs_db) > 1 else config.snrs_db[0]
    rows = []
    example_signals: dict[str, np.ndarray] | None = None
    example_selected = False

    for speech_path in speech_paths:
        clean = read_wav_mono(speech_path, config.sample_rate)
        if len(clean) < duration_samples:
            clean = np.pad(clean, (0, duration_samples - len(clean)))
        clean = clean[:duration_samples]
        clean = normalize_peak(clean, peak=0.85)
        for noise_item in noise_items:
            if isinstance(noise_item, Path):
                noise_name = noise_item.stem
                base_noise = noise_segment_from_file(noise_item, len(clean), config, rng)
            else:
                noise_name = noise_item
                base_noise = make_noise(noise_name, len(clean), config.sample_rate, rng)
            for target_snr in config.snrs_db:
                noisy, scaled_noise = mix_at_snr(clean, base_noise, target_snr)
                observed_input_snr = snr_db(clean, noisy)
                current_example: dict[str, np.ndarray] | None = None
                if (
                    not example_selected
                    and speech_path.stem == speech_paths[0].stem
                    and noise_name == example_noise_name
                    and target_snr == example_target_snr
                ):
                    current_example = {"clean": clean, "noisy": noisy, "noise": scaled_noise}
                for method in methods:
                    processed, elapsed = process_method(method, noisy, config)
                    output_snr = snr_db(clean, processed)
                    duration_s = len(clean) / config.sample_rate
                    rows.append(
                        {
                            "amostra": speech_path.stem,
                            "ruido": noise_name,
                            "grupo_ruido": noise_name.split("_", 1)[0].upper(),
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
    noise_group_summary = (
        metrics.groupby(["grupo_ruido", "metodo", "snr_alvo_db"], as_index=False)
        .agg(
            n_condicoes=("melhoria_snr_db", "size"),
            snr_saida_medio_db=("snr_saida_db", "mean"),
            melhoria_snr_media_db=("melhoria_snr_db", "mean"),
            melhoria_snr_desvio_db=("melhoria_snr_db", "std"),
            si_sdr_medio_db=("si_sdr_db", "mean"),
            rtf_medio=("rtf", "mean"),
        )
        .sort_values(["grupo_ruido", "snr_alvo_db", "metodo"])
    )
    noise_group_summary.to_csv(
        paths["tables"] / "resumo_por_grupo_ruido.csv",
        index=False,
        encoding="utf-8",
    )
    latex_table_from_summary(summary, paths["tables"] / "resumo_resultados_latex.tex")
    hardware_viability_table(paths["tables"])
    plot_metric_bars(summary, paths["figures"])

    if example_signals is not None:
        plot_example(example_signals, config.sample_rate, paths["figures"])
        for key, data in example_signals.items():
            if key in {"clean", "noisy", "stft_subtraction", "stft_wiener", "wavelet_soft"}:
                write_wav(paths["audio"] / f"exemplo_{key}.wav", normalize_peak(data), config.sample_rate)

    export_pgfplots_assets(summary, example_signals, config, paths)

    noise_origin = (
        f"Arquivos WAV locais em {noise_dir}"
        if noise_dir is not None
        else "Gerados por script: branco, rosa, hum e impulsivo."
    )
    metadata = {
        "config": asdict(config),
        "n_condicoes": int(len(metrics)),
        "n_amostras_fala": int(len(speech_paths)),
        "origem_fala": "Free Spoken Digit Dataset (FSDD)",
        "ruidos": noise_origin,
        "origem_ruido": noise_origin,
        "n_ruidos": int(len(noise_items)),
        "ruidos_efetivos": [
            item.stem if isinstance(item, Path) else item
            for item in noise_items
        ],
        "diretorio_resultados": str(paths["tables"].parent),
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
    parser.add_argument(
        "--noise-dir",
        type=Path,
        help="Pasta opcional com WAVs de ruido real. Quando usada, substitui os ruidos sinteticos.",
    )
    parser.add_argument("--max-noises", type=int, help="Limita a quantidade de WAVs de ruido lidos de --noise-dir.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        help="Diretorio de resultados. Padrao: resultados/. Use resultados/demand para uma rodada isolada.",
    )
    parser.add_argument(
        "--export-pgfplots-only",
        action="store_true",
        help="Regera apenas dados leves para pgfplots a partir dos CSVs e WAVs ja existentes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BenchmarkConfig(duration_s=args.duration, seed=args.seed, snrs_db=tuple(args.snrs))
    if args.export_pgfplots_only:
        export_pgfplots_from_existing(config, results_dir=args.results_dir)
    else:
        run_benchmark(
            config=config,
            prepare_demo_data=args.prepare_demo_data,
            noise_dir=args.noise_dir,
            max_noises=args.max_noises,
            results_dir=args.results_dir,
        )


if __name__ == "__main__":
    main()
