#!/usr/bin/env python3
"""Exercise the public EGIF + ICV + EFFIS profile under the Pages subpath."""

import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

from run_smoke import QuietHandler, chrome_snapshot, require, validate, viewer_hash


EXPECTED_ICV_ATTRIBUTION = (
    "Incendios forestales de la Comunitat Valenciana (1993–2024) "
    "CC BY 4.0, Generalitat. Datos transformados para su visualización "
    "mediante reproyección, selección de atributos, particionado y "
    "simplificación geométrica."
)


def main():
    root = Path(__file__).resolve().parents[2]
    runtime = root / "data/web/gva/manifest.json"
    development = runtime.read_bytes()
    handler = lambda *items, **kwargs: QuietHandler(*items, directory=str(root.parent), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/{root.name}/index.html"
    scenarios = {
        "initial_full_period": {},
        "year_1968": {"from": 1968, "to": 1968, "sources": "egif"},
        "year_1975": {"from": 1975, "to": 1975, "sources": "egif"},
        "year_1986": {"from": 1986, "to": 1986, "sources": "egif"},
        "year_1992": {"from": 1992, "to": 1992, "sources": "egif"},
        "year_1993": {"from": 1993, "to": 1993},
        "year_1994": {"from": 1994, "to": 1994},
        "year_2024": {"from": 2024, "to": 2024},
        "year_2025": {"from": 2025, "to": 2025},
        "year_2026": {"from": 2026, "to": 2026},
        "full_period": {"from": 1968, "to": 2026},
        "historical_transition": {"scenario": "historical-transition"},
        "egif_only": {"from": 1968, "to": 1992, "sources": "egif"},
        "egif_alicante": {"from": 1968, "to": 1992, "sources": "egif", "view": "alicante"},
        "egif_1992_gif": {"from": 1992, "to": 1992, "sources": "egif", "gif": 1},
        "egif_cause": {"__hash": viewer_hash(**{"from": 1968, "to": 1992, "src": "egif", "cause": "accidental"})},
        "egif_municipality": {"__hash": viewer_hash(lat=38.82, lng=-0.11, z=9, **{"from": 1986, "to": 1986, "src": "egif", "province": "alicante", "municipality": "03102", "entity": "egif-record:1986030531"})},
        "egif_municipality_fit": {"view": "alicante", "from": 1986, "to": 1986, "sources": "egif", "scenario": "municipality-fit", "target_municipality": "03102"},
        "egif_point_history": {"from": 1986, "to": 1986, "sources": "egif", "point": "-0.11,38.82"},
        "castellon_2024": {"view": "castellon", "from": 2024, "to": 2024},
        "valencia_2024": {"view": "valencia", "from": 2024, "to": 2024},
        "alicante_2024": {"view": "alicante", "from": 2024, "to": 2024},
        "scope_change_alicante": {"scenario": "scope-change", "target_scope": "alicante"},
        "mariola_2024": {"view": "mariola_font_roja", "from": 2024, "to": 2024},
        "zoom_transition": {"scenario": "zoom-transition", "view": "valencia", "from": 2024, "to": 2024},
        "year_transition": {"scenario": "year-transition"},
        "histogram_year_1994": {"scenario": "histogram-year", "target_year": 1994},
        "municipality_fit_elx": {"view": "alicante", "scenario": "municipality-fit", "target_municipality": "03065"},
        "municipality_fit_single": {"view": "alicante", "from": 1994, "to": 1994, "scenario": "municipality-fit", "target_municipality": "03002"},
        "municipality_fit_empty": {"view": "alicante", "from": 1994, "to": 1994, "min_area": 1000, "scenario": "municipality-fit", "target_municipality": "03065"},
        "ibi_effis_history": {"view": "alicante", "from": 2025, "to": 2025,
                              "point_geometry": "effis:rda:275862:f45dbca428aed922"},
        "nules_2026": {"view": "castellon", "from": 2026, "to": 2026,
                       "select_entity": "effis:rda:570518:3f4a4c1708631c20"},
        "tirig_2026": {"view": "castellon", "from": 2026, "to": 2026,
                       "select_entity": "effis:rda:612812:70214e1f449570a9"},
        "icv_only_2025": {"from": 2025, "to": 2025, "sources": "icv"},
        "permalink_1994_elx": {"__hash": viewer_hash(lat=38.27, lng=-0.70, z=8, **{
            "from": 1994, "to": 1994, "src": "icv", "province": "alicante",
            "municipality": "03065", "cause": "intentional",
            "entity": "gva:pif-cv:1994AL0039", "geometry": "gva:geometry:1994:2:1422"})},
        "permalink_2026_effis": {"__hash": viewer_hash(src="effis")},
        "permalink_gif": {"__hash": viewer_hash(**{"from": 2024, "to": 2024, "src": "icv", "gif": 1})},
        "permalink_minimum_area": {"__hash": viewer_hash(**{"from": 2024, "to": 2024, "src": "icv", "min_area": 100})},
        "permalink_invalid": {"__hash": "v=1&lat=999&z=99&from=1900&to=2999&src=sigif&province=moon&unknown=value"},
        "share_selected_geometry": {
            "view": "alicante", "from": 1994, "to": 1994, "scenario": "share",
            "click_geometry": "gva:geometry:1994:2:1422",
        },
        "share_selected_multi_geometry": {
            "view": "alicante", "from": 2024, "to": 2024, "scenario": "share",
            "click_geometry": "gva:geometry:2024:121:13606",
        },
    }
    results = {}
    try:
        subprocess.run(
            [sys.executable, str(root / "scripts/build_frontend_profile.py"),
             "--profile", "public", "--output", str(runtime)],
            check=True, stdout=subprocess.PIPE, text=True,
        )
        manifest = json.loads(runtime.read_text(encoding="utf-8"))
        serialized = runtime.read_text(encoding="utf-8").lower()
        require(set(manifest["sources"]) == {"egif", "icv", "effis"}, "Public source set")
        require(manifest["publication_guard"]["all_included_sources_publishable"], "Publication guard")
        require("sigif" not in serialized and "candidate" not in serialized, "No blocked source references")

        for name, query in scenarios.items():
            fragment = query.get("__hash", "")
            parameters = {"debug": 1, **{key: value for key, value in query.items() if key != "__hash"}}
            payload = chrome_snapshot("/usr/bin/google-chrome", base + "?" + urlencode(parameters) + ("#" + fragment if fragment else ""))
            validate(name, payload)
            results[name] = payload
        generated = results["permalink_1994_elx"]["final"]
        reloaded = chrome_snapshot("/usr/bin/google-chrome", base + "?debug=1" + generated["permalinkHash"])
        validate("permalink_new_session_reload", reloaded)
        results["permalink_new_session_reload"] = reloaded
        shared = results["share_selected_geometry"]["final"]
        shared_reloaded = chrome_snapshot("/usr/bin/google-chrome", base + "?debug=1" + shared["permalinkHash"])
        validate("shared_selection_new_session", shared_reloaded)
        results["shared_selection_new_session"] = shared_reloaded
        shared_multi = results["share_selected_multi_geometry"]["final"]
        shared_multi_reloaded = chrome_snapshot("/usr/bin/google-chrome", base + "?debug=1" + shared_multi["permalinkHash"])
        validate("shared_multi_selection_new_session", shared_multi_reloaded)
        results["shared_multi_selection_new_session"] = shared_multi_reloaded
        mobile = chrome_snapshot("/usr/bin/google-chrome", base + "?debug=1", "390,844")
        validate("mobile_initial", mobile)
        results["mobile_initial"] = mobile

        initial = results["initial_full_period"]["final"]
        require(initial["profile"] == "public", "Public profile marker")
        require(initial["activeSources"] == ["egif", "icv", "effis"], "Public source controls")
        require(initial["sourceControlIds"] == ["egif", "icv", "effis"], "Public includes EGIF and excludes SIGIF")
        require(not initial["sigifLegendVisible"] and not initial["sourceSeparationHelpVisible"], "No public SIGIF legend/help")
        require(initial["shareButtonVisible"] and initial["shareIconVisible"], "Public share button and SVG icon")
        require(initial["visibleSigifRecordCount"] == 0, "SIGIF excluded")
        require(initial["visibleEgifRecordCount"] == 9175, "EGIF 1968-1992 reports")
        require(initial["visibleEffisPerimeterCount"] == 25, "EFFIS 2025-2026")
        require(initial["visibleIcvFireCount"] == 13738, "ICV full period")
        require(initial["activeAssetCount"] == 15, "EGIF, twelve ICV and two EFFIS assets at start")
        require(initial["loader"]["requests"] == 17, "Initial manifest, EGIF, ICV attributes and fourteen geometry assets")
        require(initial["years"] == {"from": 1968, "to": 2026}, "Public initial full period")
        require(not initial["territoryPanelPresent"], "No former territory panel")
        require(initial["scopeOptions"] == [{"value": "all", "label": "Todo el País Valencià"}, {"value": "castellon", "label": "Castelló"}, {"value": "valencia", "label": "València"}, {"value": "alicante", "label": "Alacant"}], "Public scope options")
        require(initial["histogramBarCount"] == 59 and initial["timelineComplete"], "Public complete histogram")
        require("SIGIF" not in initial["coverageText"], "Public coverage hides SIGIF")
        require(EXPECTED_ICV_ATTRIBUTION in initial["methodologyText"], "Exact ICV attribution")
        require("Copernicus EMS / EFFIS" in initial["methodologyText"], "EFFIS attribution")
        require("Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico." in initial["methodologyText"], "EGIF attribution")

        historical_expected = {"1968": 113, "1975": 256, "1986": 385, "1992": 770}
        for year, expected in historical_expected.items():
            final = results["year_" + year]["final"]
            require(final["visibleEgifRecordCount"] == expected and final["loadedGeometryCount"] == 0 and final["visiblePerimeterCount"] == 0, year + " has EGIF reports and zero geometry")
            require("No existen perímetros individuales fiables" in final["statusText"], year + " explains the empty map")
        transition = results["historical_transition"]["years"]
        require([item["years"]["from"] for item in transition] == [1968, 1975, 1986, 1992, 1993], "Public historical transition")
        require(transition[-2]["visibleEgifRecordCount"] == 770 and transition[-1]["visibleEgifRecordCount"] == 0 and transition[-1]["visibleIcvFireCount"] > 0, "Public 1992 to 1993 source boundary")
        require(results["egif_only"]["final"]["visibleEgifRecordCount"] == 9175, "Public EGIF only")
        require(results["egif_alicante"]["final"]["visibleEgifRecordCount"] == 2514, "Public historical Alicante")
        require(results["egif_1992_gif"]["final"]["visibleEgifRecordCount"] == 9, "Public 1992 forest GIF")
        require(results["egif_cause"]["final"]["visibleEgifRecordCount"] == 256, "Public EGIF cause mapping")
        historical_municipality = results["egif_municipality"]["final"]
        require(historical_municipality["municipalityFilter"] == "03102" and historical_municipality["visibleEgifRecordCount"] > 0 and historical_municipality["selectedGeometryId"] is None, "Public historical municipality without invented geometry")
        require(historical_municipality["detailsSelectionVisible"] and not historical_municipality["selectionPopupVisible"], "Public EGIF report details without popup")
        historical_fit = results["egif_municipality_fit"]
        require(historical_fit["afterMunicipalityFit"]["municipalityFit"]["status"] == "historical-records-without-geometry" and historical_fit["afterMunicipalityFit"]["center"] == historical_fit["beforeMunicipalityFit"]["center"], "Public historical municipality keeps map view without invented location")
        require("no tienen geometría individual fiable" in results["egif_point_history"]["point"]["pointHistoryText"], "Public point history excludes EGIF")

        for year in ("1993", "1994", "2024"):
            final = results["year_" + year]["final"]
            require(final["visibleIcvFireCount"] > 0, year + " uses ICV")
            require(final["visibleEffisPerimeterCount"] == 0, year + " excludes EFFIS")
        require(results["year_2025"]["final"]["visibleEffisPerimeterCount"] == 9, "EFFIS 2025")
        require(results["year_2026"]["final"]["visibleEffisPerimeterCount"] == 16, "EFFIS 2026")

        years = results["year_transition"]["years"]
        require([item["years"]["from"] for item in years] == [2024, 2025, 2026], "Year order")
        require(years[0]["visibleIcvFireCount"] > 0 and years[0]["visibleEffisPerimeterCount"] == 0, "2024 ICV")
        require(years[1]["visibleIcvFireCount"] == 0 and years[1]["visibleEffisPerimeterCount"] == 9, "2025 EFFIS")
        require(years[2]["visibleIcvFireCount"] == 0 and years[2]["visibleEffisPerimeterCount"] == 16, "2026 EFFIS")

        full = results["full_period"]["final"]
        require(full["activeAssetCount"] == 15, "Full period uses EGIF + 12 ICV + 2 EFFIS assets")
        require(full["visiblePerimeterCount"] == 13764, "Full public perimeter count")
        require(full["visibleFireCount"] == 13738, "Full ICV fire count")

        histogram = results["histogram_year_1994"]["histogram"]
        require(histogram["years"] == {"from": 1994, "to": 1994}, "Public histogram click")
        require(histogram["histogramBarCount"] == 59 and histogram["histogramSelectedYears"] == [1994], "Public histogram remains visible")

        for province in ("castellon", "valencia", "alicante"):
            require(results[province + "_2024"]["final"]["activeProvinces"] == [province], province + " filter")
        scope = results["scope_change_alicante"]["scope"]
        require(scope["provinceFilter"] == "alicante" and scope["activeProvinces"] == ["alicante"], "Public integrated scope filters Alicante")
        require(any(item["value"] == "03065" for item in scope["availableMunicipalities"]), "Public Alicante scope contains Elx")
        require(all(not item["value"] or item["value"].startswith("03") or item["value"].startswith("raw:alicante:") for item in scope["availableMunicipalities"]), "Public municipalities limited to Alicante")
        require(results["mariola_2024"]["final"]["level"] == "local", "Mariola local level")
        require(not results["mariola_2024"]["final"]["mariolaPrimaryAccess"], "No primary Mariola control")
        levels = results["zoom_transition"]["levels"]
        require([item["level"] for item in levels] == ["overview", "regional", "local"], "Zoom levels")
        require(len({item["visiblePerimeterCount"] for item in levels}) == 1, "Zoom keeps geometry count")

        require(results["ibi_effis_history"]["point"]["history"]["effisPerimeterCount"] >= 1, "EFFIS point history")
        for case in ("nules_2026", "tirig_2026"):
            selection = results[case]["selection"]
            require("EFFIS · satelital provisional" in selection["detailsText"], case + " EFFIS details")
            require("SIGIF" not in selection["detailsText"], case + " no hidden source claim")
        require(results["icv_only_2025"]["final"]["loadedGeometryCount"] == 0, "No source fallback")
        require(results["mobile_initial"]["final"]["mobileLayout"], "Mobile responsive layout")
        require(results["mobile_initial"]["final"]["years"] == {"from": 1968, "to": 2026} and results["mobile_initial"]["final"]["activeAssetCount"] == 15 and results["mobile_initial"]["final"]["visibleEgifRecordCount"] == 9175, "Mobile public full-period initial load")
        elx_fit = results["municipality_fit_elx"]["afterMunicipalityFit"]
        require(elx_fit["municipalityFit"]["status"] == "fit-visible-perimeters" and elx_fit["municipalityFit"]["perimeterCount"] > 1, "Public Elx municipality fit")
        require(elx_fit["municipalityFit"]["minimumRenderedPaddingPx"] >= 35, "Public Elx fit padding")
        require(elx_fit["center"] != results["municipality_fit_elx"]["beforeMunicipalityFit"]["center"], "Public Elx changes framing")
        require(results["municipality_fit_elx"]["afterMunicipalityRefresh"]["center"] == elx_fit["center"], "Public progressive refresh does not refit Elx")
        single_fit = results["municipality_fit_single"]["afterMunicipalityFit"]["municipalityFit"]
        require(single_fit["perimeterCount"] == 1 and single_fit["zoom"] <= single_fit["maxZoom"] == 13, "Public single-perimeter municipality max zoom")
        empty_before = results["municipality_fit_empty"]["beforeMunicipalityFit"]
        empty_after = results["municipality_fit_empty"]["afterMunicipalityFit"]
        require(empty_after["municipalityFit"]["status"] == "no-visible-perimeters" and empty_after["center"] == empty_before["center"] and empty_after["zoom"] == empty_before["zoom"], "Public empty municipality fit is safe")
        permalink = results["permalink_1994_elx"]["final"]
        require(permalink["municipalityFilter"] == "03065" and permalink["causeFilter"] == "intentional", "Canonical public filters restored")
        require(permalink["selectedEntityId"] == "gva:pif-cv:1994AL0039" and permalink["selectedGeometryId"] == "gva:geometry:1994:2:1422", "Public entity and geometry restored")
        require(permalink["selectedGeometryHighlighted"] and permalink["detailsSelectionVisible"] and permalink["selectionPopupVisible"] and permalink["selectionPopupDomVisible"], "Public selection and popup visibly restored in the map DOM")
        require(permalink["selectionPopupGeometryId"] == permalink["selectedGeometryId"], "Public permalink popup uses exact geometry")
        require(abs(permalink["center"]["lat"] - 38.27) < 0.00002 and abs(permalink["center"]["lng"] + 0.70) < 0.00002 and permalink["zoom"] == 8, "Public municipality permalink preserves view")
        require(sum(item["label"] == "Elx" for item in permalink["availableMunicipalities"]) == 1, "One Elx option")
        require(results["permalink_2026_effis"]["final"]["activeSources"] == ["effis"], "Public EFFIS permalink")
        require(results["permalink_gif"]["final"]["gifOnly"], "Public GIF permalink")
        require(results["permalink_minimum_area"]["final"]["minimumArea"] == 100, "Public minimum area permalink")
        reloaded = results["permalink_new_session_reload"]["final"]
        for key in ("years", "activeSources", "provinceFilter", "municipalityFilter", "causeFilter", "minimumArea", "gifOnly", "selectedEntityId", "selectedGeometryId", "zoom"):
            require(reloaded[key] == permalink[key], "Public new-session permalink mismatch: " + key)
        require(reloaded["selectedGeometryHighlighted"] and reloaded["detailsSelectionVisible"], "Public new-session selection is visually restored")
        shared = results["share_selected_geometry"]["clickedSelection"]
        shared_reloaded = results["shared_selection_new_session"]["final"]
        require(shared["selectedGeometryHighlighted"] and shared["detailsSelectionVisible"], "Public clicked selection before share")
        for key in ("years", "activeSources", "provinceFilter", "selectedEntityId", "selectedGeometryId", "zoom"):
            require(shared_reloaded[key] == shared[key], "Public shared-selection mismatch: " + key)
        require(shared_reloaded["selectedGeometryHighlighted"] and shared_reloaded["detailsSelectionVisible"] and shared_reloaded["selectionPopupVisible"] and shared_reloaded["selectionPopupDomVisible"], "Public shared selection and popup visibly restored")
        require(shared_reloaded["selectionPopupGeometryId"] == shared["selectedGeometryId"], "Public shared popup uses exact geometry")
        multi = results["share_selected_multi_geometry"]["clickedSelection"]
        multi_reloaded = results["shared_multi_selection_new_session"]["final"]
        require(multi["selectedVisibleGeometryCount"] == 2, "Public acceptance fire has two geometries")
        require(multi_reloaded["selectedGeometryId"] == "gva:geometry:2024:121:13606" and multi_reloaded["selectionPopupGeometryId"] == "gva:geometry:2024:121:13606", "Public multi-geometry permalink opens exact geometry")
        require(multi_reloaded["selectedGeometryHighlighted"] and multi_reloaded["detailsSelectionVisible"] and multi_reloaded["selectionPopupVisible"] and multi_reloaded["selectionPopupDomVisible"], "Public multi-geometry selection fully restored")
        require(results["permalink_invalid"]["final"]["activeSources"] == ["egif", "icv", "effis"], "Invalid/blocked public source ignored")
        require(initial["loader"]["candidateCount"] == 0, "No candidates loaded")
        require(not any("sigif" in url.lower() or "candidate" in url.lower()
                        for url in initial["loader"]["cachedUrls"]), "No forbidden URLs")

        blocked = subprocess.run(
            [sys.executable, str(root / "scripts/build_frontend_profile.py"),
             "--profile", "public", "--include-source", "sigif",
             "--output", str(runtime.with_suffix(".blocked.json"))],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        require(blocked.returncode != 0, "Public build rejects SIGIF")
        print(json.dumps({
            "status": "passed",
            "scenario_count": len(results),
            "public_sources": initial["activeSources"],
            "initial_requests": initial["loader"]["requests"],
            "initial_response_bytes": initial["loader"]["responseBytes"],
            "initial_estimated_gzip_bytes": initial["loader"]["estimatedGzipBytes"],
            "initial_render_ms": initial["lastRender"]["renderMs"],
            "initial_app_elapsed_ms": initial["appElapsedMs"],
            "initial_heap_used_bytes": initial["heapUsedBytes"],
            "full_period_perimeters": full["visiblePerimeterCount"],
            "blocked_source_rejected": True,
        }, indent=2))
    finally:
        runtime.write_bytes(development)
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
