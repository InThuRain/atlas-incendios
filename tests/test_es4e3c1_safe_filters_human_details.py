"""Pruebas específicas ES-4E3C1; no ejecutan la suite general."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ES4E3C1SafeFiltersHumanDetailsTests(unittest.TestCase):
    def test_semantics_state_permalink_legacy_and_filtered_metrics(self):
        result = subprocess.run(
            ["node", "--experimental-modules", "tests/es4e3c1_filter_contract.mjs"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_source_contracts_exclude_unsafe_filters(self):
        source = (ROOT / "prototypes/es4c/source_filters.mjs").read_text(encoding="utf-8")
        self.assertNotIn("esfire30_min_area", source)
        self.assertNotIn("effis_gif", source)
        self.assertNotIn("egif_cause", source)
        self.assertIn("is_gif_forest_ge_500_ha", source)
        self.assertIn("mapped_area_ha", source)

    def test_accessible_filter_and_human_detail_dom(self):
        html = (ROOT / "src/national/index.html").read_text(encoding="utf-8")
        self.assertIn('aria-controls="filter-panel"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('id="active-filter-chips"', html)
        self.assertEqual(len(re.findall(r'data-detail-card="', html)), 4)
        self.assertEqual(len(re.findall(r'<summary>Más sobre estos datos</summary>', html)), 4)
        primary = re.sub(r'<details class="more-data">.*?</details>', '', html, flags=re.S)
        self.assertNotIn("geometry_id", primary)
        self.assertNotIn("source_record", primary)

    def test_loaders_filter_independently_and_keep_detail_lazy(self):
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        for source in ("egif", "icv", "effis"):
            self.assertIn(f'filtersForSource(state.filters, "{source}")', app)
        self.assertIn("EGIFDetailLoader", app)
        self.assertNotIn("esfire30_min_area", app)
        self.assertIn("active_fire_ids", (ROOT / "prototypes/es4c/icv_loader.mjs").read_text(encoding="utf-8"))

    def test_artifact_contains_new_modules_without_new_data(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "national"
            built = subprocess.run([sys.executable, "scripts/build_national_frontend.py", "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            checked = subprocess.run([sys.executable, "scripts/build_national_frontend.py", "--check", "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            manifest = json.loads((output / "asset-manifest.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        self.assertTrue({"safe-filters.mjs", "human-details.mjs", "runtime/source_filters.mjs"} <= paths)
        self.assertFalse(manifest["large_assets_included"])


if __name__ == "__main__":
    unittest.main()
