#!/usr/bin/env python3
"""Audita un PMTiles remoto sin descargarlo completo (ES-4C3D).

Sólo solicita HEAD y slices Range fijos. Los redirects se registran sin query
strings para no persistir URLs firmadas temporales. El navegador se prueba
desde el prototipo local mediante el override efímero ``pmtiles_url``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ASSET = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles"
EXPECTED_BYTES = 63052056
EXPECTED_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"
DEFAULT_OUTPUT = ROOT / "data/audit/hosting/es4c3d_real_hosting_range_validation.json"
SMOKE_PATH = ROOT / "prototypes/es4c/run_smoke.py"


def safe_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def headers_subset(headers: Any) -> dict[str, str | None]:
    values = {str(key).lower(): str(value) for key, value in headers.items()}
    keys = (
        "content-length", "content-range", "content-type", "accept-ranges", "cache-control",
        "etag", "last-modified", "content-encoding", "age", "x-cache",
        "x-cache-hits", "cdn-cache-status", "access-control-allow-origin",
        "access-control-expose-headers", "timing-allow-origin",
    )
    return {key: values.get(key) for key in keys if values.get(key) is not None}


class RedirectTracker(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.chain: list[dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        self.chain.append({"status": code, "from": safe_url(req.full_url), "to": safe_url(newurl)})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def request(url: str, method: str = "GET", headers: dict[str, str] | None = None) -> dict[str, Any]:
    tracker = RedirectTracker()
    opener = urllib.request.build_opener(tracker)
    started = time.perf_counter()
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "atlas-es4c3d-range-audit/1.0", **(headers or {})})
    try:
        with opener.open(req, timeout=60) as response:
            body = response.read()
            return {
                "status": response.status,
                "url_final": safe_url(response.geturl()),
                "headers": headers_subset(response.headers),
                "body": body,
                "redirects": tracker.chain,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            }
    except urllib.error.HTTPError as error:
        return {
            "status": error.code,
            "url_final": safe_url(error.geturl()),
            "headers": headers_subset(error.headers),
            "body": error.read(),
            "redirects": tracker.chain,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_content_range(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    try:
        unit, positions = value.split(" ", 1)
        span, total = positions.split("/", 1)
        start, end = span.split("-", 1)
        if unit != "bytes":
            return None
        return int(start), int(end), int(total)
    except (TypeError, ValueError):
        return None


def range_test(url: str, local: Path, start: int, end: int, if_range: str | None = None) -> dict[str, Any]:
    headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
    if if_range:
        headers["If-Range"] = if_range
    response = request(url, headers=headers)
    expected_length = end - start + 1
    with local.open("rb") as handle:
        handle.seek(start)
        expected = handle.read(expected_length)
    content_range = parse_content_range(response["headers"].get("content-range"))
    passed = (
        response["status"] == 206
        and len(response["body"]) == expected_length
        and content_range == (start, end, EXPECTED_BYTES)
        and response["body"] == expected
        and response["headers"].get("content-encoding") in (None, "identity")
    )
    return {
        "requested_range": f"bytes={start}-{end}",
        "status": response["status"],
        "content_range": response["headers"].get("content-range"),
        "content_length": response["headers"].get("content-length"),
        "content_encoding": response["headers"].get("content-encoding"),
        "bytes_received": len(response["body"]),
        "byte_identical_to_local": response["body"] == expected,
        "passed": passed,
        "elapsed_ms": response["elapsed_ms"],
        "headers": response["headers"],
        "redirects": response["redirects"],
        "url_final": response["url_final"],
    }


def load_smoke():
    spec = importlib.util.spec_from_file_location("es4c_smoke", SMOKE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def browser_smokes(url: str, chrome: str) -> list[dict[str, Any]]:
    smoke = load_smoke()
    scenarios = [
        ("spain_cold", "spain", "desktop", {"from": 1993, "to": 2002, "scope": "ES"}),
        ("galicia", "galicia", "desktop", {"from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12"}),
        ("ourense", "galicia", "desktop", {"from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:32054", "municipal_index": "parent"}),
        ("cangas", "spain", "desktop", {"from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent"}),
        ("elx", "pais_valencia", "desktop", {"from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent"}),
    ]
    rows: list[dict[str, Any]] = []
    for name, map_name, device, config in scenarios:
        result = smoke.run_case(chrome, map_name, device, {**config, "pmtiles_url": url})
        network = result.get("server_range_stats", {})
        errors = list(result.get("errors", []))
        source_status = result.get("coverage", {}).get("source_load_state", {}).get("esfire30")
        pmtiles_resources = result.get("after_navigation", {}).get("resources", {})
        valid = source_status == "ready" and not errors and network.get("full_pmtiles_requests", 0) == 0
        rows.append({
            "scenario": name,
            "status": "PASS" if valid else "FAIL",
            "source_status": source_status,
            "errors": errors,
            "remote_archive_url": result.get("archive_url"),
            "range_requests_local": network.get("range_requests", 0),
            "full_pmtiles_requests_local": network.get("full_pmtiles_requests", 0),
            "resource_transfer_bytes": pmtiles_resources.get("transfer_bytes"),
            "resource_requests": pmtiles_resources.get("requests"),
            "territory_filter": result.get("esfire30_territory_filter", {}).get("status"),
            "municipality_geometry_ids": result.get("esfire30_territory_filter", {}).get("geometry_ids"),
        })
    return rows


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    asset = payload.get("asset", {})
    if asset.get("bytes") != EXPECTED_BYTES or asset.get("sha256") != EXPECTED_SHA256:
        errors.append("asset_local_identity")
    for label in ("one_byte", "initial", "middle", "final", "repeat_initial"):
        if not payload.get("range_tests", {}).get(label, {}).get("passed"):
            errors.append(f"range:{label}")
    cors = payload.get("cors", {})
    if cors.get("access_control_allow_origin") not in ("*", "http://127.0.0.1", "http://localhost"):
        errors.append("cors_header")
    for smoke in payload.get("browser_smokes", []):
        if smoke.get("status") != "PASS":
            errors.append(f"browser:{smoke.get('scenario')}")
    return errors


def build(url: str, output: Path, chrome: str, with_browser: bool) -> dict[str, Any]:
    if not ASSET.is_file() or ASSET.stat().st_size != EXPECTED_BYTES or local_sha256(ASSET) != EXPECTED_SHA256:
        raise RuntimeError("El PMTiles local no coincide con el asset aprobado")
    head = request(url, method="HEAD")
    ranges = {
        "one_byte": range_test(url, ASSET, 0, 0),
        "initial": range_test(url, ASSET, 0, 16383),
        "middle": range_test(url, ASSET, 1048576, 1064959),
        "final": range_test(url, ASSET, EXPECTED_BYTES - 16384, EXPECTED_BYTES - 1),
    }
    ranges["repeat_initial"] = range_test(url, ASSET, 0, 16383)
    etag = head["headers"].get("etag") or ranges["initial"]["headers"].get("etag")
    if_range = range_test(url, ASSET, 16384, 32767, etag) if etag else None
    direct_headers = ranges["initial"]["headers"]
    payload: dict[str, Any] = {
        "schema_version": "es4c3d-real-hosting-range-validation-v1",
        "phase": "ES-4C3D",
        "hosting": {"stable_url": safe_url(url), "classification": None},
        "asset": {"local_path": str(ASSET.relative_to(ROOT)), "bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256, "geometry_count": 119498},
        "head": {key: value for key, value in head.items() if key != "body"},
        "range_tests": ranges,
        "if_range": if_range,
        "cors": {"access_control_allow_origin": direct_headers.get("access-control-allow-origin"), "access_control_expose_headers": direct_headers.get("access-control-expose-headers")},
        "cache_headers": {key: direct_headers.get(key) for key in ("cache-control", "etag", "last-modified", "age", "x-cache", "x-cache-hits", "cdn-cache-status")},
        "browser_smokes": browser_smokes(url, chrome) if with_browser else [],
        "full_download_observed": False,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }
    failures = validate(payload)
    payload["failures"] = failures
    payload["status"] = "PASS" if not failures else "FAIL"
    payload["hosting"]["classification"] = "RECOMMENDED" if not failures else "NOT_RECOMMENDED"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--browser", action="store_true", help="ejecuta cinco smokes Chromium contra el PMTiles remoto")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}))
        return 0 if not failures else 1
    payload = build(args.url, args.output, args.chrome, args.browser)
    print(json.dumps({"status": payload["status"], "failures": payload["failures"], "output": str(args.output)}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
