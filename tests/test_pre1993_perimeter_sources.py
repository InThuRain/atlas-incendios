import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest/egif/audit_pre1993_perimeter_sources.py"
SPEC = importlib.util.spec_from_file_location("pre1993_sources", SCRIPT)
pre1993_sources = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pre1993_sources
SPEC.loader.exec_module(pre1993_sources)
INVENTORY = json.loads(
    (ROOT / "data/sources/gva_pre1993_perimeter_sources.json").read_text(encoding="utf-8")
)


class Pre1993PerimeterSourceTests(unittest.TestCase):
    def test_scope_is_read_only_and_creates_no_geometry(self):
        self.assertEqual(0, INVENTORY["scope"]["geometry_created"])
        self.assertFalse(INVENTORY["scope"]["frontend_modified"])
        self.assertFalse(INVENTORY["scope"]["public_bundle_modified"])
        self.assertFalse(INVENTORY["esfire30_diagnostic"]["geometry_exported"])
        self.assertFalse(INVENTORY["esfire30_diagnostic"]["snapshot"]["downloaded_to_repository"])

    def test_source_classification_reconciles(self):
        summary = INVENTORY["source_summary"]
        self.assertEqual(14, summary["relevant_sources"])
        self.assertEqual(
            {
                "A_OFFICIAL_VECTOR": 0,
                "B_DOCUMENTED_REMOTE_SENSING": 5,
                "C_DOCUMENTED_CARTOGRAPHIC_RECONSTRUCTION": 0,
                "D_MAP_ONLY_UNCERTAIN": 1,
                "E_REFERENCE_ONLY": 4,
                "F_UNUSABLE": 4,
            },
            summary["by_quality"],
        )
        self.assertEqual(summary["relevant_sources"], sum(summary["by_quality"].values()))

    def test_esfire30_spatial_selection_reconciles(self):
        audit = INVENTORY["esfire30_diagnostic"]
        self.assertEqual(710, audit["selected_polygons"])
        self.assertEqual(710, sum(audit["by_year"].values()))
        self.assertEqual(710, sum(audit["by_primary_province"].values()))
        self.assertEqual(29, audit["cross_province_polygons"])
        self.assertEqual(710, audit["geometry_complexity"]["unique_geometry_wkb_hashes"])
        self.assertEqual(23030, audit["shapefile_crs"]["epsg"])
        self.assertIn("EPSG:25830", audit["metadata_crs_conflict"])

    def test_gif_matrix_preserves_parts_and_only_candidates(self):
        summary = INVENTORY["egif_gif_summary"]
        matrix = INVENTORY["egif_gif_matrix"]
        self.assertEqual(180, len(matrix))
        self.assertEqual(180, summary["parts"])
        self.assertEqual(0, summary["confirmed_links"])
        self.assertEqual(40, summary["with_esfire30_same_year_grid_candidate"])
        self.assertEqual(0, summary["with_esfire30_area_difference_le_10_ha"])
        self.assertEqual(58, summary["official_valencia_archive_scope_parts_1978_1992"])
        self.assertNotIn("confirmed_link", {row["link_status"] for row in matrix})

    def test_control_cases_remain_candidates(self):
        rows = {row["source_record_id"]: row for row in INVENTORY["egif_gif_matrix"]}
        for record_id in ("1986461220", "1991460176", "1991460188", "1992460251"):
            self.assertEqual("strong_candidate", rows[record_id]["link_status"])
        for record_id in ("1992460250", "1992120403", "1992469001"):
            self.assertNotEqual("confirmed_link", rows[record_id]["link_status"])

    def test_dependencies_and_constants_match_versioned_inventory(self):
        requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
        self.assertIn("pyshp==2.3.1", requirements)
        self.assertEqual(pre1993_sources.ESFIRE_SHA256, INVENTORY["esfire30_diagnostic"]["snapshot"]["sha256"])
        self.assertEqual(len(pre1993_sources.SOURCES), INVENTORY["source_summary"]["relevant_sources"])


if __name__ == "__main__":
    unittest.main()
