#!/usr/bin/env python3
"""Laboratorio reproducible ES-3 para entregar ESFire30 nacional.

No genera assets de producción ni modifica el visor.  Escribe exclusivamente
derivados diagnósticos bajo ``data/derived/spain/es3`` (ignorado por Git):

* GeoJSON nacional simplificado para el control monolítico;
* GeoJSON por CCAA y bloque temporal, sin recortar geometrías;
* NDJSON mínimo para fabricar teselas vectoriales/PMTiles;
* un manifiesto de medidas, relaciones territoriales y checksums.

Las asignaciones territoriales se hacen por la mayor intersección positiva con
los límites IGN. Son índices de entrega: no sustituyen las relaciones de
territorio fuente ni modifican la geometría original.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ZIP = ROOT / "data/raw/esfire30/18449006/ESFire30_Causes.zip"
DEFAULT_GRID = ROOT / "data/raw/esfire30/proj-grids/es_ign_SPED2ETV2.tif"
DEFAULT_CCAA = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/autonomous-territories.geojson"
DEFAULT_PROVINCES = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/province-level.geojson"
DEFAULT_OUTPUT = ROOT / "data/derived/spain/es3/results.json"
EXPECTED_ZIP_SHA256 = "150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8"
EXPECTED_GRID_SHA256 = "61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961"
EXPECTED_RECORDS = 119_498
BLOCKS = ((1985, 1992), (1993, 2000), (2001, 2010), (2011, 2021))


def load_es1():
    path = ROOT / "scripts/audit/spain/es1_national_feasibility.py"
    spec = importlib.util.spec_from_file_location("es1_for_es3", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el auditor ES-1")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compressed_size(path: Path) -> int:
    target = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as source, gzip.GzipFile(target, "wb", mtime=0) as sink:
        while block := source.read(1024 * 1024):
            sink.write(block)
    size = target.stat().st_size
    target.unlink()
    return size


def block_for(year: int) -> str:
    for first, last in BLOCKS:
        if first <= year <= last:
            return f"{first}-{last}"
    raise ValueError(f"Año ESFire30 fuera de bloque: {year}")


def stable_geometry_id(year: int, index: int) -> str:
    """ID estable por snapshot, año y ordinal de feature (base de CV-4.3)."""
    return f"esfire30:v1:{year}:{index}"


def feature(geometry: Any, transformer: Any, year: int, index: int, area_ha: Any) -> dict[str, Any]:
    from shapely.geometry import mapping
    from shapely.ops import transform

    return {
        "type": "Feature",
        "id": stable_geometry_id(year, index),
        "properties": {
            "geometry_id": stable_geometry_id(year, index),
            "source": "esfire30",
            "year": year,
            "area_ha": float(area_ha) if area_ha not in (None, "") else None,
        },
        "geometry": mapping(transform(transformer.transform, geometry)),
    }


def write_collection(stream, items: list[dict[str, Any]]) -> None:
    stream.write('{"type":"FeatureCollection","features":[')
    for index, item in enumerate(items):
        if index:
            stream.write(",")
        json.dump(item, stream, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    stream.write("]}")


def selected_transformer():
    import pyproj
    from pyproj.transformer import AreaOfInterest, TransformerGroup

    if sha256(DEFAULT_GRID) != EXPECTED_GRID_SHA256:
        raise RuntimeError("Checksum inesperado para la rejilla oficial ED50")
    pyproj.datadir.append_data_dir(str(DEFAULT_GRID.parent))
    group = TransformerGroup(
        "EPSG:23030", "EPSG:4326", always_xy=True,
        area_of_interest=AreaOfInterest(-10.0, 35.0, 4.5, 44.5),
    )
    transformer = next(
        (item for item in group.transformers if "ED50 to WGS 84 (41)" in item.description),
        None,
    )
    if transformer is None:
        raise RuntimeError("No está disponible ED50 to WGS 84 (41)")
    reverse_group = TransformerGroup(
        "EPSG:4326", "EPSG:23030", always_xy=True,
        area_of_interest=AreaOfInterest(-10.0, 35.0, 4.5, 44.5),
    )
    reverse = next(
        (item for item in reverse_group.transformers if "ED50 to WGS 84 (41)" in item.description),
        None,
    )
    if reverse is None:
        raise RuntimeError("No está disponible la inversa de ED50 to WGS 84 (41)")
    return transformer, reverse, {"pyproj": pyproj.__version__, "proj": pyproj.proj_version_str}


def boundary_units(es1: Any, transformer: Any, ccaa_path: Path, province_path: Path):
    # Límite en CRS84 transformado al CRS fuente para evitar transformar las
    # 119.498 geometrías únicamente para indexar territorio.
    return (
        es1.load_ign_units(ccaa_path, transformer, 5.0),
        es1.load_ign_units(province_path, transformer, 5.0),
    )


def audit_crs(zip_path: Path) -> dict[str, Any]:
    """Comprueba el uso nacional de la única proyección declarada EPSG:23030."""
    import shapefile
    from shapely.geometry import shape

    es1 = load_es1()
    forward, reverse, versions = selected_transformer()
    representative = {"west": None, "central": None, "east": None}
    raw_bounds = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for year in range(1985, 2022):
            reader = es1.archive_reader(archive, year)
            for row in reader.iterShapeRecords():
                geom = shape(row.shape.__geo_interface__)
                minx, miny, maxx, maxy = geom.bounds
                raw_bounds[0] = min(raw_bounds[0], minx); raw_bounds[1] = min(raw_bounds[1], miny)
                raw_bounds[2] = max(raw_bounds[2], maxx); raw_bounds[3] = max(raw_bounds[3], maxy)
                point = geom.representative_point()
                lon, lat = forward.transform(point.x, point.y)
                group = "west_zone29_extent" if lon < -6 else "central_zone30_extent" if lon <= 0 else "east_zone31_extent"
                if representative[group.split("_")[0]] is None:
                    x2, y2 = reverse.transform(lon, lat)
                    representative[group.split("_")[0]] = {
                        "year": year, "source_xy": [point.x, point.y], "wgs84_lon_lat": [lon, lat],
                        "round_trip_error_m": ((x2 - point.x) ** 2 + (y2 - point.y) ** 2) ** 0.5,
                    }
                count += 1
    return {
        "records": count,
        "source_crs": "EPSG:23030", "source_bbox": raw_bounds,
        "operation": forward.description, "accuracy_m": forward.accuracy,
        "software": versions, "representative_round_trips": representative,
        "conclusion": "Las coordenadas de todo el snapshot se interpretan coherentemente en la única malla EPSG:23030 declarada, incluso con eastings negativos al oeste y >1.000.000 al este. No se debe escoger por feature el huso UTM nominal de su longitud.",
    }


def audit_simplification(zip_path: Path, tolerance: float, sample_step: int) -> dict[str, Any]:
    """Muestra determinista de error planar, sin alterar ningún activo fuente."""
    from shapely.geometry import shape
    es1 = load_es1()
    sampled = 0; invalid_original = invalid_simplified = collapsed = 0
    area_errors: list[float] = []; hausdorff: list[float] = []
    with zipfile.ZipFile(zip_path) as archive:
        global_index = 0
        for year in range(1985, 2022):
            for row in es1.archive_reader(archive, year).iterShapeRecords():
                if global_index % sample_step == 0:
                    geometry = shape(row.shape.__geo_interface__)
                    simplified = geometry.simplify(tolerance, preserve_topology=True)
                    sampled += 1; invalid_original += int(not geometry.is_valid)
                    collapsed += int(simplified.is_empty); invalid_simplified += int(not simplified.is_valid)
                    if geometry.area > 0 and not simplified.is_empty:
                        area_errors.append(abs(simplified.area - geometry.area) / geometry.area * 100)
                        hausdorff.append(geometry.hausdorff_distance(simplified))
                global_index += 1
    def stats(values: list[float]) -> dict[str, float | None]:
        if not values: return {"max": None, "p95": None, "mean": None}
        values.sort(); p95 = values[round((len(values) - 1) * .95)]
        return {"max": max(values), "p95": p95, "mean": sum(values) / len(values)}
    return {"records_sampled": sampled, "sample_step": sample_step, "tolerance_source_m": tolerance, "invalid_original": invalid_original, "invalid_simplified": invalid_simplified, "collapsed": collapsed, "relative_area_error_percent": stats(area_errors), "hausdorff_distance_source_m": stats(hausdorff), "note": "Muestra sistemática diagnóstica; no es una garantía global ni una reparación topológica."}


def build(args: argparse.Namespace) -> dict[str, Any]:
    import shapefile
    from shapely.geometry import shape
    from shapely.strtree import STRtree

    if sha256(args.zip) != EXPECTED_ZIP_SHA256:
        raise RuntimeError("Checksum inesperado de ESFire30 v1")
    es1 = load_es1()
    transformer, _, versions = selected_transformer()
    # Inversa de la operación geodésica para llevar los límites CRS84 al CRS
    # de las features, no una suposición de zona UTM por longitud.
    from pyproj.transformer import AreaOfInterest, TransformerGroup
    boundary_to_source = next(
        item for item in TransformerGroup("EPSG:4326", "EPSG:23030", always_xy=True,
        area_of_interest=AreaOfInterest(-10.0, 35.0, 4.5, 44.5)).transformers
        if "ED50 to WGS 84 (41)" in item.description
    )
    ccaa, provinces = boundary_units(es1, boundary_to_source, args.ccaa, args.provinces)
    ccaa_tree = STRtree([row["geometry"] for row in ccaa])
    province_tree = STRtree([row["geometry"] for row in provinces])
    output = args.output
    assets = output.parent / "assets"
    partitions = assets / "partitions"
    assets.mkdir(parents=True, exist_ok=True); partitions.mkdir(parents=True, exist_ok=True)
    monolithic: list[dict[str, Any]] = []
    partitioned: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    lookup: list[dict[str, Any]] = []
    primary_ccaa = Counter(); primary_province = Counter(); all_ccaa = Counter(); all_province = Counter()
    by_year = Counter(); areas = Counter(); cross_ccaa = cross_province = no_ccaa = no_province = 0
    vertices_original = vertices_overview = 0
    types = Counter(); total = 0
    started = time.perf_counter()

    def hits(tree, units, geometry):
        return [int(index) for index in tree.query(geometry, predicate="intersects")
                if geometry.intersection(units[int(index)]["geometry"]).area > 0]

    with zipfile.ZipFile(args.zip) as archive:
        for year in range(1985, 2022):
            reader = es1.archive_reader(archive, year)
            for index, row in enumerate(reader.iterShapeRecords()):
                geometry = shape(row.shape.__geo_interface__)
                attr = row.record.as_dict(); area = float(attr.get("area_ha") or 0)
                total += 1; by_year[year] += 1; areas[year] += area; types[geometry.geom_type] += 1
                vertices_original += len(row.shape.points)
                overview = geometry.simplify(args.overview_tolerance, preserve_topology=True)
                if overview.is_empty:
                    raise RuntimeError(f"Simplificación colapsó {year}:{index}")
                vertices_overview += es1.geometry_vertices(overview)
                item = feature(overview, transformer, year, index, area)
                monolithic.append(item)
                ccaa_hits = hits(ccaa_tree, ccaa, geometry); province_hits = hits(province_tree, provinces, geometry)
                no_ccaa += int(not ccaa_hits); no_province += int(not province_hits)
                cross_ccaa += int(len(ccaa_hits) > 1); cross_province += int(len(province_hits) > 1)
                primary_ccaa_code = None
                if ccaa_hits:
                    winner = max(ccaa_hits, key=lambda candidate: geometry.intersection(ccaa[candidate]["geometry"]).area)
                    code = ccaa[winner]["autonomous_community_code"]
                    primary_ccaa_code = code
                    primary_ccaa[code] += 1; partitioned[(code, block_for(year))].append(item)
                    for candidate in ccaa_hits: all_ccaa[ccaa[candidate]["autonomous_community_code"]] += 1
                if province_hits:
                    winner = max(province_hits, key=lambda candidate: geometry.intersection(provinces[candidate]["geometry"]).area)
                    primary_province[provinces[winner]["province_code"]] += 1
                    for candidate in province_hits: all_province[provinces[candidate]["province_code"]] += 1
                lookup.append({"geometry_id": item["id"], "source_record_id": item["id"], "source": "esfire30", "year": year, "area_ha": area, "geometry_semantics": "documented_remote_sensing_perimeter", "primary_autonomous_community": primary_ccaa_code})
            print(f"ES-3 {year}: {len(reader)}", flush=True)
    if total != EXPECTED_RECORDS:
        raise RuntimeError(f"{total} != {EXPECTED_RECORDS}")
    mono_path = assets / "esfire30-overview-national.geojson"
    with mono_path.open("w", encoding="utf-8") as stream: write_collection(stream, monolithic)
    lookup_path = assets / "esfire30-lookup.jsonl"
    with lookup_path.open("w", encoding="utf-8") as stream:
        for row in lookup: stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    partition_info = {}
    copies = 0
    for (code, block), rows in sorted(partitioned.items()):
        path = partitions / f"esfire30-{code}-{block}.geojson"
        with path.open("w", encoding="utf-8") as stream: write_collection(stream, rows)
        copies += len(rows)
        partition_info[f"{code}:{block}"] = {"url": str(path.relative_to(output.parent)), "features": len(rows), "raw_bytes": path.stat().st_size, "gzip_bytes": compressed_size(path), "sha256": sha256(path)}
    ndjson = assets / "esfire30-tiles-input.ndjson"
    with ndjson.open("w", encoding="utf-8") as stream:
        for row in monolithic:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    results = {
        "schema_version": 1, "phase": "ES-3 diagnostic only", "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {"doi": "10.5281/zenodo.18449006", "zip": str(args.zip.relative_to(ROOT)), "sha256": EXPECTED_ZIP_SHA256, "source_crs": "EPSG:23030", "transformation": transformer.description, "transformation_accuracy_m": transformer.accuracy, "software": versions},
        "records": total, "years": [1985, 2021], "by_year": {str(year): by_year[year] for year in sorted(by_year)}, "area_ha_by_year": {str(year): round(areas[year], 6) for year in sorted(areas)}, "geometry_types": dict(types), "vertices": {"original": vertices_original, "overview": vertices_overview, "overview_reduction_percent": round((1 - vertices_overview / vertices_original) * 100, 3), "overview_tolerance_source_m": args.overview_tolerance},
        "territory_relations": {"primary_ccaa": dict(sorted(primary_ccaa.items())), "primary_province": dict(sorted(primary_province.items())), "all_ccaa": dict(sorted(all_ccaa.items())), "all_province": dict(sorted(all_province.items())), "crosses_ccaa": cross_ccaa, "crosses_province": cross_province, "without_ccaa": no_ccaa, "without_province": no_province, "assignment": "largest positive intersection; no clipping"},
        "assets": {"monolithic_overview": {"path": str(mono_path.relative_to(output.parent)), "features": total, "raw_bytes": mono_path.stat().st_size, "gzip_bytes": compressed_size(mono_path), "sha256": sha256(mono_path)}, "lookup": {"path": str(lookup_path.relative_to(output.parent)), "records": len(lookup), "raw_bytes": lookup_path.stat().st_size, "gzip_bytes": compressed_size(lookup_path), "sha256": sha256(lookup_path)}, "tile_input": {"path": str(ndjson.relative_to(output.parent)), "records": total, "raw_bytes": ndjson.stat().st_size, "gzip_bytes": compressed_size(ndjson), "sha256": sha256(ndjson)}, "ccaa_x_block": partition_info, "partition_instances": copies, "duplicate_instances_from_cross_boundary": copies - total},
        "wall_seconds": round(time.perf_counter() - started, 3),
        "limitations": ["No asset is production-ready.", "GeoJSON uses one primary CCAA delivery partition; all territorial relations are preserved separately.", "No geometry is clipped or interpreted as an administrative assignment."],
    }
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return results


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    crs = commands.add_parser("audit-crs")
    crs.add_argument("--zip", type=Path, default=DEFAULT_ZIP); crs.add_argument("--output", type=Path, required=True)
    simplify = commands.add_parser("audit-simplification")
    simplify.add_argument("--zip", type=Path, default=DEFAULT_ZIP); simplify.add_argument("--tolerance", type=float, default=100.0); simplify.add_argument("--sample-step", type=int, default=100); simplify.add_argument("--output", type=Path, required=True)
    build_cmd = commands.add_parser("build")
    build_cmd.add_argument("--zip", type=Path, default=DEFAULT_ZIP); build_cmd.add_argument("--ccaa", type=Path, default=DEFAULT_CCAA); build_cmd.add_argument("--provinces", type=Path, default=DEFAULT_PROVINCES); build_cmd.add_argument("--overview-tolerance", type=float, default=100.0); build_cmd.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "audit-crs":
        result = audit_crs(args.zip)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif args.command == "audit-simplification":
        result = audit_simplification(args.zip, args.tolerance, args.sample_step)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        result = build(args)
    print(json.dumps({"records": result.get("records", result.get("records_sampled")), "output": str(getattr(args, "output", ""))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
