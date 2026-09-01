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
FORBIDDEN_RUNTIME_STRINGS = ("/home/dani/", "file://", "127.0.0.1", "localhost", "r2.dev", "atlas-incendios-es4c3d4-pages-staging", "national-prototype-staging", "release-assets.githubusercontent.com", "/releases/download")


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
    total_bytes = sum(row["bytes"] for row in rows) + (output / "asset-manifest.json").stat().st_size if (output / "asset-manifest.json").exists() else sum(row["bytes"] for row in rows)
    fingerprint_input = "".join(f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows).encode("utf-8")
    duplicates = defaultdict(list)
    for row in rows:
        if row["bytes"] >= 1024 * 1024:
            duplicates[row["sha256"]].append(row["path"])
    return {
        "schema_version": "es4d4a-national-pages-artifact-v1",
        "artifact": "national-pages-staging",
        "entrypoint": "index.html",
        "file_count_excluding_manifest": len(rows),
        "total_bytes_excluding_manifest": sum(row["bytes"] for row in rows),
        "files": rows,
        "families": {key: value for key, value in sorted(families.items())},
        "largest_files": sorted(rows, key=lambda row: (-row["bytes"], row["path"]))[:20],
        "significant_duplicate_assets": [paths for paths in duplicates.values() if len(paths) > 1],
        "pmtiles": {"runtime_path": PMTILES_DESTINATION.as_posix(), "bytes": frontend.PMTILES_BYTES, "sha256": frontend.PMTILES_SHA256},
        "inputs": inputs,
        "fingerprint": {"algorithm": "sha256(sorted path + TAB + bytes + TAB + sha256 + LF; excludes asset-manifest.json)", "sha256": hashlib.sha256(fingerprint_input).hexdigest()},
        "external_runtime_dependencies": [],
        "staging_repo_candidate": "InThuRain/atlas-incendios-es4c3d4-pages-staging",
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
            "egif": copy_egif(staging, files),
            "territories": copy_territories(staging, files),
            "municipality_indexes": copy_municipality_indexes(staging, files),
            "gva_sources": copy_gva_sources(staging, files),
        }
        # Registra todos los ficheros ya presentes y no añade datos de desarrollo.
        add_frontend_records(staging, files)
        manifest = inventory(staging, files, inputs)
        manifest_path = staging / "asset-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        final_files = [path for path in staging.rglob("*") if path.is_file()]
        manifest["file_count"] = len(final_files)
        manifest["total_bytes"] = sum(path.stat().st_size for path in final_files)
        manifest["total_mib"] = round(manifest["total_bytes"] / (1024 * 1024), 3)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(staging), str(output))
    return {"valid": True, "output": label(output), "file_count": manifest["file_count"], "total_bytes": manifest["total_bytes"], "fingerprint": manifest["fingerprint"]["sha256"]}


def label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check(output: Path) -> dict:
    manifest_path = output / "asset-manifest.json"
    if not manifest_path.is_file():
        return {"valid": False, "failures": ["No existe asset-manifest.json"]}
    manifest = read_json(manifest_path)
    failures = []
    expected_paths = set()
    for row in manifest.get("files", []):
        path = output / row.get("path", "")
        expected_paths.add(row.get("path"))
        if not path.is_file() or path.stat().st_size != row.get("bytes") or sha256(path) != row.get("sha256"):
            failures.append(f"integrity:{row.get('path')}")
    actual_paths = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file() and path.name != "asset-manifest.json"}
    if actual_paths != expected_paths:
        failures.append("inventory: files no reconciliados")
    pmtiles = output / manifest.get("pmtiles", {}).get("runtime_path", "")
    if not pmtiles.is_file() or pmtiles.stat().st_size != frontend.PMTILES_BYTES or sha256(pmtiles) != frontend.PMTILES_SHA256:
        failures.append("pmtiles: bytes/SHA")
    for path in output.rglob("*"):
        relative = path.relative_to(output).as_posix() if path.is_file() else ""
        if not path.is_file() or relative == "asset-manifest.json" or relative.startswith("vendor/") or path.suffix.lower() not in {".html", ".js", ".mjs", ".json", ".css"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for forbidden in FORBIDDEN_RUNTIME_STRINGS:
            if forbidden in text:
                failures.append(f"forbidden:{path.relative_to(output)}:{forbidden}")
    if any("/.spool/" in path or path.startswith(".spool/") for path in actual_paths):
        failures.append("egif: spool incluido")
    return {"valid": not failures, "failures": sorted(set(failures)), "output": label(output), "file_count": manifest.get("file_count"), "total_bytes": manifest.get("total_bytes"), "fingerprint": manifest.get("fingerprint", {}).get("sha256")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = check(args.output) if args.check else build(args.output)
    except MissingStagingInput as error:
        result = {"valid": False, "status": "BLOCKED_MISSING_INPUT", "failures": [str(error)]}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
