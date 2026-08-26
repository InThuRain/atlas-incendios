#!/usr/bin/env python3
"""Verify the deployed public atlas and representative v=1 permalinks."""

import argparse
import json
from pathlib import Path

from run_smoke import chrome_snapshot, require, validate, viewer_hash


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="https://inthurain.github.io/atlas-incendios/",
        help="Published Pages URL, including its repository subpath.",
    )
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def debug_url(base, fragment=""):
    separator = "&" if "?" in base else "?"
    return base + separator + "debug=1" + ("#" + fragment if fragment else "")


def main():
    args = parse_args()
    base = args.url.rstrip("/") + "/"
    fragments = {
        "1986_egif": viewer_hash(lat=39.35, lng=-0.55, z=8, **{
            "from": 1986, "to": 1986, "src": "egif",
        }),
        "1986_esfire30": viewer_hash(lat=39.35, lng=-0.55, z=8, **{
            "from": 1986, "to": 1986, "src": "esfire30",
            "entity": "esfire30:record:sha256:e8f9fb21948ca9b950c4d8bc61e2cbe555c235cfdf58cbe55b266da926fd887c",
            "geometry": "esfire30:geometry:sha256:455700a9f4f007088776840643a7cb4595ed6ba7c68ce48ed41320d38b935985",
        }),
        "1994_elx": viewer_hash(lat=38.27, lng=-0.70, z=8, **{
            "from": 1994, "to": 1994, "src": "icv", "province": "alicante",
            "municipality": "03065", "cause": "intentional",
            "entity": "gva:pif-cv:1994AL0039",
            "geometry": "gva:geometry:1994:2:1422",
        }),
        "2024_gif": viewer_hash(lat=39.40, lng=-0.45, z=7, **{
            "from": 2024, "to": 2024, "src": "icv", "gif": 1,
        }),
        "2026_effis": viewer_hash(lat=39.70, lng=-0.15, z=8, **{
            "from": 2026, "to": 2026, "src": "effis", "province": "castellon",
        }),
    }
    results = {
        "initial": chrome_snapshot(args.chrome, debug_url(base)),
        **{
            name: chrome_snapshot(args.chrome, debug_url(base, fragment))
            for name, fragment in fragments.items()
        },
        "historical_transition": chrome_snapshot(
            args.chrome, debug_url(base + "?scenario=historical-transition")
        ),
        "year_1984": chrome_snapshot(args.chrome, debug_url(base + "?from=1984&to=1984&sources=egif%2Cesfire30")),
        "year_1985": chrome_snapshot(args.chrome, debug_url(base + "?from=1985&to=1985&sources=egif%2Cesfire30")),
        "year_1991": chrome_snapshot(args.chrome, debug_url(base + "?from=1991&to=1991&sources=egif%2Cesfire30")),
        "egif_only": chrome_snapshot(
            args.chrome, debug_url(base, viewer_hash(**{
                "from": 1968, "to": 1992, "src": "egif",
            }))
        ),
        "egif_alicante": chrome_snapshot(
            args.chrome, debug_url(base, viewer_hash(**{
                "from": 1968, "to": 1992, "src": "egif", "province": "alicante",
            }))
        ),
        "egif_1992_gif": chrome_snapshot(
            args.chrome, debug_url(base, viewer_hash(**{
                "from": 1992, "to": 1992, "src": "egif", "gif": 1,
            }))
        ),
        "egif_cause": chrome_snapshot(
            args.chrome, debug_url(base, viewer_hash(**{
                "from": 1968, "to": 1992, "src": "egif", "cause": "accidental",
            }))
        ),
        "egif_municipality": chrome_snapshot(
            args.chrome, debug_url(base, viewer_hash(lat=38.82, lng=-0.11, z=9, **{
                "from": 1986, "to": 1986, "src": "egif", "province": "alicante",
                "municipality": "03102", "entity": "egif-record:1986030531",
            }))
        ),
        "egif_municipality_fit": chrome_snapshot(
            args.chrome,
            debug_url(base + "?scenario=municipality-fit&target_municipality=03102&view=alicante&from=1986&to=1986&sources=egif"),
        ),
        "egif_point_history": chrome_snapshot(
            args.chrome, debug_url(base + "?from=1986&to=1986&sources=egif&point=-0.11%2C38.82")
        ),
        "esfire30_point_history": chrome_snapshot(
            args.chrome, debug_url(base + "?view=valencia&from=1986&to=1986&sources=esfire30&point_geometry=esfire30%3Ageometry%3Asha256%3A455700a9f4f007088776840643a7cb4595ed6ba7c68ce48ed41320d38b935985")
        ),
        "sot_1986": chrome_snapshot(
            args.chrome, debug_url(base + "?from=1986&to=1986&sources=esfire30&select_entity=esfire30%3Arecord%3Asha256%3Ae8f9fb21948ca9b950c4d8bc61e2cbe555c235cfdf58cbe55b266da926fd887c")
        ),
        "marines_altura_1992": chrome_snapshot(
            args.chrome, debug_url(base + "?from=1992&to=1992&sources=esfire30&select_entity=esfire30%3Arecord%3Asha256%3Ab535436d08ed029420d3ef14c3a91951c0bed7dfa562a8c5e3df12d67d7cc46c")
        ),
        "municipality_fit_elx": chrome_snapshot(
            args.chrome,
            debug_url(base + "?scenario=municipality-fit&target_municipality=03065&view=alicante"),
        ),
        "histogram_1994": chrome_snapshot(
            args.chrome,
            debug_url(base + "?scenario=histogram-year&target_year=1994"),
        ),
        "multi_geometry": chrome_snapshot(args.chrome, debug_url(base, viewer_hash(
            lat=38.70, lng=-0.52, z=10, **{
                "from": 2024, "to": 2024, "src": "icv", "province": "alicante",
                "entity": "gva:pif-cv:2024AL0005",
                "geometry": "gva:geometry:2024:121:13606",
            }
        ))),
        "mobile": chrome_snapshot(args.chrome, debug_url(base), "390,844"),
    }
    shared_source = chrome_snapshot(
        args.chrome,
        debug_url(base + "?view=alicante&from=1994&to=1994&scenario=share&click_geometry=gva%3Ageometry%3A1994%3A2%3A1422"),
    )
    results["shared_source"] = shared_source
    results["shared_reload"] = chrome_snapshot(
        args.chrome, debug_url(base, shared_source["final"]["permalinkHash"].lstrip("#"))
    )
    for name, payload in results.items():
        validate(name, payload)

    initial = results["initial"]["final"]
    require(initial["profile"] == "public", "Deployed profile is not public")
    require(initial["sourceControlIds"] == ["egif", "esfire30", "icv", "effis"], "Unexpected source controls")
    require(initial["activeSources"] == ["egif", "esfire30", "icv", "effis"], "Unexpected initial sources")
    require(initial["years"] == {"from": 1968, "to": 2026}, "Initial full period missing")
    require(initial["histogramBarCount"] == 59 and initial["timelineComplete"], "Complete histogram missing")
    require(initial["loader"]["requests"] == 18, "Unexpected initial request count")
    require(initial["visibleEgifRecordCount"] == 9175, "EGIF history missing")
    require(initial["visibleIcvFireCount"] == 13738, "ICV history missing")
    require(initial["visibleEsfire30PerimeterCount"] == 710, "ESFire30 history missing")
    require(initial["visibleEffisPerimeterCount"] == 25, "EFFIS 2025-2026 missing")
    require(not initial["sigifLegendVisible"], "SIGIF leaked into public legend")
    require(initial["loader"]["candidateCount"] == 0, "Link candidates leaked into public data")
    require(not any("sigif" in url.lower() or "candidate" in url.lower() for url in initial["loader"]["cachedUrls"]), "Forbidden public asset URL")
    require("Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico." in initial["methodologyText"], "EGIF attribution missing")
    require("10.5281/zenodo.18449006" in initial["methodologyText"] and "Landsat" in initial["coverageText"] and "30 m" in initial["coverageText"], "ESFire30 attribution or method missing")
    require(not initial["mariolaPrimaryAccess"], "Mariola is still a primary access")

    historical = results["historical_transition"]["years"]
    require([item["years"]["from"] for item in historical] == [1968, 1975, 1986, 1992, 1993], "Historical transition order")
    for item in historical[:2]:
        require(item["visibleEgifRecordCount"] > 0 and item["loadedGeometryCount"] == 0, "Historical year invented geometry")
        require("No existen perímetros individuales fiables" in item["statusText"], "Historical empty-map explanation missing")
    require(historical[2]["visibleEgifRecordCount"] == 385 and historical[2]["visibleEsfire30PerimeterCount"] == 63, "1986 EGIF/ESFire30 separation failed")
    require(historical[3]["visibleEgifRecordCount"] == 770 and historical[3]["visibleEsfire30PerimeterCount"] == 182, "1992 EGIF/ESFire30 separation failed")
    require(historical[-1]["visibleIcvFireCount"] > 0 and historical[-1]["visibleEgifRecordCount"] == 0, "1992 to 1993 transition failed")
    require(results["1986_egif"]["final"]["visibleEgifRecordCount"] == 385, "1986 EGIF count")
    require(results["year_1984"]["final"]["visibleEgifRecordCount"] > 0 and results["year_1984"]["final"]["visibleEsfire30PerimeterCount"] == 0, "1984 must predate ESFire30")
    require(results["year_1985"]["final"]["visibleEsfire30PerimeterCount"] == 127, "1985 ESFire30 start count")
    require(results["year_1991"]["final"]["visibleEsfire30PerimeterCount"] == 171, "1991 ESFire30 count")
    esfire_permalink = results["1986_esfire30"]["final"]
    require(esfire_permalink["selectedGeometryHighlighted"] and esfire_permalink["selectionPopupVisible"] and esfire_permalink["selectionPopupGeometryId"] == esfire_permalink["selectedGeometryId"], "ESFire30 permalink geometry/popup failed")
    require(results["egif_only"]["final"]["visibleEgifRecordCount"] == 9175, "EGIF-only count")
    require(results["egif_alicante"]["final"]["visibleEgifRecordCount"] == 2514, "Historical Alicante count")
    require(results["egif_1992_gif"]["final"]["visibleEgifRecordCount"] == 9, "Historical GIF filter")
    require(results["egif_cause"]["final"]["visibleEgifRecordCount"] == 256, "Historical cause filter")
    historical_municipality = results["egif_municipality"]["final"]
    require(historical_municipality["selectedEntityId"] == "egif-record:1986030531" and historical_municipality["selectedGeometryId"] is None, "Historical record selection failed")
    require(historical_municipality["detailsSelectionVisible"] and not historical_municipality["selectionPopupVisible"], "Geometry-free EGIF details failed")
    historical_fit = results["egif_municipality_fit"]
    require(historical_fit["afterMunicipalityFit"]["municipalityFit"]["status"] == "historical-records-without-geometry", "Historical municipality status failed")
    require(historical_fit["afterMunicipalityFit"]["center"] == historical_fit["beforeMunicipalityFit"]["center"], "Historical municipality invented a map position")
    require("no tienen geometría individual fiable" in results["egif_point_history"]["point"]["pointHistoryText"], "Point history did not exclude EGIF")
    esfire_history = results["esfire30_point_history"]["point"]
    require(esfire_history["history"]["historicalRemoteSensingPerimeterCount"] >= 1 and "Teledetección histórica ESFire30" in esfire_history["pointHistoryText"], "ESFire30 point history was not kept separate")
    sot = results["sot_1986"]["selection"]
    require(set(sot["selectedMunicipalityIds"]) == {"46234", "46133"} and "Sot de Chera" in sot["detailsText"] and sot["selectedAdministrativeLinkStatus"] == "unlinked", "Sot de Chera control failed")
    marines = results["marines_altura_1992"]["selection"]
    require(set(marines["selectedProvinceIds"]) == {"castellon", "valencia"} and set(marines["selectedMunicipalityIds"]) == {"46161", "12012", "46902"} and marines["selectedAdministrativeLinkStatus"] == "unlinked", "Marines-Altura control failed")

    elx = results["1994_elx"]["final"]
    require(elx["municipalityFilter"] == "03065", "Elx municipality was not restored")
    require(elx["causeFilter"] == "intentional", "Cause was not restored")
    require(elx["selectedEntityId"] == "gva:pif-cv:1994AL0039", "Selection was not restored")
    require(elx["selectedGeometryHighlighted"] and elx["detailsSelectionVisible"], "Selection UI was not restored")
    require(elx["selectionPopupVisible"] and elx["selectionPopupDomVisible"], "Selection popup was not restored")
    require(elx["selectionPopupGeometryId"] == "gva:geometry:1994:2:1422", "Wrong popup geometry")
    require(abs(elx["center"]["lat"] - 38.27) < 0.00002 and abs(elx["center"]["lng"] + 0.70) < 0.00002 and elx["zoom"] == 8, "Permalink center or zoom changed")
    municipality = results["municipality_fit_elx"]["afterMunicipalityFit"]
    require(municipality["municipalityFit"]["status"] == "fit-visible-perimeters", "Elx did not auto-fit")
    require(municipality["municipalityFit"]["perimeterCount"] == 179, "Unexpected Elx perimeter count")
    require(municipality["municipalityFit"]["minimumRenderedPaddingPx"] >= 35, "Elx padding missing")
    histogram = results["histogram_1994"]["histogram"]
    require(histogram["years"] == {"from": 1994, "to": 1994}, "Histogram click did not select 1994")
    require(histogram["histogramBarCount"] == 59 and histogram["histogramSelectedYears"] == [1994], "Histogram did not remain visible after selection")
    multi = results["multi_geometry"]["final"]
    require(multi["selectedVisibleGeometryCount"] == 2, "2024AL0005 geometries missing")
    require(multi["selectedGeometryId"] == "gva:geometry:2024:121:13606", "Wrong 2024AL0005 geometry")
    require(multi["selectionPopupVisible"] and multi["selectionPopupDomVisible"] and multi["selectionPopupGeometryId"] == multi["selectedGeometryId"], "2024AL0005 popup was not restored")
    require(results["2024_gif"]["final"]["gifOnly"], "GIF filter was not restored")
    require(results["2026_effis"]["final"]["activeSources"] == ["effis"], "EFFIS-only state failed")
    require(results["mobile"]["final"]["mobileLayout"], "Mobile layout failed")
    require(results["mobile"]["final"]["years"] == {"from": 1968, "to": 2026}, "Mobile initial period differs")
    shared = results["shared_source"]["clickedSelection"]
    shared_reload = results["shared_reload"]["final"]
    require(shared_reload["selectedEntityId"] == shared["selectedEntityId"] and shared_reload["selectedGeometryId"] == shared["selectedGeometryId"], "Shared selection changed")
    require(shared_reload["selectedGeometryHighlighted"] and shared_reload["detailsSelectionVisible"] and shared_reload["selectionPopupDomVisible"], "Shared popup/selection was not restored")

    summary = {
        "status": "passed",
        "url": base,
        "initial_requests": initial["loader"]["requests"],
        "initial_response_bytes": initial["loader"]["responseBytes"],
        "initial_estimated_gzip_bytes": initial["loader"]["estimatedGzipBytes"],
        "initial_app_elapsed_ms": initial["appElapsedMs"],
        "initial_heap_used_bytes": initial["heapUsedBytes"],
        "initial_render_ms": initial["lastRender"]["renderMs"],
        "egif_parse_ms": next(item["parseMs"] for item in initial["loader"]["events"] if item["kind"] == "egif_administrative_records"),
        "mobile_app_elapsed_ms": results["mobile"]["final"]["appElapsedMs"],
        "mobile_heap_used_bytes": results["mobile"]["final"]["heapUsedBytes"],
        "permalinks": {name: base + "#" + fragment for name, fragment in fragments.items()},
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
