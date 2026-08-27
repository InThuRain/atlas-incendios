import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/egif/es4b4a_cause_inventory.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b4a_cause_inventory", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


INVENTORY = load_module()
MAPPING = json.loads((ROOT / "config/egif-web.json").read_text(encoding="utf-8"))["causes"]["source_code_mapping"]


def record(record_id, cause):
    return {
        "record_id": record_id,
        "source_declared_location": {"province_code": "03", "community_code": "10"},
        "original_attributes": {"pif_causa": cause},
    }


class ES4B4AEgifCauseInventoryTests(unittest.TestCase):
    def test_source_values_and_null_blank_are_preserved_separately(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "egif_records_1992.jsonl"
            rows = [
                record("egif-record:one", {"idcausa": "500", "idmotivacion": "400", "causaotros": "Desconocida", "numeroparte": "one"}),
                record("egif-record:two", {"idcausa": None, "idmotivacion": " ", "causaotros": None, "numeroparte": "two"}),
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = INVENTORY.inventory_year(path, 1992, MAPPING)

        self.assertEqual(result["records"], 2)
        self.assertEqual(result["records_with_primary_cause"], 1)
        self.assertEqual(result["records_without_primary_cause"], 1)
        by_field = {field["source_path"]: field for field in result["fields"]}
        primary = by_field["pif_causa.idcausa"]
        self.assertEqual(primary["records_null"], 1)
        self.assertEqual(primary["records_blank"], 0)
        value = primary["values"][0]
        self.assertEqual(value["source_value"], "500")
        self.assertEqual(value["mapping_status"], "documented")
        self.assertEqual(value["canonical_code"], "unknown")
        self.assertEqual(by_field["pif_causa.idmotivacion"]["records_blank"], 1)
        self.assertEqual(by_field["pif_causa.causaotros"]["records_null"], 1)
        self.assertEqual(by_field["pif_causa.causaotros"]["values"][0]["source_value"], "Desconocida")
        self.assertEqual(by_field["pif_causa.causaotros"]["values"][0]["mapping_status"], "unmapped")
        self.assertNotIn("pif_causa.numeroparte", by_field)

    def test_only_existing_exact_idcausa_codes_are_annotated_as_documented(self):
        documented = INVENTORY.documented_mapping("100", MAPPING)
        unmapped = INVENTORY.documented_mapping("999", MAPPING)
        self.assertEqual(documented["mapping_status"], "documented")
        self.assertEqual(documented["canonical_code"], "lightning")
        self.assertEqual(unmapped["mapping_status"], "unmapped")
        self.assertIsNone(unmapped["canonical_code"])

    def test_cli_resume_and_check_use_checksums_without_reprocessing_valid_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            source = temporary_path / "egif_records_1992.jsonl"
            source.write_text(json.dumps(record("egif-record:one", {"idcausa": "100"})) + "\n", encoding="utf-8")
            input_manifest = temporary_path / "manifest.json"
            input_manifest.write_text(json.dumps({"blocks": [{
                "year": 1992,
                "status": "complete",
                "records": 1,
                "output_sha256": INVENTORY.sha256_file(source),
            }]}), encoding="utf-8")
            output = temporary_path / "cause-output"
            manifest = output / "manifest.json"
            arguments = [
                "--input-manifest", str(input_manifest),
                "--existing-mapping", str(ROOT / "config/egif-web.json"),
                "--output", str(output), "--manifest", str(manifest),
                "--period", "1992",
            ]
            self.assertEqual(INVENTORY.main(["--resume", *arguments]), 0)
            first = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(first["totals"]["complete_blocks"], 1)
            checksum = first["blocks"][0]["output_sha256"]
            self.assertEqual(INVENTORY.main(["--resume", *arguments]), 0)
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["blocks"][0]["output_sha256"], checksum)
            self.assertEqual(INVENTORY.main(["--check", *arguments]), 0)


if __name__ == "__main__":
    unittest.main()
