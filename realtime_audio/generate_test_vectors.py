from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from benchmark_audio.causal import CausalProcessorConfig
from realtime_audio.process_wav_blocks import (
    TARGET_SAMPLE_RATE,
    process_samples_in_blocks,
    read_wav_for_processing,
    sha256_file,
    write_pcm16,
)


ROOT = Path(__file__).resolve().parents[1]


def generate(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = CausalProcessorConfig(method="stft_subtraction", noise_mode="adaptive")
    block_ms = 20.0
    rng = np.random.default_rng(3527)
    n_samples = int(0.75 * TARGET_SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float32) / TARGET_SAMPLE_RATE
    speech_like = (
        0.22 * np.sin(2 * np.pi * 180 * t)
        + 0.10 * np.sin(2 * np.pi * 360 * t)
        + 0.05 * np.sin(2 * np.pi * 720 * t)
    )
    envelope = np.clip((t - 0.08) / 0.05, 0.0, 1.0)
    noisy = (speech_like * envelope + rng.normal(scale=0.06, size=n_samples)).astype(
        np.float32
    )

    input_path = output_dir / "noisy_input.wav"
    bypass_path = output_dir / "expected_bypass.wav"
    causal_path = output_dir / "expected_causal_subtraction.wav"
    config_path = output_dir / "config.json"
    manifest_path = output_dir / "manifest.json"

    write_pcm16(input_path, noisy)
    decoded_input, _ = read_wav_for_processing(input_path)
    bypass, _ = process_samples_in_blocks(
        decoded_input,
        CausalProcessorConfig(method="bypass"),
        block_ms,
    )
    causal, _ = process_samples_in_blocks(decoded_input, config, block_ms)
    write_pcm16(bypass_path, bypass)
    write_pcm16(causal_path, causal)
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "block_ms": block_ms,
                "causal_config": asdict(config),
            },
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    artifacts = {}
    for path in (input_path, bypass_path, causal_path, config_path):
        artifacts[path.name] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    manifest = {
        "schema_version": 1,
        "source": "Deterministic synthetic tones plus seeded Gaussian noise.",
        "seed": 3527,
        "sample_rate": TARGET_SAMPLE_RATE,
        "samples": n_samples,
        "block_ms": block_ms,
        "numeric_tolerance_float32": 1e-6,
        "numeric_tolerance_pcm16": 1.0 / 32768.0,
        "expected_behavior": (
            "Decode input to float32, process blocks in order with a reset processor, "
            "and compare decoded expected WAVs within the declared PCM16 tolerance."
        ),
        "artifacts": artifacts,
        "private_data": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera vetores sinteticos curtos para a futura transicao Raspberry Pi."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "test_vectors" / "file_blocks",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    generate(output_dir)
    print(f"Vetores gerados em {output_dir}")


if __name__ == "__main__":
    main()
