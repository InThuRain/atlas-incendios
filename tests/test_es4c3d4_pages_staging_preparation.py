"""Validaciones estáticas C3D4; no crean repositorios ni despliegan Pages."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Es4c3d4PagesStagingPreparationTests(unittest.TestCase):
    def test_completed_staging_never_targets_the_public_pages_site(self):
        payload = json.loads((ROOT / "data/audit/hosting/es4c3d4_github_pages_same_origin_validation.json").read_text())
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["pages_public_reference"]["status"], "NOT_USED_BY_C3D4")
        self.assertEqual(payload["asset"]["bytes"], 63052056)

    def test_workflow_uses_sha_gate_and_a_dispatch_selected_source_ref(self):
        workflow = (ROOT / "benchmarks/es4c3d4/pages-staging-workflow.yml").read_text()
        self.assertIn("source_ref", workflow)
        self.assertIn("63052056", workflow)
        self.assertIn("3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe", workflow)
        self.assertIn("maplibre-gl@5.16.0", workflow)
        self.assertIn("pmtiles@4.3.0", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)

    def test_builder_keeps_pmtiles_out_of_git_and_uses_relative_harness_asset(self):
        builder = (ROOT / "scripts/build_es4c3d4_pages_staging.py").read_text()
        harness = (ROOT / "benchmarks/es4c3d4/harness/app.js").read_text()
        self.assertIn("PMTiles rechazado por tamaño o SHA-256", builder)
        self.assertIn('new URL("../data/esfire30-national-fidelity-territories.pmtiles", location.href)', harness)
        self.assertIn("window.pmtiles", harness)
        self.assertIn('"ES:MUN:33011"', harness)
        self.assertIn('"ES:MUN:03065"', harness)

    def test_municipal_fixtures_preserve_the_two_smoke_memberships(self):
        fixtures = ROOT / "benchmarks/es4c3d4/fixtures/municipality-index"
        elx = json.loads((fixtures / "ES-PROV-03.json").read_text())
        cangas = json.loads((fixtures / "ES-PROV-33.json").read_text())
        self.assertEqual(elx["scope"], "single_municipality_fixture")
        self.assertEqual(len(elx["municipalities"]["ES:MUN:03065"]), 6)
        self.assertEqual(cangas["scope"], "single_municipality_fixture")
        self.assertEqual(len(cangas["municipalities"]["ES:MUN:33011"]), 2610)

if __name__ == "__main__":
    unittest.main()
