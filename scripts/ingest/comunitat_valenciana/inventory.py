#!/usr/bin/env python3
"""Inventory the annual ICV wildfire perimeter layers without downloading features."""

import argparse
import concurrent.futures
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SERVICE_URL = (
    "https://carto.icv.gva.es/arcgis/rest/services/"
    "Prevencion_de_incendios2/MapServer"
)
DEFAULT_ALTERNATE_SERVICE_URL = (
    "https://carto.icv.gva.es/arcgis/rest/services/"
    "tm_medio_ambiente/prevencion_de_incendios/MapServer"
)
DEFAULT_START_YEAR = 1993
DEFAULT_END_YEAR = 2024
FIRE_LAYER_PATTERN = re.compile(r"^Incendios\s+((?:19|20)\d{2})\b")
IDENTIFIER_FIELDS = ("NumPIF_CV", "NumPIF_Min")
REQUIRED_FIELDS = {
    "NumPIF_CV",
    "NumPIF_Min",
    "anyo",
    "nom_mun",
    "paraje",
    "f_detec",
    "fextinc",
    "g_caus_txt",
    "sup_f",
}
USER_AGENT = "atlas-incendios-cv-inventory/1.0"


class InventoryError(RuntimeError):
    """Raised when the service cannot produce a complete, trustworthy inventory."""


def request_json(url, params=None, timeout=30, attempts=3):
    """Request ArcGIS JSON with bounded retries and surface REST errors."""
    if params:
        url = "{}?{}".format(url, urllib.parse.urlencode(params))

    last_error = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("error"):
                error = payload["error"]
                details = "; ".join(error.get("details") or [])
                raise InventoryError(
                    "ArcGIS error {}: {}{}".format(
                        error.get("code", "unknown"),
                        error.get("message", "unknown error"),
                        " ({})".format(details) if details else "",
                    )
                )
            return payload
        except (
            InventoryError,
            json.JSONDecodeError,
            TimeoutError,
            urllib.error.HTTPError,
            urllib.error.URLError,
        ) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(0.5 * (2 ** attempt))

    raise InventoryError("Request failed after {} attempts: {}".format(attempts, last_error))


def discover_fire_layers(service_metadata, start_year, end_year):
    """Find one annual wildfire leaf layer for every requested year."""
    by_year = {}
    duplicates = {}

    for layer in service_metadata.get("layers") or []:
        if layer.get("subLayerIds") is not None:
            continue
        match = FIRE_LAYER_PATTERN.match(layer.get("name") or "")
        if not match:
            continue
        year = int(match.group(1))
        if year < start_year or year > end_year:
            continue
        if year in by_year:
            duplicates.setdefault(year, [by_year[year]])
            duplicates[year].append(layer)
        else:
            by_year[year] = layer

    expected_years = set(range(start_year, end_year + 1))
    missing_years = sorted(expected_years - set(by_year))
    if missing_years or duplicates:
        raise InventoryError(
            "Annual layer discovery is ambiguous; missing years: {}; duplicate years: {}".format(
                missing_years, sorted(duplicates)
            )
        )

    return [by_year[year] for year in sorted(by_year)]


def find_object_id_field(layer_metadata):
    """Use the declared OID field, falling back to the field type when omitted."""
    declared = layer_metadata.get("objectIdField") or layer_metadata.get("objectIdFieldName")
    if declared:
        return declared, False
    for field in layer_metadata.get("fields") or []:
        if field.get("type") == "esriFieldTypeOID":
            return field.get("name"), True
    return None, False


def query_count(layer_url, where, timeout):
    payload = request_json(
        layer_url + "/query",
        {
            "f": "json",
            "where": where,
            "returnCountOnly": "true",
        },
        timeout=timeout,
    )
    count = payload.get("count")
    if not isinstance(count, int):
        raise InventoryError("Count query returned no integer count for {}".format(layer_url))
    return count


def compact_field(field):
    return {
        key: field.get(key)
        for key in ("name", "alias", "type", "length", "nullable")
        if field.get(key) is not None
    }


def schema_hash(fields):
    schema = [
        {"name": field.get("name"), "type": field.get("type")}
        for field in fields
    ]
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def inventory_layer(service_url, discovered_layer, timeout):
    year_match = FIRE_LAYER_PATTERN.match(discovered_layer["name"])
    year = int(year_match.group(1))
    layer_id = discovered_layer["id"]
    layer_url = "{}/{}".format(service_url, layer_id)
    metadata = request_json(layer_url, {"f": "pjson"}, timeout=timeout)

    fields = metadata.get("fields") or []
    field_names = {field.get("name") for field in fields}
    missing_required_fields = sorted(REQUIRED_FIELDS - field_names)
    if missing_required_fields:
        raise InventoryError(
            "Layer {} ({}) lacks required fields: {}".format(
                layer_id, year, ", ".join(missing_required_fields)
            )
        )

    feature_count = query_count(layer_url, "1=1", timeout)
    identifier_completeness = {}
    for field_name in IDENTIFIER_FIELDS:
        missing_count = query_count(
            layer_url,
            "{0} IS NULL OR {0} = ''".format(field_name),
            timeout,
        )
        if missing_count > feature_count:
            raise InventoryError(
                "Missing identifier count exceeds total count for layer {} field {}".format(
                    layer_id, field_name
                )
            )
        identifier_completeness[field_name] = {
            "present_count": feature_count - missing_count,
            "missing_or_blank_count": missing_count,
            "missing_or_blank_percent": (
                round(missing_count * 100 / feature_count, 4) if feature_count else 0.0
            ),
        }

    object_id_field, inferred_object_id = find_object_id_field(metadata)
    warnings = []
    if inferred_object_id:
        warnings.append(
            "objectIdField is absent in layer metadata; inferred from esriFieldTypeOID"
        )
    if not object_id_field:
        warnings.append("No object ID field was found")

    advanced = metadata.get("advancedQueryCapabilities") or {}
    return {
        "year": year,
        "layer_id": layer_id,
        "name": metadata.get("name") or discovered_layer.get("name"),
        "url": layer_url,
        "type": metadata.get("type"),
        "geometry_type": metadata.get("geometryType"),
        "object_id_field": object_id_field,
        "feature_count": feature_count,
        "max_record_count": metadata.get("maxRecordCount"),
        "supported_query_formats": metadata.get("supportedQueryFormats"),
        "capabilities": metadata.get("capabilities"),
        "query_capabilities": {
            "supports_pagination": advanced.get("supportsPagination"),
            "supports_statistics": advanced.get("supportsStatistics"),
            "supports_count_distinct": advanced.get("supportsCountDistinct"),
            "supports_returning_query_extent": advanced.get("supportsReturningQueryExtent"),
            "uses_standardized_queries": advanced.get("useStandardizedQueries"),
        },
        "extent": metadata.get("extent"),
        "schema_hash": schema_hash(fields),
        "fields": [compact_field(field) for field in fields],
        "identifier_completeness": identifier_completeness,
        "warnings": warnings,
    }


def compare_alternate_endpoint(primary_layers, alternate_url, start_year, end_year, timeout):
    """Compare the published annual layer map; a single check cannot prove stability."""
    try:
        metadata = request_json(alternate_url, {"f": "pjson"}, timeout=timeout)
        alternate_layers = discover_fire_layers(metadata, start_year, end_year)
        primary_map = {
            layer["year"]: {"layer_id": layer["layer_id"], "name": layer["name"]}
            for layer in primary_layers
        }
        alternate_map = {
            int(FIRE_LAYER_PATTERN.match(layer["name"]).group(1)): {
                "layer_id": layer["id"],
                "name": layer["name"],
            }
            for layer in alternate_layers
        }
        return {
            "url": alternate_url,
            "reachable": True,
            "service_current_version": metadata.get("currentVersion"),
            "service_description": metadata.get("serviceDescription"),
            "map_name": metadata.get("mapName"),
            "annual_layer_map_matches_primary": alternate_map == primary_map,
            "note": "Observed equivalence at inventory time does not establish future stability.",
        }
    except InventoryError as error:
        return {
            "url": alternate_url,
            "reachable": False,
            "error": str(error),
            "annual_layer_map_matches_primary": False,
        }


def build_summary(layers):
    variants = {}
    for layer in layers:
        variants.setdefault(layer["schema_hash"], []).append(layer["year"])
    return {
        "layer_count": len(layers),
        "total_feature_count": sum(layer["feature_count"] for layer in layers),
        "geometry_types": sorted(
            {layer["geometry_type"] for layer in layers if layer["geometry_type"]}
        ),
        "all_layers_support_pagination": all(
            layer["query_capabilities"]["supports_pagination"] is True for layer in layers
        ),
        "field_schema_variants": [
            {"schema_hash": digest, "years": years}
            for digest, years in sorted(variants.items())
        ],
    }


def default_output_path():
    repository_root = Path(__file__).resolve().parents[3]
    return repository_root / "data" / "sources" / "icv_perimeters.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Inventory ICV annual wildfire perimeter layers without downloading features."
    )
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--alternate-service-url", default=DEFAULT_ALTERNATE_SERVICE_URL)
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    parser.add_argument("--output", type=Path, default=default_output_path())
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.start_year > args.end_year:
        raise InventoryError("start-year must not be greater than end-year")
    if args.workers < 1:
        raise InventoryError("workers must be at least 1")

    service_url = args.service_url.rstrip("/")
    alternate_url = args.alternate_service_url.rstrip("/")
    service_metadata = request_json(
        service_url, {"f": "pjson"}, timeout=args.timeout
    )
    discovered_layers = discover_fire_layers(
        service_metadata, args.start_year, args.end_year
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(inventory_layer, service_url, layer, args.timeout)
            for layer in discovered_layers
        ]
        layers = sorted((future.result() for future in futures), key=lambda item: item["year"])

    inventory = {
        "schema_version": 1,
        "inventory_type": "arcgis_mapserver_annual_wildfire_perimeters",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "endpoint": service_url,
            "metadata_url": service_url + "?f=pjson",
            "service_current_version": service_metadata.get("currentVersion"),
            "service_description": service_metadata.get("serviceDescription"),
            "description": service_metadata.get("description"),
            "map_name": service_metadata.get("mapName"),
            "supported_query_formats": service_metadata.get("supportedQueryFormats"),
            "max_record_count": service_metadata.get("maxRecordCount"),
            "access_information": service_metadata.get("accessInformation"),
            "copyright_text": service_metadata.get("copyrightText"),
            "document_info": service_metadata.get("documentInfo"),
            "license": None,
            "license_status": "not_declared_in_service_metadata",
        },
        "scope": {
            "start_year": args.start_year,
            "end_year": args.end_year,
            "expected_years": list(range(args.start_year, args.end_year + 1)),
            "missing_years": [],
            "duplicate_years": [],
        },
        "project_limitations": [
            {
                "statement": (
                    "La cartografía valenciana es informativa y puede no contener "
                    "todos los incendios del periodo; los recuentos son de perímetros "
                    "publicados y no sustituyen a EGIF."
                ),
                "basis": "DATA_SOURCES.md",
            }
        ],
        "summary": build_summary(layers),
        "alternate_endpoint_check": compare_alternate_endpoint(
            layers, alternate_url, args.start_year, args.end_year, args.timeout
        ),
        "layers": layers,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(args.output)

    print(
        "Inventoried {} layers ({}-{}), {} perimeter features -> {}".format(
            len(layers),
            args.start_year,
            args.end_year,
            inventory["summary"]["total_feature_count"],
            args.output,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except InventoryError as error:
        print("inventory error: {}".format(error), file=sys.stderr)
        sys.exit(1)
