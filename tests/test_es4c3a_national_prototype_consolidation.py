import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_URL = (ROOT / "prototypes/es4c/runtime_state.mjs").as_uri()


NODE_TEST = r'''
import assert from "assert";
import { createRuntimeState, reduceRuntimeState, selectedTerritoryId } from "__STATE_URL__";
let state=createRuntimeState({center:[-3.7,40.3],zoom:4});
assert.strictEqual(selectedTerritoryId(state),"ES");
state=reduceRuntimeState(state,{type:"set_scope",territory_id:"ES:CCAA:10"});
assert.strictEqual(state.territory_scope,"autonomous_community"); assert.strictEqual(state.province_id,null); assert.strictEqual(state.municipality_id,null);
state=reduceRuntimeState(state,{type:"set_province",autonomous_community_id:"ES:CCAA:10",province_id:"ES:PROV:03"});
assert.strictEqual(selectedTerritoryId(state),"ES:PROV:03");
state=reduceRuntimeState(state,{type:"select_egif_record",record_id:"egif-record:1",year:1995});
state=reduceRuntimeState(state,{type:"set_municipality",autonomous_community_id:"ES:CCAA:10",province_id:"ES:PROV:03",municipality_id:"ES:MUN:03065"});
assert.strictEqual(selectedTerritoryId(state),"ES:MUN:03065"); assert.strictEqual(state.selected_egif_record_id,null);
// Ceuta/Melilla no requieren una provincia ficticia.
state=reduceRuntimeState(state,{type:"set_municipality",autonomous_community_id:"ES:CCAA:18",province_id:null,municipality_id:"ES:MUN:51001"});
assert.strictEqual(state.province_id,null); assert.strictEqual(state.autonomous_community_id,"ES:CCAA:18");
state=reduceRuntimeState(state,{type:"set_scope",territory_id:"ES"});
assert.deepStrictEqual({scope:state.territory_scope,ccaa:state.autonomous_community_id,prov:state.province_id,mun:state.municipality_id},{scope:"ES",ccaa:null,prov:null,mun:null});
console.log(JSON.stringify({valid:true}));
'''


class ES4C3APrototypeConsolidationTests(unittest.TestCase):
    def test_canonical_territorial_state_and_selection_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "state.mjs"
            script.write_text(NODE_TEST.replace("__STATE_URL__", STATE_URL), encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"valid": True})

    def test_prototype_has_one_loading_policy_and_remains_isolated(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        smoke = (ROOT / "prototypes/es4c/run_smoke.py").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        for text in ("sourceLoadState", "beginSourceLoad", "finishSourceLoad", "selectedTerritoryId", "municipalityFilterExpression", "Límite municipal BDLJE actual"):
            self.assertIn(text, app)
        self.assertIn("C3A_SMOKES", smoke)
        self.assertIn("c3a_rapid_transition", smoke)
        self.assertNotIn("prototypes/es4c", public_index)


if __name__ == "__main__":
    unittest.main()
