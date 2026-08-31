from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/audit/hosting/es4c3d4_github_pages_same_origin_validation.py"
SPEC = importlib.util.spec_from_file_location("es4c3d4_validation", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Es4c3d4GithubPagesValidationTests(unittest.TestCase):
    def test_same_origin_urls_are_relative_to_pages_base(self):
        base = "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging"
        self.assertEqual(MODULE.asset_url(base), base + "/data/esfire30-national-fidelity-territories.pmtiles")
        self.assertEqual(MODULE.harness_url(base, "galicia"), base + "/es4c3d4/?smoke=galicia")

    def test_validation_does_not_require_cors_for_same_origin(self):
        payload = {"asset": {"bytes": 63052056, "sha256": MODULE.EXPECTED_SHA256}, "head": {"status": 200, "headers": {"content-length": "63052056"}}, "range_tests": {name: {"passed": True} for name in ("one_byte", "initial", "middle", "final")}, "browser_smokes": {"main": [{"scenario": "spain", "status": "PASS"}]}, "full_download_observed": False}
        self.assertEqual(MODULE.validate(payload), [])

    def test_full_download_fails_validation(self):
        payload = {"asset": {"bytes": 63052056, "sha256": MODULE.EXPECTED_SHA256}, "head": {"status": 200, "headers": {"content-length": "63052056"}}, "range_tests": {name: {"passed": True} for name in ("one_byte", "initial", "middle", "final")}, "browser_smokes": {}, "full_download_observed": True}
        self.assertEqual(MODULE.validate(payload), ["full_download"])


if __name__ == "__main__":
    unittest.main()
