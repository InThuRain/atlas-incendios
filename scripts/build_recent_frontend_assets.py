#!/usr/bin/env python3
"""Build reduced, local-only CV-2.3 web assets from the latest CV-2.2 snapshot."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest", type=Path, default=ROOT / "data/processed/recent/gva/latest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/web/gva/recent")
    return parser.parse_args()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def canonical_province(value):
    text = (value or "").lower()
    if "castell" in text:
        return "castellon"
    if "val" in text:
        return "valencia"
    if "alacant" in text or "alicante" in text:
        return "alicante"
    return None


def compact_json_bytes(payload):
    return (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write_asset(output, relative, payload, kind, year=None):
    data = compact_json_bytes(payload)
    path = output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(data)
    os.replace(temporary, path)
    return {
        "kind": kind,
        "year": year,
        "url": "data/web/gva/recent/" + relative.as_posix(),
        "feature_count": len(payload.get("features", [])) if isinstance(payload, dict) else len(payload),
        "bytes": len(data),
        "gzip_bytes": len(gzip.compress(data, compresslevel=9)),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def sigif_feature(row):
    return {
        "type": "Feature",
        "id": row["sigif_record_id"],
        "properties": {
            "source_id": "sigif",
            "entity_id": row["sigif_record_id"],
            "sigif_record_id": row["sigif_record_id"],
            "year": row["source_year"],
            "date": row.get("observed_date"),
            "municipality": row.get("municipality"),
            "municipality_source_id": (row.get("derived_admin_at_point") or {}).get("municipality_ine_code"),
            "province": (row.get("derived_admin_at_point") or {}).get("province"),
            "province_key": canonical_province((row.get("derived_admin_at_point") or {}).get("province")),
            "county": row.get("comarca"),
            "place_name": row.get("place_name"),
            "cause": row.get("cause"),
            "reported_area_ha": row.get("reported_total_area_ha"),
            "reported_wooded_area_ha": row.get("reported_wooded_area_ha"),
            "reported_shrub_grass_area_ha": row.get("reported_shrub_grass_area_ha"),
            "is_gif": float(row.get("reported_total_area_ha") or 0) >= 500,
            "source_row_index": row.get("source_row_index"),
            "source_row_hash_sha256": row.get("source_row_hash_sha256"),
            "source_status": "provisional_administrative",
            "geometry_kind": "start_point",
            "coordinate_crs_original": row.get("coordinate_crs"),
            "x1_original": row.get("x1_original"),
            "y1_original": row.get("y1_original"),
            "acquired_at": (row.get("provenance") or {}).get("acquired_at"),
            "coverage_complete": (row.get("provenance") or {}).get("coverage_complete"),
        },
        "geometry": row["point_epsg4326"],
    }


def effis_feature(feature):
    source = feature["properties"]
    return {
        "type": "Feature",
        "id": source["geometry_id"],
        "properties": {
            "source_id": "effis",
            "entity_id": source["geometry_id"],
            "geometry_id": source["geometry_id"],
            "effis_id": source.get("effis_id"),
            "year": source.get("source_year"),
            "date": source.get("effis_fire_date"),
            "final_date": source.get("effis_final_date"),
            "last_update": source.get("effis_last_update"),
            "municipality": source.get("effis_commune"),
            "province": source.get("effis_province"),
            "province_key": canonical_province(source.get("effis_province")),
            "mapped_area_ha": source.get("effis_area_ha"),
            "source_status": "provisional_satellite",
            "geometry_quality": "B_provisional_satellite",
            "geometry_kind": "satellite_perimeter",
            "geometry_checksum_sha256": source.get("geometry_checksum_sha256"),
            "acquired_at": (source.get("provenance") or {}).get("acquired_at"),
        },
        "geometry": feature["geometry"],
    }


def main():
    args = parse_args()
    latest = read_json(args.latest)
    snapshot = ROOT / latest["manifest"]
    base = snapshot.parent
    coverage = read_json(base / "coverage_report.json")
    assets = []
    for year in (2025, 2026):
        sigif_rows = read_jsonl(base / f"sigif_fires_{year}.jsonl")
        sigif = {"type": "FeatureCollection", "features": [sigif_feature(row) for row in sigif_rows]}
        assets.append(write_asset(args.output, Path("sigif") / f"{year}.geojson", sigif, "sigif_points", year))
        effis_source = read_json(base / f"effis_geometries_{year}.geojson")
        effis = {"type": "FeatureCollection", "features": [effis_feature(item) for item in effis_source["features"]]}
        assets.append(write_asset(args.output, Path("effis") / f"{year}.geojson", effis, "effis_perimeters", year))

    candidates = read_jsonl(base / "sigif_effis_link_candidates.jsonl")
    visible = [item for item in candidates if item["candidate_strength"] in {"strong_candidate", "possible_candidate"}]
    weak = [item for item in candidates if item["candidate_strength"] == "weak_candidate"]
    assets.append(write_asset(args.output, Path("candidates-visible.json"), visible, "link_candidates_visible"))
    assets.append(write_asset(args.output, Path("candidates-weak.json"), weak, "link_candidates_debug"))

    manifest = {
        "schema_version": 1,
        "phase": "CV-2.3",
        "snapshot_id": latest["snapshot_id"],
        "acquired_at": latest["updated_at"],
        "source_processed_manifest": latest["manifest"],
        "coverage": coverage["years"],
        "assets": assets,
        "candidate_links_are_confirmed": False,
        "transformations": [
            "SIGIF EPSG:4326 derived points copied from the demonstrated CV-2.2 transformation",
            "EFFIS geometries retained in EPSG:4326 without simplification",
            "browser attributes reduced; source snapshots and original attributes remain in processed data",
        ],
    }
    write_asset(args.output, Path("assets-manifest.json"), manifest, "recent_manifest")
    print(json.dumps({"output": str(args.output), "assets": assets}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
