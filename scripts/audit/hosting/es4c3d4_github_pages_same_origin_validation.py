#!/usr/bin/env python3
"""Valida Pages same-origin C3D4 sin reconstruir ni descargar el PMTiles entero."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = ROOT / "scripts/audit/hosting/es4c3d_real_hosting_range.py"
CDP_PATH = ROOT / "benchmarks/gva_frontend/cdp_client.py"
ASSET = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles"
EXPECTED_BYTES = 63052056
EXPECTED_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"
DEFAULT_BASE_URL = "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/"
DEFAULT_OUTPUT = ROOT / "data/audit/hosting/es4c3d4_github_pages_same_origin_validation.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CORE = load_module(CORE_PATH, "es4c3d4_range_core")
CDP = load_module(CDP_PATH, "es4c3d4_cdp")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_base_url(value: str) -> str:
    return value.rstrip("/") + "/"


def asset_url(base_url: str) -> str:
    return normalize_base_url(base_url) + "data/esfire30-national-fidelity-territories.pmtiles"


def harness_url(base_url: str, smoke: str) -> str:
    return normalize_base_url(base_url) + "es4c3d4/?" + urlencode({"smoke": smoke})


def local_identity() -> dict[str, Any]:
    if not ASSET.is_file() or ASSET.stat().st_size != EXPECTED_BYTES or sha256(ASSET) != EXPECTED_SHA256:
        raise RuntimeError("El PMTiles local no coincide con el asset nacional aprobado")
    return {"path": str(ASSET.relative_to(ROOT)), "bytes": EXPECTED_BYTES, "sha256": EXPECTED_SHA256, "geometry_count": 119498}


def range_test(url: str, start: int, end: int) -> dict[str, Any]:
    response = CORE.request(url, headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"})
    with ASSET.open("rb") as source:
        source.seek(start)
        expected = source.read(end - start + 1)
    content_range = CORE.parse_content_range(response["headers"].get("content-range"))
    passed = response["status"] == 206 and content_range == (start, end, EXPECTED_BYTES) and response["body"] == expected
    return {
        "requested_range": f"bytes={start}-{end}", "status": response["status"],
        "content_range": response["headers"].get("content-range"), "content_length": response["headers"].get("content-length"),
        "bytes_received": len(response["body"]), "byte_identical_to_local": response["body"] == expected,
        "elapsed_ms": response["elapsed_ms"], "headers": response["headers"], "passed": passed,
    }


def smoke_row(name: str, result: dict[str, Any], expected_municipality_ids: int | None = None) -> dict[str, Any]:
    pmtiles = result.get("pmtiles", {})
    rows = pmtiles.get("rows", [])
    errors = list(result.get("errors", [])) + list(result.get("runtime_errors", []))
    valid = (
        result.get("source_status") == "ready" and not errors and pmtiles.get("range_requests", 0) > 0
        and not pmtiles.get("full_download_observed") and result.get("browser_range_fetch", {}).get("status") == 206
    )
    if expected_municipality_ids is not None:
        valid = valid and result.get("territory_membership_count") == expected_municipality_ids
    return {
        "scenario": name, "status": "PASS" if valid else "FAIL", "source_status": result.get("source_status"),
        "rendered_features": result.get("rendered_features"), "selected_geometry_id": result.get("selected_geometry_id"),
        "browser_range_fetch": result.get("browser_range_fetch"), "map_ready_ms": result.get("map_ready_ms"),
        "requests": pmtiles.get("requests", 0), "range_requests": pmtiles.get("range_requests", 0),
        "response_bytes_total": pmtiles.get("bytes", 0), "full_download_observed": pmtiles.get("full_download_observed", False),
        "statuses": sorted({row.get("status") for row in rows}, key=lambda value: str(value)),
        "content_range_samples": [row.get("content_range") for row in rows if row.get("content_range")][:4],
        "territory_membership_count": result.get("territory_membership_count"), "errors": errors,
    }


def run_smoke(base_url: str, chrome: str, name: str, device: str = "desktop", expected_municipality_ids: int | None = None) -> dict[str, Any]:
    window = "390,844" if device == "mobile_390x844" else "1280,800"
    result = CDP.run_page(chrome, harness_url(base_url, name), window, timeout=150)
    return smoke_row(name if device == "desktop" else f"mobile_{name}", result, expected_municipality_ids)


def run_sequence(base_url: str, chrome: str, names: list[str], label: str) -> list[dict[str, Any]]:
    urls = [harness_url(base_url, name) for name in names]
    results = CDP.run_pages(chrome, urls, "1280,800", timeout=150)
    return [smoke_row(f"{label}_{index + 1}_{name}", result) for index, (name, result) in enumerate(zip(names, results))]


def validate(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    asset = payload.get("asset", {})
    if asset.get("bytes") != EXPECTED_BYTES or asset.get("sha256") != EXPECTED_SHA256:
        failures.append("local_asset_identity")
    if payload.get("head", {}).get("status") != 200 or payload.get("head", {}).get("headers", {}).get("content-length") != str(EXPECTED_BYTES):
        failures.append("head")
    for name in ("one_byte", "initial", "middle", "final"):
        if not payload.get("range_tests", {}).get(name, {}).get("passed"):
            failures.append(f"range:{name}")
    for group, rows in payload.get("browser_smokes", {}).items():
        for row in rows:
            if row.get("status") != "PASS":
                failures.append(f"browser:{group}:{row.get('scenario')}")
    if payload.get("full_download_observed"):
        failures.append("full_download")
    return failures


def build(base_url: str, output: Path, chrome: str) -> dict[str, Any]:
    base_url = normalize_base_url(base_url)
    url = asset_url(base_url)
    asset = local_identity()
    head_response = CORE.request(url, method="HEAD")
    head = {key: value for key, value in head_response.items() if key != "body"}
    ranges = {
        "one_byte": range_test(url, 0, 0),
        "initial": range_test(url, 0, 16383),
        "middle": range_test(url, 1048576, 1064959),
        "final": range_test(url, EXPECTED_BYTES - 16384, EXPECTED_BYTES - 1),
    }
    main = [
        run_smoke(base_url, chrome, "spain"), run_smoke(base_url, chrome, "galicia"), run_smoke(base_url, chrome, "ourense"),
        run_smoke(base_url, chrome, "cangas", expected_municipality_ids=2610), run_smoke(base_url, chrome, "elx", expected_municipality_ids=6),
    ]
    reload = run_sequence(base_url, chrome, ["elx", "elx"], "reload")
    repeat = run_sequence(base_url, chrome, ["spain", "galicia", "spain", "galicia"], "territorial_repeat")
    mobile = [run_smoke(base_url, chrome, "elx", "mobile_390x844", 6), run_smoke(base_url, chrome, "cangas", "mobile_390x844", 2610)]
    groups = {"main": main, "reload": reload, "territorial_repeat": repeat, "mobile": mobile}
    all_rows = [row for rows in groups.values() for row in rows]
    payload: dict[str, Any] = {
        "schema_version": "es4c3d4-github-pages-same-origin-validation-v1", "phase": "ES-4C3D4",
        "asset": asset, "endpoint": {"base_url": base_url, "pmtiles_url": url, "type": "github_pages_same_origin_staging"},
        "head": head, "range_tests": ranges,
        "cors": {"required": False, "result": "NOT_REQUIRED_SAME_ORIGIN", "access_control_allow_origin": ranges["initial"]["headers"].get("access-control-allow-origin")},
        "browser_smokes": groups,
        "pages_request_counts": {row["scenario"]: {"requests": row["requests"], "range_requests": row["range_requests"], "bytes": row["response_bytes_total"]} for row in all_rows},
        "full_download_observed": any(row["full_download_observed"] for row in all_rows),
        "cdn_cache_validation": "NOT_VALIDATED_GITHUB_PAGES_STAGING", "warnings": ["GitHub Pages staging no equivale a una decisión de hosting de producción.", "La ausencia de ACAO no es un fallo: PMTiles y el harness se sirven desde el mismo origin."],
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "chrome": chrome},
    }
    payload["failures"] = validate(payload)
    payload["status"] = "PASS" if not payload["failures"] else "FAIL"
    payload["pages_same_origin_validation"] = payload["status"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = validate(payload)
        print(json.dumps({"valid": not failures, "failures": failures, "output": str(args.output)}))
        return 0 if not failures else 1
    payload = build(args.base_url, args.output, args.chrome)
    print(json.dumps({"status": payload["status"], "failures": payload["failures"], "output": str(args.output)}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
