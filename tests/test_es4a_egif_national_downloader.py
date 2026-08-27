import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest/egif/download_national_full.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("es4a_egif_full", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


download = load_module()


def fixture_zip(year: int) -> bytes:
    xml = (
        f'<pifs generated="2026-08-27T00:00:00Z"><Pif><pif_comun><anio>{year}'
        f'</anio></pif_comun><pif_localizacion><idprovincia>03</idprovincia>'
        f'</pif_localizacion></Pif></pifs>'
    ).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("egif.xml", xml)
    return output.getvalue()


class ES4ANationalDownloaderTests(unittest.TestCase):
    def test_period_syntax_is_explicit_and_inclusive(self):
        self.assertEqual((1968, 1968), download.parse_period("1968"))
        self.assertEqual((1968, 1971), download.parse_period("1968-1971"))
        self.assertEqual((1992, 2023), download.parse_period("1992:2023"))
        with self.assertRaises(Exception):
            download.parse_period("2023-1968")

    def test_annual_blocks_reconcile_the_inventory_and_never_exceed_export_limit(self):
        counts = download.expected_counts(ROOT / "data/sources/spain_source_inventory.json")
        blocks = download.annual_blocks(counts, counts)
        self.assertEqual(646_887, sum(block["expected_records"] for block in blocks))
        self.assertEqual(56, len(blocks))
        self.assertEqual("year-1968", blocks[0]["block_id"])
        self.assertEqual("year-2023", blocks[-1]["block_id"])
        self.assertTrue(all(block["expected_records"] <= 50_000 for block in blocks))

    def test_full_zip_validation_is_generic_not_limited_to_1968_1992(self):
        validation = download.validate_full_zip(fixture_zip(2023))
        self.assertEqual(1, validation["record_count"])
        self.assertEqual({"2023": 1}, validation["annual_counts"])
        self.assertEqual({"03": 1}, validation["province_counts"])

    def test_complete_block_is_reused_only_when_checksum_and_manifest_counts_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            block = {"block_id": "year-1968", "year_from": 1968, "year_to": 1968, "expected_records": 1}
            entry = download.new_entry(block, output)
            path = download.block_path(output, entry)
            payload = fixture_zip(1968)
            path.write_bytes(payload)
            entry.update(
                {
                    "status": "complete",
                    "sha256": download.sha256_bytes(payload),
                    "records_downloaded": 1,
                    "annual_counts_downloaded": {"1968": 1},
                }
            )
            self.assertEqual((True, "ok", None), download.verify_entry(entry, output, deep=False))
            self.assertTrue(download.verify_entry(entry, output, deep=True)[0])
            entry["records_downloaded"] = 2
            self.assertFalse(download.verify_entry(entry, output, deep=False)[0])

    def test_manifest_contains_explicit_pending_state_before_any_network_operation(self):
        manifest = download.empty_manifest(ROOT / "data/sources/spain_source_inventory.json")
        with tempfile.TemporaryDirectory() as temporary:
            entry = download.new_entry(
                {"block_id": "year-1992", "year_from": 1992, "year_to": 1992, "expected_records": 15_956},
                Path(temporary).resolve(),
            )
        manifest["blocks"].append(entry)
        self.assertEqual("pending", manifest["blocks"][0]["status"])
        self.assertIn("parameters", manifest["blocks"][0])
        self.assertIn("source_urls", manifest["blocks"][0])
        self.assertEqual("|".join(["1"] * 17), manifest["chapters"])


if __name__ == "__main__":
    unittest.main()
