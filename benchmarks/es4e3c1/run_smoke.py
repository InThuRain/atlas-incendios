#!/usr/bin/env python3
"""Smokes Chromium dirigidos de filtros/fichas E3C1; no es un benchmark."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import CDPClient  # noqa: E402
sys.path.insert(0, str(ROOT / "prototypes/es4c"))
from run_smoke import start_server  # noqa: E402
_spec = importlib.util.spec_from_file_location("es4e3b2_smoke", ROOT / "benchmarks/es4e3b2/run_smoke.py")
_module = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_module)
temporary_site = _module.temporary_site

SCENARIOS = {
    "spain_egif_500": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop", "egif_min"),
    "galicia_egif_gif": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12"}, "desktop", "egif_gif"),
    "gva_icv_min": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop", "icv_min"),
    "gva_icv_cause": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop", "icv_cause"),
    "gva_zero": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop", "icv_zero"),
    "gva_2024_detail": ({"smoke": "pais_valencia", "from": 2024, "to": 2024, "egif_scope": "ES:CCAA:10"}, "desktop", "icv_detail"),
    "galicia_egif_detail": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12"}, "desktop", "egif_detail"),
    "galicia_esfire_detail": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12"}, "desktop", "esfire_detail"),
    "elx_effis": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "desktop", "effis_detail"),
    "canarias": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:05"}, "desktop", "coverage"),
    "invalidation": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop", "invalidation"),
    "permalink": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop", "permalink"),
    "mobile_filters": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "mobile", "mobile_filter"),
    "mobile_detail": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile", "mobile_detail"),
}

FILTERS = {
    "egif_min": {"filter_id": "egif_min_area", "filter_type": "min_value", "source": "egif", "metric_id": "egif_declared_forest_area_ha", "value": 500, "unit": "ha"},
    "egif_gif": {"filter_id": "egif_gif", "filter_type": "flag", "source": "egif", "metric_id": "egif_administrative_gif_count", "value": True, "unit": None},
    "icv_min": {"filter_id": "icv_min_area", "filter_type": "min_value", "source": "icv", "metric_id": "icv_declared_forest_area_ha", "value": 100, "unit": "ha"},
    "icv_cause": {"filter_id": "icv_cause", "filter_type": "enum", "source": "icv", "metric_id": "icv_cause_distribution", "value": "lightning", "unit": None},
    "icv_zero": {"filter_id": "icv_cause", "filter_type": "enum", "source": "icv", "metric_id": "icv_cause_distribution", "value": "negligence", "unit": None},
    "effis_detail": {"filter_id": "effis_min_area", "filter_type": "min_value", "source": "effis", "metric_id": "effis_mapped_area_ha", "value": 0.01, "unit": "ha"},
    "mobile_filter": {"filter_id": "icv_min_area", "filter_type": "min_value", "source": "icv", "metric_id": "icv_declared_forest_area_ha", "value": 100, "unit": "ha"},
    "permalink": {"filter_id": "icv_cause", "filter_type": "enum", "source": "icv", "metric_id": "icv_cause_distribution", "value": "lightning", "unit": None},
}


def observe(chrome: str, url: str, device: str, action: str, timeout: int) -> dict:
    size = "390,844" if device == "mobile" else "1440,900"
    with tempfile.TemporaryDirectory(prefix="atlas-e3c1-cdp-") as profile:
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
            while not client.evaluate("document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && window.__nationalProductShell?.metrics?.getState()?.result?.status === 'complete'"):
                if time.monotonic() > deadline: raise TimeoutError("El runtime E3C1 no quedó preparado")
                time.sleep(.08)
            requested = FILTERS.get(action)
            if requested:
                await_filter = "await window.__es4cRuntime.setAnalysisFilter(%s); await window.__nationalProductShell.metrics.update(window.__es4cRuntime.getState(), null, {force:true}); window.__nationalProductShell.sync();" % json.dumps(requested)
                client.evaluate(f"(async()=>{{{await_filter} return true;}})()")
            if action == "icv_detail": client.evaluate("window.__es4cRuntime.selectIcvRecord('gva:pif-cv:2024AL0005')")
            if action == "egif_detail": client.evaluate("(async()=>{const id=document.querySelector('#egif-record-rows button')?.dataset.recordId; return id ? await window.__es4cRuntime.selectEgifRecord(id) : null})()")
            if action == "esfire_detail": client.evaluate("window.__es4cRuntime.selectFirstRenderedFeature()")
            if action in ("effis_detail", "mobile_detail"): client.evaluate("(()=>{const f=window.__es4cRuntime.getEffisResult().features[0]; return f && window.__es4cRuntime.selectEffisFeature(f);})()")
            if action == "invalidation": client.evaluate("(async()=>{await window.__es4cRuntime.setAnalysisFilter({filter_id:'icv_cause',filter_type:'enum',source:'icv',metric_id:'icv_cause_distribution',value:'lightning',unit:null}); await window.__es4cRuntime.setEgifScope('ES:CCAA:12',{fit:false}); window.__nationalProductShell.sync(); return true})()")
            if action == "mobile_filter": client.evaluate("document.querySelector('#open-filters').click()")
            if action == "mobile_detail": client.evaluate("document.querySelector('[data-detail-card=\"effis\"] [data-detail-minimize]').click()")
            if action == "permalink":
                saved_hash = client.evaluate("location.hash")
                client.command("Page.navigate", {"url": url + saved_hash})
                while not client.evaluate("document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && window.__nationalProductShell?.metrics?.getState()?.result?.status === 'complete' && window.__es4cRuntime.getState().filters.length === 1"):
                    if time.monotonic() > deadline: raise TimeoutError("El filtro no se restauró al recargar")
                    time.sleep(.08)
                reloaded = client.evaluate("window.__es4cRuntime.getState().filters[0].filter_id")
                client.evaluate("history.pushState({filterTest:true},'',location.pathname+location.search)")
                client.evaluate("window.__es4cRuntime.clearAnalysisFilters()")
                client.evaluate("history.back()")
                navigation_deadline = time.monotonic() + 20
                while client.evaluate("window.__es4cRuntime.getState().filters.length") != 1:
                    if time.monotonic() > navigation_deadline: raise TimeoutError("Back no restauró el filtro")
                    time.sleep(.05)
                time.sleep(.75)
                back = client.evaluate("window.__es4cRuntime.getState().filters[0].filter_id")
                client.evaluate("history.forward()")
                navigation_deadline = time.monotonic() + 20
                while client.evaluate("window.__es4cRuntime.getState().filters.length") != 0:
                    if time.monotonic() > navigation_deadline: raise TimeoutError("Forward no restauró la ausencia de filtro")
                    time.sleep(.05)
                time.sleep(.75)
                forward = client.evaluate("window.__es4cRuntime.getState().filters.length")
                client.evaluate("history.back()")
                navigation_deadline = time.monotonic() + 20
                while client.evaluate("window.__es4cRuntime.getState().filters.length") != 1:
                    if time.monotonic() > navigation_deadline: raise TimeoutError("Segundo Back no restauró el filtro")
                    time.sleep(.05)
                client.evaluate("window.__filterPermalinkSmoke=%s" % json.dumps({"reload": reloaded, "back": back, "forward_count": forward}))
            time.sleep(.25)
            return client.evaluate(r'''(() => {
              const s=window.__es4cRuntime.getState(); const metric=window.__nationalProductShell.metrics.getState();
              const rect=q=>{const r=document.querySelector(q)?.getBoundingClientRect();return r?{top:r.top,bottom:r.bottom,height:r.height}:null};
              return {state:s, filters:window.__nationalProductShell.filters.getState(), cards:[...document.querySelectorAll('#summary-cards .summary-card')].map(x=>x.innerText),
                summary_status:document.querySelector('#summary-loading-status').textContent, histogram_status:document.querySelector('#histogram-status').textContent,
                chips:[...document.querySelectorAll('.filter-chip')].map(x=>x.textContent), filter_status:document.querySelector('#filter-status').textContent,
                egif:window.__es4cRuntime.getEgifResult(), icv_metrics:window.__es4cRuntime.getIcvResult().metrics, effis_metrics:window.__es4cRuntime.getEffisResult().metrics,
                detail:{egif:document.querySelector('#egif-detail')?.innerText,icv:document.querySelector('#icv-detail')?.innerText,effis:document.querySelector('#effis-detail')?.innerText,esfire:document.querySelector('[data-detail-card="esfire30"]')?.innerText},
                coverage:document.querySelector('#human-coverage-message').textContent, panel_rect:rect('#filter-panel'), panel_hidden:document.querySelector('#filter-panel').hidden,
                effis_minimized:document.querySelector('#effis-detail')?.classList.contains('is-minimized'), hash:location.hash,
                permalink_smoke:window.__filterPermalinkSmoke || null,
                bootstrap_error:document.querySelector('#national-bootstrap-error').textContent, runtime_errors:JSON.parse(document.querySelector('#runtime-test-output').textContent).errors || [],
                metric_mode:(metric.result.territory.source_summaries||[]).map(x=>[x.source_id,x.filtered_summary_mode])};
            })()''')
        finally:
            if client: client.close()
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            time.sleep(.25)


def validate(runs: list[dict]) -> list[str]:
    failures = []
    rows = {row["scenario"]: row for row in runs}
    for row in runs:
        if row.get("bootstrap_error") or row.get("runtime_errors"): failures.append(f"{row['scenario']}: errores de runtime")
    for name in ("spain_egif_500", "galicia_egif_gif", "gva_icv_min", "gva_icv_cause", "gva_zero", "elx_effis"):
        if not rows[name]["state"]["filters"] or not rows[name]["chips"]: failures.append(f"{name}: filtro/chip ausente")
        if "filter" not in rows[name]["hash"] and "es4c-state-v1" not in rows[name]["hash"]: failures.append(f"{name}: estado no serializado")
    if rows["gva_zero"]["icv_metrics"]["records"] != 0 or "0" not in " ".join(rows["gva_zero"]["cards"]): failures.append("gva_zero: cero filtrado incorrecto")
    if rows["invalidation"]["state"]["filters"] or "retirado" not in rows["invalidation"]["filter_status"]: failures.append("invalidation: filtro contextual no retirado")
    if rows["permalink"]["permalink_smoke"] != {"reload": "icv_cause", "back": "icv_cause", "forward_count": 0}: failures.append("permalink: reload/back-forward incorrectos")
    if "2 perímetros" not in (rows["gva_2024_detail"]["detail"]["icv"] or ""): failures.append("gva_2024_detail: caso 1:N ausente")
    if "Registro de incendio" not in (rows["galicia_egif_detail"]["detail"].get("egif") or ""): failures.append("galicia_egif_detail: ficha ausente")
    if "Perímetro Landsat" not in (rows["galicia_esfire_detail"]["detail"]["esfire"] or ""): failures.append("galicia_esfire_detail: ficha ausente")
    if "Área cartografiada" not in (rows["elx_effis"]["detail"]["effis"] or ""): failures.append("elx_effis: ficha humana incompleta")
    if "no de perímetros cartografiados" not in rows["canarias"]["coverage"]: failures.append("canarias: ausencia de cobertura incorrecta")
    if rows["mobile_filters"]["panel_hidden"] or not rows["mobile_filters"]["panel_rect"]: failures.append("mobile_filters: drawer no visible")
    if not rows["mobile_detail"]["effis_minimized"]: failures.append("mobile_detail: ficha no minimizable")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--chrome", default="/usr/bin/google-chrome"); parser.add_argument("--all", action="store_true"); parser.add_argument("--scenario", action="append", choices=tuple(SCENARIOS)); parser.add_argument("--output", type=Path, default=Path("/tmp/es4e3c1-smokes.json")); parser.add_argument("--check", action="store_true"); parser.add_argument("--timeout", type=int, default=150); args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8")); failures = validate(payload["runs"]); print(json.dumps({"valid": not failures, "failures": failures, "runs": len(payload["runs"])})); return 0 if not failures else 1
    selected = list(SCENARIOS) if args.all else (args.scenario or ["gva_icv_cause"])
    with tempfile.TemporaryDirectory(prefix="atlas-e3c1-site-") as directory:
        site = temporary_site(Path(directory)); server, _range = start_server(root=site)
        try:
            runs = []
            for name in selected:
                query, device, action = SCENARIOS[name]; url = f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(query)}"; row = observe(args.chrome, url, device, action, args.timeout); row.update({"scenario": name, "device": device}); runs.append(row)
        finally: server.shutdown(); server.server_close()
    failures = validate(runs) if args.all else []
    payload = {"phase": "ES-4E3C1", "runs": runs, "valid": not failures, "failures": failures}; args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(json.dumps({"valid": not failures, "failures": failures, "runs": len(runs), "output": str(args.output)})); return 0 if not failures else 1


if __name__ == "__main__": raise SystemExit(main())
