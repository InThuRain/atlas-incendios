#!/usr/bin/env python3
"""Validate the geometry-free EGIF web derivative and its reconciliation."""

import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PROVINCES = {"alicante": 2514, "castellon": 2600, "valencia": 4061}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/web/gva/egif/assets-manifest.json")
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    asset = manifest["asset"]
    path = args.asset_root / asset["url"]
    payload = path.read_bytes()
    checks = {
        "bytes": len(payload),
        "gzip_bytes": len(gzip.compress(payload, compresslevel=9, mtime=0)),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if any(checks[key] != asset[key] for key in checks):
        raise SystemExit("EGIF asset size/checksum mismatch")
    web = json.loads(payload)
    if web.get("fields") != asset.get("fields"):
        raise SystemExit("EGIF compact schema mismatch")
    forbidden_fields = {"original_attributes", "coordinates", "map_sheet", "grid", "point", "centroid"}
    if forbidden_fields.intersection(web["fields"]):
        raise SystemExit("EGIF web asset leaks raw/spatial fields")
    records = [dict(zip(web["fields"], row)) for row in web["records"]]
    if len(records) != 9175 or len({item["record_id"] for item in records}) != 9175 or len({item["fire_id"] for item in records}) != 9175:
        raise SystemExit("EGIF identity/count mismatch")
    if any(item["source"] != "egif" or item["entity_type"] != "administrative_record" or item["geometry"] is not None for item in records):
        raise SystemExit("EGIF entity/geometry contract mismatch")
    if any(item["identity_status"] != "source_record_only" or item["episode_identity_status"] != "unresolved" for item in records):
        raise SystemExit("EGIF report/episode identity semantics changed")
    provinces = collections.Counter(item["province_id"] for item in records)
    if dict(provinces) != EXPECTED_PROVINCES:
        raise SystemExit("EGIF province count mismatch")
    in_1992 = collections.Counter(item["province_id"] for item in records if item["year"] == 1992)
    if dict(in_1992) != {"alicante": 201, "castellon": 213, "valencia": 356}:
        raise SystemExit("EGIF 1992 count mismatch")
    metrics = manifest["metrics"]
    expected = {"records": 9175, "gif_forest_ge_500_ha": 180, "municipality_resolved": 5254,
                "municipality_unresolved": 3921, "with_grid_reference": 8565,
                "without_usable_spatial_location": 610, "geometries": 0}
    if any(metrics[key] != value for key, value in expected.items()):
        raise SystemExit("EGIF CV-3.2 reconciliation mismatch")
    if metrics["cause_source_values_unmapped"] != 0:
        raise SystemExit("An EGIF cause source value is not explicitly classified")
    if [item["id"] for item in manifest["coverage_regimes"]] != ["selective", "transitional", "systematic_or_near_systematic"]:
        raise SystemExit("EGIF coverage regime mismatch")
    if not manifest["validation"]["annual_publication_discrepancy_preserved"]:
        raise SystemExit("The 1992 XML/annual-publication discrepancy was lost")
    print(json.dumps({"status": "passed", "asset": asset, "metrics": metrics, "year_1992": dict(in_1992)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
