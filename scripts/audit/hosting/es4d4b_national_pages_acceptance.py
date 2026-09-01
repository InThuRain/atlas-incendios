#!/usr/bin/env python3
"""Aceptación remota ES-4D4B del artifact nacional en GitHub Pages staging.

No construye datasets ni modifica el runtime. Comprueba el árbol D4A1 ya
aprobado, HTTP Range y smokes Chromium directamente contra el origin Pages.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[3]
BASE_URL = "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/"
OUTPUT = ROOT / "data/audit/production/es4d4b_national_production_staging_acceptance.json"
PMTILES_PATH = "data/esfire30/v1/3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe/esfire30-national-fidelity-territories.pmtiles"
PMTILES_BYTES = 63052056
PMTILES_SHA256 = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"
PAYLOAD_FINGERPRINT = "bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8"
MANIFEST_SHA256 = "c2c57a70130fd2e4527ac6a50ebb1c86e73bb667d6c5c5940f9b015b9823aceb"
SITE_IDENTITY_SHA256 = "df9b4206eea460942717705559a9705a9fae7fc3039436c199e09118a2019401"

CORE_PATH = ROOT / "scripts/audit/hosting/es4c3d_real_hosting_range.py"
CDP_PATH = ROOT / "benchmarks/gva_frontend/cdp_client.py"
ARTIFACT_CHECK_PATH = ROOT / "scripts/build_national_pages_artifact.py"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CORE = load_module(CORE_PATH, "es4d4b_range_core")
CDP = load_module(CDP_PATH, "es4d4b_cdp")
ASSEMBLER = load_module(ARTIFACT_CHECK_PATH, "es4d4b_artifact")

LEGACY_1995 = "#v=1&lat=39.30000&lng=-0.70000&z=8&from=1995&to=1995&src=egif%2Cesfire30%2Cicv&province=all&min_area=0&gif=0"
LEGACY_2024 = "#v=1&lat=38.50000&lng=-0.50000&z=10&from=2024&to=2024&src=icv&province=alicante&min_area=0&gif=0&entity=gva%3Apif-cv%3A2024AL0005&geometry=gva%3Ageometry%3A2024%3A121%3A13587"
LEGACY_2024_RECORD_ONLY = "#v=1&lat=38.50000&lng=-0.50000&z=10&from=2024&to=2024&src=icv&province=alicante&min_area=0&gif=0&entity=gva%3Apif-cv%3A2024AL0005"
LEGACY_ELX_2025 = "#v=1&lat=38.17000&lng=-0.71000&z=11&from=2025&to=2025&src=effis&province=alicante&municipality=03065&min_area=10&gif=0&entity=effis%3Arda%3A285361%3Af05085eba622a5bb&geometry=effis%3Arda%3A285361%3Af05085eba622a5bb"
NATIVE_ELX = "#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM4LjE3OTEsImxvbiI6LTAuNzE4OTIsInoiOjExLjQ4fSwidGltZSI6eyJmcm9tIjoxOTkzLCJ0byI6MTk5M30sInRlcnJpdG9yeSI6eyJzY29wZSI6Im11bmljaXBhbGl0eSIsImF1dG9ub21vdXNfY29tbXVuaXR5X2lkIjoiRVM6Q0NBQToxMCIsInByb3ZpbmNlX2lkIjoiRVM6UFJPVjowMyIsIm11bmljaXBhbGl0eV9pZCI6IkVTOk1VTjowMzA2NSJ9LCJzb3VyY2VzIjp7ImVzZmlyZTMwIjp0cnVlLCJlZ2lmIjp0cnVlLCJpY3YiOnRydWUsImVmZmlzIjp0cnVlfSwic2VsZWN0aW9ucyI6eyJnZW9tZXRyeV9pZCI6bnVsbCwiZWdpZl9yZWNvcmRfaWQiOm51bGwsImljdl9nZW9tZXRyeV9pZCI6bnVsbCwiaWN2X3JlY29yZF9pZCI6bnVsbCwiZWZmaXNfZ2VvbWV0cnlfaWQiOm51bGx9fQ"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def url(base: str, path: str = "") -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def read_remote_json(base: str, path: str) -> tuple[dict, dict]:
    response = CORE.request(url(base, path))
    if response["status"] != 200:
        raise RuntimeError(f"remote metadata HTTP {response['status']}: {path}")
    return json.loads(response["body"].decode("utf-8")), response


def range_test(base: str, start: int, end: int) -> dict:
    remote = CORE.request(url(base, PMTILES_PATH), headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"})
    local = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles"
    with local.open("rb") as handle:
        handle.seek(start)
        expected = handle.read(end - start + 1)
    expected_range = (start, end, PMTILES_BYTES)
    return {
        "requested_range": f"bytes={start}-{end}", "status": remote["status"],
        "content_range": remote["headers"].get("content-range"), "bytes_received": len(remote["body"]),
        "byte_identical_to_local": remote["body"] == expected, "headers": remote["headers"],
        "elapsed_ms": remote["elapsed_ms"], "passed": remote["status"] == 206
        and CORE.parse_content_range(remote["headers"].get("content-range")) == expected_range
        and remote["body"] == expected,
    }


def runtime_url(base: str, smoke: str, config: dict | None = None, state_hash: str | None = None) -> str:
    query: dict[str, str] = {"smoke": smoke, "pmtiles_url": url(base, PMTILES_PATH), "pmtiles_telemetry": "1", "browser_range_fetch": "1"}
    for key, value in (config or {}).items():
        if value is None:
            continue
        query[key] = str(value)
    return url(base) + "?" + urlencode(query) + (state_hash or "")


def concise_smoke(name: str, result: dict, required_ids: int | None = None, esfire_expected: str = "ready") -> dict:
    remote = result.get("remote_pmtiles", {})
    errors = list(result.get("errors", [])) + list(result.get("map_error_events", []))
    source_state = result.get("coverage", {}).get("source_load_state", {}).get("esfire30")
    coverage_state = result.get("coverage", {}).get("esfire30", {}).get("status")
    esfire_valid = source_state == "ready" if esfire_expected == "ready" else coverage_state == esfire_expected
    valid = (
        not errors
        and esfire_valid
        and result.get("browser_range_fetch", {}).get("status") == 206
        and not remote.get("full_download_observed")
        and remote.get("range_requests", 0) > 0
    )
    if required_ids is not None:
        valid = valid and result.get("esfire30_territory_filter", {}).get("geometry_ids") == required_ids
    return {
        "scenario": name, "status": "PASS" if valid else "FAIL", "errors": errors,
        "state": result.get("state"), "coverage": result.get("coverage"),
        "egif": result.get("egif"), "icv": result.get("icv"), "effis": result.get("effis"),
        "selection": result.get("selection"), "icv_selection": result.get("icv_selection"),
        "effis_selection": result.get("effis_selection"), "legacy_hash_active": result.get("legacy_hash_active"),
        "input_hash_format": result.get("input_hash_format"), "legacy_copy": result.get("legacy_copy"),
        "legacy_history": result.get("legacy_history"), "remote_pmtiles": remote,
        "browser_range_fetch": result.get("browser_range_fetch"),
        "territory_filter": result.get("esfire30_territory_filter"),
        "target_2024AL0005_geometries": result.get("icv", {}).get("target_2024AL0005_geometries"),
        "usable_ms": result.get("initial", {}).get("usable_ms"), "heap_delta_bytes": result.get("heap_delta_bytes"),
    }


def run_smokes(base: str, chrome: str) -> list[dict]:
    cases = [
        ("spain", "spain", {"from": 1968, "to": 2026, "egif_scope": "ES"}, None, None, "desktop", "ready"),
        ("galicia", "galicia", {"from": 1993, "to": 2002, "egif_scope": "ES:CCAA:12", "territory_select": "ES:CCAA:12"}, None, None, "desktop", "ready"),
        ("ourense", "galicia", {"from": 1993, "to": 2002, "egif_scope": "ES:CCAA:12", "province_select": "ES:PROV:32"}, None, None, "desktop", "ready"),
        ("cangas", "spain", {"from": 1985, "to": 2021, "egif_scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index_strategy": "parent"}, None, 2610, "desktop", "ready"),
        ("gva_1995", "pais_valencia", {"from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10"}, LEGACY_1995, None, "desktop", "ready"),
        ("legacy_transition_copy", "pais_valencia", {"from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10", "legacy_interaction": "1", "legacy_copy": "1", "state_prepare": "both"}, LEGACY_1995, None, "desktop", "ready"),
        ("gva_2024", "pais_valencia", {"from": 2024, "to": 2024, "egif_scope": "ES:CCAA:10", "select_icv_geometry_id": "gva:geometry:2024:121:13587"}, LEGACY_2024, None, "desktop", "no_coverage"),
        ("gva_2024_record_only", "pais_valencia", {"from": 2024, "to": 2024, "egif_scope": "ES:CCAA:10"}, LEGACY_2024_RECORD_ONLY, None, "desktop", "no_coverage"),
        # ESFire30 ends in 2021.  In 2025 this same municipal state exercises
        # EFFIS, while ESFire30 correctly remains ``no_coverage``; therefore
        # it must not be required to expose Elx's six historical geometry ids.
        ("gva_2025_elx", "pais_valencia", {"from": 2025, "to": 2025, "egif_scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index_strategy": "parent"}, LEGACY_ELX_2025, None, "desktop", "no_coverage"),
        ("gva_2026", "pais_valencia", {"from": 2026, "to": 2026, "egif_scope": "ES:CCAA:10"}, None, None, "desktop", "no_coverage"),
        ("alacant", "pais_valencia", {"from": 1993, "to": 2002, "egif_scope": "ES:CCAA:10", "province_select": "ES:PROV:03"}, None, None, "desktop", "ready"),
        ("native_elx", "pais_valencia", {"territory_restore": "1", "state_prepare": "both"}, NATIVE_ELX, 6, "desktop", "ready"),
        ("canarias", "spain", {"from": 1993, "to": 2002, "egif_scope": "ES", "municipality_select": "ES:MUN:35016", "municipal_index_strategy": "parent"}, None, None, "desktop", "ready"),
        ("mobile_elx", "pais_valencia", {"from": 2025, "to": 2025, "egif_scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index_strategy": "parent"}, LEGACY_ELX_2025, None, "mobile_390x844", "no_coverage"),
    ]
    rows = []
    for name, smoke, config, state_hash, required_ids, device, esfire_expected in cases:
        window = "390,844" if device == "mobile_390x844" else "1280,800"
        result = CDP.run_page(chrome, runtime_url(base, smoke, config, state_hash), window, timeout=150)
        row = concise_smoke(name, result, required_ids, esfire_expected)
        if name == "legacy_transition_copy":
            history = result.get("legacy_history") or {}
            copied = result.get("legacy_copy") or {}
            transition_valid = (
                history.get("final_format") == "national_v1"
                and str(history.get("back_hash", "")).startswith("#v=1")
                and str(history.get("forward_hash", "")).startswith("#es4c-state-v1")
                and "#es4c-state-v1" in str(copied)
            )
            row["legacy_transition_valid"] = transition_valid
            if not transition_valid:
                row["status"] = "FAIL"
        if name == "gva_2024_record_only":
            state = result.get("state", {})
            # A source record can resolve to several geometries.  The legacy
            # record-only URL must preserve only the record, never guess one.
            record_only_valid = (
                state.get("selected_icv_record_id") == "gva:pif-cv:2024AL0005"
                and state.get("selected_icv_geometry_id") is None
            )
            row["record_only_valid"] = record_only_valid
            if not record_only_valid:
                row["status"] = "FAIL"
        row["device"] = device
        rows.append(row)
    return rows


def run_sequence(base: str, chrome: str, name: str, steps: list[tuple[str, str, dict]]) -> dict:
    """Navigate in one temporary Chromium profile to observe reload/cache state."""
    urls = []
    for number, (smoke, label, config) in enumerate(steps):
        config = dict(config)
        config["sequence_step"] = str(number)
        urls.append(runtime_url(base, smoke, config, None))
    results = CDP.run_pages(chrome, urls, "1280,800", timeout=150)
    rows = []
    valid = True
    for number, ((_, label, _), result) in enumerate(zip(steps, results)):
        remote = result.get("remote_pmtiles", {})
        errors = list(result.get("errors", [])) + list(result.get("map_error_events", []))
        row_valid = not errors and not remote.get("full_download_observed") and remote.get("range_requests", 0) > 0
        valid = valid and row_valid
        rows.append({
            "step": number, "label": label, "status": "PASS" if row_valid else "FAIL",
            "state": result.get("state"), "errors": errors,
            "remote_pmtiles": {key: remote.get(key) for key in ("requests", "range_requests", "response_bytes", "full_download_observed")},
            "usable_ms": result.get("initial", {}).get("usable_ms"),
        })
    return {"scenario": name, "status": "PASS" if valid else "FAIL", "steps": rows}


def run_sequences(base: str, chrome: str, only: str | None = None) -> list[dict]:
    elx = {"from": 2025, "to": 2025, "egif_scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index_strategy": "parent"}
    spain = {"from": 1993, "to": 2002, "egif_scope": "ES"}
    galicia = {"from": 1993, "to": 2002, "egif_scope": "ES:CCAA:12", "territory_select": "ES:CCAA:12"}
    sequences = []
    if only in (None, "reload_elx_2025"):
        sequences.append(run_sequence(base, chrome, "reload_elx_2025", [("pais_valencia", "first_load", elx), ("pais_valencia", "reload", elx)]))
    if only in (None, "repeat_spain_galicia"):
        sequences.append(run_sequence(base, chrome, "repeat_spain_galicia", [("spain", "spain_1", spain), ("galicia", "galicia_1", galicia), ("spain", "spain_2", spain), ("galicia", "galicia_2", galicia)]))
    return sequences


def run_permalink_supplement(base: str, chrome: str) -> list[dict]:
    """Run only the cases added after the primary remote matrix.

    This keeps the long, already-accepted main matrix reusable when the
    remaining evidence consists of History API and record-only assertions.
    """
    cases = [
        ("legacy_transition_copy", "pais_valencia", {"from": 1995, "to": 1995, "egif_scope": "ES:CCAA:10", "legacy_interaction": "1", "legacy_copy": "1", "state_prepare": "both"}, LEGACY_1995, "ready"),
        ("gva_2024_record_only", "pais_valencia", {"from": 2024, "to": 2024, "egif_scope": "ES:CCAA:10"}, LEGACY_2024_RECORD_ONLY, "no_coverage"),
    ]
    rows = []
    for name, smoke, config, state_hash, expected in cases:
        result = CDP.run_page(chrome, runtime_url(base, smoke, config, state_hash), "1280,800", timeout=150)
        row = concise_smoke(name, result, None, expected)
        if name == "legacy_transition_copy":
            history = result.get("legacy_history") or {}
            copied = result.get("legacy_copy") or {}
            row["legacy_transition_valid"] = (
                history.get("final_format") == "national_v1"
                and str(history.get("back_hash", "")).startswith("#v=1")
                and str(history.get("forward_hash", "")).startswith("#es4c-state-v1")
                and "#es4c-state-v1" in str(copied)
            )
            if not row["legacy_transition_valid"]:
                row["status"] = "FAIL"
        else:
            state = result.get("state", {})
            row["record_only_valid"] = (
                state.get("selected_icv_record_id") == "gva:pif-cv:2024AL0005"
                and state.get("selected_icv_geometry_id") is None
            )
            if not row["record_only_valid"]:
                row["status"] = "FAIL"
        rows.append(row)
    return rows


def sample_assets(base: str, manifest: dict) -> list[dict]:
    wanted = ("frontend", "egif", "territories", "municipality_geometry", "municipality_indexes", "icv", "effis")
    rows = []
    for family in wanted:
        candidates = [row for row in manifest["files"] if row["family"] == family]
        row = min(candidates, key=lambda item: (item["bytes"], item["path"]))
        response = CORE.request(url(base, row["path"]))
        rows.append({"family": family, "path": row["path"], "status": response["status"], "bytes": len(response["body"]), "sha256": sha256_bytes(response["body"]), "expected_bytes": row["bytes"], "expected_sha256": row["sha256"], "passed": response["status"] == 200 and len(response["body"]) == row["bytes"] and sha256_bytes(response["body"]) == row["sha256"], "headers": response["headers"]})
    return rows


def build(base: str, chrome: str) -> dict:
    local = ASSEMBLER.verify_identity(ROOT / "build/national-pages-staging")
    if not local.get("valid"):
        raise RuntimeError("ARTIFACT_IDENTITY_MISMATCH: " + ", ".join(local["failures"]))
    manifest, manifest_response = read_remote_json(base, "asset-manifest.json")
    identity, identity_response = read_remote_json(base, "site-identity.json")
    ranges = {"0_0": range_test(base, 0, 0), "initial": range_test(base, 0, 16383), "middle": range_test(base, 1048576, 1064959), "final": range_test(base, PMTILES_BYTES - 16384, PMTILES_BYTES - 1)}
    head = CORE.request(url(base, PMTILES_PATH), method="HEAD")
    smokes = run_smokes(base, chrome)
    sequences = run_sequences(base, chrome)
    samples = sample_assets(base, manifest)
    cache_paths = {"html": "", "js": "runtime/app.js", "json": "data/egif/v1/2026-08-27/manifest.json", "geojson": "data/territories/spain/v1/ccaa.geojson", "pmtiles": PMTILES_PATH}
    cache_headers = {kind: CORE.request(url(base, path), method="HEAD")["headers"] for kind, path in cache_paths.items()}
    production = CORE.request("https://inthurain.github.io/atlas-incendios/", method="HEAD")
    manifest_remote_sha = sha256_bytes(manifest_response["body"])
    site_remote_sha = sha256_bytes(identity_response["body"])
    failures = []
    if manifest_remote_sha != MANIFEST_SHA256: failures.append("remote_manifest_sha")
    if site_remote_sha != SITE_IDENTITY_SHA256: failures.append("remote_site_identity_sha")
    if identity.get("site_file_count") != 350 or identity.get("site_total_bytes") != "00000000000500450914": failures.append("remote_site_identity_contract")
    if manifest.get("payload_fingerprint", {}).get("sha256") != PAYLOAD_FINGERPRINT: failures.append("remote_payload_fingerprint")
    if head["status"] != 200 or head["headers"].get("content-length") != str(PMTILES_BYTES) or head["headers"].get("accept-ranges") != "bytes": failures.append("pmtiles_head")
    failures.extend(f"range:{name}" for name, row in ranges.items() if not row["passed"])
    failures.extend(f"asset:{row['family']}" for row in samples if not row["passed"])
    failures.extend(f"smoke:{row['scenario']}" for row in smokes if row["status"] != "PASS")
    failures.extend(f"sequence:{row['scenario']}" for row in sequences if row["status"] != "PASS")
    if production["status"] != 200: failures.append("production_root")
    full_download = any(row["remote_pmtiles"].get("full_download_observed") for row in smokes)
    if full_download: failures.append("full_pmtiles_download")
    return {
        "phase": "ES-4D4B", "attempts": {
            # Immutable historical result from ab31782: its workflow halted in
            # the extraction gate, before upload/deploy.  Keeping the original
            # counts here makes the correction auditable rather than turning
            # attempt 1 into a retroactive pass.
            "attempt_1": {
                "status": "FAIL_ARTIFACT_IDENTITY", "workflow_run": 33516317541,
                "source_commit": "ab31782", "deployed": False,
                "predeploy_commit": "d8e6f84cfeb9597dc0f4327f427912b97ae93c3e",
                "artifact_identity": {
                    "expected_file_count": 349, "actual_file_count": 349,
                    "expected_total_bytes": 500449810, "actual_total_bytes": 500449871,
                    "difference_bytes": 61, "status": "ARTIFACT_IDENTITY_MISMATCH",
                },
                "package": {"bytes": 136809234, "sha256": "52ca395bc0ef9fa5dadec3f62f3b145c36dd6e1560900d80758d4cb9df810ab5"},
            },
            "attempt_2": {"status": "PASS" if not failures else "FAIL", "workflow_run": 33525357443, "d4a1_commit": "a7c3c4d"},
        },
        "endpoint": {"staging": url(base), "production": "https://inthurain.github.io/atlas-incendios/", "pmtiles": url(base, PMTILES_PATH)},
        "local_identity": local,
        "remote_identity": {"asset_manifest_sha256": manifest_remote_sha, "site_identity_sha256": site_remote_sha, "asset_manifest_headers": manifest_response["headers"], "site_identity_headers": identity_response["headers"], "site_identity": identity, "payload_fingerprint": manifest.get("payload_fingerprint", {}).get("sha256")},
        "pmtiles_head": {key: value for key, value in head.items() if key != "body"}, "range_tests": ranges,
        "representative_assets": samples, "browser_smokes": smokes, "browser_sequences": sequences,
        "cache_headers": cache_headers, "production_root": {"status": production["status"], "headers": production["headers"], "intact": production["status"] == 200},
        "full_pmtiles_download_observed": full_download, "unexpected_external_data_domains": [],
        "cdn_cache_validation": "NOT_VALIDATED_GITHUB_PAGES_STAGING", "warnings": ["GitHub Pages staging is not a production root switch.", "Cache headers are observational only; no CDN policy conclusion is made."],
        "failures": failures, "status": "PASS" if not failures else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--supplement-permalinks", action="store_true", help="Añade evidencia History API sin repetir la matriz primaria.")
    parser.add_argument("--supplement-sequences", action="store_true", help="Añade evidencia reload/repetición sin repetir la matriz primaria.")
    parser.add_argument("--supplement-reload", action="store_true", help="Añade solo la evidencia de reload.")
    parser.add_argument("--supplement-repeat", action="store_true", help="Añade solo la evidencia España/Galicia repetida.")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        valid = payload.get("status") == "PASS" and not payload.get("failures")
        print(json.dumps({"valid": valid, "failures": payload.get("failures", []), "output": str(args.output)}, sort_keys=True))
        return 0 if valid else 1
    if args.supplement_permalinks or args.supplement_sequences or args.supplement_reload or args.supplement_repeat:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        if args.supplement_permalinks:
            payload["browser_permalink_supplement"] = run_permalink_supplement(args.base_url, args.chrome)
        if args.supplement_sequences or args.supplement_reload or args.supplement_repeat:
            collected = {row["scenario"]: row for row in payload.get("browser_sequences", [])}
            only = "reload_elx_2025" if args.supplement_reload and not args.supplement_sequences else ("repeat_spain_galicia" if args.supplement_repeat and not args.supplement_sequences else None)
            wanted = run_sequences(args.base_url, args.chrome, only)
            for row in wanted:
                if args.supplement_sequences or (args.supplement_reload and row["scenario"] == "reload_elx_2025") or (args.supplement_repeat and row["scenario"] == "repeat_spain_galicia"):
                    collected[row["scenario"]] = row
            payload["browser_sequences"] = [collected[name] for name in sorted(collected)]
        supplemental = payload.get("browser_permalink_supplement", [])
        sequences = payload.get("browser_sequences", [])
        # If the primary matrix was produced before a small harness correction,
        # the directed rerun is the authoritative observation for that same
        # scenario.  Replace it rather than retaining a stale false negative.
        by_scenario = {row["scenario"]: row for row in supplemental}
        if by_scenario:
            payload["browser_smokes"] = [by_scenario.get(row["scenario"], row) for row in payload.get("browser_smokes", [])]
        payload["supplement_failures"] = [
            *(f"permalink:{row['scenario']}" for row in supplemental if row["status"] != "PASS"),
            *(f"sequence:{row['scenario']}" for row in sequences if row["status"] != "PASS"),
        ]
        # The stored status remains the aggregate acceptance status, now also
        # covering these additional directed checks.
        payload["failures"] = [
            failure for failure in payload.get("failures", [])
            if not failure.startswith(("permalink:", "sequence:"))
            and failure not in {f"smoke:{name}" for name in by_scenario}
        ] + payload["supplement_failures"]
        payload["status"] = "PASS" if not payload["failures"] else "FAIL"
        payload["attempts"]["attempt_2"]["status"] = payload["status"]
        args.output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "failures": payload["failures"], "output": str(args.output)}, ensure_ascii=False, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1
    payload = build(args.base_url, args.chrome)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "failures": payload["failures"], "output": str(args.output)}, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
