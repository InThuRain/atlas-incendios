import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/esfire30/es4c2b1b_territory_relations.py"
SPEC = importlib.util.spec_from_file_location("es4c2b1b_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def relation(geometry_id, territory_id, level, fraction=1.0):
    return {
        "geometry_id": geometry_id, "territory_id": territory_id,
        "territory_type": "province" if level == "province" else "autonomous_community",
        "territory_level": level, "relation_type": "spatial_intersection",
        "intersection_class": "positive_area_intersection", "intersection_area_m2": 100,
        "intersection_fraction": fraction,
    }


class ES4C2B1BAuditTests(unittest.TestCase):
    def setUp(self):
        self.territories = {
            "ES:CCAA:01": {"territory_id": "ES:CCAA:01", "official_code": "01", "official_name": "Uno", "territory_type": "autonomous_community"},
            "ES:CCAA:02": {"territory_id": "ES:CCAA:02", "official_code": "02", "official_name": "Dos", "territory_type": "autonomous_community"},
            "ES:PROV:01": {"territory_id": "ES:PROV:01", "official_code": "01", "official_name": "P uno", "territory_type": "province"},
            "ES:PROV:02": {"territory_id": "ES:PROV:02", "official_code": "02", "official_name": "P dos", "territory_type": "province"},
        }
        self.parents = {"ES:PROV:01": "ES:CCAA:01", "ES:PROV:02": "ES:CCAA:02"}
        self.rows = [
            relation("esfire30:v1:2000:0", "ES:CCAA:01", "autonomous_community"),
            relation("esfire30:v1:2000:0", "ES:PROV:01", "province"),
            relation("esfire30:v1:2000:1", "ES:CCAA:01", "autonomous_community", .999999),
            relation("esfire30:v1:2000:1", "ES:CCAA:02", "autonomous_community", .000001),
            relation("esfire30:v1:2000:1", "ES:PROV:01", "province", .999999),
            relation("esfire30:v1:2000:1", "ES:PROV:02", "province", .000001),
            relation("esfire30:v1:2000:2", "ES:CCAA:02", "autonomous_community"),
            relation("esfire30:v1:2000:2", "ES:PROV:02", "province"),
        ]
        self.manifest = {"input": {"geometry_snapshot": {"records_expected": 3}}, "totals": {"relation_count": len(self.rows)}}
        self.es3 = {"territory_relations": {"crosses_ccaa": 1, "crosses_province": 1, "without_ccaa": 0, "without_province": 0}}

    def test_cardinality_slivers_hierarchy_and_excess(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"; path.write_text("\n".join(json.dumps(row) for row in self.rows) + "\n")
            report = MODULE.audit(self.manifest, self.territories, self.parents, self.es3, self.rows, [], [path], [])
        self.assertEqual(2, report["baseline"]["excess_relations"])
        self.assertEqual({"0": 0, "1": 2, "2": 1, "3": 0, "4+": 0, "multi_geometry_count": 1, "maximum": 2}, report["cardinality"]["ccaa"])
        self.assertEqual(0, report["hierarchy"]["inconsistent"])
        self.assertEqual(2, report["slivers"]["buckets"]["[1e-06,1e-05)"] + report["slivers"]["buckets"]["[0,1e-06)"])
        self.assertTrue(report["integrity"]["valid"])

    def test_duplicate_and_hierarchy_anomalies_are_not_silenced(self):
        rows = self.rows + [dict(self.rows[0]), relation("esfire30:v1:2000:2", "ES:PROV:01", "province", .1)]
        manifest = {"input": {"geometry_snapshot": {"records_expected": 3}}, "totals": {"relation_count": len(rows)}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"; path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            report = MODULE.audit(manifest, self.territories, self.parents, self.es3, rows, [], [path], [])
        self.assertEqual(1, report["relations"]["duplicate_logical_keys"])
        self.assertEqual(1, report["hierarchy"]["inconsistent"])
        self.assertFalse(report["integrity"]["valid"])

    def test_compact_encodings_are_deterministic(self):
        ccaa = {"esfire30:v1:2000:0": {"ES:CCAA:01"}}
        province = {"esfire30:v1:2000:0": {"ES:PROV:01"}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"; path.write_text("{}\n")
            first = MODULE.compact_representations(ccaa, province, [path], [], 1)
            second = MODULE.compact_representations(ccaa, province, [path], [], 1)
        self.assertEqual(first, second)
        self.assertIn("D_dictionary_encoded_territory_ids", first)


if __name__ == "__main__":
    unittest.main()
