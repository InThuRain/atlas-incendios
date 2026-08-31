#!/usr/bin/env python3
"""Construye un artifact Pages aislado para ES-4C3D4.

Parte del site público ya montado, pero sólo añade un harness experimental
same-origin y el PMTiles comprobado. No publica, no modifica Pages y no añade
el binario a Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BYTES = 63052056
EXPECTED_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"
HARNESS = ROOT / "benchmarks/es4c3d4/harness"
FIXTURES = ROOT / "benchmarks/es4c3d4/fixtures/municipality-index"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-site", type=Path, required=True)
    parser.add_argument("--pmtiles", type=Path, required=True)
    parser.add_argument("--vendor-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    public_site, pmtiles, vendor, output = args.public_site.resolve(), args.pmtiles.resolve(), args.vendor_dir.resolve(), args.output.resolve()
    if not public_site.is_dir():
        raise SystemExit("No existe el artifact público de partida")
    if not pmtiles.is_file() or pmtiles.stat().st_size != EXPECTED_BYTES or sha256(pmtiles) != EXPECTED_SHA256:
        raise SystemExit("PMTiles rechazado por tamaño o SHA-256")
    required = [HARNESS / "index.html", HARNESS / "app.js", vendor / "maplibre-gl-5.16.0.js", vendor / "pmtiles-4.3.0.js"]
    required += [FIXTURES / f"ES-PROV-{code}.json" for code in ("03", "33")]
    if any(not path.is_file() for path in required):
        raise SystemExit("Faltan assets locales del harness C3D4")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(output.parent), prefix="es4c3d4-pages-") as temp:
        staged = Path(temp) / "site"
        shutil.copytree(public_site, staged)
        harness = staged / "es4c3d4"
        shutil.copytree(HARNESS, harness)
        copy(vendor / "maplibre-gl-5.16.0.js", harness / "vendor/maplibre-gl-5.16.0.js")
        copy(vendor / "pmtiles-4.3.0.js", harness / "vendor/pmtiles-4.3.0.js")
        for code in ("03", "33"):
            copy(FIXTURES / f"ES-PROV-{code}.json", harness / f"municipality-index/ES-PROV-{code}.json")
        pmtiles_target = staged / "data/esfire30-national-fidelity-territories.pmtiles"
        copy(pmtiles, pmtiles_target)
        files = [path for path in staged.rglob("*") if path.is_file()]
        manifest = {
            "schema_version": "es4c3d4-pages-staging-v1",
            "public_site_bytes": sum(path.stat().st_size for path in public_site.rglob("*") if path.is_file()),
            "pmtiles": {"path": "data/esfire30-national-fidelity-territories.pmtiles", "bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256},
            "harness": "es4c3d4/index.html",
            "bytes_before_manifest": sum(path.stat().st_size for path in files),
        }
        (staged / "es4c3d4-staging-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        previous = output.with_name(output.name + ".previous")
        if previous.exists(): shutil.rmtree(previous)
        if output.exists(): os.replace(output, previous)
        os.replace(staged, output)
        if previous.exists(): shutil.rmtree(previous)
    print(json.dumps({"output": str(output), "bytes": sum(path.stat().st_size for path in output.rglob("*") if path.is_file())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
