import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/relations/esfire30/municipalities.py"
SPEC = importlib.util.spec_from_file_location("es4c2b3a1_municipal_relations", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class Cache:
    def __init__(self, rows):
        from shapely.strtree import STRtree
        self.rows = rows
        self.trees = {
            province_id: (STRtree([item["geometry"] for item in units]), units)
            for province_id, units in rows.items()
        }

    def tree(self, province_id):
        return self.trees[province_id]


class ES4C2B3A1MunicipalRelationTests(unittest.TestCase):
    def setUp(self):
        from shapely.geometry import box

        self.box = box
        self.cache = Cache({
            "ES:PROV:03": [
                {"municipality_id": "ES:MUN:03001", "province_id": "ES:PROV:03", "autonomous_community_id": "ES:CCAA:10", "geometry": box(0, 0, 5, 10)},
                {"municipality_id": "ES:MUN:03002", "province_id": "ES:PROV:03", "autonomous_community_id": "ES:CCAA:10", "geometry": box(5, 0, 10, 10)},
            ],
            "ES:PROV:46": [
                {"municipality_id": "ES:MUN:46001", "province_id": "ES:PROV:46", "autonomous_community_id": "ES:CCAA:10", "geometry": box(10, 0, 15, 10)},
            ],
            "ES:PROV:02": [
                {"municipality_id": "ES:MUN:02001", "province_id": "ES:PROV:02", "autonomous_community_id": "ES:CCAA:08", "geometry": box(15, 0, 20, 10)},
            ],
        })

    def test_exact_current_crosswalk_has_all_8132_canonical_municipalities(self):
        by_id, by_province = MODULE.load_catalog()
        self.assertEqual(8_132, len(by_id))
        self.assertEqual(8_130, sum(len(rows) for rows in by_province.values()))
        self.assertEqual(2, sum(row["province_id"] is None for row in by_id.values()))  # Ceuta/Melilla; no ESFire30 coverage.
        self.assertEqual("ES:PROV:03", by_id["ES:MUN:03065"]["province_id"])
        self.assertNotIn("ES:MUN:53001", by_id)

    def test_prefilter_preserves_all_multi_province_positive_relations(self):
        geometry = self.box(4, 1, 18, 9)
        positives, touches, candidates, spatial = MODULE.relation_rows(
            MODULE.load_previous(), "esfire30:v1:2014:930", geometry,
            {"ES:PROV:03", "ES:PROV:46", "ES:PROV:02"},
            {"ES:CCAA:10", "ES:CCAA:08"}, self.cache,
        )
        self.assertEqual([], touches)
        self.assertEqual(4, candidates)
        self.assertEqual(4, spatial)
        self.assertEqual({"ES:MUN:03001", "ES:MUN:03002", "ES:MUN:46001", "ES:MUN:02001"}, {row["municipality_id"] for row in positives})
        self.assertTrue(all(row["intersection_area_m2"] > 0 for row in positives))
        self.assertTrue(all(row["parent_province_id"] in {"ES:PROV:03", "ES:PROV:46", "ES:PROV:02"} for row in positives))
        schema = json.loads((ROOT / "schemas/national/v1/atlas-contracts.schema.json").read_text(encoding="utf-8"))
        required_relation = schema["$defs"]["territoryRelation"]["required"]
        required_provenance = schema["$defs"]["provenance"]["required"]
        for row in positives:
            self.assertTrue(all(key in row for key in required_relation))
            self.assertTrue(all(key in row["provenance"] for key in required_provenance))

    def test_boundary_touches_are_audit_only_and_output_is_deterministic(self):
        previous = MODULE.load_previous()
        geometry = self.box(20, 1, 22, 2)
        positives, touches, _, _ = MODULE.relation_rows(previous, "esfire30:v1:2000:1", geometry, {"ES:PROV:02"}, {"ES:CCAA:08"}, self.cache)
        self.assertEqual([], positives)
        self.assertEqual(1, len(touches))
        self.assertEqual("boundary_touch_only", touches[0]["intersection_class"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            entry = {"relations_path": str(output / "relations-2000.jsonl"), "boundary_touches_path": str(output / "boundary-touches-2000.jsonl")}
            (output / "relations-2000.jsonl").write_text("", encoding="utf-8")
            (output / "boundary-touches-2000.jsonl").write_text("", encoding="utf-8")
            entry.update({"relations_sha256": MODULE.sha256(output / "relations-2000.jsonl"), "boundary_touches_sha256": MODULE.sha256(output / "boundary-touches-2000.jsonl"), "relation_count": 0, "boundary_touch_count": 0})
            self.assertEqual((True, "ok"), MODULE.verify_block(entry))
        self.assertEqual("esfire30:v1:1995:7", previous.geometry_id(1995, 7))

    def test_positive_sliver_is_not_rounded_to_zero_in_output(self):
        positives, touches, _, _ = MODULE.relation_rows(
            MODULE.load_previous(), "esfire30:v1:1990:1901", self.box(9.999999, 1, 10.000001, 2),
            {"ES:PROV:03"}, {"ES:CCAA:10"}, self.cache,
        )
        self.assertEqual([], touches)
        self.assertEqual(1, len(positives))
        self.assertTrue(all(row["intersection_area_m2"] > 0 for row in positives))
        self.assertTrue(any(row["intersection_area_m2"] < 0.001 for row in positives))

    def test_hierarchy_inconsistency_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Jerarquía"):
            MODULE.relation_rows(
                MODULE.load_previous(), "esfire30:v1:2011:88", self.box(1, 1, 2, 2),
                {"ES:PROV:03"}, {"ES:CCAA:08"}, self.cache,
            )

    def test_manifest_totals_keep_open_municipal_cardinality(self):
        result = MODULE.totals([
            {"year": 1985, "status": "complete", "geometry_count": 2, "relation_count": 8, "boundary_touch_count": 1, "zero_relation_count": 0, "max_municipalities": 6, "bytes": 91},
            {"year": 1986, "status": "failed", "geometry_count": 0, "relation_count": 0, "boundary_touch_count": 0, "zero_relation_count": 0, "max_municipalities": 0, "bytes": 0},
        ], [1985, 1986])
        self.assertEqual(2, result["configured_blocks"])
        self.assertEqual(1, result["complete_blocks"])
        self.assertEqual(6, result["max_municipalities"])


if __name__ == "__main__":
    unittest.main()
