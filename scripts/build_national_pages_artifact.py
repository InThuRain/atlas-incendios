#!/usr/bin/env python3
"""Ensambla el artifact estático nacional completo para staging Pages.

No genera datos. Copia exclusivamente outputs aceptados del repositorio a un
árbol auto-contenido y registra su integridad. Las rutas del runtime son
relativas al directorio raíz del artifact, por lo que el mismo resultado sirve
bajo cualquier base path de GitHub Pages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

import build_national_frontend as frontend


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build/national-pages-staging"
PMTILES_SOURCE = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles"
PMTILES_DESTINATION = Path("data/esfire30/v1") / frontend.PMTILES_SHA256 / PMTILES_SOURCE.name
EGIF_SOURCE = ROOT / "data/web/spain/egif/2026-08-27"
EGIF_DESTINATION = Path("data/egif/v1/2026-08-27")
GVA_SOURCE = ROOT / "data/web/gva"
TERRITORY_SOURCE = ROOT / "data/territories/spain/territories-2026-01-01.json"
CCAA_SOURCE = ROOT / "data/derived/spain/es4c2a/ccaa.geojson"
PROVINCES_SOURCE = ROOT / "data/derived/spain/es4c2a/provinces.geojson"
MUNICIPALITY_CATALOG_SOURCE = ROOT / "data/territories/spain/municipality_catalog_2026-08-29.json"
MUNICIPALITY_SHARDS_SOURCE = ROOT / "data/derived/spain/es4c2a3/municipalities"
MUNICIPALITY_INDEX_SOURCE = ROOT / "data/derived/spain/es4c2b/runtime/municipality-index"
HIGHLIGHTS_SOURCE = ROOT / "data/derived/spain/national-highlights-v1"
SUMMARY_SOURCE = ROOT / "data/derived/spain/national-ux-summary-v1"
BASEMAP_MANIFEST_SOURCE = frontend.BASEMAP_MANIFEST_PATH
BASEMAP_SOURCE = ROOT / frontend.BASEMAP_MANIFEST["pmtiles"]["source_path"]
BASEMAP_DESTINATION = Path(frontend.BASEMAP_MANIFEST["pmtiles"]["runtime_path"])
BASEMAP_GLYPH_SOURCE = ROOT / frontend.BASEMAP_MANIFEST["glyphs"]["source_path"]
BASEMAP_GLYPH_DESTINATION = Path(frontend.BASEMAP_MANIFEST["glyphs"]["runtime_template"].replace("{fontstack}", frontend.BASEMAP_MANIFEST["glyphs"]["fontstack"]).replace("{range}", frontend.BASEMAP_MANIFEST["glyphs"]["range"]))
BASEMAP_LICENSE_SOURCE = ROOT / frontend.BASEMAP_MANIFEST["glyphs"]["license_source_path"]
BASEMAP_LICENSE_DESTINATION = Path(frontend.BASEMAP_MANIFEST["glyphs"]["license_runtime_path"])
BASEMAP_MANIFEST_DESTINATION = BASEMAP_DESTINATION.parent / "manifest.json"
FORBIDDEN_RUNTIME_STRINGS = ("/home/dani/", "file://", "127.0.0.1", "localhost", "r2.dev", "atlas-incendios-es4c3d4-pages-staging", "national-prototype-staging", "release-assets.githubusercontent.com", "/releases/download")
PAYLOAD_MANIFEST_PATH = Path("asset-manifest.json")
SITE_IDENTITY_PATH = Path("site-identity.json")
SITE_METADATA_PATHS = {PAYLOAD_MANIFEST_PATH.as_posix(), SITE_IDENTITY_PATH.as_posix()}


class MissingStagingInput(FileNotFoundError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise MissingStagingInput(f"MISSING_STAGING_INPUT: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def require_file(path: Path) -> Path:
    if not path.is_file():
        raise MissingStagingInput(f"MISSING_STAGING_INPUT: {path.relative_to(ROOT)}")
    return path


def copy_file(source: Path, output: Path, destination: Path, family: str, logical_id: str, source_label: str, files: list[dict]) -> None:
    require_file(source)
    target = output / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    files.append({"path": destination.as_posix(), "family": family, "logical_id": logical_id, "source": source_label})


def copy_egif(output: Path, files: list[dict]) -> dict:
    manifest_path = require_file(EGIF_SOURCE / "manifest.json")
    manifest = read_json(manifest_path)
    assets = manifest.get("assets")
    if not isinstance(assets, list) or len(assets) != 88:
        raise MissingStagingInput("MISSING_STAGING_INPUT: EGIF manifest no contiene 88 assets runtime")
    copy_file(manifest_path, output, EGIF_DESTINATION / "manifest.json", "egif", "egif:manifest", "EGIF national web v1", files)
    copied = set()
    for asset in assets:
        for variant in ("initial", "detail"):
            path = asset.get(variant, {}).get("path")
            if not isinstance(path, str) or path in copied:
                raise MissingStagingInput(f"MISSING_STAGING_INPUT: path {variant} EGIF inválido")
            copied.add(path)
            copy_file(EGIF_SOURCE / path, output, EGIF_DESTINATION / path, "egif", asset.get("asset_id", "egif:unknown"), "EGIF national web v1", files)
    return {"assets": len(assets), "runtime_files": len(copied), "records": manifest.get("totals", {}).get("record_count")}


def copy_gva_sources(output: Path, files: list[dict]) -> dict:
    manifest_path = require_file(GVA_SOURCE / "manifest.json")
    manifest = read_json(manifest_path)
    paths = {Path("manifest.json"): ("runtime_metadata", "gva:manifest")}
    icv = manifest.get("icv", {})
    for key, descriptor in icv.get("attributes", {}).items():
        if isinstance(descriptor, dict) and isinstance(descriptor.get("url"), str):
            paths[Path(descriptor["url"]).relative_to("data/web/gva")] = ("icv", f"icv:{key}")
    for asset in icv.get("geometry_assets", []):
        url = asset.get("url")
        if isinstance(url, str):
            paths[Path(url).relative_to("data/web/gva")] = ("icv", f"icv:{asset.get('province')}:{asset.get('temporal_block')}:{asset.get('level')}")
    for asset in manifest.get("recent", {}).get("assets", []):
        if asset.get("kind") == "effis_perimeters" and isinstance(asset.get("url"), str):
            paths[Path(asset["url"]).relative_to("data/web/gva")] = ("effis", f"effis:{asset.get('year')}")
    for relative in (Path("provenance.json"), Path("recent/assets-manifest.json")):
        paths[relative] = ("runtime_metadata", f"gva:{relative.stem}")
    for relative, (family, logical_id) in sorted(paths.items()):
        copy_file(GVA_SOURCE / relative, output, Path("data/web/gva") / relative, family, logical_id, "GVA public web snapshot", files)
    effis_assets = [asset for asset in manifest.get("recent", {}).get("assets", []) if asset.get("kind") == "effis_perimeters"]
    counts = {str(asset.get("year")): asset.get("feature_count") for asset in effis_assets}
    if counts != {"2025": 9, "2026": 16}:
        raise MissingStagingInput("MISSING_STAGING_INPUT: snapshot EFFIS no coincide con 2025=9, 2026=16")
    return {"icv_geometry_assets": len(icv.get("geometry_assets", [])), "icv_records": 13738, "effis": counts, "snapshot": "20260819T174426Z"}


def copy_territories(output: Path, files: list[dict]) -> dict:
    copy_file(CCAA_SOURCE, output, Path("data/territories/spain/v1/ccaa.geojson"), "territories", "territories:ccaa", "BDLJE current 2026-08", files)
    copy_file(PROVINCES_SOURCE, output, Path("data/territories/spain/v1/provinces.geojson"), "territories", "territories:provinces", "BDLJE current 2026-08", files)
    copy_file(TERRITORY_SOURCE, output, Path("data/territories/spain/territories-2026-01-01.json"), "territories", "territories:catalog", "ES-2 territory snapshot", files)
    catalog = read_json(MUNICIPALITY_CATALOG_SOURCE)
    municipalities = catalog.get("municipalities", [])
    if len(municipalities) != 8132:
        raise MissingStagingInput("MISSING_STAGING_INPUT: catálogo municipal no contiene 8132 municipios")
    copy_file(MUNICIPALITY_CATALOG_SOURCE, output, Path("data/territories/spain/v1/municipality-catalog.json"), "territories", "territories:municipality-catalog", "BDLJE current 2026-08", files)
    shard_ids = sorted({row.get("asset_id") for row in municipalities})
    if len(shard_ids) != 52:
        raise MissingStagingInput("MISSING_STAGING_INPUT: catálogo municipal no reconcilia 52 shards")
    for asset_id in shard_ids:
        filename = asset_id[len("municipalities:"):].replace(":", "-") + ".geojson"
        copy_file(MUNICIPALITY_SHARDS_SOURCE / filename, output, Path("data/territories/spain/v1/municipalities") / filename, "municipality_geometry", asset_id, "BDLJE current 2026-08", files)
    return {"municipalities": len(municipalities), "shards": len(shard_ids)}


def copy_municipality_indexes(output: Path, files: list[dict]) -> dict:
    source_manifest_path = require_file(MUNICIPALITY_INDEX_SOURCE / "manifest.json")
    source_manifest = read_json(source_manifest_path)
    if source_manifest.get("schema_version") != "es4c2b3b1-municipality-runtime-index-v1":
        raise MissingStagingInput("MISSING_STAGING_INPUT: schema de índice municipal inesperado")
    destination_root = Path("data/esfire30/v1/municipality-index")
    staged = json.loads(json.dumps(source_manifest))
    by_parent = staged.get("by_parent", [])
    if len(by_parent) != 47:
        raise MissingStagingInput("MISSING_STAGING_INPUT: índice municipal no contiene 47 shards parent")
    for row in by_parent:
        source_relative = Path(row["path"])
        destination = destination_root / "by-parent" / source_relative.name
        copy_file(ROOT / source_relative, output, destination, "municipality_indexes", f"esfire30:municipality:{row['parent_id']}", "ESFire30 municipality inverse index v1", files)
        row["path"] = destination.as_posix()
    national = staged.get("national", {})
    source_relative = Path(national.get("path", ""))
    destination = destination_root / source_relative.name
    copy_file(ROOT / source_relative, output, destination, "municipality_indexes", "esfire30:municipality:national", "ESFire30 municipality inverse index v1", files)
    national["path"] = destination.as_posix()
    target = output / destination_root / "manifest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(staged, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    files.append({"path": (destination_root / "manifest.json").as_posix(), "family": "municipality_indexes", "logical_id": "esfire30:municipality-index:manifest", "source": "ESFire30 municipality inverse index v1 (paths relocated)"})
    return {"parent_shards": len(by_parent), "national_included": True, "municipalities_with_geometry_ids": source_manifest.get("reconciliation", {}).get("municipalities_with_geometry_ids")}


def copy_highlights(output: Path, files: list[dict]) -> dict:
    manifest = read_json(HIGHLIGHTS_SOURCE / "manifest.json")
    if manifest.get("schema_version") != "national-highlights-v1" or len(manifest.get("assets", [])) != 1:
        raise MissingStagingInput("MISSING_STAGING_INPUT: manifest de destacados nacionales inválido")
    destination = Path("data/highlights/national-highlights-v1")
    copy_file(HIGHLIGHTS_SOURCE / "manifest.json", output, destination / "manifest.json", "highlights", "highlights:manifest", "National highlights v1", files)
    descriptor = manifest["assets"][0]
    copy_file(HIGHLIGHTS_SOURCE / descriptor["path"], output, destination / descriptor["path"], "highlights", "highlights:egif", "National highlights v1", files)
    return {"assets": 1, "source": "egif", "bytes": descriptor.get("bytes")}


def copy_summary(output: Path, files: list[dict]) -> dict:
    manifest = read_json(SUMMARY_SOURCE / "manifest.json")
    if manifest.get("schema_version") != "national-ux-summary-v1" or manifest.get("payload_file_count") != 122:
        raise MissingStagingInput("MISSING_STAGING_INPUT: manifest de resumen nacional inválido")
    destination = Path("data/summary/national-ux-summary-v1")
    source_files = sorted(path for path in SUMMARY_SOURCE.rglob("*.json") if path.is_file())
    for source in source_files:
        relative = source.relative_to(SUMMARY_SOURCE)
        copy_file(source, output, destination / relative, "summary", f"summary:{relative.as_posix()}", "National UX summary v1", files)
    return {"payload_files": manifest["payload_file_count"], "runtime_files": len(source_files), "payload_bytes": manifest.get("payload_bytes")}


def copy_basemap(output: Path, files: list[dict]) -> dict:
    contract = frontend.BASEMAP_MANIFEST
    checks = (
        (BASEMAP_SOURCE, contract["pmtiles"]["bytes"], contract["pmtiles"]["sha256"], "PMTiles"),
        (BASEMAP_GLYPH_SOURCE, contract["glyphs"]["bytes"], contract["glyphs"]["sha256"], "glyph"),
        (BASEMAP_LICENSE_SOURCE, contract["glyphs"]["license_bytes"], contract["glyphs"]["license_sha256"], "OFL"),
    )
    for source, expected_bytes, expected_sha, label_ in checks:
        require_file(source)
        if source.stat().st_size != expected_bytes or sha256(source) != expected_sha:
            raise MissingStagingInput(f"MISSING_STAGING_INPUT: basemap {label_} no coincide con bytes/SHA contractual")
    copy_file(BASEMAP_SOURCE, output, BASEMAP_DESTINATION, "basemap", "basemap:protomaps-20260902-z12", "Protomaps 20260902 z12 regional extract", files)
    copy_file(BASEMAP_GLYPH_SOURCE, output, BASEMAP_GLYPH_DESTINATION, "basemap", "basemap:glyph:Noto-Sans-Regular:0-255", "Noto Sans Regular glyph", files)
    copy_file(BASEMAP_LICENSE_SOURCE, output, BASEMAP_LICENSE_DESTINATION, "basemap", "basemap:glyph-license:OFL", "Noto SIL OFL", files)
    copy_file(BASEMAP_MANIFEST_SOURCE, output, BASEMAP_MANIFEST_DESTINATION, "basemap", "basemap:manifest", "National basemap manifest v1", files)
    return {
        "version": contract["basemap_version"],
        "pmtiles": {"runtime_path": BASEMAP_DESTINATION.as_posix(), "bytes": contract["pmtiles"]["bytes"], "sha256": contract["pmtiles"]["sha256"]},
        "glyph": {"runtime_path": BASEMAP_GLYPH_DESTINATION.as_posix(), "bytes": contract["glyphs"]["bytes"], "sha256": contract["glyphs"]["sha256"]},
        "runtime_external_domains": [],
    }


def add_frontend_records(output: Path, files: list[dict]) -> None:
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.relative_to(output).as_posix() != "asset-manifest.json":
            relative = path.relative_to(output).as_posix()
            if not any(row["path"] == relative for row in files):
                files.append({"path": relative, "family": "frontend" if not relative.startswith("vendor/") else "other", "logical_id": f"frontend:{relative}", "source": "src/national + shared runtime"})


def inventory(output: Path, records: list[dict], inputs: dict) -> dict:
    rows = []
    for record in sorted(records, key=lambda item: item["path"]):
        path = output / record["path"]
        if not path.is_file():
            raise RuntimeError(f"Artifact incompleto: {record['path']}")
        rows.append({
            **record,
            # `path` se conserva para el verificador compacto existente;
            # los nombres explícitos hacen que el manifest sea también el
            # contrato de despliegue/CI de D4B.
            "runtime_path": record["path"],
            "required": True,
            "source_version": record["source"],
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    families = defaultdict(lambda: {"files": 0, "raw_bytes": 0})
    for row in rows:
        family = families[row["family"]]
        family["files"] += 1; family["raw_bytes"] += row["bytes"]
    payload_total_bytes = sum(row["bytes"] for row in rows)
    fingerprint_input = "".join(f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows).encode("utf-8")
    duplicates = defaultdict(list)
    for row in rows:
        if row["bytes"] >= 1024 * 1024:
            duplicates[row["sha256"]].append(row["path"])
    return {
        "schema_version": "es4d4a-national-pages-artifact-v2",
        "artifact": "national-pages-staging",
        "entrypoint": "index.html",
        "identity_contract": {
            "payload_scope": "all deployable files except asset-manifest.json and site-identity.json",
            "site_scope": "all physical deployable files, including both identity metadata files",
            "site_identity_path": SITE_IDENTITY_PATH.as_posix(),
            "site_metadata_paths": sorted(SITE_METADATA_PATHS),
        },
        "payload_file_count": len(rows),
        "payload_total_bytes": payload_total_bytes,
        "files": rows,
        "families": {key: value for key, value in sorted(families.items())},
        "largest_files": sorted(rows, key=lambda row: (-row["bytes"], row["path"]))[:20],
        "significant_duplicate_assets": [paths for paths in duplicates.values() if len(paths) > 1],
        "pmtiles": {"runtime_path": PMTILES_DESTINATION.as_posix(), "bytes": frontend.PMTILES_BYTES, "sha256": frontend.PMTILES_SHA256},
        "basemap": inputs.get("basemap"),
        "inputs": inputs,
        "payload_fingerprint": {
            "algorithm": "sha256(sorted path + TAB + bytes + TAB + sha256 + LF; excludes identity metadata)",
            "sha256": hashlib.sha256(fingerprint_input).hexdigest(),
        },
        "external_runtime_dependencies": [],
        "staging_repo_candidate": "InThuRain/atlas-incendios-es4c3d4-pages-staging",
    }


def canonical_json(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_identity_metadata(staging: Path, manifest: dict) -> dict:
    """Write non-circular payload and whole-site identity metadata.

    The payload manifest deliberately does not list either identity metadata
    file.  The site identity uses a fixed-width decimal total, so its own
    bytes are included without an iterative/self-hashing fixed point.
    """
    manifest_path = staging / PAYLOAD_MANIFEST_PATH
    manifest_path.write_bytes(canonical_json(manifest))
    manifest_sha256 = sha256(manifest_path)
    site_file_count = manifest["payload_file_count"] + len(SITE_METADATA_PATHS)
    identity = {
        "schema_version": "es4d4a-site-identity-v1",
        "identity_scope": "all physical deployable files, including identity metadata",
        "site_file_count": site_file_count,
        # Keeping this fixed-width makes the final serialized size independent
        # of the value it carries; it is a decimal byte count, not an ID.
        "site_total_bytes": "00000000000000000000",
        "payload_file_count": manifest["payload_file_count"],
        "payload_total_bytes": manifest["payload_total_bytes"],
        "payload_fingerprint": manifest["payload_fingerprint"],
        "asset_manifest": {"path": PAYLOAD_MANIFEST_PATH.as_posix(), "sha256": manifest_sha256},
        "pmtiles": manifest["pmtiles"],
    }
    identity_path = staging / SITE_IDENTITY_PATH
    provisional = canonical_json(identity)
    site_total_bytes = manifest["payload_total_bytes"] + manifest_path.stat().st_size + len(provisional)
    identity["site_total_bytes"] = f"{site_total_bytes:020d}"
    final = canonical_json(identity)
    if len(final) != len(provisional):
        raise RuntimeError("site-identity serialization changed fixed-width size")
    identity_path.write_bytes(final)
    return {
        "site_file_count": site_file_count,
        "site_total_bytes": site_total_bytes,
        "payload_file_count": manifest["payload_file_count"],
        "payload_total_bytes": manifest["payload_total_bytes"],
        "payload_fingerprint": manifest["payload_fingerprint"]["sha256"],
        "manifest_sha256": manifest_sha256,
        "site_identity_sha256": sha256(identity_path),
    }


def build(output: Path) -> dict:
    require_file(PMTILES_SOURCE)
    if PMTILES_SOURCE.stat().st_size != frontend.PMTILES_BYTES or sha256(PMTILES_SOURCE) != frontend.PMTILES_SHA256:
        raise MissingStagingInput("MISSING_STAGING_INPUT: PMTiles nacional no coincide con bytes/SHA contractual")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="national-pages-artifact-", dir=str(output.parent)) as temporary:
        staging = Path(temporary) / "artifact"
        frontend.build(staging)
        (staging / ".nojekyll").write_text("", encoding="utf-8")
        files: list[dict] = []
        add_frontend_records(staging, files)
        copy_file(PMTILES_SOURCE, staging, PMTILES_DESTINATION, "pmtiles", "esfire30:national-fidelity-territories", "ESFire30 v1 territorial PMTiles", files)
        inputs = {
            "pmtiles": {"source": str(PMTILES_SOURCE.relative_to(ROOT)), "bytes": frontend.PMTILES_BYTES, "sha256": frontend.PMTILES_SHA256},
            "basemap": copy_basemap(staging, files),
            "egif": copy_egif(staging, files),
            "territories": copy_territories(staging, files),
            "municipality_indexes": copy_municipality_indexes(staging, files),
            "gva_sources": copy_gva_sources(staging, files),
            "highlights": copy_highlights(staging, files),
            "summary": copy_summary(staging, files),
        }
        # Registra todos los ficheros ya presentes y no añade datos de desarrollo.
        add_frontend_records(staging, files)
        manifest = inventory(staging, files, inputs)
        identity = write_identity_metadata(staging, manifest)
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(staging), str(output))
    return {"valid": True, "output": label(output), **identity}


def label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def verify_identity(output: Path) -> dict:
    manifest_path = output / PAYLOAD_MANIFEST_PATH
    if not manifest_path.is_file():
        return {"valid": False, "failures": ["No existe asset-manifest.json"]}
    manifest = read_json(manifest_path)
    identity_path = output / SITE_IDENTITY_PATH
    if not identity_path.is_file():
        return {"valid": False, "failures": ["No existe site-identity.json"]}
    identity = read_json(identity_path)
    failures = []
    expected_paths = set()
    for row in manifest.get("files", []):
        path = output / row.get("path", "")
        if row.get("path") in expected_paths:
            failures.append(f"manifest: duplicate path:{row.get('path')}")
        expected_paths.add(row.get("path"))
        if not path.is_file() or path.stat().st_size != row.get("bytes") or sha256(path) != row.get("sha256"):
            failures.append(f"integrity:{row.get('path')}")
    actual_paths = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file() and not path.is_symlink()}
    if actual_paths != expected_paths | SITE_METADATA_PATHS:
        failures.append("inventory: files no reconciliados")
    actual_file_count = len(actual_paths)
    actual_total_bytes = sum((output / relative).stat().st_size for relative in actual_paths)
    fingerprint_input = "".join(
        f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in sorted(manifest.get("files", []), key=lambda row: row["path"])
    ).encode("utf-8")
    if identity.get("schema_version") != "es4d4a-site-identity-v1":
        failures.append("identity: schema")
    if identity.get("site_file_count") != actual_file_count:
        failures.append("identity: site_file_count")
    if identity.get("site_total_bytes") != f"{actual_total_bytes:020d}":
        failures.append("identity: site_total_bytes")
    if manifest.get("payload_file_count") != len(expected_paths):
        failures.append("manifest: payload_file_count")
    if manifest.get("payload_total_bytes") != sum(row.get("bytes", 0) for row in manifest.get("files", [])):
        failures.append("manifest: payload_total_bytes")
    if manifest.get("payload_fingerprint", {}).get("sha256") != hashlib.sha256(fingerprint_input).hexdigest():
        failures.append("manifest: payload_fingerprint")
    if identity.get("payload_file_count") != manifest.get("payload_file_count") or identity.get("payload_total_bytes") != manifest.get("payload_total_bytes") or identity.get("payload_fingerprint", {}).get("sha256") != manifest.get("payload_fingerprint", {}).get("sha256"):
        failures.append("identity: payload contract")
    if identity.get("asset_manifest", {}).get("path") != PAYLOAD_MANIFEST_PATH.as_posix() or identity.get("asset_manifest", {}).get("sha256") != sha256(manifest_path):
        failures.append("identity: asset manifest sha256")
    pmtiles = output / manifest.get("pmtiles", {}).get("runtime_path", "")
    if not pmtiles.is_file() or pmtiles.stat().st_size != frontend.PMTILES_BYTES or sha256(pmtiles) != frontend.PMTILES_SHA256:
        failures.append("pmtiles: bytes/SHA")
    basemap_contract = manifest.get("basemap", {}).get("pmtiles", {})
    basemap = output / basemap_contract.get("runtime_path", "")
    if not basemap.is_file() or basemap.stat().st_size != frontend.BASEMAP_BYTES or sha256(basemap) != frontend.BASEMAP_SHA256:
        failures.append("basemap: bytes/SHA")
    for path in output.rglob("*"):
        relative = path.relative_to(output).as_posix() if path.is_file() else ""
        if not path.is_file() or relative in SITE_METADATA_PATHS or relative.startswith("vendor/") or path.suffix.lower() not in {".html", ".js", ".mjs", ".json", ".css"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for forbidden in FORBIDDEN_RUNTIME_STRINGS:
            if forbidden in text:
                failures.append(f"forbidden:{path.relative_to(output)}:{forbidden}")
    if any("/.spool/" in path or path.startswith(".spool/") for path in actual_paths):
        failures.append("egif: spool incluido")
    return {
        "valid": not failures,
        "failures": sorted(set(failures)),
        "output": label(output),
        "site_file_count": actual_file_count,
        "site_total_bytes": actual_total_bytes,
        "payload_file_count": manifest.get("payload_file_count"),
        "payload_total_bytes": manifest.get("payload_total_bytes"),
        "payload_fingerprint": manifest.get("payload_fingerprint", {}).get("sha256"),
        "manifest_sha256": sha256(manifest_path),
        "site_identity_sha256": sha256(identity_path),
    }


def check(output: Path) -> dict:
    return verify_identity(output)


def physical_inventory(output: Path) -> list[dict]:
    rows = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and not path.is_symlink():
            rows.append({
                "relative_path": path.relative_to(output).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return rows


def identity_audit(output: Path, baseline: Path | None = None, repro_artifact: Path | None = None) -> dict:
    """Create the independent physical audit consumed before a D4B upload."""
    checked = verify_identity(output)
    manifest = read_json(output / PAYLOAD_MANIFEST_PATH)
    rows = physical_inventory(output)
    physical_paths = {row["relative_path"] for row in rows}
    payload_paths = {row["path"] for row in manifest.get("files", [])}
    comparison = None
    if baseline:
        baseline_manifest = read_json(baseline / PAYLOAD_MANIFEST_PATH)
        before = {row["path"]: (row["bytes"], row["sha256"]) for row in baseline_manifest.get("files", [])}
        after = {row["path"]: (row["bytes"], row["sha256"]) for row in manifest.get("files", [])}
        baseline_files = physical_inventory(baseline)
        baseline_payload_total = sum(bytes_ for bytes_, _ in before.values())
        baseline_declared_total = baseline_manifest.get("total_bytes")
        baseline_final_manifest_bytes = (baseline / PAYLOAD_MANIFEST_PATH).stat().st_size
        comparison = {
            "baseline_artifact": label(baseline),
            "baseline_payload_file_count": len(before),
            "baseline_payload_total_bytes": baseline_payload_total,
            "changed_payload_assets": sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path)),
            "pmtiles_unchanged": before.get(PMTILES_DESTINATION.as_posix()) == after.get(PMTILES_DESTINATION.as_posix()),
            "original_declared_total_bytes": baseline_declared_total,
            "original_observed_physical_total_bytes": sum(row["size_bytes"] for row in baseline_files),
            "original_delta_bytes": sum(row["size_bytes"] for row in baseline_files) - baseline_declared_total,
            "affected_paths": [PAYLOAD_MANIFEST_PATH.as_posix()],
            "asset_manifest_first_serialization_bytes": baseline_declared_total - baseline_payload_total,
            "asset_manifest_final_serialization_bytes": baseline_final_manifest_bytes,
            "root_cause": "The v1 builder counted asset-manifest.json after its first serialization, then rewrote that same file with final file_count/total_bytes/total_mib fields without recalculating the physical total.",
            "why_payload_fingerprint_matched": "The v1 fingerprint was calculated from the 348 payload rows and deliberately excluded asset-manifest.json, so changing only its final serialization could not change that fingerprint.",
        }
    reproducible = None
    if repro_artifact:
        repro = verify_identity(repro_artifact)
        reproducible_fields = ("site_file_count", "site_total_bytes", "payload_file_count", "payload_total_bytes", "payload_fingerprint", "manifest_sha256", "site_identity_sha256")
        matches = {field: checked.get(field) == repro.get(field) for field in reproducible_fields}
        reproducible = {
            "artifact": label(repro_artifact),
            "identity": repro,
            "matches": matches,
            "status": "PASS" if checked.get("valid") and repro.get("valid") and all(matches.values()) else "FAIL",
        }
    audit_status = "PASS" if checked.get("valid") and (reproducible is None or reproducible["status"] == "PASS") else "FAIL"
    return {
        "phase": "ES-4D4A1",
        "status": audit_status,
        "identity_contract": {
            "before": {
                "manifest_file_count": "ambiguous: final physical file count while manifest self was excluded from files",
                "manifest_total_bytes": "ambiguous: calculated using an earlier asset-manifest serialization",
                "fingerprint": "payload records only; asset-manifest.json excluded",
            },
            "after": {
                "site_file_count": "all physical deployable files, including asset-manifest.json and site-identity.json",
                "site_total_bytes": "exact sum of all physical deployable files",
                "payload_file_count": "files enumerated and hashed in asset-manifest.json; excludes the two identity metadata files",
                "payload_total_bytes": "sum of files enumerated in asset-manifest.json",
                "payload_fingerprint": "sorted payload path + bytes + SHA-256 rows; excludes identity metadata",
            },
        },
        "physical_inventory": rows,
        "physical_file_count": len(rows),
        "physical_total_bytes": sum(row["size_bytes"] for row in rows),
        "manifest_inventory": {
            "payload_file_count": manifest.get("payload_file_count"),
            "payload_total_bytes": manifest.get("payload_total_bytes"),
            "represented_paths": sorted(payload_paths),
            "in_both": sorted(physical_paths & payload_paths),
            "physical_only": sorted(physical_paths - payload_paths),
            "manifest_only": sorted(payload_paths - physical_paths),
            "deliberately_excluded_metadata": sorted(SITE_METADATA_PATHS),
        },
        "site_identity": read_json(output / SITE_IDENTITY_PATH),
        "site_file_count": checked.get("site_file_count"),
        "site_total_bytes": checked.get("site_total_bytes"),
        "payload_file_count": checked.get("payload_file_count"),
        "payload_total_bytes": checked.get("payload_total_bytes"),
        "payload_fingerprint": checked.get("payload_fingerprint"),
        "manifest_sha256": checked.get("manifest_sha256"),
        "independent_checker": checked,
        "local_d4b_gate": {
            "status": "PASS" if checked.get("valid") else "FAIL",
            "checks": [
                "physical paths equal payload paths plus declared identity metadata",
                "physical site file count and bytes equal site-identity.json",
                "every payload size and SHA-256 equals asset-manifest.json",
                "payload fingerprint recomputes",
                "asset-manifest SHA-256 equals site-identity.json",
                "PMTiles bytes and SHA-256 equal the closed contract",
            ],
        },
        "dataset_runtime_asset_comparison": comparison,
        "reproducible": reproducible,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--identity-audit", type=Path, help="Escribe inventario físico y simulación independiente del gate D4B.")
    parser.add_argument("--baseline", type=Path, help="Artifact anterior para comprobar que payload/runtime assets no cambiaron.")
    parser.add_argument("--repro-artifact", type=Path, help="Segundo artifact limpio para registrar reproducibilidad completa.")
    args = parser.parse_args()
    try:
        result = check(args.output) if args.check else build(args.output)
        if result.get("valid") and args.identity_audit:
            audit = identity_audit(args.output, args.baseline, args.repro_artifact)
            args.identity_audit.parent.mkdir(parents=True, exist_ok=True)
            args.identity_audit.write_bytes(canonical_json(audit))
            result["identity_audit"] = label(args.identity_audit)
    except MissingStagingInput as error:
        result = {"valid": False, "status": "BLOCKED_MISSING_INPUT", "failures": [str(error)]}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
