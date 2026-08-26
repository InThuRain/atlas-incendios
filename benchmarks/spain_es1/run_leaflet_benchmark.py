#!/usr/bin/env python3
"""Mide GeoJSON ESFire30 diagnóstico con Leaflet Canvas en Chrome limpio."""

from __future__ import annotations

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


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIOS = (
    ("spain_overview_full", "data/derived/spain/es1/esfire30-overview.geojson"),
    ("spain_overview_1985", "data/derived/spain/es1/esfire30-overview-1985.geojson"),
    (
        "spain_overview_1985_1992",
        "data/derived/spain/es1/esfire30-overview-1985-1992.geojson",
    ),
    ("gva_overview_1985_1992", "data/web/gva/esfire30/geometry/overview.geojson"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/derived/spain/es1/leaflet-desktop.json",
    )
    return parser.parse_args()


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def main() -> int:
    args = parse_args()
    handler = lambda *items, **kwargs: SimpleHTTPRequestHandler(
        *items, directory=str(ROOT), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = {}
    try:
        for name, dataset in DEFAULT_SCENARIOS:
            path = ROOT / dataset
            if not path.exists():
                raise FileNotFoundError(path)
            runs = []
            url = (
                f"http://127.0.0.1:{server.server_port}/"
                f"benchmarks/spain_es1/leaflet_benchmark.html?dataset={quote(dataset)}"
            )
            for _ in range(args.repetitions):
                command = [
                    args.chrome,
                    "--headless",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--enable-precise-memory-info",
                    "--dump-dom",
                ]
                if args.mobile:
                    command.append("--window-size=390,844")
                command.append(url)
                process = subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    timeout=360,
                )
                match = re.search(
                    r'<pre id="result"[^>]*>(.*?)</pre>', process.stdout, re.DOTALL
                )
                if not match:
                    raise RuntimeError("Chrome no devolvió el resultado")
                run = json.loads(html.unescape(match.group(1)).strip())
                if "error" in run:
                    raise RuntimeError(run["error"])
                runs.append(run)
            metrics = ("fetch_ms", "parse_ms", "render_ms", "heap_delta_bytes")
            results[name] = {
                "dataset": dataset,
                "geometry_count": runs[0]["geometry_count"],
                "source_bytes": runs[0]["source_bytes"],
                "gzip_bytes": len(__import__("gzip").compress(path.read_bytes(), mtime=0)),
                "metrics": {
                    metric: summarize([run[metric] for run in runs])
                    for metric in metrics
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
            "viewport": "390x844" if args.mobile else "headless default 800x600",
            "raster_tiles_loaded": False,
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".part")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
