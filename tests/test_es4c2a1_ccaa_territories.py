import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/territories/build_ccaa_prototype.py"
LAYER_URL = (ROOT / "prototypes/es4c/territory_layer.mjs").as_uri()


def polygon(x, y):
    return {"type": "Polygon", "coordinates": [[[x, y], [x + .1, y], [x + .1, y + .1], [x, y + .1], [x, y]]]}


class ES4C2A1CCAATerritoriesTests(unittest.TestCase):
    def test_builder_crosswalk_bounds_and_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            features = []
            territories = []
            for number in range(1, 20):
                code = f"{number:02d}"
                geometry = polygon(number, 30)
                if code == "05":
                    geometry = {"type": "MultiPolygon", "coordinates": [polygon(1, 28)["coordinates"], polygon(2, 28)["coordinates"]]}
                features.append({"type": "Feature", "properties": {"nationalcode": f"34{code}0000000", "nameunit": f"Fuente {code}", "nationallevelname": "Comunidad autónoma"}, "geometry": geometry})
                territories.append({"territory_id": f"ES:CCAA:{code}", "official_code": code, "official_name": f"Canónico {code}", "territory_type": "autonomous_city" if code in {"18", "19"} else "autonomous_community"})
            features.append({"type": "Feature", "properties": {"nationalcode": "34200000000", "nameunit": "Territorios no asociados a ninguna autonomía", "nationallevelname": "Comunidad autónoma"}, "geometry": polygon(25, 30)})
            source = directory / "source.geojson"; source.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
            snapshot = directory / "snapshot.json"; snapshot.write_text(json.dumps({"territories": territories}), encoding="utf-8")
            output = directory / "ccaa.geojson"; manifest = directory / "manifest.json"
            command = ["python3", str(BUILDER), "--source", str(source), "--snapshot", str(snapshot), "--output", str(output), "--manifest", str(manifest), "--tolerance-m", "0"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            checked = subprocess.run(command + ["--check"], capture_output=True, text=True)
            self.assertEqual(0, checked.returncode, checked.stderr)
            collection = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(19, len(collection["features"]))
            self.assertEqual("ES:CCAA:05", collection["features"][4]["properties"]["territory_id"])
            self.assertEqual("MultiPolygon", collection["features"][4]["geometry"]["type"])
            ceuta = next(row for row in collection["features"] if row["properties"]["territory_id"] == "ES:CCAA:18")
            self.assertEqual("autonomous_city", ceuta["properties"]["territory_type"])
            written = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertTrue(written["validation"]["multiparts_preserved"])
            self.assertEqual("Obra derivada de BDLJE CC-BY 4.0 ign.es", written["source"]["attribution"])

    def test_layer_selects_by_official_territory_id_and_fits_bounds(self):
        program = r'''
import assert from "assert";
import { addOfficialTerritoryLayer, CCAA_SELECTED_LAYER } from "__LAYER_URL__";
(async () => {
  const features=Array.from({length:19},(_,index)=>({type:"Feature",properties:{territory_id:`ES:CCAA:${String(index+1).padStart(2,"0")}`,bounds:[index,30,index+.5,31]},geometry:{type:"Polygon",coordinates:[]}}));
  const events={}; const calls=[]; let selected=null;
  const map={addSource:(...x)=>calls.push(["source",...x]),addLayer:(x)=>calls.push(["layer",x]),on:(event,layer,callback)=>events[`${event}:${layer}`]=callback,getCanvas:()=>({style:{}}),setFilter:(...x)=>calls.push(["filter",...x]),fitBounds:(...x)=>calls.push(["fit",...x])};
  const layer=await addOfficialTerritoryLayer(map,{fetchImpl:async()=>({ok:true,json:async()=>({features,metadata:{national_bounds:[-10,20,5,45]}})}),onSelect:(id)=>selected=id});
  layer.setSelected("ES:CCAA:10"); assert.strictEqual(calls.filter(x=>x[0]==="filter").pop()[1],CCAA_SELECTED_LAYER);
  events["click:official-ccaa-territories-fill"]({features:[features[9]]}); assert.strictEqual(selected,"ES:CCAA:10");
  assert.strictEqual(layer.fit("ES:CCAA:05"),true); assert.deepStrictEqual(calls.filter(x=>x[0]==="fit").pop()[1],[[4,30],[4.5,31]]);
  assert.strictEqual(layer.fit("ES"),true); console.log(JSON.stringify({valid:true}));
})().catch((error) => { console.error(error); process.exit(1); });
'''.replace("__LAYER_URL__", LAYER_URL)
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "territory-layer-test.mjs"
            script.write_text(program, encoding="utf-8")
            result = subprocess.run(["node", "--experimental-modules", str(script)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"valid": True}, json.loads(result.stdout))

    def test_prototype_keeps_esfire30_territorial_filter_explicitly_out_of_scope(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        html = (ROOT / "prototypes/es4c/index.html").read_text(encoding="utf-8")
        self.assertIn("syncTerritoryLayer({ fit });", app)
        self.assertIn("no se filtra territorialmente", html)
        self.assertNotIn("primary_autonomous_community", app)


if __name__ == "__main__":
    unittest.main()
