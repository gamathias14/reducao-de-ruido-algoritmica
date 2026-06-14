from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from df.enhance import enhance, init_df


def main() -> int:
    model_dir = os.environ.get("PTC3527_DEEPFILTERNET_MODEL")
    if model_dir is None:
        model_dir = str(
            Path.home()
            / ".cache"
            / "ptc3527-benchmark"
            / "deepfilternet-v0.5.6"
            / "DeepFilterNet3"
        )
    started = time.perf_counter()
    model, df_state, _ = init_df(
        model_base_dir=model_dir,
        log_level="ERROR",
        log_file=None,
        config_allow_defaults=True,
    )
    init_seconds = time.perf_counter() - started

    payload = sys.stdin.buffer.read()
    if len(payload) % 4:
        print("input byte count is not divisible by four", file=sys.stderr)
        return 2
    values = np.frombuffer(payload, dtype="<f4").copy()
    audio = torch.from_numpy(values).reshape(1, -1)
    started = time.perf_counter()
    output = enhance(model, df_state, audio, pad=False)
    processing_seconds = time.perf_counter() - started
    result = output.detach().cpu().numpy().reshape(-1).astype("<f4", copy=False)
    model_lookahead_samples = 2 * 480
    result = np.pad(result, (model_lookahead_samples, 0))[: len(values)]
    sys.stdout.buffer.write(result.tobytes(order="C"))
    print(
        "sample_rate=48000 "
        "fft_size=960 hop_size=480 lookahead_frames=2 "
        "causal_delay_samples=1440 "
        f"input_samples={len(values)} output_samples={len(result)} "
        f"init_seconds={init_seconds:.9f} "
        f"processing_seconds={processing_seconds:.9f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
