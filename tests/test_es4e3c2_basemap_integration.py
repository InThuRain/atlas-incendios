"""Pruebas específicas de ES-4E3C2_BASEMAP_INTEGRATION."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/national-basemap-protomaps-20260902-z12.json"


class BasemapIntegrationTests(unittest.TestCase):
    def test_asset_identity_and_reproducible_contract(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["pmtiles"]["bytes"], 293324998)
        self.assertEqual(contract["pmtiles"]["sha256"], "72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729")
        self.assertEqual(contract["glyphs"]["file_count"], 9)
        self.assertEqual(contract["glyphs"]["total_bytes"], 909374)
        self.assertEqual(contract["glyphs"]["files"][0]["bytes"], 76044)
        self.assertEqual(contract["glyphs"]["files"][0]["sha256"], "62c6d49b15fa836eb6aa45e259c7ca6762f44b011b09e47776efbe4a6db1b397")
        self.assertEqual(contract["glyphs"]["source_commit"], "028c18f713baecad011301ff7a69acc39bcc2ae7")
        self.assertEqual(contract["glyphs"]["license_bytes"], 4374)
        self.assertEqual(contract["style"]["sprites"], [])
        self.assertEqual(contract["runtime_external_domains"], [])
        self.assertFalse(contract["api_keys_required"])
        self.assertIn("20260902-z12/72bb270f", contract["pmtiles"]["runtime_path"])
        result = subprocess.run(["python3", "scripts/basemaps/prepare_protomaps_basemap.py", "--check"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_style_fallback_attribution_and_layer_order_contract(self):
        style = (ROOT / "src/national/basemap-context.mjs").read_text(encoding="utf-8")
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/national/index.html").read_text(encoding="utf-8")
        registry = (ROOT / "src/national/source-registry.mjs").read_text(encoding="utf-8")
        self.assertEqual(style.count('"source-layer"'), 11)
        self.assertIn('state.status = "fallback_bdlje_only"', style)
        self.assertIn('fallback = "bdlje_only"', style)
        self.assertNotIn("sprite", style.lower())
        self.assertNotIn("https://", style)
        self.assertIn("BASEMAP_GLYPHS_TEMPLATE", app)
        self.assertIn("isBasemapTransportError", app)
        self.assertIn('>Protomaps</a> · <a href="https://www.openstreetmap.org/copyright"', html)
        self.assertIn("© OpenStreetMap contributors</a> · <a href=\"https://www.ign.es/\"", html)
        self.assertIn("Obra derivada de BDLJE CC-BY 4.0 ign.es</a>", html)
        self.assertIn('role: "cartographic_context"', registry)
        self.assertIn('wildfire_source: false', registry)
        for layer_file in ("territory_layer.mjs", "province_layer.mjs", "municipality_layer.mjs"):
            text = (ROOT / "prototypes/es4c" / layer_file).read_text(encoding="utf-8")
            self.assertRegex(text, re.compile(r"map\.addLayer\(\{.*?id: [A-Z_]*SELECTED_LAYER.*?\}, fireLayer\);", re.S))

    def test_frontend_and_full_assembly_contracts_remain_separate(self):
        with tempfile.TemporaryDirectory(prefix="basemap-frontend-test-") as directory:
            output = Path(directory) / "frontend"
            built = subprocess.run(["python3", "scripts/build_national_frontend.py", "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(built.returncode, 0, built.stderr or built.stdout)
            checked = subprocess.run(["python3", "scripts/build_national_frontend.py", "--check", "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr or checked.stdout)
            manifest = json.loads((output / "asset-manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["large_assets_included"])
            basemap = manifest["logical_asset_config"]["assets"]["basemap"]
            self.assertEqual(basemap["pmtiles"]["bytes"], 293324998)
            self.assertFalse((output / basemap["pmtiles"]["path"]).exists())
            self.assertTrue((output / "basemap-context.mjs").is_file())
        assembly = (ROOT / "scripts/build_national_pages_artifact.py").read_text(encoding="utf-8")
        self.assertIn("copy_basemap", assembly)
        self.assertIn("copy_summary", assembly)
        self.assertIn('"protomaps_basemap_pmtiles", "protomaps_basemap_pmtiles"', assembly)


if __name__ == "__main__":
    unittest.main()
