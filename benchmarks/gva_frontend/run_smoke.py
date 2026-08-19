#!/usr/bin/env python3
"""Exercise the CV-1.5 frontend in Chrome under a GitHub Pages-like path."""

import argparse
import html
import json
import os
import re
import statistics
import subprocess
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


def chrome_snapshot(chrome, url, window_size="1440,900"):
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
    if not result:
        raise RuntimeError("Frontend debug scenario did not complete")
    payload = json.loads(result)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def require(condition, message):
    if not condition:
        raise AssertionError(message)


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
            parameters = {"debug": 1, **query}
            payload = chrome_snapshot(
                args.chrome, base_url + "?" + urlencode(parameters)
            )
            validate(name, payload)
            results[name] = payload
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
    require(initial["activeAssetCount"] == 2, "Initial view must request SIGIF + EFFIS 2026")
    require(initial["loader"]["requests"] == 4, "Initial requests: manifest, candidates and two data assets")
    require(initial["years"] == {"from": 2026, "to": 2026}, "Initial year")
    require(initial["visibleSigifRecordCount"] == 143, "SIGIF 2026 records")
    require(initial["visibleEffisPerimeterCount"] == 16, "EFFIS 2026 perimeters")
    require("cobertura incompleta" in initial["coverageText"], "2026 incomplete coverage visible")

    for province in ("castellon", "valencia", "alicante"):
        final = results[province]["final"]
        require(final["activeProvinces"] == [province], province + ": province")
        require(final["activeAssetCount"] == 2, province + ": two recent statewide assets")

    pilot = results["mariola_font_roja"]["final"]
    require(pilot["level"] == "local", "Pilot must use local geometry")
    require(pilot["activeProvinces"] == ["alicante"], "Pilot province")

    full = results["full_period"]["final"]
    require(full["activeAssetCount"] == 16, "Full period uses 12 ICV + 4 recent assets")
    require(full["visiblePerimeterCount"] == 13764, "Full ICV + EFFIS perimeter count")
    require(full["visibleFireCount"] == 13738, "Full fire count")

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

    mobile = results["mobile_initial"]["final"]
    require(mobile["mobileLayout"], "Mobile media query")
    require(mobile["activeAssetCount"] == 2, "Mobile progressive recent load")

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
