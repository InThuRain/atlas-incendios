"""Static safeguards for the two manual release workflows."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
ANCHOR = "f7a3532f633a247f33dee3ebba9fbcc316c0e534"


def load_gate():
    path = ROOT / "scripts/check_national_product_release_gate.py"
    spec = importlib.util.spec_from_file_location("national_release_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseWorkflowPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.national = (WORKFLOWS / "pages-national-product.yml").read_text(encoding="utf-8")
        cls.rollback = (WORKFLOWS / "pages-legacy-gva-rollback.yml").read_text(encoding="utf-8")
        cls.gate = load_gate()

    def test_national_is_manual_identity_gated_and_ordered(self):
        for text in (self.national, self.rollback):
            self.assertIn("workflow_dispatch:", text)
            self.assertNotIn("\n  push:", text)
            self.assertIn("group: pages", text)
            self.assertIn("cancel-in-progress: false", text)
            for permission in ("contents: read", "pages: write", "id-token: write"):
                self.assertIn(permission, text)
        for value in self.gate.GOLDEN_ARCHIVE.values():
            self.assertIn(str(value), (ROOT / "scripts/check_national_product_release_gate.py").read_text(encoding="utf-8"))
        for value in self.gate.GOLDEN_SITE.values():
            self.assertIn(str(value), (ROOT / "scripts/check_national_product_release_gate.py").read_text(encoding="utf-8"))
        self.assertNotIn("build_national", self.national)
        self.assertNotIn("package_national", self.national)
        order = [
            self.national.index("Download fixed golden national archive"),
            self.national.index("Verify archive, extract safely and gate exact site identity"),
            self.national.index("Upload exact national Pages artifact"),
            self.national.index("actions/deploy-pages@v4"),
        ]
        self.assertEqual(order, sorted(order))

    def test_rollback_is_fixed_to_the_legacy_anchor(self):
        self.assertIn(f"ref: {ANCHOR}", self.rollback)
        self.assertIn("scripts/download_public_data_bundle.py", self.rollback)
        self.assertIn("scripts/build_public_site.py", self.rollback)
        self.assertIn("scripts/validate_public_site.py", self.rollback)
        self.assertNotIn("git reset", self.rollback)
        self.assertNotIn("force", self.rollback)

    def test_negative_identity_comparisons_fail_without_large_fixtures(self):
        archive = dict(self.gate.GOLDEN_ARCHIVE)
        archive["sha256"] = "0" * 64
        self.assertEqual(self.gate.mismatches(self.gate.GOLDEN_ARCHIVE, archive), ["sha256"])
        site = dict(self.gate.GOLDEN_SITE)
        site["site_total_bytes"] += 1
        self.assertEqual(self.gate.mismatches(self.gate.GOLDEN_SITE, site), ["site_total_bytes"])
        site = dict(self.gate.GOLDEN_SITE)
        site["site_identity_sha256"] = "f" * 64
        self.assertEqual(self.gate.mismatches(self.gate.GOLDEN_SITE, site), ["site_identity_sha256"])
