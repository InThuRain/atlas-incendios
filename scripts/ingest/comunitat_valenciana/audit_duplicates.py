#!/usr/bin/env python3
"""Audit equivalent ICV geometries, identity patterns, dates and OGC validity."""

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import shapely
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.validation import explain_validity
except ImportError as error:  # pragma: no cover - exercised by users without audit deps
    shapely = None
    SHAPELY_IMPORT_ERROR = error
else:
    SHAPELY_IMPORT_ERROR = None


AUDIT_VERSION = 1
DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")
IDENTITY_FIELDS = {"OBJECTID", "NumPIF_CV", "NumPIF_Min", "anyo"}
NON_EVENT_FIELDS = IDENTITY_FIELDS | {"shape_Leng"}
SUBSTANTIAL_FIELDS = (
    "nom_mun",
    "paraje",
    "f_detec",
    "fextinc",
    "g_caus_txt",
    "sup_f",
)
CSV_FIELDS = (
    "group_id",
    "geometry_equivalence_checksum_sha256",
    "primary_category",
    "pattern_codes",
    "group_feature_count",
    "group_years",
    "group_year_span",
    "substantially_different_fields",
    "source_year",
    "layer_id",
    "OBJECTID",
    "NumPIF_CV",
    "NumPIF_Min",
    "municipality",
    "place_name",
    "detection_date",
    "extinction_date",
    "cause",
    "reported_forest_area_ha",
    "geometry_id",
    "fire_id",
    "raw_geometry_checksum_sha256",
    "topology_valid",
    "topology_validity_reason",
    "constructed_ogc_type",
)


class AuditError(RuntimeError):
    """Raised when the audit inputs or results are incomplete."""


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


def sha256_value(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


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
        raise AuditError("Invalid JSON file {}: {}".format(path, error))


def load_jsonl(path):
    records = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise AuditError(
                        "Invalid JSONL at {}:{}: {}".format(path, line_number, error)
                    )
    except (OSError, UnicodeDecodeError) as error:
        raise AuditError("Cannot read {}: {}".format(path, error))
    return records


def write_json_atomic(path, payload):
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_csv_atomic(path, groups):
    temporary = path.with_name(path.name + ".part")
    row_count = 0
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for group in groups:
                for feature in group["features"]:
                    row = {
                        "group_id": group["group_id"],
                        "geometry_equivalence_checksum_sha256": group[
                            "geometry_equivalence_checksum_sha256"
                        ],
                        "primary_category": group["classification"][
                            "primary_category"
                        ],
                        "pattern_codes": "|".join(
                            group["classification"]["pattern_codes"]
                        ),
                        "group_feature_count": group["feature_count"],
                        "group_years": "|".join(map(str, group["years"])),
                        "group_year_span": group["temporal_analysis"]["year_span"],
                        "substantially_different_fields": "|".join(
                            group["attribute_comparison"][
                                "substantially_different_fields"
                            ]
                        ),
                        "topology_valid": feature["topology"]["is_valid"],
                        "topology_validity_reason": feature["topology"][
                            "validity_reason"
                        ],
                        "constructed_ogc_type": feature["topology"][
                            "constructed_ogc_type"
                        ],
                    }
                    row.update(
                        {
                            field: feature.get(field)
                            for field in CSV_FIELDS
                            if field not in row
                        }
                    )
                    writer.writerow(row)
                    row_count += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return row_count


def verify_processed_file(processed_dir, manifest, key):
    entry = manifest["outputs"][key]
    path = processed_dir / entry["path"]
    if not path.is_file():
        raise AuditError("Missing processed file: {}".format(path))
    if path.stat().st_size != entry["file_size_bytes"]:
        raise AuditError("Processed file size differs from manifest: {}".format(path))
    checksum = sha256_file(path)
    if checksum != entry["sha256"]:
        raise AuditError("Processed file checksum differs from manifest: {}".format(path))
    return path, checksum


def parse_date(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, None
    text = str(value).strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date(), None
        except ValueError:
            continue
    return None, "Unsupported date value: {!r}".format(value)


def year_from_identifier(value):
    match = re.match(r"^(\d{4})", str(value or ""))
    return int(match.group(1)) if match else None


def distinct_values(records, field):
    values = {}
    for record in records:
        value = record["attributes"].get(field)
        values[canonical_json(value)] = value
    return [values[key] for key in sorted(values)]


def signed_ring_area(coordinates):
    return sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(coordinates, coordinates[1:])
    ) / 2.0


def xy_ring(raw_ring):
    return [(position[0], position[1]) for position in raw_ring]


def construct_ogc_geometry(esri_geometry):
    """Construct a Shapely view using Esri ring orientation; never repair it."""
    rings = esri_geometry.get("rings") or []
    ring_records = []
    shells = []
    holes = []
    for index, raw_ring in enumerate(rings):
        coordinates = xy_ring(raw_ring)
        area = signed_ring_area(coordinates)
        orientation = "clockwise" if area < 0 else "counterclockwise" if area > 0 else "zero_area"
        repeated_consecutive = sum(
            first == second for first, second in zip(coordinates, coordinates[1:])
        )
        ring_record = {
            "ring_index": index,
            "position_count": len(coordinates),
            "distinct_vertex_count": len(set(coordinates[:-1])),
            "orientation": orientation,
            "signed_area": area,
            "closed": bool(coordinates) and coordinates[0] == coordinates[-1],
            "repeated_consecutive_position_count": repeated_consecutive,
        }
        try:
            ring_polygon = Polygon(coordinates)
            ring_record["ring_is_simple"] = ring_polygon.exterior.is_simple
            ring_record["ring_validity_reason"] = explain_validity(ring_polygon)
        except Exception as error:  # GEOS construction diagnostic, not repair
            ring_polygon = None
            ring_record["ring_is_simple"] = False
            ring_record["ring_validity_reason"] = "Construction error: {}".format(error)
        ring_records.append(ring_record)
        item = {"index": index, "coordinates": coordinates, "polygon": ring_polygon}
        if area < 0:
            shells.append(item)
        else:
            holes.append(item)

    if not shells:
        return None, ring_records, [], "No clockwise exterior ring"

    shell_holes = {shell["index"]: [] for shell in shells}
    unassigned_holes = []
    for hole in holes:
        if hole["polygon"] is None or hole["polygon"].is_empty:
            unassigned_holes.append(hole["index"])
            continue
        candidates = [
            shell
            for shell in shells
            if shell["polygon"] is not None
            and shell["polygon"].covers(hole["polygon"])
        ]
        if not candidates:
            unassigned_holes.append(hole["index"])
            continue
        parent = min(candidates, key=lambda shell: abs(shell["polygon"].area))
        shell_holes[parent["index"]].append(hole["coordinates"])

    if unassigned_holes:
        return (
            None,
            ring_records,
            unassigned_holes,
            "Interior rings could not be assigned to a clockwise exterior ring",
        )

    polygons = [
        Polygon(shell["coordinates"], shell_holes[shell["index"]])
        for shell in shells
    ]
    geometry = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
    return geometry, ring_records, [], None


def validity_reason_category(reason):
    return re.sub(r"\[[^\]]*\]$", "", reason or "Unknown").strip()


def topology_audit(geometry_records):
    results = {}
    reason_counts = collections.Counter()
    ring_orientation_counts = collections.Counter()
    invalid_records = []
    constructed_type_counts = collections.Counter()
    summary_counts = collections.Counter()

    for record in geometry_records:
        geometry, ring_records, unassigned_holes, construction_error = (
            construct_ogc_geometry(record["geometry"])
        )
        for ring in ring_records:
            ring_orientation_counts[ring["orientation"]] += 1
        summary_counts["ring_count"] += len(ring_records)
        summary_counts["ring_self_intersection_count"] += sum(
            not ring["ring_is_simple"] for ring in ring_records
        )
        summary_counts["rings_with_repeated_consecutive_positions"] += sum(
            ring["repeated_consecutive_position_count"] > 0 for ring in ring_records
        )
        summary_counts["zero_area_ring_count"] += sum(
            ring["orientation"] == "zero_area" for ring in ring_records
        )
        summary_counts["unassigned_hole_count"] += len(unassigned_holes)
        summary_counts["multiple_ring_geometry_count"] += len(ring_records) > 1

        if geometry is None:
            is_valid = False
            reason = construction_error
            constructed_type = None
            exterior_count = sum(
                ring["orientation"] == "clockwise" for ring in ring_records
            )
            hole_count = sum(
                ring["orientation"] == "counterclockwise" for ring in ring_records
            )
        else:
            is_valid = geometry.is_valid
            reason = explain_validity(geometry)
            constructed_type = geometry.geom_type
            constructed_type_counts[constructed_type] += 1
            exterior_count = 1 if constructed_type == "Polygon" else len(geometry.geoms)
            hole_count = sum(
                len(polygon.interiors)
                for polygon in (
                    [geometry] if constructed_type == "Polygon" else geometry.geoms
                )
            )
        summary_counts["multiple_exterior_geometry_count"] += exterior_count > 1
        summary_counts["geometry_with_interior_rings_count"] += hole_count > 0

        result = {
            "is_valid": bool(is_valid),
            "validity_reason": reason,
            "validity_reason_category": validity_reason_category(reason),
            "constructed_ogc_type": constructed_type,
            "ring_count": len(ring_records),
            "exterior_ring_count": exterior_count,
            "interior_ring_count": hole_count,
            "unassigned_hole_ring_indices": unassigned_holes,
            "rings_with_self_intersection": [
                ring["ring_index"] for ring in ring_records if not ring["ring_is_simple"]
            ],
            "rings_with_repeated_consecutive_positions": [
                ring["ring_index"]
                for ring in ring_records
                if ring["repeated_consecutive_position_count"] > 0
            ],
            "ring_orientation_counts": dict(
                sorted(
                    collections.Counter(
                        ring["orientation"] for ring in ring_records
                    ).items()
                )
            ),
        }
        results[record["geometry_id"]] = result
        if is_valid:
            summary_counts["valid_geometry_count"] += 1
        else:
            summary_counts["invalid_geometry_count"] += 1
            reason_counts[result["validity_reason_category"]] += 1
            invalid_records.append(
                {
                    "geometry_id": record["geometry_id"],
                    "fire_id": record["fire_id"],
                    "source_year": record["source_year"],
                    "source_layer_id": record["source_layer_id"],
                    "source_objectid": record["source_objectid"],
                    "NumPIF_CV": record["num_pif_cv"],
                    "NumPIF_Min": record["num_pif_min"],
                    **result,
                }
            )

    invalid_records.sort(
        key=lambda item: (
            item["source_year"], item["source_layer_id"], item["source_objectid"]
        )
    )
    return results, {
        "engine": {
            "library": "Shapely",
            "shapely_version": shapely.__version__,
            "geos_version": shapely.geos_version_string,
        },
        "method": (
            "Esri rings are interpreted using documented orientation: clockwise shells "
            "and counterclockwise holes. A Shapely Polygon or MultiPolygon is constructed "
            "without make_valid, buffer, simplification or coordinate changes."
        ),
        "geometry_count": len(geometry_records),
        "valid_geometry_count": summary_counts["valid_geometry_count"],
        "invalid_geometry_count": summary_counts["invalid_geometry_count"],
        "invalid_reason_counts": dict(sorted(reason_counts.items())),
        "self_intersection_geometry_count": sum(
            count for reason, count in reason_counts.items() if "Self-intersection" in reason
        ),
        "ring_count": summary_counts["ring_count"],
        "multiple_ring_geometry_count": summary_counts[
            "multiple_ring_geometry_count"
        ],
        "multiple_exterior_geometry_count": summary_counts[
            "multiple_exterior_geometry_count"
        ],
        "geometry_with_interior_rings_count": summary_counts[
            "geometry_with_interior_rings_count"
        ],
        "ring_orientation_counts": dict(sorted(ring_orientation_counts.items())),
        "ring_self_intersection_count": summary_counts[
            "ring_self_intersection_count"
        ],
        "rings_with_repeated_consecutive_positions": summary_counts[
            "rings_with_repeated_consecutive_positions"
        ],
        "zero_area_ring_count": summary_counts["zero_area_ring_count"],
        "unassigned_hole_count": summary_counts["unassigned_hole_count"],
        "constructed_ogc_type_counts": dict(sorted(constructed_type_counts.items())),
        "invalid_geometries": invalid_records,
        "geometry_repaired": False,
    }


def source_record_map(fire_records):
    records = {}
    for fire in fire_records:
        for source_record in fire["source_records"]:
            locator = (
                source_record["source_year"],
                source_record["source_layer_id"],
                source_record["source_objectid"],
            )
            if locator in records:
                raise AuditError("Duplicate source record locator: {}".format(locator))
            records[locator] = {
                "fire_id": fire["fire_id"],
                "attributes": source_record["original_attributes"],
            }
    return records


def feature_for_group(geometry_record, source_records, topology_results):
    locator = (
        geometry_record["source_year"],
        geometry_record["source_layer_id"],
        geometry_record["source_objectid"],
    )
    source_record = source_records.get(locator)
    if source_record is None:
        raise AuditError("No original attributes for geometry {}".format(locator))
    if source_record["fire_id"] != geometry_record["fire_id"]:
        raise AuditError("Fire linkage differs between processed files for {}".format(locator))
    attributes = source_record["attributes"]
    detection_date, detection_error = parse_date(attributes.get("f_detec"))
    extinction_date, extinction_error = parse_date(attributes.get("fextinc"))
    detection_year = detection_date.year if detection_date else None
    identifier_year = year_from_identifier(attributes.get("NumPIF_CV"))
    return {
        "source_year": geometry_record["source_year"],
        "layer_id": geometry_record["source_layer_id"],
        "OBJECTID": geometry_record["source_objectid"],
        "NumPIF_CV": attributes.get("NumPIF_CV"),
        "NumPIF_Min": attributes.get("NumPIF_Min"),
        "municipality": attributes.get("nom_mun"),
        "place_name": attributes.get("paraje"),
        "detection_date": attributes.get("f_detec"),
        "extinction_date": attributes.get("fextinc"),
        "cause": attributes.get("g_caus_txt"),
        "reported_forest_area_ha": attributes.get("sup_f"),
        "geometry_id": geometry_record["geometry_id"],
        "fire_id": geometry_record["fire_id"],
        "raw_geometry_checksum_sha256": geometry_record[
            "geometry_checksum_sha256"
        ],
        "date_checks": {
            "parsed_detection_date": detection_date.isoformat()
            if detection_date
            else None,
            "parsed_extinction_date": extinction_date.isoformat()
            if extinction_date
            else None,
            "detection_parse_error": detection_error,
            "extinction_parse_error": extinction_error,
            "detection_year": detection_year,
            "NumPIF_CV_year_prefix": identifier_year,
            "detection_year_matches_source_year": (
                detection_year == geometry_record["source_year"]
                if detection_year is not None
                else None
            ),
            "NumPIF_CV_year_matches_detection_year": (
                identifier_year == detection_year
                if identifier_year is not None and detection_year is not None
                else None
            ),
            "NumPIF_CV_year_matches_source_year": (
                identifier_year == geometry_record["source_year"]
                if identifier_year is not None
                else None
            ),
            "extinction_before_detection": (
                extinction_date < detection_date
                if extinction_date is not None and detection_date is not None
                else None
            ),
        },
        "topology": topology_results[geometry_record["geometry_id"]],
        "attributes": attributes,
    }


def compare_attributes(features):
    source_records = [{"attributes": feature["attributes"]} for feature in features]
    values = {
        field: distinct_values(source_records, field) for field in SUBSTANTIAL_FIELDS
    }
    differing = [field for field, field_values in values.items() if len(field_values) > 1]
    non_identifier_hashes = {
        sha256_value(
            {
                key: value
                for key, value in feature["attributes"].items()
                if key not in NON_EVENT_FIELDS
            }
        )
        for feature in features
    }
    exact_attribute_hashes = {
        sha256_value(feature["attributes"]) for feature in features
    }
    all_fields = sorted(
        {
            field
            for feature in features
            for field in feature["attributes"]
            if field not in NON_EVENT_FIELDS
        }
    )
    non_identifier_differences = {}
    for field in all_fields:
        field_values = distinct_values(source_records, field)
        if len(field_values) > 1:
            non_identifier_differences[field] = field_values
    return {
        "requested_field_values": values,
        "substantially_different_fields": differing,
        "substantial_attributes_identical": not differing,
        "all_non_identifier_attributes_identical": len(non_identifier_hashes) == 1,
        "non_identifier_attribute_differences": non_identifier_differences,
        "all_original_attributes_identical": len(exact_attribute_hashes) == 1,
    }


def classify_group(features, attribute_comparison):
    years = {feature["source_year"] for feature in features}
    identifier_pairs = {
        (feature["NumPIF_CV"], feature["NumPIF_Min"]) for feature in features
    }
    if len(identifier_pairs) == 1:
        primary = "A"
    elif len(years) == 1:
        primary = "B"
    elif len(years) > 1:
        primary = "C"
    else:
        primary = "E"
    patterns = [primary]
    if attribute_comparison["substantially_different_fields"]:
        patterns.append("D")
    if len({feature["raw_geometry_checksum_sha256"] for feature in features}) == 1:
        patterns.append("E_RAW_IDENTICAL")
    else:
        patterns.append("E_RING_REORDERED")
    return {
        "primary_category": primary,
        "pattern_codes": patterns,
        "identifier_pair_count": len(identifier_pairs),
    }


def temporal_group_analysis(features, attribute_comparison):
    years = sorted({feature["source_year"] for feature in features})
    gaps = [right - left for left, right in zip(years, years[1:])]
    detection_dates = sorted(
        {
            feature["date_checks"]["parsed_detection_date"]
            for feature in features
            if feature["date_checks"]["parsed_detection_date"] is not None
        }
    )
    checks = {
        "detection_year_matches_source_year": [
            feature["date_checks"]["detection_year_matches_source_year"]
            for feature in features
        ],
        "NumPIF_CV_year_matches_detection_year": [
            feature["date_checks"]["NumPIF_CV_year_matches_detection_year"]
            for feature in features
        ],
        "NumPIF_CV_year_matches_source_year": [
            feature["date_checks"]["NumPIF_CV_year_matches_source_year"]
            for feature in features
        ],
    }

    strict_republication_evidence = (
        len(years) > 1
        and len(detection_dates) == 1
        and attribute_comparison["substantial_attributes_identical"]
    )
    if len(years) <= 1:
        republication_status = "not_applicable_single_year"
        republication_reason = "The group does not span multiple annual layers."
    elif strict_republication_evidence:
        republication_status = "attribute_candidate_not_confirmed"
        republication_reason = (
            "Detection date and substantial attributes are identical across annual layers, "
            "but no official metadata rule confirms republication."
        )
    else:
        republication_status = "not_supported_by_record_attributes"
        republication_reason = (
            "Detection date or other substantial attributes change between annual layers; "
            "only coordinate reuse is demonstrated."
        )
    return {
        "year_span": years[-1] - years[0],
        "gaps_between_distinct_years": gaps,
        "all_distinct_years_consecutive": bool(gaps) and all(gap == 1 for gap in gaps),
        "detection_dates": detection_dates,
        "detection_dates_identical": len(detection_dates) == 1,
        "detection_dates_change_with_annual_layer": (
            len(detection_dates) > 1
            and all(value is True for value in checks["detection_year_matches_source_year"])
        ),
        "all_detection_years_match_source_year": all(
            value is True for value in checks["detection_year_matches_source_year"]
        ),
        "all_NumPIF_CV_years_match_detection_year": all(
            value is True for value in checks["NumPIF_CV_year_matches_detection_year"]
        ),
        "all_NumPIF_CV_years_match_source_year": all(
            value is True for value in checks["NumPIF_CV_year_matches_source_year"]
        ),
        "republication_assessment": {
            "status": republication_status,
            "criteria": (
                "Candidate requires multiple annual layers, one shared detection date and "
                "identical municipality, place, detection/extinction dates, cause and area."
            ),
            "reason": republication_reason,
            "officially_confirmed": False,
        },
    }


def build_duplicate_groups(geometry_records, source_records, topology_results):
    grouped = collections.defaultdict(list)
    for geometry_record in geometry_records:
        grouped[geometry_record["geometry_equivalence_checksum_sha256"]].append(
            geometry_record
        )

    groups = []
    for checksum, records in grouped.items():
        if len(records) < 2:
            continue
        records.sort(
            key=lambda item: (
                item["source_year"], item["source_layer_id"], item["source_objectid"]
            )
        )
        features = [
            feature_for_group(record, source_records, topology_results)
            for record in records
        ]
        comparison = compare_attributes(features)
        classification = classify_group(features, comparison)
        temporal_analysis = temporal_group_analysis(features, comparison)
        group = {
            "group_id": "gva:equivalent-geometry:{}".format(checksum[:16]),
            "geometry_equivalence_checksum_sha256": checksum,
            "equivalence_method": records[0]["geometry_equivalence_method"],
            "feature_count": len(features),
            "years": sorted({feature["source_year"] for feature in features}),
            "NumPIF_CV_values": sorted(
                {feature["NumPIF_CV"] for feature in features}, key=str
            ),
            "NumPIF_Min_values": sorted(
                {feature["NumPIF_Min"] for feature in features}, key=str
            ),
            "classification": classification,
            "attribute_comparison": comparison,
            "temporal_analysis": temporal_analysis,
            "topology_summary": {
                "valid_feature_count": sum(
                    feature["topology"]["is_valid"] for feature in features
                ),
                "invalid_feature_count": sum(
                    not feature["topology"]["is_valid"] for feature in features
                ),
                "validity_reasons": sorted(
                    {feature["topology"]["validity_reason"] for feature in features}
                ),
            },
            "features": features,
        }
        for feature in group["features"]:
            feature.pop("attributes")
        groups.append(group)
    groups.sort(key=lambda group: group["geometry_equivalence_checksum_sha256"])
    return groups


def temporal_dataset_audit(source_records):
    unparsed = []
    end_before_start = []
    for locator, source_record in sorted(source_records.items()):
        attributes = source_record["attributes"]
        detection, detection_error = parse_date(attributes.get("f_detec"))
        extinction, extinction_error = parse_date(attributes.get("fextinc"))
        for field, value, error in (
            ("f_detec", attributes.get("f_detec"), detection_error),
            ("fextinc", attributes.get("fextinc"), extinction_error),
        ):
            if error:
                unparsed.append(
                    {
                        "source_year": locator[0],
                        "layer_id": locator[1],
                        "OBJECTID": locator[2],
                        "NumPIF_CV": attributes.get("NumPIF_CV"),
                        "field": field,
                        "value": value,
                        "error": error,
                    }
                )
        if detection and extinction and extinction < detection:
            end_before_start.append(
                {
                    "source_year": locator[0],
                    "layer_id": locator[1],
                    "OBJECTID": locator[2],
                    "NumPIF_CV": attributes.get("NumPIF_CV"),
                    "NumPIF_Min": attributes.get("NumPIF_Min"),
                    "detection_date": attributes.get("f_detec"),
                    "extinction_date": attributes.get("fextinc"),
                    "day_difference": (extinction - detection).days,
                }
            )
    return {
        "feature_count_checked": len(source_records),
        "unparsed_date_value_count": len(unparsed),
        "unparsed_date_values": unparsed,
        "extinction_before_detection_count": len(end_before_start),
        "extinction_before_detection": end_before_start,
        "known_2019VL0147_is_isolated": (
            len(end_before_start) == 1
            and end_before_start[0]["NumPIF_CV"] == "2019VL0147"
            and end_before_start[0]["OBJECTID"] == 755
        ),
    }


def representative_groups(groups, limit=20):
    selected = collections.OrderedDict()

    def add(group, reason):
        item = selected.setdefault(
            group["group_id"],
            {
                "group_id": group["group_id"],
                "primary_category": group["classification"]["primary_category"],
                "feature_count": group["feature_count"],
                "years": group["years"],
                "year_span": group["temporal_analysis"]["year_span"],
                "NumPIF_CV_values": group["NumPIF_CV_values"],
                "substantially_different_fields": group["attribute_comparison"][
                    "substantially_different_fields"
                ],
                "invalid_geometry_count": group["topology_summary"][
                    "invalid_feature_count"
                ],
                "selection_reasons": [],
            },
        )
        if reason not in item["selection_reasons"]:
            item["selection_reasons"].append(reason)

    for group in groups:
        if group["classification"]["primary_category"] == "A":
            add(group, "same identifiers with multiple source geometries")
    for group in groups:
        if not group["attribute_comparison"]["substantially_different_fields"]:
            add(group, "substantial attributes coincide despite coordinate reuse")
    for group in sorted(groups, key=lambda item: (-item["feature_count"], item["group_id"]))[:8]:
        add(group, "largest coordinate-equivalence group")
    for group in sorted(
        groups,
        key=lambda item: (-item["temporal_analysis"]["year_span"], item["group_id"]),
    )[:8]:
        add(group, "longest cross-year span")
    for group in sorted(
        (item for item in groups if item["topology_summary"]["invalid_feature_count"]),
        key=lambda item: (-item["topology_summary"]["invalid_feature_count"], item["group_id"]),
    )[:8]:
        add(group, "contains OGC-invalid geometry")
    for group in sorted(
        (item for item in groups if item["classification"]["primary_category"] == "B"),
        key=lambda item: (-item["feature_count"], item["group_id"]),
    )[:8]:
        add(group, "same-year reuse under different identifiers")
    return list(selected.values())[:limit]


def summary_for_groups(groups, all_years):
    primary_counts = collections.Counter()
    primary_feature_counts = collections.Counter()
    pattern_counts = collections.Counter()
    pattern_feature_counts = collections.Counter()
    years = collections.defaultdict(lambda: {"groups": 0, "features": 0})
    republication_counts = collections.Counter()
    multiyear_republication_counts = collections.Counter()
    multiyear_patterns = collections.Counter()
    substantial_difference_fields = collections.Counter()
    multiyear_span_distribution = collections.Counter()

    for group in groups:
        primary = group["classification"]["primary_category"]
        primary_counts[primary] += 1
        primary_feature_counts[primary] += group["feature_count"]
        for pattern in group["classification"]["pattern_codes"]:
            pattern_counts[pattern] += 1
            pattern_feature_counts[pattern] += group["feature_count"]
        for field in group["attribute_comparison"][
            "substantially_different_fields"
        ]:
            substantial_difference_fields[field] += 1
        for year in group["years"]:
            years[year]["groups"] += 1
            years[year]["features"] += sum(
                feature["source_year"] == year for feature in group["features"]
            )
        republication_counts[
            group["temporal_analysis"]["republication_assessment"]["status"]
        ] += 1
        if len(group["years"]) > 1:
            temporal = group["temporal_analysis"]
            comparison = group["attribute_comparison"]
            multiyear_republication_counts[
                temporal["republication_assessment"]["status"]
            ] += 1
            multiyear_span_distribution[temporal["year_span"]] += 1
            multiyear_patterns["all_detection_years_match_source_year"] += (
                temporal["all_detection_years_match_source_year"]
            )
            multiyear_patterns["all_NumPIF_CV_years_match_detection_year"] += (
                temporal["all_NumPIF_CV_years_match_detection_year"]
            )
            multiyear_patterns["detection_dates_identical"] += temporal[
                "detection_dates_identical"
            ]
            multiyear_patterns["detection_dates_change_with_annual_layer"] += temporal[
                "detection_dates_change_with_annual_layer"
            ]
            multiyear_patterns["substantial_attributes_identical"] += comparison[
                "substantial_attributes_identical"
            ]
            multiyear_patterns["all_non_identifier_attributes_identical"] += comparison[
                "all_non_identifier_attributes_identical"
            ]
            multiyear_patterns["all_distinct_years_consecutive"] += temporal[
                "all_distinct_years_consecutive"
            ]

    return {
        "equivalent_geometry_group_count": len(groups),
        "features_in_groups": sum(group["feature_count"] for group in groups),
        "multiyear_group_count": sum(len(group["years"]) > 1 for group in groups),
        "classification": {
            "primary_category_group_counts": dict(sorted(primary_counts.items())),
            "primary_category_feature_counts": dict(
                sorted(primary_feature_counts.items())
            ),
            "overlapping_pattern_group_counts": dict(sorted(pattern_counts.items())),
            "overlapping_pattern_feature_counts": dict(
                sorted(pattern_feature_counts.items())
            ),
        },
        "republication_assessment_counts_all_groups": dict(
            sorted(republication_counts.items())
        ),
        "multiyear_republication_assessment_counts": dict(
            sorted(multiyear_republication_counts.items())
        ),
        "multiyear_temporal_pattern_group_counts": dict(
            sorted(multiyear_patterns.items())
        ),
        "substantial_difference_field_group_counts": dict(
            sorted(substantial_difference_fields.items())
        ),
        "multiyear_span_distribution": [
            {"span_years": span, "group_count": count}
            for span, count in sorted(multiyear_span_distribution.items())
        ],
        "year_distribution": [
            {"year": year, **years[year]} for year in sorted(all_years)
        ],
        "representative_or_unusual_cases": representative_groups(groups),
    }


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser(
        description="Audit ICV coordinate-equivalent geometries and OGC validity."
    )
    parser.add_argument("--processed-dir", type=Path, default=root / "data/processed/gva")
    parser.add_argument(
        "--metadata-audit",
        type=Path,
        default=root / "data/sources/icv_metadata_audit.json",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=root / "data/processed/gva/duplicate_geometry_report.json",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=root / "data/processed/gva/duplicate_geometry_report.csv",
    )
    return parser.parse_args()


def main():
    if shapely is None:
        raise AuditError(
            "Shapely is required: install requirements-audit.txt ({})".format(
                SHAPELY_IMPORT_ERROR
            )
        )
    args = parse_args()
    manifest_path = args.processed_dir / "manifest.json"
    prior_report_path = args.processed_dir / "report.json"
    manifest = load_json(manifest_path)
    prior_report = load_json(prior_report_path)
    fires_path, fires_checksum = verify_processed_file(
        args.processed_dir, manifest, "fires"
    )
    geometries_path, geometries_checksum = verify_processed_file(
        args.processed_dir, manifest, "geometries"
    )
    fires = load_jsonl(fires_path)
    geometries = load_jsonl(geometries_path)
    if len(fires) != manifest["outputs"]["fires"]["record_count"]:
        raise AuditError("Fire record count differs from processed manifest")
    if len(geometries) != manifest["outputs"]["geometries"]["record_count"]:
        raise AuditError("Geometry record count differs from processed manifest")
    for geometry in geometries:
        if sha256_value(geometry["geometry"]) != geometry["geometry_checksum_sha256"]:
            raise AuditError(
                "Embedded geometry checksum mismatch: {}".format(
                    geometry["geometry_id"]
                )
            )

    source_records = source_record_map(fires)
    if len(source_records) != len(geometries):
        raise AuditError("Source-record and geometry counts differ")
    topology_results, topology_summary = topology_audit(geometries)
    groups = build_duplicate_groups(geometries, source_records, topology_results)
    if len(groups) != 296:
        raise AuditError("Expected 296 equivalent-geometry groups; found {}".format(len(groups)))
    summary = summary_for_groups(
        groups, {geometry["source_year"] for geometry in geometries}
    )
    if summary["features_in_groups"] != 1823:
        raise AuditError(
            "Expected 1,823 features in equivalent groups; found {}".format(
                summary["features_in_groups"]
            )
        )
    if summary["multiyear_group_count"] != 263:
        raise AuditError(
            "Expected 263 multiyear groups; found {}".format(
                summary["multiyear_group_count"]
            )
        )

    metadata_audit = load_json(args.metadata_audit)
    temporal_audit = temporal_dataset_audit(source_records)
    report = {
        "schema_version": 1,
        "audit_version": AUDIT_VERSION,
        "report_type": "gva_icv_duplicate_geometry_identity_and_topology_audit",
        "reproducibility": {
            "generated_at_omitted_for_deterministic_output": True,
            "input_files": {
                "processed_manifest": {
                    "path": str(manifest_path.relative_to(repository_root())),
                    "sha256": sha256_file(manifest_path),
                },
                "fires": {"path": fires_path.name, "sha256": fires_checksum},
                "geometries": {
                    "path": geometries_path.name,
                    "sha256": geometries_checksum,
                },
                "metadata_audit": {
                    "path": str(args.metadata_audit.relative_to(repository_root())),
                    "sha256": sha256_file(args.metadata_audit),
                },
            },
            "fires_or_geometries_modified": False,
        },
        "classification_definitions": {
            "primary_categories_are_mutually_exclusive": True,
            "A": "Same exact coordinate geometry and the same NumPIF_CV/NumPIF_Min pair.",
            "B": "Same exact coordinate geometry under different identifier pairs within one source year.",
            "C": "Same exact coordinate geometry under different identifier pairs across multiple source years.",
            "E": "Other identity pattern not covered by A-C.",
            "overlapping_patterns": {
                "D": (
                    "At least one substantial field differs: municipality, place, detection "
                    "date, extinction date, cause or declared forest area."
                ),
                "E_RAW_IDENTICAL": "Canonical original geometry objects have the same checksum.",
                "E_RING_REORDERED": (
                    "Coordinates are equivalent only after ignoring ring start, orientation "
                    "or order."
                ),
            },
        },
        "summary": summary,
        "official_metadata_research": metadata_audit,
        "temporal_consistency": temporal_audit,
        "topological_validation": {
            "previous_structural_validation": prior_report["geometry_validation"][
                "raw_structural_checks"
            ],
            "structural_vs_ogc_note": (
                "The previous checks validate JSON/ring structure only. OGC validity below "
                "also tests spatial relationships such as self-intersection, nested shells "
                "and hole/shell consistency."
            ),
            **topology_summary,
        },
        "identity_implication": (
            "Coordinate equality alone does not change the current fire_id rule. Distinct "
            "NumPIF identifiers remain distinct fires; the sole category-A case remains one "
            "fire with two preserved geometry records."
        ),
        "recurrence_implication": (
            "Equivalent coordinates must not be counted as proof of recurrent burning. "
            "Future recurrence calculations need event identity plus a policy for exact "
            "geometry reuse and topologically invalid geometries."
        ),
        "groups": groups,
    }

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(args.json_output, report)
    csv_row_count = write_csv_atomic(args.csv_output, groups)
    if csv_row_count != summary["features_in_groups"]:
        raise AuditError("CSV row count does not match features in duplicate groups")
    validated_report = load_json(args.json_output)
    if len(validated_report["groups"]) != 296:
        raise AuditError("Written JSON report lost duplicate groups")
    print(
        "Audited {} geometries: {} valid, {} invalid; {} duplicate groups / {} CSV rows".format(
            len(geometries),
            topology_summary["valid_geometry_count"],
            topology_summary["invalid_geometry_count"],
            len(groups),
            csv_row_count,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("audit interrupted; processed source files were not modified", file=sys.stderr)
        sys.exit(130)
    except (AuditError, OSError, ValueError, TypeError) as error:
        print("audit error: {}".format(error), file=sys.stderr)
        sys.exit(1)
