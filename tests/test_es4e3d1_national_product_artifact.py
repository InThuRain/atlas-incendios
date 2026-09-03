"""Contratos específicos del artifact nacional de producto ES-4E3D1."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSEMBLER = ROOT / "scripts/build_national_pages_artifact.py"
CHECKER = ROOT / "scripts/check_national_product_artifact.py"
RANGE_SERVER = ROOT / "benchmarks/es4e3c2_basemap/run.py"
PACKAGING_SMOKE = ROOT / "benchmarks/es4e3d1/run_packaging_smoke.py"
EVIDENCE = ROOT / "data/audit/product/es4e3d1_national_product_artifact.json"


class ES4E3D1ProductArtifactTests(unittest.TestCase):
    def test_product_output_and_approved_inputs_are_fixed(self):
        source = ASSEMBLER.read_text(encoding="utf-8")
        for expected in (
            'PRODUCT_OUTPUT = ROOT / "build/national-product-staging"',
            'APPROVED_SOURCE_COMMIT = "ab5d6c17891dcb05a54c85c5c3a1809d0325ba5a"',
            'SUMMARY_FINGERPRINT = "2546247b68ef8e27fed3334cf5fb4a027056f094e36420213080c431bfb850e4"',
            'SUMMARY_MANIFEST_SHA256 = "b09e69648b6b2dee03265f12a00624de72d4006301b04d796889c1bf151a8e7b"',
            'HIGHLIGHTS_MANIFEST_SHA256',
        ):
            self.assertIn(expected, source)

    def test_two_pmtiles_have_unambiguous_logical_ids_and_families(self):
        source = ASSEMBLER.read_text(encoding="utf-8")
        self.assertIn('"esfire30_fire_pmtiles"', source)
        self.assertIn('"protomaps_basemap_pmtiles"', source)
        self.assertNotIn('"pmtiles", "esfire30:national-fidelity-territories"', source)

    def test_independent_checker_covers_physical_failures(self):
        source = CHECKER.read_text(encoding="utf-8")
        for expected in (
            "extra asset",
            "missing asset",
            "size mismatch",
            "SHA mismatch",
            "manifest mismatch",
            "site identity mismatch",
            "payload fingerprint mismatch",
        ):
            self.assertIn(expected, source)

    def test_large_outputs_remain_ignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("build/national-product-staging/", ignored)
        self.assertIn("build/national-product-staging-repro/", ignored)

    def test_frontend_rewrites_prototype_fallbacks_inside_artifact(self):
        source = (ROOT / "scripts/build_national_frontend.py").read_text(encoding="utf-8")
        self.assertIn("STAGED_RUNTIME_REPLACEMENTS", source)
        self.assertIn('"data/territories/spain/v1/municipalities"', source)
        self.assertIn('"data/esfire30/v1/municipality-index"', source)

    def test_reused_range_server_serves_directory_index_responses(self):
        source = RANGE_SERVER.read_text(encoding="utf-8")
        self.assertIn("if remaining is None:", source)
        self.assertIn("return super().copyfile(source, output)", source)

    def test_packaging_smoke_can_resume_only_the_pending_fallback(self):
        source = PACKAGING_SMOKE.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--resume"', source)
        self.assertIn('dir=str(artifact.parent)', source)

    def test_glyph_audit_uses_browser_resources_so_missing_ranges_are_visible(self):
        source = PACKAGING_SMOKE.read_text(encoding="utf-8")
        self.assertIn("def requested_glyph_ranges", source)
        self.assertIn('row.get("resources", [])', source)
        self.assertIn('"unbundled_ranges"', source)

    def test_evidence_preserves_blocked_attempt_and_records_fixed_attempt(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["status"]["artifact_identity_status"], "PASS")
        self.assertEqual(evidence["status"]["product_artifact_status"], "READY_FOR_LOCAL_ACCEPTANCE")
        self.assertEqual(evidence["status"]["next_phase"], "ES-4E3D2_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE")
        self.assertEqual(evidence["attempts"]["attempt_1"]["status"], "BLOCKED_GLYPH_COVERAGE")
        self.assertEqual(evidence["attempts"]["attempt_1"]["site_identity"]["total_bytes"], 811665494)
        self.assertEqual(evidence["attempts"]["attempt_2"]["status"], "READY_FOR_LOCAL_ACCEPTANCE")
        self.assertEqual(evidence["site_identity"]["total_bytes"], 812510441)
        self.assertTrue(evidence["glyphs"]["range_discovery_stable"])
        self.assertIn("8192-8447.pbf", evidence["glyphs"]["bundled_ranges"])


if __name__ == "__main__":
    unittest.main()
