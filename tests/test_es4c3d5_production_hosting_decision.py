from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Es4c3d5ProductionHostingDecisionTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "data/audit/hosting/es4c3d5_production_hosting_decision.json").read_text())

    def test_decision_is_explicit_and_uses_validated_candidates(self):
        self.assertEqual(self.payload["initial_production_hosting"], "GITHUB_PAGES")
        self.assertEqual(self.payload["fallback_hosting"], "CLOUDFLARE_R2_CUSTOM_DOMAIN")
        self.assertEqual(self.payload["candidates"]["github_pages_same_origin"]["technical_validation"], "PASS")
        self.assertIn("FUTURE_SCALING_OPTION", self.payload["candidates"]["cloudflare_r2_custom_domain"]["classification"])

    def test_references_match_the_existing_evidence(self):
        pages = json.loads((ROOT / self.payload["technical_evidence"]["github_pages_same_origin"]).read_text())
        r2 = json.loads((ROOT / self.payload["technical_evidence"]["cloudflare_r2_dev"]).read_text())
        self.assertEqual(pages["status"], "PASS")
        self.assertEqual(r2["status"], "PASS")
        self.assertEqual(pages["asset"]["sha256"], self.payload["technical_evidence"]["asset"]["sha256"])
        self.assertFalse(pages["full_download_observed"])

    def test_review_triggers_and_next_phase_are_present(self):
        self.assertGreaterEqual(len(self.payload["review_triggers"]), 4)
        self.assertEqual(self.payload["next_phase"], "ES-4D1_NATIONAL_PRODUCTION_MIGRATION_DESIGN")


if __name__ == "__main__":
    unittest.main()
