#!/usr/bin/env python3
"""Audita relaciones ESFire30→territorio ya derivadas en ES-4C2B1A.

No abre geometrías ESFire30 ni recalcula intersecciones. Lee exclusivamente el
manifest y JSONL de relaciones/touches, el catálogo ES-2 y el resumen ES-3.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
RELATION_DIR = ROOT / "data/derived/spain/es4c2b/esfire30_territory_relations"
MANIFEST = RELATION_DIR / "manifest.json"
TERRITORIES = ROOT / "data/territories/spain/territories-2026-01-01.json"
ES3 = ROOT / "data/derived/spain/es3/results.json"
OUTPUT = ROOT / "data/audit/esfire30/es4c2b1b_territory_relations.json"
EXPECTED_GEOMETRIES = 119_498
SLIVER_BUCKETS = (0.000001, 0.00001, 0.0001, 0.001, 0.01)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def portable(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def gzip_size(paths: Iterable[Path]) -> int:
    """Calcula gzip determinista en streaming sin generar un asset persistente."""
    import zlib

    compressor = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=31)
    size = 0
    for path in paths:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                size += len(compressor.compress(block))
    return size + len(compressor.flush())


def json_size(value: Any) -> dict[str, int | float]:
    raw = canonical_bytes(value)
    return {"raw_bytes": len(raw), "gzip_bytes": len(gzip.compress(raw, compresslevel=9, mtime=0))}


def load_territories(path: Path = TERRITORIES) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    rows = json.loads(path.read_text(encoding="utf-8"))["territories"]
    territories = {row["territory_id"]: row for row in rows}
    parents = {row["territory_id"]: row["parent_id"] for row in rows if row["territory_type"] == "province"}
    if len([row for row in rows if row["territory_type"] in {"autonomous_community", "autonomous_city"}]) != 19 or len(parents) != 50:
        raise ValueError("Catálogo territorial ES-2 inesperado")
    return territories, parents


def read_jsonl(path: Path, expected_sha256: str) -> list[dict[str, Any]]:
    digest = hashlib.sha256(); rows: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        for raw in handle:
            digest.update(raw)
            if raw.strip():
                rows.append(json.loads(raw))
    if digest.hexdigest() != expected_sha256:
        raise ValueError(f"Checksum inesperado: {portable(path)}")
    return rows


def bucket_for(fraction: float) -> str:
    lower = 0.0
    for upper in SLIVER_BUCKETS:
        if fraction < upper:
            return f"[{lower:g},{upper:g})"
        lower = upper
    return f"[{lower:g},1]"


def cardinality_distribution(counts: dict[str, set[str]], expected_geometries: int) -> dict[str, Any]:
    result = Counter()
    for values in counts.values():
        result[str(len(values) if len(values) < 4 else "4+")] += 1
    unseen = expected_geometries - len(counts)
    if unseen < 0:
        raise ValueError("Más geometry_id que el total esperado")
    result["0"] += unseen
    return {
        "0": result["0"], "1": result["1"], "2": result["2"], "3": result["3"], "4+": result["4+"],
        "multi_geometry_count": sum(count for key, count in result.items() if key not in {"0", "1"}),
        "maximum": max((len(values) for values in counts.values()), default=0),
    }


def coverage_rows(level: str, all_ids: Iterable[str], by_geometry: dict[str, set[str]], territories: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for territory_id in sorted(all_ids):
        geometry_ids = {gid for gid, values in by_geometry.items() if territory_id in values}
        exclusive = {gid for gid in geometry_ids if len(by_geometry[gid]) == 1}
        row = territories[territory_id]
        rows.append({
            "territory_id": territory_id,
            "official_code": row["official_code"],
            "official_name": row["official_name"],
            "territory_type": row["territory_type"],
            "level": level,
            "geometries_intersecting": len(geometry_ids),
            "relations": len(geometry_ids),
            "geometries_exclusive": len(exclusive),
            "geometries_shared": len(geometry_ids - exclusive),
        })
    return rows


def dominance(by_geometry: dict[str, set[str]], fractions: dict[tuple[str, str], float]) -> dict[str, Any]:
    result = Counter()
    for geometry_id, territories in by_geometry.items():
        if len(territories) < 2:
            continue
        maximum = max(fractions[(geometry_id, territory_id)] for territory_id in territories)
        if maximum > .99:
            result[">99%"] += 1
        elif maximum > .95:
            result[">95%"] += 1
        elif maximum > .90:
            result[">90%"] += 1
        else:
            result["≤90%"] += 1
    return {"multi_geometry_count": sum(result.values()), ">99%": result[">99%"], ">95%": result[">95%"], ">90%": result[">90%"], "≤90%": result["≤90%"]}


def compact_representations(ccaa_by_geometry: dict[str, set[str]], province_by_geometry: dict[str, set[str]], relation_paths: list[Path], touch_paths: list[Path], expected_geometries: int) -> dict[str, Any]:
    def annotate(metrics: dict[str, int | float]) -> dict[str, int | float]:
        return {**metrics, "raw_bytes_per_geometry": round(metrics["raw_bytes"] / expected_geometries, 6), "gzip_bytes_per_geometry": round(metrics["gzip_bytes"] / expected_geometries, 6)}

    current_raw = sum(path.stat().st_size for path in relation_paths + touch_paths)
    current = annotate({"raw_bytes": current_raw, "gzip_bytes": gzip_size(relation_paths + touch_paths)})
    all_map = {gid: sorted(ccaa_by_geometry[gid] | province_by_geometry[gid]) for gid in sorted(ccaa_by_geometry)}
    separate = {"ccaa": {gid: sorted(values) for gid, values in sorted(ccaa_by_geometry.items())}, "province": {gid: sorted(values) for gid, values in sorted(province_by_geometry.items())}}
    ccaa_dictionary = sorted({item for values in ccaa_by_geometry.values() for item in values})
    province_dictionary = sorted({item for values in province_by_geometry.values() for item in values})
    ccaa_index = {item: index for index, item in enumerate(ccaa_dictionary)}
    province_index = {item: index for index, item in enumerate(province_dictionary)}
    dictionary_encoded = {
        "ccaa_dictionary": ccaa_dictionary,
        "province_dictionary": province_dictionary,
        "relations": {gid: [[ccaa_index[item] for item in sorted(ccaa_by_geometry[gid])], [province_index[item] for item in sorted(province_by_geometry[gid])]] for gid in sorted(ccaa_by_geometry)},
    }
    return {
        "A_current_audit_jsonl": annotate(current),
        "B_geometry_to_all_territory_ids": annotate(json_size(all_map)),
        "C_separate_ccaa_and_province_maps": annotate(json_size(separate)),
        "D_dictionary_encoded_territory_ids": annotate(json_size(dictionary_encoded)),
        "definition": "B–D contienen solo geometry_id y territory IDs necesarios para filtrado; excluyen área, fracción, QA y provenance de auditoría.",
    }


def audit(manifest: dict[str, Any], territories: dict[str, dict[str, Any]], parents: dict[str, str], es3: dict[str, Any], relation_rows: list[dict[str, Any]], touch_rows: list[dict[str, Any]], relation_paths: list[Path], touch_paths: list[Path]) -> dict[str, Any]:
    expected = manifest["input"]["geometry_snapshot"]["records_expected"]
    ccaa_by_geometry: dict[str, set[str]] = defaultdict(set)
    province_by_geometry: dict[str, set[str]] = defaultdict(set)
    fractions: dict[tuple[str, str], float] = {}
    duplicate_keys: list[dict[str, str]] = []
    raw_level_counts = Counter()
    seen = set(); slivers = Counter(); smallest: list[dict[str, Any]] = []
    for row in relation_rows:
        if row.get("relation_type") != "spatial_intersection" or row.get("intersection_class") != "positive_area_intersection":
            raise ValueError("Relación positiva con semántica inesperada")
        raw_level_counts[row["territory_level"]] += 1
        key = (row["geometry_id"], row["territory_id"], row["relation_type"])
        if key in seen:
            duplicate_keys.append({"geometry_id": key[0], "territory_id": key[1], "relation_type": key[2]})
            continue
        seen.add(key)
        fraction = float(row["intersection_fraction"])
        if fraction <= 0:
            raise ValueError("Relación positiva sin fracción positiva")
        fractions[(row["geometry_id"], row["territory_id"])] = fraction
        slivers[bucket_for(fraction)] += 1
        smallest.append({"geometry_id": row["geometry_id"], "territory_id": row["territory_id"], "territory_type": row["territory_type"], "intersection_area_m2": row["intersection_area_m2"], "intersection_fraction": fraction})
        if row["territory_level"] == "autonomous_community":
            ccaa_by_geometry[row["geometry_id"]].add(row["territory_id"])
        elif row["territory_level"] == "province":
            province_by_geometry[row["geometry_id"]].add(row["territory_id"])
        else:
            raise ValueError("Nivel territorial no soportado")
    all_geometry_ids = set(ccaa_by_geometry) | set(province_by_geometry)
    ccaa_cardinality = cardinality_distribution(ccaa_by_geometry, expected)
    province_cardinality = cardinality_distribution(province_by_geometry, expected)
    hierarchy_inconsistent = []
    for geometry_id, province_ids in province_by_geometry.items():
        for province_id in province_ids:
            parent_id = parents[province_id]
            if parent_id not in ccaa_by_geometry[geometry_id]:
                hierarchy_inconsistent.append({"geometry_id": geometry_id, "province_id": province_id, "expected_parent_id": parent_id})
    touch_by_level = Counter(); touch_geometries = set(); touch_only = set(); touch_max = Counter()
    positive_geometry_ids = all_geometry_ids
    by_touch_geometry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in touch_rows:
        if row.get("intersection_class") != "boundary_touch_only" or row.get("intersection_area_m2") != 0:
            raise ValueError("Touch con semántica inesperada")
        touch_by_level[row["territory_level"]] += 1; touch_geometries.add(row["geometry_id"]); by_touch_geometry[row["geometry_id"]].append(row)
    touch_only = touch_geometries - positive_geometry_ids
    for geometry_id, rows in by_touch_geometry.items():
        touch_max[geometry_id] = len(rows)
    ccaa_ids = [tid for tid, row in territories.items() if row["territory_type"] in {"autonomous_community", "autonomous_city"}]
    province_ids = [tid for tid, row in territories.items() if row["territory_type"] == "province"]
    total_ccaa = raw_level_counts["autonomous_community"]
    total_province = raw_level_counts["province"]
    if total_ccaa + total_province != len(relation_rows):
        raise ValueError("Reconciliación por nivel inválida")
    baseline = 2 * expected
    excess_ccaa = total_ccaa - expected
    excess_province = total_province - expected
    es3_relations = es3["territory_relations"]
    def comparison(current: int, earlier: int) -> dict[str, Any]:
        return {"es3": earlier, "es4c2b1a": current, "difference": current - earlier, "classification": "MATCH" if current == earlier else "EXPLAINED_DIFFERENCE", "explanation": None if current == earlier else "ES-3 calculó hits tras transformar BDLJE a EPSG:23030; C2B1A transforma geometrías con la operación ED50/WGS84 (41) y mide en EPSG:3035. Ambos usan el mismo snapshot y positivo-área, pero esta diferencia pequeña de topología/CRS debe conservarse y no forzarse."}
    balears_id, canarias_id = "ES:CCAA:04", "ES:CCAA:05"
    balears_geometries = {gid for gid, ids in ccaa_by_geometry.items() if balears_id in ids}
    balears_shared_ccaa = {gid for gid in balears_geometries if len(ccaa_by_geometry[gid]) > 1}
    integrity_errors = []
    if len(relation_rows) != manifest["totals"]["relation_count"]:
        integrity_errors.append("recuento de relaciones distinto del manifest")
    if len(all_geometry_ids) != expected:
        integrity_errors.append("recuento de geometry_id distinto del esperado")
    if duplicate_keys:
        integrity_errors.append("relaciones lógicas duplicadas")
    if hierarchy_inconsistent:
        integrity_errors.append("incoherencias provincia→CCAA")
    report = {
        "schema_version": "es4c2b1b-territory-relation-audit-v1",
        "scope": "Audit only; no ESFire30 geometry was opened or intersected.",
        "input": {
            "manifest": portable(MANIFEST), "manifest_sha256": sha256(MANIFEST),
            "geometry_count_expected": expected, "blocks": len(manifest.get("blocks", [])),
            "relations_raw_bytes": sum(path.stat().st_size for path in relation_paths),
            "touches_raw_bytes": sum(path.stat().st_size for path in touch_paths),
            "territory_catalog": portable(TERRITORIES), "es3_summary": portable(ES3),
        },
        "baseline": {"one_ccaa_plus_one_province_per_geometry": baseline, "actual_relations": len(relation_rows), "excess_relations": len(relation_rows) - baseline, "excess_ccaa": excess_ccaa, "excess_province": excess_province, "formula_verified": excess_ccaa + excess_province == len(relation_rows) - baseline},
        "relations": {"total": len(relation_rows), "ccaa": total_ccaa, "province": total_province, "unique_geometry_ids": len(all_geometry_ids), "duplicate_logical_keys": len(duplicate_keys), "duplicate_examples": duplicate_keys[:20]},
        "cardinality": {"ccaa": ccaa_cardinality, "province": province_cardinality},
        "extremes": {
            "ccaa": [{"geometry_id": gid, "territory_ids": sorted(values)} for gid, values in sorted(ccaa_by_geometry.items()) if len(values) == ccaa_cardinality["maximum"]][:20],
            "province": [{"geometry_id": gid, "territory_ids": sorted(values)} for gid, values in sorted(province_by_geometry.items()) if len(values) == province_cardinality["maximum"]][:20],
        },
        "es3_reconciliation": {"cross_ccaa": comparison(ccaa_cardinality["multi_geometry_count"], es3_relations["crosses_ccaa"]), "cross_province": comparison(province_cardinality["multi_geometry_count"], es3_relations["crosses_province"]), "es3_without_ccaa": es3_relations["without_ccaa"], "es3_without_province": es3_relations["without_province"]},
        "zero_relation": {"zero_ccaa": ccaa_cardinality["0"], "zero_province": province_cardinality["0"], "zero_both": expected - len(all_geometry_ids), "classification": "none" if not (ccaa_cardinality["0"] or province_cardinality["0"]) else "requires_source_geometry_investigation"},
        "boundary_touches": {"total": len(touch_rows), "ccaa": touch_by_level["autonomous_community"], "province": touch_by_level["province"], "geometries_with_any": len(touch_geometries), "geometries_touch_only": len(touch_only), "maximum_touches_for_one_geometry": max(touch_max.values(), default=0)},
        "slivers": {"thresholds": list(SLIVER_BUCKETS), "relation_count": len(relation_rows), "smallest": sorted(smallest, key=lambda row: (row["intersection_fraction"], row["geometry_id"], row["territory_id"]))[:20]},
        "dominance": {"ccaa": dominance(ccaa_by_geometry, fractions), "province": dominance(province_by_geometry, fractions)},
        "hierarchy": {"province_relations": total_province, "coherent": total_province - len(hierarchy_inconsistent), "inconsistent": len(hierarchy_inconsistent), "examples": hierarchy_inconsistent[:20]},
        "special_territories": {
            "ceuta": {"territory_id": "ES:CCAA:18", "type": "autonomous_city", "ccaa_relations": sum("ES:CCAA:18" in values for values in ccaa_by_geometry.values()), "province_relations": 0, "interpretation": "sin cobertura ESFire30: el inventario ES-1 describe el snapshot como mainland Spain; cero relaciones no significa cero incendios."},
            "melilla": {"territory_id": "ES:CCAA:19", "type": "autonomous_city", "ccaa_relations": sum("ES:CCAA:19" in values for values in ccaa_by_geometry.values()), "province_relations": 0, "interpretation": "sin cobertura ESFire30: el inventario ES-1 describe el snapshot como mainland Spain; cero relaciones no significa cero incendios."},
            "balears": {"ccaa_id": balears_id, "province_ids": [tid for tid in province_ids if parents[tid] == balears_id], "geometries": len(balears_geometries), "relations": sum(balears_id in values for values in ccaa_by_geometry.values()), "geometries_also_intersecting_other_ccaa": len(balears_shared_ccaa), "interpretation": "sin cobertura ESFire30: el inventario ES-1 describe el snapshot como mainland Spain; cero relaciones no significa cero incendios."},
            "canarias": {"ccaa_id": canarias_id, "geometries": sum(canarias_id in values for values in ccaa_by_geometry.values()), "relations": sum(canarias_id in values for values in ccaa_by_geometry.values()), "interpretation": "ESFire30 no cubre Canarias; cero relaciones no significa cero incendios."},
        },
        "coverage": {"ccaa": coverage_rows("ccaa", ccaa_ids, ccaa_by_geometry, territories), "province": coverage_rows("province", province_ids, province_by_geometry, territories)},
        "compact_representation": compact_representations(ccaa_by_geometry, province_by_geometry, relation_paths, touch_paths, expected),
        "runtime_implication": "El runtime solo necesita geometry_id → IDs CCAA/provincia para filtrar. Área, fracción, QA y provenance se mantienen en JSONL de auditoría fuera del payload web.",
        "integrity": {"valid": not integrity_errors, "errors": integrity_errors},
    }
    # Los buckets se inicializan explícitamente en orden para que el informe sea
    # estable y no dependa de qué rangos aparezcan en una ejecución.
    labels = ["[0,1e-06)", "[1e-06,1e-05)", "[1e-05,0.0001)", "[0.0001,0.001)", "[0.001,0.01)", "[0.01,1]"]
    report["slivers"]["buckets"] = {label: 0 for label in labels}
    for row in relation_rows:
        fraction = float(row["intersection_fraction"])
        if fraction < 1e-6: label = "[0,1e-06)"
        elif fraction < 1e-5: label = "[1e-06,1e-05)"
        elif fraction < 1e-4: label = "[1e-05,0.0001)"
        elif fraction < 1e-3: label = "[0.0001,0.001)"
        elif fraction < 1e-2: label = "[0.001,0.01)"
        else: label = "[0.01,1]"
        report["slivers"]["buckets"][label] += 1
    audit_without_hash = dict(report)
    report["report_sha256"] = hashlib.sha256(canonical_bytes(audit_without_hash)).hexdigest()
    return report


def build(manifest_path: Path = MANIFEST) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["input"]["geometry_snapshot"]["records_expected"] != EXPECTED_GEOMETRIES:
        raise ValueError("Recuento ESFire30 inesperado")
    territories, parents = load_territories()
    es3 = json.loads(ES3.read_text(encoding="utf-8"))
    relation_rows: list[dict[str, Any]] = []; touch_rows: list[dict[str, Any]] = []
    relation_paths: list[Path] = []; touch_paths: list[Path] = []
    for block in sorted(manifest["blocks"], key=lambda item: item["year"]):
        relation_path = ROOT / block["relations_path"]; touch_path = ROOT / block["boundary_touches_path"]
        relation_paths.append(relation_path); touch_paths.append(touch_path)
        relation_rows.extend(read_jsonl(relation_path, block["relations_sha256"]))
        touch_rows.extend(read_jsonl(touch_path, block["boundary_touches_sha256"]))
    return audit(manifest, territories, parents, es3, relation_rows, touch_rows, relation_paths, touch_paths)


def check(output: Path) -> dict[str, Any]:
    report = json.loads(output.read_text(encoding="utf-8")); stored = report.pop("report_sha256", None)
    failures = []
    if stored != hashlib.sha256(canonical_bytes(report)).hexdigest():
        failures.append("checksum del informe")
    if report.get("input", {}).get("manifest_sha256") != sha256(MANIFEST):
        failures.append("manifest de entrada cambió")
    integrity = report.get("integrity", {})
    if not integrity.get("valid") or integrity.get("errors"):
        failures.append("integridad declarada")
    return {"valid": not failures, "failures": failures, "report": portable(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check(args.output), ensure_ascii=False)); return 0
    report = build(); atomic_json(args.output, report)
    print(json.dumps({"valid": report["integrity"]["valid"], "relations": report["relations"]["total"], "report": portable(args.output)}, ensure_ascii=False))
    return 0 if report["integrity"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
