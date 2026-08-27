import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/relations/egif/territories.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b3_territories", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MAPPER = load_module()
SNAPSHOT = ROOT / "data/territories/spain/territories-2026-01-01.json"
MANIFEST = ROOT / "data/sources/spain_territory_snapshot_manifest.json"
CROSSWALK = json.loads((ROOT / "config/egif-territory-crosswalk-v1.json").read_text())


def record(community, province, municipality, name=None):
    return {
        "record_id": "egif-record:fixture",
        "source_record_id": "fixture",
        "year": 1992,
        "geometry": None,
        "geometry_ids": [],
        "source_declared_location": {"community_code": community, "province_code": province, "municipality_code": municipality, "municipality_name": name},
        "provenance": {"retrieved_at": "2026-08-27T00:00:00Z"},
    }


class ES4B3TerritoryMapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.territories, cls.by_ccaa, cls.by_province, cls.by_municipality, _ = MAPPER.load_territories(SNAPSHOT, MANIFEST)

    def resolve(self, item, historical=None):
        return MAPPER.resolve_record(item, territories=self.territories, by_ccaa=self.by_ccaa, by_province=self.by_province, by_municipality=self.by_municipality, crosswalk=CROSSWALK, historical=historical or {})

    def by_level(self, item):
        return {row["level"]: row for row in item["mappings"]}

    def test_valencian_code_mapping_preserves_source_and_resolves_elx_and_herbers(self):
        elx = self.by_level(self.resolve(record("9", "3", "65")))
        self.assertEqual("ES:CCAA:10", elx["autonomous_community"]["territory_id"])
        self.assertEqual("ES:PROV:03", elx["province"]["territory_id"])
        self.assertEqual("ES:MUN:03065", elx["municipality"]["territory_id"])
        self.assertEqual("65", elx["municipality"]["source_value"])
        herbers = self.by_level(self.resolve(record("9", "12", "68")))
        self.assertEqual("ES:MUN:12068", herbers["municipality"]["territory_id"])

    def test_ceuta_and_melilla_stay_autonomous_cities_not_provinces(self):
        ceuta = self.by_level(self.resolve(record("18", "51", "1")))
        self.assertEqual("ES:CCAA:18", ceuta["autonomous_community"]["territory_id"])
        self.assertEqual("ES:CCAA:18", ceuta["province"]["territory_id"])
        self.assertEqual("ES:MUN:51001", ceuta["municipality"]["territory_id"])
        # No source-community code for Melilla is invented: the province-equivalent
        # path remains structurally valid while the unknown source code is explicit.
        melilla = self.by_level(self.resolve(record("19", "52", "1")))
        self.assertEqual("invalid_source_value", melilla["autonomous_community"]["resolution_status"])
        self.assertEqual("ES:CCAA:19", melilla["province"]["territory_id"])
        self.assertEqual("ES:MUN:52001", melilla["municipality"]["territory_id"])

    def test_historical_candidate_and_unresolved_values_are_not_auto_promoted(self):
        historical = {("03", "999"): {"territory_id": "ES:MUN:03065", "evidence": "fixture official historical mapping"}}
        mapped = self.by_level(self.resolve(record("9", "3", "999"), historical))
        self.assertEqual("historical_resolved", mapped["municipality"]["resolution_status"])
        candidate = self.by_level(self.resolve(record("9", "3", "999", "Elx/Elche")))
        self.assertEqual("candidate", candidate["municipality"]["resolution_status"])
        self.assertEqual(["ES:MUN:03065"], candidate["municipality"]["candidate_territory_ids"])
        unresolved = self.by_level(self.resolve(record("9", "3", "999")))
        self.assertEqual("unresolved", unresolved["municipality"]["resolution_status"])

    def test_invalid_codes_and_source_null_remain_explicit(self):
        mapped = self.by_level(self.resolve(record("99", "3", "0")))
        self.assertEqual("invalid_source_value", mapped["autonomous_community"]["resolution_status"])
        self.assertEqual("unresolved", mapped["municipality"]["resolution_status"])

    def test_strict_relations_have_targets_and_never_change_egif_geometry(self):
        source = record("9", "3", "65")
        audit = self.resolve(source)
        relations = list(MAPPER.strict_relations(audit))
        self.assertEqual(6, len(relations))
        self.assertEqual({"source_declared", "canonical_mapping"}, {item["relation_type"] for item in relations})
        self.assertTrue(all(item["territory_id"].startswith("ES:") for item in relations))
        self.assertIsNone(source["geometry"])
        self.assertEqual([], source["geometry_ids"])


if __name__ == "__main__":
    unittest.main()
