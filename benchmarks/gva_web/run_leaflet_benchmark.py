#!/usr/bin/env python3
"""Run the isolated Leaflet benchmark in headless Chrome."""

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
from urllib.parse import quote


SCENARIOS = (
    (
        "overview_all",
        "data/derived/gva/web/levels/overview/geojson/all/all.geojson",
        "whole",
    ),
    (
        "regional_all",
        "data/derived/gva/web/levels/regional/geojson/all/all.geojson",
        "whole",
    ),
    (
        "regional_temporal_block",
        "data/derived/gva/web/levels/regional/geojson/temporal_blocks/2010-2019.geojson",
        "whole",
    ),
    (
        "local_mariola_font_roja",
        "data/derived/gva/web/levels/local/geojson/province/alicante.geojson",
        "local",
    ),
)


def repository_root():
    return Path(__file__).resolve().parents[2]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--output",
        type=Path,
        default=repository_root() / "data/derived/gva/web/leaflet_benchmark.json",
    )
    return parser.parse_args()


def summary(values):
    return {
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def main():
    args = parse_args()
    root = repository_root()
    handler = lambda *items, **kwargs: SimpleHTTPRequestHandler(
        *items, directory=str(root), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = {}
    try:
        for name, dataset, scenario in SCENARIOS:
            runs = []
            url = (
                "http://127.0.0.1:{}/benchmarks/gva_web/leaflet_benchmark.html"
                "?dataset={}&scenario={}".format(
                    server.server_port, quote(dataset), quote(scenario)
                )
            )
            for _ in range(args.repetitions):
                process = subprocess.run(
                    [
                        args.chrome,
                        "--headless",
                        "--no-sandbox",
                        "--disable-gpu",
                        "--enable-precise-memory-info",
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
                    r'<pre id="result"[^>]*>(.*?)</pre>', process.stdout, re.DOTALL
                )
                if not match:
                    raise RuntimeError("Chrome output did not contain a benchmark result")
                result_text = html.unescape(match.group(1)).strip()
                if not result_text or result_text == "pending":
                    raise RuntimeError(
                        "Chrome benchmark did not complete; result={!r}".format(
                            result_text
                        )
                    )
                try:
                    run = json.loads(result_text)
                except json.JSONDecodeError as error:
                    raise RuntimeError(
                        "Invalid benchmark result {!r}: {}".format(
                            result_text[:500], error
                        )
                    )
                if "error" in run:
                    raise RuntimeError(run["error"])
                runs.append(run)
            metric_names = (
                "fetch_ms",
                "parse_ms",
                "layer_add_ms",
                "settled_render_ms",
                "heap_delta_bytes",
            )
            results[name] = {
                "dataset": dataset,
                "scenario": scenario,
                "repetitions": args.repetitions,
                "source_geometry_count": runs[0]["source_geometry_count"],
                "rendered_geometry_count": runs[0]["rendered_geometry_count"],
                "source_bytes": runs[0]["source_bytes"],
                "leaflet_version": runs[0]["leaflet_version"],
                "prefer_canvas": runs[0]["prefer_canvas"],
                "metrics": {
                    metric: summary([run[metric] for run in runs])
                    for metric in metric_names
                    if runs[0][metric] is not None
                },
                "runs": runs,
            }
    finally:
        server.shutdown()
        server.server_close()
    payload = {
        "schema_version": 1,
        "environment": {
            "chrome": args.chrome,
            "leaflet": "1.9.4",
            "tiles_loaded": False,
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".part")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(args.output))
    print(args.output)


if __name__ == "__main__":
    main()
