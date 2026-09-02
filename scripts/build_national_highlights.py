#!/usr/bin/env python3
"""Construye el pequeño índice anual de destacados EGIF nacionales.

El runtime de España no carga INITIAL. Este derivado conserva únicamente los
diez registros con mayor superficie forestal declarada conocida de cada año,
con una segunda lista para el filtro GIF. No lee DETAIL, no crea geometrías y
no relaciona EGIF con ninguna otra fuente.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/web/spain/egif/2026-08-27/manifest.json"
TERRITORIES = ROOT / "data/territories/spain/territories-2026-01-01.json"
DEFAULT_OUTPUT = ROOT / "data/derived/spain/national-highlights-v1"
SCHEMA_VERSION = "national-highlights-v1"
LIMIT = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def ranked(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: (-row["reported_forest_area_ha"], row["record_id"]))[:LIMIT]


def build(output: Path) -> dict:
    manifest = json.loads(SOURCE.read_text(encoding="utf-8"))
    territory_catalog = json.loads(TERRITORIES.read_text(encoding="utf-8"))
    territory_names = {row["territory_id"]: row["official_name"] for row in territory_catalog["territories"]}
    if manifest.get("totals", {}).get("records") != 646887 or len(manifest.get("assets", [])) != 88:
        raise RuntimeError("Manifest EGIF nacional inesperado")
    annual: dict[int, dict[str, list[dict]]] = {}
    known = 0
    scanned = 0
    for asset in sorted(manifest["assets"], key=lambda row: row["asset_id"]):
        initial_path = SOURCE.parent / asset["initial"]["path"]
        if sha256(initial_path) != asset["initial"]["sha256"]:
            raise RuntimeError(f"Checksum INITIAL inesperado: {asset['asset_id']}")
        payload = json.loads(initial_path.read_text(encoding="utf-8"))
        columns = payload["columns"]
        for ordinal, record_id in enumerate(columns["record_id"]):
            scanned += 1
            area = columns["reported_forest_area_ha"][ordinal]
            if not isinstance(area, (int, float)) or isinstance(area, bool):
                continue
            known += 1
            year = int(columns["year"][ordinal])
            row = {
                "record_id": record_id,
                "asset_id": asset["asset_id"],
                "year": year,
                "autonomous_community_id": columns["autonomous_community_id"][ordinal],
                "province_id": columns["province_id"][ordinal],
                "municipality_id": columns["municipality_id"][ordinal],
                "province_name": territory_names.get(columns["province_id"][ordinal]),
                "municipality_name": territory_names.get(columns["municipality_id"][ordinal]),
                "reported_forest_area_ha": area,
                "is_gif_forest_ge_500_ha": columns["is_gif_forest_ge_500_ha"][ordinal],
            }
            slot = annual.setdefault(year, {"all": [], "gif_true": []})
            slot["all"] = ranked([*slot["all"], row])
            if row["is_gif_forest_ge_500_ha"] is True:
                slot["gif_true"] = ranked([*slot["gif_true"], row])

    if scanned != 646887 or set(annual) != set(range(1968, 2024)):
        raise RuntimeError(f"Recuento/eje EGIF inesperado: {scanned}, {min(annual)}-{max(annual)}")
    data = {
        "schema_version": SCHEMA_VERSION,
        "source_id": "egif",
        "entity_type": "administrative_source_record",
        "metric_id": "egif_declared_forest_area_ha",
        "ordering": "reported_forest_area_ha_desc_record_id_asc",
        "unit": "ha",
        "null_policy": "excluded_not_zero",
        "limit_per_year": LIMIT,
        "years": {str(year): annual[year] for year in sorted(annual)},
    }
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="national-highlights-", dir=output.parent) as directory:
        temporary = Path(directory) / "egif.json"
        temporary.write_bytes(canonical_bytes(data))
        target = output / "egif.json"
        temporary.replace(target)
    manifest_output = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": "2026-09-02",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": sha256(SOURCE),
            "records_scanned": scanned,
            "records_with_known_forest_area": known,
        },
        "territory_catalog": {"path": str(TERRITORIES.relative_to(ROOT)), "sha256": sha256(TERRITORIES)},
        "assets": [{
            "source_id": "egif",
            "path": "egif.json",
            "bytes": target.stat().st_size,
            "gzip_bytes": len(gzip.compress(target.read_bytes(), mtime=0)),
            "sha256": sha256(target),
        }],
        "contracts": {
            "ranking": "one source + one documented metric",
            "metric_id": "egif_declared_forest_area_ha",
            "null_policy": "excluded_not_zero",
            "detail": "lazy_on_explicit_selection",
            "geometry": "none",
        },
    }
    (output / "manifest.json").write_bytes(canonical_bytes(manifest_output))
    return {"valid": True, "records_scanned": scanned, "known_area": known, "years": len(annual), "output": str(output.relative_to(ROOT))}


def check(output: Path) -> dict:
    failures: list[str] = []
    try:
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        data = json.loads((output / "egif.json").read_text(encoding="utf-8"))
        asset = manifest["assets"][0]
        if manifest.get("schema_version") != SCHEMA_VERSION or data.get("schema_version") != SCHEMA_VERSION:
            failures.append("schema")
        if sha256(output / asset["path"]) != asset["sha256"] or (output / asset["path"]).stat().st_size != asset["bytes"]:
            failures.append("asset integrity")
        if set(data.get("years", {})) != {str(year) for year in range(1968, 2024)}:
            failures.append("year axis")
        seen = set()
        for year, groups in data.get("years", {}).items():
            for group, rows in groups.items():
                if len(rows) > LIMIT or rows != ranked(rows):
                    failures.append(f"ranking:{year}:{group}")
                for row in rows:
                    if row["reported_forest_area_ha"] is None or row["year"] != int(year):
                        failures.append(f"row:{year}:{group}")
                    if group == "gif_true" and row["is_gif_forest_ge_500_ha"] is not True:
                        failures.append(f"gif:{year}")
                    seen.add(row["record_id"])
        if not seen:
            failures.append("empty")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        failures.append(str(error))
    return {"valid": not failures, "failures": sorted(set(failures)), "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check(args.output) if args.check else build(args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
