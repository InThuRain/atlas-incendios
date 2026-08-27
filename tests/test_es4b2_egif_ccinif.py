import importlib.util
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/relations/egif/ccinif.py'
AUDIT_SCRIPT=ROOT/'scripts/audit/spain/es4b2_egif_normalized_audit.py'

def load():
 spec=importlib.util.spec_from_file_location('es4b2_relations',SCRIPT); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); return module

relation=load()

def load_audit():
 spec=importlib.util.spec_from_file_location('es4b2_audit',AUDIT_SCRIPT); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); return module

audit=load_audit()

def record(sheet,grid,community='9'):
 return {'record_id':'egif-record:1992460250','source_record_id':'1992460250','year':1992,'source_declared_location':{'sheet':sheet,'grid':grid,'community_code':community},'provenance':{'retrieved_at':'2026-08-27T00:00:00Z'}}

class ES4B2RelationsTests(unittest.TestCase):
 def test_exact_pair_only_promotes_to_confirmed(self):
  cells={'0704:C11':[{}]}
  row=relation.relation_row(record(' 0704 ','c11'),cells,set())
  self.assertEqual('confirmed',row['status']); self.assertEqual('ccinif-grid:0704-C11',row['spatial_reference_id']); self.assertIsNone(row['fire_geometry'])
 def test_partial_and_canary_references_stay_ambiguous(self):
  self.assertEqual('ambiguous',relation.relation_row(record(None,'B01'),{},set())['status'])
  self.assertEqual('ambiguous',relation.relation_row(record('0000','A01','12'),{}, {'A01'})['status'])
 def test_complete_unknown_pair_is_unusable_and_missing_pair_is_no_reference(self):
  self.assertEqual('unusable',relation.relation_row(record('0704','Z99'),{},set())['status'])
  self.assertEqual('no_reference',relation.relation_row(record(None,None),{},set())['status'])

 def test_substantial_fingerprint_flags_anomaly_without_equating_identity(self):
  first={'record_id':'egif-record:a','source_record_id':'a','source_database_id':'1','year':1992,'detection_date':'1992-01-01','extinction_date':'1992-01-02','source_declared_location':{'sheet':'0704','grid':'C11'},'cause_raw':'1','reported_wooded_area_ha':1,'reported_nonwooded_area_ha':2,'reported_agricultural_area_ha':None,'reported_other_nonforest_area_ha':None,'reported_total_area_ha':3,'reported_forest_area_ha':3,'form_model':'historical_form_6'}
  second={**first,'record_id':'egif-record:b','source_record_id':'b','source_database_id':'2'}
  self.assertEqual(audit.substantial_fingerprint(first),audit.substantial_fingerprint(second))

if __name__=='__main__': unittest.main()
