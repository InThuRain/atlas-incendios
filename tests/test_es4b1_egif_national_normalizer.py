import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/normalize/egif/national.py"
AUDIT_SCRIPT = ROOT / "scripts/audit/spain/es4b1_egif_schema_inventory.py"


def load_module():
    spec = importlib.util.spec_from_file_location("es4b1_egif_normalizer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


normalizer = load_module()


def load_audit_module():
    spec = importlib.util.spec_from_file_location("es4b1_egif_schema_audit", AUDIT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = load_audit_module()


def source_record(year=2023):
    number = f"{year}030001"
    return {
        "idpif": "123",
        "numeroparte": number,
        "pif_comun": {"anio": str(year), "numeroparte": number, "idpif": "123"},
        "pif_localizacion": {"idcomunidad": "10", "idprovincia": "03", "idmunicipio": "065", "hoja": "0804", "cuadricula": "B01", "x": "700000", "y": "4300000"},
        "pif_tiempos": {"deteccion": f"{year}-07-01T10:00:00", "extinguido": f"{year}-07-01T12:00:00"},
        "pif_causa": {"idcausa": "400"},
        "pif_perdidas": {"superficiearboladatotal": "12.5", "superficienoarboladatotal": "4.5"},
    }


RAW_ENTRY = {
    "block_id": "year-2023", "raw_path": "data/raw/example.zip", "sha256": "a" * 64,
    "retrieved_at": "2026-08-27T00:00:00Z", "source_urls": {"search": "https://example.test/egif"},
}


class ES4B1NationalNormalizerTests(unittest.TestCase):
    def test_valid_source_number_keeps_published_compatible_egif_record_id(self):
        record = normalizer.normalize_record(source_record(), RAW_ENTRY, "fixture.xml")
        self.assertEqual("egif-record:2023030001", record["record_id"])
        self.assertEqual(record["record_id"], record["fire_id"])
        self.assertEqual("source_record_only", record["identity_status"])
        self.assertEqual("2023030001", record["source_record_id"])

    def test_administrative_record_never_acquires_geometry_or_episode_identity(self):
        record = normalizer.normalize_record(source_record(), RAW_ENTRY, "fixture.xml")
        self.assertIsNone(record["geometry"])
        self.assertEqual([], record["geometry_ids"])
        self.assertIsNone(record["spatial_reference_id"])
        self.assertEqual("unresolved", record["episode_identity_status"])
        self.assertEqual([], normalizer.contract_errors(record))

    def test_raw_location_cause_and_original_attributes_are_preserved_without_mapping(self):
        original = source_record()
        record = normalizer.normalize_record(original, RAW_ENTRY, "fixture.xml")
        self.assertEqual("0804", record["source_declared_location"]["sheet"])
        self.assertEqual("B01", record["source_declared_location"]["grid"])
        self.assertEqual("400", record["cause_raw"])
        self.assertIsNone(record["cause_code"])
        self.assertEqual("unmapped", record["cause_mapping_status"])
        self.assertEqual(original, record["original_attributes"])

    def test_atomic_jsonl_is_deterministic_and_validates_source_id_uniqueness(self):
        records = [normalizer.normalize_record(source_record(), RAW_ENTRY, "fixture.xml")]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.jsonl"
            first = normalizer.write_jsonl_atomic(path, iter(records))
            second = normalizer.write_jsonl_atomic(path, iter(records))
            self.assertEqual(first[:3], second[:3])
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([], normalizer.contract_errors(loaded))

    def test_period_models_preserve_known_historical_boundaries_without_claiming_later_ones(self):
        self.assertEqual("historical_form_1", normalizer.period_model(1968))
        self.assertEqual("historical_form_6", normalizer.period_model(1992))
        self.assertEqual("post_1992_export_schema_not_yet_periodized", normalizer.period_model(2023))
        self.assertEqual("selective", normalizer.coverage_status(1979))
        self.assertEqual("transitional", normalizer.coverage_status(1980))
        self.assertEqual("systematic", normalizer.coverage_status(1992))

    def test_schema_inventory_period_parser_remains_explicit(self):
        self.assertEqual((1968, 1968), audit.parse_period("1968"))
        self.assertEqual((1968, 2023), audit.parse_period("1968:2023"))
        with self.assertRaises(Exception):
            audit.parse_period("2023-1968")


if __name__ == "__main__":
    unittest.main()
