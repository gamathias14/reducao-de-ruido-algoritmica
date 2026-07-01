from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from realtime_audio.process_wav_rnnoise import process_wav as process_wav_rnnoise


SCRIPT_VERSION = 1


def run_subprocess(args: Sequence[str | Path], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(arg) for arg in args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Comando falhou com codigo "
            f"{result.returncode}:\nCOMANDO: {' '.join(str(arg) for arg in args)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def run_ffmpeg(args: list[str | Path]) -> subprocess.CompletedProcess[str]:
    return run_subprocess(["ffmpeg", "-hide_banner", "-nostats", *args])


def parse_loudnorm_json(stderr: str) -> dict[str, Any]:
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Nao foi possivel encontrar JSON do filtro loudnorm.")
    return json.loads(stderr[start : end + 1])


def join_filters(filters: Sequence[str]) -> str:
    return ",".join(filter(None, filters))


def loudnorm_base(target_i: float, target_lra: float, target_tp: float) -> str:
    return f"loudnorm=I={target_i}:LRA={target_lra}:TP={target_tp}:print_format=json"


def loudnorm_second_pass(
    measured: dict[str, Any],
    target_i: float,
    target_lra: float,
    target_tp: float,
) -> str:
    return ":".join(
        [
            f"loudnorm=I={target_i}",
            f"LRA={target_lra}",
            f"TP={target_tp}",
            f"measured_I={measured['input_i']}",
            f"measured_LRA={measured['input_lra']}",
            f"measured_TP={measured['input_tp']}",
            f"measured_thresh={measured['input_thresh']}",
            f"offset={measured['target_offset']}",
            "linear=true",
            "print_format=json",
        ]
    )


def measure_loudnorm(
    path: Path,
    *,
    target_i: float,
    target_lra: float,
    target_tp: float,
    pre_filters: Sequence[str] = (),
) -> dict[str, Any]:
    filter_chain = join_filters([*pre_filters, loudnorm_base(target_i, target_lra, target_tp)])
    result = run_ffmpeg(["-i", path, "-af", filter_chain, "-f", "null", "-"])
    return parse_loudnorm_json(result.stderr)


def render_loudnormed_wav(
    input_path: Path,
    output_path: Path,
    *,
    output_sample_rate: int,
    pre_filters: Sequence[str],
    target_i: float,
    target_lra: float,
    target_tp: float,
) -> tuple[dict[str, Any], float]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    measured = measure_loudnorm(
        input_path,
        target_i=target_i,
        target_lra=target_lra,
        target_tp=target_tp,
        pre_filters=pre_filters,
    )
    filter_chain = join_filters(
        [*pre_filters, loudnorm_second_pass(measured, target_i, target_lra, target_tp)]
    )
    result = run_ffmpeg(
        [
            "-y",
            "-i",
            input_path,
            "-af",
            filter_chain,
            "-ar",
            str(output_sample_rate),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            output_path,
        ]
    )
    elapsed_s = time.perf_counter() - started
    return {"first_pass": measured, "second_pass": parse_loudnorm_json(result.stderr)}, elapsed_s


def render_resampled_wav(input_path: Path, output_path: Path, *, sample_rate: int) -> float:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    run_ffmpeg(
        [
            "-y",
            "-i",
            input_path,
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            output_path,
        ]
    )
    return time.perf_counter() - started


def encode_mp3(input_path: Path, output_path: Path, *, sample_rate: int, bitrate: str) -> float:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    run_ffmpeg(
        [
            "-y",
            "-i",
            input_path,
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            output_path,
        ]
    )
    return time.perf_counter() - started


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_stem(path: Path) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in path.stem).strip("_") or "audio"


def probe_audio_metadata(path: Path) -> dict[str, Any]:
    result = run_subprocess(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels,codec_name,duration",
            "-of",
            "json",
            path,
        ]
    )
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    if not streams:
        raise ValueError(f"Nao foi possivel obter metadados de audio: {path}")
    stream = streams[0]
    return {
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 1),
        "codec_name": stream.get("codec_name"),
        "duration_s_probe": finite_or_none(stream.get("duration")),
    }


def decode_audio_with_ffmpeg(path: Path, sample_rate: int) -> np.ndarray:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-v",
            "error",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "-",
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg falhou ao decodificar audio para metricas: "
            f"{path}\n{result.stderr.decode('utf-8', errors='replace')}"
        )
    return np.frombuffer(result.stdout, dtype=np.float32).astype(np.float64)


def read_float_mono(path: Path) -> tuple[int, np.ndarray, dict[str, Any]]:
    if path.suffix.lower() == ".wav":
        sr, data = wavfile.read(path)
        values = np.asarray(data)
        channels = int(values.shape[1]) if values.ndim == 2 else 1
        dtype_name = str(values.dtype)
        if values.ndim == 2:
            values = values.mean(axis=1)
        if np.issubdtype(values.dtype, np.integer):
            values = values.astype(np.float64) / float(np.iinfo(data.dtype).max)
        else:
            values = values.astype(np.float64)
        values = values.reshape(-1)
        metadata = {
            "sample_rate": int(sr),
            "channels": channels,
            "dtype": dtype_name,
            "codec_name": "pcm_wav",
            "samples": int(values.size),
            "duration_s": float(values.size / int(sr)) if sr else 0.0,
        }
        return int(sr), values, metadata

    probed = probe_audio_metadata(path)
    sr = int(probed["sample_rate"])
    values = decode_audio_with_ffmpeg(path, sr).reshape(-1)
    metadata = {
        **probed,
        "dtype": "decoded_float32",
        "samples": int(values.size),
        "duration_s": float(values.size / sr) if sr else 0.0,
    }
    return sr, values, metadata


def resample_values(values: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    if source_sr == target_sr:
        return values
    divisor = math.gcd(source_sr, target_sr)
    up = target_sr // divisor
    down = source_sr // divisor
    return resample_poly(values, up, down).astype(np.float64)


def finite_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def rms_and_peak(path: Path) -> dict[str, float]:
    _, values, _ = read_float_mono(path)
    rms = float(np.sqrt(np.mean(values * values))) if values.size else 0.0
    peak = float(np.max(np.abs(values))) if values.size else 0.0
    return {
        "rms_linear": rms,
        "rms_dbfs": 20.0 * math.log10(max(rms, 1e-12)),
        "peak_linear": peak,
        "peak_dbfs": 20.0 * math.log10(max(peak, 1e-12)),
    }


def spectral_metrics(path: Path, *, active_mask_from: Path | None = None) -> dict[str, float | int | str]:
    sr, values, _ = read_float_mono(path)
    nfft = 512
    hop = max(1, int(round(0.010 * sr)))
    if len(values) < nfft:
        return {
            "active_frames": 0,
            "active_mask_source": "insufficient_length",
            "spectral_centroid_hz": 0.0,
            "band_3_8khz_energy": 0.0,
            "band_3_8khz_share_pct": 0.0,
        }

    active_source = "self"
    ref_values = values
    if active_mask_from is not None and active_mask_from.exists():
        ref_sr, raw_ref, _ = read_float_mono(active_mask_from)
        ref_values = resample_values(raw_ref, ref_sr, sr)
        active_source = str(active_mask_from)

    max_len = min(len(values), len(ref_values))
    window = np.hanning(nfft)
    starts: list[int] = []
    for start in range(0, max_len - nfft + 1, hop):
        ref_frame = ref_values[start : start + nfft] * window
        if float(np.sqrt(np.mean(ref_frame * ref_frame))) > 0.025:
            starts.append(start)

    if not starts:
        return {
            "active_frames": 0,
            "active_mask_source": active_source,
            "spectral_centroid_hz": 0.0,
            "band_3_8khz_energy": 0.0,
            "band_3_8khz_share_pct": 0.0,
        }

    freq = np.fft.rfftfreq(nfft, 1.0 / sr)
    spectra = []
    centroids = []
    for start in starts:
        frame = values[start : start + nfft] * window
        power = np.abs(np.fft.rfft(frame)) ** 2 + 1e-18
        spectra.append(power)
        centroids.append(float((freq * power).sum() / power.sum()))
    mean_power = np.mean(np.stack(spectra), axis=0)
    total = float(mean_power.sum())
    high_limit = min(8000.0, sr / 2.0)
    high_mask = (freq >= 3000.0) & (freq <= high_limit)
    band_energy = float(mean_power[high_mask].sum()) if np.any(high_mask) else 0.0
    return {
        "active_frames": len(starts),
        "active_mask_source": active_source,
        "spectral_centroid_hz": float(np.mean(centroids)),
        "band_3_8khz_energy": band_energy,
        "band_3_8khz_share_pct": float(100.0 * band_energy / max(total, 1e-18)),
    }


def analyze_loudness(path: Path, *, target_i: float, target_lra: float, target_tp: float) -> dict[str, float | None]:
    measured = measure_loudnorm(path, target_i=target_i, target_lra=target_lra, target_tp=target_tp)
    return {
        "integrated_lufs": finite_or_none(measured.get("input_i")),
        "true_peak_db": finite_or_none(measured.get("input_tp")),
        "lra_lu": finite_or_none(measured.get("input_lra")),
        "threshold_lufs": finite_or_none(measured.get("input_thresh")),
    }


def file_audio_record(
    path: Path,
    *,
    target_i: float,
    target_lra: float,
    target_tp: float,
    active_mask_from: Path | None,
) -> dict[str, Any]:
    _, _, metadata = read_float_mono(path)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        **metadata,
        "loudness": analyze_loudness(
            path,
            target_i=target_i,
            target_lra=target_lra,
            target_tp=target_tp,
        ),
        **rms_and_peak(path),
        "spectral_metrics": spectral_metrics(path, active_mask_from=active_mask_from),
    }


def ensure_tmp_output_dir(output_dir: Path) -> Path:
    tmp_root = (ROOT_DIR / "tmp").resolve()
    resolved = output_dir if output_dir.is_absolute() else ROOT_DIR / output_dir
    resolved = resolved.resolve()
    if resolved != tmp_root and tmp_root not in resolved.parents:
        raise ValueError(
            "Por seguranca metodologica, esta rotina so grava dentro de tmp/. "
            f"Recebido: {resolved}"
        )
    return resolved


def resolve_deepfilter_command(command: str | None) -> list[str]:
    if command:
        return shlex.split(command)

    candidates: list[Path | str] = []
    found = shutil.which("deepFilter")
    if found:
        candidates.append(found)
    executable_dir = Path(sys.executable).resolve().parent
    candidates.extend(
        [
            executable_dir / "deepFilter.exe",
            executable_dir / "deepFilter",
            executable_dir / "Scripts" / "deepFilter.exe",
            executable_dir / "Scripts" / "deepFilter",
        ]
    )
    for candidate in candidates:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return [str(candidate_path)]
    return ["deepFilter"]


def command_exists(command_parts: Sequence[str]) -> bool:
    if not command_parts:
        return False
    executable = command_parts[0]
    if Path(executable).exists():
        return True
    return shutil.which(executable) is not None


def get_command_version(command_parts: Sequence[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [*command_parts, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}
    return {
        "available": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip()[:1000],
        "stderr": result.stderr.strip()[:1000],
    }


def find_deepfilter_output(output_dir: Path, *, input_stem: str) -> Path:
    wavs = sorted(output_dir.rglob("*.wav"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not wavs:
        raise FileNotFoundError(
            "O DeepFilterNet terminou sem gerar WAV detectavel em " f"{output_dir}."
        )
    stem_matches = [path for path in wavs if input_stem.lower() in path.stem.lower()]
    return stem_matches[0] if stem_matches else wavs[0]


def run_deepfilternet(
    *,
    command_parts: Sequence[str],
    input_wav_48k: Path,
    raw_output_dir: Path,
    extra_args: Sequence[str],
) -> tuple[Path, dict[str, Any]]:
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    for old_wav in raw_output_dir.rglob("*.wav"):
        old_wav.unlink()

    command = [*command_parts, *extra_args, "--output-dir", str(raw_output_dir), str(input_wav_48k)]
    started = time.perf_counter()
    result = run_subprocess(command)
    elapsed_s = time.perf_counter() - started
    output_path = find_deepfilter_output(raw_output_dir, input_stem=input_wav_48k.stem)
    return output_path, {
        "command": command,
        "stdout": result.stdout.strip()[:4000],
        "stderr": result.stderr.strip()[:4000],
        "elapsed_s": elapsed_s,
    }


def make_comparison_variant(
    *,
    key: str,
    label: str,
    description: str,
    source_wav: Path,
    wav_dir: Path,
    mp3_dir: Path,
    run_name: str,
    output_sample_rate: int,
    pre_filters: Sequence[str],
    target_i: float,
    target_lra: float,
    target_tp: float,
    mp3_bitrate: str,
    active_mask_from: Path | None,
    base_processing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    wav_path = wav_dir / f"{run_name}_{key}.wav"
    mp3_path = mp3_dir / f"{run_name}_{key}.mp3"
    loudnorm_passes, postprocess_elapsed_s = render_loudnormed_wav(
        source_wav,
        wav_path,
        output_sample_rate=output_sample_rate,
        pre_filters=pre_filters,
        target_i=target_i,
        target_lra=target_lra,
        target_tp=target_tp,
    )
    mp3_elapsed_s = encode_mp3(
        wav_path,
        mp3_path,
        sample_rate=output_sample_rate,
        bitrate=mp3_bitrate,
    )
    wav_record = file_audio_record(
        wav_path,
        target_i=target_i,
        target_lra=target_lra,
        target_tp=target_tp,
        active_mask_from=active_mask_from,
    )
    mp3_record = file_audio_record(
        mp3_path,
        target_i=target_i,
        target_lra=target_lra,
        target_tp=target_tp,
        active_mask_from=active_mask_from,
    )
    source_sr, _, source_metadata = read_float_mono(source_wav)
    duration_s = source_metadata["duration_s"]
    return {
        "key": key,
        "label": label,
        "description": description,
        "source_wav": str(source_wav),
        "source_sample_rate": source_sr,
        "comparison_sample_rate": output_sample_rate,
        "pre_loudnorm_filters": list(pre_filters),
        "loudnorm_passes": loudnorm_passes,
        "postprocess_elapsed_s": postprocess_elapsed_s,
        "mp3_encode_elapsed_s": mp3_elapsed_s,
        "postprocess_rtf": postprocess_elapsed_s / max(float(duration_s), 1e-12),
        "base_processing": base_processing,
        "wav": wav_record,
        "mp3": mp3_record,
    }


def build_readme(output_dir: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Avaliacao offline com DeepFilterNet",
        "",
        "Arquivos temporarios para escuta comparativa. Nada aqui substitui os audios publicados no questionario.",
        "",
        "## Saidas MP3",
        "",
    ]
    for item in report["comparisons"]:
        lines.append(f"- {item['key']}: `{item['mp3']['path']}`")
    lines.extend(
        [
            "",
            "## Metodo",
            "",
            "O DeepFilterNet e executado como trilha offline separada. A entrada e convertida para mono em 48 kHz antes do DeepFilterNet e as comparacoes finais sao normalizadas para o sample rate do pipeline principal, por padrao 16 kHz.",
            "",
            "A normalizacao usa o mesmo alvo da rotina RNNoise: loudnorm em dois passes com `I = -16 LUFS`, `LRA = 7 LU` e `TP = -1 dBTP`, salvo parametros alterados via CLI.",
            "",
            "Esta rotina nao prova tempo real, baixa latencia nem compatibilidade com microfone virtual Windows.",
            "",
            f"Relatorio completo: `{output_dir / 'deepfilternet_report.json'}`",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera uma avaliacao offline DeepFilterNet comparavel ao RNNoise + EQ/loudness."
    )
    parser.add_argument("--input", type=Path, required=True, help="WAV de entrada ruidoso.")
    parser.add_argument("--clean-reference", type=Path, help="WAV limpo pareado, quando existir.")
    parser.add_argument("--output-dir", type=Path, default=Path("tmp/deepfilternet_eval"))
    parser.add_argument("--name", help="Nome base da execucao. Padrao: stem do arquivo de entrada.")
    parser.add_argument("--deepfilter-command", help="Comando do DeepFilterNet. Padrao: deepFilter ou entrypoint da venv atual.")
    parser.add_argument(
        "--deepfilter-extra-arg",
        action="append",
        default=[],
        help="Argumento extra repassado ao DeepFilterNet. Pode ser usado multiplas vezes.",
    )
    parser.add_argument("--deepfilter-sample-rate", type=int, default=48000)
    parser.add_argument("--comparison-sample-rate", type=int, default=16000)
    parser.add_argument("--target-i", type=float, default=-16.0, help="Loudness integrado alvo em LUFS.")
    parser.add_argument("--target-lra", type=float, default=7.0, help="Loudness range alvo em LU.")
    parser.add_argument("--target-tp", type=float, default=-1.0, help="True peak maximo em dBTP.")
    parser.add_argument("--eq-freq-hz", type=float, default=3000.0)
    parser.add_argument("--eq-q", type=float, default=1.0)
    parser.add_argument("--eq-gain-db", type=float, default=2.0)
    parser.add_argument("--startup-preroll-ms", type=float, default=200.0)
    parser.add_argument("--fade-in-ms", type=float, default=0.0)
    parser.add_argument("--mp3-bitrate", default="96k")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = args.input
    if not input_path.exists():
        print(f"Arquivo de entrada inexistente: {input_path}", file=sys.stderr)
        return 2
    if args.clean_reference and not args.clean_reference.exists():
        print(f"Referencia limpa inexistente: {args.clean_reference}", file=sys.stderr)
        return 2
    if input_path.suffix.lower() != ".wav":
        print("A entrada deve ser WAV para manter a trilha auditavel.", file=sys.stderr)
        return 2
    if args.deepfilter_sample_rate != 48000:
        print(
            "Aviso: o sample rate usual do DeepFilterNet e 48 kHz; "
            f"registrando uso explicito de {args.deepfilter_sample_rate} Hz.",
            file=sys.stderr,
        )

    try:
        output_root = ensure_tmp_output_dir(args.output_dir)
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    command_parts = resolve_deepfilter_command(args.deepfilter_command)
    if not command_exists(command_parts):
        print(
            "Erro: comando DeepFilterNet nao encontrado. Instale em venv isolada dentro de tmp/ "
            "ou informe --deepfilter-command. Exemplo: python -m venv tmp\\.venv_deepfilternet; "
            "tmp\\.venv_deepfilternet\\Scripts\\python -m pip install -r requirements.txt; "
            "tmp\\.venv_deepfilternet\\Scripts\\python -m pip install deepfilternet",
            file=sys.stderr,
        )
        return 2

    run_name = args.name or safe_stem(input_path)
    output_dir = output_root / run_name
    wav_dir = output_dir / "wav"
    mp3_dir = output_dir / "mp3"
    metrics_dir = output_dir / "metrics"
    deepfilter_raw_dir = output_dir / "deepfilternet_raw"
    for directory in (wav_dir, mp3_dir, metrics_dir, deepfilter_raw_dir):
        directory.mkdir(parents=True, exist_ok=True)

    command_args = list(argv) if argv is not None else sys.argv[1:]
    started_total = time.perf_counter()
    input_sr, _, input_metadata = read_float_mono(input_path)
    active_mask_from = args.clean_reference or input_path
    eq_filter = f"equalizer=f={args.eq_freq_hz}:width_type=q:width={args.eq_q}:g={args.eq_gain_db}"

    deepfilter_input_48k = wav_dir / f"{run_name}_deepfilternet_input_{args.deepfilter_sample_rate}hz.wav"
    deepfilter_resample_elapsed_s = render_resampled_wav(
        input_path,
        deepfilter_input_48k,
        sample_rate=args.deepfilter_sample_rate,
    )

    try:
        deepfilter_output_raw, deepfilter_run = run_deepfilternet(
            command_parts=command_parts,
            input_wav_48k=deepfilter_input_48k,
            raw_output_dir=deepfilter_raw_dir,
            extra_args=args.deepfilter_extra_arg,
        )
    except (FileNotFoundError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Erro ao executar DeepFilterNet: {exc}", file=sys.stderr)
        return 2

    _, _, deepfilter_input_metadata = read_float_mono(deepfilter_input_48k)
    deepfilter_duration_s = float(deepfilter_input_metadata["duration_s"])
    deepfilter_base_processing = {
        "method": "deepfilternet",
        "offline_only": True,
        "input_sample_rate": args.deepfilter_sample_rate,
        "elapsed_s": deepfilter_run["elapsed_s"],
        "rtf": deepfilter_run["elapsed_s"] / max(deepfilter_duration_s, 1e-12),
    }

    rnnoise_base_wav = wav_dir / f"{run_name}_rnnoise_base.wav"
    rnnoise_metrics_path = metrics_dir / f"{run_name}_rnnoise_base.json"
    rnnoise_started = time.perf_counter()
    rnnoise_metrics = process_wav_rnnoise(
        input_path=input_path,
        output_path=rnnoise_base_wav,
        metrics_path=rnnoise_metrics_path,
        overwrite=True,
        startup_preroll_ms=args.startup_preroll_ms,
        fade_in_ms=args.fade_in_ms,
        command_args=["prepare_deepfilternet_eval.py", "--input", str(input_path)],
    )
    rnnoise_elapsed_s = time.perf_counter() - rnnoise_started
    rnnoise_duration_s = float(rnnoise_metrics["processing"]["processed_samples"]) / 16000.0
    rnnoise_base_processing = {
        "method": "rnnoise",
        "startup_preroll_ms": args.startup_preroll_ms,
        "fade_in_ms": args.fade_in_ms,
        "elapsed_s": rnnoise_elapsed_s,
        "rtf": rnnoise_elapsed_s / max(rnnoise_duration_s, 1e-12),
        "metrics_json": str(rnnoise_metrics_path),
    }

    comparisons: list[dict[str, Any]] = []
    comparisons.append(
        make_comparison_variant(
            key="noisy_reference_loudnorm",
            label="Referencia ruidosa com loudness equalizado",
            description="Entrada ruidosa normalizada para servir de referencia perceptual.",
            source_wav=input_path,
            wav_dir=wav_dir,
            mp3_dir=mp3_dir,
            run_name=run_name,
            output_sample_rate=args.comparison_sample_rate,
            pre_filters=(),
            target_i=args.target_i,
            target_lra=args.target_lra,
            target_tp=args.target_tp,
            mp3_bitrate=args.mp3_bitrate,
            active_mask_from=active_mask_from,
        )
    )
    comparisons.append(
        make_comparison_variant(
            key="rnnoise_presence_eq_loudnorm",
            label="RNNoise + EQ de presenca + loudness",
            description="Melhor variante atual do projeto, equivalente a trilha escolhida para o questionario.",
            source_wav=rnnoise_base_wav,
            wav_dir=wav_dir,
            mp3_dir=mp3_dir,
            run_name=run_name,
            output_sample_rate=args.comparison_sample_rate,
            pre_filters=(eq_filter,),
            target_i=args.target_i,
            target_lra=args.target_lra,
            target_tp=args.target_tp,
            mp3_bitrate=args.mp3_bitrate,
            active_mask_from=active_mask_from,
            base_processing=rnnoise_base_processing,
        )
    )
    comparisons.append(
        make_comparison_variant(
            key="deepfilternet_loudnorm",
            label="DeepFilterNet + loudness",
            description="Saida DeepFilterNet offline com normalizacao final de loudness.",
            source_wav=deepfilter_output_raw,
            wav_dir=wav_dir,
            mp3_dir=mp3_dir,
            run_name=run_name,
            output_sample_rate=args.comparison_sample_rate,
            pre_filters=(),
            target_i=args.target_i,
            target_lra=args.target_lra,
            target_tp=args.target_tp,
            mp3_bitrate=args.mp3_bitrate,
            active_mask_from=active_mask_from,
            base_processing=deepfilter_base_processing,
        )
    )
    comparisons.append(
        make_comparison_variant(
            key="deepfilternet_presence_eq_loudnorm",
            label="DeepFilterNet + EQ de presenca + loudness",
            description="Variante exploratoria com o mesmo EQ leve usado para comparar timbre do RNNoise.",
            source_wav=deepfilter_output_raw,
            wav_dir=wav_dir,
            mp3_dir=mp3_dir,
            run_name=run_name,
            output_sample_rate=args.comparison_sample_rate,
            pre_filters=(eq_filter,),
            target_i=args.target_i,
            target_lra=args.target_lra,
            target_tp=args.target_tp,
            mp3_bitrate=args.mp3_bitrate,
            active_mask_from=active_mask_from,
            base_processing=deepfilter_base_processing,
        )
    )
    if args.clean_reference:
        comparisons.append(
            make_comparison_variant(
                key="clean_reference_loudnorm",
                label="Referencia limpa com loudness equalizado",
                description="Referencia limpa pareada, quando disponivel, normalizada para escuta comparativa.",
                source_wav=args.clean_reference,
                wav_dir=wav_dir,
                mp3_dir=mp3_dir,
                run_name=run_name,
                output_sample_rate=args.comparison_sample_rate,
                pre_filters=(),
                target_i=args.target_i,
                target_lra=args.target_lra,
                target_tp=args.target_tp,
                mp3_bitrate=args.mp3_bitrate,
                active_mask_from=args.clean_reference,
            )
        )

    report: dict[str, Any] = {
        "schema_version": SCRIPT_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_name": run_name,
        "command_args": command_args,
        "input": {
            "path": str(input_path),
            "sha256": sha256_file(input_path),
            **input_metadata,
        },
        "clean_reference": None,
        "output_policy": {
            "tmp_only": True,
            "output_dir": str(output_dir),
            "questionnaire_modified": False,
            "apps_script_modified": False,
        },
        "sample_rates": {
            "original_hz": input_sr,
            "deepfilternet_hz": args.deepfilter_sample_rate,
            "comparison_hz": args.comparison_sample_rate,
            "note": (
                "Se a entrada original for 16 kHz, o upsample para 48 kHz nao cria "
                "conteudo acima de 8 kHz; ele apenas satisfaz a entrada usual do DeepFilterNet."
            ),
        },
        "loudness_target": {
            "integrated_lufs": args.target_i,
            "lra_lu": args.target_lra,
            "true_peak_db": args.target_tp,
            "method": "ffmpeg loudnorm two-pass",
        },
        "presence_eq": {
            "filter": "ffmpeg equalizer",
            "freq_hz": args.eq_freq_hz,
            "q": args.eq_q,
            "gain_db": args.eq_gain_db,
            "order": "denoise -> optional EQ -> final loudnorm",
        },
        "deepfilternet": {
            "command_parts": command_parts,
            "extra_args": list(args.deepfilter_extra_arg),
            "version_probe": get_command_version(command_parts),
            "input_48k": file_audio_record(
                deepfilter_input_48k,
                target_i=args.target_i,
                target_lra=args.target_lra,
                target_tp=args.target_tp,
                active_mask_from=active_mask_from,
            ),
            "raw_output": file_audio_record(
                deepfilter_output_raw,
                target_i=args.target_i,
                target_lra=args.target_lra,
                target_tp=args.target_tp,
                active_mask_from=active_mask_from,
            ),
            "resample_input_elapsed_s": deepfilter_resample_elapsed_s,
            "run": deepfilter_run,
            "rtf": deepfilter_base_processing["rtf"],
        },
        "rnnoise_reference": {
            "base_wav": file_audio_record(
                rnnoise_base_wav,
                target_i=args.target_i,
                target_lra=args.target_lra,
                target_tp=args.target_tp,
                active_mask_from=active_mask_from,
            ),
            "metrics_json": str(rnnoise_metrics_path),
            "processing": rnnoise_base_processing,
        },
        "comparisons": comparisons,
        "timing": {
            "total_elapsed_s": time.perf_counter() - started_total,
            "deepfilternet_command_elapsed_s": deepfilter_run["elapsed_s"],
            "deepfilternet_command_rtf": deepfilter_base_processing["rtf"],
            "rnnoise_elapsed_s": rnnoise_elapsed_s,
            "rnnoise_rtf": rnnoise_base_processing["rtf"],
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "executable": sys.executable,
        },
        "methodological_limitations": [
            "Avaliacao offline: nao mede captura, reproducao, driver, ponte PCM ou microfone virtual.",
            "Nao usar estes RTFs para prometer baixa latencia fisica ou compatibilidade em tempo real.",
            "Quando a entrada e 16 kHz, o DeepFilterNet recebe versao reamostrada para 48 kHz sem informacao nova acima de 8 kHz.",
            "A variante DeepFilterNet + EQ e exploratoria e usa o mesmo pos-processamento de presenca aplicado ao RNNoise para comparacao de timbre.",
            "As saidas ficam em tmp/ e nao integram o questionario publicado sem decisao explicita posterior.",
        ],
    }
    if args.clean_reference:
        report["clean_reference"] = file_audio_record(
            args.clean_reference,
            target_i=args.target_i,
            target_lra=args.target_lra,
            target_tp=args.target_tp,
            active_mask_from=args.clean_reference,
        )

    report_path = output_dir / "deepfilternet_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    build_readme(output_dir, report)

    print(f"Avaliacao DeepFilterNet gerada em: {output_dir}")
    print(f"Relatorio: {report_path}")
    for item in comparisons:
        print(f"- {item['key']}: {item['mp3']['path']}")
    print(
        "Observacao: resultado offline; nao altera questionario, Apps Script ou promessa de tempo real."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
