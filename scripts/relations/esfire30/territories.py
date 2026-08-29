#!/usr/bin/env python3
"""Deriva relaciones ESFire30 geometry → territorio ES-2 de forma reanudable.

Las filas positivas significan exclusivamente que una geometría canónica de
ESFire30 intersecta con área positiva un límite administrativo BDLJE. No
asignan un incendio a un territorio ni enlazan con EGIF. Los contactos de
frontera de área cero se auditan aparte y nunca se emiten como relaciones.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
ZIP = ROOT / "data/raw/esfire30/18449006/ESFire30_Causes.zip"
GRID = ROOT / "data/raw/esfire30/proj-grids/es_ign_SPED2ETV2.tif"
CCAA = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/autonomous-territories.geojson"
PROVINCES = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/province-level.geojson"
SNAPSHOT = ROOT / "data/territories/spain/territories-2026-01-01.json"
CCAA_MANIFEST = ROOT / "data/sources/spain_ccaa_territories_manifest.json"
PROVINCE_MANIFEST = ROOT / "data/sources/spain_province_territories_manifest.json"
OUTPUT = ROOT / "data/derived/spain/es4c2b/esfire30_territory_relations"
ES3_CORE_RESULTS = ROOT / "data/derived/spain/es3/results.json"
ZIP_SHA256 = "150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8"
GRID_SHA256 = "61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961"
CCAA_SHA256 = "48d1cd7b1cc2a3a98f6d02a0043fddc8db43ba28aaa8789d6b030243417bf757"
PROVINCE_SHA256 = "58e4f68f4efc324dd9dfd0c1df0ea755846e3b717676b7137456577dc2083290"
YEARS = tuple(range(1985, 2022))
EXPECTED_GEOMETRIES = 119_498
PIPELINE_VERSION = "es-4c2b1a-esfire30-territory-relations-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def load_es3() -> Any:
    path = ROOT / "scripts/audit/spain/es3_esfire30_delivery.py"
    spec = importlib.util.spec_from_file_location("es3_for_es4c2b", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar la metodología ES-3")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_contract_territories() -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, str]]:
    payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    territories = {row["territory_id"]: row for row in payload["territories"]}
    ccaa = {row["official_code"]: row["territory_id"] for row in territories.values() if row["territory_type"] in {"autonomous_community", "autonomous_city"}}
    provinces = {row["official_code"]: row["territory_id"] for row in territories.values() if row["territory_type"] == "province"}
    if len(ccaa) != 19 or len(provinces) != 50:
        raise ValueError("Snapshot ES-2 territorial inesperado")
    return territories, ccaa, provinces


def verify_inputs() -> dict[str, str]:
    expected = ((ZIP, ZIP_SHA256), (GRID, GRID_SHA256), (CCAA, CCAA_SHA256), (PROVINCES, PROVINCE_SHA256))
    actual = {}
    for path, checksum in expected:
        if not path.is_file() or sha256(path) != checksum:
            raise ValueError(f"Checksum inesperado o fichero ausente: {portable(path)}")
        actual[portable(path)] = checksum
    # Los manifests C2A verifican que estas son exactamente las capas BDLJE
    # utilizadas para los derivados administrativos del prototipo.
    for path, checksum in ((CCAA_MANIFEST, CCAA_SHA256), (PROVINCE_MANIFEST, PROVINCE_SHA256)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["source"]["raw_sha256"] != checksum:
            raise ValueError(f"Manifest territorial incoherente: {portable(path)}")
    return actual


def territory_units() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Carga BDLJE canónico en EPSG:3035 y cruza códigos con ES-2."""
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform

    territories, ccaa_ids, province_ids = load_contract_territories()
    transform_to_area = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform

    def read(path: Path, level: str) -> list[dict[str, Any]]:
        collection = json.loads(path.read_text(encoding="utf-8")); units = []
        for feature in collection.get("features", []):
            props = feature.get("properties") or {}; nationalcode = str(props.get("nationalcode") or "")
            if props.get("nationallevelname") != level or len(nationalcode) != 11 or not nationalcode.startswith("34"):
                raise ValueError(f"Feature BDLJE inválida en {portable(path)}")
            if nationalcode in {"34200000000", "34205400000"}:
                continue
            ccaa_code, province_code = nationalcode[2:4], nationalcode[4:6]
            if level == "Comunidad autónoma":
                territory_id = ccaa_ids.get(ccaa_code)
                territory_type = territories.get(territory_id or "", {}).get("territory_type")
            else:
                # 51/52 son representaciones fuente de ciudades autónomas, no
                # provincias ES-2: ESFire30 no cubre esas ciudades y no se
                # introducen relaciones territoriales nuevas para ellas.
                territory_id = province_ids.get(province_code)
                territory_type = "province" if territory_id else None
            if not territory_id:
                continue
            geom = transform(transform_to_area, shape(feature.get("geometry")))
            if geom.is_empty or not geom.is_valid:
                raise ValueError(f"Geometría BDLJE inválida: {nationalcode}")
            units.append({"territory_id": territory_id, "territory_type": territory_type, "parent_id": territories[territory_id].get("parent_id"), "geometry": geom})
        return units

    ccaa, provinces = read(CCAA, "Comunidad autónoma"), read(PROVINCES, "Provincia")
    if len(ccaa) != 19 or len(provinces) != 50:
        raise ValueError(f"Crosswalk BDLJE/ES-2 inesperado: CCAA={len(ccaa)}, provincias={len(provinces)}")
    return ccaa, provinces, territories


def source_transformer() -> tuple[Any, dict[str, Any]]:
    """Reutiliza la operación ED50→WGS84 con grid oficial establecida en ES-3."""
    from pyproj import Transformer
    from shapely.ops import transform

    es3 = load_es3(); forward, _, versions = es3.selected_transformer()
    to_area = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
    def transform_geometry(geometry: Any) -> Any:
        geographic = transform(forward.transform, geometry)
        return transform(to_area.transform, geographic)
    return transform_geometry, {"source_crs": "EPSG:23030", "intermediate_crs": "EPSG:4326", "area_crs": "EPSG:3035", "ed50_to_wgs84_operation": forward.description, "ed50_to_wgs84_accuracy_m": forward.accuracy, "software": versions}


def geometry_id(year: int, ordinal: int) -> str:
    return f"esfire30:v1:{year}:{ordinal}"


def relation_id(geometry_id_value: str, territory_id: str) -> str:
    token = hashlib.sha256(f"{geometry_id_value}|{territory_id}|spatial_intersection".encode("utf-8")).hexdigest()[:24]
    return f"territory-relation:esfire30:{token}"


def geometry_ids_checksum(year: int, ordinals: Iterable[int]) -> str:
    """Huella determinista de la selección de geometrías de un bloque."""
    digest = hashlib.sha256()
    for ordinal in sorted(ordinals):
        digest.update(f"{geometry_id(year, ordinal)}\n".encode("utf-8"))
    return digest.hexdigest()


def relation_rows(geometry_id_value: str, geometry: Any, trees: dict[str, tuple[Any, list[dict[str, Any]]]], *, year: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Emite solo solapes de área positiva; conserva contactos como auditoría."""
    if geometry.is_empty or not geometry.is_valid or geometry.area <= 0:
        raise ValueError(f"Geometría ESFire30 inválida: {geometry_id_value}")
    positives, touches = [], []
    source_area = geometry.area
    for level, (tree, units) in trees.items():
        for raw_index in tree.query(geometry, predicate="intersects"):
            unit = units[int(raw_index)]
            overlap = geometry.intersection(unit["geometry"])
            area = overlap.area
            common = {
                "geometry_id": geometry_id_value, "subject_id": geometry_id_value,
                "territory_id": unit["territory_id"], "territory_type": unit["territory_type"],
                "territory_level": level, "relation_type": "spatial_intersection",
                "intersection_area_m2": round(area, 3), "intersection_fraction": round(area / source_area, 12),
            }
            if area > 0:
                positives.append({
                    "territory_relation_id": relation_id(geometry_id_value, unit["territory_id"]),
                    **common, "mapping_status": "confirmed", "qa_status": "not_checkable",
                    "intersection_class": "positive_area_intersection",
                    # La procedencia detallada (URLs, operaciones y checksums)
                    # vive una sola vez en el manifest. Repetirla en cada fila
                    # multiplicaría innecesariamente un output N:M nacional.
                    "provenance": {"source_id": "esfire30", "source_record_id": geometry_id_value, "retrieved_at": "2026-08-26T00:00:00Z", "snapshot_id": "zenodo-18449006-v1", "transformations": [PIPELINE_VERSION]},
                })
            else:
                # Esta fila es evidencia diagnóstica, no territory_relation.
                touches.append({**common, "intersection_class": "boundary_touch_only"})
    keys = [(row["geometry_id"], row["territory_id"], row["relation_type"]) for row in positives]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Relación ESFire30 duplicada: {geometry_id_value}")
    positive_ccaa = {row["territory_id"] for row in positives if row["territory_level"] == "autonomous_community"}
    for row in positives:
        if row["territory_level"] != "province": continue
        # El parent está evaluado después en build; se completa al emitir.
        row["_positive_ccaa"] = positive_ccaa
    return positives, touches


def paths(output: Path, year: int) -> tuple[Path, Path]:
    return output / f"relations-{year}.jsonl", output / f"boundary-touches-{year}.jsonl"


def write_year(output: Path, year: int, rows: Iterable[tuple[int, Any]], trees: dict[str, tuple[Any, list[dict[str, Any]]]], territories: dict[str, dict[str, Any]], transform_geometry: Any) -> dict[str, Any]:
    relation_path, touch_path = paths(output, year)
    relation_path.parent.mkdir(parents=True, exist_ok=True)
    relation_fd, relation_tmp = tempfile.mkstemp(prefix=f".{relation_path.name}.", suffix=".part", dir=output)
    touch_fd, touch_tmp = tempfile.mkstemp(prefix=f".{touch_path.name}.", suffix=".part", dir=output)
    relation_digest, touch_digest, geometry_digest = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    counts = Counter(); geometry_count = 0; multi_ccaa = multi_province = zero_relation = hierarchy_inconsistencies = 0
    try:
        with os.fdopen(relation_fd, "wb") as relation_handle, os.fdopen(touch_fd, "wb") as touch_handle:
            for ordinal, raw_geometry in rows:
                geometry_count += 1; gid = geometry_id(year, ordinal)
                geometry_digest.update(f"{gid}\n".encode("utf-8"))
                geometry = transform_geometry(raw_geometry)
                positives, touches = relation_rows(gid, geometry, trees, year=year)
                ccaa = {row["territory_id"] for row in positives if row["territory_level"] == "autonomous_community"}
                provinces = {row["territory_id"] for row in positives if row["territory_level"] == "province"}
                multi_ccaa += int(len(ccaa) > 1); multi_province += int(len(provinces) > 1); zero_relation += int(not positives)
                for relation in positives:
                    if relation["territory_level"] == "province":
                        parent = territories[relation["territory_id"]]["parent_id"]
                        relation["hierarchy_parent_present"] = parent in ccaa
                        hierarchy_inconsistencies += int(parent not in ccaa)
                    relation.pop("_positive_ccaa", None)
                    line = (json.dumps(relation, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                    relation_handle.write(line); relation_digest.update(line); counts["positive_relations"] += 1
                for touch in touches:
                    line = (json.dumps(touch, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                    touch_handle.write(line); touch_digest.update(line); counts["boundary_touches"] += 1
            relation_handle.flush(); os.fsync(relation_handle.fileno()); touch_handle.flush(); os.fsync(touch_handle.fileno())
        os.replace(relation_tmp, relation_path); os.replace(touch_tmp, touch_path)
    except BaseException:
        for temporary in (relation_tmp, touch_tmp):
            try: os.unlink(temporary)
            except FileNotFoundError: pass
        raise
    return {"year": year, "status": "complete", "geometry_count": geometry_count, "geometry_ids_sha256": geometry_digest.hexdigest(), "relation_count": counts["positive_relations"], "boundary_touch_count": counts["boundary_touches"], "multi_ccaa_count": multi_ccaa, "multi_province_count": multi_province, "zero_relation_count": zero_relation, "hierarchy_inconsistency_count": hierarchy_inconsistencies, "relations_path": portable(relation_path), "boundary_touches_path": portable(touch_path), "relations_sha256": relation_digest.hexdigest(), "boundary_touches_sha256": touch_digest.hexdigest(), "bytes": relation_path.stat().st_size + touch_path.stat().st_size}


def verify_block(entry: dict[str, Any]) -> tuple[bool, str]:
    for path_key, checksum_key, expected_class, count_key in (("relations_path", "relations_sha256", "positive_area_intersection", "relation_count"), ("boundary_touches_path", "boundary_touches_sha256", "boundary_touch_only", "boundary_touch_count")):
        path = ROOT / entry[path_key]
        if not path.is_file() or sha256(path) != entry[checksum_key]: return False, f"{path.name}: checksum"
        seen = set()
        line_count = 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line_count += 1
                row = json.loads(line)
                if row.get("intersection_class") != expected_class: return False, f"{path.name}: clase"
                if expected_class == "positive_area_intersection":
                    key = (row.get("geometry_id"), row.get("territory_id"), row.get("relation_type"))
                    if key in seen or row.get("intersection_area_m2", 0) <= 0: return False, f"{path.name}: duplicado/área"
                    seen.add(key)
        if line_count != entry.get(count_key): return False, f"{path.name}: recuento"
    return True, "ok"


def manifest_base(input_checksums: dict[str, str], transform_info: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "relation_contract": "schemas/national/v1/atlas-contracts.schema.json#/territoryRelation", "semantics": "geometry ESFire30 intersects administrative territory; not source-declared origin, fire identity or EGIF link", "input": {"geometry_snapshot": {"doi": "10.5281/zenodo.18449006", "zip": portable(ZIP), "records_expected": EXPECTED_GEOMETRIES, "geometry_id": "esfire30:v1:<year>:<source-feature-ordinal>"}, "territories": {"ccaa_manifest": portable(CCAA_MANIFEST), "province_manifest": portable(PROVINCE_MANIFEST), "snapshot": portable(SNAPSHOT)}, "checksums": input_checksums, "calculation": transform_info}, "policy": {"positive_relation": "intersection area > 0 in EPSG:3035", "boundary_touch": "area = 0 is retained in boundary-touches audit, never emitted as a territory relation", "slivers": "no area/fraction threshold; positive intersections retain area and fraction", "geometry": "canonical ESFire30 raw geometry only; no PMTiles, bounds, centroids, clipping or repair"}, "blocks": []}


def totals_for(blocks: Iterable[dict[str, Any]], years: Iterable[int]) -> dict[str, int]:
    wanted = set(years)
    selected = [item for item in blocks if item.get("year") in wanted]
    complete = [item for item in selected if item.get("status") == "complete"]
    return {
        "configured_blocks": len(wanted),
        "complete_blocks": len(complete),
        "geometry_count": sum(item.get("geometry_count", 0) for item in complete),
        "relation_count": sum(item.get("relation_count", 0) for item in complete),
        "boundary_touch_count": sum(item.get("boundary_touch_count", 0) for item in complete),
        "bytes": sum(item.get("bytes", 0) for item in complete),
    }


def archive_rows(archive: zipfile.ZipFile, es3: Any, year: int, wanted: set[int] | None = None):
    from shapely.geometry import shape
    reader = es3.load_es1().archive_reader(archive, year)
    for ordinal, shape_record in enumerate(reader.iterShapeRecords()):
        if wanted is None or ordinal in wanted:
            yield ordinal, shape(shape_record.shape.__geo_interface__)


def parse_sample(value: str) -> tuple[int, int]:
    # Canonical serialized ID: esfire30:v1:YEAR:ORDINAL.
    parts = value.split(":")
    if len(parts) != 4 or parts[:2] != ["esfire30", "v1"]:
        raise argparse.ArgumentTypeError(f"geometry_id inválido: {value}")
    year, ordinal = parts[2:]
    try:
        numeric_year, numeric_ordinal = int(year), int(ordinal)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"geometry_id inválido: {value}") from exc
    if numeric_year not in YEARS or numeric_ordinal < 0: raise argparse.ArgumentTypeError(f"geometry_id fuera de cobertura: {value}")
    return numeric_year, numeric_ordinal


def run(args: argparse.Namespace) -> dict[str, Any]:
    import shapefile  # dependency deliberately explicit for user command
    from shapely.strtree import STRtree
    del shapefile
    input_checksums = verify_inputs(); ccaa, provinces, territories = territory_units(); transform_geometry, transform_info = source_transformer()
    trees = {"autonomous_community": (STRtree([row["geometry"] for row in ccaa]), ccaa), "province": (STRtree([row["geometry"] for row in provinces]), provinces)}
    manifest_path = args.output / "manifest.json"; manifest = manifest_base(input_checksums, transform_info)
    existing = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() and args.resume else manifest
    existing_blocks = {item["year"]: item for item in existing.get("blocks", [])}
    targets: dict[int, set[int] | None]
    if args.sample:
        targets = {}
        for raw_id in args.sample:
            year, ordinal = parse_sample(raw_id); targets.setdefault(year, set()).add(ordinal)
        output_kind = "sample"
    elif args.all:
        targets = {year: None for year in YEARS}; output_kind = "national"
    elif args.year:
        targets = {year: None for year in args.year}; output_kind = "year_subset"
    else:
        raise ValueError("Indica --sample, --year o --all")
    manifest.update({"run_kind": output_kind, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "blocks": list(existing_blocks.values())})
    core = json.loads(ES3_CORE_RESULTS.read_text(encoding="utf-8"))
    expected_by_year = {int(year): count for year, count in core["by_year"].items()}
    with zipfile.ZipFile(ZIP) as archive:
        es3 = load_es3()
        for year in sorted(targets):
            old = existing_blocks.get(year)
            expected_count = len(targets[year]) if targets[year] is not None else expected_by_year[year]
            expected_ids_sha256 = geometry_ids_checksum(year, targets[year]) if targets[year] is not None else None
            same_selection = targets[year] is None or (old is not None and old.get("geometry_ids_sha256") == expected_ids_sha256)
            if old and args.resume and not args.force and old.get("status") == "complete" and old.get("geometry_count") == expected_count and same_selection:
                valid, _ = verify_block(old)
                if valid:
                    print(f"ESFire30 {year}: reutilizado", flush=True); continue
            entry = write_year(args.output, year, archive_rows(archive, es3, year, targets[year]), trees, territories, transform_geometry)
            existing_blocks[year] = entry; manifest["blocks"] = [existing_blocks[key] for key in sorted(existing_blocks)]
            manifest["totals"] = totals_for(manifest["blocks"], targets)
            atomic_json(manifest_path, manifest); print(f"ESFire30 {year}: completo ({entry['geometry_count']:,} geometrías, {entry['relation_count']:,} relaciones)", flush=True)
    manifest["blocks"] = [existing_blocks[key] for key in sorted(existing_blocks)]
    manifest["totals"] = totals_for(manifest["blocks"], targets)
    atomic_json(manifest_path, manifest)
    return manifest


def check(args: argparse.Namespace) -> dict[str, Any]:
    manifest = json.loads((args.output / "manifest.json").read_text(encoding="utf-8")); failures = []
    targets = set(YEARS if args.all else args.year or [])
    if args.sample:
        targets = {parse_sample(value)[0] for value in args.sample}
    for entry in manifest.get("blocks", []):
        if entry.get("year") in targets:
            valid, reason = verify_block(entry)
            if not valid: failures.append(f"{entry['year']}: {reason}")
            if args.sample:
                requested = {parse_sample(value)[1] for value in args.sample if parse_sample(value)[0] == entry.get("year")}
                if entry.get("geometry_ids_sha256") != geometry_ids_checksum(entry["year"], requested):
                    failures.append(f"{entry['year']}: selección de muestra")
    complete = [item for item in manifest.get("blocks", []) if item.get("year") in targets and item.get("status") == "complete"]
    if len(complete) != len(targets): failures.append("bloques completos insuficientes")
    if args.all and sum(item["geometry_count"] for item in complete) != EXPECTED_GEOMETRIES: failures.append("reconciliación nacional de geometrías")
    return {"valid": not failures, "failures": failures, "totals": manifest.get("totals", {})}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT); parser.add_argument("--resume", action="store_true"); parser.add_argument("--force", action="store_true")
    parser.add_argument("--all", action="store_true"); parser.add_argument("--year", type=int, action="append"); parser.add_argument("--sample", action="append", metavar="GEOMETRY_ID")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check(args), ensure_ascii=False)); return 0
    result = run(args); print(json.dumps({"totals": result.get("totals", {}), "manifest": portable(args.output / "manifest.json")}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
