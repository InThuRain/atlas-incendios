#!/usr/bin/env python3
"""Measure CV-1.5 initial/full-period performance with Chrome's real clock."""

import argparse
import json
import os
import statistics
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

from cdp_client import run_page


def repository_root():
    return Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format_value, *args):
        return


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data/derived/gva/frontend/performance_report.json",
    )
    return parser.parse_args()


def run_chrome(chrome, url, window_size):
    payload = run_page(chrome, url, window_size)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload["final"]


def metric_summary(runs, path):
    values = []
    for run in runs:
        value = run
        for key in path:
            value = value[key]
        values.append(value)
    return {
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def main():
    args = parse_args()
    root = repository_root()
    scenarios = {
        "desktop_initial_2024": ({}, "1440,900"),
        "desktop_full_1993_2024": ({"from": 1993, "to": 2024}, "1440,900"),
        "mobile_initial_2024": ({}, "390,844"),
    }
    handler = lambda *items, **kwargs: QuietHandler(
        *items, directory=str(root.parent), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = "http://127.0.0.1:{}/{}/index.html".format(
        server.server_port, root.name
    )
    results = {}
    try:
        for name, (query, window_size) in scenarios.items():
            runs = []
            url = base_url + "?" + urlencode({"debug": 1, **query})
            for _ in range(args.repetitions):
                runs.append(run_chrome(args.chrome, url, window_size))
            results[name] = {
                "repetitions": args.repetitions,
                "window_size": window_size,
                "visible_fire_count": runs[0]["visibleFireCount"],
                "visible_perimeter_count": runs[0]["visiblePerimeterCount"],
                "active_asset_count": runs[0]["activeAssetCount"],
                "raw_geometry_bytes": runs[0]["lastLoad"]["rawBytes"],
                "estimated_gzip_geometry_bytes": runs[0]["lastLoad"]["estimatedGzipBytes"],
                "metrics": {
                    "app_elapsed_ms": metric_summary(runs, ("appElapsedMs",)),
                    "geometry_load_ms": metric_summary(runs, ("lastLoad", "loadMs")),
                    "geometry_render_ms": metric_summary(runs, ("lastRender", "renderMs")),
                    "heap_used_bytes": metric_summary(runs, ("heapUsedBytes",)),
                    "response_bytes": metric_summary(runs, ("loader", "responseBytes")),
                    "estimated_gzip_bytes": metric_summary(runs, ("loader", "estimatedGzipBytes")),
                },
                "runs": runs,
            }
    finally:
        server.shutdown()
        server.server_close()

    payload = {
        "schema_version": 1,
        "status": "complete",
        "environment": {
            "chrome": args.chrome,
            "leaflet": "1.9.4",
            "server_compression": False,
            "tiles_excluded_from_loader_metrics": True,
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
