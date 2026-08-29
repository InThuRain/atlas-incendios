#!/usr/bin/env python3
"""Smokes dirigidos del PMTiles territorial embebido de ES-4C2B2B1."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks/gva_frontend"))
from cdp_client import run_page  # noqa: E402
sys.path.insert(0, str(ROOT / "prototypes/es4c"))
from run_smoke import start_server  # noqa: E402

MANIFEST = ROOT / "data/derived/spain/es4c2b/pmtiles/esfire30-territories-sample-manifest.json"
CASES = {
    "pais_valencia": {"scope": "ccaa", "code": 10, "view": "valencian"},
    "alacant": {"scope": "prov", "code": 3, "view": "valencian"},
    "valencia": {"scope": "prov", "code": 46, "view": "valencian"},
    "galicia": {"scope": "ccaa", "code": 12, "view": "galicia"},
    "ourense": {"scope": "prov", "code": 32, "view": "ourense"},
    "multi_provincia": {"scope": "prov", "code": 3, "view": "valencian", "selected": "alacant_valencia_geometry_id"},
    "multi_provincia_valencia": {"scope": "prov", "code": 46, "view": "valencian", "selected": "alacant_valencia_geometry_id"},
    "multi_ccaa": {"scope": "ccaa", "code": None, "view": "spain", "selected": "multi_ccaa_geometry_id"},
    "year_territory": {"scope": "ccaa", "code": 12, "view": "galicia", "from": 1993, "to": 2002},
    "string_alacant": {"scope": "prov", "code": 3, "view": "valencian", "encoding": "strings"},
}

def run_case(chrome: str, name: str, mobile: bool) -> dict:
    config = CASES[name]; manifest = json.loads(MANIFEST.read_text(encoding="utf-8")); selection = manifest["selection"]
    if name == "multi_ccaa":
        # El caso usa el segundo territorio de una geometría multi-CCAA,
        # obtenido del NDJSON de relaciones del manifest de muestra.
        selected = selection[config["selected"]]
        import importlib.util
        spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build/esfire30/territory_pmtiles.py")
        module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module)
        ccaa, _province, _ = module.load_membership()
        config = {**config, "code": ccaa[selected][1]}
    server, range_state = start_server()
    try:
        query = {"scope": config["scope"], "code": config["code"], "view": config["view"], "from": config.get("from", 1985), "to": config.get("to", 2021), "encoding": config.get("encoding", "slots")}
        if config.get("selected"):
            query["selected_geometry_id"] = selection[config["selected"]]
        from urllib.parse import urlencode
        result = run_page(chrome, f"http://127.0.0.1:{server.server_port}/prototypes/es4c/territory_pmtiles_sample.html?{urlencode(query)}", "390,844" if mobile else "1280,800", timeout=120)
        result.update({"scenario": name, "mobile": mobile, "range": range_state.payload(), "expected": query})
        return result
    finally:
        server.shutdown(); server.server_close()

def validate(rows: list[dict]) -> list[str]:
    errors = []
    for row in rows:
        label = row["scenario"]
        if row.get("errors"): errors.append(f"{label}: {row['errors']}")
        if not row.get("sample_properties", {}).get("geometry_id"): errors.append(f"{label}: geometry_id ausente")
        if row.get("range", {}).get("full_pmtiles_requests") != 0: errors.append(f"{label}: descarga PMTiles completa")
        if not row.get("range", {}).get("range_requests"): errors.append(f"{label}: no hubo Range")
        if any(status != 206 for status in row.get("range", {}).get("statuses", [])): errors.append(f"{label}: Range no 206")
        if row["scenario"] != "multi_ccaa" and row.get("rendered_features", 0) <= 0: errors.append(f"{label}: filtro no mostró features")
        if row.get("territory_filter_mismatches") != 0: errors.append(f"{label}: se renderizó una feature fuera del filtro territorial")
        if row.get("selected_geometry_id") and row.get("selected_geometry_available") is not True: errors.append(f"{label}: geometry_id seleccionado no se preservó")
        if row.get("selected_geometry_id") and "selected_geometry_at_next_zoom" in row and row.get("selected_geometry_at_next_zoom") is not True: errors.append(f"{label}: geometry_id no se preservó al siguiente zoom")
    return errors

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--smoke", choices=tuple(CASES), action="append"); parser.add_argument("--mobile", action="store_true"); parser.add_argument("--chrome", default="/usr/bin/google-chrome"); parser.add_argument("--output", type=Path, default=ROOT / "prototypes/es4c/territory-pmtiles-smoke.json"); parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        data = json.loads(args.output.read_text(encoding="utf-8")); errors = validate(data["runs"]); print(json.dumps({"valid": not errors, "errors": errors})); return int(bool(errors))
    names = args.smoke or tuple(CASES); rows = [run_case(args.chrome, name, args.mobile) for name in names]; errors = validate(rows); data = {"runs": rows, "valid": not errors, "errors": errors}; args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8"); print(json.dumps({"valid": not errors, "errors": errors, "runs": len(rows), "output": str(args.output)})); return int(bool(errors))
if __name__ == "__main__": raise SystemExit(main())
