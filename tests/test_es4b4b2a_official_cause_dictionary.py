import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/egif/es4b4b2a_official_cause_dictionary.py"
OUTPUT = ROOT / "data/reference/egif/idcausa_official_code_table.json"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b4b2a_official_cause_dictionary", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


DICTIONARY = load_module()


class ES4B4B2AOfficialCauseDictionaryTests(unittest.TestCase):
    def test_literal_rows_keep_unique_source_key_and_unknown_language(self):
        snapshot = {"results": {"bindings": [
            {"cause": {"value": "https://example/Causa/España/211"}, "label": {"value": "Causa: Quemas de rastrojos"}, "description": {"value": "Quema agrícola"}},
        ]}}
        metadata = {"retrieved_at": "2026-08-19T21:27:18Z", "source_url": "https://example/sparql", "query": "SELECT", "raw_path": "fixture", "sha256": "0" * 64, "license": "CC BY 4.0"}
        rows = DICTIONARY.extract_rows(snapshot, metadata)
        self.assertEqual(rows[0]["source_code"], "211")
        self.assertEqual(rows[0]["source_label"], "Causa: Quemas de rastrojos")
        self.assertIsNone(rows[0]["language"])
        self.assertEqual(rows[0]["temporal_validity"], "unknown")

    def test_reconciliation_preserves_87_code_set_without_canonical_mapping(self):
        codes = [{"cause_source_code": str(code), "frequency": 1, "years": [2023]} for code in range(1, 88)]
        dossier = {"idcausa_codes": codes}
        rows = [{"source_code": "1", "source_label": "uno", "language": None, "source_uri": "x", "temporal_validity": "unknown"}]
        reference = DICTIONARY.build_reference(dossier, rows, provenance={"fixture": True})
        self.assertEqual(reference["reconciliation"]["observed_code_count"], 87)
        self.assertEqual(reference["reconciliation"]["exact_codes_found"], 1)
        self.assertEqual(reference["reconciliation"]["codes_not_found"], 86)
        self.assertNotIn("canonical_code", json.dumps(reference))

    @unittest.skipUnless(OUTPUT.exists(), "requires the versioned ES-4B4B2A reference output")
    def test_versioned_partial_reference_reconciles_actual_87_codes_and_top_ten(self):
        reference = json.loads(OUTPUT.read_text(encoding="utf-8"))
        reconciliation = reference["reconciliation"]
        self.assertEqual(reference["recovery_status"], "partial_official_linked_data_dictionary_recovered; EGIFWEB_CodXXXXX_Access_table_not_recovered")
        self.assertEqual(reconciliation["observed_code_count"], 87)
        self.assertEqual(reconciliation["exact_codes_found"], 35)
        self.assertEqual(reconciliation["codes_not_found"], 52)
        self.assertEqual(reconciliation["codes_with_multiple_labels"], 0)
        self.assertEqual([item["source_code"] for item in reconciliation["top_ten_unmapped_from_es4b4b1"]], list(DICTIONARY.TOP_TEN))
        self.assertTrue(all(item["dictionary_status"] == "exact_label_found" for item in reconciliation["top_ten_unmapped_from_es4b4b1"]))


if __name__ == "__main__":
    unittest.main()
