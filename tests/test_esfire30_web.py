import importlib.util
import json
import sys
import unittest
from pathlib import Path

from shapely.geometry import Polygon


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_esfire30_frontend_assets.py"
SPEC = importlib.util.spec_from_file_location("esfire30_web", SCRIPT)
esfire30_web = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = esfire30_web
SPEC.loader.exec_module(esfire30_web)


class ESFire30WebTests(unittest.TestCase):
    def test_stable_identity_does_not_use_source_record_order(self):
        first = esfire30_web.source_fingerprint(
            1986, {"area_ha": 12.5, "cause": "unknown"}, "geometry-sha"
        )
        reordered = esfire30_web.source_fingerprint(
            1986, {"cause": "unknown", "area_ha": 12.5}, "geometry-sha"
        )
        changed = esfire30_web.source_fingerprint(
            1986, {"area_ha": 12.6, "cause": "unknown"}, "geometry-sha"
        )
        self.assertEqual(first, reordered)
        self.assertNotEqual(first, changed)

    def test_web_feature_keeps_identity_and_spatial_relations_separate(self):
        geometry = Polygon([(0, 0), (10, 0), (10, 10), (0, 0)])
        item = {
            "stable_record_id": "esfire30:record:sha256:stable",
            "source_record_id": "esfire30:v1:record:sha256:versioned",
            "geometry_id": "esfire30:geometry:sha256:geometry",
            "source_version": "v1",
            "source_record_index": 12,
            "source_feature_fingerprint_sha256": "stable",
            "source_geometry_checksum_sha256": "geometry",
            "source_year": 1986,
            "source_area_ha": 5.5,
            "primary_province": "valencia",
            "intersected_provinces": ["castellon", "valencia"],
            "municipalities": [
                {"municipality_id": "46001", "municipality_name": "Ademús", "province": "valencia"},
                {"municipality_id": "12001", "municipality_name": "Atzeneta del Maestrat", "province": "castellon"},
            ],
        }
        feature = esfire30_web.web_feature(item, geometry)
        properties = feature["properties"]
        self.assertEqual(item["stable_record_id"], properties["entity_id"])
        self.assertEqual(item["geometry_id"], properties["geometry_id"])
        self.assertEqual(["castellon", "valencia"], properties["province_ids"])
        self.assertEqual(["46001", "12001"], properties["municipality_ids"])
        self.assertEqual(["valencia", "castellon"], properties["municipality_province_ids"])
        self.assertEqual("unresolved", properties["episode_identity_status"])
        self.assertEqual("unlinked", properties["administrative_link_status"])
        self.assertNotIn("egif", properties)

    def test_lod_and_crs_policy_is_fail_closed_configuration(self):
        config = json.loads((ROOT / "config/esfire30-web.json").read_text(encoding="utf-8"))
        self.assertEqual("EPSG:23030", config["source_crs"])
        self.assertEqual("EPSG:4326", config["web_crs"])
        self.assertEqual(64, len(config["grid"]["sha256"]))
        self.assertEqual(0, config["lod"]["local"]["tolerance_m"])
        self.assertLess(config["lod"]["regional"]["tolerance_m"], config["lod"]["overview"]["tolerance_m"])

    def test_candidate_public_profile_includes_esfire30_and_rejects_sigif(self):
        catalog = json.loads((ROOT / "config/sources-gva.json").read_text(encoding="utf-8"))
        self.assertIn("esfire30", catalog["profiles"]["development"]["sources"])
        self.assertIn("esfire30", catalog["profiles"]["public"]["sources"])
        self.assertTrue(catalog["sources"]["esfire30"]["publishable"])
        self.assertEqual("B_documented_remote_sensing", catalog["sources"]["esfire30"]["geometry_quality"])
        self.assertNotIn("sigif", catalog["profiles"]["public"]["sources"])


if __name__ == "__main__":
    unittest.main()
