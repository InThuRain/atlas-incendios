import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks/es4b5c/run.py"
SCENARIOS = ROOT / "benchmarks/es4b5c/scenarios.json"
HTML = ROOT / "benchmarks/es4b5c/egif_benchmark.html"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b5c_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUN = load_module()


class ES4B5CBrowserHarnessTests(unittest.TestCase):
    def test_scenarios_cover_approved_national_cases_without_frontend_reference(self):
        scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"]
        self.assertEqual(11, len(scenarios))
        self.assertTrue({"a_la_rioja_full", "b_pais_valencia_full", "c_cataluna_full", "d_andalucia_full", "e_castilla_y_leon_full", "f_galicia_full", "g_galicia_1993_2002", "h_spain_1993_2002", "i_spain_2013_2023", "j_spain_all_initial"}.issubset({item["id"] for item in scenarios}))
        self.assertNotIn("index.html", HTML.read_text(encoding="utf-8"))
        self.assertFalse(next(item for item in scenarios if item["id"] == "smoke_la_rioja_2013_2023").get("include_in_all", True))

    def test_plan_supports_desktop_mobile_cold_warm(self):
        scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"]
        args = RUN.parse_args(["--scenario", "a_la_rioja_full", "--desktop", "--mobile", "--cold", "--warm"])
        jobs = RUN.plan(args, scenarios)
        self.assertEqual(4, len(jobs))
        self.assertEqual({"desktop", "mobile_390x844"}, {item["device"]["id"] for item in jobs})
        self.assertEqual({"cold", "warm"}, {item["cache_mode"] for item in jobs})

    def test_all_excludes_the_explicit_smoke_scenario(self):
        scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"]
        args = RUN.parse_args(["--all"])
        self.assertEqual(10, len(RUN.requested_scenarios(args, scenarios)))
        self.assertNotIn("smoke_la_rioja_2013_2023", [item["id"] for item in RUN.requested_scenarios(args, scenarios)])

    def test_results_validation_supports_resume_check_contract(self):
        scenario = json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"][0]
        item = {"scenario": scenario, "device": {"id": "desktop", "viewport": "1440,900"}, "cache_mode": "cold"}
        key = RUN.result_key(item)
        payload = {"runs": {key: {"status": "complete", "scenario": scenario["id"], "device": item["device"], "cache_mode": "cold", "manifest_sha256": "fixture", "errors": [], "result": {"complete": True}}}}
        self.assertEqual([], RUN.validate_results(payload, [item], "fixture"))
        payload["runs"][key]["errors"] = ["failure"]
        self.assertEqual([f"invalid result: {key}"], RUN.validate_results(payload, [item], "fixture"))


if __name__ == "__main__":
    unittest.main()
