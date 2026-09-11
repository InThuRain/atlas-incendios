#!/usr/bin/env python3
"""Read-only, resumable POST5 acceptance; never dispatches or deploys."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('post4', ROOT / 'scripts/audit/product/es4post4_production_patch_staging.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
PRODUCTION = 'https://inthurain.github.io/atlas-incendios/'
STAGING = P.BASE_URL
EXPECTED_ORIGIN = '84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c'


def command(*args):
    return subprocess.check_output(args, cwd=str(ROOT), text=True).strip()


def identity(base):
    result = {}
    for filename in ('', 'asset-manifest.json', 'site-identity.json'):
        response = P.HOSTING.HTTP.request(base + filename, headers={'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'})
        result[filename or 'root'] = {'status': response['status'], 'sha256': hashlib.sha256(response['body']).hexdigest()}
    return result


def settled_restore(url, reload_page=False):
    with P.REMOTE.evaluation.chrome_session(P.CHROME, 'desktop', 180) as (client, deadline):
        client.command('Page.navigate', {'url':url})
        def settle():
            while not client.evaluate('Boolean(window.__es4cRuntime?.map)'):
                if time.monotonic() > deadline:
                    raise TimeoutError('No runtime in permalink')
                time.sleep(.1)
            while not client.evaluate("(()=>{const r=window.__es4cRuntime,s=r.getState();return (!s.icv_visible||r.getIcvResult()?.status==='complete')&&(!s.effis_visible||r.getEffisResult()?.status==='complete')})()"):
                if time.monotonic() > deadline:
                    raise TimeoutError('Perimeter source did not settle after restore')
                time.sleep(.1)
            while True:
                P.POPUP.wait_map_stable(client, deadline)
                result = client.evaluate("({state:window.__es4cRuntime.getState(),hash:location.hash,map_loaded:window.__es4cRuntime.map.loaded(),errors:globalThis.__e3c2BrowserErrors||[]})")
                if result['map_loaded']:
                    return result
        fresh = settle()
        if reload_page:
            client.command('Page.reload')
            return {'fresh_before_reload':fresh,'after_reload':settle()}
        return {'fresh_tab':fresh}


def precheck():
    prior = json.loads((ROOT / 'data/audit/product/es4post4_production_patch_staging.json').read_text())
    release = json.loads(command('gh', 'release', 'view', prior['staging_release']['tag'], '--repo', prior['staging_release']['repository'], '--json', 'tagName,url,assets,isPrerelease'))
    asset = next(a for a in release['assets'] if a['url'] == prior['staging_release']['asset_url'])
    old, staging = identity(PRODUCTION), identity(STAGING)
    origin = command('git', 'rev-parse', 'origin/main')
    local = json.loads((ROOT / 'build/es4post5/local-gate.json').read_text())
    passed = (origin == EXPECTED_ORIGIN and old['root']['status'] == 200 and staging['root']['status'] == 200
              and old['site-identity.json']['sha256'] == P.PRODUCTION_PRE_POST2_IDENTITY
              and staging['site-identity.json']['sha256'] == P.EXPECTED['site_identity_sha256']
              and staging['asset-manifest.json']['sha256'] == P.EXPECTED['asset_manifest_sha256']
              and asset['size'] == prior['patch_tar']['bytes'] and asset['digest'] == 'sha256:' + prior['patch_tar']['sha256']
              and local['valid'])
    return {'passed': passed, 'local_head': command('git', 'rev-parse', 'HEAD'), 'origin_main': origin,
            'behind_ahead': command('git', 'rev-list', '--left-right', '--count', 'origin/main...HEAD'),
            'worktree': command('git', 'status', '--short'), 'old_production': old, 'staging': staging,
            'release': release, 'local_gate': local}


def finalize(data):
    """Persist the actual deployment receipts and compact browser evidence."""
    run_id = '34620607559'
    repo = 'InThuRain/atlas-incendios'
    run = json.loads(command('gh','run','view',run_id,'--repo',repo,'--json','databaseId,url,headSha,status,conclusion,createdAt,updatedAt,jobs'))
    artifacts = json.loads(command('gh','api',f'repos/{repo}/actions/runs/{run_id}/artifacts'))['artifacts']
    deployment = json.loads(command('gh','api',f'repos/{repo}/deployments/6397065009'))
    deployment_status = json.loads(command('gh','api',f'repos/{repo}/deployments/6397065009/statuses'))[0]
    runner = json.loads((ROOT / 'build/es4post5/runner/runner-national-product-identity.json').read_text())
    clean = json.loads((ROOT / 'build/es4post5/clean-browser.json').read_text())
    required = ['precheck','before-dispatch','static','interactions','regressions','mobile-journey','clean-cache'] + ['temporal:'+n for n in ('gva_1993_2024','gva_1995','gva_2024','recurrence_2000_2020')] + ['popup:'+n for n in P.POPUP_CASES] + ['permalinks:'+n for n in P.PERMALINK_STAGES]
    failures = [k for k in required if not data.get(k, {}).get('passed')]
    failures += ['clean:'+k for k in ('temporal:gva_1993_2024','popup:icv_1995') if not clean.get(k, {}).get('passed')]
    if not runner['valid'] or run['conclusion'] != 'success' or deployment_status['state'] != 'success':
        failures.append('deployment')
    reg = data['regressions']['scenarios']
    summaries = reg['spain_1995']['summary']['result']['territory']['source_summaries']
    spain = {metric['metric_id']:metric['values'][1995-source['year_axis']['from']] for source in summaries for metric in source['metrics']}
    if spain.get('egif_record_count') != 25557 or spain.get('esfire30_perimeter_count') != 5035 or abs(spain.get('egif_declared_forest_area_ha',0)-141082.17) > .01:
        failures.append('spain_metrics')
    regressions = {'spain_1995':spain,'canarias':reg['canarias_1995']['esfire_coverage'], 'scenarios':{key:{field:row.get(field) for field in ('passed','state','ready_ms','errors','external_runtime_domains','network')} for key,row in reg.items()}, 'interactions':data['interactions']}
    result = {
        'phase':'ES-4POST5_PRODUCTION_PATCH_EXECUTION',
        'precheck':{**data['precheck'],'initial_worktree_before_preparation':'no tracked changes; untracked build/ only'},
        'old_production':data['precheck']['old_production'],
        'patch_candidate':{'archive':P.PATCH_TAR,'site':P.EXPECTED,'asset_url':data['precheck']['release']['assets'][0]['url']},
        'rollback_strategy':{'status':'READY','primary':'.github/workflows/pages-national-pre-post2-rollback.yml','expected_identity':P.PRODUCTION_PRE_POST2_IDENTITY,'deep':'.github/workflows/pages-legacy-gva-rollback.yml','gva_anchor':'f7a3532f633a247f33dee3ebba9fbcc316c0e534'},
        'workflow_update':{'path':'.github/workflows/pages-national-product.yml','contract':'config/national-product-post2-patch-identity.json','manual_only':True,'concurrency':'pages','cancel_in_progress':False,'focused_tests':6,'rebuild':False},
        'predeploy_commit':run['headSha'],
        'push':{'commits':command('git','log','--reverse','--format=%H %s',EXPECTED_ORIGIN+'..'+run['headSha']).splitlines(),'before_dispatch':data['before-dispatch'],'normal_push':True,'auto_deploy_observed':False},
        'runner_gate':runner,
        'deployment':{'run':run,'artifacts':[{k:a[k] for k in ('id','name','size_in_bytes')} for a in artifacts],'id':deployment['id'],'sha':deployment['sha'],'status':deployment_status['state'],'completed_at':deployment_status['created_at'],'environment_url':deployment_status['environment_url']},
        'remote_identity':data['static']['remote_identity'],
        'pmtiles':data['static']['pmtiles'],
        'glyphs':data['static']['glyphs'],
        'icv':{name:data['temporal:'+name] for name in ('gva_1993_2024','gva_1995','gva_2024')},
        'temporal':data['temporal:recurrence_2000_2020'],
        'popup':{name:data['popup:'+name] for name in P.POPUP_CASES},
        'multi_hit':data['popup:mixed_overlap'],
        'regressions':regressions,
        'mobile':data['mobile-journey'],
        'permalinks':{key:data['permalinks:'+key] for key in P.PERMALINK_STAGES},
        'clean_cache':{'http':data['clean-cache'],'browser':clean,'method':'fresh temporary Chromium profile per session'},
        'staging':data['clean-cache']['staging'],
        'rollback':{'triggered':False,'result':'NOT_REQUIRED'},
        'production_identity':{'main_commit':run['headSha'],'workflow_run_id':int(run_id),'pages_deployment_id':deployment['id'],**data['static']['remote_identity']},
        'release_tag_recommendation':{'status':'READY_FOR_DECISION','name':'national-product-v1.0.0','reason':'No national-product version tag exists; first versioned national product release after parity acceptance. Earlier untagged production remains traceable by deployment and SHA.','created':False},
        'status':'PASS' if not failures else 'FAIL', 'failures':failures,
        'national_product_status':'LIVE_POST2' if not failures else 'REQUIRES_INVESTIGATION',
        'next_phase':'ES-4POST6_POST_RELEASE_CHECKPOINT' if not failures else 'ES-4POST5_PRODUCTION_PATCH_EXECUTION',
    }
    output = ROOT / 'data/audit/product/es4post5_production_patch_execution.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'failures':failures,'output':str(output)}))
    return int(bool(failures))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', required=True, choices=('precheck', 'before-dispatch', 'static', 'temporal', 'popup', 'interactions', 'regressions', 'permalinks', 'mobile-journey', 'clean-cache', 'check', 'finalize'))
    parser.add_argument('--scenario')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/es4post5/observations.json')
    args = parser.parse_args()
    data = json.loads(args.output.read_text()) if args.output.exists() else {}
    group = args.group
    if group == 'finalize':
        return finalize(data)
    if group == 'precheck':
        row = precheck()
    elif group == 'before-dispatch':
        current = identity(PRODUCTION)
        row = {'identity': current, 'passed': current['site-identity.json']['sha256'] == P.PRODUCTION_PRE_POST2_IDENTITY,
               'local_head': command('git', 'rev-parse', 'HEAD'), 'origin_main': command('git', 'rev-parse', 'origin/main'),
               'behind_ahead': command('git', 'rev-list', '--left-right', '--count', 'origin/main...HEAD'),
               'runs': json.loads(command('gh', 'run', 'list', '--repo', 'InThuRain/atlas-incendios', '--limit', '5', '--json', 'databaseId,name,event,headSha,status,conclusion'))}
    elif group == 'static':
        row = P.static_gate(PRODUCTION, P.ARTIFACT)
    elif group == 'temporal':
        name = args.scenario or 'gva_1993_2024'
        # POST4 partial helper assumes the full-range case is present; observe
        # the selected case directly so each expensive sample runs only once.
        start, end, selected, counts = P.TEMPORAL_CASES[name]
        screenshot = ROOT / 'build/es4post5' / (name + '.png')
        raw = P.TEMPORAL.observe(P.CHROME, P.query_url(PRODUCTION, {'smoke':'pais_valencia','from':start,'to':end,'egif_scope':'ES:CCAA:10','territory_select':'ES:CCAA:10','territory_restore':'1'}), selected, screenshot=screenshot)
        row = P.compact_temporal_row(raw)
        row['screenshot'] = raw['screenshot']
        row['passed'] = (not counts or (row['loaded_records'], row['loaded_geometries']) == counts) and row['temporal']['domain'] == {'from':start,'to':end} and row['temporal']['palette'] == {'old':'rgb(44,123,182)','recent':'rgb(240,82,46)'} and not row['runtime_errors'] and not row['browser_errors'] and 'Año del perímetro' in row['legend']
        group += ':' + name
    elif group == 'popup':
        row = P.remote_popup_cases(PRODUCTION, 180, {args.scenario})
        group += ':' + args.scenario
    elif group == 'interactions':
        row = P.interactions(PRODUCTION, 180)
    elif group == 'regressions':
        row = P.regressions(PRODUCTION, 180)
    elif group == 'permalinks':
        stage = args.scenario
        group += ':' + stage
        if stage == 'native_capture':
            row = {'capture': P.REMOTE.capture_native_remote(PRODUCTION, 180), 'passed': True}
        elif stage in ('native_fresh', 'native_reload'):
            captured = data['permalinks:native_capture']['capture']
            row = settled_restore(captured['before']['url'], reload_page=stage == 'native_reload')
            restored = row['after_reload' if stage == 'native_reload' else 'fresh_tab']['state']
            row['passed'] = P.permalink_logical_state(captured['before']['state']) == P.permalink_logical_state(restored)
        else:
            state_hash = P.REMOTE.e3d2.LEGACY_HISTORIC if stage == 'legacy_historic' else P.REMOTE.shell.LEGACY_ELX_EFFIS_HASH
            # A smoke query runs a scripted camera journey after bootstrap;
            # public permalink acceptance must use the real URL without it.
            row = settled_restore(PRODUCTION + state_hash)['fresh_tab']
            expected_year = 1995 if stage == 'legacy_historic' else 2025
            expected_center, expected_zoom = ([-.7,39.3],8) if stage == 'legacy_historic' else ([-.71,38.17],11)
            row['camera_preserved'] = row['state']['center'] == expected_center and row['state']['zoom'] == expected_zoom
            row['passed'] = row['state']['from'] == expected_year and row['state']['to'] == expected_year and row['map_loaded'] and row['camera_preserved'] and not row['errors']
    elif group == 'mobile-journey':
        harness = P.POPUP.load_module('post5_mobile', 'benchmarks/es4e3c2_basemap/run.py')
        with harness.chrome_session(P.CHROME, 'mobile', 180) as (client, deadline):
            client.command('Page.navigate', {'url': P.query_url(PRODUCTION, {'smoke':'pais_valencia','from':1995,'to':1995,'egif_scope':'ES:CCAA:10','territory_select':'ES:CCAA:10','territory_restore':'1'})})
            P.POPUP.wait_runtime(client, deadline, 'icv')
            client.evaluate("window.__es4cRuntime.setSourceVisibility('esfire30',true).then(()=>true)")
            P.POPUP.wait_map_stable(client, deadline)
            chooser = P.POPUP.direct_case(client, deadline, 'icv', 1995, multi_sources=True)
            choices = client.evaluate("[...document.querySelectorAll('.direct-popup__choices button')].map(b=>({text:b.innerText,id:b.dataset.popupGeometryId}))")
            client.evaluate("document.querySelector('.direct-popup__choices button')?.click()")
            popup = P.POPUP.wait_popup(client, deadline)
            snapshot = P.POPUP.popup_snapshot(client)
            P.TEMPORAL.capture(client, ROOT / 'build/es4post5/mobile-popup.png')
            details = client.evaluate("(()=>{const b=document.querySelector('.direct-popup__details');if(!b)return false;b.click();return true})()")
            row = {'chooser':chooser,'choices':choices,'popup':popup,'snapshot':snapshot,'details_clicked':details,
                   'viewport':client.evaluate('({width:innerWidth,height:innerHeight})'),
                   'legend':client.evaluate("document.querySelector('#user-map-legend')?.innerText"),
                   'errors':client.evaluate('globalThis.__e3c2BrowserErrors||[]')}
            row['passed'] = chooser['popup']['hit_count'] >= 2 and popup['active'] and details and not row['errors'] and row['viewport'] == {'width':390,'height':844}
    elif group == 'clean-cache':
        row = {'identity': identity(PRODUCTION), 'staging': identity(STAGING)}
        row['passed'] = row['identity']['site-identity.json']['sha256'] == P.EXPECTED['site_identity_sha256'] and row['staging']['site-identity.json']['sha256'] == P.EXPECTED['site_identity_sha256']
    else:
        failures = [key for key, value in data.items() if isinstance(value, dict) and value.get('passed') is False]
        required = ['precheck','before-dispatch','static','interactions','regressions','mobile-journey','clean-cache'] + ['temporal:'+n for n in ('gva_1993_2024','gva_1995','gva_2024','recurrence_2000_2020')] + ['popup:'+n for n in P.POPUP_CASES] + ['permalinks:'+n for n in P.PERMALINK_STAGES]
        failures += ['missing:'+key for key in required if key not in data]
        print(json.dumps({'valid':not failures,'failures':failures}))
        return int(bool(failures))
    row['observed_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data[group] = row
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'group':group,'passed':row.get('passed'),'output':str(args.output)}), flush=True)
    return int(not row.get('passed'))


if __name__ == '__main__':
    raise SystemExit(main())
