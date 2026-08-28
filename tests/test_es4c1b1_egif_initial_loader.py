import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER_URL = (ROOT / "prototypes/es4c/egif_initial_loader.mjs").as_uri()


NODE_TEST = r'''
import assert from "assert";
import { TextEncoder } from "util";
import { blocksIntersecting, assetsForScope, manifestSummary, summarizeInitialAssets, EGIFInitialLoader } from "__LOADER_URL__";
global.performance = { now: () => 1 };
global.TextEncoder = TextEncoder;
class AbortControllerFake { constructor(){ this.signal={aborted:false}; } abort(){ this.signal.aborted=true; } }
async function main() {
const asset = (id, territory, from, to, counts) => ({ asset_id:id, source_id:"egif", territory_id:territory, from_year:from, to_year:to, status:"complete", record_count:counts.reduce((a,b)=>a+b,0), year_spools:counts.reduce((out,count,index)=>{out[String(from+index)]={record_count:count}; return out;},{}), initial:{path:`assets/${id}/initial.json`,gzip_size:10} });
const manifest = { temporal_blocks:[[1968,1979],[1980,1992],[1993,2002]], assets:[asset("a","ES:CCAA:10",1993,2002,[2,3]),asset("b","ES:CCAA:12",1993,2002,[4,5]) ] };
assert.deepStrictEqual(blocksIntersecting(manifest.temporal_blocks, 2000, 2005), [[1993,2002]]);
assert.strictEqual(assetsForScope(manifest,"ES:CCAA:10",1995,1998).length,1);
assert.strictEqual(manifestSummary(manifest,1993,1994).records,14);
const columns = {record_id:["egif-record:1","egif-record:2","egif-record:3"],year:[1993,1994,1994],is_gif_forest_ge_500_ha:[true,false,false],municipality_id:["ES:MUN:1",null,"ES:MUN:2"],reported_forest_area_ha:[10,null,0]};
const aggregate = summarizeInitialAssets([{asset:manifest.assets[0],data:{columns},lookup:new Map([["egif-record:1",0],["egif-record:2",1],["egif-record:3",2]]),metrics:{raw_bytes:20,fetch_ms:1,parse_ms:1}}],1993,1994);
assert.strictEqual(aggregate.records,3); assert.strictEqual(aggregate.administrative_gif,1); assert.strictEqual(aggregate.municipality_resolved,2); assert.strictEqual(aggregate.known_forest_area_sum,10); assert.strictEqual(aggregate.records_with_known_forest_area,2); assert.strictEqual(aggregate.records_with_unknown_forest_area,1);
let calls=0; let delayedResolve;
const payloadFor = (id) => ({ asset_id:id, columns:{record_id:[`egif-record:${id}`],year:[1993],is_gif_forest_ge_500_ha:[false],municipality_id:[null],reported_forest_area_ha:[0]} });
const fetchImpl = (url) => {
  calls += 1;
  if (url.endsWith("manifest.json")) return Promise.resolve({ok:true,text:async()=>JSON.stringify(manifest)});
  if (url.includes("/a/")) return new Promise((resolve)=>{ delayedResolve=()=>resolve({ok:true,text:async()=>JSON.stringify(payloadFor("a"))}); });
  return Promise.resolve({ok:true,text:async()=>JSON.stringify(payloadFor("b"))});
};
const loader = new EGIFInitialLoader({manifestUrl:"http://local/manifest.json",fetchImpl,AbortControllerImpl:AbortControllerFake});
const first = loader.loadScope({territoryId:"ES:CCAA:10",fromYear:1993,toYear:1993});
await new Promise((resolve) => setTimeout(resolve, 0));
const second = loader.loadScope({territoryId:"ES:CCAA:12",fromYear:1993,toYear:1993});
delayedResolve();
const [oldResult,newResult] = await Promise.all([first,second]);
assert.strictEqual(oldResult.status,"stale"); assert.strictEqual(newResult.status,"complete"); assert.strictEqual(newResult.summary.records,1);
await loader.loadScope({territoryId:"ES:CCAA:12",fromYear:1993,toYear:1993});
assert.strictEqual(calls,3); // manifest + asset a abortada + asset b cacheada
console.log(JSON.stringify({valid:true}));
}
main().catch((error) => { console.error(error); process.exit(1); });
'''


class ES4C1B1InitialLoaderTests(unittest.TestCase):
    def test_loader_contract_resolver_columnar_cache_and_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "loader-test.mjs"
            script.write_text(NODE_TEST.replace("__LOADER_URL__", LOADER_URL), encoding="utf-8")
            result = subprocess.run(
                ["node", "--experimental-modules", str(script)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"valid": True}, json.loads(result.stdout))

    def test_initial_loader_keeps_detail_out_of_its_own_contract_and_public_frontend_untouched(self):
        loader = (ROOT / "prototypes/es4c/egif_initial_loader.mjs").read_text(encoding="utf-8")
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("initial.path", loader)
        self.assertNotIn("detail.path", loader)
        self.assertIn("territory_scope", app)
        self.assertNotIn("prototypes/es4c", public_index)


if __name__ == "__main__":
    unittest.main()
