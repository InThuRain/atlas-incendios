#!/usr/bin/env python3
"""Aceptación acotada ES-4C3B para el runtime aislado nacional.

No construye datos. Reutiliza el servidor Range y Chromium de los smokes, y
puede inyectar respuestas 503 locales para comprobar aislamiento de fallos.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMOKE_PATH = ROOT / "prototypes/es4c/run_smoke.py"
DEFAULT_OUTPUT = ROOT / "prototypes/es4c/c3b-acceptance-results.json"


def load_smoke():
    spec = importlib.util.spec_from_file_location("es4c_smoke", SMOKE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def config(from_year, to_year, scope="ES", **extra):
    return {"from": from_year, "to": to_year, "scope": scope, **extra}


SCENARIOS = [
    ("clean_spain", "spain", "desktop", config(1993, 2002, initial_requests=0, expect_esfire="national")),
    ("spain_1975", "spain", "desktop", config(1975, 1975, initial_requests=0, expect_esfire="inactive")),
    ("elx_end_to_end", "pais_valencia", "desktop", config(1993, 2002, municipality_select="ES:MUN:03065", municipal_index="parent", c3a_select_both=True, c3a_roundtrip=True, expect_municipal_ids=6, expect_records=49, require_both=True)),
    ("galicia_ourense", "galicia", "desktop", config(1993, 2002, municipality_select="ES:MUN:32054", municipal_index="parent", expect_municipal_ids=152, expect_records=444)),
    ("cangas", "spain", "desktop", config(1985, 2021, municipality_select="ES:MUN:33011", municipal_index="parent", expect_municipal_ids=2610, expect_records=3044, require_selection=True)),
    ("agost_zero_relations", "pais_valencia", "desktop", config(1993, 2002, municipality_select="ES:MUN:03002", municipal_index="parent", expect_municipal_ids=0, expect_records=3)),
    ("canarias_no_coverage", "spain", "desktop", config(1993, 2002, municipality_select="ES:MUN:35016", municipal_index="parent", expect_esfire="no_coverage", expect_records=7)),
    ("ceuta_hierarchy", "spain", "desktop", config(1995, 1995, municipality_select="ES:MUN:51001", municipal_index="parent", expect_esfire="no_coverage", require_city_parent=True)),
    ("multi_province", "pais_valencia", "desktop", config(1985, 1985, province_select="ES:PROV:03", select_geometry_id="esfire30:v1:1985:268", require_selected="esfire30:v1:1985:268")),
    ("multi_ccaa", "spain", "desktop", config(1985, 1985, territory_select="ES:CCAA:17", select_geometry_id="esfire30:v1:1985:1037", require_selected="esfire30:v1:1985:1037")),
    ("selector_click", "pais_valencia", "desktop", config(1993, 2002, territory_click="ES:CCAA:10", require_scope="autonomous_community")),
    ("legacy_url", "pais_valencia", "desktop", config(1995, 1995, state_hash="#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM5LjMsImxvbiI6LTAuNywieiI6OH0sInRpbWUiOnsiZnJvbSI6MTk5NSwidG8iOjE5OTV9LCJ0ZXJyaXRvcnkiOnsic2NvcGUiOiJhdXRvbm9tb3VzX2NvbW11bml0eSIsImF1dG9ub21vdXNfY29tbXVuaXR5X2lkIjoiRVM6Q0NBQToxMCJ9LCJzb3VyY2VzIjp7ImVzZmlyZTMwIjp0cnVlLCJlZ2lmIjp0cnVlfSwic2VsZWN0aW9ucyI6eyJnZW9tZXRyeV9pZCI6bnVsbCwiZWdpZl9yZWNvcmRfaWQiOm51bGx9fQ", territory_restore=True, require_scope="autonomous_community")),
    ("invalid_hash", "spain", "desktop", config(1995, 1995, corrupt_hash="#es4c-state-v99=broken", require_scope="ES")),
    ("stale_galicia_to_elx", "spain", "desktop", config(1993, 2002, c3a_rapid_transition=True, expect_final_territory="ES:MUN:03065")),
    ("cache_municipal_parent", "spain", "desktop", config(1985, 2021, municipality_select="ES:MUN:33011", municipality_sequence="ES:MUN:33001", municipal_index="parent", expect_municipal_ids=1306, require_parent_cache=True)),
    ("detail_lazy", "pais_valencia", "desktop", config(1993, 2002, scope="ES:CCAA:10", detail="same_asset", require_detail=True)),
    ("fault_egif_initial", "pais_valencia", "desktop", config(1993, 2002, municipality_select="ES:MUN:03065", fault_paths=("/initial.json",), expect_egif_error=True)),
    ("fault_detail", "pais_valencia", "desktop", config(1993, 2002, scope="ES:CCAA:10", detail="single", fault_paths=("/detail.json",), expect_detail_error=True)),
    ("fault_municipal_geojson", "pais_valencia", "desktop", config(1993, 2002, municipality_select="ES:MUN:03065", fault_paths=("/ES-PROV-03.geojson",), expect_municipal_error=True)),
    ("fault_municipal_index", "pais_valencia", "desktop", config(1993, 2002, municipality_select="ES:MUN:03065", municipal_index="parent", fault_paths=("/municipality-index/by-parent/ES-PROV-03.json",), expect_index_error=True)),
    ("fault_pmtiles", "spain", "desktop", config(1993, 2002, fault_paths=(".pmtiles",), expect_pmtiles_error=True)),
    ("mobile_elx", "pais_valencia", "mobile_390x844", config(1993, 2002, municipality_select="ES:MUN:03065", municipal_index="parent", expect_municipal_ids=6)),
    ("mobile_cangas", "spain", "mobile_390x844", config(1985, 2021, municipality_select="ES:MUN:33011", municipal_index="parent", expect_municipal_ids=2610, require_selection=True)),
]


def values(result):
    return {
        "state": result.get("state", {}),
        "coverage": result.get("coverage", {}),
        "filter": result.get("esfire30_territory_filter", {}),
        "egif": result.get("egif", {}),
        "detail": result.get("egif_detail"),
        "network": result.get("server_range_stats", {}),
        "municipality": result.get("municipality_layer", {}),
        "consolidation": result.get("consolidation", {}),
    }


def validate(name, result, expected):
    data = values(result)
    errors = list(result.get("errors", []))
    state, coverage, filt, egif, detail, network = data["state"], data["coverage"], data["filter"], data["egif"], data["detail"], data["network"]
    injected = bool(network.get("injected_failures"))
    if not injected:
        if network.get("full_pmtiles_requests") != 0:
            errors.append("descarga PMTiles completa")
        if network.get("range_requests", 0) <= 0:
            errors.append("sin HTTP Range PMTiles")
    if expected.get("initial_requests") is not None and network.get("initial_requests") != expected["initial_requests"]:
        errors.append("requests INITIAL inesperados")
    if expected.get("expect_esfire") and filt.get("status") != expected["expect_esfire"]:
        errors.append(f"filtro ESFire30 esperado {expected['expect_esfire']}, actual {filt.get('status')}")
    if expected.get("expect_municipal_ids") is not None and filt.get("geometry_ids") != expected["expect_municipal_ids"]:
        errors.append("cardinalidad de índice municipal inesperada")
    if expected.get("expect_records") is not None and egif.get("summary", {}).get("records") != expected["expect_records"]:
        errors.append("recuento EGIF inesperado")
    if expected.get("require_scope") and state.get("territory_scope") != expected["require_scope"]:
        errors.append("scope restaurado inesperado")
    if expected.get("require_city_parent") and not (state.get("autonomous_community_id") == "ES:CCAA:18" and state.get("province_id") is None):
        errors.append("Ceuta usa jerarquía provincial ficticia")
    if expected.get("require_selected") and state.get("selected_geometry_id") != expected["require_selected"]:
        errors.append("multi-territorio no seleccionable")
    if expected.get("require_selection") and not state.get("selected_geometry_id"):
        errors.append("selección ESFire30 ausente")
    if expected.get("require_both"):
        selected = data["consolidation"].get("selection") or {}
        restored = data["consolidation"].get("restore") or {}
        if not selected.get("egif_record_id") or not selected.get("geometry_id") or not restored.get("selected_egif_record_id") or not restored.get("selected_geometry_id"):
            errors.append("selecciones dobles/restauración ausentes")
    if expected.get("expect_final_territory") and (data["consolidation"].get("rapid_transition") or {}).get("final_territory") != expected["expect_final_territory"]:
        errors.append("respuesta stale territorial")
    if expected.get("require_parent_cache"):
        steps = (result.get("municipality_esfire_index", {}).get("sequence") or {}).get("steps", [])
        if not steps or not steps[-1].get("index_cached"):
            errors.append("índice padre no reutilizado")
    if expected.get("require_detail") and not (detail and detail.get("second", {}).get("result", {}).get("metrics", {}).get("cached")):
        errors.append("DETAIL no fue lazy/cacheado")
    if expected.get("expect_egif_error") and egif.get("status") != "error":
        errors.append("fallo INITIAL EGIF no quedó aislado como error")
    if expected.get("expect_detail_error") and not (detail and detail.get("result", {}).get("status") == "error"):
        errors.append("fallo DETAIL no quedó localizado")
    if expected.get("expect_municipal_error") and data["municipality"].get("load_status") != "error":
        errors.append("fallo GeoJSON municipal no se registró")
    if expected.get("expect_index_error") and filt.get("status") != "error":
        errors.append("fallo índice municipal no se registró")
    if expected.get("expect_pmtiles_error"):
        # Este requisito se evalúa deliberadamente contra el estado de fuente,
        # no solo contra el evento MapLibre, para detectar UI engañosa.
        if coverage.get("source_load_state", {}).get("esfire30") != "error":
            errors.append("PMTiles fallido no cambia ESFire30 a error")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--scenario", choices=[row[0] for row in SCENARIOS], action="append")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--append", action="store_true", help="añade escenarios a un resultado local existente")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        failures = [row for row in payload["runs"] if row["status"] != "PASS"]
        print(json.dumps({"valid": not failures, "failures": [row["scenario"] for row in failures], "output": str(args.output)}))
        return 0 if not failures else 1
    smoke = load_smoke()
    requested = set(args.scenario or [row[0] for row in SCENARIOS])
    runs = []
    for scenario, map_name, device, expected in SCENARIOS:
        if scenario not in requested:
            continue
        print(f"{scenario}::{device}: aceptando", flush=True)
        result = smoke.run_case(args.chrome, map_name, device, expected)
        failures = validate(scenario, result, expected)
        runs.append({"scenario": scenario, "device": device, "status": "PASS" if not failures else "FAIL", "failures": failures, "result": result})
    previous = []
    if args.append and args.output.is_file():
        previous = json.loads(args.output.read_text(encoding="utf-8")).get("runs", [])
        previous = [row for row in previous if row.get("scenario") not in requested]
    payload = {
        "schema_version": 1,
        "phase": "ES-4C3B",
        "environment": {"platform": platform.platform(), "python": platform.python_version(), "chrome": args.chrome},
        "runs": previous + runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    all_runs = payload["runs"]
    print(json.dumps({"valid": not any(row["status"] == "FAIL" for row in all_runs), "runs": len(all_runs), "failed": [row["scenario"] for row in all_runs if row["status"] == "FAIL"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
