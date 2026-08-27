#!/usr/bin/env python3
"""Streaming QA for the normalized national EGIF dataset; no geometry writes."""
from __future__ import annotations
import argparse, hashlib, json, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/audit/spain'))
from es1_5_ccinif_historical_grid import normalize_component, pair_key  # type: ignore
sys.path.insert(0, str(ROOT / 'scripts/ingest/egif'))
from gva_1968_1992 import atomic_write_json, sha256_file  # type: ignore
INPUT=ROOT/'data/processed/egif/spain/2026-08-27/manifest.json'
OUTPUT=ROOT/'data/derived/spain/es4b2/normalized_audit.json'


def substantial_fingerprint(record):
 """Hash a conservative comparison subset, deliberately excluding identifiers.

 It is an anomaly signal only: equal values do not establish that two parts
 describe one physical episode, so callers must never use it to deduplicate.
 """
 keys = ('year', 'detection_date', 'extinction_date', 'source_declared_location',
         'cause_raw', 'reported_wooded_area_ha', 'reported_nonwooded_area_ha',
         'reported_agricultural_area_ha', 'reported_other_nonforest_area_ha',
         'reported_total_area_ha', 'reported_forest_area_ha', 'form_model')
 payload = {key: record.get(key) for key in keys}
 encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
 return hashlib.sha256(encoded).hexdigest()

def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument('--input-manifest',type=Path,default=INPUT); p.add_argument('--output',type=Path,default=OUTPUT); args=p.parse_args(argv)
 m=json.loads(args.input_manifest.read_text()); blocks=[b for b in m['blocks'] if b['status']=='complete']
 input_dir=args.input_manifest.resolve().parent
 totals=Counter(); source_ids=Counter(); db_ids=Counter(); record_ids=Counter(); fingerprints=Counter(); years=Counter(); fields=Counter(); invalid=Counter(); pairs=Counter()
 for b in blocks:
  path=input_dir/f"egif_records_{b['year']}.jsonl"
  with path.open(encoding='utf-8') as f:
   for line in f:
    r=json.loads(line); totals['records']+=1; years[r.get('year')]+=1; source_ids[r.get('source_record_id')]+=1; db_ids[r.get('source_database_id')]+=1; record_ids[r['record_id']]+=1; fingerprints[substantial_fingerprint(r)]+=1
    if r.get('geometry') is not None or r.get('geometry_ids')!=[]: invalid['non_null_geometry']+=1
    loc=r.get('source_declared_location') or {}
    for name,key in [('sheet','sheet'),('grid','grid'),('province','province_code'),('community','community_code'),('municipality','municipality_code')]: fields[name]+=int(bool(loc.get(key)))
    fields['xy'] += int(bool(loc.get('x') and loc.get('y')))
    key=pair_key(normalize_component(loc.get('sheet')), normalize_component(loc.get('grid')))
    if key: pairs[key] += 1
    fields['cause']+=int(r.get('cause_raw') is not None); fields['forest_area']+=int(r.get('reported_forest_area_ha') is not None); fields['detection']+=int(r.get('detection_date') is not None); fields['extinction']+=int(r.get('extinction_date') is not None)
 # Classifications are reproduced from the checksum-bound ES-1.5 audit rather
 # than re-running its national XML location acquisition/crosswalk here.
 cc_path=ROOT/'data/sources/ccinif_historical_grid_manifest.json'
 cc_payload=json.loads(cc_path.read_text())
 cc=cc_payload['egif_crosswalk']
 duplicate_fingerprints=[count for count in fingerprints.values() if count > 1]
 result={'records':totals['records'],'years':[min(years),max(years)],'year_count':len(years),'manifest_records':m['totals']['records'],'input_manifest_sha256':sha256_file(args.input_manifest),'field_presence':dict(fields),'unique_complete_hoja_cuad_pairs':len(pairs),'invalid':dict(invalid),'source_record_id_duplicate_values':sum(1 for k,v in source_ids.items() if k is not None and v>1),'idpif_duplicate_values':sum(1 for k,v in db_ids.items() if k is not None and v>1),'record_id_duplicate_values':sum(1 for v in record_ids.values() if v>1),'substantially_identical_id_distinct_groups':len(duplicate_fingerprints),'substantially_identical_id_distinct_records':sum(duplicate_fingerprints),'substantial_fingerprint_definition':'year, dates, declared location, raw cause, declared surfaces and form model; identifiers, provenance and original_attributes excluded; anomaly signal only, never an identity rule','es15_crosswalk_reused':cc,'es15_crosswalk_manifest':str(cc_path.relative_to(ROOT)),'es15_crosswalk_manifest_sha256':sha256_file(cc_path)}
 atomic_write_json(args.output,result); print(json.dumps(result,ensure_ascii=False)); return 0
if __name__=='__main__': raise SystemExit(main())
