#!/usr/bin/env python3
"""Smokes locales dirigidos de la integración productiva Protomaps z12.

Construye sólo el frontend ligero, enlaza los assets derivados ya existentes
y separa telemetría Range de basemap y ESFire30. No crea un artifact Pages.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as evaluation  # noqa: E402

BUILDER = ROOT / "scripts/build_national_frontend.py"
CONTRACT = json.loads((ROOT / "config/national-basemap-protomaps-20260902-z12.json").read_text(encoding="utf-8"))
BASEMAP = ROOT / CONTRACT["pmtiles"]["source_path"]
GLYPHS = [(descriptor, ROOT / descriptor["source_path"]) for descriptor in CONTRACT["glyphs"]["files"]]
OUTPUT = ROOT / "build/es4e3c2-basemap/integration-results.json"

SCENARIOS = {
    "spain": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES", "territory_restore": "1"}, "desktop"),
    "galicia": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "territory_select": "ES:CCAA:12", "territory_restore": "1"}, "desktop"),
    "ourense": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "province_select": "ES:PROV:32", "territory_restore": "1"}, "desktop"),
    "cangas": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:03", "province_select": "ES:PROV:33", "municipality_select": "ES:MUN:33011", "territory_restore": "1"}, "desktop"),
    "gva_1995": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10", "territory_restore": "1"}, "desktop"),
    "elx": ({"smoke": "pais_valencia", "from": 1993, "to": 2002, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065", "territory_restore": "1"}, "desktop"),
    "canarias": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:05", "territory_select": "ES:CCAA:05", "territory_restore": "1"}, "desktop"),
    "mobile_spain": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES", "territory_restore": "1"}, "mobile"),
    "mobile_elx": ({"smoke": "pais_valencia", "from": 1993, "to": 2002, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065", "territory_restore": "1"}, "mobile"),
}


def build_site(directory: Path, include_basemap: bool) -> Path:
    site = directory / ("with-basemap" if include_basemap else "fallback")
    result = subprocess.run([sys.executable, str(BUILDER), "--output", str(site)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    data = site / "data"
    data.mkdir()
    for child in evaluation.BASELINE_DATA.iterdir():
        (data / child.name).symlink_to(child, target_is_directory=child.is_dir())
    for category, source in (("summary", evaluation.SUMMARY), ("highlights", evaluation.HIGHLIGHTS)):
        parent = data / category
        parent.mkdir(exist_ok=True)
        target = parent / source.name
        if not target.exists():
            target.symlink_to(source, target_is_directory=True)
    if include_basemap:
        archive = site / CONTRACT["pmtiles"]["runtime_path"]
        archive.parent.mkdir(parents=True)
        archive.symlink_to(BASEMAP)
        for descriptor, source in GLYPHS:
            glyph = site / CONTRACT["glyphs"]["runtime_template"].replace("{fontstack}", CONTRACT["glyphs"]["fontstack"]).replace("{range}", descriptor["range"])
            glyph.parent.mkdir(parents=True, exist_ok=True)
            glyph.symlink_to(source)
    return site


def wait_ready(client, deadline: float, expected_basemap: str) -> None:
    condition = f"document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && window.__atlasBasemapContext?.status === '{expected_basemap}'"
    while not client.evaluate(condition):
        if time.monotonic() > deadline:
            detail = client.evaluate("({basemap:window.__atlasBasemapContext,runtime:document.querySelector('#runtime-test-output')?.textContent,bootstrap:document.querySelector('#national-bootstrap-error')?.textContent})")
            raise TimeoutError(f"La integración no convergió: {detail}")
        time.sleep(.08)
    evaluation.wait_for_map_stable(client, deadline)


def summarize(rows: list[dict]) -> dict:
    basemap = [row for row in rows if row["path"].endswith("/basemap.pmtiles")]
    esfire = [row for row in rows if row["path"].endswith("/esfire30-national-fidelity-territories.pmtiles")]
    glyphs = [row for row in rows if "/fonts/Noto%20Sans%20Regular/" in row["path"] and row["path"].endswith(".pbf")]
    return {
        "basemap": {"requests": len(basemap), "range_requests": sum(row["range"] for row in basemap), "bytes": sum(row["bytes"] for row in basemap), "statuses": sorted({row["status"] for row in basemap}), "full_download": any(row["status"] == 200 and row["bytes"] == CONTRACT["pmtiles"]["bytes"] for row in basemap)},
        "esfire30": {"requests": len(esfire), "range_requests": sum(row["range"] for row in esfire), "bytes": sum(row["bytes"] for row in esfire), "statuses": sorted({row["status"] for row in esfire}), "full_download": any(row["status"] == 200 and row["bytes"] == 63052056 for row in esfire)},
        "glyphs": {"requests": len(glyphs), "bytes": sum(row["bytes"] for row in glyphs), "statuses": sorted({row["status"] for row in glyphs}), "paths": sorted({row["path"] for row in glyphs})},
    }


def observe(chrome: str, url: str, device: str, scenario: str, log, timeout: int) -> dict:
    marker = log.mark()
    started = time.monotonic()
    with evaluation.chrome_session(chrome, device, timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url})
        wait_ready(client, deadline, "ready")
        if scenario in {"gva_1995", "elx"}:
            client.evaluate("(async()=>{await window.__es4cRuntime.setSourceVisibility('esfire30',true);return true})()")
            evaluation.wait_for_map_stable(client, deadline)
        if scenario == "gva_1995":
            client.evaluate("(async()=>{await window.__es4cRuntime.setAnalysisFilter({filter_id:'icv_min_area',filter_type:'min_value',source:'icv',metric_id:'icv_declared_forest_area_ha',value:500,unit:'ha'});await window.__nationalProductShell.metrics.update(window.__es4cRuntime.getState(),null,{force:true});window.__nationalProductShell.sync();return true})()")
            while client.evaluate("document.querySelector('#highlights-slot')?.dataset.status") == "loading":
                if time.monotonic() > deadline:
                    raise TimeoutError("GVA: filtro/destacados no convergieron")
                time.sleep(.05)
            if client.evaluate("Boolean(document.querySelector('#highlights-list button'))"):
                client.evaluate("(()=>{document.querySelector('#highlights-list button').click();return true})()")
        if scenario == "elx":
            client.evaluate("window.__es4cRuntime.selectFirstRenderedFeature()")
        if device == "mobile":
            client.evaluate("(()=>{window.__es4cRuntime.map.panBy([16,8],{duration:0});window.__es4cRuntime.map.zoomTo(window.__es4cRuntime.map.getZoom()+0.1,{duration:0});return true})()")
            evaluation.wait_for_map_stable(client, deadline)
        observed = client.evaluate(r'''(() => {
          const map=window.__es4cRuntime.map; const layers=map.getStyle().layers.map(x=>x.id);
          const rt=JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}');
          const labels=['atlas-context-regions','atlas-context-localities','atlas-context-road-labels'].filter(id=>map.getLayer(id));
          const rendered=labels.flatMap(id=>map.queryRenderedFeatures({layers:[id]}));
          const resources=performance.getEntriesByType('resource').map(x=>x.name);
          return {basemap:window.__atlasBasemapContext,state:window.__es4cRuntime.getState(),layers,map_loaded:map.loaded(),
            rendered_labels:rendered.length,label_examples:[...new Set(rendered.map(x=>x.properties?.name).filter(Boolean))].slice(0,20),
            context:document.querySelector('.map-context')?.innerText||'',attribution:document.querySelector('.map-attribution')?.innerText||'',
            legend:[...document.querySelectorAll('#user-map-legend li')].map(x=>x.textContent),histogram_bars:document.querySelectorAll('#histogram-chart button').length,
            highlight_status:document.querySelector('#highlights-slot')?.dataset.status,filter_ids:(window.__es4cRuntime.getState().filters||[]).map(x=>x.filter_id),
            details:{esfire:document.querySelector('[data-detail-card="esfire30"]')?.innerText||'',icv:document.querySelector('#icv-detail')?.innerText||''},
            viewport:{width:innerWidth,height:innerHeight},map_rect:(()=>{const r=document.querySelector('.map-region').getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height}})(),
            resources,heap:performance.memory?.usedJSHeapSize??null,runtime_errors:rt.errors||[],bootstrap_error:document.querySelector('#national-bootstrap-error')?.textContent||''};
        })()''')
    observed.update({"elapsed_ms": round((time.monotonic() - started) * 1000, 2), "network": summarize(log.since(marker))})
    observed["external_runtime_domains"] = sorted({urlparse(url).hostname for url in observed["resources"] if urlparse(url).hostname not in {None, "127.0.0.1", "localhost"}})
    return observed


def observe_fallback(chrome: str, url: str, log, timeout: int) -> dict:
    marker = log.mark()
    with evaluation.chrome_session(chrome, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url})
        wait_ready(client, deadline, "fallback_bdlje_only")
        result = client.evaluate("(()=>{const map=window.__es4cRuntime.map;const rt=JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}');return {basemap:window.__atlasBasemapContext,bdlje:Boolean(map.getLayer('official-ccaa-territories-fill')),esfire30:Boolean(map.getLayer('esfire30-perimeters')),runtime_errors:rt.errors||[],bootstrap_error:document.querySelector('#national-bootstrap-error').textContent,context:document.querySelector('.map-context').innerText}})()")
    result["network"] = summarize(log.since(marker))
    return result


def validate(payload: dict) -> list[str]:
    failures = []
    for row in payload["runs"]:
        name = row["scenario"]
        network = row["network"]
        if row["basemap"]["status"] != "ready" or row["basemap"]["errors"]:
            failures.append(f"{name}: basemap no ready")
        if network["basemap"]["requests"] < 1 or network["basemap"]["requests"] != network["basemap"]["range_requests"] or network["basemap"]["full_download"]:
            failures.append(f"{name}: Range basemap")
        if network["esfire30"]["requests"] and (network["esfire30"]["requests"] != network["esfire30"]["range_requests"] or network["esfire30"]["full_download"]):
            failures.append(f"{name}: Range ESFire30")
        expected_glyph_paths = {f'/{CONTRACT["glyphs"]["runtime_template"].replace("{fontstack}", CONTRACT["glyphs"]["fontstack"]).replace("{range}", descriptor["range"]).replace(" ", "%20")}' for descriptor, _source in GLYPHS}
        if network["glyphs"]["requests"] < 1 or network["glyphs"]["statuses"] != [200] or not set(network["glyphs"]["paths"]).issubset(expected_glyph_paths):
            failures.append(f"{name}: glyph")
        if row["external_runtime_domains"] or row["runtime_errors"] or row["bootstrap_error"]:
            failures.append(f"{name}: runtime/external error")
        order = row["layers"]
        basemap_last = max(order.index(layer) for layer in row["basemap"]["layer_ids"])
        bdlje = [order.index(layer) for layer in ("official-ccaa-territories-fill", "official-ccaa-territories-selected")]
        fire = order.index("esfire30-perimeters")
        if not (basemap_last < min(bdlje) <= max(bdlje) < fire):
            failures.append(f"{name}: layer ordering")
        if row["histogram_bars"] < 1 or row["highlight_status"] not in {"ready", "empty", "deferred", "inactive"}:
            failures.append(f"{name}: producto")
        if name == "gva_1995" and row["filter_ids"] != ["icv_min_area"]:
            failures.append("gva_1995: filtro ICV")
        if name == "gva_1995" and not (row["state"].get("selected_icv_record_id") or row["state"].get("selected_icv_geometry_id")):
            failures.append("gva_1995: selección/destacado ICV")
        if name == "elx" and (not row["state"].get("selected_geometry_id") or "Perímetro Landsat" not in row["details"]["esfire"]):
            failures.append("elx: selección ESFire30")
        if row["viewport"]["width"] == 390 and (row["map_rect"]["top"] > 80 or row["map_rect"]["bottom"] > 844 * .62):
            failures.append(f"{name}: mapa móvil")
    fallback = payload["fallback"]
    if fallback["basemap"]["status"] != "fallback_bdlje_only" or not fallback["bdlje"] or not fallback["esfire30"] or fallback["runtime_errors"] or fallback["bootstrap_error"]:
        failures.append("fallback BDLJE-only")
    return sorted(set(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8")); failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "runs": len(payload.get("runs", []))})); return 0 if not failures else 1
    with tempfile.TemporaryDirectory(prefix="atlas-basemap-integration-") as temporary:
        root = Path(temporary)
        site = build_site(root, True)
        fallback_site = build_site(root, False)
        runs = []
        with evaluation.server_for(site) as (server, log):
            for name, (query, device) in SCENARIOS.items():
                url = f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(query)}"
                row = observe(args.chrome, url, device, name, log, args.timeout); row.update({"scenario": name, "device": device}); runs.append(row)
                print(json.dumps({"scenario": name, "basemap_bytes": row["network"]["basemap"]["bytes"], "esfire30_bytes": row["network"]["esfire30"]["bytes"], "labels": row["rendered_labels"], "elapsed_ms": row["elapsed_ms"]}), flush=True)
        with evaluation.server_for(fallback_site) as (server, log):
            query = SCENARIOS["spain"][0]
            fallback = observe_fallback(args.chrome, f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(query)}", log, args.timeout)
    payload = {"phase": "ES-4E3C2_BASEMAP_INTEGRATION", "runs": runs, "fallback": fallback}
    failures = validate(payload); payload.update({"valid": not failures, "failures": failures})
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "runs": len(runs), "output": str(args.output)})); return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
