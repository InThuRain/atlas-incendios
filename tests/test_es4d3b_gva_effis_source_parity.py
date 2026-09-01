"""Contratos ES-4D3B para EFFIS GVA ya publicado; no descarga ni recalcula."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/web/gva/manifest.json"
CONFIG = ROOT / "src/national/asset-config.mjs"
REGISTRY = ROOT / "src/national/source-registry.mjs"
LOADER = ROOT / "prototypes/es4c/effis_loader.mjs"
STATE = ROOT / "prototypes/es4c/runtime_state.mjs"
SERIALIZER = ROOT / "prototypes/es4c/state_serialization.mjs"
RUNTIME = ROOT / "prototypes/es4c/app.js"


class GvaEffisSourceParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.assets = {asset["year"]: asset for asset in cls.manifest["recent"]["assets"] if asset["kind"] == "effis_perimeters"}

    def test_closed_snapshot_and_assets_match_manifest(self):
        recent = self.manifest["recent"]
        self.assertEqual(recent["snapshot_id"], "20260819T174426Z")
        self.assertEqual(set(self.assets), {2025, 2026})
        expected = {
            2025: (9, 37756, 11120, "afd7c30131d1c9829867b31633b4e5a0135df613722a1e72204c54af15a699c5"),
            2026: (16, 218475, 66631, "cd0e1f6f06220b673a5293787c5a9206b117a79d34295e1b934f58c87a3e7619"),
        }
        for year, (count, raw, gzip, digest) in expected.items():
            asset = self.assets[year]
            self.assertEqual((asset["feature_count"], asset["bytes"], asset["gzip_bytes"], asset["sha256"]), (count, raw, gzip, digest))
            path = ROOT / asset["url"]
            self.assertEqual(path.stat().st_size, raw)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_feature_identity_and_documented_attributes(self):
        for year, asset in self.assets.items():
            features = json.loads((ROOT / asset["url"]).read_text(encoding="utf-8"))["features"]
            self.assertEqual(len(features), asset["feature_count"])
            ids = [feature["properties"]["geometry_id"] for feature in features]
            self.assertEqual(len(ids), len(set(ids)))
            for feature in features:
                properties = feature["properties"]
                self.assertIsNotNone(feature["geometry"])
                self.assertTrue(properties["geometry_id"].startswith("effis:rda:"))
                self.assertEqual(properties["source_id"], "effis")
                self.assertEqual(properties["year"], year)

    def test_registry_preserves_provisional_semantics_and_scope(self):
        source = REGISTRY.read_text(encoding="utf-8")
        self.assertIn('coverage: { from: 2025, to: 2026 }', source)
        self.assertIn('territory_coverage: ["ES:CCAA:10"]', source)
        self.assertIn("perímetros satelitales provisionales EFFIS; no son perímetros oficiales ICV", source)
        self.assertIn("European Union, Copernicus EMS / EFFIS (CC BY 4.0)", source)

    def test_loader_only_uses_published_manifest_and_attributes(self):
        source = LOADER.read_text(encoding="utf-8")
        self.assertIn('asset.kind === "effis_perimeters"', source)
        self.assertIn("province_key", source)
        self.assertIn("municipality_id", source)
        self.assertIn("atributos documentados", source)
        self.assertNotIn("turf", source.lower())
        self.assertNotIn("intersect(", source)

    def test_state_and_serialization_are_additive_v1(self):
        self.assertIn("effis_visible: false", STATE.read_text(encoding="utf-8"))
        self.assertIn('type === "select_effis_geometry"', STATE.read_text(encoding="utf-8"))
        source = SERIALIZER.read_text(encoding="utf-8")
        self.assertIn("effis: Boolean(state.effis_visible)", source)
        self.assertIn("effis_geometry_id", source)
        self.assertIn("time.to <= 2026", source)
        self.assertIn('STATE_VERSION = "es4c-state-v1"', source)

    def test_runtime_is_separate_and_does_not_make_a_combined_total(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn('const EFFIS_SOURCE_ID = "effis"', source)
        self.assertIn("async function refreshEffis()", source)
        self.assertIn("datos EFFIS no integrados para este territorio", source)
        self.assertNotIn("TOTAL INCENDIOS", source)

    def test_snapshot_provenance_warns_about_area_and_2026_is_not_closed_campaign(self):
        effis = self.manifest["sources"]["effis"]
        self.assertEqual(effis["entity_type"], "provisional_satellite_perimeter")
        self.assertEqual(effis["source_status"], "provisional_satellite")
        self.assertEqual(effis["geometry_quality"], "B_provisional_satellite")
        coverage = {row["year"]: row for row in self.manifest["recent"]["coverage"]}
        self.assertEqual(coverage[2026]["effis_max_firedate"], "2026-08-08 00:00:00")
        self.assertEqual(coverage[2026]["effis_area_warning"], "Satellite-derived sum; not official administrative burned area.")


if __name__ == "__main__":
    unittest.main()
