#!/usr/bin/env python3
"""Static guards for ES-4D1: this phase must remain design-only."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MigrationDesignTests(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((ROOT / "data/audit/production/es4d1_migration_inventory.json").read_text(encoding="utf-8"))
        self.parity = json.loads((ROOT / "data/audit/production/es4d1_feature_parity.json").read_text(encoding="utf-8"))
        self.gates = json.loads((ROOT / "data/audit/production/es4d1_release_gates.json").read_text(encoding="utf-8"))

    def test_real_current_surfaces_and_workflows_exist(self):
        self.assertTrue((ROOT / "index.html").is_file())
        self.assertTrue((ROOT / "prototypes/es4c/index.html").is_file())
        self.assertTrue((ROOT / ".github/workflows/pages.yml").is_file())
        ids = {item["id"] for item in self.inventory["current_surfaces"]}
        self.assertEqual(ids, {"gva_public", "national_prototype", "gva_public_assets", "pages_staging_evidence"})

    def test_pages_and_pmtiles_configuration_is_single_and_versioned(self):
        self.assertEqual(self.inventory["hosting"]["initial_production"], "GITHUB_PAGES")
        self.assertIn("{sha256}", self.inventory["hosting"]["pmtiles_runtime_path_template"])
        pmtiles = next(asset for asset in self.inventory["assets"] if asset["id"] == "esfire30_pmtiles")
        self.assertEqual(pmtiles["bytes"], 63052056)
        self.assertEqual(pmtiles["sha256"], "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe")

    def test_parity_preserves_gva_and_identifies_root_switch_gaps(self):
        self.assertEqual(self.parity["permalink"]["public_gva"]["format"], "#v=1")
        self.assertEqual(self.parity["permalink"]["national"]["format"], "#es4c-state-v1")
        gaps = {item["feature"] for item in self.parity["features"] if item["root_switch"] == "must_have_parity_gap"}
        self.assertIn("ICV official consolidated perimeters 1993-2024", gaps)
        self.assertIn("EFFIS provisional perimeters 2025-2026", gaps)
        self.assertIn("public GVA #v=1 permalink", gaps)

    def test_release_gates_do_not_authorize_a_root_switch(self):
        self.assertFalse(self.gates["production_root_switch_authorized"])
        statuses = {gate["id"]: gate["status"] for gate in self.gates["gates"]}
        self.assertEqual(statuses["range_browser"], "evidence_passed_revalidate_on_final_endpoint")
        self.assertEqual(statuses["explicit_switch_authorization"], "not_requested")

    def test_document_preserves_semantic_separation_and_current_public_url(self):
        document = (ROOT / "ES_4D1_NATIONAL_PRODUCTION_MIGRATION_DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("https://inthurain.github.io/atlas-incendios/", document)
        self.assertIn("No hay enlace ni fusión automática entre", document)
        self.assertIn("ICV y EFFIS son necesarios antes de cambiar la raíz", document)


if __name__ == "__main__":
    unittest.main()
