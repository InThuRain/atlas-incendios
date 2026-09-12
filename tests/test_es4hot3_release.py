import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from tests.test_es4d5_release_workflows_preparation import load_gate, ROOT


class Hot3ReleaseTests(unittest.TestCase):
    def test_manual_workflows_and_concurrency(self):
        for name in ('pages-national-product.yml','pages-national-v1-0-0-rollback.yml','pages-national-pre-post2-rollback.yml','pages-legacy-gva-rollback.yml'):
            text=(ROOT/'.github/workflows'/name).read_text()
            y=yaml.load(text,Loader=yaml.BaseLoader)
            self.assertEqual(['workflow_dispatch'],list(y['on']))
            self.assertEqual({'group':'pages','cancel-in-progress':'false'},y['concurrency'])

    def test_fixed_contracts_and_order(self):
        for name,contract,tag in [('pages-national-product.yml','hot1-candidate','national-product-v1.0.1-staging-hot2'),('pages-national-v1-0-0-rollback.yml','post2-patch','national-product-post2-staging-es4post4')]:
            text=(ROOT/'.github/workflows'/name).read_text()
            self.assertIn('/'+tag+'/',text)
            self.assertIn('--contract config/national-product-'+contract+'-identity.json',text)
            self.assertNotIn('build_',text)
            self.assertLess(text.index('check_national_product_release_gate.py'),text.index('actions/upload-pages-artifact'))
            self.assertLess(text.index('actions/upload-pages-artifact'),text.index('actions/deploy-pages'))
        c=json.loads((ROOT/'config/national-product-hot1-candidate-identity.json').read_text())
        self.assertEqual(501,c['site']['site_file_count'])
        self.assertEqual('6ae69340c9fb676d2331e9afbf1dd98569873b43119f73e2672665122fc4e30a',c['site']['site_identity_sha256'])

    def test_wrong_archive_sha_rejected(self):
        gate=load_gate()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.tar';p.write_bytes(b'test')
            self.assertFalse(gate.archive_gate(p,{'bytes':4,'sha256':'0'*64})['valid'])
            self.assertTrue(gate.archive_gate(p,{'bytes':4,'sha256':hashlib.sha256(b'test').hexdigest()})['valid'])

    def test_wrong_site_identity_rejected(self):
        gate=load_gate()
        expected=json.loads((ROOT/'config/national-product-hot1-candidate-identity.json').read_text())['site']
        bad=dict(expected,site_identity_sha256='0'*64)
        self.assertEqual(['site_identity_sha256'],gate.mismatches(expected,bad))


if __name__=='__main__':unittest.main()
