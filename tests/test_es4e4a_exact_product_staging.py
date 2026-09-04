"""Static contracts for the E4A exact-artifact deployment mechanism."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "benchmarks/es4e4a/pages-staging-workflow.yml"
PACKAGER = ROOT / "scripts/package_national_product_artifact.py"
AUDITOR = ROOT / "scripts/audit/hosting/es4e4a_national_product_staging.py"


class ES4E4AExactProductStagingTests(unittest.TestCase):
    def test_workflow_transports_then_gates_without_a_rebuild(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "transport_url", "transport_sha256", "transport_bytes",
            "tar --extract --file", "check_national_product_artifact.py",
            "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4",
            "es4e4a-runner-identity",
        ):
            self.assertIn(required, workflow)
        for forbidden in (
            "build_national_pages_artifact.py",
            "build_national_frontend.py",
            "download_public_data_bundle.py",
        ):
            self.assertNotIn(forbidden, workflow)

    def test_packager_uses_the_product_checker_and_deterministic_container(self):
        source = PACKAGER.read_text(encoding="utf-8")
        for required in (
            "check_national_product_artifact as checker",
            "checker.check(artifact)",
            "FAIL_ARTIFACT_IDENTITY",
            "info.mtime = 0", "tarfile.USTAR_FORMAT",
            "payload_fingerprint", "site_identity_sha256",
        ):
            self.assertIn(required, source)

    def test_remote_auditor_has_two_pmtiles_ranges_and_small_product_smokes(self):
        source = AUDITOR.read_text(encoding="utf-8")
        for required in (
            '"protomaps_basemap_pmtiles"', '"esfire30_fire_pmtiles"',
            '"0_0"', '"middle"', '"final"', '"spain_1995"',
            '"gva_1995"', '"elx_2025"', '"mobile_spain"',
            '"external_runtime_domains"', '"full_download_observed"',
            '"https://inthurain.github.io/atlas-incendios/"',
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
