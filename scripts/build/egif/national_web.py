#!/usr/bin/env python3
"""Build resumable, compact, geometry-free national EGIF web assets.

ES-4B5B1 implements the approved ES-4B5A contract. It intentionally accepts
only the ``development`` profile and only EGIF input: CCINIF, SIGIF, fire
geometry and any national public deployment are out of scope.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import resource
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ingest/egif"))
sys.path.insert(0, str(ROOT / "scripts/audit/egif"))
from gva_1968_1992 import atomic_write_json, sha256_file, utc_now  # type: ignore
from es4b5a_web_derivative_design import (  # type: ignore
    DETAIL_FIELDS,
    INITIAL_FIELDS,
    SCHEMA_VERSION,
    detail_record,
    initial_record,
)

INPUT_DIR = ROOT / "data/processed/egif/spain/2026-08-27"
INPUT_MANIFEST = INPUT_DIR / "manifest.json"
TERRITORY_DIR = ROOT / "data/derived/spain/es4b3/territory_relations/2026-08-27"
TERRITORY_MANIFEST = TERRITORY_DIR / "manifest.json"
DEFAULT_OUTPUT = ROOT / "data/web/spain/egif/2026-08-27"
PIPELINE_VERSION = "es-4b5b1-egif-national-web-builder-1"
TEMPORAL_BLOCKS = ((1968, 1979), (1980, 1992), (1993, 2002), (2003, 2012), (2013, 2023))
ASSET_SCHEMA_VERSION = "egif-national-web-v1"
PROFILE = "development"
FORBIDDEN_WEB_FIELDS = {"geometry", "geometry_ids", "spatial_reference_id", "original_attributes", "source_declared_location"}


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


def temporal_block(year: int) -> tuple[int, int]:
    for start, end in TEMPORAL_BLOCKS:
        if start <= year <= end:
            return start, end
    raise ValueError(f"Año EGIF fuera de bloques aprobados: {year}")


def block_label(start: int, end: int) -> str:
    return f"{start}-{end}"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def gzip_size(value: bytes) -> int:
    return len(gzip.compress(value, compresslevel=9, mtime=0))


def portable(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def relative_to_output(path: Path, output: Path) -> str:
    try:
        return str(path.relative_to(output))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def input_blocks(path: Path) -> dict[int, dict[str, Any]]:
    return {int(item["year"]): item for item in read_json(path)["blocks"] if item.get("status") == "complete"}


def territory_blocks(path: Path) -> dict[int, dict[str, Any]]:
    return {int(item["year"]): item for item in read_json(path)["blocks"] if item.get("status") == "complete"}


def safe_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def asset_id(territory_id: str, start: int, end: int) -> str:
    return f"egif:{territory_id}:{block_label(start, end)}"


def asset_paths(output: Path, territory_id: str, start: int, end: int) -> tuple[Path, Path]:
    relative = Path("assets") / safe_component(territory_id) / block_label(start, end)
    return output / relative / "initial.json", output / relative / "detail.json"


def spool_paths(output: Path, asset: str, year: int) -> tuple[Path, Path]:
    relative = Path(".spool") / safe_component(asset) / str(year)
    return output / relative / "initial.jsonl", output / relative / "detail.jsonl"


def columnar_payload(*, asset: dict[str, Any], fields: tuple[str, ...], rows: list[dict[str, Any]], role: str, initial_record_id_checksum: str | None = None) -> bytes:
    payload: dict[str, Any] = {
        "schema_version": ASSET_SCHEMA_VERSION,
        "source_id": "egif",
        "entity_type": "administrative_record",
        "asset_id": asset["asset_id"],
        "territory_id": asset["territory_id"],
        "from_year": asset["from_year"],
        "to_year": asset["to_year"],
        "role": role,
        "fields": list(fields),
        "null_representation": "JSON null",
        "dictionary_encoding": "none",
        "columns": {field: [row.get(field) for row in rows] for field in fields},
    }
    if initial_record_id_checksum is not None:
        payload["initial_record_id_order_sha256"] = initial_record_id_checksum
        payload["ordinal_alignment"] = "same_sorted_record_id_order_as_initial"
    return canonical_json(payload) + b"\n"


def initial_payload(asset: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[bytes, str]:
    identifiers = [row["record_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{asset['asset_id']}: record_id duplicado")
    if any(not identifier.startswith("egif-record:") for identifier in identifiers):
        raise ValueError(f"{asset['asset_id']}: record_id EGIF inválido")
    return columnar_payload(asset=asset, fields=INITIAL_FIELDS, rows=rows, role="initial"), digest(canonical_json(identifiers))


def detail_payload(asset: dict[str, Any], rows: list[dict[str, Any]], initial_ids_checksum: str) -> bytes:
    return columnar_payload(asset=asset, fields=DETAIL_FIELDS, rows=rows, role="detail_on_selection", initial_record_id_checksum=initial_ids_checksum)


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def write_year_spools(output: Path, year: int, grouped: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for identifier, group in grouped.items():
        rows = sorted(group["initial"], key=lambda row: row["record_id"])
        details_by_id = group["detail"]
        # The spool needs the stable ID to reconnect rows after combining and
        # sorting multiple years. The final lazy asset deliberately omits it:
        # its ordinal is aligned to the initial asset instead.
        details = [{"record_id": row["record_id"], **details_by_id[row["record_id"]]} for row in rows]
        initial_path, detail_path = spool_paths(output, identifier, year)
        initial_data, detail_data = jsonl_bytes(rows), jsonl_bytes(details)
        atomic_bytes(initial_path, initial_data)
        atomic_bytes(detail_path, detail_data)
        result[identifier] = {
            "year": year,
            "record_count": len(rows),
            "initial_spool_path": portable(initial_path), "initial_spool_sha256": digest(initial_data),
            "detail_spool_path": portable(detail_path), "detail_spool_sha256": digest(detail_data),
        }
    return result


def read_spool(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def ensure_asset(entry: dict[str, Any], territory_id: str, start: int, end: int) -> None:
    entry.setdefault("asset_id", asset_id(territory_id, start, end))
    entry.setdefault("source_id", "egif")
    entry.setdefault("territory_id", territory_id)
    entry.setdefault("from_year", start)
    entry.setdefault("to_year", end)
    entry.setdefault("format", "json_columnar")
    entry.setdefault("schema_version", ASSET_SCHEMA_VERSION)
    entry.setdefault("profile", PROFILE)
    entry.setdefault("status", "pending")
    entry.setdefault("year_spools", {})
    entry.setdefault("errors", [])


def validate_asset(entry: dict[str, Any], output: Path) -> tuple[bool, str]:
    if entry.get("status") != "complete":
        return False, "asset not complete"
    initial_path = output / entry.get("initial", {}).get("path", "")
    detail_path = output / entry.get("detail", {}).get("path", "")
    if not initial_path.is_file() or not detail_path.is_file():
        return False, "initial or detail file missing"
    for path, metadata in ((initial_path, entry["initial"]), (detail_path, entry["detail"])):
        if path.stat().st_size != metadata.get("raw_size") or sha256_file(path) != metadata.get("sha256"):
            return False, f"checksum or size mismatch: {path.name}"
        if gzip_size(path.read_bytes()) != metadata.get("gzip_size"):
            return False, f"gzip size mismatch: {path.name}"
    initial, detail = read_json(initial_path), read_json(detail_path)
    if initial.get("fields") != list(INITIAL_FIELDS) or detail.get("fields") != list(DETAIL_FIELDS):
        return False, "unexpected column contract"
    if set(initial.get("columns", {})) & FORBIDDEN_WEB_FIELDS:
        return False, "forbidden EGIF field in initial asset"
    count = entry.get("record_count")
    if any(len(values) != count for values in initial.get("columns", {}).values()):
        return False, "initial column length mismatch"
    if any(len(values) != count for values in detail.get("columns", {}).values()):
        return False, "detail column length mismatch"
    identifiers = initial["columns"].get("record_id", [])
    if len(set(identifiers)) != count or any(not item.startswith("egif-record:") for item in identifiers):
        return False, "record_id contract mismatch"
    if detail.get("initial_record_id_order_sha256") != digest(canonical_json(identifiers)):
        return False, "detail ordinal alignment mismatch"
    gif = initial["columns"].get("is_gif_forest_ge_500_ha", [])
    if any(item not in {True, False, None} for item in gif):
        return False, "invalid GIF tri-state"
    if any(item is not None for item in initial["columns"].get("canonical_cause", [])):
        return False, "canonical cause must remain null while ontology is blocked"
    if any(item != "unmapped" for item in initial["columns"].get("cause_mapping_status", [])):
        return False, "unexpected cause mapping status"
    return True, "ok"


def selected_years(args: argparse.Namespace, available: dict[int, dict[str, Any]]) -> list[int]:
    if args.all:
        return sorted(available)
    years = sorted({year for start, end in args.period for year in range(start, end + 1)})
    missing = set(years) - set(available)
    if missing:
        raise ValueError("Años sin input EGIF normalizado: " + ", ".join(map(str, sorted(missing))))
    requested = set(years)
    partial_blocks = [block_label(start, end) for start, end in TEMPORAL_BLOCKS if requested & set(range(start, end + 1)) and not set(range(start, end + 1)) <= requested]
    if partial_blocks:
        raise ValueError("--period debe cubrir bloques ES-4B5A completos: " + ", ".join(partial_blocks))
    return years


def selected_assets(entries: dict[str, dict[str, Any]], years: list[int], territories: set[str]) -> list[dict[str, Any]]:
    selected = []
    requested_blocks = {temporal_block(year) for year in years}
    for entry in entries.values():
        if (entry["from_year"], entry["to_year"]) not in requested_blocks:
            continue
        if territories and entry["territory_id"] not in territories:
            continue
        selected.append(entry)
    return sorted(selected, key=lambda item: item["asset_id"])


def manifest_template() -> dict[str, Any]:
    return {
        "schema_version": 1, "pipeline_version": PIPELINE_VERSION, "profile": PROFILE,
        "source_ids": ["egif"], "excluded_source_ids": ["ccinif_grid", "gva_sigif"],
        "publication_status": "development_only_no_national_public_profile", "temporal_blocks": [list(item) for item in TEMPORAL_BLOCKS],
        "scan_blocks": [], "assets": [],
    }


def scan_covers_territories(scan: dict[str, Any], territories: set[str]) -> bool:
    if scan.get("all_territories"):
        return True
    return territories.issubset(set(scan.get("territory_scope", [])))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=INPUT_MANIFEST)
    parser.add_argument("--territory-manifest", type=Path, default=TERRITORY_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--period", action="append", type=parse_period, default=[])
    parser.add_argument("--territory", action="append", default=[])
    parser.add_argument("--profile", choices=[PROFILE], default=PROFILE)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.all and not args.period:
        parser.error("indica --all o al menos un --period")
    args.input_manifest = args.input_manifest.resolve(); args.territory_manifest = args.territory_manifest.resolve(); args.output = args.output.resolve()
    args.manifest = (args.manifest or args.output / "manifest.json").resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    input_entries, territory_entries = input_blocks(args.input_manifest), territory_blocks(args.territory_manifest)
    years = selected_years(args, input_entries)
    if set(years) - set(territory_entries):
        raise SystemExit("Faltan auditorías territoriales ES-4B3 para años seleccionados")
    territories = set(args.territory)
    if any(not item.startswith("ES:CCAA:") for item in territories):
        raise SystemExit("--territory acepta solo territory_id de CCAA, por ejemplo ES:CCAA:10")
    manifest = read_json(args.manifest) if args.manifest.exists() else manifest_template()
    if manifest.get("pipeline_version") != PIPELINE_VERSION or manifest.get("profile") != PROFILE:
        raise SystemExit("El manifest existente no pertenece a este builder/profile")
    assets = {item["asset_id"]: item for item in manifest.get("assets", [])}
    scans = {int(item["year"]): item for item in manifest.get("scan_blocks", [])}
    run_started = time.perf_counter()

    def persist() -> None:
        manifest["scan_blocks"] = [scans[year] for year in sorted(scans)]
        manifest["assets"] = [assets[key] for key in sorted(assets)]
        complete = [item for item in manifest["assets"] if item.get("status") == "complete"]
        manifest.update({
            "updated_at": utc_now(), "input_manifest": portable(args.input_manifest), "territory_manifest": portable(args.territory_manifest),
            "selection": {"years": years, "territories": sorted(territories), "all": bool(args.all)},
            "totals": {"configured_assets": len(manifest["assets"]), "complete_assets": len(complete), "records": sum(item.get("record_count", 0) for item in complete), "raw_bytes": sum(item.get("initial", {}).get("raw_size", 0) + item.get("detail", {}).get("raw_size", 0) for item in complete), "gzip_bytes": sum(item.get("initial", {}).get("gzip_size", 0) + item.get("detail", {}).get("gzip_size", 0) for item in complete)},
        })
        atomic_write_json(args.manifest, manifest)

    if args.check:
        failures = 0
        for entry in selected_assets(assets, years, territories):
            ok, message = validate_asset(entry, args.output)
            entry["status"] = "complete" if ok else "failed"; entry["errors"] = [] if ok else [message]
            failures += int(not ok); print(f"{entry['asset_id']}: {'comprobado' if ok else 'inválido'}", flush=True)
        if args.all and not territories and manifest.get("totals", {}).get("records") != sum(input_entries[year]["records"] for year in years):
            failures += 1; print("Reconciliación nacional inválida", flush=True)
        persist(); print(json.dumps({"failures": failures, "totals": manifest["totals"]}, ensure_ascii=False)); return 2 if failures else 0

    # First stage: one checkpoint per input year. Each year is converted once
    # into compact per-asset spools, so Ctrl+C never loses validated year work.
    for year in years:
        source, territory_source = input_entries[year], territory_entries[year]
        scan = scans.setdefault(year, {"year": year, "status": "pending", "input_sha256": source["output_sha256"], "territory_audit_sha256": territory_source["audit_sha256"], "records": source["records"], "spools": {}, "errors": []})
        if args.resume and scan.get("status") == "complete" and scan.get("input_sha256") == source["output_sha256"] and scan.get("territory_audit_sha256") == territory_source["audit_sha256"] and scan_covers_territories(scan, territories):
            print(f"EGIF {year}: spool reutilizado", flush=True); continue
        scan.update({"status": "building", "errors": []}); persist(); scan_started = time.perf_counter()
        input_path = args.input_manifest.parent / f"egif_records_{year}.jsonl"
        audit_path = args.territory_manifest.parent / f"territory_mapping_audit_{year}.jsonl"
        try:
            if sha256_file(input_path) != source["output_sha256"] or sha256_file(audit_path) != territory_source["audit_sha256"]:
                raise RuntimeError("checksum de input o auditoría territorial no coincide")
            grouped: dict[str, dict[str, Any]] = {}
            scanned = kept = 0
            with input_path.open(encoding="utf-8") as input_handle, audit_path.open(encoding="utf-8") as audit_handle:
                for ordinal, (record_line, audit_line) in enumerate(zip(input_handle, audit_handle), 1):
                    record, audit = json.loads(record_line), json.loads(audit_line); scanned += 1
                    if record.get("record_id") != audit.get("record_id"):
                        raise RuntimeError(f"record_id/audit mismatch en {year}:{ordinal}")
                    compact = initial_record(record, audit, profile=PROFILE)
                    territory_id = compact["autonomous_community_id"]
                    if territory_id is None:
                        raise RuntimeError(f"CCAA no resuelta: {record['record_id']}")
                    if territories and territory_id not in territories:
                        continue
                    start, end = temporal_block(year); identifier = asset_id(territory_id, start, end)
                    bucket = grouped.setdefault(identifier, {"territory_id": territory_id, "start": start, "end": end, "initial": [], "detail": {}})
                    bucket["initial"].append(compact); bucket["detail"][compact["record_id"]] = detail_record(record); kept += 1
                if input_handle.readline() or audit_handle.readline():
                    raise RuntimeError(f"número de líneas distinto entre input/audit {year}")
            if scanned != source["records"]:
                raise RuntimeError(f"recuento input {year}: {scanned} != {source['records']}")
            spools = write_year_spools(args.output, year, grouped)
            for identifier, data in spools.items():
                bucket = grouped[identifier]; entry = assets.setdefault(identifier, {})
                ensure_asset(entry, bucket["territory_id"], bucket["start"], bucket["end"])
                entry["year_spools"][str(year)] = data
                entry["input_checksums"] = {str(item_year): input_entries[item_year]["output_sha256"] for item_year in sorted(int(key) for key in entry["year_spools"])}
                entry["territory_audit_checksums"] = {str(item_year): territory_entries[item_year]["audit_sha256"] for item_year in sorted(int(key) for key in entry["year_spools"])}
            previous_scope = set(scan.get("territory_scope", []))
            scan.update({"status": "complete", "records_scanned": scanned, "records_selected": kept, "spools": spools, "territory_scope": sorted(previous_scope | territories), "all_territories": not territories, "builder_seconds": round(time.perf_counter() - scan_started, 3), "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, "errors": []}); persist(); print(f"EGIF {year}: spool completo ({kept:,} seleccionados)", flush=True)
        except BaseException as exc:
            scan.update({"status": "failed", "errors": [str(exc) or type(exc).__name__]}); persist(); raise

    # Second stage: combine the checked annual spools into one compact asset per
    # source × CCAA × approved temporal block. Existing valid assets are kept.
    for entry in selected_assets(assets, years, territories):
        relevant_years = [year for year in years if temporal_block(year) == (entry["from_year"], entry["to_year"])]
        if args.resume and entry.get("status") == "complete" and validate_asset(entry, args.output)[0]:
            print(f"{entry['asset_id']}: reutilizado", flush=True); continue
        entry.update({"status": "building", "errors": []}); persist(); started = time.perf_counter()
        try:
            rows, details = [], []
            for year in sorted(relevant_years):
                spool = entry["year_spools"].get(str(year))
                if spool is None:
                    continue
                initial_spool, detail_spool = ROOT / spool["initial_spool_path"], ROOT / spool["detail_spool_path"]
                if digest(initial_spool.read_bytes()) != spool["initial_spool_sha256"] or digest(detail_spool.read_bytes()) != spool["detail_spool_sha256"]:
                    raise RuntimeError(f"spool checksum mismatch: {entry['asset_id']} {year}")
                rows.extend(read_spool(initial_spool)); details.extend(read_spool(detail_spool))
            rows.sort(key=lambda item: item["record_id"])
            detail_by_id = {row.get("record_id"): row for row in details}
            if len(rows) != len(detail_by_id) or None in detail_by_id:
                raise RuntimeError(f"detail cardinality mismatch: {entry['asset_id']}")
            details = [{field: detail_by_id[row["record_id"]].get(field) for field in DETAIL_FIELDS} for row in rows]
            initial_data, ids_checksum = initial_payload(entry, rows); detail_data = detail_payload(entry, details, ids_checksum)
            initial_path, detail_path = asset_paths(args.output, entry["territory_id"], entry["from_year"], entry["to_year"])
            atomic_bytes(initial_path, initial_data); atomic_bytes(detail_path, detail_data)
            entry.update({
                "status": "complete", "record_count": len(rows), "input_years": relevant_years,
                "initial": {"path": relative_to_output(initial_path, args.output), "raw_size": len(initial_data), "gzip_size": gzip_size(initial_data), "sha256": digest(initial_data), "record_id_order_sha256": ids_checksum},
                "detail": {"path": relative_to_output(detail_path, args.output), "raw_size": len(detail_data), "gzip_size": gzip_size(detail_data), "sha256": digest(detail_data), "ordinal_alignment": "same_sorted_record_id_order_as_initial"},
                "builder_seconds": round(time.perf_counter() - started, 3), "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                "errors": [],
            })
            ok, message = validate_asset(entry, args.output)
            if not ok:
                raise RuntimeError(message)
            persist(); print(f"{entry['asset_id']}: completo ({len(rows):,})", flush=True)
        except BaseException as exc:
            entry.update({"status": "failed", "errors": [str(exc) or type(exc).__name__]}); persist(); raise
    manifest["last_build"] = {"completed_at": utc_now(), "wall_seconds": round(time.perf_counter() - run_started, 3), "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, "selected_years": years, "selected_territories": sorted(territories)}
    persist(); print(json.dumps({"failures": 0, "totals": manifest["totals"], "last_build": manifest["last_build"]}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
