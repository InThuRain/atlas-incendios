#!/usr/bin/env python3
"""Validate ES-2 national contracts and fail-closed publication profiles."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ALLOWED_GEOMETRY_SEMANTICS = {
    "none",
    "official_fire_perimeter",
    "documented_remote_sensing_perimeter",
    "provisional_remote_sensing_perimeter",
    "historical_location_reference",
    "administrative_point",
    "documented_cartographic_reconstruction",
}
FIRE_GEOMETRY_SEMANTICS = ALLOWED_GEOMETRY_SEMANTICS - {"none", "historical_location_reference"}
CONFIRMED_LICENSE = "confirmed"
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$")


class ContractError(ValueError):
    pass


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_keys(item: dict, keys: Iterable[str], context: str) -> None:
    missing = [key for key in keys if key not in item]
    if missing:
        raise ContractError(f"{context}: missing keys {missing}")


def require_identifier(value: object, context: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ContractError(f"{context}: invalid identifier {value!r}")
    return value


def validate_source_catalog(catalog: dict) -> None:
    require_keys(catalog, ["schema_version", "catalog_id", "country", "profiles", "sources"], "source catalog")
    if catalog["schema_version"] != 1 or catalog["country"] != "ES":
        raise ContractError("source catalog: unsupported schema/country")
    sources = catalog["sources"]
    if not isinstance(sources, dict) or not sources:
        raise ContractError("source catalog: sources must be a non-empty object")
    for key, source in sources.items():
        require_keys(source, [
            "source_id", "name", "owner", "scope", "temporal_coverage",
            "geometry_semantics", "quality", "license", "publishable",
            "publication_status", "update_policy", "provenance",
        ], f"source {key}")
        if key != source["source_id"]:
            raise ContractError(f"source {key}: source_id mismatch")
        require_identifier(key, f"source {key}")
        if source["scope"].get("country") != "ES":
            raise ContractError(f"source {key}: scope country must be ES")
        unknown = set(source["geometry_semantics"]) - ALLOWED_GEOMETRY_SEMANTICS
        if unknown:
            raise ContractError(f"source {key}: unknown geometry semantics {sorted(unknown)}")
        license_data = source["license"]
        require_keys(license_data, ["status", "license_id", "url", "attribution", "transformation_notice_required"], f"source {key} license")
        if source["publishable"] and license_data["status"] != CONFIRMED_LICENSE:
            raise ContractError(f"source {key}: publishable source lacks confirmed license")
    for profile, source_ids in catalog["profiles"].items():
        missing = set(source_ids) - set(sources)
        if missing:
            raise ContractError(f"profile {profile}: unknown sources {sorted(missing)}")


def validate_publication(catalog: dict, source_ids: Iterable[str], assets: Iterable[dict] = ()) -> dict:
    """Fail closed unless every requested source and asset is publishable."""
    validate_source_catalog(catalog)
    requested = list(source_ids)
    if not requested:
        raise ContractError("publication profile: no sources requested")
    for source_id in requested:
        source = catalog["sources"].get(source_id)
        if source is None:
            raise ContractError(f"publication profile: unknown source {source_id}")
        if not source["publishable"]:
            raise ContractError(f"publication profile: blocked source {source_id}")
        license_data = source["license"]
        if license_data["status"] != CONFIRMED_LICENSE or not license_data.get("attribution"):
            raise ContractError(f"publication profile: incomplete license/attribution for {source_id}")
    asset_count = 0
    for asset in assets:
        asset_count += 1
        require_keys(asset, ["asset_id", "source_id", "profile", "publishable", "license_status", "attribution", "provenance", "url", "sha256", "byte_size"], "publication asset")
        if asset["source_id"] not in requested:
            raise ContractError(f"publication asset {asset['asset_id']}: source absent from profile")
        if not asset["publishable"] or asset["license_status"] != CONFIRMED_LICENSE:
            raise ContractError(f"publication asset {asset['asset_id']}: blocked")
        if not asset["attribution"] or not asset["provenance"]:
            raise ContractError(f"publication asset {asset['asset_id']}: missing attribution/provenance")
        if not re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]):
            raise ContractError(f"publication asset {asset['asset_id']}: invalid checksum")
    return {
        "all_included_sources_publishable": True,
        "source_count": len(requested),
        "asset_count": asset_count,
    }


def validate_territory_snapshot(snapshot: dict, manifest: dict) -> None:
    require_keys(snapshot, ["schema_version", "snapshot_id", "reference_date", "country", "geometry_embedded", "territories"], "territory snapshot")
    if snapshot["geometry_embedded"]:
        raise ContractError("territory snapshot: ES-2 snapshot must not embed geometry")
    territories = snapshot["territories"]
    by_id = {}
    types = {"country": 0, "autonomous_community": 0, "autonomous_city": 0, "province": 0, "municipality": 0}
    for item in territories:
        require_keys(item, ["territory_id", "territory_type", "official_code", "official_name", "parent_id", "aliases", "valid_from", "valid_to", "predecessor_ids", "successor_ids", "provenance"], "territory")
        territory_id = require_identifier(item["territory_id"], "territory")
        if territory_id in by_id:
            raise ContractError(f"territory snapshot: duplicate {territory_id}")
        if item["territory_type"] not in types:
            raise ContractError(f"territory {territory_id}: invalid territory_type")
        types[item["territory_type"]] += 1
        by_id[territory_id] = item
    for territory_id, item in by_id.items():
        parent = item["parent_id"]
        if parent is not None and parent not in by_id:
            raise ContractError(f"territory {territory_id}: missing parent {parent}")
    expected = {"country": 1, "autonomous_community": 17, "autonomous_city": 2, "province": 50, "municipality": 8132}
    if types != expected:
        raise ContractError(f"territory snapshot: counts {types} != {expected}")
    for territory_id, item in by_id.items():
        parent = by_id.get(item["parent_id"])
        if item["territory_type"] == "country" and item["parent_id"] is not None:
            raise ContractError("country territory cannot have a parent")
        if item["territory_type"] in {"autonomous_community", "autonomous_city"} and (not parent or parent["territory_type"] != "country"):
            raise ContractError(f"territory {territory_id}: autonomous territory must descend from country")
        if item["territory_type"] == "province" and (not parent or parent["territory_type"] != "autonomous_community"):
            raise ContractError(f"territory {territory_id}: province must descend from an autonomous community")
        if item["territory_type"] == "municipality" and (not parent or parent["territory_type"] not in {"province", "autonomous_city"}):
            raise ContractError(f"territory {territory_id}: municipality must descend from province or autonomous city")
    if manifest.get("counts", {}).get("total_territories") != len(territories):
        raise ContractError("territory manifest: total count mismatch")
    if manifest.get("output", {}).get("geometry_embedded"):
        raise ContractError("territory manifest: geometry unexpectedly embedded")
    require_keys(manifest, ["schema_version", "manifest_type", "generated_at", "partitions"], "territory manifest")
    if manifest["manifest_type"] != "territory" or len(manifest["partitions"]) != 1:
        raise ContractError("territory manifest: expected one territory partition")
    partition = manifest["partitions"][0]
    require_keys(partition, ["partition_id", "source_id", "territory_ids", "period", "lod", "geometry_semantics", "feature_count", "byte_size", "sha256", "url", "publication_profiles"], "territory partition")
    if partition["feature_count"] != len(territories) or partition["sha256"] != manifest["output"]["sha256"]:
        raise ContractError("territory manifest: partition/output mismatch")


def validate_fixture(fixture: dict, catalog: dict) -> None:
    require_keys(fixture, ["fixture_id", "territories", "source_records", "fire_geometries", "historical_spatial_references", "territory_relations", "candidate_links"], "fixture")
    territory_ids = {item["territory_id"] for item in fixture["territories"]}
    geometry_ids = {item["geometry_id"] for item in fixture["fire_geometries"]}
    spatial_ids = {item["spatial_reference_id"] for item in fixture["historical_spatial_references"]}
    relation_ids = set()
    relation_tuples = set()
    for item in fixture["territory_relations"]:
        require_keys(item, ["territory_relation_id", "subject_id", "territory_id", "relation_type", "mapping_status", "qa_status", "provenance"], "territory relation")
        if item["territory_id"] not in territory_ids:
            raise ContractError(f"fixture {fixture['fixture_id']}: missing territory {item['territory_id']}")
        relation_id = require_identifier(item["territory_relation_id"], "territory relation")
        relation_key = (item["subject_id"], item["territory_id"], item["relation_type"])
        if relation_id in relation_ids or relation_key in relation_tuples:
            raise ContractError(f"fixture {fixture['fixture_id']}: duplicated territory relation")
        relation_ids.add(relation_id)
        relation_tuples.add(relation_key)
    for item in fixture["source_records"]:
        require_keys(item, ["record_id", "source_id", "temporal_validity", "geometry_ids", "spatial_reference_id", "provenance"], "source record")
        require_identifier(item["record_id"], "source record")
        if item["source_id"] not in catalog["sources"]:
            raise ContractError(f"fixture {fixture['fixture_id']}: unknown source {item['source_id']}")
        missing_geometries = set(item["geometry_ids"]) - geometry_ids
        if missing_geometries:
            raise ContractError(f"fixture {fixture['fixture_id']}: missing geometries {sorted(missing_geometries)}")
        if item["spatial_reference_id"] is not None and item["spatial_reference_id"] not in spatial_ids:
            raise ContractError(f"fixture {fixture['fixture_id']}: missing spatial reference {item['spatial_reference_id']}")
        if item["source_id"] == "egif" and item["geometry_ids"]:
            raise ContractError("EGIF source record must keep geometry_ids empty")
    for item in fixture["fire_geometries"]:
        require_keys(item, ["geometry_id", "source_id", "geometry_semantics", "quality", "geometry", "territory_relation_ids", "provenance"], "fire geometry")
        if item["geometry_semantics"] not in FIRE_GEOMETRY_SEMANTICS:
            raise ContractError(f"fire geometry {item['geometry_id']}: invalid semantics")
        missing_relations = set(item["territory_relation_ids"]) - relation_ids
        if missing_relations:
            raise ContractError(f"fire geometry {item['geometry_id']}: missing relations {sorted(missing_relations)}")
    for item in fixture["historical_spatial_references"]:
        require_keys(item, ["spatial_reference_id", "source_id", "spatial_semantics", "interpretation_status", "geometry_parts", "geometry_status", "provenance"], "historical spatial reference")
        if item["spatial_semantics"] != "historical_location_reference" or item["geometry_status"] != "not_fire_geometry":
            raise ContractError(f"spatial reference {item['spatial_reference_id']}: semantic contract violated")
        if item["interpretation_status"] == "ambiguous" and item.get("sheet_id") is not None and "canarias" in item["spatial_reference_id"]:
            raise ContractError("Canary ambiguous reference must not invent a sheet code")
    for item in fixture["candidate_links"]:
        require_keys(item, ["candidate_link_id", "subject_id", "object_id", "link_type", "status", "evidence", "provenance"], "candidate link")
        if item["status"] == "confirmed" and not any(e.get("kind") == "independent_documentary_identity" for e in item["evidence"]):
            raise ContractError(f"candidate link {item['candidate_link_id']}: confirmation lacks documentary identity")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path("config/sources-spain.json"))
    parser.add_argument("--snapshot", type=Path, default=Path("data/territories/spain/territories-2026-01-01.json"))
    parser.add_argument("--territory-manifest", type=Path, default=Path("data/sources/spain_territory_snapshot_manifest.json"))
    parser.add_argument("--fixtures", nargs="*", type=Path, default=sorted(Path("tests/fixtures/es2").glob("*.json")))
    parser.add_argument("--publication-profile")
    parser.add_argument("--force-source", action="append", default=[])
    args = parser.parse_args()

    catalog = load_json(args.catalog)
    validate_source_catalog(catalog)
    validate_territory_snapshot(load_json(args.snapshot), load_json(args.territory_manifest))
    for path in args.fixtures:
        validate_fixture(load_json(path), catalog)
    publication = None
    if args.publication_profile:
        if args.publication_profile not in catalog["profiles"]:
            raise ContractError(f"Unknown publication profile {args.publication_profile}")
        sources = list(catalog["profiles"][args.publication_profile]) + args.force_source
        publication = validate_publication(catalog, sources)
    print(json.dumps({
        "valid": True,
        "catalog_sources": len(catalog["sources"]),
        "fixtures": len(args.fixtures),
        "publication_guard": publication,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        raise SystemExit(2)
