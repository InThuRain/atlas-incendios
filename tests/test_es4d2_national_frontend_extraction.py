import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_URL = (ROOT / "src/national/asset-config.mjs").as_uri()
REGISTRY_URL = (ROOT / "src/national/source-registry.mjs").as_uri()
BUILD = ROOT / "scripts/build_national_frontend.py"


NODE_CONTRACT = r'''
import assert from "assert";
import { LOCAL_ASSET_CONFIG, PMTILES_BYTES, PMTILES_PRODUCTION_PATH, PMTILES_SHA256, resolveAssetConfig } from "__CONFIG_URL__";
import { NATIONAL_SOURCE_REGISTRY, sourceFor } from "__REGISTRY_URL__";
const config = resolveAssetConfig({asset_base_url:"/national-preview/"});
assert.strictEqual(config.assets.esfire30.pmtiles.path, "/national-preview/data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles");
assert.strictEqual(config.pmtiles_protocol_module, "/national-preview/data/derived/spain/es3/tools/browser/pmtiles-4.3.0.mjs");
assert.strictEqual(PMTILES_BYTES, 63052056);
assert.strictEqual(config.assets.esfire30.pmtiles.sha256, PMTILES_SHA256);
assert.ok(PMTILES_PRODUCTION_PATH.includes(PMTILES_SHA256));
assert.deepStrictEqual(Object.keys(NATIONAL_SOURCE_REGISTRY).sort(), ["bdlje", "effis", "egif", "esfire30", "icv", "protomaps"]);
assert.strictEqual(sourceFor("protomaps").role, "cartographic_context");
assert.strictEqual(sourceFor("protomaps").wildfire_source, false);
assert.strictEqual(sourceFor("egif").coverage.from, 1968);
assert.strictEqual(sourceFor("esfire30").coverage.to, 2021);
assert.strictEqual(sourceFor("icv").coverage.to, 2024);
assert.strictEqual(sourceFor("effis").coverage.from, 2025);
console.log(JSON.stringify({valid:true, base:LOCAL_ASSET_CONFIG.asset_base_url}));
'''


class ES4D2NationalFrontendExtractionTests(unittest.TestCase):
    def test_asset_config_and_source_registry_are_central_and_extensible(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "contract.mjs"
            script.write_text(
                NODE_CONTRACT.replace("__CONFIG_URL__", CONFIG_URL).replace("__REGISTRY_URL__", REGISTRY_URL),
                encoding="utf-8",
            )
            result = subprocess.run(["node", "--experimental-modules", str(script)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_entrypoint_is_independent_from_prototype_html_and_has_no_staging_url(self):
        entry = (ROOT / "src/national/index.html").read_text(encoding="utf-8")
        bootstrap = (ROOT / "src/national/bootstrap.js").read_text(encoding="utf-8")
        for required in ("id=\"map\"", "id=\"territory-scope\"", "id=\"egif-record-browser\"", "id=\"runtime-test-output\"", "bootstrap.js"):
            self.assertIn(required, entry)
        self.assertNotIn("debug-output", entry)
        self.assertNotIn("prototypes/es4c/index.html", entry)
        self.assertIn("runtime_entry", bootstrap)
        for path in ROOT.joinpath("src/national").rglob("*"):
            if path.is_file():
                self.assertNotIn("r2.dev", path.read_text(encoding="utf-8"))
                self.assertNotIn("github.io/atlas-incendios-es4c3d4-pages-staging", path.read_text(encoding="utf-8"))

    def test_static_artifact_is_reproducible_and_excludes_large_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "national"
            build = subprocess.run([sys.executable, str(BUILD), "--output", str(output)], capture_output=True, text=True, check=False)
            self.assertEqual(build.returncode, 0, build.stderr)
            checked = subprocess.run([sys.executable, str(BUILD), "--check", "--output", str(output)], capture_output=True, text=True, check=False)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            manifest = json.loads((output / "asset-manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["large_assets_included"])
        self.assertEqual(manifest["logical_asset_config"]["assets"]["esfire30"]["pmtiles"]["bytes"], 63052056)
        # D4A reutiliza este frontend bajo un base path de Pages: los paths
        # runtime son relativos y no codifican el nombre de ningún repositorio.
        self.assertTrue(manifest["logical_asset_config"]["assets"]["esfire30"]["pmtiles"]["path"].startswith("data/esfire30/v1/"))
        self.assertIn("runtime/app.js", {entry["path"] for entry in manifest["files"]})
        self.assertIn("vendor/node_modules/fflate/index.js", {entry["path"] for entry in manifest["files"]})


if __name__ == "__main__":
    unittest.main()
