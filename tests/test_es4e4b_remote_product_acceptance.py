"""Static contracts for the E4B remote-only acceptance harness."""
from __future__ import annotations
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "benchmarks/es4e4b/run_remote_acceptance.py"


class ES4E4BRemoteAcceptanceTests(unittest.TestCase):
    def test_harness_is_staging_only_and_reuses_accepted_observers(self):
        text = HARNESS.read_text(encoding="utf-8")
        self.assertIn("atlas-incendios-es4c3d4-pages-staging", text)
        for expected in ("metrics", "filters", "highlights", "Network.setBlockedURLs", "cdn_cache_validation", "full_pmtiles_download_observed"):
            self.assertIn(expected, text)
        for forbidden in ("build_national_frontend.py", "gh workflow", "git push", "Page.navigate', {'url': 'https://inthurain.github.io/atlas-incendios/"):
            self.assertNotIn(forbidden, text)

    def test_contract_keeps_remote_identity_and_two_pmtiles_families(self):
        text = HARNESS.read_text(encoding="utf-8")
        for expected in ("static_identity", "protomaps_pmtiles", "esfire30_pmtiles", "asset-manifest.json", "site-identity.json"):
            self.assertIn(expected, text)


if __name__ == "__main__": unittest.main()
