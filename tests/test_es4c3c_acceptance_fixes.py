import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER_URL = (ROOT / "prototypes/es4c/municipality_loader.mjs").as_uri()


NODE_TEST = r'''
import assert from "assert";
import { TextEncoder } from "util";
import { MunicipalityLoader } from "__LOADER_URL__";
global.TextEncoder = TextEncoder;
global.performance = { now: (() => { let n = 0; return () => ++n; })() };
class AbortControllerFake { constructor(){this.signal={aborted:false};} abort(){this.signal.aborted=true;} }
const rows=[
  {municipality_id:"ES:MUN:03065",province_id:"ES:PROV:03",autonomous_community_id:"ES:CCAA:10",official_name:"Elx",bounds:[-1,38,0,39],asset_id:"municipalities:ES:PROV:03"},
  ...Array.from({length:8131},(_,i)=>({municipality_id:`ES:MUN:${String(60000+i).padStart(5,"0")}`,province_id:"ES:PROV:03",autonomous_community_id:"ES:CCAA:10",official_name:`x${i}`,bounds:[0,0,1,1],asset_id:"municipalities:ES:PROV:03"}))
];
let shardRequests=0;
const response=(data)=>({ok:true,text:async()=>JSON.stringify(data)});
const fetchImpl=async (url)=>{
  if(url.includes("municipality_catalog")) return response({municipalities:rows});
  shardRequests += 1;
  if(shardRequests === 1) return {ok:false,status:503,text:async()=>""};
  return response({features:[{properties:{municipality_id:"ES:MUN:03065"},geometry:{type:"Polygon",coordinates:[]}}]});
};
async function main() {
  const loader=new MunicipalityLoader({fetchImpl,AbortControllerImpl:AbortControllerFake});
  let failed=false;
  try { await loader.loadForParent({provinceId:"ES:PROV:03"}); } catch(error) { failed=String(error.message).includes("503"); }
  assert.strictEqual(failed,true);
  assert.strictEqual(loader.assetCache.has("municipalities:ES:PROV:03"),false);
  const retried=await loader.loadForParent({provinceId:"ES:PROV:03"});
  assert.strictEqual(retried.status,"complete");
  assert.strictEqual(retried.shard.data.features[0].properties.municipality_id,"ES:MUN:03065");
  console.log(JSON.stringify({valid:true,shardRequests}));
}
main().catch((error)=>{console.error(error);process.exit(1);});
'''


class ES4C3CAcceptanceFixTests(unittest.TestCase):
    def test_municipal_failure_is_not_cached_and_retry_can_succeed(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "municipal-retry.mjs"
            script.write_text(NODE_TEST.replace("__LOADER_URL__", LOADER_URL), encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_runtime_contains_transactional_municipality_and_pmtiles_error_contracts(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        for contract in (
            "municipalityParentEvent",
            "expectedMunicipalityId",
            "El shard municipal no contiene",
            "markEsfireTransportError",
            "isEsfireTransportError",
            "esfireTransportError",
            "ESFire30 no disponible por error de carga",
        ):
            self.assertIn(contract, app)


if __name__ == "__main__":
    unittest.main()
