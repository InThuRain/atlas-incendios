"""Close HOT2 from persisted observations and read-only remote receipts.

Never uploads, dispatches, tags, builds or modifies runtime.
"""
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('hot2_regressions', ROOT / 'scripts/audit/product/es4hot2_regressions.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
REPO = 'InThuRain/atlas-incendios-es4c3d4-pages-staging'
RUN = '34699143697'
TAG = 'national-product-v1.0.1-staging-hot2'
EXPECTED_PRODUCTION = 'f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1'


def read(path):
    return json.loads((ROOT / path).read_text())


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def main():
    result = read('data/audit/product/es4hot2_click_routing_staging.json')
    contract = read('config/national-product-hot1-candidate-identity.json')
    remote = read('build/es4hot2/remote-clicks.json')
    clean = read('build/es4hot2/remote-clean.json')
    double_selection = read('build/es4hot2/remote-double-selection.json')
    regressions = read('build/es4hot2/remote-regressions.json')
    release = json.loads(command('gh', 'release', 'view', TAG, '--repo', REPO, '--json', 'tagName,url,isPrerelease,assets'))
    run = json.loads(command('gh', 'run', 'view', RUN, '--repo', REPO, '--json', 'databaseId,url,headSha,status,conclusion,jobs'))
    deployments = json.loads(command('gh', 'api', f'repos/{REPO}/deployments?sha={run["headSha"]}'))
    deployment = next(d for d in deployments if d['environment'] == 'github-pages')
    deployment_status = json.loads(command('gh', 'api', f'repos/{REPO}/deployments/{deployment["id"]}/statuses'))[0]
    runner = read('build/es4hot2/runner/runner-hot2-gate.json')
    production = R.Q.identity(R.Q.PRODUCTION)
    staging = R.Q.identity(R.Q.STAGING)
    tag = command('git', 'ls-remote', 'origin', 'refs/tags/national-product-v1.0.0', 'refs/tags/national-product-v1.0.0^{}')
    remote_main = command('git', 'ls-remote', 'origin', 'refs/heads/main').split()[0]
    failures = []
    asset = next(a for a in release['assets'] if a['name'] == 'national-product-hot1-candidate.tar.gz')
    if asset['size'] != contract['archive']['bytes'] or asset['digest'] != 'sha256:' + contract['archive']['sha256']:
        failures.append('remote_tar')
    if not runner['valid'] or run['conclusion'] != 'success' or deployment_status['state'] != 'success':
        failures.append('deployment')
    for key, field in (('asset-manifest.json', 'asset_manifest_sha256'), ('site-identity.json', 'site_identity_sha256')):
        if staging[key]['sha256'] != contract['site'][field] or staging[key]['status'] != 200:
            failures.append('remote_identity:' + key)
    if production['site-identity.json']['sha256'] != EXPECTED_PRODUCTION or production['root']['status'] != 200:
        failures.append('production_identity')
    if '534cfe37a7120904f48c87bba71b4fcb7423bb5f\trefs/tags/national-product-v1.0.0^{}' not in tag:
        failures.append('production_tag')
    if remote_main != result['git']['origin_main']:
        failures.append('unexpected_origin_main')
    cases = ('icv', 'province', 'municipality', 'multi', 'recovered', 'double0', 'double1', 'esfire30', 'effis', 'mobile', 'filtered', 'hidden', 'period')
    for name in cases:
        row = remote.get(name, {})
        if not row.get('passed') or not row.get('territory_unchanged') or row.get('errors'):
            failures.append('remote_click:' + name)
        if row.get('hover', {}).get('cursor') != 'pointer':
            failures.append('hover:' + name)
    for name in ('icv', 'province', 'mobile'):
        row = clean.get(name, {})
        if not row.get('passed') or not row.get('background', {}).get('passed'):
            failures.append('clean:' + name)
    validation = R.validate(regressions)
    failures.extend(validation['failures'])
    for name in ('double0', 'double1'):
        if not double_selection.get(name, {}).get('chooser_selection', {}).get('passed'):
            failures.append('individual_geometry_selection:' + name)
    resources = [p for rows in (remote, clean) for r in rows.values() for p in r.get('pmtiles_resources', [])]
    full_download = any(p.get('status') == 200 and max(p.get('bytes', 0), p.get('transfer_bytes', 0)) >= 63052056 for p in resources)
    if full_download:
        failures.append('full_download')
    if not resources or any(p.get('status') != 206 for p in resources):
        failures.append('runtime_range_status')
    detail_requests = sorted({u for r in remote.values() for u in r.get('new_resource_urls', []) if 'detail' in u.lower()})
    if detail_requests:
        failures.append('popup_detail_request')
    # Explicit caller examines text and source semantics as well as these gates.
    result.update({
        'status': 'PASS' if not failures else 'FAIL', 'failures': failures,
        'authorization': 'User explicitly authorized upload and staging deployment after local checkpoint b52b3b7.',
        'staging_release': release, 'deployment': {'run': run, 'deployment': deployment, 'status': deployment_status, 'runner_gate': runner},
        'remote_identity': staging, 'remote_clicks': remote, 'clean_profile': clean,
        'individual_2024_geometry_selection': double_selection,
        'remote_regressions': regressions, 'popup_detail_requests': detail_requests,
        'full_download_observed': full_download, 'production_final_identity': production,
        'production_unchanged': production['site-identity.json']['sha256'] == EXPECTED_PRODUCTION,
        'production_tag_receipt': tag,
        'final_git_before_closing_commit': {'head': command('git', 'rev-parse', 'HEAD'), 'origin_main': remote_main, 'ahead_behind': command('git', 'rev-list', '--left-right', '--count', 'HEAD...origin/main')},
        'decision': {'HOTFIX_STAGING_STATUS': 'PASS' if not failures else 'FAIL',
                     'REMOTE_CLICK_ROUTING': 'PASS' if not failures else 'FAIL',
                     'PRODUCTION_HOTFIX_CANDIDATE': 'READY_FOR_V1_0_1_PRODUCTION' if not failures else 'NOT_ACCEPTED'},
        'next_phase': 'ES-4HOT3_V1_0_1_PRODUCTION_EXECUTION' if not failures else 'ES-4HOT2_CLICK_ROUTING_STAGING_FIX',
    })
    result.pop('blocker', None)
    destination = ROOT / 'data/audit/product/es4hot2_click_routing_staging.json'
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'failures': failures, 'deployment_id': deployment['id']}))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
