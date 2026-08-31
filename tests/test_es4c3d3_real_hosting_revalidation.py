"""Pruebas estáticas C3D3; no realizan tráfico contra R2 ni lanzan Chromium."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit/hosting/es4c3d3_real_hosting_revalidation.py"
SPEC = importlib.util.spec_from_file_location("es4c3d3_revalidation", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AUDIT)


class Es4c3d3RealHostingRevalidationTests(unittest.TestCase):
    def test_fixed_origin_and_asset_identity_are_explicit(self) -> None:
        self.assertEqual(AUDIT.ORIGIN, "http://127.0.0.1:8765")
        self.assertEqual(AUDIT.EXPECTED_BYTES, 63052056)
        self.assertEqual(len(AUDIT.EXPECTED_SHA256), 64)
        self.assertIn("r2.dev", AUDIT.ENDPOINT)

    def test_validation_rejects_full_download_and_missing_browser_fetch(self) -> None:
        payload = {
            "asset": {"bytes": AUDIT.EXPECTED_BYTES, "sha256": AUDIT.EXPECTED_SHA256},
            "head": {"status": 200, "headers": {"content-length": str(AUDIT.EXPECTED_BYTES)}},
            "range_tests": {name: {"passed": True} for name in ("one_byte", "initial", "middle", "final")},
            "cors": {"access_control_allow_origin": AUDIT.ORIGIN},
            "browser_fetch": {"passed": True},
            "browser_smokes": {"main": [{"scenario": "spain", "status": "PASS"}]},
            "full_download_observed": False,
        }
        self.assertEqual(AUDIT.validate(payload), [])
        payload["full_download_observed"] = True
        payload["browser_fetch"] = {"passed": False}
        self.assertEqual(AUDIT.validate(payload), ["browser_fetch", "full_download"])

    def test_runtime_telemetry_is_gated_and_does_not_change_default_asset(self) -> None:
        app = (ROOT / "prototypes/es4c/app.js").read_text(encoding="utf-8")
        smoke = (ROOT / "prototypes/es4c/run_smoke.py").read_text(encoding="utf-8")
        self.assertIn('params.get("pmtiles_telemetry") === "1"', app)
        self.assertIn('params.get("browser_range_fetch") === "1"', app)
        self.assertIn('pmtiles_telemetry', smoke)
        self.assertIn('server_port: int = 0', smoke)


if __name__ == "__main__":
    unittest.main()
