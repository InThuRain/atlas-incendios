"""Contratos específicos de cobertura glyph ES-4E3D1_GLYPH_FIX."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/national-basemap-protomaps-20260902-z12.json"
ACQUIRE = ROOT / "scripts/basemaps/acquire_protomaps_glyphs.py"
ASSEMBLER = ROOT / "scripts/build_national_pages_artifact.py"
CHECKER = ROOT / "scripts/check_national_product_artifact.py"
MATRIX = ROOT / "benchmarks/es4e3d1/run_glyph_coverage.py"
PACKAGING = ROOT / "benchmarks/es4e3d1/run_packaging_smoke.py"
EVIDENCE = ROOT / "data/audit/product/es4e3d1_glyph_coverage.json"

EXPECTED_RANGES = [
    "0-255", "256-511", "512-767", "768-1023", "1024-1279",
    "1536-1791", "7680-7935", "8192-8447", "11520-11775",
]


class ES4E3D1GlyphCoverageTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.glyphs = self.contract["glyphs"]

    def test_manifest_freezes_one_fontstack_and_verified_ranges(self):
        self.assertEqual(self.glyphs["fontstack"], "Noto Sans Regular")
        self.assertEqual([row["range"] for row in self.glyphs["files"]], EXPECTED_RANGES)
        self.assertEqual(self.glyphs["file_count"], 9)
        self.assertEqual(self.glyphs["total_bytes"], 909374)
        self.assertEqual(sum(row["bytes"] for row in self.glyphs["files"]), 909374)
        self.assertEqual(self.glyphs["source_commit"], "028c18f713baecad011301ff7a69acc39bcc2ae7")
        self.assertEqual(self.glyphs["discovery_contract"], "ACCEPTANCE_MATRIX_COMPLETE")
        self.assertEqual(len({row["sha256"] for row in self.glyphs["files"]}), 9)

    def test_style_and_runtime_use_only_approved_fontstack(self):
        style_source = (ROOT / "benchmarks/es4e3c2_basemap/candidate.mjs").read_text(encoding="utf-8")
        frontend_source = (ROOT / "scripts/build_national_frontend.py").read_text(encoding="utf-8")
        self.assertIn("Noto Sans Regular", style_source)
        self.assertNotIn("Noto Sans Bold", style_source)
        self.assertNotIn("Noto Serif", style_source)
        self.assertIn('BASEMAP_MANIFEST["glyphs"]["files"]', frontend_source)

    def test_acquisition_is_explicit_and_validates_binary_pbf(self):
        source = ACQUIRE.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--download", action="store_true"', source)
        self.assertIn("validate_glyph_pbf", source)
        self.assertIn("la respuesta es HTML", source)
        self.assertIn("remote identity", source)
        self.assertIn("OFL identity", source)

    def test_assembler_and_checker_cover_every_declared_file(self):
        assembler = ASSEMBLER.read_text(encoding="utf-8")
        checker = CHECKER.read_text(encoding="utf-8")
        self.assertIn('glyph_descriptors = contract["glyphs"]["files"]', assembler)
        self.assertIn('for descriptor in glyph_contract["files"]', checker)
        self.assertIn("extra asset", checker)
        self.assertIn("glyph bytes", checker)
        self.assertIn("glyph SHA", checker)

    def test_matrix_is_expanded_and_observes_failed_browser_requests(self):
        source = MATRIX.read_text(encoding="utf-8")
        for context in (
            "spain", "galicia", "asturias", "cantabria", "pais_vasco",
            "navarra", "catalunya", "comunitat_valenciana", "illes_balears",
            "andalucia", "ceuta", "melilla", "canarias",
            "interior_madrid_toledo", "interior_castilla_leon", "interior_aragon",
        ):
            self.assertIn(f'"{context}"', source)
        self.assertIn("ZOOMS = (5, 7, 9, 12, 14)", source)
        self.assertIn("performance.getEntriesByType('resource')", source)
        self.assertIn('"glyph_404_count"', source)

    def test_quick_smokes_include_requested_mobile_cases(self):
        source = PACKAGING.read_text(encoding="utf-8")
        self.assertIn('"mobile_elx"', source)
        self.assertIn('"mobile_asturias"', source)
        self.assertIn("requested - BUNDLED_GLYPH_RANGES", source)

    def test_evidence_records_stable_bounded_coverage(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["discovery_method"], "ACCEPTANCE_MATRIX_COMPLETE")
        self.assertEqual(evidence["glyph_404_count"], 0)
        self.assertEqual(evidence["glyph_unbundled_range_count"], 0)
        self.assertTrue(evidence["range_discovery_stable"])
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["matrix"]["contexts"], 16)
        self.assertEqual(evidence["matrix"]["views_per_run"], 80)


if __name__ == "__main__":
    unittest.main()
