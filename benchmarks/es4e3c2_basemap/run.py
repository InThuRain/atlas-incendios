#!/usr/bin/env python3
"""Comparación local BDLJE-only vs Protomaps z12 para ES-4E3C2.

No modifica el runtime ni construye artifacts publicables. Todos los assets y
screenshots grandes viven en build/es4e3c2-basemap/ (ignorado).
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILDER = ROOT / "scripts/build_national_frontend.py"
BASELINE_DATA = ROOT / "build/national-pages-staging/data"
SUMMARY = ROOT / "data/derived/spain/national-ux-summary-v1"
HIGHLIGHTS = ROOT / "data/derived/spain/national-highlights-v1"
EXPERIMENT = ROOT / "build/es4e3c2-basemap"
CANDIDATE = EXPERIMENT / "protomaps-spain-z12.pmtiles"
FONTS = EXPERIMENT / "fonts"
OUTPUT = EXPERIMENT / "results.json"
SCREENSHOTS = EXPERIMENT / "screenshots"

sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import CDPClient  # noqa: E402

SCENARIOS = {
    "spain": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES", "territory_restore": "1"}, "desktop"),
    "galicia": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "territory_select": "ES:CCAA:12", "territory_restore": "1"}, "desktop"),
    "ourense": ({"smoke": "galicia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:12", "province_select": "ES:PROV:32", "territory_restore": "1"}, "desktop"),
    "gva_1995": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10", "territory_select": "ES:CCAA:10", "territory_restore": "1"}, "desktop"),
    "elx": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065", "territory_restore": "1"}, "desktop"),
    "cangas": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:03", "province_select": "ES:PROV:33", "municipality_select": "ES:MUN:33011", "territory_restore": "1"}, "desktop"),
    "canarias": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:05", "territory_select": "ES:CCAA:05", "territory_restore": "1"}, "desktop"),
    "mobile_spain": ({"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES", "territory_restore": "1"}, "mobile"),
    "mobile_elx": ({"smoke": "pais_valencia", "from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10", "municipality_select": "ES:MUN:03065", "territory_restore": "1"}, "mobile"),
}
COMPARABLE_SCREENSHOTS = {"spain", "ourense", "gva_1995", "elx", "cangas", "canarias"}


class RequestLog:
    def __init__(self):
        self.lock = threading.Lock()
        self.rows: list[dict] = []

    def mark(self) -> int:
        with self.lock:
            return len(self.rows)

    def add(self, row: dict) -> None:
        with self.lock:
            self.rows.append(row)

    def since(self, marker: int) -> list[dict]:
        with self.lock:
            return [dict(row) for row in self.rows[marker:]]


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    if not header or not header.startswith("bytes="):
        return None
    start_text, end_text = header[6:].split(",", 1)[0].split("-", 1)
    if start_text:
        start = int(start_text); end = int(end_text) if end_text else size - 1
    else:
        suffix = int(end_text); start = max(size - suffix, 0); end = size - 1
    if start < 0 or end < start or start >= size:
        raise ValueError("invalid Range")
    return start, min(end, size - 1)


class RangeHandler(SimpleHTTPRequestHandler):
    request_log: RequestLog

    def log_message(self, fmt, *args):  # noqa: A003
        pass

    def send_head(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()
        stream = open(path, "rb")
        size = os.fstat(stream.fileno()).st_size
        try:
            requested = parse_range(self.headers.get("Range"), size)
        except (TypeError, ValueError):
            stream.close(); self.send_error(416, "Range Not Satisfiable"); return None
        if requested is None:
            start, end, status = 0, size - 1, 200
        else:
            start, end, status = requested[0], requested[1], 206
            stream.seek(start)
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        if status == 206: self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        self.remaining = length
        self.request_log.add({"method": self.command, "path": self.path.split("?", 1)[0], "status": status, "bytes": length, "range": status == 206, "start": start, "end": end})
        return stream

    def copyfile(self, source, output):
        remaining = getattr(self, "remaining", None)
        try:
            while remaining:
                block = source.read(min(64 * 1024, remaining))
                if not block: break
                output.write(block); remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            pass


@contextmanager
def server_for(root: Path):
    log = RequestLog()
    class Handler(RangeHandler):
        request_log = log
    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *args, **kwargs: Handler(*args, directory=str(root), **kwargs))
    server.daemon_threads = True; server.block_on_close = False
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        yield server, log
    finally:
        server.shutdown(); server.server_close()


def build_site(directory: Path, candidate: bool) -> Path:
    if not BASELINE_DATA.is_dir() or not SUMMARY.is_dir() or not HIGHLIGHTS.is_dir():
        raise FileNotFoundError("Faltan assets locales aceptados del runtime nacional")
    site = directory / ("candidate" if candidate else "baseline")
    result = subprocess.run([sys.executable, str(BUILDER), "--output", str(site)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode: raise RuntimeError(result.stderr or result.stdout)
    data = site / "data"; data.mkdir()
    for child in BASELINE_DATA.iterdir():
        (data / child.name).symlink_to(child, target_is_directory=child.is_dir())
    for category, source in (("summary", SUMMARY), ("highlights", HIGHLIGHTS)):
        parent = data / category; parent.mkdir(exist_ok=True)
        target = parent / source.name
        if not target.exists(): target.symlink_to(source, target_is_directory=True)
    if candidate:
        basemap = data / "basemap"; basemap.mkdir()
        (basemap / CANDIDATE.name).symlink_to(CANDIDATE)
        (basemap / "fonts").symlink_to(FONTS, target_is_directory=True)
        shutil.copy2(HERE / "candidate.mjs", site / "basemap-candidate.mjs")
        app = site / "runtime/app.js"
        text = "globalThis.__e3c2AppStages=['module-start'];\n" + app.read_text(encoding="utf-8")
        needle = "style: {\n    version: 8,"
        if text.count(needle) != 1: raise RuntimeError("No se pudo insertar el glyph endpoint en el runtime temporal")
        text = text.replace(needle, 'style: {\n    version: 8,\n    glyphs: new URL(".", location.href).toString() + "data/basemap/fonts/{fontstack}/{range}.pbf",')
        text = text.replace("const map = new maplibregl.Map({", "globalThis.__e3c2AppStages.push('before-map');\nconst map = new maplibregl.Map({")
        text = text.replace("map.addControl(new maplibregl.NavigationControl", "globalThis.__e3c2AppStages.push('after-map');\nmap.addControl(new maplibregl.NavigationControl")
        text = text.replace("window.__es4cRuntime = {", "globalThis.__e3c2AppStages.push('before-export');\nwindow.__es4cRuntime = {")
        text += "\nglobalThis.__e3c2AppStages.push('module-end:' + Boolean(window.__es4cRuntime));\n"
        app.write_text(text, encoding="utf-8")
        index = site / "index.html"
        html = index.read_text(encoding="utf-8").replace("</body>", '  <script type="module" src="basemap-candidate.mjs"></script>\n  </body>')
        index.write_text(html, encoding="utf-8")
    return site


@contextmanager
def chrome_session(chrome: str, device: str, timeout: int):
    profile = Path(tempfile.mkdtemp(prefix="atlas-e3c2-basemap-cdp-"))
    size = "390,844" if device == "mobile" else "1440,900"
    process = subprocess.Popen([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--enable-precise-memory-info", "--remote-debugging-port=0", "--remote-allow-origins=*", "--user-data-dir=" + str(profile), "--window-size=" + size, "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = None
    try:
        deadline = time.monotonic() + timeout; port_file = profile / "DevToolsActivePort"
        while not port_file.exists():
            if process.poll() is not None: raise RuntimeError("Chromium terminó antes de abrir DevTools")
            if time.monotonic() > deadline: raise TimeoutError("Chromium no abrió DevTools")
            time.sleep(.05)
        port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
            page = next(row for row in json.load(response) if row["type"] == "page")
        client = CDPClient(page["webSocketDebuggerUrl"]); client.command("Page.enable"); client.command("Runtime.enable")
        client.command("Page.addScriptToEvaluateOnNewDocument", {"source": "globalThis.__e3c2BrowserErrors=[]; addEventListener('error',e=>__e3c2BrowserErrors.push(String(e.message||e.error))); addEventListener('unhandledrejection',e=>__e3c2BrowserErrors.push(String(e.reason)));"})
        if device == "mobile": client.command("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        yield client, deadline
    finally:
        if client: client.close()
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        shutil.rmtree(profile, ignore_errors=True)


def observe(chrome: str, url: str, device: str, candidate: bool, log: RequestLog, screenshot: Path | None, timeout: int) -> dict:
    marker = log.mark(); started = time.monotonic()
    with chrome_session(chrome, device, timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url})
        condition = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && Boolean(window.__es4cRuntime)"
        if candidate: condition += " && window.__basemapEvaluation?.status === 'installed'"
        while not client.evaluate(condition):
            if time.monotonic() > deadline:
                diagnostic = client.evaluate("({bootstrap:document.querySelector('#national-bootstrap-error')?.textContent, runtime:document.querySelector('#runtime-test-output')?.textContent, basemap:window.__basemapEvaluation, appStages:globalThis.__e3c2AppStages, browserErrors:globalThis.__e3c2BrowserErrors, readyState:document.readyState, scripts:[...document.scripts].map(x=>x.src)})")
                diagnostic["runtimeImport"] = client.evaluate("(async()=>{try{await import('./runtime/app.js');return 'ok'}catch(e){return String(e.stack||e)}})()")
                diagnostic["candidateImport"] = client.evaluate("(async()=>{try{await import('./basemap-candidate.mjs');return 'ok'}catch(e){return String(e.stack||e)}})()")
                raise TimeoutError(f"El escenario no convergió: {diagnostic}; requests={log.since(marker)[-30:]}")
            time.sleep(.08)
        # Da tiempo al source vectorial, glyphs y compositor; loaded() solo se
        # usa como señal diagnóstica porque MapLibre puede revalidar en idle.
        stable = 0
        while stable < 5:
            loaded = client.evaluate("window.__es4cRuntime.map.loaded() && !window.__es4cRuntime.map.isMoving()")
            stable = stable + 1 if loaded else 0
            if time.monotonic() > deadline: break
            time.sleep(.12)
        time.sleep(.7)
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            captured = client.command("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            screenshot.write_bytes(base64.b64decode(captured["data"]))
        observed = client.evaluate(r'''(() => {
          const map=window.__es4cRuntime.map; const layers=map.getStyle().layers.map(x=>x.id);
          const resources=performance.getEntriesByType('resource').map(x=>({name:x.name,transfer_size:x.transferSize,encoded_body_size:x.encodedBodySize,duration_ms:x.duration}));
          const labels=['es4e3c2-regions','es4e3c2-localities','es4e3c2-road-labels'].filter(id=>map.getLayer(id));
          const labelFeatures=labels.flatMap(id=>map.queryRenderedFeatures({layers:[id]}));
          const sourcePlaces=map.getSource('es4e3c2-protomaps')?map.querySourceFeatures('es4e3c2-protomaps',{sourceLayer:'places'}):[];
          const sourceRoads=map.getSource('es4e3c2-protomaps')?map.querySourceFeatures('es4e3c2-protomaps',{sourceLayer:'roads'}):[];
          const runtime=JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}');
          return {state:window.__es4cRuntime.getState(),center:[map.getCenter().lng,map.getCenter().lat],zoom:map.getZoom(),map_loaded:map.loaded(),
            layers,rendered_label_count:labelFeatures.length,rendered_label_examples:[...new Set(labelFeatures.map(x=>x.properties?.name).filter(Boolean))].slice(0,20),
            source_places_count:sourcePlaces.length,source_place_examples:[...new Set(sourcePlaces.map(x=>x.properties?.name).filter(Boolean))].slice(0,30),source_place_details:sourcePlaces.slice(0,30).map(x=>({name:x.properties?.name,kind:x.properties?.kind,min_zoom:x.properties?.min_zoom,sort_key:x.properties?.sort_key})),source_roads_count:sourceRoads.length,
            basemap:window.__basemapEvaluation||null,resources,heap:performance.memory?.usedJSHeapSize??null,
            browser_errors:globalThis.__e3c2BrowserErrors||[],runtime_errors:runtime.errors||[],bootstrap_error:document.querySelector('#national-bootstrap-error')?.textContent||'',
            context:document.querySelector('.map-context')?.innerText||'',viewport:{width:innerWidth,height:innerHeight}};
        })()''')
    rows = log.since(marker)
    candidate_pmtiles = [row for row in rows if row["path"].endswith("/protomaps-spain-z12.pmtiles")]
    glyphs = [row for row in rows if "/data/basemap/fonts/" in row["path"] and row["path"].endswith(".pbf")]
    observed.update({
        "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
        "http": {
            "candidate_pmtiles_requests": len(candidate_pmtiles),
            "candidate_pmtiles_range_requests": sum(row["range"] for row in candidate_pmtiles),
            "candidate_pmtiles_bytes": sum(row["bytes"] for row in candidate_pmtiles),
            "candidate_full_downloads": sum(row["status"] == 200 and row["bytes"] == CANDIDATE.stat().st_size for row in candidate_pmtiles),
            "glyph_requests": len(glyphs), "glyph_bytes": sum(row["bytes"] for row in glyphs),
            "glyph_paths": sorted({row["path"] for row in glyphs}),
            "statuses": sorted({row["status"] for row in candidate_pmtiles}),
        },
        "external_runtime_domains": sorted({urlparse(row["name"]).hostname for row in observed["resources"] if urlparse(row["name"]).hostname not in {"127.0.0.1", "localhost", None}}),
        "screenshot": str(screenshot.relative_to(ROOT)) if screenshot else None,
    })
    return observed


def summarize_basemap_rows(rows: list[dict]) -> dict:
    pmtiles = [row for row in rows if row["path"].endswith("/protomaps-spain-z12.pmtiles")]
    glyphs = [row for row in rows if "/data/basemap/fonts/" in row["path"] and row["path"].endswith(".pbf")]
    return {
        "pmtiles_requests": len(pmtiles),
        "pmtiles_range_requests": sum(row["range"] for row in pmtiles),
        "pmtiles_bytes": sum(row["bytes"] for row in pmtiles),
        "full_downloads": sum(row["status"] == 200 and row["bytes"] == CANDIDATE.stat().st_size for row in pmtiles),
        "glyph_requests": len(glyphs),
        "glyph_bytes": sum(row["bytes"] for row in glyphs),
        "statuses": sorted({row["status"] for row in pmtiles}),
    }


def wait_for_map_stable(client: CDPClient, deadline: float) -> None:
    stable = 0
    while stable < 5:
        loaded = client.evaluate("window.__es4cRuntime.map.loaded() && !window.__es4cRuntime.map.isMoving()")
        stable = stable + 1 if loaded else 0
        if time.monotonic() > deadline:
            raise TimeoutError("El mapa no quedó estable durante la navegación secuencial")
        time.sleep(.12)
    time.sleep(.7)


def observe_navigation_sequence(chrome: str, base_url: str, name: str, transitions: list[tuple[str, str]], log: RequestLog, timeout: int) -> dict:
    """Mide deltas de Range y glyphs sin reiniciar la sesión del navegador."""
    session_marker = log.mark()
    stages = []
    with chrome_session(chrome, "desktop", timeout) as (client, deadline):
        client.command("Page.navigate", {"url": base_url})
        condition = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && window.__basemapEvaluation?.status === 'installed'"
        while not client.evaluate(condition):
            if time.monotonic() > deadline:
                raise TimeoutError(f"{name}: la carga inicial no convergió")
            time.sleep(.08)
        wait_for_map_stable(client, deadline)
        initial_rows = log.since(session_marker)
        stages.append({"stage": "spain", "delta": summarize_basemap_rows(initial_rows), "cumulative": summarize_basemap_rows(initial_rows)})

        for stage_name, expression in transitions:
            marker = log.mark()
            started = time.monotonic()
            client.evaluate(expression)
            wait_for_map_stable(client, deadline)
            delta_rows = log.since(marker)
            cumulative_rows = log.since(session_marker)
            stages.append({
                "stage": stage_name,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
                "delta": summarize_basemap_rows(delta_rows),
                "cumulative": summarize_basemap_rows(cumulative_rows),
                "state": client.evaluate("window.__es4cRuntime.getState()"),
                "map_loaded": client.evaluate("window.__es4cRuntime.map.loaded()"),
            })
        browser_errors = client.evaluate("globalThis.__e3c2BrowserErrors||[]")
        runtime_errors = client.evaluate("JSON.parse(document.querySelector('#runtime-test-output').textContent||'{}').errors||[]")
        heap = client.evaluate("performance.memory?.usedJSHeapSize??null")
    return {"name": name, "stages": stages, "browser_errors": browser_errors, "runtime_errors": runtime_errors, "heap": heap}


def validate(payload: dict) -> list[str]:
    failures = []
    candidates = [row for row in payload["runs"] if row["variant"] == "protomaps_z12"]
    for row in candidates:
        if row["basemap"].get("status") != "installed" or row["basemap"].get("errors"):
            failures.append(f"{row['scenario']}: basemap no instalado/errores")
        if row["http"]["candidate_pmtiles_requests"] < 1 or row["http"]["candidate_pmtiles_requests"] != row["http"]["candidate_pmtiles_range_requests"]:
            failures.append(f"{row['scenario']}: PMTiles sin Range 206")
        if row["http"]["candidate_full_downloads"] or row["external_runtime_domains"]:
            failures.append(f"{row['scenario']}: full download o dominio externo")
        if row["browser_errors"] or row["runtime_errors"] or row["bootstrap_error"]:
            failures.append(f"{row['scenario']}: error browser/runtime")
        order = row["layers"]
        if order.index("es4e3c2-earth") >= order.index("official-ccaa-territories-fill") or order.index("official-ccaa-territories-fill") >= order.index("esfire30-perimeters"):
            failures.append(f"{row['scenario']}: orden de capas")
    for name in ("spain", "galicia", "ourense", "gva_1995", "elx", "cangas", "canarias", "mobile_spain", "mobile_elx"):
        if not any(row["scenario"] == name and row["variant"] == "protomaps_z12" for row in candidates):
            failures.append(f"falta escenario {name}")
    expected_sequences = {"spain_galicia_ourense", "spain_gva_alacant_elx"}
    actual_sequences = {row["name"] for row in payload.get("sequences", [])}
    if expected_sequences != actual_sequences:
        failures.append("faltan recorridos secuenciales")
    for sequence in payload.get("sequences", []):
        if sequence["browser_errors"] or sequence["runtime_errors"]:
            failures.append(f"{sequence['name']}: errores browser/runtime")
        for stage in sequence["stages"]:
            delta = stage["delta"]
            if delta["full_downloads"] or delta["pmtiles_requests"] != delta["pmtiles_range_requests"]:
                failures.append(f"{sequence['name']}/{stage['stage']}: PMTiles sin Range 206")
    return sorted(set(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--scenario", choices=tuple(SCENARIOS))
    parser.add_argument("--candidate-only", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8")); failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "runs": len(payload.get("runs", []))})); return 0 if not failures else 1
    if not CANDIDATE.is_file() or not (FONTS / "Noto Sans Regular/0-255.pbf").is_file():
        raise FileNotFoundError("Falta PMTiles z12 o glyph mínimo en build/es4e3c2-basemap")
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    runs = []
    sequences = []
    with tempfile.TemporaryDirectory(prefix="atlas-e3c2-basemap-site-") as directory:
        root = Path(directory); sites = {False: build_site(root, False), True: build_site(root, True)}
        variants = (True,) if args.candidate_only else (False, True)
        for candidate in variants:
            with server_for(sites[candidate]) as (server, log):
                selected = [args.scenario] if args.scenario else (list(SCENARIOS) if candidate else sorted(COMPARABLE_SCREENSHOTS))
                for name in selected:
                    query, device = SCENARIOS[name]
                    screenshot = SCREENSHOTS / f"{name}--{'protomaps-z12' if candidate else 'bdlje-only'}.png" if (name in COMPARABLE_SCREENSHOTS or device == "mobile") else None
                    url = f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(query)}"
                    row = observe(args.chrome, url, device, candidate, log, screenshot, args.timeout)
                    row.update({"scenario": name, "device": device, "variant": "protomaps_z12" if candidate else "bdlje_only"})
                    runs.append(row)
                    print(json.dumps({"scenario": name, "variant": row["variant"], "pmtiles_bytes": row["http"]["candidate_pmtiles_bytes"], "glyph_bytes": row["http"]["glyph_bytes"], "labels": row["rendered_label_count"], "elapsed_ms": row["elapsed_ms"]}), flush=True)
        if not args.scenario:
            with server_for(sites[True]) as (server, log):
                initial = {"smoke": "spain", "from": 1995, "to": 1995, "egif_scope": "ES", "territory_restore": "1"}
                base_url = f"http://127.0.0.1:{server.server_port}/index.html?{urlencode(initial)}"
                sequences.append(observe_navigation_sequence(args.chrome, base_url, "spain_galicia_ourense", [
                    ("galicia", "window.__es4cRuntime.setEgifScope('ES:CCAA:12')"),
                    ("ourense", "window.__es4cRuntime.setProvinceScope('ES:PROV:32','ES:CCAA:12')"),
                ], log, args.timeout))
                sequences.append(observe_navigation_sequence(args.chrome, base_url, "spain_gva_alacant_elx", [
                    ("pais_valencia", "window.__es4cRuntime.setEgifScope('ES:CCAA:10')"),
                    ("alacant", "window.__es4cRuntime.setProvinceScope('ES:PROV:03','ES:CCAA:10')"),
                    ("elx", "window.__es4cRuntime.setMunicipalityScope('ES:MUN:03065')"),
                ], log, args.timeout))
                for sequence in sequences:
                    print(json.dumps({"sequence": sequence["name"], "stages": [{"stage": row["stage"], "delta": row["delta"]} for row in sequence["stages"]]}), flush=True)
    payload = {"phase": "ES-4E3C2_BASEMAP_DECISION", "runs": runs, "sequences": sequences}
    failures = validate(payload); payload.update({"valid": not failures, "failures": failures})
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not failures, "failures": failures, "runs": len(runs), "output": str(args.output)})); return 0 if not failures else 1


if __name__ == "__main__": raise SystemExit(main())
