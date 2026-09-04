#!/usr/bin/env python3
"""E4A: identity and delivery gate for the exact national product artifact.

It deliberately performs only small, representative remote product checks.
The human/product journey acceptance remains the next phase (E4B).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_URL = "https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/"
DEFAULT_ARTIFACT = ROOT / "build/national-product-staging"
DEFAULT_OUTPUT = ROOT / "data/audit/product/es4e4a_national_product_staging_deployment.json"
EXPECTED = {
    "site_file_count": 497,
    "site_total_bytes": 812510441,
    "payload_file_count": 495,
    "payload_total_bytes": 812291384,
    "payload_fingerprint": "10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3",
    "asset_manifest_sha256": "377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e",
    "site_identity_sha256": "f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e",
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
CHECKER = load(ROOT / "scripts/check_national_product_artifact.py", "es4e4a_checker")
HTTP = load(ROOT / "scripts/audit/hosting/es4c3d_real_hosting_range.py", "es4e4a_http")
EVALUATION = load(ROOT / "benchmarks/es4e3c2_basemap/run.py", "es4e4a_evaluation")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def remote_url(base: str, path: str = "") -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


def request_json(base: str, path: str) -> tuple[dict, dict]:
    response = HTTP.request(remote_url(base, path), headers={"Accept-Encoding": "identity"})
    if response["status"] != 200:
        raise RuntimeError(f"HTTP {response['status']} leyendo {path}")
    return json.loads(response["body"].decode("utf-8")), response


def pmtiles_descriptor(manifest: dict, logical_id: str) -> dict:
    descriptor = manifest.get("pmtiles_assets", {}).get(logical_id)
    if not isinstance(descriptor, dict):
        raise RuntimeError(f"PMTiles ausente en manifest: {logical_id}")
    for key in ("runtime_path", "bytes", "sha256"):
        if key not in descriptor:
            raise RuntimeError(f"PMTiles sin {key}: {logical_id}")
    return descriptor


def range_probe(base: str, artifact: Path, descriptor: dict, start: int, end: int) -> dict:
    path = descriptor["runtime_path"]
    response = HTTP.request(remote_url(base, path), headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"})
    local = artifact / path
    with local.open("rb") as source:
        source.seek(start)
        expected = source.read(end - start + 1)
    total = descriptor["bytes"]
    return {
        "request": f"bytes={start}-{end}",
        "status": response["status"],
        "content_range": response["headers"].get("content-range"),
        "bytes": len(response["body"]),
        "byte_identical_to_local": response["body"] == expected,
        "elapsed_ms": response["elapsed_ms"],
        "headers": response["headers"],
        "passed": response["status"] == 206
        and HTTP.parse_content_range(response["headers"].get("content-range")) == (start, end, total)
        and response["body"] == expected,
    }


def pmtiles_checks(base: str, artifact: Path, descriptor: dict) -> dict:
    size = descriptor["bytes"]
    path = descriptor["runtime_path"]
    head = HTTP.request(remote_url(base, path), method="HEAD")
    middle = max(0, (size // 2) - 8192)
    probes = {
        "0_0": range_probe(base, artifact, descriptor, 0, 0),
        "initial": range_probe(base, artifact, descriptor, 0, 16383),
        "middle": range_probe(base, artifact, descriptor, middle, middle + 16383),
        "final": range_probe(base, artifact, descriptor, size - 16384, size - 1),
    }
    return {
        "path": path,
        "expected_bytes": size,
        "expected_sha256": descriptor["sha256"],
        "head": {key: value for key, value in head.items() if key != "body"},
        "probes": probes,
        "passed": head["status"] == 200 and all(row["passed"] for row in probes.values()),
    }


def representative_assets(base: str, manifest: dict) -> list[dict]:
    required = ("frontend", "summary", "highlights", "territories", "icv", "effis")
    rows = []
    for family in required:
        candidates = [row for row in manifest.get("files", []) if row.get("family") == family]
        if not candidates:
            rows.append({"family": family, "passed": False, "failure": "family absent"})
            continue
        descriptor = min(candidates, key=lambda row: (row["bytes"], row["path"]))
        response = HTTP.request(remote_url(base, descriptor["path"]), headers={"Accept-Encoding": "identity"})
        body = response["body"]
        rows.append({
            "family": family, "path": descriptor["path"], "status": response["status"],
            "bytes": len(body), "sha256": sha256_bytes(body),
            "expected_bytes": descriptor["bytes"], "expected_sha256": descriptor["sha256"],
            "headers": response["headers"],
            "passed": response["status"] == 200 and len(body) == descriptor["bytes"] and sha256_bytes(body) == descriptor["sha256"],
        })
    return rows


def glyph_checks(base: str, manifest: dict) -> list[dict]:
    glyphs = sorted(row for row in manifest.get("files", []) if row.get("family") == "glyph")
    rows = []
    for descriptor in glyphs:
        response = HTTP.request(remote_url(base, descriptor["path"]), method="HEAD")
        rows.append({"path": descriptor["path"], "status": response["status"], "headers": response["headers"], "passed": response["status"] == 200})
    return rows


def wait_ready(client, deadline: float) -> None:
    condition = "document.querySelector('#runtime-test-output')?.dataset.complete === 'true' && window.__atlasBasemapContext?.status === 'ready' && Boolean(window.__es4cRuntime?.map)"
    while not client.evaluate(condition):
        if time.monotonic() > deadline:
            detail = client.evaluate("({basemap:window.__atlasBasemapContext,test:document.querySelector('#runtime-test-output')?.textContent,error:document.querySelector('#national-bootstrap-error')?.textContent})")
            raise TimeoutError(f"El staging no llegó a ready: {detail}")
        time.sleep(.08)
    EVALUATION.wait_for_map_stable(client, deadline)


def browser_fetch_range(client, pmtiles_url: str) -> dict:
    expression = """(async () => {
      try {
        const response = await fetch(__URL__, {headers:{Range:'bytes=0-0'}});
        const body = await response.arrayBuffer();
        return {status:response.status, content_range:response.headers.get('content-range'), bytes:body.byteLength};
      } catch (error) { return {error:String(error)}; }
    })()""".replace("__URL__", json.dumps(pmtiles_url))
    return client.evaluate(expression)


def browser_smoke(base: str, chrome: str, name: str, query: dict, device: str, timeout: int, pmtiles_path: str) -> dict:
    url = remote_url(base, "index.html") + "?" + urlencode(query)
    with EVALUATION.chrome_session(chrome, device, timeout) as (client, deadline):
        client.command("Page.navigate", {"url": url})
        wait_ready(client, deadline)
        direct_range = browser_fetch_range(client, remote_url(base, pmtiles_path))
        result = client.evaluate("""(() => {
          const output=JSON.parse(document.querySelector('#runtime-test-output')?.textContent||'{}');
          const map=window.__es4cRuntime?.map;
          const resources=performance.getEntriesByType('resource').map(entry=>({name:entry.name,transfer_size:entry.transferSize||0,response_status:entry.responseStatus||null}));
          const cardText=[...document.querySelectorAll('.metric-card,.summary-card,[data-metric]')].map(node=>node.innerText).join(' | ');
          return {shell:Boolean(document.querySelector('#national-product-shell')),map:Boolean(map),map_loaded:Boolean(map?.loaded()),
            basemap:window.__atlasBasemapContext, state:window.__es4cRuntime?.getState(),errors:output.errors||[],
            bootstrap_error:document.querySelector('#national-bootstrap-error')?.textContent||'',
            histogram_rows:document.querySelectorAll('#histogram-data-body tr').length,
            histogram_bars:document.querySelectorAll('#histogram-chart button').length,
            cards:cardText, attribution:document.querySelector('.map-attribution')?.innerText||document.body.innerText,
            map_rect:(()=>{const rect=document.querySelector('.map-region')?.getBoundingClientRect();return rect&&{top:rect.top,bottom:rect.bottom,width:rect.width,height:rect.height};})(),
            resources};
        })()""")
    origin = urlparse(base).hostname
    external = sorted({urlparse(row["name"]).hostname for row in result["resources"] if urlparse(row["name"]).hostname and urlparse(row["name"]).hostname != origin})
    pmtiles_resources = [row for row in result["resources"] if pmtiles_path in urlparse(row["name"]).path]
    return {
        "scenario": name, "device": device, "url": url, "status": "PASS" if (
            result["shell"] and result["map"] and result["map_loaded"] and result["basemap"].get("status") == "ready"
            and not result["errors"] and not result["bootstrap_error"] and not external and direct_range.get("status") == 206
        ) else "FAIL",
        "runtime": {key: value for key, value in result.items() if key != "resources"},
        "browser_range_fetch": direct_range, "external_runtime_domains": external,
        "pmtiles_resources": pmtiles_resources,
        "full_download_observed": any(row["response_status"] == 200 and row["transfer_size"] >= 63052056 for row in pmtiles_resources),
    }


def build(base: str, artifact: Path, chrome: str, timeout: int) -> dict:
    local = CHECKER.check(artifact)
    if not local.get("valid"):
        raise RuntimeError("FAIL_ARTIFACT_IDENTITY: " + ", ".join(local.get("failures", [])))
    manifest, remote_manifest = request_json(base, "asset-manifest.json")
    identity, remote_identity = request_json(base, "site-identity.json")
    manifest_sha = sha256_bytes(remote_manifest["body"])
    identity_sha = sha256_bytes(remote_identity["body"])
    protomaps = pmtiles_descriptor(manifest, "protomaps_basemap_pmtiles")
    esfire30 = pmtiles_descriptor(manifest, "esfire30_fire_pmtiles")
    ranges = {"protomaps": pmtiles_checks(base, artifact, protomaps), "esfire30": pmtiles_checks(base, artifact, esfire30)}
    assets = representative_assets(base, manifest)
    glyphs = glyph_checks(base, manifest)
    smokes = [
        browser_smoke(base, chrome, "spain_1995", {"smoke":"spain","from":1995,"to":1995,"egif_scope":"ES"}, "desktop", timeout, esfire30["runtime_path"]),
        browser_smoke(base, chrome, "gva_1995", {"smoke":"pais_valencia","from":1995,"to":1995,"egif_scope":"ES:CCAA:10"}, "desktop", timeout, esfire30["runtime_path"]),
        browser_smoke(base, chrome, "elx_2025", {"smoke":"pais_valencia","from":2025,"to":2025,"egif_scope":"ES:CCAA:10","municipality_select":"ES:MUN:03065"}, "desktop", timeout, esfire30["runtime_path"]),
        browser_smoke(base, chrome, "mobile_spain", {"smoke":"spain","from":1995,"to":1995,"egif_scope":"ES"}, "mobile", timeout, esfire30["runtime_path"]),
    ]
    production = HTTP.request("https://inthurain.github.io/atlas-incendios/", method="HEAD")
    cache_paths = {"html":"", "js":"runtime/app.js", "json":"data/egif/v1/2026-08-27/manifest.json", "glyph":glyphs[0]["path"] if glyphs else "", "protomaps":protomaps["runtime_path"], "esfire30":esfire30["runtime_path"]}
    headers = {name: HTTP.request(remote_url(base, path), method="HEAD")["headers"] for name, path in cache_paths.items()}
    failures = []
    if any(local.get(key) != expected for key, expected in EXPECTED.items()): failures.append("local_identity")
    if manifest_sha != EXPECTED["asset_manifest_sha256"]: failures.append("remote_asset_manifest")
    if identity_sha != EXPECTED["site_identity_sha256"]: failures.append("remote_site_identity")
    if identity.get("site_file_count") != EXPECTED["site_file_count"] or identity.get("site_total_bytes") != f"{EXPECTED['site_total_bytes']:020d}": failures.append("remote_site_contract")
    if manifest.get("payload_fingerprint", {}).get("sha256") != EXPECTED["payload_fingerprint"]: failures.append("remote_payload_fingerprint")
    failures.extend(f"range:{name}" for name, row in ranges.items() if not row["passed"])
    failures.extend(f"asset:{row['family']}" for row in assets if not row["passed"])
    if len(glyphs) != 9 or any(not row["passed"] for row in glyphs): failures.append("glyphs")
    failures.extend(f"smoke:{row['scenario']}" for row in smokes if row["status"] != "PASS" or row["full_download_observed"])
    if production["status"] != 200: failures.append("production_root")
    return {
        "phase": "ES-4E4A", "endpoint": remote_url(base), "local_identity": local,
        "remote_identity": {"asset_manifest_sha256":manifest_sha,"site_identity_sha256":identity_sha,"site_identity":identity,"asset_manifest_headers":remote_manifest["headers"],"site_identity_headers":remote_identity["headers"]},
        "required_assets": assets, "pmtiles_range": ranges, "glyphs": glyphs,
        "quick_smokes": smokes, "cache_headers": headers,
        "production_status": {"status":production["status"],"headers":production["headers"],"unchanged":production["status"] == 200},
        "remote_artifact_identity_status": "PASS" if not any(item.startswith("remote_") for item in failures) else "FAIL",
        "remote_range_status": "PASS" if not any(item.startswith("range:") for item in failures) else "FAIL",
        "remote_packaging_smoke_status": "PASS" if not any(item.startswith("smoke:") for item in failures) else "FAIL",
        "full_download_observed": any(row["full_download_observed"] for row in smokes),
        "status": "PASS" if not failures else "FAIL", "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        valid = payload.get("status") == "PASS" and not payload.get("failures")
        print(json.dumps({"valid":valid,"failures":payload.get("failures",[]),"output":str(args.output)}, sort_keys=True))
        return 0 if valid else 1
    payload = build(args.base_url, args.artifact.resolve(), args.chrome, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"status":payload["status"],"failures":payload["failures"],"output":str(args.output)}, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
