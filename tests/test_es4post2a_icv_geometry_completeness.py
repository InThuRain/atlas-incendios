"""Focused ES-4POST2A contracts; they never rebuild or download ICV."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIRES = ROOT / "data/web/gva/fires.json"
CROSSWALK = (ROOT / "prototypes/es4c/icv_territory_crosswalk.mjs").as_uri()
FILTERS = (ROOT / "prototypes/es4c/source_filters.mjs").as_uri()
LOADER = ROOT / "prototypes/es4c/icv_loader.mjs"
BUILDER = ROOT / "scripts/build_national_frontend.py"

# Fixture de regresión POST1: ésta era exactamente la tabla incompleta que
# aplicaba el loader antes de POST2A. La prueba conserva la evidencia del
# 12.404 / 12.405 y demuestra que el crosswalk actual no puede volver a ella.
PRE_FIX_RAW_VALUES = {"Alicante/Alacant", "Castellón/Castelló", "Valencia/València"}
EXPECTED_BY_YEAR = {2016: 341, 2017: 346, 2018: 375, 2019: 272}
EXPECTED_BY_RAW = {"ALICANTE": 338, "CASTELLON": 273, "Castellon": 1, "VALENCIA": 722}
EXPECTED_MAPPING = {
    "ALICANTE": "ES:PROV:03", "Alicante/Alacant": "ES:PROV:03",
    "CASTELLON": "ES:PROV:12", "Castellon": "ES:PROV:12", "Castellón/Castelló": "ES:PROV:12",
    "VALENCIA": "ES:PROV:46", "Valencia/València": "ES:PROV:46",
}


def resolve_in_node(values: list[object]) -> list[object]:
    script = (
        f'import {{ resolveIcvProvince }} from "{CROSSWALK}";\n'
        f'const values = {json.dumps(values, ensure_ascii=False)};\n'
        'console.log(JSON.stringify(values.map(value => resolveIcvProvince(value))));\n'
    )
    with tempfile.TemporaryDirectory() as directory:
        module = Path(directory) / "crosswalk-contract.mjs"
        module.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", "--experimental-modules", str(module)], text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def matches_filters_in_node(record: dict, filters: list[dict]) -> bool:
    script = (
        f'import {{ recordMatchesSourceFilters }} from "{FILTERS}";\n'
        f'const record = {json.dumps(record, ensure_ascii=False)};\n'
        f'const filters = {json.dumps(filters, ensure_ascii=False)};\n'
        'console.log(JSON.stringify(recordMatchesSourceFilters("icv", record, filters)));\n'
    )
    with tempfile.TemporaryDirectory() as directory:
        module = Path(directory) / "filters-contract.mjs"
        module.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", "--experimental-modules", str(module)], text=True, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class IcvGeometryCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fires = json.loads(FIRES.read_text(encoding="utf-8"))["fires"]

    def test_pre_fix_regression_fixture_and_canonical_total(self):
        pre_fix = [row for row in self.fires if row["province"] in PRE_FIX_RAW_VALUES]
        self.assertEqual((len(pre_fix), sum(len(row["geometry_ids"]) for row in pre_fix)), (12404, 12405))
        self.assertEqual((len(self.fires), sum(len(row["geometry_ids"]) for row in self.fires)), (13738, 13739))
        recovered = [row for row in self.fires if row["province"] not in PRE_FIX_RAW_VALUES]
        self.assertEqual((len(recovered), sum(len(row["geometry_ids"]) for row in recovered)), (1334, 1334))
        self.assertEqual(Counter(row["year"] for row in recovered), EXPECTED_BY_YEAR)
        self.assertEqual(Counter(row["province"] for row in recovered), EXPECTED_BY_RAW)

    def test_explicit_crosswalk_covers_every_observed_value_and_never_guesses(self):
        values = sorted({row["province"] for row in self.fires})
        resolved = resolve_in_node(values + ["Alicante", "VALÈNCIA", "UNKNOWN_PROVINCE", None])
        by_value = dict(zip(values, resolved[:len(values)]))
        self.assertEqual({key: value["territory_id"] for key, value in by_value.items()}, EXPECTED_MAPPING)
        self.assertTrue(all(value["autonomous_community_id"] == "ES:CCAA:10" for value in by_value.values()))
        self.assertEqual(resolved[-4:], [None, None, None, None])

    def test_all_affected_years_and_existing_cardinality_remain_exact(self):
        for year, count in EXPECTED_BY_YEAR.items():
            rows = [row for row in self.fires if row["year"] == year]
            self.assertEqual(sum(len(row["geometry_ids"]) for row in rows), len(rows))
            self.assertEqual(sum(row["province"] not in PRE_FIX_RAW_VALUES for row in rows), count)
        rows_1995 = [row for row in self.fires if row["year"] == 1995]
        self.assertEqual((len(rows_1995), sum(len(row["geometry_ids"]) for row in rows_1995)), (467, 467))
        rows_2024 = [row for row in self.fires if row["year"] == 2024]
        self.assertEqual((len(rows_2024), sum(len(row["geometry_ids"]) for row in rows_2024)), (472, 473))
        target = next(row for row in rows_2024 if row["fire_id"] == "gva:pif-cv:2024AL0005")
        self.assertEqual(len(target["geometry_ids"]), 2)

    def test_loader_uses_crosswalk_and_frontend_packages_it(self):
        source = LOADER.read_text(encoding="utf-8")
        self.assertIn('from "./icv_territory_crosswalk.mjs"', source)
        self.assertIn("resolveIcvProvince(fire.province)?.province_key", source)
        self.assertNotIn("ICV_KEY_BY_PROVINCE", source)
        self.assertIn('"icv_territory_crosswalk.mjs"', BUILDER.read_text(encoding="utf-8"))

    def test_recovered_record_keeps_icv_area_gif_and_cause_filters(self):
        record = next(row for row in self.fires if row["fire_id"] == "gva:pif-cv:2016AL0074")
        self.assertEqual(record["province"], "ALICANTE")
        self.assertTrue(matches_filters_in_node(record, [{
            "filter_id": "icv_min_area", "filter_type": "min_value", "source": "icv",
            "metric_id": "icv_declared_forest_area_ha", "value": 500, "unit": "ha",
        }]))
        self.assertTrue(matches_filters_in_node(record, [{
            "filter_id": "icv_gif", "filter_type": "flag", "source": "icv",
            "metric_id": "icv_gif_count", "value": True, "unit": None,
        }]))
        self.assertTrue(matches_filters_in_node(record, [{
            "filter_id": "icv_cause", "filter_type": "enum", "source": "icv",
            "metric_id": "icv_cause_distribution", "value": "negligence", "unit": None,
        }]))


if __name__ == "__main__":
    unittest.main()
