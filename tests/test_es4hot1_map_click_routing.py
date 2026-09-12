"""Focused arbitration regressions; browser counterpart uses real CDP input."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ClickRoutingTests(unittest.TestCase):
    def test_precedence_and_exclusive_mutation(self):
        uri=(ROOT/'prototypes/es4c/map_click_routing.mjs').as_uri()
        script=f'''import {{routeMapClick}} from {json.dumps(uri)};
const results=[];
for(const scenario of ['point','single','multi','background','empty']){{
  let territory='ES:CCAA:10'; const calls=[];
  const result=routeMapClick({{point:[12,34]}},{{
    pointQueryActive:()=>scenario==='point',
    handlePointQuery:()=>calls.push('point'),
    queryFireHits:()=>{{calls.push('query_fire');return scenario==='single'?[{{id:'a'}}]:scenario==='multi'?[{{id:'a'}},{{id:'b'}}]:[];}},
    handleFireHits:h=>calls.push('fire:'+h.length),
    queryTerritory:()=>{{calls.push('query_territory');return scenario==='empty'?null:{{id:'ES:PROV:03'}};}},
    handleTerritory:t=>{{territory=t.id;calls.push('territory');}},
    handleEmpty:()=>calls.push('empty')
  }});results.push({{scenario,result,calls,territory}});
}}console.log(JSON.stringify(results));'''
        with tempfile.TemporaryDirectory() as directory:
            module=Path(directory)/'routing.mjs'
            module.write_text(script)
            result=subprocess.run(['node','--experimental-modules',str(module)],capture_output=True,text=True,check=True)
        rows=json.loads(result.stdout)
        self.assertEqual(rows[0]['calls'],['point'])
        for i,n in ((1,1),(2,2)):
            self.assertEqual(rows[i]['calls'],['query_fire',f'fire:{n}'])
            self.assertEqual(rows[i]['territory'],'ES:CCAA:10')
        self.assertEqual(rows[3]['territory'],'ES:PROV:03')
        self.assertEqual(rows[4]['calls'],['query_fire','query_territory','empty'])

    def test_admin_controllers_cannot_compete_with_global_click(self):
        for filename in ('territory_layer.mjs','province_layer.mjs','municipality_layer.mjs'):
            source=(ROOT/'prototypes/es4c'/filename).read_text()
            self.assertNotIn('map.on("click"',source,filename)
            self.assertIn('selectFromFeature',source)
        app=(ROOT/'prototypes/es4c/app.js').read_text()
        self.assertEqual(app.count('map.on("click",'),1)
        self.assertIn('return routeMapClick(event,',app)

    def test_query_includes_visible_representations_and_no_tolerance_box(self):
        app=(ROOT/'prototypes/es4c/app.js').read_text()
        query=app[app.index('function mapPopupHits'):app.index('function handleFirePopupHits')]
        for layer in ['FILL_LAYER','OUTLINE_LAYER','SELECTED_LAYER','HOVER_LAYER','ICV_SELECTED_LAYER','EFFIS_HOVER_LAYER']:
            self.assertIn(layer,query)
        self.assertIn('state[`${popupSourceForLayer(layerId)}_visible`]',query)
        self.assertIn('map.getLayoutProperty(layerId, "visibility") !== "none"',query)
        self.assertIn('map.queryRenderedFeatures(point, { layers })',query)
        self.assertNotIn('CCAA_FILL_LAYER',query)
        self.assertIn('dedupeAndSortHits',query)

    def test_browser_regression_uses_real_gesture_and_territory_assertions(self):
        source=(ROOT/'scripts/audit/product/es4hot1_map_click_routing.py').read_text()
        self.assertIn('Input.dispatchMouseEvent',source)
        self.assertIn('Input.dispatchTouchEvent',source)
        self.assertNotIn('runtime.handleMapPopupClick(',source)
        self.assertIn("before['territory']==after['territory']",source)
        self.assertIn("expected in after['selection'].values()",source)

    def test_legacy_point_query_contract_is_untouched(self):
        legacy=(ROOT/'js/app.js').read_text()
        self.assertIn('if (state.pointMode) return;',legacy)
        self.assertIn('if (state.pointMode) queryPoint(event.latlng)',legacy)
        self.assertIn('"map_click_routing.mjs"',(ROOT/'scripts/build_national_frontend.py').read_text())

if __name__=='__main__':unittest.main()
