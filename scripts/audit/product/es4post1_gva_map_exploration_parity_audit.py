#!/usr/bin/env python3
"""Read-only ES-4POST1 map-exploration parity observations.

This auditor deliberately does not build, deploy or alter either product.  It
compares the pinned legacy GVA worktree served locally with the live national
Pages URL.  Dataset totals are calculated from the pinned assets; browser
counts deliberately distinguish loaded source features from the subset that
MapLibre renders in the current viewport.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import http.server
import importlib.util
import json
import socketserver
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

from shapely.geometry import shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[3]
LEGACY_WORKTREE = Path("/tmp/atlas-es4post1-gva")
LEGACY_SITE = LEGACY_WORKTREE / "data/derived/gva/publication/site"
NATIONAL_URL = "https://inthurain.github.io/atlas-incendios"
OUTPUT = ROOT / "data/audit/product/es4post1_gva_map_exploration_parity_audit.json"
CHROME = "/usr/bin/google-chrome"
RANGES = ((1993, 1993), (1995, 1995), (2000, 2000), (2010, 2010), (2020, 2020), (2024, 2024), (1993, 2024), (2000, 2010), (2015, 2024))


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


evaluation = load_module("es4post1_evaluation", "benchmarks/es4e3c2_basemap/run.py")


@contextlib.contextmanager
def served(directory: Path):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(directory), **kwargs)
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()
            thread.join(timeout=5)


def assets_for_years(site: Path) -> dict:
    root = site / "data/web/gva"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    fires_payload = json.loads((root / "fires.json").read_text(encoding="utf-8"))
    fires = fires_payload["fires"]
    geometry_rows = []
    for asset in manifest["icv"]["geometry_assets"]:
        if asset["level"] != "overview":
            continue
        payload = json.loads((site / asset["url"]).read_text(encoding="utf-8"))
        geometry_rows.extend(payload["features"])
    # Overview assets are the canonical one-per-geometry view for this audit.
    by_geometry = {str(row["properties"]["geometry_id"]): row for row in geometry_rows}
    if len(by_geometry) != 13739:
        raise ValueError(f"ICV overview geometry identity mismatch: {len(by_geometry)}")
    records = list(fires)
    fire_by_id = {str(row["fire_id"]): row for row in records}
    current_runtime_provinces = {"Alicante/Alacant", "Castellón/Castelló", "Valencia/València"}
    rows = []
    for start, end in RANGES:
        selected_records = [row for row in records if start <= int(row["year"]) <= end]
        selected_geometries = [row for row in by_geometry.values() if start <= int(row["properties"]["year"]) <= end]
        runtime_records = [row for row in selected_records if row["province"] in current_runtime_provinces]
        rows.append({
            "from": start, "to": end, "icv_records": len(selected_records), "icv_geometries": len(selected_geometries),
            "national_current_loader_records": len(runtime_records),
            "national_current_loader_excluded_records": len(selected_records) - len(runtime_records),
        })
    esfire = json.loads((root / "esfire30/geometry/overview.geojson").read_text(encoding="utf-8"))["features"]
    for row in rows:
        row["legacy_esfire30_geometries"] = sum(row["from"] <= int(feature["properties"]["year"]) <= row["to"] for feature in esfire)
    # Evidence of actual historic overlap is selected from the Mariola / Font
    # Roja / interior Alacant area, never inferred from a generic viewport.
    target_names = {"Agres", "Alcoi", "Banyeres de Mariola", "Bocairent", "Ibi", "Muro de Alcoy"}
    candidate_rows = [row for row in by_geometry.values() if fire_by_id.get(str(row["properties"].get("fire_id")), {}).get("municipality_name") in target_names]
    geometries = [shape(row["geometry"]) for row in candidate_rows]
    tree = STRtree(geometries)
    examples, seen = [], set()
    for index, geometry in enumerate(geometries):
        for raw_other in tree.query(geometry):
            other = int(raw_other)
            if other <= index:
                continue
            left, right = candidate_rows[index], candidate_rows[other]
            if left["properties"].get("year") == right["properties"].get("year"):
                continue
            try:
                if geometry.intersection(geometries[other]).area <= 0:
                    continue
            except Exception:
                continue
            key = tuple(sorted((str(left["properties"]["geometry_id"]), str(right["properties"]["geometry_id"]))))
            if key in seen:
                continue
            seen.add(key)
            examples.append({
                "zone": fire_by_id.get(str(left["properties"].get("fire_id")), {}).get("municipality_name"),
                "left": {"geometry_id": left["properties"]["geometry_id"], "fire_id": left["properties"].get("fire_id"), "year": left["properties"].get("year")},
                "right": {"geometry_id": right["properties"]["geometry_id"], "fire_id": right["properties"].get("fire_id"), "year": right["properties"].get("year")},
                "positive_area_overlap": True,
            })
            if len(examples) == 3:
                break
        if len(examples) == 3:
            break
    if len(examples) != 3:
        raise ValueError("No se localizaron tres solapes positivos en las zonas dirigidas")
    return {
        "icv_manifest": {"coverage": [manifest["sources"]["icv"]["year_min"], manifest["sources"]["icv"]["year_max"]], "fires_sha256": manifest["icv"]["attributes"]["fires"]["sha256"]},
        "ranges": rows, "icv_geometry_count": len(by_geometry), "icv_record_count": len(records),
        "legacy_esfire30": {"geometry_count": len(esfire), "coverage": [manifest["sources"]["esfire30"]["year_min"], manifest["sources"]["esfire30"]["year_max"]]},
        "national_current_loader_exclusion": {
            "reason": "ICV_KEY_BY_PROVINCE only recognizes title-cased province labels",
            "records": sum(row["province"] not in current_runtime_provinces for row in records),
            "by_year": dict(sorted(Counter(int(row["year"]) for row in records if row["province"] not in current_runtime_provinces).items())),
            "by_source_value": dict(sorted(Counter(str(row["province"]) for row in records if row["province"] not in current_runtime_provinces).items())),
        },
        "overlap_examples": examples,
    }


def wait_legacy(client, deadline: float):
    while not client.evaluate("document.querySelector('#debug-output')?.dataset.complete === 'true'"):
        if time.monotonic() > deadline:
            raise TimeoutError("El GVA histórico no convergió")
        time.sleep(.08)


def wait_national(client, deadline: float):
    condition = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && Boolean(window.__es4cRuntime?.map)"
    while not client.evaluate(condition):
        if time.monotonic() > deadline:
            detail = client.evaluate("({boot:document.querySelector('#national-bootstrap-error')?.textContent,test:document.querySelector('#runtime-test-output')?.textContent})")
            raise TimeoutError(f"El nacional no convergió: {detail}")
        time.sleep(.08)
    evaluation.wait_for_map_stable(client, deadline)


def capture(client, path: Path | None) -> str | None:
    if not path:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    image = client.command("Page.captureScreenshot", {"format": "png", "fromSurface": True})
    path.write_bytes(base64.b64decode(image["data"]))
    return str(path.relative_to(ROOT))


def legacy_browser(base: str, start: int, end: int, entity_id: str, geometry_id: str, timeout: int, screenshot: Path | None = None) -> dict:
    fragment = urlencode({"v": 1, "lat": 38.65, "lng": -0.52, "z": 8, "from": start, "to": end, "src": "icv,esfire30", "province": "all", "entity": entity_id, "geometry": geometry_id})
    with evaluation.chrome_session(CHROME, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": f"{base}/index.html?debug=1#{fragment}"})
        wait_legacy(client, deadline)
        # The legacy app only opens a popup after selecting a valid entity. Its
        # debug state tells us whether the direct, geometry-bound interaction
        # took place (as opposed to a static data-card assertion).
        result = client.evaluate("JSON.parse(document.querySelector('#debug-output').textContent)")
        result["final"]["screenshot"] = capture(client, screenshot)
    return result["final"]


def national_browser(start: int, end: int, timeout: int, screenshot: Path | None = None, device: str = "desktop") -> dict:
    query = {"smoke": "pais_valencia", "from": start, "to": end, "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10"}
    with evaluation.chrome_session(CHROME, device, timeout) as (client, deadline):
        client.command("Page.navigate", {"url": f"{NATIONAL_URL}/index.html?{urlencode(query)}"})
        wait_national(client, deadline)
        # The smoke chooses an administrative scope.  Wait for ICV separately:
        # it is an isolated asynchronous loader and must not be conflated with
        # the generic smoke-complete marker.
        while not client.evaluate("['complete','error','no_coverage','disabled','no_territory_coverage'].includes(window.__es4cRuntime.getIcvResult()?.status)"):
            if time.monotonic() > deadline:
                raise TimeoutError("ICV nacional no terminó")
            time.sleep(.08)
        client.evaluate("(()=>{window.__es4cRuntime.map.jumpTo({center:[-0.52,38.65],zoom:8});return true})()")
        client.evaluate("(async()=>{await window.__es4cRuntime.refreshIcv();return true})()")
        evaluation.wait_for_map_stable(client, deadline)
        result = client.evaluate("""(()=>{
          const map=window.__es4cRuntime.map, icv=window.__es4cRuntime.getIcvResult();
          const features=icv.features||[]; const chosen=features[0]||null;
          if(chosen) window.__es4cRuntime.selectIcvFeature(chosen);
          return {
            state:window.__es4cRuntime.getState(), icv_status:icv.status,
            loaded_records:icv.metrics?.records??null, loaded_geometries:icv.metrics?.geometries??null,
            source_features:map.querySourceFeatures('icv').length,
            rendered_features:map.queryRenderedFeatures({layers:['icv-perimeters']}).length,
            selected_geometry_id:window.__es4cRuntime.getState().selected_icv_geometry_id,
            detail_visible:!document.querySelector('#icv-detail')?.hidden,
            detail_text:document.querySelector('#icv-detail')?.innerText||'',
            runtime_errors:JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}').errors||[]
          };
        })()""")
        result["screenshot"] = capture(client, screenshot)
        result["esfire_default_visible"] = client.evaluate("window.__es4cRuntime.getState().esfire30_visible")
        client.evaluate("(async()=>{await window.__es4cRuntime.setSourceVisibility('esfire30',true);return true})()")
        evaluation.wait_for_map_stable(client, deadline)
        result["esfire_rendered_when_enabled"] = client.evaluate("window.__es4cRuntime.map.queryRenderedFeatures({layers:['esfire30-perimeters']}).length")
    return result


def run(timeout: int) -> dict:
    if not LEGACY_SITE.is_dir():
        raise FileNotFoundError(f"No existe el GVA reconstruido: {LEGACY_SITE}")
    static = assets_for_years(LEGACY_SITE)
    geometry_1995 = next(row for row in json.loads((LEGACY_SITE / "data/web/gva/geometry/overview/alicante/1993-1999.geojson").read_text(encoding="utf-8"))["features"] if row["properties"]["year"] == 1995)["properties"]
    geometry_2024 = next(row for row in json.loads((LEGACY_SITE / "data/web/gva/geometry/overview/alicante/2020-2024.geojson").read_text(encoding="utf-8"))["features"] if row["properties"]["year"] == 2024)["properties"]
    geometry_1993 = next(row for row in json.loads((LEGACY_SITE / "data/web/gva/geometry/overview/alicante/1993-1999.geojson").read_text(encoding="utf-8"))["features"] if row["properties"]["year"] == 1993)["properties"]
    screenshot_root = OUTPUT.parent / "es4post1"
    with served(LEGACY_SITE) as legacy_url:
        browser = {
            "legacy_1995": legacy_browser(legacy_url, 1995, 1995, geometry_1995["fire_id"], geometry_1995["geometry_id"], timeout, screenshot_root / "legacy-gva-1995.png"),
            "legacy_2024": legacy_browser(legacy_url, 2024, 2024, geometry_2024["fire_id"], geometry_2024["geometry_id"], timeout),
            "legacy_overlap_1993_2024": legacy_browser(legacy_url, 1993, 2024, geometry_1993["fire_id"], geometry_1993["geometry_id"], timeout),
            "national_1995": national_browser(1995, 1995, timeout, screenshot_root / "national-1995.png"),
            "national_2024": national_browser(2024, 2024, timeout),
            "national_overlap_1993_2024": national_browser(1993, 2024, timeout, screenshot_root / "national-overlap-1993-2024.png"),
            "national_mobile_1995": national_browser(1995, 1995, timeout, screenshot_root / "national-mobile-1995.png", "mobile"),
        }
    assessment = {
        "geometry_completeness": "FAIL",
        "default_geometry_source": "PARTIAL",
        "temporal_visual_encoding": "FAIL",
        "overlap_visual_encoding": "FAIL",
        "direct_click": "PARTIAL",
        "basic_popup": "FAIL",
        "map_first": "PARTIAL",
        "mobile": "PARTIAL",
        "map_exploration_parity": "FAIL",
        "post_release_product_parity_review": "FAILED_NEEDS_FIX",
        "release_tag_status": "HOLD",
        "next_phase": "ES-4POST2_GVA_MAP_EXPLORATION_PARITY_IMPLEMENTATION",
    }
    source_render_matrix = {
        "gva_1995": {"expected_icv_records": 467, "expected_icv_geometries": 467, "legacy_loaded": browser["legacy_1995"]["loadedGeometryCount"], "legacy_rendered": browser["legacy_1995"]["visiblePerimeterCount"], "national_loaded": browser["national_1995"]["loaded_geometries"], "national_rendered_viewport": browser["national_1995"]["rendered_features"]},
        "gva_2024": {"expected_icv_records": 472, "expected_icv_geometries": 473, "legacy_rendered": browser["legacy_2024"]["visiblePerimeterCount"], "national_loaded": browser["national_2024"]["loaded_geometries"], "national_rendered_viewport": browser["national_2024"]["rendered_features"]},
        "gva_1993_2024": {"expected_icv_records": 13738, "expected_icv_geometries": 13739, "legacy_rendered": browser["legacy_overlap_1993_2024"]["visiblePerimeterCount"], "national_loaded": browser["national_overlap_1993_2024"]["loaded_geometries"], "national_excluded": 1334, "national_rendered_viewport": browser["national_overlap_1993_2024"]["rendered_features"]},
    }
    return {
        "phase": "ES-4POST1",
        "production_identity": {"url": NATIONAL_URL, "root_switch_commit": "84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c", "site_identity_sha256": "f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e", "observed_read_only": True},
        "old_gva_reference": {"commit": "f7a3532f633a247f33dee3ebba9fbcc316c0e534", "site": str(LEGACY_SITE), "rebuild_status": "PASS"},
        "legacy_reference": {"commit": "f7a3532f633a247f33dee3ebba9fbcc316c0e534", "site": str(LEGACY_SITE)},
        "national_reference": NATIONAL_URL,
        "static": static,
        "browser": browser,
        "scenarios": static["ranges"],
        "source_render_matrix": source_render_matrix,
        "geometry_completeness": {"status": "FAIL", "root_cause": "ICV province source-value normalization", "expected": [13738, 13739], "national_loaded": [12404, 12405]},
        "recommended_source": {"gva_1993_2024": "ICV primary official geometry; ESFire30 remains complementary and independent"},
        "temporal_encoding": {"legacy": "interpolated 1985-old blue to 2026-recent red RGB", "national": "constant ICV green #246b55", "status": "FAIL"},
        "overlap": {"examples": static["overlap_examples"], "legacy": "year colour makes different dates readable", "national": "constant fill has no temporal overlap cue", "status": "FAIL"},
        "click_flow": {"legacy": "Leaflet feature click -> selectEntity -> L.popup", "national": "MapLibre feature click -> sidebar/bottom detail", "status": "PARTIAL"},
        "popup": {"legacy": "direct map popup", "national": "human detail card outside the map", "status": "FAIL"},
        "human_tests": {"same_year_1995": "PASS geometry availability, FAIL temporal/popup parity", "complete_history": "FAIL 1334 ICV omitted in national runtime"},
        "mobile": {"viewport": "390x844", "selection_detail": "PASS", "map_popup_and_temporal_reading": "FAIL"},
        "screenshots": {key: value.get("screenshot") for key, value in browser.items() if value.get("screenshot")},
        "regressions": ["ICV 2016-2019 province-value exclusion", "constant ICV visual encoding", "no map-anchored basic popup"],
        "root_causes": ["ICV_KEY_BY_PROVINCE accepts only three title-cased source values", "ICV paint has no year expression", "selection design moved context from popup to detail card"],
        "production_risk": "MAJOR_PRODUCT_REGRESSION_FIX_FORWARD_REQUIRED",
        "rollback_recommendation": "NO_AUTOMATIC_ROLLBACK; keep national live and fix forward before tag",
        "implementation_plan": ["normalize documented ICV province source values", "restore temporal/overlap visual encoding and legend", "add accessible map-anchored basic popup while retaining full detail card", "repeat exact parity audit"],
        "decision": assessment,
        "assessment": assessment,
    }


def check(payload: dict) -> list[str]:
    failures = []
    static = payload["static"]
    if (static["icv_record_count"], static["icv_geometry_count"]) != (13738, 13739): failures.append("ICV total no coincide con 13738/13739")
    lookup = {(row["from"], row["to"]): row for row in static["ranges"]}
    if (lookup[(1995, 1995)]["icv_records"], lookup[(1995, 1995)]["icv_geometries"]) != (467, 467): failures.append("ICV 1995 no coincide con 467/467")
    if (lookup[(2024, 2024)]["icv_records"], lookup[(2024, 2024)]["icv_geometries"]) != (472, 473): failures.append("ICV 2024 no coincide con 472/473")
    if lookup[(1993, 2024)]["national_current_loader_excluded_records"] != 1334: failures.append("La exclusión ICV nacional esperada no coincide")
    for key in ("national_1995", "national_2024", "national_overlap_1993_2024", "national_mobile_1995"):
        row = payload["browser"][key]
        extra = 1 if key in {"national_2024", "national_overlap_1993_2024"} else 0
        if row["icv_status"] != "complete" or row["loaded_geometries"] != row["loaded_records"] + extra: failures.append(f"{key}: ICV no cargó la cardinalidad esperada")
        if not row["selected_geometry_id"] or not row["detail_visible"]: failures.append(f"{key}: ICV no es seleccionable con ficha")
        if row["runtime_errors"]: failures.append(f"{key}: errores runtime")
    if payload["browser"]["national_overlap_1993_2024"]["loaded_records"] != lookup[(1993, 2024)]["national_current_loader_records"]: failures.append("El browser nacional no reproduce el subconjunto ICV actual")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
    else:
        payload = run(args.timeout)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failures = check(payload)
    print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
