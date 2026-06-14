from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark_audio.causal import CausalProcessorConfig, CausalSTFTProcessor


SAMPLE_RATE = 16_000
BLOCK_SIZE = 320
BANDS_HZ = (
    ("0_300", 0.0, 300.0),
    ("300_1000", 300.0, 1_000.0),
    ("1000_2000", 1_000.0, 2_000.0),
    ("2000_4000", 2_000.0, 4_000.0),
    ("4000_8000", 4_000.0, 8_001.0),
)


def read_pcm16(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as handle:
        if (
            handle.getnchannels() != 1
            or handle.getsampwidth() != 2
            or handle.getframerate() != SAMPLE_RATE
        ):
            raise ValueError(f"Esperado WAV mono PCM16 de 16 kHz: {path}")
        values = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    return values.astype(np.float32) / 32768.0


def write_pcm16(path: Path, samples: np.ndarray) -> None:
    pcm = np.rint(np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def db(value: float) -> float:
    return 10.0 * math.log10(max(value, 1e-24))


def process(samples: np.ndarray, smoothing: float) -> np.ndarray:
    processor = CausalSTFTProcessor(
        CausalProcessorConfig(
            sample_rate=SAMPLE_RATE,
            method="stft_subtraction",
            n_fft=512,
            hop_length=160,
            spectral_alpha=1.5,
            spectral_floor=0.02,
            gain_smoothing=smoothing,
            noise_mode="adaptive",
        )
    )
    outputs = []
    for start in range(0, samples.size, BLOCK_SIZE):
        outputs.append(processor.process_block(samples[start : start + BLOCK_SIZE])[0])
    return np.concatenate(outputs).astype(np.float32)


def active_mask(raw: np.ndarray) -> np.ndarray:
    count = raw.size // BLOCK_SIZE
    blocks = raw[: count * BLOCK_SIZE].reshape(count, BLOCK_SIZE)
    levels = np.sqrt(np.mean(np.square(blocks, dtype=np.float64), axis=1))
    noise_floor = float(np.quantile(levels, 0.20))
    threshold = max(10.0 ** (-48.0 / 20.0), noise_floor * 10.0 ** (6.0 / 20.0))
    return levels > threshold


def metrics(raw: np.ndarray, output: np.ndarray, active: np.ndarray) -> dict[str, object]:
    count = min(raw.size, output.size) // BLOCK_SIZE
    raw_blocks = raw[: count * BLOCK_SIZE].reshape(count, BLOCK_SIZE)[active[:count]]
    out_blocks = output[: count * BLOCK_SIZE].reshape(count, BLOCK_SIZE)[active[:count]]
    window = np.hanning(BLOCK_SIZE)
    raw_spectra = np.fft.rfft(raw_blocks.astype(np.float64) * window, axis=1)
    out_spectra = np.fft.rfft(out_blocks.astype(np.float64) * window, axis=1)
    raw_power = np.maximum(np.square(np.abs(raw_spectra)), 1e-24)
    out_power = np.maximum(np.square(np.abs(out_spectra)), 1e-24)
    flatness = np.exp(np.mean(np.log(out_power), axis=1)) / np.mean(out_power, axis=1)
    median_power = np.median(out_power, axis=1, keepdims=True)
    tonal = out_power[:, 1:-1] > 10.0 * median_power
    tonal &= out_power[:, 1:-1] > out_power[:, :-2]
    tonal &= out_power[:, 1:-1] > out_power[:, 2:]
    frequencies = np.fft.rfftfreq(BLOCK_SIZE, 1.0 / SAMPLE_RATE)
    band_psd_db = {}
    band_delta_raw_db = {}
    for name, low, high in BANDS_HZ:
        selected = (frequencies >= low) & (frequencies < high)
        output_band = float(np.mean(out_power[:, selected]))
        raw_band = float(np.mean(raw_power[:, selected]))
        band_psd_db[name] = db(output_band)
        band_delta_raw_db[name] = db(output_band / max(raw_band, 1e-24))

    raw_active = raw_blocks.reshape(-1).astype(np.float64)
    out_active = out_blocks.reshape(-1).astype(np.float64)
    residual = out_active - raw_active
    raw_energy = float(np.sum(np.square(raw_active)))
    residual_energy = float(np.sum(np.square(residual)))
    scale = float(np.dot(out_active, raw_active) / max(raw_energy, 1e-24))
    target = scale * raw_active
    si_residual = out_active - target
    raw_envelope = np.sqrt(np.mean(np.square(raw_blocks, dtype=np.float64), axis=1))
    out_envelope = np.sqrt(np.mean(np.square(out_blocks, dtype=np.float64), axis=1))
    return {
        "active_block_count": int(len(raw_blocks)),
        "tonal_peak_density_per_block": float(np.mean(np.sum(tonal, axis=1))),
        "spectral_flatness_median": float(np.median(flatness)),
        "band_psd_db": band_psd_db,
        "band_delta_from_raw_db": band_delta_raw_db,
        "snr_against_raw_db": db(raw_energy / max(residual_energy, 1e-24)),
        "si_sdr_against_raw_db": db(
            float(np.sum(np.square(target)))
            / max(float(np.sum(np.square(si_residual))), 1e-24)
        ),
        "envelope_correlation": float(np.corrcoef(raw_envelope, out_envelope)[0, 1]),
        "active_energy_ratio_db": db(
            float(np.sum(np.square(out_active))) / max(raw_energy, 1e-24)
        ),
    }


def compare_signals(reference: np.ndarray, estimate: np.ndarray) -> dict[str, float]:
    common = min(reference.size, estimate.size)
    reference64 = reference[:common].astype(np.float64)
    estimate64 = estimate[:common].astype(np.float64)
    error = estimate64 - reference64
    denominator = float(np.dot(reference64, reference64))
    gain = (
        0.0
        if denominator <= 1e-24
        else float(np.dot(estimate64, reference64) / denominator)
    )
    residual = estimate64 - gain * reference64
    correlation = float(np.corrcoef(reference64, estimate64)[0, 1])
    return {
        "correlation": correlation,
        "fitted_gain": gain,
        "rmse_dbfs": 20.0 * math.log10(
            max(float(np.sqrt(np.mean(np.square(error)))), 1e-12)
        ),
        "fitted_residual_rmse_dbfs": 20.0 * math.log10(
            max(float(np.sqrt(np.mean(np.square(residual)))), 1e-12)
        ),
        "max_abs_error": float(np.max(np.abs(error))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-full", type=Path, required=True)
    parser.add_argument("--baseline-reference", type=Path, required=True)
    parser.add_argument("--cut-start", type=int, required=True)
    parser.add_argument("--cut-stop", type=int, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument(
        "--smoothing",
        type=float,
        nargs="+",
        default=[0.50, 0.70, 0.85, 0.93],
    )
    args = parser.parse_args()

    raw_full = read_pcm16(args.raw_full)
    baseline_reference = read_pcm16(args.baseline_reference)
    variants = [0.0, *args.smoothing]
    active = active_mask(raw_full[args.cut_start : args.cut_stop])
    processed = {value: process(raw_full, value) for value in variants}
    cut = {
        value: samples[args.cut_start : args.cut_stop]
        for value, samples in processed.items()
    }
    raw_cut = raw_full[args.cut_start : args.cut_stop]
    results = {
        str(value): metrics(raw_cut, cut[value], active)
        for value in variants
    }
    baseline = results["0.0"]
    baseline_tonal = float(baseline["tonal_peak_density_per_block"])
    baseline_high = float(baseline["band_delta_from_raw_db"]["4000_8000"])
    candidates = []
    for value in args.smoothing:
        item = results[str(value)]
        tonal_reduction = (
            baseline_tonal - float(item["tonal_peak_density_per_block"])
        ) / max(baseline_tonal, 1e-12)
        extra_high_loss = (
            float(item["band_delta_from_raw_db"]["4000_8000"]) - baseline_high
        )
        accepted = (
            tonal_reduction >= 0.10
            and extra_high_loss >= -1.0
            and float(item["envelope_correlation"]) >= 0.97
            and float(item["active_energy_ratio_db"]) >= -3.0
        )
        candidates.append(
            {
                "gain_smoothing": value,
                "tonal_peak_reduction_fraction": tonal_reduction,
                "extra_4_8k_change_vs_baseline_db": extra_high_loss,
                "objective_gate": accepted,
            }
        )
    eligible = [item for item in candidates if item["objective_gate"]]
    selected = (
        max(eligible, key=lambda item: item["tonal_peak_reduction_fraction"])
        if eligible
        else None
    )

    private_files = []
    args.private_output_dir.mkdir(parents=True, exist_ok=True)
    if selected is not None:
        outputs = {
            "A_baseline_common_cut.wav": cut[0.0],
            "B_smoothed_common_cut.wav": cut[selected["gain_smoothing"]],
        }
        for name, samples in outputs.items():
            path = args.private_output_dir / name
            write_pcm16(path, samples)
            private_files.append(
                {"name": name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            )

    baseline_reproduction = compare_signals(baseline_reference, cut[0.0])
    summary = {
        "privacy": "private_audio_outside_repository",
        "new_voice_recording": False,
        "private_audio_location": str(args.private_output_dir),
        "sources": {
            "raw_full_sha256": sha256(args.raw_full),
            "baseline_reference_sha256": sha256(args.baseline_reference),
            "cut_start_sample": args.cut_start,
            "cut_stop_sample": args.cut_stop,
            "cut_duration_s": (args.cut_stop - args.cut_start) / SAMPLE_RATE,
        },
        "family": "causal_temporal_smoothing_of_spectral_gain",
        "frozen": {
            "sample_rate_hz": SAMPLE_RATE,
            "block_size": BLOCK_SIZE,
            "n_fft": 512,
            "hop_length": 160,
            "spectral_alpha": 1.5,
            "spectral_floor": 0.02,
            "noise_estimator": "adaptive",
        },
        "active_detection": {
            "scope": "raw_common_cut",
            "rule": "max(-48 dBFS, q20 block RMS + 6 dB)",
            "block_count": int(np.count_nonzero(active)),
        },
        "variants": results,
        "candidate_decisions": candidates,
        "selected": selected,
        "baseline_reference_comparison": {
            "reference": "checkpoint40_B_pre_bridge_common_cut",
            "comparison": baseline_reproduction,
        },
        "private_pair_prepared": selected is not None,
        "private_files": private_files,
    }
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (args.private_output_dir / "private_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(args.public_output)


if __name__ == "__main__":
    main()
