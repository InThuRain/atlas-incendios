import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/egif/es4b5c2_browser_analysis.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b5c2_browser_analysis", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ANALYSIS = load_module()


def wrapper(scenario, device, cache, assets=1, records=10):
    result = {
        "initial_records": records, "initial_asset_count": assets,
        "network": {"initial": {"gzip_estimated_bytes": 11, "body_bytes": 101, "resource_transfer_bytes": 111, "requests": assets, "fetch_ms": 1.2, "parse_ms": 0.4},
                    "detail": {"gzip_estimated_bytes": 7, "body_bytes": 71, "resource_transfer_bytes": 81, "requests": 1, "fetch_ms": 0.7, "parse_ms": 0.2}},
        "timings_ms": {"initial_load_wall_ms": 2, "initial_parse_ms_sum": 0.4, "prepare_ms_sum": 0.3, "filter_ms": 0.1, "lookup_ms": 0, "first_selection_ms": 0.5, "second_selection_same_asset_ms": 0},
        "heap": {"before": {"status": "available", "used_js_heap_size": 100}, "after_initial": {"status": "available", "used_js_heap_size": 200}, "after_detail": {"status": "available", "used_js_heap_size": 250}},
        "selection": {"second_same_asset_additional_detail_requests": 0 if assets == 1 else 1, "other_detail": {"additional_requests": 1} if assets > 1 else {"status": "unavailable"}},
        "filters": {}, "lookup": {}, "columnar_vs_objects_small_sample": {"status": "not_run"},
    }
    return {"status": "complete", "scenario": scenario, "scenario_label": scenario, "device": {"id": device}, "cache_mode": cache, "result": result, "errors": []}


class ES4B5C2BrowserAnalysisTests(unittest.TestCase):
    def test_compact_row_keeps_raw_transfer_and_manifest_gzip_distinct(self):
        row = ANALYSIS.compact_row(wrapper("fixture", "desktop", "cold", assets=2))
        self.assertEqual(11, row["initial_gzip_manifest_bytes"])
        self.assertEqual(101, row["initial_body_raw_bytes"])
        self.assertEqual(111, row["initial_resource_transfer_bytes"])
        self.assertEqual("not_usable_for_comparison", row["same_asset_detail_telemetry"]["status"])

    def test_single_asset_selection_is_the_only_direct_same_asset_probe(self):
        row = ANALYSIS.compact_row(wrapper("fixture", "desktop", "cold", assets=1))
        self.assertEqual({"status": "verified", "additional_detail_requests": 0}, row["same_asset_detail_telemetry"])

    def test_full_matrix_excludes_smoke_and_has_one_observation_per_combination(self):
        payload = {"environment": {}, "runs": {}}
        for scenario in ANALYSIS.SCENARIOS:
            for device in ANALYSIS.DEVICES:
                for cache in ANALYSIS.CACHE_MODES:
                    payload["runs"][ANALYSIS.run_key(scenario, device, cache)] = wrapper(scenario, device, cache)
        payload["runs"]["smoke"] = wrapper("smoke_la_rioja_2013_2023", "desktop", "cold")
        result = ANALYSIS.analyze(payload)
        self.assertTrue(result["integrity"]["valid"])
        self.assertEqual(40, result["input"]["main_runs"])
        self.assertEqual(1, result["input"]["smoke_runs_excluded_from_comparisons"])
        self.assertEqual("VIABLE_BUT_NOT_DEFAULT", next(item for item in result["scenario_summaries"] if item["scenario"] == "j_spain_all_initial")["classification"])


if __name__ == "__main__":
    unittest.main()
