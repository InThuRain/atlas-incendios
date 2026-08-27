#!/usr/bin/env python3
"""Mide archivos GeoJSON diagnósticos ES-3 con Leaflet Canvas local."""
from __future__ import annotations
import argparse, gzip, json, os, statistics, sys, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmarks/gva_frontend'))
from cdp_client import run_page
DEFAULT=(
 ('spain_overview','data/derived/spain/es3/assets/esfire30-overview-national.geojson'),
 ('galicia_1985_1992','data/derived/spain/es3/assets/partitions/esfire30-12-1985-1992.geojson'),
 ('andalucia_1985_1992','data/derived/spain/es3/assets/partitions/esfire30-01-1985-1992.geojson'),
 ('cataluna_1985_1992','data/derived/spain/es3/assets/partitions/esfire30-09-1985-1992.geojson'),
 ('pais_valencia_1985_1992','data/derived/spain/es3/assets/partitions/esfire30-10-1985-1992.geojson'),
)
def main():
 p=argparse.ArgumentParser();p.add_argument('--mobile',action='store_true');p.add_argument('--repetitions',type=int,default=1);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 h=lambda *x,**y:SimpleHTTPRequestHandler(*x,directory=str(ROOT),**y);s=ThreadingHTTPServer(('127.0.0.1',0),h);threading.Thread(target=s.serve_forever,daemon=True).start();result={}
 try:
  for name,dataset in DEFAULT:
   path=ROOT/dataset;url=f'http://127.0.0.1:{s.server_port}/benchmarks/es3/geojson_benchmark.html?dataset={quote(dataset)}';rows=[run_page('/usr/bin/google-chrome',url,'390,844' if a.mobile else '1280,800',timeout=180) for _ in range(a.repetitions)]
   if any('error'in row for row in rows):raise RuntimeError(rows)
   result[name]={'dataset':dataset,'raw_bytes':path.stat().st_size,'gzip_bytes':len(gzip.compress(path.read_bytes(),mtime=0)),'runs':rows,'median':{key:statistics.median(row[key] for row in rows if row[key] is not None) for key in ('geometry_count','fetch_ms','parse_ms','render_ms','heap_delta_bytes')}}
 finally:s.shutdown();s.server_close()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'schema_version':1,'renderer':'Leaflet 1.9.4 Canvas','viewport':'390x844' if a.mobile else '1280x800','scenarios':result},indent=2)+'\n',encoding='utf-8');print(a.output)
if __name__=='__main__':raise SystemExit(main())
