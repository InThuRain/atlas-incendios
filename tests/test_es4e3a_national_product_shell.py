"""Contratos dirigidos de ES-4E3A: shell de producto, sin datasets nuevos."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "src/national/index.html"
CSS = ROOT / "src/national/styles.css"
SHELL = ROOT / "src/national/product-shell.mjs"
BUILD = ROOT / "scripts/build_national_frontend.py"


class VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden_depth = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if self.hidden_depth or "hidden" in attributes or attributes.get("aria-hidden") == "true" or "runtime-diagnostics" in attributes.get("class", ""):
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.text.append(data)


class ES4E3ANationalProductShellTests(unittest.TestCase):
    def test_shell_preserves_runtime_dom_contract_and_product_order(self):
        html = HTML.read_text(encoding="utf-8")
        runtime = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        ids = set(re.findall(r'id="([^"]+)"', html))
        runtime_ids = set(re.findall(r'querySelector\("#(?:debug-output, #)?([A-Za-z0-9_-]+)"\)', runtime))
        self.assertFalse(runtime_ids - ids, sorted(runtime_ids - ids))
        order = [html.index(marker) for marker in ('class="map-region"', 'class="primary-controls"', 'class="summary-section"', 'id="timeline-slot"', 'id="filters-slot"', 'class="results-section"', 'id="sources-methodology"')]
        self.assertEqual(order, sorted(order))
        self.assertNotIn('id="sources-methodology" class="sources-methodology" open', html)

    def test_recommended_view_and_human_messages_are_deterministic(self):
        result = subprocess.run(
            ["node", "--experimental-modules", "tests/es4e3a_product_shell_contract.mjs"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_primary_copy_omits_runtime_states_and_false_metrics(self):
        parser = VisibleTextParser()
        parser.feed(HTML.read_text(encoding="utf-8"))
        visible = " ".join(parser.text).lower()
        for forbidden in ("source_record", "fire_geometry", "no_coverage", "not_integrated_for_territory", " initial", " detail", " shard", "— incendios", "0 ha"):
            self.assertNotIn(forbidden, visible)
        self.assertNotIn("queryrenderedfeatures", SHELL.read_text(encoding="utf-8").lower())
        self.assertIn("Los registros administrativos y los perímetros cartografiados son conjuntos independientes", HTML.read_text(encoding="utf-8"))

    def test_layout_accessibility_and_mobile_map_contract(self):
        html = HTML.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        self.assertIn('aria-label="Ruta territorial"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("aria-expanded", SHELL.read_text(encoding="utf-8"))
        self.assertIn("min-height: 2.75rem", css)
        self.assertRegex(css, r"grid-template: 4\.25rem minmax\(0, 1fr\) / minmax\(0, 1fr\) clamp\(22\.5rem, 29vw, 27\.5rem\)")
        self.assertIn("height: 42vh", css)
        self.assertIn("runtime.map.resize", SHELL.read_text(encoding="utf-8"))

    def test_frontend_build_includes_product_shell_without_large_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "national"
            built = subprocess.run([sys.executable, str(BUILD), "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            checked = subprocess.run([sys.executable, str(BUILD), "--check", "--output", str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            manifest = json.loads((output / "asset-manifest.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        self.assertIn("product-shell.mjs", paths)
        self.assertIn("source-registry.mjs", paths)
        self.assertFalse(manifest["large_assets_included"])


if __name__ == "__main__":
    unittest.main()
