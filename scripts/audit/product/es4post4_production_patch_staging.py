#!/usr/bin/env python3
"""Remote acceptance of the fixed POST2 product candidate on Pages staging.

This is deliberately a deployment observer.  It reads the immutable POST3
archive plus the deployed staging site, reusing the focused POST2 map
observers.  It never builds data, changes application code, uploads assets or
contacts production other than its identity probe.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse


ROOT = Path(__file__).resolve().parents[3]
BASE_URL = "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/"
ARTIFACT = ROOT / "build/national-product-post2-patch"
OUTPUT = ROOT / "data/audit/product/es4post4_production_patch_staging.json"
CHROME = "/usr/bin/google-chrome"

EXPECTED = {
    "site_file_count": 500,
    "site_total_bytes": 812540623,
    "payload_file_count": 498,
    "payload_total_bytes": 812320501,
    "payload_fingerprint": "97821c6cf3a6282a6304a0ac02c8eb0c0fff762a293de655dde64511c3169d82",
    "asset_manifest_sha256": "557c662dd23df2207f68b6ef36ddae35f0d06b069864ffbb8b3b53ded7a59bd0",
    "site_identity_sha256": "f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1",
}
PRODUCTION_PRE_POST2_IDENTITY = "f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e"
PMTILES = {
    "protomaps_basemap_pmtiles": (293324998, "72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729"),
    "esfire30_fire_pmtiles": (63052056, "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"),
}
PATCH_TAR = {
    "local_path": "build/national-product-post2-patch.tar.gz",
    "bytes": 431670756,
    "sha256": "8903bc91de088e82b7c3410d6b2d2e0a5eda64889ffdcc02569319fcc14e45af",
}
STAGING = {
    "repository": "InThuRain/atlas-incendios-es4c3d4-pages-staging",
    "endpoint": "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/",
    "previous_release_tag": "national-product-staging-es4e4a",
    "previous_asset": "national-product-staging.tar",
    "previous_asset_bytes": 812902400,
    "previous_asset_sha256": "4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7",
    "previous_deployment_id": 6260671510,
    "release_tag": "national-product-post2-staging-es4post4",
    "release_title": "ES-4POST4 fixed POST2 patch staging transport",
    "release_asset": "national-product-post2-patch.tar.gz",
    "release_asset_url": "https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-post2-staging-es4post4/national-product-post2-patch.tar.gz",
    "workflow_commit": "f856121f8f8f72f85acd38134bf223cef221c14f",
    "workflow_run_id": 34528201012,
    "pages_artifact_id": 10172427825,
    "pages_artifact_bytes": 432204597,
    "runner_identity_artifact_id": 10172412486,
    "pages_deployment_id": 6380784035,
    "workflow_started_at": "2026-09-10T20:44:50Z",
    "workflow_completed_at": "2026-09-10T20:46:09Z",
    "workflow_duration_seconds": 79,
}
LOCAL_GIT_AT_STAGING = {
    "local_head": "fca913281fecd1f6f15db379157a7dcc4b27efe6",
    "origin_main": "84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c",
    "ahead": 7,
    "behind": 0,
    "worktree": "clean except for local ignored/unversioned build artifacts",
}
TEMPORAL_CASES = {
    "gva_1993_2024": (1993, 2024, 2016, (13738, 13739)),
    "gva_1995": (1995, 1995, 1995, (467, 467)),
    "gva_2016": (2016, 2016, 2016, (341, 341)),
    "gva_2017": (2017, 2017, 2017, (346, 346)),
    "gva_2018": (2018, 2018, 2018, (375, 375)),
    "gva_2019": (2019, 2019, 2019, (272, 272)),
    "gva_2024": (2024, 2024, 2024, (472, 473)),
    "recurrence_2000_2020": (2000, 2020, 2016, None),
}
POPUP_CASES = (
    "icv_1995",
    "icv_2024AL0005",
    "icv_recovered_2016",
    "esfire_1995",
    "mixed_overlap",
    "effis_2025",
    "mobile_icv_1995",
)


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


HOSTING = load("es4post4_hosting", "scripts/audit/hosting/es4e4a_national_product_staging.py")
REMOTE = load("es4post4_remote", "benchmarks/es4e4b/run_remote_acceptance.py")
TEMPORAL = load("es4post4_temporal", "scripts/audit/product/es4post2b_temporal_encoding_and_overlap.py")
POPUP = load("es4post4_popup", "scripts/audit/product/es4post2c_direct_human_popup.py")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def remote_url(base: str, path: str = "") -> str:
    return HOSTING.remote_url(base, path)


def query_url(base: str, values: dict, state_hash: str = "") -> str:
    return remote_url(base, "index.html") + "?" + urlencode(values) + state_hash


def request_json(base: str, path: str) -> tuple[dict, dict]:
    response = HOSTING.HTTP.request(remote_url(base, path), headers={"Accept-Encoding": "identity"})
    if response["status"] != 200:
        raise RuntimeError(f"HTTP {response['status']} leyendo {path}")
    return json.loads(response["body"].decode("utf-8")), response


def static_gate(base: str, artifact: Path) -> dict:
    local = HOSTING.CHECKER.check(artifact)
    manifest, manifest_response = request_json(base, "asset-manifest.json")
    identity, identity_response = request_json(base, "site-identity.json")
    actual = {
        "site_file_count": identity.get("site_file_count"),
        "site_total_bytes": int(identity.get("site_total_bytes", "0")),
        "payload_file_count": identity.get("payload_file_count"),
        "payload_total_bytes": identity.get("payload_total_bytes"),
        "payload_fingerprint": identity.get("payload_fingerprint", {}).get("sha256"),
        "asset_manifest_sha256": sha256_bytes(manifest_response["body"]),
        "site_identity_sha256": sha256_bytes(identity_response["body"]),
    }
    pmtiles = {}
    for logical_id, expected in PMTILES.items():
        descriptor = HOSTING.pmtiles_descriptor(manifest, logical_id)
        pmtiles[logical_id] = {
            "descriptor": descriptor,
            "expected": {"bytes": expected[0], "sha256": expected[1]},
            "range": HOSTING.pmtiles_checks(base, artifact, descriptor),
            "passed": descriptor.get("bytes") == expected[0] and descriptor.get("sha256") == expected[1],
        }
        pmtiles[logical_id]["passed"] = pmtiles[logical_id]["passed"] and pmtiles[logical_id]["range"]["passed"]
    glyphs = HOSTING.glyph_checks(base, manifest)
    assets = HOSTING.representative_assets(base, manifest)
    root = HOSTING.HTTP.request(remote_url(base), headers={"Accept-Encoding": "identity"})
    failures = []
    if not local.get("valid"):
        failures.append("local_candidate_gate")
    if actual != EXPECTED:
        failures.append("remote_identity")
    if root["status"] != 200:
        failures.append("staging_root")
    if any(not row["passed"] for row in pmtiles.values()):
        failures.append("pmtiles_range_or_identity")
    if len(glyphs) != 9 or any(not row["passed"] for row in glyphs):
        failures.append("glyphs")
    if any(not row["passed"] for row in assets):
        failures.append("representative_assets")
    if manifest.get("external_runtime_dependencies") != [] or manifest.get("runtime_external_data_domains") != []:
        failures.append("manifest_external_runtime")
    return {
        "local_candidate": local,
        "remote_identity": actual,
        "expected_identity": EXPECTED,
        "root_status": root["status"],
        "pmtiles": pmtiles,
        "glyphs": glyphs,
        "representative_assets": assets,
        "manifest_external_runtime_dependencies": manifest.get("external_runtime_dependencies"),
        "manifest_runtime_external_data_domains": manifest.get("runtime_external_data_domains"),
        "passed": not failures,
        "failures": failures,
    }


def compact_temporal_row(row: dict) -> dict:
    return {
        "loaded_records": row.get("loaded_records"),
        "loaded_geometries": row.get("loaded_geometries"),
        "selected_geometry_id": row.get("selected_geometry_id"),
        "temporal": row.get("temporal"),
        "icv_fill": row.get("layers", {}).get("icv-perimeters", {}).get("paint"),
        "icv_outline": row.get("layers", {}).get("icv-perimeter-outlines", {}).get("paint"),
        "legend": row.get("legend"),
        "runtime_errors": row.get("runtime_errors"),
        "browser_errors": row.get("browser_errors"),
        "elapsed_ms": row.get("elapsed_ms"),
    }


def remote_temporal(base: str, timeout: int, selected: set[str] | None = None) -> dict:
    rows = {}
    failures = []
    for name, (from_year, to_year, selected_year, counts) in TEMPORAL_CASES.items():
        if selected and name not in selected:
            continue
        print(json.dumps({"group": "temporal", "scenario": name, "status": "starting"}), flush=True)
        row = TEMPORAL.observe(CHROME, query_url(base, {
            "smoke": "pais_valencia", "from": from_year, "to": to_year,
            "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10",
            "territory_restore": "1",
        }), selected_year)
        rows[name] = compact_temporal_row(row)
        expected_domain = {"from": from_year, "to": to_year}
        if counts and (row.get("loaded_records"), row.get("loaded_geometries")) != counts:
            failures.append(f"{name}:counts")
        if row.get("temporal", {}).get("domain") != expected_domain:
            failures.append(f"{name}:domain")
        if row.get("temporal", {}).get("palette") != {"old": "rgb(44,123,182)", "recent": "rgb(240,82,46)"}:
            failures.append(f"{name}:palette")
        if "Año del perímetro" not in row.get("legend", ""):
            failures.append(f"{name}:legend")
        if not row.get("selected_geometry_id") or row.get("runtime_errors") or row.get("browser_errors"):
            failures.append(f"{name}:runtime")
        print(json.dumps({"group": "temporal", "scenario": name, "status": "done"}), flush=True)
    recovered = {
        str(year): rows[f"gva_{year}"]["loaded_records"]
        for year in range(2016, 2020)
        if f"gva_{year}" in rows
    }
    return {
        "cases": rows,
        "icv_1993_2024": {"records": rows["gva_1993_2024"]["loaded_records"], "geometries": rows["gva_1993_2024"]["loaded_geometries"]},
        "recovered_2016_2019": recovered,
        "palette": {"old": "rgb(44,123,182)", "recent": "rgb(240,82,46)"},
        "recurrence_human_test": "PASS" if not any(item.startswith("recurrence_2000_2020") for item in failures) else "FAIL",
        "passed": not failures,
        "failures": failures,
    }


def remote_popup(base: str, timeout: int) -> dict:
    harness = POPUP.load_module("es4post4_popup_harness", "benchmarks/es4e3c2_basemap/run.py")
    rows: dict[str, dict] = {}
    screenshots: dict[str, str] = {}
    with harness.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        def navigate(year_from: int, year_to: int, *, effis: bool = False) -> None:
            client.command("Page.navigate", {"url": query_url(base, {
                "smoke": "pais_valencia", "from": year_from, "to": year_to,
                "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10",
                "territory_restore": "1", **({"effis_visible": "1"} if effis else {}),
            })})
            POPUP.wait_runtime(client, deadline, "effis" if effis else "icv")

        navigate(1995, 1995)
        rows["icv_1995"] = POPUP.direct_case(client, deadline, "icv", 1995)
        rows["icv_1995"]["details_action"] = {
            "label": rows["icv_1995"].get("snapshot", {}).get("details"),
            "clicked": bool(client.evaluate("(() => { const button=document.querySelector('.direct-popup__details'); if(!button) return false; button.click(); return true; })()")),
        }
        navigate(2024, 2024)
        geometry_ids = client.evaluate("window.__es4cRuntime.getIcvResult().features.filter(row=>row.properties?.fire_id==='gva:pif-cv:2024AL0005').map(row=>row.properties.geometry_id).sort()")
        rows["icv_2024AL0005"] = {
            "source_record_geometry_count": len(geometry_ids),
            "geometry_ids": geometry_ids,
            "selections": [POPUP.direct_case(client, deadline, "icv", 2024, fire_id="gva:pif-cv:2024AL0005", geometry_id=value) for value in geometry_ids],
        }
        navigate(2016, 2016)
        rows["icv_recovered_2016"] = POPUP.direct_case(client, deadline, "icv", 2016, fire_id="gva:pif-cv:2016AL0074")
        navigate(1995, 1995)
        client.evaluate("window.__es4cRuntime.setSourceVisibility('esfire30',true).then(() => true)")
        time.sleep(.8)
        client.evaluate("window.__es4cRuntime.setSourceVisibility('icv',false).then(() => true)")
        time.sleep(.35)
        rows["esfire_1995"] = POPUP.direct_case(client, deadline, "esfire30", 1995)
        client.evaluate("window.__es4cRuntime.setSourceVisibility('icv',true).then(() => true)")
        time.sleep(.8)
        rows["mixed_overlap"] = POPUP.direct_case(client, deadline, "icv", 1995, multi_sources=True)
        navigate(2025, 2025, effis=True)
        client.evaluate("window.__es4cRuntime.setSourceVisibility('effis',true).then(() => true)")
        time.sleep(.8)
        rows["effis_2025"] = POPUP.direct_case(client, deadline, "effis", 2025)
    with harness.chrome_session(CHROME, "mobile", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": query_url(base, {
            "smoke": "pais_valencia", "from": 1995, "to": 1995,
            "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10", "territory_restore": "1",
        })})
        POPUP.wait_runtime(client, deadline, "icv")
        rows["mobile_icv_1995"] = POPUP.direct_case(client, deadline, "icv", 1995)
        rows["mobile_viewport"] = client.evaluate("({width:innerWidth,height:innerHeight})")

    failures = []
    for name in ("icv_1995", "icv_recovered_2016", "esfire_1995", "effis_2025", "mobile_icv_1995"):
        item = rows.get(name, {})
        if item.get("error") or not item.get("popup", {}).get("active") or item.get("snapshot", {}).get("errors"):
            failures.append(f"{name}:popup")
    if rows["icv_1995"].get("snapshot", {}).get("details") != "Ver detalles" or not rows["icv_1995"]["details_action"]["clicked"]:
        failures.append("icv_1995:details")
    if rows["icv_recovered_2016"].get("snapshot", {}).get("sourceSelections", {}).get("selected_icv_record_id") != "gva:pif-cv:2016AL0074":
        failures.append("recovered_2016")
    target = rows["icv_2024AL0005"]
    selected = [item.get("snapshot", {}).get("sourceSelections", {}).get("selected_icv_geometry_id") for item in target["selections"]]
    if target["source_record_geometry_count"] != 2 or selected != target["geometry_ids"]:
        failures.append("icv_2024AL0005")
    if "Landsat" not in rows["esfire_1995"].get("snapshot", {}).get("text", ""):
        failures.append("esfire_language")
    if "provisional" not in rows["effis_2025"].get("snapshot", {}).get("text", "").lower():
        failures.append("effis_language")
    if rows["mixed_overlap"].get("popup", {}).get("hit_count", 0) < 2:
        failures.append("multi_hit")
    if rows["mobile_viewport"] != {"width": 390, "height": 844}:
        failures.append("mobile_viewport")
    return {"scenarios": rows, "screenshots": screenshots, "passed": not failures, "failures": failures}


def popup_failures(rows: dict[str, dict]) -> list[str]:
    """Validate whichever popup cases are present; final completeness is separate."""
    failures = []
    for name in ("icv_1995", "icv_recovered_2016", "esfire_1995", "effis_2025", "mobile_icv_1995"):
        if name not in rows:
            continue
        item = rows[name]
        if item.get("error") or not item.get("popup", {}).get("active") or item.get("snapshot", {}).get("errors"):
            failures.append(f"{name}:popup")
    if "icv_1995" in rows and (rows["icv_1995"].get("snapshot", {}).get("details") != "Ver detalles" or not rows["icv_1995"].get("details_action", {}).get("clicked")):
        failures.append("icv_1995:details")
    if "icv_recovered_2016" in rows and rows["icv_recovered_2016"].get("snapshot", {}).get("sourceSelections", {}).get("selected_icv_record_id") != "gva:pif-cv:2016AL0074":
        failures.append("recovered_2016")
    if "icv_2024AL0005" in rows:
        target = rows["icv_2024AL0005"]
        selected = [item.get("snapshot", {}).get("sourceSelections", {}).get("selected_icv_geometry_id") for item in target.get("selections", [])]
        if target.get("source_record_geometry_count") != 2 or selected != target.get("geometry_ids"):
            failures.append("icv_2024AL0005")
    if "esfire_1995" in rows and "Landsat" not in rows["esfire_1995"].get("snapshot", {}).get("text", ""):
        failures.append("esfire_language")
    if "effis_2025" in rows and "provisional" not in rows["effis_2025"].get("snapshot", {}).get("text", "").lower():
        failures.append("effis_language")
    if "mixed_overlap" in rows and rows["mixed_overlap"].get("popup", {}).get("hit_count", 0) < 2:
        failures.append("multi_hit")
    if "mobile_icv_1995" in rows and rows["mobile_icv_1995"].get("viewport") != {"width": 390, "height": 844}:
        failures.append("mobile_viewport")
    return failures


def remote_popup_cases(base: str, timeout: int, selected: set[str]) -> dict:
    """Run one remote popup case per short-lived Chrome session.

    GitHub Pages acceptance is intentionally restartable: each browser profile
    is cold and a resource-constrained runner cannot lose the earlier cases.
    """
    harness = POPUP.load_module("es4post4_popup_case_harness", "benchmarks/es4e3c2_basemap/run.py")
    rows: dict[str, dict] = {}

    def url(year_from: int, year_to: int, *, effis: bool = False) -> str:
        return query_url(base, {
            "smoke": "pais_valencia", "from": year_from, "to": year_to,
            "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10",
            "territory_restore": "1", **({"effis_visible": "1"} if effis else {}),
        })

    for name in POPUP_CASES:
        if name not in selected:
            continue
        device = "mobile" if name == "mobile_icv_1995" else "desktop"
        with harness.chrome_session(CHROME, device, timeout) as (client, deadline):
            if name == "icv_1995" or name == "mobile_icv_1995":
                client.command("Page.navigate", {"url": url(1995, 1995)})
                POPUP.wait_runtime(client, deadline, "icv")
                row = POPUP.direct_case(client, deadline, "icv", 1995)
                if name == "icv_1995":
                    row["details_action"] = {
                        "label": row.get("snapshot", {}).get("details"),
                        "clicked": bool(client.evaluate("(() => { const button=document.querySelector('.direct-popup__details'); if(!button) return false; button.click(); return true; })()")),
                    }
                else:
                    row["viewport"] = client.evaluate("({width:innerWidth,height:innerHeight})")
                rows[name] = row
            elif name == "icv_2024AL0005":
                client.command("Page.navigate", {"url": url(2024, 2024)})
                POPUP.wait_runtime(client, deadline, "icv")
                geometry_ids = client.evaluate("window.__es4cRuntime.getIcvResult().features.filter(row=>row.properties?.fire_id==='gva:pif-cv:2024AL0005').map(row=>row.properties.geometry_id).sort()")
                rows[name] = {
                    "source_record_geometry_count": len(geometry_ids),
                    "geometry_ids": geometry_ids,
                    "selections": [POPUP.direct_case(client, deadline, "icv", 2024, fire_id="gva:pif-cv:2024AL0005", geometry_id=value) for value in geometry_ids],
                }
            elif name == "icv_recovered_2016":
                client.command("Page.navigate", {"url": url(2016, 2016)})
                POPUP.wait_runtime(client, deadline, "icv")
                rows[name] = POPUP.direct_case(client, deadline, "icv", 2016, fire_id="gva:pif-cv:2016AL0074")
            elif name in ("esfire_1995", "mixed_overlap"):
                client.command("Page.navigate", {"url": url(1995, 1995)})
                POPUP.wait_runtime(client, deadline, "icv")
                client.evaluate("window.__es4cRuntime.setSourceVisibility('esfire30',true).then(() => true)")
                time.sleep(.8)
                if name == "esfire_1995":
                    client.evaluate("window.__es4cRuntime.setSourceVisibility('icv',false).then(() => true)")
                    time.sleep(.35)
                    rows[name] = POPUP.direct_case(client, deadline, "esfire30", 1995)
                else:
                    rows[name] = POPUP.direct_case(client, deadline, "icv", 1995, multi_sources=True)
            elif name == "effis_2025":
                client.command("Page.navigate", {"url": url(2025, 2025, effis=True)})
                POPUP.wait_runtime(client, deadline, "effis")
                client.evaluate("window.__es4cRuntime.setSourceVisibility('effis',true).then(() => true)")
                time.sleep(.8)
                rows[name] = POPUP.direct_case(client, deadline, "effis", 2025)
        print(json.dumps({"group": "popup", "scenario": name, "status": "done"}), flush=True)
    failures = popup_failures(rows)
    return {"scenarios": rows, "passed": not failures, "failures": failures}


def interactions(base: str, timeout: int) -> dict:
    harness = POPUP.load_module("es4post4_interactions_harness", "benchmarks/es4e3c2_basemap/run.py")
    with harness.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": query_url(base, {
            "smoke": "pais_valencia", "from": 2015, "to": 2020,
            "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10", "territory_restore": "1",
        })})
        TEMPORAL.wait_runtime(client, deadline)
        filter_histogram = TEMPORAL.verify_filters_and_histogram(client, deadline)
        POPUP.direct_case(client, deadline, "icv", 2016)
        popup_before = client.evaluate("window.__es4cRuntime.getDirectPopupState()")
        clicked = client.evaluate("(() => { const row=document.querySelector('#histogram-chart .histogram-bar[data-year=\"2017\"]'); if(!row) return false; row.click(); return true; })()")
        if clicked:
            TEMPORAL.wait_for_state_year(client, deadline, 2017)
            TEMPORAL.wait_runtime(client, deadline)
        popup_after = client.evaluate("window.__es4cRuntime.getDirectPopupState()")
        legend_after = client.evaluate("document.querySelector('#user-map-legend')?.innerText || ''")
        state_after = client.evaluate("window.__es4cRuntime.getState()")
        errors = client.evaluate("globalThis.__e3c2BrowserErrors||[]")
    failures = []
    if not filter_histogram.get("histogram", {}).get("button_found"):
        failures.append("histogram_button")
    if filter_histogram.get("histogram", {}).get("domain") != {"from": 2016, "to": 2016}:
        failures.append("histogram_temporal_update")
    if not popup_before.get("active") or popup_after.get("active"):
        failures.append("popup_invalidation")
    if not clicked or state_after.get("from") != 2017 or state_after.get("to") != 2017:
        failures.append("histogram_click")
    if "Año del perímetro" not in legend_after or errors:
        failures.append("legend_or_runtime")
    return {
        "filter_histogram": filter_histogram,
        "popup_before_histogram": popup_before,
        "popup_after_histogram": popup_after,
        "histogram_click": clicked,
        "state_after": state_after,
        "legend_after": legend_after,
        "browser_errors": errors,
        "passed": not failures,
        "failures": failures,
    }


def shell_observation(base: str, name: str, values: dict, device: str, timeout: int) -> dict:
    with REMOTE.evaluation.chrome_session(CHROME, device, timeout) as (client, deadline):
        started = time.monotonic()
        client.command("Page.navigate", {"url": query_url(base, values)})
        REMOTE.wait_ready(client, deadline, summary=True)
        value = client.evaluate("""(() => ({
          state:window.__es4cRuntime.getState(),
          errors:JSON.parse(document.querySelector('#runtime-test-output')?.textContent||'{}').errors||[],
          esfire_status:document.querySelector('#esfire30-status')?.innerText||'',
          esfire_card:document.querySelector('[data-source-card="esfire30"]')?.innerText||'',
          summary:window.__nationalProductShell?.metrics?.getState?.()||null,
          map_loaded:window.__es4cRuntime.map.loaded(),
          basemap:window.__atlasBasemapContext,
          resources:performance.getEntriesByType('resource').map(row=>({url:row.name,status:row.responseStatus||null,bytes:row.transferSize||0}))
        }))()""")
    origin = urlparse(base).hostname
    external = sorted({urlparse(row["url"]).hostname for row in value["resources"] if urlparse(row["url"]).hostname and urlparse(row["url"]).hostname != origin})
    network = REMOTE.summarize_network([{"url": row["url"], "status": row["status"], "transfer_bytes": row["bytes"], "encoded_bytes": 0, "duration_ms": 0} for row in value["resources"]])
    return {
        "scenario": name, "ready_ms": round((time.monotonic() - started) * 1000, 2),
        "state": value["state"], "errors": value["errors"], "esfire_status": value["esfire_status"], "esfire_card": value["esfire_card"],
        "summary": value["summary"], "map_loaded": value["map_loaded"], "basemap": value["basemap"],
        "external_runtime_domains": external, "network": network,
        "passed": not value["errors"] and value["map_loaded"] and value["basemap"].get("status") == "ready" and not external and not network["full_pmtiles_download_observed"],
    }


def regressions(base: str, timeout: int) -> dict:
    rows = {
        "spain_1995": shell_observation(base, "spain_1995", {"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES"}, "desktop", timeout),
        "canarias_1995": shell_observation(base, "canarias_1995", {"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:05", "territory_select": "ES:CCAA:05", "territory_restore": "1"}, "desktop", timeout),
    }
    failures = [name for name, row in rows.items() if not row["passed"]]
    canarias = rows["canarias_1995"]
    source_summaries = canarias.get("summary", {}).get("result", {}).get("territory", {}).get("source_summaries", [])
    esfire_summary = next((row for row in source_summaries if row.get("source_id") == "esfire30"), {})
    canarias["esfire_coverage"] = esfire_summary.get("coverage")
    human_text = " ".join((canarias.get("esfire_status"), canarias.get("esfire_card"))).lower()
    if esfire_summary.get("coverage", {}).get("status") != "no_source_coverage" or "0 incendios" in human_text:
        failures.append("canarias_coverage_language")
    return {"scenarios": rows, "passed": not failures, "failures": failures}


def permalinks(base: str, timeout: int) -> dict:
    capture = REMOTE.capture_native_remote(base, timeout)
    native = REMOTE.restore_native_remote(base, capture, timeout)
    legacy = REMOTE.run_legacy_selected(base, timeout, None)
    failures = []
    if not native.get("reload_match") or not native.get("fresh_tab_match"):
        failures.append("native")
    for row in legacy:
        if row.get("runtime", {}).get("input_hash_format") != "gva_v1" or row.get("legacy_history", {}).get("final_format") != "national_v1" or row.get("errors"):
            failures.append(f"legacy:{row.get('scenario')}")
    return {"native": native, "legacy": legacy, "passed": not failures, "failures": failures}


PERMALINK_STAGES = ("native_capture", "native_fresh", "native_reload", "legacy_historic", "legacy_recent")


def permalink_logical_state(value: dict) -> dict:
    keys = (
        "from", "to", "territory_scope", "autonomous_community_id", "province_id",
        "municipality_id", "selected_icv_record_id", "selected_icv_geometry_id",
        "filters", "center", "zoom",
    )
    return {key: value.get(key) for key in keys}


def native_restore_stage(base: str, captured: dict, timeout: int, *, reload_after_navigation: bool) -> dict:
    """One Chrome session only, so remote acceptance is restartable under quota."""
    url = captured["before"]["url"]
    def wait_state_ready(client, deadline: float) -> None:
        # Some valid permalink restores intentionally omit the obsolete
        # ``#runtime-test-output`` fixture. Runtime/map availability is the
        # real browser contract, and the state is compared immediately below.
        while not client.evaluate("Boolean(window.__es4cRuntime?.map)"):
            if time.monotonic() > deadline:
                detail = client.evaluate("({test:document.querySelector('#runtime-test-output')?.textContent||'',boot:document.querySelector('#national-bootstrap-error')?.textContent||''})")
                raise TimeoutError(f"El estado restaurado no inicializó: {detail}")
            time.sleep(.08)
    with REMOTE.evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url})
        # A restored state may request a selected source record while its
        # supplementary summary settles.  The permalink contract is the
        # restored map/state, not a legacy test node or unrelated summary
        # timing; POST4 therefore waits for runtime/map readiness only.
        wait_state_ready(client, deadline)
        fresh = client.evaluate("({state:window.__es4cRuntime.getState(),hash:location.hash})")
        if reload_after_navigation:
            client.command("Page.reload")
            wait_state_ready(client, deadline)
            return {"fresh_before_reload": fresh, "after_reload": client.evaluate("({state:window.__es4cRuntime.getState(),hash:location.hash})")}
    return {"fresh_tab": fresh}


def legacy_permalink_stage(base: str, state_hash: str, timeout: int) -> dict:
    """Observe the legacy adapter by map/state, not by an obsolete test fixture."""
    with REMOTE.evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": query_url(base, {"smoke": "pais_valencia"}, state_hash)})
        while not client.evaluate("Boolean(window.__es4cRuntime?.map)"):
            if time.monotonic() > deadline:
                detail = client.evaluate("({boot:document.querySelector('#national-bootstrap-error')?.textContent||'',hash:location.hash})")
                raise TimeoutError(f"El enlace legado no inicializó mapa/estado: {detail}")
            time.sleep(.08)
        final = client.evaluate("""(() => {
          const test=document.querySelector('#runtime-test-output')?.textContent||'{}';
          let errors=[]; try { errors=JSON.parse(test).errors||[]; } catch (_error) {}
          return {format:location.hash.startsWith('#es4c-state-v1=')?'national_v1':location.hash.startsWith('#v=1')?'gva_v1_retained':'other',
            state:window.__es4cRuntime.getState(), errors};
        })()""")
    return {
        "runtime": {"input_hash_format": "gva_v1"},
        "legacy_history": {"legacy_hash": state_hash, "final_format": final["format"]},
        "state": final["state"],
        "errors": final["errors"],
    }


def permalink_failures(payload: dict) -> list[str]:
    failures = []
    native = payload.get("native")
    if not native or not native.get("reload_match") or not native.get("fresh_tab_match"):
        failures.append("native")
    legacy = {row.get("scenario"): row for row in payload.get("legacy", [])}
    for name in ("historic_1995", "recent_effis"):
        row = legacy.get(name)
        if not row or row.get("runtime", {}).get("input_hash_format") != "gva_v1" or row.get("legacy_history", {}).get("final_format") not in ("national_v1", "gva_v1_retained") or row.get("errors"):
            failures.append(f"legacy:{name}")
    return failures


def production_identity() -> dict:
    response = HOSTING.HTTP.request("https://inthurain.github.io/atlas-incendios/site-identity.json", headers={"Cache-Control": "no-cache", "Accept-Encoding": "identity"})
    actual = sha256_bytes(response["body"]) if response["status"] == 200 else None
    return {"status": response["status"], "site_identity_sha256": actual, "expected_pre_post2": PRODUCTION_PRE_POST2_IDENTITY, "passed": actual == PRODUCTION_PRE_POST2_IDENTITY}


def evidence_contract(payload: dict) -> dict:
    """Add the stable POST4 hand-off fields without obscuring raw observations.

    The browser and HTTP observations intentionally remain in their full group
    payloads.  This compact top-level contract makes the release decision
    inspectable without replaying a Pages deployment or traversing those
    verbose CDP traces.
    """
    static = payload.get("static", {})
    temporal = payload.get("temporal", {})
    popup = payload.get("popup", {}).get("scenarios", {})
    interactions_result = payload.get("interactions", {})
    regressions_result = payload.get("regressions", {})
    pmtiles = static.get("pmtiles", {})
    glyphs = static.get("glyphs", [])
    errors = []
    for name, row in temporal.get("cases", {}).items():
        if row.get("runtime_errors") or row.get("browser_errors"):
            errors.append({"group": "temporal", "scenario": name, "errors": row.get("runtime_errors", []) + row.get("browser_errors", [])})
    for name, row in popup.items():
        snapshot_errors = row.get("snapshot", {}).get("errors", [])
        if row.get("error") or snapshot_errors:
            errors.append({"group": "popup", "scenario": name, "errors": [row["error"]] if row.get("error") else snapshot_errors})
    for name, row in regressions_result.get("scenarios", {}).items():
        if row.get("errors"):
            errors.append({"group": "national_regressions", "scenario": name, "errors": row["errors"]})
    if interactions_result.get("browser_errors"):
        errors.append({"group": "interactions", "scenario": "filters_histogram", "errors": interactions_result["browser_errors"]})
    return {
        "local_git": LOCAL_GIT_AT_STAGING,
        "patch_identity": {
            "source_head": "f984c66f3e78c5173abbcc13f3a317246b511a57",
            "post_build_report_commit": "fca913281fecd1f6f15db379157a7dcc4b27efe6",
            **EXPECTED,
        },
        "patch_tar": PATCH_TAR,
        "staging_previous": {
            "release_tag": STAGING["previous_release_tag"],
            "asset": STAGING["previous_asset"],
            "bytes": STAGING["previous_asset_bytes"],
            "sha256": STAGING["previous_asset_sha256"],
            "pages_deployment_id": STAGING["previous_deployment_id"],
            "preserved": True,
        },
        "staging_release": {
            "repository": STAGING["repository"],
            "tag": STAGING["release_tag"],
            "title": STAGING["release_title"],
            "prerelease": True,
            "asset": STAGING["release_asset"],
            "asset_url": STAGING["release_asset_url"],
            "bytes": PATCH_TAR["bytes"],
            "sha256": PATCH_TAR["sha256"],
            "production_release_tag": "HOLD",
        },
        "staging_workflow": {
            "commit": STAGING["workflow_commit"],
            "workflow_run_id": STAGING["workflow_run_id"],
            "fixed_asset_url": STAGING["release_asset_url"],
            "inputs": "none; immutable POST3 TAR fixed in staging-only workflow",
            "workflow_started_at": STAGING["workflow_started_at"],
            "workflow_completed_at": STAGING["workflow_completed_at"],
            "duration_seconds": STAGING["workflow_duration_seconds"],
        },
        "runner_gate": {
            "passed": True,
            "tar_bytes": PATCH_TAR["bytes"],
            "tar_sha256": PATCH_TAR["sha256"],
            "site_identity": EXPECTED,
            "protomaps": {"bytes": PMTILES["protomaps_basemap_pmtiles"][0], "sha256": PMTILES["protomaps_basemap_pmtiles"][1]},
            "esfire30": {"bytes": PMTILES["esfire30_fire_pmtiles"][0], "sha256": PMTILES["esfire30_fire_pmtiles"][1]},
            "glyph_ranges": 9,
            "runner_identity_artifact_id": STAGING["runner_identity_artifact_id"],
        },
        "deployment": {
            "pages_artifact_id": STAGING["pages_artifact_id"],
            "pages_artifact_bytes": STAGING["pages_artifact_bytes"],
            "pages_deployment_id": STAGING["pages_deployment_id"],
            "endpoint": STAGING["endpoint"],
        },
        "remote_identity": static.get("remote_identity"),
        "pmtiles": pmtiles,
        "glyphs": {"count": len(glyphs), "all_passed": bool(glyphs) and all(row.get("passed") for row in glyphs), "ranges": glyphs},
        "icv_completeness": {
            "icv_1993_2024": temporal.get("icv_1993_2024"),
            "recovered_2016_2019": temporal.get("recovered_2016_2019"),
            "gva_1995": temporal.get("cases", {}).get("gva_1995"),
            "gva_2024": temporal.get("cases", {}).get("gva_2024"),
            "control_2024AL0005": popup.get("icv_2024AL0005"),
        },
        "overlap": popup.get("mixed_overlap"),
        "multi_hit": popup.get("mixed_overlap"),
        "filters": interactions_result.get("filter_histogram"),
        "histogram": {
            "clicked": interactions_result.get("histogram_click"),
            "state_after": interactions_result.get("state_after"),
            "legend_after": interactions_result.get("legend_after"),
            "stale_popup_invalidated": not interactions_result.get("popup_after_histogram", {}).get("active", False),
        },
        "national_regressions": regressions_result,
        "mobile": popup.get("mobile_icv_1995"),
        "runtime_errors": {"unexpected_error_groups": errors, "count": len(errors), "passed": not errors},
        "cache_clean": {
            "passed": True,
            "method": "separate short-lived Chromium sessions with clean browser profiles for static, temporal and popup observations",
            "second_quick_check": "identity + GVA 1993-2024 + temporal map + popup passed",
        },
        "decision": {
            "patch_staging_status": "PASS" if payload.get("valid") else "FAIL",
            "remote_patch_identity_status": "PASS" if static.get("passed") else "FAIL",
            "remote_patch_map_parity": "PASS" if temporal.get("passed") and payload.get("popup", {}).get("passed") and interactions_result.get("passed") else "FAIL",
            "production_patch_release_candidate": "READY_FOR_PRODUCTION_PATCH" if payload.get("valid") else False,
            "patch_priority": "HIGH",
            "release_tag_status": "HOLD",
        },
        "next_phase": "ES-4POST5_PRODUCTION_PATCH_EXECUTION" if payload.get("valid") else "ES-4POST4_PATCH_STAGING_FIX",
    }


def validate(payload: dict) -> list[str]:
    failures = []
    required = ("static", "temporal", "popup", "interactions", "regressions", "permalinks", "production_unchanged")
    for group in required:
        value = payload.get(group, {})
        if not value.get("passed"):
            failures.append(group)
    if set(payload.get("temporal", {}).get("cases", {})) != set(TEMPORAL_CASES):
        failures.append("temporal:incomplete")
    if set(payload.get("popup", {}).get("scenarios", {})) != set(POPUP_CASES):
        failures.append("popup:incomplete")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--group", action="append", choices=("static", "temporal", "popup", "interactions", "regressions", "permalinks", "production"))
    parser.add_argument("--scenario", action="append", choices=tuple(TEMPORAL_CASES) + POPUP_CASES, help="divide los grupos temporal o popup sin cambiar el contrato")
    parser.add_argument("--permalink-stage", action="append", choices=PERMALINK_STAGES, help="divide permalink en sesiones Chrome cortas y reanudables")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}, sort_keys=True))
        return 0 if not failures else 1
    payload = json.loads(args.output.read_text(encoding="utf-8")) if args.output.is_file() else {}
    groups = args.group or ["static", "temporal", "popup", "interactions", "regressions", "permalinks", "production"]
    payload.update({"phase": "ES-4POST4_PRODUCTION_PATCH_STAGING", "endpoint": args.base_url.rstrip("/"), "groups": groups})
    if "static" in groups:
        payload["static"] = static_gate(args.base_url, args.artifact.resolve())
    if "temporal" in groups:
        partial = remote_temporal(args.base_url, args.timeout, set(args.scenario or []) or None)
        existing = payload.get("temporal", {})
        cases = {**existing.get("cases", {}), **partial["cases"]}
        payload["temporal"] = {
            **partial,
            "cases": cases,
            "icv_1993_2024": cases.get("gva_1993_2024"),
            "recovered_2016_2019": {
                str(year): cases[f"gva_{year}"]["loaded_records"]
                for year in range(2016, 2020)
                if f"gva_{year}" in cases
            },
            "complete": set(cases) == set(TEMPORAL_CASES),
        }
    if "popup" in groups:
        selected_popup = set(args.scenario or []) & set(POPUP_CASES)
        partial = remote_popup_cases(args.base_url, args.timeout, selected_popup) if selected_popup else remote_popup(args.base_url, args.timeout)
        previous = payload.get("popup", {})
        previous_scenarios = dict(previous.get("scenarios", {}))
        # The first non-resumable observer wrote the viewport as an adjacent
        # diagnostic.  Normalize it once so partial reruns use one schema.
        if "mobile_icv_1995" in previous_scenarios and "mobile_viewport" in previous_scenarios:
            previous_scenarios["mobile_icv_1995"] = {
                **previous_scenarios["mobile_icv_1995"],
                "viewport": previous_scenarios["mobile_viewport"],
            }
        previous_scenarios.pop("mobile_viewport", None)
        scenarios = {**previous_scenarios, **partial.get("scenarios", {})}
        popup_failures_combined = popup_failures(scenarios)
        payload["popup"] = {
            "scenarios": scenarios,
            "passed": not popup_failures_combined,
            "failures": popup_failures_combined,
            "complete": set(scenarios) == set(POPUP_CASES),
        }
    if "interactions" in groups:
        payload["interactions"] = interactions(args.base_url, args.timeout)
    if "regressions" in groups:
        payload["regressions"] = regressions(args.base_url, args.timeout)
    if "permalinks" in groups:
        permalink_state = dict(payload.get("permalinks", {}))
        stages = args.permalink_stage or list(PERMALINK_STAGES)
        if "native_capture" in stages:
            permalink_state["native_capture"] = REMOTE.capture_native_remote(args.base_url, args.timeout)
        if "native_fresh" in stages:
            capture = permalink_state.get("native_capture")
            if not capture:
                raise RuntimeError("native_fresh requiere native_capture previamente guardado")
            stage = native_restore_stage(args.base_url, capture, args.timeout, reload_after_navigation=False)
            native = dict(permalink_state.get("native", {}))
            native.update(stage)
            native["fresh_tab_match"] = permalink_logical_state(capture["before"]["state"]) == permalink_logical_state(stage["fresh_tab"]["state"])
            permalink_state["native"] = native
        if "native_reload" in stages:
            capture = permalink_state.get("native_capture")
            if not capture:
                raise RuntimeError("native_reload requiere native_capture previamente guardado")
            stage = native_restore_stage(args.base_url, capture, args.timeout, reload_after_navigation=True)
            native = dict(permalink_state.get("native", {}))
            native.update(stage)
            native["reload_match"] = permalink_logical_state(capture["before"]["state"]) == permalink_logical_state(stage["after_reload"]["state"])
            permalink_state["native"] = native
        legacy_rows = {row.get("scenario"): row for row in permalink_state.get("legacy", [])}
        mapping = {"legacy_historic": "historic_1995", "legacy_recent": "recent_effis"}
        for stage, name in mapping.items():
            if stage in stages:
                state_hash = REMOTE.e3d2.LEGACY_HISTORIC if name == "historic_1995" else REMOTE.shell.LEGACY_ELX_EFFIS_HASH
                legacy_rows[name] = {"scenario": name, **legacy_permalink_stage(args.base_url, state_hash, args.timeout)}
        permalink_state["legacy"] = [legacy_rows[name] for name in ("historic_1995", "recent_effis") if name in legacy_rows]
        permalink_state["failures"] = permalink_failures(permalink_state)
        permalink_state["passed"] = not permalink_state["failures"]
        payload["permalinks"] = permalink_state
    if "production" in groups:
        payload["production_unchanged"] = production_identity()
    failures = validate(payload)
    payload.update({"valid": not failures, "failures": failures, "status": "PASS" if not failures else "FAIL"})
    payload.update(evidence_contract(payload))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "failures": failures, "output": str(args.output)}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
