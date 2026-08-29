#!/usr/bin/env python3
"""Audita relaciones ESFire30→municipio ya calculadas, sin spatial join nacional.

Lee exclusivamente los JSONL C2B3A1, catálogos ES-2 y relaciones C2B1A. Solo
abre las 83 geometrías sin municipio para clasificarlas frente a unidades BDLJE
no municipales y límites provinciales actuales.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import os
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
RELATION_DIR = ROOT / "data/derived/spain/es4c2b/esfire30_municipality_relations"
MANIFEST = RELATION_DIR / "manifest.json"
PROVINCE_DIR = ROOT / "data/derived/spain/es4c2b/esfire30_territory_relations"
PROVINCE_MANIFEST = PROVINCE_DIR / "manifest.json"
CATALOG = ROOT / "data/territories/spain/municipality_catalog_2026-08-29.json"
TERRITORIES = ROOT / "data/territories/spain/territories-2026-01-01.json"
MUNICIPAL_AUDIT = ROOT / "data/audit/territories/es4c2a3b_municipal_geometry_full_audit.json"
BUILDER = ROOT / "scripts/relations/esfire30/municipalities.py"
OUTPUT = ROOT / "data/audit/esfire30/es4c2b3a2_municipal_relations.json"
EXPECTED_GEOMETRIES, EXPECTED_MUNICIPALITIES, EXPECTED_ZEROS = 119_498, 8_132, 83
SLIVER_LABELS = ("<1e-6", "1e-6–1e-5", "1e-5–1e-4", "1e-4–1e-3", "1e-3–1e-2", ">=1e-2")
REFERENCE_IDS = ("ES:MUN:03065", "ES:MUN:03014", "ES:MUN:46250", "ES:MUN:08019", "ES:MUN:32054", "ES:MUN:15030", "ES:MUN:41091", "ES:MUN:17079", "ES:MUN:17094", "ES:MUN:09109", "ES:MUN:09276", "ES:MUN:46001")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable(path: Path) -> str:
    try: return str(path.relative_to(ROOT))
    except ValueError: return str(path)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def metrics(value: Any) -> dict[str, int]:
    raw = canonical_bytes(value)
    return {"raw_bytes": len(raw), "gzip_bytes": len(gzip.compress(raw, compresslevel=9, mtime=0))}


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader: raise RuntimeError(f"No se puede cargar {path}")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def percentile(values: Iterable[int], quantile: float) -> int:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * quantile)] if ordered else 0


def sliver_bucket(value: float) -> str:
    if value < 1e-6: return "<1e-6"
    if value < 1e-5: return "1e-6–1e-5"
    if value < 1e-4: return "1e-5–1e-4"
    if value < 1e-3: return "1e-4–1e-3"
    if value < 1e-2: return "1e-3–1e-2"
    return ">=1e-2"


def geometry_cardinality(counts: dict[str, set[str]], geometry_ids: set[str]) -> dict[str, Any]:
    values = [len(counts.get(gid, set())) for gid in geometry_ids]; result = Counter()
    for value in values:
        result["0" if value == 0 else "1" if value == 1 else "2" if value == 2 else "3" if value == 3 else "4" if value == 4 else "5" if value == 5 else "6–10" if value <= 10 else "11–15" if value <= 15 else "16–19" if value <= 19 else "20+"] += 1
    return {"buckets": {key: result[key] for key in ("0", "1", "2", "3", "4", "5", "6–10", "11–15", "16–19", "20+")}, "mean": sum(values) / len(values), "median": percentile(values, .5), "p95": percentile(values, .95), "p99": percentile(values, .99), "maximum": max(values)}


def municipality_cardinality(counts: dict[str, set[str]], municipality_ids: Iterable[str]) -> dict[str, Any]:
    values = [len(counts.get(mid, set())) for mid in municipality_ids]; result = Counter()
    for value in values:
        result["0" if value == 0 else "1–10" if value <= 10 else "11–50" if value <= 50 else "51–100" if value <= 100 else "101–250" if value <= 250 else "251–500" if value <= 500 else "501–1000" if value <= 1000 else "1001–2500" if value <= 2500 else "2501–5000" if value <= 5000 else ">5000"] += 1
    labels = ("0", "1–10", "11–50", "51–100", "101–250", "251–500", "501–1000", "1001–2500", "2501–5000", ">5000")
    return {"buckets": {key: result[key] for key in labels}, "mean": sum(values) / len(values), "median": percentile(values, .5), "p95": percentile(values, .95), "p99": percentile(values, .99), "maximum": max(values)}


def read_jsonl(path: Path, checksum: str):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for line in source:
            digest.update(line)
            if line.strip(): yield json.loads(line)
    if digest.hexdigest() != checksum: raise ValueError(f"Checksum inesperado: {portable(path)}")


def load_catalog() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["municipalities"]
    municipalities = {row["municipality_id"]: row for row in catalog}
    if len(municipalities) != EXPECTED_MUNICIPALITIES: raise ValueError("Catálogo municipal inesperado")
    territories = {row["territory_id"]: row for row in json.loads(TERRITORIES.read_text(encoding="utf-8"))["territories"]}
    return municipalities, territories, {row["territory_id"]: row for row in territories.values() if row["territory_type"] in {"autonomous_community", "autonomous_city", "province"}}


def load_parent_relations() -> tuple[dict[str, set[str]], dict[str, set[str]], set[str]]:
    manifest = json.loads(PROVINCE_MANIFEST.read_text(encoding="utf-8")); provinces, ccaa = defaultdict(set), defaultdict(set)
    for block in manifest["blocks"]:
        path = ROOT / block["relations_path"]
        for row in read_jsonl(path, block["relations_sha256"]):
            if row.get("intersection_class") != "positive_area_intersection": continue
            if row["territory_level"] == "province": provinces[row["geometry_id"]].add(row["territory_id"])
            elif row["territory_level"] == "autonomous_community": ccaa[row["geometry_id"]].add(row["territory_id"])
    return provinces, ccaa, set(provinces) | set(ccaa)


def index_sizes(forward: dict[str, set[str]], inverse: dict[str, set[str]], catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    forward_json = {key: sorted(value) for key, value in sorted(forward.items())}
    inverse_json = {key: sorted(value) for key, value in sorted(inverse.items())}
    by_province, by_ccaa = defaultdict(dict), defaultdict(dict)
    for municipality_id, values in inverse_json.items():
        row = catalog[municipality_id]
        if row["province_id"]: by_province[row["province_id"]][municipality_id] = values
        by_ccaa[row["autonomous_community_id"]][municipality_id] = values
    def shards(groups: dict[str, dict[str, list[str]]]) -> dict[str, Any]:
        sized = {key: metrics(value) for key, value in sorted(groups.items())}
        return {"asset_count": len(sized), "raw_bytes": sum(x["raw_bytes"] for x in sized.values()), "gzip_bytes": sum(x["gzip_bytes"] for x in sized.values()), "largest": sorted(({"territory_id": key, **value} for key, value in sized.items()), key=lambda row: (-row["gzip_bytes"], row["territory_id"]))[:10]}
    entries = [{"municipality_id": key, "geometry_count": len(value), **metrics({key: value})} for key, value in inverse_json.items()]
    return {"inverse_national": {**metrics(inverse_json), "bytes_per_municipality": metrics(inverse_json)["gzip_bytes"] / EXPECTED_MUNICIPALITIES, "largest_entry": max(entries, key=lambda row: row["gzip_bytes"])}, "forward_national": {**metrics(forward_json), "bytes_per_geometry": metrics(forward_json)["gzip_bytes"] / EXPECTED_GEOMETRIES}, "inverse_by_province": shards(by_province), "inverse_by_ccaa": shards(by_ccaa)}


def targeted_zero_audit(zero_ids: set[str], provinces_by_geometry: dict[str, set[str]], builder: Any) -> dict[str, Any]:
    """Abre solo las 83 geometrías zero y las 81 unidades BDLJE no municipales."""
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform
    from shapely.strtree import STRtree

    audit = json.loads(MUNICIPAL_AUDIT.read_text(encoding="utf-8")); source_path = ROOT / audit["source"]["path"]
    raw = json.loads(source_path.read_text(encoding="utf-8")); to_area = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform
    units_by_province: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in raw["features"]:
        props = feature.get("properties") or {}; code = str(props.get("nationalcode") or "")
        if len(code) == 11 and code.startswith("34") and code[6:11].startswith("53"):
            units_by_province[f"ES:PROV:{code[4:6]}"] .append({"source_code": code, "name": props.get("nameunit"), "geometry": transform(to_area, shape(feature["geometry"]))})
    if sum(len(values) for values in units_by_province.values()) != 81: raise ValueError("Inventario NON_MUNICIPAL_UNIT inesperado")
    trees = {key: (STRtree([u["geometry"] for u in values]), values) for key, values in units_by_province.items()}
    previous = builder.load_previous(); transform_geometry, _ = previous.source_transformer(); province_units = {row["territory_id"]: row["geometry"] for row in previous.territory_units()[1]}
    targets: dict[int, set[int]] = defaultdict(set)
    for gid in zero_ids:
        _, _, year, ordinal = gid.split(":"); targets[int(year)].add(int(ordinal))
    rows = []
    with zipfile.ZipFile(previous.ZIP) as archive:
        es3 = previous.load_es3()
        for year in sorted(targets):
            for ordinal, raw_geometry in previous.archive_rows(archive, es3, year, targets[year]):
                gid = previous.geometry_id(year, ordinal); geometry = transform_geometry(raw_geometry); area = geometry.area
                parents = sorted(provinces_by_geometry[gid]); non_municipal = []
                province_area = 0.0
                for province_id in parents:
                    province_area += geometry.intersection(province_units[province_id]).area
                    if province_id in trees:
                        tree, units = trees[province_id]
                        for raw_index in tree.query(geometry, predicate="intersects"):
                            unit = units[int(raw_index)]; overlap = geometry.intersection(unit["geometry"])
                            if overlap.area > 0: non_municipal.append({"source_code": unit["source_code"], "name": unit["name"], "intersection_area_m2": overlap.area, "intersection_fraction_fire": overlap.area / area})
                coverage_fraction = min(1.0, province_area / area)
                if non_municipal: classification = "positive_non_municipal_unit"
                elif coverage_fraction < .999999999: classification = "partly_outside_parent_province_extent_potential_coast_or_outer_boundary"
                else: classification = "current_municipal_coverage_gap_or_cartographic_difference"
                rows.append({"geometry_id": gid, "parent_province_ids": parents, "parent_province_coverage_fraction": coverage_fraction, "non_municipal_positive_intersections": sorted(non_municipal, key=lambda r: r["source_code"]), "classification": classification})
    if len(rows) != len(zero_ids): raise ValueError("Auditoría zero incompleta")
    counts = Counter(row["classification"] for row in rows)
    return {"geometry_count": len(rows), "classification": dict(sorted(counts.items())), "non_municipal_geometry_count": sum(bool(row["non_municipal_positive_intersections"]) for row in rows), "rows": sorted(rows, key=lambda row: row["geometry_id"])}


def build() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")); municipalities, territories, territorial_units = load_catalog(); provinces_by_geometry, ccaa_by_geometry, all_geometry_ids = load_parent_relations()
    if len(all_geometry_ids) != EXPECTED_GEOMETRIES: raise ValueError("C2B1A no reconcilia geometry_id")
    forward, inverse, seen = defaultdict(set), defaultdict(set), set(); duplicates = []; slivers = Counter(); smallest = []; fractions_municipality = []; source_area = {}
    ccaa_cov = defaultdict(lambda: {"municipalities": set(), "geometries": set(), "relations": 0}); province_cov = defaultdict(lambda: {"municipalities": set(), "geometries": set(), "relations": 0})
    relation_count, touch_count, hierarchy_errors = 0, 0, []
    for block in sorted(manifest["blocks"], key=lambda row: row["year"]):
        relation_path, touch_path = ROOT / block["relations_path"], ROOT / block["boundary_touches_path"]
        for touch in read_jsonl(touch_path, block["boundary_touches_sha256"]):
            if touch.get("intersection_class") != "boundary_touch_only": raise ValueError("Touch inesperado")
            touch_count += 1
        for row in read_jsonl(relation_path, block["relations_sha256"]):
            if row.get("intersection_class") != "positive_area_intersection" or row.get("relation_type") != "spatial_intersection": raise ValueError("Relación inesperada")
            gid, mid = row["geometry_id"], row["municipality_id"]; key = (gid, mid, row["relation_type"]); relation_count += 1
            if key in seen: duplicates.append({"geometry_id": gid, "municipality_id": mid}); continue
            seen.add(key)
            if mid not in municipalities or row.get("intersection_area_m2", 0) <= 0: raise ValueError("Municipio/área inválidos")
            forward[gid].add(mid); inverse[mid].add(gid); fraction = float(row["intersection_fraction"]); slivers[sliver_bucket(fraction)] += 1
            smallest.append({"geometry_id": gid, "municipality_id": mid, "intersection_area_m2": row["intersection_area_m2"], "intersection_fraction_fire": fraction, "intersection_fraction_municipality": row.get("intersection_fraction_municipality")})
            if fraction > 0: source_area.setdefault(gid, float(row["intersection_area_m2"]) / fraction)
            if row.get("intersection_fraction_municipality") is not None: fractions_municipality.append(float(row["intersection_fraction_municipality"]))
            catalog = municipalities[mid]; expected_province, expected_ccaa = catalog["province_id"], catalog["autonomous_community_id"]
            if expected_province not in provinces_by_geometry[gid] or expected_ccaa not in ccaa_by_geometry[gid]: hierarchy_errors.append({"geometry_id": gid, "municipality_id": mid, "province_id": expected_province, "autonomous_community_id": expected_ccaa})
            for level, territory_id in (("ccaa", expected_ccaa), ("province", expected_province)):
                if territory_id:
                    coverage = ccaa_cov[territory_id] if level == "ccaa" else province_cov[territory_id]
                    coverage["municipalities"].add(mid); coverage["geometries"].add(gid); coverage["relations"] += 1
    zero_ids = all_geometry_ids - set(forward)
    if relation_count != manifest["totals"]["relation_count"] or len(zero_ids) != EXPECTED_ZEROS: raise ValueError("Reconciliación municipal inesperada")
    builder = load_module(BUILDER, "es4c2b3a1_builder_for_audit")
    zero_audit = targeted_zero_audit(zero_ids, provinces_by_geometry, builder)
    cardinality_g = geometry_cardinality(forward, all_geometry_ids); cardinality_m = municipality_cardinality(inverse, municipalities)
    def coverage(groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        output=[]
        for tid in sorted(territorial_units):
            unit=territorial_units[tid]
            if unit["territory_type"] not in ({"autonomous_community", "autonomous_city"} if groups is ccaa_cov else {"province"}): continue
            row=groups[tid]; output.append({"territory_id":tid,"official_name":unit["official_name"],"municipalities_with_geometry":len(row["municipalities"]),"geometry_ids_unique":len(row["geometries"]),"municipality_relations":row["relations"]})
        return output
    top = sorted(({"municipality_id": mid, "official_name": municipalities[mid]["official_name"], "province_id": municipalities[mid]["province_id"], "geometry_count": len(inverse[mid])} for mid in municipalities), key=lambda row:(-row["geometry_count"],row["municipality_id"]))[:25]
    references=[{"municipality_id":mid,"official_name":municipalities[mid]["official_name"],"province_id":municipalities[mid]["province_id"],"geometry_count":len(inverse[mid])} for mid in REFERENCE_IDS]
    large_controls=[{"geometry_id":gid,"municipality_count":len(forward.get(gid,set())),"source_area_estimate_m2":source_area.get(gid)} for gid in ("esfire30:v1:1994:2841","esfire30:v1:2004:2622","esfire30:v1:2012:24","esfire30:v1:2021:1311")]
    extremes=[{"geometry_id":gid,"municipality_count":len(mids),"source_area_estimate_m2":source_area.get(gid)} for gid,mids in sorted(forward.items()) if len(mids)>=16]
    report={"schema_version":"es4c2b3a2-municipal-relation-audit-v1","scope":"Audit of precomputed C2B3A1 JSONL; targeted geometry reads are limited to the 83 zero-relation geometry_ids.","input":{"municipal_manifest":portable(MANIFEST),"municipal_manifest_sha256":sha256(MANIFEST),"province_manifest":portable(PROVINCE_MANIFEST),"province_manifest_sha256":sha256(PROVINCE_MANIFEST),"municipality_catalog":portable(CATALOG),"municipality_catalog_sha256":sha256(CATALOG),"geometry_count_expected":EXPECTED_GEOMETRIES,"municipality_count":EXPECTED_MUNICIPALITIES},"semantics":"current_municipality_intersection != historical_municipality_containment; counts are ESFire30 perimeters intersecting current BDLJE municipalities, not administrative fire incidence.","reconciliation":{"geometry_ids":len(all_geometry_ids),"relations":relation_count,"expected_relations":143477,"duplicates":len(duplicates),"duplicate_examples":duplicates[:20],"hierarchy_inconsistencies":len(hierarchy_errors),"hierarchy_examples":hierarchy_errors[:20],"boundary_touches":touch_count,"municipality_unresolved_geometry_count":len(zero_ids)},"geometry_to_municipality":{"distribution":cardinality_g,"extreme_geometries":extremes,"large_perimeter_controls":large_controls},"municipality_to_geometry":{"distribution":cardinality_m,"top_25":top,"reference_cases":references},"zero_relation":zero_audit,"slivers":{"fraction_of_fire_buckets":{label:slivers[label] for label in SLIVER_LABELS},"smallest_20":sorted(smallest,key=lambda row:(row["intersection_fraction_fire"],row["geometry_id"],row["municipality_id"]))[:20],"fraction_of_municipality":{"available_relations":len(fractions_municipality),"minimum":min(fractions_municipality),"p50":percentile([int(value*10**15) for value in fractions_municipality],.5)/10**15,"p95":percentile([int(value*10**15) for value in fractions_municipality],.95)/10**15}},"coverage":{"ccaa":coverage(ccaa_cov),"province":coverage(province_cov)},"indexes":index_sizes(forward,inverse,municipalities),"multi_parent_controls":{"multi_province":"esfire30:v1:2011:88","multi_ccaa":"esfire30:v1:1985:1037","municipalities_for_multi_province":sorted(forward.get("esfire30:v1:2011:88",set())),"municipalities_for_multi_ccaa":sorted(forward.get("esfire30:v1:1985:1037",set()))},"runtime_note":"No runtime conclusion from list size alone. Compare the largest municipality list with Galicia 38645 before any Chromium phase; zero-municipality geometries remain visible at Spain/CCAA/province but have no municipal filter entry."}
    report["report_sha256"]=hashlib.sha256(canonical_bytes(report)).hexdigest(); return report


def check(output: Path) -> dict[str, Any]:
    report=json.loads(output.read_text(encoding="utf-8")); stored=report.pop("report_sha256",None); failures=[]
    if stored!=hashlib.sha256(canonical_bytes(report)).hexdigest(): failures.append("checksum del informe")
    if report["reconciliation"]["geometry_ids"]!=EXPECTED_GEOMETRIES or report["reconciliation"]["relations"]!=143477: failures.append("reconciliación")
    if report["reconciliation"]["duplicates"] or report["reconciliation"]["hierarchy_inconsistencies"]: failures.append("integridad")
    return {"valid":not failures,"failures":failures,"report":portable(output)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--output",type=Path,default=OUTPUT); parser.add_argument("--check",action="store_true"); args=parser.parse_args()
    if args.check: print(json.dumps(check(args.output),ensure_ascii=False)); return 0
    report=build(); atomic_json(args.output,report); print(json.dumps({"valid":not report["reconciliation"]["duplicates"] and not report["reconciliation"]["hierarchy_inconsistencies"],"relations":report["reconciliation"]["relations"],"report":portable(args.output)},ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
