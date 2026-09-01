"""Contratos ES-4D3C: adapter puro para hashes públicos GVA v1."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/gva_permalink_v1.json"
ADAPTER = ROOT / "src/national/compat/gva-v1.mjs"
RUNTIME = ROOT / "prototypes/es4c/app.js"
BUILDER = ROOT / "scripts/build_national_frontend.py"


class GvaPermalinkCompatibilityTests(unittest.TestCase):
    def test_fixtures_are_deterministic_and_cover_public_contract(self):
        payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
        ids = {row["id"] for row in payload["fixtures"]}
        self.assertEqual(ids, {"default_gva", "map_year_province", "icv_geometry_2024al0005", "icv_record_only_2024al0005", "effis_elx_2025", "malformed_values"})
        self.assertTrue(all(row["hash"].startswith("#v=1") for row in payload["fixtures"]))

    def test_adapter_runs_all_fixtures_and_preserves_multi_geometry_semantics(self):
        result = subprocess.run(["node", "--experimental-modules", "tests/gva_permalink_v1_adapter.mjs"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_adapter_is_encapsulated_and_build_copies_it(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("parseLegacyGvaV1State", source)
        self.assertIn("adaptLegacyGvaV1State", source)
        self.assertIn("dispatchStateHash", source)
        self.assertIn("compat/gva-v1.mjs", RUNTIME.read_text(encoding="utf-8"))
        self.assertIn("NATIONAL_COMPAT", BUILDER.read_text(encoding="utf-8"))

    def test_unknown_and_invalid_do_not_use_legacy_heuristics(self):
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn('params.get("v") !== GVA_V1', source)
        self.assertIn("unknown_version", source)
        self.assertIn("invalid", source)


if __name__ == "__main__":
    unittest.main()
