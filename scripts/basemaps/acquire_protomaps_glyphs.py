#!/usr/bin/env python3
"""Adquisición explícita y verificable de glyphs Protomaps E3D1.

Sin ``--download`` solo comprueba los inputs locales. El assembler y los tests
rutinarios nunca invocan la red.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "config/national-basemap-protomaps-20260902-z12.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift <= 63:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
    raise ValueError("varint PBF inválido")


def fields(data: bytes) -> list[tuple[int, int, bytes | int]]:
    result = []
    offset = 0
    while offset < len(data):
        tag, offset = read_varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ValueError("campo PBF cero")
        if wire == 0:
            value, offset = read_varint(data, offset)
        elif wire == 1:
            if offset + 8 > len(data): raise ValueError("fixed64 truncado")
            value = data[offset:offset + 8]; offset += 8
        elif wire == 2:
            size, offset = read_varint(data, offset)
            if offset + size > len(data): raise ValueError("bytes PBF truncados")
            value = data[offset:offset + size]; offset += size
        elif wire == 5:
            if offset + 4 > len(data): raise ValueError("fixed32 truncado")
            value = data[offset:offset + 4]; offset += 4
        else:
            raise ValueError(f"wire type PBF no soportado: {wire}")
        result.append((number, wire, value))
    return result


def validate_glyph_pbf(data: bytes, expected_range: str) -> dict:
    if data.lstrip().lower().startswith((b"<!doctype", b"<html")):
        raise ValueError("la respuesta es HTML, no glyph PBF")
    top = fields(data)
    stacks = [value for number, wire, value in top if number == 1 and wire == 2 and isinstance(value, bytes)]
    if not stacks or len(stacks) != len(top):
        raise ValueError("estructura glyph PBF inesperada")
    names = []
    ranges = []
    glyph_count = 0
    for stack in stacks:
        inner = fields(stack)
        names.extend(value.decode("utf-8") for number, wire, value in inner if number == 1 and wire == 2 and isinstance(value, bytes))
        ranges.extend(value.decode("utf-8") for number, wire, value in inner if number == 2 and wire == 2 and isinstance(value, bytes))
        glyph_count += sum(1 for number, wire, _value in inner if number == 3 and wire == 2)
    if expected_range not in ranges or glyph_count < 1:
        raise ValueError(f"glyph PBF no declara {expected_range} o está vacío")
    return {"font_names": sorted(set(names)), "declared_ranges": sorted(set(ranges)), "glyph_count": glyph_count}


def acquire(download: bool, timeout: int) -> dict:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    glyphs = contract["glyphs"]
    rows = []
    failures = []
    for descriptor in glyphs["files"]:
        range_name = descriptor["range"]
        path = ROOT / descriptor["source_path"]
        if not path.is_file() and download:
            url = glyphs["source_url_template"].replace("{range}", range_name)
            request = Request(url, headers={"User-Agent": "atlas-incendios-es4e3d1-glyph-fix"})
            with urlopen(request, timeout=timeout) as response:
                data = response.read()
            validate_glyph_pbf(data, range_name)
            if len(data) != descriptor["bytes"] or sha256_bytes(data) != descriptor["sha256"]:
                failures.append(f"remote identity:{range_name}")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{range_name}-", delete=False) as temporary:
                temporary.write(data)
                temporary_path = Path(temporary.name)
            temporary_path.replace(path)
        if not path.is_file():
            failures.append(f"missing:{range_name}")
            continue
        data = path.read_bytes()
        try:
            structure = validate_glyph_pbf(data, range_name)
        except ValueError as error:
            failures.append(f"invalid PBF:{range_name}:{error}")
            continue
        row = {
            "range": range_name,
            "path": descriptor["source_path"],
            "source": glyphs["source_url_template"].replace("{range}", range_name),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "pbf": structure,
        }
        rows.append(row)
        if row["bytes"] != descriptor["bytes"] or row["sha256"] != descriptor["sha256"]:
            failures.append(f"local identity:{range_name}")
    license_path = ROOT / glyphs["license_source_path"]
    if not license_path.is_file() or license_path.stat().st_size != glyphs["license_bytes"] or sha256_bytes(license_path.read_bytes()) != glyphs["license_sha256"]:
        failures.append("OFL identity")
    return {
        "valid": not failures,
        "failures": failures,
        "fontstack": glyphs["fontstack"],
        "source_repository": glyphs["source_repository"],
        "source_commit": glyphs["source_commit"],
        "license": "SIL OFL 1.1",
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "files": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Descarga explícitamente solo ficheros ausentes y verifica bytes/SHA/PBF.")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = acquire(args.download, args.timeout)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
