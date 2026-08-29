import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/territories/audit_municipality_geometry_full.py"


def module():
    spec = importlib.util.spec_from_file_location("es4c2a3b_municipal_geometry_full", SCRIPT)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


MODULE = module()


class ES4C2A3BMunicipalityGeometryFullTests(unittest.TestCase):
    def test_shard_assignment_keeps_autonomous_cities_out_of_province_assets(self):
        self.assertEqual(("ES:PROV:03", "ES-PROV-03", "ES:PROV:03"), MODULE.shard_key("10", "03"))
        self.assertEqual(("ES:CCAA:18", "ES-CCAA-18", None), MODULE.shard_key("18", "51"))
        self.assertEqual(("ES:CCAA:19", "ES-CCAA-19", None), MODULE.shard_key("19", "52"))
        self.assertEqual("literal_prefix:Comunidad", MODULE.non_municipal_label("Comunidad de prueba"))

    def test_stream_reader_and_shard_writer_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.geojson"
            source.write_text('{"type":"FeatureCollection","features":[{"type":"Feature","id":"b"},{"type":"Feature","id":"a"}]}\n', encoding="utf-8")
            self.assertEqual(["b", "a"], [feature["id"] for feature in MODULE.iter_features(source)])
            lines = root / "rows.jsonl"
            lines.write_text('ES:MUN:00002\t{"id":"b"}\nES:MUN:00001\t{"id":"a"}\n', encoding="utf-8")
            output = root / "shard.geojson"
            first = MODULE.write_shard(lines, output)
            self.assertEqual({"type": "FeatureCollection", "features": [{"id": "a"}, {"id": "b"}]}, json.loads(output.read_text(encoding="utf-8")))
            self.assertEqual((len(output.read_bytes()), MODULE.sha256(output)), first)

    def test_full_audit_reconciles_shards_catalog_and_controls(self):
        audit = json.loads(MODULE.AUDIT.read_text(encoding="utf-8"))
        self.assertEqual(8213, audit["reconciliation"]["source_features"])
        self.assertEqual({"MATCHED_CURRENT": 8132, "NON_MUNICIPAL_UNIT": 81}, audit["reconciliation"]["classification"])
        self.assertEqual(8132, audit["shards_0m"]["totals"]["municipalities"])
        self.assertEqual(8132, audit["catalog"]["records"])
        self.assertEqual(0, audit["geometry"]["invalid"])
        self.assertEqual(0, audit["geometry"]["null"])
        self.assertIn("Llocnou de la Corona", audit["controls"])
        self.assertEqual(52, audit["shards_0m"]["totals"]["shards"])

    def test_partition_measurement_keeps_province_delivery_and_does_not_invent_pmtiles(self):
        audit = json.loads(MODULE.AUDIT.read_text(encoding="utf-8"))
        sizes = audit["partition_comparison"]
        self.assertEqual(146192799, sizes["national_single_geojson_0m"]["raw_bytes"])
        self.assertEqual(46636931, sizes["national_single_geojson_0m"]["gzip_bytes"])
        self.assertEqual(19, len(sizes["ccaa_geojson_0m"]))
        self.assertEqual(52, sizes["province_or_autonomous_city_geojson_0m"]["assets"])
        self.assertFalse(sizes["administrative_pmtiles"]["measured"])


if __name__ == "__main__":
    unittest.main()
