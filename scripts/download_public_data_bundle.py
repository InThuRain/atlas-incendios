#!/usr/bin/env python3
"""Download, verify and safely extract the immutable public data bundle."""

import argparse
import hashlib
import json
import os
import tarfile
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "config/public-data-bundle.json")
    parser.add_argument("--destination", type=Path, default=ROOT)
    parser.add_argument("--url")
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    release = manifest["release"]
    url = args.url or "https://github.com/{}/releases/download/{}/{}".format(
        manifest["repository"], release["tag"], release["asset_name"]
    )
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / release["asset_name"]
        request = urllib.request.Request(url, headers={"User-Agent": "atlas-incendios-pages-build/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        expected = manifest["archive"]
        if archive.stat().st_size != expected["bytes"] or sha256(archive) != expected["sha256"]:
            raise SystemExit("Public data bundle checksum mismatch")
        destination = args.destination.resolve()
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            actual_names = {member.name for member in members if member.isfile()}
            expected_names = {item["path"] for item in manifest["contents"]["files"]}
            if actual_names != expected_names:
                raise SystemExit("Public bundle file set mismatch")
            for member in members:
                target = (destination / member.name).resolve()
                if destination not in target.parents:
                    raise SystemExit("Unsafe path in public bundle")
            bundle.extractall(destination)
    for item in manifest["contents"]["files"]:
        path = args.destination / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise SystemExit("Extracted public asset mismatch: {}".format(item["path"]))
    print("Verified and extracted {} public bundle files".format(manifest["contents"]["file_count"]))


if __name__ == "__main__":
    main()
