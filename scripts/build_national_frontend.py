#!/usr/bin/env python3
"""Compone el artifact estático nacional sin incluir datasets pesados.

El asset PMTiles, EGIF y las geometrías territoriales permanecen fuera del
árbol Git. El artifact solo declara sus rutas lógicas e inmutables para que el
workflow de publicación posterior pueda incorporarlos y verificarlos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/national"
RUNTIME = ROOT / "prototypes/es4c"
NATIONAL_COMPAT = SOURCE / "compat/gva-v1.mjs"
VENDOR = ROOT / "data/derived/spain/es3/tools/browser"
PMTILES_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"
PMTILES_BYTES = 63052056
RUNTIME_FILES = (
    "app.js",
    "egif_initial_loader.mjs",
    "egif_detail_loader.mjs",
    "territory_catalog.mjs",
    "province_catalog.mjs",
    "runtime_state.mjs",
    "state_serialization.mjs",
    "territory_layer.mjs",
    "province_layer.mjs",
    "municipality_loader.mjs",
    "municipality_layer.mjs",
    "municipality_esfire_index.mjs",
    "icv_loader.mjs",
    "effis_loader.mjs",
    "compat_gva_v1.mjs",
)
# PMTiles 4.3.0 conserva una importación ESM relativa a fflate. Se entrega
# junto al módulo PMTiles para que el artifact sea realmente autocontenido.
VENDOR_FILES = (
    "maplibre-gl-5.16.0.js",
    "pmtiles-4.3.0.mjs",
    "node_modules/fflate/index.js",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def production_config() -> dict:
    return {
        # Todas las rutas del artifact son relativas al directorio que contiene
        # index.html. Así el mismo árbol funciona bajo un repo Pages y bajo la
        # raíz de un dominio, sin conocer ninguno de los dos nombres.
        "asset_base_url": "./",
        "runtime_entry": "./runtime/app.js",
        "maplibre_script": "./vendor/maplibre-gl-5.16.0.js",
        "pmtiles_protocol_module": "../vendor/pmtiles-4.3.0.mjs",
        "assets": {
            "esfire30": {"pmtiles": {
                "logical_id": "esfire30-national-fidelity-territories",
                "path": f"data/esfire30/v1/{PMTILES_SHA256}/esfire30-national-fidelity-territories.pmtiles",
                "bytes": PMTILES_BYTES,
                "sha256": PMTILES_SHA256,
                "source": "ESFire30 v1",
                "required": True,
            }},
            "egif": {"manifest": {"logical_id": "egif-national-web-manifest-2026-08-27", "path": "data/egif/v1/2026-08-27/manifest.json", "required": True}},
            "icv": {
                "manifest": {"logical_id": "gva-icv-public-manifest", "path": "data/web/gva/manifest.json", "required": True},
                "asset_base_url": {"path": "./", "required": True},
            },
            "effis": {
                "manifest": {"logical_id": "gva-recent-effis-public-manifest", "path": "data/web/gva/manifest.json", "required": True},
                "asset_base_url": {"path": "./", "required": True},
            },
            "territories": {
                "ccaa": {"path": "data/territories/spain/v1/ccaa.geojson", "required": True},
                "provinces": {"path": "data/territories/spain/v1/provinces.geojson", "required": True},
                "catalog": {"path": "data/territories/spain/territories-2026-01-01.json", "required": True},
            },
            "municipalities": {
                "catalog": {"path": "data/territories/spain/v1/municipality-catalog.json", "required": True},
                "shards_root": {"path": "data/territories/spain/v1/municipalities", "required": True},
            },
            "esfire30_municipality_indexes": {
                "root": {"path": "data/esfire30/v1/municipality-index", "required": True},
                "manifest": {"path": "data/esfire30/v1/municipality-index/manifest.json", "required": True},
            },
        },
    }


def runtime_config_module(config: dict) -> str:
    return "// Generado por scripts/build_national_frontend.py; no editar.\n" + (
        "globalThis.__ATLAS_NATIONAL_RUNTIME_CONFIG__ = "
        + json.dumps(config, ensure_ascii=False, indent=2)
        + ";\n"
    )


def artifact_manifest(output: Path, config: dict) -> dict:
    files = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        files.append({
            "path": path.relative_to(output).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    return {
        "schema_version": 1,
        "artifact": "national-frontend-static",
        "entrypoint": "index.html",
        "runtime": {"shared_origin": "prototypes/es4c", "files": list(RUNTIME_FILES)},
        "large_assets_included": False,
        "logical_asset_config": config,
        "files": files,
    }


def build(output: Path) -> dict:
    required = [SOURCE / "index.html", SOURCE / "bootstrap.js", SOURCE / "styles.css", NATIONAL_COMPAT, *[RUNTIME / name for name in RUNTIME_FILES if name != "compat_gva_v1.mjs"], *[VENDOR / name for name in VENDOR_FILES]]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Faltan inputs del artifact: " + ", ".join(missing))
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="national-frontend-", dir=str(output.parent)) as directory:
        staging = Path(directory) / "national"
        staging.mkdir()
        for name in ("index.html", "bootstrap.js", "styles.css"):
            shutil.copy2(SOURCE / name, staging / name)
        (staging / "runtime-config.js").write_text(runtime_config_module(production_config()), encoding="utf-8")
        shutil.copytree(RUNTIME, staging / "runtime", ignore=shutil.ignore_patterns("*.json", "*.html", "*.css", "run_*.py", "*sample*", "__pycache__"))
        # El código fuente del adapter vive en src/national; el artifact lo
        # copia junto al runtime compartido y ajusta sólo su import relativo.
        shutil.copy2(NATIONAL_COMPAT, staging / "runtime" / "compat_gva_v1.mjs")
        app_path = staging / "runtime" / "app.js"
        app_path.write_text(app_path.read_text(encoding="utf-8").replace(
            'from "../../src/national/compat/gva-v1.mjs"', 'from "./compat_gva_v1.mjs"'
        ), encoding="utf-8")
        # Solo los módulos consumidos por app.js se conservan; evitar que el
        # artifact transporte harnesses o diagnósticos del prototipo.
        for path in (staging / "runtime").iterdir():
            if path.is_file() and path.name not in RUNTIME_FILES:
                path.unlink()
        (staging / "vendor").mkdir()
        for name in VENDOR_FILES:
            target = staging / "vendor" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(VENDOR / name, target)
        config = production_config()
        manifest = artifact_manifest(staging, config)
        (staging / "asset-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(staging), str(output))
    try:
        output_label = str(output.relative_to(ROOT))
    except ValueError:
        output_label = str(output)
    return {"output": output_label, "files": len(manifest["files"]), "large_assets_included": False}


def check(output: Path) -> dict:
    manifest_path = output / "asset-manifest.json"
    if not manifest_path.is_file():
        return {"valid": False, "failures": ["No existe asset-manifest.json"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for entry in manifest.get("files", []):
        path = output / entry["path"]
        if not path.is_file() or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            failures.append(entry["path"])
    config = manifest.get("logical_asset_config", {})
    pmtiles = config.get("assets", {}).get("esfire30", {}).get("pmtiles", {})
    if pmtiles.get("sha256") != PMTILES_SHA256 or pmtiles.get("bytes") != PMTILES_BYTES:
        failures.append("logical PMTiles config")
    if pmtiles.get("path", "").startswith(("http://", "https://")):
        failures.append("PMTiles host-specific path")
    try:
        output_label = str(output.relative_to(ROOT))
    except ValueError:
        output_label = str(output)
    return {"valid": not failures, "failures": failures, "output": output_label}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/national")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check(args.output) if args.check else build(args.output)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
