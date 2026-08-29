#!/usr/bin/env python3
"""Serializa para el prototipo el índice inverso municipal ya auditado.

No calcula intersecciones ni abre geometrías. Lee las relaciones positive-area
de ES-4C2B3A1, cuyo inventario, cardinalidad y semántica quedaron cerrados en
ES-4C2B3A2, y las entrega como ``municipality_id -> geometry_id[]``.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RELATION_DIR = ROOT / "data/derived/spain/es4c2b/esfire30_municipality_relations"
RELATION_MANIFEST = RELATION_DIR / "manifest.json"
AUDIT = ROOT / "data/audit/esfire30/es4c2b3a2_municipal_relations.json"
CATALOG = ROOT / "data/territories/spain/municipality_catalog_2026-08-29.json"
DEFAULT_OUTPUT = ROOT / "data/derived/spain/es4c2b/runtime/municipality-index"
EXPECTED_GEOMETRIES, EXPECTED_RELATIONS, EXPECTED_MUNICIPALITIES = 119_498, 143_477, 8_132
SCHEMA_VERSION = "es4c2b3b1-municipality-runtime-index-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def gzip_bytes(value: bytes) -> int:
    return len(gzip.compress(value, compresslevel=9, mtime=0))


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(value)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def read_jsonl(path: Path, expected_sha256: str):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for line in source:
            digest.update(line)
            if line.strip():
                yield json.loads(line)
    if digest.hexdigest() != expected_sha256:
        raise ValueError(f"Checksum relation input inesperado: {portable(path)}")


def load_catalog() -> dict[str, dict[str, Any]]:
    rows = json.loads(CATALOG.read_text(encoding="utf-8"))["municipalities"]
    catalog = {row["municipality_id"]: row for row in rows}
    if len(catalog) != EXPECTED_MUNICIPALITIES:
        raise ValueError("Catálogo municipal inesperado")
    return catalog


def load_inverse() -> tuple[dict[str, list[str]], int, int]:
    manifest = json.loads(RELATION_MANIFEST.read_text(encoding="utf-8"))
    inverse: dict[str, set[str]] = defaultdict(set)
    geometry_ids: set[str] = set()
    relation_count = 0
    for block in sorted(manifest["blocks"], key=lambda item: item["year"]):
        path = ROOT / block["relations_path"]
        for relation in read_jsonl(path, block["relations_sha256"]):
            if relation.get("intersection_class") != "positive_area_intersection":
                raise ValueError("Relación municipal no positiva")
            municipality_id, geometry_id = relation["municipality_id"], relation["geometry_id"]
            before = len(inverse[municipality_id])
            inverse[municipality_id].add(geometry_id)
            if len(inverse[municipality_id]) == before:
                raise ValueError(f"Duplicado municipal: {municipality_id}/{geometry_id}")
            geometry_ids.add(geometry_id)
            relation_count += 1
    # Las 83 geometrías sin relación municipal positiva no aparecen en los
    # JSONL de relaciones. La cobertura total procede del manifest C2B3A1,
    # no de inventar entradas municipales vacías para esas geometrías.
    manifest_geometry_count = manifest.get("totals", {}).get("geometry_count")
    if relation_count != EXPECTED_RELATIONS or manifest_geometry_count != EXPECTED_GEOMETRIES:
        raise ValueError("Reconciliación de relaciones municipales inesperada")
    return {key: sorted(value) for key, value in sorted(inverse.items())}, relation_count, manifest_geometry_count


def payload(scope: str, municipalities: dict[str, list[str]], parent_id: str | None = None) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "scope": scope, "parent_id": parent_id, "municipalities": municipalities}


def artifact(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    raw = canonical_bytes(value)
    atomic_bytes(path, raw)
    return {"path": portable(path), "sha256": sha256(path), "raw_bytes": len(raw), "gzip_bytes": gzip_bytes(raw), "municipality_entries": len(value["municipalities"]), "geometry_references": sum(len(ids) for ids in value["municipalities"].values())}


def build(output: Path = DEFAULT_OUTPUT, resume: bool = False) -> dict[str, Any]:
    catalog = load_catalog()
    inverse, relation_count, geometry_count = load_inverse()
    if set(inverse) - set(catalog):
        raise ValueError("Índice con municipio fuera del catálogo")
    national_value = payload("national", inverse)
    national_path = output / "municipality-geometry-ids-national.json"
    # `--resume` es idempotente: únicamente conserva el asset si sus bytes
    # deterministas ya coinciden con los que se producirían ahora.
    raw = canonical_bytes(national_value)
    if not (resume and national_path.is_file() and national_path.read_bytes() == raw):
        atomic_bytes(national_path, raw)
    national = artifact(national_path, national_value)
    parents: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for municipality_id, geometry_ids in inverse.items():
        row = catalog[municipality_id]
        parent_id = row["province_id"] or row["autonomous_community_id"]
        parents[parent_id][municipality_id] = geometry_ids
    shards = []
    for parent_id, municipalities in sorted(parents.items()):
        value = payload("parent", dict(sorted(municipalities.items())), parent_id)
        path = output / "by-parent" / f"{parent_id.replace(':', '-')}.json"
        raw = canonical_bytes(value)
        if not (resume and path.is_file() and path.read_bytes() == raw):
            atomic_bytes(path, raw)
        shards.append({"parent_id": parent_id, **artifact(path, value)})
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "semantics": "municipality_id maps to ESFire30 geometry_ids whose canonical geometry has positive-area intersection with the current BDLJE municipal boundary; it is not EGIF municipality, historical municipality, ignition or primary territory",
        "inputs": {
            "municipal_relation_manifest": portable(RELATION_MANIFEST),
            "municipal_relation_manifest_sha256": sha256(RELATION_MANIFEST),
            "audit": portable(AUDIT),
            "audit_sha256": sha256(AUDIT),
            "municipality_catalog": portable(CATALOG),
            "municipality_catalog_sha256": sha256(CATALOG),
        },
        "reconciliation": {
            "geometry_ids": geometry_count,
            "positive_area_relations": relation_count,
            "municipalities_total": EXPECTED_MUNICIPALITIES,
            "municipalities_with_geometry_ids": len(inverse),
            "municipalities_with_zero_geometry_ids": EXPECTED_MUNICIPALITIES - len(inverse),
            "max_geometry_ids_per_municipality": max(map(len, inverse.values())),
            "audit_zero_geometry_relations": audit["reconciliation"]["municipality_unresolved_geometry_count"],
        },
        "national": national,
        "by_parent": shards,
        "by_parent_totals": {"asset_count": len(shards), "raw_bytes": sum(item["raw_bytes"] for item in shards), "gzip_bytes": sum(item["gzip_bytes"] for item in shards)},
    }
    manifest_path = output / "manifest.json"
    atomic_bytes(manifest_path, canonical_bytes(manifest))
    return {"valid": True, "output": portable(manifest_path), "national": national, "shards": len(shards), **manifest["reconciliation"]}


def check(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    manifest_path = output / "manifest.json"
    if not manifest_path.is_file():
        return {"valid": False, "failures": [f"No existe {portable(manifest_path)}"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")); failures = []
    if manifest.get("schema_version") != SCHEMA_VERSION: failures.append("schema_version")
    reconciliation = manifest.get("reconciliation", {})
    if reconciliation.get("geometry_ids") != EXPECTED_GEOMETRIES: failures.append("geometry_ids")
    if reconciliation.get("positive_area_relations") != EXPECTED_RELATIONS: failures.append("positive_area_relations")
    for artifact_row in [manifest.get("national", {})] + manifest.get("by_parent", []):
        path = ROOT / artifact_row.get("path", "")
        if not path.is_file() or sha256(path) != artifact_row.get("sha256"):
            failures.append(f"checksum:{artifact_row.get('path')}")
    return {"valid": not failures, "failures": failures, "output": portable(manifest_path), **reconciliation}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check(args.output) if args.check else build(args.output, args.resume)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__": raise SystemExit(main())
