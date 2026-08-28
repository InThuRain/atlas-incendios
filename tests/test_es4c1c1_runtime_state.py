import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_URL = (ROOT / "prototypes/es4c/runtime_state.mjs").as_uri()


NODE_TEST = r'''
import assert from "assert";
import { createRuntimeState, effectiveCoverage, intersectCoverage, reduceRuntimeState } from "__STATE_URL__";
assert.deepStrictEqual(intersectCoverage({from:1980,to:1990},{from:1985,to:2021}),{from:1985,to:1990});
assert.strictEqual(intersectCoverage({from:1975,to:1980},{from:1985,to:2021}),null);
let state=createRuntimeState({from:1975,to:1975});
assert.deepStrictEqual(effectiveCoverage(state,"egif"),{from:1975,to:1975});
assert.strictEqual(effectiveCoverage(state,"esfire30"),null);
state=reduceRuntimeState(state,{type:"set_range",from:1980,to:1990});
assert.deepStrictEqual(effectiveCoverage(state,"egif"),{from:1980,to:1990});
assert.deepStrictEqual(effectiveCoverage(state,"esfire30"),{from:1985,to:1990});
state=reduceRuntimeState(state,{type:"select_geometry",geometry_id:"esfire30:x",year:1986});
state=reduceRuntimeState(state,{type:"select_egif_record",record_id:"egif-record:1",year:1981});
state=reduceRuntimeState(state,{type:"set_visibility",source_id:"esfire30",visible:false});
assert.strictEqual(state.selected_geometry_id,null); assert.strictEqual(state.selected_egif_record_id,"egif-record:1");
state=reduceRuntimeState(state,{type:"set_range",from:1990,to:1991});
assert.strictEqual(state.selected_egif_record_id,null);
state=reduceRuntimeState(state,{type:"set_scope",territory_id:"ES:CCAA:10"});
assert.strictEqual(state.autonomous_community_id,"ES:CCAA:10");
state=reduceRuntimeState(state,{type:"select_egif_record",record_id:"egif-record:2",year:1990});
state=reduceRuntimeState(state,{type:"set_scope",territory_id:"ES:CCAA:12"});
assert.strictEqual(state.selected_egif_record_id,null);
console.log(JSON.stringify({valid:true}));
'''


class ES4C1C1RuntimeStateTests(unittest.TestCase):
    def test_coverage_state_toggles_and_invalidations(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "state-test.mjs"
            script.write_text(NODE_TEST.replace("__STATE_URL__", STATE_URL), encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], check=False, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"valid": True}, json.loads(result.stdout))

    def test_runtime_isolated_and_has_independent_source_contracts(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        state = (ROOT / "prototypes/es4c/runtime_state.mjs").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("esfire30_visible", state)
        self.assertIn("egif_visible", state)
        self.assertIn("selected_geometry_id", state)
        self.assertIn("selected_egif_record_id", state)
        self.assertIn("effectiveCoverage", app)
        self.assertNotIn("prototypes/es4c", public_index)


if __name__ == "__main__":
    unittest.main()
