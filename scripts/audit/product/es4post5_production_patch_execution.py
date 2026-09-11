#!/usr/bin/env python3
"""Read-only, resumable POST5 acceptance; never dispatches or deploys."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import subprocess
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', required=True, choices=('precheck', 'before-dispatch', 'static', 'temporal', 'popup', 'interactions', 'regressions', 'permalinks', 'clean-cache', 'check'))
    parser.add_argument('--scenario')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/es4post5/observations.json')
    args = parser.parse_args()
    data = json.loads(args.output.read_text()) if args.output.exists() else {}
    group = args.group
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
        raw = P.TEMPORAL.observe(P.CHROME, P.query_url(PRODUCTION, {'smoke':'pais_valencia','from':start,'to':end,'egif_scope':'ES:CCAA:10','territory_select':'ES:CCAA:10','territory_restore':'1'}), selected)
        row = P.compact_temporal_row(raw)
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
            row = P.native_restore_stage(PRODUCTION, captured, 180, reload_after_navigation=stage == 'native_reload')
            restored = row['after_reload' if stage == 'native_reload' else 'fresh_tab']['state']
            row['passed'] = P.permalink_logical_state(captured['before']['state']) == P.permalink_logical_state(restored)
        else:
            state_hash = P.REMOTE.e3d2.LEGACY_HISTORIC if stage == 'legacy_historic' else P.REMOTE.shell.LEGACY_ELX_EFFIS_HASH
            row = P.legacy_permalink_stage(PRODUCTION, state_hash, 180)
            expected_year = 1995 if stage == 'legacy_historic' else 2025
            row['passed'] = row['state']['from'] == expected_year and row['state']['to'] == expected_year and not row['errors']
    elif group == 'clean-cache':
        row = {'identity': identity(PRODUCTION), 'staging': identity(STAGING)}
        row['passed'] = row['identity']['site-identity.json']['sha256'] == P.EXPECTED['site_identity_sha256'] and row['staging']['site-identity.json']['sha256'] == P.EXPECTED['site_identity_sha256']
    else:
        failures = [key for key, value in data.items() if isinstance(value, dict) and value.get('passed') is False]
        required = ['precheck','before-dispatch','static','interactions','regressions','clean-cache'] + ['temporal:'+n for n in ('gva_1993_2024','gva_1995','gva_2024','recurrence_2000_2020')] + ['popup:'+n for n in P.POPUP_CASES] + ['permalinks:'+n for n in P.PERMALINK_STAGES]
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
