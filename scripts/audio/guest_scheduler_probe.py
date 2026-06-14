from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def wait_for_file(path: Path, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.01)
    raise TimeoutError(f"marker was not created: {path}")


def publish_ready(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("ready\n", encoding="ascii")
    temporary.replace(path)


def summarize(values: list[float], prefix: str) -> dict[str, float]:
    samples = np.asarray(values, dtype=np.float64)
    return {
        f"{prefix}_mean": float(np.mean(samples)) if values else 0.0,
        f"{prefix}_p95": (
            float(np.percentile(samples, 95)) if values else 0.0
        ),
        f"{prefix}_p99": (
            float(np.percentile(samples, 99)) if values else 0.0
        ),
        f"{prefix}_max": float(np.max(samples)) if values else 0.0,
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    publish_ready(args.ready_file)
    wait_for_file(args.start_file, args.start_timeout)
    started_ns = time.perf_counter_ns()
    previous_ns = started_ns
    deadline_ns = started_ns + int(args.max_duration * 1e9)
    interval_ns = int(args.interval_ms * 1e6)
    intervals_ms: list[float] = []
    samples: list[dict[str, float | int]] = []
    while time.perf_counter_ns() < deadline_ns and not args.stop_file.is_file():
        time.sleep(args.interval_ms / 1000.0)
        current_ns = time.perf_counter_ns()
        interval_ms = (current_ns - previous_ns) / 1e6
        intervals_ms.append(interval_ms)
        samples.append(
            {
                "qpc_ns": current_ns,
                "interval_ms": interval_ms,
                "lateness_ms": max(
                    0.0,
                    (current_ns - previous_ns - interval_ns) / 1e6,
                ),
            }
        )
        previous_ns = current_ns
    result: dict[str, object] = {
        "status": "completed",
        "interval_ms": args.interval_ms,
        "sample_count": len(samples),
        "elapsed_ms": (previous_ns - started_ns) / 1e6,
        "gaps_over_10ms": sum(value > 10.0 for value in intervals_ms),
        "gaps_over_30ms": sum(value > 30.0 for value in intervals_ms),
        "gaps_over_100ms": sum(value > 100.0 for value in intervals_ms),
        "samples": samples,
    }
    result.update(summarize(intervals_ms, "observed_interval_ms"))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--start-file", type=Path, required=True)
    parser.add_argument("--stop-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval-ms", type=float, default=2.0)
    parser.add_argument("--max-duration", type=float, default=40.0)
    parser.add_argument("--start-timeout", type=float, default=120.0)
    args = parser.parse_args()
    result = run(args)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
