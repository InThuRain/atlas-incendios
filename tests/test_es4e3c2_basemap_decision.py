"""Pruebas estáticas y pequeñas de la decisión ES-4E3C2."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/audit/product/es4e3c2_basemap_decision.json"
STYLE = ROOT / "benchmarks/es4e3c2_basemap/candidate.mjs"
HARNESS = ROOT / "benchmarks/es4e3c2_basemap/run.py"


class BasemapDecisionTests(unittest.TestCase):
    def test_pinned_source_region_size_and_decision(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["source_build"]["id"], "20260902.pmtiles")
        self.assertFalse(data["source_build"]["planet_downloaded"])
        self.assertEqual(data["region"]["logical_territories"], 19)
        self.assertFalse(data["region"]["bbox_used"])
        self.assertEqual(data["pmtiles"]["bytes"], 293324998)
        self.assertEqual(data["pmtiles"]["maxzoom"], 12)
        self.assertEqual(data["pmtiles"]["verify"], "PASS")
        self.assertFalse(data["zoom_candidates"]["z13"]["tested"])
        self.assertEqual(data["recommendation"], "ADOPT_PROTOMAPS_Z12")
        self.assertEqual(data["status"]["protomaps_adoption"], "NOT_AUTHORIZED_YET")

    def test_physical_accounting_and_license_contract(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        projected = data["projected_site_sizes"]
        current = data["current_site_size"]["current_e3_pre_basemap_projected_site_bytes"]
        self.assertEqual(data["complete_self_hosted_basemap_bytes"], 293411976)
        self.assertEqual(projected["with_z12_bytes"], current + data["complete_self_hosted_basemap_bytes"])
        self.assertEqual(projected["z12_pages_bytes_remaining"], projected["pages_limit_bytes_used_for_conservative_accounting"] - projected["with_z12_bytes"])
        self.assertEqual(data["sprites"]["bytes"], 0)
        self.assertIn("OpenStreetMap", data["attribution"]["proposal"])
        self.assertIn("OFL", data["licenses"]["glyph_font"])

    def test_harness_is_isolated_range_based_and_has_required_sequences(self):
        style = STYLE.read_text(encoding="utf-8")
        harness = HARNESS.read_text(encoding="utf-8")
        self.assertIn('BASEMAP_ARCHIVE_PATH = "data/basemap/protomaps-spain-z12.pmtiles"', style)
        self.assertNotIn("https://", style)
        self.assertNotIn("sprite", style.lower())
        self.assertIn('before = map.getLayer("official-ccaa-territories-fill")', style)
        self.assertIn('"spain_galicia_ourense"', harness)
        self.assertIn('"spain_gva_alacant_elx"', harness)
        self.assertIn("candidate_pmtiles_range_requests", harness)
        self.assertIn("candidate_full_downloads", harness)
        self.assertIn("build/es4e3c2-basemap", (ROOT / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
