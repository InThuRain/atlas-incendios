#!/usr/bin/env python3
"""Reúne las mediciones ES-3 sin copiar assets diagnósticos a Git."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DERIVED=ROOT/'data/derived/spain/es3'
def load(name): return json.loads((DERIVED/name).read_text(encoding='utf-8'))
def sha(path):
 d=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):d.update(block)
 return d.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'benchmarks/es3/results.json');a=p.parse_args()
 core=load('results.json');pm=DERIVED/'assets/esfire30-national.pmtiles';mb=DERIVED/'assets/esfire30-national.mbtiles'
 fidelity=DERIVED/'assets/esfire30-national-fidelity.pmtiles'
 out={'schema_version':1,'phase':'ES-3 diagnostic benchmark','dataset':{'name':'ESFire30 v1','doi':'10.5281/zenodo.18449006','records':core['records'],'years':core['years'],'source_crs':core['source']['source_crs'],'transformation':core['source']['transformation'],'vertices':core['vertices'],'territory_relations':core['territory_relations']},'geojson':{'assets':core['assets'],'desktop':load('geojson-desktop.json'),'mobile':load('geojson-mobile.json')},'pmtiles':{'visual_overview':{'path':'data/derived/spain/es3/assets/esfire30-national.pmtiles','bytes':pm.stat().st_size,'sha256':sha(pm),'mbtiles_bytes':mb.stat().st_size,'min_zoom':4,'max_zoom':14,'addressed_tiles':89568,'tile_contents':89559,'feature_retention':'drop-smallest-as-needed: visual overview only, not feature-complete at every zoom','desktop':load('vector-desktop.json'),'mobile':load('vector-mobile.json')},'fidelity_candidate':{'path':'data/derived/spain/es3/assets/esfire30-national-fidelity.pmtiles','bytes':fidelity.stat().st_size,'sha256':sha(fidelity),'min_zoom':4,'max_zoom':14,'feature_retention':'no tile/feature limits and no tiny-polygon reduction at maximum zoom; must be revalidated per zoom before production','desktop':load('vector-fidelity-desktop.json'),'mobile':load('vector-fidelity-mobile.json')},'input_properties':['geometry_id','year'],'selection_contract':'geometry_id remains a vector-tile property and joins the separate lookup; MVT numeric feature id is intentionally not used.'},'simplification_sample':{'10m':load('simplification-10m.json'),'30m':load('simplification-30m.json'),'100m':load('simplification-audit.json')},'limits':['Measurements are localhost/headless diagnostics, not a production deployment.','PMTiles requests require an HTTP server with Range support.','No asset in data/derived is published or used by the Valencian frontend.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(a.output)
if __name__=='__main__':main()
