#!/usr/bin/env python3
"""Compose the runtime dataset manifest for a controlled frontend profile."""

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("development", "public"), default="development")
    parser.add_argument("--include-source", action="append", choices=("icv", "sigif", "effis"))
    parser.add_argument("--catalog", type=Path, default=ROOT / "config/sources-gva.json")
    parser.add_argument("--icv-manifest", type=Path, default=ROOT / "config/datasets-gva.json")
    parser.add_argument("--recent-manifest", type=Path, default=ROOT / "data/web/gva/recent/assets-manifest.json")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def coverage_for_sources(items, requested):
    requested = set(requested)
    if {"sigif", "effis"}.issubset(requested):
        return items
    filtered = []
    for item in items:
        row = {key: item[key] for key in ("year", "acquired_at") if key in item}
        if "sigif" in requested:
            row.update(
                (key, value)
                for key, value in item.items()
                if key.startswith("sigif_")
                or key in {
                    "coverage_start_requested",
                    "coverage_end_requested",
                    "coverage_complete",
                    "warnings",
                }
            )
        if "effis" in requested:
            row.update(
                (key, value)
                for key, value in item.items()
                if key.startswith("effis_")
            )
        filtered.append(row)
    return filtered


def main():
    args = parse_args()
    catalog = read_json(args.catalog)
    requested = args.include_source or catalog["profiles"][args.profile]["sources"]
    blocked = [source for source in requested if not catalog["sources"][source]["publishable"]]
    if args.profile == "public" and blocked:
        raise SystemExit("Public profile refused non-publishable source(s): " + ", ".join(blocked))

    icv = read_json(args.icv_manifest) if "icv" in requested else None
    recent = read_json(args.recent_manifest) if set(requested) & {"sigif", "effis"} else None
    active = {source: catalog["sources"][source] for source in requested}
    maximum = max(item["year_max"] for item in active.values())
    minimum = min(item["year_min"] for item in active.values())
    recent_assets = []
    if recent:
        for asset in recent["assets"]:
            if asset["kind"].startswith("sigif") and "sigif" not in requested:
                continue
            if asset["kind"].startswith("effis") and "effis" not in requested:
                continue
            if asset["kind"].startswith("link_candidates") and not {"sigif", "effis"}.issubset(requested):
                continue
            recent_assets.append(asset)
    runtime = {
        "schema_version": 2,
        "profile": args.profile,
        "years": {
            "min": catalog["timeline"]["min_year"] if args.profile == "development" else minimum,
            "max": maximum,
            "default": min(catalog["timeline"]["default_year"], maximum),
        },
        "query": catalog["query"],
        "sources": active,
        "territories": (icv or read_json(args.icv_manifest))["territories"],
        "zoom_levels": (icv or read_json(args.icv_manifest))["zoom_levels"],
        "icv": ({
            "attributes": icv["attributes"],
            "temporal_blocks": icv["temporal_blocks"],
            "geometry_assets": icv["geometry_assets"],
        } if icv else None),
        "recent": ({
            "snapshot_id": recent["snapshot_id"],
            "acquired_at": recent["acquired_at"],
            "coverage": coverage_for_sources(recent["coverage"], requested),
            "assets": recent_assets,
            "candidate_links_are_confirmed": False,
        } if recent else None),
        "publication_guard": {
            "all_included_sources_publishable": not blocked,
            "no_files_are_published_by_this_build": True,
        },
    }
    output = args.output or (ROOT / "data/web/gva/manifest.json" if args.profile == "development" else ROOT / "data/derived/gva/frontend/profiles/public/manifest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".part")
    temporary.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    print(output)


if __name__ == "__main__":
    main()
