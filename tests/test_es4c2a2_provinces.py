import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/territories/build_provinces_prototype.py"
LAYER_URL = (ROOT / "prototypes/es4c/province_layer.mjs").as_uri()
STATE_URL = (ROOT / "prototypes/es4c/runtime_state.mjs").as_uri()
SERIALIZER_URL = (ROOT / "prototypes/es4c/state_serialization.mjs").as_uri()
INITIAL_URL = (ROOT / "prototypes/es4c/egif_initial_loader.mjs").as_uri()
DETAIL_URL = (ROOT / "prototypes/es4c/egif_detail_loader.mjs").as_uri()


def polygon(x, y):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + .1, y], [x + .1, y + .1], [x, y + .1], [x, y]]]}


class ES4C2A2ProvinceTests(unittest.TestCase):
    def test_builder_explains_53_source_features_and_crosswalks_50_provinces(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            features, territories = [], []
            for code in range(1, 51):
                province = f"{code:02d}"
                community = "10" if province in {"03", "12", "46"} else "01"
                features.append({"type": "Feature", "properties": {"nationalcode": f"34{community}{province}00000", "nameunit": f"Fuente {province}", "nationallevelname": "Provincia"}, "geometry": polygon(code, 30)})
                territories.append({"territory_id": f"ES:PROV:{province}", "official_code": province, "official_name": f"Canónica {province}", "territory_type": "province", "parent_id": f"ES:CCAA:{community}"})
            for code, city in (("51", "18"), ("52", "19")):
                features.append({"type": "Feature", "properties": {"nationalcode": f"34{city}{code}00000", "nameunit": f"Ciudad {city}", "nationallevelname": "Provincia"}, "geometry": polygon(int(code), 35)})
                territories.append({"territory_id": f"ES:CCAA:{city}", "official_code": city, "official_name": f"Ciudad {city}", "territory_type": "autonomous_city", "parent_id": "ES"})
            features.append({"type": "Feature", "properties": {"nationalcode": "34205400000", "nameunit": "No asociado", "nationallevelname": "Provincia"}, "geometry": polygon(54, 35)})
            source = directory / "source.geojson"; source.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
            snapshot = directory / "snapshot.json"; snapshot.write_text(json.dumps({"territories": territories}), encoding="utf-8")
            output, manifest, catalog = directory / "provinces.geojson", directory / "manifest.json", directory / "province_catalog.mjs"
            command = ["python3", str(BUILDER), "--source", str(source), "--snapshot", str(snapshot), "--output", str(output), "--manifest", str(manifest), "--catalog", str(catalog), "--tolerance-m", "0"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(0, subprocess.run(command + ["--check"], capture_output=True, text=True).returncode)
            written = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(53, written["source_schema"]["source_features"])
            self.assertEqual({"canonical_province": 50, "autonomous_city_province_equivalent": 2, "unassociated": 1}, written["source_schema"]["features_by_role"])
            self.assertEqual(50, written["derived"]["logical_provinces"])
            self.assertEqual({"ES:CCAA:18", "ES:CCAA:19"}, {row["territory_id"] for row in written["province_equivalent_source_units"]})
            self.assertIn("ES:PROV:03", catalog.read_text(encoding="utf-8"))

    def test_state_serializer_and_province_layer_preserve_parent_semantics(self):
        program = r'''
import assert from "assert";
import { createRuntimeState, reduceRuntimeState } from "__STATE_URL__";
import { parseStateHash, serializeState } from "__SERIALIZER_URL__";
import { addOfficialProvinceLayer, PROVINCE_SELECTED_LAYER } from "__LAYER_URL__";
import { summarizeInitialAssets } from "__INITIAL_URL__";
import { pageOfInitialRows, recordMatchesInitialScope } from "__DETAIL_URL__";
async function main() {
const defaults={...createRuntimeState({center:[-3.7,40.3],zoom:4})};
let state=reduceRuntimeState(defaults,{type:"set_province",province_id:"ES:PROV:03",autonomous_community_id:"ES:CCAA:10"});
assert.strictEqual(state.territory_scope,"province"); assert.strictEqual(state.province_id,"ES:PROV:03");
state=reduceRuntimeState(state,{type:"set_scope",territory_id:"ES:CCAA:10"}); assert.strictEqual(state.province_id,null);
const hash=serializeState({...defaults,territory_scope:"province",autonomous_community_id:"ES:CCAA:10",province_id:"ES:PROV:03"});
const parents=new Map([["ES:PROV:03","ES:CCAA:10"]]);
assert.strictEqual(parseStateHash(hash,defaults,new Set(["ES:CCAA:10"]),parents).state.province_id,"ES:PROV:03");
assert.strictEqual(parseStateHash(hash,defaults,new Set(["ES:CCAA:10"]),new Map()).state.territory_scope,"ES");
const features=Array.from({length:50},(_,i)=>({type:"Feature",properties:{territory_id:`ES:PROV:${String(i+1).padStart(2,"0")}`,parent_id:i<3?"ES:CCAA:10":"ES:CCAA:01",bounds:[i,30,i+.5,31]},geometry:{type:"Polygon",coordinates:[]}}));
const events={}, calls=[]; let selected=null;
const map={addSource:(...x)=>calls.push(["source",...x]),addLayer:(x)=>calls.push(["layer",x]),on:(event,layer,callback)=>events[`${event}:${layer}`]=callback,getCanvas:()=>({style:{}}),setFilter:(...x)=>calls.push(["filter",...x]),fitBounds:(...x)=>calls.push(["fit",...x])};
const layer=await addOfficialProvinceLayer(map,{fetchImpl:async()=>({ok:true,json:async()=>({features})}),onSelect:(id,parent)=>selected=[id,parent]});
layer.setScope("ES:CCAA:10","ES:PROV:03"); assert.strictEqual(calls.filter(x=>x[0]==="filter").pop()[1],PROVINCE_SELECTED_LAYER);
events["click:official-province-territories-fill"]({features:[features[2]]}); assert.deepStrictEqual(selected,["ES:PROV:03","ES:CCAA:10"]); assert.strictEqual(layer.fit("ES:PROV:03"),true);
const columns={record_id:["egif-record:1","egif-record:2"],year:[1995,1995],province_id:["ES:PROV:03","ES:PROV:46"],is_gif_forest_ge_500_ha:[false,true],municipality_id:[null,"ES:MUN:1"],reported_forest_area_ha:[null,4]};
const loaded={asset:{asset_id:"a",initial:{gzip_size:1}},data:{columns},lookup:new Map([["egif-record:1",0],["egif-record:2",1]]),metrics:{raw_bytes:1,fetch_ms:0,parse_ms:0}};
assert.strictEqual(summarizeInitialAssets([loaded],1995,1995,"ES:PROV:03").records,1); assert.strictEqual(pageOfInitialRows([loaded],1995,1995,0,10,"ES:PROV:46").rows.length,1); assert.strictEqual(recordMatchesInitialScope([loaded],"egif-record:1",1995,1995,"ES:PROV:46"),false);
console.log(JSON.stringify({valid:true}));
}
main().catch((error) => { console.error(error); process.exit(1); });
'''.replace("__STATE_URL__", STATE_URL).replace("__SERIALIZER_URL__", SERIALIZER_URL).replace("__LAYER_URL__", LAYER_URL).replace("__INITIAL_URL__", INITIAL_URL).replace("__DETAIL_URL__", DETAIL_URL)
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "province-test.mjs"; script.write_text(program, encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"valid": True}, json.loads(result.stdout))

    def test_prototype_isolated_and_keeps_esfire30_territorial_filter_out_of_scope(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("setProvinceScope", app)
        self.assertIn("province_id", app)
        self.assertNotIn("primary_autonomous_community", app)
        self.assertNotIn("prototypes/es4c", public_index)


if __name__ == "__main__":
    unittest.main()
