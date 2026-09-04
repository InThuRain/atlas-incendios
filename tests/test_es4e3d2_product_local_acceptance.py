import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/audit/product/es4e3d2_national_product_local_acceptance.json"
REPORT = ROOT / "ES_4E3D2_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE.md"


class ProductLocalAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_authorized_artifact_identity_is_frozen(self):
        identity = self.payload["artifact_identity"]
        self.assertEqual(identity["status"], "PASS")
        self.assertEqual((identity["site_file_count"], identity["site_total_bytes"]), (497, 812510441))
        self.assertEqual(identity["payload_fingerprint"], "10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3")
        self.assertEqual(identity["site_identity_sha256"], "f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e")

    def test_required_product_journeys_and_source_semantics(self):
        journeys = self.payload["journeys"]
        required = {
            "spain_full_1968_2026", "spain_1975", "spain_1995", "galicia_1995",
            "ourense_1995", "cangas_del_narcea_1985_2021", "gva_1995",
            "gva_1995_icv_min_500", "gva_2024", "icv_2024al0005", "gva_2026",
            "elx_2025", "canarias_1995",
        }
        self.assertEqual(set(journeys), required)
        self.assertTrue(all(row["status"] == "PASS" for row in journeys.values()))
        self.assertFalse(journeys["spain_full_1968_2026"]["cross_source_total"])
        self.assertEqual(journeys["canarias_1995"]["esfire30"], "not_available_for_territory_not_zero")

    def test_critical_safety_and_restore_gates_pass(self):
        self.assertTrue(self.payload["network"]["protomaps_range_only"])
        self.assertTrue(self.payload["network"]["esfire30_range_only"])
        self.assertFalse(self.payload["network"]["full_pmtiles_download_observed"])
        self.assertTrue(self.payload["permalinks"]["fresh_browser_profile_restore"])
        self.assertTrue(self.payload["legacy"]["back_restores_legacy_hash"])
        self.assertEqual(self.payload["errors"]["unexpected_console_or_runtime_errors"], 0)

    def test_decision_has_no_blocker_and_keeps_d5_paused(self):
        decision = self.payload["decision"]
        self.assertEqual(decision["product_local_acceptance"], "PASS_WITH_MINOR_GAPS")
        self.assertEqual(decision["blockers"], 0)
        self.assertEqual(decision["product_release_candidate"], "READY_FOR_REMOTE_PRODUCT_STAGING")
        self.assertEqual(decision["d5_status"], "PAUSED_FOR_PRODUCT_RECONCILIATION")
        self.assertEqual(decision["next_phase"], "ES-4E4_NATIONAL_PRODUCT_STAGING")
        self.assertIn("No se modificaron runtime", REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
