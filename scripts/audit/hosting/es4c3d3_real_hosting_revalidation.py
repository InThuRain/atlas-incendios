#!/usr/bin/env python3
"""Revalida R2 r2.dev desde HTTP y Chromium sin descargar el PMTiles completo.

ES-4C3D3 reutiliza el auditor C3D para la semántica de Range, pero exige el
origin fijo que autoriza la CORS de staging y captura las respuestas que el
protocolo PMTiles solicita realmente desde Chromium.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = ROOT / "scripts/audit/hosting/es4c3d_real_hosting_range.py"
SMOKE_PATH = ROOT / "prototypes/es4c/run_smoke.py"
ASSET = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles"
EXPECTED_BYTES = 63052056
EXPECTED_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"
ORIGIN = "http://127.0.0.1:8765"
ENDPOINT = "https://pub-96622990cd314a1c8431ce65ec2c25ca.r2.dev/esfire30-national-fidelity-territories.pmtiles"
DEFAULT_OUTPUT = ROOT / "data/audit/hosting/es4c3d3_real_hosting_revalidation.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CORE = load_module(CORE_PATH, "es4c3d_range_core")


def local_identity() -> dict[str, Any]:
    if not ASSET.is_file() or ASSET.stat().st_size != EXPECTED_BYTES:
        raise RuntimeError("El PMTiles local no tiene el tamaño aprobado")
    checksum = CORE.local_sha256(ASSET)
    if checksum != EXPECTED_SHA256:
        raise RuntimeError("El PMTiles local no tiene el SHA-256 aprobado")
    return {"local_path": str(ASSET.relative_to(ROOT)), "bytes": EXPECTED_BYTES, "sha256": checksum, "geometry_count": 119498}


def first_local_byte() -> int:
    with ASSET.open("rb") as source:
        return source.read(1)[0]


def range_test(url: str, start: int, end: int) -> dict[str, Any]:
    response = CORE.request(url, headers={
        "Origin": ORIGIN,
        "Range": f"bytes={start}-{end}",
        "Accept-Encoding": "identity",
    })
    with ASSET.open("rb") as source:
        source.seek(start)
        expected = source.read(end - start + 1)
    content_range = CORE.parse_content_range(response["headers"].get("content-range"))
    return {
        "requested_range": f"bytes={start}-{end}",
        "status": response["status"],
        "content_range": response["headers"].get("content-range"),
        "content_length": response["headers"].get("content-length"),
        "bytes_received": len(response["body"]),
        "byte_identical_to_local": response["body"] == expected,
        "headers": response["headers"],
        "elapsed_ms": response["elapsed_ms"],
        "passed": response["status"] == 206 and content_range == (start, end, EXPECTED_BYTES) and response["body"] == expected,
    }


def remote_stats(result: dict[str, Any]) -> dict[str, Any]:
    values = result.get("remote_pmtiles", {})
    rows = values.get("rows", [])
    return {
        "r2_request_count": values.get("requests", 0),
        "r2_range_request_count": values.get("range_requests", 0),
        "r2_response_bytes_total": values.get("response_bytes", 0),
        "statuses": sorted({row.get("status") for row in rows}, key=lambda value: str(value)),
        "content_range_samples": [row.get("content_range") for row in rows if row.get("content_range")][:4],
        "full_download_observed": bool(values.get("full_download_observed")),
        "request_errors": [row.get("error") for row in rows if row.get("error") and not row.get("aborted")],
        "aborted_requests": sum(1 for row in rows if row.get("aborted")),
    }


def smoke_row(name: str, result: dict[str, Any], expectation: dict[str, Any]) -> dict[str, Any]:
    stats = remote_stats(result)
    source_status = result.get("coverage", {}).get("source_load_state", {}).get("esfire30")
    errors = list(result.get("errors", []))
    direct_fetch = result.get("browser_range_fetch")
    valid = (
        source_status == "ready"
        and not errors
        and not stats["request_errors"]
        and not stats["full_download_observed"]
        and stats["r2_range_request_count"] > 0
    )
    if expectation.get("municipality_ids") is not None:
        valid = valid and result.get("esfire30_territory_filter", {}).get("geometry_ids") == expectation["municipality_ids"]
    if expectation.get("require_independent_selections"):
        selected = result.get("consolidation", {}).get("selection") or {}
        valid = valid and bool(selected.get("geometry_id")) and bool(selected.get("egif_record_id"))
    if expectation.get("browser_fetch"):
        valid = valid and direct_fetch == {
            "status": 206, "content_range": "bytes 0-0/63052056", "content_length": "1", "bytes": 1,
            "first_byte": first_local_byte(),
        }
    return {
        "scenario": name,
        "status": "PASS" if valid else "FAIL",
        "source_status": source_status,
        "errors": errors,
        "browser_range_fetch": direct_fetch,
        "territory_filter": result.get("esfire30_territory_filter", {}).get("status"),
        "municipality_geometry_ids": result.get("esfire30_territory_filter", {}).get("geometry_ids"),
        "selected_geometry_id": result.get("state", {}).get("selected_geometry_id"),
        "selected_egif_record_id": result.get("state", {}).get("selected_egif_record_id"),
        "heap_delta_bytes": result.get("heap_delta_bytes"),
        "map_errors": result.get("map_error_events", []),
        **stats,
    }


def browser_smokes(url: str, chrome: str) -> dict[str, Any]:
    smoke = load_module(SMOKE_PATH, "es4c3d3_smoke")
    common = {"pmtiles_url": url, "pmtiles_telemetry": True}
    scenarios = [
        ("spain_cold", "spain", "desktop", {"from": 1993, "to": 2002, "scope": "ES", "browser_range_fetch": True}, {"browser_fetch": True}),
        ("galicia", "galicia", "desktop", {"from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12"}, {}),
        ("ourense", "galicia", "desktop", {"from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:32"}, {}),
        ("cangas", "spain", "desktop", {"from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent"}, {"municipality_ids": 2610}),
        ("elx", "pais_valencia", "desktop", {"from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent", "c3a_select_both": True}, {"municipality_ids": 6, "require_independent_selections": True}),
    ]
    rows = []
    for name, map_name, device, config, expectation in scenarios:
        result = smoke.run_case(chrome, map_name, device, {**common, **config}, server_port=8765)
        rows.append(smoke_row(name, result, expectation))

    # Dos navegaciones a la misma URL comparten un único perfil Chromium
    # efímero: evidencia de recarga sin confundirlo con caché CDN de r2.dev.
    reload_config = {**common, "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent"}
    reload_results = smoke.run_case_sequence(chrome, [("reload_elx_first", "desktop", reload_config), ("reload_elx_second", "desktop", reload_config)], server_port=8765)
    reload_rows = [smoke_row(name, result, {"municipality_ids": 6}) for (name, _device, _config), result in zip([(item[0], item[1], item[2]) for item in [("reload_elx_first", "desktop", reload_config), ("reload_elx_second", "desktop", reload_config)]], reload_results)]

    repeat_cases = [
        ("repeat_spain_1", "desktop", {**common, "from": 1993, "to": 2002, "scope": "ES"}),
        ("repeat_galicia_1", "desktop", {**common, "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12"}),
        ("repeat_spain_2", "desktop", {**common, "from": 1993, "to": 2002, "scope": "ES"}),
        ("repeat_galicia_2", "desktop", {**common, "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12"}),
    ]
    repeat_results = smoke.run_case_sequence(chrome, repeat_cases, server_port=8765)
    repeat_rows = [smoke_row(name, result, {}) for (name, _device, _config), result in zip(repeat_cases, repeat_results)]

    mobile_cases = [
        ("mobile_elx", "pais_valencia", "mobile_390x844", {**common, "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent"}, {"municipality_ids": 6}),
        ("mobile_cangas", "spain", "mobile_390x844", {**common, "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent"}, {"municipality_ids": 2610}),
    ]
    mobile_rows = []
    for name, map_name, device, config, expectation in mobile_cases:
        result = smoke.run_case(chrome, map_name, device, config, server_port=8765)
        mobile_rows.append(smoke_row(name, result, expectation))
    return {"main": rows, "reload": reload_rows, "territorial_repeat": repeat_rows, "mobile": mobile_rows}


def validate(payload: dict[str, Any]) -> list[str]:
    failures = []
    if payload.get("asset", {}).get("bytes") != EXPECTED_BYTES or payload.get("asset", {}).get("sha256") != EXPECTED_SHA256:
        failures.append("local_asset_identity")
    head = payload.get("head", {})
    if head.get("status") != 200 or head.get("headers", {}).get("content-length") != str(EXPECTED_BYTES):
        failures.append("head")
    for name in ("one_byte", "initial", "middle", "final"):
        if not payload.get("range_tests", {}).get(name, {}).get("passed"):
            failures.append(f"range:{name}")
    cors = payload.get("cors", {})
    if cors.get("access_control_allow_origin") != ORIGIN:
        failures.append("cors_http")
    if not payload.get("browser_fetch", {}).get("passed"):
        failures.append("browser_fetch")
    for group, rows in payload.get("browser_smokes", {}).items():
        for row in rows:
            if row.get("status") != "PASS":
                failures.append(f"browser:{group}:{row.get('scenario')}")
    if payload.get("full_download_observed"):
        failures.append("full_download")
    return failures


def build(url: str, output: Path, chrome: str) -> dict[str, Any]:
    asset = local_identity()
    head_response = CORE.request(url, method="HEAD", headers={"Origin": ORIGIN})
    head = {key: value for key, value in head_response.items() if key != "body"}
    ranges = {
        "one_byte": range_test(url, 0, 0),
        "initial": range_test(url, 0, 16383),
        "middle": range_test(url, 1048576, 1064959),
        "final": range_test(url, EXPECTED_BYTES - 16384, EXPECTED_BYTES - 1),
    }
    browser = browser_smokes(url, chrome)
    all_rows = [row for rows in browser.values() for row in rows]
    browser_fetch_row = browser["main"][0].get("browser_range_fetch")
    browser_fetch = {
        "result": browser_fetch_row,
        "passed": browser_fetch_row == {"status": 206, "content_range": "bytes 0-0/63052056", "content_length": "1", "bytes": 1, "first_byte": first_local_byte()},
    }
    direct_headers = ranges["initial"]["headers"]
    payload: dict[str, Any] = {
        "schema_version": "es4c3d3-real-hosting-revalidation-v1",
        "phase": "ES-4C3D3",
        "asset": asset,
        "endpoint": {"url": CORE.safe_url(url), "type": "cloudflare_r2_dev_staging", "origin": ORIGIN},
        "head": head,
        "range_tests": ranges,
        "cors": {"access_control_allow_origin": direct_headers.get("access-control-allow-origin"), "access_control_expose_headers": direct_headers.get("access-control-expose-headers")},
        "browser_fetch": browser_fetch,
        "browser_smokes": browser,
        "r2_request_counts": {row["scenario"]: {"requests": row["r2_request_count"], "range_requests": row["r2_range_request_count"], "bytes": row["r2_response_bytes_total"]} for row in all_rows},
        "full_download_observed": any(row["full_download_observed"] for row in all_rows),
        "cdn_cache_validation": "NOT_APPLICABLE_R2_DEV",
        "warnings": ["STAGING_WARNING: el objeto r2.dev no expone Cache-Control; no bloquea Range/CORS/browser.", "R2_DEV_CDN_CACHE_VALIDATION=NOT_APPLICABLE: r2.dev no valida la caché CDN de producción."],
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "chrome": chrome},
    }
    payload["failures"] = validate(payload)
    payload["status"] = "PASS" if not payload["failures"] else "FAIL"
    payload["r2_dev_staging_validation"] = "PASS" if payload["status"] == "PASS" else "FAIL"
    payload["real_browser_range_cors"] = "PASS" if payload["status"] == "PASS" else "FAIL"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=ENDPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}))
        return 0 if not failures else 1
    payload = build(args.url, args.output, args.chrome)
    print(json.dumps({"status": payload["status"], "failures": payload["failures"], "output": str(args.output)}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
