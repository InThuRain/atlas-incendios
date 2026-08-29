import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/territories/audit_municipalities.py"
AUDIT = ROOT / "data/audit/territories/es4c2a3a_municipalities.json"


def load_module():
    spec = importlib.util.spec_from_file_location("es4c2a3a_municipalities", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


class ES4C2A3AMunicipalityTests(unittest.TestCase):
    def test_documented_bdlje_code_crosswalk_and_parent_hierarchy(self):
        municipalities = MODULE.municipal_snapshot(MODULE.SNAPSHOT)
        features = [
            {"properties": {"nationallevelname": "Municipio", "nationalcode": "34010404001", "nameunit": "Abla"}},
            {"properties": {"nationallevelname": "Municipio", "nationalcode": "34185151001", "nameunit": "Ceuta"}},
            {"properties": {"nationallevelname": "Municipio", "nationalcode": "34070953004", "nameunit": "Comunidad"}},
        ]
        report = MODULE.source_classification(features, municipalities)
        self.assertEqual({"MATCHED_CURRENT": 2, "NON_MUNICIPAL_UNIT": 1}, report["counts"])
        self.assertEqual([], report["parent_mismatch"])
        self.assertEqual(("01", "04", "04001"), MODULE.national_code_parts("34010404001"))

    def test_catalog_and_shard_design_are_deterministic_and_keep_autonomous_cities_out_of_province_shards(self):
        municipalities = MODULE.municipal_snapshot(MODULE.SNAPSHOT)
        first = MODULE.catalog_estimate(municipalities)
        second = MODULE.catalog_estimate(municipalities)
        self.assertEqual(first, second)
        self.assertEqual(8132, first["records"])
        self.assertGreater(first["gzip_bytes_without_bounds"], 0)
        self.assertEqual(("03", "46", "32", "41", "09", "17", "01", "35", "38", "07"), MODULE.SAMPLE_PROVINCES)

    def test_audit_inventory_and_sample_geometry_accounting(self):
        payload = json.loads(AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(8213, payload["inventory"]["source_features"])
        self.assertEqual(8132, payload["inventory"]["classification"]["MATCHED_CURRENT"])
        self.assertEqual(81, payload["inventory"]["classification"]["NON_MUNICIPAL_UNIT"])
        self.assertEqual([], payload["inventory"]["parent_hierarchy_mismatches"])
        self.assertEqual(10, len(payload["geometry_samples"]))
        for sample in payload["geometry_samples"].values():
            self.assertEqual(0, sample["null_geometry"])
            self.assertEqual(0, sample["invalid_geometry"])
            self.assertLess(sample["sizes"]["10"]["gzip_bytes"], sample["sizes"]["0"]["gzip_bytes"])
        self.assertTrue(payload["geometry_samples"]["17"]["special_cases"]["Llívia"])
        self.assertTrue(payload["geometry_samples"]["09"]["special_cases"]["Condado de Treviño"])
        self.assertTrue(payload["geometry_samples"]["46"]["special_cases"]["Rincón de Ademuz (municipio de Ademuz)"])


if __name__ == "__main__":
    unittest.main()
