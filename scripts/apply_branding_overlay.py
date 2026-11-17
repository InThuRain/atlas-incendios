"""Apply exact accepted logo/theme bytes, with complete before/after CI gates."""
import argparse
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path('accepted-staging/scripts').resolve()))
import check_national_product_artifact as C
import apply_view_data_export_overlay as B

def main():
    p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);a=p.parse_args()
    overlay=Path('branding-overlay');contract=json.loads(Path('branding-contract.json').read_text())
    before=B.physical(a.site)
    paths=set(contract['changed']+contract['added'])|{'asset-manifest.json','site-identity.json'}
    assert not any(p.is_symlink() for p in overlay.rglob('*'))
    assert {p.relative_to(overlay).as_posix() for p in overlay.rglob('*') if p.is_file()}==paths
    expected=contract['identity']
    assert C.sha256(overlay/'site-identity.json')==expected['site_identity_sha256']
    assert C.sha256(overlay/'asset-manifest.json')==expected['manifest_sha256']
    old=C.read_json(a.site/'asset-manifest.json');new=C.read_json(overlay/'asset-manifest.json')
    for key in ['external_runtime_dependencies','runtime_external_data_domains']:assert old[key]==new[key]
    prev={r['path']:r for r in old['files']};nxt={r['path']:r for r in new['files']}
    assert set(nxt)-set(prev)==set(contract['added']) and not set(prev)-set(nxt)
    assert {n for n in prev if prev[n]!=nxt[n]}==set(contract['changed'])
    for name in paths:
        target=a.site/name;assert not target.is_symlink()
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(overlay/name,target)
    final=C.check(a.site)
    assert final['failures']==['external runtime dependencies'],final
    assert final['site_identity_sha256']==expected['site_identity_sha256']
    assert final['asset_manifest_sha256']==expected['manifest_sha256']
    assert final['payload_fingerprint']==expected['payload_fingerprint']
    Path('runner-branding-gate.json').write_text(json.dumps(dict(passed=True,before=before,final=final),indent=2)+'\n')
    print('PASS_EXACT_BRANDING_ARTIFACT')
if __name__=='__main__':main()
