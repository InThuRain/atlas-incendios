#!/usr/bin/env python3
"""Smokes dirigidos E3B2: métricas e histograma sobre runtime local aceptado."""
from __future__ import annotations

import argparse
import json
import os
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
BUILDER = ROOT / "scripts/build_national_frontend.py"
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import CDPClient  # noqa: E402
sys.path.insert(0, str(ROOT / "prototypes/es4c"))
from run_smoke import start_server  # noqa: E402


SCENARIOS = {
    "spain_full": ({"smoke": "spain", "from": 1968, "to": 2026, "egif_scope": "ES"}, "desktop"),
    "spain_1975": ({"smoke": "spain", "from": 1975, "to": 1975, "egif_scope": "ES"}, "desktop"),
    "spain_1995": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop"),
    "galicia_1995": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12"}, "desktop"),
    "ourense_1995": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "province_select": "ES:PROV:32"}, "desktop"),
    "gva_1995": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "desktop"),
    "gva_2024": ({"smoke": "pais_valencia", "from": 2024, "to": 2024, "egif_scope": "ES:CCAA:10"}, "desktop"),
    "gva_2026": ({"smoke": "pais_valencia", "from": 2026, "to": 2026, "egif_scope": "ES:CCAA:10"}, "desktop"),
    "elx_2025": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "desktop"),
    "cangas": ({"smoke": "spain", "from": 1985, "to": 2021, "egif_scope": "ES:CCAA:03", "province_select": "ES:PROV:33", "municipality_select": "ES:MUN:33011"}, "desktop"),
    "canarias_1995": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:05"}, "desktop"),
    "mobile_spain_1995": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "mobile"),
    "mobile_elx_2025": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile"),
}


def temporary_site(directory: Path) -> Path:
    if not BASELINE_DATA.is_dir() or not SUMMARY.is_dir():
        raise FileNotFoundError("Faltan el artifact técnico D4B o national-ux-summary-v1")
    site = directory / "site"
    result = subprocess.run([sys.executable, str(BUILDER), "--output", str(site)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    data = site / "data"
    data.mkdir()
    for child in BASELINE_DATA.iterdir():
        (data / child.name).symlink_to(child, target_is_directory=child.is_dir())
    summary_parent = data / "summary"
    summary_parent.mkdir()
    (summary_parent / "national-ux-summary-v1").symlink_to(SUMMARY, target_is_directory=True)
    return site


def observe(chrome: str, url: str, device: str, timeout: int = 150, interaction=None) -> dict:
    size = "390,844" if device == "mobile" else "1440,900"
    with tempfile.TemporaryDirectory(prefix="atlas-e3b2-cdp-") as profile:
        process = subprocess.Popen([
            chrome, "--headless", "--no-sandbox", "--disable-gpu", "--enable-precise-memory-info",
            "--remote-debugging-port=0", "--remote-allow-origins=*", "--user-data-dir=" + profile,
            "--window-size=" + size, "about:blank",
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
                client.command("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
            started = time.monotonic()
            client.command("Page.navigate", {"url": url})
            while True:
                complete = client.evaluate("document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && window.__nationalProductShell?.metrics?.getState()?.result?.status === 'complete'")
                if complete:
                    break
                if time.monotonic() > deadline:
                    diagnostic = client.evaluate("({bootstrap:document.querySelector('#national-bootstrap-error')?.textContent, shell:Boolean(window.__nationalProductShell), metric:window.__nationalProductShell?.metrics?.getState?.(), runtimeComplete:document.querySelector('#runtime-test-output')?.dataset.complete})")
                    raise TimeoutError(f"El summary E3B2 no quedó visible: {diagnostic}")
                time.sleep(.08)
            visible_ms = (time.monotonic() - started) * 1000
            time.sleep(.25)
            client.evaluate("document.querySelector('#copy-state-link').click()")
            time.sleep(.15)
            expression = r'''(() => {
              const runtime = JSON.parse(document.querySelector('#runtime-test-output').textContent);
              const metricState = window.__nationalProductShell.metrics.getState();
              const rect = selector => { const r=document.querySelector(selector)?.getBoundingClientRect(); return r?{top:r.top,bottom:r.bottom,width:r.width,height:r.height}:null; };
              const bars = [...document.querySelectorAll('#histogram-chart .histogram-bar')];
              const year = y => { const b=bars.find(row=>row.dataset.year===String(y)); return b?{status:[...b.classList].find(x=>x.startsWith('histogram-bar--'))?.replace('histogram-bar--',''),label:b.getAttribute('aria-label'),in_range:b.classList.contains('is-in-range')}:null; };
              return {
                runtime, state:window.__es4cRuntime.getState(),
                cards:[...document.querySelectorAll('#summary-cards .summary-card')].map(node=>node.innerText),
                summary_status:document.querySelector('#summary-loading-status').textContent,
                histogram_status:document.querySelector('#histogram-status').textContent,
                selected_series:metricState.selected_series_id,
                tabs:[...document.querySelectorAll('#histogram-series-tabs button')].map(node=>({id:node.dataset.metricId,selected:node.getAttribute('aria-selected'),text:node.textContent})),
                years:{1975:year(1975),1995:year(1995),2024:year(2024),2025:year(2025),2026:year(2026)},
                asset:metricState.result.asset, telemetry:metricState.telemetry,
                histogram_bars:bars.length, accessible_rows:document.querySelectorAll('#histogram-data-body tr').length,
                map_rect:rect('.map-region'), summary_rect:rect('.summary-section'), viewport:{width:innerWidth,height:innerHeight},
                copy_status:document.querySelector('#copy-state-status').textContent,
                bootstrap_error:document.querySelector('#national-bootstrap-error').textContent,
              };
            })()'''
            result = client.evaluate(expression)
            result["summary_visible_ms"] = visible_ms
            if interaction == "year_click":
                client.evaluate("document.querySelector('#histogram-chart [data-year=\"1995\"]').click()")
                interaction_deadline = time.monotonic() + 15
                while client.evaluate("window.__es4cRuntime.getState().from !== 1995 || window.__es4cRuntime.getState().to !== 1995"):
                    if time.monotonic() > interaction_deadline:
                        raise TimeoutError("Click de año no actualizó el estado")
                    time.sleep(.05)
                time.sleep(.15)
                result["year_click"] = client.evaluate("({from:window.__es4cRuntime.getState().from,to:window.__es4cRuntime.getState().to,highlight:document.querySelector('#histogram-chart [data-year=\"1995\"]').classList.contains('is-in-range')})")
            if interaction == "series_switch":
                client.evaluate("window.__nationalProductShell.metrics.selectSeries('esfire30_perimeter_count')")
                result["series_switch"] = client.evaluate("({selected:window.__nationalProductShell.metrics.getState().selected_series_id,aria:document.querySelector('[data-metric-id=\"esfire30_perimeter_count\"]').getAttribute('aria-selected')})")
            return result
        finally:
            if client:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
            time.sleep(.25)


def validate(runs: list[dict]) -> list[str]:
    failures = []
    by_name = {row["scenario"]: row for row in runs}
    for row in runs:
        name = row["scenario"]
        if row.get("bootstrap_error"):
            failures.append(f"{name}: bootstrap: {row['bootstrap_error']}")
        if row.get("runtime", {}).get("errors"):
            failures.append(f"{name}: runtime errors: {row['runtime']['errors']}")
        if row.get("histogram_bars") != 59 or row.get("accessible_rows") != 59:
            failures.append(f"{name}: eje anual/accesible incompleto")
        if not row.get("cards") or len(row["cards"]) > 4:
            failures.append(f"{name}: tarjetas fuera de contrato")
        if row.get("asset", {}).get("path") is None:
            failures.append(f"{name}: asset summary no identificado")
    expected_series = {
        "spain_full": "egif_record_count", "spain_1975": "egif_record_count", "spain_1995": "egif_record_count",
        "galicia_1995": "egif_record_count", "ourense_1995": "egif_record_count", "gva_1995": "icv_fire_record_count",
        "gva_2024": "icv_fire_record_count", "gva_2026": "effis_perimeter_count", "elx_2025": "effis_perimeter_count",
    }
    for name, metric in expected_series.items():
        if by_name[name]["selected_series"] != metric:
            failures.append(f"{name}: serie {by_name[name]['selected_series']} != {metric}")
    if by_name["spain_full"].get("year_click") != {"from": 1995, "to": 1995, "highlight": True}:
        failures.append("spain_full: click de año no coordinó state/highlight")
    if by_name["gva_1995"].get("series_switch") != {"selected": "esfire30_perimeter_count", "aria": "true"}:
        failures.append("gva_1995: cambio explícito de serie no funcionó")
    expected_text = {
        "spain_full": ["646.887", "119.498"], "spain_1975": ["4.128"], "spain_1995": ["25.557", "5.035"],
        "gva_1995": ["467", "ICV", "EGIF"], "gva_2024": ["472", "ICV"], "gva_2026": ["16", "EFFIS"],
        "elx_2025": ["1", "EFFIS"],
    }
    for name, needles in expected_text.items():
        haystack = " ".join(by_name[name]["cards"])
        for needle in needles:
            if needle not in haystack:
                failures.append(f"{name}: falta {needle} en tarjetas")
    if by_name["spain_1975"]["years"]["1975"]["status"] != "value" or "4.128" not in by_name["spain_1975"]["years"]["1975"]["label"]:
        failures.append("spain_1975: barra EGIF incorrecta")
    if by_name["canarias_1995"]["selected_series"] != "egif_record_count" or "ESFire30" in " ".join(by_name["canarias_1995"]["cards"]):
        failures.append("canarias_1995: ausencia ESFire30 mal presentada")
    if "snapshot de 19/08/2026" not in by_name["gva_2026"]["summary_status"]:
        failures.append("gva_2026: falta aviso snapshot")
    for name in ("mobile_spain_1995", "mobile_elx_2025"):
        row = by_name[name]
        if row["map_rect"]["top"] > 80 or row["map_rect"]["bottom"] > row["viewport"]["height"] * .62:
            failures.append(f"{name}: mapa desplazado del primer viewport")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), action="append")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("/tmp/es4e3b2-smokes.json"))
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload["runs"])
        print(json.dumps({"valid": not failures, "failures": failures, "runs": len(payload["runs"])}))
        return 0 if not failures else 1
    selected = list(SCENARIOS) if args.all else (args.scenario or ["spain_1995"])
    with tempfile.TemporaryDirectory(prefix="atlas-e3b2-site-") as directory:
        site = temporary_site(Path(directory))
        server, range_state = start_server(root=site)
        try:
            runs = []
            for name in selected:
                config, device = SCENARIOS[name]
                url = f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(config)}"
                interaction = "year_click" if name == "spain_full" else "series_switch" if name == "gva_1995" else None
                observed = observe(args.chrome, url, device, timeout=args.timeout, interaction=interaction)
                observed.update({"scenario": name, "device": device})
                runs.append(observed)
        finally:
            server.shutdown(); server.server_close()
    failures = validate(runs) if args.all else []
    payload = {"phase": "ES-4E3B2", "runs": runs, "range": range_state.payload(), "valid": not failures, "failures": failures}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "runs": len(runs), "output": str(args.output)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
