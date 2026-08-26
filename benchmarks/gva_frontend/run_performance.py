#!/usr/bin/env python3
"""Measure CV-2.3 recent, consolidated and full-period frontend performance."""

import argparse
import json
import os
import statistics
import subprocess
import sys
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
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--profile", choices=("development", "public"), default="development")
    parser.add_argument("--url", help="Use an already deployed viewer instead of starting the local server")
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data/derived/gva/frontend/performance_report.json",
    )
    return parser.parse_args()


def run_chrome(chrome, url, window_size, timeout):
    payload = run_page(chrome, url, window_size, timeout=timeout)
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


def event_metric_summary(runs, kind, field):
    values = []
    for run in runs:
        event = next((item for item in run["loader"]["events"] if item["kind"] == kind), None)
        if event is not None:
            values.append(event[field])
    if not values:
        return None
    return {"min": min(values), "median": statistics.median(values), "max": max(values), "mean": statistics.fmean(values)}


def main():
    args = parse_args()
    root = repository_root()
    runtime = root / "data/web/gva/manifest.json"
    development = runtime.read_bytes()
    if args.profile == "public":
        subprocess.run(
            [sys.executable, str(root / "scripts/build_frontend_profile.py"),
             "--profile", "public", "--output", str(runtime)],
            check=True, stdout=subprocess.PIPE, text=True,
        )
    manifest = json.loads(runtime.read_text(encoding="utf-8"))
    years = manifest["years"]
    baseline_sources = ",".join(source for source in manifest["sources"] if source != "egif")
    without_esfire30_sources = ",".join(source for source in manifest["sources"] if source != "esfire30")
    scenarios = {
        "desktop_latest_year": ({"from": years["max"], "to": years["max"]}, "1440,900"),
        "desktop_baseline_1993_2026": ({"from": 1993, "to": years["max"], "sources": baseline_sources}, "1440,900"),
        "desktop_initial_full_period": ({}, "1440,900"),
        "desktop_full_without_esfire30": ({"sources": without_esfire30_sources}, "1440,900"),
        "mobile_latest_year": ({"from": years["max"], "to": years["max"]}, "390,844"),
        "mobile_baseline_1993_2026": ({"from": 1993, "to": years["max"], "sources": baseline_sources}, "390,844"),
        "mobile_initial_full_period": ({}, "390,844"),
        "mobile_full_without_esfire30": ({"sources": without_esfire30_sources}, "390,844"),
        "desktop_historical_egif_only": ({"from": 1985, "to": 1992, "sources": "egif"}, "1440,900"),
        "desktop_historical_with_esfire30": ({"from": 1985, "to": 1992, "sources": "egif,esfire30"}, "1440,900"),
        "desktop_1986": ({"from": 1986, "to": 1986, "sources": "egif,esfire30"}, "1440,900"),
        "mobile_historical_egif_only": ({"from": 1985, "to": 1992, "sources": "egif"}, "390,844"),
        "mobile_historical_with_esfire30": ({"from": 1985, "to": 1992, "sources": "egif,esfire30"}, "390,844"),
        "mobile_1986": ({"from": 1986, "to": 1986, "sources": "egif,esfire30"}, "390,844"),
    }
    server = None
    if args.url:
        base_url = args.url.rstrip("/") + "/"
    else:
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
            for repetition in range(1, args.repetitions + 1):
                print(f"{name}: repetition {repetition}/{args.repetitions}", flush=True)
                try:
                    runs.append(run_chrome(args.chrome, url, window_size, args.timeout))
                except TimeoutError:
                    print(f"{name}: transient timeout; retrying once", flush=True)
                    runs.append(run_chrome(args.chrome, url, window_size, args.timeout))
            results[name] = {
                "repetitions": args.repetitions,
                "window_size": window_size,
                "visible_fire_count": runs[0]["visibleFireCount"],
                "visible_egif_record_count": runs[0]["visibleEgifRecordCount"],
                "visible_esfire30_perimeter_count": runs[0]["visibleEsfire30PerimeterCount"],
                "visible_perimeter_count": runs[0]["visiblePerimeterCount"],
                "visible_sigif_record_count": runs[0]["visibleSigifRecordCount"],
                "visible_effis_perimeter_count": runs[0]["visibleEffisPerimeterCount"],
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
                    "egif_fetch_ms": event_metric_summary(runs, "egif_administrative_records", "fetchMs"),
                    "egif_parse_ms": event_metric_summary(runs, "egif_administrative_records", "parseMs"),
                    "esfire30_fetch_ms": event_metric_summary(runs, "esfire30_perimeters", "fetchMs"),
                    "esfire30_parse_ms": event_metric_summary(runs, "esfire30_perimeters", "parseMs"),
                },
                "runs": runs,
            }
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if args.profile == "public":
            runtime.write_bytes(development)

    payload = {
        "schema_version": 1,
        "status": "complete",
        "profile": args.profile,
        "period": {"min": years["min"], "max": years["max"], "comparison_year": years["max"]},
        "environment": {
            "chrome": args.chrome,
            "leaflet": "1.9.4",
            "server_compression": False,
            "url": args.url or base_url,
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
