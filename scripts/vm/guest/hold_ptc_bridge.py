from __future__ import annotations

import argparse
import time

from realtime_audio.ptc_pcm_bridge import PtcPcmBridgeClient


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mantém a ponte PTC PCM ocupada para teste de contenção."
    )
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()

    client = PtcPcmBridgeClient()
    client.open()
    print("READY", flush=True)
    try:
        time.sleep(args.duration)
    finally:
        client.close()


if __name__ == "__main__":
    main()
