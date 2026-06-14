from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\PTC3527\checkpoint45")
sys.path.insert(0, str(ROOT))

from causal_wpt import CausalWPTConfig, CausalWPTProcessor


def blocks(count: int) -> list[np.ndarray]:
    rng = np.random.default_rng(3527)
    return [
        rng.normal(scale=0.04, size=320).astype(np.float32)
        for _ in range(count)
    ]


def run(processor: CausalWPTProcessor, values: list[np.ndarray]) -> np.ndarray:
    return np.concatenate([processor.process_block(block)[0] for block in values])


def main() -> None:
    config = CausalWPTConfig()
    values = blocks(100)
    processor = CausalWPTProcessor(config)
    started = time.perf_counter()
    first = run(processor, values)
    elapsed_ms = 1_000.0 * (time.perf_counter() - started)
    processor.reset()
    second = run(processor, values)
    if not np.array_equal(first, second):
        raise RuntimeError("Reset nao reproduziu a mesma saida.")
    if not np.all(np.isfinite(first)):
        raise RuntimeError("Saida nao finita.")

    prefix = values[:20]
    left = CausalWPTProcessor(config)
    right = CausalWPTProcessor(config)
    left_prefix = run(left, prefix)
    right_prefix = run(right, prefix)
    left.process_block(np.ones(320, dtype=np.float32))
    right.process_block(-np.ones(320, dtype=np.float32))
    if not np.array_equal(left_prefix, right_prefix):
        raise RuntimeError("O futuro alterou o prefixo comum.")

    average_ms = elapsed_ms / len(values)
    if average_ms >= 20.0:
        raise RuntimeError(f"Custo medio excedeu o bloco: {average_ms:.3f} ms.")
    if processor.state_memory_bytes >= 64 * 1024:
        raise RuntimeError("Estado excedeu 64 KiB.")

    print(
        json.dumps(
            {
                "source": "deterministic_synthetic_no_voice",
                "blocks": len(values),
                "average_ms": average_ms,
                "state_memory_bytes": processor.state_memory_bytes,
                "algorithmic_context_ms": config.algorithmic_context_ms,
                "result": "CHECKPOINT45_VM_VALIDATION=OK",
            },
            sort_keys=True,
        )
    )
    print("CHECKPOINT45_VM_VALIDATION=OK")


if __name__ == "__main__":
    main()
