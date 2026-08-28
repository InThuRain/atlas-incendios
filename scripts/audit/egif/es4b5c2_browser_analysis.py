#!/usr/bin/env python3
"""Analyse existing ES-4B5C Chromium results without launching a browser."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "benchmarks/es4b5c/results.json"
OUTPUT = ROOT / "data/audit/egif/es4b5c2_browser_summary.json"
SCENARIOS = (
    "a_la_rioja_full", "b_pais_valencia_full", "c_cataluna_full", "d_andalucia_full",
    "e_castilla_y_leon_full", "f_galicia_full", "g_galicia_1993_2002",
    "h_spain_1993_2002", "i_spain_2013_2023", "j_spain_all_initial",
)
DEVICES = ("desktop", "mobile_390x844")
CACHE_MODES = ("cold", "warm")
MIB = 1024 * 1024


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def difference(after: dict[str, Any], before: dict[str, Any]) -> int | None:
    if after.get("status") != "available" or before.get("status") != "available":
        return None
    return after["used_js_heap_size"] - before["used_js_heap_size"]


def mib(value: int | None) -> float | None:
    return round(value / MIB, 3) if value is not None else None


def run_key(scenario: str, device: str, cache_mode: str) -> str:
    return f"{scenario}::{device}::{cache_mode}"


def compact_row(wrapper: dict[str, Any]) -> dict[str, Any]:
    result = wrapper["result"]
    initial = result["network"]["initial"]
    detail = result["network"]["detail"]
    timing = result["timings_ms"]
    heap = result["heap"]
    selection = result["selection"]
    same_asset_telemetry = (
        {"status": "verified", "additional_detail_requests": selection["second_same_asset_additional_detail_requests"]}
        if result["initial_asset_count"] == 1
        else {"status": "not_usable_for_comparison", "reason": "the harness recorded this after loading a second detail asset", "reported_value": selection["second_same_asset_additional_detail_requests"], "other_detail_requests": selection["other_detail"].get("additional_requests")}
    )
    return {
        "scenario": wrapper["scenario"], "scenario_label": wrapper["scenario_label"], "device": wrapper["device"]["id"], "cache_mode": wrapper["cache_mode"],
        "initial_records": result["initial_records"], "initial_assets": result["initial_asset_count"],
        "initial_gzip_manifest_bytes": initial["gzip_estimated_bytes"], "initial_body_raw_bytes": initial["body_bytes"],
        "initial_resource_transfer_bytes": initial["resource_transfer_bytes"], "initial_requests": initial["requests"],
        "initial_fetch_ms_sum_parallel": initial["fetch_ms"], "initial_load_wall_ms": timing["initial_load_wall_ms"],
        "initial_parse_ms_sum": timing["initial_parse_ms_sum"], "initial_prepare_ms_sum": timing["prepare_ms_sum"],
        "filter_bundle_ms": timing["filter_ms"], "lookup_query_ms": timing["lookup_ms"],
        "heap_before_bytes": heap["before"]["used_js_heap_size"], "heap_initial_bytes": heap["after_initial"]["used_js_heap_size"],
        "heap_initial_delta_bytes": difference(heap["after_initial"], heap["before"]),
        "detail_gzip_manifest_bytes_probe": detail["gzip_estimated_bytes"], "detail_body_raw_bytes_probe": detail["body_bytes"],
        "detail_resource_transfer_bytes_probe": detail["resource_transfer_bytes"], "detail_requests_probe": detail["requests"],
        "detail_fetch_ms_sum_probe": detail["fetch_ms"], "detail_parse_ms_sum_probe": detail["parse_ms"],
        "first_selection_ms": timing["first_selection_ms"], "second_selection_same_asset_ms": timing["second_selection_same_asset_ms"],
        "heap_detail_bytes": heap["after_detail"]["used_js_heap_size"], "heap_detail_delta_from_initial_bytes": difference(heap["after_detail"], heap["after_initial"]),
        "filters": result["filters"], "lookup": result["lookup"], "columnar_vs_objects_small_sample": result["columnar_vs_objects_small_sample"],
        "same_asset_detail_telemetry": same_asset_telemetry, "errors": wrapper.get("errors", []),
    }


def scenario_grade(scenario: str, cold_rows: list[dict[str, Any]]) -> dict[str, Any]:
    maximum = max(row["heap_initial_delta_bytes"] for row in cold_rows if row["heap_initial_delta_bytes"] is not None)
    # ES-3's existing diagnostic CCAA geometry budget is <=85 MiB. It is not
    # an EGIF SLA; it is used as a documented comparison point for deciding
    # whether this records-only payload leaves headroom for a geometry layer.
    comparison = 85 * MIB
    if scenario in {"a_la_rioja_full", "b_pais_valencia_full", "c_cataluna_full", "d_andalucia_full", "e_castilla_y_leon_full"}:
        label = "GOOD" if maximum <= comparison else "MARGINAL"
    elif scenario == "f_galicia_full":
        label = "MARGINAL" if maximum > comparison else "ACCEPTABLE"
    elif scenario == "g_galicia_1993_2002":
        label = "ACCEPTABLE" if maximum <= comparison else "MARGINAL"
    elif scenario == "h_spain_1993_2002":
        label = "MARGINAL" if maximum > comparison else "ACCEPTABLE"
    elif scenario == "i_spain_2013_2023":
        label = "ACCEPTABLE" if maximum <= comparison else "MARGINAL"
    else:
        label = "VIABLE_BUT_NOT_DEFAULT"
    return {"classification": label, "max_cold_initial_heap_delta_bytes": maximum, "max_cold_initial_heap_delta_mib": mib(maximum),
            "comparison_basis": "ES-3 CCAA diagnostic geometry budget: 85 MiB; EGIF has no geometry and therefore must leave headroom rather than consume that budget by default"}


def analyze(payload: dict[str, Any], *, strict: bool = True) -> dict[str, Any]:
    runs = payload.get("runs", {})
    smoke = {key: row for key, row in runs.items() if row.get("scenario") == "smoke_la_rioja_2013_2023"}
    main_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for scenario in SCENARIOS:
        for device in DEVICES:
            for cache_mode in CACHE_MODES:
                key = run_key(scenario, device, cache_mode)
                wrapper = runs.get(key)
                if not wrapper:
                    errors.append(f"missing main run: {key}")
                    continue
                if wrapper.get("status") != "complete" or wrapper.get("errors") or wrapper.get("result", {}).get("error"):
                    errors.append(f"failed main run: {key}")
                    continue
                main_rows.append(compact_row(wrapper))
    if strict and len(main_rows) != 40:
        errors.append(f"expected 40 main rows, found {len(main_rows)}")
    rows_by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in main_rows:
        rows_by_scenario[row["scenario"]].append(row)
    scenario_summaries = []
    for scenario in SCENARIOS:
        rows = rows_by_scenario.get(scenario, [])
        cold_rows = [row for row in rows if row["cache_mode"] == "cold"]
        scenario_summaries.append({"scenario": scenario, "observations": len(rows), "cold_observations": len(cold_rows),
                                   **(scenario_grade(scenario, cold_rows) if cold_rows else {"classification": "INCOMPLETE"})})
    cold_warm = []
    for scenario in SCENARIOS:
        for device in DEVICES:
            by_mode = {row["cache_mode"]: row for row in rows_by_scenario[scenario] if row["device"] == device}
            if {"cold", "warm"} <= set(by_mode):
                cold, warm = by_mode["cold"], by_mode["warm"]
                cold_warm.append({"scenario": scenario, "device": device,
                                  "cold_transfer_bytes": cold["initial_resource_transfer_bytes"], "warm_transfer_bytes": warm["initial_resource_transfer_bytes"],
                                  "cold_load_wall_ms": cold["initial_load_wall_ms"], "warm_load_wall_ms": warm["initial_load_wall_ms"],
                                  "cold_parse_ms": cold["initial_parse_ms_sum"], "warm_parse_ms": warm["initial_parse_ms_sum"],
                                  "cold_prepare_ms": cold["initial_prepare_ms_sum"], "warm_prepare_ms": warm["initial_prepare_ms_sum"],
                                  "heap_comparison": "not comparable: warm runs include an in-page priming pass and GC timing is uncontrolled"})
    desktop_mobile = []
    for scenario in SCENARIOS:
        for cache_mode in CACHE_MODES:
            by_device = {row["device"]: row for row in rows_by_scenario[scenario] if row["cache_mode"] == cache_mode}
            if {"desktop", "mobile_390x844"} <= set(by_device):
                desktop, mobile = by_device["desktop"], by_device["mobile_390x844"]
                desktop_mobile.append({"scenario": scenario, "cache_mode": cache_mode,
                                       "desktop_initial_heap_delta_bytes": desktop["heap_initial_delta_bytes"], "mobile_initial_heap_delta_bytes": mobile["heap_initial_delta_bytes"],
                                       "desktop_parse_ms": desktop["initial_parse_ms_sum"], "mobile_parse_ms": mobile["initial_parse_ms_sum"],
                                       "desktop_prepare_ms": desktop["initial_prepare_ms_sum"], "mobile_prepare_ms": mobile["initial_prepare_ms_sum"],
                                       "desktop_filter_bundle_ms": desktop["filter_bundle_ms"], "mobile_filter_bundle_ms": mobile["filter_bundle_ms"],
                                       "limitation": "mobile is viewport emulation only; no mobile CPU/network/UA simulation"})
    return {
        "schema_version": 1, "audit_id": "es-4b5c2-egif-browser-analysis-1",
        "input": {"results_runs_total": len(runs), "main_runs": len(main_rows), "smoke_runs_excluded_from_comparisons": len(smoke),
                  "results_environment": payload.get("environment")},
        "integrity": {"valid": not errors, "errors": errors, "main_matrix_observations_per_combination": 1,
                      "percentiles": "not computed: each scenario × device × cache combination has one observation"},
        "rows": main_rows, "scenario_summaries": scenario_summaries, "cold_vs_warm": cold_warm, "desktop_vs_mobile_viewport": desktop_mobile,
        "architecture_decision": {
            "ccaa_x_temporal_block_initial_columnar": "RECOMMENDED",
            "ccaa_full_period_initial": "VIABLE; Galicia full is MARGINAL as a default because it consumes 145.75 MiB cold EGIF-only heap increment",
            "spain_x_temporal_block_initial": "VIABLE on explicit demand; 1993-2002 is MARGINAL and must not combine by default with a heavy geometry view",
            "spain_all_initial": "VIABLE_BUT_NOT_DEFAULT; technically completes but consumes 184.31-252.49 MiB cold INITIAL heap before geometry",
            "detail_lazy": "RECOMMENDED; large detail assets confirm that detail must not be initial payload",
        },
        "known_measurement_limitations": [
            "fetch_ms is the sum of parallel fetch durations; initial_load_wall_ms is the elapsed load metric.",
            "localhost has no HTTP compression, CDN, TLS or real network latency; body raw bytes, Resource Timing transferSize and manifest gzip are intentionally distinct.",
            "warm heap is not comparable with cold heap because the warm benchmark executes a priming pass in the same browser context and GC is uncontrolled.",
            "The multi-asset same-asset selection request counter was recorded after a later other-detail selection; only the one-asset smoke validates it directly. Do not aggregate that field.",
            "Columnar-vs-objects is a <=1,000-row timing sample, with no isolated heap measurement.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    analysis = analyze(read_json(args.results.resolve()))
    if not args.check:
        atomic_json(args.output.resolve(), analysis)
    print(json.dumps({"valid": analysis["integrity"]["valid"], "main_runs": analysis["input"]["main_runs"], "smoke_runs_excluded": analysis["input"]["smoke_runs_excluded_from_comparisons"], "errors": analysis["integrity"]["errors"]}, ensure_ascii=False))
    return 0 if analysis["integrity"]["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
