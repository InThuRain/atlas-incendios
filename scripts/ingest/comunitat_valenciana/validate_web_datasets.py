#!/usr/bin/env python3
"""Validate the serialized CV-1.4 web derivatives and their partitions."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

try:
    import shapely
    from shapely.geometry import shape
    from shapely.validation import explain_validity
except ImportError as error:  # pragma: no cover
    shapely = None
    SHAPELY_IMPORT_ERROR = error
else:
    SHAPELY_IMPORT_ERROR = None


class ValidationError(RuntimeError):
    pass


def repository_root():
    return Path(__file__).resolve().parents[3]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--web-dir", type=Path, default=root / "data/derived/gva/web"
    )
    parser.add_argument(
        "--processed-dir", type=Path, default=root / "data/processed/gva"
    )
    return parser.parse_args()


def validate_checksum(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise ValidationError("Checksum mismatch: {}".format(path))


def ids_from_file(path, format_name):
    payload = load_json(path)
    if format_name == "geojson":
        return [feature["properties"]["geometry_id"] for feature in payload["features"]]
    fields = payload["fields"]
    geometry_id_index = fields.index("geometry_id")
    return [feature[geometry_id_index] for feature in payload["features"]]


def main():
    if shapely is None:
        raise ValidationError(
            "Shapely is required: install requirements-web.txt ({})".format(
                SHAPELY_IMPORT_ERROR
            )
        )
    args = parse_args()
    build_report = load_json(args.web_dir / "build_report.json")
    processed_manifest = load_json(args.processed_dir / "manifest.json")
    for key in ("fires", "geometries"):
        entry = processed_manifest["outputs"][key]
        validate_checksum(args.processed_dir / entry["path"], entry["sha256"])

    expected_count = build_report["baseline"]["geometry_count"]
    expected_reused = build_report["baseline"]["geometry_reuse_marked_count"]
    results = {}
    reference_ids = None
    for level in ("local", "regional", "overview"):
        all_path = args.web_dir / "levels" / level / "geojson/all/all.geojson"
        payload = load_json(all_path)
        features = payload["features"]
        ids = [feature["properties"]["geometry_id"] for feature in features]
        if len(features) != expected_count or len(set(ids)) != expected_count:
            raise ValidationError("Feature/ID count mismatch in {}".format(all_path))
        if reference_ids is None:
            reference_ids = set(ids)
        elif set(ids) != reference_ids:
            raise ValidationError("Levels contain different geometry IDs")
        valid_count = 0
        empty_count = 0
        invalid_reasons = {}
        reused_count = 0
        geometry_types = {}
        for feature in features:
            geometry = shape(feature["geometry"])
            geometry_types[geometry.geom_type] = geometry_types.get(geometry.geom_type, 0) + 1
            reused_count += bool(feature["properties"]["geometry_reused"])
            if geometry.is_empty:
                empty_count += 1
            elif geometry.is_valid:
                valid_count += 1
            else:
                reason = explain_validity(geometry)
                invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
        if empty_count or valid_count != expected_count or reused_count != expected_reused:
            raise ValidationError("Geometry validation failed in {}".format(all_path))

        partition_results = {}
        for strategy, strategy_report in build_report["level_partition_outputs"][level].items():
            partition_results[strategy] = {}
            for format_name in ("geojson", "compact_json"):
                files = [
                    item
                    for item in strategy_report["files"]
                    if item["format"] == format_name
                ]
                partition_ids = []
                for item in files:
                    path = args.web_dir / item["path"]
                    validate_checksum(path, item["sha256"])
                    file_ids = ids_from_file(path, format_name)
                    if len(file_ids) != item["geometry_count"]:
                        raise ValidationError("Count mismatch: {}".format(path))
                    partition_ids.extend(file_ids)
                if len(partition_ids) != expected_count or set(partition_ids) != reference_ids:
                    raise ValidationError(
                        "Partition strategy loses/duplicates IDs: {} {}".format(
                            level, strategy
                        )
                    )
                partition_results[strategy][format_name] = {
                    "file_count": len(files),
                    "geometry_count": len(partition_ids),
                    "unique_geometry_id_count": len(set(partition_ids)),
                }
        results[level] = {
            "geometry_count": len(features),
            "unique_geometry_id_count": len(set(ids)),
            "valid_geometry_count_after_epsg4326_rounding": valid_count,
            "invalid_geometry_count_after_epsg4326_rounding": expected_count - valid_count,
            "empty_geometry_count_after_epsg4326_rounding": empty_count,
            "invalid_reasons": invalid_reasons,
            "geometry_types": geometry_types,
            "geometry_reused_marked_count": reused_count,
            "partitions": partition_results,
        }

    report = {
        "schema_version": 1,
        "validation_status": "complete",
        "shapely_version": shapely.__version__,
        "normalized_inputs_checksum_valid": True,
        "raw_or_normalized_modified": False,
        "results": results,
    }
    output_path = args.web_dir / "validation_report.json"
    temporary = output_path.with_name(output_path.name + ".part")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(output_path))
    print(output_path)


if __name__ == "__main__":
    try:
        main()
    except (ValidationError, OSError, KeyError, TypeError, ValueError) as error:
        print("web validation failed: {}".format(error), file=sys.stderr)
        sys.exit(1)
