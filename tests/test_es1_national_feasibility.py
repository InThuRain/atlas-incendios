import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_INVENTORY = ROOT / "data/sources/spain_source_inventory.json"
PERIMETER_INVENTORY = ROOT / "data/sources/spain_official_perimeter_inventory.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_audit_module():
    path = ROOT / "scripts/audit/spain/es1_national_feasibility.py"
    spec = importlib.util.spec_from_file_location("es1_national_feasibility", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ES1NationalFeasibilityTests(unittest.TestCase):
    def test_egif_count_inventory_is_reconciled_and_not_mislabelled(self):
        inventory = load_json(SOURCE_INVENTORY)
        egif = next(source for source in inventory["sources"] if source["id"] == "egif")
        counts = egif["annual_counts"]
        self.assertEqual(646_887, sum(counts.values()))
        self.assertEqual(646_887, egif["records_observed"])
        self.assertEqual(5_223, counts["2023"])
        self.assertEqual(0, counts["2024"])
        self.assertEqual(0, counts["2025"])
        self.assertIn("do not prove", egif["coverage_warning"])
        self.assertEqual("administrative_record", egif["entity_type"])
        self.assertTrue(egif["geometry_role"].startswith("none"))

    def test_esfire30_measurements_and_source_separation_are_preserved(self):
        inventory = load_json(SOURCE_INVENTORY)
        sources = {source["id"]: source for source in inventory["sources"]}
        esfire = sources["esfire30"]
        measured = esfire["measured_geometry"]
        self.assertEqual(119_498, esfire["records_observed"])
        self.assertEqual(6_196_709, measured["vertices_original"])
        self.assertEqual(119_498, measured["polygon"] + measured["multipolygon"])
        self.assertEqual(
            119_498, sum(measured["primary_autonomous_community_counts"].values())
        )
        self.assertEqual(1_342, measured["crosses_autonomous_communities"])
        self.assertEqual(2_364, measured["crosses_provinces"])
        self.assertTrue(sources["effis"]["role"].startswith("recent provisional"))
        self.assertTrue(
            any("Independent sources coexist" in row for row in inventory["non_equivalence"])
        )

    def test_official_perimeter_inventory_covers_all_territories_and_summary(self):
        inventory = load_json(PERIMETER_INVENTORY)
        territories = inventory["territories"]
        self.assertEqual(19, len(territories))
        self.assertEqual(19, len({row["code"] for row in territories}))
        counts = {status: 0 for status in inventory["classification"]}
        for territory in territories:
            counts[territory["status"]] += 1
            self.assertTrue(territory["access"].startswith("http"))
            self.assertTrue(territory["next_action"])
        for status, count in counts.items():
            self.assertEqual(count, inventory["summary"][status])
        ready = {row["name"] for row in territories if row["status"] == "A_READY"}
        self.assertEqual(
            {
                "Andalucía",
                "Cataluña/Catalunya",
                "Comunitat Valenciana",
                "Comunidad Foral de Navarra",
            },
            ready,
        )

    def test_d_not_found_is_explicitly_a_discovery_result_not_nonexistence(self):
        inventory = load_json(PERIMETER_INVENTORY)
        self.assertIn("not proof", inventory["classification"]["D_NOT_FOUND"])
        self.assertIn("not proof", inventory["summary"]["warning"])

    def test_temporal_blocks_and_egif_query_are_stable(self):
        module = load_audit_module()
        self.assertEqual("1985-1989", module.temporal_block(1985))
        self.assertEqual("1990-1999", module.temporal_block(1999))
        self.assertEqual("2020-2021", module.temporal_block(2021))
        url = module.egif_count_url(1968, 2025)
        self.assertTrue(url.startswith(module.EGIF_SEARCH_URL))
        self.assertIn("AD%3D1968", url)
        self.assertIn("AH%3D2025", url)

    def test_report_records_no_frontend_or_publication_work(self):
        report = (ROOT / "ES_1_NATIONAL_FEASIBILITY.md").read_text(encoding="utf-8")
        self.assertIn("modificado el visor del País Valencià", report)
        self.assertIn("no se ha publicado", report)
        self.assertIn("ES-2 — Modelo territorial nacional", report)


if __name__ == "__main__":
    unittest.main()
