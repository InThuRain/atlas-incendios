import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DETAIL_URL = (ROOT / "prototypes/es4c/egif_detail_loader.mjs").as_uri()


NODE_TEST = r'''
import assert from "assert";
import { TextEncoder } from "util";
import { locateRecord, selectedInitialRow, pageOfInitialRows, EGIFDetailLoader } from "__DETAIL_URL__";
global.performance = { now: (() => { let value=0; return () => ++value; })() };
global.TextEncoder = TextEncoder;
class AbortControllerFake { constructor(){ this.signal={aborted:false}; } abort(){ this.signal.aborted=true; } }
const asset = {asset_id:"egif:ES:CCAA:10:1993-2002",record_count:3,initial:{path:"asset/initial.json",record_id_order_sha256:"same"},detail:{path:"asset/detail.json",gzip_size:7}};
const initial = {asset, data:{columns:{record_id:["egif-record:1","egif-record:2","egif-record:3"],year:[1993,1994,1994],autonomous_community_id:["ES:CCAA:10","ES:CCAA:10","ES:CCAA:10"],province_id:["ES:PROV:03","ES:PROV:03","ES:PROV:03"],municipality_id:["ES:MUN:03001",null,"ES:MUN:03002"],reported_forest_area_ha:[0,null,5],is_gif_forest_ge_500_ha:[false,null,false],cause_source_code:["01","02","03"],canonical_cause:[null,null,null],cause_mapping_status:["unmapped","unmapped","unmapped"]}}, lookup:new Map([["egif-record:1",0],["egif-record:2",1],["egif-record:3",2]])};
assert.strictEqual(locateRecord([initial],"egif-record:2").ordinal,1);
assert.strictEqual(selectedInitialRow(initial,0).reported_forest_area_ha,0);
assert.strictEqual(selectedInitialRow(initial,1).reported_forest_area_ha,null);
const page=pageOfInitialRows([initial],1993,1994,0,2); assert.strictEqual(page.total,3); assert.deepStrictEqual(page.rows.map((row)=>row.record_id),["egif-record:1","egif-record:2"]);
let requests=0;
const detail = {asset_id:asset.asset_id,role:"detail_on_selection",initial_record_id_order_sha256:"same",ordinal_alignment:"same_sorted_record_id_order_as_initial",fields:["source_record_id","source_municipality_name","reported_total_area_ha"],columns:{source_record_id:["1","2","3"],source_municipality_name:["Original 1","Original 2","Original 3"],reported_total_area_ha:[0,null,9]}};
const fetchImpl = async () => { requests += 1; return {ok:true,text:async()=>JSON.stringify(detail)}; };
async function main() {
const loader=new EGIFDetailLoader({manifestUrl:"http://local/manifest.json",fetchImpl,AbortControllerImpl:AbortControllerFake});
const first=await loader.select({recordId:"egif-record:2",loadedAssets:[initial]});
assert.strictEqual(first.record.municipality_id,null); assert.strictEqual(first.record.reported_total_area_ha,null); assert.strictEqual(first.record.canonical_cause,null); assert.strictEqual(first.record.cause_mapping_status,"unmapped");
const second=await loader.select({recordId:"egif-record:3",loadedAssets:[initial]});
assert.strictEqual(second.metrics.cached,true); assert.strictEqual(requests,1);
assert.throws(()=>locateRecord([],"egif-record:1").ordinal);
console.log(JSON.stringify({valid:true}));
}
main().catch((error) => { console.error(error); process.exit(1); });
'''


class ES4C1B2DetailLoaderTests(unittest.TestCase):
    def test_detail_lookup_pagination_nulls_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "detail-test.mjs"
            script.write_text(NODE_TEST.replace("__DETAIL_URL__", DETAIL_URL), encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], check=False, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"valid": True}, json.loads(result.stdout))

    def test_detail_runtime_is_isolated_from_public_frontend_and_semantics(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        detail = (ROOT / "prototypes/es4c/egif_detail_loader.mjs").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("selected_egif_record_id", app)
        self.assertIn("selected_geometry_id", app)
        self.assertIn("detail.path", detail)
        self.assertNotIn("spatial_reference_id", detail)
        self.assertNotIn("prototypes/es4c", public_index)


if __name__ == "__main__":
    unittest.main()
