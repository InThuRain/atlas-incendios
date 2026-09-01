#!/usr/bin/env python3
"""Smokes dirigidos de la shell E3A sobre el artifact técnico local congelado.

Sirve los assets aceptados de D4B mediante enlaces temporales y superpone sólo
los ficheros de ``src/national``. No modifica ni recompone el staging remoto.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "build/national-pages-staging"
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import CDPClient  # noqa: E402
sys.path.insert(0, str(ROOT / "prototypes/es4c"))
from run_smoke import start_server  # noqa: E402


NATIVE_ELX_HASH = "#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM4LjE3OTEsImxvbiI6LTAuNzE4OTIsInoiOjExLjQ4fSwidGltZSI6eyJmcm9tIjoxOTkzLCJ0byI6MTk5M30sInRlcnJpdG9yeSI6eyJzY29wZSI6Im11bmljaXBhbGl0eSIsImF1dG9ub21vdXNfY29tbXVuaXR5X2lkIjoiRVM6Q0NBQToxMCIsInByb3ZpbmNlX2lkIjoiRVM6UFJPVjowMyIsIm11bmljaXBhbGl0eV9pZCI6IkVTOk1VTjowMzA2NSJ9LCJzb3VyY2VzIjp7ImVzZmlyZTMwIjp0cnVlLCJlZ2lmIjp0cnVlfSwic2VsZWN0aW9ucyI6eyJnZW9tZXRyeV9pZCI6ImVzZmlyZTMwOnYxOjE5OTM6Nzc3IiwiZWdpZl9yZWNvcmRfaWQiOm51bGx9fQ"
LEGACY_ELX_EFFIS_HASH = "#v=1&lat=38.17000&lng=-0.71000&z=11&from=2025&to=2025&src=effis&province=alicante&municipality=03065&min_area=10&gif=0&entity=effis%3Arda%3A285361%3Af05085eba622a5bb&geometry=effis%3Arda%3A285361%3Af05085eba622a5bb"

SCENARIOS = {
    "spain_default": ({"smoke": "spain"}, "desktop"),
    "galicia_1995": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12"}, "desktop"),
    "gva_1995": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop"),
    "gva_2024": ({"smoke": "pais_valencia", "from": 2024, "to": 2024, "egif_scope": "ES:CCAA:10"}, "desktop"),
    "gva_2026": ({"smoke": "pais_valencia", "from": 2026, "to": 2026, "egif_scope": "ES:CCAA:10"}, "desktop"),
    "elx_2025": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "desktop"),
    "spain_1975": ({"smoke": "spain", "from": 1975, "to": 1975, "egif_scope": "ES"}, "desktop"),
    "canarias_1995": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:05"}, "desktop"),
    "agost_zero": ({"smoke": "pais_valencia", "from": 1985, "to": 2021, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03002"}, "desktop"),
    "legacy_elx_effis": ({"smoke": "pais_valencia", "legacy_copy": 1, "_hash": LEGACY_ELX_EFFIS_HASH}, "desktop"),
    "native_elx": ({"smoke": "pais_valencia", "_hash": NATIVE_ELX_HASH}, "desktop"),
    "mobile_spain": ({"smoke": "spain"}, "mobile"),
    "mobile_elx_2025": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile"),
}


def temporary_site(directory: Path) -> Path:
    if not BASELINE.is_dir():
        raise FileNotFoundError("Falta build/national-pages-staging, baseline técnico local aceptado")
    site = directory / "site"
    site.mkdir()
    overrides = {"index.html", "styles.css", "bootstrap.js", "product-shell.mjs", "source-registry.mjs"}
    for child in BASELINE.iterdir():
        if child.name not in overrides:
            (site / child.name).symlink_to(child, target_is_directory=child.is_dir())
    for name in overrides:
        source = ROOT / "src/national" / name
        if source.is_file():
            shutil.copy2(source, site / name)
    return site


def observed_page(chrome: str, url: str, device: str, timeout: int = 150) -> dict:
    window_size = "390,844" if device == "mobile" else "1440,900"
    with tempfile.TemporaryDirectory(prefix="atlas-e3a-cdp-") as profile:
        process = subprocess.Popen([
            chrome, "--headless", "--no-sandbox", "--disable-gpu", "--enable-precise-memory-info",
            "--remote-debugging-port=0", "--remote-allow-origins=*", "--user-data-dir=" + profile,
            "--window-size=" + window_size, "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = None
        try:
            deadline = time.monotonic() + timeout
            port_file = Path(profile) / "DevToolsActivePort"
            while not port_file.exists():
                if process.poll() is not None:
                    raise RuntimeError("Chromium terminó antes de abrir DevTools")
                if time.monotonic() > deadline:
                    raise TimeoutError("Chromium no abrió DevTools")
                time.sleep(.05)
            port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                page = next(row for row in json.load(response) if row["type"] == "page")
            client = CDPClient(page["webSocketDebuggerUrl"])
            client.command("Page.enable"); client.command("Runtime.enable")
            if device == "mobile":
                client.command("Emulation.setDeviceMetricsOverride", {
                    "width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True,
                })
            client.command("Page.navigate", {"url": url})
            while True:
                complete = client.evaluate("document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && Boolean(window.__nationalProductShell)")
                if complete:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("El smoke E3A no terminó")
                time.sleep(.08)
            time.sleep(.35)
            expression = r'''(() => {
              window.__nationalProductShell.sync();
              const rect = (selector) => {
                const row = document.querySelector(selector)?.getBoundingClientRect();
                return row ? {top:row.top,left:row.left,right:row.right,bottom:row.bottom,width:row.width,height:row.height} : null;
              };
              const runtime = JSON.parse(document.querySelector('#runtime-test-output').textContent);
              const state = window.__es4cRuntime.getState();
              const primary = [...document.querySelectorAll('.explorer-panel > :not(details)')].map(node => node.innerText).join(' ');
              return {
                runtime,
                state,
                recommended_view: window.__nationalProductShell.recommendedView(),
                header_territory: document.querySelector('#header-territory').textContent,
                header_period: document.querySelector('#header-period').textContent,
                coverage_copy: document.querySelector('#human-coverage-message').textContent,
                egif_copy: document.querySelector('#egif-human-status').textContent,
                legend: [...document.querySelectorAll('#user-map-legend li')].map(node => node.textContent),
                sources_open: document.querySelector('#sources-methodology').open,
                sources_summary_expanded: document.querySelector('#sources-methodology > summary').getAttribute('aria-expanded'),
                rectangles: {header:rect('.product-header'),map:rect('.map-region'),panel:rect('.explorer-panel')},
                viewport: {width:innerWidth,height:innerHeight},
                primary_internal_terms: [' idle',' ready',' complete',' no_coverage',' not_integrated_for_territory',' initial',' detail',' shard'].filter(term => primary.toLowerCase().includes(term)),
                bootstrap_error: document.querySelector('#national-bootstrap-error').textContent,
                hash_format: location.hash.startsWith('#v=1') ? 'gva_v1' : location.hash.startsWith('#es4c-state-v1=') ? 'national_v1' : 'other'
              };
            })()'''
            return client.evaluate(expression)
        finally:
            if client:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
            time.sleep(.2)


def validate(runs: list[dict]) -> list[str]:
    failures = []
    by_name = {row["scenario"]: row for row in runs}
    for row in runs:
        name = row["scenario"]
        if row.get("bootstrap_error"):
            failures.append(f"{name}: bootstrap error: {row['bootstrap_error']}")
        if row.get("runtime", {}).get("errors"):
            failures.append(f"{name}: runtime errors: {row['runtime']['errors']}")
        if row.get("sources_open") or row.get("sources_summary_expanded") != "false":
            failures.append(f"{name}: fuentes/metodología no está plegado")
        if row.get("primary_internal_terms"):
            failures.append(f"{name}: términos internos visibles: {row['primary_internal_terms']}")
        rectangles = row.get("rectangles", {})
        if row["device"] == "desktop":
            map_rect, panel_rect = rectangles.get("map"), rectangles.get("panel")
            if not map_rect or not panel_rect or map_rect["width"] <= panel_rect["width"] * 1.8:
                failures.append(f"{name}: mapa no domina layout desktop")
        else:
            map_rect = rectangles.get("map")
            if not map_rect or map_rect["top"] > 80 or map_rect["bottom"] > row["viewport"]["height"] * .62:
                failures.append(f"{name}: mapa no aparece pronto en primer viewport móvil")
    expected_primary = {
        "spain_default": "esfire30", "galicia_1995": "esfire30", "gva_1995": "icv",
        "gva_2024": "icv", "gva_2026": "effis", "elx_2025": "effis",
    }
    for name, source in expected_primary.items():
        if by_name[name]["recommended_view"]["primary"] != source:
            failures.append(f"{name}: fuente recomendada != {source}")
    if "no de perímetros" not in by_name["spain_1975"]["coverage_copy"]:
        failures.append("spain_1975: copy humano de ausencia incorrecto")
    if "no de perímetros" not in by_name["canarias_1995"]["coverage_copy"]:
        failures.append("canarias_1995: copy humano de ausencia incorrecto")
    if "No hay perímetros Landsat" not in by_name["agost_zero"]["coverage_copy"]:
        failures.append("agost_zero: resultado cero confundido con ausencia de datos")
    if by_name["legacy_elx_effis"]["runtime"].get("input_hash_format") != "gva_v1":
        failures.append("legacy: #v=1 no restaurado")
    if by_name["native_elx"]["runtime"].get("input_hash_format") != "national_v1":
        failures.append("native: #es4c-state-v1 no restaurado")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), action="append")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("/tmp/es4e3a-smokes.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload["runs"])
        print(json.dumps({"valid": not failures, "failures": failures, "runs": len(payload["runs"])}))
        return 0 if not failures else 1
    selected = list(SCENARIOS) if args.all else (args.scenario or ["spain_default"])
    with tempfile.TemporaryDirectory(prefix="atlas-e3a-site-") as directory:
        site = temporary_site(Path(directory))
        server, range_state = start_server(root=site)
        try:
            runs = []
            for name in selected:
                config, device = SCENARIOS[name]
                query = {key: value for key, value in config.items() if not key.startswith("_")}
                url = f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(query)}{config.get('_hash', '')}"
                observed = observed_page(args.chrome, url, device)
                observed.update({"scenario": name, "device": device})
                runs.append(observed)
        finally:
            server.shutdown(); server.server_close()
    failures = validate(runs) if args.all else []
    payload = {"phase": "ES-4E3A", "runs": runs, "range": range_state.payload(), "valid": not failures, "failures": failures}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "runs": len(runs), "output": str(args.output)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
