#!/usr/bin/env python3
"""Empaqueta de forma determinista el artifact D4A para transporte a Pages.

No reconstruye ni modifica el artifact. El paquete es solo un contenedor de
transferencia para un release temporal del repositorio de staging; el workflow
remoto revalida el manifest de contenido antes de desplegarlo.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import tarfile
from pathlib import Path

import build_national_pages_artifact as artifact


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "build/national-pages-staging"
DEFAULT_OUTPUT = ROOT / "build/national-pages-staging-d4a.tar.gz"
EXPECTED = {
    "file_count": 349,
    "total_bytes": 500449810,
    "fingerprint": "bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_contract(root: Path) -> dict:
    checked = artifact.check(root)
    if not checked.get("valid"):
        raise RuntimeError("ARTIFACT_IDENTITY_MISMATCH: " + ", ".join(checked["failures"]))
    manifest = json.loads((root / "asset-manifest.json").read_text(encoding="utf-8"))
    actual = {
        "file_count": manifest.get("file_count"),
        "total_bytes": manifest.get("total_bytes"),
        "fingerprint": manifest.get("fingerprint", {}).get("sha256"),
    }
    if actual != EXPECTED:
        raise RuntimeError(f"ARTIFACT_IDENTITY_MISMATCH: expected={EXPECTED} actual={actual}")
    return manifest


def package(root: Path, output: Path) -> dict:
    manifest = verify_contract(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as compressed:
            with tarfile.open(mode="w", fileobj=compressed, format=tarfile.USTAR_FORMAT) as archive:
                for path in sorted(item for item in root.rglob("*") if item.is_file()):
                    relative = path.relative_to(root).as_posix()
                    info = archive.gettarinfo(str(path), arcname=relative)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as source:
                        archive.addfile(info, source)
    return {
        "valid": True,
        "artifact": artifact.label(root),
        "output": artifact.label(output),
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "artifact_fingerprint": manifest["fingerprint"]["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = package(args.artifact, args.output)
    except RuntimeError as error:
        result = {"valid": False, "failure": str(error)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
