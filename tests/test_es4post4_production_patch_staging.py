"""Focused static contract for the POST4 remote-staging auditor."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts/audit/product/es4post4_production_patch_staging.py"


def load_auditor():
    spec = importlib.util.spec_from_file_location("es4post4_auditor_test", AUDITOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Post4StagingContractTests(unittest.TestCase):
    def test_fixed_patch_identity_and_staging_only_endpoint(self):
        module = load_auditor()
        self.assertEqual(module.EXPECTED["site_file_count"], 500)
        self.assertEqual(module.EXPECTED["payload_file_count"], 498)
        self.assertEqual(module.EXPECTED["site_identity_sha256"], "f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1")
        self.assertIn("atlas-incendios-es4c3d4-pages-staging", module.BASE_URL)
        self.assertNotEqual(module.BASE_URL.rstrip("/"), "https://inthurain.github.io/atlas-incendios")

    def test_permalink_validation_accepts_a_retained_legacy_hash(self):
        module = load_auditor()
        payload = {
            "native": {"reload_match": True, "fresh_tab_match": True},
            "legacy": [
                {"scenario": "historic_1995", "runtime": {"input_hash_format": "gva_v1"}, "legacy_history": {"final_format": "gva_v1_retained"}, "errors": []},
                {"scenario": "recent_effis", "runtime": {"input_hash_format": "gva_v1"}, "legacy_history": {"final_format": "national_v1"}, "errors": []},
            ],
        }
        self.assertEqual(module.permalink_failures(payload), [])


if __name__ == "__main__":
    unittest.main()
