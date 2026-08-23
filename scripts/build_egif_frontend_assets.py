#!/usr/bin/env python3
"""Build the minimal, geometry-free EGIF 1968–1992 web derivative."""

import argparse
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PROVINCES = {"alicante": 2514, "castellon": 2600, "valencia": 4061}
PROVINCE_KEYS = {"Alicante": "alicante", "Castellon": "castellon", "Castellón": "castellon", "Valencia": "valencia"}
EXPECTED_TOTAL = sum(EXPECTED_PROVINCES.values())
WEB_FIELDS = (
    "record_id", "fire_id", "source", "entity_type", "year", "province_id", "province_name",
    "municipality_id", "municipality_name", "forest_area_ha", "total_area_ha", "gif_forest",
    "cause_source_code", "cause_raw", "cause_code", "cause_label", "cause_mapping_status",
    "coverage_regime", "has_municipality", "has_grid_reference", "identity_status",
    "episode_identity_status", "geometry",
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/egif/gva/fires_1968_1992.jsonl")
    parser.add_argument("--audit-report", type=Path, default=ROOT / "data/processed/egif/gva/report.json")
    parser.add_argument("--source-manifest", type=Path, default=ROOT / "data/sources/egif_gva_1968_1992_manifest.json")
    parser.add_argument("--config", type=Path, default=ROOT / "config/egif-web.json")
    parser.add_argument("--municipality-catalog", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/web/gva/egif")
    return parser.parse_args()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def file_metadata(payload):
    return {
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": sha256_bytes(payload),
    }


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def display_path(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def municipality_catalog(path, config):
    payload = read_json(path)
    id_field = config["municipalities"]["id_field"]
    name_field = config["municipalities"]["name_field"]
    result = {}
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        identifier = str(properties.get(id_field) or "").strip()
        name = str(properties.get(name_field) or "").strip()
        if identifier and name:
            result[identifier] = name
    if not result:
        raise ValueError("The canonical municipality catalogue is empty")
    return result


def compact_record(source, canonical_municipalities, config):
    province_id = PROVINCE_KEYS.get(source.get("province"))
    if not province_id:
        raise ValueError("Unexpected province: {!r}".format(source.get("province")))
    municipality_codine = str(source.get("municipality_codine") or "").strip() or None
    source_municipality_resolved = bool(source.get("municipality"))
    municipality_id = municipality_codine if source_municipality_resolved and municipality_codine in canonical_municipalities else None
    municipality_name = canonical_municipalities.get(municipality_id)
    source_cause_code = str(source.get("cause_source_code") or "").strip() or None
    cause_code = config["causes"]["source_code_mapping"].get(source_cause_code)
    cause_label = config["causes"]["canonical_labels"].get(cause_code)
    location = source.get("location_original") or {}
    has_grid = bool(location.get("map_sheet") or location.get("grid"))
    return {
        "record_id": source["source_record_id"],
        "fire_id": source["fire_id"],
        "source": "egif",
        "entity_type": "administrative_record",
        "year": source["year"],
        "province_id": province_id,
        "province_name": source["province"],
        "municipality_id": municipality_id,
        "municipality_name": municipality_name,
        "forest_area_ha": source.get("reported_forest_area_ha"),
        "total_area_ha": source.get("reported_total_area_ha"),
        "gif_forest": bool(source.get("is_gif_ge_500_ha")),
        "cause_source_code": source_cause_code,
        "cause_raw": source.get("cause"),
        "cause_code": cause_code,
        "cause_label": cause_label,
        "cause_mapping_status": "mapped" if cause_code else "unmapped",
        "coverage_regime": source["coverage_status"],
        "has_municipality": bool(municipality_id),
        "has_grid_reference": has_grid,
        "identity_status": source["identity_status"],
        "episode_identity_status": source["episode_identity_status"],
        "geometry": None,
    }


def build(args):
    config = read_json(args.config)
    vocabulary = read_json(ROOT / config["causes"]["vocabulary_path"])
    config["causes"]["canonical_labels"] = vocabulary["causes"]["categories"]
    audit = read_json(args.audit_report)
    source_manifest = read_json(args.source_manifest)
    catalog_path = args.municipality_catalog or ROOT / config["municipalities"]["catalog_path"]
    municipalities = municipality_catalog(catalog_path, config)
    source_bytes = args.input.read_bytes()
    records = []
    for number, line in enumerate(source_bytes.splitlines(), 1):
        if not line.strip():
            continue
        source = json.loads(line)
        record = compact_record(source, municipalities, config)
        if record["geometry"] is not None:
            raise ValueError("EGIF geometry must remain null")
        records.append(record)
    if len(records) != EXPECTED_TOTAL or audit["totals"]["records"] != EXPECTED_TOTAL:
        raise ValueError("Expected exactly {} EGIF records".format(EXPECTED_TOTAL))
    if len({record["record_id"] for record in records}) != EXPECTED_TOTAL:
        raise ValueError("EGIF record_id is not unique")
    if len({record["fire_id"] for record in records}) != EXPECTED_TOTAL:
        raise ValueError("EGIF fire_id is not unique")

    province_counts = collections.Counter(record["province_id"] for record in records)
    if dict(province_counts) != EXPECTED_PROVINCES:
        raise ValueError("Province counts do not reconcile: {}".format(dict(province_counts)))
    annual_counts = collections.Counter(record["year"] for record in records)
    source_annual = collections.Counter()
    for province in source_manifest["provinces"]:
        source_annual.update({int(year): count for year, count in province["annual_counts_downloaded"].items()})
    if annual_counts != source_annual:
        raise ValueError("Annual counts do not reconcile with the source manifest")

    cause_counts = collections.Counter((record["cause_source_code"], record["cause_raw"], record["cause_code"], record["cause_label"]) for record in records)
    unresolved_with_code = sum(bool(record["cause_source_code"]) and not record["cause_code"] for record in records)
    metrics = {
        "records": len(records),
        "by_province": dict(sorted(province_counts.items())),
        "gif_forest_ge_500_ha": sum(record["gif_forest"] for record in records),
        "municipality_resolved": sum(record["has_municipality"] for record in records),
        "municipality_unresolved": sum(not record["has_municipality"] for record in records),
        "canonical_municipalities_represented": len({record["municipality_id"] for record in records if record["municipality_id"]}),
        "with_grid_reference": sum(record["has_grid_reference"] for record in records),
        "without_usable_spatial_location": sum(not record["has_grid_reference"] for record in records),
        "geometries": sum(record["geometry"] is not None for record in records),
        "cause_source_values_mapped": sum(record["cause_mapping_status"] == "mapped" for record in records),
        "cause_source_values_unmapped": unresolved_with_code,
    }
    expected_metrics = {
        "gif_forest_ge_500_ha": 180,
        "municipality_resolved": 5254,
        "with_grid_reference": 8565,
        "without_usable_spatial_location": 610,
        "geometries": 0,
    }
    for key, value in expected_metrics.items():
        if metrics[key] != value:
            raise ValueError("{} does not reconcile: {} != {}".format(key, metrics[key], value))

    asset_payload = json.dumps({
        "schema_version": 1,
        "source": "egif",
        "entity_type": "administrative_record",
        "geometry_availability": "none",
        "fields": WEB_FIELDS,
        "records": [[record[field] for field in WEB_FIELDS] for record in records],
    }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    asset_name = "records-1968-1992.json"
    asset_info = file_metadata(asset_payload)
    asset_info.update({
        "kind": "egif_administrative_records",
        "url": "data/web/gva/egif/" + asset_name,
        "record_count": len(records),
        "year_min": config["years"]["min"],
        "year_max": config["years"]["max"],
        "fields": WEB_FIELDS,
    })
    manifest = {
        "schema_version": 1,
        "source": "egif",
        "entity_type": "administrative_record",
        "episode_identity_status": "unresolved",
        "geometry_availability": "none",
        "asset": asset_info,
        "metrics": metrics,
        "annual_counts": {str(year): annual_counts[year] for year in range(config["years"]["min"], config["years"]["max"] + 1)},
        "coverage_regimes": config["coverage_regimes"],
        "cause_mapping": {
            "basis": config["causes"]["mapping_basis"],
            "rows": [
                {"source_code": code, "source_label": raw, "record_count": count, "cause_code": canonical, "cause_label": label,
                 "mapping_status": "mapped" if canonical else "unmapped"}
                for (code, raw, canonical, label), count in sorted(cause_counts.items())
            ],
        },
        "municipality_mapping": {
            "policy": config["municipalities"]["policy"],
            "catalog_source": config["municipalities"]["catalog_path"],
        },
        "provenance": {
            "normalized_input": display_path(args.input),
            "normalized_input_bytes": len(source_bytes),
            "normalized_input_sha256": sha256_bytes(source_bytes),
            "source_manifest": display_path(args.source_manifest),
            "source_retrieved_at": sorted({item["retrieved_at"] for item in source_manifest["provinces"]}),
            "transformations": ["attribute selection", "canonical municipality display names by documented CODINE", "documented cause-code mapping", "compact JSON serialization"],
            "geometry_created": False,
            "records_deduplicated": False,
        },
        "validation": {
            "status": "complete",
            "expected_total": EXPECTED_TOTAL,
            "reconciled_with_cv_3_2": True,
            "annual_counts_reconciled": True,
            "xml_1992": {"alicante": 201, "castellon": 213, "valencia": 356, "total": 770},
            "annual_publication_1992": {"alicante": 201, "castellon": 214, "valencia": 354, "total": 769},
            "annual_publication_discrepancy_preserved": True,
        },
    }
    manifest_payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write(args.output_dir / asset_name, asset_payload)
    atomic_write(args.output_dir / "assets-manifest.json", manifest_payload)
    return manifest


def main():
    manifest = build(parse_args())
    print(json.dumps({"asset": manifest["asset"], "metrics": manifest["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
