import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/relations/esfire30/territories.py"
SPEC = importlib.util.spec_from_file_location("es4c2b_relations", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ES4C2B1ATerritoryRelationTests(unittest.TestCase):
    def setUp(self):
        from shapely.geometry import box
        from shapely.strtree import STRtree

        self.box = box
        ccaa = [
            {"territory_id": "ES:CCAA:10", "territory_type": "autonomous_community", "geometry": box(0, 0, 10, 10)},
            {"territory_id": "ES:CCAA:08", "territory_type": "autonomous_community", "geometry": box(10, 0, 20, 10)},
        ]
        provinces = [
            {"territory_id": "ES:PROV:03", "territory_type": "province", "parent_id": "ES:CCAA:10", "geometry": box(0, 0, 5, 10)},
            {"territory_id": "ES:PROV:46", "territory_type": "province", "parent_id": "ES:CCAA:10", "geometry": box(5, 0, 10, 10)},
            {"territory_id": "ES:PROV:02", "territory_type": "province", "parent_id": "ES:CCAA:08", "geometry": box(10, 0, 20, 10)},
        ]
        self.trees = {"autonomous_community": (STRtree([item["geometry"] for item in ccaa]), ccaa), "province": (STRtree([item["geometry"] for item in provinces]), provinces)}
        self.territories = {item["territory_id"]: item for item in ccaa + provinces}

    def test_positive_nm_intersections_keep_area_fraction_and_stable_ids(self):
        geometry = self.box(4, 1, 12, 9)
        first, touches = MODULE.relation_rows("esfire30:v1:2014:930", geometry, self.trees, year=2014)
        second, _ = MODULE.relation_rows("esfire30:v1:2014:930", geometry, self.trees, year=2014)
        self.assertEqual([], touches)
        self.assertEqual([row["territory_relation_id"] for row in first], [row["territory_relation_id"] for row in second])
        self.assertEqual({"ES:CCAA:10", "ES:CCAA:08", "ES:PROV:03", "ES:PROV:46", "ES:PROV:02"}, {row["territory_id"] for row in first})
        self.assertTrue(all(row["intersection_area_m2"] > 0 for row in first))
        self.assertTrue(all(row["relation_type"] == "spatial_intersection" for row in first))
        self.assertEqual(len(first), len({(row["geometry_id"], row["territory_id"]) for row in first}))
        schema = json.loads((ROOT / "schemas/national/v1/atlas-contracts.schema.json").read_text(encoding="utf-8"))
        required_relation = schema["$defs"]["territoryRelation"]["required"]
        required_provenance = schema["$defs"]["provenance"]["required"]
        for row in first:
            self.assertTrue(all(key in row for key in required_relation))
            self.assertTrue(all(key in row["provenance"] for key in required_provenance))

    def test_boundary_touch_is_audit_not_positive_relation(self):
        geometry = self.box(20, 1, 22, 2)
        positives, touches = MODULE.relation_rows("esfire30:v1:2000:1", geometry, self.trees, year=2000)
        self.assertEqual([], positives)
        self.assertEqual(2, len(touches))  # CCAA y su provincia, ambas solo contactan por borde.
        self.assertTrue(all(row["intersection_class"] == "boundary_touch_only" for row in touches))
        self.assertTrue(all(row["intersection_area_m2"] == 0 for row in touches))

    def test_year_output_is_deterministic_and_checkable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            identity = lambda value: value
            first = MODULE.write_year(output, 1995, [(2, self.box(4, 1, 12, 9))], self.trees, self.territories, identity)
            self.assertEqual(5, first["relation_count"])
            self.assertEqual(0, first["hierarchy_inconsistency_count"])
            self.assertEqual((True, "ok"), MODULE.verify_block(first))
            first_bytes = (output / "relations-1995.jsonl").read_bytes()
            second = MODULE.write_year(output, 1995, [(2, self.box(4, 1, 12, 9))], self.trees, self.territories, identity)
            self.assertEqual(first["relations_sha256"], second["relations_sha256"])
            self.assertEqual(first_bytes, (output / "relations-1995.jsonl").read_bytes())

    def test_geometry_id_and_sample_parser_are_stable(self):
        self.assertEqual("esfire30:v1:1995:7", MODULE.geometry_id(1995, 7))
        self.assertEqual((1995, 7), MODULE.parse_sample("esfire30:v1:1995:7"))
        self.assertEqual(MODULE.geometry_ids_checksum(1995, {7, 9}), MODULE.geometry_ids_checksum(1995, {9, 7}))
        self.assertNotEqual(MODULE.geometry_ids_checksum(1995, {7}), MODULE.geometry_ids_checksum(1995, {9}))
        with self.assertRaises(Exception):
            MODULE.parse_sample("esfire30:v1:1970:7")

    def test_resume_totals_are_recomputed_from_completed_blocks(self):
        totals = MODULE.totals_for([
            {"year": 1995, "status": "complete", "geometry_count": 2, "relation_count": 5, "boundary_touch_count": 1, "bytes": 99},
            {"year": 1996, "status": "failed", "geometry_count": 0, "relation_count": 0, "boundary_touch_count": 0, "bytes": 0},
        ], {1995, 1996})
        self.assertEqual(2, totals["configured_blocks"])
        self.assertEqual(1, totals["complete_blocks"])
        self.assertEqual(2, totals["geometry_count"])
        self.assertEqual(5, totals["relation_count"])


if __name__ == "__main__":
    unittest.main()
