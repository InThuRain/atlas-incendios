"""Contratos estáticos del ensamblado completo ES-4D4A.

No construye los ~500 MB del artifact: ese trabajo y los smokes se ejecutan
por el comando dedicado, que es reanudable y deja evidencia local ignorada.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSEMBLER = ROOT / "scripts/build_national_pages_artifact.py"
CHECKER = ROOT / "scripts/check_national_pages_artifact.py"
FRONTEND_BUILDER = ROOT / "scripts/build_national_frontend.py"


class ES4D4ANationalStagingArtifactTests(unittest.TestCase):
    def test_assembler_declares_the_closed_runtime_contract(self):
        source = ASSEMBLER.read_text(encoding="utf-8")
        for required in (
            "EGIF_SOURCE",
            "MUNICIPALITY_SHARDS_SOURCE",
            "MUNICIPALITY_INDEX_SOURCE",
            "PMTILES_DESTINATION",
            "len(assets) != 88",
            "len(municipalities) != 8132",
            "len(shard_ids) != 52",
            "len(by_parent) != 47",
            '{"2025": 9, "2026": 16}',
            "significant_duplicate_assets",
            "external_runtime_dependencies",
        ):
            self.assertIn(required, source)

    def test_runtime_paths_are_relative_and_pmtiles_dependency_is_vendored(self):
        source = FRONTEND_BUILDER.read_text(encoding="utf-8")
        self.assertIn('"asset_base_url": "./"', source)
        self.assertIn('"runtime_entry": "./runtime/app.js"', source)
        self.assertIn('"node_modules/fflate/index.js"', source)
        self.assertIn('from "./compat_gva_v1.mjs"', source)

    def test_checker_covers_integrity_no_fallback_and_directed_smokes(self):
        source = CHECKER.read_text(encoding="utf-8")
        for required in (
            "artifact.check",
            "FORBIDDEN_REQUEST_PREFIXES",
            "PMTiles full download",
            "gva_2024",
            "gva_2026",
            "asturias_cangas",
            "native_permalink",
            "canarias_no_esfire30",
            "mobile_effis_2026",
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
