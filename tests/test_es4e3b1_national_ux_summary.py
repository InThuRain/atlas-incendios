import importlib.util
import json
import unittest
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_national_ux_summary.py"
OUTPUT = ROOT / "data/derived/spain/national-ux-summary-v1"


def load_builder():
    spec = importlib.util.spec_from_file_location("es4e3b1_summary", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def territory(path, territory_id):
    payload = json.loads((OUTPUT / path).read_text(encoding="utf-8"))
    return next(row for row in payload["territories"] if row["territory"]["territory_id"] == territory_id)


def source(row, source_id):
    return next(item for item in row["source_summaries"] if item["source_id"] == source_id)


def metric_value(row, source_id, metric_id, year):
    summary = source(row, source_id)
    metric = next(item for item in summary["metrics"] if item["metric_id"] == metric_id)
    return metric["values"][year - summary["year_axis"]["from"]]


class ES4E3B1NationalUxSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))

    def test_check_schema_metrics_and_no_combined_totals(self):
        result = self.builder.check()
        self.assertTrue(result["valid"], result)
        self.assertEqual("national-ux-summary-v1", self.manifest["schema_version"])
        self.assertEqual(122, self.manifest["payload_file_count"])
        seen = set()
        for file_row in self.manifest["files"]:
            payload = json.loads((OUTPUT / file_row["path"]).read_text(encoding="utf-8"))
            self.assertIn(payload["scope"], {"territory", "municipalities_by_parent"})
            for row in payload["territories"]:
                for summary in row["source_summaries"]:
                    start, end = summary["coverage"]["from"], summary["coverage"]["to"]
                    for item in summary["metrics"]:
                        seen.add(item["metric_id"])
                        self.assertIn(item["metric_id"], self.builder.ALLOWED_METRICS)
                        self.assertNotIn("combined", item["metric_id"])
                        self.assertEqual(end - start + 1, len(item["values"]))
        self.assertEqual(self.builder.ALLOWED_METRICS, seen)
        self.assertFalse(self.manifest["semantics"]["cross_source_sum_allowed"])

    def test_source_reconciliation_and_icv_one_to_many(self):
        rec = self.manifest["source_reconciliation"]
        self.assertEqual({"source_records": 646887, "municipality_unresolved": 71490}, rec["egif"])
        self.assertEqual(119498, rec["esfire30"]["geometries"])
        self.assertEqual(120847, rec["esfire30"]["ccaa_relations"])
        self.assertEqual(121887, rec["esfire30"]["province_relations"])
        self.assertEqual(143477, rec["esfire30"]["municipality_relations"])
        self.assertEqual(13738, rec["icv"]["fire_records"])
        self.assertEqual(13739, rec["icv"]["geometries"])
        self.assertEqual({"fire_record_count": 1, "geometry_count": 2}, rec["icv"]["control_2024AL0005"])
        self.assertEqual({"2025": 9, "2026": 16}, rec["effis"]["annual_geometries"])

    def test_zero_unknown_and_coverage_semantics(self):
        stats = defaultdict(self.builder.blank_stats)
        stats[2000]["records"] = 1
        stats[2000]["area_unknown"] = 1
        stats[2001]["records"] = 1
        stats[2001]["area_known"] = 1
        stats[2001]["area_sum"] = Decimal("0")
        self.assertEqual([None, 0], self.builder.annual_values(stats, (2000, 2001), "area_sum", area=True))
        baleares = source(territory("ccaa/ES-CCAA-04.json", "ES:CCAA:04"), "esfire30")
        self.assertEqual("no_source_coverage", baleares["coverage"]["status"])
        self.assertEqual([], baleares["metrics"])
        agost = source(territory("municipalities/by-parent/ES-PROV-03.json", "ES:MUN:03002"), "esfire30")
        self.assertEqual("available", agost["coverage"]["status"])
        self.assertEqual(0, sum(agost["metrics"][0]["values"]))

    def test_known_contract_examples_and_territorial_samples(self):
        spain = territory("national.json", "ES")
        gva = territory("ccaa/ES-CCAA-10.json", "ES:CCAA:10")
        galicia = territory("ccaa/ES-CCAA-12.json", "ES:CCAA:12")
        ourense = territory("provinces/ES-PROV-32.json", "ES:PROV:32")
        elx = territory("municipalities/by-parent/ES-PROV-03.json", "ES:MUN:03065")
        cangas = territory("municipalities/by-parent/ES-PROV-33.json", "ES:MUN:33011")
        self.assertEqual(4128, metric_value(spain, "egif", "egif_record_count", 1975))
        self.assertEqual(25557, metric_value(spain, "egif", "egif_record_count", 1995))
        self.assertEqual(467, metric_value(gva, "egif", "egif_record_count", 1995))
        self.assertEqual(467, metric_value(gva, "icv", "icv_fire_record_count", 1995))
        self.assertEqual(472, metric_value(gva, "icv", "icv_fire_record_count", 2024))
        self.assertEqual(16, metric_value(gva, "effis", "effis_perimeter_count", 2026))
        self.assertEqual(38645, sum(source(galicia, "esfire30")["metrics"][0]["values"]))
        self.assertEqual(16265, sum(source(ourense, "esfire30")["metrics"][0]["values"]))
        self.assertEqual(6, sum(source(elx, "esfire30")["metrics"][0]["values"]))
        self.assertEqual(1, metric_value(elx, "effis", "effis_perimeter_count", 2025))
        self.assertEqual(2610, sum(source(cangas, "esfire30")["metrics"][0]["values"]))

    def test_canonical_identity_is_order_independent(self):
        self.assertEqual(self.builder.canonical_bytes({"b": 2, "a": 1}), self.builder.canonical_bytes({"a": 1, "b": 2}))
        rows = self.manifest["files"]
        self.assertEqual(sorted(row["path"] for row in rows), [row["path"] for row in rows])
        fingerprint_rows = [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in rows]
        import hashlib
        self.assertEqual(self.manifest["fingerprint"], hashlib.sha256(self.builder.canonical_bytes(fingerprint_rows)).hexdigest())


if __name__ == "__main__":
    unittest.main()
