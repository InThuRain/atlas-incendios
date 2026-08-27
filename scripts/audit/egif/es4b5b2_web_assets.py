#!/usr/bin/env python3
"""Audit existing ES-4B5B1 national EGIF web assets without rebuilding them.

The audit uses the builder manifest as its primary evidence.  It reads only
the compact ``initial.json`` assets to prove record-level reconciliation and
field distributions; it never opens the 3.78 GB normalised EGIF JSONL input.
The lazy detail files are accounted for from their manifest metadata and a
small deterministic sample is deserialised for structural validation.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ingest/egif"))
from gva_1968_1992 import atomic_write_json, sha256_file  # type: ignore

WEB_DIR = ROOT / "data/web/spain/egif/2026-08-27"
DEFAULT_MANIFEST = WEB_DIR / "manifest.json"
DEFAULT_NORMALIZED_MANIFEST = ROOT / "data/processed/egif/spain/2026-08-27/manifest.json"
DEFAULT_TERRITORY_MANIFEST = ROOT / "data/derived/spain/es4b3/territory_relations/2026-08-27/manifest.json"
DEFAULT_TERRITORIES = ROOT / "data/territories/spain/territories-2026-01-01.json"
DEFAULT_OUTPUT = ROOT / "data/audit/egif/es4b5b2_web_assets.json"

EXPECTED_RECORDS = 646_887
EXPECTED_MUNICIPALITY_RESOLVED = 575_397
EXPECTED_MUNICIPALITY_UNRESOLVED = 71_490
EXPECTED_SOURCE_IDS = ["egif"]
EXPECTED_EXCLUDED_SOURCE_IDS = ["ccinif_grid", "gva_sigif"]
INITIAL_FIELDS = [
    "record_id", "year", "autonomous_community_id", "province_id", "municipality_id",
    "reported_forest_area_ha", "is_gif_forest_ge_500_ha", "cause_source_code",
    "canonical_cause", "cause_mapping_status", "coverage_status", "identity_status",
    "episode_identity_status",
]
DETAIL_FIELDS = [
    "source_record_id", "detection_date", "extinction_date", "reported_total_area_ha",
    "reported_wooded_area_ha", "reported_nonwooded_area_ha", "source_municipality_name",
    "source_paraje", "form_model", "source_database_id",
]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def gzip_size(value: bytes) -> int:
    return len(gzip.compress(value, compresslevel=9, mtime=0))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def portable(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def bytes_per_record(value: int, records: int) -> float | None:
    return round(value / records, 6) if records else None


def ratio(raw: int, compressed: int) -> float | None:
    return round(compressed / raw, 8) if raw else None


def named_territories(path: Path) -> dict[str, str]:
    return {item["territory_id"]: item["official_name"] for item in read_json(path)["territories"]}


def add_size(target: dict[str, int], asset: dict[str, Any]) -> None:
    for role in ("initial", "detail"):
        metadata = asset[role]
        target[f"{role}_raw_bytes"] += metadata["raw_size"]
        target[f"{role}_gzip_bytes"] += metadata["gzip_size"]
    target["raw_bytes"] += asset["initial"]["raw_size"] + asset["detail"]["raw_size"]
    target["gzip_bytes"] += asset["initial"]["gzip_size"] + asset["detail"]["gzip_size"]


def validate_asset_metadata(asset: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    if asset.get("status") != "complete":
        errors.append("asset status is not complete")
    for role in ("initial", "detail"):
        metadata = asset.get(role, {})
        path = root / metadata.get("path", "")
        if not path.is_file():
            errors.append(f"missing {role} asset")
            continue
        if path.stat().st_size != metadata.get("raw_size"):
            errors.append(f"{role} raw size mismatch")
        if sha256_file(path) != metadata.get("sha256"):
            errors.append(f"{role} sha256 mismatch")
        if gzip_size(path.read_bytes()) != metadata.get("gzip_size"):
            errors.append(f"{role} gzip size mismatch")
    return errors


def parse_initial(asset: dict[str, Any], root: Path) -> dict[str, Any]:
    payload = read_json(root / asset["initial"]["path"])
    if payload.get("role") != "initial" or payload.get("fields") != INITIAL_FIELDS:
        raise ValueError(f"{asset['asset_id']}: unexpected initial contract")
    columns = payload.get("columns")
    if not isinstance(columns, dict) or set(columns) != set(INITIAL_FIELDS):
        raise ValueError(f"{asset['asset_id']}: initial columns mismatch")
    count = asset["record_count"]
    if any(len(columns[field]) != count for field in INITIAL_FIELDS):
        raise ValueError(f"{asset['asset_id']}: initial column length mismatch")
    return payload


def validate_detail_sample(asset: dict[str, Any], root: Path) -> dict[str, Any]:
    initial = read_json(root / asset["initial"]["path"])
    detail = read_json(root / asset["detail"]["path"])
    if detail.get("role") != "detail_on_selection" or detail.get("fields") != DETAIL_FIELDS:
        raise ValueError(f"{asset['asset_id']}: unexpected detail contract")
    columns = detail.get("columns")
    if not isinstance(columns, dict) or set(columns) != set(DETAIL_FIELDS):
        raise ValueError(f"{asset['asset_id']}: detail columns mismatch")
    count = asset["record_count"]
    if any(len(columns[field]) != count for field in DETAIL_FIELDS):
        raise ValueError(f"{asset['asset_id']}: detail column length mismatch")
    record_ids = initial["columns"]["record_id"]
    if detail.get("initial_record_id_order_sha256") != digest(canonical_json(record_ids)):
        raise ValueError(f"{asset['asset_id']}: lazy ordinal alignment mismatch")
    if record_ids and not (record_ids[0].startswith("egif-record:") and record_ids[-1].startswith("egif-record:")):
        raise ValueError(f"{asset['asset_id']}: invalid first/last record id")
    return {"asset_id": asset["asset_id"], "record_count": count, "first_record_id": record_ids[0] if record_ids else None, "last_record_id": record_ids[-1] if record_ids else None}


def expected_years(path: Path) -> dict[int, int]:
    return {int(item["year"]): item["records"] for item in read_json(path)["blocks"] if item.get("status") == "complete"}


def audit(*, manifest_path: Path = DEFAULT_MANIFEST, normalized_manifest_path: Path = DEFAULT_NORMALIZED_MANIFEST,
          territory_manifest_path: Path = DEFAULT_TERRITORY_MANIFEST, territories_path: Path = DEFAULT_TERRITORIES,
          validate_checksums: bool = True) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    root = manifest_path.parent
    assets = sorted(manifest.get("assets", []), key=lambda item: item["asset_id"])
    names = named_territories(territories_path)
    errors: list[str] = []
    if manifest.get("source_ids") != EXPECTED_SOURCE_IDS:
        errors.append(f"unexpected source_ids: {manifest.get('source_ids')}")
    if sorted(manifest.get("excluded_source_ids", [])) != sorted(EXPECTED_EXCLUDED_SOURCE_IDS):
        errors.append(f"unexpected excluded_source_ids: {manifest.get('excluded_source_ids')}")

    per_asset: list[dict[str, Any]] = []
    per_territory: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "assets": 0, "records": 0, "raw_bytes": 0, "gzip_bytes": 0,
        "initial_raw_bytes": 0, "initial_gzip_bytes": 0, "detail_raw_bytes": 0, "detail_gzip_bytes": 0,
    })
    per_block: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "assets": 0, "records": 0, "raw_bytes": 0, "gzip_bytes": 0,
        "initial_raw_bytes": 0, "initial_gzip_bytes": 0, "detail_raw_bytes": 0, "detail_gzip_bytes": 0,
    })
    years = Counter()
    seen_ids: set[str] = set()
    duplicate_ids: list[str] = []
    municipality = Counter()
    gif = Counter()
    cause_source = Counter()
    canonical_cause = Counter()
    mapping_status = Counter()
    territory_values = Counter()
    province_values = Counter()
    lookup_raw = lookup_gzip = 0

    for asset in assets:
        if validate_checksums:
            errors.extend(f"{asset['asset_id']}: {message}" for message in validate_asset_metadata(asset, root))
        initial = parse_initial(asset, root)
        columns = initial["columns"]
        ids = columns["record_id"]
        if ids != sorted(ids):
            errors.append(f"{asset['asset_id']}: record_id order is not sorted")
        if len(ids) != len(set(ids)):
            errors.append(f"{asset['asset_id']}: duplicate record_id inside asset")
        for record_id in ids:
            if not isinstance(record_id, str) or not record_id.startswith("egif-record:"):
                errors.append(f"{asset['asset_id']}: invalid record_id")
                continue
            if record_id in seen_ids:
                duplicate_ids.append(record_id)
            seen_ids.add(record_id)
        if any(value != asset["territory_id"] for value in columns["autonomous_community_id"]):
            errors.append(f"{asset['asset_id']}: CCAA values do not match asset territory")
        if any(value is None for value in columns["autonomous_community_id"]):
            errors.append(f"{asset['asset_id']}: null CCAA")
        if any(value is None for value in columns["province_id"]):
            errors.append(f"{asset['asset_id']}: null province")
        if any(value is not None for value in columns["canonical_cause"]):
            errors.append(f"{asset['asset_id']}: canonical cause is populated without codebook")
        if any(value != "unmapped" for value in columns["cause_mapping_status"]):
            errors.append(f"{asset['asset_id']}: cause mapping status differs from unmapped")
        if any(value not in (True, False, None) for value in columns["is_gif_forest_ge_500_ha"]):
            errors.append(f"{asset['asset_id']}: GIF is not tri-state")

        current_lookup_raw = len(canonical_json(ids))
        current_lookup_gzip = gzip_size(canonical_json(ids))
        lookup_raw += current_lookup_raw; lookup_gzip += current_lookup_gzip
        raw = asset["initial"]["raw_size"] + asset["detail"]["raw_size"]
        compressed = asset["initial"]["gzip_size"] + asset["detail"]["gzip_size"]
        item = {
            "asset_id": asset["asset_id"], "autonomous_community_id": asset["territory_id"],
            "autonomous_community_name": names.get(asset["territory_id"]), "from_year": asset["from_year"], "to_year": asset["to_year"],
            "record_count": asset["record_count"], "raw_bytes": raw, "gzip_bytes": compressed,
            "raw_bytes_per_record": bytes_per_record(raw, asset["record_count"]), "gzip_bytes_per_record": bytes_per_record(compressed, asset["record_count"]),
            "compression_ratio_gzip_over_raw": ratio(raw, compressed),
            "initial": asset["initial"], "detail": asset["detail"],
            "record_id_column": {"raw_bytes": current_lookup_raw, "gzip_bytes": current_lookup_gzip,
                                 "initial_raw_percent": round(current_lookup_raw * 100 / asset["initial"]["raw_size"], 6),
                                 "initial_gzip_percent": round(current_lookup_gzip * 100 / asset["initial"]["gzip_size"], 6)},
        }
        per_asset.append(item)
        territorial = per_territory[asset["territory_id"]]; territorial["assets"] += 1; territorial["records"] += asset["record_count"]; add_size(territorial, asset)
        block_id = f"{asset['from_year']}-{asset['to_year']}"; temporal = per_block[block_id]; temporal["assets"] += 1; temporal["records"] += asset["record_count"]; add_size(temporal, asset)
        years.update(columns["year"]); municipality.update("null" if value is None else "resolved" for value in columns["municipality_id"])
        gif.update("true" if value is True else "false" if value is False else "unknown" for value in columns["is_gif_forest_ge_500_ha"])
        cause_source.update("null" if value is None else "present" for value in columns["cause_source_code"])
        canonical_cause.update("null" if value is None else "present" for value in columns["canonical_cause"])
        mapping_status.update("null" if value is None else str(value) for value in columns["cause_mapping_status"])
        territory_values.update(columns["autonomous_community_id"]); province_values.update("null" if value is None else "present" for value in columns["province_id"])

    expected = expected_years(normalized_manifest_path)
    annual_mismatch = {str(year): {"assets": years.get(year, 0), "input": expected.get(year)} for year in sorted(set(years) | set(expected)) if years.get(year, 0) != expected.get(year)}
    if annual_mismatch:
        errors.append("annual record reconciliation mismatch")
    territory_manifest = read_json(territory_manifest_path)
    territory_totals = territory_manifest.get("totals", {})
    if territory_totals.get("records") != len(seen_ids):
        errors.append("territory manifest total does not match web record total")
    if len(assets) != 88:
        errors.append(f"expected 88 assets, found {len(assets)}")
    if len(seen_ids) != EXPECTED_RECORDS:
        errors.append(f"expected {EXPECTED_RECORDS} unique record IDs, found {len(seen_ids)}")
    if duplicate_ids:
        errors.append(f"duplicate record IDs across assets: {len(duplicate_ids)}")

    totals = manifest.get("totals", {})
    calculated_raw = sum(item["raw_bytes"] for item in per_asset)
    calculated_gzip = sum(item["gzip_bytes"] for item in per_asset)
    if totals.get("records") != len(seen_ids) or totals.get("raw_bytes") != calculated_raw or totals.get("gzip_bytes") != calculated_gzip:
        errors.append("manifest totals do not match asset aggregate")
    if municipality["resolved"] != EXPECTED_MUNICIPALITY_RESOLVED or municipality["null"] != EXPECTED_MUNICIPALITY_UNRESOLVED:
        errors.append("municipality resolved/null count differs from ES-4B3 approved total")
    if territory_values.get(None, 0) or province_values.get("null", 0):
        errors.append("null administrative territory observed")

    sample_indices = sorted({0, len(assets) // 2, len(assets) - 1, max(range(len(assets)), key=lambda index: per_asset[index]["gzip_bytes"])}) if assets else []
    structural_sample = [validate_detail_sample(assets[index], root) for index in sample_indices]
    territory_rows = []
    for territory_id, values in sorted(per_territory.items()):
        row = {"autonomous_community_id": territory_id, "autonomous_community_name": names.get(territory_id), **values}
        row["national_record_percent"] = round(values["records"] * 100 / len(seen_ids), 6) if seen_ids else None
        row["raw_bytes_per_record"] = bytes_per_record(values["raw_bytes"], values["records"])
        row["gzip_bytes_per_record"] = bytes_per_record(values["gzip_bytes"], values["records"])
        territory_rows.append(row)
    block_rows = []
    for block_id, values in sorted(per_block.items()):
        row = {"temporal_block": block_id, **values}
        row["raw_bytes_per_record"] = bytes_per_record(values["raw_bytes"], values["records"])
        row["gzip_bytes_per_record"] = bytes_per_record(values["gzip_bytes"], values["records"])
        block_rows.append(row)
    initial_raw = sum(item["initial"]["raw_size"] for item in per_asset); initial_gzip = sum(item["initial"]["gzip_size"] for item in per_asset)
    detail_raw = sum(item["detail"]["raw_size"] for item in per_asset); detail_gzip = sum(item["detail"]["gzip_size"] for item in per_asset)

    result = {
        "schema_version": 1,
        "audit_id": "es-4b5b2-egif-web-assets-1",
        "input": {"builder_manifest": portable(manifest_path), "builder_manifest_sha256": sha256_file(manifest_path),
                  "normalized_manifest": portable(normalized_manifest_path), "normalized_manifest_sha256": sha256_file(normalized_manifest_path),
                  "territory_manifest": portable(territory_manifest_path), "territory_manifest_sha256": sha256_file(territory_manifest_path)},
        "source_scope": {"included_source_ids": manifest.get("source_ids"), "excluded_source_ids": manifest.get("excluded_source_ids"), "profile": manifest.get("profile")},
        "integrity": {"valid": not errors, "errors": errors, "assets": len(assets), "unique_record_ids": len(seen_ids), "duplicate_record_ids": len(duplicate_ids),
                      "annual_reconciliation": {"expected_records": sum(expected.values()), "asset_records": sum(years.values()), "mismatches": annual_mismatch},
                      "territory_manifest_records": territory_totals.get("records"), "structural_sample": structural_sample},
        "totals": {"records": len(seen_ids), "raw_bytes": calculated_raw, "gzip_bytes": calculated_gzip,
                   "raw_bytes_per_record": bytes_per_record(calculated_raw, len(seen_ids)), "gzip_bytes_per_record": bytes_per_record(calculated_gzip, len(seen_ids)),
                   "compression_ratio_gzip_over_raw": ratio(calculated_raw, calculated_gzip)},
        "initial_vs_detail": {"initial": {"raw_bytes": initial_raw, "gzip_bytes": initial_gzip, "raw_percent": round(initial_raw * 100 / calculated_raw, 6), "gzip_percent": round(initial_gzip * 100 / calculated_gzip, 6), "raw_bytes_per_record": bytes_per_record(initial_raw, len(seen_ids)), "gzip_bytes_per_record": bytes_per_record(initial_gzip, len(seen_ids))},
                              "detail_on_selection": {"raw_bytes": detail_raw, "gzip_bytes": detail_gzip, "raw_percent": round(detail_raw * 100 / calculated_raw, 6), "gzip_percent": round(detail_gzip * 100 / calculated_gzip, 6), "raw_bytes_per_record": bytes_per_record(detail_raw, len(seen_ids)), "gzip_bytes_per_record": bytes_per_record(detail_gzip, len(seen_ids))}},
        "record_id_lookup_cost": {"serialized_lookup": "none; the record_id column is the source for a runtime record_id -> ordinal map", "record_id_column_raw_bytes": lookup_raw, "record_id_column_gzip_bytes": lookup_gzip,
                                  "initial_raw_percent": round(lookup_raw * 100 / initial_raw, 6), "initial_gzip_percent": round(lookup_gzip * 100 / initial_gzip, 6),
                                  "runtime_map_heap": "not measured; reserved for ES-4B5C browser benchmarks"},
        "territory_fields": {"autonomous_community": dict(sorted(territory_values.items())), "province": dict(sorted(province_values.items())), "municipality": dict(sorted(municipality.items()))},
        "cause_fields": {"cause_source_code": dict(sorted(cause_source.items())), "canonical_cause": dict(sorted(canonical_cause.items())), "cause_mapping_status": dict(sorted(mapping_status.items()))},
        "gif_administrative": dict(sorted(gif.items())),
        "assets": per_asset,
        "top_assets": {"by_gzip_bytes": sorted(per_asset, key=lambda item: (-item["gzip_bytes"], item["asset_id"]))[:10],
                       "by_record_count": sorted(per_asset, key=lambda item: (-item["record_count"], item["asset_id"]))[:10],
                       "worst_compression": sorted(per_asset, key=lambda item: (-item["compression_ratio_gzip_over_raw"], item["asset_id"]))[:10]},
        "by_autonomous_community": territory_rows,
        "by_temporal_block": block_rows,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--normalized-manifest", type=Path, default=DEFAULT_NORMALIZED_MANIFEST)
    parser.add_argument("--territory-manifest", type=Path, default=DEFAULT_TERRITORY_MANIFEST)
    parser.add_argument("--territories", type=Path, default=DEFAULT_TERRITORIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-checksums", action="store_true", help="only for small synthetic unit-test fixtures")
    args = parser.parse_args(argv)
    result = audit(manifest_path=args.manifest.resolve(), normalized_manifest_path=args.normalized_manifest.resolve(),
                   territory_manifest_path=args.territory_manifest.resolve(), territories_path=args.territories.resolve(),
                   validate_checksums=not args.skip_checksums)
    atomic_write_json(args.output.resolve(), result)
    print(json.dumps({"valid": result["integrity"]["valid"], "assets": result["integrity"]["assets"], "records": result["totals"]["records"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if result["integrity"]["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
