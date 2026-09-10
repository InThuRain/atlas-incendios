"""Focused ES-4POST2B contracts; no browser, data rebuild or remote access."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLE = (ROOT / "prototypes/es4c/temporal_style.mjs").as_uri()
APP = ROOT / "prototypes/es4c/app.js"
ICV_LOADER = ROOT / "prototypes/es4c/icv_loader.mjs"
FILTERS = ROOT / "prototypes/es4c/source_filters.mjs"
SHELL = ROOT / "src/national/product-shell.mjs"
CSS = ROOT / "src/national/styles.css"
BUILDER = ROOT / "scripts/build_national_frontend.py"


def style_values(cases: list[dict]) -> list[dict]:
    script = (
        f'import {{ temporalColor, temporalColorExpression, temporalVisualState }} from "{STYLE}";\n'
        f'const cases = {json.dumps(cases)};\n'
        'console.log(JSON.stringify(cases.map(item => {\n'
        '  const visual=temporalVisualState(item.from,item.to);\n'
        '  return {visual, color:temporalColor(item.year,visual.domain), expression:temporalColorExpression(visual.domain)};\n'
        '})));\n'
    )
    with tempfile.TemporaryDirectory() as directory:
        module = Path(directory) / "temporal-contract.mjs"
        module.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", "--experimental-modules", str(module)], text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class TemporalEncodingTests(unittest.TestCase):
    def test_exact_gva_palette_endpoints_and_linear_intermediate(self):
        old, middle, recent = style_values([
            {"from": 1993, "to": 2024, "year": 1993},
            {"from": 1993, "to": 2024, "year": 2008},
            {"from": 1993, "to": 2024, "year": 2024},
        ])
        self.assertEqual(old["color"], "rgb(44,123,182)")
        self.assertEqual(middle["color"], "rgb(139,103,116)")
        self.assertEqual(recent["color"], "rgb(240,82,46)")
        self.assertEqual(old["visual"]["palette"], {"old": "rgb(44,123,182)", "recent": "rgb(240,82,46)"})

    def test_requested_range_is_explicit_and_independent_from_filtered_results(self):
        first, second = style_values([
            {"from": 2000, "to": 2020, "year": 2010},
            {"from": 2000, "to": 2020, "year": 2010},
        ])
        self.assertEqual(first["visual"]["domain"], {"from": 2000, "to": 2020})
        self.assertEqual(first["color"], second["color"])
        self.assertEqual(first["expression"][0], "interpolate")

    def test_single_year_is_safe_and_uses_one_documented_temporal_value(self):
        item = style_values([{"from": 1995, "to": 1995, "year": 1995}])[0]
        self.assertTrue(item["visual"]["single_year"])
        self.assertEqual(item["visual"]["domain"], {"from": 1995, "to": 1995})
        self.assertEqual(item["color"], "rgb(44,123,182)")
        self.assertEqual(item["expression"], "rgb(44,123,182)")

    def test_maplibre_uses_year_sort_and_temporal_fill_for_all_polygon_sources(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn('"fill-sort-key": ["to-number", ["get", "year"]]', source)
        self.assertIn('const OUTLINE_LAYER = "esfire30-perimeter-outlines"', source)
        self.assertIn('const ICV_OUTLINE_LAYER = "icv-perimeter-outlines"', source)
        self.assertIn('const EFFIS_OUTLINE_LAYER = "effis-perimeter-outlines"', source)
        self.assertIn('applyTemporalStyle();', source)
        self.assertIn('showHover("icv"', source)
        self.assertIn('showHover("effis"', source)
        self.assertIn('showHover("esfire30"', source)
        self.assertIn('paint: { "line-color": "#151a18", "line-width": 3', source)

    def test_one_to_many_icv_identity_and_human_filters_do_not_define_the_temporal_scale(self):
        loader = ICV_LOADER.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        filters = FILTERS.read_text(encoding="utf-8")
        self.assertIn('"gva:pif-cv:2024AL0005"', loader)
        self.assertIn('target_2024AL0005_geometries: targetFire.length', loader)
        self.assertIn('filter_id: "icv_min_area"', filters)
        self.assertIn('filter_id: "icv_gif"', filters)
        self.assertIn('filter_id: "icv_cause"', filters)
        self.assertIn('temporalVisualState(state.from, state.to)', app)
        self.assertNotIn('latestIcvResult.metrics', app[app.index('function currentTemporalVisual'):app.index('function applyTemporalStyle')])

    def test_legend_is_primary_textual_temporal_scale_and_sources_remain_secondary(self):
        shell = SHELL.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        self.assertIn('heading.textContent = "Año del perímetro"', shell)
        self.assertIn('"Más antiguo ← → más reciente"', shell)
        self.assertIn('heading.textContent = "Capas"', shell)
        self.assertIn('getTemporalVisualState', shell)
        self.assertIn('linear-gradient(90deg, rgb(44 123 182), rgb(240 82 46))', css)

    def test_frontend_builder_carries_the_shared_temporal_runtime_module(self):
        self.assertIn('"temporal_style.mjs"', BUILDER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
