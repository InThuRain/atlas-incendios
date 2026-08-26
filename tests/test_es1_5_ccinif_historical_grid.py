import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/spain/es1_5_ccinif_historical_grid.py"
DOWNLOAD_SCRIPT = ROOT / "scripts/ingest/egif/download_national_locations.py"
MANIFEST = ROOT / "data/sources/ccinif_historical_grid_manifest.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = load_module("es1_5_ccinif_grid", SCRIPT)
sys.path.insert(0, str(DOWNLOAD_SCRIPT.parent))
download = load_module("es1_5_egif_location_download", DOWNLOAD_SCRIPT)


class ES15CCINIFHistoricalGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_exact_normalization_does_not_fuzzy_match_or_pad(self):
        self.assertEqual("0704:C11", audit.pair_key(" 0704 ", "c11"))
        self.assertEqual("704:C11", audit.pair_key("704", "C11"))
        self.assertNotEqual(
            audit.pair_key("704", "C11"), audit.pair_key("0704", "C11")
        )
        self.assertIsNone(audit.pair_key("0704", None))

    def test_national_location_download_blocks_reconcile(self):
        counts = download.expected_counts(ROOT / "data/sources/spain_source_inventory.json")
        blocks = download.contiguous_blocks(counts, 50_000)
        self.assertEqual(646_887, sum(counts.values()))
        self.assertEqual(15, len(blocks))
        self.assertTrue(all(block["expected"] <= 50_000 for block in blocks))
        self.assertEqual(
            {"year_from": 1968, "year_to": 1979, "expected": 42_967},
            blocks[0],
        )
        self.assertEqual(
            {"year_from": 2018, "year_to": 2023, "expected": 47_816},
            blocks[-1],
        )

    def test_kmz_inventory_preserves_labels_and_geometry_parts(self):
        structure = self.manifest["structure"]
        self.assertEqual(702, structure["sheet_polygon_parts"])
        self.assertEqual(43, structure["logical_sheets"])
        self.assertEqual(6_220, structure["grid_polygon_parts"])
        self.assertEqual(5_286, structure["keyed_logical_cells"])
        self.assertEqual(6_063, structure["keyed_grid_geometry_parts"])
        self.assertEqual(157, structure["unkeyed_geometry_parts"])
        self.assertEqual(118, structure["cells_with_multiple_parts"])
        self.assertEqual(46, structure["maximum_parts_per_cell"])

    def test_national_crosswalk_is_exhaustive_and_fail_closed(self):
        crosswalk = self.manifest["egif_crosswalk"]
        states = crosswalk["classification"]
        self.assertEqual(646_887, crosswalk["records"])
        self.assertEqual(646_887, sum(states.values()))
        self.assertEqual(631_935, crosswalk["records_with_complete_reference"])
        self.assertEqual(626_957, crosswalk["exact_matches"])
        self.assertEqual(5_183, crosswalk["unique_exact_matches"])
        self.assertEqual(626_957, states["A_CONFIRMED"])
        self.assertEqual(0, states["B_PROBABLE"])
        self.assertEqual(3_465, states["C_AMBIGUOUS"])
        self.assertEqual(1_515, states["D_UNUSABLE"])
        self.assertEqual(14_950, states["NO_REFERENCE"])
        for row in crosswalk["by_year"].values():
            self.assertEqual(
                row["records"],
                sum(row.get(state, 0) for state in states),
            )

    def test_gva_reproduces_cv35_and_promotes_only_exact_pairs(self):
        gva = self.manifest["gva_control"]
        self.assertEqual(9_175, gva["records"])
        self.assertEqual(8_565, gva["with_sheet_and_grid"])
        self.assertEqual(610, gva["NO_REFERENCE"])
        self.assertEqual(270, gva["unique_complete_references"])
        self.assertEqual(270, gva["unique_exact_matches"])
        self.assertEqual(8_565, gva["A_CONFIRMED"])
        for item in self.manifest["control_records"].values():
            self.assertTrue(item["pair_matches_expected"])
            self.assertTrue(item["present_in_ccinif"])
            self.assertEqual("A_CONFIRMED", item["classification"])

    def test_temporal_use_and_xy_coexistence_are_data_driven(self):
        coverage = self.manifest["temporal_coverage"]
        self.assertEqual(1968, coverage["first_year_with_complete_sheet_grid"])
        self.assertEqual(2023, coverage["last_year_with_complete_sheet_grid"])
        self.assertEqual(1974, coverage["first_year_with_exact_ccinif_match"])
        self.assertEqual(2023, coverage["last_year_with_exact_ccinif_match"])
        self.assertEqual(1998, coverage["first_year_with_xy"])
        self.assertEqual(2023, coverage["last_year_with_xy"])

    def test_geometry_is_reference_only_and_license_is_closed(self):
        self.assertFalse(self.manifest["publishable"])
        self.assertEqual("false_pending_permission", self.manifest["license_status"])
        semantics = self.manifest["semantics"]
        self.assertIsNone(semantics["egif_geometry"])
        self.assertEqual("historical_grid_cell", semantics["reference_entity"])
        self.assertIn("grid cell as fire perimeter", semantics["prohibited_interpretations"])

    def test_future_format_deduplicates_cell_geometry(self):
        estimate = self.manifest["future_web_estimate"]
        self.assertEqual(5_183, estimate["unique_cells"])
        self.assertEqual(626_957, estimate["relations"])
        self.assertLess(estimate["unique_cells"], estimate["relations"])
        self.assertLess(estimate["grid_geojson_gzip_bytes"], 1_000_000)


if __name__ == "__main__":
    unittest.main()
