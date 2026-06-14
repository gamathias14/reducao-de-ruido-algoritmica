from __future__ import annotations

import argparse
import csv
import json
import secrets
from pathlib import Path

import numpy as np

from benchmark_audio.denoise import read_wav_mono, resample_audio
from benchmark_audio.literature_harness import (
    FrozenBaselineAdapter,
    OMLSAIMCRAAdapter,
    RNNoiseAdapter,
    audio_sha256,
)
from realtime_audio.process_wav_blocks import sha256_file
from scripts.audio.evaluate_checkpoint41_gain_smoothing import write_pcm16


SAMPLE_RATE = 16_000
SYSTEM_IDS = ("baseline_stft", "omlsa_imcra", "rnnoise")


def _process_full(source: np.ndarray) -> dict[str, np.ndarray]:
    baseline = FrozenBaselineAdapter().process(source, SAMPLE_RATE).audio
    omlsa = OMLSAIMCRAAdapter().process(source, SAMPLE_RATE).audio
    rnnoise_adapter = RNNoiseAdapter()
    native = resample_audio(source, SAMPLE_RATE, rnnoise_adapter.metadata.native_sample_rate)
    rnnoise_native = rnnoise_adapter.process(
        native, rnnoise_adapter.metadata.native_sample_rate
    ).audio
    rnnoise = resample_audio(
        rnnoise_native, rnnoise_adapter.metadata.native_sample_rate, SAMPLE_RATE
    )
    if len(rnnoise) < len(source):
        rnnoise = np.pad(rnnoise, (0, len(source) - len(rnnoise)))
    return {
        "baseline_stft": np.asarray(baseline[: len(source)], dtype=np.float32),
        "omlsa_imcra": np.asarray(omlsa[: len(source)], dtype=np.float32),
        "rnnoise": np.asarray(rnnoise[: len(source)], dtype=np.float32),
    }


def prepare_trio(
    *,
    source_path: Path,
    cut_start: int,
    cut_stop: int,
    private_output_dir: Path,
    public_output: Path,
) -> dict[str, object]:
    source = read_wav_mono(source_path, SAMPLE_RATE, normalize=False)
    if cut_start < 0 or cut_stop <= cut_start or cut_stop > len(source):
        raise ValueError(
            f"Corte invalido: {cut_start}:{cut_stop} para {len(source)} amostras."
        )
    if private_output_dir.exists() and any(private_output_dir.iterdir()):
        raise FileExistsError(
            f"Diretorio privado nao vazio: {private_output_dir}"
        )
    private_output_dir.mkdir(parents=True, exist_ok=True)
    public_output.parent.mkdir(parents=True, exist_ok=True)

    processed = _process_full(source)
    labels = ["A", "B", "C"]
    secrets.SystemRandom().shuffle(labels)
    mapping = dict(zip(labels, SYSTEM_IDS, strict=True))
    files = []
    for label in labels:
        system_id = mapping[label]
        cut = processed[system_id][cut_start:cut_stop]
        filename = f"trial_001_{label}.wav"
        path = private_output_dir / filename
        write_pcm16(path, cut)
        files.append(
            {
                "blind_label": label,
                "name": filename,
                "samples": len(cut),
                "duration_s": len(cut) / SAMPLE_RATE,
                "sha256": sha256_file(path),
                "float32_sha256_before_pcm16": audio_sha256(cut),
                "rms_dbfs": float(
                    20.0
                    * np.log10(max(float(np.sqrt(np.mean(cut * cut))), 1e-12))
                ),
                "peak_abs": float(np.max(np.abs(cut))),
            }
        )

    private_key = {
        "privacy": "private_not_for_repository",
        "source_path": str(source_path.resolve()),
        "source_sha256": sha256_file(source_path),
        "cut_start_sample": cut_start,
        "cut_stop_sample": cut_stop,
        "mapping": mapping,
        "normalization": "none",
        "fade_ms": 0,
    }
    (private_output_dir / "blind_key.json").write_text(
        json.dumps(private_key, indent=2),
        encoding="utf-8",
    )
    with (private_output_dir / "ratings.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "listener_id",
                "trial_id",
                "blind_label",
                "listening_date",
                "playback_device",
                "volume_setting",
                "intelligibility_1_5",
                "naturalness_1_5",
                "residual_noise_1_5",
                "artifacts_1_5",
                "preference_rank",
                "heard_clipping_or_dropouts",
                "notes",
            ]
        )
        for label in sorted(labels):
            writer.writerow(["", "trial_001", label, "", "", "fixed", "", "", "", "", "", "", ""])

    summary: dict[str, object] = {
        "status": "private_listening_pending",
        "protocol": "checkpoint46r_literature_private_trio_v1",
        "privacy": "private_audio_outside_repository",
        "source_authorization": "checkpoint38_explicit_user_authorization",
        "new_voice_recording": False,
        "sample_rate_hz": SAMPLE_RATE,
        "source_sha256": sha256_file(source_path),
        "source_samples": len(source),
        "common_cut": {
            "start_sample": cut_start,
            "stop_sample": cut_stop,
            "duration_s": (cut_stop - cut_start) / SAMPLE_RATE,
        },
        "systems_in_blind_set": list(SYSTEM_IDS),
        "normalization": "none",
        "fade_ms": 0,
        "private_key_written": True,
        "private_key_location_disclosed_publicly": False,
        "files": files,
        "human_listening_requested": True,
        "human_decision": None,
        "vm_started": False,
        "endpoint_used": False,
    }
    public_output.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepara trio privado cego do benchmark de literatura."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cut-start", type=int, required=True)
    parser.add_argument("--cut-stop", type=int, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_trio(
        source_path=args.source,
        cut_start=args.cut_start,
        cut_stop=args.cut_stop,
        private_output_dir=args.private_output_dir,
        public_output=args.public_output,
    )


if __name__ == "__main__":
    main()
