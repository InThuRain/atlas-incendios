import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(relative_path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTRACTS = load_module("scripts/contracts/validate_national_contracts.py", "es2_contracts")
ADAPTER = load_module("scripts/contracts/adapt_gva_catalog.py", "es2_gva_adapter")


def load(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class NationalDataModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load("config/sources-spain.json")
        cls.snapshot = load("data/territories/spain/territories-2026-01-01.json")
        cls.manifest = load("data/sources/spain_territory_snapshot_manifest.json")
        cls.gva = load("tests/fixtures/es2/valencian_country.json")
        cls.navarra = load("tests/fixtures/es2/navarra.json")
        cls.canarias = load("tests/fixtures/es2/canary_islands.json")

    def test_all_schema_documents_are_valid_json(self):
        paths = sorted((ROOT / "schemas/national/v1").glob("*.json"))
        self.assertGreaterEqual(len(paths), 4)
        for path in paths:
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_catalog_and_all_control_fixtures_validate(self):
        CONTRACTS.validate_source_catalog(self.catalog)
        for fixture in (self.gva, self.navarra, self.canarias):
            CONTRACTS.validate_fixture(fixture, self.catalog)

    def test_official_territory_snapshot_counts_hierarchy_and_checksum(self):
        CONTRACTS.validate_territory_snapshot(self.snapshot, self.manifest)
        self.assertEqual(self.manifest["counts"], {
            "autonomous_cities": 2,
            "autonomous_communities": 17,
            "country": 1,
            "municipalities": 8132,
            "province_equivalent_codes_for_autonomous_cities": 2,
            "provinces": 50,
            "statistical_codes_at_province_level": 52,
            "total_territories": 8202,
        })
        payload = (ROOT / self.manifest["output"]["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), self.manifest["output"]["sha256"])
        self.assertFalse(self.snapshot["geometry_embedded"])

    def test_territory_codes_are_ids_and_names_are_not_identity(self):
        by_id = {item["territory_id"]: item for item in self.snapshot["territories"]}
        self.assertEqual(by_id["ES:MUN:03065"]["official_name"], "Elx/Elche")
        self.assertEqual(by_id["ES:MUN:03065"]["parent_id"], "ES:PROV:03")
        self.assertEqual(by_id["ES:PROV:03"]["parent_id"], "ES:CCAA:10")

    def test_ceuta_and_melilla_are_autonomous_cities_not_provinces(self):
        by_id = {item["territory_id"]: item for item in self.snapshot["territories"]}
        for ccaa_code, equivalent_code, municipality_code in (("18", "51", "51001"), ("19", "52", "52001")):
            city = by_id[f"ES:CCAA:{ccaa_code}"]
            self.assertEqual(city["territory_type"], "autonomous_city")
            self.assertEqual(city["province_equivalent_code"], equivalent_code)
            self.assertNotIn(f"ES:PROV:{equivalent_code}", by_id)
            municipality = by_id[f"ES:MUN:{municipality_code}"]
            self.assertEqual(municipality["parent_id"], city["territory_id"])
            self.assertEqual(municipality["province_equivalent_code"], equivalent_code)

    def test_valencian_fixture_reconciles_published_counts_and_legacy_ids(self):
        self.assertEqual(self.gva["expected_reconciliation"], {
            "icv_records": 13738,
            "icv_geometries": 13739,
            "egif_records_1968_1992": 9175,
            "esfire30_geometries_1985_1992": 710,
            "legacy_permalink_version": 1,
        })
        ids = {item["record_id"] for item in self.gva["source_records"]}
        self.assertIn("gva:pif-cv:2024AL0005", ids)
        self.assertIn("egif-record:1968030045", ids)
        geometry_ids = {item["geometry_id"] for item in self.gva["fire_geometries"]}
        self.assertIn("gva:geometry:2024:32:1", geometry_ids)
        compatibility = load("config/compatibility-gva-v1.json")
        self.assertEqual(compatibility["permalink"]["current_version"], 1)
        self.assertIn("public-data-v5", compatibility["immutable_interfaces"])

    def test_gva_catalog_adapter_preserves_profile_order_and_ids(self):
        legacy = load("config/sources-gva.json")
        compatibility = load("config/compatibility-gva-v1.json")
        profiles = ADAPTER.adapt_profiles(legacy, self.catalog, compatibility)
        self.assertEqual(profiles["pilot_public"], ["egif", "esfire30", "gva_icv", "effis"])
        self.assertEqual(profiles["pilot_development"], ["egif", "esfire30", "gva_icv", "gva_sigif", "effis"])
        ADAPTER.validate_id_policies(compatibility)

    def test_historical_reference_is_not_fire_geometry_and_can_be_multipart(self):
        reference = self.canarias["historical_spatial_references"][0]
        self.assertEqual(reference["geometry_status"], "not_fire_geometry")
        self.assertEqual(reference["spatial_semantics"], "historical_location_reference")
        self.assertEqual(reference["interpretation_status"], "ambiguous")
        self.assertIsNone(reference["sheet_id"])
        self.assertEqual(len(reference["geometry_parts"]), 2)
        record = self.canarias["source_records"][0]
        self.assertEqual(record["geometry_ids"], [])
        self.assertEqual(record["spatial_reference_id"], reference["spatial_reference_id"])

    def test_navarra_autonomous_source_coexists_without_becoming_publishable(self):
        source = self.catalog["sources"]["navarra_official"]
        self.assertEqual(source["geometry_semantics"], ["official_fire_perimeter"])
        self.assertFalse(source["publishable"])
        self.assertEqual(source["publication_status"], "design_only")
        self.assertEqual(self.navarra["candidate_links"][0]["status"], "candidate")

    def test_publication_guard_accepts_pilot_and_blocks_sigif_and_ccinif(self):
        result = CONTRACTS.validate_publication(self.catalog, self.catalog["profiles"]["pilot_public"])
        self.assertTrue(result["all_included_sources_publishable"])
        for blocked in ("gva_sigif", "ccinif_grid", "navarra_official"):
            with self.assertRaises(CONTRACTS.ContractError):
                CONTRACTS.validate_publication(self.catalog, ["egif", blocked])

    def test_publication_guard_checks_asset_license_attribution_and_provenance(self):
        good = {
            "asset_id": "fixture:asset:egif",
            "source_id": "egif",
            "profile": "pilot_public",
            "publishable": True,
            "license_status": "confirmed",
            "attribution": "Origen de los datos: MITECO.",
            "provenance": {"snapshot": "fixture"},
            "url": "data/fixture.json",
            "sha256": "0" * 64,
            "byte_size": 1,
        }
        CONTRACTS.validate_publication(self.catalog, ["egif"], [good])
        for key, value in (("publishable", False), ("attribution", None), ("provenance", {}), ("sha256", "bad")):
            bad = copy.deepcopy(good)
            bad[key] = value
            with self.assertRaises(CONTRACTS.ContractError):
                CONTRACTS.validate_publication(self.catalog, ["egif"], [bad])

    def test_source_declared_and_spatial_relations_are_not_equivalent(self):
        fixture = copy.deepcopy(self.gva)
        fixture["territory_relations"].append({
            "territory_relation_id": "tr:gva2024al0005:elx-spatial",
            "subject_id": "gva:geometry:2024:32:1",
            "territory_id": "ES:MUN:03065",
            "relation_type": "spatial_intersection",
            "mapping_status": "confirmed",
            "qa_status": "municipality_mismatch",
            "provenance": {"source_id": "gva_icv", "source_record_id": "2024AL0005", "retrieved_at": "2026-08-26T00:00:00Z", "transformations": []},
        })
        CONTRACTS.validate_fixture(fixture, self.catalog)
        types = {item["relation_type"] for item in fixture["territory_relations"]}
        self.assertIn("source_declared", types)
        self.assertIn("spatial_intersection", types)

    def test_multiterritorial_geometry_uses_relations_without_geometry_duplication(self):
        fixture = copy.deepcopy(self.gva)
        fixture["territories"].append({
            "territory_id": "ES:PROV:46", "territory_type": "province", "official_code": "46", "official_name": "Valencia/València", "parent_id": "ES:CCAA:10", "aliases": [], "valid_from": "2026-01-01", "valid_to": None, "predecessor_ids": [], "successor_ids": [],
            "provenance": {"source_id": "ine_rel_2026_01_01", "source_record_id": "46", "retrieved_at": "2026-08-26T12:00:00Z", "transformations": []},
        })
        fixture["territory_relations"].append({
            "territory_relation_id": "tr:gva2024al0005:valencia",
            "subject_id": "gva:geometry:2024:32:1", "territory_id": "ES:PROV:46", "relation_type": "spatial_intersection", "mapping_status": "confirmed", "qa_status": "province_mismatch",
            "provenance": {"source_id": "gva_icv", "source_record_id": "2024AL0005", "retrieved_at": "2026-08-26T00:00:00Z", "transformations": []},
        })
        fixture["fire_geometries"][0]["territory_relation_ids"].append("tr:gva2024al0005:valencia")
        CONTRACTS.validate_fixture(fixture, self.catalog)
        self.assertEqual(len([item for item in fixture["fire_geometries"] if item["geometry_id"] == "gva:geometry:2024:32:1"]), 1)

    def test_duplicate_territory_relation_fails_closed(self):
        fixture = copy.deepcopy(self.gva)
        duplicate = copy.deepcopy(fixture["territory_relations"][0])
        duplicate["territory_relation_id"] = "tr:duplicate"
        fixture["territory_relations"].append(duplicate)
        with self.assertRaises(CONTRACTS.ContractError):
            CONTRACTS.validate_fixture(fixture, self.catalog)

    def test_missing_geometry_reference_fails(self):
        fixture = copy.deepcopy(self.gva)
        fixture["source_records"][0]["geometry_ids"] = ["gva:geometry:missing"]
        with self.assertRaises(CONTRACTS.ContractError):
            CONTRACTS.validate_fixture(fixture, self.catalog)

    def test_temporal_municipality_fields_preserve_history_without_inference(self):
        municipality = next(item for item in self.gva["territories"] if item["territory_type"] == "municipality")
        self.assertIn("valid_from", municipality)
        self.assertIn("valid_to", municipality)
        self.assertIn("predecessor_ids", municipality)
        self.assertIn("successor_ids", municipality)
        self.assertEqual(municipality["predecessor_ids"], [])

    def test_provisional_source_is_explicit_not_zero_or_final(self):
        sigif = self.catalog["sources"]["gva_sigif"]
        self.assertEqual(sigif["temporal_coverage"][0]["completeness_status"], "provisional")
        self.assertEqual(sigif["update_policy"], "live_provisional")
        self.assertFalse(sigif["publishable"])

    def test_cause_mapping_contract_distinguishes_documented_candidate_unmapped(self):
        schema = load("schemas/national/v1/atlas-contracts.schema.json")
        values = schema["$defs"]["causeMapping"]["properties"]["mapping_status"]["enum"]
        self.assertEqual(values, ["documented", "candidate", "unmapped"])


if __name__ == "__main__":
    unittest.main()
