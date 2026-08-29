import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('idx',ROOT/'scripts/build/esfire30/territory_runtime_index.py')
MOD=importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MOD)

class TerritoryIndexTests(unittest.TestCase):
 def test_index_reconciles_existing_audited_relations(self):
  result=MOD.check(MOD.OUTPUT)
  self.assertTrue(result['valid'],result)
 def test_canonical_encoder_is_deterministic(self):
  self.assertEqual(MOD.enc({'b':[2,1],'a':0}),MOD.enc({'a':0,'b':[2,1]}))

if __name__=='__main__': unittest.main()
