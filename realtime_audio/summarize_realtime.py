from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def flatten_metrics(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    config = data.get("config", {})
    summary = data.get("summary", {})
    stream_latency = data.get("stream_latency_ms") or {}
    return {
        "arquivo": path.name,
        "label": data.get("label", ""),
        "sample_rate": config.get("sample_rate", ""),
        "block_ms": config.get("block_ms", ""),
        "method": config.get("method", ""),
        "noise_mode": config.get("noise_mode", ""),
        "calibration_ms": config.get("calibration_ms", ""),
        "n_fft": config.get("n_fft", ""),
        "hop_length": config.get("hop_length", ""),
        "blocks": summary.get("blocks", ""),
        "processing_mean_ms": summary.get("processing_mean_ms", ""),
        "processing_worst_ms": summary.get("processing_worst_ms", ""),
        "processing_std_ms": summary.get("processing_std_ms", ""),
        "processing_p95_ms": summary.get("processing_p95_ms", ""),
        "processing_p99_ms": summary.get("processing_p99_ms", ""),
        "rtf_block_mean": summary.get("rtf_block_mean", ""),
        "rtf_block_worst": summary.get("rtf_block_worst", ""),
        "blocks_over_budget": summary.get("blocks_over_budget", ""),
        "state_memory_max_bytes": summary.get("state_memory_max_bytes", ""),
        "speech_probable_fraction": summary.get("speech_probable_fraction", ""),
        "warming_blocks": summary.get("warming_blocks", ""),
        "input_latency_ms": stream_latency.get("input_ms", ""),
        "output_latency_ms": stream_latency.get("output_ms", ""),
        "io_total_latency_ms": stream_latency.get("io_total_ms", ""),
        "algorithmic_latency_estimated_ms": data.get("algorithmic_latency_estimated_ms", ""),
        "total_latency_estimated_ms": data.get("total_latency_estimated_ms", ""),
        "status_counts": json.dumps(data.get("status_counts", {}), ensure_ascii=False, sort_keys=True),
    }


def summarize(input_dir: Path, output_path: Path, pattern: str) -> None:
    rows = [flatten_metrics(path) for path in sorted(input_dir.glob(pattern))]
    if not rows:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em {input_dir} com padrao {pattern!r}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agrega metricas JSON do prototipo realtime em CSV.")
    parser.add_argument("--input-dir", default=str(ROOT / "resultados" / "realtime"))
    parser.add_argument("--output", default=str(ROOT / "resultados" / "tabelas" / "realtime_windows_summary.csv"))
    parser.add_argument("--pattern", default="*_metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summarize(Path(args.input_dir), Path(args.output), args.pattern)
    print(f"Resumo salvo em {args.output}")


if __name__ == "__main__":
    main()
