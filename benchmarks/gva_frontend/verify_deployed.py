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
        "mobile": chrome_snapshot(args.chrome, debug_url(base), "390,844"),
    }
    for name, payload in results.items():
        validate(name, payload)

    initial = results["initial"]["final"]
    require(initial["profile"] == "public", "Deployed profile is not public")
    require(initial["sourceControlIds"] == ["icv", "effis"], "Unexpected source controls")
    require(initial["activeSources"] == ["icv", "effis"], "Unexpected initial sources")
    require(initial["loader"]["requests"] == 2, "Unexpected initial request count")
    require(initial["visibleEffisPerimeterCount"] == 16, "EFFIS 2026 missing")
    require(not initial["sigifLegendVisible"], "SIGIF leaked into public legend")
    require(not initial["mariolaPrimaryAccess"], "Mariola is still a primary access")

    elx = results["1994_elx"]["final"]
    require(elx["municipalityFilter"] == "03065", "Elx municipality was not restored")
    require(elx["causeFilter"] == "intentional", "Cause was not restored")
    require(elx["selectedEntityId"] == "gva:pif-cv:1994AL0039", "Selection was not restored")
    require(results["2024_gif"]["final"]["gifOnly"], "GIF filter was not restored")
    require(results["2026_effis"]["final"]["activeSources"] == ["effis"], "EFFIS-only state failed")
    require(results["mobile"]["final"]["mobileLayout"], "Mobile layout failed")

    summary = {
        "status": "passed",
        "url": base,
        "initial_requests": initial["loader"]["requests"],
        "initial_response_bytes": initial["loader"]["responseBytes"],
        "initial_estimated_gzip_bytes": initial["loader"]["estimatedGzipBytes"],
        "initial_app_elapsed_ms": initial["appElapsedMs"],
        "permalinks": {name: base + "#" + fragment for name, fragment in fragments.items()},
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
