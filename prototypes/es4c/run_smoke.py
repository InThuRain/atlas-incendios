#!/usr/bin/env python3
"""Smokes locales del prototipo ES-4C1A con soporte HTTP Range explícito.

No construye PMTiles ni es parte del Atlas público. Sirve el árbol del
repositorio para reutilizar el archivo diagnóstico validado de ES-3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlencode

ROOT = Path(__file__).resolve().parents[2]
ES3_RESULTS = ROOT / "benchmarks/es3/results.json"
ARCHIVE = ROOT / "data/derived/spain/es3/assets/esfire30-national-fidelity.pmtiles"
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import run_page  # noqa: E402

SCENARIOS = ("spain", "galicia", "pais_valencia")
EGIF_SMOKES = {
    "a_spain_1993_2002": {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "records": 200513, "initial_requests": 0},
    "b_pais_valencia_1993_2002": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "records": 5159, "initial_requests": 1},
    "c_galicia_1993_2002": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES:CCAA:12", "records": 110605, "initial_requests": 1},
    "d_galicia_2013_2023": {"map": "galicia", "from": 2013, "to": 2023, "scope": "ES:CCAA:12", "records": 20850, "initial_requests": 1},
    "e_rapid_galicia_to_rioja": {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "rapid": True, "records": 1191, "final_scope": "ES:CCAA:17"},
    "f_mobile_pais_valencia": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "records": 5159, "initial_requests": 1, "mobile_only": True},
}
EXPECTED_SHA256 = "92f0f081131932075f54a89d86fc8aa7e5879d56ca4d7177c64562f9612751b4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_archive() -> dict:
    if not ARCHIVE.is_file():
        raise FileNotFoundError(
            f"No existe {ARCHIVE}. Reejecuta externamente el pipeline PMTiles de fidelidad de ES-3 antes de ES-4C1A."
        )
    expected = json.loads(ES3_RESULTS.read_text(encoding="utf-8"))["pmtiles"]["fidelity_candidate"]
    actual = sha256(ARCHIVE)
    if actual != expected["sha256"] or actual != EXPECTED_SHA256:
        raise RuntimeError(f"Checksum PMTiles inesperado: {actual}")
    if ARCHIVE.stat().st_size != expected["bytes"]:
        raise RuntimeError(f"Tamaño PMTiles inesperado: {ARCHIVE.stat().st_size}")
    return {"path": str(ARCHIVE.relative_to(ROOT)), "bytes": ARCHIVE.stat().st_size, "sha256": actual}


def parse_single_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Parsea un único Range bytes=; devuelve límites inclusivos o None."""
    if not header or not header.startswith("bytes="):
        return None
    spec = header[6:].split(",", 1)[0]
    if "-" not in spec:
        raise ValueError("Range sin separador")
    start_text, end_text = spec.split("-", 1)
    if not start_text and not end_text:
        raise ValueError("Range vacío")
    if start_text:
        start = int(start_text)
        end = int(end_text) if end_text else size - 1
    else:
        suffix = int(end_text)
        if suffix <= 0:
            raise ValueError("Sufijo Range inválido")
        start = max(size - suffix, 0)
        end = size - 1
    if start < 0 or end < start or start >= size:
        raise ValueError("Range fuera de archivo")
    return start, min(end, size - 1)


class RangeState:
    def __init__(self):
        self.lock = threading.Lock()
        self.range_requests = 0
        self.full_pmtiles_requests = 0
        self.range_bytes = 0
        self.statuses = []
        self.initial_requests = 0
        self.initial_raw_bytes = 0
        self.detail_requests = 0

    def record(self, is_range: bool, bytes_sent: int, status: int) -> None:
        with self.lock:
            if is_range:
                self.range_requests += 1
                self.range_bytes += bytes_sent
            else:
                self.full_pmtiles_requests += 1
            self.statuses.append(status)

    def record_egif(self, path: str, bytes_sent: int) -> None:
        with self.lock:
            if path.endswith("/initial.json"):
                self.initial_requests += 1
                self.initial_raw_bytes += bytes_sent
            elif path.endswith("/detail.json"):
                self.detail_requests += 1

    def payload(self) -> dict:
        with self.lock:
            return {
                "range_requests": self.range_requests,
                "full_pmtiles_requests": self.full_pmtiles_requests,
                "range_bytes": self.range_bytes,
                "statuses": list(self.statuses),
                "initial_requests": self.initial_requests,
                "initial_raw_bytes": self.initial_raw_bytes,
                "detail_requests": self.detail_requests,
            }


class RangeRequestHandler(SimpleHTTPRequestHandler):
    range_state: RangeState

    def log_message(self, format, *args):  # noqa: A003
        pass

    def do_GET(self):  # noqa: N802
        if self.path.split("?", 1)[0] == "/__range_stats":
            body = json.dumps(self.range_state.payload()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def send_head(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()
        stream = open(path, "rb")
        size = os.fstat(stream.fileno()).st_size
        is_pmtiles = path.endswith(".pmtiles")
        try:
            requested = parse_single_range(self.headers.get("Range"), size)
        except (TypeError, ValueError):
            stream.close()
            self.send_error(416, "Range Not Satisfiable")
            return None
        if requested is None:
            self.send_response(200)
            self.send_header("Content-type", self.guess_type(path))
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.remaining = None
            if is_pmtiles:
                self.range_state.record(False, size, 200)
            elif path.endswith(("/initial.json", "/detail.json")):
                self.range_state.record_egif(path, size)
            return stream
        start, end = requested
        length = end - start + 1
        stream.seek(start)
        self.send_response(206)
        self.send_header("Content-type", self.guess_type(path))
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self.remaining = length
        if is_pmtiles:
            self.range_state.record(True, length, 206)
        return stream

    def copyfile(self, source, output):
        remaining = getattr(self, "remaining", None)
        if remaining is None:
            try:
                return super().copyfile(source, output)
            except (BrokenPipeError, ConnectionResetError):
                return None
        try:
            while remaining:
                block = source.read(min(64 * 1024, remaining))
                if not block:
                    break
                output.write(block)
                remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            return None


def start_server(background: bool = True) -> tuple[ThreadingHTTPServer, RangeState]:
    state = RangeState()
    class Handler(RangeRequestHandler):
        range_state = state
    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *args, **kwargs: Handler(*args, directory=str(ROOT), **kwargs))
    if background:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def run_case(chrome: str, scenario: str, device: str, egif_config: dict | None = None) -> dict:
    server, state = start_server()
    try:
        window = "390,844" if device == "mobile_390x844" else "1280,800"
        query = {"smoke": scenario}
        if egif_config:
            query.update({"from": egif_config["from"], "to": egif_config["to"], "egif_scope": egif_config["scope"]})
            if egif_config.get("rapid"):
                query["egif_rapid"] = "1"
        url = f"http://127.0.0.1:{server.server_port}/prototypes/es4c/index.html?{urlencode(query)}"
        result = run_page(chrome, url, window, timeout=120)
        result["server_range_stats"] = state.payload()
        result["device"] = device
        if egif_config:
            result["expected_egif"] = egif_config
        return result
    finally:
        server.shutdown()
        server.server_close()


def validate_results(payload: dict) -> list[str]:
    errors = []
    for result in payload.get("runs", []):
        label = f"{result.get('scenario')}::{result.get('device')}"
        if result.get("errors"):
            errors.append(f"{label}: {result['errors']}")
        if not result.get("selection", {}).get("geometry_id"):
            errors.append(f"{label}: no se seleccionó geometry_id")
        if not result.get("selection", {}).get("stable_at_next_zoom"):
            errors.append(f"{label}: geometry_id no se mantuvo visible al siguiente zoom")
        stats = result.get("server_range_stats", {})
        if stats.get("range_requests", 0) <= 0:
            errors.append(f"{label}: no se observó Range")
        if stats.get("full_pmtiles_requests", 0) != 0:
            errors.append(f"{label}: se descargó PMTiles completo")
        if any(status != 206 for status in stats.get("statuses", [])):
            errors.append(f"{label}: estados PMTiles distintos de 206")
        expected_egif = result.get("expected_egif")
        if expected_egif:
            egif = result.get("egif", {})
            if egif.get("status") != "complete":
                errors.append(f"{label}: EGIF no completó: {egif}")
            elif egif.get("summary", {}).get("records") != expected_egif["records"]:
                errors.append(f"{label}: recuento EGIF inesperado")
            if stats.get("detail_requests") != 0:
                errors.append(f"{label}: DETAIL fue solicitado en C1B1")
            if "initial_requests" in expected_egif and stats.get("initial_requests") != expected_egif["initial_requests"]:
                errors.append(f"{label}: assets INITIAL inesperados: {stats.get('initial_requests')}")
            if expected_egif.get("final_scope") and result.get("state", {}).get("autonomous_community_id") != expected_egif["final_scope"]:
                errors.append(f"{label}: cancelación no conservó el último ámbito")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--scenario", choices=SCENARIOS, action="append")
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--all-smokes", action="store_true")
    parser.add_argument("--egif-smoke", choices=tuple(EGIF_SMOKES), action="append")
    parser.add_argument("--all-egif-smokes", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "prototypes/es4c/smoke-results.json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--serve", action="store_true", help="sirve el prototipo interactivo local con HTTP Range")
    args = parser.parse_args()
    if args.serve:
        validate_archive()
        server, _state = start_server(background=False)
        print(f"http://127.0.0.1:{server.server_port}/prototypes/es4c/index.html", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        errors = validate_results(payload)
        print(json.dumps({"valid": not errors, "errors": errors, "output": str(args.output)}))
        return 0 if not errors else 1
    archive = validate_archive()
    requested_egif = args.egif_smoke or (tuple(EGIF_SMOKES) if args.all_egif_smokes else ())
    scenarios = args.scenario or (SCENARIOS if args.all_smokes else (() if requested_egif else ("spain",)))
    devices = []
    if args.desktop or not args.mobile:
        devices.append("desktop")
    if args.mobile:
        devices.append("mobile_390x844")
    rows = []
    for name in requested_egif:
        config = EGIF_SMOKES[name]
        egif_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in egif_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config))
    for scenario in scenarios:
        for device in devices:
            print(f"{scenario}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, scenario, device))
    payload = {"schema_version": 1, "archive": archive, "runs": rows}
    errors = validate_results(payload)
    payload["valid"] = not errors
    payload["errors"] = errors
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": not errors, "errors": errors, "output": str(args.output), "runs": len(rows)}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
