"""Pruebas locales del auditor de hosting real ES-4C3D (sin red)."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/hosting/es4c3d_real_hosting_range.py"
SPEC = importlib.util.spec_from_file_location("es4c3d_range_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AUDIT)


class Es4c3dRealHostingRangeTests(unittest.TestCase):
    def test_sanitizes_signed_redirect_and_parses_byte_ranges(self) -> None:
        self.assertEqual(
            AUDIT.safe_url("https://example.test/file.pmtiles?signature=secret&expires=1"),
            "https://example.test/file.pmtiles",
        )
        self.assertEqual(AUDIT.parse_content_range("bytes 0-16383/63052056"), (0, 16383, 63052056))
        self.assertIsNone(AUDIT.parse_content_range("items 0-1/2"))
        self.assertIsNone(AUDIT.parse_content_range("malformed"))

    def test_validation_requires_ranges_cors_and_browser_smokes(self) -> None:
        payload = {
            "asset": {"bytes": AUDIT.EXPECTED_BYTES, "sha256": AUDIT.EXPECTED_SHA256},
            "range_tests": {label: {"passed": True} for label in ("one_byte", "initial", "middle", "final", "repeat_initial")},
            "cors": {"access_control_allow_origin": "*"},
            "browser_smokes": [{"scenario": "galicia", "status": "PASS"}],
        }
        self.assertEqual(AUDIT.validate(payload), [])
        payload["cors"] = {"access_control_allow_origin": None}
        payload["browser_smokes"] = [{"scenario": "galicia", "status": "FAIL"}]
        self.assertEqual(AUDIT.validate(payload), ["cors_header", "browser:galicia"])

    def test_prototype_override_is_ephemeral_and_https_only(self) -> None:
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        self.assertIn('params.get("pmtiles_url")', app)
        self.assertIn("/^https:\\/\\//.test(remotePmtilesUrl || \"\")", app)
        self.assertIn("url: `pmtiles://${archiveUrl}`", app)
        self.assertNotIn("pmtiles_url:", app)


if __name__ == "__main__":
    unittest.main()
