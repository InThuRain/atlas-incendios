#!/usr/bin/env python3
"""Verifica o prepara el bundle Protomaps cerrado de ES-4E3C2.

No descarga ni extrae datos. El PMTiles de 293 MB debe existir previamente;
la adquisición reproducible queda declarada en el manifest contractual.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "config/national-basemap-protomaps-20260902-z12.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def source_checks(payload: dict) -> list[tuple[Path, int, str, str]]:
    checks = [
        (ROOT / payload["pmtiles"]["source_path"], payload["pmtiles"]["bytes"], payload["pmtiles"]["sha256"], "pmtiles"),
    ]
    checks.extend(
        (ROOT / descriptor["source_path"], descriptor["bytes"], descriptor["sha256"], f'glyph:{descriptor["range"]}')
        for descriptor in payload["glyphs"]["files"]
    )
    checks.append((ROOT / payload["glyphs"]["license_source_path"], payload["glyphs"]["license_bytes"], payload["glyphs"]["license_sha256"], "font_license"))
    return checks


def verify_sources(payload: dict) -> dict:
    failures = []
    files = []
    for path, expected_bytes, expected_sha, role in source_checks(payload):
        if not path.is_file():
            failures.append(f"missing:{role}:{path.relative_to(ROOT)}")
            continue
        actual_bytes = path.stat().st_size
        actual_sha = sha256(path)
        files.append({"role": role, "path": str(path.relative_to(ROOT)), "bytes": actual_bytes, "sha256": actual_sha})
        if actual_bytes != expected_bytes or actual_sha != expected_sha:
            failures.append(f"identity:{role}")
    return {"valid": not failures, "failures": failures, "files": files}


def prepare(output: Path, payload: dict) -> dict:
    checked = verify_sources(payload)
    if not checked["valid"]:
        return checked
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="national-basemap-", dir=str(output.parent)) as temporary:
        staging = Path(temporary) / "bundle"
        for source, _, _, role in source_checks(payload):
            if role == "pmtiles":
                destination = staging / Path(payload["pmtiles"]["runtime_path"]).name
            elif role.startswith("glyph:"):
                destination = staging / "fonts" / payload["glyphs"]["fontstack"] / f'{role.split(":", 1)[1]}.pbf'
            else:
                destination = staging / "fonts" / "OFL.txt"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        shutil.copy2(CONTRACT_PATH, staging / "manifest.json")
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(staging), str(output))
    return {"valid": True, "output": str(output), "files": checked["files"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verifica los inputs locales sin copiar ni descargar.")
    parser.add_argument("--output", type=Path, help="Copia un bundle autocontenido al directorio indicado.")
    args = parser.parse_args()
    payload = contract()
    result = prepare(args.output, payload) if args.output else verify_sources(payload)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
