"""Focused contracts for ES-4POST2C; no data build, network or Chromium."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POPUP = (ROOT / "prototypes/es4c/direct_popup.mjs").as_uri()
RUNTIME_STATE = (ROOT / "prototypes/es4c/runtime_state.mjs").as_uri()
APP = ROOT / "prototypes/es4c/app.js"
CSS = ROOT / "src/national/styles.css"
BUILDER = ROOT / "scripts/build_national_frontend.py"


def popup_values(cases: list[dict]) -> list[dict]:
    script = (
        f'import {{ dedupeAndSortHits, popupModel, chooserLabel }} from "{POPUP}";\n'
        f'const cases = {json.dumps(cases)};\n'
        'const results=cases.map(item => {\n'
        ' const hits=(item.hits||[]).map((row,index)=>({sourceId:row.sourceId,renderOrder:index,feature:{properties:row.properties||{}}}));\n'
        ' const sorted=dedupeAndSortHits(hits);\n'
        ' return {model: item.sourceId ? popupModel(item) : null, hits: sorted.map(hit=>({sourceId:hit.sourceId,geometryId:hit.geometryId,year:hit.feature.properties.year,label:chooserLabel(hit)}))};\n'
        '}); console.log(JSON.stringify(results));\n'
    )
    with tempfile.TemporaryDirectory() as directory:
        module = Path(directory) / "popup-contract.mjs"
        module.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", "--experimental-modules", str(module)], text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def runtime_transition_values() -> dict:
    script = (
        f'import {{ createRuntimeState, reduceRuntimeState }} from "{RUNTIME_STATE}";\n'
        'const initial=createRuntimeState({territory_scope:"autonomous_community",autonomous_community_id:"ES:CCAA:10",icv_visible:true,effis_visible:true});\n'
        'const selected=reduceRuntimeState(initial,{type:"select_icv_geometry",geometry_id:"gva:geometry:test",year:1995,record_id:"gva:pif-cv:test"});\n'
        'const period=reduceRuntimeState(selected,{type:"set_range",from:1994,to:1994});\n'
        'const territory=reduceRuntimeState(selected,{type:"set_scope",territory_id:"ES:CCAA:12"});\n'
        'const toggle=reduceRuntimeState(selected,{type:"set_visibility",source_id:"icv",visible:false});\n'
        'console.log(JSON.stringify({period,territory,toggle}));\n'
    )
    with tempfile.TemporaryDirectory() as directory:
        module = Path(directory) / "runtime-popup-contract.mjs"
        module.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", "--experimental-modules", str(module)], text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class DirectHumanPopupTests(unittest.TestCase):
    def test_source_models_only_expose_human_loaded_fields(self):
        icv, esfire, effis = popup_values([
            {"sourceId": "icv", "properties": {"year": 1995, "province": "Valencia"}, "record": {"start_date": "1995-08-12", "place_name": "Sierra", "municipality_name": "Xàtiva", "province": "Valencia", "reported_forest_area_ha": 500, "cause_label": "Negligencia"}},
            {"sourceId": "esfire30", "properties": {"geometry_id": "esfire30:v1:1995:1", "year": 1995}, "territoryName": "Comunitat Valenciana"},
            {"sourceId": "effis", "properties": {"geometry_id": "effis:1", "year": 2025, "date": "2025-07-03", "municipality_name": "Ourense", "mapped_area_ha": 42.25}, "territoryName": "Galicia"},
        ])
        self.assertEqual(icv["model"]["rows"][0], ["Fecha", "12/08/1995"])
        self.assertIn(["GIF", "Sí"], icv["model"]["rows"])
        self.assertNotIn("geometry_id", json.dumps(icv["model"]))
        self.assertEqual(esfire["model"]["title"], "Perímetro Landsat")
        self.assertNotIn("Causa", [row[0] for row in esfire["model"]["rows"]])
        self.assertNotIn("Superficie", [row[0] for row in esfire["model"]["rows"]])
        self.assertIn("no constituye cartografía oficial", esfire["model"]["note"])
        self.assertIn(["Superficie", "42,25 ha"], effis["model"]["rows"])
        self.assertEqual(effis["model"]["note"], "Dato satelital provisional.")

    def test_source_models_omit_blank_or_placeholder_fields(self):
        model = popup_values([{
            "sourceId": "icv", "properties": {"year": 1995},
            "record": {"start_date": "1995-08-12", "place_name": "   ", "municipality_name": "No disponible", "province": None,
                       "reported_forest_area_ha": None, "cause_label": "undefined"},
        }])[0]["model"]
        self.assertEqual(model["rows"], [["Fecha", "12/08/1995"]])

    def test_dedupes_fill_outline_but_keeps_sources_and_tie_order(self):
        result = popup_values([{"hits": [
            {"sourceId": "icv", "properties": {"geometry_id": "a", "year": 1995}},
            {"sourceId": "icv", "properties": {"geometry_id": "a", "year": 1995}},
            {"sourceId": "esfire30", "properties": {"geometry_id": "a", "year": 1996}},
            {"sourceId": "effis", "properties": {"geometry_id": "e", "year": 1996}},
        ]}])[0]["hits"]
        self.assertEqual([(row["sourceId"], row["geometryId"]) for row in result], [("esfire30", "a"), ("effis", "e"), ("icv", "a")])

    def test_app_uses_one_map_click_path_and_preserves_popup_contract(self):
        app = APP.read_text(encoding="utf-8")
        self.assertIn('map.on("click", handleMapPopupClick);', app)
        self.assertNotIn('map.on("click", FILL_LAYER,', app)
        self.assertIn('map.queryRenderedFeatures(point, { layers })', app)
        self.assertIn('closeOnMove: false', app)
        self.assertIn('closeOnClick: false', app)
        self.assertIn('setLngLat(lngLat)', app)
        self.assertIn('button.dataset.popupGeometryId = hit.geometryId', app)
        self.assertIn('"Ver detalles"', app)
        self.assertIn('document.addEventListener("keydown"', app)
        self.assertIn('if (!hits.length) { closeDirectPopup(); return; }', app)
        self.assertIn('"set_filter", "remove_filter", "clear_filters"', app)
        self.assertIn('closeDirectPopupFor("icv")', app)
        self.assertIn('closeDirectPopupFor("effis")', app)
        self.assertIn('closeDirectPopupFor("esfire30")', app)
        self.assertIn('event.type)) closeDirectPopup();', app)
        self.assertNotIn('innerHTML', app[app.index('function popupTerritoryName'):app.index('function clearEgifSelection')])

    def test_details_are_reused_and_mobile_popup_does_not_force_sheet(self):
        app = APP.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        self.assertIn('selectIcvFeature(hit.feature, { showDetail })', app)
        self.assertIn('selectEffisFeature(hit.feature, { showDetail })', app)
        self.assertIn('card.scrollIntoView', app)
        self.assertIn('data-map-popup-active="true"', css)
        self.assertIn('.direct-popup__choices', css)
        self.assertIn('.maplibregl-popup { position: absolute;', css)
        self.assertIn('.maplibregl-popup-content { position: relative;', css)
        self.assertIn('.direct-popup__details { position: sticky;', css)

    def test_builder_carries_popup_module(self):
        self.assertIn('"direct_popup.mjs"', BUILDER.read_text(encoding="utf-8"))

    def test_period_territory_and_source_changes_invalidate_selected_icv(self):
        values = runtime_transition_values()
        for name in ("period", "territory", "toggle"):
            self.assertIsNone(values[name]["selected_icv_geometry_id"], name)
            self.assertIsNone(values[name]["selected_icv_record_id"], name)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
