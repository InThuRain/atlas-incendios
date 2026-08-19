#!/usr/bin/env python3
"""Build the minimal static CV frontend asset set from CV-1.4 derivatives."""

import argparse
import gzip
import hashlib
import json
import os
import shutil
from pathlib import Path


LEVELS = ("overview", "regional", "local")
PROVINCES = ("castellon", "valencia", "alicante")
TEMPORAL_BLOCKS = ("1993-1999", "2000-2009", "2010-2019", "2020-2024")


class AssetBuildError(RuntimeError):
    pass


def repository_root():
    return Path(__file__).resolve().parents[1]


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--derived-dir", type=Path, default=root / "data/derived/gva/web"
    )
    parser.add_argument(
        "--target-dir", type=Path, default=root / "data/web/gva"
    )
    parser.add_argument(
        "--manifest", type=Path, default=root / "config/datasets-gva.json"
    )
    parser.add_argument(
        "--copy-assets",
        action="store_true",
        help="Copy the selected production assets into data/web/gva",
    )
    return parser.parse_args()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_bytes(value, pretty=False):
    if pretty:
        return (
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        ).encode("utf-8")
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def copy_atomic(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    try:
        shutil.copyfile(str(source), str(temporary))
        os.replace(str(temporary), str(target))
    finally:
        if temporary.exists():
            temporary.unlink()


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_metrics(path):
    payload = path.read_bytes()
    return {
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def visit_coordinates(value, bounds):
    if value and isinstance(value[0], (int, float)):
        bounds[0] = min(bounds[0], value[0])
        bounds[1] = min(bounds[1], value[1])
        bounds[2] = max(bounds[2], value[0])
        bounds[3] = max(bounds[3], value[1])
        return
    for item in value:
        visit_coordinates(item, bounds)


def geojson_summary(path):
    payload = load_json(path)
    features = payload.get("features")
    if not isinstance(features, list):
        raise AssetBuildError("Not a GeoJSON FeatureCollection: {}".format(path))
    bounds = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in ("Polygon", "MultiPolygon"):
            raise AssetBuildError("Non-polygon geometry in {}".format(path))
        visit_coordinates(geometry["coordinates"], bounds)
    if any(value in (float("inf"), float("-inf")) for value in bounds):
        raise AssetBuildError("Empty GeoJSON file: {}".format(path))
    return len(features), bounds


def union_bounds(bounds_values):
    return [
        min(item[0] for item in bounds_values),
        min(item[1] for item in bounds_values),
        max(item[2] for item in bounds_values),
        max(item[3] for item in bounds_values),
    ]


def main():
    args = parse_args()
    report = load_json(args.derived_dir / "build_report.json")
    if report["web_schema"]["geometry_deduplicated"]:
        raise AssetBuildError("CV-1.4 geometries unexpectedly deduplicated")

    report_files = {}
    for level in LEVELS:
        strategy = report["level_partition_outputs"][level][
            "province_temporal_blocks"
        ]
        for item in strategy["files"]:
            if item["format"] == "geojson":
                report_files[(level, item["partition"])] = item

    geometry_assets = []
    expected_target_paths = set()
    province_bounds = {province: [] for province in PROVINCES}
    for level in LEVELS:
        for province in PROVINCES:
            for block in TEMPORAL_BLOCKS:
                partition = "{}/{}".format(province, block)
                try:
                    report_entry = report_files[(level, partition)]
                except KeyError:
                    raise AssetBuildError("Missing partition {} {}".format(level, partition))
                source = args.derived_dir / report_entry["path"]
                if sha256(source) != report_entry["sha256"]:
                    raise AssetBuildError("Checksum mismatch: {}".format(source))
                feature_count, bounds = geojson_summary(source)
                if feature_count != report_entry["geometry_count"]:
                    raise AssetBuildError("Feature count mismatch: {}".format(source))
                relative_target = (
                    Path("geometry") / level / province / (block + ".geojson")
                )
                if args.copy_assets:
                    copy_atomic(source, args.target_dir / relative_target)
                expected_target_paths.add((args.target_dir / relative_target).resolve())
                geometry_assets.append(
                    {
                        "level": level,
                        "province": province,
                        "temporal_block": block,
                        "url": "data/web/gva/{}".format(relative_target.as_posix()),
                        "feature_count": feature_count,
                        "bounds": bounds,
                        "bytes": report_entry["bytes"],
                        "gzip_bytes": report_entry["gzip_bytes"],
                        "sha256": report_entry["sha256"],
                    }
                )
                if level == "overview":
                    province_bounds[province].append(bounds)

    static_assets = []
    fires_source = args.derived_dir / "fires/all/all.json"
    provenance_source = args.derived_dir / "provenance.json"
    for name, source, url in (
        ("fires", fires_source, "data/web/gva/fires.json"),
        ("provenance", provenance_source, "data/web/gva/provenance.json"),
    ):
        metrics = file_metrics(source)
        if args.copy_assets:
            target = args.target_dir / (name + ".json")
            copy_atomic(source, target)
            expected_target_paths.add(target.resolve())
        static_assets.append({"name": name, "url": url, **metrics})

    production_raw_bytes = sum(item["bytes"] for item in geometry_assets) + sum(
        item["bytes"] for item in static_assets
    )
    production_gzip_bytes = sum(
        item["gzip_bytes"] for item in geometry_assets
    ) + sum(item["gzip_bytes"] for item in static_assets)
    normalized_province_bounds = {
        province: union_bounds(values)
        for province, values in province_bounds.items()
    }
    cv_bounds = union_bounds(list(normalized_province_bounds.values()))

    manifest = {
        "schema_version": 1,
        "dataset": "gva_icv_wildfire_perimeters_1993_2024_web",
        "years": {"min": 1993, "max": 2024, "default": 2024},
        "crs": "EPSG:4326",
        "source": {
            "label": "Institut Cartogràfic Valencià / Generalitat Valenciana",
            "dataset": "Incendios forestales de la Comunitat Valenciana 1993-2024",
            "dataset_identifier": "spa_icv_ince_incendios",
            "owner": "Servicio de Prevención de Incendios Forestales, Dirección General de Prevención de Incendios Forestales, Generalitat Valenciana",
            "publisher": "Institut Cartogràfic Valencià, Generalitat Valenciana",
            "catalog_url": "https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024",
            "metadata_url": "https://catalogo.icv.gva.es/geonetwork/srv/api/records/spa_icv_ince_incendios/formatters/xml",
            "metadata_revision_date": "2026-07-27",
            "license_id": "CC-BY-4.0",
            "license": "Creative Commons Atribución 4.0 Internacional (CC BY 4.0)",
            "license_url": "https://creativecommons.org/licenses/by/4.0/legalcode",
            "terms_url": "https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv",
            "attribution": "Incendios forestales de la Comunitat Valenciana (1993-2024) CC BY 4.0 © Institut Cartogràfic Valencià, Generalitat",
            "credit": "Servicio de Prevención de Incendios Forestales, Dirección General de Prevención de Incendios Forestales, Generalitat Valenciana; Institut Cartogràfic Valencià, Generalitat Valenciana",
            "access_constraints": "Sin limitaciones al acceso público",
            "informative_and_non_binding": True,
            "complete_inventory": False,
        },
        "derivation": {
            "is_modified": True,
            "modified_by": "Atlas de Incendios",
            "modification_notice": "Derivado modificado por Atlas de Incendios: normalización y separación de incendios y geometrías, reproyección del servicio a EPSG:4326, selección de atributos, particionado y simplificación geométrica multiescala. No es un producto oficial del ICV ni implica respaldo de la Generalitat Valenciana.",
            "operations": [
                "normalization_and_entity_separation",
                "reprojection_to_EPSG_4326",
                "attribute_selection",
                "province_and_temporal_partitioning",
                "topology_preserving_multiscale_simplification",
                "adaptive_coordinate_rounding",
            ],
            "geometry_levels": {
                "local": {"maximum_tolerance_m": 1, "maximum_relative_area_error": 0.01},
                "regional": {"maximum_tolerance_m": 10, "maximum_relative_area_error": 0.05},
                "overview": {"maximum_tolerance_m": 50, "maximum_relative_area_error": 0.15},
            },
            "geometry_repaired": False,
            "geometry_deduplicated": False,
            "original_raw_modified": False,
        },
        "publication": {
            "status": "blocked_pending_icv_clarification",
            "assets_committed": False,
            "license_review_required": True,
            "checked_on": "2026-08-19",
            "data_license_file": "LICENSE_DATA.md",
            "blocking_questions": [
                "how_express_acceptance_by_each_recipient_applies_to_public_static_web_distribution",
                "whether_documented_multiscale_simplification_is_compatible_with_the_no_alteration_or_denaturalisation_condition",
                "confirmation_of_the_attribution_formula_for_this_jointly_credited_dataset",
            ],
            "note": "No publicar los assets hasta obtener aclaración escrita del ICV o del órgano titular sobre aceptación expresa, simplificación y fórmula de atribución.",
        },
        "zoom_levels": {
            "overview": {"min_zoom": 0, "max_zoom": 8},
            "regional": {"min_zoom": 9, "max_zoom": 10},
            "local": {"min_zoom": 11, "max_zoom": 20},
        },
        "temporal_blocks": [
            {"id": "1993-1999", "min_year": 1993, "max_year": 1999},
            {"id": "2000-2009", "min_year": 2000, "max_year": 2009},
            {"id": "2010-2019", "min_year": 2010, "max_year": 2019},
            {"id": "2020-2024", "min_year": 2020, "max_year": 2024},
        ],
        "territories": {
            "comunitat_valenciana": {
                "label": "Comunitat Valenciana",
                "bounds": cv_bounds,
                "provinces": list(PROVINCES),
            },
            "castellon": {
                "label": "Castellón",
                "bounds": normalized_province_bounds["castellon"],
                "provinces": ["castellon"],
            },
            "valencia": {
                "label": "Valencia",
                "bounds": normalized_province_bounds["valencia"],
                "provinces": ["valencia"],
            },
            "alicante": {
                "label": "Alicante",
                "bounds": normalized_province_bounds["alicante"],
                "provinces": ["alicante"],
            },
            "mariola_font_roja": {
                "label": "Mariola–Font Roja",
                "bounds": [-0.91, 38.48, -0.20, 38.93],
                "provinces": ["alicante"],
                "preferred_zoom": 11,
            },
        },
        "attributes": {
            "fires": next(item for item in static_assets if item["name"] == "fires"),
            "provenance": next(
                item for item in static_assets if item["name"] == "provenance"
            ),
        },
        "geometry_assets": geometry_assets,
        "production_subset": {
            "geometry_file_count": len(geometry_assets),
            "static_file_count": len(static_assets),
            "total_file_count": len(geometry_assets) + len(static_assets),
            "raw_bytes": production_raw_bytes,
            "gzip_bytes": production_gzip_bytes,
            "benchmark_matrix_included": False,
            "formats": ["GeoJSON", "JSON"],
        },
    }
    write_atomic(args.manifest, canonical_bytes(manifest, pretty=True))
    if args.copy_assets:
        for path in args.target_dir.rglob("*"):
            if path.is_file() and path.resolve() not in expected_target_paths:
                path.unlink()
        for path in sorted(args.target_dir.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        actual_paths = {
            path.resolve() for path in args.target_dir.rglob("*") if path.is_file()
        }
        if actual_paths != expected_target_paths:
            raise AssetBuildError("Production target does not contain the exact asset set")
        for asset in geometry_assets + static_assets:
            relative_url = Path(asset["url"]).relative_to("data/web/gva")
            if sha256(args.target_dir / relative_url) != asset["sha256"]:
                raise AssetBuildError("Copied asset checksum mismatch: {}".format(relative_url))
    print(
        "Manifest {}: {} production files, {} raw bytes, {} gzip bytes{}".format(
            args.manifest,
            manifest["production_subset"]["total_file_count"],
            production_raw_bytes,
            production_gzip_bytes,
            "; assets copied to {}".format(args.target_dir)
            if args.copy_assets
            else "",
        )
    )


if __name__ == "__main__":
    main()
