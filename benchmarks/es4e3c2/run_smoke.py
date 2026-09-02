#!/usr/bin/env python3
"""Smokes Chromium dirigidos E3C2; no despliega ni ejecuta benchmarks."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
BASELINE_DATA = ROOT / "build/national-pages-staging/data"
SUMMARY = ROOT / "data/derived/spain/national-ux-summary-v1"
HIGHLIGHTS = ROOT / "data/derived/spain/national-highlights-v1"
BUILDER = ROOT / "scripts/build_national_frontend.py"
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import CDPClient  # noqa: E402
sys.path.insert(0, str(ROOT / "prototypes/es4c"))
from run_smoke import start_server  # noqa: E402

SCENARIOS = {
    "spain_1995_egif": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop", "click"),
    "galicia_1995_egif": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12"}, "desktop", "click"),
    "gva_1995_icv": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop", "click"),
    "gva_2024_icv": ({"smoke": "pais_valencia", "from": 2024, "to": 2024, "egif_scope": "ES:CCAA:10"}, "desktop", "click"),
    "gva_2026_effis": ({"smoke": "pais_valencia", "from": 2026, "to": 2026, "egif_scope": "ES:CCAA:10"}, "desktop", "click"),
    "elx_2025_effis": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "desktop", "click"),
    "gva_1995_icv_500": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop", "filter_click"),
    "ourense_context": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "province_select": "ES:PROV:32"}, "desktop", "none"),
    "canarias_context": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:05"}, "desktop", "none"),
    "mobile_elx": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile", "click"),
}


@contextmanager
def temporary_chrome_profile():
    profile = Path(tempfile.mkdtemp(prefix="atlas-e3c2-cdp-"))
    try:
        yield str(profile)
    finally:
        # Chromium puede mantener brevemente ficheros auxiliares tras cerrar el
        # proceso principal; la limpieza del harness no debe invalidar el smoke.
        for _attempt in range(5):
            shutil.rmtree(str(profile), ignore_errors=True)
            if not profile.exists():
                break
            time.sleep(.05)


def temporary_site(directory: Path) -> Path:
    site = directory / "site"
    result = subprocess.run([sys.executable, str(BUILDER), "--output", str(site)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    data = site / "data"; data.mkdir()
    for child in BASELINE_DATA.iterdir():
        (data / child.name).symlink_to(child, target_is_directory=child.is_dir())
    for category, source in (("summary", SUMMARY), ("highlights", HIGHLIGHTS)):
        parent = data / category; parent.mkdir()
        (parent / source.name).symlink_to(source, target_is_directory=True)
    return site


def observe(chrome: str, url: str, device: str, action: str, timeout: int) -> dict:
    size = "390,844" if device == "mobile" else "1440,900"
    with temporary_chrome_profile() as profile:
        process = subprocess.Popen([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--enable-precise-memory-info", "--remote-debugging-port=0", "--remote-allow-origins=*", "--user-data-dir=" + profile, "--window-size=" + size, "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = None
        try:
            deadline = time.monotonic() + timeout
            port_file = Path(profile) / "DevToolsActivePort"
            while not port_file.exists():
                if process.poll() is not None: raise RuntimeError("Chromium terminó antes de abrir DevTools")
                if time.monotonic() > deadline: raise TimeoutError("Chromium no abrió DevTools")
                time.sleep(.05)
            port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                page = next(row for row in json.load(response) if row["type"] == "page")
            client = CDPClient(page["webSocketDebuggerUrl"]); client.command("Page.enable"); client.command("Runtime.enable")
            if device == "mobile": client.command("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
            client.command("Page.navigate", {"url": url})
            while not client.evaluate("document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && ['ready','empty','deferred','inactive'].includes(document.querySelector('#highlights-slot')?.dataset.status)"):
                if time.monotonic() > deadline: raise TimeoutError("Destacados E3C2 no quedaron preparados")
                time.sleep(.08)
            if action == "filter_click":
                client.evaluate("(async()=>{await window.__es4cRuntime.setAnalysisFilter({filter_id:'icv_min_area',filter_type:'min_value',source:'icv',metric_id:'icv_declared_forest_area_ha',value:500,unit:'ha'}); await window.__nationalProductShell.metrics.update(window.__es4cRuntime.getState(),null,{force:true}); window.__nationalProductShell.sync(); return true})()")
                while client.evaluate("document.querySelector('#highlights-slot').dataset.status") != "ready":
                    if time.monotonic() > deadline: raise TimeoutError("Filtro/destacados no convergieron")
                    time.sleep(.05)
            if action in {"click", "filter_click"} and client.evaluate("Boolean(document.querySelector('#highlights-list button'))"):
                client.evaluate("document.querySelector('#highlights-list button').click()")
                while not client.evaluate(r'''(() => {
                  const source=document.querySelector('#highlights-slot').dataset.source;
                  const state=window.__es4cRuntime.getState();
                  if(source==='egif') return Boolean(state.selected_egif_record_id) && document.querySelector('#egif-detail').innerText.includes('Registro de incendio');
                  if(source==='icv') return Boolean(state.selected_icv_record_id) && document.querySelector('#icv-detail').innerText.includes('Incendio oficial documentado');
                  if(source==='effis') return Boolean(state.selected_effis_geometry_id) && document.querySelector('#effis-detail').innerText.includes('Perímetro satelital provisional');
                  return false;
                })()'''):
                    if time.monotonic() > deadline:
                        diagnostic = client.evaluate("({source:document.querySelector('#highlights-slot').dataset.source,status:document.querySelector('#highlights-status').textContent,state:window.__es4cRuntime.getState(),egif:document.querySelector('#egif-detail').innerText,icv:document.querySelector('#icv-detail').innerText,effis:document.querySelector('#effis-detail').innerText})")
                        raise TimeoutError(f"La ficha destacada no se abrió: {diagnostic}")
                    time.sleep(.08)
            time.sleep(.2)
            return client.evaluate(r'''(() => {
              const rt=JSON.parse(document.querySelector('#runtime-test-output').textContent); const hs=window.__nationalProductShell.highlights.getState();
              const r=q=>{const x=document.querySelector(q)?.getBoundingClientRect();return x?{top:x.top,bottom:x.bottom,height:x.height,width:x.width}:null};
              const layers=window.__es4cRuntime.map.getStyle().layers.map(x=>x.id);
              return {state:window.__es4cRuntime.getState(),source:document.querySelector('#highlights-slot').dataset.source,status:document.querySelector('#highlights-slot').dataset.status,
                title:document.querySelector('#highlights-title').textContent,contract:document.querySelector('#highlights-contract').textContent,
                items:[...document.querySelectorAll('#highlights-list button')].map(x=>x.innerText),visible_items:document.querySelectorAll('#highlights-list button').length,
                detail:{egif:document.querySelector('#egif-detail')?.innerText,icv:document.querySelector('#icv-detail')?.innerText,effis:document.querySelector('#effis-detail')?.innerText},
                result_status:hs?.result?.status,metric_id:hs?.contract?.metric_id,ranking_count:hs?.ranked?.length,telemetry:hs?.result?.telemetry,
                map_context:document.querySelector('.map-context')?.innerText,legend:[...document.querySelectorAll('#user-map-legend li')].map(x=>x.textContent),
                layer_order:{ccaa:layers.indexOf('official-ccaa-territories-fill'),fire:layers.indexOf('esfire30-perimeters'),selected:layers.indexOf('official-ccaa-territories-selected')},
                map_rect:r('.map-region'),viewport:{width:innerWidth,height:innerHeight},resources:performance.getEntriesByType('resource').map(x=>x.name),
                heap:performance.memory?.usedJSHeapSize??null,errors:rt.errors||[],bootstrap:document.querySelector('#national-bootstrap-error').textContent};
            })()''')
        finally:
            if client: client.close()
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


def validate(runs: list[dict]) -> list[str]:
    failures = []; by = {row["scenario"]: row for row in runs}
    expected = {"spain_1995_egif": "egif", "galicia_1995_egif": "egif", "gva_1995_icv": "icv", "gva_2024_icv": "icv", "gva_2026_effis": "effis", "elx_2025_effis": "effis", "gva_1995_icv_500": "icv"}
    for row in runs:
        if row.get("errors") or row.get("bootstrap"): failures.append(f"{row['scenario']}: errores de runtime")
        if row["layer_order"]["ccaa"] < 0 or row["layer_order"]["ccaa"] >= row["layer_order"]["fire"] or row["layer_order"]["selected"] <= row["layer_order"]["fire"]: failures.append(f"{row['scenario']}: jerarquía cartográfica")
        if not (row.get("map_context") or "").strip(): failures.append(f"{row['scenario']}: contexto territorial ausente")
        if row.get("device") != "mobile" and "BDLJE" not in (row.get("map_context") or ""): failures.append(f"{row['scenario']}: atribución contextual BDLJE ausente")
    for name, source in expected.items():
        row = by[name]
        if row["source"] != source or row["status"] != "ready" or not 1 <= row["visible_items"] <= 5: failures.append(f"{name}: destacados {source} incorrectos")
        detail_marker = {"egif": "Registro de incendio", "icv": "Incendio oficial documentado", "effis": "Perímetro satelital provisional"}[source]
        if "ha" not in " ".join(row["items"]) or detail_marker not in (row["detail"][source] or ""): failures.append(f"{name}: ranking/ficha incompletos")
    if by["spain_1995_egif"]["telemetry"].get("requests") != 2: failures.append("spain: derivado nacional no fue mínimo")
    if by["spain_1995_egif"]["state"].get("selected_egif_record_id") is None: failures.append("spain: selección EGIF ausente")
    if any("geometry" in text.lower() for text in by["spain_1995_egif"]["items"]): failures.append("spain: marcador/geometría EGIF inventada")
    if any("\n" not in item for item in by["gva_1995_icv_500"]["items"]): failures.append("gva filter: cards no humanas")
    if by["canarias_context"]["result_status"] != "complete" or "Perímetros Landsat" in by["canarias_context"]["legend"]: failures.append("canarias: contexto/cobertura")
    if by["mobile_elx"]["map_rect"]["top"] > 80 or by["mobile_elx"]["map_rect"]["bottom"] > by["mobile_elx"]["viewport"]["height"] * .62: failures.append("mobile: mapa no inmediato")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--chrome", default="/usr/bin/google-chrome"); parser.add_argument("--all", action="store_true"); parser.add_argument("--scenario", action="append", choices=tuple(SCENARIOS)); parser.add_argument("--output", type=Path, default=Path("/tmp/es4e3c2-smokes.json")); parser.add_argument("--check", action="store_true"); parser.add_argument("--timeout", type=int, default=150); args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8")); failures = validate(payload["runs"]); print(json.dumps({"valid": not failures, "failures": failures, "runs": len(payload["runs"])})); return 0 if not failures else 1
    selected = list(SCENARIOS) if args.all else (args.scenario or ["spain_1995_egif"])
    with tempfile.TemporaryDirectory(prefix="atlas-e3c2-site-") as directory:
        site = temporary_site(Path(directory)); server, _range = start_server(root=site)
        try:
            runs = []
            for name in selected:
                query, device, action = SCENARIOS[name]; row = observe(args.chrome, f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(query)}", device, action, args.timeout); row.update({"scenario": name, "device": device}); runs.append(row)
        finally: server.shutdown(); server.server_close()
    failures = validate(runs) if args.all else []
    payload = {"phase": "ES-4E3C2", "valid": not failures, "failures": failures, "runs": runs}; args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(json.dumps({"valid": not failures, "failures": failures, "runs": len(runs), "output": str(args.output)})); return 0 if not failures else 1


if __name__ == "__main__": raise SystemExit(main())
