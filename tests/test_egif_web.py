import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_egif_frontend_assets.py"
SPEC = importlib.util.spec_from_file_location("egif_web", SCRIPT)
egif_web = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = egif_web
SPEC.loader.exec_module(egif_web)


class EgifWebTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/egif-web.json").read_text(encoding="utf-8"))
        vocabulary = json.loads((ROOT / self.config["causes"]["vocabulary_path"]).read_text(encoding="utf-8"))
        self.config["causes"]["canonical_labels"] = vocabulary["causes"]["categories"]
        self.base = {
            "source_record_id": "1992460001",
            "fire_id": "egif-record:1992460001",
            "province": "Valencia",
            "year": 1992,
            "municipality_codine": "46001",
            "municipality": "Ademuz",
            "reported_forest_area_ha": 501.5,
            "reported_total_area_ha": 503.0,
            "is_gif_ge_500_ha": True,
            "cause_source_code": "310",
            "cause": "Otras causas por ferrocarril (sin especificar)",
            "coverage_status": "systematic_or_near_systematic",
            "location_original": {"map_sheet": "1", "grid": "2"},
            "identity_status": "source_record_only",
            "episode_identity_status": "unresolved",
        }

    def test_compact_record_never_creates_geometry(self):
        record = egif_web.compact_record(self.base, {"46001": "Ademús"}, self.config)
        self.assertIsNone(record["geometry"])
        self.assertEqual("46001", record["municipality_id"])
        self.assertEqual("Ademús", record["municipality_name"])
        self.assertEqual("accidental", record["cause_code"])
        self.assertEqual("Accidental", record["cause_label"])
        self.assertTrue(record["has_grid_reference"])
        self.assertTrue(record["gif_forest"])

    def test_unknown_municipality_code_remains_unresolved(self):
        source = dict(self.base, municipality_codine="46999", municipality=None)
        record = egif_web.compact_record(source, {"46001": "Ademús"}, self.config)
        self.assertIsNone(record["municipality_id"])
        self.assertIsNone(record["municipality_name"])

    def test_unlisted_cause_remains_explicitly_unmapped(self):
        source = dict(self.base, cause_source_code="999", cause="Valor no documentado")
        record = egif_web.compact_record(source, {"46001": "Ademús"}, self.config)
        self.assertIsNone(record["cause_code"])
        self.assertEqual("unmapped", record["cause_mapping_status"])
        self.assertEqual("Valor no documentado", record["cause_raw"])

    def test_public_profile_declares_egif_publishable_but_keeps_sigif_blocked(self):
        catalog = json.loads((ROOT / "config/sources-gva.json").read_text(encoding="utf-8"))
        self.assertEqual(1968, catalog["timeline"]["min_year"])
        self.assertIn("egif", catalog["profiles"]["public"]["sources"])
        self.assertTrue(catalog["sources"]["egif"]["publishable"])
        self.assertNotIn("sigif", catalog["profiles"]["public"]["sources"])
        self.assertFalse(catalog["sources"]["sigif"]["publishable"])

    def test_historical_and_modern_cause_categories_remain_distinct(self):
        vocabulary = json.loads((ROOT / "config/ui-vocabularies.json").read_text(encoding="utf-8"))["causes"]
        self.assertEqual("Negligencia", vocabulary["categories"]["negligence"])
        self.assertEqual("Accidental", vocabulary["categories"]["accidental"])
        self.assertEqual(
            "Negligencias y causas accidentales",
            vocabulary["categories"]["negligence_and_accidental"],
        )
        self.assertEqual(3, len({
            vocabulary["categories"]["negligence"],
            vocabulary["categories"]["accidental"],
            vocabulary["categories"]["negligence_and_accidental"],
        }))


if __name__ == "__main__":
    unittest.main()
