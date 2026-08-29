import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("territory_pmtiles", ROOT / "scripts/build/esfire30/territory_pmtiles.py")
MOD = importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MOD)


class TerritoryPmtilesEncodingTests(unittest.TestCase):
    def test_slots_are_numeric_sorted_and_omit_absent_values(self):
        ccaa = {"g": [3, 10]}; province = {"g": [3, 46, 50]}
        self.assertEqual(MOD.slots_for("g", ccaa, province), {"ccaa_1": 3, "ccaa_2": 10, "prov_1": 3, "prov_2": 46, "prov_3": 50})

    def test_existing_sample_reconciles_if_present(self):
        manifest = MOD.OUTPUT / MOD.output_names(True)[3]
        if manifest.exists():
            result = MOD.check(sample=True, output=MOD.OUTPUT)
            self.assertTrue(result["valid"], result)

    def test_relative_output_is_resolved_from_repository_root(self):
        self.assertEqual(MOD.resolve_output(Path("data/derived/example")), ROOT / "data/derived/example")


if __name__ == "__main__":
    unittest.main()
