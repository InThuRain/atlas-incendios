#!/usr/bin/env python3
"""Ejecuta el prototipo aislado MapLibre + PMTiles de ES-3.

Los binarios/librerías y el archivo PMTiles se generan bajo data/derived/ y no
forman parte del frontend ni de los assets versionables.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys_path = ROOT / "benchmarks/gva_frontend"
import sys
sys.path.insert(0, str(sys_path))
from cdp_client import run_page  # noqa: E402

SCENARIOS = {
    "spain_full": {"center": "-3.7,40.3", "zoom": 4},
    "galicia": {"center": "-8.1,42.6", "zoom": 6},
    "andalucia": {"center": "-4.8,37.3", "zoom": 6},
    "cataluna": {"center": "1.7,41.8", "zoom": 7},
    "pais_valencia": {"center": "-0.7,39.3", "zoom": 8},
    "provincia_local": {"center": "-3.5,37.2", "zoom": 9},
}


class RangeRequestHandler(SimpleHTTPRequestHandler):
    """Servidor de diagnóstico con HTTP Range, requisito de PMTiles.

    Python 3.8 no lo implementa en SimpleHTTPRequestHandler. No es parte del
    producto ni una afirmación sobre GitHub Pages: permite medir el archivo
    PMTiles bajo el comportamiento HTTP que necesita.
    """

    def send_head(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()
        stream = open(path, "rb")
        size = os.fstat(stream.fileno()).st_size
        header = self.headers.get("Range")
        if not header or not header.startswith("bytes="):
            self.send_response(200); self.send_header("Content-type", self.guess_type(path)); self.send_header("Content-Length", str(size)); self.send_header("Accept-Ranges", "bytes"); self.end_headers(); return stream
        spec = header[6:].split(",", 1)[0]
        start_text, end_text = spec.split("-", 1)
        start = int(start_text) if start_text else 0
        end = int(end_text) if end_text else size - 1
        if start >= size or end < start:
            stream.close(); self.send_error(416, "Range Not Satisfiable"); return None
        end = min(end, size - 1); length = end - start + 1
        stream.seek(start)
        self.send_response(206); self.send_header("Content-type", self.guess_type(path)); self.send_header("Content-Length", str(length)); self.send_header("Content-Range", f"bytes {start}-{end}/{size}"); self.send_header("Accept-Ranges", "bytes"); self.end_headers()
        self.range_length = length
        return stream

    def copyfile(self, source, output):
        remaining = getattr(self, "range_length", None)
        if remaining is None: return super().copyfile(source, output)
        while remaining:
            block = source.read(min(64 * 1024, remaining))
            if not block: break
            output.write(block); remaining -= len(block)

def summary(rows):
    return {key: statistics.median([row[key] for row in rows if row[key] is not None])
            for key in ("total_ms", "rendered_features", "pmtiles_requests", "pmtiles_transfer_bytes", "pmtiles_encoded_bytes", "heap_delta_bytes")}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--archive", default="esfire30-national.pmtiles")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive = ROOT / "data/derived/spain/es3/assets" / args.archive
    if not archive.exists(): raise FileNotFoundError(archive)
    handler = lambda *a, **kw: RangeRequestHandler(*a, directory=str(ROOT), **kw)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = {}
    try:
        for name, query in SCENARIOS.items():
            url = f"http://127.0.0.1:{server.server_port}/benchmarks/es3/vector_benchmark.html?{urlencode({**query, 'archive': args.archive})}"
            rows = [run_page(args.chrome, url, "390,844" if args.mobile else "1280,800", timeout=180) for _ in range(args.repetitions)]
            if any(row.get("error") for row in rows): raise RuntimeError(f"{name}: {rows}")
            results[name] = {"runs": rows, "median": summary(rows)}
    finally:
        server.shutdown(); server.server_close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": 1, "renderer": "MapLibre GL JS with PMTiles", "viewport": "390x844" if args.mobile else "1280x800", "archive_bytes": archive.stat().st_size, "scenarios": results}, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0
if __name__ == "__main__": raise SystemExit(main())
