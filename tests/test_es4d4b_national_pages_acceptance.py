"""Contratos estáticos y evidencia local de ES-4D4B.

No abre Chromium ni la red: la aceptación real está en el harness D4B y en su
evidencia machine-readable.
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/audit/hosting/es4d4b_national_pages_acceptance.py"
EVIDENCE = ROOT / "data/audit/production/es4d4b_national_production_staging_acceptance.json"
SPEC = importlib.util.spec_from_file_location("es4d4b_acceptance", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ES4D4BNationalPagesAcceptanceTests(unittest.TestCase):
    def test_harness_keeps_identity_and_range_contracts_explicit(self):
        source = PATH.read_text(encoding="utf-8")
        for required in (
            "PAYLOAD_FINGERPRINT",
            "MANIFEST_SHA256",
            "SITE_IDENTITY_SHA256",
            "range_test(base, 0, 0)",
            "range_test(base, 1048576, 1064959)",
            "full_pmtiles_download",
            "legacy_transition_copy",
            "gva_2024_record_only",
            "run_sequences",
            "--supplement-permalinks",
        ):
            self.assertIn(required, source)

    def test_runtime_urls_keep_pmtiles_same_origin(self):
        base = "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/"
        rendered = MODULE.runtime_url(base, "spain", {"sequence_step": "0"})
        self.assertIn("pmtiles_url=https%3A%2F%2Finthurain.github.io%2Fatlas-incendios-es4c3d4-pages-staging%2Fdata%2Fesfire30", rendered)
        self.assertIn("sequence_step=0", rendered)

    def test_evidence_preserves_attempt_one_and_accepts_attempt_two(self):
        payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["attempts"]["attempt_1"]["status"], "FAIL_ARTIFACT_IDENTITY")
        self.assertFalse(payload["attempts"]["attempt_1"]["deployed"])
        self.assertEqual(payload["attempts"]["attempt_2"]["status"], "PASS")
        self.assertFalse(payload["full_pmtiles_download_observed"])


if __name__ == "__main__":
    unittest.main()
