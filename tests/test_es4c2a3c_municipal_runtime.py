import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER_URL = (ROOT / "prototypes/es4c/municipality_loader.mjs").as_uri()
STATE_URL = (ROOT / "prototypes/es4c/runtime_state.mjs").as_uri()
SERIALIZER_URL = (ROOT / "prototypes/es4c/state_serialization.mjs").as_uri()
EGIF_URL = (ROOT / "prototypes/es4c/egif_detail_loader.mjs").as_uri()

NODE_TEST = r'''
import assert from "assert";
import { TextEncoder } from "util";
import { buildMunicipalityCatalog, shardPathForAsset, MunicipalityLoader } from "__LOADER_URL__";
import { createRuntimeState, reduceRuntimeState } from "__STATE_URL__";
import { parseStateHash, serializeState } from "__SERIALIZER_URL__";
import { pageOfInitialRows, recordMatchesInitialScope } from "__EGIF_URL__";
global.TextEncoder = TextEncoder; global.performance = { now: (() => { let n = 0; return () => ++n; })() };
class AbortControllerFake { constructor(){this.signal={aborted:false};} abort(){this.signal.aborted=true;} }
const catalogRows=[
  {municipality_id:"ES:MUN:03065",province_id:"ES:PROV:03",autonomous_community_id:"ES:CCAA:10",official_name:"Elx/Elche",bounds:[-1,38,0,39],asset_id:"municipalities:ES:PROV:03"},
  {municipality_id:"ES:MUN:51001",province_id:null,autonomous_community_id:"ES:CCAA:18",official_name:"Ceuta",bounds:[-6,35,-5,36],asset_id:"municipalities:ES:CCAA:18"},
  ...Array.from({length:8130},(_,i)=>({municipality_id:`ES:MUN:${String(60000+i).padStart(5,"0")}`,province_id:"ES:PROV:03",autonomous_community_id:"ES:CCAA:10",official_name:`x${i}`,bounds:[0,0,1,1],asset_id:"municipalities:ES:PROV:03"}))
];
const catalog = buildMunicipalityCatalog({municipalities:catalogRows});
assert.ok(catalog.byProvince.get("ES:PROV:03").some((row)=>row.municipality_id==="ES:MUN:03065")); assert.strictEqual(catalog.byCity.get("ES:CCAA:18").length,1);
assert.strictEqual(shardPathForAsset("municipalities:ES:PROV:03"),"/data/derived/spain/es4c2a3/municipalities/ES-PROV-03.geojson");
let state=createRuntimeState(); state=reduceRuntimeState(state,{type:"set_municipality",municipality_id:"ES:MUN:03065",province_id:"ES:PROV:03",autonomous_community_id:"ES:CCAA:10"});
assert.strictEqual(state.territory_scope,"municipality"); assert.strictEqual(state.municipality_id,"ES:MUN:03065");
const defaults={...createRuntimeState(),center:[-3.7,40.3],zoom:4}; const parsed=parseStateHash(serializeState({...state,center:[-0.5,38.2],zoom:8}),defaults,new Set(["ES:CCAA:10","ES:CCAA:18"]),new Map([["ES:PROV:03","ES:CCAA:10"]]),catalog.byId);
assert.strictEqual(parsed.state.municipality_id,"ES:MUN:03065"); assert.strictEqual(parsed.state.province_id,"ES:PROV:03");
const columns={record_id:["egif-record:1","egif-record:2"],year:[1995,1995],province_id:["ES:PROV:03","ES:PROV:03"],municipality_id:["ES:MUN:03065",null]};
const loaded={asset:{asset_id:"a"},data:{columns},lookup:new Map([["egif-record:1",0],["egif-record:2",1]])};
assert.strictEqual(pageOfInitialRows([loaded],1995,1995,0,50,"ES:PROV:03","ES:MUN:03065").total,1);
assert.strictEqual(recordMatchesInitialScope([loaded],"egif-record:2",1995,1995,"ES:PROV:03","ES:MUN:03065"),false);
async function main() {
let calls=0; const resolvers=[]; const response=(data)=>({ok:true,text:async()=>JSON.stringify(data)});
const fetchImpl=(url)=>{calls++; if(url.includes("municipality_catalog")) return Promise.resolve(response({municipalities:[
  ...catalogRows
]})); return new Promise(resolve=>{resolvers.push(()=>resolve(response({features:[{properties:{municipality_id:"ES:MUN:03065"},geometry:{type:"MultiPolygon",coordinates:[]}}]})));});};
const loader=new MunicipalityLoader({fetchImpl,AbortControllerImpl:AbortControllerFake}); const first=loader.loadForParent({provinceId:"ES:PROV:03"}); await new Promise(r=>setTimeout(r,0)); const second=loader.loadForParent({provinceId:"ES:PROV:03"}); await new Promise(r=>setTimeout(r,0)); resolvers.forEach((resolve)=>resolve()); const [one,two]=await Promise.all([first,second]); assert.strictEqual(one.status,"stale"); assert.strictEqual(two.status,"complete");
console.log(JSON.stringify({valid:true,calls}));
}
main().catch((error) => { console.error(error); process.exit(1); });
'''


class ES4C2A3CMunicipalRuntimeTests(unittest.TestCase):
    def test_catalog_state_serializer_and_egif_municipality_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "municipal-runtime.mjs"
            script.write_text(NODE_TEST.replace("__LOADER_URL__", LOADER_URL).replace("__STATE_URL__", STATE_URL).replace("__SERIALIZER_URL__", SERIALIZER_URL).replace("__EGIF_URL__", EGIF_URL), encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_runtime_isolated_and_documents_current_boundary_semantics(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("municipality_id", app)
        self.assertIn("filtrado municipal pendiente", app)
        self.assertIn("partes EGIF enlazadas documentalmente al municipio canónico", app)
        self.assertNotIn("prototypes/es4c", public_index)


if __name__ == "__main__":
    unittest.main()
