import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build/esfire30/municipality_runtime_index.py"
LOADER_URL = (ROOT / "prototypes/es4c/municipality_esfire_index.mjs").as_uri()


def load_builder():
    spec = importlib.util.spec_from_file_location("es4c2b3b1_municipal_runtime_index", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NODE_TEST = r'''
import assert from "assert";
import { TextEncoder } from "util";
import { buildMunicipalityIndex, municipalityFilterExpression, MunicipalityEsfireIndexLoader } from "__LOADER_URL__";
global.TextEncoder = TextEncoder; global.performance = { now: (() => { let i = 0; return () => ++i; })() };
class AbortControllerFake { constructor(){ this.signal={aborted:false}; } abort(){ this.signal.aborted=true; } }
const schema="es4c2b3b1-municipality-runtime-index-v1";
const national={schema_version:schema,scope:"national",parent_id:null,municipalities:{"ES:MUN:03002":[],"ES:MUN:03065":["esfire30:v1:1993:777","esfire30:v1:2006:76"]}};
const parent={schema_version:schema,scope:"parent",parent_id:"ES:PROV:03",municipalities:{"ES:MUN:03002":[],"ES:MUN:03065":["esfire30:v1:1993:777","esfire30:v1:2006:76"]}};
assert.strictEqual(buildMunicipalityIndex(national).municipalityIds.get("ES:MUN:03065").length,2);
assert.deepStrictEqual(municipalityFilterExpression([]),["==",["get","geometry_id"],"__municipality_without_esfire30_geometry__"]);
assert.deepStrictEqual(municipalityFilterExpression(["esfire30:v1:1993:777"]),["in",["get","geometry_id"],["literal",["esfire30:v1:1993:777"]]]);
let calls=[]; const manifest={schema_version:schema,national:{path:"national.json"},by_parent:[{parent_id:"ES:PROV:03",path:"parent-03.json"}]};
const fetchImpl=async (url)=>{calls.push(url); const data=url.endsWith("manifest.json")?manifest:url.endsWith("national.json")?national:parent; return {ok:true,text:async()=>JSON.stringify(data)};};
async function main() {
const loader=new MunicipalityEsfireIndexLoader({manifestUrl:"/manifest.json",fetchImpl,AbortControllerImpl:AbortControllerFake});
let result=await loader.resolve({municipalityId:"ES:MUN:03065",parentId:"ES:PROV:03",strategy:"parent"}); assert.strictEqual(result.geometry_ids.length,2); assert.strictEqual(result.metrics.cached,false);
result=await loader.resolve({municipalityId:"ES:MUN:03002",parentId:"ES:PROV:03",strategy:"parent"}); assert.strictEqual(result.geometry_ids.length,0); assert.strictEqual(result.metrics.cached,true);
result=await loader.resolve({municipalityId:"ES:MUN:03065",parentId:"ES:PROV:03",strategy:"national"}); assert.strictEqual(result.geometry_ids.length,2); assert.strictEqual(result.strategy,"national");
assert.strictEqual(calls.filter(x=>x.endsWith("parent-03.json")).length,1); assert.strictEqual(calls.filter(x=>x.endsWith("national.json")).length,1);
console.log(JSON.stringify({valid:true}));
}
main().catch((error)=>{console.error(error);process.exit(1);});
'''


class ES4C2B3B1MunicipalRuntimeIndexTests(unittest.TestCase):
    def test_runtime_manifest_check_and_reconciliation(self):
        builder = load_builder()
        result = builder.check()
        self.assertTrue(result["valid"], result)
        self.assertEqual(119498, result["geometry_ids"])
        self.assertEqual(143477, result["positive_area_relations"])
        manifest = json.loads((ROOT / "data/derived/spain/es4c2b/runtime/municipality-index/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(2610, manifest["reconciliation"]["max_geometry_ids_per_municipality"])
        self.assertEqual(1966, manifest["reconciliation"]["municipalities_with_zero_geometry_ids"])

    def test_loader_national_parent_cache_and_filter_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "loader.mjs"
            path.write_text(NODE_TEST.replace("__LOADER_URL__", LOADER_URL), encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(path)], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_runtime_uses_municipal_list_only_at_municipal_scope(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        self.assertIn("municipalityFilterExpression", app)
        self.assertIn("geometry_id_set", app)
        self.assertIn("Límite municipal BDLJE actual (snapshot 2026)", app)
        self.assertIn("no son municipio EGIF, municipio histórico, origen ni punto de ignición", app)
        self.assertIn("municipality_id !== municipalityId", app)


if __name__ == "__main__":
    unittest.main()
