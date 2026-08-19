#!/usr/bin/env python3
"""Validate the exact static production subset consumed by CV-1.5."""

import argparse
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def repository_root():
    return Path(__file__).resolve().parents[1]


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, default=root / "config/datasets-gva.json"
    )
    parser.add_argument(
        "--asset-dir", type=Path, default=root / "data/web/gva"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data/derived/gva/frontend/asset_validation.json",
    )
    return parser.parse_args()


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def metrics(path):
    payload = path.read_bytes()
    return {
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def local_path(asset_dir, url):
    relative = Path(url).relative_to("data/web/gva")
    return asset_dir / relative


def main():
    args = parse_args()
    manifest = load_json(args.manifest)
    source = manifest["source"]
    required_source_fields = (
        "dataset_identifier",
        "owner",
        "publisher",
        "catalog_url",
        "metadata_url",
        "metadata_revision_date",
        "license_id",
        "license_url",
        "terms_url",
        "attribution",
        "credit",
    )
    missing_source_fields = [
        field for field in required_source_fields if not source.get(field)
    ]
    if missing_source_fields:
        raise ValidationError(
            "Missing source/license metadata: {}".format(missing_source_fields)
        )
    if source["license_id"] != "CC-BY-4.0":
        raise ValidationError("Unexpected source license")
    derivation = manifest["derivation"]
    if (
        not derivation.get("is_modified")
        or derivation.get("geometry_repaired")
        or derivation.get("geometry_deduplicated")
        or not derivation.get("modification_notice")
    ):
        raise ValidationError("Incomplete or inconsistent derivation metadata")
    publication = manifest["publication"]
    if publication.get("status") not in (
        "blocked_pending_icv_clarification",
        "ready",
    ):
        raise ValidationError("Unknown publication status")
    if publication["status"] == "ready" and publication.get(
        "license_review_required"
    ):
        raise ValidationError("Publication cannot be ready with a pending review")
    geometry_assets = manifest["geometry_assets"]
    static_assets = list(manifest["attributes"].values())
    assets = geometry_assets + static_assets
    expected_paths = {local_path(args.asset_dir, asset["url"]).resolve() for asset in assets}
    actual_paths = {
        path.resolve() for path in args.asset_dir.rglob("*") if path.is_file()
    }
    if actual_paths != expected_paths:
        missing = sorted(str(path) for path in expected_paths - actual_paths)
        unexpected = sorted(str(path) for path in actual_paths - expected_paths)
        raise ValidationError("Asset set mismatch; missing={}, unexpected={}".format(missing, unexpected))

    raw_bytes = 0
    gzip_bytes = 0
    for asset in assets:
        path = local_path(args.asset_dir, asset["url"])
        actual = metrics(path)
        for field in ("bytes", "gzip_bytes", "sha256"):
            if actual[field] != asset[field]:
                raise ValidationError("{} differs for {}".format(field, path))
        raw_bytes += actual["bytes"]
        gzip_bytes += actual["gzip_bytes"]

    fire_payload = load_json(local_path(args.asset_dir, manifest["attributes"]["fires"]["url"]))
    fires = fire_payload["fires"]
    fire_by_id = {fire["fire_id"]: fire for fire in fires}
    if len(fires) != 13738 or len(fire_by_id) != 13738:
        raise ValidationError("Unexpected fire count")
    known = fire_by_id.get("gva:pif-cv:2024AL0005")
    if not known or len(known["geometry_ids"]) != 2:
        raise ValidationError("2024AL0005 does not retain two geometry IDs")

    level_results = {}
    reference_ids = None
    for level in ("overview", "regional", "local"):
        features = []
        level_assets = [asset for asset in geometry_assets if asset["level"] == level]
        if len(level_assets) != 12:
            raise ValidationError("{} does not contain 12 assets".format(level))
        for asset in level_assets:
            payload = load_json(local_path(args.asset_dir, asset["url"]))
            if len(payload["features"]) != asset["feature_count"]:
                raise ValidationError("Feature count differs: {}".format(asset["url"]))
            features.extend(payload["features"])
        ids = [feature["properties"]["geometry_id"] for feature in features]
        fire_ids = {feature["properties"]["fire_id"] for feature in features}
        reused = sum(bool(feature["properties"]["geometry_reused"]) for feature in features)
        known_features = [
            feature
            for feature in features
            if feature["properties"]["fire_id"] == "gva:pif-cv:2024AL0005"
        ]
        if len(features) != 13739 or len(set(ids)) != 13739:
            raise ValidationError("Unexpected geometry count in {}".format(level))
        if len(fire_ids) != 13738 or reused != 1823 or len(known_features) != 2:
            raise ValidationError("Identity/reuse mismatch in {}".format(level))
        if reference_ids is None:
            reference_ids = set(ids)
        elif set(ids) != reference_ids:
            raise ValidationError("Levels contain different geometry IDs")
        level_results[level] = {
            "asset_count": len(level_assets),
            "geometry_count": len(features),
            "unique_geometry_id_count": len(set(ids)),
            "unique_fire_id_count": len(fire_ids),
            "geometry_reused_count": reused,
            "2024AL0005_geometry_count": len(known_features),
        }

    subset = manifest["production_subset"]
    if (
        raw_bytes != subset["raw_bytes"]
        or gzip_bytes != subset["gzip_bytes"]
        or len(assets) != subset["total_file_count"]
    ):
        raise ValidationError("Production totals differ from manifest")
    report = {
        "schema_version": 1,
        "status": "complete",
        "manifest": str(args.manifest.relative_to(repository_root())),
        "asset_count": len(assets),
        "raw_bytes": raw_bytes,
        "gzip_bytes": gzip_bytes,
        "benchmark_assets_included": False,
        "publication_status": publication["status"],
        "license_id": source["license_id"],
        "derivative_changes_disclosed": derivation["is_modified"],
        "fires": {"count": len(fires), "unique_fire_id_count": len(fire_by_id)},
        "levels": level_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".part")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(args.output))
    print(args.output)


if __name__ == "__main__":
    try:
        main()
    except (ValidationError, OSError, KeyError, TypeError, ValueError) as error:
        print("frontend asset validation failed: {}".format(error), file=sys.stderr)
        sys.exit(1)
