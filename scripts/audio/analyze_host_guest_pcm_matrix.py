from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCENARIOS = (
    ("01-bypass-v0", "bypass", 0),
    ("02-rnnoise-v0", "rnnoise", 0),
    ("03-rnnoise-v1", "rnnoise", 1),
    ("04-bypass-v1", "bypass", 1),
)
PHYSICAL_SCENARIOS = (
    ("01-bypass-physical", "bypass", 0),
    ("02-rnnoise-physical", "rnnoise", 0),
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def analyze(root: Path, *, mode: str = "synthetic") -> dict[str, Any]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    loaded: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    scenarios = SCENARIOS if mode == "synthetic" else PHYSICAL_SCENARIOS

    for name, method, variant in scenarios:
        scenario_root = root / name
        server = read_json(scenario_root / "server.json")
        client = read_json(scenario_root / "client.json")
        loaded[name] = (server, client)
        prefix = f"{name}:"
        check(server.get("status") == "completed", prefix + "server", failures)
        check(client.get("status") == "completed", prefix + "client", failures)
        check(client.get("method") == method, prefix + "method", failures)
        check(server.get("variant") == variant, prefix + "variant", failures)
        check(
            server.get("block_count") == client.get("block_count"),
            prefix + "block_count",
            failures,
        )
        check(
            server.get("input_sha256") == client.get("input_sha256"),
            prefix + "input_hash",
            failures,
        )
        check(client.get("sequence_errors") == 0, prefix + "sequence", failures)
        check(client.get("crc_errors") == 0, prefix + "crc", failures)
        check(client.get("framing_errors") == 0, prefix + "framing", failures)
        check(
            server.get("receiver_ack", {}).get("received")
            == server.get("block_count"),
            prefix + "ack_count",
            failures,
        )
        check(
            server.get("receiver_ack", {}).get("sequence_errors") == 0,
            prefix + "ack_sequence",
            failures,
        )
        check(
            0.98 <= float(server.get("audio_to_covered_ratio", 0.0)) <= 1.02,
            prefix + "server_cadence_ratio",
            failures,
        )
        check(
            0.98 <= float(client.get("audio_to_covered_ratio", 0.0)) <= 1.02,
            prefix + "client_cadence_ratio",
            failures,
        )
        check(
            int(server.get("interval_stalls_over_100ms", 1)) == 0,
            prefix + "server_stall_100ms",
            failures,
        )
        check(
            int(client.get("interval_stalls_over_100ms", 1)) == 0,
            prefix + "client_stall_100ms",
            failures,
        )
        rows.append(
            {
                "scenario": name,
                "method": method,
                "variant": variant,
                "blocks": client.get("block_count"),
                "input_sha256": client.get("input_sha256"),
                "output_sha256": client.get("output_float32_sha256"),
                "output_prefix_sha256": client.get(
                    "output_prefix_float32_sha256"
                ),
                "server_interval_p99_ms": server.get("send_interval_ms_p99"),
                "server_interval_max_ms": server.get("send_interval_ms_max"),
                "client_interval_p99_ms": client.get(
                    "receive_interval_ms_p99"
                ),
                "client_interval_max_ms": client.get(
                    "receive_interval_ms_max"
                ),
                "client_stalls_over_30ms": client.get(
                    "interval_stalls_over_30ms"
                ),
                "client_bursts_under_10ms": client.get(
                    "interval_bursts_under_10ms"
                ),
                "processing_p99_ms": client.get("processing_ms_p99"),
                "processing_max_ms": client.get("processing_ms_max"),
                "processing_over_20ms": client.get("processing_over_20ms"),
            }
        )

    if mode == "synthetic":
        bypass_v0 = loaded["01-bypass-v0"][1]
        rnnoise_v0 = loaded["02-rnnoise-v0"][1]
        rnnoise_v1 = loaded["03-rnnoise-v1"][1]
        bypass_v1 = loaded["04-bypass-v1"][1]
        check(
            bypass_v0["input_sha256"] == rnnoise_v0["input_sha256"],
            "paired_input_v0",
            failures,
        )
        check(
            bypass_v1["input_sha256"] == rnnoise_v1["input_sha256"],
            "paired_input_v1",
            failures,
        )
        check(
            bypass_v0["input_sha256"] != bypass_v1["input_sha256"],
            "variant_inputs_diverge",
            failures,
        )
        check(
            bypass_v0["output_prefix_float32_sha256"]
            == bypass_v1["output_prefix_float32_sha256"],
            "bypass_causal_prefix",
            failures,
        )
        check(
            rnnoise_v0["output_prefix_float32_sha256"]
            == rnnoise_v1["output_prefix_float32_sha256"],
            "rnnoise_causal_prefix",
            failures,
        )
    else:
        bypass = loaded["01-bypass-physical"][1]
        rnnoise = loaded["02-rnnoise-physical"][1]
        check(
            bypass["input_sha256"] == rnnoise["input_sha256"],
            "paired_physical_input",
            failures,
        )

    return {
        "status": "accepted" if not failures else "rejected",
        "mode": mode,
        "contract": {
            "sample_rate": 16_000,
            "frames_per_block": 320,
            "block_duration_ms": 20,
            "driver_changed": False,
            "pcm_v1_changed": False,
            "driver_depth_changed": False,
            "local_queue_changed": False,
        },
        "scenario_count": len(rows),
        "failures": failures,
        "scenarios": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=("synthetic", "physical"),
        default="synthetic",
    )
    args = parser.parse_args()

    result = analyze(args.root, mode=args.mode)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if result["status"] != "accepted":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
