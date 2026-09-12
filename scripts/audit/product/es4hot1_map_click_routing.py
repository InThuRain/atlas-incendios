"""Real CDP mouse/tap regression: never calls the fire click helper.

Use --base for production reproduction; omit it for a lightweight local
frontend with symlinked existing data. No dataset or PMTiles build.
"""
import argparse
import contextlib
import json
import tempfile
import time
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('post4', ROOT/'scripts/audit/product/es4post4_production_patch_staging.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
H = P.POPUP
B = H.load_module('hot1_browser', 'benchmarks/es4e3c2_basemap/run.py')

SNAPSHOT = """(()=>{const r=window.__es4cRuntime,s=r.getState();return {
territory:Object.fromEntries(['territory_scope','autonomous_community_id','province_id','municipality_id'].map(k=>[k,s[k]])),
selection:Object.fromEntries(Object.entries(s).filter(([k])=>k.startsWith('selected_'))),popup:r.getDirectPopupState()}})()"""

def pixel(client, source=None, fire=None, geometry=None, multi=False, no_admin=False):
    return client.evaluate("""((source,fire,geometry,multi,noAdmin)=>{
      const r=window.__es4cRuntime,m=r.map,c=m.getCanvas(),rect=c.getBoundingClientRect();
      const layers=['icv-perimeters','icv-perimeter-outlines','esfire30-perimeters','esfire30-perimeter-outlines','effis-perimeters','effis-perimeter-outlines'].filter(x=>m.getLayer(x));
      const admin=['official-municipality-territories-fill','official-province-territories-fill','official-ccaa-territories-fill'].filter(x=>m.getLayer(x));
      const points=[[c.clientWidth/2,c.clientHeight/2]];
      for(let y=16;y<c.clientHeight-16;y+=8)for(let x=16;x<c.clientWidth-16;x+=8)points.push([x,y]);
      for(const [x,y] of points){
        if(document.elementFromPoint(rect.x+x,rect.y+y)!==c)continue;
        const pt=m.project(m.unproject([x,y]));
        const seen=new Set(),hits=m.queryRenderedFeatures(pt,{layers}).filter(f=>{const k=f.source+'|'+f.properties.geometry_id;if(seen.has(k))return false;seen.add(k);return true});
        const targets=m.queryRenderedFeatures(pt,{layers:admin});
        if(source ? !hits.some(f=>f.layer.id.startsWith(source+'-')&&(!fire||f.properties.fire_id===fire)&&(!geometry||f.properties.geometry_id===geometry)) : hits.length||!targets.length)continue;
        if(multi&&hits.length<2)continue;
        if(noAdmin&&targets.length)continue;
        return {x:rect.x+x,y:rect.y+y,point:{x,y},lngLat:m.unproject([x,y]),hits:hits.map(f=>({source:f.source,layer:f.layer.id,geometry_id:f.properties.geometry_id})),territories:targets.map(f=>({layer:f.layer.id,properties:f.properties}))};
      }return null;
    })(%s,%s,%s,%s,%s)""" % tuple(json.dumps(x) for x in (source,fire,geometry,multi,no_admin)))

def gesture(client, pt, mobile=False):
    client.command('Input.dispatchMouseEvent',{'type':'mouseMoved','x':pt['x'],'y':pt['y']})
    time.sleep(.15)
    hover=client.evaluate("(()=>{const m=window.__es4cRuntime.map;return {cursor:m.getCanvas().style.cursor,highlight_filters:['icv-hover','esfire30-hover','effis-hover'].filter(l=>m.getLayer(l)).map(l=>({layer:l,filter:m.getFilter(l)}))}})()")
    if mobile:
        client.command('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':pt['x'],'y':pt['y']}]})
        client.command('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    else:
        for kind in ('mousePressed','mouseReleased'):
            client.command('Input.dispatchMouseEvent',{'type':kind,'x':pt['x'],'y':pt['y'],'button':'left','clickCount':1})
    return hover

def trace(client):
    # Observation only: delegate to every original listener, preserving order.
    client.evaluate("""(()=>{const m=window.__es4cRuntime.map;window.__hot1Events=[];
      if(m.__hot1Traced)return;m.__hot1Traced=true;
      m._listeners.click=m._listeners.click.map((fn,i)=>function(e){
        const before=%s;const result=fn.call(this,e);const after=%s;
        window.__hot1Events.push({i,name:fn.name,before,after});return result;
      });})()""" % (SNAPSHOT,SNAPSHOT))

def run(base, name):
    mobile=name=='mobile'
    source='effis' if name=='effis' else 'esfire30' if name=='esfire30' else 'icv'
    year=2025 if source=='effis' else 2024 if name.startswith('double') else 2016 if name in ('recovered','province','municipality','isolated') else 1995
    with B.chrome_session(H.CHROME,'mobile' if mobile else 'desktop',180) as (client,deadline):
        url=P.query_url(base,{'smoke':'pais_valencia','from':year,'to':year,'egif_scope':'ES:CCAA:10','territory_select':'ES:CCAA:10','territory_restore':'1','effis_visible':'1' if source=='effis' else '0'})
        client.command('Page.navigate',{'url':url});H.wait_runtime(client,deadline,'effis' if source=='effis' else 'icv')
        if name in ('province','municipality'):
            client.evaluate("window.__es4cRuntime.setProvinceScope('ES:PROV:03','ES:CCAA:10').then(()=>true)")
        if name=='municipality':
            municipality_id=client.evaluate("window.__es4cRuntime.getIcvResult().fires_by_id.get('gva:pif-cv:2016AL0074').municipality_id")
            if not municipality_id:raise RuntimeError('No documented municipality for fixture')
            # ICV stores INE5; the public territorial API accepts canonical ES-2 IDs.
            if len(municipality_id)==5 and municipality_id.isdigit():municipality_id='ES:MUN:'+municipality_id
            client.evaluate("window.__es4cRuntime.setMunicipalityScope(%s).then(()=>true)" % json.dumps(municipality_id))
        if source=='esfire30' or name=='multi':
            client.evaluate("window.__es4cRuntime.setSourceVisibility('esfire30',true).then(()=>true)")
            if source=='esfire30':client.evaluate("window.__es4cRuntime.setSourceVisibility('icv',false).then(()=>true)")
        H.wait_map_stable(client,deadline)
        fire='gva:pif-cv:2016AL0074' if name in ('recovered','province','municipality','isolated') else 'gva:pif-cv:2024AL0005' if name.startswith('double') else None
        geometry=None
        if name.startswith('double'):
            ids=client.evaluate("window.__es4cRuntime.getIcvResult().features.filter(f=>f.properties.fire_id==='gva:pif-cv:2024AL0005').map(f=>f.properties.geometry_id).sort()")
            geometry=ids[int(name[-1])]
        if name=='multi': H.focus_real_icv_esfire_overlap(client)
        else:H.focus_source_geometry(client,source,fire,geometry)
        H.wait_map_stable(client,deadline)
        pt=pixel(client,source,fire,geometry,name=='multi',name=='isolated')
        if not pt:raise RuntimeError('No uncovered painted pixel: '+name)
        trace(client);before=client.evaluate(SNAPSHOT)
        resources_before=client.evaluate('performance.getEntriesByType("resource").map(x=>x.name)')
        hover=gesture(client,pt,mobile)
        time.sleep(.8);immediate=client.evaluate(SNAPSHOT)
        H.wait_map_stable(client,deadline)
        after=client.evaluate(SNAPSHOT)
        expected=geometry or next(h['geometry_id'] for h in pt['hits'] if h['layer'].startswith(source+'-'))
        row={'point':pt,'hover':hover,'before':before,'immediate':immediate,'after':after,'events':client.evaluate('window.__hot1Events'),
             'expected_geometry':expected,'territory_unchanged':before['territory']==after['territory'],
             'errors':client.evaluate('globalThis.__e3c2BrowserErrors||[]'),
             'human_popup':H.popup_snapshot(client),
             'new_resource_urls':[url for url in client.evaluate('performance.getEntriesByType("resource").map(x=>x.name)') if url not in resources_before]}
        row['passed']=row['territory_unchanged'] and after['popup']['active'] and not row['errors']
        if name!='multi' and len(pt['hits'])==1:
            row['passed']=row['passed'] and expected in after['selection'].values()
        if name in ('hidden','filtered','period'):
            if name=='hidden':
                client.evaluate("window.__es4cRuntime.setSourceVisibility('icv',false).then(()=>true)")
            elif name=='filtered':
                client.evaluate("window.__es4cRuntime.setAnalysisFilter({filter_id:'icv_min_area',filter_type:'min_value',source:'icv',metric_id:'icv_declared_forest_area_ha',value:1000000,unit:'ha'}).then(()=>true)")
            else:
                client.evaluate("document.querySelector('#from-year').value='1968';document.querySelector('#to-year').value='1968';window.__es4cRuntime.applyYears().then(()=>true)")
            H.wait_map_stable(client,deadline)
            invalidated=client.evaluate(SNAPSHOT)
            remaining=client.evaluate("window.__es4cRuntime.map.queryRenderedFeatures(window.__es4cRuntime.map.project(%s),{layers:['icv-perimeters','icv-perimeter-outlines','icv-hover','icv-selected']}).length" % json.dumps(pt['lngLat']))
            gesture(client,pt);time.sleep(.8);H.wait_map_stable(client,deadline)
            removed_after=client.evaluate(SNAPSHOT)
            row['removed_feature']={'before_click':invalidated,'after_click':removed_after,'remaining_rendered_hits':remaining,
                'passed':not invalidated['popup']['active'] and remaining==0 and not removed_after['popup']['active'] and invalidated['territory']!=removed_after['territory']}
            row['passed']=row['passed'] and row['removed_feature']['passed']
        if name in ('icv','province','mobile'):
            client.evaluate('window.__es4cRuntime.closeDirectPopup()')
            bg=pixel(client)
            if not bg: raise RuntimeError('No background pixel')
            bg_before=client.evaluate(SNAPSHOT);gesture(client,bg,mobile);time.sleep(.8)
            H.wait_map_stable(client,deadline);bg_after=client.evaluate(SNAPSHOT)
            row['background']={'point':bg,'before':bg_before,'after':bg_after,'passed':bg_before['territory']!=bg_after['territory'] and not bg_after['popup']['active']}
            row['passed']=row['passed'] and row['background']['passed']
        return row

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base');parser.add_argument('--expect-bug',action='store_true');parser.add_argument('--cases',nargs='+',default=['icv','recovered','province','multi','esfire30','effis','mobile','double0','double1']);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();rows=json.loads(args.output.read_text()) if args.output.exists() else {}
    with contextlib.ExitStack() as stack:
        base=args.base
        if not base:
            directory=Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='atlas-hot1-')))
            site=H.build_site(directory)
            server,_=stack.enter_context(B.server_for(site));base=f'http://127.0.0.1:{server.server_port}/'
        for case in args.cases:
            print(json.dumps({'case':case,'status':'starting'}),flush=True)
            rows[case]=run(base,case)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({'case':case,'passed':rows[case]['passed'],'territory_unchanged':rows[case]['territory_unchanged']}),flush=True)
    return int(not all(not rows[c]['passed'] if args.expect_bug else rows[c]['passed'] for c in args.cases))

if __name__=='__main__':raise SystemExit(main())
