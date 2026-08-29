import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build/esfire30/territory_pmtiles.py"
MANIFEST = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories-manifest.json"


def load_builder():
    spec = importlib.util.spec_from_file_location("esfire30_territory_pmtiles", BUILDER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ES4C2B2B2TerritoryPMTilesTests(unittest.TestCase):
    def test_national_manifest_reconciles_closed_territorial_input(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual("es4c2b2b1-territory-pmtiles-v1", payload["schema_version"])
        self.assertEqual(119498, payload["selection"]["geometry_count"])
        self.assertEqual(120847, payload["selection"]["ccaa_relations"])
        self.assertEqual(121887, payload["selection"]["province_relations"])
        self.assertEqual(["ccaa_1", "ccaa_2", "ccaa_3"], payload["encoding"]["ccaa"])
        self.assertEqual(["prov_1", "prov_2", "prov_3"], payload["encoding"]["province"])
        self.assertEqual("property omitted", payload["encoding"]["absent_slot"])

    def test_slot_encoding_is_deterministic_and_preserves_documented_multi_territory_cases(self):
        builder = load_builder()
        ccaa, province, _manifest = builder.load_membership()
        self.assertEqual([3, 46], province["esfire30:v1:1985:268"])
        self.assertEqual([7, 17], ccaa["esfire30:v1:1985:1037"])
        self.assertEqual(
            {"ccaa_1": 10, "prov_1": 3, "prov_2": 46},
            builder.slots_for("esfire30:v1:1985:268", ccaa, province),
        )
        self.assertEqual(
            {"ccaa_1": 7, "ccaa_2": 17, "prov_1": 9, "prov_2": 26},
            builder.slots_for("esfire30:v1:1985:1037", ccaa, province),
        )
        self.assertTrue(all(len(values) <= 3 for values in ccaa.values()))
        self.assertTrue(all(len(values) <= 3 for values in province.values()))

    def test_runtime_uses_mvt_slots_without_external_geometry_index(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        self.assertIn("esfire30-national-fidelity-territories.pmtiles", app)
        self.assertIn('property_prefix: match[1] === "CCAA" ? "ccaa" : "prov"', app)
        self.assertIn('`${esfireTerritory.property_prefix}_${slot}`', app)
        self.assertIn("territoryFilterExpression", app)
        self.assertNotIn("ESFire30TerritoryIndex", app)


if __name__ == "__main__":
    unittest.main()
