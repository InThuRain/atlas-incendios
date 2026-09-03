import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HIGHLIGHTS = ROOT / "data/derived/spain/national-highlights-v1"


class HighlightsMapPolishTests(unittest.TestCase):
    def test_small_national_derivative_contract(self):
        manifest = json.loads((HIGHLIGHTS / "manifest.json").read_text(encoding="utf-8"))
        data = json.loads((HIGHLIGHTS / "egif.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "national-highlights-v1")
        self.assertEqual(manifest["source"]["records_scanned"], 646887)
        self.assertLess(manifest["assets"][0]["bytes"], 400_000)
        self.assertEqual(data["null_policy"], "excluded_not_zero")
        self.assertEqual(data["ordering"], "reported_forest_area_ha_desc_record_id_asc")
        self.assertNotIn("geometry", (HIGHLIGHTS / "egif.json").read_text(encoding="utf-8"))
        for groups in data["years"].values():
            self.assertLessEqual(len(groups["all"]), 10)
            self.assertLessEqual(len(groups["gif_true"]), 10)

    def test_builder_check_and_frontend_contract(self):
        result = subprocess.run(["python3", "scripts/build_national_highlights.py", "--check"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        frontend = (ROOT / "scripts/build_national_frontend.py").read_text(encoding="utf-8")
        self.assertIn('"highlights.mjs"', frontend)
        self.assertIn('"egif_highlights_loader.mjs"', frontend)
        self.assertIn('"national-highlights-v1"', frontend)

    def test_local_map_context_is_same_origin_and_layered_below_fire(self):
        html = (ROOT / "src/national/index.html").read_text(encoding="utf-8")
        css = (ROOT / "src/national/styles.css").read_text(encoding="utf-8")
        layers = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in (
            "prototypes/es4c/territory_layer.mjs", "prototypes/es4c/province_layer.mjs", "prototypes/es4c/municipality_layer.mjs"
        ))
        self.assertIn("Contexto Protomaps/OSM", html)
        self.assertIn("límites administrativos BDLJE/IGN", html)
        self.assertIn("map-context", css)
        self.assertIn('map.getLayer("esfire30-perimeters")', layers)
        self.assertNotIn("tiles.openstreetmap.org", html + css + layers)


if __name__ == "__main__":
    unittest.main()
