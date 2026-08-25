#!/usr/bin/env python3
"""Descarga atómica y verificable del snapshot ESFire30 Causes v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DESTINATION = ROOT / "data/raw/esfire30/18449006"
RECORD_ID = 18_449_006
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
EXPECTED = {
    "ESFire30_Causes.zip": {
        "bytes": 93_127_811,
        "sha256": "150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8",
    },
    "read_me.txt": {
        "bytes": 5_444,
        "sha256": "f1de630a5b4eef2723aa7f8d9504e78b6c33bf2900868a0e7526a96da626f94d",
    },
}
GRID_URL = "https://cdn.proj.org/es_ign_SPED2ETV2.tif"
GRID_DESTINATION = ROOT / "data/raw/esfire30/proj-grids/es_ign_SPED2ETV2.tif"
GRID_EXPECTED = {
    "bytes": 180_404,
    "sha256": "61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid(path: Path, expected: dict[str, object]) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == expected["bytes"]
        and sha256(path) == expected["sha256"]
    )


def fetch(
    url: str,
    destination: Path,
    expected: dict[str, object] | None = None,
    attempts: int = 4,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "atlas-incendios-cv4.2/1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} al descargar {url}")
                with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
                    while chunk := response.read(1024 * 1024):
                        temporary.write(chunk)
                    temporary_path = Path(temporary.name)
            if expected is not None and not valid(temporary_path, expected):
                temporary_path.unlink()
                raise RuntimeError(f"Tamaño o SHA-256 inesperado para {destination.name}")
            temporary_path.replace(destination)
            return
        except (OSError, RuntimeError, urllib.error.URLError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"No se pudo descargar {url}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DESTINATION)
    parser.add_argument("--grid-destination", type=Path, default=GRID_DESTINATION)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    metadata_path = args.destination / "zenodo-record.json"
    if args.force or not metadata_path.exists():
        fetch(API_URL, metadata_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("id") != RECORD_ID or metadata.get("doi") != "10.5281/zenodo.18449006":
        raise RuntimeError("El registro Zenodo descargado no es el snapshot esperado")

    available = {item["key"]: item for item in metadata.get("files", [])}
    for filename, expected in EXPECTED.items():
        target = args.destination / filename
        if valid(target, expected) and not args.force:
            print(f"válido, se conserva: {target}")
            continue
        item = available.get(filename)
        if item is None:
            raise RuntimeError(f"Zenodo no publica el fichero esperado {filename}")
        fetch(item["links"]["self"], target, expected)
        if not valid(target, expected):
            raise RuntimeError(f"Tamaño o SHA-256 inesperado para {filename}")
        print(f"descargado y verificado: {target}")

    if valid(args.grid_destination, GRID_EXPECTED) and not args.force:
        print(f"válido, se conserva: {args.grid_destination}")
    else:
        fetch(GRID_URL, args.grid_destination, GRID_EXPECTED)
        print(f"descargado y verificado: {args.grid_destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
