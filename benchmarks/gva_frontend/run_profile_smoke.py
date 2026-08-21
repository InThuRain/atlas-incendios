#!/usr/bin/env python3
"""Exercise the public ICV + EFFIS profile under the Pages subpath."""

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
        "initial_2026": {},
        "year_1993": {"from": 1993, "to": 1993},
        "year_1994": {"from": 1994, "to": 1994},
        "year_2024": {"from": 2024, "to": 2024},
        "year_2025": {"from": 2025, "to": 2025},
        "year_2026": {"from": 2026, "to": 2026},
        "full_period": {"from": 1993, "to": 2026},
        "castellon_2024": {"view": "castellon", "from": 2024, "to": 2024},
        "valencia_2024": {"view": "valencia", "from": 2024, "to": 2024},
        "alicante_2024": {"view": "alicante", "from": 2024, "to": 2024},
        "mariola_2024": {"view": "mariola_font_roja", "from": 2024, "to": 2024},
        "zoom_transition": {"scenario": "zoom-transition", "view": "valencia", "from": 2024, "to": 2024},
        "year_transition": {"scenario": "year-transition"},
        "ibi_effis_history": {"view": "alicante", "from": 2025, "to": 2025,
                              "point_geometry": "effis:rda:275862:f45dbca428aed922"},
        "nules_2026": {"view": "castellon", "from": 2026, "to": 2026,
                       "select_entity": "effis:rda:570518:3f4a4c1708631c20"},
        "tirig_2026": {"view": "castellon", "from": 2026, "to": 2026,
                       "select_entity": "effis:rda:612812:70214e1f449570a9"},
        "icv_only_2025": {"from": 2025, "to": 2025, "sources": "icv"},
        "permalink_1994_elx": {"__hash": viewer_hash(lat=38.27, lng=-0.70, z=8, **{
            "from": 1994, "to": 1994, "src": "icv", "province": "alicante",
            "municipality": "03065", "cause": "intentional"})},
        "permalink_2026_effis": {"__hash": viewer_hash(src="effis")},
        "permalink_gif": {"__hash": viewer_hash(**{"from": 2024, "to": 2024, "src": "icv", "gif": 1})},
        "permalink_minimum_area": {"__hash": viewer_hash(**{"from": 2024, "to": 2024, "src": "icv", "min_area": 100})},
        "permalink_invalid": {"__hash": "v=1&lat=999&z=99&from=1900&to=2999&src=sigif&province=moon&unknown=value"},
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
        require(set(manifest["sources"]) == {"icv", "effis"}, "Public source set")
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
        mobile = chrome_snapshot("/usr/bin/google-chrome", base + "?debug=1", "390,844")
        validate("mobile_initial", mobile)
        results["mobile_initial"] = mobile

        initial = results["initial_2026"]["final"]
        require(initial["profile"] == "public", "Public profile marker")
        require(initial["activeSources"] == ["icv", "effis"], "Public source controls")
        require(initial["sourceControlIds"] == ["icv", "effis"], "No public SIGIF control")
        require(not initial["sigifLegendVisible"] and not initial["sourceSeparationHelpVisible"], "No public SIGIF legend/help")
        require(initial["shareButtonVisible"], "Public share button")
        require(initial["visibleSigifRecordCount"] == 0, "SIGIF excluded")
        require(initial["visibleEffisPerimeterCount"] == 16, "EFFIS 2026")
        require(initial["visibleIcvFireCount"] == 0, "No ICV outside its period")
        require(initial["activeAssetCount"] == 1, "Only EFFIS 2026 geometry at start")
        require(initial["loader"]["requests"] == 2, "Initial manifest + EFFIS request")
        require("SIGIF" not in initial["coverageText"], "Public coverage hides SIGIF")
        require(EXPECTED_ICV_ATTRIBUTION in initial["methodologyText"], "Exact ICV attribution")
        require("Copernicus EMS / EFFIS" in initial["methodologyText"], "EFFIS attribution")

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
        require(full["activeAssetCount"] == 14, "Full period uses 12 ICV + 2 EFFIS assets")
        require(full["visiblePerimeterCount"] == 13764, "Full public perimeter count")
        require(full["visibleFireCount"] == 13738, "Full ICV fire count")

        for province in ("castellon", "valencia", "alicante"):
            require(results[province + "_2024"]["final"]["activeProvinces"] == [province], province + " filter")
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
        permalink = results["permalink_1994_elx"]["final"]
        require(permalink["municipalityFilter"] == "03065" and permalink["causeFilter"] == "intentional", "Canonical public filters restored")
        require(sum(item["label"] == "Elx" for item in permalink["availableMunicipalities"]) == 1, "One Elx option")
        require(results["permalink_2026_effis"]["final"]["activeSources"] == ["effis"], "Public EFFIS permalink")
        require(results["permalink_gif"]["final"]["gifOnly"], "Public GIF permalink")
        require(results["permalink_minimum_area"]["final"]["minimumArea"] == 100, "Public minimum area permalink")
        reloaded = results["permalink_new_session_reload"]["final"]
        for key in ("years", "activeSources", "provinceFilter", "municipalityFilter", "causeFilter", "minimumArea", "gifOnly", "zoom"):
            require(reloaded[key] == permalink[key], "Public new-session permalink mismatch: " + key)
        require(results["permalink_invalid"]["final"]["activeSources"] == ["icv", "effis"], "Invalid/blocked public source ignored")
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
