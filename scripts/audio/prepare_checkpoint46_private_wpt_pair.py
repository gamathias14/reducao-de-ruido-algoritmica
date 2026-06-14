from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark_audio.causal_wpt import CausalWPTConfig, CausalWPTProcessor
from scripts.audio.evaluate_checkpoint41_gain_smoothing import (
    BLOCK_SIZE,
    SAMPLE_RATE,
    compare_signals,
    read_pcm16,
    sha256,
    write_pcm16,
)
from scripts.audio.evaluate_checkpoint42_wiener import process as process_stft


def process_wpt(samples: np.ndarray) -> np.ndarray:
    processor = CausalWPTProcessor(CausalWPTConfig())
    outputs = []
    for start in range(0, samples.size, BLOCK_SIZE):
        block = samples[start : start + BLOCK_SIZE]
        outputs.append(processor.process_block(block)[0])
    return np.concatenate(outputs).astype(np.float32)


def prepare_pair(
    *,
    raw_full_path: Path,
    baseline_reference_path: Path,
    cut_start: int,
    cut_stop: int,
    private_output_dir: Path,
    public_output: Path,
) -> dict[str, object]:
    if public_output.exists():
        existing = json.loads(public_output.read_text(encoding="utf-8"))
        if existing.get("status") == "completed_wpt_rejected":
            raise ValueError("O Checkpoint 46 ja foi concluido e nao pode ser reaberto.")

    raw_full = read_pcm16(raw_full_path)
    baseline_reference = read_pcm16(baseline_reference_path)
    if not 0 <= cut_start < cut_stop <= raw_full.size:
        raise ValueError("Corte invalido para a tomada integral.")

    baseline_full = process_stft(raw_full, "stft_subtraction")
    wpt_full = process_wpt(raw_full)
    if baseline_full.shape != raw_full.shape or wpt_full.shape != raw_full.shape:
        raise ValueError("O processamento integral nao preservou o comprimento.")

    baseline_cut = baseline_full[cut_start:cut_stop]
    wpt_cut = wpt_full[cut_start:cut_stop]
    if baseline_cut.shape != wpt_cut.shape:
        raise ValueError("Os sinais do par nao possuem o mesmo comprimento.")

    private_output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "A_baseline_pre_bridge.wav": baseline_cut,
        "B_wpt_causal_pre_bridge.wav": wpt_cut,
    }
    private_files = []
    for name, samples in outputs.items():
        path = private_output_dir / name
        write_pcm16(path, samples)
        private_files.append(
            {
                "name": name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "samples": int(samples.size),
                "duration_s": samples.size / SAMPLE_RATE,
            }
        )

    config = CausalWPTConfig()
    summary: dict[str, object] = {
        "date": "2026-06-13",
        "checkpoint": 46,
        "status": "private_listening_pending",
        "privacy": "private_audio_outside_repository",
        "source_authorization": "checkpoint38_explicit_user_authorization",
        "new_voice_recording": False,
        "private_audio_location": str(private_output_dir),
        "sources": {
            "raw_full_sha256": sha256(raw_full_path),
            "baseline_reference_sha256": sha256(baseline_reference_path),
            "cut_start_sample": cut_start,
            "cut_stop_sample": cut_stop,
            "cut_duration_s": (cut_stop - cut_start) / SAMPLE_RATE,
        },
        "pair": {
            "sample_rate_hz": SAMPLE_RATE,
            "channels": 1,
            "sample_width_bits": 16,
            "fade_ms": 0,
            "normalization": "none",
            "common_cut": True,
            "files": private_files,
        },
        "baseline": {
            "method": "causal_stft_subtraction",
            "reference_reproduction": compare_signals(
                baseline_reference,
                baseline_cut,
            ),
        },
        "causal_wpt": {
            "frame_length": config.frame_length,
            "block_size": config.block_size,
            "wavelet": config.wavelet,
            "level": config.level,
            "warmup_blocks": config.warmup_blocks,
            "history_blocks": config.history_blocks,
            "noise_quantile": config.noise_quantile,
            "gain_floor": config.gain_floor,
        },
        "listening_dimensions": [
            "intelligibility",
            "naturalness",
            "metallic_hiss",
            "overall_preference",
        ],
        "human_listening_requested": True,
        "human_decision": None,
        "app_integrated": False,
        "end_to_end_run": False,
    }
    encoded = json.dumps(summary, indent=2, ensure_ascii=False)
    public_output.parent.mkdir(parents=True, exist_ok=True)
    public_output.write_text(encoded, encoding="utf-8")
    (private_output_dir / "private_manifest.json").write_text(
        encoded,
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-full", type=Path, required=True)
    parser.add_argument("--baseline-reference", type=Path, required=True)
    parser.add_argument("--cut-start", type=int, required=True)
    parser.add_argument("--cut-stop", type=int, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    args = parser.parse_args()

    prepare_pair(
        raw_full_path=args.raw_full,
        baseline_reference_path=args.baseline_reference,
        cut_start=args.cut_start,
        cut_stop=args.cut_stop,
        private_output_dir=args.private_output_dir,
        public_output=args.public_output,
    )
    print(args.public_output)


if __name__ == "__main__":
    main()
