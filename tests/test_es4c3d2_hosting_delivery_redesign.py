"""Validaciones estáticas de ES-4C3D2; no crean hosting ni usan red."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA = "3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe"


class Es4c3d2HostingDeliveryRedesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads((ROOT / "data/audit/hosting/es4c3d2_hosting_delivery_redesign.json").read_text(encoding="utf-8"))
        self.cors = json.loads((ROOT / "benchmarks/es4c3d2/r2-cors-staging.json").read_text(encoding="utf-8"))
        self.dashboard_cors = json.loads((ROOT / "benchmarks/es4c3d2/r2-cors-staging-dashboard.json").read_text(encoding="utf-8"))

    def test_asset_and_pages_estimate_are_reproducible(self) -> None:
        asset = self.payload["asset"]
        delivery = self.payload["current_delivery"]
        self.assertEqual(asset["bytes"], 63052056)
        self.assertEqual(asset["sha256"], EXPECTED_SHA)
        self.assertEqual(delivery["current_site_bytes"] + asset["bytes"], delivery["pages_with_pmtiles_bytes_estimate"])
        self.assertLess(delivery["pages_with_pmtiles_bytes_estimate"], delivery["pages_published_site_limit_bytes"])

    def test_preferred_staging_is_not_a_production_endpoint(self) -> None:
        self.assertEqual(self.payload["preferred"]["id"], "cloudflare_r2_public_development_url")
        self.assertEqual(self.payload["preferred"]["scope"], "staging only")
        self.assertEqual(self.payload["fallback"]["id"], "github_pages_same_origin_staging")
        self.assertEqual(self.payload["status"], "STAGING_READY_FOR_REVALIDATION")
        self.assertEqual(self.payload["next_validation"]["phase"], "ES-4C3D3_REAL_HOSTING_REVALIDATION")

    def test_cors_policy_is_explicit_and_does_not_use_wildcard(self) -> None:
        rule = self.cors["rules"][0]
        allowed = rule["allowed"]
        self.assertNotIn("*", allowed["origins"])
        self.assertEqual(allowed["methods"], ["GET", "HEAD"])
        self.assertIn("Range", allowed["headers"])
        self.assertIn("Content-Range", rule["exposeHeaders"])
        self.assertIn("http://127.0.0.1:8765", allowed["origins"])

    def test_real_staging_preflight_is_only_a_preflight(self) -> None:
        staging = self.payload["r2_staging"]
        preflight = staging["preflight"]
        self.assertEqual(preflight["head_content_length"], self.payload["asset"]["bytes"])
        self.assertEqual(preflight["range_0_0_status"], 206)
        self.assertEqual(preflight["access_control_allow_origin"], "http://127.0.0.1:8765")
        self.assertEqual(preflight["status"], "READY_FOR_C3D3_NOT_FULLY_VALIDATED")
        self.assertIsNone(preflight["cache_control"])

    def test_dashboard_policy_matches_the_restricted_wrangler_policy(self) -> None:
        wrangler = self.cors["rules"][0]
        dashboard = self.dashboard_cors[0]
        self.assertEqual(dashboard["AllowedOrigins"], wrangler["allowed"]["origins"])
        self.assertEqual(dashboard["AllowedMethods"], wrangler["allowed"]["methods"])
        self.assertEqual(dashboard["AllowedHeaders"], wrangler["allowed"]["headers"])
        self.assertEqual(dashboard["ExposeHeaders"], wrangler["exposeHeaders"])
        self.assertEqual(self.payload["local_cli_compatibility"]["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
