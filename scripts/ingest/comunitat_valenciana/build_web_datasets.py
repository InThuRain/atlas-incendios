#!/usr/bin/env python3
"""Build and benchmark derived web datasets for the Comunitat Valenciana."""

import argparse
import collections
import gzip
import hashlib
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

try:
    import shapely
    from shapely.geometry import mapping, shape
    from shapely.ops import transform
except ImportError as error:  # pragma: no cover
    shapely = None
    SHAPELY_IMPORT_ERROR = error
else:
    SHAPELY_IMPORT_ERROR = None

from audit_duplicates import AuditError, construct_ogc_geometry


BUILD_VERSION = 3
WEB_MERCATOR_HALF_WORLD = 20037508.342789244
WEB_COORDINATE_PRECISIONS = (6, 9)
DEFAULT_TOLERANCES = (0, 1, 2, 5, 10, 20, 50, 100, 200, 500)
LEVEL_PROFILES = {
    "local": {
        "tolerance_m_web_mercator": 1,
        "max_per_geometry_relative_area_error": 0.01,
        "intended_scale": "local/municipal",
    },
    "regional": {
        "tolerance_m_web_mercator": 10,
        "max_per_geometry_relative_area_error": 0.05,
        "intended_scale": "province/county",
    },
    "overview": {
        "tolerance_m_web_mercator": 50,
        "max_per_geometry_relative_area_error": 0.15,
        "intended_scale": "whole Comunitat Valenciana",
    },
}
COMPACT_GEOMETRY_FIELDS = (
    "geometry_id",
    "fire_id",
    "year",
    "province",
    "source",
    "provenance_id",
    "geometry_reused",
    "geometry_reuse_group",
    "geometry_type",
    "coordinates",
)


class WebBuildError(RuntimeError):
    """Raised when a web derivative cannot be generated without data loss."""


def repository_root():
    return Path(__file__).resolve().parents[3]


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def json_bytes(value):
    return canonical_json(value).encode("utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WebBuildError("Invalid JSON file {}: {}".format(path, error))


def load_jsonl(path):
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise WebBuildError(
                    "Invalid JSONL at {}:{}: {}".format(path, line_number, error)
                )
    return records


def write_bytes_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_json_atomic(path, value, pretty=False):
    if pretty:
        payload = json.dumps(
            value, ensure_ascii=False, allow_nan=False, indent=2
        ).encode("utf-8") + b"\n"
    else:
        payload = json_bytes(value) + b"\n"
    write_bytes_atomic(path, payload)


def verify_processed_file(processed_dir, manifest, key):
    entry = manifest["outputs"][key]
    path = processed_dir / entry["path"]
    if path.stat().st_size != entry["file_size_bytes"]:
        raise WebBuildError("Size differs from manifest: {}".format(path))
    checksum = sha256_file(path)
    if checksum != entry["sha256"]:
        raise WebBuildError("Checksum differs from manifest: {}".format(path))
    return path, checksum


def percentile(values, percentage):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentage
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def distribution(values):
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.5),
        "p75": percentile(values, 0.75),
        "p90": percentile(values, 0.9),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def geometry_vertex_count(geometry):
    if geometry.geom_type == "Polygon":
        polygons = [geometry]
    elif geometry.geom_type == "MultiPolygon":
        polygons = geometry.geoms
    else:
        return 0
    return sum(
        max(0, len(polygon.exterior.coords) - 1)
        + sum(max(0, len(ring.coords) - 1) for ring in polygon.interiors)
        for polygon in polygons
    )


def web_mercator_to_wgs84(x, y, z=None):
    def convert(x_value, y_value):
        longitude = x_value / WEB_MERCATOR_HALF_WORLD * 180.0
        latitude = math.degrees(
            2.0
            * math.atan(
                math.exp(y_value / WEB_MERCATOR_HALF_WORLD * math.pi)
            )
            - math.pi / 2.0
        )
        return longitude, latitude

    # shapely.ops.transform first tries the callable with coordinate sequences
    # and falls back to scalars only when that fails. Supporting both forms
    # keeps this compatible with the pinned Shapely 2.0 release.
    if isinstance(x, (tuple, list)):
        converted = [convert(x_value, y_value) for x_value, y_value in zip(x, y)]
        longitudes = tuple(item[0] for item in converted)
        latitudes = tuple(item[1] for item in converted)
        if z is None:
            return longitudes, latitudes
        return longitudes, latitudes, z

    longitude, latitude = convert(x, y)
    if z is None:
        return longitude, latitude
    return longitude, latitude, z


def rounded_coordinates(value, precision):
    if isinstance(value, (tuple, list)):
        if value and isinstance(value[0], (int, float)):
            return [round(number, precision) for number in value[:2]]
        return [rounded_coordinates(item, precision) for item in value]
    raise WebBuildError("Unexpected coordinate structure")


def web_geometry(geometry):
    projected = transform(web_mercator_to_wgs84, geometry)
    geo_interface = mapping(projected)
    for precision in WEB_COORDINATE_PRECISIONS:
        serialized = {
            "type": geo_interface["type"],
            "coordinates": rounded_coordinates(
                geo_interface["coordinates"], precision
            ),
        }
        serialized_shape = shape(serialized)
        if not serialized_shape.is_empty and serialized_shape.is_valid:
            return serialized, precision
    raise WebBuildError("Geometry is invalid at all configured web precisions")


def slug(value):
    normalized = str(value or "unknown").lower()
    replacements = {
        "á": "a",
        "à": "a",
        "é": "e",
        "è": "e",
        "í": "i",
        "ó": "o",
        "ò": "o",
        "ú": "u",
        "ü": "u",
        "ç": "c",
    }
    for source, destination in replacements.items():
        normalized = normalized.replace(source, destination)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def province_partition(value):
    """Collapse known monolingual/bilingual labels only for web partitioning."""
    normalized = slug(value)
    for canonical in ("alicante", "castellon", "valencia"):
        if normalized == canonical or normalized.startswith(canonical + "-"):
            return canonical
    return normalized or "unknown"


def temporal_block(year):
    if year < 2000:
        return "1993-1999"
    start = year // 10 * 10
    end = min(start + 9, 2024)
    return "{}-{}".format(start, end)


def reuse_index(audit_report):
    index = {}
    for group in audit_report["groups"]:
        for feature in group["features"]:
            index[feature["geometry_id"]] = {
                "group_id": group["group_id"],
                "group_size": group["feature_count"],
                "primary_category": group["classification"]["primary_category"],
            }
    return index


def provenance_catalog(geometries):
    catalog = {}
    geometry_to_provenance = {}
    for geometry in geometries:
        provenance_id = "gva:icv:{}:{}".format(
            geometry["source_year"], geometry["source_layer_id"]
        )
        geometry_to_provenance[geometry["geometry_id"]] = provenance_id
        value = {
            "provenance_id": provenance_id,
            "source": geometry["source"],
            "source_year": geometry["source_year"],
            "source_layer_id": geometry["source_layer_id"],
            **geometry["provenance"],
        }
        old = catalog.setdefault(provenance_id, value)
        if old != value:
            raise WebBuildError("Inconsistent provenance {}".format(provenance_id))
    return catalog, geometry_to_provenance


def web_fire_record(fire):
    return {
        "fire_id": fire["fire_id"],
        "num_pif_cv": fire["num_pif_cv"],
        "num_pif_min": fire["num_pif_min"],
        "year": fire["year"],
        "start_date": fire["start_date"],
        "end_date": fire["end_date"],
        "municipality": fire["municipality"],
        "county": fire["county"],
        "province": fire["province"],
        "place_name": fire["place_name"],
        "cause": fire["cause"],
        "reported_forest_area_ha": fire["reported_forest_area_ha"],
        "source_dataset": fire["source_dataset"],
        "geometry_ids": fire["geometry_ids"],
    }


def geometry_metadata(record, fire, provenance_id, reuse):
    return {
        "geometry_id": record["geometry_id"],
        "fire_id": record["fire_id"],
        "year": record["source_year"],
        "province": fire["province"],
        "source": record["source"],
        "provenance_id": provenance_id,
        "geometry_reused": reuse is not None,
        "geometry_reuse_group": reuse["group_id"] if reuse else None,
    }


def geojson_feature(metadata, geometry):
    return {
        "type": "Feature",
        "id": metadata["geometry_id"],
        "properties": metadata,
        "geometry": geometry,
    }


def compact_feature(metadata, geometry):
    values = dict(metadata)
    values["geometry_type"] = geometry["type"]
    values["coordinates"] = geometry["coordinates"]
    return [values[field] for field in COMPACT_GEOMETRY_FIELDS]


def gzip_size(payload):
    return len(gzip.compress(payload, compresslevel=9, mtime=0))


def serialize_size(payload):
    encoded = json_bytes(payload)
    return len(encoded), gzip_size(encoded)


def simplification_result(original, tolerance):
    if tolerance == 0:
        return original, False
    candidate = original.simplify(tolerance, preserve_topology=True)
    if (
        candidate.is_empty
        or candidate.geom_type not in ("Polygon", "MultiPolygon")
        or not candidate.is_valid
        or candidate.area <= 0
    ):
        return original, True
    return candidate, False


def candidate_metrics(
    tolerance,
    geometries,
    shapes,
    fires_by_id,
    provenance_by_geometry,
    reuse_by_geometry,
    original_vertex_total,
    cached_candidate=None,
):
    vertex_counts = []
    relative_area_errors = []
    hausdorff_distances = []
    small_area_errors = []
    small_hausdorff = []
    fallback_count = 0
    invalid_count = 0
    empty_count = 0
    geojson_features = []
    compact_features = []
    precision_counts = collections.Counter()

    for record, original in zip(geometries, shapes):
        simplified, fallback = simplification_result(original, tolerance)
        fallback_count += fallback
        invalid_count += not simplified.is_valid
        empty_count += simplified.is_empty
        vertices = geometry_vertex_count(simplified)
        vertex_counts.append(vertices)
        area_error = abs(simplified.area - original.area) / original.area
        relative_area_errors.append(area_error)
        if cached_candidate is None:
            distance = (
                0.0 if tolerance == 0 else original.hausdorff_distance(simplified)
            )
            hausdorff_distances.append(distance)

        fire = fires_by_id[record["fire_id"]]
        declared_area = fire["reported_forest_area_ha"]
        if declared_area is not None and declared_area < 1:
            small_area_errors.append(area_error)
            if cached_candidate is None:
                small_hausdorff.append(distance)

        converted, precision = web_geometry(simplified)
        precision_counts[precision] += 1
        metadata = geometry_metadata(
            record,
            fire,
            provenance_by_geometry[record["geometry_id"]],
            reuse_by_geometry.get(record["geometry_id"]),
        )
        geojson_features.append(geojson_feature(metadata, converted))
        compact_features.append(compact_feature(metadata, converted))

    geojson_payload = {"type": "FeatureCollection", "features": geojson_features}
    compact_payload = {
        "schema_version": 1,
        "crs": "EPSG:4326",
        "fields": list(COMPACT_GEOMETRY_FIELDS),
        "features": compact_features,
    }
    geojson_bytes, geojson_gzip = serialize_size(geojson_payload)
    compact_bytes, compact_gzip = serialize_size(compact_payload)
    vertex_total = sum(vertex_counts)
    return {
        "tolerance_m_web_mercator": tolerance,
        "geometry_count": len(geometries),
        "vertex_count": vertex_total,
        "vertex_reduction_percent": (
            (original_vertex_total - vertex_total) / original_vertex_total * 100
        ),
        "vertex_distribution": distribution(vertex_counts),
        "relative_area_error": distribution(relative_area_errors),
        "hausdorff_distance_m_web_mercator": (
            distribution(hausdorff_distances)
            if cached_candidate is None
            else cached_candidate["hausdorff_distance_m_web_mercator"]
        ),
        "small_fire_definition": "reported_forest_area_ha < 1",
        "small_fire_count": len(small_area_errors),
        "small_fire_relative_area_error": distribution(small_area_errors),
        "small_fire_hausdorff_distance_m_web_mercator": (
            distribution(small_hausdorff)
            if cached_candidate is None
            else cached_candidate["small_fire_hausdorff_distance_m_web_mercator"]
        ),
        "coordinate_precision_counts": {
            str(key): value for key, value in sorted(precision_counts.items())
        },
        "invalid_geometry_count": invalid_count,
        "empty_geometry_count": empty_count,
        "fallback_to_original_count": fallback_count,
        "formats": {
            "geojson": {
                "bytes": geojson_bytes,
                "gzip_bytes": geojson_gzip,
            },
            "compact_json": {
                "bytes": compact_bytes,
                "gzip_bytes": compact_gzip,
            },
        },
    }


def recommend_levels(candidates):
    recommendations = {}
    by_tolerance = {
        candidate["tolerance_m_web_mercator"]: candidate
        for candidate in candidates
    }
    for level, profile in LEVEL_PROFILES.items():
        tolerance = profile["tolerance_m_web_mercator"]
        if tolerance not in by_tolerance:
            raise WebBuildError(
                "Required level tolerance {} was not benchmarked".format(tolerance)
            )
        recommendations[level] = {
            **profile,
            "selection_basis": (
                "Nominal tolerance selected from the full comparison; each "
                "geometry is retained unsimplified when the derived polygon is "
                "structurally unsafe or exceeds the per-geometry area-error guard."
            ),
            "unguarded_candidate_metrics": by_tolerance[tolerance],
        }
    return recommendations


def build_level_features(
    tolerance,
    max_relative_area_error,
    geometries,
    shapes,
    fires_by_id,
    provenance_by_geometry,
    reuse_by_geometry,
    measure_hausdorff=True,
):
    features = []
    vertex_counts = []
    area_errors = []
    hausdorff_distances = []
    protected_by_reason = collections.Counter()
    precision_counts = collections.Counter()
    for record, original in zip(geometries, shapes):
        simplified, fallback = simplification_result(original, tolerance)
        if fallback:
            protected_by_reason["structural_safety"] += 1
        else:
            relative_area_error = abs(simplified.area - original.area) / original.area
            if relative_area_error > max_relative_area_error:
                simplified = original
                protected_by_reason["relative_area_error"] += 1
        area_error = abs(simplified.area - original.area) / original.area
        vertex_counts.append(geometry_vertex_count(simplified))
        area_errors.append(area_error)
        if measure_hausdorff:
            hausdorff_distances.append(original.hausdorff_distance(simplified))
        fire = fires_by_id[record["fire_id"]]
        metadata = geometry_metadata(
            record,
            fire,
            provenance_by_geometry[record["geometry_id"]],
            reuse_by_geometry.get(record["geometry_id"]),
        )
        geometry, precision = web_geometry(simplified)
        precision_counts[precision] += 1
        features.append(
            {
                "metadata": metadata,
                "geojson": geojson_feature(metadata, geometry),
                "compact": compact_feature(metadata, geometry),
            }
        )
    return features, {
        "geometry_count": len(features),
        "vertex_count": sum(vertex_counts),
        "vertex_distribution": distribution(vertex_counts),
        "relative_area_error": distribution(area_errors),
        "hausdorff_distance_m_web_mercator": (
            distribution(hausdorff_distances) if measure_hausdorff else None
        ),
        "protected_geometry_count": sum(protected_by_reason.values()),
        "protected_by_reason": dict(sorted(protected_by_reason.items())),
        "coordinate_precision_counts": {
            str(key): value for key, value in sorted(precision_counts.items())
        },
        "invalid_geometry_count": 0,
        "empty_geometry_count": 0,
    }


def partition_features(features, strategy):
    partitions = collections.defaultdict(list)
    for item in features:
        metadata = item["metadata"]
        year = metadata["year"]
        province = province_partition(metadata["province"])
        if strategy == "all":
            key = "all"
        elif strategy == "year":
            key = str(year)
        elif strategy == "temporal_blocks":
            key = temporal_block(year)
        elif strategy == "province":
            key = province
        elif strategy == "province_temporal_blocks":
            key = "{}/{}".format(province, temporal_block(year))
        else:
            raise WebBuildError("Unknown partition strategy {}".format(strategy))
        partitions[key].append(item)
    return partitions


def write_partitioned_level(level_dir, features):
    strategies = (
        "all",
        "year",
        "temporal_blocks",
        "province",
        "province_temporal_blocks",
    )
    result = {}
    for strategy in strategies:
        partitions = partition_features(features, strategy)
        strategy_result = {"file_count": len(partitions), "files": []}
        for format_name, extension in (
            ("geojson", "geojson"),
            ("compact_json", "json"),
        ):
            strategy_dir = level_dir / format_name / strategy
            if strategy_dir.exists():
                for stale_path in strategy_dir.rglob("*." + extension):
                    stale_path.unlink()
        for key in sorted(partitions):
            items = partitions[key]
            geojson_payload = {
                "type": "FeatureCollection",
                "features": [item["geojson"] for item in items],
            }
            compact_payload = {
                "schema_version": 1,
                "crs": "EPSG:4326",
                "fields": list(COMPACT_GEOMETRY_FIELDS),
                "features": [item["compact"] for item in items],
            }
            for format_name, extension, payload in (
                ("geojson", "geojson", geojson_payload),
                ("compact_json", "json", compact_payload),
            ):
                path = level_dir / format_name / strategy / (key + "." + extension)
                encoded = json_bytes(payload) + b"\n"
                write_bytes_atomic(path, encoded)
                strategy_result["files"].append(
                    {
                        "partition": key,
                        "format": format_name,
                        "path": str(path.relative_to(level_dir.parent.parent)),
                        "geometry_count": len(items),
                        "bytes": len(encoded),
                        "gzip_bytes": gzip_size(encoded),
                        "sha256": hashlib.sha256(encoded).hexdigest(),
                    }
                )
        for format_name in ("geojson", "compact_json"):
            format_files = [
                item
                for item in strategy_result["files"]
                if item["format"] == format_name
            ]
            strategy_result[format_name] = {
                "file_count": len(format_files),
                "total_bytes": sum(item["bytes"] for item in format_files),
                "total_gzip_bytes": sum(item["gzip_bytes"] for item in format_files),
                "largest_file_bytes": max(item["bytes"] for item in format_files),
                "largest_file_gzip_bytes": max(
                    item["gzip_bytes"] for item in format_files
                ),
                "smallest_file_bytes": min(item["bytes"] for item in format_files),
                "median_file_bytes": percentile(
                    [item["bytes"] for item in format_files], 0.5
                ),
            }
        result[strategy] = strategy_result
    return result


def partition_fire_records(fires, output_dir):
    strategies = ("all", "temporal_blocks", "province")
    result = {}
    for strategy in strategies:
        partitions = collections.defaultdict(list)
        for fire in fires:
            if strategy == "all":
                key = "all"
            elif strategy == "temporal_blocks":
                key = temporal_block(fire["year"])
            else:
                key = province_partition(fire["province"])
            partitions[key].append(fire)
        strategy_dir = output_dir / strategy
        if strategy_dir.exists():
            for stale_path in strategy_dir.rglob("*.json"):
                stale_path.unlink()
        files = []
        for key in sorted(partitions):
            path = output_dir / strategy / (key + ".json")
            payload = {
                "schema_version": 1,
                "fires": sorted(partitions[key], key=lambda item: item["fire_id"]),
            }
            encoded = json_bytes(payload) + b"\n"
            write_bytes_atomic(path, encoded)
            files.append(
                {
                    "partition": key,
                    "path": str(path.relative_to(output_dir.parent)),
                    "fire_count": len(partitions[key]),
                    "bytes": len(encoded),
                    "gzip_bytes": gzip_size(encoded),
                    "sha256": hashlib.sha256(encoded).hexdigest(),
                }
            )
        result[strategy] = {
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "total_gzip_bytes": sum(item["gzip_bytes"] for item in files),
            "files": files,
        }
    return result


def parse_tolerances(value):
    tolerances = tuple(sorted({float(item) for item in value.split(",")}))
    if not tolerances or tolerances[0] != 0 or any(item < 0 for item in tolerances):
        raise argparse.ArgumentTypeError("Tolerances must be non-negative and include 0")
    return tolerances


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser(
        description="Build simplified EPSG:4326 derivatives and benchmark their size/error."
    )
    parser.add_argument("--processed-dir", type=Path, default=root / "data/processed/gva")
    parser.add_argument(
        "--audit-report",
        type=Path,
        default=root / "data/processed/gva/duplicate_geometry_report.json",
    )
    parser.add_argument("--output-dir", type=Path, default=root / "data/derived/gva/web")
    parser.add_argument(
        "--tolerances",
        type=parse_tolerances,
        default=DEFAULT_TOLERANCES,
        help="Comma-separated Web Mercator tolerances in metres, including 0",
    )
    parser.add_argument(
        "--recompute-candidates",
        action="store_true",
        help="Ignore a compatible build report and recompute all tolerance metrics",
    )
    return parser.parse_args()


def reusable_candidates(report_path, args, fires_checksum, geometries_checksum):
    if args.recompute_candidates or not report_path.exists():
        return None
    report = load_json(report_path)
    try:
        same_inputs = (
            report["inputs"]["fires"]["sha256"] == fires_checksum
            and report["inputs"]["geometries"]["sha256"]
            == geometries_checksum
            and report["inputs"]["duplicate_geometry_report"]["sha256"]
            == sha256_file(args.audit_report)
            and report["engine"]["coordinate_precision_strategy"]
            == {
                "default_decimal_degrees": WEB_COORDINATE_PRECISIONS[0],
                "validity_fallback_decimal_degrees": WEB_COORDINATE_PRECISIONS[1],
            }
        )
        candidates = report["candidate_tolerances"]
        same_tolerances = [
            item["tolerance_m_web_mercator"] for item in candidates
        ] == list(args.tolerances)
    except (KeyError, TypeError):
        return None
    return candidates if same_inputs and same_tolerances else None


def reusable_geometry_metric_candidates(
    report_path, args, fires_checksum, geometries_checksum
):
    """Reuse precision-independent Hausdorff metrics after serialization changes."""
    if args.recompute_candidates or not report_path.exists():
        return None
    report = load_json(report_path)
    try:
        same_inputs = (
            report["inputs"]["fires"]["sha256"] == fires_checksum
            and report["inputs"]["geometries"]["sha256"] == geometries_checksum
            and report["inputs"]["duplicate_geometry_report"]["sha256"]
            == sha256_file(args.audit_report)
        )
        candidates = report["candidate_tolerances"]
        same_tolerances = [
            item["tolerance_m_web_mercator"] for item in candidates
        ] == list(args.tolerances)
    except (KeyError, TypeError):
        return None
    return candidates if same_inputs and same_tolerances else None


def reusable_level_metrics(report_path, recommendations):
    if not report_path.exists():
        return None
    report = load_json(report_path)
    try:
        previous = report["recommended_levels"]
        for level, recommendation in recommendations.items():
            if (
                previous[level]["tolerance_m_web_mercator"]
                != recommendation["tolerance_m_web_mercator"]
                or previous[level]["max_per_geometry_relative_area_error"]
                != recommendation["max_per_geometry_relative_area_error"]
            ):
                return None
        return report["derived_level_metrics"]
    except (KeyError, TypeError):
        return None


def main():
    if shapely is None:
        raise WebBuildError(
            "Shapely is required: install requirements-web.txt ({})".format(
                SHAPELY_IMPORT_ERROR
            )
        )
    args = parse_args()
    manifest_path = args.processed_dir / "manifest.json"
    manifest = load_json(manifest_path)
    fires_path, fires_checksum = verify_processed_file(
        args.processed_dir, manifest, "fires"
    )
    geometries_path, geometries_checksum = verify_processed_file(
        args.processed_dir, manifest, "geometries"
    )
    fires = load_jsonl(fires_path)
    geometries = load_jsonl(geometries_path)
    audit_report = load_json(args.audit_report)
    fires_by_id = {fire["fire_id"]: fire for fire in fires}
    if len(fires_by_id) != len(fires):
        raise WebBuildError("Duplicate fire_id in normalized input")
    reuse_by_geometry = reuse_index(audit_report)
    if len(reuse_by_geometry) != audit_report["summary"]["features_in_groups"]:
        raise WebBuildError("Incomplete geometry reuse index")
    provenance, provenance_by_geometry = provenance_catalog(geometries)

    shapes = []
    original_vertex_counts = []
    original_ring_counts = []
    original_areas = []
    for record in geometries:
        geometry, ring_records, unassigned_holes, error = construct_ogc_geometry(
            record["geometry"]
        )
        if error or unassigned_holes or geometry is None or not geometry.is_valid:
            raise WebBuildError(
                "Cannot construct valid geometry {}: {}".format(
                    record["geometry_id"], error or "invalid OGC geometry"
                )
            )
        shapes.append(geometry)
        original_vertex_counts.append(geometry_vertex_count(geometry))
        original_ring_counts.append(len(ring_records))
        original_areas.append(geometry.area)

    original_vertex_total = sum(original_vertex_counts)
    report_path = args.output_dir / "build_report.json"
    candidates = reusable_candidates(
        report_path, args, fires_checksum, geometries_checksum
    )
    if candidates is None:
        cached_geometry_candidates = reusable_geometry_metric_candidates(
            report_path, args, fires_checksum, geometries_checksum
        )
        cached_by_tolerance = {
            item["tolerance_m_web_mercator"]: item
            for item in (cached_geometry_candidates or [])
        }
        candidates = []
        for tolerance in args.tolerances:
            print(
                "Evaluating tolerance {} m{}...".format(
                    tolerance,
                    " with cached distance metrics"
                    if tolerance in cached_by_tolerance
                    else "",
                ),
                flush=True,
            )
            candidates.append(
                candidate_metrics(
                    tolerance,
                    geometries,
                    shapes,
                    fires_by_id,
                    provenance_by_geometry,
                    reuse_by_geometry,
                    original_vertex_total,
                    cached_candidate=cached_by_tolerance.get(tolerance),
                )
            )
    else:
        print("Reusing compatible tolerance metrics from {}".format(report_path))
    recommendations = recommend_levels(candidates)
    cached_level_metrics = reusable_level_metrics(report_path, recommendations)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    web_fires = [web_fire_record(fire) for fire in fires]
    fire_partitions = partition_fire_records(
        web_fires, args.output_dir / "fires"
    )
    write_json_atomic(
        args.output_dir / "provenance.json",
        {
            "schema_version": 1,
            "provenance": [provenance[key] for key in sorted(provenance)],
        },
    )

    level_outputs = {}
    built_profiles = {}
    level_metrics = {}
    for level, recommendation in recommendations.items():
        tolerance = recommendation["tolerance_m_web_mercator"]
        area_guard = recommendation["max_per_geometry_relative_area_error"]
        profile_key = (tolerance, area_guard)
        if profile_key not in built_profiles:
            built_profiles[profile_key] = build_level_features(
                tolerance,
                area_guard,
                geometries,
                shapes,
                fires_by_id,
                provenance_by_geometry,
                reuse_by_geometry,
                measure_hausdorff=cached_level_metrics is None,
            )
        features, metrics = built_profiles[profile_key]
        if cached_level_metrics is not None:
            metrics["hausdorff_distance_m_web_mercator"] = cached_level_metrics[
                level
            ]["hausdorff_distance_m_web_mercator"]
        metrics["vertex_reduction_percent"] = (
            (original_vertex_total - metrics["vertex_count"])
            / original_vertex_total
            * 100
        )
        level_metrics[level] = metrics
        print("Writing {} level at {} m...".format(level, tolerance), flush=True)
        level_outputs[level] = write_partitioned_level(
            args.output_dir / "levels" / level,
            features,
        )

    report = {
        "schema_version": 1,
        "build_version": BUILD_VERSION,
        "report_type": "gva_web_dataset_simplification_and_partition_benchmark",
        "inputs": {
            "processed_manifest": {
                "path": str(manifest_path.relative_to(repository_root())),
                "sha256": sha256_file(manifest_path),
            },
            "fires": {"path": fires_path.name, "sha256": fires_checksum},
            "geometries": {
                "path": geometries_path.name,
                "sha256": geometries_checksum,
            },
            "duplicate_geometry_report": {
                "path": str(args.audit_report.relative_to(repository_root())),
                "sha256": sha256_file(args.audit_report),
            },
            "normalized_inputs_modified": False,
        },
        "engine": {
            "shapely_version": shapely.__version__,
            "geos_version": shapely.geos_version_string,
            "source_crs": "EPSG:3857 (ArcGIS wkid 102100/latestWkid 3857)",
            "web_crs": "EPSG:4326",
            "simplification": "Shapely simplify(preserve_topology=True)",
            "coordinate_precision_strategy": {
                "default_decimal_degrees": WEB_COORDINATE_PRECISIONS[0],
                "validity_fallback_decimal_degrees": WEB_COORDINATE_PRECISIONS[1],
            },
        },
        "baseline": {
            "fire_count": len(fires),
            "geometry_count": len(geometries),
            "original_vertex_count": original_vertex_total,
            "original_vertex_distribution": distribution(original_vertex_counts),
            "original_ring_count": sum(original_ring_counts),
            "original_ring_distribution": distribution(original_ring_counts),
            "original_planar_area_m2_web_mercator_distribution": distribution(
                original_areas
            ),
            "normalized_file_sizes": {
                "fires_bytes": fires_path.stat().st_size,
                "geometries_bytes": geometries_path.stat().st_size,
                "total_bytes": fires_path.stat().st_size + geometries_path.stat().st_size,
            },
            "geometry_reuse_marked_count": len(reuse_by_geometry),
        },
        "candidate_tolerances": candidates,
        "recommended_levels": recommendations,
        "derived_level_metrics": level_metrics,
        "web_schema": {
            "geometry_properties": [
                "geometry_id",
                "fire_id",
                "year",
                "province",
                "source",
                "provenance_id",
                "geometry_reused",
                "geometry_reuse_group",
            ],
            "fire_attributes_separate": True,
            "original_attributes_included": False,
            "provenance_catalog_separate": True,
            "geometry_deduplicated": False,
        },
        "fire_partitions": fire_partitions,
        "level_partition_outputs": level_outputs,
        "partition_strategy_definitions": {
            "all": "One file for all 13,739 geometries.",
            "year": "One file per source year (32 files).",
            "temporal_blocks": "1993-1999 plus one file per subsequent decade.",
            "province": "One file for each of the three provinces.",
            "province_temporal_blocks": (
                "Province plus temporal block; at most 12 simple partitions."
            ),
        },
        "safety": {
            "empty_or_collapsed_output_geometries": 0,
            "per_geometry_area_error_guards_enabled": True,
            "geometry_repair_performed": False,
            "normalized_files_modified": False,
            "equal_geometries_deduplicated": False,
        },
    }
    write_json_atomic(report_path, report, pretty=True)
    print(
        "Built web derivatives for {} fires / {} geometries; report: {}".format(
            len(fires), len(geometries), report_path
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("web dataset build interrupted; normalized inputs were not modified", file=sys.stderr)
        sys.exit(130)
    except (WebBuildError, AuditError, OSError, ValueError, TypeError) as error:
        print("web dataset build error: {}".format(error), file=sys.stderr)
        sys.exit(1)
