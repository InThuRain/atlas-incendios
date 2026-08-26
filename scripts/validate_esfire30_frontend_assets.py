#!/usr/bin/env python3
"""Validate the exact ESFire30 web assets without requiring the raw snapshot."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[1]


def metrics(path):
    payload = path.read_bytes()
    return {
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/web/gva/esfire30/assets-manifest.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if (manifest.get("source") != "esfire30" or manifest.get("source_version") != "v1"
            or manifest.get("doi") != "10.5281/zenodo.18449006"
            or manifest.get("geometry_quality") != "B_DOCUMENTED_REMOTE_SENSING"
            or manifest.get("episode_identity_status") != "unresolved"):
        raise SystemExit("Unexpected ESFire30 source metadata")
    expected_metrics = manifest["metrics"]
    if (expected_metrics.get("features") != 710
            or expected_metrics.get("primary_province_counts") != {"alicante": 195, "castellon": 206, "valencia": 309}
            or expected_metrics.get("mapped_area_ha") != 127083.78
            or expected_metrics.get("mapped_area_ge_500_ha") != 36):
        raise SystemExit("Unexpected ESFire30 reconciliation metrics")

    reference_ids = None
    levels = {}
    for asset in manifest.get("assets", []):
        path = ROOT / asset["url"]
        actual = metrics(path)
        if any(actual[key] != asset[key] for key in ("bytes", "gzip_bytes", "sha256")):
            raise SystemExit("ESFire30 asset integrity mismatch: {}".format(asset["url"]))
        payload = json.loads(path.read_text(encoding="utf-8"))
        features = payload.get("features", [])
        if len(features) != 710 or len(features) != asset.get("feature_count"):
            raise SystemExit("Unexpected ESFire30 feature count: {}".format(asset["url"]))
        ids = []
        for feature in features:
            properties = feature.get("properties", {})
            geometry = shape(feature.get("geometry"))
            if (properties.get("source_id") != "esfire30"
                    or properties.get("episode_identity_status") != "unresolved"
                    or properties.get("administrative_link_status") != "unlinked"
                    or not str(properties.get("entity_id", "")).startswith("esfire30:record:sha256:")
                    or not str(properties.get("geometry_id", "")).startswith("esfire30:geometry:sha256:")
                    or geometry.is_empty or not geometry.is_valid
                    or geometry.geom_type not in {"Polygon", "MultiPolygon"}):
                raise SystemExit("Invalid ESFire30 web feature")
            ids.append(properties["geometry_id"])
        if len(set(ids)) != 710:
            raise SystemExit("Duplicate ESFire30 geometry_id")
        if reference_ids is None:
            reference_ids = set(ids)
        elif set(ids) != reference_ids:
            raise SystemExit("ESFire30 LOD levels contain different identities")
        levels[asset["level"]] = actual
    if set(levels) != {"local", "regional", "overview"}:
        raise SystemExit("ESFire30 must contain exactly three LOD assets")
    print(json.dumps({"status": "passed", "features_per_level": 710, "levels": levels, "metrics": expected_metrics}, indent=2))


if __name__ == "__main__":
    main()
