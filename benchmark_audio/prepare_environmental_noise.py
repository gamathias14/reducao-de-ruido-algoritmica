from __future__ import annotations

import argparse
import csv
import hashlib
import io
import math
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError

import numpy as np
from scipy import signal
from scipy.io import wavfile

from .denoise import SAMPLE_RATE, normalize_peak, write_wav


ROOT = Path(__file__).resolve().parents[1]
DEMAND_RECORD_URL = "https://zenodo.org/records/1227121"
DEMAND_RECORD_API = "https://zenodo.org/api/records/1227121"
DEMAND_DOI = "10.5281/zenodo.1227121"
DEMAND_LICENSE = "CC BY-SA 3.0"
DEMAND_LICENSE_NOTE = (
    "O texto descritivo do registro Zenodo informa CC BY-SA 3.0 para obra, audio e documento; "
    "o metadado atual de direitos no Zenodo tambem deve ser conferido antes de redistribuir derivados."
)
DEFAULT_DEMAND_SUBSET = ("DKITCHEN", "OOFFICE", "PCAFETER", "STRAFFIC")


@dataclass(frozen=True)
class DemandArchive:
    code: str
    category: str
    description: str
    filename: str
    size_bytes: int
    md5: str
    sample_rate: int = SAMPLE_RATE

    @property
    def url(self) -> str:
        return f"{DEMAND_RECORD_API}/files/{self.filename}/content"


DEMAND_16K_ARCHIVES: tuple[DemandArchive, ...] = (
    DemandArchive("DKITCHEN", "domestic", "kitchen", "DKITCHEN_16k.zip", 110_501_049, "7ffbf52d7f4699f96927846103dc8788"),
    DemandArchive("DLIVING", "domestic", "living room", "DLIVING_16k.zip", 80_170_627, "46741384d9e434a0bd8b3ec1830b6052"),
    DemandArchive("DWASHING", "domestic", "washing room", "DWASHING_16k.zip", 102_343_250, "7e5ee9437ce9409c5f9a779b6212a240"),
    DemandArchive("NFIELD", "nature", "field", "NFIELD_16k.zip", 86_536_782, "a740046c6f4e174e16f5d568aaec5024"),
    DemandArchive("NPARK", "nature", "park", "NPARK_16k.zip", 86_029_332, "80f1385a34d7f1705758926b57f138ce"),
    DemandArchive("NRIVER", "nature", "river", "NRIVER_16k.zip", 98_689_565, "54264db61d3fe073fb81f2e40e0d19b5"),
    DemandArchive("OHALLWAY", "office", "hallway", "OHALLWAY_16k.zip", 77_941_854, "fe918bbb0e63e73d09ba7f4843ef33f1"),
    DemandArchive("OMEETING", "office", "meeting room", "OMEETING_16k.zip", 82_703_355, "62f7cfe7fe6d30b7d8a215fe37c2dfd2"),
    DemandArchive("OOFFICE", "office", "office", "OOFFICE_16k.zip", 88_995_191, "7b61cc2d182d5a654cb9c3101ddd4041"),
    DemandArchive("PCAFETER", "public", "cafeteria", "PCAFETER_16k.zip", 107_431_494, "99927d148128254141a9417d051510bb"),
    DemandArchive("PRESTO", "public", "restaurant", "PRESTO_16k.zip", 111_292_815, "b98d2e6854eeebb397f29a8ad7457092"),
    DemandArchive("PSTATION", "public", "station", "PSTATION_16k.zip", 119_441_094, "d7448009f6c2aeb6ba570375df1750a3"),
    DemandArchive("SPSQUARE", "public", "public square", "SPSQUARE_16k.zip", 110_928_528, "205d0e7b8fe74504a2f8d252fc414b9e"),
    DemandArchive("STRAFFIC", "transport", "traffic", "STRAFFIC_16k.zip", 118_572_691, "2efa87262f272bbf9ba578088e81939c"),
    DemandArchive("TBUS", "transport", "bus", "TBUS_16k.zip", 128_916_709, "706b11b0d8504f9f3b3f3211e91b3863"),
    DemandArchive("TCAR", "transport", "car", "TCAR_16k.zip", 130_045_975, "4d930012796bd298932245a26189f973"),
    DemandArchive("TMETRO", "transport", "metro", "TMETRO_16k.zip", 126_589_090, "95daf4df678e13b120e14211e6d89571"),
)


def demand_archives_by_code() -> dict[str, DemandArchive]:
    return {archive.code: archive for archive in DEMAND_16K_ARCHIVES}


def selected_archives(environments: list[str] | tuple[str, ...] | None) -> list[DemandArchive]:
    archives_by_code = demand_archives_by_code()
    if environments is None:
        codes = DEFAULT_DEMAND_SUBSET
    else:
        codes = tuple(code.upper() for code in environments)

    unknown = sorted(set(codes) - set(archives_by_code))
    if unknown:
        raise ValueError(f"Ambientes DEMAND desconhecidos: {', '.join(unknown)}")
    return [archives_by_code[code] for code in codes]


def relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def default_paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "raw": root / "dados" / "external" / "demand",
        "prepared": root / "dados" / "demo" / "noise_demand",
        "tables": root / "resultados" / "tabelas",
    }


def write_demand_manifest(path: Path, archives: list[DemandArchive] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = archives if archives is not None else list(DEMAND_16K_ARCHIVES)
    fieldnames = [
        "dataset",
        "code",
        "category",
        "description",
        "sample_rate_hz",
        "filename",
        "size_bytes",
        "md5",
        "source_url",
        "record_url",
        "doi",
        "license",
        "license_note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for archive in selected:
            writer.writerow(
                {
                    "dataset": "DEMAND",
                    "code": archive.code,
                    "category": archive.category,
                    "description": archive.description,
                    "sample_rate_hz": archive.sample_rate,
                    "filename": archive.filename,
                    "size_bytes": archive.size_bytes,
                    "md5": archive.md5,
                    "source_url": archive.url,
                    "record_url": DEMAND_RECORD_URL,
                    "doi": DEMAND_DOI,
                    "license": DEMAND_LICENSE,
                    "license_note": DEMAND_LICENSE_NOTE,
                }
            )


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_archive(archive: DemandArchive, raw_dir: Path, download: bool, retries: int = 4) -> Path | None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / archive.filename
    if target.exists() and target.stat().st_size > 0:
        if file_md5(target) == archive.md5:
            return target
        if not download:
            raise RuntimeError(f"Arquivo local com MD5 inesperado: {target}")

    if not download:
        return None

    request = urllib.request.Request(archive.url, headers={"User-Agent": "ptc3527-demand-prep/0.1"})
    tmp = target.with_suffix(target.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                with tmp.open("wb") as handle:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        handle.write(chunk)
            tmp.replace(target)
            if file_md5(target) != archive.md5:
                raise RuntimeError(f"MD5 inesperado apos download de {archive.filename}")
            return target
        except (HTTPError, URLError, ConnectionResetError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if tmp.exists():
                tmp.unlink()
            if attempt < retries:
                time.sleep(2.0 * attempt)

    raise RuntimeError(f"Nao foi possivel baixar {archive.filename}: {last_error}") from last_error


def select_channel_member(wav_members: list[str], channel: int) -> str:
    if not wav_members:
        raise ValueError("O arquivo ZIP nao contem WAVs.")
    if channel < 1:
        raise ValueError("O canal DEMAND deve ser >= 1.")

    sorted_members = sorted(wav_members)
    candidates = [f"ch{channel:02d}", f"ch{channel}", f"_{channel:02d}", f"_{channel}"]
    for member in sorted_members:
        stem = Path(member).stem.lower()
        if any(token in stem for token in candidates):
            return member

    index = channel - 1
    if index >= len(sorted_members):
        raise ValueError(f"Canal {channel} indisponivel; ZIP contem {len(sorted_members)} WAVs.")
    return sorted_members[index]


def wav_bytes_to_float_mono(data: bytes, target_sr: int) -> np.ndarray:
    sample_rate, audio = wavfile.read(io.BytesIO(data))
    audio = np.asarray(audio)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if np.issubdtype(audio.dtype, np.integer):
        scale = float(np.iinfo(audio.dtype).max)
        audio = audio.astype(np.float32) / scale
    else:
        audio = audio.astype(np.float32)
    if sample_rate != target_sr:
        gcd = math.gcd(int(sample_rate), int(target_sr))
        audio = signal.resample_poly(audio, target_sr // gcd, sample_rate // gcd).astype(np.float32)
    return normalize_peak(audio, peak=0.95)


def load_demand_channel(zip_path: Path, channel: int, target_sr: int) -> tuple[np.ndarray, str]:
    with zipfile.ZipFile(zip_path) as archive:
        wav_members = [name for name in archive.namelist() if name.lower().endswith(".wav")]
        member = select_channel_member(wav_members, channel)
        data = archive.read(member)
    return wav_bytes_to_float_mono(data, target_sr), member


def segment_audio(audio: np.ndarray, segment_samples: int, max_segments: int) -> list[np.ndarray]:
    if segment_samples <= 0:
        raise ValueError("Duracao do segmento deve gerar ao menos uma amostra.")
    if max_segments <= 0:
        return []
    if audio.size == 0:
        return []
    if len(audio) < segment_samples:
        repeats = math.ceil(segment_samples / len(audio))
        audio = np.tile(audio, repeats)

    available = len(audio) // segment_samples
    n_segments = min(max_segments, available)
    segments = []
    for index in range(n_segments):
        start = index * segment_samples
        segments.append(audio[start : start + segment_samples].astype(np.float32))
    return segments


def write_prepared_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset",
        "code",
        "category",
        "description",
        "channel",
        "segment_index",
        "source_archive",
        "source_member",
        "output_wav",
        "sample_rate_hz",
        "duration_s",
        "samples",
        "preprocessing",
        "status",
        "message",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prepare_demand_noise(
    *,
    root: Path = ROOT,
    environments: list[str] | tuple[str, ...] | None = None,
    channel: int = 1,
    segment_duration_s: float = 3.0,
    max_segments_per_env: int = 3,
    download: bool = False,
) -> list[dict[str, object]]:
    paths = default_paths(root)
    paths["raw"].mkdir(parents=True, exist_ok=True)
    paths["prepared"].mkdir(parents=True, exist_ok=True)
    paths["tables"].mkdir(parents=True, exist_ok=True)

    archives = selected_archives(environments)
    write_demand_manifest(paths["tables"] / "demand_archives_manifest.csv", list(DEMAND_16K_ARCHIVES))

    rows: list[dict[str, object]] = []
    segment_samples = int(round(SAMPLE_RATE * segment_duration_s))
    for archive in archives:
        base_row = {
            "dataset": "DEMAND",
            "code": archive.code,
            "category": archive.category,
            "description": archive.description,
            "channel": channel,
            "source_archive": relative_or_absolute(paths["raw"] / archive.filename, root),
            "sample_rate_hz": SAMPLE_RATE,
            "duration_s": segment_duration_s,
            "preprocessing": "single channel, mono float32, peak normalization, fixed non-overlapping segments",
        }
        zip_path = ensure_archive(archive, paths["raw"], download=download)
        if zip_path is None:
            rows.append(
                {
                    **base_row,
                    "segment_index": "",
                    "source_member": "",
                    "output_wav": "",
                    "samples": "",
                    "status": "missing_archive",
                    "message": "Arquivo ausente; rode novamente com --download ou copie o ZIP para dados/external/demand.",
                }
            )
            continue

        audio, member = load_demand_channel(zip_path, channel=channel, target_sr=SAMPLE_RATE)
        segments = segment_audio(audio, segment_samples, max_segments_per_env)
        for index, segment in enumerate(segments, start=1):
            out = paths["prepared"] / f"{archive.code.lower()}_ch{channel:02d}_seg{index:02d}.wav"
            write_wav(out, segment, SAMPLE_RATE)
            rows.append(
                {
                    **base_row,
                    "segment_index": index,
                    "source_member": member,
                    "output_wav": relative_or_absolute(out, root),
                    "samples": int(len(segment)),
                    "status": "prepared",
                    "message": "",
                }
            )

    write_prepared_rows(paths["tables"] / "demand_noise_prepared.csv", rows)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepara ruidos ambientais DEMAND para o benchmark.")
    parser.add_argument("--manifest-only", action="store_true", help="Apenas escreve o manifesto dos arquivos DEMAND 16 kHz.")
    parser.add_argument("--download", action="store_true", help="Baixa os ZIPs selecionados para dados/external/demand.")
    parser.add_argument(
        "--environments",
        nargs="+",
        default=list(DEFAULT_DEMAND_SUBSET),
        help="Codigos DEMAND 16 kHz a preparar. Use --all-environments para todos.",
    )
    parser.add_argument("--all-environments", action="store_true", help="Prepara todos os ambientes 16 kHz listados.")
    parser.add_argument("--channel", type=int, default=1, help="Canal single-channel do DEMAND a extrair.")
    parser.add_argument("--segment-duration", type=float, default=3.0, help="Duracao de cada snippet em segundos.")
    parser.add_argument("--max-segments-per-env", type=int, default=3, help="Numero maximo de snippets por ambiente.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = default_paths(ROOT)
    paths["tables"].mkdir(parents=True, exist_ok=True)

    if args.manifest_only:
        manifest_path = paths["tables"] / "demand_archives_manifest.csv"
        write_demand_manifest(manifest_path, list(DEMAND_16K_ARCHIVES))
        print(f"Manifesto DEMAND escrito em: {manifest_path}")
        return

    environments = [archive.code for archive in DEMAND_16K_ARCHIVES] if args.all_environments else args.environments
    rows = prepare_demand_noise(
        root=ROOT,
        environments=environments,
        channel=args.channel,
        segment_duration_s=args.segment_duration,
        max_segments_per_env=args.max_segments_per_env,
        download=args.download,
    )
    prepared = sum(1 for row in rows if row["status"] == "prepared")
    missing = sum(1 for row in rows if row["status"] == "missing_archive")
    print(f"Snippets DEMAND preparados: {prepared}. Arquivos ausentes: {missing}.")
    print(f"Tabela: {paths['tables'] / 'demand_noise_prepared.csv'}")


if __name__ == "__main__":
    main()
