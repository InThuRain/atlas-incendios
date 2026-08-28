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
EGIF_DETAIL_SMOKES = {
    "a_gva_first_detail": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "single", "detail_requests": 1},
    "b_same_asset_cache": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "same_asset", "detail_requests": 1, "cached_second": True},
    "c_other_block": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "change_block", "detail_requests": 1, "other_block": True},
    "d_null_municipality": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "null_municipality", "detail_requests": 1},
    "e_unmapped_cause": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "single", "detail_requests": 1},
    "f_rapid_a_to_b": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "rapid", "detail_requests_min": 1},
    "g_independent_esfire": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "single", "detail_requests": 1},
    "h_mobile_list_detail": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES:CCAA:10", "detail": "single", "detail_requests": 1, "mobile_only": True},
}
C1C_SMOKES = {
    "a_spain_1975": {"map": "spain", "from": 1975, "to": 1975, "scope": "ES", "expect_geometry": False, "egif_status": "covered", "esfire_status": "no_coverage", "initial_requests": 0},
    "b_pais_valencia_1975": {"map": "pais_valencia", "from": 1975, "to": 1975, "scope": "ES:CCAA:10", "expect_geometry": False, "egif_status": "covered", "esfire_status": "no_coverage", "initial_requests": 1},
    "c_pais_valencia_1995": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "expect_geometry": True, "egif_status": "covered", "esfire_status": "covered", "initial_requests": 1},
    "d_pais_valencia_2023": {"map": "pais_valencia", "from": 2023, "to": 2023, "scope": "ES:CCAA:10", "expect_geometry": False, "egif_status": "covered", "esfire_status": "no_coverage", "initial_requests": 1},
    "e_partial_1980_1990": {"map": "pais_valencia", "from": 1980, "to": 1990, "scope": "ES:CCAA:10", "expect_geometry": True, "egif_status": "covered", "esfire_status": "covered", "esfire_effective": {"from": 1985, "to": 1990}, "initial_requests": 1},
    "f_toggle_egif": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "source_toggle": "egif:off", "expect_geometry": True, "egif_status": "disabled", "esfire_status": "covered", "initial_requests": 1},
    "g_toggle_esfire30": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "source_toggle": "esfire30:off", "expect_geometry": False, "egif_status": "covered", "esfire_status": "disabled", "initial_requests": 1},
    "h_rapid_range": {"map": "pais_valencia", "from": 1975, "to": 1975, "scope": "ES:CCAA:10", "range_rapid": True, "expect_geometry": True, "egif_status": "covered", "esfire_status": "covered", "final_range": {"from": 1995, "to": 1995}},
    "i_mobile_mixed": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "expect_geometry": True, "egif_status": "covered", "esfire_status": "covered", "initial_requests": 1, "mobile_only": True},
}
C1C2_SMOKES = {
    "a_gva_1995_round_trip": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "roundtrip": "none", "expect_geometry": True, "records": 467, "initial_requests_min": 1},
    "b_spain_1975_round_trip": {"map": "spain", "from": 1975, "to": 1975, "scope": "ES", "roundtrip": "none", "expect_geometry": False, "records": 4128, "initial_requests": 0, "esfire_status": "no_coverage"},
    "c_gva_2023_round_trip": {"map": "pais_valencia", "from": 2023, "to": 2023, "scope": "ES:CCAA:10", "roundtrip": "none", "expect_geometry": False, "records": 96, "initial_requests_min": 1, "esfire_status": "no_coverage"},
    "d_egif_selection_round_trip": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "roundtrip": "egif", "expect_geometry": True, "records": 467, "require_egif_selection": True},
    "e_geometry_selection_round_trip": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "roundtrip": "geometry", "expect_geometry": True, "records": 467, "require_geometry_selection": True},
    "f_both_selection_round_trip": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "roundtrip": "both", "expect_geometry": True, "records": 467, "require_egif_selection": True, "require_geometry_selection": True},
    "g_corrupt_hash": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "corrupt_hash": "#es4c-state-v99=broken", "expect_geometry": True, "safe_defaults": True},
    "h_history_restore": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "roundtrip": "none", "history_test": True, "expect_geometry": True, "records": 467},
    "i_mobile_copy_restore": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES:CCAA:10", "roundtrip": "both", "expect_geometry": True, "records": 467, "require_egif_selection": True, "require_geometry_selection": True, "mobile_only": True},
}
C2A_SMOKES = {
    "a_spain_boundaries": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "expect_geometry": True, "expected_territory": None},
    "b_pais_valencia_click": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "territory_click": "ES:CCAA:10", "expect_geometry": True, "expected_territory": "ES:CCAA:10", "records": 5159, "initial_requests": 1},
    "c_galicia_selector": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12", "expect_geometry": True, "expected_territory": "ES:CCAA:12", "records": 110605, "initial_requests": 1},
    "d_andalucia_selector": {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:01", "expect_geometry": False, "expected_territory": "ES:CCAA:01"},
    "e_canarias_selector": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:05", "expect_geometry": False, "expected_territory": "ES:CCAA:05"},
    "f_baleares_selector": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:04", "expect_geometry": False, "expected_territory": "ES:CCAA:04"},
    "g_ceuta_selector": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:18", "expect_geometry": False, "expected_territory": "ES:CCAA:18"},
    "h_melilla_selector": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:19", "expect_geometry": False, "expected_territory": "ES:CCAA:19"},
    "i_restore_c1c2_gva": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "state_hash": "#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM5LjMsImxvbiI6LTAuNywieiI6OH0sInRpbWUiOnsiZnJvbSI6MTk5NSwidG8iOjE5OTV9LCJ0ZXJyaXRvcnkiOnsic2NvcGUiOiJhdXRvbm9tb3VzX2NvbW11bml0eSIsImF1dG9ub21vdXNfY29tbXVuaXR5X2lkIjoiRVM6Q0NBQToxMCJ9LCJzb3VyY2VzIjp7ImVzZmlyZTMwIjp0cnVlLCJlZ2lmIjp0cnVlfSwic2VsZWN0aW9ucyI6eyJnZW9tZXRyeV9pZCI6bnVsbCwiZWdpZl9yZWNvcmRfaWQiOm51bGx9fQ", "territory_restore": True, "expect_geometry": False, "expected_territory": "ES:CCAA:10", "records": 467, "initial_requests": 1, "expected_center": [-0.7, 39.3], "expected_zoom": 8},
    "j_mobile_pais_valencia": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:10", "expect_geometry": True, "expected_territory": "ES:CCAA:10", "records": 467, "initial_requests": 1, "mobile_only": True},
}
C2A2_SMOKES = {
    "a_gva_alacant": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:03", "expected_province": "ES:PROV:03", "expected_parent": "ES:CCAA:10"},
    "b_gva_valencia_cache": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "province_sequence": "ES:PROV:03,ES:PROV:46", "expected_province": "ES:PROV:46", "expected_parent": "ES:CCAA:10", "same_ccaa_cache": True},
    "c_galicia_coruna": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:15", "expected_province": "ES:PROV:15", "expected_parent": "ES:CCAA:12"},
    "d_andalucia_sevilla": {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:41", "expected_province": "ES:PROV:41", "expected_parent": "ES:CCAA:01"},
    "e_canarias_las_palmas": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "province_select": "ES:PROV:35", "expected_province": "ES:PROV:35", "expected_parent": "ES:CCAA:05", "expect_geometry": False},
    "f_canarias_tenerife": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "province_select": "ES:PROV:38", "expected_province": "ES:PROV:38", "expected_parent": "ES:CCAA:05", "expect_geometry": False},
    "g_baleares": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "province_select": "ES:PROV:07", "expected_province": "ES:PROV:07", "expected_parent": "ES:CCAA:04", "expect_geometry": False},
    "h_ceuta": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:18", "expected_territory": "ES:CCAA:18", "expect_geometry": False},
    "i_melilla": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:19", "expected_territory": "ES:CCAA:19", "expect_geometry": False},
    "j_restore_province": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "state_hash": "#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM5LjMsImxvbiI6LTAuNywieiI6OH0sInRpbWUiOnsiZnJvbSI6MTk5NSwidG8iOjE5OTV9LCJ0ZXJyaXRvcnkiOnsic2NvcGUiOiJwcm92aW5jZSIsImF1dG9ub21vdXNfY29tbXVuaXR5X2lkIjoiRVM6Q0NBQToxMCIsInByb3ZpbmNlX2lkIjoiRVM6UFJPVjo0NiJ9LCJzb3VyY2VzIjp7ImVzZmlyZTMwIjp0cnVlLCJlZ2lmIjp0cnVlfSwic2VsZWN0aW9ucyI6eyJnZW9tZXRyeV9pZCI6bnVsbCwiZWdpZl9yZWNvcmRfaWQiOm51bGx9fQ", "territory_restore": True, "expected_province": "ES:PROV:46", "expected_parent": "ES:CCAA:10", "expect_geometry": False, "expected_center": [-0.7, 39.3], "expected_zoom": 8},
    "k_up_to_spain": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "province_select": "ES:PROV:03", "territory_up": True, "expected_territory": None},
    "l_mobile_gva": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "province_select": "ES:PROV:03", "expected_province": "ES:PROV:03", "expected_parent": "ES:CCAA:10", "mobile_only": True},
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
        self.detail_raw_bytes = 0

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
                self.detail_raw_bytes += bytes_sent

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
                "detail_raw_bytes": self.detail_raw_bytes,
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
            if egif_config.get("detail"):
                query["egif_detail"] = egif_config["detail"]
            if egif_config.get("source_toggle"):
                query["source_toggle"] = egif_config["source_toggle"]
            if egif_config.get("range_rapid"):
                query["range_rapid"] = "1"
            if egif_config.get("history_test"):
                query["history_test"] = "1"
            if egif_config.get("territory_select"):
                query["territory_select"] = egif_config["territory_select"]
            if egif_config.get("territory_click"):
                query["territory_click"] = egif_config["territory_click"]
            if egif_config.get("territory_restore"):
                query["territory_restore"] = "1"
            for key in ("province_select", "province_click", "province_sequence"):
                if egif_config.get(key):
                    query[key] = egif_config[key]
            if egif_config.get("territory_up"):
                query["territory_up"] = "1"
        url = f"http://127.0.0.1:{server.server_port}/prototypes/es4c/index.html?{urlencode(query)}"
        if egif_config and egif_config.get("corrupt_hash"):
            url += egif_config["corrupt_hash"]
        if egif_config and egif_config.get("state_hash"):
            url += egif_config["state_hash"]
        if egif_config and egif_config.get("roundtrip"):
            prepare_query = dict(query)
            prepare_query["state_prepare"] = egif_config["roundtrip"]
            prepare_url = f"http://127.0.0.1:{server.server_port}/prototypes/es4c/index.html?{urlencode(prepare_query)}"
            prepared = run_page(chrome, prepare_url, window, timeout=120)
            serialized_hash = prepared.get("serialized_hash")
            if not serialized_hash:
                return {"errors": ["No se produjo hash serializado"], "scenario": scenario, "device": device, "roundtrip_preparation": prepared}
            result = run_page(chrome, url + serialized_hash, window, timeout=120)
            result["roundtrip_preparation"] = prepared
        else:
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
        expect_geometry = result.get("expected_egif", {}).get("expect_geometry", True)
        if expect_geometry and not result.get("selection", {}).get("geometry_id"):
            errors.append(f"{label}: no se seleccionó geometry_id")
        if expect_geometry and not result.get("selection", {}).get("stable_at_next_zoom"):
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
            if expected_egif.get("egif_status") == "disabled" and egif.get("status") != "inactive":
                errors.append(f"{label}: EGIF desactivado no quedó inactivo: {egif}")
            elif expected_egif.get("egif_status") != "disabled" and egif.get("status") != "complete":
                errors.append(f"{label}: EGIF no completó: {egif}")
            elif "records" in expected_egif and egif.get("summary", {}).get("records") != expected_egif["records"]:
                errors.append(f"{label}: recuento EGIF inesperado")
            if not expected_egif.get("detail") and expected_egif.get("roundtrip") not in ("egif", "both") and stats.get("detail_requests") != 0:
                errors.append(f"{label}: DETAIL fue solicitado en C1B1")
            if "initial_requests" in expected_egif and stats.get("initial_requests") != expected_egif["initial_requests"]:
                errors.append(f"{label}: assets INITIAL inesperados: {stats.get('initial_requests')}")
            if stats.get("initial_requests", 0) < expected_egif.get("initial_requests_min", 0):
                errors.append(f"{label}: INITIAL no fue restaurado")
            if expected_egif.get("final_scope") and result.get("state", {}).get("autonomous_community_id") != expected_egif["final_scope"]:
                errors.append(f"{label}: cancelación no conservó el último ámbito")
            coverage = result.get("coverage", {})
            if expected_egif.get("egif_status") and coverage.get("egif", {}).get("status") != expected_egif["egif_status"]:
                errors.append(f"{label}: cobertura EGIF inesperada: {coverage.get('egif')}")
            if expected_egif.get("esfire_status") and coverage.get("esfire30", {}).get("status") != expected_egif["esfire_status"]:
                errors.append(f"{label}: cobertura ESFire30 inesperada: {coverage.get('esfire30')}")
            if expected_egif.get("esfire_effective") != None and coverage.get("esfire30", {}).get("effective_coverage") != expected_egif["esfire_effective"]:
                errors.append(f"{label}: intersección ESFire30 inesperada")
            if expected_egif.get("final_range") and coverage.get("requested_range") != expected_egif["final_range"]:
                errors.append(f"{label}: cambio rápido de rango dejó estado obsoleto")
            if expected_egif.get("require_egif_selection") and not result.get("state", {}).get("selected_egif_record_id"):
                errors.append(f"{label}: no restauró selección EGIF")
            if expected_egif.get("require_geometry_selection") and not result.get("state", {}).get("selected_geometry_id"):
                errors.append(f"{label}: no restauró selección ESFire30")
            if expected_egif.get("safe_defaults"):
                state = result.get("state", {})
                if state.get("from") != 1985 or state.get("to") != 2021 or state.get("autonomous_community_id") is not None:
                    errors.append(f"{label}: hash corrupto no aplicó defaults seguros")
            if expected_egif.get("history_test") and result.get("history_round_trip", {}).get("final_range") != {"from": 1995, "to": 1995}:
                errors.append(f"{label}: back/forward básico no restauró el estado")
            expected_territory = expected_egif.get("expected_territory", "__absent__")
            if expected_territory != "__absent__":
                territory = result.get("territory_layer", {})
                if not territory.get("loaded"):
                    errors.append(f"{label}: capa territorial BDLJE no cargó")
                elif territory.get("selected_territory_id") != expected_territory:
                    errors.append(f"{label}: highlight territorial inesperado")
                if expected_territory and not territory.get("selected_bounds"):
                    errors.append(f"{label}: territorio seleccionado sin bounds oficiales")
            if expected_egif.get("expected_center"):
                center = result.get("state", {}).get("center") or []
                expected_center = expected_egif["expected_center"]
                if len(center) != 2 or any(abs(center[index] - expected_center[index]) > 0.0001 for index in range(2)):
                    errors.append(f"{label}: restore territorial cambió el centro serializado")
                if abs(result.get("state", {}).get("zoom", 0) - expected_egif["expected_zoom"]) > 0.01:
                    errors.append(f"{label}: restore territorial cambió el zoom serializado")
            expected_province = expected_egif.get("expected_province")
            if expected_province:
                province = result.get("province_layer", {})
                if not province.get("loaded"):
                    errors.append(f"{label}: capa provincial BDLJE no cargó")
                elif province.get("selected_province_id") != expected_province:
                    errors.append(f"{label}: highlight provincial inesperado")
                elif not province.get("selected_bounds"):
                    errors.append(f"{label}: provincia seleccionada sin bounds oficiales")
                if result.get("state", {}).get("autonomous_community_id") != expected_egif.get("expected_parent"):
                    errors.append(f"{label}: parent CCAA provincial inesperado")
            if expected_egif.get("same_ccaa_cache"):
                interaction = result.get("province_layer", {}).get("interaction", {})
                if interaction.get("first_initial_requests") != interaction.get("final_initial_requests"):
                    errors.append(f"{label}: cambió provincia y volvió a pedir INITIAL de la misma CCAA")
            if expected_egif.get("detail"):
                detail = result.get("egif_detail", {})
                if not detail or detail.get("status") == "missing_initial":
                    errors.append(f"{label}: no se ejecutó selección DETAIL")
                if expected_egif["detail"] in ("single", "null_municipality", "change_block") and detail.get("result", {}).get("status") != "complete":
                    errors.append(f"{label}: DETAIL no completó: {detail}")
                if stats.get("detail_requests", 0) < expected_egif.get("detail_requests_min", expected_egif.get("detail_requests", 0)):
                    errors.append(f"{label}: DETAIL insuficiente")
                if "detail_requests" in expected_egif and stats.get("detail_requests") != expected_egif["detail_requests"]:
                    errors.append(f"{label}: requests DETAIL inesperados: {stats.get('detail_requests')}")
                if expected_egif["detail"] == "rapid" and detail.get("final_record_id") != detail.get("second", {}).get("record_id"):
                    errors.append(f"{label}: DETAIL stale reemplazó la selección B")
                if expected_egif.get("cached_second") and not detail.get("second", {}).get("result", {}).get("metrics", {}).get("cached"):
                    errors.append(f"{label}: la segunda selección no reutilizó DETAIL")
                if expected_egif.get("other_block") and not detail.get("result", {}).get("asset_id", "").endswith("2003-2012"):
                    errors.append(f"{label}: DETAIL no cambió al bloque temporal esperado")
                if expected_egif["detail"] == "null_municipality" and detail.get("result", {}).get("record", {}).get("municipality_id") is not None:
                    errors.append(f"{label}: municipio null no se preservó")
                if expected_egif["detail"] == "single" and detail.get("result", {}).get("record", {}).get("canonical_cause") is not None:
                    errors.append(f"{label}: se inventó causa canónica")
                browser = result.get("egif_record_browser", {})
                if not browser.get("visible") or browser.get("rows", 0) <= 0:
                    errors.append(f"{label}: lista paginada EGIF no visible")
                if not browser.get("detail_visible"):
                    errors.append(f"{label}: ficha EGIF no visible")
                if expected_egif.get("detail") == "single" and result.get("state", {}).get("selected_geometry_id") and not result.get("state", {}).get("selected_egif_record_id"):
                    errors.append(f"{label}: selección EGIF no coexistió con ESFire30")
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
    parser.add_argument("--egif-detail-smoke", choices=tuple(EGIF_DETAIL_SMOKES), action="append")
    parser.add_argument("--all-egif-detail-smokes", action="store_true")
    parser.add_argument("--c1c-smoke", choices=tuple(C1C_SMOKES), action="append")
    parser.add_argument("--all-c1c-smokes", action="store_true")
    parser.add_argument("--c1c2-smoke", choices=tuple(C1C2_SMOKES), action="append")
    parser.add_argument("--all-c1c2-smokes", action="store_true")
    parser.add_argument("--c2a-smoke", choices=tuple(C2A_SMOKES), action="append")
    parser.add_argument("--all-c2a-smokes", action="store_true")
    parser.add_argument("--c2a2-smoke", choices=tuple(C2A2_SMOKES), action="append")
    parser.add_argument("--all-c2a2-smokes", action="store_true")
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
    requested_detail = args.egif_detail_smoke or (tuple(EGIF_DETAIL_SMOKES) if args.all_egif_detail_smokes else ())
    requested_c1c = args.c1c_smoke or (tuple(C1C_SMOKES) if args.all_c1c_smokes else ())
    requested_c1c2 = args.c1c2_smoke or (tuple(C1C2_SMOKES) if args.all_c1c2_smokes else ())
    requested_c2a = args.c2a_smoke or (tuple(C2A_SMOKES) if args.all_c2a_smokes else ())
    requested_c2a2 = args.c2a2_smoke or (tuple(C2A2_SMOKES) if args.all_c2a2_smokes else ())
    scenarios = args.scenario or (SCENARIOS if args.all_smokes else (() if (requested_egif or requested_detail or requested_c1c or requested_c1c2 or requested_c2a or requested_c2a2) else ("spain",)))
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
    for name in requested_detail:
        config = EGIF_DETAIL_SMOKES[name]
        detail_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in detail_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config))
    for name in requested_c1c:
        config = C1C_SMOKES[name]
        c1c_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c1c_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config))
    for name in requested_c1c2:
        config = C1C2_SMOKES[name]
        c1c2_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c1c2_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config))
    for name in requested_c2a:
        config = C2A_SMOKES[name]
        c2a_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c2a_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config))
    for name in requested_c2a2:
        config = C2A2_SMOKES[name]
        c2a2_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c2a2_devices:
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
