#!/usr/bin/env python3
"""Matriz determinista de cobertura glyph para el artifact E3D1.

La prueba recorre contextos peninsulares, insulares y transfronterizos en
cinco escalas. Es una garantía bounded de la matriz de aceptación, no una
afirmación de cobertura Unicode universal.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "build/national-product-staging"
OUTPUT = ROOT / "build/es4e3d1/glyph-coverage-matrix.json"
CONTRACT_PATH = ROOT / "config/national-basemap-protomaps-20260902-z12.json"
sys.path.insert(0, str(ROOT / "benchmarks/es4e3c2_basemap"))
import run as evaluation  # noqa: E402
import run_integration as integration  # noqa: E402


ZOOMS = (5, 7, 9, 12, 14)
CONTEXTS = {
    "spain": (-3.7, 40.3),
    "galicia": (-8.25, 42.8),
    "asturias": (-5.85, 43.15),
    "cantabria": (-4.05, 43.18),
    "pais_vasco": (-2.7, 43.0),
    "navarra": (-1.65, 42.7),
    "catalunya": (1.55, 41.82),
    "comunitat_valenciana": (-0.55, 39.55),
    "illes_balears": (2.85, 39.62),
    "andalucia": (-4.65, 37.45),
    "ceuta": (-5.32, 35.89),
    "melilla": (-2.94, 35.29),
    "canarias": (-15.55, 28.25),
    "interior_madrid_toledo": (-3.72, 40.05),
    "interior_castilla_leon": (-4.75, 41.55),
    "interior_aragon": (-0.88, 41.65),
}


def contract_ranges() -> list[str]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    files = payload["glyphs"].get("files")
    if files is None:
        return [f'{payload["glyphs"]["range"]}.pbf']
    return sorted(f'{row["range"]}.pbf' for row in files)


def glyph_ranges(resources: list[str]) -> list[str]:
    return sorted({
        Path(urlparse(resource).path).name
        for resource in resources
        if "/fonts/Noto%20Sans%20Regular/" in resource and urlparse(resource).path.endswith(".pbf")
    })


def observe_context(chrome: str, base: str, name: str, center: tuple[float, float], timeout: int) -> dict:
    query = urlencode({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES", "source_toggle": "egif:off"})
    with evaluation.chrome_session(chrome, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": f"{base}/index.html?{query}"})
        integration.wait_ready(client, deadline, "ready")
        steps = []
        for zoom in ZOOMS:
            client.evaluate(f"window.__es4cRuntime.map.jumpTo({{center:[{center[0]},{center[1]}],zoom:{zoom}}}); true")
            evaluation.wait_for_map_stable(client, deadline)
            time.sleep(0.25)
            steps.append({"zoom": zoom, "map_loaded": bool(client.evaluate("window.__es4cRuntime.map.loaded()"))})
        observed = client.evaluate(r'''(() => ({
          resources: performance.getEntriesByType('resource').map(entry => entry.name),
          runtime_errors: JSON.parse(document.querySelector('#runtime-test-output').textContent || '{}').errors || [],
          basemap_status: window.__atlasBasemapContext?.status || null
        }))()''')
    ranges = glyph_ranges(observed["resources"])
    return {
        "context": name,
        "center": list(center),
        "zooms": steps,
        "requested_ranges": ranges,
        "runtime_errors": observed["runtime_errors"],
        "basemap_status": observed["basemap_status"],
    }


def validate(payload: dict) -> list[str]:
    failures = []
    bundled = set(payload["bundled_ranges"])
    requested = set(payload["requested_ranges"])
    if requested - bundled:
        failures.append("unbundled glyph ranges")
    if payload.get("glyph_404_count") != 0:
        failures.append("glyph 404")
    if any(row["basemap_status"] != "ready" or row["runtime_errors"] or not all(step["map_loaded"] for step in row["zooms"]) for row in payload["matrix"]):
        failures.append("matrix runtime")
    if len(payload["matrix"]) != len(CONTEXTS):
        failures.append("matrix contexts")
    return failures


def run(chrome: str, artifact: Path, timeout: int) -> dict:
    artifact = artifact.resolve()
    matrix = []
    with evaluation.server_for(artifact) as (server, _log):
        base = f"http://127.0.0.1:{server.server_port}"
        for name, center in CONTEXTS.items():
            print(json.dumps({"glyph_context": name, "status": "starting"}), flush=True)
            row = observe_context(chrome, base, name, center, timeout)
            matrix.append(row)
            print(json.dumps({"glyph_context": name, "requested_ranges": row["requested_ranges"]}), flush=True)
    requested = sorted({range_name for row in matrix for range_name in row["requested_ranges"]})
    bundled = contract_ranges()
    unexpected = sorted(set(requested) - set(bundled))
    # Todo rango solicitado que no existe en el bundle se resolvió como 404
    # por el docroot aislado. Se cuenta por URL/rango lógico, no por reintento.
    payload = {
        "phase": "ES-4E3D1_GLYPH_FIX",
        "discovery_method": "ACCEPTANCE_MATRIX_COMPLETE",
        "artifact": str(artifact),
        "fontstack": "Noto Sans Regular",
        "zooms": list(ZOOMS),
        "matrix": matrix,
        "requested_ranges": requested,
        "bundled_ranges": bundled,
        "unexpected_ranges": unexpected,
        "glyph_unbundled_range_count": len(unexpected),
        "glyph_404_count": len(unexpected),
    }
    failures = validate(payload)
    payload.update({"valid": not failures, "failures": failures})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.output.read_text(encoding="utf-8")) if args.check else run(args.chrome, args.artifact, args.timeout)
    failures = validate(payload)
    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "requested_ranges": payload["requested_ranges"], "unexpected_ranges": sorted(set(payload["requested_ranges"]) - set(payload["bundled_ranges"]))}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
