import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ingest/egif/gva_1968_1992.py"
SPEC = importlib.util.spec_from_file_location("egif_gva_pipeline", SCRIPT)
egif = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = egif
SPEC.loader.exec_module(egif)


def synthetic_original(report_id="1992030104", database_id="10", province="3"):
    return {
        "idpif": database_id,
        "numeroparte": report_id,
        "pif_comun": {"idpif": database_id, "numeroparte": report_id, "anio": "1992"},
        "pif_localizacion": {
            "numeroparte": report_id,
            "idcomunidad": "9",
            "idprovincia": province,
            "idmunicipio": "54",
            "nummunicipiosafectados": "1",
            "hoja": "0821",
            "cuadricula": "A12",
        },
        "pif_tiempos": {
            "numeroparte": report_id,
            "deteccion": "1992-07-01T12:00:00",
            "extinguido": "1992-07-01T18:00:00",
        },
        "pif_causa": {"numeroparte": report_id, "idcausa": "100"},
        "pif_perdidas": {
            "numeroparte": report_id,
            "superficiearboladatotal": "37.0000",
            "superficienoarboladatotal": "363.0000",
            "superficienoarboladaagricola": "100.0000",
        },
    }


class EgifPipelineTests(unittest.TestCase):
    def test_search_page_parser_requires_export_metadata(self):
        html = b'''<input name="__RequestVerificationToken" value="token">
        <input id="hddPifTotal" value="2514"><input id="egif_pin" value="pin">
        <div data-busqueda="criteria"></div>'''
        self.assertEqual(egif.parse_search_page(html), ("token", 2514, "pin", "criteria"))

    def test_xml_conversion_preserves_repeated_source_fields(self):
        node = ET.fromstring("<ParteMonte><valor>1</valor><valor>1</valor></ParteMonte>")
        self.assertEqual(egif.element_to_value(node), {"valor": ["1", "1"]})

    def test_zip_validation_counts_explicit_zero_years(self):
        xml = b'''<?xml version="1.0" encoding="utf-8"?>
        <pifs><Pif><pif_comun><anio>1968</anio></pif_comun>
        <pif_localizacion><idprovincia>3</idprovincia></pif_localizacion></Pif></pifs>'''
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("snapshot.xml", xml)
        result = egif.validate_zip(stream.getvalue())
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["annual_counts"]["1968"], 1)
        self.assertEqual(result["annual_counts"]["1972"], 0)
        self.assertEqual(result["province_counts"], {"3": 1})

    def test_normalization_separates_forest_and_total_area_and_has_no_geometry(self):
        source = {
            "source_url": egif.SEARCH_URL,
            "raw_path": "data/raw/test.zip",
            "sha256": "abc",
            "retrieved_at": "2026-08-19T00:00:00Z",
        }
        record = egif.normalized_record(
            synthetic_original(), "Alicante", "03", source, "test.xml",
            {"03054": "Castell de Castells"}, {"100": "Rayo"},
        )
        self.assertEqual(record["reported_forest_area_ha"], 400.0)
        self.assertEqual(record["reported_total_area_ha"], 500.0)
        self.assertFalse(record["is_gif_ge_500_ha"])
        self.assertEqual(record["municipality"], "Castell de Castells")
        self.assertIsNone(record["geometry"])
        self.assertIsNone(record["derived_coordinates_epsg4326"])
        self.assertEqual(record["location_quality"], "map_sheet_or_grid")

    def test_identity_uses_unique_structurally_valid_report_number_only(self):
        source = {
            "source_url": egif.SEARCH_URL,
            "raw_path": "raw.zip",
            "sha256": "abc",
            "retrieved_at": "2026-08-19T00:00:00Z",
        }
        records = [
            egif.normalized_record(synthetic_original("1992030104", "10"), "Alicante", "03", source, "x.xml", {}, {}),
            egif.normalized_record(synthetic_original("1992030105", "11"), "Alicante", "03", source, "x.xml", {}, {}),
        ]
        report = egif.assign_identity(records)
        self.assertEqual(records[0]["fire_id"], "egif-record:1992030104")
        self.assertEqual(records[0]["identity_status"], "source_record_only")
        self.assertEqual(records[0]["episode_identity_status"], "unresolved")
        self.assertEqual(report["ambiguous_records"], 0)
        self.assertFalse(report["incident_level_identity_available"])

        duplicate = [
            egif.normalized_record(synthetic_original("1992030104", "10"), "Alicante", "03", source, "x.xml", {}, {}),
            egif.normalized_record(synthetic_original("1992030104", "12"), "Alicante", "03", source, "x.xml", {}, {}),
        ]
        report = egif.assign_identity(duplicate)
        self.assertEqual(report["ambiguous_records"], 2)
        self.assertTrue(all(item["identity_status"] == "ambiguous" for item in duplicate))

    def test_documented_period_metadata(self):
        self.assertEqual(egif.model_for_year(1968), "historical_form_1")
        self.assertEqual(egif.model_for_year(1989), "historical_form_5")
        self.assertEqual(egif.model_for_year(1992), "historical_form_6")
        self.assertEqual(egif.coverage_for_year(1979), "selective")
        self.assertEqual(egif.coverage_for_year(1991), "transitional")
        self.assertEqual(egif.coverage_for_year(1992), "systematic_or_near_systematic")


if __name__ == "__main__":
    unittest.main()
