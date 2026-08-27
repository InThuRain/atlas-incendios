#!/usr/bin/env python3
"""Run reproducible Chromium measurements over existing national EGIF assets.

This laboratory runner never invokes the builder. It serves the repository
read-only, opens the isolated HTML harness and writes only an ignored results
file. ``cold`` starts a fresh Chromium profile. ``warm`` uses a fresh profile
too, but the harness performs one discarded priming pass before measuring a
second pass in that same browser context.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import run_page  # type: ignore

HARNESS = ROOT / "benchmarks/es4b5c/egif_benchmark.html"
SCENARIOS_PATH = ROOT / "benchmarks/es4b5c/scenarios.json"
MANIFEST = ROOT / "data/web/spain/egif/2026-08-27/manifest.json"
DEFAULT_OUTPUT = ROOT / "benchmarks/es4b5c/results.json"
DEFAULT_CHROME = "/usr/bin/google-chrome"


class QuietCacheHandler(SimpleHTTPRequestHandler):
    """Static local server with immutable caching only for the built assets."""

    def log_message(self, _format, *args):
        return

    def end_headers(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/data/web/spain/egif/2026-08-27/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def git_revision() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def browser_version(chrome: str) -> str | None:
    try:
        return subprocess.check_output([chrome, "--version"], text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--all", action="store_true", help="run the ten approved scenarios")
    group.add_argument("--scenario", action="append", help="scenario ID; repeat for several")
    parser.add_argument("--desktop", action="store_true", help="1440×900 viewport")
    parser.add_argument("--mobile", action="store_true", help="390×844 viewport (viewport emulation only)")
    parser.add_argument("--cold", action="store_true", help="fresh Chromium profile per run")
    parser.add_argument("--warm", action="store_true", help="prime then measure in one fresh Chromium profile")
    parser.add_argument("--resume", action="store_true", help="keep complete scenario/device/cache rows")
    parser.add_argument("--check", action="store_true", help="validate a prior results JSON without opening Chromium")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chrome", default=DEFAULT_CHROME)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)
    if not args.all and not args.scenario:
        parser.error("indica --all o al menos un --scenario")
    if not args.desktop and not args.mobile:
        args.desktop = True
    if not args.cold and not args.warm:
        args.cold = True
    return args


def requested_scenarios(args: argparse.Namespace, definitions: list[dict]) -> list[dict]:
    index = {item["id"]: item for item in definitions}
    ids = [item["id"] for item in definitions if item.get("include_in_all", True)] if args.all else args.scenario
    unknown = sorted(set(ids) - set(index))
    if unknown:
        raise ValueError("Escenario desconocido: " + ", ".join(unknown))
    return [index[item] for item in ids]


def plan(args: argparse.Namespace, definitions: list[dict]) -> list[dict]:
    devices = []
    if args.desktop:
        devices.append({"id": "desktop", "viewport": "1440,900", "note": "headless Chromium desktop viewport"})
    if args.mobile:
        devices.append({"id": "mobile_390x844", "viewport": "390,844", "note": "390×844 viewport; no mobile CPU, UA or network throttling"})
    cache_modes = (["cold"] if args.cold else []) + (["warm"] if args.warm else [])
    return [{"scenario": scenario, "device": device, "cache_mode": cache_mode}
            for scenario in requested_scenarios(args, definitions) for device in devices for cache_mode in cache_modes]


def result_key(item: dict) -> str:
    return f"{item['scenario']['id']}::{item['device']['id']}::{item['cache_mode']}"


def valid_row(row: dict, item: dict, manifest_sha256: str) -> bool:
    return row.get("status") == "complete" and row.get("scenario") == item["scenario"]["id"] and row.get("device", {}).get("id") == item["device"]["id"] and row.get("cache_mode") == item["cache_mode"] and row.get("manifest_sha256") == manifest_sha256 and not row.get("errors")


def validate_results(payload: dict, jobs: list[dict], manifest_sha256: str) -> list[str]:
    errors: list[str] = []
    rows = payload.get("runs", {})
    for item in jobs:
        key = result_key(item)
        if key not in rows:
            errors.append(f"missing result: {key}")
        elif not valid_row(rows[key], item, manifest_sha256):
            errors.append(f"invalid result: {key}")
    return errors


def start_server() -> tuple[ThreadingHTTPServer, str]:
    handler = lambda *items, **kwargs: QuietCacheHandler(*items, directory=str(ROOT), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    definitions = read_json(SCENARIOS_PATH)["scenarios"]
    jobs = plan(args, definitions)
    manifest_sha = sha256_file(MANIFEST)
    output = args.output.resolve()
    payload = read_json(output) if output.exists() else {"schema_version": 1, "phase": "ES-4B5C", "runs": {}}
    if args.check:
        errors = validate_results(payload, jobs, manifest_sha)
        print(json.dumps({"valid": not errors, "errors": errors, "output": str(output)}, ensure_ascii=False))
        return 0 if not errors else 2

    server, base_url = start_server()
    try:
        for item in jobs:
            key = result_key(item)
            existing = payload["runs"].get(key)
            if args.resume and existing and valid_row(existing, item, manifest_sha):
                print(f"{key}: reutilizado", flush=True)
                continue
            query = urlencode({"scenario": item["scenario"]["id"], "cache": item["cache_mode"], "manifest": "/data/web/spain/egif/2026-08-27/manifest.json"})
            url = f"{base_url}/benchmarks/es4b5c/egif_benchmark.html?{query}"
            print(f"{key}: ejecutando", flush=True)
            try:
                result = run_page(args.chrome, url, item["device"]["viewport"], timeout=args.timeout)
                if result.get("error"):
                    raise RuntimeError(result["error"])
                payload["runs"][key] = {
                    "status": "complete", "scenario": item["scenario"]["id"], "scenario_label": item["scenario"]["label"],
                    "device": item["device"], "cache_mode": item["cache_mode"], "manifest_sha256": manifest_sha,
                    "result": result, "errors": [],
                }
            except BaseException as exc:
                payload["runs"][key] = {
                    "status": "failed", "scenario": item["scenario"]["id"], "scenario_label": item["scenario"]["label"],
                    "device": item["device"], "cache_mode": item["cache_mode"], "manifest_sha256": manifest_sha,
                    "errors": [str(exc) or type(exc).__name__],
                }
                atomic_json(output, payload)
                raise
            payload.update({
                "schema_version": 1, "phase": "ES-4B5C", "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "environment": {"git_commit": git_revision(), "browser": browser_version(args.chrome), "python": sys.version.split()[0],
                                "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
                                "manifest": str(MANIFEST.relative_to(ROOT)), "manifest_sha256": manifest_sha,
                                "server": {"kind": "local_python_http", "compression": "none", "asset_cache_control": "public, max-age=31536000, immutable"}},
            })
            atomic_json(output, payload)
    finally:
        server.shutdown(); server.server_close()
    errors = validate_results(payload, jobs, manifest_sha)
    print(json.dumps({"valid": not errors, "errors": errors, "output": str(output), "runs": len(payload["runs"])}, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
