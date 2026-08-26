#!/usr/bin/env python3
"""Validate the final Pages directory and its exact public data surface."""

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_ICV_ATTRIBUTION = "Incendios forestales de la Comunitat Valenciana (1993–2024) CC BY 4.0, Generalitat. Datos transformados para su visualización mediante reproyección, selección de atributos, particionado y simplificación geométrica."
EXPECTED_CLOUDFLARE_BEACON = "https://static.cloudflareinsights.com/beacon.min.js"
EXPECTED_CLOUDFLARE_TOKEN = "6fa57a47de124ffe8b2bfb8b61ad3baf"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    args = parser.parse_args()
    runtime_path = args.site / "data/web/gva/manifest.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if runtime["profile"] != "public" or set(runtime["sources"]) != {"egif", "esfire30", "icv", "effis"}:
        raise SystemExit("Invalid public source set")
    if runtime["sources"]["icv"]["attribution"] != EXPECTED_ICV_ATTRIBUTION:
        raise SystemExit("Incorrect ICV attribution")
    if runtime["sources"]["icv"]["copyright_holder"] != "Generalitat":
        raise SystemExit("Incorrect ICV copyright holder")
    esfire30 = runtime["sources"]["esfire30"]
    if not esfire30["publishable"] or esfire30.get("license_id") != "CC-BY-4.0" or "10.5281/zenodo.18449006" not in esfire30["attribution"]:
        raise SystemExit("Incomplete ESFire30 publication metadata")
    if not runtime["publication_guard"]["all_included_sources_publishable"]:
        raise SystemExit("Publication guard is false")
    serialized = runtime_path.read_text(encoding="utf-8").lower()
    if "sigif" in serialized or "candidate" in serialized:
        raise SystemExit("Forbidden source reference in runtime manifest")

    assets = [runtime["egif"]["asset"]] + list(runtime["esfire30"]["assets"]) + list(runtime["icv"]["geometry_assets"]) + list(runtime["icv"]["attributes"].values()) + list(runtime["recent"]["assets"])
    if len(assets) != 44 or len(runtime["esfire30"]["assets"]) != 3 or len(runtime["icv"]["geometry_assets"]) != 36 or len(runtime["recent"]["assets"]) != 2:
        raise SystemExit("Unexpected public asset composition")
    expected_data = {"data/web/gva/manifest.json"}
    for asset in assets:
        expected_data.add(asset["url"])
        path = args.site / asset["url"]
        if not path.is_file() or path.stat().st_size != asset["bytes"] or sha256(path) != asset["sha256"]:
            raise SystemExit("Public asset integrity mismatch: {}".format(asset["url"]))
    actual_data = {path.relative_to(args.site).as_posix() for path in (args.site / "data").rglob("*") if path.is_file()}
    if actual_data != expected_data:
        raise SystemExit("Unexpected public data file set")
    index = (args.site / "index.html").read_text(encoding="utf-8")
    if EXPECTED_CLOUDFLARE_BEACON not in index or EXPECTED_CLOUDFLARE_TOKEN not in index:
        raise SystemExit("Missing or incorrect Cloudflare Web Analytics beacon")
    for link in ("LICENSE_DATA.md", "THIRD_PARTY_LICENSES.md"):
        if link not in index or not (args.site / link).is_file():
            raise SystemExit("Missing visible license link: {}".format(link))
    total = sum((args.site / item).stat().st_size for item in expected_data)
    print(json.dumps({"status": "passed", "sources": ["egif", "esfire30", "icv", "effis"], "data_assets": len(assets), "data_files_with_manifest": len(expected_data), "data_bytes_with_manifest": total}, indent=2))


if __name__ == "__main__":
    main()
