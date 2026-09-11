"""Identity failures must prevent extraction/deployment of the POST2 patch."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from tests.test_es4d5_release_workflows_preparation import load_gate, ROOT


class PatchReleaseTests(unittest.TestCase):
    def test_manual_workflows_share_concurrency_and_gate_before_upload(self):
        for name in ('pages-national-product.yml', 'pages-national-pre-post2-rollback.yml', 'pages-legacy-gva-rollback.yml'):
            value = yaml.load((ROOT / '.github/workflows' / name).read_text(), Loader=yaml.BaseLoader)
            self.assertEqual(value['on'], {'workflow_dispatch': ''})
            self.assertEqual(value['concurrency'], {'group': 'pages', 'cancel-in-progress': 'false'})
            if name == 'pages-legacy-gva-rollback.yml':
                continue
            steps = value['jobs']['deploy']['steps']
            commands = '\n'.join(step.get('run', '') for step in steps)
            self.assertNotIn('build_', commands)
            gate = next(i for i, s in enumerate(steps) if 'check_national_product_release_gate.py' in s.get('run', ''))
            upload = next(i for i, s in enumerate(steps) if 'upload-pages-artifact' in s.get('uses', ''))
            deploy = next(i for i, s in enumerate(steps) if 'deploy-pages' in s.get('uses', ''))
            self.assertLess(gate, upload)
            self.assertLess(upload, deploy)
            if name == 'pages-national-product.yml':
                self.assertIn('--contract config/national-product-post2-patch-identity.json', commands)
                self.assertIn('national-product-post2-staging-es4post4/national-product-post2-patch.tar.gz', commands)
            else:
                self.assertNotIn('--contract', commands)
                self.assertIn('national-product-staging-es4e4a/national-product-staging.tar', commands)

    def test_wrong_archive_sha_stops_before_extraction(self):
        gate = load_gate()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture'
            path.write_bytes(b'bad')
            contract = {'archive': {'bytes': 3, 'sha256': '0' * 64}, 'site': gate.GOLDEN_SITE}
            with patch.object(gate, 'extract_safely') as extract:
                result = gate.gate(path, extract_to=Path(directory) / 'site', contract=contract)
            self.assertFalse(result['valid'])
            self.assertEqual(result['archive']['failures'], ['archive:sha256'])
            extract.assert_not_called()

    def test_wrong_site_identity_fails_final_gate(self):
        gate = load_gate()
        expected = json.loads((ROOT / 'config/national-product-post2-patch-identity.json').read_text())['site']
        actual = {**expected, 'valid': True, 'failures': [], 'site_identity_sha256': '0' * 64}
        with patch.object(gate.site_checker, 'check', return_value=actual), patch.object(gate, 'count_staging_references', return_value=0):
            result = gate.site_gate(Path('unused'), expected)
        self.assertFalse(result['valid'])
        self.assertIn('site:site_identity_sha256', result['failures'])
