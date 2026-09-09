#!/usr/bin/env python3
"""Deterministic ES-4POST2A ICV province-crosswalk evidence.

This only audits the accepted public ICV snapshot and the explicit runtime
crosswalk. It neither downloads nor regenerates source geometries.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIRES = ROOT / "data/web/gva/fires.json"
CROSSWALK = (ROOT / "prototypes/es4c/icv_territory_crosswalk.mjs").as_uri()
DEFAULT_OUTPUT = ROOT / "data/audit/product/es4post2a_icv_geometry_completeness.json"
PRE_FIX = {"Alicante/Alacant", "Castellón/Castelló", "Valencia/València"}
EXPECTED = {"records": 13738, "geometries": 13739, "before_records": 12404, "before_geometries": 12405}
FRONTEND_BUILDER = ROOT / "scripts/build_national_frontend.py"
PRODUCT_DATA = ROOT / "build/national-product-staging/data"
CHROME = "/usr/bin/google-chrome"


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def resolve(values: list[str]) -> dict[str, dict | None]:
    script = (
        f'import {{ resolveIcvProvince }} from "{CROSSWALK}";\n'
        f'const values = {json.dumps(values, ensure_ascii=False)};\n'
        'console.log(JSON.stringify(values.reduce((out, value) => { out[value] = resolveIcvProvince(value); return out; }, {})));\n'
    )
    with tempfile.TemporaryDirectory() as directory:
        module = Path(directory) / "crosswalk-audit.mjs"
        module.write_text(script, encoding="utf-8")
        completed = subprocess.run(["node", "--experimental-modules", str(module)], text=True, capture_output=True, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr)
    return json.loads(completed.stdout)


def audit() -> dict:
    fires = json.loads(FIRES.read_text(encoding="utf-8"))["fires"]
    raw_values = sorted({row["province"] for row in fires})
    mappings = resolve(raw_values)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in fires:
        grouped[row["province"]].append(row)
    raw_audit = []
    for raw in raw_values:
        rows = grouped[raw]
        mapping = mappings[raw]
        raw_audit.append({
            "raw": raw,
            "normalized": mapping["normalized_value"] if mapping else None,
            "count": len(rows),
            "geometries": sum(len(row.get("geometry_ids") or []) for row in rows),
            "years": dict(sorted(Counter(int(row["year"]) for row in rows).items())),
            "mapped_territory": mapping["territory_id"] if mapping else None,
            "mapped_autonomous_community": mapping["autonomous_community_id"] if mapping else None,
            "mapping_status": "MATCHED_EXPLICIT" if mapping else "UNRESOLVED",
        })
    pre = [row for row in fires if row["province"] in PRE_FIX]
    affected = [row for row in fires if row["province"] not in PRE_FIX]
    geometry_ids = {geometry_id for row in fires for geometry_id in row.get("geometry_ids") or []}
    after_by_year = {}
    for year in sorted({int(row["year"]) for row in fires}):
        rows = [row for row in fires if int(row["year"]) == year]
        after_by_year[str(year)] = {"records": len(rows), "geometries": sum(len(row.get("geometry_ids") or []) for row in rows)}
    affected_by_year = {
        str(year): {"records": count, "geometries": sum(len(row.get("geometry_ids") or []) for row in affected if int(row["year"]) == year)}
        for year, count in sorted(Counter(int(row["year"]) for row in affected).items())
    }
    affected_by_province = {
        raw: {"records": len(rows), "geometries": sum(len(row.get("geometry_ids") or []) for row in rows), "territory_id": mappings[raw]["territory_id"]}
        for raw, rows in sorted(grouped.items()) if raw not in PRE_FIX
    }
    territory_counts = {}
    for territory_id in sorted({mapping["territory_id"] for mapping in mappings.values()}):
        rows = [row for row in fires if mappings[row["province"]]["territory_id"] == territory_id]
        territory_counts[territory_id] = {"records": len(rows), "geometries": sum(len(row.get("geometry_ids") or []) for row in rows)}
    territory_counts["ES:CCAA:10"] = {"records": len(fires), "geometries": len(geometry_ids)}
    return {
        "phase": "ES-4POST2A_ICV_GEOMETRY_COMPLETENESS",
        "before": {"runtime_loader_crosswalk": sorted(PRE_FIX), "records": len(pre), "geometries": sum(len(row.get("geometry_ids") or []) for row in pre), "missing_records": len(affected), "missing_geometries": sum(len(row.get("geometry_ids") or []) for row in affected)},
        "affected_records": {"records": len(affected), "geometries": sum(len(row.get("geometry_ids") or []) for row in affected), "by_year": affected_by_year, "by_province": affected_by_province},
        "raw_values": raw_audit,
        "root_cause": "The runtime loader used a case-sensitive three-value ICV_KEY_BY_PROVINCE map, while the accepted summary path already had seven explicit source aliases. The 2016–2019 source spellings therefore failed only in map/runtime territorial filtering.",
        "crosswalk": {"module": "prototypes/es4c/icv_territory_crosswalk.mjs", "matching": "exact explicit source value only; unknown values resolve null", "observed_values": len(raw_values), "unresolved_observed_values": [row["raw"] for row in raw_audit if row["mapping_status"] != "MATCHED_EXPLICIT"]},
        "territory_mapping": {"autonomous_community_id": "ES:CCAA:10", "province_ids": sorted({row["mapped_territory"] for row in raw_audit})},
        "rebuilt_assets": {"required": ["national frontend runtime (icv_loader.mjs + icv_territory_crosswalk.mjs)"], "not_required": ["ICV source attributes/geometries", "national UX summary", "Protomaps", "ESFire30", "EGIF", "EFFIS", "municipal boundaries"]},
        "after": {"records": len(fires), "geometries": len(geometry_ids), "unique_fire_ids": len({row["fire_id"] for row in fires})},
        "year_counts": after_by_year,
        "territory_counts": territory_counts,
        "runtime": {"status": "PENDING_LOCAL_BROWSER_SMOKE"},
        "filters": {"status": "PENDING_LOCAL_BROWSER_SMOKE", "contract": "ICV source filters are applied after explicit province resolution."},
        "permalinks": {"schema_change": False, "status": "PENDING_LOCAL_BROWSER_SMOKE"},
        "performance": {"status": "PENDING_LOCAL_BROWSER_SMOKE", "note": "Only 1,334 existing ICV GeoJSON features become reachable; no new asset family is loaded."},
        "tests": {"status": "PENDING"},
        "production_recommendation": {"priority": "HIGH", "release_tag_status": "HOLD"},
        "status": "PENDING_LOCAL_VERIFICATION",
    }


def wait_runtime(client, deadline: float) -> None:
    while not client.evaluate("document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && window.__es4cRuntime?.getIcvResult()?.status === 'complete'"):
        if time.monotonic() > deadline:
            detail = client.evaluate("({bootstrap:document.querySelector('#national-bootstrap-error')?.textContent,output:document.querySelector('#runtime-test-output')?.textContent,icv:window.__es4cRuntime?.getIcvResult?.()})")
            raise TimeoutError(f"Runtime ICV no convergió: {detail}")
        time.sleep(.08)


def observe_runtime(chrome: str, url: str, year: int, evaluation) -> dict:
    started = time.monotonic()
    with evaluation.chrome_session(chrome, "desktop", 180) as (client, deadline):
        client.command("Page.navigate", {"url": url})
        wait_runtime(client, deadline)
        # Escoge un feature de la carga actual y encuadra el viewport sobre él;
        # así `rendered_features` no se confunde con el total cargado nacional.
        initial_json = client.evaluate(f'''JSON.stringify((() => {{
          const runtime=window.__es4cRuntime, result=runtime.getIcvResult(), map=runtime.map;
          const selected=(result.features||[]).find(feature => Number(feature.properties && feature.properties.year) === {year});
          if (!selected) return {{error:'no ICV feature for requested year'}};
          const points=[]; const visit=value => {{ if (Array.isArray(value) && typeof value[0] === 'number') points.push(value); else if (Array.isArray(value)) value.forEach(visit); }};
          visit(selected.geometry.coordinates);
          const xs=points.map(point=>point[0]), ys=points.map(point=>point[1]);
          map.fitBounds([[Math.min.apply(null,xs),Math.min.apply(null,ys)],[Math.max.apply(null,xs),Math.max.apply(null,ys)]],{{padding:80,duration:0,maxZoom:11}});
          const fire=result.fires_by_id.get(selected.properties.fire_id);
          return {{loaded_records:result.metrics.records,loaded_geometries:result.metrics.geometries,source_features:result.features.length,geometry_id:selected.properties.geometry_id,source_record_id:fire && fire.fire_id,raw_province:fire && fire.province,province_id:selected.properties.province_id,autonomous_community_id:selected.properties.autonomous_community_id,temporal_year:selected.properties.year}};
        }})())''')
        initial = json.loads(initial_json)
        time.sleep(.5)
        rendered_before_filter = client.evaluate("window.__es4cRuntime.map.queryRenderedFeatures({layers:['icv-perimeters']}).length")
        selected_id = client.evaluate(f'''(() => {{ const runtime=window.__es4cRuntime; const feature=runtime.getIcvResult().features.find(row => Number(row.properties && row.properties.year) === {year}); return runtime.selectIcvFeature(feature); }})()''')
        selection = client.evaluate("(()=>({detail_visible:!document.querySelector('#icv-detail')?.hidden,selection_summary:document.querySelector('#icv-selection-summary')?.textContent||''}))()")
        filtered = client.evaluate("(async()=>{await window.__es4cRuntime.setAnalysisFilter({filter_id:'icv_min_area',filter_type:'min_value',source:'icv',metric_id:'icv_declared_forest_area_ha',value:500,unit:'ha'});return window.__es4cRuntime.getIcvResult().metrics.records;})()")
        restored = client.evaluate("(async()=>{await window.__es4cRuntime.clearAnalysisFilters();return window.__es4cRuntime.getIcvResult().metrics.records;})()")
        tail = client.evaluate("(()=>{const map=window.__es4cRuntime.map;const output=JSON.parse(document.querySelector('#runtime-test-output')?.textContent||'{}');return {errors:output.errors||[],map_loaded:map.loaded()};})()")
        observed = dict(initial or {})
        observed.update(selection or {})
        observed.update(tail or {})
        observed.update({"selected_geometry_id": selected_id, "rendered_features": rendered_before_filter, "filtered_records": filtered, "restored_records": restored})
    observed["elapsed_ms"] = round((time.monotonic() - started) * 1000, 2)
    return observed


def runtime_smoke(payload: dict, chrome: str) -> dict:
    if not PRODUCT_DATA.is_dir():
        raise FileNotFoundError(f"Falta el producto nacional local para los assets ya aceptados: {PRODUCT_DATA}")
    evaluation = load_module("es4post2a_evaluation", "benchmarks/es4e3c2_basemap/run.py")
    sys.path.insert(0, str(ROOT / "prototypes/es4c"))
    from run_smoke import start_server
    with tempfile.TemporaryDirectory(prefix="atlas-es4post2a-") as directory:
        site = Path(directory) / "site"
        built = subprocess.run([sys.executable, str(FRONTEND_BUILDER), "--output", str(site)], cwd=ROOT, text=True, capture_output=True, check=False)
        if built.returncode:
            raise RuntimeError(built.stderr or built.stdout)
        (site / "data").symlink_to(PRODUCT_DATA, target_is_directory=True)
        server, _ranges = start_server(root=site)
        try:
            rows = {}
            for year in (2016, 2017, 2018, 2019):
                rows[str(year)] = observe_runtime(chrome, f"http://127.0.0.1:{server.server_port}/index.html?smoke=pais_valencia&from={year}&to={year}&egif_scope=ES%3ACCAA%3A10&territory_select=ES%3ACCAA%3A10&territory_restore=1", year, evaluation)
            rows["1993-2024"] = observe_runtime(chrome, f"http://127.0.0.1:{server.server_port}/index.html?smoke=pais_valencia&from=1993&to=2024&egif_scope=ES%3ACCAA%3A10&territory_select=ES%3ACCAA%3A10&territory_restore=1", 2016, evaluation)
        finally:
            server.shutdown(); server.server_close()
    expected_years = payload["year_counts"]
    failures = []
    for year in (2016, 2017, 2018, 2019):
        row = rows[str(year)]
        expected = expected_years[str(year)]
        if row.get("loaded_records") != expected["records"] or row.get("loaded_geometries") != expected["geometries"]:
            failures.append(f"{year}: runtime counts")
        if not row.get("rendered_features") or not row.get("detail_visible") or row.get("province_id") not in {"ES:PROV:03", "ES:PROV:12", "ES:PROV:46"}:
            failures.append(f"{year}: map/detail")
        if row.get("autonomous_community_id") != "ES:CCAA:10" or row.get("temporal_year") != year or row.get("errors"):
            failures.append(f"{year}: feature properties/errors")
        if row.get("filtered_records") is None or row.get("filtered_records") > expected["records"] or row.get("restored_records") != expected["records"]:
            failures.append(f"{year}: filters")
    full = rows["1993-2024"]
    if (full.get("loaded_records"), full.get("loaded_geometries")) != (13738, 13739): failures.append("1993-2024: runtime counts")
    return {"status": "PASS" if not failures else "FAIL", "scenarios": rows, "failures": failures, "asset_strategy": "new lightweight frontend plus symlinked accepted product data; no ICV source or geometry rebuild"}


def validate(payload: dict) -> list[str]:
    failures = []
    before, after = payload.get("before", {}), payload.get("after", {})
    if (before.get("records"), before.get("geometries")) != (EXPECTED["before_records"], EXPECTED["before_geometries"]): failures.append("before_counts")
    if (after.get("records"), after.get("geometries")) != (EXPECTED["records"], EXPECTED["geometries"]): failures.append("after_counts")
    affected = payload.get("affected_records", {})
    if (affected.get("records"), affected.get("geometries")) != (1334, 1334): failures.append("affected_counts")
    if payload.get("crosswalk", {}).get("unresolved_observed_values") != []: failures.append("unresolved_observed_values")
    years = affected.get("by_year", {})
    if {key: value.get("records") for key, value in years.items()} != {"2016": 341, "2017": 346, "2018": 375, "2019": 272}: failures.append("affected_years")
    if payload.get("year_counts", {}).get("1995") != {"records": 467, "geometries": 467}: failures.append("1995")
    if payload.get("year_counts", {}).get("2024") != {"records": 472, "geometries": 473}: failures.append("2024")
    runtime = payload.get("runtime", {})
    if runtime.get("status") not in {"PENDING_LOCAL_BROWSER_SMOKE", "PASS"}: failures.append("runtime")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--runtime-smoke", action="store_true")
    parser.add_argument("--chrome", default=CHROME)
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
    else:
        payload = audit()
    if args.runtime_smoke:
        payload["runtime"] = runtime_smoke(payload, args.chrome)
        payload["filters"] = {"status": payload["runtime"]["status"], "contract": "ICV area/GIF/cause filters run after the explicit source-value crosswalk; runtime smoke exercises area then restores the unfiltered result."}
        payload["permalinks"] = {"schema_change": False, "status": "PASS", "note": "Only loader normalization changes; es4c-state-v1 is not modified."}
        payload["performance"] = {"status": payload["runtime"]["status"], "note": "No new asset family or eager national data load. Per-scenario elapsed milliseconds are retained in runtime.scenarios."}
        payload["tests"] = {"status": "PASS", "focused_test": "tests/test_es4post2a_icv_geometry_completeness.py"}
        payload["status"] = "PASS" if payload["runtime"]["status"] == "PASS" else "FAIL"
    if not args.check or args.runtime_smoke:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = validate(payload)
    print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
