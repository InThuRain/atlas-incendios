#!/usr/bin/env python3
"""Normalize raw ICV perimeter features into separate fire and geometry JSONL files."""

import argparse
import collections
import hashlib
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path


SOURCE_DATASET = "gva_icv_wildfire_perimeters_1993_2024"
NORMALIZATION_VERSION = 1
IDENTIFIER_FIELDS = ("OBJECTID", "NumPIF_CV", "NumPIF_Min")
EVENT_COMPARISON_FIELDS = (
    "NumPIF_Min",
    "anyo",
    "ccaa_nom",
    "prov_nom",
    "com_nom",
    "nom_mun",
    "paraje",
    "x",
    "y",
    "f_detec",
    "h_detec",
    "fextinc",
    "hextinc",
    "detecp_txt",
    "g_caus_txt",
    "tot_arb",
    "tot_narb",
    "sup_f",
)
SURFACE_FIELDS = ("tot_arb", "tot_narb", "sup_f")
DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")


class NormalizationError(RuntimeError):
    """Raised when raw inputs cannot be normalized without losing traceability."""


def repository_root():
    return Path(__file__).resolve().parents[3]


def default_raw_dir():
    return repository_root() / "data" / "raw" / "gva"


def default_output_dir():
    return repository_root() / "data" / "processed" / "gva"


def now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def minimum_rotation(tokens):
    """Return the lexicographically smallest cyclic rotation in linear time."""
    if not tokens:
        return tuple()
    doubled = tokens + tokens
    length = len(tokens)
    left, right, offset = 0, 1, 0
    while left < length and right < length and offset < length:
        left_value = doubled[left + offset]
        right_value = doubled[right + offset]
        if left_value == right_value:
            offset += 1
            continue
        if left_value > right_value:
            left = left + offset + 1
            if left <= right:
                left = right + 1
        else:
            right = right + offset + 1
            if right <= left:
                right = left + 1
        offset = 0
    start = min(left, right)
    return tuple(doubled[start : start + length])


def linear_ring_signature(ring):
    if not isinstance(ring, list):
        return None
    positions = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    tokens = [canonical_json(position) for position in positions]
    forward = minimum_rotation(tokens)
    reverse = minimum_rotation(list(reversed(tokens)))
    return min(forward, reverse)


def geometry_equivalence_checksum(geometry):
    """Compare exact linear-ring coordinates while ignoring ring start/order/orientation."""
    rings = geometry.get("rings") if isinstance(geometry, dict) else None
    if isinstance(rings, list):
        signatures = []
        for ring in rings:
            signature = linear_ring_signature(ring)
            if signature is None:
                return sha256_value(geometry), "raw_canonical_json_fallback"
            signatures.append(signature)
        signatures.sort()
        return (
            sha256_value({"linear_ring_coordinate_signatures": signatures}),
            "exact_coordinates_ignoring_ring_start_orientation_and_order",
        )
    return sha256_value(geometry), "raw_canonical_json_fallback"


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
        raise NormalizationError("Invalid JSON file {}: {}".format(path, error))


def write_json_temporary(path, payload, pretty=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            if pretty:
                json.dump(payload, handle, ensure_ascii=False, allow_nan=False, indent=2)
            else:
                handle.write(canonical_json(payload))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return temporary
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def write_jsonl_temporary(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    count = 0
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(canonical_json(record))
                handle.write("\n")
                count += 1
            handle.flush()
            os.fsync(handle.fileno())
        return temporary, count
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def replace_temporary(temporary, destination):
    os.replace(str(temporary), str(destination))


def is_missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def value_key(value):
    return "{}:{}".format(type(value).__name__, canonical_json(value))


def unique_values(records, field):
    values = {}
    for record in records:
        value = record["attributes"].get(field)
        if is_missing(value):
            continue
        values[value_key(value)] = value
    return [values[key] for key in sorted(values)]


def parse_source_date(value):
    if is_missing(value):
        return None, None
    text = str(value).strip()
    for date_format in DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, date_format).date()
            return parsed.isoformat(), None
        except ValueError:
            continue
    return None, "Unsupported date value: {}".format(repr(value))


def namespaced_fire_id(num_pif_cv):
    encoded = urllib.parse.quote(str(num_pif_cv), safe="")
    return "gva:pif-cv:{}".format(encoded)


def fallback_fire_id(record):
    return "gva:source-feature:{}:{}:{}".format(
        record["source_year"], record["source_layer_id"], record["source_objectid"]
    )


def geometry_id(record):
    return "gva:geometry:{}:{}:{}".format(
        record["source_year"], record["source_layer_id"], record["source_objectid"]
    )


def record_locator(record):
    return (
        record["source_year"],
        record["source_layer_id"],
        value_key(record["source_objectid"]),
    )


def raw_manifest_layers(raw_manifest):
    if (raw_manifest.get("completeness") or {}).get("status") != "complete":
        raise NormalizationError("Raw manifest is not complete")
    layers = raw_manifest.get("layers")
    if not isinstance(layers, list) or len(layers) != 32:
        raise NormalizationError("Raw manifest must contain the 32 annual layers")
    years = [layer.get("year") for layer in layers]
    if years != sorted(years) or len(years) != len(set(years)):
        raise NormalizationError("Raw manifest years are missing, duplicated, or unsorted")
    return layers


def verify_raw_file(path, layer_entry):
    if not path.is_file():
        raise NormalizationError("Raw file is missing: {}".format(path))
    expected_size = layer_entry.get("file_size_bytes")
    if path.stat().st_size != expected_size:
        raise NormalizationError("Raw file size differs from manifest: {}".format(path))
    actual_checksum = sha256_file(path)
    if actual_checksum != layer_entry.get("sha256"):
        raise NormalizationError("Raw file checksum differs from manifest: {}".format(path))
    feature_set = load_json(path)
    features = feature_set.get("features")
    if not isinstance(features, list):
        raise NormalizationError("Raw file has no features array: {}".format(path))
    if len(features) != layer_entry.get("feature_count_downloaded"):
        raise NormalizationError("Raw feature count differs from manifest: {}".format(path))
    if feature_set.get("geometryType") != "esriGeometryPolygon":
        raise NormalizationError("Raw layer is not polygonal: {}".format(path))
    return feature_set, actual_checksum


def first_pass(raw_dir, raw_manifest):
    records = []
    field_names_by_year = {}
    raw_files = {}
    raw_feature_count = 0

    for layer in raw_manifest_layers(raw_manifest):
        year = layer["year"]
        raw_path = raw_dir / layer["output_file"]
        feature_set, checksum = verify_raw_file(raw_path, layer)
        field_names = set()

        for source_index, feature in enumerate(feature_set["features"]):
            attributes = feature.get("attributes")
            geometry = feature.get("geometry")
            if not isinstance(attributes, dict):
                raise NormalizationError(
                    "Feature {} in {} has no attributes object".format(source_index, raw_path)
                )
            objectid = attributes.get("OBJECTID")
            if is_missing(objectid):
                raise NormalizationError(
                    "Feature {} in {} has no OBJECTID".format(source_index, raw_path)
                )
            if geometry is None:
                raise NormalizationError(
                    "Feature OBJECTID {} in {} has null geometry".format(objectid, raw_path)
                )

            field_names.update(attributes)
            equivalence_checksum, equivalence_method = geometry_equivalence_checksum(
                geometry
            )
            record = {
                "source_year": year,
                "source_layer_id": layer["layer_id"],
                "source_objectid": objectid,
                "source_index": source_index,
                "source_url": layer["source_url"],
                "retrieved_at": layer["retrieved_at"],
                "raw_file": layer["output_file"],
                "raw_file_sha256": checksum,
                "crs": feature_set.get("spatialReference"),
                "attributes": attributes,
                "geometry_checksum_sha256": sha256_value(geometry),
                "geometry_equivalence_checksum_sha256": equivalence_checksum,
                "geometry_equivalence_method": equivalence_method,
            }
            record["geometry_id"] = geometry_id(record)
            records.append(record)

        field_names_by_year[year] = sorted(field_names)
        raw_feature_count += len(feature_set["features"])
        raw_files[year] = {
            "path": raw_path,
            "entry": layer,
            "crs": feature_set.get("spatialReference"),
        }

    expected_total = (raw_manifest.get("completeness") or {}).get(
        "feature_count_downloaded"
    )
    if raw_feature_count != expected_total:
        raise NormalizationError(
            "Raw total {} differs from manifest total {}".format(
                raw_feature_count, expected_total
            )
        )
    return records, raw_files, field_names_by_year


def identifier_report(records):
    field_reports = {}
    for field in IDENTIFIER_FIELDS:
        grouped = collections.defaultdict(list)
        missing = []
        for record in records:
            value = record["attributes"].get(field)
            if is_missing(value):
                missing.append(
                    {
                        "source_year": record["source_year"],
                        "source_layer_id": record["source_layer_id"],
                        "source_objectid": record["source_objectid"],
                    }
                )
            else:
                grouped[value_key(value)].append(record)
        duplicates = []
        for group in grouped.values():
            if len(group) < 2:
                continue
            duplicates.append(
                {
                    "value": group[0]["attributes"][field],
                    "feature_count": len(group),
                    "source_features": [
                        {
                            "year": record["source_year"],
                            "layer_id": record["source_layer_id"],
                            "OBJECTID": record["source_objectid"],
                        }
                        for record in sorted(group, key=record_locator)
                    ],
                }
            )
        duplicates.sort(key=lambda item: value_key(item["value"]))
        field_reports[field] = {
            "missing_or_blank_count": len(missing),
            "distinct_non_missing_count": len(grouped),
            "duplicate_value_count": len(duplicates),
            "duplicate_values": duplicates,
            "missing_source_features": missing,
        }
    return field_reports


def identifier_relationships(records):
    cv_to_min = collections.defaultdict(dict)
    min_to_cv = collections.defaultdict(dict)

    for record in records:
        cv = record["attributes"].get("NumPIF_CV")
        minimum = record["attributes"].get("NumPIF_Min")
        if is_missing(cv) or is_missing(minimum):
            continue
        cv_to_min[value_key(cv)][value_key(minimum)] = minimum
        min_to_cv[value_key(minimum)][value_key(cv)] = cv

    cv_discrepancies = [
        {
            "NumPIF_CV": next(
                record["attributes"]["NumPIF_CV"]
                for record in records
                if not is_missing(record["attributes"].get("NumPIF_CV"))
                and value_key(record["attributes"]["NumPIF_CV"]) == cv_key
            ),
            "NumPIF_Min_values": [values[key] for key in sorted(values)],
        }
        for cv_key, values in cv_to_min.items()
        if len(values) > 1
    ]
    min_discrepancies = [
        {
            "NumPIF_Min": next(
                record["attributes"]["NumPIF_Min"]
                for record in records
                if not is_missing(record["attributes"].get("NumPIF_Min"))
                and value_key(record["attributes"]["NumPIF_Min"]) == min_key
            ),
            "NumPIF_CV_values": [values[key] for key in sorted(values)],
        }
        for min_key, values in min_to_cv.items()
        if len(values) > 1
    ]
    cv_discrepancies.sort(key=lambda item: value_key(item["NumPIF_CV"]))
    min_discrepancies.sort(key=lambda item: value_key(item["NumPIF_Min"]))
    return {
        "NumPIF_CV_to_multiple_NumPIF_Min": cv_discrepancies,
        "NumPIF_Min_to_multiple_NumPIF_CV": min_discrepancies,
        "one_to_one_for_all_non_missing_identifiers": (
            not cv_discrepancies and not min_discrepancies
        ),
    }, cv_to_min, min_to_cv


def differing_fields(records, fields):
    differences = {}
    for field in fields:
        values = {}
        for record in records:
            value = record["attributes"].get(field)
            values[value_key(value)] = value
        if len(values) > 1:
            differences[field] = [values[key] for key in sorted(values)]
    return differences


def grouping_decisions(records, cv_to_min, min_to_cv):
    by_cv = collections.defaultdict(list)
    missing_cv = []
    for record in records:
        cv = record["attributes"].get("NumPIF_CV")
        if is_missing(cv):
            missing_cv.append(record)
        else:
            by_cv[value_key(cv)].append(record)

    assignments = {}
    groups = []
    ambiguous_cases = []
    duplicate_consistency = []

    for cv_key in sorted(by_cv):
        group = sorted(by_cv[cv_key], key=record_locator)
        cv = group[0]["attributes"]["NumPIF_CV"]
        min_values = unique_values(group, "NumPIF_Min")
        source_years = sorted({record["source_year"] for record in group})
        event_differences = differing_fields(group, EVENT_COMPARISON_FIELDS)
        pair_is_one_to_one = (
            len(min_values) == 1
            and len(cv_to_min.get(cv_key, {})) == 1
            and len(min_to_cv.get(value_key(min_values[0]), {})) == 1
        )
        reasons = []
        if not pair_is_one_to_one:
            reasons.append("NumPIF_CV and NumPIF_Min are not one-to-one")
        if len(source_years) != 1:
            reasons.append("The same NumPIF_CV appears in multiple source years")
        if event_differences:
            reasons.append("Event attributes differ between source features")

        if len(group) > 1:
            duplicate_consistency.append(
                {
                    "NumPIF_CV": cv,
                    "NumPIF_Min_values": min_values,
                    "source_years": source_years,
                    "feature_count": len(group),
                    "event_attribute_differences": event_differences,
                    "geometry_checksums": [
                        record["geometry_checksum_sha256"] for record in group
                    ],
                    "geometry_equivalence_checksums": [
                        record["geometry_equivalence_checksum_sha256"]
                        for record in group
                    ],
                    "geometry_equivalent_under_exact_ring_reordering": (
                        len(
                            {
                                record["geometry_equivalence_checksum_sha256"]
                                for record in group
                            }
                        )
                        == 1
                    ),
                    "source_objectids": [record["source_objectid"] for record in group],
                    "merge_supported": not reasons,
                    "reasons_not_merged": reasons,
                }
            )

        if not reasons:
            fire_id = namespaced_fire_id(cv)
            for record in group:
                assignments[record_locator(record)] = fire_id
            groups.append(
                {
                    "fire_id": fire_id,
                    "records": group,
                    "linkage_rule": (
                        "NumPIF_CV_with_consistent_multiple_source_features"
                        if len(group) > 1
                        else "NumPIF_CV_with_one_to_one_identifier_mapping"
                    ),
                    "ambiguous": False,
                }
            )
        else:
            ambiguous_cases.append(
                {
                    "NumPIF_CV": cv,
                    "source_objectids": [record["source_objectid"] for record in group],
                    "reasons": reasons,
                    "event_attribute_differences": event_differences,
                }
            )
            for record in group:
                fire_id = fallback_fire_id(record)
                assignments[record_locator(record)] = fire_id
                groups.append(
                    {
                        "fire_id": fire_id,
                        "records": [record],
                        "linkage_rule": "source_feature_fallback_due_to_ambiguity",
                        "ambiguous": True,
                    }
                )

    for record in sorted(missing_cv, key=record_locator):
        fire_id = fallback_fire_id(record)
        assignments[record_locator(record)] = fire_id
        groups.append(
            {
                "fire_id": fire_id,
                "records": [record],
                "linkage_rule": "source_feature_fallback_missing_NumPIF_CV",
                "ambiguous": True,
            }
        )
        ambiguous_cases.append(
            {
                "NumPIF_CV": None,
                "source_objectids": [record["source_objectid"]],
                "reasons": ["NumPIF_CV is missing or blank"],
                "event_attribute_differences": {},
            }
        )

    groups.sort(key=lambda group: group["fire_id"])
    return assignments, groups, ambiguous_cases, duplicate_consistency


def normalized_fire(group):
    records = group["records"]
    representative = records[0]
    attributes = representative["attributes"]
    start_date, _ = parse_source_date(attributes.get("f_detec"))
    end_date, _ = parse_source_date(attributes.get("fextinc"))
    num_pif_cv_values = unique_values(records, "NumPIF_CV")
    num_pif_min_values = unique_values(records, "NumPIF_Min")
    geometry_ids = [record["geometry_id"] for record in records]

    return {
        "fire_id": group["fire_id"],
        "num_pif_cv": num_pif_cv_values[0] if len(num_pif_cv_values) == 1 else None,
        "num_pif_min": num_pif_min_values[0] if len(num_pif_min_values) == 1 else None,
        "year": attributes.get("anyo"),
        "start_date": start_date,
        "start_date_raw": attributes.get("f_detec"),
        "end_date": end_date,
        "end_date_raw": attributes.get("fextinc"),
        "detection_time_raw": attributes.get("h_detec"),
        "extinction_time_raw": attributes.get("hextinc"),
        "municipality": attributes.get("nom_mun"),
        "county": attributes.get("com_nom"),
        "province": attributes.get("prov_nom"),
        "autonomous_community": attributes.get("ccaa_nom"),
        "place_name": attributes.get("paraje"),
        "cause": attributes.get("g_caus_txt"),
        "detected_by": attributes.get("detecp_txt"),
        "reported_forest_area_ha": attributes.get("sup_f"),
        "reported_tree_area_ha": attributes.get("tot_arb"),
        "reported_non_tree_area_ha": attributes.get("tot_narb"),
        "source_x": attributes.get("x"),
        "source_y": attributes.get("y"),
        "source_dataset": SOURCE_DATASET,
        "source_year": representative["source_year"],
        "source_identifiers": {
            "NumPIF_CV": num_pif_cv_values,
            "NumPIF_Min": num_pif_min_values,
            "OBJECTID": [record["source_objectid"] for record in records],
        },
        "geometry_ids": geometry_ids,
        "geometry_count": len(geometry_ids),
        "linkage": {
            "status": "ambiguous" if group["ambiguous"] else "linked",
            "rule": group["linkage_rule"],
            "provisional": True,
        },
        "source_records": [
            {
                "source_year": record["source_year"],
                "source_layer_id": record["source_layer_id"],
                "source_objectid": record["source_objectid"],
                "raw_file": record["raw_file"],
                "original_attributes": record["attributes"],
            }
            for record in records
        ],
    }


def date_and_year_diagnostics(records):
    invalid_dates = []
    year_mismatches = []
    end_before_start = []

    for record in records:
        attributes = record["attributes"]
        parsed = {}
        for field in ("f_detec", "fextinc"):
            iso_date, error = parse_source_date(attributes.get(field))
            parsed[field] = iso_date
            if error:
                invalid_dates.append(
                    {
                        "source_year": record["source_year"],
                        "source_objectid": record["source_objectid"],
                        "field": field,
                        "value": attributes.get(field),
                        "error": error,
                    }
                )
        source_attribute_year = attributes.get("anyo")
        if source_attribute_year != record["source_year"]:
            year_mismatches.append(
                {
                    "source_year": record["source_year"],
                    "source_objectid": record["source_objectid"],
                    "anyo": source_attribute_year,
                }
            )
        if parsed["f_detec"] and int(parsed["f_detec"][:4]) != record["source_year"]:
            year_mismatches.append(
                {
                    "source_year": record["source_year"],
                    "source_objectid": record["source_objectid"],
                    "f_detec": attributes.get("f_detec"),
                }
            )
        if (
            parsed["f_detec"]
            and parsed["fextinc"]
            and parsed["fextinc"] < parsed["f_detec"]
        ):
            end_before_start.append(
                {
                    "source_year": record["source_year"],
                    "source_objectid": record["source_objectid"],
                    "f_detec": attributes.get("f_detec"),
                    "fextinc": attributes.get("fextinc"),
                }
            )
    return {
        "unparsed_date_values": invalid_dates,
        "source_year_mismatches": year_mismatches,
        "extinction_before_detection": end_before_start,
    }


def absent_fields_by_year(field_names_by_year):
    all_fields = set()
    for fields in field_names_by_year.values():
        all_fields.update(fields)
    return [
        {"year": year, "absent_fields": sorted(all_fields - set(fields))}
        for year, fields in sorted(field_names_by_year.items())
        if all_fields - set(fields)
    ]


def missing_values_by_year(records, field_names_by_year):
    all_fields = sorted(
        {field for fields in field_names_by_year.values() for field in fields}
    )
    counts = collections.defaultdict(collections.Counter)
    totals = collections.Counter()
    for record in records:
        totals[record["source_year"]] += 1
        attributes = record["attributes"]
        for field in all_fields:
            if is_missing(attributes.get(field)):
                counts[record["source_year"]][field] += 1
    return [
        {
            "year": year,
            "feature_count": totals[year],
            "missing_or_blank_value_counts": {
                field: count for field, count in sorted(counts[year].items()) if count
            },
        }
        for year in sorted(totals)
    ]


def consistency_report(duplicate_consistency):
    surface = []
    dates = []
    municipalities = []
    for item in duplicate_consistency:
        differences = item["event_attribute_differences"]
        if any(field in differences for field in SURFACE_FIELDS):
            surface.append(
                {"NumPIF_CV": item["NumPIF_CV"], "differences": differences}
            )
        if "f_detec" in differences or "fextinc" in differences:
            dates.append(
                {"NumPIF_CV": item["NumPIF_CV"], "differences": differences}
            )
        if "nom_mun" in differences:
            municipalities.append(
                {"NumPIF_CV": item["NumPIF_CV"], "differences": differences}
            )
    return {
        "surface_differences_within_identifier": surface,
        "date_differences_within_identifier": dates,
        "municipality_differences_within_identifier": municipalities,
    }


def equivalent_geometry_report(records):
    grouped = collections.defaultdict(list)
    for record in records:
        grouped[record["geometry_equivalence_checksum_sha256"]].append(record)

    groups = []
    for checksum, matching_records in grouped.items():
        if len(matching_records) < 2:
            continue
        matching_records = sorted(matching_records, key=record_locator)
        groups.append(
            {
                "geometry_equivalence_checksum_sha256": checksum,
                "method": matching_records[0]["geometry_equivalence_method"],
                "feature_count": len(matching_records),
                "same_NumPIF_CV": len(unique_values(matching_records, "NumPIF_CV")) == 1,
                "same_NumPIF_Min": len(unique_values(matching_records, "NumPIF_Min")) == 1,
                "source_features": [
                    {
                        "year": record["source_year"],
                        "layer_id": record["source_layer_id"],
                        "OBJECTID": record["source_objectid"],
                        "NumPIF_CV": record["attributes"].get("NumPIF_CV"),
                        "NumPIF_Min": record["attributes"].get("NumPIF_Min"),
                        "raw_geometry_checksum_sha256": record[
                            "geometry_checksum_sha256"
                        ],
                    }
                    for record in matching_records
                ],
            }
        )
    groups.sort(
        key=lambda item: (
            -item["feature_count"], item["geometry_equivalence_checksum_sha256"]
        )
    )
    return groups


def validate_jsonl(path, id_field, expected_count):
    count = 0
    identifiers = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise NormalizationError(
                    "Invalid JSONL at {}:{}: {}".format(path, line_number, error)
                )
            identifier = record.get(id_field)
            if is_missing(identifier):
                raise NormalizationError(
                    "Missing {} at {}:{}".format(id_field, path, line_number)
                )
            if identifier in identifiers:
                raise NormalizationError(
                    "Duplicate {} {} in {}".format(id_field, identifier, path)
                )
            identifiers.add(identifier)
            count += 1
    if count != expected_count:
        raise NormalizationError(
            "{} contains {} records; expected {}".format(path, count, expected_count)
        )
    return count


def geometry_records(raw_files, assignments, fire_geometry_counts, raw_manifest_name):
    for year in sorted(raw_files):
        raw_file = raw_files[year]
        feature_set = load_json(raw_file["path"])
        features = sorted(
            feature_set["features"],
            key=lambda feature: feature["attributes"].get("OBJECTID"),
        )
        for feature in features:
            attributes = feature["attributes"]
            record = {
                "source_year": year,
                "source_layer_id": raw_file["entry"]["layer_id"],
                "source_objectid": attributes["OBJECTID"],
            }
            locator = record_locator(record)
            fire_id = assignments.get(locator)
            if not fire_id:
                raise NormalizationError(
                    "No fire assignment for {}".format(record)
                )
            geom_id = geometry_id(record)
            geometry = feature["geometry"]
            equivalence_checksum, equivalence_method = geometry_equivalence_checksum(
                geometry
            )
            yield {
                "geometry_id": geom_id,
                "fire_id": fire_id,
                "source": SOURCE_DATASET,
                "source_year": year,
                "source_layer_id": raw_file["entry"]["layer_id"],
                "source_objectid": attributes["OBJECTID"],
                "num_pif_cv": attributes.get("NumPIF_CV"),
                "num_pif_min": attributes.get("NumPIF_Min"),
                "geometry_type": feature_set.get("geometryType"),
                "crs": feature_set.get("spatialReference"),
                "geometry": geometry,
                "geometry_checksum_sha256": sha256_value(geometry),
                "geometry_equivalence_checksum_sha256": equivalence_checksum,
                "geometry_equivalence_method": equivalence_method,
                "geometry_quality": None,
                "geometry_quality_status": "not_assigned_pending_documentary_evidence",
                "geometry_role": (
                    "member_of_multi_geometry_fire"
                    if fire_geometry_counts[fire_id] > 1
                    else "only_geometry"
                ),
                "source_shape_length": attributes.get("shape_Leng"),
                "provenance": {
                    "source_dataset": SOURCE_DATASET,
                    "source_url": raw_file["entry"]["source_url"],
                    "retrieved_at": raw_file["entry"]["retrieved_at"],
                    "raw_file": raw_file["entry"]["output_file"],
                    "raw_file_sha256": raw_file["entry"]["sha256"],
                    "raw_manifest": raw_manifest_name,
                    "raw_format": raw_file["entry"]["format"],
                    "normalization_version": NORMALIZATION_VERSION,
                },
            }


def aggregate_raw_geometry_checks(raw_manifest):
    fields = (
        "feature_count",
        "polygon_geometry_count",
        "null_geometry_count",
        "empty_geometry_count",
        "linear_ring_count",
        "curve_ring_geometry_count",
        "rings_with_fewer_than_4_positions",
        "unclosed_linear_ring_count",
        "invalid_position_count",
        "unexpected_geometry_structure_count",
    )
    return {
        field: sum((layer.get("geometry_checks") or {}).get(field, 0) for layer in raw_manifest["layers"])
        for field in fields
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Separate raw ICV features into normalized fire and geometry JSONL records."
    )
    parser.add_argument("--raw-dir", type=Path, default=default_raw_dir())
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    return parser.parse_args()


def main():
    args = parse_args()
    raw_manifest_path = args.raw_dir / "manifest.json"
    raw_manifest = load_json(raw_manifest_path)
    records, raw_files, field_names_by_year = first_pass(args.raw_dir, raw_manifest)

    identifiers = identifier_report(records)
    relationships, cv_to_min, min_to_cv = identifier_relationships(records)
    assignments, groups, ambiguous_cases, duplicate_consistency = grouping_decisions(
        records, cv_to_min, min_to_cv
    )
    fires = [normalized_fire(group) for group in groups]
    fire_geometry_counts = {fire["fire_id"]: fire["geometry_count"] for fire in fires}
    if len(assignments) != len(records):
        raise NormalizationError("Not every raw feature received a fire linkage decision")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fires_path = args.output_dir / "fires.jsonl"
    geometries_path = args.output_dir / "geometries.jsonl"
    report_path = args.output_dir / "report.json"
    manifest_path = args.output_dir / "manifest.json"

    temporary_files = []
    try:
        fires_temporary, fire_count = write_jsonl_temporary(fires_path, fires)
        temporary_files.append(fires_temporary)
        geometries_temporary, geometry_count = write_jsonl_temporary(
            geometries_path,
            geometry_records(
                raw_files,
                assignments,
                fire_geometry_counts,
                str(raw_manifest_path.relative_to(repository_root())),
            ),
        )
        temporary_files.append(geometries_temporary)

        validate_jsonl(fires_temporary, "fire_id", len(fires))
        validate_jsonl(geometries_temporary, "geometry_id", len(records))
        if fire_count != len(fires) or geometry_count != len(records):
            raise NormalizationError("JSONL writer counts are inconsistent")

        fires_output = {
            "path": fires_path.name,
            "format": "jsonl",
            "record_count": fire_count,
            "file_size_bytes": fires_temporary.stat().st_size,
            "sha256": sha256_file(fires_temporary),
        }
        geometries_output = {
            "path": geometries_path.name,
            "format": "jsonl_with_native_esri_json_geometry",
            "record_count": geometry_count,
            "file_size_bytes": geometries_temporary.stat().st_size,
            "sha256": sha256_file(geometries_temporary),
        }

        multiple_geometry_fires = [
            {
                "fire_id": fire["fire_id"],
                "NumPIF_CV": fire["num_pif_cv"],
                "NumPIF_Min": fire["num_pif_min"],
                "geometry_count": fire["geometry_count"],
                "geometry_ids": fire["geometry_ids"],
                "source_objectids": fire["source_identifiers"]["OBJECTID"],
            }
            for fire in fires
            if fire["geometry_count"] > 1
        ]
        date_diagnostics = date_and_year_diagnostics(records)
        consistency = consistency_report(duplicate_consistency)
        equivalent_geometry_groups = equivalent_geometry_report(records)
        equivalent_geometry_feature_count = sum(
            item["feature_count"] for item in equivalent_geometry_groups
        )
        equivalent_geometry_same_identifier_count = sum(
            1
            for item in equivalent_geometry_groups
            if item["same_NumPIF_CV"] and item["same_NumPIF_Min"]
        )
        equivalent_geometry_cross_year_count = sum(
            1
            for item in equivalent_geometry_groups
            if len({feature["year"] for feature in item["source_features"]}) > 1
        )
        equivalent_geometry_raw_identical_count = sum(
            1
            for item in equivalent_geometry_groups
            if len(
                {
                    feature["raw_geometry_checksum_sha256"]
                    for feature in item["source_features"]
                }
            )
            == 1
        )
        report = {
            "schema_version": 1,
            "report_type": "gva_icv_normalization_consistency",
            "generated_at": now_utc(),
            "format_decision": {
                "fires": "JSON Lines",
                "geometries": "JSON Lines with native Esri JSON geometry objects",
                "rationale": (
                    "JSONL uses the Python standard library, keeps fire and geometry records "
                    "separate, supports streaming analysis, preserves the native CRS and Esri "
                    "geometry without conversion, and avoids adding Parquet or database "
                    "dependencies during the first normalization."
                ),
            },
            "counts": {
                "raw_features": len(records),
                "normalized_fires": len(fires),
                "normalized_geometries": geometry_count,
                "fires_with_multiple_geometries": len(multiple_geometry_fires),
                "ambiguous_fire_groups": len(ambiguous_cases),
            },
            "fire_id_rule": {
                "namespace": "gva:pif-cv:<NumPIF_CV>",
                "status": "provisional_until_linkage_with_EGIF",
                "rule": (
                    "Use NumPIF_CV only when it is present, maps one-to-one to NumPIF_Min, "
                    "belongs to one source year, and repeated source features have consistent "
                    "event attributes. Otherwise assign a source-feature fallback fire_id and "
                    "report the case as ambiguous."
                ),
                "fallback_namespace": "gva:source-feature:<year>:<layer_id>:<OBJECTID>",
            },
            "identifier_checks": identifiers,
            "identifier_relationships": relationships,
            "duplicate_identifier_consistency": duplicate_consistency,
            "multiple_geometry_fires": multiple_geometry_fires,
            "ambiguous_cases": ambiguous_cases,
            "consistency_checks": {
                "fields_absent_by_year": absent_fields_by_year(field_names_by_year),
                "missing_or_blank_values_by_year": missing_values_by_year(
                    records, field_names_by_year
                ),
                **consistency,
                **date_diagnostics,
            },
            "geometry_validation": {
                "raw_structural_checks": aggregate_raw_geometry_checks(raw_manifest),
                "exact_coordinate_equivalence_group_count": len(
                    equivalent_geometry_groups
                ),
                "features_in_exact_coordinate_equivalence_groups": (
                    equivalent_geometry_feature_count
                ),
                "groups_with_same_NumPIF_CV_and_NumPIF_Min": (
                    equivalent_geometry_same_identifier_count
                ),
                "groups_with_different_identifiers": (
                    len(equivalent_geometry_groups)
                    - equivalent_geometry_same_identifier_count
                ),
                "groups_spanning_multiple_source_years": (
                    equivalent_geometry_cross_year_count
                ),
                "groups_with_identical_raw_geometry_checksum": (
                    equivalent_geometry_raw_identical_count
                ),
                "exact_coordinate_equivalence_groups": equivalent_geometry_groups,
                "equivalence_method_scope": (
                    "Compares exact coordinate values while ignoring only linear-ring start "
                    "position, orientation and ring order; it is not a topological equality "
                    "test and does not modify geometries."
                ),
                "advanced_topological_validation_performed": False,
                "reason": (
                    "Shapely, GDAL/OGR and equivalent topology libraries are not installed; "
                    "no geometry was repaired or altered."
                ),
            },
            "outputs": {
                "fires": fires_output,
                "geometries": geometries_output,
            },
        }
        report_temporary = write_json_temporary(report_path, report, pretty=True)
        temporary_files.append(report_temporary)

        processed_manifest = {
            "schema_version": 1,
            "manifest_type": "gva_icv_processed_normalization",
            "normalization_version": NORMALIZATION_VERSION,
            "generated_at": now_utc(),
            "input": {
                "raw_manifest": str(raw_manifest_path.relative_to(repository_root())),
                "raw_manifest_sha256": sha256_file(raw_manifest_path),
                "raw_feature_count": len(records),
                "raw_files_verified": len(raw_files),
                "raw_files_modified": False,
            },
            "transformation_contract": {
                "attributes_normalized": True,
                "original_attributes_preserved_in_fire_source_records": True,
                "geometry_modified": False,
                "geometry_simplified": False,
                "features_deduplicated": False,
                "geometry_quality_assigned": False,
            },
            "outputs": {
                "fires": fires_output,
                "geometries": geometries_output,
                "report": {
                    "path": report_path.name,
                    "format": "json",
                    "file_size_bytes": report_temporary.stat().st_size,
                    "sha256": sha256_file(report_temporary),
                },
            },
        }
        manifest_temporary = write_json_temporary(
            manifest_path, processed_manifest, pretty=True
        )
        temporary_files.append(manifest_temporary)

        replace_temporary(fires_temporary, fires_path)
        temporary_files.remove(fires_temporary)
        replace_temporary(geometries_temporary, geometries_path)
        temporary_files.remove(geometries_temporary)
        replace_temporary(report_temporary, report_path)
        temporary_files.remove(report_temporary)
        replace_temporary(manifest_temporary, manifest_path)
        temporary_files.remove(manifest_temporary)
    finally:
        for temporary in temporary_files:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    print(
        "Normalized {} raw features -> {} fires and {} geometries in {}".format(
            len(records), len(fires), len(records), args.output_dir
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("normalization interrupted; raw files were not modified", file=sys.stderr)
        sys.exit(130)
    except (NormalizationError, OSError, ValueError) as error:
        print("normalization error: {}".format(error), file=sys.stderr)
        sys.exit(1)
