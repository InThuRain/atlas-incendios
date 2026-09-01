"""Contratos específicos de ES-4D3A; no reconstruyen ni descargan ICV."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/web/gva/manifest.json"
FIRES = ROOT / "data/web/gva/fires.json"
CONFIG = ROOT / "src/national/asset-config.mjs"
REGISTRY = ROOT / "src/national/source-registry.mjs"
LOADER = ROOT / "prototypes/es4c/icv_loader.mjs"
STATE = ROOT / "prototypes/es4c/runtime_state.mjs"
SERIALIZER = ROOT / "prototypes/es4c/state_serialization.mjs"
RUNTIME = ROOT / "prototypes/es4c/app.js"


class GvaIcvSourceParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.fires = json.loads(FIRES.read_text(encoding="utf-8"))["fires"]

    def test_public_manifest_is_the_only_delivery_root(self):
        self.assertEqual(self.manifest["icv"]["attributes"]["fires"]["url"], "data/web/gva/fires.json")
        self.assertEqual(len(self.manifest["icv"]["geometry_assets"]), 36)
        self.assertIn('path: "/data/web/gva/manifest.json"', CONFIG.read_text(encoding="utf-8"))

    def test_reconciles_source_records(self):
        self.assertEqual(len(self.fires), 13738)
        self.assertEqual(len({row["fire_id"] for row in self.fires}), 13738)

    def test_known_multi_geometry_source_record_is_preserved(self):
        row = next(row for row in self.fires if row["fire_id"] == "gva:pif-cv:2024AL0005")
        self.assertEqual(row["geometry_ids"], ["gva:geometry:2024:121:13587", "gva:geometry:2024:121:13606"])

    def test_documented_municipality_is_not_a_spatial_join(self):
        source = LOADER.read_text(encoding="utf-8")
        self.assertIn("filtro documental por municipality_id declarado en ICV", source)
        self.assertIn("spatial join contra BDLJE", source)

    def test_province_crosswalk_is_explicit(self):
        source = LOADER.read_text(encoding="utf-8")
        for pair in ('"ES:PROV:03": "alicante"', '"ES:PROV:12": "castellon"', '"ES:PROV:46": "valencia"'):
            self.assertIn(pair, source)

    def test_registry_declares_quality_coverage_and_attribution(self):
        source = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("coverage: { from: 1993, to: 2024 }", source)
        self.assertIn('territory_coverage: ["ES:CCAA:10"]', source)
        self.assertIn("CC BY 4.0, Generalitat", source)

    def test_state_has_independent_icv_selection(self):
        source = STATE.read_text(encoding="utf-8")
        self.assertIn("selected_icv_geometry_id", source)
        self.assertIn('type === "select_icv_geometry"', source)

    def test_serialization_is_additive_v1_and_keeps_icv_2024_compatible(self):
        source = SERIALIZER.read_text(encoding="utf-8")
        self.assertIn('icv: Boolean(state.icv_visible)', source)
        self.assertIn("icv_geometry_id", source)
        # D3B extiende el rango global a 2026 para EFFIS; ICV conserva su
        # cobertura propia 1993–2024 en el registro de fuentes.
        self.assertIn("time.to <= 2026", source)
        self.assertIn('STATE_VERSION = "es4c-state-v1"', source)

    def test_runtime_uses_isolated_geojson_source(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn('const ICV_SOURCE_ID = "icv"', source)
        self.assertIn('type: "geojson", data: { type: "FeatureCollection", features: [] }', source)
        self.assertIn("async function refreshIcv()", source)

    def test_no_combined_fire_counter_contract(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertNotIn("TOTAL INCENDIOS", source)
        self.assertIn("fuentes: ESFire30", source)


if __name__ == "__main__":
    unittest.main()
