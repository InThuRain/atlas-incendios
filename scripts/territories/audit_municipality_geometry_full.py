#!/usr/bin/env python3
"""Audita y deriva shards municipales BDLJE actuales, sin integrar runtime.

ES-4C2A3B trabaja exclusivamente sobre el GeoJSON nacional ya adquirido en
ES-4C2A3A. El lector es streaming para no materializar sus coordenadas dos
veces en memoria. Las geometrías canónicas se conservan sin simplificación y
se distribuyen en shards locales por provincia o ciudad autónoma.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_municipalities as a3a  # noqa: E402


SOURCE = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/municipalities/municipality-level.geojson"
SNAPSHOT = ROOT / "data/territories/spain/territories-2026-01-01.json"
SHARDS_DIR = ROOT / "data/derived/spain/es4c2a3/municipalities"
CATALOG = ROOT / "data/territories/spain/municipality_catalog_2026-08-29.json"
AUDIT = ROOT / "data/audit/territories/es4c2a3b_municipal_geometry_full_audit.json"
SOURCE_BYTES = 147400597
SOURCE_SHA256 = "ca052a7592c45c03ea765e12e706652741964b80e8acd34e79978c31e9fe9dfc"
EXPECTED_SOURCE_FEATURES = 8213
EXPECTED_MUNICIPALITIES = 8132


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gzip_size(path: Path) -> int:
    target = path.with_suffix(path.suffix + ".gzip-size.tmp")
    with path.open("rb") as source, gzip.GzipFile(target, "wb", mtime=0) as output:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            output.write(block)
    size = target.stat().st_size
    target.unlink()
    return size


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def iter_features(path: Path) -> Iterator[dict[str, Any]]:
    """Yield FeatureCollection features without parsing all coordinates at once."""
    decoder = json.JSONDecoder()
    buffer = ""
    found_features = False
    finished = False
    with path.open("r", encoding="utf-8") as source:
        while not finished:
            chunk = source.read(1024 * 1024)
            if chunk:
                buffer += chunk
            elif not buffer:
                break
            if not found_features:
                marker = '"features":['
                index = buffer.find(marker)
                if index < 0:
                    if not chunk:
                        raise ValueError("FeatureCollection sin matriz features")
                    buffer = buffer[-len(marker):]
                    continue
                buffer = buffer[index + len(marker):]
                found_features = True
            progressed = True
            while progressed:
                progressed = False
                buffer = buffer.lstrip()
                if buffer.startswith(","):
                    buffer = buffer[1:]
                    progressed = True
                    continue
                if buffer.startswith("]"):
                    finished = True
                    break
                if not buffer:
                    break
                try:
                    feature, position = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break
                if not isinstance(feature, dict):
                    raise ValueError("Feature BDLJE no es objeto JSON")
                yield feature
                buffer = buffer[position:]
                progressed = True
            if not chunk and not finished:
                raise ValueError("FeatureCollection truncada")
    if not found_features or not finished:
        raise ValueError("FeatureCollection municipal incompleta")


def geometry_parts(geometry: Any) -> int:
    return len(geometry.geoms) if geometry.geom_type == "MultiPolygon" else 1


def geometry_vertices(geometry: Any) -> int:
    polygons = geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry]
    return sum(len(polygon.exterior.coords) + sum(len(ring.coords) for ring in polygon.interiors) for polygon in polygons)


def percentile(values: list[int], percent: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * percent)]


def source_parts(feature: dict[str, Any]) -> tuple[str, str, str] | None:
    return a3a.national_code_parts((feature.get("properties") or {}).get("nationalcode"))


def non_municipal_label(name: str) -> str:
    """Inventory literal name prefixes only; not an official new taxonomy."""
    normalized = name.strip().casefold()
    for prefix, label in (
        ("comunidad", "literal_prefix:Comunidad"),
        ("facería", "literal_prefix:Facería"),
        ("faceria", "literal_prefix:Faceria"),
        ("parzonería", "literal_prefix:Parzonería"),
        ("parzoneria", "literal_prefix:Parzoneria"),
        ("mancomunidad", "literal_prefix:Mancomunidad"),
        ("ledanía", "literal_prefix:Ledanía"),
        ("ledania", "literal_prefix:Ledania"),
        ("monte", "literal_prefix:Monte"),
    ):
        if normalized.startswith(prefix):
            return label
    return "literal_prefix:other"


def shard_key(ccaa: str, province: str) -> tuple[str, str, str | None]:
    if province in {"51", "52"}:
        return (f"ES:CCAA:{ccaa}", f"ES-CCAA-{ccaa}", None)
    return (f"ES:PROV:{province}", f"ES-PROV-{province}", f"ES:PROV:{province}")


def source_validation(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != SOURCE_BYTES:
        raise ValueError(f"Tamaño municipal fuente inesperado: {path.stat().st_size} != {SOURCE_BYTES}")
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Checksum inesperado del GeoJSON municipal adquirido")


def municipality_lookup(snapshot_path: Path) -> dict[str, dict[str, Any]]:
    return a3a.municipal_snapshot(snapshot_path)


def shard_feature(feature: dict[str, Any], territory: dict[str, Any], ccaa: str, province: str) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    asset_territory_id, _filename, province_id = shard_key(ccaa, province)
    return {
        "type": "Feature",
        "id": territory["territory_id"],
        "properties": {
            "municipality_id": territory["territory_id"],
            "province_id": province_id,
            "autonomous_community_id": f"ES:CCAA:{ccaa}",
            "official_name": territory["official_name"],
        },
        "geometry": feature["geometry"],
        "_asset_id": f"municipalities:{asset_territory_id}",
        "_source_code": str(properties.get("nationalcode")),
    }


def compact_feature(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def write_shard(lines_path: Path, shard_path: Path) -> tuple[int, str]:
    rows = lines_path.read_text(encoding="utf-8").splitlines()
    rows.sort(key=lambda row: row.partition("\t")[0])
    digest = hashlib.sha256()
    total = 0
    temporary = shard_path.with_suffix(".geojson.part")
    with temporary.open("wb") as target:
        def write(data: bytes) -> None:
            nonlocal total
            target.write(data); digest.update(data); total += len(data)
        write(b'{"type":"FeatureCollection","features":[')
        for index, row in enumerate(rows):
            if index:
                write(b",")
            write(row.partition("\t")[2].encode("utf-8"))
        write(b"]}\n")
    os.replace(temporary, shard_path)
    lines_path.unlink()
    return total, digest.hexdigest()


class CountingSink(io.RawIOBase):
    def __init__(self) -> None:
        self.count = 0

    def writable(self) -> bool:
        return True

    def write(self, data: bytes) -> int:
        self.count += len(data)
        return len(data)


def virtual_feature_collection_size(paths: list[Path]) -> dict[str, int]:
    """Measure concatenated 0 m shards without retaining another national copy."""
    prefix = b'{"type":"FeatureCollection","features":['
    suffix = b"]}\n"
    sink = CountingSink()
    raw = 0
    with gzip.GzipFile(fileobj=sink, mode="wb", mtime=0) as compressed:
        def write(data: bytes) -> None:
            nonlocal raw
            raw += len(data); compressed.write(data)
        write(prefix)
        for index, path in enumerate(paths):
            data = path.read_bytes()
            if not data.startswith(prefix) or not data.endswith(suffix):
                raise ValueError(f"Shard GeoJSON inesperado: {path}")
            body = data[len(prefix):-len(suffix)]
            if index:
                write(b",")
            write(body)
        write(suffix)
    return {"raw_bytes": raw, "gzip_bytes": sink.count}


def partition_comparison(shard_rows: list[dict[str, Any]], snapshot_path: Path, scope: str = "all") -> dict[str, Any]:
    all_territories = json.loads(snapshot_path.read_text(encoding="utf-8"))["territories"]
    province_parents = {row["territory_id"]: row["parent_id"] for row in all_territories if row.get("territory_type") == "province"}
    ccaa_shards: dict[str, list[Path]] = defaultdict(list)
    for row in shard_rows:
        parent = row["territory_id"] if row["territory_id"].startswith("ES:CCAA:") else province_parents[row["territory_id"]]
        ccaa_shards[parent].append(ROOT / row["path"])
    output: dict[str, Any] = {
        "province_or_autonomous_city_geojson_0m": {"raw_bytes": sum(row["raw_bytes"] for row in shard_rows), "gzip_bytes": sum(row["gzip_bytes"] for row in shard_rows), "assets": len(shard_rows)},
        "administrative_pmtiles": {"measured": False, "reason": "No administrative PMTiles was built: province shards already test the selected on-demand delivery strategy; PMTiles remains a future option for continuous nationwide municipal browsing."},
    }
    if scope in {"all", "national"}:
        output["national_single_geojson_0m"] = virtual_feature_collection_size([ROOT / row["path"] for row in sorted(shard_rows, key=lambda item: item["territory_id"])])
    if scope in {"all", "ccaa"}:
        output["ccaa_geojson_0m"] = {territory_id: virtual_feature_collection_size(sorted(paths)) for territory_id, paths in sorted(ccaa_shards.items())}
    return output


def build(source_path: Path, snapshot_path: Path, shards_dir: Path, catalog_path: Path, audit_path: Path, generated_at: str) -> dict[str, Any]:
    source_validation(source_path)
    municipalities = municipality_lookup(snapshot_path)
    shards_dir.mkdir(parents=True, exist_ok=True)
    lines_dir = shards_dir / ".lines"; lines_dir.mkdir(parents=True, exist_ok=True)
    for stale in lines_dir.glob("*.jsonl"):
        stale.unlink()
    handles: dict[str, Any] = {}
    shard_stats: dict[str, dict[str, Any]] = {}
    classifications = Counter()
    non_municipal_types = Counter()
    non_municipal_examples: list[dict[str, str]] = []
    hierarchy_mismatches: list[dict[str, str]] = []
    invalid: list[dict[str, str]] = []
    empty: list[dict[str, str]] = []
    null: list[dict[str, str]] = []
    seen: set[str] = set()
    catalog_rows: list[dict[str, Any]] = []
    all_vertices: list[int] = []
    controls: dict[str, dict[str, Any]] = {}
    source_features = 0
    names_to_control = {
        "Llívia": "Llívia", "Condado de Treviño": "Condado de Treviño",
        "La Puebla de Arganzón": "La Puebla de Arganzón", "Ademuz": "Ademuz",
        "Llocnou de la Corona": "Llocnou de la Corona",
    }
    try:
        for feature in iter_features(source_path):
            source_features += 1
            properties = feature.get("properties") or {}
            parsed = source_parts(feature)
            name = str(properties.get("nameunit") or "")
            if parsed is None:
                classifications["AMBIGUOUS"] += 1
                continue
            ccaa, province, code = parsed
            territory = municipalities.get(code)
            if territory is None:
                label = "NON_MUNICIPAL_UNIT" if code.startswith("53") else "UNMATCHED_SOURCE"
                classifications[label] += 1
                if label == "NON_MUNICIPAL_UNIT":
                    kind = non_municipal_label(name); non_municipal_types[kind] += 1
                    if len(non_municipal_examples) < 20:
                        non_municipal_examples.append({"nationalcode": str(properties.get("nationalcode")), "nameunit": name, "inventory_label": kind})
                continue
            expected_parent = f"ES:CCAA:{ccaa}" if province in {"51", "52"} else f"ES:PROV:{province}"
            if territory["parent_id"] != expected_parent:
                hierarchy_mismatches.append({"municipality_id": territory["territory_id"], "source_parent": expected_parent, "es2_parent": territory["parent_id"]})
            classifications["MATCHED_CURRENT"] += 1
            municipality_id = territory["territory_id"]
            if municipality_id in seen:
                raise ValueError(f"Municipio ES-2 duplicado en BDLJE: {municipality_id}")
            seen.add(municipality_id)
            geometry_data = feature.get("geometry")
            if geometry_data is None:
                null.append({"municipality_id": municipality_id, "source_code": str(properties.get("nationalcode"))}); continue
            geometry = shape(geometry_data)
            if geometry.is_empty:
                empty.append({"municipality_id": municipality_id, "source_code": str(properties.get("nationalcode"))}); continue
            if geometry.geom_type not in {"Polygon", "MultiPolygon"} or not geometry.is_valid:
                invalid.append({"municipality_id": municipality_id, "source_code": str(properties.get("nationalcode")), "geometry_type": geometry.geom_type}); continue
            asset_territory_id, filename, province_id = shard_key(ccaa, province)
            stat = shard_stats.setdefault(asset_territory_id, {
                "asset_id": f"municipalities:{asset_territory_id}", "territory_id": asset_territory_id,
                "filename": f"{filename}.geojson", "municipality_count": 0, "feature_count": 0,
                "vertices": 0, "geometry_types": Counter(), "multipart_features": 0,
                "largest_municipality": None,
            })
            row = shard_feature(feature, territory, ccaa, province)
            lines_path = lines_dir / f"{filename}.jsonl"
            if asset_territory_id not in handles:
                handles[asset_territory_id] = lines_path.open("a", encoding="utf-8")
            handles[asset_territory_id].write(f"{municipality_id}\t" + canonical_json(compact_feature(row)).decode("utf-8") + "\n")
            vertices = geometry_vertices(geometry)
            parts = geometry_parts(geometry)
            stat["municipality_count"] += 1; stat["feature_count"] += 1; stat["vertices"] += vertices
            stat["geometry_types"][geometry.geom_type] += 1
            if parts > 1: stat["multipart_features"] += 1
            candidate = {"municipality_id": municipality_id, "official_name": territory["official_name"], "vertices": vertices, "geometry_type": geometry.geom_type, "geometry_parts": parts}
            if stat["largest_municipality"] is None or vertices > stat["largest_municipality"]["vertices"]:
                stat["largest_municipality"] = candidate
            bounds = [float(value) for value in geometry.bounds]
            catalog_rows.append({"municipality_id": municipality_id, "province_id": province_id, "autonomous_community_id": f"ES:CCAA:{ccaa}", "official_name": territory["official_name"], "bounds": bounds, "asset_id": row["_asset_id"]})
            all_vertices.append(vertices)
            if name in names_to_control:
                controls[names_to_control[name]] = {**candidate, "bounds": bounds, "asset_id": row["_asset_id"]}
    finally:
        for handle in handles.values():
            handle.close()
    if source_features != EXPECTED_SOURCE_FEATURES:
        raise ValueError(f"Feature count fuente inesperado: {source_features}")
    if classifications != Counter({"MATCHED_CURRENT": EXPECTED_MUNICIPALITIES, "NON_MUNICIPAL_UNIT": 81}):
        raise ValueError(f"Crosswalk municipal inesperado: {dict(classifications)}")
    if len(seen) != EXPECTED_MUNICIPALITIES or set(row["municipality_id"].split(":")[-1] for row in catalog_rows) != set(municipalities):
        raise ValueError("Municipios ES-2 no reconciliados exactamente")
    if hierarchy_mismatches or invalid or empty or null:
        raise ValueError(json.dumps({"hierarchy_mismatches": hierarchy_mismatches, "invalid": invalid, "empty": empty, "null": null}, ensure_ascii=False))
    if set(controls) != set(names_to_control.values()):
        raise ValueError(f"Faltan controles dirigidos: {sorted(set(names_to_control.values()) - set(controls))}")
    if len(shard_stats) != 52:
        raise ValueError(f"Shards esperados: 50 provincias + 2 ciudades autónomas; obtenidos {len(shard_stats)}")
    shard_rows = []
    for territory_id, stat in sorted(shard_stats.items()):
        path = shards_dir / stat["filename"]
        raw_bytes, digest = write_shard(lines_dir / (Path(stat["filename"]).stem + ".jsonl"), path)
        stat["geometry_types"] = dict(sorted(stat["geometry_types"].items()))
        stat.update({"path": display_path(path), "raw_bytes": raw_bytes, "gzip_bytes": gzip_size(path), "sha256": digest})
        shard_rows.append(stat)
    lines_dir.rmdir()
    partition_sizes = partition_comparison(shard_rows, snapshot_path)
    catalog_rows.sort(key=lambda row: row["municipality_id"])
    catalog = {"schema_version": "es4c2a3b-municipality-catalog-v1", "semantics": "Current BDLJE administrative bounds only; not historical municipality geometry.", "municipalities": catalog_rows}
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_bytes(canonical_json(catalog) + b"\n")
    totals = {
        "municipalities": len(catalog_rows), "features": sum(row["feature_count"] for row in shard_rows),
        "shards": len(shard_rows), "vertices": sum(row["vertices"] for row in shard_rows),
        "raw_bytes": sum(row["raw_bytes"] for row in shard_rows), "gzip_bytes": sum(row["gzip_bytes"] for row in shard_rows),
    }
    audit = {
        "schema_version": "es4c2a3b-municipal-geometry-full-audit-v1", "phase": "ES-4C2A3B", "generated_at": generated_at,
        "source": {"path": display_path(source_path), "bytes": source_path.stat().st_size, "sha256": sha256(source_path), "features": source_features, "format": "GeoJSON FeatureCollection", "organization": "IGN / CNIG", "product": "BDLJE / Límites y Unidades Administrativas Actuales", "license": "CC BY 4.0", "attribution": "Obra derivada de BDLJE CC-BY 4.0 ign.es", "web_crs": "GeoJSON CRS84 / EPSG:4326-compatible longitude-latitude"},
        "reconciliation": {"source_features": source_features, "classification": dict(sorted(classifications.items())), "logical_municipalities": len(catalog_rows), "duplicate_municipalities": 0, "hierarchy_mismatches": hierarchy_mismatches},
        "geometry": {"polygon_features": sum(row["geometry_types"].get("Polygon", 0) for row in shard_rows), "multipolygon_features": sum(row["geometry_types"].get("MultiPolygon", 0) for row in shard_rows), "null": len(null), "empty": len(empty), "invalid": len(invalid), "vertices_per_municipality": {"min": min(all_vertices), "median": percentile(all_vertices, .5), "p95": percentile(all_vertices, .95), "max": max(all_vertices), "total": sum(all_vertices)}},
        "shards_0m": {"format": "GeoJSON FeatureCollection", "geometry_transformation": "select attributes only; source geometry retained without simplification", "totals": totals, "by_asset": shard_rows, "top_10_raw": sorted(shard_rows, key=lambda row: (-row["raw_bytes"], row["territory_id"]))[:10], "top_10_gzip": sorted(shard_rows, key=lambda row: (-row["gzip_bytes"], row["territory_id"]))[:10], "top_10_vertices": sorted(shard_rows, key=lambda row: (-row["vertices"], row["territory_id"]))[:10], "top_10_municipalities": sorted(shard_rows, key=lambda row: (-row["municipality_count"], row["territory_id"]))[:10]},
        "partition_comparison": partition_sizes,
        "catalog": {"path": display_path(catalog_path), "sha256": sha256(catalog_path), "records": len(catalog_rows), "raw_bytes": catalog_path.stat().st_size, "gzip_bytes": gzip_size(catalog_path), "bytes_per_municipality_raw": catalog_path.stat().st_size / len(catalog_rows), "bytes_per_municipality_gzip": gzip_size(catalog_path) / len(catalog_rows), "fields": ["municipality_id", "province_id", "autonomous_community_id", "official_name", "bounds", "asset_id"]},
        "controls": controls,
        "non_municipal_units": {"count": 81, "name_prefix_inventory_not_official_taxonomy": dict(sorted(non_municipal_types.items())), "examples": non_municipal_examples},
        "historical_semantics": "BDLJE municipal geometry is a current administrative boundary. An EGIF municipality_id is a documentary link to a current canonical municipality when resolvable; neither proves the historical event lies inside the current polygon.",
        "delivery_recommendation": "GeoJSON 0 m by province on demand plus the lightweight national catalogue; do not load a national municipal GeoJSON initially. PMTiles remains a future option only for continuous nationwide municipal browsing.",
        "esfire30_future_note": "Do not calculate ESFire30→municipality here and do not use mun_1..mun_3. A future relation may have high cardinality and needs an inverse index, local tiles, or spatial query design.",
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_bytes(canonical_json(audit) + b"\n")
    return audit


def refresh_partition_sizes(snapshot_path: Path, audit_path: Path, scope: str) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    current = audit.get("partition_comparison") or {}
    measured = partition_comparison(audit["shards_0m"]["by_asset"], snapshot_path, scope)
    current.update(measured)
    audit["partition_comparison"] = current
    audit_path.write_bytes(canonical_json(audit) + b"\n")
    return audit


def validate(source_path: Path, shards_dir: Path, catalog_path: Path, audit_path: Path) -> dict[str, Any]:
    source_validation(source_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    rec = audit["reconciliation"]
    if rec["source_features"] != EXPECTED_SOURCE_FEATURES or rec["logical_municipalities"] != EXPECTED_MUNICIPALITIES:
        raise ValueError("Reconciliación de auditoría incorrecta")
    if rec["classification"] != {"MATCHED_CURRENT": 8132, "NON_MUNICIPAL_UNIT": 81} or rec["hierarchy_mismatches"]:
        raise ValueError("Clasificación municipal inesperada")
    shard_rows = audit["shards_0m"]["by_asset"]
    ids = set()
    for row in shard_rows:
        path = ROOT / row["path"]
        if not path.is_file() or sha256(path) != row["sha256"] or path.stat().st_size != row["raw_bytes"]:
            raise ValueError(f"Shard municipal inválido: {row['territory_id']}")
        collection = json.loads(path.read_text(encoding="utf-8"))
        feature_ids = [feature.get("properties", {}).get("municipality_id") for feature in collection.get("features", [])]
        if len(feature_ids) != row["municipality_count"] or len(feature_ids) != len(set(feature_ids)):
            raise ValueError(f"IDs municipales inesperados: {row['territory_id']}")
        if ids & set(feature_ids):
            raise ValueError("Municipio duplicado entre shards")
        ids.update(feature_ids)
    if len(ids) != EXPECTED_MUNICIPALITIES:
        raise ValueError("Total de municipios en shards incorrecto")
    if not catalog_path.is_file() or sha256(catalog_path) != audit["catalog"]["sha256"]:
        raise ValueError("Catálogo municipal inválido")
    return {"valid": True, "source_features": EXPECTED_SOURCE_FEATURES, "municipalities": len(ids), "shards": len(shard_rows), "raw_bytes": audit["shards_0m"]["totals"]["raw_bytes"], "gzip_bytes": audit["shards_0m"]["totals"]["gzip_bytes"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--shards-dir", type=Path, default=SHARDS_DIR)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=AUDIT)
    parser.add_argument("--generated-at", default="2026-08-29T00:00:00Z")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-partition-sizes", action="store_true", help="mide A/B/C sobre shards existentes sin releer el raw nacional")
    parser.add_argument("--partition-scope", choices=("all", "national", "ccaa"), default="all")
    args = parser.parse_args()
    if args.check:
        result = validate(args.source, args.shards_dir, args.catalog, args.output)
        print(json.dumps(result, ensure_ascii=False)); return 0
    if args.refresh_partition_sizes:
        result = refresh_partition_sizes(args.snapshot, args.output, args.partition_scope)
        print(json.dumps({"valid": True, "output": display_path(args.output), "partition_comparison": result["partition_comparison"]}, ensure_ascii=False)); return 0
    result = build(args.source, args.snapshot, args.shards_dir, args.catalog, args.output, args.generated_at)
    print(json.dumps({"valid": True, "municipalities": result["reconciliation"]["logical_municipalities"], "shards": result["shards_0m"]["totals"]["shards"], "output": display_path(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
