"""Pruebas dirigidas de ES-4E3B2, sin suite general ni datasets nuevos."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "src/national/index.html"
CSS = ROOT / "src/national/styles.css"
SHELL = ROOT / "src/national/product-shell.mjs"
LOADER = ROOT / "src/national/ux-summary-loader.mjs"
HISTOGRAM = ROOT / "src/national/metrics-histogram.mjs"
BUILD = ROOT / "scripts/build_national_frontend.py"


class ES4E3B2MetricsHistogramUiTests(unittest.TestCase):
    def test_metric_loader_and_histogram_contracts(self):
        result = subprocess.run(
            ["node", "--experimental-modules", "tests/es4e3b2_metrics_contract.mjs"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_human_ui_is_single_series_accessible_and_source_typed(self):
        html = HTML.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        module = HISTOGRAM.read_text(encoding="utf-8")
        self.assertIn('role="tablist"', html)
        self.assertIn('id="histogram-data-body"', html)
        self.assertIn('aria-label', module)
        self.assertIn("selectedSeriesId", module)
        self.assertNotIn("stack", module.lower())
        self.assertNotIn("Total de incendios", html)
        self.assertIn("grid-template-columns: repeat(59", css)
        self.assertIn("histogram-bar--gap", css)

    def test_loader_is_lazy_cached_cancelable_and_isolated(self):
        source = LOADER.read_text(encoding="utf-8")
        shell = SHELL.read_text(encoding="utf-8")
        self.assertIn("manifest.files", source)
        self.assertIn("assetCache", source)
        self.assertIn("AbortController", source)
        self.assertIn('status: "stale"', source)
        self.assertIn("No se ha podido cargar el resumen de este territorio", HISTOGRAM.read_text(encoding="utf-8"))
        self.assertIn("createMetricsHistogramUi", shell)

    def test_frontend_builder_declares_summary_without_host_or_pages_assembly(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "national"
            built = subprocess.run([sys.executable, str(BUILD), "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            checked = subprocess.run([sys.executable, str(BUILD), "--check", "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            manifest = json.loads((output / "asset-manifest.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        self.assertIn("ux-summary-loader.mjs", paths)
        self.assertIn("metrics-histogram.mjs", paths)
        summary = manifest["logical_asset_config"]["assets"]["ux_summary"]["manifest"]
        self.assertEqual(summary["schema_version"], "national-ux-summary-v1")
        self.assertFalse(summary["path"].startswith(("http://", "https://", "/home/")))
        self.assertFalse(manifest["large_assets_included"])

    def test_runtime_dom_contract_and_permalink_remain_additive(self):
        html = HTML.read_text(encoding="utf-8")
        runtime = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        ids = set(re.findall(r'id="([^"]+)"', html))
        runtime_ids = set(re.findall(r'querySelector\("#(?:debug-output, #)?([A-Za-z0-9_-]+)"\)', runtime))
        self.assertFalse(runtime_ids - ids, sorted(runtime_ids - ids))
        self.assertNotIn("histogram", (ROOT / "prototypes/es4c/state_serialization.mjs").read_text(encoding="utf-8"))
        self.assertIn("copy-state-link", html)


if __name__ == "__main__":
    unittest.main()
