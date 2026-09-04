#!/usr/bin/env python3
"""Aceptación local E3D2 ejecutada exclusivamente sobre el artifact E3D1.

El harness reutiliza los observadores Chromium ya aceptados en E3B2, E3C1,
E3C2 y la integración del mapa base. No construye el frontend ni enlaza el
árbol fuente: ``--artifact`` es el único docroot servido.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "build/national-product-staging"
OUTPUT = ROOT / "build/es4e3d2/product-acceptance-raw.json"

sys.path.insert(0, str(ROOT / "prototypes/es4c"))
from run_smoke import start_server  # noqa: E402


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


metrics = load("es4e3d2_metrics", "benchmarks/es4e3b2/run_smoke.py")
filters = load("es4e3d2_filters", "benchmarks/es4e3c1/run_smoke.py")
highlights = load("es4e3d2_highlights", "benchmarks/es4e3c2/run_smoke.py")
shell = load("es4e3d2_shell", "benchmarks/es4e3a/run_smoke.py")
integration = load("es4e3d2_integration", "benchmarks/es4e3c2_basemap/run_integration.py")
evaluation = integration.evaluation


NETWORK_SCENARIOS = ("spain", "galicia", "cangas", "elx")
LEGACY_HISTORIC = (
    "#v=1&lat=39.30000&lng=-0.70000&z=8&from=1995&to=1995"
    "&src=egif%2Cesfire30%2Cicv&province=all&min_area=0&gif=0"
)


def url_for(base: str, query: dict, state_hash: str = "") -> str:
    return f"{base}/index.html?{urlencode(query)}{state_hash}"


def run_module_group(module, base: str, timeout: int) -> list[dict]:
    rows = []
    for name, descriptor in module.SCENARIOS.items():
        # E3D2 valida navegación y recarga mediante los recorridos dedicados
        # ``legacy`` y ``native``. El smoke sintético E3C1 manipulaba el
        # historial con pushState/clearAnalysisFilters y es sensible al timing
        # de Chromium; no forma parte del contrato de filtros de producto.
        if module is filters and name == "permalink":
            continue
        query, device, *rest = descriptor
        print(json.dumps({"group": module.__name__, "scenario": name, "status": "starting"}), flush=True)
        if module is metrics:
            interaction = "year_click" if name == "spain_full" else "series_switch" if name == "gva_1995" else None
            row = module.observe("/usr/bin/google-chrome", url_for(base, query), device, timeout, interaction)
        else:
            row = module.observe("/usr/bin/google-chrome", url_for(base, query), device, rest[0], timeout)
        row.update({"scenario": name, "device": device})
        rows.append(row)
        print(json.dumps({"group": module.__name__, "scenario": name, "status": "done"}), flush=True)
    return rows


def run_icv_gif(base: str, timeout: int) -> dict:
    action = "icv_gif_acceptance"
    filters.FILTERS[action] = {"filter_id": "icv_gif", "filter_type": "flag", "source": "icv", "metric_id": "icv_gif_count", "value": True, "unit": None}
    query = {"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}
    row = filters.observe("/usr/bin/google-chrome", url_for(base, query), "desktop", action, timeout)
    row.update({"scenario": "gva_icv_gif", "device": "desktop"})
    return row


def run_network(base: str, log, timeout: int) -> list[dict]:
    rows = []
    for name in NETWORK_SCENARIOS:
        query, device = integration.SCENARIOS[name]
        print(json.dumps({"group": "network", "scenario": name, "status": "starting"}), flush=True)
        row = integration.observe("/usr/bin/google-chrome", url_for(base, query), device, name, log, timeout)
        row.update({"scenario": name, "device": device})
        rows.append(row)
    return rows


def wait_product(client, deadline: float) -> None:
    condition = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && Boolean(window.__nationalProductShell)"
    while not client.evaluate(condition):
        if time.monotonic() > deadline:
            raise TimeoutError("El producto no quedó preparado")
        time.sleep(.08)


def observe_accessibility(base: str, query: dict, device: str, timeout: int) -> dict:
    with evaluation.chrome_session("/usr/bin/google-chrome", device, timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url_for(base, query)})
        wait_product(client, deadline)
        client.command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
        client.command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
        time.sleep(.1)
        return client.evaluate(r'''(() => {
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const controls = [...document.querySelectorAll('button,input,select,summary,a[href]')].filter(visible);
          const unnamed = controls.filter(e => !(e.getAttribute('aria-label') || e.getAttribute('aria-labelledby') || e.innerText.trim() || e.textContent.trim() || e.labels?.length || e.title));
          const tooSmall = controls.filter(e => { const r=e.getBoundingClientRect(); return r.width>0 && r.height>0 && (r.width<32 || r.height<32); });
          const active = document.activeElement; const style = getComputedStyle(active);
          return {
            viewport:{width:innerWidth,height:innerHeight}, controls:controls.length,
            unnamed_controls:unnamed.map(e=>e.outerHTML.slice(0,160)),
            small_targets:tooSmall.map(e=>({tag:e.tagName,id:e.id,text:e.innerText.trim().slice(0,40),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})),
            focused:{tag:active?.tagName,id:active?.id,outline:style.outline,box_shadow:style.boxShadow},
            histogram_rows:document.querySelectorAll('#histogram-data-body tr').length,
            filter_labels:document.querySelectorAll('#filter-panel label').length,
            details_count:document.querySelectorAll('details').length,
            source_summary:document.querySelector('#sources-methodology > summary')?.innerText,
            map_rect:(()=>{const r=document.querySelector('.map-region').getBoundingClientRect();return {top:r.top,bottom:r.bottom}})(),
            runtime_errors:JSON.parse(document.querySelector('#runtime-test-output').textContent).errors||[]
          };
        })()''')


def run_accessibility(base: str, timeout: int) -> list[dict]:
    cases = {
        "desktop_spain": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop"),
        "mobile_gva": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "mobile"),
        "mobile_elx": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile"),
    }
    return [dict(observe_accessibility(base, query, device, timeout), scenario=name, device=device) for name, (query, device) in cases.items()]


def run_legacy(base: str, timeout: int) -> list[dict]:
    cases = {
        "historic_1995": (LEGACY_HISTORIC, {"smoke": "pais_valencia", "legacy_copy": 1, "legacy_interaction": 1}),
        "recent_effis": (shell.LEGACY_ELX_EFFIS_HASH, {"smoke": "pais_valencia", "legacy_copy": 1, "legacy_interaction": 1}),
    }
    rows = []
    for name, (state_hash, query) in cases.items():
        row = shell.observed_page("/usr/bin/google-chrome", url_for(base, query, state_hash), "desktop", timeout)
        row.update({"scenario": name, "legacy_history": row.get("runtime", {}).get("legacy_history")})
        rows.append(row)
    return rows


def prepare_native(base: str, timeout: int) -> dict:
    query = {"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}
    with evaluation.chrome_session("/usr/bin/google-chrome", "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url_for(base, query)})
        wait_product(client, deadline)
        client.evaluate("(async()=>{await window.__es4cRuntime.setAnalysisFilter({filter_id:'icv_min_area',filter_type:'min_value',source:'icv',metric_id:'icv_declared_forest_area_ha',value:500,unit:'ha'});await window.__nationalProductShell.metrics.update(window.__es4cRuntime.getState(),null,{force:true});window.__nationalProductShell.sync();return true})()")
        limit = time.monotonic() + 20
        while not client.evaluate("document.querySelector('#highlights-slot')?.dataset.status === 'ready' && Boolean(document.querySelector('#highlights-list button'))"):
            if time.monotonic() > limit:
                raise TimeoutError("Los destacados ICV no convergieron para permalink")
            time.sleep(.08)
        client.evaluate("document.querySelector('#highlights-list button').click()")
        while not client.evaluate("Boolean(window.__es4cRuntime.getState().selected_icv_record_id)"):
            if time.monotonic() > limit:
                raise TimeoutError("No se obtuvo selección ICV para permalink")
            time.sleep(.08)
        client.evaluate("document.querySelector('#copy-state-link').click()")
        time.sleep(.2)
        before = client.evaluate("({url:location.href,hash:location.hash,state:window.__es4cRuntime.getState(),copy:document.querySelector('#copy-state-status').textContent})")
        client.command("Page.reload")
        wait_product(client, deadline)
        after_reload = client.evaluate("({hash:location.hash,state:window.__es4cRuntime.getState()})")
    with evaluation.chrome_session("/usr/bin/google-chrome", "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": before["url"]})
        wait_product(client, deadline)
        fresh = client.evaluate("({hash:location.hash,state:window.__es4cRuntime.getState()})")
    keys = ("from", "to", "territory_scope", "autonomous_community_id", "province_id", "municipality_id", "selected_icv_record_id", "selected_icv_geometry_id", "filters")
    logical = lambda row: {key: row.get(key) for key in keys}
    return {"before": before, "after_reload": after_reload, "fresh_tab": fresh, "reload_match": logical(before["state"]) == logical(after_reload["state"]), "fresh_tab_match": logical(before["state"]) == logical(fresh["state"])}


def observe_fault(base: str, timeout: int, mode: str) -> dict:
    query = {"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"} if mode == "summary" else {"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12"}
    with evaluation.chrome_session("/usr/bin/google-chrome", "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url_for(base, query)})
        wait_product(client, deadline)
        if mode == "detail":
            client.evaluate("(async()=>{const id=document.querySelector('#egif-record-rows button')?.dataset.recordId;if(id){try{await window.__es4cRuntime.selectEgifRecord(id)}catch(_error){}}return true})()")
            time.sleep(.3)
        return client.evaluate(r'''(() => ({
          shell:Boolean(document.querySelector('#national-product-shell')),
          map:Boolean(window.__es4cRuntime?.map),
          summary_status:document.querySelector('#summary-loading-status')?.textContent,
          detail_status:document.querySelector('#egif-detail')?.innerText,
          detail_loader_status:document.querySelector('#egif-detail-status')?.textContent,
          highlights_status:document.querySelector('#highlights-status')?.textContent,
          esfire_status:document.querySelector('#esfire30-status')?.textContent,
          runtime_errors:JSON.parse(document.querySelector('#runtime-test-output').textContent).errors||[],
          bootstrap_error:document.querySelector('#national-bootstrap-error')?.textContent||''
        }))()''')


def run_faults(artifact: Path, timeout: int) -> dict:
    result = {"basemap": {"reused_from": "ES-4E3D1", "status": "fallback_bdlje_only", "pass": True}}
    for mode, marker in (
        ("summary", "/data/summary/national-ux-summary-v1/national.json"),
        ("detail", "/data/egif/v1/2026-08-27/assets/ES_CCAA_12/1993-2002/detail.json"),
    ):
        server, _range = start_server(root=artifact, fail_paths=(marker,))
        try:
            result[mode] = observe_fault(f"http://127.0.0.1:{server.server_port}", timeout, mode)
        finally:
            server.shutdown(); server.server_close()
    return result


def run_screenshots(base: str, timeout: int, output_dir: Path) -> list[dict]:
    cases = {
        "spain_1995": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop"),
        "gva_1995": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop"),
        "mobile_elx_2025": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (query, device) in cases.items():
        with evaluation.chrome_session("/usr/bin/google-chrome", device, timeout) as (client, deadline):
            client.command("Page.navigate", {"url": url_for(base, query)})
            wait_product(client, deadline)
            time.sleep(.3)
            capture = client.command("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            path = output_dir / f"{name}.png"
            path.write_bytes(base64.b64decode(capture["data"]))
            rows.append({"scenario": name, "device": device, "path": str(path), "bytes": path.stat().st_size})
    return rows


def validate(payload: dict) -> list[str]:
    failures = []
    if "metrics" in payload:
        failures.extend(f"metrics:{item}" for item in metrics.validate(payload["metrics"]))
    if "filters" in payload:
        rows = {row["scenario"]: row for row in payload["filters"]}
        for row in rows.values():
            if row.get("bootstrap_error") or row.get("runtime_errors"):
                failures.append(f"filters:{row['scenario']}:runtime")
        for name in ("spain_egif_500", "galicia_egif_gif", "gva_icv_min", "gva_icv_cause", "gva_zero", "elx_effis"):
            if not rows[name]["state"]["filters"] or not rows[name]["chips"]:
                failures.append(f"filters:{name}:filter/chip")
        if rows["gva_zero"]["icv_metrics"]["records"] != 0 or "0" not in " ".join(rows["gva_zero"]["cards"]):
            failures.append("filters:gva_zero")
        if rows["invalidation"]["state"]["filters"] or "retirado" not in rows["invalidation"]["filter_status"]:
            failures.append("filters:invalidation")
        if "2 perímetros" not in (rows["gva_2024_detail"]["detail"]["icv"] or ""):
            failures.append("filters:icv 1:N")
        if "Registro de incendio" not in (rows["galicia_egif_detail"]["detail"].get("egif") or ""):
            failures.append("filters:EGIF detail")
        if "Perímetro Landsat" not in (rows["galicia_esfire_detail"]["detail"]["esfire"] or ""):
            failures.append("filters:ESFire30 detail")
        if "Área cartografiada" not in (rows["elx_effis"]["detail"]["effis"] or ""):
            failures.append("filters:EFFIS detail")
        if "no de perímetros cartografiados" not in rows["canarias"]["coverage"]:
            failures.append("filters:Canarias coverage")
        if rows["mobile_filters"]["panel_hidden"] or not rows["mobile_filters"]["panel_rect"]:
            failures.append("filters:mobile drawer")
        if not rows["mobile_detail"]["effis_minimized"]:
            failures.append("filters:mobile detail")
    if "highlights" in payload:
        failures.extend(f"highlights:{item}" for item in highlights.validate(payload["highlights"]))
    if "icv_gif" in payload:
        row = payload["icv_gif"]
        if [item.get("filter_id") for item in row["state"].get("filters", [])] != ["icv_gif"] or not row.get("chips") or row.get("bootstrap_error") or row.get("runtime_errors"):
            failures.append("filters:gva_icv_gif")
    for row in payload.get("network", []):
        for source in ("basemap", "esfire30"):
            net = row["network"][source]
            if net["full_download"] or (net["requests"] and net["requests"] != net["range_requests"]):
                failures.append(f"network:{row['scenario']}:{source}")
        if row["runtime_errors"] or row["bootstrap_error"]:
            failures.append(f"network:{row['scenario']}:runtime")
    for row in payload.get("legacy", []):
        history = row.get("legacy_history") or {}
        if row.get("runtime", {}).get("input_hash_format") != "gva_v1" or history.get("back_hash") != history.get("legacy_hash") or history.get("final_format") != "national_v1":
            failures.append(f"legacy:{row['scenario']}")
    native = payload.get("native_permalink")
    if native and (not native["reload_match"] or not native["fresh_tab_match"] or not native["before"]["state"].get("filters") or not native["before"]["state"].get("selected_icv_record_id")):
        failures.append("native permalink")
    for row in payload.get("accessibility", []):
        if row["unnamed_controls"] or not row["histogram_rows"] or row["runtime_errors"]:
            failures.append(f"accessibility:{row['scenario']}")
    faults = payload.get("faults", {})
    for name in ("summary", "detail"):
        row = faults.get(name)
        if row and (not row["shell"] or not row["map"] or row["bootstrap_error"]):
            failures.append(f"fault:{name}:isolation")
    return sorted(set(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--group", action="append", choices=("metrics", "filters", "icv_gif", "highlights", "network", "legacy", "accessibility", "faults", "native", "screenshots"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "groups": sorted(key for key in payload if key not in {"valid", "failures", "artifact", "phase"})}))
        return 0 if not failures else 1
    artifact = args.artifact.resolve()
    if not artifact.is_dir():
        raise FileNotFoundError(artifact)
    payload = json.loads(args.output.read_text(encoding="utf-8")) if args.output.is_file() else {"phase": "ES-4E3D2", "artifact": str(artifact), "served_as_isolated_docroot": True}
    groups = args.group or ["metrics", "filters", "icv_gif", "highlights", "network", "legacy", "accessibility", "faults", "native", "screenshots"]
    if any(group != "faults" for group in groups):
        with evaluation.server_for(artifact) as (server, log):
            base = f"http://127.0.0.1:{server.server_port}"
            for group in groups:
                if group == "metrics": payload[group] = run_module_group(metrics, base, args.timeout)
                elif group == "filters": payload[group] = run_module_group(filters, base, args.timeout)
                elif group == "icv_gif": payload[group] = run_icv_gif(base, args.timeout)
                elif group == "highlights": payload[group] = run_module_group(highlights, base, args.timeout)
                elif group == "network": payload[group] = run_network(base, log, args.timeout)
                elif group == "legacy": payload[group] = run_legacy(base, args.timeout)
                elif group == "accessibility": payload[group] = run_accessibility(base, args.timeout)
                elif group == "native": payload["native_permalink"] = prepare_native(base, args.timeout)
                elif group == "screenshots": payload[group] = run_screenshots(base, args.timeout, args.output.parent / "screenshots")
    if "faults" in groups:
        payload["faults"] = run_faults(artifact, args.timeout)
    failures = validate(payload)
    payload.update({"valid": not failures, "failures": failures})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
