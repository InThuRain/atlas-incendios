#!/usr/bin/env python3
"""Create the public-safe ICV + EFFIS release bundle used by Pages CI."""

import argparse
import gzip
import hashlib
import json
import os
import tarfile
import tempfile
from pathlib import Path

from build_frontend_profile import coverage_for_sources


ROOT = Path(__file__).resolve().parents[1]
RELEASE_TAG = "public-data-v1"
ASSET_NAME = "atlas-public-data-v1.tar.gz"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def deterministic_archive(output, files):
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".part")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path, relative in sorted(files, key=lambda item: item[1].as_posix()):
                    info = archive.gettarinfo(str(path), arcname=relative.as_posix())
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with path.open("rb") as handle:
                        archive.addfile(info, handle)
    os.replace(temporary, output)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-dir", type=Path, default=ROOT / "data/web/gva")
    parser.add_argument("--icv-manifest", type=Path, default=ROOT / "config/datasets-gva.json")
    parser.add_argument("--recent-manifest", type=Path, default=ROOT / "data/web/gva/recent/assets-manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/derived/gva/publication" / ASSET_NAME)
    parser.add_argument("--bundle-manifest", type=Path, default=ROOT / "config/public-data-bundle.json")
    return parser.parse_args()


def main():
    args = parse_args()
    icv = load(args.icv_manifest)
    recent = load(args.recent_manifest)
    if icv["publication"]["status"] != "ready":
        raise SystemExit("ICV publication metadata is not ready")

    icv_assets = list(icv["geometry_assets"]) + list(icv["attributes"].values())
    effis_assets = [item for item in recent["assets"] if item["kind"] == "effis_perimeters"]
    if len(icv_assets) != 38 or len(effis_assets) != 2:
        raise SystemExit("Unexpected public asset count")

    selected = []
    records = []
    for asset in icv_assets + effis_assets:
        relative = Path(asset["url"])
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size != asset["bytes"] or sha256(path) != asset["sha256"]:
            raise SystemExit("Asset integrity mismatch: {}".format(relative))
        selected.append((path, relative))
        records.append({"path": relative.as_posix(), "bytes": asset["bytes"], "sha256": asset["sha256"]})

    public_recent = {
        "schema_version": 1,
        "phase": "public-profile-v1",
        "snapshot_id": recent["snapshot_id"],
        "acquired_at": recent["acquired_at"],
        "coverage": coverage_for_sources(recent["coverage"], ["effis"]),
        "assets": effis_assets,
        "transformations": [
            "EFFIS geometries retained in EPSG:4326 without simplification",
            "browser attributes reduced; source snapshots and original attributes are not distributed",
        ],
    }
    serialized = json.dumps(public_recent, ensure_ascii=False, sort_keys=True).lower()
    if "sigif" in serialized or "candidate" in serialized:
        raise SystemExit("Forbidden recent-source metadata in public bundle")

    with tempfile.TemporaryDirectory(dir=str(args.output.parent if args.output.parent.exists() else ROOT)) as directory:
        temporary_manifest = Path(directory) / "assets-manifest.json"
        atomic_json(temporary_manifest, public_recent)
        relative_manifest = Path("data/web/gva/recent/assets-manifest.json")
        selected.append((temporary_manifest, relative_manifest))
        records.append({"path": relative_manifest.as_posix(), "bytes": temporary_manifest.stat().st_size, "sha256": sha256(temporary_manifest)})
        deterministic_archive(args.output, selected)

    manifest = {
        "schema_version": 1,
        "repository": "InThuRain/atlas-incendios",
        "release": {"tag": RELEASE_TAG, "asset_name": ASSET_NAME},
        "archive": {"bytes": args.output.stat().st_size, "sha256": sha256(args.output)},
        "contents": {
            "file_count": len(records),
            "uncompressed_bytes": sum(item["bytes"] for item in records),
            "icv_data_assets": len(icv_assets),
            "effis_data_assets": len(effis_assets),
            "files": sorted(records, key=lambda item: item["path"]),
        },
        "excluded": ["SIGIF", "SIGIF-EFFIS link candidates", "raw", "processed", "benchmarks"],
    }
    atomic_json(args.bundle_manifest, manifest)
    print(json.dumps({"bundle": str(args.output), **manifest["archive"], **manifest["contents"]}, indent=2))


if __name__ == "__main__":
    main()
