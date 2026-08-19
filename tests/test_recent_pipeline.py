import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "ingest"
    / "comunitat_valenciana"
    / "download_recent.py"
)
SPEC = importlib.util.spec_from_file_location("download_recent", SCRIPT)
recent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recent)


class RecentPipelineTests(unittest.TestCase):
    def test_sigif_table_preserves_duplicate_rows_and_order(self):
        header = "".join("<th>{}</th>".format(value) for value in recent.EXPECTED_SIGIF_COLUMNS)
        row = [
            "03/01/2025",
            "Estivella",
            "castillo beselga",
            "Negligencia",
            "0,0000",
            "0,0068",
            "0,0068",
            "14:59",
            "0:71",
            "Llamada particular",
            "1",
            "El Camp de Morvedre",
            "725719",
            "4399081",
        ]
        cells = "".join("<td>{}</td>".format(value) for value in row)
        document = (
            '<table id="estadisticasProvisionaleTable"><tr>{}</tr>'
            "<tr>{}</tr><tr>{}</tr></table>"
        ).format(header, cells, cells)
        columns, rows = recent.parse_sigif_table(
            document.encode("utf-8"), "estadisticasProvisionaleTable"
        )
        self.assertEqual(list(recent.EXPECTED_SIGIF_COLUMNS), columns)
        self.assertEqual([row, row], rows)

    def test_decimal_parser_keeps_spanish_public_values(self):
        self.assertEqual(183.4198, recent.parse_decimal("183,4198"))
        self.assertEqual(1000.5, recent.parse_decimal("1.000,5"))
        self.assertIsNone(recent.parse_decimal(""))

    def test_candidate_score_does_not_confirm_identity(self):
        record = {
            "municipality": "Ibi",
            "reported_total_area_ha": 183.4198,
            "derived_admin_at_point": {"province": "Alacant/Alicante"},
        }
        feature = {
            "properties": {
                "effis_commune": "Ibi",
                "effis_province": "Alicante/Alacant",
                "effis_area_ha": 185.0,
            }
        }
        (
            score,
            municipality_match,
            province_match,
            similarity,
            reasons_for,
            reasons_against,
        ) = recent.score_candidate(record, feature, 13.184, 0)
        self.assertEqual(90, score)
        self.assertTrue(municipality_match)
        self.assertTrue(province_match)
        self.assertGreater(similarity, 0.99)
        self.assertTrue(reasons_for)
        self.assertFalse(reasons_against)

    def test_effis_year_uses_firedate_without_relabeling_it(self):
        feature = {"properties": {"FIREDATE": "2026-06-25 13:40:00"}}
        self.assertEqual(2026, recent.effis_year(feature))


if __name__ == "__main__":
    unittest.main()
