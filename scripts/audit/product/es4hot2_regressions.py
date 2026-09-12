"""Read-only HOT2 identity, temporal, delivery and permalink observations."""
import argparse
import contextlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('post5', ROOT / 'scripts/audit/product/es4post5_production_patch_execution.py')
Q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Q)
P = Q.P


def validate(rows):
    failures = []
    if not rows.get('temporal', {}).get('passed'):
        failures.append('temporal')
    for name, probes in rows.get('range', {}).items():
        if not probes or not all(p.get('passed') for p in probes):
            failures.append('range:' + name)
    if len(rows.get('range', {})) != 2:
        failures.append('range:missing')
    if len(rows.get('glyphs', [])) != 9 or not all(r.get('passed') for r in rows.get('glyphs', [])):
        failures.append('glyphs')
    before = rows.get('native_capture', {}).get('before', {}).get('state')
    for name in ('fresh_before_reload', 'after_reload'):
        actual = rows.get('native_restore', {}).get(name, {})
        if not before or P.permalink_logical_state(before) != P.permalink_logical_state(actual.get('state', {})) or actual.get('errors') or not actual.get('map_loaded'):
            failures.append('native:' + name)
    for name, year, center, zoom in (('legacy_historic', 1995, [-.7, 39.3], 8), ('legacy_recent', 2025, [-.71, 38.17], 11)):
        actual = rows.get(name, {}).get('fresh_tab', {})
        s = actual.get('state', {})
        if (s.get('from'), s.get('to'), s.get('center'), s.get('zoom')) != (year, year, center, zoom) or actual.get('errors') or not actual.get('map_loaded'):
            failures.append(name)
    return {'passed': not failures, 'failures': failures}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    rows = json.loads(args.output.read_text()) if args.resume and args.output.exists() else {}
    def save(key, work):
        if key not in rows:
            print(json.dumps({'gate': key, 'status': 'starting'}), flush=True)
            rows[key] = work()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    with contextlib.ExitStack() as stack:
        base = args.base
        if not base:
            B = P.POPUP.load_module('hot2_server', 'benchmarks/es4e3c2_basemap/run.py')
            server, _ = stack.enter_context(B.server_for(args.artifact.resolve()))
            base = f'http://127.0.0.1:{server.server_port}/'
        save('identity', lambda: Q.identity(base))
        save('temporal', lambda: P.remote_temporal(base, 180, {'gva_1993_2024', 'recurrence_2000_2020'}))
        manifest = json.loads((args.artifact / 'asset-manifest.json').read_text())
        save('range', lambda: {name: [P.HOSTING.range_probe(base, args.artifact, descriptor, 0, end) for end in (0, 16383)] for name, descriptor in manifest['pmtiles_assets'].items()})
        save('glyphs', lambda: P.HOSTING.glyph_checks(base, manifest))
        save('native_capture', lambda: P.REMOTE.capture_native_remote(base, 180))
        # A local server can have a new port on resume; preserve the captured hash.
        native_url = base + '#' + rows['native_capture']['before']['url'].split('#', 1)[1]
        save('native_restore', lambda: Q.settled_restore(native_url, True))
        save('legacy_historic', lambda: Q.settled_restore(base + P.REMOTE.e3d2.LEGACY_HISTORIC))
        save('legacy_recent', lambda: Q.settled_restore(base + P.REMOTE.shell.LEGACY_ELX_EFFIS_HASH))
    rows['validation'] = validate(rows)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(rows['validation']), flush=True)
    return int(not rows['validation']['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
