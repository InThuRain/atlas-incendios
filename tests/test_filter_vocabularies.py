import json
from pathlib import Path
import unittest

from scripts.filter_vocabularies import MunicipalityResolver, enrich_record


SETTINGS = {
    "identifier_field": "cod_ine_mun",
    "display_field": "nom_mun",
    "alias_fields": ["nom_mun", "nom_mun_cas", "nom_mun_val", "noms_mun"],
    "documented_historical_aliases": [{
        "municipality_raw": "Herbés",
        "province": "castellon",
        "municipality_id": "12068",
        "evidence_url": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2020-12459",
        "evidence": "Decreto 111/2020",
    }],
}


def feature(identifier, display, spanish, valencian, bilingual=None):
    return {
        "type": "Feature",
        "properties": {
            "cod_ine_mun": identifier,
            "nom_mun": display,
            "nom_mun_cas": spanish,
            "nom_mun_val": valencian,
            "noms_mun": bilingual,
        },
        "geometry": None,
    }


class MunicipalityResolverTests(unittest.TestCase):
    def setUp(self):
        catalog = {
            "type": "FeatureCollection",
            "features": [
                feature("03065", "Elx", "Elche", "Elx", "Elx/Elche"),
                feature("03139", "la Vila Joiosa", "Villajoyosa", "la Vila Joiosa", "la Vila Joiosa/Villajoyosa"),
                feature("12068", "Herbers", "Herbers", "Herbers"),
                feature("12001", "Atzeneta del Maestrat", "Adzaneta", "Atzeneta del Maestrat"),
                feature("46001", "Ademuz", "Ademuz", "Ademús"),
            ],
        }
        self.resolver = MunicipalityResolver(catalog, SETTINGS)

    def test_elx_official_aliases_resolve_to_one_id(self):
        for raw in ("Elx", "ELX", "Elche", "Elche/Elx", "Elx / Elche"):
            with self.subTest(raw=raw):
                result = self.resolver.resolve(raw, "alicante")
                self.assertEqual("resolved", result["status"])
                self.assertEqual("03065", result["municipality_id"])
                self.assertEqual("Elx", result["municipality_name"])

    def test_wrong_province_is_not_guessed(self):
        result = self.resolver.resolve("Elx", "valencia")
        self.assertEqual("unresolved", result["status"])
        self.assertIsNone(result["municipality_id"])

    def test_bilingual_components_converge_on_an_official_municipality(self):
        result = self.resolver.resolve("Villajoyosa/Vila Joiosa (la)", "alicante")
        self.assertEqual("03139", result["municipality_id"])
        self.assertEqual("exact_official_bilingual_component", result["method"])

    def test_unresolved_typo_is_not_guessed(self):
        result = self.resolver.resolve("CASTIELFABID", "valencia")
        self.assertEqual("unresolved", result["status"])

    def test_documented_historical_alias_resolves_with_official_evidence(self):
        result = self.resolver.resolve("Herbés", "castellon")
        self.assertEqual("12068", result["municipality_id"])
        self.assertEqual("documented_historical_alias", result["method"])

        documented_only = self.resolver.resolve("HERBÉS", "castellon", enhanced=True)
        self.assertEqual("12068", documented_only["municipality_id"])

    def test_valid_source_identifier_can_resolve_a_historical_label(self):
        result = self.resolver.resolve("Elx (l')", "alicante", "03065")
        self.assertEqual("03065", result["municipality_id"])
        self.assertEqual("validated_source_identifier", result["method"])

    def test_enrichment_preserves_raw_values(self):
        causes = {
            "categories": {"intentional": "Intencionado"},
            "raw_mapping": {"Intencionada": "intentional"},
        }
        record = {"municipality": "Elche/Elx", "province": "Alicante", "cause": "Intencionada"}
        audit = enrich_record(record, "icv", self.resolver, causes)
        self.assertEqual("Elche/Elx", record["municipality_raw"])
        self.assertEqual("03065", record["municipality_id"])
        self.assertEqual("Elx", record["municipality_name"])
        self.assertEqual("Intencionada", record["cause_raw"])
        self.assertEqual("intentional", record["cause_code"])
        self.assertEqual("Intencionado", record["cause_label"])
        self.assertEqual("resolved", audit["municipality_status"])

    def test_cause_vocabulary_keeps_distinct_administrative_states(self):
        root = Path(__file__).resolve().parents[1]
        vocabulary = json.loads((root / "config/ui-vocabularies.json").read_text(encoding="utf-8"))["causes"]
        self.assertEqual("unknown", vocabulary["raw_mapping"]["Desconocida"])
        self.assertEqual("under_investigation", vocabulary["raw_mapping"]["En investigación"])
        self.assertEqual("negligence", vocabulary["raw_mapping"]["Negligencia"])
        self.assertEqual("negligence_and_accidental", vocabulary["raw_mapping"]["Negligencias y Causas accidentales"])
        self.assertTrue(set(vocabulary["raw_mapping"].values()).issubset(vocabulary["categories"]))


if __name__ == "__main__":
    unittest.main()
