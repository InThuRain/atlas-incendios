#!/usr/bin/env python3
"""Exercise the CV-1.5 frontend in Chrome under a GitHub Pages-like path."""

import argparse
import html
import json
import os
import re
import statistics
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode


def repository_root():
    return Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format_value, *args):
        return


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data/derived/gva/frontend/smoke_report.json",
    )
    return parser.parse_args()


def find_reused_case(root):
    base = root / "data/web/gva/geometry/overview"
    for province_dir in sorted(base.iterdir()):
        for path in sorted(province_dir.glob("*.geojson")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for feature in payload["features"]:
                if feature["properties"]["geometry_reused"]:
                    properties = feature["properties"]
                    return {
                        "province": province_dir.name,
                        "year": properties["year"],
                        "fire_id": properties["fire_id"],
                        "geometry_id": properties["geometry_id"],
                    }
    raise RuntimeError("No reused geometry found in production assets")


def chrome_snapshot(chrome, url, window_size="1440,900", attempts=3):
    result = ""
    for attempt in range(attempts):
        process = subprocess.run(
            [
                chrome,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--enable-precise-memory-info",
                "--virtual-time-budget=120000",
                "--window-size=" + window_size,
                "--dump-dom",
                url,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            timeout=150,
        )
        match = re.search(
            r'<pre id="debug-output"[^>]*>(.*?)</pre>', process.stdout, re.DOTALL
        )
        if not match:
            raise RuntimeError("Chrome output does not contain #debug-output")
        result = html.unescape(match.group(1)).strip()
        if result:
            break
        if attempt + 1 < attempts:
            print("Chrome returned before the debug scenario completed; retrying", file=sys.stderr)
    if not result:
        raise RuntimeError("Frontend debug scenario did not complete after {} attempts".format(attempts))
    payload = json.loads(result)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def viewer_hash(**overrides):
    values = {
        "v": 1, "lat": 39.35, "lng": -0.55, "z": 8,
        "from": 2026, "to": 2026, "src": "icv,sigif,effis",
        "province": "all", "min_area": 0, "gif": 0,
    }
    values.update(overrides)
    return urlencode(values)


def validate(name, payload):
    final = payload["final"]
    require(final["level"] in ("overview", "regional", "local"), name + ": level")
    require(final["visibleFireCount"] <= final["visiblePerimeterCount"], name + ": fire/perimeter counts")
    require(len(final["activeAssetUrls"]) == len(set(final["activeAssetUrls"])), name + ": duplicate assets")


def main():
    args = parse_args()
    root = repository_root()
    reused = find_reused_case(root)
    scenarios = {
        "initial_cv": {},
        "castellon": {"view": "castellon"},
        "valencia": {"view": "valencia"},
        "alicante": {"view": "alicante"},
        "scope_change_alicante": {"scenario": "scope-change", "target_scope": "alicante"},
        "mariola_font_roja": {"view": "mariola_font_roja"},
        "full_period": {"from": 1993, "to": 2026},
        "single_year": {"from": 2024, "to": 2024},
        "gif_only": {"from": 2024, "to": 2024, "gif": 1},
        "zoom_transition": {
            "scenario": "zoom-transition",
            "view": "valencia",
            "province": "valencia",
        },
        "year_transition": {"scenario": "year-transition"},
        "histogram_year_1994": {"scenario": "histogram-year", "target_year": 1994},
        "municipality_fit_elx": {"view": "alicante", "scenario": "municipality-fit", "target_municipality": "03065"},
        "municipality_fit_single": {"view": "alicante", "from": 1994, "to": 1994, "scenario": "municipality-fit", "target_municipality": "03002"},
        "municipality_fit_empty": {"view": "alicante", "from": 1994, "to": 1994, "min_area": 1000, "scenario": "municipality-fit", "target_municipality": "03065"},
        "fire_2024al0005": {
            "view": "alicante",
            "from": 2024,
            "to": 2024,
            "select_fire": "gva:pif-cv:2024AL0005",
        },
        "ibi_sigif_2025": {
            "view": "alicante", "from": 2025, "to": 2025,
            "select_entity": "sigif:gva:2025:5db6d62db268826e197c:1",
        },
        "ibi_effis_history": {
            "view": "alicante", "from": 2025, "to": 2025,
            "point_geometry": "effis:rda:275862:f45dbca428aed922",
        },
        "nules_2026": {
            "view": "castellon", "from": 2026, "to": 2026,
            "select_entity": "effis:rda:570518:3f4a4c1708631c20",
        },
        "tirig_2026": {
            "view": "castellon", "from": 2026, "to": 2026,
            "select_entity": "effis:rda:612812:70214e1f449570a9",
        },
        "sources_icv_only_2025": {
            "from": 2025, "to": 2025, "sources": "icv",
        },
        "reused_geometry_point": {
            "view": reused["province"],
            "from": reused["year"],
            "to": reused["year"],
            "select_fire": reused["fire_id"],
            "point_geometry": reused["geometry_id"],
        },
        "permalink_1994_elx_cause_selection": {
            "__hash": viewer_hash(lat=38.27, lng=-0.70, z=8, **{
                "from": 1994, "to": 1994, "src": "icv", "province": "alicante",
                "municipality": "03065", "cause": "intentional",
                "entity": "gva:pif-cv:1994AL0039", "geometry": "gva:geometry:1994:2:1422",
            })
        },
        "permalink_2026_effis": {"__hash": viewer_hash(src="effis")},
        "permalink_gif": {"__hash": viewer_hash(**{"from": 2024, "to": 2024, "src": "icv", "gif": 1})},
        "permalink_minimum_area": {"__hash": viewer_hash(**{"from": 2024, "to": 2024, "src": "icv", "min_area": 100})},
        "permalink_invalid_ignored": {"__hash": "v=1&lat=999&z=99&from=1900&to=2999&src=not-a-source&province=moon&unknown=value"},
        "share_view": {"scenario": "share"},
        "share_selected_geometry": {
            "view": "alicante", "from": 1994, "to": 1994, "scenario": "share",
            "click_geometry": "gva:geometry:1994:2:1422",
        },
        "share_selected_multi_geometry": {
            "view": "alicante", "from": 2024, "to": 2024, "scenario": "share",
            "click_geometry": "gva:geometry:2024:121:13606",
        },
    }
    server_root = root.parent
    handler = lambda *items, **kwargs: QuietHandler(
        *items, directory=str(server_root), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = "http://127.0.0.1:{}/{}/index.html".format(
        server.server_port, root.name
    )
    results = {}
    try:
        for name, query in scenarios.items():
            fragment = query.get("__hash", "")
            parameters = {"debug": 1, **{key: value for key, value in query.items() if key != "__hash"}}
            payload = chrome_snapshot(args.chrome, base_url + "?" + urlencode(parameters) + ("#" + fragment if fragment else ""))
            validate(name, payload)
            results[name] = payload
        generated = results["permalink_1994_elx_cause_selection"]["final"]
        reloaded = chrome_snapshot(args.chrome, base_url + "?debug=1" + generated["permalinkHash"])
        validate("permalink_new_session_reload", reloaded)
        results["permalink_new_session_reload"] = reloaded
        shared = results["share_selected_geometry"]["final"]
        shared_reloaded = chrome_snapshot(args.chrome, base_url + "?debug=1" + shared["permalinkHash"])
        validate("shared_selection_new_session", shared_reloaded)
        results["shared_selection_new_session"] = shared_reloaded
        shared_multi = results["share_selected_multi_geometry"]["final"]
        shared_multi_reloaded = chrome_snapshot(args.chrome, base_url + "?debug=1" + shared_multi["permalinkHash"])
        validate("shared_multi_selection_new_session", shared_multi_reloaded)
        results["shared_multi_selection_new_session"] = shared_multi_reloaded
        mobile = chrome_snapshot(
            args.chrome, base_url + "?" + urlencode({"debug": 1}), "390,844"
        )
        validate("mobile_initial", mobile)
        results["mobile_initial"] = mobile
    finally:
        server.shutdown()
        server.server_close()

    initial = results["initial_cv"]["final"]
    require(initial["level"] == "overview", "Initial view must use overview")
    require(initial["activeAssetCount"] == 16, "Initial view must request the complete manifested period")
    require(initial["loader"]["requests"] == 19, "Initial requests: manifest, ICV attributes, candidates and 16 data assets")
    require(initial["years"] == {"from": 1993, "to": 2026}, "Initial full period")
    require(initial["visibleSigifRecordCount"] == 424, "All SIGIF records")
    require(initial["visibleEffisPerimeterCount"] == 25, "All EFFIS perimeters")
    require(initial["visibleIcvFireCount"] == 13738, "All ICV fires")
    require(initial["sigifLegendVisible"] and initial["sourceSeparationHelpVisible"], "Development SIGIF legend/help")
    require(initial["shareButtonVisible"] and initial["shareIconVisible"], "Development share button and SVG icon")
    require(not initial["territoryPanelPresent"], "The former territory panel must be absent")
    require(initial["scopeOptions"] == [{"value": "all", "label": "Todo el País Valencià"}, {"value": "castellon", "label": "Castelló"}, {"value": "valencia", "label": "València"}, {"value": "alicante", "label": "Alacant"}], "Canonical scope options")
    require(initial["histogramBarCount"] == 34 and initial["timelineComplete"], "Complete 1993-2026 histogram")
    require("cobertura incompleta" in initial["coverageText"], "2026 incomplete coverage visible")

    for province in ("castellon", "valencia", "alicante"):
        final = results[province]["final"]
        require(final["activeProvinces"] == [province], province + ": province")
        require(final["activeAssetCount"] == 8, province + ": four ICV blocks and four recent assets")
    scope = results["scope_change_alicante"]["scope"]
    require(scope["provinceFilter"] == "alicante" and scope["activeProvinces"] == ["alicante"], "Integrated scope control filters Alicante")
    require(any(item["value"] == "03065" for item in scope["availableMunicipalities"]), "Alicante scope contains Elx")
    require(all(not item["value"] or item["value"].startswith("03") or item["value"].startswith("raw:alicante:") for item in scope["availableMunicipalities"]), "Municipality selector is limited to Alicante")

    pilot = results["mariola_font_roja"]["final"]
    require(pilot["level"] == "local", "Pilot must use local geometry")
    require(pilot["activeProvinces"] == ["alicante"], "Pilot province")
    require(not pilot["mariolaPrimaryAccess"], "Mariola must not be a primary UI access")

    full = results["full_period"]["final"]
    require(full["activeAssetCount"] == 16, "Full period uses 12 ICV + 4 recent assets")
    require(full["visiblePerimeterCount"] == 13764, "Full ICV + EFFIS perimeter count")
    require(full["visibleFireCount"] == 13738, "Full fire count")

    histogram = results["histogram_year_1994"]["histogram"]
    require(histogram["years"] == {"from": 1994, "to": 1994}, "Histogram click selects one year")
    require(histogram["histogramBarCount"] == 34 and histogram["histogramSelectedYears"] == [1994], "Histogram remains visible after selection")

    gif = results["gif_only"]["final"]
    require(gif["visibleFireCount"] > 0, "GIF filter should have results")
    require(gif["visibleFireCount"] == gif["visibleGifCount"], "GIF filter correctness")

    levels = results["zoom_transition"]["levels"]
    require([item["level"] for item in levels] == ["overview", "regional", "local"], "Zoom levels")
    perimeter_counts = {item["visiblePerimeterCount"] for item in levels}
    require(len(perimeter_counts) == 1, "Zoom transition duplicated/lost perimeters")

    years = results["year_transition"]["years"]
    require([item["years"]["from"] for item in years] == [2024, 2025, 2026], "Year transition order")
    require(years[0]["visibleIcvFireCount"] > 0 and years[0]["visibleSigifRecordCount"] == 0, "2024 ICV only")
    require(years[1]["visibleIcvFireCount"] == 0 and years[1]["visibleSigifRecordCount"] > 0 and years[1]["visibleEffisPerimeterCount"] > 0, "2025 recent sources")
    require(years[2]["visibleIcvFireCount"] == 0 and years[2]["visibleSigifRecordCount"] > 0 and years[2]["visibleEffisPerimeterCount"] > 0, "2026 recent sources")

    selected = results["fire_2024al0005"]["selection"]
    require(selected["selectedVisibleGeometryCount"] == 2, "2024AL0005 geometry count")
    require(selected["visibleFireCount"] < selected["visiblePerimeterCount"], "Distinct counts")

    ibi = results["ibi_sigif_2025"]["selection"]
    require(ibi["selectedCandidateStrengths"] == ["strong_candidate"], "Ibi strong candidate")
    require("Score 90/100" in ibi["detailsText"], "Ibi candidate score")
    require(ibi["visibleSigifRecordCount"] > 0, "Ibi keeps SIGIF visible")
    require(ibi["visibleEffisPerimeterCount"] > 0, "Ibi keeps EFFIS visible and separate")

    ibi_history = results["ibi_effis_history"]["point"]
    require(ibi_history["history"]["effisPerimeterCount"] >= 1, "EFFIS point history")

    for case in ("nules_2026", "tirig_2026"):
        selected_recent = results[case]["selection"]
        require("cobertura termina el 30/06/2026" in selected_recent["detailsText"], case + ": cutoff caveat")

    icv_only = results["sources_icv_only_2025"]["final"]
    require(icv_only["activeSources"] == ["icv"], "Source toggle state")
    require(icv_only["activeAssetCount"] == 0, "No ICV assets in 2025")
    require(icv_only["loadedGeometryCount"] == 0, "No mixed source fallback")
    require(not any("candidates-weak" in url for url in initial["loader"]["cachedUrls"]), "Weak candidates not loaded by default")

    reused_result = results["reused_geometry_point"]["point"]
    require(reused_result["history"]["fireCount"] >= 1, "Point history fire count")
    require(reused_result["history"]["reused"], "Point history reuse warning")

    elx_fit = results["municipality_fit_elx"]["afterMunicipalityFit"]
    require(elx_fit["municipalityFit"]["status"] == "fit-visible-perimeters" and elx_fit["municipalityFit"]["perimeterCount"] > 1, "Elx fits its visible perimeters")
    require(elx_fit["municipalityFit"]["minimumRenderedPaddingPx"] >= 35, "Elx fit keeps visual padding")
    require(elx_fit["center"] != results["municipality_fit_elx"]["beforeMunicipalityFit"]["center"], "Elx changes the map framing")
    require(results["municipality_fit_elx"]["afterMunicipalityRefresh"]["center"] == elx_fit["center"], "Progressive detail refresh does not refit Elx")
    single_fit = results["municipality_fit_single"]["afterMunicipalityFit"]["municipalityFit"]
    require(single_fit["perimeterCount"] == 1 and single_fit["zoom"] <= single_fit["maxZoom"] == 13, "Single-perimeter municipality avoids extreme zoom")
    empty_before = results["municipality_fit_empty"]["beforeMunicipalityFit"]
    empty_after = results["municipality_fit_empty"]["afterMunicipalityFit"]
    require(empty_after["municipalityFit"]["status"] == "no-visible-perimeters" and empty_after["center"] == empty_before["center"] and empty_after["zoom"] == empty_before["zoom"], "Municipality without visible perimeters keeps the view")

    permalink = results["permalink_1994_elx_cause_selection"]["final"]
    require(permalink["years"] == {"from": 1994, "to": 1994}, "Permalink year restore")
    require(permalink["municipalityFilter"] == "03065", "Permalink municipality ID restore")
    require(permalink["causeFilter"] == "intentional", "Permalink cause restore")
    require(permalink["selectedEntityId"] == "gva:pif-cv:1994AL0039" and permalink["hashRestored"], "Permalink selection restore")
    require(permalink["selectedGeometryId"] == "gva:geometry:1994:2:1422" and permalink["selectedGeometryHighlighted"] and permalink["detailsSelectionVisible"], "Permalink restores highlighted geometry and details")
    require(permalink["selectionPopupVisible"] and permalink["selectionPopupDomVisible"] and permalink["selectionPopupGeometryId"] == permalink["selectedGeometryId"], "Permalink restores the exact geometry popup in the map DOM")
    require(abs(permalink["center"]["lat"] - 38.27) < 0.00002 and abs(permalink["center"]["lng"] + 0.70) < 0.00002 and permalink["zoom"] == 8, "Municipality permalink preserves shared center and zoom")
    require(sum(item["label"] == "Elx" for item in permalink["availableMunicipalities"]) == 1, "Elx canonical option")
    require(results["permalink_2026_effis"]["final"]["activeSources"] == ["effis"], "EFFIS permalink source restore")
    require(results["permalink_gif"]["final"]["gifOnly"], "GIF permalink restore")
    require(results["permalink_minimum_area"]["final"]["minimumArea"] == 100, "Minimum area permalink restore")
    reloaded = results["permalink_new_session_reload"]["final"]
    for key in ("years", "activeSources", "provinceFilter", "municipalityFilter", "causeFilter", "minimumArea", "gifOnly", "selectedEntityId", "selectedGeometryId", "zoom"):
        require(reloaded[key] == permalink[key], "New-session permalink mismatch: " + key)
    require(abs(reloaded["center"]["lat"] - permalink["center"]["lat"]) < 0.00002 and abs(reloaded["center"]["lng"] - permalink["center"]["lng"]) < 0.00002, "New-session center mismatch")
    shared = results["share_selected_geometry"]["clickedSelection"]
    shared_reloaded = results["shared_selection_new_session"]["final"]
    require(shared["selectedGeometryHighlighted"] and shared["detailsSelectionVisible"], "Clicked geometry is highlighted before sharing")
    for key in ("years", "activeSources", "provinceFilter", "selectedEntityId", "selectedGeometryId", "zoom"):
        require(shared_reloaded[key] == shared[key], "Shared-selection mismatch: " + key)
    require(shared_reloaded["selectedGeometryHighlighted"] and shared_reloaded["detailsSelectionVisible"] and shared_reloaded["selectionPopupVisible"] and shared_reloaded["selectionPopupDomVisible"], "Shared geometry, details and popup restored visually")
    require(shared_reloaded["selectionPopupGeometryId"] == shared["selectedGeometryId"], "Shared popup belongs to the selected geometry")
    multi = results["share_selected_multi_geometry"]["clickedSelection"]
    multi_reloaded = results["shared_multi_selection_new_session"]["final"]
    require(multi["selectedVisibleGeometryCount"] == 2, "Acceptance fire exposes two geometries")
    require(multi_reloaded["selectedGeometryId"] == "gva:geometry:2024:121:13606" and multi_reloaded["selectionPopupGeometryId"] == "gva:geometry:2024:121:13606", "Multi-geometry permalink opens the exact requested geometry")
    require(multi_reloaded["selectedGeometryHighlighted"] and multi_reloaded["detailsSelectionVisible"] and multi_reloaded["selectionPopupVisible"] and multi_reloaded["selectionPopupDomVisible"], "Multi-geometry permalink restores popup, highlight and details")
    invalid = results["permalink_invalid_ignored"]["final"]
    require(invalid["years"] == {"from": 1993, "to": 2026} and invalid["activeSources"] == ["icv", "sigif", "effis"], "Invalid hash values ignored with full-period fallback")
    require(bool(results["share_view"]["share"]["feedback"]), "Share action gives feedback")

    mobile = results["mobile_initial"]["final"]
    require(mobile["mobileLayout"], "Mobile media query")
    require(mobile["activeAssetCount"] == 16 and mobile["years"] == {"from": 1993, "to": 2026}, "Mobile full-period initial load")

    summary = {
        "schema_version": 1,
        "status": "passed",
        "github_pages_subpath_tested": "/{}/".format(root.name),
        "reused_case": reused,
        "scenario_count": len(results),
        "initial_data_requests": initial["loader"]["requests"],
        "initial_geometry_requests": initial["activeAssetCount"],
        "initial_visible_fires": initial["visibleFireCount"],
        "initial_visible_perimeters": initial["visiblePerimeterCount"],
        "full_period_visible_fires": full["visibleFireCount"],
        "full_period_visible_perimeters": full["visiblePerimeterCount"],
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".part")
    temporary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(args.output))
    print(args.output)


if __name__ == "__main__":
    main()
