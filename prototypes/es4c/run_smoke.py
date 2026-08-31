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
BASELINE_ARCHIVE = ROOT / "data/derived/spain/es3/assets/esfire30-national-fidelity.pmtiles"
BASELINE_EXPECTED_SHA256 = "92f0f081131932075f54a89d86fc8aa7e5879d56ca4d7177c64562f9612751b4"
ARCHIVE_MANIFEST = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories-manifest.json"
ARCHIVE = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles"
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import run_page, run_pages  # noqa: E402

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
C2A3C_SMOKES = {
    "a_alacant_elx": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03065", "expected_municipality": "ES:MUN:03065"},
    "b_valencia_llocnou": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:46152", "expected_municipality": "ES:MUN:46152"},
    "c_girona_llivia": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "municipality_select": "ES:MUN:17094", "expected_municipality": "ES:MUN:17094"},
    "d_burgos_trevino": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "municipality_select": "ES:MUN:09109", "expected_municipality": "ES:MUN:09109"},
    "e_ceuta": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "municipality_select": "ES:MUN:51001", "expected_municipality": "ES:MUN:51001"},
    "f_rapid_barcelona_girona": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "municipality_rapid": True, "expected_municipality": "ES:MUN:17001", "expect_geometry": False},
    "g_mobile_elx": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "municipality_select": "ES:MUN:03065", "expected_municipality": "ES:MUN:03065", "mobile_only": True},
    "h_barcelona_heavy": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "municipality_select": "ES:MUN:08001", "expected_municipality": "ES:MUN:08001", "expect_geometry": False},
}
C2B2_SMOKES = {
    "a_spain": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_index_status": "national", "territory_index_ids": None},
    "b_pais_valencia": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:10", "territory_index_status": "covered", "territory_index_ids": 2203},
    "c_alacant": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:03", "territory_index_status": "covered", "territory_index_ids": 468},
    "d_valencia": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:46", "territory_index_status": "covered", "territory_index_ids": 945},
    "e_galicia": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12", "territory_index_status": "covered", "territory_index_ids": 38645},
    "f_ourense": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:32", "territory_index_status": "covered", "territory_index_ids": 16265},
    "g_baleares": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "province_select": "ES:PROV:07", "territory_index_status": "no_coverage", "territory_index_ids": 0},
    "h_mobile_pais_valencia": {"map": "pais_valencia", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:10", "territory_index_status": "covered", "territory_index_ids": 2203, "mobile_only": True},
}
C2B2B2_SMOKES = {
    # La primera feature renderizada de España a z4 puede desaparecer al
    # cambiar de tesela tras el zoom del smoke. La estabilidad de identidad se
    # verifica explícitamente en los controles multi-territorio de abajo.
    "a_spain": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_filter_status": "national", "expect_stable_geometry": False},
    "b_pais_valencia": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:10", "territory_filter_status": "covered"},
    "c_alacant": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:03", "territory_filter_status": "covered"},
    "d_valencia": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:46", "territory_filter_status": "covered"},
    "e_galicia": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12", "territory_filter_status": "covered"},
    "f_ourense": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:32", "territory_filter_status": "covered"},
    "g_sevilla": {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:41", "territory_filter_status": "covered"},
    "h_multi_alacant": {"map": "pais_valencia", "from": 1985, "to": 1985, "scope": "ES", "province_select": "ES:PROV:03", "select_geometry_id": "esfire30:v1:1985:268", "territory_filter_status": "covered", "expected_slots": {"ccaa_1": 10, "ccaa_2": None, "ccaa_3": None, "prov_1": 3, "prov_2": 46, "prov_3": None}},
    "i_multi_valencia": {"map": "pais_valencia", "from": 1985, "to": 1985, "scope": "ES", "province_select": "ES:PROV:46", "select_geometry_id": "esfire30:v1:1985:268", "territory_filter_status": "covered", "expected_slots": {"ccaa_1": 10, "ccaa_2": None, "ccaa_3": None, "prov_1": 3, "prov_2": 46, "prov_3": None}},
    "j_multi_ccaa_07": {"map": "spain", "from": 1985, "to": 1985, "scope": "ES", "territory_select": "ES:CCAA:07", "select_geometry_id": "esfire30:v1:1985:1037", "territory_filter_status": "covered", "expected_slots": {"ccaa_1": 7, "ccaa_2": 17, "ccaa_3": None, "prov_1": 9, "prov_2": 26, "prov_3": None}},
    "k_multi_ccaa_17": {"map": "spain", "from": 1985, "to": 1985, "scope": "ES", "territory_select": "ES:CCAA:17", "select_geometry_id": "esfire30:v1:1985:1037", "territory_filter_status": "covered", "expected_slots": {"ccaa_1": 7, "ccaa_2": 17, "ccaa_3": None, "prov_1": 9, "prov_2": 26, "prov_3": None}},
    "l_year_territory": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12", "territory_filter_status": "covered"},
    "m_baleares": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "province_select": "ES:PROV:07", "territory_filter_status": "no_coverage", "expect_geometry": False},
    "n_canarias": {"map": "spain", "from": 1995, "to": 1995, "scope": "ES", "territory_select": "ES:CCAA:05", "territory_filter_status": "no_coverage", "expect_geometry": False},
    "o_mobile_galicia": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "territory_select": "ES:CCAA:12", "territory_filter_status": "covered", "mobile_only": True},
    "p_mobile_alacant": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "province_select": "ES:PROV:03", "territory_filter_status": "covered", "mobile_only": True},
    "q_restore_alacant": {
        "map": "pais_valencia", "from": 1985, "to": 1985, "scope": "ES", "territory_restore": True,
        "state_hash": "#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM4Ljg0NjY2LCJsb24iOi0wLjM5NDEzLCJ6IjoxMH0sInRpbWUiOnsiZnJvbSI6MTk4NSwidG8iOjE5ODV9LCJ0ZXJyaXRvcnkiOnsic2NvcGUiOiJwcm92aW5jZSIsImF1dG9ub21vdXNfY29tbXVuaXR5X2lkIjoiRVM6Q0NBQToxMCIsInByb3ZpbmNlX2lkIjoiRVM6UFJPVjowMyJ9LCJzb3VyY2VzIjp7ImVzZmlyZTMwIjp0cnVlLCJlZ2lmIjp0cnVlfSwic2VsZWN0aW9ucyI6eyJnZW9tZXRyeV9pZCI6ImVzZmlyZTMwOnYxOjE5ODU6MjY4IiwiZWdpZl9yZWNvcmRfaWQiOm51bGx9fQ",
        "expect_geometry": False, "territory_filter_status": "covered", "restore_geometry_id": "esfire30:v1:1985:268",
    },
}
C2B3B1_SMOKES = {
    # El índice tiene listas para toda la cobertura. Los casos se ejecutan con
    # el rango completo para medir la lista real; el caso year confirma el AND.
    "a_elx": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent", "municipal_ids": 6},
    "b_barcelona": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:08019", "municipal_index": "parent", "municipal_ids": 20},
    "c_ourense": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:32054", "municipal_index": "parent", "municipal_ids": 152},
    "d_trevino": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:09109", "municipal_index": "parent", "municipal_ids": 73},
    "e_cangas_parent": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent", "municipal_ids": 2610},
    # El control genérico de zoom puede desplazar fuera del viewport la primera
    # feature elegida; la pertenencia y selección municipal se validan antes.
    "f_cangas_national": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "national", "municipal_ids": 2610, "expect_stable_geometry": False},
    "g_allande": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33001", "municipal_index": "parent", "municipal_ids": 1306},
    "h_viana": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:32086", "municipal_index": "parent", "municipal_ids": 1178},
    "i_zero_agost": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:03002", "municipal_index": "parent", "municipal_ids": 0, "expect_geometry": False},
    "j_multi_alacant": {"map": "spain", "from": 2011, "to": 2011, "scope": "ES", "municipality_select": "ES:MUN:03084", "municipal_index": "parent", "municipal_ids": 18, "select_geometry_id": "esfire30:v1:2011:88"},
    "k_multi_valencia": {"map": "spain", "from": 2011, "to": 2011, "scope": "ES", "municipality_select": "ES:MUN:46255", "municipal_index": "parent", "municipal_ids": 22, "select_geometry_id": "esfire30:v1:2011:88"},
    "l_year_municipality": {"map": "spain", "from": 1993, "to": 1993, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent", "municipal_ids": 6},
    "m_mobile_cangas": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent", "municipal_ids": 2610, "mobile_only": True},
    "n_same_parent_cache": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipality_sequence": "ES:MUN:33001", "municipal_index": "parent", "municipal_ids": 1306, "same_parent_cache": True},
    "o_parent_change": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipality_sequence": "ES:MUN:32054", "municipal_index": "parent", "municipal_ids": 152, "parent_change": True},
    "p_selection_invalidation": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipality_selection_change": "ES:MUN:33001", "municipal_index": "parent", "municipal_ids": 1306, "selection_invalidation": True},
    "q_restore": {"map": "spain", "from": 1993, "to": 1993, "scope": "ES", "territory_restore": True, "state_hash": "#es4c-state-v1=eyJ2IjoiZXM0Yy1zdGF0ZS12MSIsIm1hcCI6eyJsYXQiOjM4LjE3OTEsImxvbiI6LTAuNzE4OTIsInoiOjExLjQ4fSwidGltZSI6eyJmcm9tIjoxOTkzLCJ0byI6MTk5M30sInRlcnJpdG9yeSI6eyJzY29wZSI6Im11bmljaXBhbGl0eSIsImF1dG9ub21vdXNfY29tbXVuaXR5X2lkIjoiRVM6Q0NBQToxMCIsInByb3ZpbmNlX2lkIjoiRVM6UFJPVjowMyIsIm11bmljaXBhbGl0eV9pZCI6IkVTOk1VTjowMzA2NSJ9LCJzb3VyY2VzIjp7ImVzZmlyZTMwIjp0cnVlLCJlZ2lmIjp0cnVlfSwic2VsZWN0aW9ucyI6eyJnZW9tZXRyeV9pZCI6ImVzZmlyZTMwOnYxOjE5OTM6Nzc3IiwiZWdpZl9yZWNvcmRfaWQiOm51bGx9fQ", "municipal_index": "parent", "municipal_ids": 6, "expect_geometry": False, "restore_geometry_id": "esfire30:v1:1993:777"},
}
C3A_SMOKES = {
    "a_elx_end_to_end": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent", "municipal_ids": 6, "c3a_select_both": True, "c3a_roundtrip": True, "require_both_selections": True, "require_restore": True},
    "b_galicia_ourense": {"map": "galicia", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:32054", "municipal_index": "parent", "municipal_ids": 152},
    "c_cangas": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent", "municipal_ids": 2610},
    "d_canarias": {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:35016", "municipal_index": "parent", "expect_geometry": False, "esfire_status": "covered", "municipal_no_coverage": True},
    "e_agost_zero_relations": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03002", "municipal_index": "parent", "municipal_ids": 0, "expect_geometry": False},
    "f_rapid_galicia_to_elx": {"map": "spain", "from": 1993, "to": 2002, "scope": "ES", "c3a_rapid_transition": True, "expected_final_territory": "ES:MUN:03065", "municipal_index": "parent"},
    # El smoke móvil de Elx comprueba navegación, filtros, panel y ficha EGIF;
    # la selección ESFire30 móvil se verifica en Cangas, cuyo viewport tiene
    # features renderizadas de forma reproducible.
    "g_mobile_elx": {"map": "pais_valencia", "from": 1993, "to": 2002, "scope": "ES", "municipality_select": "ES:MUN:03065", "municipal_index": "parent", "municipal_ids": 6, "expect_geometry": False, "mobile_only": True},
    "h_mobile_cangas": {"map": "spain", "from": 1985, "to": 2021, "scope": "ES", "municipality_select": "ES:MUN:33011", "municipal_index": "parent", "municipal_ids": 2610, "mobile_only": True},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_archive() -> dict:
    if not ARCHIVE.is_file():
        raise FileNotFoundError(f"No existe {ARCHIVE}. Ejecuta externamente el builder territorial ya aprobado.")
    expected = json.loads(ARCHIVE_MANIFEST.read_text(encoding="utf-8"))["artifacts"]["enriched"]
    actual = sha256(ARCHIVE)
    if actual != expected["sha256"]:
        raise RuntimeError(f"Checksum PMTiles inesperado: {actual}")
    if ARCHIVE.stat().st_size != expected["bytes"]:
        raise RuntimeError(f"Tamaño PMTiles inesperado: {ARCHIVE.stat().st_size}")
    return {"path": str(ARCHIVE.relative_to(ROOT)), "bytes": ARCHIVE.stat().st_size, "sha256": actual, "manifest": str(ARCHIVE_MANIFEST.relative_to(ROOT))}


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
        self.municipal_index_requests = 0
        self.municipal_index_raw_bytes = 0
        self.injected_failures = []
        self.consumed_fail_once = set()

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

    def record_municipal_index(self, bytes_sent: int) -> None:
        with self.lock:
            self.municipal_index_requests += 1
            self.municipal_index_raw_bytes += bytes_sent

    def record_injected_failure(self, path: str, status: int) -> None:
        with self.lock:
            self.injected_failures.append({"path": path, "status": status})

    def take_fail_once(self, marker: str) -> bool:
        with self.lock:
            if marker in self.consumed_fail_once:
                return False
            self.consumed_fail_once.add(marker)
            return True

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
                "municipal_index_requests": self.municipal_index_requests,
                "municipal_index_raw_bytes": self.municipal_index_raw_bytes,
                "injected_failures": list(self.injected_failures),
            }


class RangeRequestHandler(SimpleHTTPRequestHandler):
    range_state: RangeState
    fail_paths: tuple[str, ...] = ()
    fail_once_paths: tuple[str, ...] = ()

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
        path = self.path.split("?", 1)[0]
        always_fail = any(marker in path for marker in self.fail_paths)
        once_marker = next((marker for marker in self.fail_once_paths if marker in path), None)
        if always_fail or (once_marker and self.range_state.take_fail_once(once_marker)):
            self.range_state.record_injected_failure(path, 503)
            self.send_error(503, "Acceptance harness injected failure")
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
            elif "/municipality-index/" in path:
                self.range_state.record_municipal_index(size)
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


def start_server(background: bool = True, fail_paths: tuple[str, ...] = (), fail_once_paths: tuple[str, ...] = (), port: int = 0) -> tuple[ThreadingHTTPServer, RangeState]:
    state = RangeState()
    failure_markers = tuple(fail_paths)
    failure_once_markers = tuple(fail_once_paths)
    class Handler(RangeRequestHandler):
        range_state = state
        fail_paths = failure_markers
        fail_once_paths = failure_once_markers
    server = ThreadingHTTPServer(("127.0.0.1", port), lambda *args, **kwargs: Handler(*args, directory=str(ROOT), **kwargs))
    if background:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def build_case_url(port: int, scenario: str, egif_config: dict | None = None, entry_path: str = "/prototypes/es4c/index.html") -> str:
    """Construye una URL de smoke; C3D3 fija explícitamente el puerto 8765."""
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
        for key in ("municipality_select", "municipality_click"):
            if egif_config.get(key):
                query[key] = egif_config[key]
        if egif_config.get("municipal_index"):
            query["municipal_index_strategy"] = egif_config["municipal_index"]
        if egif_config.get("municipality_sequence"):
            query["municipality_sequence"] = egif_config["municipality_sequence"]
        if egif_config.get("municipality_selection_change"):
            query["municipality_selection_change"] = egif_config["municipality_selection_change"]
        if egif_config.get("municipality_rapid"):
            query["municipality_rapid"] = "1"
        if egif_config.get("municipality_retry"):
            query["municipality_retry"] = "1"
        if egif_config.get("municipality_retry_id"):
            query["municipality_retry_id"] = egif_config["municipality_retry_id"]
        if egif_config.get("pmtiles_retry"):
            query["pmtiles_retry"] = "1"
        if egif_config.get("pmtiles_url"):
            query["pmtiles_url"] = egif_config["pmtiles_url"]
        if egif_config.get("pmtiles_telemetry"):
            query["pmtiles_telemetry"] = "1"
        if egif_config.get("browser_range_fetch"):
            query["browser_range_fetch"] = "1"
        if egif_config.get("state_prepare"):
            query["state_prepare"] = egif_config["state_prepare"]
        if egif_config.get("territory_up"):
            query["territory_up"] = "1"
        if egif_config.get("select_geometry_id"):
            query["select_geometry_id"] = egif_config["select_geometry_id"]
        if egif_config.get("select_icv_geometry_id"):
            query["select_icv_geometry_id"] = egif_config["select_icv_geometry_id"]
        if egif_config.get("c3a_select_both"):
            query["c3a_select_both"] = "1"
        if egif_config.get("c3a_roundtrip"):
            query["c3a_roundtrip"] = "1"
        if egif_config.get("c3a_rapid_transition"):
            query["c3a_rapid_transition"] = "1"
        if egif_config.get("icv_rapid"):
            query["icv_rapid"] = "1"
    url = f"http://127.0.0.1:{port}{entry_path}?{urlencode(query)}"
    if egif_config and egif_config.get("corrupt_hash"):
        url += egif_config["corrupt_hash"]
    if egif_config and egif_config.get("state_hash"):
        url += egif_config["state_hash"]
    return url


def run_case(chrome: str, scenario: str, device: str, egif_config: dict | None = None, server_port: int = 0, entry_path: str = "/prototypes/es4c/index.html") -> dict:
    server, state = start_server(
        fail_paths=tuple((egif_config or {}).get("fault_paths", ())),
        fail_once_paths=tuple((egif_config or {}).get("fault_once_paths", ())),
        port=server_port,
    )
    try:
        window = "390,844" if device == "mobile_390x844" else "1280,800"
        url = build_case_url(server.server_port, scenario, egif_config, entry_path)
        if egif_config and egif_config.get("roundtrip"):
            prepare_config = dict(egif_config)
            prepare_config["state_prepare"] = egif_config["roundtrip"]
            prepare_url = build_case_url(server.server_port, scenario, prepare_config, entry_path)
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


def run_case_sequence(chrome: str, cases: list[tuple[str, str, dict]], server_port: int = 0, entry_path: str = "/prototypes/es4c/index.html") -> list[dict]:
    """Ejecuta smokes consecutivos con un único perfil Chromium efímero."""
    server, state = start_server(port=server_port)
    try:
        if not cases:
            return []
        window = "390,844" if cases[0][1] == "mobile_390x844" else "1280,800"
        urls = []
        for index, (scenario, _device, config) in enumerate(cases):
            base_url = build_case_url(server.server_port, scenario, config, entry_path)
            separator = "&" if "?" in base_url else "?"
            urls.append(f"{base_url}{separator}sequence_step={index}")
        results = run_pages(chrome, urls, window, timeout=120)
        for result, (scenario, device, config) in zip(results, cases):
            result["server_range_stats"] = state.payload()
            result["device"] = device
            result["expected_egif"] = config
            result["sequence_profile"] = "shared_ephemeral_chromium"
            result["scenario"] = scenario
        return results
    finally:
        server.shutdown()
        server.server_close()


def validate_results(payload: dict) -> list[str]:
    errors = []
    for result in payload.get("runs", []):
        label = f"{result.get('scenario')}::{result.get('device')}"
        if result.get("errors"):
            errors.append(f"{label}: {result['errors']}")
        expected_egif = result.get("expected_egif", {})
        consolidated_geometry = (result.get("consolidation", {}).get("selection") or {}).get("geometry_id")
        expect_geometry = expected_egif.get("expect_geometry", True)
        if expect_geometry and not (result.get("selection", {}).get("geometry_id") or consolidated_geometry):
            errors.append(f"{label}: no se seleccionó geometry_id")
        # En alcance municipal, el smoke mueve el mapa al primer vértice que
        # devuelve una tesela; al siguiente zoom puede caer fuera de viewport
        # aunque el filtro, la selección y el geometry_id sean correctos. No
        # es una prueba de identidad ni una condición de C2B3B1.
        require_stable_geometry = expected_egif.get("expect_stable_geometry", True) and result.get("state", {}).get("territory_scope") != "municipality" and not expected_egif.get("c3a_select_both")
        if expect_geometry and require_stable_geometry and not result.get("selection", {}).get("stable_at_next_zoom"):
            errors.append(f"{label}: geometry_id no se mantuvo visible al siguiente zoom")
        stats = result.get("server_range_stats", {})
        if stats.get("range_requests", 0) <= 0:
            errors.append(f"{label}: no se observó Range")
        if stats.get("full_pmtiles_requests", 0) != 0:
            errors.append(f"{label}: se descargó PMTiles completo")
        if any(status != 206 for status in stats.get("statuses", [])):
            errors.append(f"{label}: estados PMTiles distintos de 206")
        if expected_egif:
            egif = result.get("egif", {})
            if expected_egif.get("egif_status") == "disabled" and egif.get("status") != "inactive":
                errors.append(f"{label}: EGIF desactivado no quedó inactivo: {egif}")
            elif expected_egif.get("egif_status") != "disabled" and egif.get("status") != "complete":
                errors.append(f"{label}: EGIF no completó: {egif}")
            elif "records" in expected_egif and egif.get("summary", {}).get("records") != expected_egif["records"]:
                errors.append(f"{label}: recuento EGIF inesperado")
            if not expected_egif.get("detail") and not expected_egif.get("c3a_select_both") and expected_egif.get("roundtrip") not in ("egif", "both") and stats.get("detail_requests") != 0:
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
            if expected_egif.get("expected_municipality"):
                municipality = result.get("municipality_layer", {})
                if not municipality.get("loaded") or municipality.get("selected_municipality_id") != expected_egif["expected_municipality"]:
                    errors.append(f"{label}: municipio BDLJE seleccionado inesperado: {municipality}")
                elif not municipality.get("selected_bounds"):
                    errors.append(f"{label}: municipio sin bounds 0 m")
            if "territory_index_status" in expected_egif:
                index = result.get("esfire30_territory_index", {})
                if index.get("status") != expected_egif["territory_index_status"]:
                    errors.append(f"{label}: estado de índice territorial inesperado: {index}")
                if index.get("geometry_ids") != expected_egif["territory_index_ids"]:
                    errors.append(f"{label}: cardinalidad de índice territorial inesperada: {index}")
            if "territory_filter_status" in expected_egif:
                territory_filter = result.get("esfire30_territory_filter", {})
                if territory_filter.get("status") != expected_egif["territory_filter_status"]:
                    errors.append(f"{label}: estado de filtro MVT territorial inesperado: {territory_filter}")
                if territory_filter.get("external_index_loaded") is not False:
                    errors.append(f"{label}: el filtro territorial sigue dependiendo del índice externo")
                requested_geometry = expected_egif.get("select_geometry_id")
                if requested_geometry and result.get("selection", {}).get("geometry_id") != requested_geometry:
                    errors.append(f"{label}: la geometría de control no se seleccionó tras el filtro territorial")
                if expected_egif.get("expected_slots") and result.get("selection", {}).get("territory_slots") != {"geometry_id": requested_geometry, "year": 1985, **expected_egif["expected_slots"]}:
                    errors.append(f"{label}: slots territoriales MVT inesperados: {result.get('selection', {}).get('territory_slots')}")
                if expected_egif.get("restore_geometry_id") and result.get("state", {}).get("selected_geometry_id") != expected_egif["restore_geometry_id"]:
                    errors.append(f"{label}: no restauró geometry_id compatible con territorio y periodo")
            if "municipal_ids" in expected_egif:
                territory_filter = result.get("esfire30_territory_filter", {})
                if territory_filter.get("status") != "municipality":
                    errors.append(f"{label}: no aplicó filtro municipal: {territory_filter}")
                if territory_filter.get("geometry_ids") != expected_egif["municipal_ids"]:
                    errors.append(f"{label}: lista municipal inesperada: {territory_filter}")
                if territory_filter.get("strategy") != expected_egif.get("municipal_index"):
                    errors.append(f"{label}: estrategia municipal inesperada: {territory_filter}")
                if expected_egif.get("municipal_ids", 0) > 0 and territory_filter.get("expression_bytes", 0) <= 0:
                    errors.append(f"{label}: no construyó expresión municipal")
                sequence = result.get("municipality_esfire_index", {}).get("sequence") or {}
                if expected_egif.get("same_parent_cache"):
                    steps = sequence.get("steps", [])
                    if len(steps) != 1 or not steps[0].get("index_cached"):
                        errors.append(f"{label}: cambio municipal del mismo padre no reutilizó índice")
                if expected_egif.get("parent_change"):
                    steps = sequence.get("steps", [])
                    if len(steps) != 1 or steps[0].get("parent_id") != "ES:PROV:32" or steps[0].get("index_cached"):
                        errors.append(f"{label}: cambio de provincia no cargó el índice padre correspondiente")
                if expected_egif.get("selection_invalidation"):
                    invalidation = result.get("municipality_esfire_index", {}).get("selection_invalidation") or {}
                    if not invalidation.get("before_geometry_id") or invalidation.get("after_geometry_id") is not None:
                        errors.append(f"{label}: selección ESFire30 no se invalidó al cambiar municipio")
                if expected_egif.get("restore_geometry_id") and result.get("state", {}).get("selected_geometry_id") != expected_egif["restore_geometry_id"]:
                    errors.append(f"{label}: no restauró geometry_id municipal compatible")
            if expected_egif.get("municipal_no_coverage") and result.get("esfire30_territory_filter", {}).get("status") != "no_coverage":
                errors.append(f"{label}: municipio sin cobertura quedó como cero relaciones")
            consolidation = result.get("consolidation", {})
            if expected_egif.get("require_both_selections"):
                selected = consolidation.get("selection") or {}
                if not selected.get("geometry_id") or not selected.get("egif_record_id"):
                    errors.append(f"{label}: no coexistieron selecciones EGIF/ESFire30")
            if expected_egif.get("require_restore"):
                restored = consolidation.get("restore") or {}
                if not restored.get("selected_geometry_id") or not restored.get("selected_egif_record_id"):
                    errors.append(f"{label}: restore consolidado no restauró ambas selecciones")
            if expected_egif.get("expected_final_territory") and (consolidation.get("rapid_transition") or {}).get("final_territory") != expected_egif["expected_final_territory"]:
                errors.append(f"{label}: transición rápida dejó ámbito stale")
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
    parser.add_argument("--c2a3c-smoke", choices=tuple(C2A3C_SMOKES), action="append")
    parser.add_argument("--all-c2a3c-smokes", action="store_true")
    parser.add_argument("--c2b2-smoke", choices=tuple(C2B2_SMOKES), action="append")
    parser.add_argument("--all-c2b2-smokes", action="store_true")
    parser.add_argument("--c2b2b2-smoke", choices=tuple(C2B2B2_SMOKES), action="append")
    parser.add_argument("--all-c2b2b2-smokes", action="store_true")
    parser.add_argument("--c2b3b1-smoke", choices=tuple(C2B3B1_SMOKES), action="append")
    parser.add_argument("--all-c2b3b1-smokes", action="store_true")
    parser.add_argument("--c3a-smoke", choices=tuple(C3A_SMOKES), action="append")
    parser.add_argument("--all-c3a-smokes", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "prototypes/es4c/smoke-results.json")
    parser.add_argument("--entry-path", default="/prototypes/es4c/index.html", help="entrypoint HTML relativo al root servido; permite validar la extracción D2")
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
    requested_c2a3c = args.c2a3c_smoke or (tuple(C2A3C_SMOKES) if args.all_c2a3c_smokes else ())
    requested_c2b2 = args.c2b2_smoke or (tuple(C2B2_SMOKES) if args.all_c2b2_smokes else ())
    requested_c2b2b2 = args.c2b2b2_smoke or (tuple(C2B2B2_SMOKES) if args.all_c2b2b2_smokes else ())
    requested_c2b3b1 = args.c2b3b1_smoke or (tuple(C2B3B1_SMOKES) if args.all_c2b3b1_smokes else ())
    requested_c3a = args.c3a_smoke or (tuple(C3A_SMOKES) if args.all_c3a_smokes else ())
    scenarios = args.scenario or (SCENARIOS if args.all_smokes else (() if (requested_egif or requested_detail or requested_c1c or requested_c1c2 or requested_c2a or requested_c2a2 or requested_c2a3c or requested_c2b2 or requested_c2b2b2 or requested_c2b3b1 or requested_c3a) else ("spain",)))
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
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_detail:
        config = EGIF_DETAIL_SMOKES[name]
        detail_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in detail_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c1c:
        config = C1C_SMOKES[name]
        c1c_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c1c_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c1c2:
        config = C1C2_SMOKES[name]
        c1c2_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c1c2_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c2a:
        config = C2A_SMOKES[name]
        c2a_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c2a_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c2a2:
        config = C2A2_SMOKES[name]
        c2a2_devices = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in c2a2_devices:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c2a3c:
        config = C2A3C_SMOKES[name]
        devices_for_case = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in devices_for_case:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c2b2:
        config = C2B2_SMOKES[name]
        devices_for_case = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in devices_for_case:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c2b2b2:
        config = C2B2B2_SMOKES[name]
        devices_for_case = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in devices_for_case:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c2b3b1:
        config = C2B3B1_SMOKES[name]
        devices_for_case = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in devices_for_case:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for name in requested_c3a:
        config = C3A_SMOKES[name]
        devices_for_case = ["mobile_390x844"] if config.get("mobile_only") else ["desktop"]
        for device in devices_for_case:
            print(f"{name}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, config["map"], device, config, entry_path=args.entry_path))
    for scenario in scenarios:
        for device in devices:
            print(f"{scenario}::{device}: ejecutando", flush=True)
            rows.append(run_case(args.chrome, scenario, device, entry_path=args.entry_path))
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
