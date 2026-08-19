#!/usr/bin/env python3
"""Download complete annual ICV perimeter layers as native Esri FeatureSet JSON."""

import argparse
import collections
import hashlib
import http.client
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


FORMAT_NAME = "esri-feature-set-json"
MANIFEST_SCHEMA_VERSION = 1
DOWNLOAD_CONTRACT_VERSION = 1
IDENTIFIER_FIELDS = ("OBJECTID", "NumPIF_CV", "NumPIF_Min")
USER_AGENT = "atlas-incendios-cv-download/1.0"


class DownloadError(RuntimeError):
    """Raised when a layer cannot be downloaded and validated completely."""


def repository_root():
    return Path(__file__).resolve().parents[3]


def default_inventory_path():
    return repository_root() / "data" / "sources" / "icv_perimeters.json"


def default_output_dir():
    return repository_root() / "data" / "raw" / "gva"


def now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def request_json(url, params=None, timeout=60, attempts=3):
    """Request JSON with retries, including ArcGIS errors returned with HTTP 200."""
    request_url = url
    if params:
        request_url = "{}?{}".format(url, urllib.parse.urlencode(params))

    last_error = None
    for attempt in range(attempts):
        request = urllib.request.Request(request_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
            if payload.get("error"):
                error = payload["error"]
                details = "; ".join(error.get("details") or [])
                raise DownloadError(
                    "ArcGIS error {}: {}{}".format(
                        error.get("code", "unknown"),
                        error.get("message", "unknown error"),
                        " ({})".format(details) if details else "",
                    )
                )
            return payload
        except (
            DownloadError,
            ConnectionError,
            ConnectionResetError,
            TimeoutError,
            http.client.IncompleteRead,
            json.JSONDecodeError,
            socket.timeout,
            UnicodeDecodeError,
            urllib.error.HTTPError,
            urllib.error.URLError,
        ) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(1 * (2 ** attempt))

    raise DownloadError(
        "Request failed after {} attempts for {}: {}".format(attempts, url, last_error)
    )


def query_count(layer_url, timeout, attempts):
    payload = request_json(
        layer_url + "/query",
        {"f": "json", "where": "1=1", "returnCountOnly": "true"},
        timeout=timeout,
        attempts=attempts,
    )
    count = payload.get("count")
    if not isinstance(count, int) or count < 0:
        raise DownloadError("Count query returned an invalid count for {}".format(layer_url))
    return count


def query_page(layer, offset, page_size, timeout, attempts):
    object_id_field = layer.get("object_id_field")
    if not object_id_field:
        raise DownloadError("Inventory has no object ID field for year {}".format(layer["year"]))
    return request_json(
        layer["url"] + "/query",
        {
            "f": "json",
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "returnTrueCurves": "true",
            "returnZ": "true",
            "returnM": "true",
            "orderByFields": "{} ASC".format(object_id_field),
            "resultOffset": offset,
            "resultRecordCount": page_size,
        },
        timeout=timeout,
        attempts=attempts,
    )


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DownloadError("Invalid JSON file {}: {}".format(path, error))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_temporary(path, payload, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            if compact:
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
            else:
                json.dump(payload, handle, ensure_ascii=False, allow_nan=False, indent=2)
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


def atomic_write_json(path, payload, compact=False):
    temporary = write_json_temporary(path, payload, compact=compact)
    os.replace(str(temporary), str(path))


def stable_value_key(value):
    return "{}:{}".format(
        type(value).__name__,
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def is_missing_identifier(value):
    return value is None or (isinstance(value, str) and not value.strip())


def identifier_analysis(features, field_name):
    counts = collections.Counter()
    values = {}
    occurrences = []
    missing_count = 0

    for feature in features:
        attributes = feature.get("attributes")
        value = attributes.get(field_name) if isinstance(attributes, dict) else None
        if is_missing_identifier(value):
            missing_count += 1
            continue
        key = stable_value_key(value)
        counts[key] += 1
        values[key] = value
        occurrences.append((key, value))

    duplicates = [
        {"value": values[key], "count": count}
        for key, count in counts.items()
        if count > 1
    ]
    duplicates.sort(key=lambda item: stable_value_key(item["value"]))
    return {
        "summary": {
            "field": field_name,
            "missing_or_blank_count": missing_count,
            "distinct_non_missing_count": len(counts),
            "duplicate_value_count": len(duplicates),
            "features_with_duplicated_values": sum(item["count"] for item in duplicates),
            "duplicate_excess_count": sum(item["count"] - 1 for item in duplicates),
            "unique_among_non_missing": not duplicates,
            "unique_and_complete": not duplicates and missing_count == 0,
            "duplicate_values": duplicates,
        },
        "occurrences": occurrences,
    }


def polygon_structure_analysis(features):
    result = {
        "feature_count": len(features),
        "polygon_geometry_count": 0,
        "null_geometry_count": 0,
        "empty_geometry_count": 0,
        "linear_ring_count": 0,
        "curve_ring_geometry_count": 0,
        "rings_with_fewer_than_4_positions": 0,
        "unclosed_linear_ring_count": 0,
        "invalid_position_count": 0,
        "unexpected_geometry_structure_count": 0,
        "topological_validity_checked": False,
    }

    for feature in features:
        geometry = feature.get("geometry")
        if geometry is None:
            result["null_geometry_count"] += 1
            continue
        if not isinstance(geometry, dict):
            result["unexpected_geometry_structure_count"] += 1
            continue
        if "curveRings" in geometry:
            curve_rings = geometry.get("curveRings")
            if not isinstance(curve_rings, list) or not curve_rings:
                result["empty_geometry_count"] += 1
            else:
                result["curve_ring_geometry_count"] += 1
                result["polygon_geometry_count"] += 1
            continue
        rings = geometry.get("rings")
        if not isinstance(rings, list):
            result["unexpected_geometry_structure_count"] += 1
            continue
        if not rings:
            result["empty_geometry_count"] += 1
            continue

        result["polygon_geometry_count"] += 1
        result["linear_ring_count"] += len(rings)
        for ring in rings:
            if not isinstance(ring, list):
                result["unexpected_geometry_structure_count"] += 1
                continue
            if len(ring) < 4:
                result["rings_with_fewer_than_4_positions"] += 1
            if ring and ring[0] != ring[-1]:
                result["unclosed_linear_ring_count"] += 1
            for position in ring:
                if (
                    not isinstance(position, list)
                    or len(position) < 2
                    or not all(isinstance(value, (int, float)) for value in position[:2])
                ):
                    result["invalid_position_count"] += 1

    return result


def validate_feature_set(feature_set, layer, expected_count):
    errors = []
    warnings = []
    features = feature_set.get("features")
    if not isinstance(features, list):
        raise DownloadError("FeatureSet for {} has no features array".format(layer["year"]))
    if len(features) != expected_count:
        errors.append(
            "Downloaded {} features, expected {}".format(len(features), expected_count)
        )
    if feature_set.get("geometryType") != "esriGeometryPolygon":
        errors.append(
            "Unexpected geometryType: {}".format(feature_set.get("geometryType"))
        )

    identifiers = {}
    occurrences = {}
    for field_name in IDENTIFIER_FIELDS:
        analysis = identifier_analysis(features, field_name)
        identifiers[field_name] = analysis["summary"]
        occurrences[field_name] = analysis["occurrences"]

    object_id = identifiers["OBJECTID"]
    if not object_id["unique_and_complete"]:
        errors.append("OBJECTID is missing or duplicated within the layer")

    geometry = polygon_structure_analysis(features)
    if geometry["unexpected_geometry_structure_count"]:
        errors.append("One or more geometries have an unexpected polygon structure")
    if geometry["null_geometry_count"]:
        warnings.append("{} features have null geometry".format(geometry["null_geometry_count"]))
    if geometry["empty_geometry_count"]:
        warnings.append("{} features have empty geometry".format(geometry["empty_geometry_count"]))
    if geometry["rings_with_fewer_than_4_positions"]:
        warnings.append(
            "{} rings have fewer than four positions".format(
                geometry["rings_with_fewer_than_4_positions"]
            )
        )
    if geometry["unclosed_linear_ring_count"]:
        warnings.append(
            "{} linear rings are not closed".format(
                geometry["unclosed_linear_ring_count"]
            )
        )
    if geometry["invalid_position_count"]:
        errors.append(
            "{} coordinate positions are structurally invalid".format(
                geometry["invalid_position_count"]
            )
        )

    return {
        "errors": errors,
        "warnings": warnings,
        "identifiers": identifiers,
        "identifier_occurrences": occurrences,
        "geometry": geometry,
        "features": features,
    }


def feature_set_metadata(page):
    return {
        key: value
        for key, value in page.items()
        if key not in ("features", "exceededTransferLimit")
    }


def download_layer(layer, output_path, page_size, timeout, attempts):
    year = layer["year"]
    inventory_count = layer["feature_count"]
    live_count_before = query_count(layer["url"], timeout, attempts)
    warnings = []
    if live_count_before != inventory_count:
        warnings.append(
            "Source count changed since inventory: {} -> {}".format(
                inventory_count, live_count_before
            )
        )

    layer_limit = layer.get("max_record_count") or page_size
    effective_page_size = min(page_size, layer_limit)
    if effective_page_size < 1:
        raise DownloadError("Invalid page size for year {}".format(year))

    offset = 0
    page_counts = []
    merged_metadata = None
    features = []
    page_number = 0

    while offset < live_count_before or not page_counts:
        remaining = live_count_before - offset
        requested = min(effective_page_size, remaining) if remaining > 0 else 1
        page = query_page(layer, offset, requested, timeout, attempts)
        page_features = page.get("features")
        if not isinstance(page_features, list):
            raise DownloadError("Page {} for {} has no features array".format(page_number, year))
        if len(page_features) > requested:
            raise DownloadError(
                "Page {} for {} returned {} features after requesting {}".format(
                    page_number, year, len(page_features), requested
                )
            )
        if remaining > 0 and not page_features:
            raise DownloadError(
                "Pagination stopped at offset {} before expected count {} for {}".format(
                    offset, live_count_before, year
                )
            )

        metadata = feature_set_metadata(page)
        if merged_metadata is None:
            merged_metadata = metadata
        elif metadata != merged_metadata:
            raise DownloadError("FeatureSet metadata changed between pages for {}".format(year))

        features.extend(page_features)
        page_counts.append(len(page_features))
        offset += len(page_features)
        page_number += 1
        print(
            "{}: page {} -> {} features ({}/{})".format(
                year, page_number, len(page_features), offset, live_count_before
            ),
            flush=True,
        )

        if live_count_before == 0:
            break
        if offset < live_count_before and page.get("exceededTransferLimit") is False:
            warnings.append(
                "Page {} reported exceededTransferLimit=false before the expected count; "
                "explicit pagination continued".format(page_number)
            )

    live_count_after = query_count(layer["url"], timeout, attempts)
    if live_count_after != live_count_before:
        raise DownloadError(
            "Source count changed during download for {}: {} -> {}".format(
                year, live_count_before, live_count_after
            )
        )
    if len(features) != live_count_after:
        raise DownloadError(
            "Incomplete layer {}: downloaded {}, live count {}".format(
                year, len(features), live_count_after
            )
        )

    feature_set = dict(merged_metadata or {})
    feature_set["features"] = features
    validation = validate_feature_set(feature_set, layer, live_count_after)
    errors = list(validation["errors"])
    warnings.extend(validation["warnings"])
    if errors:
        raise DownloadError("; ".join(errors))

    temporary_path = write_json_temporary(output_path, feature_set, compact=True)
    try:
        persisted = load_json(temporary_path)
        persisted_validation = validate_feature_set(persisted, layer, live_count_after)
        if persisted_validation["errors"]:
            raise DownloadError(
                "Persisted file validation failed for {}: {}".format(
                    year, "; ".join(persisted_validation["errors"])
                )
            )
        os.replace(str(temporary_path), str(output_path))
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise

    status = "complete_with_warnings" if warnings else "complete"
    entry = {
        "year": year,
        "layer_id": layer["layer_id"],
        "source_url": layer["url"],
        "retrieved_at": now_utc(),
        "output_file": output_path.name,
        "format": FORMAT_NAME,
        "download_contract_version": DOWNLOAD_CONTRACT_VERSION,
        "source_crs": feature_set.get("spatialReference"),
        "feature_count_inventory": inventory_count,
        "feature_count_expected": live_count_before,
        "feature_count_live_after": live_count_after,
        "feature_count_downloaded": len(features),
        "source_changed_since_inventory": live_count_before != inventory_count,
        "page_size": effective_page_size,
        "page_count": len(page_counts),
        "page_feature_counts": page_counts,
        "file_size_bytes": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
        "validation_status": status,
        "errors": [],
        "warnings": warnings,
        "identifier_checks": validation["identifiers"],
        "geometry_checks": validation["geometry"],
    }
    return entry, validation["identifier_occurrences"]


def cached_layer(layer, output_path, old_entry):
    if not isinstance(old_entry, dict):
        return None, "manifest entry is missing"
    required_matches = (
        old_entry.get("year") == layer["year"]
        and old_entry.get("layer_id") == layer["layer_id"]
        and old_entry.get("source_url") == layer["url"]
        and old_entry.get("feature_count_inventory") == layer["feature_count"]
        and old_entry.get("feature_count_expected") == layer["feature_count"]
        and old_entry.get("feature_count_downloaded") == layer["feature_count"]
        and old_entry.get("format") == FORMAT_NAME
        and old_entry.get("download_contract_version") == DOWNLOAD_CONTRACT_VERSION
        and old_entry.get("validation_status") in ("complete", "complete_with_warnings")
    )
    if not required_matches:
        return None, "manifest entry does not match the current inventory contract"
    if not output_path.is_file():
        return None, "data file is missing"
    if output_path.stat().st_size != old_entry.get("file_size_bytes"):
        return None, "file size does not match the manifest"
    if sha256_file(output_path) != old_entry.get("sha256"):
        return None, "checksum does not match the manifest"

    feature_set = load_json(output_path)
    validation = validate_feature_set(feature_set, layer, layer["feature_count"])
    if validation["errors"]:
        return None, "; ".join(validation["errors"])
    return (old_entry, validation["identifier_occurrences"]), None


def failed_entry(layer, output_path, error, retained_existing):
    return {
        "year": layer["year"],
        "layer_id": layer["layer_id"],
        "source_url": layer["url"],
        "retrieved_at": now_utc(),
        "output_file": output_path.name,
        "format": FORMAT_NAME,
        "download_contract_version": DOWNLOAD_CONTRACT_VERSION,
        "feature_count_inventory": layer["feature_count"],
        "feature_count_expected": None,
        "feature_count_downloaded": None,
        "validation_status": "failed",
        "retained_existing_valid_file": retained_existing,
        "errors": [str(error)],
        "warnings": [],
    }


def cross_year_identifier_analysis(occurrences_by_year):
    result = {}
    for field_name in IDENTIFIER_FIELDS:
        values = {}
        for year, field_occurrences in occurrences_by_year.items():
            for key, value in field_occurrences.get(field_name, []):
                record = values.setdefault(
                    key, {"value": value, "year_counts": collections.Counter()}
                )
                record["year_counts"][year] += 1

        duplicates = []
        for record in values.values():
            if len(record["year_counts"]) < 2:
                continue
            years = [
                {"year": year, "count": count}
                for year, count in sorted(record["year_counts"].items())
            ]
            duplicates.append(
                {
                    "value": record["value"],
                    "years": years,
                    "total_feature_count": sum(item["count"] for item in years),
                }
            )
        duplicates.sort(key=lambda item: stable_value_key(item["value"]))
        result[field_name] = {
            "values_repeated_between_years": len(duplicates),
            "affected_feature_count": sum(
                item["total_feature_count"] for item in duplicates
            ),
            "duplicate_values": duplicates,
        }
    return result


def relative_or_absolute(path, base):
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path.resolve())


def load_inventory(path):
    inventory = load_json(path)
    layers = inventory.get("layers")
    if not isinstance(layers, list) or not layers:
        raise DownloadError("Inventory has no annual layers")
    years = [layer.get("year") for layer in layers]
    if any(not isinstance(year, int) for year in years) or len(years) != len(set(years)):
        raise DownloadError("Inventory years are missing or duplicated")
    for layer in layers:
        for key in ("year", "layer_id", "url", "feature_count", "object_id_field"):
            if layer.get(key) is None:
                raise DownloadError(
                    "Inventory layer {} lacks {}".format(layer.get("year"), key)
                )
    return inventory


def load_old_manifest(path):
    if not path.is_file():
        return None
    try:
        manifest = load_json(path)
    except DownloadError as error:
        print("warning: existing manifest ignored: {}".format(error), file=sys.stderr)
        return None
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        print("warning: existing manifest schema is incompatible", file=sys.stderr)
        return None
    return manifest


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Download complete ICV annual perimeter layers listed in the CV-1.1 inventory."
        )
    )
    parser.add_argument("--inventory", type=Path, default=default_inventory_path())
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    parser.add_argument(
        "--year",
        action="append",
        type=int,
        dest="years",
        help="Download only this year; repeat the option for multiple years.",
    )
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.page_size < 1 or args.timeout < 1 or args.attempts < 1:
        raise DownloadError("page-size, timeout and attempts must be positive")

    inventory = load_inventory(args.inventory)
    all_layers = sorted(inventory["layers"], key=lambda item: item["year"])
    available_years = {layer["year"] for layer in all_layers}
    selected_years = set(args.years or available_years)
    unknown_years = sorted(selected_years - available_years)
    if unknown_years:
        raise DownloadError("Years are absent from the inventory: {}".format(unknown_years))
    layers = [layer for layer in all_layers if layer["year"] in selected_years]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    old_manifest = load_old_manifest(manifest_path)
    old_entries = {
        entry.get("year"): entry
        for entry in (old_manifest or {}).get("layers", [])
        if isinstance(entry, dict)
    }

    entries = []
    occurrences_by_year = {}
    downloaded_years = []
    skipped_years = []
    failed_years = []

    for layer in layers:
        year = layer["year"]
        output_path = args.output_dir / "{}.json".format(year)
        cached = None
        cache_error = None
        if old_entries.get(year):
            cached, cache_error = cached_layer(layer, output_path, old_entries[year])
        if cached and not args.force:
            entry, occurrences = cached
            entries.append(entry)
            occurrences_by_year[year] = occurrences
            skipped_years.append(year)
            print("{}: valid cached file, skipped".format(year), flush=True)
            continue

        retained_existing = bool(cached)
        try:
            print("{}: downloading {}".format(year, layer["url"]), flush=True)
            entry, occurrences = download_layer(
                layer, output_path, args.page_size, args.timeout, args.attempts
            )
            if cache_error and not args.force:
                entry["warnings"].append(
                    "Existing cache was not reused: {}".format(cache_error)
                )
                if entry["validation_status"] == "complete":
                    entry["validation_status"] = "complete_with_warnings"
            entries.append(entry)
            occurrences_by_year[year] = occurrences
            downloaded_years.append(year)
        except (DownloadError, OSError, ValueError) as error:
            print("{}: FAILED: {}".format(year, error), file=sys.stderr, flush=True)
            entries.append(failed_entry(layer, output_path, error, retained_existing))
            failed_years.append(year)

    entries.sort(key=lambda item: item["year"])
    successful_entries = [
        entry for entry in entries if entry["validation_status"] != "failed"
    ]
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": "raw_icv_annual_perimeter_download",
        "generated_at": now_utc(),
        "inventory": {
            "path": relative_or_absolute(args.inventory, repository_root()),
            "sha256": sha256_file(args.inventory),
            "generated_at": inventory.get("generated_at"),
            "source_endpoint": (inventory.get("source") or {}).get("endpoint"),
        },
        "download_contract": {
            "version": DOWNLOAD_CONTRACT_VERSION,
            "format": FORMAT_NAME,
            "native_crs_preserved": True,
            "geometry_simplified": False,
            "attributes_normalized": False,
            "features_deduplicated": False,
            "query_order": "OBJECTID ASC (field read from inventory)",
            "topological_validity_checked": False,
        },
        "run": {
            "requested_years": sorted(selected_years),
            "force": args.force,
            "page_size_requested": args.page_size,
            "downloaded_years": downloaded_years,
            "skipped_valid_years": skipped_years,
            "failed_years": failed_years,
        },
        "completeness": {
            "status": "failed" if failed_years else "complete",
            "year_count_requested": len(layers),
            "year_count_complete": len(successful_entries),
            "feature_count_inventory": sum(layer["feature_count"] for layer in layers),
            "feature_count_expected": sum(
                entry.get("feature_count_expected") or 0 for entry in successful_entries
            ),
            "feature_count_downloaded": sum(
                entry.get("feature_count_downloaded") or 0 for entry in successful_entries
            ),
            "source_changed_years": [
                entry["year"]
                for entry in successful_entries
                if entry.get("source_changed_since_inventory")
            ],
        },
        "cross_year_identifier_checks": cross_year_identifier_analysis(
            occurrences_by_year
        ),
        "layers": entries,
    }
    atomic_write_json(manifest_path, manifest, compact=False)

    print(
        "Complete years: {}/{}; features: {}/{}; manifest: {}".format(
            len(successful_entries),
            len(layers),
            manifest["completeness"]["feature_count_downloaded"],
            manifest["completeness"]["feature_count_expected"],
            manifest_path,
        ),
        flush=True,
    )
    if failed_years:
        raise DownloadError("Failed years: {}".format(", ".join(map(str, failed_years))))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("download interrupted; completed files were preserved", file=sys.stderr)
        sys.exit(130)
    except DownloadError as error:
        print("download error: {}".format(error), file=sys.stderr)
        sys.exit(1)
