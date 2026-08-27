import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/egif/es4b5a_web_derivative_design.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b5a_web_derivative_design", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


WEB = load_module()


def fixture_record():
    return {
        "record_id": "egif-record:1995030065", "source_id": "egif", "entity_type": "administrative_record",
        "year": 1995, "geometry": None, "geometry_ids": [], "reported_forest_area_ha": 500.0,
        "reported_total_area_ha": 540.0, "reported_wooded_area_ha": 300.0, "reported_nonwooded_area_ha": 200.0,
        "is_gif_forest_ge_500_ha": True, "cause_raw": "211", "identity_status": "source_record_only",
        "episode_identity_status": "unresolved", "source_record_id": "1995030065", "source_database_id": "fixture-db",
        "detection_date": "1995-08-01T12:00:00", "extinction_date": "1995-08-02T12:00:00", "form_model": "post_1992_export_schema_not_yet_periodized",
        "temporal_validity": {"coverage_status": "systematic"},
        "source_declared_location": {"municipality_name": "Elx", "paraje": "fixture"},
    }


def fixture_audit(municipality="ES:MUN:03065"):
    return {"record_id": "egif-record:1995030065", "mappings": [
        {"level": "autonomous_community", "resolution_status": "resolved", "territory_id": "ES:CCAA:10"},
        {"level": "province", "resolution_status": "resolved", "territory_id": "ES:PROV:03"},
        {"level": "municipality", "resolution_status": "resolved" if municipality else "unresolved", "territory_id": municipality},
    ]}


class ES4B5AWebDerivativeTests(unittest.TestCase):
    def test_initial_record_preserves_id_and_null_canonical_cause(self):
        row = WEB.initial_record(fixture_record(), fixture_audit())
        self.assertEqual("egif-record:1995030065", row["record_id"])
        self.assertEqual("ES:CCAA:10", row["autonomous_community_id"])
        self.assertEqual("ES:MUN:03065", row["municipality_id"])
        self.assertTrue(row["is_gif_forest_ge_500_ha"])
        self.assertEqual("211", row["cause_source_code"])
        self.assertIsNone(row["canonical_cause"])

    def test_unresolved_municipality_stays_null_and_ccinif_is_absent(self):
        row = WEB.initial_record(fixture_record(), fixture_audit(None), profile="public")
        self.assertIsNone(row["municipality_id"])
        self.assertNotIn("spatial_reference_id", row)
        self.assertNotIn("geometry", row)

    def test_missing_forest_area_keeps_gif_unknown(self):
        item = fixture_record()
        item["reported_forest_area_ha"] = None
        item["is_gif_forest_ge_500_ha"] = False
        self.assertIsNone(WEB.initial_record(item, fixture_audit())["is_gif_forest_ge_500_ha"])

    def test_serializations_are_deterministic_and_round_trip(self):
        rows = [WEB.initial_record(fixture_record(), fixture_audit())]
        for builder, parser, indexer in ((WEB.array_payload, WEB.parse_array, WEB.lookup_from_array), (WEB.jsonl_payload, WEB.parse_jsonl, WEB.lookup_from_rows), (WEB.columnar_payload, WEB.parse_columnar, WEB.lookup_from_columnar)):
            first, second = builder(rows), builder(rows)
            self.assertEqual(first, second)
            decoded = parser(first)
            self.assertEqual(indexer(decoded), {"egif-record:1995030065": 0})

    def test_detail_keeps_selection_fields_out_of_initial_payload(self):
        record = fixture_record()
        initial = WEB.initial_record(record, fixture_audit())
        detail = WEB.detail_record(record)
        self.assertNotIn("detection_date", initial)
        self.assertEqual("1995-08-01T12:00:00", detail["detection_date"])
        self.assertNotIn("original_attributes", detail)


if __name__ == "__main__":
    unittest.main()
