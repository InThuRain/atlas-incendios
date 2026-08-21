#!/usr/bin/env python3
"""Assemble the self-contained GitHub Pages directory from a public profile."""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_FILES = ("index.html", "LICENSE_DATA.md", "THIRD_PARTY_LICENSES.md")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-dir", type=Path, default=ROOT / "data/web/gva")
    parser.add_argument("--output", type=Path, default=ROOT / "data/derived/gva/publication/site")
    return parser.parse_args()


def main():
    args = parse_args()
    runtime_path = args.asset_dir / "manifest.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    serialized = runtime_path.read_text(encoding="utf-8").lower()
    if runtime["profile"] != "public" or set(runtime["sources"]) != {"icv", "effis"}:
        raise SystemExit("Runtime manifest is not the public ICV + EFFIS profile")
    if not runtime["publication_guard"]["all_included_sources_publishable"]:
        raise SystemExit("Public publication guard failed")
    if "sigif" in serialized or "candidate" in serialized:
        raise SystemExit("Forbidden source or candidate reference in public runtime manifest")

    assets = list(runtime["icv"]["geometry_assets"]) + list(runtime["icv"]["attributes"].values()) + list(runtime["recent"]["assets"])
    if len(assets) != 40:
        raise SystemExit("Expected exactly 40 public data assets")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(args.output.parent), prefix="public-site-") as directory:
        staging = Path(directory) / "site"
        staging.mkdir()
        for relative in SITE_FILES:
            shutil.copy2(ROOT / relative, staging / relative)
        shutil.copytree(ROOT / "css", staging / "css")
        shutil.copytree(ROOT / "js", staging / "js")
        (staging / ".nojekyll").write_text("", encoding="utf-8")

        target_manifest = staging / "data/web/gva/manifest.json"
        target_manifest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runtime_path, target_manifest)
        for asset in assets:
            relative = Path(asset["url"])
            source = ROOT / relative
            if not source.is_file() or source.stat().st_size != asset["bytes"] or sha256(source) != asset["sha256"]:
                raise SystemExit("Public asset mismatch: {}".format(relative))
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        files = []
        for path in sorted(item for item in staging.rglob("*") if item.is_file()):
            relative = path.relative_to(staging).as_posix()
            if any(part in {"raw", "processed", "benchmarks", "sigif"} for part in Path(relative).parts) or "candidate" in relative.lower():
                raise SystemExit("Forbidden path in public site: {}".format(relative))
            files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
        site_manifest = {
            "schema_version": 1,
            "profile": "public",
            "data_asset_count": len(assets),
            "file_count_before_manifest": len(files),
            "bytes_before_manifest": sum(item["bytes"] for item in files),
            "files": files,
        }
        (staging / "site-assets.json").write_text(json.dumps(site_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        previous = args.output.with_name(args.output.name + ".previous")
        if previous.exists():
            shutil.rmtree(previous)
        if args.output.exists():
            os.replace(args.output, previous)
        os.replace(staging, args.output)
        if previous.exists():
            shutil.rmtree(previous)
    print(json.dumps({"site": str(args.output), "data_assets": len(assets), "files": len(files) + 1}, indent=2))


if __name__ == "__main__":
    main()
