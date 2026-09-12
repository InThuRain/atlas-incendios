import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hot2', ROOT / 'scripts/audit/product/es4hot2_regressions.py')
HOT2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(HOT2)


class Hot2StagingTests(unittest.TestCase):
    def fixture(self):
        state = {'from': 1995, 'to': 1995, 'center': [-.7, 39.3], 'zoom': 8}
        observed = {'state': state, 'map_loaded': True, 'errors': []}
        recent = {'state': {'from': 2025, 'to': 2025, 'center': [-.71, 38.17], 'zoom': 11}, 'map_loaded': True, 'errors': []}
        return {'temporal': {'passed': True}, 'range': {'base': [{'passed': True}], 'fire': [{'passed': True}]},
                'glyphs': [{'passed': True}] * 9, 'native_capture': {'before': {'state': state}},
                'native_restore': {'fresh_before_reload': observed, 'after_reload': observed},
                'legacy_historic': {'fresh_tab': observed}, 'legacy_recent': {'fresh_tab': recent}}

    def test_complete_regression_evidence_passes(self):
        self.assertTrue(HOT2.validate(self.fixture())['passed'])

    def test_missing_or_failed_evidence_fails_closed(self):
        self.assertFalse(HOT2.validate({})['passed'])
        for key in ('temporal', 'range', 'glyphs', 'native_restore', 'legacy_recent'):
            rows = self.fixture()
            del rows[key]
            self.assertFalse(HOT2.validate(rows)['passed'], key)

    def test_restore_camera_drift_fails(self):
        rows = copy.deepcopy(self.fixture())
        rows['native_restore']['after_reload']['state']['zoom'] = 3
        self.assertFalse(HOT2.validate(rows)['passed'])

    def test_staging_workflow_and_contract_are_fixed(self):
        contract = json.loads((ROOT / 'config/national-product-hot1-candidate-identity.json').read_text())
        self.assertEqual(501, contract['site']['site_file_count'])
        self.assertEqual('d98810048994d90bf0a99a883dee94c29a1abb5e', contract['source_commit'])
        workflow = (ROOT / 'benchmarks/es4hot2/pages-hot2.yml').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertNotIn('inputs:', workflow)
        self.assertNotIn('build_national', workflow)
        self.assertIn('atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-v1.0.1-staging-hot2/', workflow)
        self.assertLess(workflow.index('check_national_product_release_gate.py'), workflow.index('actions/upload-pages-artifact'))


if __name__ == '__main__':
    unittest.main()
