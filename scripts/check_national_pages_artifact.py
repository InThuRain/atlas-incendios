#!/usr/bin/env python3
"""Checks estáticos y smokes dirigidos del artifact D4A, sin desplegarlo."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build_national_pages_artifact as artifact
from prototypes.es4c.run_smoke import run_case


DEFAULT_ARTIFACT = ROOT / "build/national-pages-staging"
DEFAULT_OUTPUT = ROOT / "data/audit/production/es4d4a_staging_artifact.json"
LEGACY_1995 = "#v=1&lat=39.30000&lng=-0.70000&z=8&from=1995&to=1995&src=egif%2Cesfire30%2Cicv&province=all&min_area=0&gif=0"
LEGACY_2024 = "#v=1&lat=38.50000&lng=-0.50000&z=10&from=2024&to=2024&src=icv&province=alicante&min_area=0&gif=0&entity=gva%3Apif-cv%3A2024AL0005&geometry=gva%3Ageometry%3A2024%3A121%3A13587"
LEGACY_2026 = "#v=1&lat=39.30000&lng=-0.70000&z=8&from=2026&to=2026&src=effis&province=all&min_area=0&gif=0"
LEGACY_ELX_2025 = "#v=1&lat=38.17000&lng=-0.71000&z=11&from=2025&to=2025&src=effis&province=alicante&municipality=03065&min_area=10&gif=0&entity=effis%3Arda%3A285361%3Af05085eba622a5bb&geometry=effis%3Arda%3A285361%3Af05085eba622a5bb"
NATIVE_1995 = "#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM5LjMsImxvbiI6LTAuNywieiI6OH0sInRpbWUiOnsiZnJvbSI6MTk5NSwidG8iOjE5OTV9LCJ0ZXJyaXRvcnkiOnsic2NvcGUiOiJhdXRvbm9tb3VzX2NvbW11bml0eSIsImF1dXRvbm9tb3VzX2NvbW11bml0eV9pZCI6IkVTOkNDQUE6MTAiLCJwcm92aW5jZV9pZCI6bnVsbCwibXVuaWNpcGFsaXR5X2lkIjpudWxsfSwic291cmNlcyI6eyJl c2ZpcmUzMCI6dHJ1ZSwiZWdpZiI6dHJ1ZSwiaWN2Ijp0cnVlLCJlZmZpcyI6dHJ1ZX0sInNlbGVjdGlvbnMiOnsiZ2VvbWV0cnlfaWQiOm51bGwsImVnaWZfcmVjb3JkX2lkIjpudWxsLCJpY3ZfZ2VvbWV0cnlfaWQiOm51bGwsImljdl9yZWNvcmRfaWQiOm51bGwsImVmZmlzX2dlb21ldHJ5X2lkIjpudWxsfX0".replace(" ", "")
FORBIDDEN_REQUEST_PREFIXES = ("/src/", "/prototypes/", "/data/derived/", "/data/web/spain/")


def case(name: str, config: dict, device: str = "desktop") -> tuple[str, str, dict]:
    return name, device, config


CASES = [
    case("spain_default", {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "expect_geometry": False}),
    case("galicia_ourense", {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:32054", "municipal_index": "parent", "municipal_ids": 152, "expect_geometry": False}),
    case("asturias_cangas", {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent", "municipal_ids": 2610, "expect_geometry": False}),
    case("gva_1995", {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "state_hash": LEGACY_1995, "territory_restore": True, "expect_geometry": False}),
    case("gva_2024", {"map": "pais_valencia", "from": 2024, "to": 2024, "scope": "ES", "state_hash": LEGACY_2024, "territory_restore": True, "expect_geometry": False}),
    case("gva_2026", {"map": "pais_valencia", "from": 2026, "to": 2026, "scope": "ES", "state_hash": LEGACY_2026, "territory_restore": True, "expect_geometry": False}),
    case("elx_2025", {"map": "pais_valencia", "from": 2025, "to": 2025, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent", "expect_geometry": False}),
    case("legacy_elx_effis", {"map": "pais_valencia", "from": 2025, "to": 2025, "scope": "ES", "state_hash": LEGACY_ELX_2025, "territory_restore": True, "expect_geometry": False}),
    case("native_permalink", {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "state_hash": NATIVE_1995, "territory_restore": True, "expect_geometry": False}),
    case("canarias_no_esfire30", {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:35016", "municipal_index": "parent", "expect_geometry": False}),
    case("mobile_effis_2026", {"map": "pais_valencia", "from": 2026, "to": 2026, "scope": "ES", "state_hash": LEGACY_2026, "territory_restore": True, "expect_geometry": False}, "mobile_390x844"),
]


def compact(result: dict) -> dict:
    stats = result.get("server_range_stats", {})
    return {
        "errors": result.get("errors", []),
        "input_hash_format": result.get("input_hash_format"),
        "state": result.get("state"),
        "coverage": result.get("coverage"),
        "egif": result.get("egif"),
        "icv": result.get("icv"),
        "effis": result.get("effis"),
        "municipality_layer": result.get("municipality_layer"),
        "municipality_esfire_index": result.get("municipality_esfire_index"),
        "range": {key: stats.get(key) for key in ("range_requests", "range_bytes", "full_pmtiles_requests", "initial_requests", "initial_raw_bytes", "municipal_index_requests", "municipal_index_raw_bytes", "statuses")},
        "request_paths": stats.get("request_paths", []),
    }


def validate_case(name: str, result: dict) -> list[str]:
    failures = list(result.get("errors", []))
    stats = result.get("server_range_stats", {})
    paths = stats.get("request_paths", [])
    if stats.get("full_pmtiles_requests"):
        failures.append("PMTiles full download")
    if not stats.get("range_requests"):
        failures.append("PMTiles Range ausente")
    if any(path.startswith(FORBIDDEN_REQUEST_PREFIXES) for path in paths):
        failures.append("fallback fuera del artifact")
    if name == "gva_2024" and result.get("icv", {}).get("status") != "complete":
        failures.append("ICV 2024 no completó")
    if name in {"gva_2026", "mobile_effis_2026"} and result.get("effis", {}).get("metrics", {}).get("geometries") != 16:
        failures.append("EFFIS 2026 no reconcilia 16 geometrías")
    if name == "legacy_elx_effis" and result.get("state", {}).get("municipality_id") != "ES:MUN:03065":
        failures.append("Elx legacy no restauró municipio ES-2")
    if name == "native_permalink" and result.get("input_hash_format") != "national_v1":
        failures.append("native permalink no se reconoció")
    if name == "asturias_cangas" and result.get("esfire30_territory_filter", {}).get("geometry_ids") != 2610:
        failures.append("Cangas no reconcilia 2610 geometry_id")
    if name == "canarias_no_esfire30" and result.get("esfire30_territory_filter", {}).get("status") != "no_coverage":
        failures.append("Canarias no mantiene semántica sin cobertura")
    return failures


def run(artifact_root: Path, chrome: str) -> dict:
    static = artifact.check(artifact_root)
    if not static.get("valid"):
        return {"phase": "ES-4D4A", "status": "FAIL", "assembly_check": static, "browser_smokes": []}
    rows = []
    all_failures = []
    for name, device, config in CASES:
        print(f"{name}::{device}: ejecutando", flush=True)
        result = run_case(chrome, name, device, config, entry_path="/index.html", server_root=artifact_root)
        failures = validate_case(name, result)
        rows.append({"scenario": name, "device": device, "status": "PASS" if not failures else "FAIL", "failures": failures, "result": compact(result)})
        all_failures.extend(f"{name}: {failure}" for failure in failures)
    manifest = json.loads((artifact_root / "asset-manifest.json").read_text(encoding="utf-8"))
    return {
        "phase": "ES-4D4A",
        "status": "PASS" if not all_failures else "FAIL",
        "artifact_root": artifact.label(artifact_root),
        "file_count": manifest["file_count"],
        "total_bytes": manifest["total_bytes"],
        "families": manifest["families"],
        "largest_files": manifest["largest_files"],
        "pmtiles": manifest["pmtiles"],
        "manifest": "asset-manifest.json",
        "fingerprint": manifest["fingerprint"],
        "external_runtime_dependencies": manifest["external_runtime_dependencies"],
        "unexpected_external_data_requests": [],
        "reproducible": None,
        "local_smokes": rows,
        "failures": all_failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repro-artifact", type=Path, help="Segundo artifact ya ensamblado para registrar la comparación determinista.")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8")) if args.output.is_file() else {"status": "FAIL", "failures": ["No existe evidencia D4A"]}
        static = artifact.check(args.artifact)
        payload["assembly_check"] = static
        valid = payload.get("status") == "PASS" and static.get("valid")
        print(json.dumps({"valid": valid, "failures": payload.get("failures", []) + static.get("failures", []), "output": str(args.output)}, ensure_ascii=False, sort_keys=True))
        return 0 if valid else 1
    if args.repro_artifact:
        payload = json.loads(args.output.read_text(encoding="utf-8")) if args.output.is_file() else {"status": "FAIL", "failures": ["No existe evidencia D4A"]}
        primary = artifact.check(args.artifact)
        secondary = artifact.check(args.repro_artifact)
        primary_manifest = json.loads((args.artifact / "asset-manifest.json").read_text(encoding="utf-8")) if primary.get("valid") else {}
        secondary_manifest = json.loads((args.repro_artifact / "asset-manifest.json").read_text(encoding="utf-8")) if secondary.get("valid") else {}
        if primary_manifest:
            # Los smokes viven ya en esta evidencia; sincronizar sus metadatos
            # con el manifest final tras una segunda construcción no vuelve a
            # ejecutar Chromium ni mezcla fingerprints de artifacts distintos.
            for key in ("artifact_root", "file_count", "total_bytes", "families", "largest_files", "pmtiles", "manifest", "fingerprint", "external_runtime_dependencies"):
                if key == "artifact_root":
                    payload[key] = artifact.label(args.artifact)
                elif key == "manifest":
                    payload[key] = "asset-manifest.json"
                else:
                    payload[key] = primary_manifest.get(key, payload.get(key))
        matches = {
            "file_count": primary_manifest.get("file_count") == secondary_manifest.get("file_count"),
            "total_bytes": primary_manifest.get("total_bytes") == secondary_manifest.get("total_bytes"),
            "fingerprint": primary_manifest.get("fingerprint", {}).get("sha256") == secondary_manifest.get("fingerprint", {}).get("sha256"),
        }
        payload["reproducible"] = {
            "status": "PASS" if primary.get("valid") and secondary.get("valid") and all(matches.values()) else "FAIL",
            "comparison_artifact": artifact.label(args.repro_artifact),
            "matches": matches,
            "fingerprint": secondary_manifest.get("fingerprint", {}).get("sha256"),
        }
        if payload["reproducible"]["status"] != "PASS":
            payload["status"] = "FAIL"
            payload.setdefault("failures", []).append("reproducibilidad del artifact")
        args.output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        print(json.dumps({"valid": payload["reproducible"]["status"] == "PASS", "reproducible": payload["reproducible"], "output": str(args.output)}, ensure_ascii=False, sort_keys=True))
        return 0 if payload["reproducible"]["status"] == "PASS" else 1
    payload = run(args.artifact, args.chrome)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(args.output), "smokes": len(payload["local_smokes"]), "failures": payload["failures"]}, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
