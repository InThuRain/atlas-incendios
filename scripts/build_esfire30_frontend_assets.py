#!/usr/bin/env python3
"""Build normalized and web-only ESFire30 1985–1992 derivatives for CV-4.3."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import os
import statistics
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "scripts/ingest/esfire30/audit.py"
SPEC = importlib.util.spec_from_file_location("esfire30_cv42_audit_for_build", AUDIT_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)

EXPECTED_PRJ_SHA256 = "76169956e88617ef11da84dc3032ac3aafaa3e239d1dad9d8317df43b7e504ee"
EXPECTED_FEATURES = 710
LEVELS = ("local", "regional", "overview")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=AUDIT.DEFAULT_ZIP)
    parser.add_argument("--grid", type=Path, default=AUDIT.DEFAULT_GRID)
    parser.add_argument("--boundary", type=Path, default=AUDIT.DEFAULT_BOUNDARY)
    parser.add_argument("--config", type=Path, default=ROOT / "config/esfire30-web.json")
    parser.add_argument("--normalized", type=Path, default=ROOT / "data/processed/esfire30/gva/features_1985_1992.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "data/web/gva/esfire30")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def canonical_bytes(payload: Any, pretty: bool = False) -> bytes:
    options = {"ensure_ascii": False, "allow_nan": False}
    if pretty:
        return (json.dumps(payload, indent=2, **options) + "\n").encode("utf-8")
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), **options) + "\n").encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def file_info(payload: bytes) -> dict[str, Any]:
    return {
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def normalized_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): normalized_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized_value(item) for item in value]
    return value


def source_fingerprint(year: int, attributes: dict[str, Any], geometry_checksum: str) -> str:
    payload = canonical_bytes({
        "year": year,
        "original_attributes": normalized_value(attributes),
        "original_geometry_checksum_sha256": geometry_checksum,
    })
    return hashlib.sha256(payload).hexdigest()


def vertex_count(geometry) -> int:
    parts = geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry]
    return sum(
        len(part.exterior.coords) + sum(len(ring.coords) for ring in part.interiors)
        for part in parts
    )


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def error_summary(values: list[float]) -> dict[str, float]:
    return {
        "median": round(statistics.median(values), 8),
        "p95": round(percentile(values, 0.95), 8),
        "max": round(max(values), 8),
    }


def round_coordinates(value: Any, digits: int = 6) -> Any:
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (int, float)):
            return [round(float(item), digits) for item in value]
        return [round_coordinates(item, digits) for item in value]
    return value


def rounded_mapping(geometry) -> dict[str, Any]:
    from shapely.geometry import mapping

    result = mapping(geometry)
    return {"type": result["type"], "coordinates": round_coordinates(result["coordinates"])}


def province_key(value: str) -> str:
    if value == "Alicante":
        return "alicante"
    if value == "Castellón":
        return "castellon"
    if value == "Valencia":
        return "valencia"
    raise ValueError("Provincia inesperada: {}".format(value))


def load_spatial_catalog(boundary_path: Path, transforms: dict[str, Any]):
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union
    from shapely.prepared import prep

    payload = json.loads(boundary_path.read_text(encoding="utf-8"))
    municipalities = {}
    province_parts = {}
    for feature in payload["features"]:
        properties = feature["properties"]
        municipality_id = str(properties["cod_ine_mun"])
        geometry_wgs84 = shape(feature["geometry"])
        geometry_ed50 = transform(transforms["wgs84_to_ed50"].transform, geometry_wgs84)
        province = province_key(AUDIT.province_name(properties["provincia"]))
        municipalities[municipality_id] = {
            "name": properties["nom_mun"],
            "province": province,
            "geometry": geometry_ed50,
            "prepared": prep(geometry_ed50),
        }
        province_parts.setdefault(province, []).append(geometry_ed50)
    provinces = {key: unary_union(parts) for key, parts in province_parts.items()}
    return municipalities, provinces


def spatial_relations(geometry, municipalities, provinces):
    province_areas = {
        key: geometry.intersection(province).area
        for key, province in provinces.items()
        if geometry.intersects(province)
    }
    province_areas = {key: area for key, area in province_areas.items() if area > 0}
    if not province_areas:
        return None
    municipality_rows = []
    for municipality_id, item in municipalities.items():
        if not item["prepared"].intersects(geometry):
            continue
        area = geometry.intersection(item["geometry"]).area
        if area > 0:
            municipality_rows.append({
                "municipality_id": municipality_id,
                "municipality_name": item["name"],
                "province": item["province"],
                "intersection_area_m2": round(area, 3),
            })
    municipality_rows.sort(key=lambda item: (-item["intersection_area_m2"], item["municipality_id"]))
    return {
        "primary_province": max(province_areas, key=province_areas.get),
        "intersected_provinces": sorted(province_areas),
        "municipalities": municipality_rows,
    }


def inspect_source(args, config, transforms):
    from shapely.geometry import shape
    from shapely.ops import transform

    if args.zip.stat().st_size != AUDIT.EXPECTED_ZIP_BYTES or AUDIT.sha256_file(args.zip) != AUDIT.EXPECTED_ZIP_SHA256:
        raise ValueError("El ZIP ESFire30 no coincide con el snapshot v1 auditado")
    municipalities, provinces = load_spatial_catalog(args.boundary, transforms)
    selected = []
    with zipfile.ZipFile(args.zip) as archive:
        for year in AUDIT.PRE1993_YEARS:
            prj = archive.read("RF_jja/predicciones_{}.prj".format(year)).decode("utf-8").strip()
            if hashlib.sha256(prj.encode("utf-8")).hexdigest() != EXPECTED_PRJ_SHA256 or "ED_1950_UTM_Zone_30N" not in prj:
                raise ValueError("El CRS fuente de {} ya no coincide con EPSG:23030 auditado".format(year))
            reader = AUDIT.archive_reader(archive, year)
            for index, shape_record in enumerate(reader.iterShapeRecords()):
                geometry = shape(shape_record.shape.__geo_interface__)
                relations = spatial_relations(geometry, municipalities, provinces)
                if relations is None:
                    continue
                attributes = normalized_value(shape_record.record.as_dict())
                geometry_checksum = AUDIT.raw_geometry_checksum(shape_record.shape)
                fingerprint = source_fingerprint(year, attributes, geometry_checksum)
                source_record_id = "esfire30:{}:record:sha256:{}".format(config["source_version"], fingerprint)
                stable_record_id = "esfire30:record:sha256:{}".format(fingerprint)
                geometry_id = "esfire30:geometry:sha256:{}".format(geometry_checksum)
                derived = transform(transforms["ed50_to_4326"].transform, geometry)
                selected.append({
                    "source_record_id": source_record_id,
                    "stable_record_id": stable_record_id,
                    "geometry_id": geometry_id,
                    "source_feature_fingerprint_sha256": fingerprint,
                    "source_geometry_checksum_sha256": geometry_checksum,
                    "source_version": config["source_version"],
                    "source_year": year,
                    "source_record_index": index,
                    "source_area_ha": float(attributes["area_ha"]),
                    "source_crs": config["source_crs"],
                    "original_attributes": attributes,
                    "geometry_original": geometry,
                    "geometry_epsg4326": derived,
                    "primary_province": relations["primary_province"],
                    "intersected_provinces": relations["intersected_provinces"],
                    "municipalities": relations["municipalities"],
                })
    if len(selected) != EXPECTED_FEATURES:
        raise ValueError("Se esperaban 710 polígonos y se obtuvieron {}".format(len(selected)))
    if len({item["source_record_id"] for item in selected}) != EXPECTED_FEATURES:
        raise ValueError("source_record_id no es único")
    if len({item["geometry_id"] for item in selected}) != EXPECTED_FEATURES:
        raise ValueError("geometry_id no es único")
    return selected


def normalized_payload(features, transforms):
    from shapely.geometry import mapping

    rows = []
    for item in features:
        rows.append({
            "source_record_id": item["source_record_id"],
            "stable_record_id": item["stable_record_id"],
            "geometry_id": item["geometry_id"],
            "source": "esfire30",
            "source_version": item["source_version"],
            "source_year": item["source_year"],
            "source_record_index": item["source_record_index"],
            "source_feature_fingerprint_sha256": item["source_feature_fingerprint_sha256"],
            "source_geometry_checksum_sha256": item["source_geometry_checksum_sha256"],
            "source_area_ha": item["source_area_ha"],
            "source_crs": item["source_crs"],
            "geometry_original": mapping(item["geometry_original"]),
            "geometry_epsg4326": mapping(item["geometry_epsg4326"]),
            "primary_province": item["primary_province"],
            "intersected_provinces": item["intersected_provinces"],
            "municipalities": item["municipalities"],
            "geometry_quality": "B_DOCUMENTED_REMOTE_SENSING",
            "episode_identity_status": "unresolved",
            "original_attributes": item["original_attributes"],
            "provenance": {
                "doi": AUDIT.ZENODO_DOI,
                "snapshot_sha256": AUDIT.EXPECTED_ZIP_SHA256,
                "transformation": transforms["metadata"]["selected_operation_4326"],
                "transformation_accuracy_m": transforms["metadata"]["declared_accuracy_m"],
                "grid_sha256": AUDIT.EXPECTED_GRID_SHA256,
                "geodetic_accuracy_is_not_thematic_accuracy": True,
            },
        })
    return b"".join(canonical_bytes(row) for row in rows)


def web_feature(item, geometry):
    municipality_ids = [row["municipality_id"] for row in item["municipalities"]]
    municipality_names = [row["municipality_name"] for row in item["municipalities"]]
    municipality_province_ids = [row["province"] for row in item["municipalities"]]
    return {
        "type": "Feature",
        "id": item["geometry_id"],
        "properties": {
            "source_id": "esfire30",
            "entity_id": item["stable_record_id"],
            "source_record_id": item["source_record_id"],
            "geometry_id": item["geometry_id"],
            "source_version": item["source_version"],
            "source_index": item["source_record_index"],
            "source_checksum": item["source_feature_fingerprint_sha256"],
            "geometry_checksum_sha256": item["source_geometry_checksum_sha256"],
            "year": item["source_year"],
            "mapped_area_ha": item["source_area_ha"],
            "primary_province": item["primary_province"],
            "province_ids": item["intersected_provinces"],
            "municipality_ids": municipality_ids,
            "municipality_names": municipality_names,
            "municipality_province_ids": municipality_province_ids,
            "source_status": "historical_remote_sensing",
            "geometry_quality": "B_DOCUMENTED_REMOTE_SENSING",
            "geometry_kind": "landsat_burned_area_perimeter",
            "native_resolution_m": 30,
            "minimum_area_method_ha": 5,
            "episode_identity_status": "unresolved",
            "administrative_link_status": "unlinked",
        },
        "geometry": rounded_mapping(geometry),
    }


def build(args):
    from shapely.ops import transform

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if AUDIT.sha256_file(args.grid) != config["grid"]["sha256"]:
        raise ValueError("La rejilla IGN esperada no está disponible o cambió")
    transforms = AUDIT.prepare_transformations(args.grid)
    if "ED50 to WGS 84 (41)" not in transforms["metadata"]["selected_operation_4326"]:
        raise ValueError("PROJ seleccionó una transformación distinta de la auditada")
    features = inspect_source(args, config, transforms)
    normalized = normalized_payload(features, transforms)

    assets = []
    lod_metrics = {}
    web_payloads = {}
    original_vertices = sum(vertex_count(item["geometry_original"]) for item in features)
    for level in LEVELS:
        tolerance = float(config["lod"][level]["tolerance_m"])
        output_features = []
        area_errors = []
        small_errors = []
        vertices = 0
        invalid = empty = 0
        for item in features:
            original = item["geometry_original"]
            simplified = original if tolerance == 0 else original.simplify(tolerance, preserve_topology=True)
            invalid += int(not simplified.is_valid)
            empty += int(simplified.is_empty)
            error = abs(simplified.area - original.area) / original.area
            area_errors.append(error)
            if item["source_area_ha"] < 10:
                small_errors.append(error)
            vertices += vertex_count(simplified)
            derived = transform(transforms["ed50_to_4326"].transform, simplified)
            output_features.append(web_feature(item, derived))
        payload = canonical_bytes({"type": "FeatureCollection", "features": output_features})
        web_payloads[level] = payload
        info = file_info(payload)
        asset = {
            "level": level,
            "kind": "esfire30_perimeters",
            "url": "data/web/gva/esfire30/geometry/{}.geojson".format(level),
            "feature_count": len(output_features),
            "year_min": config["years"]["min"],
            "year_max": config["years"]["max"],
            **info,
        }
        assets.append(asset)
        lod_metrics[level] = {
            "tolerance_m": tolerance,
            "vertices": vertices,
            "vertex_reduction_percent": round(100 * (1 - vertices / original_vertices), 3),
            "relative_area_error": error_summary(area_errors),
            "small_lt_10_ha_max_relative_area_error": round(max(small_errors), 8),
            "invalid": invalid,
            "empty_or_collapsed": empty,
            "bytes": info["bytes"],
            "gzip_bytes": info["gzip_bytes"],
        }

    counts = Counter(item["source_year"] for item in features)
    province_counts = Counter(item["primary_province"] for item in features)
    manifest = {
        "schema_version": 1,
        "phase": "CV-4.3",
        "source": "esfire30",
        "source_version": config["source_version"],
        "doi": config["doi"],
        "entity_type": "independent_historical_remote_sensing_perimeter",
        "geometry_quality": "B_DOCUMENTED_REMOTE_SENSING",
        "episode_identity_status": "unresolved",
        "administrative_link_status": "unlinked",
        "years": config["years"],
        "identity": config["identity"],
        "crs": {
            "source": config["source_crs"],
            "web": config["web_crs"],
            "operation": transforms["metadata"]["selected_operation_4326"],
            "declared_geodetic_accuracy_m": transforms["metadata"]["declared_accuracy_m"],
            "grid": transforms["metadata"]["grid"],
            "warning": "La precisión geodésica de transformación no representa la precisión temática Landsat.",
        },
        "assets": assets,
        "metrics": {
            "features": len(features),
            "annual_counts": {str(year): counts[year] for year in range(1985, 1993)},
            "primary_province_counts": dict(sorted(province_counts.items())),
            "multi_province_features": sum(len(item["intersected_provinces"]) > 1 for item in features),
            "municipality_relations": sum(len(item["municipalities"]) for item in features),
            "multi_municipality_features": sum(len(item["municipalities"]) > 1 for item in features),
            "mapped_area_ha": round(sum(item["source_area_ha"] for item in features), 6),
            "mapped_area_ge_500_ha": sum(item["source_area_ha"] >= 500 for item in features),
            "original_vertices": original_vertices,
        },
        "lod": lod_metrics,
        "municipality_relation": config["municipality_relation"],
        "province_relation": config["province_relation"],
        "provenance": {
            "snapshot": "data/raw/esfire30/18449006/ESFire30_Causes.zip",
            "snapshot_sha256": AUDIT.EXPECTED_ZIP_SHA256,
            "normalized": str(args.normalized.relative_to(ROOT)),
            "normalized_bytes": len(normalized),
            "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
            "raw_geometry_preserved": True,
            "polygons_clipped": False,
            "records_deduplicated": False,
        },
        "license": {
            "id": "CC-BY-4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "publishable": True,
            "attribution": "ESFire30 Causes, Ochoa, Chuvieco, Rodrigues y Franquesa (2026), versión v1, CC BY 4.0, DOI 10.5281/zenodo.18449006. Datos transformados para el Atlas mediante selección territorial, reproyección a EPSG:4326, selección de atributos y simplificación geométrica según nivel de zoom.",
        },
        "validation": {
            "expected_features": EXPECTED_FEATURES,
            "feature_count_reconciled": len(features) == EXPECTED_FEATURES,
            "unique_source_record_ids": len({item["source_record_id"] for item in features}),
            "unique_stable_record_ids": len({item["stable_record_id"] for item in features}),
            "unique_geometry_ids": len({item["geometry_id"] for item in features}),
            "all_lods_valid": all(not item["invalid"] and not item["empty_or_collapsed"] for item in lod_metrics.values()),
        },
    }
    manifest_payload = canonical_bytes(manifest, pretty=True)

    expected = {args.normalized: normalized, args.output / "assets-manifest.json": manifest_payload}
    expected.update({args.output / "geometry" / "{}.geojson".format(level): payload for level, payload in web_payloads.items()})
    if args.check:
        mismatches = [str(path) for path, payload in expected.items() if not path.is_file() or path.read_bytes() != payload]
        if mismatches:
            raise SystemExit("Derivados ESFire30 no reproducibles: " + ", ".join(mismatches))
        print("OK: derivados ESFire30 reproducibles")
        return manifest
    for path, payload in expected.items():
        atomic_write(path, payload)
    return manifest


def main():
    manifest = build(parse_args())
    print(json.dumps({"assets": manifest["assets"], "metrics": manifest["metrics"], "lod": manifest["lod"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
