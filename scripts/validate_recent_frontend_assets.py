#!/usr/bin/env python3
"""Validate CV-2.3 reduced assets, identity separation and coverage metadata."""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/web/gva/recent/assets-manifest.json"


def fail(message):
    raise RuntimeError(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def asset_path(url):
    return ROOT / url


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--public-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = load(args.manifest)
    assets = {asset["kind"] + (f":{asset['year']}" if asset.get("year") else ""): asset for asset in manifest["assets"]}
    expected = ({"effis_perimeters:2025": 9, "effis_perimeters:2026": 16} if args.public_only else
                {"sigif_points:2025": 281, "sigif_points:2026": 143, "effis_perimeters:2025": 9,
                 "effis_perimeters:2026": 16, "link_candidates_visible": 11, "link_candidates_debug": 42})
    if set(assets) != set(expected):
        fail("Unexpected recent asset set")
    for key, count in expected.items():
        asset = assets.get(key)
        if not asset or asset["feature_count"] != count:
            fail(f"Unexpected count for {key}")
        payload = asset_path(asset["url"]).read_bytes()
        actual = {"bytes": len(payload), "gzip_bytes": len(gzip.compress(payload, compresslevel=9)), "sha256": hashlib.sha256(payload).hexdigest()}
        if any(actual[field] != asset[field] for field in actual):
            fail(f"Integrity mismatch for {key}")

    effis_2025 = load(asset_path(assets["effis_perimeters:2025"]["url"]))["features"]
    effis_2026 = load(asset_path(assets["effis_perimeters:2026"]["url"]))["features"]
    ibi_effis = [item for item in effis_2025 if item["properties"]["effis_id"] == "275862"]
    if len(ibi_effis) != 1:
        fail("Ibi EFFIS acceptance perimeter missing")
    if not args.public_only:
        sigif_2025 = load(asset_path(assets["sigif_points:2025"]["url"]))["features"]
        candidates = load(asset_path(assets["link_candidates_visible"]["url"]))
        ibi_sigif = [item for item in sigif_2025 if item["properties"]["municipality"] == "Ibi" and item["properties"]["place_name"] == "Sant Pasqual"]
        ibi_links = [item for item in candidates if item["effis_id"] == "275862"]
        if len(ibi_sigif) != 1 or len(ibi_links) != 1:
            fail("Ibi acceptance records missing")
        if ibi_links[0]["candidate_strength"] != "strong_candidate" or ibi_links[0]["score"] != 90 or ibi_links[0]["link_status"] != "candidate":
            fail("Ibi candidate was changed or confirmed")
        if ibi_sigif[0]["properties"]["entity_id"] == ibi_effis[0]["properties"]["entity_id"]:
            fail("SIGIF and EFFIS identities were merged")
    for effis_id in ("570518", "612812"):
        matches = [item for item in effis_2026 if item["properties"]["effis_id"] == effis_id]
        if len(matches) != 1 or matches[0]["properties"]["date"] <= "2026-06-30":
            fail(f"Post-cutoff case missing: {effis_id}")
    coverage = {item["year"]: item for item in manifest["coverage"]}
    if args.public_only:
        serialized = json.dumps(manifest).lower()
        if "sigif" in serialized or "candidate" in serialized:
            fail("Forbidden source metadata in public recent manifest")
    elif coverage[2026]["coverage_complete"] is not False or coverage[2026]["sigif_max_date"] != "2026-06-30":
        fail("2026 incomplete coverage lost")
    collections = (effis_2025, effis_2026) if args.public_only else (sigif_2025, effis_2025, effis_2026)
    for collection in collections:
        if any("original_attributes" in item["properties"] for item in collection):
            fail("Raw original_attributes leaked into web assets")

    with tempfile.TemporaryDirectory() as directory:
        public_path = Path(directory) / "public.json"
        public = subprocess.run([sys.executable, str(ROOT / "scripts/build_frontend_profile.py"), "--profile", "public", "--output", str(public_path)], capture_output=True, text=True)
        blocked = subprocess.run([sys.executable, str(ROOT / "scripts/build_frontend_profile.py"), "--profile", "public", "--include-source", "sigif", "--output", str(Path(directory) / "blocked.json")], capture_output=True, text=True)
        if public.returncode or blocked.returncode == 0:
            fail("Public profile guard failed")
        public_manifest = load(public_path)
        if set(public_manifest["sources"]) != {"icv", "effis"} or public_manifest["icv"] is None:
            fail("Public profile does not contain the publishable ICV and EFFIS sources")
        icv_source = public_manifest["sources"]["icv"]
        if (
            icv_source.get("copyright_holder") != "Generalitat"
            or not icv_source.get("license_status", "").startswith("provider_confirmed_")
            or "Datos transformados para su visualización" not in icv_source.get("attribution", "")
        ):
            fail("Public profile lost the provider-confirmed ICV attribution")
        public_coverage = json.dumps(public_manifest["recent"]["coverage"])
        if "sigif_" in public_coverage or "candidate" in public_coverage or "coverage_complete" in public_coverage:
            fail("Blocked SIGIF metadata leaked into the public profile")
    total = sum(asset["bytes"] for asset in manifest["assets"])
    gzip_total = sum(asset["gzip_bytes"] for asset in manifest["assets"])
    summary = {"status": "passed", "profile": "public" if args.public_only else "development",
               "assets": len(manifest["assets"]), "bytes": total, "gzip_bytes": gzip_total,
               "effis": {"2025": 9, "2026": 16}, "public_guard": "passed"}
    if not args.public_only:
        summary.update({"sigif": {"2025": 281, "2026": 143}, "visible_candidates": 11, "weak_debug_candidates": 42})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        print(f"recent frontend validation failed: {error}", file=sys.stderr)
        sys.exit(1)
