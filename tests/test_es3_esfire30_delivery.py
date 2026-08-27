import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts/audit/spain/es3_esfire30_delivery.py"
    spec = importlib.util.spec_from_file_location("es3_esfire30_delivery", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ES3DeliveryContractTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_temporal_blocks_cover_the_snapshot_without_overlap(self):
        self.assertEqual("1985-1992", self.module.block_for(1985))
        self.assertEqual("1985-1992", self.module.block_for(1992))
        self.assertEqual("1993-2000", self.module.block_for(1993))
        self.assertEqual("2001-2010", self.module.block_for(2010))
        self.assertEqual("2011-2021", self.module.block_for(2021))
        with self.assertRaises(ValueError):
            self.module.block_for(1984)

    def test_geometry_id_is_snapshot_stable_and_source_separated(self):
        self.assertEqual("esfire30:v1:1986:412", self.module.stable_geometry_id(1986, 412))
        self.assertNotEqual(
            self.module.stable_geometry_id(1992, 1),
            self.module.stable_geometry_id(1993, 1),
        )

    def test_es3_script_explicitly_preserves_delivery_not_administrative_semantics(self):
        text = (ROOT / "scripts/audit/spain/es3_esfire30_delivery.py").read_text(encoding="utf-8")
        self.assertIn("documented_remote_sensing_perimeter", text)
        self.assertIn("no clipping", text)
        self.assertIn("No asset is production-ready", text)

    def test_public_frontend_is_not_an_es3_benchmark_target(self):
        text = (ROOT / "benchmarks/es3/vector_benchmark.html").read_text(encoding="utf-8")
        self.assertIn("data/derived/spain/es3", text)
        self.assertNotIn("public-data-v5", text)

    def test_approved_delivery_decisions_are_documented_without_migrating_leaflet(self):
        report = (ROOT / "ES_3_ESFIRE30_DELIVERY_BENCHMARK.md").read_text(encoding="utf-8")
        decision = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
        architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
        self.assertIn("NOT_RECOMMENDED", report)
        self.assertIn("RECOMMENDED para provincia/local", report)
        self.assertIn("RECOMMENDED para España/overview/regional", report)
        self.assertIn("PMTiles de fidelidad", architecture)
        self.assertIn("no se migra aún el visor valenciano", decision)
        self.assertIn("100 m no se usa para\ndetalle", decision)
        self.assertIn("GitHub Pages sigue pendiente", decision)


if __name__ == "__main__":
    unittest.main()
