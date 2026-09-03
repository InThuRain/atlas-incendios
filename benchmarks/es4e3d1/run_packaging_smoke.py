#!/usr/bin/env python3
"""Checks de packaging E3D1 ejecutados exclusivamente desde el artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "build/national-product-staging"
OUTPUT = ROOT / "build/es4e3d1/packaging-smokes.json"
sys.path.insert(0, str(ROOT / "benchmarks/es4e3c2_basemap"))
import run as evaluation  # noqa: E402
import run_integration as integration  # noqa: E402

CONTRACT = json.loads((ROOT / "config/national-basemap-protomaps-20260902-z12.json").read_text(encoding="utf-8"))
BASEMAP_SOURCE = ROOT / CONTRACT["pmtiles"]["source_path"]
FIRE_SOURCE = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles"
BASEMAP_RUNTIME = Path(CONTRACT["pmtiles"]["runtime_path"])
FIRE_RUNTIME = Path("data/esfire30/v1/3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe/esfire30-national-fidelity-territories.pmtiles")
GLYPH_DESCRIPTORS = CONTRACT["glyphs"]["files"]
BUNDLED_GLYPH_RANGES = {f'{descriptor["range"]}.pbf' for descriptor in GLYPH_DESCRIPTORS}
FORBIDDEN_BROWSER_PATHS = ("/src/", "/prototypes/", "/data/derived/", "/work/")

QUICK = {
    "root": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop", "/"),
    "spain": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop", "/index.html"),
    "gva_1995": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10"}, "desktop", "/index.html"),
    "elx": ({"smoke": "pais_valencia", "from": 1993, "to": 2002, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "desktop", "/index.html"),
    "mobile": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "mobile", "/index.html"),
    "mobile_elx": ({"smoke": "pais_valencia", "from": 1993, "to": 2002, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile", "/index.html"),
    "mobile_asturias": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:03", "territory_select": "ES:CCAA:03", "source_toggle": "egif:off"}, "mobile", "/index.html"),
}

GLYPH_CONTEXTS = {
    "galicia": ("galicia", "ES:CCAA:12"),
    "asturias": ("spain", "ES:CCAA:03"),
    "pais_vasco": ("spain", "ES:CCAA:16"),
    "catalunya": ("spain", "ES:CCAA:09"),
    "comunitat_valenciana": ("pais_valencia", "ES:CCAA:10"),
    "illes_balears": ("spain", "ES:CCAA:04"),
    "ceuta": ("spain", "ES:CCAA:18"),
    "melilla": ("spain", "ES:CCAA:19"),
}


def requested_glyph_ranges(row: dict) -> list[str]:
    """Devuelve todos los rangos que Chromium intentó resolver.

    El log del servidor solo registra ficheros existentes porque los 404 los
    atiende ``SimpleHTTPRequestHandler`` antes de pasar por ``RequestLog``.
    PerformanceResourceTiming, en cambio, conserva también esas solicitudes
    fallidas y es la fuente correcta para la auditoría de cobertura.
    """
    return sorted({
        Path(resource.split("?", 1)[0]).name
        for resource in row.get("resources", [])
        if "/fonts/Noto%20Sans%20Regular/" in resource and resource.split("?", 1)[0].endswith(".pbf")
    })


def fetch(url: str, start: int | None = None, end: int | None = None) -> tuple[int, bytes, dict]:
    headers = {"Range": f"bytes={start}-{end}"} if start is not None else {}
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return response.status, response.read(), dict(response.headers.items())


def range_audit(artifact: Path) -> dict:
    rows = {}
    with evaluation.server_for(artifact) as (server, _log):
        base = f"http://127.0.0.1:{server.server_port}"
        for logical_id, runtime, source in (
            ("protomaps_basemap_pmtiles", BASEMAP_RUNTIME, BASEMAP_SOURCE),
            ("esfire30_fire_pmtiles", FIRE_RUNTIME, FIRE_SOURCE),
        ):
            size = source.stat().st_size
            probes = {
                "zero": (0, 0),
                "initial": (0, 16383),
                "middle": (size // 2, size // 2 + 16383),
                "final": (size - 16384, size - 1),
            }
            checks = []
            with source.open("rb") as local:
                for name, (start, end) in probes.items():
                    status, body, headers = fetch(f"{base}/{runtime.as_posix()}", start, end)
                    local.seek(start)
                    expected = local.read(end - start + 1)
                    checks.append({
                        "probe": name,
                        "start": start,
                        "end": end,
                        "status": status,
                        "bytes": len(body),
                        "content_range": headers.get("Content-Range"),
                        "byte_identical": body == expected,
                    })
            rows[logical_id] = {"size": size, "checks": checks, "full_download": False}
        glyph_rows = []
        for descriptor in GLYPH_DESCRIPTORS:
            runtime = CONTRACT["glyphs"]["runtime_template"].replace("{fontstack}", CONTRACT["glyphs"]["fontstack"]).replace("{range}", descriptor["range"])
            glyph_status, glyph_body, _headers = fetch(f"{base}/{runtime.replace(' ', '%20')}")
            glyph_rows.append({"range": descriptor["range"], "status": glyph_status, "bytes": len(glyph_body), "sha256_matches": hashlib.sha256(glyph_body).hexdigest() == descriptor["sha256"]})
    return {"pmtiles": rows, "glyphs": glyph_rows}


def run_browser(chrome: str, artifact: Path, timeout: int) -> tuple[list[dict], list[dict]]:
    quick_rows = []
    glyph_rows = []
    with evaluation.server_for(artifact) as (server, log):
        base = f"http://127.0.0.1:{server.server_port}"
        status, body, _headers = fetch(f"{base}/")
        if status != 200 or b'id="national-product-shell"' not in body:
            raise RuntimeError(f"Docroot del artifact inválido: status={status}, bytes={len(body)}, root={artifact}")
        for name, (query, device, entry) in QUICK.items():
            print(json.dumps({"quick": name, "status": "starting", "artifact": str(artifact)}), flush=True)
            row = integration.observe(chrome, f"{base}{entry}?{urlencode(query)}", device, f"{name}_quick", log, timeout)
            row["scenario"] = name
            quick_rows.append(row)
            print(json.dumps({"quick": name, "basemap": row["basemap"]["status"], "errors": row["runtime_errors"]}), flush=True)
        for name, (map_name, territory_id) in GLYPH_CONTEXTS.items():
            print(json.dumps({"glyph": name, "status": "starting"}), flush=True)
            query = {"smoke": map_name, "from": 1995, "to": 1995, "egif_scope": territory_id, "territory_select": territory_id, "source_toggle": "egif:off"}
            row = integration.observe(chrome, f"{base}/index.html?{urlencode(query)}", "desktop", f"glyph_{name}", log, timeout)
            glyph_rows.append({
                "scenario": name,
                "status": row["basemap"]["status"],
                "glyphs": row["network"]["glyphs"],
                "requested_ranges": requested_glyph_ranges(row),
                "unbundled_ranges": sorted(set(requested_glyph_ranges(row)) - BUNDLED_GLYPH_RANGES),
                "labels": row["label_examples"],
                "runtime_errors": row["runtime_errors"],
                "external_runtime_domains": row["external_runtime_domains"],
            })
            print(json.dumps({"glyph": name, "requested_ranges": requested_glyph_ranges(row)}), flush=True)
    return quick_rows, glyph_rows


def run_fallback(chrome: str, artifact: Path, timeout: int) -> dict:
    # El árbol de fault injection usa hardlinks y por ello debe vivir en el
    # mismo filesystem que el artifact, no necesariamente en /tmp.
    with tempfile.TemporaryDirectory(prefix="es4e3d1-fallback-", dir=str(artifact.parent)) as temporary:
        fault_site = Path(temporary) / "artifact"
        shutil.copytree(artifact, fault_site, copy_function=os.link)
        (fault_site / BASEMAP_RUNTIME).unlink()
        with evaluation.server_for(fault_site) as (server, log):
            query = QUICK["spain"][0]
            return integration.observe_fallback(chrome, f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(query)}", log, timeout)


def validate(payload: dict) -> list[str]:
    failures = []
    for logical_id, asset in payload["range_audit"]["pmtiles"].items():
        for check in asset["checks"]:
            expected = check["end"] - check["start"] + 1
            expected_range = f"bytes {check['start']}-{check['end']}/{asset['size']}"
            if check["status"] != 206 or check["bytes"] != expected or check["content_range"] != expected_range or not check["byte_identical"]:
                failures.append(f"Range:{logical_id}:{check['probe']}")
    glyph_http = payload["range_audit"]["glyphs"]
    if len(glyph_http) != len(GLYPH_DESCRIPTORS) or any(row["status"] != 200 or not row["sha256_matches"] for row in glyph_http):
        failures.append("glyph artifact HTTP")
    for row in payload["quick_smokes"]:
        network = row["network"]
        if row["basemap"]["status"] != "ready" or row["runtime_errors"] or row["bootstrap_error"] or row["external_runtime_domains"]:
            failures.append(f"quick:{row['scenario']}:runtime")
        if network["basemap"]["full_download"] or network["esfire30"]["full_download"]:
            failures.append(f"quick:{row['scenario']}:full download")
        if network["basemap"]["requests"] != network["basemap"]["range_requests"]:
            failures.append(f"quick:{row['scenario']}:basemap Range")
        if network["esfire30"]["requests"] and network["esfire30"]["requests"] != network["esfire30"]["range_requests"]:
            failures.append(f"quick:{row['scenario']}:fire Range")
        if any(marker in resource for marker in FORBIDDEN_BROWSER_PATHS for resource in row["resources"]):
            failures.append(f"quick:{row['scenario']}:source-tree fallback")
    by_name = {row["scenario"]: row for row in payload["quick_smokes"]}
    if by_name["elx"]["state"].get("municipality_id") != "ES:MUN:03065":
        failures.append("quick:elx:municipality")
    if by_name["mobile"]["viewport"]["width"] != 390 or by_name["mobile"]["map_rect"]["top"] > 80:
        failures.append("quick:mobile:map first")
    for scenario in ("mobile_elx", "mobile_asturias"):
        if by_name[scenario]["viewport"]["width"] != 390 or by_name[scenario]["map_rect"]["top"] > 80:
            failures.append(f"quick:{scenario}:map first")
    if by_name["mobile_elx"]["state"].get("municipality_id") != "ES:MUN:03065":
        failures.append("quick:mobile_elx:municipality")
    requested = {
        range_name
        for row in payload["glyph_coverage"]
        for range_name in row.get("requested_ranges", [Path(path).name for path in row["glyphs"]["paths"]])
    }
    if requested - BUNDLED_GLYPH_RANGES:
        failures.append("glyph coverage:additional range")
    if any(row["status"] != "ready" or row["runtime_errors"] or row["glyphs"]["statuses"] != [200] for row in payload["glyph_coverage"]):
        failures.append("glyph coverage:runtime")
    fallback = payload["fallback"]
    if fallback["basemap"]["status"] != "fallback_bdlje_only" or not fallback["bdlje"] or not fallback["esfire30"] or fallback["runtime_errors"] or fallback["bootstrap_error"]:
        failures.append("fallback BDLJE-only")
    return sorted(set(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Reutiliza Range/quick/glyph válidos y ejecuta solo el fallback pendiente.")
    args = parser.parse_args()
    args.artifact = args.artifact.resolve()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "quick_smokes": len(payload.get("quick_smokes", [])), "glyph_contexts": len(payload.get("glyph_coverage", []))}))
        return 0 if not failures else 1
    if args.resume and args.output.is_file():
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        reusable = all(key in payload for key in ("range_audit", "quick_smokes", "glyph_coverage"))
        if not reusable:
            print(json.dumps({"valid": False, "failures": ["No existe evidencia parcial reutilizable"]}))
            return 1
        payload.pop("valid", None)
        payload.pop("failures", None)
    else:
        payload = {
            "phase": "ES-4E3D1",
            "artifact": str(args.artifact),
            "served_as_isolated_docroot": True,
            "range_audit": range_audit(args.artifact),
        }
    try:
        if not args.resume:
            payload["quick_smokes"], payload["glyph_coverage"] = run_browser(args.chrome, args.artifact, args.timeout)
        print(json.dumps({"fallback": "starting", "artifact": str(args.artifact)}), flush=True)
        payload["fallback"] = run_fallback(args.chrome, args.artifact, args.timeout)
    except Exception as error:  # conserva el preflight y un diagnóstico legible
        payload.update({"valid": False, "failures": [f"{type(error).__name__}: {error}"]})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"valid": False, "failures": payload["failures"], "output": str(args.output)}), flush=True)
        return 1
    failures = validate(payload)
    payload.update({
        "valid": not failures,
        "failures": failures,
        "glyph_coverage_status": "PASS_FOR_TESTED_SPANISH_CONTEXTS" if not any(item.startswith("glyph coverage") for item in failures) else "INCOMPLETE",
        "full_protomaps_download": False,
        "full_esfire30_download": False,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output), "quick_smokes": len(payload["quick_smokes"]), "glyph_contexts": len(payload["glyph_coverage"])}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
