#!/usr/bin/env python3
"""Deriva ESFire30 → municipio BDLJE actual sin usar EGIF ni PMTiles.

La relación significa solo intersección positiva del perímetro canónico con la
división municipal actual (snapshot 2026-08). El prefiltro provincial procede
del resultado C2B1A ya validado; no elige provincia principal ni elimina
slivers. Los límites históricos municipales no se reconstruyen aquí.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import resource
import sys
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS = ROOT / "scripts/relations/esfire30/territories.py"
CATALOG = ROOT / "data/territories/spain/municipality_catalog_2026-08-29.json"
CATALOG_SHA256 = "51174a29f166b194fa9d95e9b3bfc91521b0a189d193fe3a49efde58d35377c8"
MUNICIPAL_AUDIT = ROOT / "data/audit/territories/es4c2a3b_municipal_geometry_full_audit.json"
MUNICIPAL_SOURCE_SHA256 = "ca052a7592c45c03ea765e12e706652741964b80e8acd34e79978c31e9fe9dfc"
MUNICIPAL_ROOT = ROOT / "data/derived/spain/es4c2a3/municipalities"
PROVINCE_RELATIONS = ROOT / "data/derived/spain/es4c2b/esfire30_territory_relations"
PROVINCE_MANIFEST = PROVINCE_RELATIONS / "manifest.json"
OUTPUT = ROOT / "data/derived/spain/es4c2b/esfire30_municipality_relations"
EXPECTED_GEOMETRIES = 119_498
EXPECTED_MUNICIPALITIES = 8_132
PIPELINE_VERSION = "es-4c2b3a1-esfire30-municipality-relations-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable(path: Path) -> str:
    try: return str(path.relative_to(ROOT))
    except ValueError: return str(path)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def load_previous() -> Any:
    spec = importlib.util.spec_from_file_location("es4c2b1a_province_relations", PREVIOUS)
    if not spec or not spec.loader: raise RuntimeError("No se pudo cargar C2B1A")
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module); return module


def verify_inputs(previous: Any) -> dict[str, str]:
    checksums = previous.verify_inputs()
    if not CATALOG.is_file() or sha256(CATALOG) != CATALOG_SHA256: raise ValueError("Catálogo municipal BDLJE ausente o checksum inesperado")
    municipal_audit = json.loads(MUNICIPAL_AUDIT.read_text(encoding="utf-8"))
    source = municipal_audit.get("source", {})
    reconciliation = municipal_audit.get("reconciliation", {})
    shards = municipal_audit.get("shards_0m", {}).get("totals", {})
    if source.get("sha256") != MUNICIPAL_SOURCE_SHA256 or reconciliation.get("logical_municipalities") != EXPECTED_MUNICIPALITIES or shards.get("municipalities") != EXPECTED_MUNICIPALITIES:
        raise ValueError("Auditoría municipal C2A3B incoherente")
    province = json.loads(PROVINCE_MANIFEST.read_text(encoding="utf-8"))
    if province.get("totals", {}).get("geometry_count") != EXPECTED_GEOMETRIES: raise ValueError("Manifest provincial C2B1A no reconciliado")
    checksums[portable(CATALOG)] = CATALOG_SHA256
    checksums[portable(MUNICIPAL_AUDIT)] = sha256(MUNICIPAL_AUDIT)
    checksums["BDLJE municipal snapshot 2026-08"] = MUNICIPAL_SOURCE_SHA256
    checksums[portable(PROVINCE_MANIFEST)] = sha256(PROVINCE_MANIFEST)
    return checksums


def load_catalog() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    payload = json.loads(CATALOG.read_text(encoding="utf-8")); rows = payload.get("municipalities", [])
    if len(rows) != EXPECTED_MUNICIPALITIES: raise ValueError("Recuento municipal inesperado")
    by_id, by_province = {}, defaultdict(list)
    for row in rows:
        municipality_id, province_id = row.get("municipality_id"), row.get("province_id")
        if not isinstance(municipality_id, str) or not municipality_id.startswith("ES:MUN:") or municipality_id in by_id:
            raise ValueError("Crosswalk municipal inválido")
        # Ceuta/Melilla no aparecen como provincias C2B1A; no tendrán
        # candidatos ESFire30 mientras la fuente siga sin cobertura allí.
        if province_id: by_province[province_id].append(row)
        by_id[municipality_id] = row
    return by_id, by_province


def shard_path(asset_id: str) -> Path:
    if not asset_id.startswith("municipalities:ES:"): raise ValueError(f"asset_id municipal inválido: {asset_id}")
    return MUNICIPAL_ROOT / f"{asset_id.split(':', 1)[1].replace(':', '-')}.geojson"


def load_province_memberships(year: int) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, Any]]:
    manifest = json.loads(PROVINCE_MANIFEST.read_text(encoding="utf-8")); block = next((row for row in manifest.get("blocks", []) if row.get("year") == year), None)
    if not block or block.get("status") != "complete": raise ValueError(f"Relaciones provinciales C2B1A no disponibles: {year}")
    path = ROOT / block["relations_path"]
    if sha256(path) != block.get("relations_sha256"): raise ValueError(f"Checksum provincial inesperado: {year}")
    provinces, communities = defaultdict(set), defaultdict(set)
    with path.open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row.get("intersection_class") != "positive_area_intersection": continue
            if row.get("territory_level") == "province": provinces[row["geometry_id"]].add(row["territory_id"])
            elif row.get("territory_level") == "autonomous_community": communities[row["geometry_id"]].add(row["territory_id"])
    return provinces, communities, block


class MunicipalGeometryCache:
    def __init__(self, by_province: dict[str, list[dict[str, Any]]]): self.by_province = by_province; self.cache: dict[str, tuple[Any, list[dict[str, Any]]]] = {}
    def tree(self, province_id: str) -> tuple[Any, list[dict[str, Any]]]:
        if province_id in self.cache: return self.cache[province_id]
        from pyproj import Transformer
        from shapely.geometry import shape
        from shapely.ops import transform
        from shapely.strtree import STRtree
        catalog_rows = self.by_province.get(province_id, [])
        if not catalog_rows: return STRtree([]), []
        asset_ids = {row["asset_id"] for row in catalog_rows}
        if len(asset_ids) != 1: raise ValueError(f"Shard municipal ambiguo: {province_id}")
        collection = json.loads(shard_path(next(iter(asset_ids))).read_text(encoding="utf-8"))
        expected = {row["municipality_id"] for row in catalog_rows}; units = []
        forward = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform
        for feature in collection.get("features", []):
            props = feature.get("properties") or {}; municipality_id = props.get("municipality_id")
            if municipality_id not in expected or props.get("province_id") != province_id: raise ValueError("Shard municipal/catálogo incoherente")
            geometry = transform(forward, shape(feature.get("geometry")))
            if geometry.is_empty or not geometry.is_valid: raise ValueError(f"Geometría municipal inválida: {municipality_id}")
            units.append({"municipality_id": municipality_id, "province_id": province_id, "autonomous_community_id": props.get("autonomous_community_id"), "geometry": geometry})
        if {row["municipality_id"] for row in units} != expected: raise ValueError(f"Shard municipal incompleto: {province_id}")
        result = STRtree([row["geometry"] for row in units]), units; self.cache[province_id] = result; return result


def relation_id(previous: Any, geometry_id: str, municipality_id: str) -> str:
    return previous.relation_id(geometry_id, municipality_id)


def relation_rows(previous: Any, geometry_id: str, geometry: Any, province_ids: set[str], community_ids: set[str], cache: MunicipalGeometryCache) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    if geometry.is_empty or not geometry.is_valid or geometry.area <= 0: raise ValueError(f"Geometría ESFire30 inválida: {geometry_id}")
    positives, touches, candidates, post_prefilter = [], [], 0, 0; source_area = geometry.area
    for province_id in sorted(province_ids):
        tree, units = cache.tree(province_id); candidates += len(units)
        for raw_index in tree.query(geometry, predicate="intersects"):
            post_prefilter += 1; municipality = units[int(raw_index)]; overlap = geometry.intersection(municipality["geometry"]); area = overlap.area
            # No redondear aquí: un sliver de área positiva puede ser inferior
            # a 0,001 m² y seguir siendo una relación válida por contrato.
            common = {"geometry_id": geometry_id, "subject_id": geometry_id, "territory_id": municipality["municipality_id"], "municipality_id": municipality["municipality_id"], "territory_type": "municipality", "territory_level": "municipality", "relation_type": "spatial_intersection", "intersection_area_m2": float(area), "intersection_fraction": float(area / source_area), "intersection_fraction_municipality": float(area / municipality["geometry"].area), "parent_province_id": province_id, "parent_autonomous_community_id": municipality["autonomous_community_id"]}
            if area > 0:
                positives.append({"territory_relation_id": relation_id(previous, geometry_id, municipality["municipality_id"]), **common, "mapping_status": "confirmed", "qa_status": "not_checkable", "intersection_class": "positive_area_intersection", "provenance": {"source_id": "esfire30", "source_record_id": geometry_id, "retrieved_at": "2026-08-26T00:00:00Z", "snapshot_id": "zenodo-18449006-v1", "transformations": [PIPELINE_VERSION, "bdlje-current-2026-08"]}})
            else: touches.append({**common, "intersection_class": "boundary_touch_only"})
    keys = {(row["geometry_id"], row["territory_id"], row["relation_type"]) for row in positives}
    if len(keys) != len(positives): raise ValueError(f"Relación municipal duplicada: {geometry_id}")
    for row in positives:
        if row["parent_province_id"] not in province_ids or row["parent_autonomous_community_id"] not in community_ids: raise ValueError(f"Jerarquía C2B1A inconsistente: {geometry_id}")
    return positives, touches, candidates, post_prefilter


def paths(output: Path, year: int) -> tuple[Path, Path]: return output / f"relations-{year}.jsonl", output / f"boundary-touches-{year}.jsonl"


def write_year(previous: Any, output: Path, year: int, rows: Iterable[tuple[int, Any]], cache: MunicipalGeometryCache, transform_geometry: Any) -> dict[str, Any]:
    province_memberships, community_memberships, input_block = load_province_memberships(year); relation_path, touch_path = paths(output, year); relation_path.parent.mkdir(parents=True, exist_ok=True)
    relation_fd, relation_tmp = tempfile.mkstemp(prefix=f".{relation_path.name}.", suffix=".part", dir=output); touch_fd, touch_tmp = tempfile.mkstemp(prefix=f".{touch_path.name}.", suffix=".part", dir=output)
    digest, touch_digest, geometry_digest = hashlib.sha256(), hashlib.sha256(), hashlib.sha256(); counts = Counter(); started = time.monotonic()
    try:
        with os.fdopen(relation_fd, "wb") as relations, os.fdopen(touch_fd, "wb") as touches_handle:
            for ordinal, raw in rows:
                gid = previous.geometry_id(year, ordinal); geometry_digest.update(f"{gid}\n".encode()); geometry = transform_geometry(raw)
                positives, touches, candidates, tested = relation_rows(previous, gid, geometry, province_memberships.get(gid, set()), community_memberships.get(gid, set()), cache)
                counts["geometry_count"] += 1; counts["candidate_municipalities"] += candidates; counts["spatial_candidates"] += tested; counts["zero_relation_count"] += int(not positives); counts["max_municipalities"] = max(counts["max_municipalities"], len(positives))
                for row in positives:
                    line = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(); relations.write(line); digest.update(line); counts["relation_count"] += 1
                for row in touches:
                    line = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(); touches_handle.write(line); touch_digest.update(line); counts["boundary_touch_count"] += 1
            relations.flush(); os.fsync(relations.fileno()); touches_handle.flush(); os.fsync(touches_handle.fileno())
        os.replace(relation_tmp, relation_path); os.replace(touch_tmp, touch_path)
    except BaseException:
        for temporary in (relation_tmp, touch_tmp):
            try: os.unlink(temporary)
            except FileNotFoundError: pass
        raise
    # Linux reports ru_maxrss in KiB; it is process-wide diagnostic evidence,
    # not memory allocated exclusively by this yearly block.
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    return {"year": year, "status": "complete", "geometry_count": counts["geometry_count"], "geometry_ids_sha256": geometry_digest.hexdigest(), "relation_count": counts["relation_count"], "boundary_touch_count": counts["boundary_touch_count"], "zero_relation_count": counts["zero_relation_count"], "max_municipalities": counts["max_municipalities"], "candidate_municipalities": counts["candidate_municipalities"], "spatial_candidates": counts["spatial_candidates"], "hierarchy_inconsistency_count": 0, "province_relation_input_sha256": input_block["relations_sha256"], "relations_path": portable(relation_path), "boundary_touches_path": portable(touch_path), "relations_sha256": digest.hexdigest(), "boundary_touches_sha256": touch_digest.hexdigest(), "bytes": relation_path.stat().st_size + touch_path.stat().st_size, "elapsed_seconds": round(time.monotonic() - started, 3), "process_peak_rss_bytes": peak_rss}


def verify_block(entry: dict[str, Any]) -> tuple[bool, str]:
    for key, checksum, klass, count in (("relations_path", "relations_sha256", "positive_area_intersection", "relation_count"), ("boundary_touches_path", "boundary_touches_sha256", "boundary_touch_only", "boundary_touch_count")):
        path = ROOT / entry[key]
        if not path.is_file() or sha256(path) != entry[checksum]: return False, f"{path.name}: checksum"
        seen, lines = set(), 0
        with path.open(encoding="utf-8") as source:
            for line in source:
                lines += 1; row = json.loads(line)
                if row.get("intersection_class") != klass: return False, f"{path.name}: clase"
                if klass == "positive_area_intersection":
                    key_value = (row.get("geometry_id"), row.get("territory_id"), row.get("relation_type"))
                    if key_value in seen or row.get("intersection_area_m2", 0) <= 0 or row.get("territory_type") != "municipality": return False, f"{path.name}: duplicado/área"
                    seen.add(key_value)
        if lines != entry[count]: return False, f"{path.name}: recuento"
    return True, "ok"


def totals(blocks: Iterable[dict[str, Any]], years: Iterable[int]) -> dict[str, int]:
    selected = [row for row in blocks if row.get("year") in set(years) and row.get("status") == "complete"]
    return {"configured_blocks": len(set(years)), "complete_blocks": len(selected), "geometry_count": sum(row["geometry_count"] for row in selected), "relation_count": sum(row["relation_count"] for row in selected), "boundary_touch_count": sum(row["boundary_touch_count"] for row in selected), "zero_relation_count": sum(row["zero_relation_count"] for row in selected), "max_municipalities": max([row["max_municipalities"] for row in selected] or [0]), "bytes": sum(row["bytes"] for row in selected)}


def manifest_base(previous: Any, checksums: dict[str, str], transform: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "relation_contract": "schemas/national/v1/atlas-contracts.schema.json#/territoryRelation", "semantics": "current_municipality_intersection != historical_municipality_containment; ESFire30 geometry intersects BDLJE current municipal boundary, not EGIF/source municipality or ignition", "input": {"geometry_snapshot": {"doi": "10.5281/zenodo.18449006", "zip": portable(previous.ZIP), "geometry_id": "esfire30:v1:<year>:<source-feature-ordinal>"}, "municipalities": {"catalog": portable(CATALOG), "snapshot": "BDLJE current 2026-08", "municipality_count": EXPECTED_MUNICIPALITIES}, "province_prefilter": {"manifest": portable(PROVINCE_MANIFEST), "relation_output": portable(PROVINCE_RELATIONS)}, "checksums": checksums, "calculation": transform}, "policy": {"positive_relation": "intersection area > 0 in EPSG:3035", "boundary_touch": "area = 0 audited separately, never intersects", "slivers": "no threshold; all positive intersections retained", "prefilter": "all provinces already related to each geometry in C2B1A; multi-province geometry evaluates all candidates", "geometry": "canonical ESFire30 raw geometry only; no PMTiles, centroid, bounds, clipping or repair"}, "blocks": []}


def run(args: argparse.Namespace) -> dict[str, Any]:
    previous = load_previous(); checksums = verify_inputs(previous); _, by_province = load_catalog(); transform_geometry, transform_info = previous.source_transformer(); cache = MunicipalGeometryCache(by_province)
    if args.sample:
        targets: dict[int, set[int] | None] = {}
        for value in args.sample:
            year, ordinal = previous.parse_sample(value); targets.setdefault(year, set()).add(ordinal)
        kind = "sample"
    elif args.all: targets, kind = {year: None for year in previous.YEARS}, "national"
    elif args.year: targets, kind = {year: None for year in args.year}, "year_subset"
    else: raise ValueError("Indica --sample, --year o --all")
    manifest_path = args.output / "manifest.json"; manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if args.resume and manifest_path.exists() else manifest_base(previous, checksums, transform_info); existing = {row["year"]: row for row in manifest.get("blocks", [])}
    core = json.loads(previous.ES3_CORE_RESULTS.read_text(encoding="utf-8")); expected_by_year = {int(year): count for year, count in core["by_year"].items()}
    with zipfile.ZipFile(previous.ZIP) as archive:
        es3 = previous.load_es3()
        for year in sorted(targets):
            old, selection = existing.get(year), targets[year]; expected = len(selection) if selection is not None else expected_by_year[year]; expected_hash = previous.geometry_ids_checksum(year, selection) if selection is not None else None
            if old and args.resume and not args.force and old.get("status") == "complete" and old.get("geometry_count") == expected and (selection is None or old.get("geometry_ids_sha256") == expected_hash) and verify_block(old)[0]:
                print(f"ESFire30 {year}: reutilizado", flush=True); continue
            entry = write_year(previous, args.output, year, previous.archive_rows(archive, es3, year, selection), cache, transform_geometry); existing[year] = entry
            manifest.update({"run_kind": kind, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "blocks": [existing[key] for key in sorted(existing)], "totals": totals(existing.values(), existing.keys()) }); atomic_json(manifest_path, manifest); print(f"ESFire30 {year}: completo ({entry['geometry_count']:,} geometrías, {entry['relation_count']:,} relaciones)", flush=True)
    manifest.update({"run_kind": kind, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "blocks": [existing[key] for key in sorted(existing)], "totals": totals(existing.values(), existing.keys()) }); atomic_json(manifest_path, manifest); return manifest


def check(args: argparse.Namespace) -> dict[str, Any]:
    previous = load_previous(); manifest = json.loads((args.output / "manifest.json").read_text(encoding="utf-8")); wanted = set(previous.YEARS if args.all else args.year or [])
    if args.sample: wanted = {previous.parse_sample(value)[0] for value in args.sample}
    failures = []
    for block in (row for row in manifest.get("blocks", []) if row.get("year") in wanted):
        valid, reason = verify_block(block)
        if not valid: failures.append(f"{block['year']}: {reason}")
        if args.sample:
            selected = {previous.parse_sample(value)[1] for value in args.sample if previous.parse_sample(value)[0] == block["year"]}
            if block.get("geometry_ids_sha256") != previous.geometry_ids_checksum(block["year"], selected): failures.append(f"{block['year']}: selección")
    complete = [row for row in manifest.get("blocks", []) if row.get("year") in wanted and row.get("status") == "complete"]
    if len(complete) != len(wanted): failures.append("bloques completos insuficientes")
    if args.all and sum(row["geometry_count"] for row in complete) != EXPECTED_GEOMETRIES: failures.append("reconciliación nacional de geometrías")
    return {"valid": not failures, "failures": failures, "totals": manifest.get("totals", {})}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output", type=Path, default=OUTPUT); parser.add_argument("--resume", action="store_true"); parser.add_argument("--force", action="store_true"); parser.add_argument("--all", action="store_true"); parser.add_argument("--year", type=int, action="append"); parser.add_argument("--sample", action="append", metavar="GEOMETRY_ID"); parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check: print(json.dumps(check(args), ensure_ascii=False)); return 0
    result = run(args); print(json.dumps({"totals": result.get("totals", {}), "manifest": portable(args.output / "manifest.json")}, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
