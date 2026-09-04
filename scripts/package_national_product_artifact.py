#!/usr/bin/env python3
"""Empaqueta el site E3D1/E3D2 exacto sin reconstruirlo.

El archivo resultante sólo transporta el árbol local hacia el runner E4A.  La
identidad contractual sigue siendo la del sitio extraído, comprobada tanto
antes de empaquetar como de nuevo en el runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

import check_national_product_artifact as checker


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "build/national-product-staging"
DEFAULT_OUTPUT = ROOT / "build/es4e4a/national-product-staging.tar"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package(artifact: Path, output: Path) -> dict:
    identity = checker.check(artifact)
    if not identity.get("valid"):
        raise RuntimeError("FAIL_ARTIFACT_IDENTITY: " + ", ".join(identity.get("failures", [])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for path in sorted(item for item in artifact.rglob("*") if item.is_file() and not item.is_symlink()):
            info = archive.gettarinfo(str(path), arcname=path.relative_to(artifact).as_posix())
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with path.open("rb") as source:
                archive.addfile(info, source)
    return {
        "valid": True,
        "artifact": str(artifact),
        "archive": str(output),
        "archive_bytes": output.stat().st_size,
        "archive_sha256": sha256(output),
        "site_identity": {key: identity[key] for key in (
            "site_file_count", "site_total_bytes", "payload_file_count",
            "payload_total_bytes", "payload_fingerprint", "asset_manifest_sha256",
            "site_identity_sha256",
        )},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = package(args.artifact.resolve(), args.output.resolve())
    except RuntimeError as error:
        result = {"valid": False, "failure": str(error)}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
