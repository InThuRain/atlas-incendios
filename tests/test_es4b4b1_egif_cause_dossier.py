import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/egif/es4b4b1_cause_dossier.py"
AGGREGATE = ROOT / "data/derived/spain/es4b4a/causes/2026-08-27"
DICTIONARY = ROOT / "data/raw/egif/gva/1968_1992/dictionaries/causes.sparql.json"
OUTPUT = ROOT / "data/audit/egif/es4b4b1_cause_codes.json"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b4b1_cause_dossier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DOSSIER = load_module()


def field(path, values):
    return {"source_path": path, "records_present": 10, "records_null": 0, "records_blank": 0, "values": values}


def value(code, frequency, years, status="unmapped", canonical=None):
    return {"source_value": code, "frequency": frequency, "years": years, "example_record_id": f"egif-record:{code}", "mapping_status": status, "canonical_code": canonical, "mapping_basis": "fixture" if status == "documented" else None, "provinces": {"03": frequency}, "communities": {"10": frequency}}


class ES4B4B1CauseDossierTests(unittest.TestCase):
    def test_complete_code_table_preserves_statuses_and_secondary_dimensions(self):
        aggregate = {
            "records": 10, "records_with_primary_cause": 10, "records_without_primary_cause": 0,
            "fields": [
                field("pif_causa.idcausa", [value("100", 6, [1992], "documented", "lightning"), value("211", 4, [1992, 2016])]),
                field("pif_causa.idcausante", [value("1", 10, [1992, 2016])]),
            ],
        }
        schemas = {"field_signatures": [
            {"years": [1992], "fields": ["pif_causa.idcausa", "pif_causa.idcausante"]},
            {"years": [2016], "fields": ["pif_causa.idcausa", "pif_causa.idcausante", "pif_causa.idmotivacion"]},
        ]}
        dictionary = {"100": {"label": "Causa: Rayo", "description": "Rayo"}}
        result = DOSSIER.build_dossier(aggregate, schemas, dictionary, input_provenance={"fixture": True})
        self.assertEqual(result["summary"], {
            "records": 10, "primary_cause_present": 10, "primary_cause_missing": 0,
            "idcausa_distinct_codes": 2, "documented_code_count": 1, "unmapped_code_count": 1,
            "documented_frequency": 6, "unmapped_frequency": 4, "source_cause_field_count": 2,
        })
        by_code = {item["cause_source_code"]: item for item in result["idcausa_codes"]}
        self.assertEqual(by_code["100"]["documentation"]["source_label_exact"], "Causa: Rayo")
        self.assertIsNone(by_code["211"]["documentation"])
        self.assertEqual(by_code["211"]["secondary_context"]["available_source_fields_in_code_years"], ["pif_causa.idcausante", "pif_causa.idmotivacion"])
        self.assertFalse(by_code["211"]["semantic_change_possible"])
        self.assertEqual(result["documentation_gaps"][0]["cause_source_code"], "211")
        self.assertEqual(result["secondary_fields"][0]["source_path"], "pif_causa.idcausante")
        self.assertEqual(DOSSIER.render_report(result), DOSSIER.render_report(result))

    @unittest.skipUnless(AGGREGATE.exists() and DICTIONARY.exists() and OUTPUT.exists(), "requires ignored local ES-4B4A aggregates and dictionary snapshot")
    def test_local_national_dossier_reconciles_all_codes_frequencies_and_is_deterministic(self):
        output = json.loads(OUTPUT.read_text(encoding="utf-8"))
        aggregate = json.loads((AGGREGATE / "cause_values_global.json").read_text(encoding="utf-8"))
        schemas = json.loads((AGGREGATE / "cause_schema_periods.json").read_text(encoding="utf-8"))
        primary = next(field for field in aggregate["fields"] if field["source_path"] == "pif_causa.idcausa")
        codes = output["idcausa_codes"]
        self.assertEqual(len(codes), 87)
        self.assertEqual(sum(code["frequency"] for code in codes), 646887)
        self.assertEqual(sum(code["frequency"] for code in codes if code["mapping_status"] == "documented"), 609964)
        self.assertEqual(sum(code["frequency"] for code in codes if code["mapping_status"] == "unmapped"), 36923)
        self.assertEqual({code["cause_source_code"] for code in codes}, {value["source_value"] for value in primary["values"]})
        rebuilt = DOSSIER.build_dossier(aggregate, schemas, DOSSIER.source_dictionary(DICTIONARY), input_provenance=output["input_provenance"])
        self.assertEqual(json.dumps(output, ensure_ascii=False, sort_keys=True), json.dumps(rebuilt, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
