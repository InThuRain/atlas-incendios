import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build/egif/national_web.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b5b1_egif_web_builder", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = load_module()


def payload(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def record(year, ordinal):
    source_id = f"{year}030{ordinal:04d}"
    return {
        "record_id": f"egif-record:{source_id}", "source_id": "egif", "entity_type": "administrative_record",
        "year": year, "geometry": None, "geometry_ids": [], "reported_forest_area_ha": 500.0 if ordinal == 1 else None,
        "is_gif_forest_ge_500_ha": ordinal == 1, "cause_raw": "211", "identity_status": "source_record_only",
        "episode_identity_status": "unresolved", "source_record_id": source_id, "source_database_id": f"db-{source_id}",
        "detection_date": f"{year}-01-01T00:00:00", "extinction_date": f"{year}-01-02T00:00:00",
        "reported_total_area_ha": 500.0, "reported_wooded_area_ha": 500.0, "reported_nonwooded_area_ha": 0.0,
        "form_model": "fixture", "temporal_validity": {"coverage_status": "fixture"},
        "source_declared_location": {"municipality_name": None, "paraje": None},
    }


def audit(record_id):
    return {"record_id": record_id, "mappings": [
        {"level": "autonomous_community", "resolution_status": "resolved", "territory_id": "ES:CCAA:10"},
        {"level": "province", "resolution_status": "resolved", "territory_id": "ES:PROV:03"},
        {"level": "municipality", "resolution_status": "unresolved", "territory_id": None},
    ]}


class ES4B5B1BuilderTests(unittest.TestCase):
    def test_partial_period_is_rejected(self):
        args = type("Args", (), {"all": False, "period": [(1974, 1974)]})()
        with self.assertRaisesRegex(ValueError, "bloques ES-4B5A completos"):
            BUILDER.selected_years(args, {1974: {"records": 1}})

    def test_columnar_serialization_is_deterministic_and_detail_uses_ordinal_alignment(self):
        asset = {"asset_id": "egif:ES:CCAA:10:1968-1979", "territory_id": "ES:CCAA:10", "from_year": 1968, "to_year": 1979}
        rows = [{"record_id": "egif-record:fixture", "year": 1974, "autonomous_community_id": "ES:CCAA:10", "province_id": "ES:PROV:03", "municipality_id": None, "reported_forest_area_ha": None, "is_gif_forest_ge_500_ha": None, "cause_source_code": "211", "canonical_cause": None, "cause_mapping_status": "unmapped", "coverage_status": "fixture", "identity_status": "source_record_only", "episode_identity_status": "unresolved"}]
        initial, checksum = BUILDER.initial_payload(asset, rows)
        self.assertEqual(initial, BUILDER.initial_payload(asset, rows)[0])
        detail = json.loads(BUILDER.detail_payload(asset, [{field: None for field in BUILDER.DETAIL_FIELDS}], checksum))
        self.assertEqual(checksum, detail["initial_record_id_order_sha256"])
        self.assertNotIn("record_id", detail["columns"])

    def test_resume_check_and_sample_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); normalized = base / "normalized"; territorial = base / "territorial"; output = base / "web"
            normalized.mkdir(); territorial.mkdir()
            input_blocks, territory_blocks = [], []
            for year in range(1968, 1980):
                rows = [record(year, 1)]
                records_data = b"".join(payload(item) for item in rows)
                record_path = normalized / f"egif_records_{year}.jsonl"; record_path.write_bytes(records_data)
                audits_data = b"".join(payload(audit(item["record_id"])) for item in rows)
                audit_path = territorial / f"territory_mapping_audit_{year}.jsonl"; audit_path.write_bytes(audits_data)
                input_blocks.append({"year": year, "status": "complete", "records": 1, "output_sha256": sha(records_data)})
                territory_blocks.append({"year": year, "status": "complete", "records": 1, "audit_sha256": sha(audits_data)})
            input_manifest = normalized / "manifest.json"; input_manifest.write_bytes(payload({"blocks": input_blocks}))
            territory_manifest = territorial / "manifest.json"; territory_manifest.write_bytes(payload({"blocks": territory_blocks}))
            command = ["--resume", "--period", "1968:1979", "--territory", "ES:CCAA:10", "--input-manifest", str(input_manifest), "--territory-manifest", str(territory_manifest), "--output", str(output)]
            self.assertEqual(0, BUILDER.main(command))
            self.assertEqual(0, BUILDER.main(command))  # resume does not regenerate valid assets
            self.assertEqual(0, BUILDER.main(["--check", *command[1:]]))
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(12, manifest["totals"]["records"])
            self.assertEqual(["egif"], manifest["source_ids"])
            self.assertIn("ccinif_grid", manifest["excluded_source_ids"])
            asset = manifest["assets"][0]
            self.assertTrue((output / asset["initial"]["path"]).is_file())
            initial = json.loads((output / asset["initial"]["path"]).read_text())
            self.assertTrue(all(value is None for value in initial["columns"]["municipality_id"]))
            self.assertTrue(all(value is None for value in initial["columns"]["canonical_cause"]))
            self.assertEqual({True}, set(initial["columns"]["is_gif_forest_ge_500_ha"]))


if __name__ == "__main__":
    unittest.main()
