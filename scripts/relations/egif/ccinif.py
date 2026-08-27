#!/usr/bin/env python3
"""Relaciona partes EGIF normalizados con celdas CCINIF por igualdad exacta.

La salida es local y no publicable: ``historical_grid_cells`` mantiene la
geometría de referencia entregada por CCINIF y las relaciones se almacenan por
año. Nunca escribe una geometría en el registro EGIF ni infiere perímetros.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/audit/spain"))
from es1_5_ccinif_historical_grid import (  # type: ignore
    RAW_CCINIF,
    inspect_kmz,
    normalize_component,
    pair_key,
)
sys.path.insert(0, str(ROOT / "scripts/ingest/egif"))
from gva_1968_1992 import atomic_write_bytes, atomic_write_json, sha256_file, utc_now  # type: ignore

INPUT_DIR = ROOT / "data/processed/egif/spain/2026-08-27"
INPUT_MANIFEST = INPUT_DIR / "manifest.json"
GRID_MANIFEST = ROOT / "data/sources/ccinif_historical_grid_manifest.json"
OUTPUT_DIR = ROOT / "data/derived/spain/es4b2/ccinif_relations/2026-08-27"
OUTPUT_MANIFEST = OUTPUT_DIR / "manifest.json"
PIPELINE_VERSION = "es-4b2-egif-ccinif-relations-1"


def parse_period(value: str) -> tuple[int, int]:
    try:
        if ":" in value:
            start, end = map(int, value.split(":", 1))
        elif "-" in value:
            start, end = map(int, value.split("-", 1))
        else:
            start = end = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value}") from exc
    if start > end:
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value}")
    return start, end


def portable(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def grid_assets() -> tuple[dict[str, list[dict[str, Any]]], set[str], dict[str, Any]]:
    grid_path = RAW_CCINIF / "CUADRICULAS.kmz"
    try:
        result = inspect_kmz(grid_path, "historical_grid_cell")
    except ModuleNotFoundError as exc:
        if exc.name == "shapely":
            raise SystemExit(
                "Falta Shapely en este intérprete. Instala requirements-dev.txt y ejecuta "
                ".venv/bin/python scripts/relations/egif/ccinif.py ..."
            ) from exc
        raise
    labels = {normalize_component(item["name"]) for item in result["_unkeyed"] if normalize_component(item["name"])}
    return result["_polygons_by_pair"], labels, result


def grid_cell_id(key: str) -> str:
    return "ccinif-grid:" + key.replace(":", "-")


def cells_payload(cells: dict[str, list[dict[str, Any]]], inspection: dict[str, Any]) -> dict[str, Any]:
    grid_manifest = json.loads(GRID_MANIFEST.read_text(encoding="utf-8"))
    raw = grid_manifest["raw_assets"]["CUADRICULAS.kmz"]
    rows = []
    for key in sorted(cells):
        sheet, grid = key.split(":", 1)
        rows.append({
            "spatial_reference_id": grid_cell_id(key),
            "source_id": "ccinif_grid",
            "spatial_semantics": "historical_location_reference",
            "reference_system": "CCINIF historical 10 km reference grid",
            "sheet_id": sheet,
            "grid_id": grid,
            "nominal_resolution_m": 10_000,
            "interpretation_status": "confirmed",
            "geometry_status": "not_fire_geometry",
            "geometry_parts": [part["geometry"].__geo_interface__ for part in cells[key]],
            "provenance": {
                "source_id": "ccinif_grid", "source_record_id": key,
                "source_url": None, "retrieved_at": grid_manifest["generated_at"],
                "snapshot_id": "received_2026-08-26", "checksums": {"kmz_sha256": raw["sha256"]},
                "transformations": ["KML geometry preserved as historical location reference; not a fire perimeter"],
            },
        })
    return {
        "schema_version": 1, "pipeline_version": PIPELINE_VERSION,
        "publishable": False, "license_status": "false_pending_permission",
        "geometry_semantics": "historical_location_reference",
        "geometry_status": "not_fire_geometry", "grid_cells": rows,
        "source_grid_checksum": raw["sha256"], "grid_parts": inspection["keyed_geometry_parts"],
    }


def atomic_jsonl(path: Path, rows: Iterator[dict[str, Any]]) -> tuple[int, int, str, Counter[str]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    digest = hashlib.sha256(); count = 0; states: Counter[str] = Counter()
    try:
        with os.fdopen(fd, "wb") as handle:
            for row in rows:
                line = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
                handle.write(line); digest.update(line); count += 1; states[row["status"]] += 1
            handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise
    return count, path.stat().st_size, digest.hexdigest(), states


def relation_row(record: dict[str, Any], cells: dict[str, list[dict[str, Any]]], canary_labels: set[str]) -> dict[str, Any]:
    location = record.get("source_declared_location") or {}
    sheet, grid = normalize_component(location.get("sheet")), normalize_component(location.get("grid"))
    community = normalize_component(location.get("community_code"))
    key = pair_key(sheet, grid)
    if key and key in cells:
        status, reason, reference = "confirmed", "exact_hoja_cuad_match", grid_cell_id(key)
    elif sheet and grid and community == "12" and grid in canary_labels:
        status, reason, reference = "ambiguous", "canary_grid_label_without_unique_hoja_geometry", None
    elif sheet and grid:
        status, reason, reference = "unusable", "complete_pair_absent_from_keyed_ccinif_grid", None
    elif sheet or grid:
        status, reason, reference = "ambiguous", "partial_hoja_or_cuad_reference", None
    else:
        status, reason, reference = "no_reference", "neither_hoja_nor_cuad", None
    return {
        "record_id": record["record_id"], "source_record_id": record.get("source_record_id"), "year": record.get("year"),
        "spatial_reference_id": reference, "status": status, "reason": reason,
        "source_sheet": sheet, "source_grid": grid, "source_pair": key,
        "geometry_semantics": "historical_location_reference", "fire_geometry": None,
        "provenance": {"source_id": "egif", "source_record_id": record.get("source_record_id"), "retrieved_at": record["provenance"]["retrieved_at"], "transformations": ["exact normalized HOJA+CUAD equality only"]},
    }


def load_input(path: Path) -> dict[int, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {int(item["year"]): item for item in payload["blocks"] if item.get("status") == "complete"}


def output_path(output: Path, year: int) -> Path:
    return output / f"record_to_grid_{year}.jsonl"


def verify(entry: dict[str, Any], output: Path) -> tuple[bool, str]:
    path = output_path(output, entry["year"])
    if not path.exists() or sha256_file(path) != entry.get("output_sha256"):
        return False, "relation output missing or checksum mismatch"
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["status"] not in {"confirmed", "ambiguous", "unusable", "no_reference"} or row.get("fire_geometry") is not None:
                return False, "invalid relation semantics"
            count += 1
    return (count == entry["records"], "ok" if count == entry["records"] else "record count mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=INPUT_MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=OUTPUT_MANIFEST)
    parser.add_argument("--all", action="store_true"); parser.add_argument("--period", action="append", type=parse_period)
    group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--resume", action="store_true"); group.add_argument("--check", action="store_true"); group.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.all and not args.period: parser.error("indica --all o --period")
    args.input_manifest=args.input_manifest.resolve(); args.output=args.output.resolve(); args.manifest=args.manifest.resolve(); args.output.mkdir(parents=True, exist_ok=True)
    input_dir = args.input_manifest.parent
    inputs = load_input(args.input_manifest); years = sorted(inputs) if args.all else sorted({y for a,b in args.period for y in range(a,b+1)})
    missing = set(years)-inputs.keys()
    if missing: raise SystemExit("Años sin input normalizado complete: " + ", ".join(map(str, sorted(missing))))
    cells, canary_labels, inspection = grid_assets()
    cell_path = args.output / "historical_grid_cells.json"
    cell_data = cells_payload(cells, inspection)
    cell_bytes = (json.dumps(cell_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    cell_checksum = hashlib.sha256(cell_bytes).hexdigest()
    if not cell_path.exists() or sha256_file(cell_path) != cell_checksum: atomic_write_bytes(cell_path, cell_bytes)
    manifest = json.loads(args.manifest.read_text()) if args.manifest.exists() else {"schema_version":1,"pipeline_version":PIPELINE_VERSION,"publishable":False,"license_status":"false_pending_permission","blocks":[]}
    if manifest.get("pipeline_version") != PIPELINE_VERSION:
        raise SystemExit("El manifest existente pertenece a otro pipeline; usa otra ruta --manifest")
    entries={item["year"]:item for item in manifest["blocks"]}; failures=0

    def persist() -> None:
        """Persiste cada transición de bloque: Ctrl+C nunca borra progreso válido."""
        manifest["blocks"] = sorted(entries.values(), key=lambda x: x["year"])
        complete = [x for x in manifest["blocks"] if x.get("status") == "complete"]
        manifest.update({
            "updated_at": utc_now(), "input_manifest": portable(args.input_manifest),
            "grid_cells": portable(cell_path), "grid_sha256": cell_checksum,
            "grid_cell_count": len(cells),
            "totals": {"configured_blocks": len(manifest["blocks"]), "complete_blocks": len(complete),
                       "records": sum(x["records"] for x in complete), "bytes": sum(x.get("bytes", 0) for x in complete)},
        })
        atomic_write_json(args.manifest, manifest)

    for year in years:
        source=inputs[year]; entry=entries.setdefault(year,{"year":year,"status":"pending","records":source["records"],"input_sha256":source["output_sha256"],"errors":[]})
        if args.check:
            entry.update({"status":"downloading", "errors":[]}); persist()
            ok,msg=verify(entry,args.output); entry.update({"status":"complete" if ok else "failed","errors":[] if ok else [msg]}); persist()
            failures+=int(not ok); print(f"EGIF {year}: {'comprobado' if ok else 'inválido'}",flush=True); continue
        if entry.get("status")=="complete" and not args.force and verify(entry,args.output)[0]: print(f"EGIF {year}: reutilizado",flush=True); continue
        entry.update({"status":"downloading", "errors":[]}); persist()
        try:
            input_path=input_dir / f"egif_records_{year}.jsonl"
            if sha256_file(input_path)!=source["output_sha256"]: raise RuntimeError("input checksum mismatch")
            def rows():
                with input_path.open(encoding="utf-8") as handle:
                    for line in handle: yield relation_row(json.loads(line),cells,canary_labels)
            count,size,checksum,states=atomic_jsonl(output_path(args.output,year),rows())
            entry.update({"status":"complete","records":count,"bytes":size,"output_sha256":checksum,"input_sha256":source["output_sha256"],"grid_sha256":cell_checksum,"states":dict(states),"errors":[]})
            persist(); print(f"EGIF {year}: completo ({count:,})",flush=True)
        except BaseException as exc:
            entry.update({"status":"failed", "errors":[str(exc) or type(exc).__name__]}); persist()
            raise
    persist(); print(json.dumps({"failures":failures,"totals":manifest["totals"]},ensure_ascii=False)); return 2 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
