#!/usr/bin/env python3
"""Deriva el índice runtime ESFire30-territorio desde JSONL ya auditado.

No abre geometrías ni recalcula intersecciones. Todas las relaciones positivas,
incluidos slivers, se incluyen exactamente una vez.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, os, tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/derived/spain/es4c2b/esfire30_territory_relations/manifest.json"
AUDIT = ROOT / "data/audit/esfire30/es4c2b1b_territory_relations.json"
OUTPUT = ROOT / "data/derived/spain/es4c2b/runtime"
EXPECTED = {"geometry_count":119498,"ccaa_relations":120847,"province_relations":121887}

def sha(path):
 d=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): d.update(b)
 return d.hexdigest()
def enc(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def size(v):
 b=enc(v); return {"raw_bytes":len(b),"gzip_bytes":len(gzip.compress(b,compresslevel=9,mtime=0))}
def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.',suffix='.part')
 try:
  with os.fdopen(fd,'wb') as f: f.write(enc(value)); f.write(b'\n'); f.flush(); os.fsync(f.fileno())
  os.replace(tmp,path)
 except BaseException:
  try: os.unlink(tmp)
  except FileNotFoundError: pass
  raise
def load():
 manifest=json.loads(SOURCE.read_text()); ccaa=defaultdict(set); province=defaultdict(set)
 for block in manifest['blocks']:
  path=ROOT/block['relations_path']
  if sha(path)!=block['relations_sha256']: raise ValueError(f'checksum {path}')
  for line in path.read_text().splitlines():
   row=json.loads(line)
   if row['intersection_class']!='positive_area_intersection': raise ValueError('clase')
   target=ccaa if row['territory_level']=='autonomous_community' else province
   target[row['territory_id']].add(row['geometry_id'])
 return manifest,ccaa,province
def build(output):
 manifest,ccaa,province=load()
 ccaa={k:sorted(v) for k,v in sorted(ccaa.items())}; province={k:sorted(v) for k,v in sorted(province.items())}
 ids=set().union(*[set(v) for v in ccaa.values()],*[set(v) for v in province.values()])
 if len(ids)!=EXPECTED['geometry_count'] or sum(map(len,ccaa.values()))!=EXPECTED['ccaa_relations'] or sum(map(len,province.values()))!=EXPECTED['province_relations']: raise ValueError('reconciliación')
 payload={"schema_version":"es4c2b2a-external-territory-index-v1","source_id":"esfire30","semantics":"geometry intersects territory; not administrative fire assignment","geometry_count":len(ids),"ccaa_to_geometry_ids":ccaa,"province_to_geometry_ids":province}
 path=output/'territory-index.json'; atomic(path,payload)
 # Comparativa sin persistir alternativas redundantes.
 forward_ccaa=defaultdict(list); forward_prov=defaultdict(list)
 for territory,items in ccaa.items():
  for gid in items: forward_ccaa[gid].append(territory)
 for territory,items in province.items():
  for gid in items: forward_prov[gid].append(territory)
 direct={"geometry_to_ccaa_ids":{k:sorted(v) for k,v in sorted(forward_ccaa.items())},"geometry_to_province_ids":{k:sorted(v) for k,v in sorted(forward_prov.items())}}
 territory_dict=sorted(set(ccaa)|set(province)); code={v:i for i,v in enumerate(territory_dict)}
 encoded={"territory_dictionary":territory_dict,"geometry_membership":{gid:[[code[x] for x in direct['geometry_to_ccaa_ids'][gid]],[code[x] for x in direct['geometry_to_province_ids'][gid]]] for gid in sorted(ids)}}
 result={"schema_version":"es4c2b2a-runtime-index-manifest-v1","input":{"relation_manifest":str(SOURCE.relative_to(ROOT)),"relation_manifest_sha256":sha(SOURCE),"audit":str(AUDIT.relative_to(ROOT)),"audit_sha256":sha(AUDIT)},"output":{"path":str(path.relative_to(ROOT)),"sha256":sha(path),"format":"compact JSON, sorted arrays","counts":{"geometry_count":len(ids),"ccaa_relations":sum(map(len,ccaa.values())),"province_relations":sum(map(len,province.values()))},"sizes":{"runtime_reverse_direct":size(payload),"forward_direct":size(direct),"forward_territory_dictionary":size(encoded)}}}
 atomic(output/'manifest.json',result); return result
def check(output):
 m=json.loads((output/'manifest.json').read_text()); p=output/'territory-index.json'; errors=[]
 if not p.is_file() or sha(p)!=m['output']['sha256']: errors.append('checksum')
 else:
  d=json.loads(p.read_text()); c=d.get('ccaa_to_geometry_ids',{}); q=d.get('province_to_geometry_ids',{})
  if len(set().union(*map(set,c.values()),*map(set,q.values())))!=EXPECTED['geometry_count']: errors.append('geometrías')
  if sum(map(len,c.values()))!=EXPECTED['ccaa_relations'] or sum(map(len,q.values()))!=EXPECTED['province_relations']: errors.append('relaciones')
  if any(len(x)!=len(set(x)) for x in list(c.values())+list(q.values())): errors.append('duplicados')
 return {"valid":not errors,"failures":errors,"output":str(output/'manifest.json')}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=OUTPUT); p.add_argument('--check',action='store_true'); a=p.parse_args()
 r=check(a.output) if a.check else build(a.output); print(json.dumps(r,ensure_ascii=False)); return 0 if r.get('valid',True) else 1
if __name__=='__main__': raise SystemExit(main())
