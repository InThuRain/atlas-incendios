import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERIALIZER_URL = (ROOT / "prototypes/es4c/state_serialization.mjs").as_uri()


NODE_TEST = r'''
import assert from "assert";
import { canonicalPayload, parseStateHash, serializeState, STATE_VERSION } from "__SERIALIZER_URL__";
const defaults={center:[-3.7,40.3],zoom:4,from:1985,to:2021,territory_scope:"ES",autonomous_community_id:null,esfire30_visible:true,egif_visible:true,selected_geometry_id:null,selected_egif_record_id:null};
const state={...defaults,center:[-0.1234567,39.9876543],zoom:7.123,from:1995,to:1995,territory_scope:"autonomous_community",autonomous_community_id:"ES:CCAA:10",egif_visible:false,selected_geometry_id:"esfire30:v1:1995:86",selected_egif_record_id:"egif-record:1995030001"};
const hash=serializeState(state); assert.ok(hash.startsWith("#es4c-state-v1=")); assert.strictEqual(hash,serializeState({...state,center:[-0.12345671,39.98765431]}));
const parsed=parseStateHash(hash,defaults,new Set(["ES:CCAA:10"])); assert.strictEqual(parsed.status,"complete"); assert.deepStrictEqual(parsed.state.center,[-0.12346,39.98765]); assert.strictEqual(parsed.state.selected_egif_record_id,"egif-record:1995030001");
assert.strictEqual(canonicalPayload(state).v,STATE_VERSION);
assert.strictEqual(parseStateHash("#es4c-state-v2=bad",defaults,new Set()).status,"unknown_version");
assert.strictEqual(parseStateHash("#es4c-state-v1=not-valid",defaults,new Set()).status,"invalid");
const partial='#es4c-state-v1='+Buffer.from(JSON.stringify({v:STATE_VERSION,time:{from:2023,to:1968},map:{lat:200,lon:1,z:99},territory:{scope:"autonomous_community",autonomous_community_id:"bad"},sources:{egif:"true"},selections:{geometry_id:"wrong",egif_record_id:"egif-record:x"}})).toString("base64").replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
const safe=parseStateHash(partial,defaults,new Set(["ES:CCAA:10"])); assert.strictEqual(safe.state.from,defaults.from); assert.deepStrictEqual(safe.state.center,[-3.7,40.3]); assert.strictEqual(safe.state.autonomous_community_id,null); assert.strictEqual(safe.state.selected_geometry_id,null); assert.strictEqual(safe.state.egif_visible,true);
console.log(JSON.stringify({valid:true}));
'''


class ES4C1C2StateSerializationTests(unittest.TestCase):
    def test_round_trip_canonicalization_and_safe_invalid_values(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "serialization-test.mjs"
            script.write_text(NODE_TEST.replace("__SERIALIZER_URL__", SERIALIZER_URL), encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], check=False, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"valid": True}, json.loads(result.stdout))

    def test_serializer_is_prototype_only(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("es4c-state-v1", (ROOT / "prototypes/es4c/state_serialization.mjs").read_text(encoding="utf-8"))
        self.assertIn("history.replaceState", app)
        self.assertNotIn("es4c-state-v1", public_index)


if __name__ == "__main__":
    unittest.main()
