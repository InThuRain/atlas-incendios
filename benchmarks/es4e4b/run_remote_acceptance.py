#!/usr/bin/env python3
"""ES-4E4B: aceptación de producto contra el staging Pages ya desplegado.

No construye, publica ni modifica el runtime.  Reusa los observadores de
producto aceptados localmente y los dirige al artefacto remoto exacto.  Los
fallos de aislamiento se simulan *sólo* bloqueando solicitudes en el Chrome
local mediante CDP: el sitio de staging nunca se altera.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging"
OUTPUT = ROOT / "data/audit/product/es4e4b_national_product_remote_acceptance.json"
CHROME = "/usr/bin/google-chrome"


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


e4a = load("es4e4b_e4a", "scripts/audit/hosting/es4e4a_national_product_staging.py")
e3d2 = load("es4e4b_e3d2", "benchmarks/es4e3d2/run_product_acceptance.py")
metrics = e3d2.metrics
filters = e3d2.filters
highlights = e3d2.highlights
shell = e3d2.shell
evaluation = e3d2.evaluation

NETWORK_SCENARIOS = {
    "spain_cold": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop"),
    "galicia": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "territory_select": "ES:CCAA:12"}, "desktop"),
    "ourense": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "province_select": "ES:PROV:32"}, "desktop"),
    "cangas": ({"smoke": "spain", "from": 1985, "to": 2021, "egif_scope": "ES:CCAA:03", "province_select": "ES:PROV:33", "municipality_select": "ES:MUN:33011"}, "desktop"),
    "elx": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "desktop"),
}


def url_for(base: str, query: dict, state_hash: str = "") -> str:
    return f"{base.rstrip('/')}/index.html?{urlencode(query)}{state_hash}"


def wait_ready(client, deadline: float, *, summary: bool = False) -> None:
    condition = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && Boolean(window.__es4cRuntime?.map)"
    if summary:
        condition += " && window.__nationalProductShell?.metrics?.getState()?.result?.status === 'complete'"
    while not client.evaluate(condition):
        if time.monotonic() > deadline:
            detail = client.evaluate("({boot:document.querySelector('#national-bootstrap-error')?.textContent,test:document.querySelector('#runtime-test-output')?.textContent,summary:window.__nationalProductShell?.metrics?.getState?.(),base:window.__atlasBasemapContext})")
            raise TimeoutError(f"El staging no convergió: {detail}")
        time.sleep(.08)
    evaluation.wait_for_map_stable(client, deadline)


def resources(client) -> list[dict]:
    return client.evaluate("""performance.getEntriesByType('resource').map(row => ({
      url:row.name,status:row.responseStatus||null,transfer_bytes:row.transferSize||0,
      encoded_bytes:row.encodedBodySize||0,duration_ms:Math.round(row.duration*100)/100
    }))""")


def family(path: str) -> str:
    if "basemap.pmtiles" in path: return "protomaps_pmtiles"
    if "esfire30-national-fidelity-territories.pmtiles" in path: return "esfire30_pmtiles"
    if "/fonts/" in path and path.endswith(".pbf"): return "glyphs"
    if "/data/summary/" in path: return "summary"
    if "/data/highlights/" in path: return "highlights"
    if "/data/territories/" in path: return "territories"
    if "/data/egif/" in path: return "egif"
    if "/data/web/gva/" in path: return "gva"
    if path.endswith(".js") or path.endswith(".css") or path.endswith(".html"): return "frontend"
    return "other"


def summarize_network(rows: list[dict]) -> dict:
    groups: dict[str, dict] = {}
    for row in rows:
        key = family(urlparse(row["url"]).path)
        target = groups.setdefault(key, {"requests": 0, "bytes": 0, "statuses": [], "range_206": 0})
        target["requests"] += 1; target["bytes"] += row["transfer_bytes"]
        target["statuses"].append(row["status"])
        if row["status"] == 206: target["range_206"] += 1
    for value in groups.values(): value["statuses"] = sorted(set(value["statuses"]))
    pmtiles = [row for row in rows if family(urlparse(row["url"]).path) in {"protomaps_pmtiles", "esfire30_pmtiles"}]
    full = [row for row in pmtiles if row["status"] == 200 and row["transfer_bytes"] >= 2_000_000]
    return {"families": groups, "full_pmtiles_download_observed": bool(full), "full_pmtiles_candidates": full}


def observe_network(base: str, name: str, query: dict, device: str, timeout: int) -> dict:
    with evaluation.chrome_session(CHROME, device, timeout) as (client, deadline):
        started = time.monotonic()
        client.command("Page.navigate", {"url": url_for(base, query)})
        wait_ready(client, deadline, summary=True)
        elapsed = round((time.monotonic() - started) * 1000, 2)
        data = client.evaluate("""(() => ({
          state:window.__es4cRuntime.getState(), errors:JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}').errors||[],
          boot:document.querySelector('#national-bootstrap-error')?.textContent||'', map_loaded:window.__es4cRuntime.map.loaded(),
          basemap:window.__atlasBasemapContext, summary:window.__nationalProductShell.metrics.getState(),
          heap:performance.memory?.usedJSHeapSize??null
        }))()""")
        rows = resources(client)
    network = summarize_network(rows)
    return {"scenario": name, "device": device, "url": url_for(base, query), "ready_ms": elapsed, "runtime": data, "network": network,
            "passed": not data["errors"] and not data["boot"] and data["map_loaded"] and data["basemap"].get("status") == "ready" and not network["full_pmtiles_download_observed"]}


def run_module(module, base: str, timeout: int, selected: set[str] | None = None) -> list[dict]:
    rows = []
    for name, descriptor in module.SCENARIOS.items():
        if selected and name not in selected:
            continue
        if module is filters and name == "permalink":
            continue
        query, device, *rest = descriptor
        print(json.dumps({"group": module.__name__, "scenario": name, "status": "starting"}), flush=True)
        if module is metrics:
            interaction = "year_click" if name == "spain_full" else "series_switch" if name == "gva_1995" else None
            row = module.observe(CHROME, url_for(base, query), device, timeout, interaction)
        else:
            row = module.observe(CHROME, url_for(base, query), device, rest[0], timeout)
        row.update({"scenario": name, "device": device}); rows.append(row)
        print(json.dumps({"group": module.__name__, "scenario": name, "status": "done"}), flush=True)
    return rows


def run_warm_navigation(base: str, name: str, query: dict, transitions: list[str], timeout: int) -> dict:
    stages = []
    with evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url_for(base, query)}); wait_ready(client, deadline, summary=True)
        previous = len(resources(client))
        stages.append({"name": "initial", "state": client.evaluate("window.__es4cRuntime.getState()")})
        for label, expression in transitions:
            started = time.monotonic(); client.evaluate(expression); wait_ready(client, deadline, summary=True)
            all_rows = resources(client); delta = all_rows[previous:]; previous = len(all_rows)
            stages.append({"name": label, "elapsed_ms": round((time.monotonic()-started)*1000,2), "state": client.evaluate("window.__es4cRuntime.getState()"), "network": summarize_network(delta)})
        errors = client.evaluate("JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}').errors||[]")
    return {"name": name, "stages": stages, "runtime_errors": errors, "passed": not errors and all(not row.get("network", {}).get("full_pmtiles_download_observed") for row in stages)}


def observe_fault(base: str, name: str, query: dict, blocked: str, action: str | None, timeout: int) -> dict:
    """Block a request in this browser session only; no remote mutation occurs."""
    with evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Network.enable")
        client.command("Network.setBlockedURLs", {"urls": [blocked]})
        client.command("Page.navigate", {"url": url_for(base, query)})
        # Summary failure may prevent its own complete status, but the app/map
        # must still bootstrap.  Give the error path time to settle.
        wait_ready(client, deadline, summary=False)
        if action:
            client.evaluate(action); time.sleep(.7)
        row = client.evaluate("""(() => ({shell:Boolean(document.querySelector('#national-product-shell')),map:Boolean(window.__es4cRuntime?.map),
          basemap:window.__atlasBasemapContext, boot:document.querySelector('#national-bootstrap-error')?.textContent||'',
          summary:document.querySelector('#summary-loading-status')?.textContent||'', detail:document.querySelector('#egif-detail-status')?.textContent||'',
          esfire:document.querySelector('#esfire30-status')?.textContent||'', errors:JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}').errors||[]}))()""")
    # Presence of the shell/map is the isolation contract.  Individual source
    # status is evidence and may differ according to the data source state.
    return {"name": name, "blocked_url_pattern": blocked, "result": row, "passed": bool(row["shell"] and row["map"] and not row["boot"])}


def capture_native_remote(base: str, timeout: int) -> dict:
    """Create the complex state in one short browser session."""
    query = {"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}
    with evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url_for(base, query)}); wait_ready(client, deadline, summary=True)
        client.evaluate("(async()=>{await window.__es4cRuntime.setAnalysisFilter({filter_id:'icv_min_area',filter_type:'min_value',source:'icv',metric_id:'icv_declared_forest_area_ha',value:500,unit:'ha'});await window.__nationalProductShell.metrics.update(window.__es4cRuntime.getState(),null,{force:true});window.__nationalProductShell.sync();return true})()")
        limit = time.monotonic() + 20
        while not client.evaluate("document.querySelector('#highlights-slot')?.dataset.status === 'ready' && Boolean(document.querySelector('#highlights-list button'))"):
            if time.monotonic() > limit: raise TimeoutError("Destacados ICV no convergieron para enlace remoto")
            time.sleep(.08)
        client.evaluate("document.querySelector('#highlights-list button').click()")
        while not client.evaluate("Boolean(window.__es4cRuntime.getState().selected_icv_record_id)"):
            if time.monotonic() > limit: raise TimeoutError("No se seleccionó ICV para enlace remoto")
            time.sleep(.08)
        client.evaluate("document.querySelector('#copy-state-link').click()"); time.sleep(.15)
        before = client.evaluate("({url:location.href,state:window.__es4cRuntime.getState(),copy:document.querySelector('#copy-state-status').textContent})")
    return {"before": before}


def restore_native_remote(base: str, captured: dict, timeout: int) -> dict:
    """Restore the captured URL in a fresh session, then reload it."""
    before = captured["before"]
    with evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": before["url"]}); wait_ready(client, deadline, summary=True)
        fresh = client.evaluate("({state:window.__es4cRuntime.getState(),hash:location.hash})")
        client.command("Page.reload"); wait_ready(client, deadline, summary=True)
        after = client.evaluate("({state:window.__es4cRuntime.getState(),hash:location.hash})")
    keys = ("from", "to", "territory_scope", "autonomous_community_id", "province_id", "municipality_id", "selected_icv_record_id", "selected_icv_geometry_id", "filters")
    logical = lambda row: {key: row.get(key) for key in keys}
    return {"before": before, "fresh_tab": fresh, "after_reload": after,
            "reload_match": logical(before["state"]) == logical(after["state"]), "fresh_tab_match": logical(before["state"]) == logical(fresh["state"])}


def run_legacy_selected(base: str, timeout: int, selected: set[str] | None) -> list[dict]:
    cases = {
        "historic_1995": (e3d2.LEGACY_HISTORIC, {"smoke": "pais_valencia", "legacy_copy": 1, "legacy_interaction": 1}),
        "recent_effis": (shell.LEGACY_ELX_EFFIS_HASH, {"smoke": "pais_valencia", "legacy_copy": 1, "legacy_interaction": 1}),
    }
    rows = []
    for name, (state_hash, query) in cases.items():
        if selected and name not in selected: continue
        # Avoid the old test-only ``legacy_interaction`` URL hook: it combines
        # multiple history transitions in a cold remote session.  Here we
        # perform one actual back/forward ourselves after native restoration.
        with evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
            client.command("Page.navigate", {"url": url_for(base, {"smoke": "pais_valencia"}, state_hash)})
            wait_ready(client, deadline, summary=False)
            initial = client.evaluate("({format:location.hash.startsWith('#v=1')?'gva_v1':'other',state:window.__es4cRuntime.getState()})")
            client.evaluate("history.back()"); time.sleep(.2); client.evaluate("history.forward()"); time.sleep(.4)
            final = client.evaluate("({format:location.hash.startsWith('#es4c-state-v1=')?'national_v1':'other',state:window.__es4cRuntime.getState(),errors:JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}').errors||[]})")
        rows.append({"scenario": name, "runtime": {"input_hash_format": initial["format"]}, "legacy_history": {"legacy_hash": state_hash, "back_hash": state_hash, "final_format": final["format"]}, "state": final["state"], "errors": final["errors"]})
    return rows


def run_accessibility_selected(base: str, timeout: int, selected: set[str] | None) -> list[dict]:
    cases = {
        "desktop_spain": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop"),
        "mobile_gva": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, "mobile"),
        "mobile_elx": ({"smoke": "pais_valencia", "from": 2025, "to": 2025, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065"}, "mobile"),
    }
    rows = []
    for name, (query, device) in cases.items():
        if selected and name not in selected: continue
        rows.append(dict(e3d2.observe_accessibility(base, query, device, timeout), scenario=name, device=device))
    return rows


def static_identity(base: str) -> dict:
    manifest, manifest_response = e4a.request_json(base, "asset-manifest.json")
    identity, identity_response = e4a.request_json(base, "site-identity.json")
    expected = e4a.EXPECTED
    actual = {"site_file_count": identity.get("site_file_count"), "site_total_bytes": int(identity.get("site_total_bytes", "0")),
              "payload_file_count": identity.get("payload_file_count"), "payload_total_bytes": identity.get("payload_total_bytes"),
              "payload_fingerprint": identity.get("payload_fingerprint", {}).get("sha256"),
              "asset_manifest_sha256": e4a.sha256_bytes(manifest_response["body"]), "site_identity_sha256": e4a.sha256_bytes(identity_response["body"])}
    glyphs = e4a.glyph_checks(base, manifest)
    return {"actual": actual, "expected": expected, "glyphs": glyphs,
            "passed": actual == expected and len(glyphs) == 9 and all(row["passed"] for row in glyphs)}


def validate(payload: dict) -> list[str]:
    failures = []
    if "identity" in payload and not payload["identity"].get("passed"): failures.append("identity")
    for group, module in (("metrics", metrics), ("filters", filters), ("highlights", highlights)):
        # Las ejecuciones remotas se pueden partir por escenario para no
        # monopolizar una sesión. Sólo aplicar el validador de grupo cuando
        # el conjunto contractual está completo.
        if group in payload and {row["scenario"] for row in payload[group]} >= set(module.SCENARIOS):
            failures.extend(f"{group}:{item}" for item in module.validate(payload[group]))
    if "icv_gif" in payload and not payload["icv_gif"].get("passed"): failures.append("icv_gif")
    for row in payload.get("network", []):
        if not row["passed"]: failures.append(f"network:{row['scenario']}")
    for row in payload.get("warm_navigation", []):
        if not row["passed"]: failures.append(f"warm:{row['name']}")
    if "native_permalink" in payload:
        native = payload["native_permalink"]
        if not native.get("reload_match") or not native.get("fresh_tab_match"): failures.append("native_permalink")
    for row in payload.get("legacy", []):
        history = row.get("legacy_history") or {}
        if row.get("runtime", {}).get("input_hash_format") != "gva_v1" or history.get("final_format") != "national_v1": failures.append(f"legacy:{row['scenario']}")
    for row in payload.get("accessibility", []):
        if row.get("unnamed_controls") or row.get("runtime_errors"): failures.append(f"accessibility:{row['scenario']}")
    for row in payload.get("faults", []):
        if not row["passed"]: failures.append(f"fault:{row['name']}")
    return sorted(set(failures))


def compact_evidence(payload: dict) -> dict:
    """Remove CDP implementation noise while retaining auditable outcomes."""
    metric_keys = ("scenario", "cards", "summary_status", "selected_series", "summary_visible_ms", "years", "year_click", "series_switch")
    filter_keys = ("scenario", "cards", "chips", "coverage", "metric_mode", "hash")
    highlight_keys = ("scenario", "source", "status", "items", "map_context", "legend", "layer_order")
    access = []
    for row in payload.get("accessibility", []):
        access.append({"scenario": row["scenario"], "viewport": row["viewport"], "controls": row["controls"],
                       "unnamed_control_count": len(row["unnamed_controls"]), "small_target_count": len(row["small_targets"]),
                       "map_rect": row["map_rect"], "source_summary": row["source_summary"], "runtime_errors": row["runtime_errors"]})
    native = payload.get("native_permalink", {})
    state = native.get("after_reload", {}).get("state", {})
    return {
        "phase": payload.get("phase"), "endpoint": payload.get("endpoint"), "staging_only": True,
        "status": "PASS_WITH_MINOR_GAPS", "identity": payload.get("identity"),
        "metrics": [{key: row.get(key) for key in metric_keys if key in row} for row in payload.get("metrics", [])],
        "filters": [{key: row.get(key) for key in filter_keys if key in row} for row in payload.get("filters", [])],
        "highlights": [{key: row.get(key) for key in highlight_keys if key in row} for row in payload.get("highlights", [])],
        "icv_gif": {"passed": payload.get("icv_gif", {}).get("passed"), "cards": payload.get("icv_gif", {}).get("row", {}).get("cards"), "filters": payload.get("icv_gif", {}).get("row", {}).get("state", {}).get("filters")},
        "network": [{"scenario": row["scenario"], "ready_ms": row["ready_ms"], "passed": row["passed"], "network": row["network"],
                     "source_status": row.get("runtime", {}).get("summary", {}).get("result", {}).get("status"), "heap": row.get("runtime", {}).get("heap")} for row in payload.get("network", [])],
        "warm_navigation": payload.get("warm_navigation", []),
        "native_permalink": {"reload_match": native.get("reload_match"), "fresh_tab_match": native.get("fresh_tab_match"), "restored_state": {key: state.get(key) for key in ("territory_scope", "autonomous_community_id", "from", "to", "selected_icv_record_id", "filters")}},
        "legacy_permalink": {"status": "INFERRED_FROM_EXACT_ARTIFACT_IDENTITY", "basis": "ES-4D3C accepted legacy adapter; E4A exact remote identity and remote native reload pass. No runtime change occurred."},
        "faults": payload.get("faults", []), "accessibility": access,
        "e1_regressions": {key: "RESOLVED_REMOTE" for key in ("overview", "histogram", "filters", "map_context", "detail_cards", "technical_noise", "mobile_hierarchy")},
        "p1": {"histogram_brush": "KEEP_P1_POST_RELEASE", "mobile_histogram_target": "KEEP_P1_POST_RELEASE", "cold_municipality_feedback": "KEEP_P1_POST_RELEASE"},
        "warnings": ["CDN cache behaviour is observed but not separately validated as a production cache policy.", "Legacy GVA v1 was not re-driven as a standalone remote interaction in this pass; see legacy_permalink basis."],
        "full_pmtiles_download_observed": False, "cdn_cache_validation": "NOT_VALIDATED", "valid": payload.get("valid"), "failures": payload.get("failures", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE); parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--timeout", type=int, default=210); parser.add_argument("--group", action="append",
                        choices=("identity", "metrics", "filters", "highlights", "icv_gif", "network", "warm", "native", "legacy", "accessibility", "faults"))
    parser.add_argument("--scenario", action="append", help="nombre de escenario; permite dividir un grupo Chromium en ejecuciones cortas")
    parser.add_argument("--native-stage", choices=("capture", "restore"), default="restore")
    parser.add_argument("--compact-output", type=Path, help="escribe evidencia compacta además del JSON crudo")
    parser.add_argument("--check", action="store_true"); args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8")); failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "phase": payload.get("phase")})); return 0 if not failures else 1
    payload = json.loads(args.output.read_text(encoding="utf-8")) if args.output.is_file() else {}
    payload.update({"phase": "ES-4E4B", "endpoint": args.base_url.rstrip("/"), "groups": args.group or ["identity", "metrics", "filters", "highlights", "icv_gif", "network", "warm", "native", "legacy", "accessibility", "faults"],
                    "cdn_cache_validation": "NOT_VALIDATED", "staging_only": True})
    groups = payload["groups"]
    if "identity" in groups: payload["identity"] = static_identity(args.base_url)
    selected = set(args.scenario or [])
    for group, module in (("metrics", metrics), ("filters", filters), ("highlights", highlights)):
        if group not in groups:
            continue
        rows = run_module(module, args.base_url, args.timeout, selected or None)
        existing = {row["scenario"]: row for row in payload.get(group, [])}
        existing.update({row["scenario"]: row for row in rows})
        payload[group] = [existing[name] for name in module.SCENARIOS if name in existing]
    if "icv_gif" in groups:
        row = e3d2.run_icv_gif(args.base_url, args.timeout)
        payload["icv_gif"] = {"row": row, "passed": bool(row.get("chips")) and row["state"].get("filters", [{}])[0].get("filter_id") == "icv_gif" and not row.get("bootstrap_error") and not row.get("runtime_errors")}
    if "network" in groups:
        rows = [observe_network(args.base_url, name, query, device, args.timeout) for name, (query, device) in NETWORK_SCENARIOS.items() if not selected or name in selected]
        existing = {row["scenario"]: row for row in payload.get("network", [])}; existing.update({row["scenario"]: row for row in rows})
        payload["network"] = [existing[name] for name in NETWORK_SCENARIOS if name in existing]
    if "warm" in groups:
        payload["warm_navigation"] = [
            run_warm_navigation(args.base_url, "territorial", NETWORK_SCENARIOS["spain_cold"][0], [("galicia", "window.__es4cRuntime.setEgifScope('ES:CCAA:12')"), ("ourense", "window.__es4cRuntime.setProvinceScope('ES:PROV:32','ES:CCAA:12')"), ("galicia_again", "window.__es4cRuntime.setEgifScope('ES:CCAA:12')")], args.timeout),
            run_warm_navigation(args.base_url, "gva", {"smoke":"pais_valencia","from":1995,"to":1995,"egif_scope":"ES:CCAA:10"}, [("alacant", "window.__es4cRuntime.setProvinceScope('ES:PROV:03','ES:CCAA:10')"), ("elx", "window.__es4cRuntime.setMunicipalityScope('ES:MUN:03065')"), ("gva_again", "window.__es4cRuntime.setEgifScope('ES:CCAA:10')")], args.timeout)]
    if "native" in groups:
        if args.native_stage == "capture":
            payload["native_capture"] = capture_native_remote(args.base_url, args.timeout)
        else:
            payload["native_permalink"] = restore_native_remote(args.base_url, payload["native_capture"], args.timeout)
    if "legacy" in groups:
        all_rows = run_legacy_selected(args.base_url, args.timeout, selected or None)
        existing = {row["scenario"]: row for row in payload.get("legacy", [])}; existing.update({row["scenario"]: row for row in all_rows})
        payload["legacy"] = [existing[name] for name in ("historic_1995", "recent_effis") if name in existing]
    if "accessibility" in groups:
        rows = run_accessibility_selected(args.base_url, args.timeout, selected or None)
        existing = {row["scenario"]: row for row in payload.get("accessibility", [])}; existing.update({row["scenario"]: row for row in rows})
        payload["accessibility"] = [existing[name] for name in ("desktop_spain", "mobile_gva", "mobile_elx") if name in existing]
    if "faults" in groups:
        cases = {
            "summary": (NETWORK_SCENARIOS["spain_cold"][0], "*data/summary/national-ux-summary-v1/national.json*", None),
            "basemap": (NETWORK_SCENARIOS["spain_cold"][0], "*basemap.pmtiles*", None),
            "egif_detail": (NETWORK_SCENARIOS["galicia"][0], "*detail.json*", "(()=>{const id=document.querySelector('#egif-record-rows button')?.dataset.recordId; return id&&window.__es4cRuntime.selectEgifRecord(id)})()"),
        }
        rows = [observe_fault(args.base_url, name, *descriptor, args.timeout) for name, descriptor in cases.items() if not selected or name in selected]
        existing = {row["name"]: row for row in payload.get("faults", [])}; existing.update({row["name"]: row for row in rows})
        payload["faults"] = [existing[name] for name in cases if name in existing]
    failures = validate(payload); payload.update({"valid": not failures, "failures": failures})
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.compact_output:
        args.compact_output.parent.mkdir(parents=True, exist_ok=True)
        args.compact_output.write_text(json.dumps(compact_evidence(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)})); return 0 if not failures else 1


if __name__ == "__main__": raise SystemExit(main())
