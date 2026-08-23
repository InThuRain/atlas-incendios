import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest/egif/audit_spatial_references.py"
SPEC = importlib.util.spec_from_file_location("egif_spatial_audit", SCRIPT)
egif_spatial_audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = egif_spatial_audit
SPEC.loader.exec_module(egif_spatial_audit)


class EgifSpatialReferenceAuditTests(unittest.TestCase):
    def test_documented_periods_cover_the_six_historical_models(self):
        self.assertEqual(("historical_form_1", "1968-1971"), egif_spatial_audit.model_for_year(1968))
        self.assertEqual(("historical_form_2", "1972-1979"), egif_spatial_audit.model_for_year(1979))
        self.assertEqual(("historical_form_3", "1980-1982"), egif_spatial_audit.model_for_year(1982))
        self.assertEqual(("historical_form_4", "1983-1988"), egif_spatial_audit.model_for_year(1988))
        self.assertEqual(("historical_form_5", "1989"), egif_spatial_audit.model_for_year(1989))
        self.assertEqual(("historical_form_6", "1990-1992"), egif_spatial_audit.model_for_year(1992))

    def test_values_at_path_is_case_insensitive_and_traverses_relationship_lists(self):
        source = {
            "PIF_ANEXO": {
                "RelTeselaAfectadaPif": [
                    {"IdTesela": 12},
                    {"IdTesela": 34},
                ]
            }
        }
        self.assertEqual(
            ["12", "34"],
            egif_spatial_audit.values_at_path(
                source,
                "pif_anexo.RelTeselaAfectadaPif.idtesela",
            ),
        )

    def test_confidence_is_fail_closed_without_reproducible_geometry(self):
        self.assertEqual("NO_REFERENCE", egif_spatial_audit.confidence_for(None, None))
        self.assertEqual("B_PROBABLE", egif_spatial_audit.confidence_for("0704", "C11"))
        self.assertEqual("C_AMBIGUOUS", egif_spatial_audit.confidence_for("704", "C11"))
        self.assertEqual("C_AMBIGUOUS", egif_spatial_audit.confidence_for("0704", None))

    def test_versioned_audit_keeps_geometry_ineligible(self):
        audit = json.loads(
            (ROOT / "data/sources/egif_spatial_reference_audit.json").read_text(encoding="utf-8")
        )
        self.assertEqual(9_175, audit["scope"]["records"])
        self.assertEqual(0, audit["scope"]["geometry_created"])
        self.assertEqual(0, audit["classification_totals"]["A_CONFIRMED"])
        self.assertEqual(8_565, audit["classification_totals"]["B_PROBABLE"])
        self.assertEqual(610, audit["classification_totals"]["NO_REFERENCE"])
        self.assertEqual(0, audit["core_finding"]["future_representation_eligible_records"])

    def test_reference_pairs_are_complete_and_not_partial(self):
        audit = json.loads(
            (ROOT / "data/sources/egif_spatial_reference_audit.json").read_text(encoding="utf-8")
        )["reference_coverage"]
        self.assertEqual(8_565, audit["with_sheet_and_grid"])
        self.assertEqual(0, audit["sheet_only"])
        self.assertEqual(0, audit["grid_only"])
        self.assertEqual(270, audit["unique_sheet_grid_pairs"])

    def test_year_and_province_distributions_reconcile(self):
        audit = json.loads(
            (ROOT / "data/sources/egif_spatial_reference_audit.json").read_text(encoding="utf-8")
        )
        states = tuple(audit["classification_policy"])
        self.assertEqual(9_175, sum(row["records"] for row in audit["by_year"]))
        self.assertEqual(9_175, sum(row["records"] for row in audit["by_province"]))
        for group in (audit["by_year"], audit["by_province"], audit["by_documented_period"]):
            for row in group:
                self.assertEqual(row["records"], sum(row[state] for state in states))


if __name__ == "__main__":
    unittest.main()
