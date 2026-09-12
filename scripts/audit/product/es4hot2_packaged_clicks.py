"""HOT2 real-pointer gate against an existing packaged site; never builds data."""
import argparse
import contextlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('hot1', ROOT / 'scripts/audit/product/es4hot1_map_click_routing.py')
HOT1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(HOT1)


def main():
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--artifact', type=Path)
    target.add_argument('--base')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', nargs='+', default=['icv', 'province', 'municipality', 'multi', 'recovered', 'double0', 'double1', 'esfire30', 'effis', 'mobile', 'filtered', 'hidden', 'period'])
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    rows = json.loads(args.output.read_text()) if args.resume and args.output.exists() else {}
    with contextlib.ExitStack() as stack:
        base = args.base
        if args.artifact:
            artifact = args.artifact.resolve()
            assert (artifact / 'site-identity.json').is_file(), 'Packaged artifact required'
            server, _ = stack.enter_context(HOT1.B.server_for(artifact))
            base = f'http://127.0.0.1:{server.server_port}/'
        for case in args.cases:
            if rows.get(case, {}).get('passed'):
                continue
            print(json.dumps({'case': case, 'status': 'starting'}), flush=True)
            try:
                rows[case] = HOT1.run(base, case)
            except Exception as error:
                rows[case] = {'passed': False, 'error': f'{type(error).__name__}: {error}'}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({'case': case, 'passed': rows[case]['passed']}), flush=True)
            if not rows[case]['passed']:
                return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
