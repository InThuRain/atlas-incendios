import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "prototypes/es4c/run_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4c1a_runtime", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNTIME = load_module()


class ES4C1ARuntimeTests(unittest.TestCase):
    def test_fidelity_asset_matches_es3_provenance(self):
        source = json.loads((ROOT / "benchmarks/es3/results.json").read_text(encoding="utf-8"))
        candidate = source["pmtiles"]["fidelity_candidate"]
        self.assertEqual(RUNTIME.BASELINE_EXPECTED_SHA256, candidate["sha256"])
        self.assertEqual(61347888, candidate["bytes"])
        self.assertTrue(RUNTIME.BASELINE_ARCHIVE.is_file())
        self.assertEqual(candidate["sha256"], RUNTIME.sha256(RUNTIME.BASELINE_ARCHIVE))

    def test_range_parser_preserves_http_inclusive_bounds(self):
        self.assertEqual((5, 9), RUNTIME.parse_single_range("bytes=5-9", 10))
        self.assertEqual((5, 9), RUNTIME.parse_single_range("bytes=5-", 10))
        self.assertEqual((7, 9), RUNTIME.parse_single_range("bytes=-3", 10))
        self.assertIsNone(RUNTIME.parse_single_range(None, 10))

    def test_prototype_keeps_documented_remote_sensing_and_stable_property_selection(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        public_index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('geometry_semantics: "documented_remote_sensing_perimeter"', app)
        self.assertIn('properties?.geometry_id', app)
        self.assertIn('filter: ["==", ["get", "geometry_id"], "__none__"]', app)
        self.assertNotIn("prototypes/es4c", public_index)


if __name__ == "__main__":
    unittest.main()
