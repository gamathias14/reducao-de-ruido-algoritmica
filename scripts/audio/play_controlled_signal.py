from __future__ import annotations

import argparse
import math
import time

import numpy as np
import sounddevice as sd


def find_output_device(name_substring: str) -> int:
    needle = name_substring.casefold()
    host_apis = sd.query_hostapis()
    matches = [
        index
        for index, device in enumerate(sd.query_devices())
        if int(device["max_output_channels"]) > 0
        and needle
        in (
            f"{device['name']}, "
            f"{host_apis[int(device['hostapi'])]['name']}"
        ).casefold()
    ]
    if not matches:
        raise RuntimeError(f"Dispositivo de saida nao encontrado: {name_substring}")
    if len(matches) > 1:
        names = ", ".join(f"{index}:{sd.query_devices(index)['name']}" for index in matches)
        raise RuntimeError(f"Saida ambigua ({names}); use um nome mais especifico.")
    return matches[0]


def _quality_matrix_mono(
    time_s: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    carrier = (
        0.55 * np.sin(2.0 * math.pi * 220.0 * time_s)
        + 0.30 * np.sin(2.0 * math.pi * 440.0 * time_s + 0.3)
        + 0.15 * np.sin(2.0 * math.pi * 880.0 * time_s + 0.7)
    )
    cycle_s = np.mod(time_s, 10.0)
    noise = rng.normal(scale=0.0125, size=time_s.size)

    noise_gate = ((cycle_s >= 2.0) & (cycle_s < 10.0)).astype(np.float64)
    active_gate = ((cycle_s >= 4.0) & (cycle_s < 8.0)).astype(np.float64)
    ramp_s = 0.04
    noise_gate = np.where(
        (cycle_s >= 2.0) & (cycle_s < 2.0 + ramp_s),
        np.sin(0.5 * math.pi * (cycle_s - 2.0) / ramp_s) ** 2,
        noise_gate,
    )
    noise_gate = np.where(
        cycle_s >= 10.0 - ramp_s,
        np.cos(0.5 * math.pi * (cycle_s - (10.0 - ramp_s)) / ramp_s) ** 2,
        noise_gate,
    )
    active_gate = np.where(
        (cycle_s >= 4.0) & (cycle_s < 4.0 + ramp_s),
        np.sin(0.5 * math.pi * (cycle_s - 4.0) / ramp_s) ** 2,
        active_gate,
    )
    active_gate = np.where(
        (cycle_s >= 8.0 - ramp_s) & (cycle_s < 8.0),
        np.cos(0.5 * math.pi * (cycle_s - (8.0 - ramp_s)) / ramp_s) ** 2,
        active_gate,
    )

    syllable_phase = np.mod(time_s, 0.8)
    active_envelope = 0.30 + 0.70 * np.sin(
        math.pi * np.minimum(syllable_phase, 0.64) / 0.64
    ) ** 2
    active_envelope[syllable_phase >= 0.64] = 0.0
    mono = noise * noise_gate + carrier * active_envelope * active_gate
    return np.clip(mono, -1.0, 1.0)


def build_signal(
    duration_s: float,
    sample_rate: int,
    peak: float,
    *,
    mode: str = "enveloped",
    seed: int = 3527,
) -> np.ndarray:
    frames = int(round(duration_s * sample_rate))
    time_s = np.arange(frames, dtype=np.float64) / sample_rate

    carrier = (
        0.55 * np.sin(2.0 * math.pi * 220.0 * time_s)
        + 0.30 * np.sin(2.0 * math.pi * 440.0 * time_s + 0.3)
        + 0.15 * np.sin(2.0 * math.pi * 880.0 * time_s + 0.7)
    )
    if mode == "continuous":
        mono = carrier
    elif mode == "enveloped":
        syllable_phase = np.mod(time_s, 1.0)
        envelope = np.where(
            syllable_phase < 0.72,
            0.25 + 0.75 * np.sin(math.pi * syllable_phase / 0.72) ** 2,
            0.0,
        )
        slow_modulation = 0.75 + 0.25 * np.sin(2.0 * math.pi * 0.37 * time_s)
        mono = carrier * envelope * slow_modulation
    elif mode == "quality-matrix":
        rng = np.random.default_rng(seed)
        mono = _quality_matrix_mono(time_s, rng)
        return np.column_stack((mono, mono)).astype(np.float32) * peak
    else:
        raise ValueError(f"Modo de sinal inválido: {mode}")
    mono *= peak / max(float(np.max(np.abs(mono))), np.finfo(np.float64).eps)
    return np.column_stack((mono, mono)).astype(np.float32)


def play_quality_matrix(
    *,
    device: int,
    duration_s: float,
    sample_rate: int,
    peak: float,
    seed: int,
) -> None:
    total_frames = int(round(duration_s * sample_rate))
    frame_index = 0
    rng = np.random.default_rng(seed)

    def callback(
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        nonlocal frame_index
        remaining = total_frames - frame_index
        count = min(frames, max(0, remaining))
        outdata.fill(0.0)
        if count:
            indices = frame_index + np.arange(count, dtype=np.float64)
            mono = _quality_matrix_mono(indices / sample_rate, rng) * peak
            outdata[:count, 0] = mono
            outdata[:count, 1] = mono
            frame_index += count
        if count < frames or frame_index >= total_frames:
            raise sd.CallbackStop

    with sd.OutputStream(
        samplerate=sample_rate,
        device=device,
        channels=2,
        dtype="float32",
        callback=callback,
    ) as stream:
        while stream.active:
            time.sleep(0.05)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproduz um sinal deterministico para ensaios da ponte virtual."
    )
    parser.add_argument("--output-device", required=True, help="Substring unica da saida.")
    parser.add_argument("--duration", type=float, default=75.0, help="Duracao em segundos.")
    parser.add_argument("--sample-rate", type=int, default=48_000)
    parser.add_argument(
        "--peak",
        type=float,
        default=0.10,
        help="Pico linear ou teto do modo em blocos, entre 0 e 1.",
    )
    parser.add_argument(
        "--mode",
        choices=("enveloped", "continuous", "quality-matrix"),
        default="enveloped",
        help="Envelope conhecido ou multiton contínuo para diagnóstico.",
    )
    parser.add_argument("--seed", type=int, default=3527)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.duration <= 0:
        raise ValueError("A duracao deve ser positiva.")
    if not 0.0 < args.peak <= 1.0:
        raise ValueError("O pico deve estar no intervalo (0, 1].")

    device = find_output_device(args.output_device)
    if args.mode == "quality-matrix":
        print(
            f"device={device} name={sd.query_devices(device)['name']} "
            f"duration_s={args.duration:.3f} peak={args.peak:.6f} "
            f"mode=quality-matrix seed={args.seed}",
            flush=True,
        )
        play_quality_matrix(
            device=device,
            duration_s=args.duration,
            sample_rate=args.sample_rate,
            peak=args.peak,
            seed=args.seed,
        )
        return
    signal = build_signal(
        args.duration,
        args.sample_rate,
        args.peak,
        mode=args.mode,
        seed=args.seed,
    )
    rms = float(np.sqrt(np.mean(np.square(signal[:, 0], dtype=np.float64))))
    print(
        f"device={device} name={sd.query_devices(device)['name']} "
        f"duration_s={args.duration:.3f} peak={np.max(np.abs(signal)):.6f} "
        f"rms={rms:.6f}"
    )
    sd.play(signal, samplerate=args.sample_rate, device=device, blocking=True)


if __name__ == "__main__":
    main()
