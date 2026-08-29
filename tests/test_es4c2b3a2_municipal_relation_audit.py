import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/esfire30/es4c2b3a2_municipal_relations.py"
SPEC = importlib.util.spec_from_file_location("es4c2b3a2_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ES4C2B3A2MunicipalAuditTests(unittest.TestCase):
    def test_geometry_cardinality_keeps_zero_and_open_upper_bucket(self):
        all_geometry = {"g0", "g1", "g2", "g3", "g6", "g19", "g20"}
        values = {
            "g1": {"m1"}, "g2": {"m1", "m2"}, "g3": {"m1", "m2", "m3"},
            "g6": {f"m{x}" for x in range(6)}, "g19": {f"m{x}" for x in range(19)},
            "g20": {f"m{x}" for x in range(20)},
        }
        report = MODULE.geometry_cardinality(values, all_geometry)
        self.assertEqual(1, report["buckets"]["0"])
        self.assertEqual(1, report["buckets"]["6–10"])
        self.assertEqual(1, report["buckets"]["16–19"])
        self.assertEqual(1, report["buckets"]["20+"])
        self.assertEqual(20, report["maximum"])

    def test_inverse_cardinality_and_slivers_are_deterministic(self):
        counts = {"m0": set(), "m1": {"g1"}, "m2": {f"g{x}" for x in range(51)}, "m3": {f"g{x}" for x in range(2600)}}
        report = MODULE.municipality_cardinality(counts, counts)
        self.assertEqual(1, report["buckets"]["0"])
        self.assertEqual(1, report["buckets"]["51–100"])
        self.assertEqual(1, report["buckets"]["2501–5000"])
        self.assertEqual(2600, report["maximum"])
        self.assertEqual("<1e-6", MODULE.sliver_bucket(1e-8))
        self.assertEqual(">=1e-2", MODULE.sliver_bucket(.01))

    def test_compact_forward_inverse_and_shards_are_stable(self):
        forward = {"g2": {"ES:MUN:00002", "ES:MUN:00001"}, "g1": {"ES:MUN:00001"}}
        inverse = {"ES:MUN:00001": {"g2", "g1"}, "ES:MUN:00002": {"g2"}}
        catalog = {
            "ES:MUN:00001": {"province_id": "ES:PROV:01", "autonomous_community_id": "ES:CCAA:01"},
            "ES:MUN:00002": {"province_id": "ES:PROV:01", "autonomous_community_id": "ES:CCAA:01"},
        }
        first = MODULE.index_sizes(forward, inverse, catalog)
        second = MODULE.index_sizes(forward, inverse, catalog)
        self.assertEqual(first, second)
        self.assertEqual(1, first["inverse_by_province"]["asset_count"])
        self.assertEqual("ES:MUN:00001", first["inverse_national"]["largest_entry"]["municipality_id"])

    def test_positive_non_municipal_units_are_not_municipality_ids(self):
        # The audit never receives 53xxx BDLJE units in the canonical
        # municipality catalogue; they can only be evidence for zero relations.
        municipalities, _, _ = MODULE.load_catalog()
        self.assertEqual(8_132, len(municipalities))
        self.assertFalse(any(identifier.startswith("ES:MUN:53") for identifier in municipalities))


if __name__ == "__main__":
    unittest.main()
