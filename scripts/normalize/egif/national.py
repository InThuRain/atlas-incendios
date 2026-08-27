#!/usr/bin/env python3
"""Normaliza snapshots completos EGIF nacionales por año y de forma reanudable.

ES-4B1 conserva el XML original dentro de ``original_attributes`` y produce
solamente registros administrativos: ``geometry`` y ``geometry_ids`` continúan
siendo nulos/vacíos. No crea vínculos CCINIF, municipios canónicos ni episodios
físicos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import sys
import tempfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ingest/egif"))

from gva_1968_1992 import (  # type: ignore  # shared streaming XML decoder
    PipelineError,
    atomic_write_json,
    child_text,
    first_child,
    iter_records,
    nested,
    sha256_file,
    utc_now,
)


RAW_DIR = ROOT / "data/raw/egif/spain/full/2026-08-27"
RAW_MANIFEST = RAW_DIR / "manifest.json"
OUTPUT_DIR = ROOT / "data/processed/egif/spain/2026-08-27"
OUTPUT_MANIFEST = OUTPUT_DIR / "manifest.json"
PIPELINE_VERSION = "es-4b1-egif-national-normalizer-1"
IDENTIFIER_RE = re.compile(r"^\d{10}$")


def text(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    result = str(value).strip()
    return result or None


def integer(value: Any) -> int | None:
    value = text(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def decimal(value: Any) -> Decimal | None:
    value = text(value)
    if value is None:
        return None
    try:
        result = Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def decimal_value(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def period_model(year: int | None) -> str:
    if year is None:
        return "unknown"
    for start, end, name in (
        (1968, 1971, "historical_form_1"),
        (1972, 1979, "historical_form_2"),
        (1980, 1982, "historical_form_3"),
        (1983, 1988, "historical_form_4"),
        (1989, 1989, "historical_form_5"),
        (1990, 1992, "historical_form_6"),
    ):
        if start <= year <= end:
            return name
    return "post_1992_export_schema_not_yet_periodized"


def coverage_status(year: int | None) -> str:
    if year is None:
        return "unknown"
    if year <= 1979:
        return "selective"
    if year <= 1991:
        return "transitional"
    return "systematic"


def raw_location(original: dict[str, Any]) -> dict[str, Any]:
    location = nested(original, "pif_localizacion") or {}
    return {
        "community_code": text(location.get("idcomunidad")),
        "province_code": text(location.get("idprovincia")),
        "municipality_code": text(location.get("idmunicipio")),
        "municipality_name": text(location.get("municipio")),
        "paraje": text(location.get("paraje")) or text(location.get("nombreparaje")),
        "sheet": text(location.get("hoja")),
        "grid": text(location.get("cuadricula")),
        "x": text(location.get("x")),
        "y": text(location.get("y")),
        "zone": text(location.get("huso")),
        "datum_code": text(location.get("iddatum")),
        "latitude": text(location.get("latitud")),
        "longitude": text(location.get("longitud")),
    }


def stable_record_id(
    original: dict[str, Any],
    year: int | None,
    province_code: str | None,
    *,
    force_ambiguous: bool = False,
    record_ordinal: int = 0,
) -> tuple[str, str, str | None]:
    common = nested(original, "pif_comun") or {}
    number = text(original.get("numeroparte")) or text(common.get("numeroparte"))
    database_id = text(original.get("idpif")) or text(common.get("idpif"))
    expected_prefix = f"{year:04d}{province_code.zfill(2)}" if year is not None and province_code else None
    if (
        not force_ambiguous
        and number
        and IDENTIFIER_RE.fullmatch(number)
        and expected_prefix
        and number.startswith(expected_prefix)
    ):
        return f"egif-record:{number}", "source_record_only", number
    fingerprint = json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        "egif-record:sha256:" + hashlib.sha256(
            f"{fingerprint}|ordinal={record_ordinal}".encode("utf-8")
        ).hexdigest()[:24],
        "ambiguous",
        number,
    )


def normalize_record(
    original: dict[str, Any],
    raw_entry: dict[str, Any],
    member: str,
    *,
    duplicate_source_ids: set[str] | None = None,
    record_ordinal: int = 0,
) -> dict[str, Any]:
    common = nested(original, "pif_comun") or {}
    times = nested(original, "pif_tiempos") or {}
    losses = nested(original, "pif_perdidas") or {}
    cause = nested(original, "pif_causa") or {}
    location = raw_location(original)
    year = integer(common.get("anio"))
    if year is None:
        number = text(original.get("numeroparte"))
        if number and number[:4].isdigit():
            year = int(number[:4])
    province_code = location["province_code"]
    original_number = text(original.get("numeroparte")) or text(common.get("numeroparte"))
    record_id, identity_status, source_record_id = stable_record_id(
        original,
        year,
        province_code,
        force_ambiguous=bool(original_number and duplicate_source_ids and original_number in duplicate_source_ids),
        record_ordinal=record_ordinal,
    )
    wooded = decimal(losses.get("superficiearboladatotal"))
    nonwooded = decimal(losses.get("superficienoarboladatotal"))
    forest = wooded + nonwooded if wooded is not None and nonwooded is not None else wooded or nonwooded
    agricultural = decimal(losses.get("superficienoarboladaagricola"))
    other_nonforest = decimal(losses.get("superficienoarboladaotras"))
    parts = [part for part in (forest, agricultural, other_nonforest) if part is not None]
    total_area = sum(parts, Decimal("0")) if parts else None
    cause_value = text(cause.get("idcausa"))
    coordinates = {key: location[key] for key in ("x", "y", "zone", "datum_code", "latitude", "longitude") if location[key] is not None}
    return {
        "record_id": record_id,
        "fire_id": record_id,
        "legacy_ids": [f"egif-record:{source_record_id}"] if identity_status == "ambiguous" and source_record_id else [],
        "source_id": "egif",
        "entity_type": "administrative_record",
        "identity_status": identity_status,
        "source_record_id": source_record_id,
        "source_database_id": text(original.get("idpif")) or text(common.get("idpif")),
        "episode_id": None,
        "episode_identity_status": "unresolved",
        "year": year,
        "detection_date": text(times.get("deteccion")),
        "extinction_date": text(times.get("extinguido")),
        "temporal_validity": {
            "start": text(times.get("deteccion")) or (str(year) if year is not None else None),
            "end": text(times.get("extinguido")) or (str(year) if year is not None else None),
            "coverage_status": coverage_status(year),
            "completeness_status": "unknown",
        },
        "declared_territory_ids": [],
        "source_declared_location": location,
        "municipality_id": None,
        "geometry": None,
        "geometry_ids": [],
        "geometry_id": None,
        "geometry_availability": "none",
        "spatial_reference_id": None,
        "reported_wooded_area_ha": decimal_value(wooded),
        "reported_nonwooded_area_ha": decimal_value(nonwooded),
        "reported_forest_area_ha": decimal_value(forest),
        "reported_agricultural_area_ha": decimal_value(agricultural),
        "reported_other_nonforest_area_ha": decimal_value(other_nonforest),
        "reported_total_area_ha": decimal_value(total_area),
        "is_gif_forest_ge_500_ha": bool(forest is not None and forest >= Decimal("500")),
        "cause_raw": cause_value,
        "cause_code": None,
        "cause_mapping_status": "unmapped",
        "form_model": period_model(year),
        "form_model_assignment_basis": "documented CV-3.2 ranges through 1992; later period not yet subdivided",
        "provenance": {
            "source_id": "egif",
            "source_record_id": source_record_id,
            "source_url": raw_entry["source_urls"]["search"],
            "retrieved_at": raw_entry["retrieved_at"],
            "snapshot_id": raw_entry["block_id"],
            "raw_path": raw_entry["raw_path"],
            "xml_member": member,
            "checksums": {"raw_sha256": raw_entry["sha256"]},
            "transformations": ["streaming XML to normalized JSONL; no geometry, territory or cause inference"],
        },
        "original_attributes": original,
    }


def contract_errors(record: dict[str, Any]) -> list[str]:
    errors = []
    for field in ("record_id", "source_id", "entity_type", "temporal_validity", "geometry_ids", "spatial_reference_id", "provenance"):
        if field not in record:
            errors.append(f"missing {field}")
    if record.get("source_id") != "egif":
        errors.append("source_id must be egif")
    if record.get("entity_type") != "administrative_record":
        errors.append("entity_type must be administrative_record")
    if record.get("geometry") is not None or record.get("geometry_ids") != [] or record.get("geometry_id") is not None:
        errors.append("EGIF must not have fire geometry")
    if record.get("episode_identity_status") != "unresolved":
        errors.append("episode identity must remain unresolved")
    if record.get("spatial_reference_id") is not None:
        errors.append("CCINIF relation is out of scope for ES-4B1")
    if not isinstance(record.get("original_attributes"), dict):
        errors.append("original_attributes must be preserved")
    return errors


def output_path(output: Path, year: int) -> Path:
    return output / f"egif_records_{year}.jsonl"


def write_jsonl_atomic(path: Path, records: Iterator[dict[str, Any]]) -> tuple[int, str, int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    digest = hashlib.sha256()
    count = 0
    seen_record_ids: set[str] = set()
    try:
        with os.fdopen(fd, "wb") as handle:
            for record in records:
                errors = contract_errors(record)
                if errors:
                    raise PipelineError("; ".join(errors))
                if record["record_id"] in seen_record_ids:
                    raise PipelineError(f"record_id repetido dentro del bloque: {record['record_id']}")
                seen_record_ids.add(record["record_id"])
                line = (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                handle.write(line)
                digest.update(line)
                count += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    return count, digest.hexdigest(), path.stat().st_size, rss


def source_record_id_counts(raw_path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for original, _ in iter_records(raw_path):
        common = nested(original, "pif_comun") or {}
        source_id = text(original.get("numeroparte")) or text(common.get("numeroparte"))
        if source_id:
            counts[source_id] += 1
    return counts


def iter_normalized(
    raw_path: Path, raw_entry: dict[str, Any], duplicate_source_ids: set[str]
) -> Iterator[dict[str, Any]]:
    for ordinal, (original, metadata) in enumerate(iter_records(raw_path), start=1):
        yield normalize_record(
            original,
            raw_entry,
            metadata["xml_member"],
            duplicate_source_ids=duplicate_source_ids,
            record_ordinal=ordinal,
        )


def load_raw_manifest(path: Path) -> dict[int, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = {int(item["year_from"]): item for item in payload.get("blocks", [])}
    if not entries or any(item.get("status") != "complete" for item in entries.values()):
        raise PipelineError("El manifiesto raw debe contener bloques complete")
    return entries


def empty_manifest(raw_manifest: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "source": "EGIF/MITECO normalized administrative records",
        "input_manifest": str(raw_manifest.relative_to(ROOT)),
        "geometry_contract": "geometry=null; spatial_reference_id=null; no CCINIF link in ES-4B1",
        "blocks": [],
        "updated_at": utc_now(),
    }


def load_output_manifest(path: Path, raw_manifest: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_manifest(raw_manifest)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("pipeline_version") != PIPELINE_VERSION:
        raise PipelineError("Manifiesto de salida incompatible")
    return payload


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["blocks"] = sorted(manifest["blocks"], key=lambda item: item["year"])
    complete = [item for item in manifest["blocks"] if item.get("status") == "complete"]
    manifest["totals"] = {
        "configured_blocks": len(manifest["blocks"]),
        "complete_blocks": len(complete),
        "records": sum(item.get("records", 0) for item in complete),
        "bytes": sum(item.get("bytes", 0) for item in complete),
    }
    manifest["updated_at"] = utc_now()
    atomic_write_json(path, manifest)


def parse_period(value: str) -> tuple[int, int]:
    value = value.strip()
    sep = ":" if ":" in value else "-" if "-" in value else None
    try:
        start, end = (map(int, value.split(sep, 1)) if sep else (int(value), int(value)))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value}") from exc
    if start > end:
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value}")
    return start, end


def chosen_years(args: argparse.Namespace, raw: dict[int, dict[str, Any]]) -> list[int]:
    if args.all:
        return sorted(raw)
    years = {year for start, end in args.period or [] for year in range(start, end + 1)}
    if not years:
        raise PipelineError("Indica --all o al menos un --period")
    missing = sorted(years - raw.keys())
    if missing:
        raise PipelineError("Años sin bloque raw completo: " + ", ".join(map(str, missing)))
    return sorted(years)


def verify_block(entry: dict[str, Any], output: Path, *, deep: bool) -> tuple[bool, str]:
    path = output_path(output, entry["year"])
    if not path.exists():
        return False, "output absent"
    if sha256_file(path) != entry.get("output_sha256"):
        return False, "output checksum mismatch"
    if not deep:
        return (entry.get("records") == entry.get("expected_records"), "ok")
    count = 0
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if contract_errors(record):
                    return False, "contract validation failure"
                count += 1
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)
    return (count == entry.get("expected_records"), "ok" if count == entry.get("expected_records") else "record count mismatch")


def run(args: argparse.Namespace) -> dict[str, Any]:
    raw = load_raw_manifest(args.input_manifest)
    years = chosen_years(args, raw)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = load_output_manifest(args.manifest, args.input_manifest)
    entries = {item["year"]: item for item in manifest.get("blocks", [])}
    failures = 0
    for year in years:
        input_entry = raw[year]
        input_path = ROOT / input_entry["raw_path"]
        if not input_path.exists() or sha256_file(input_path) != input_entry["sha256"]:
            raise PipelineError(f"{year}: input raw missing or checksum mismatch")
        entry = entries.setdefault(year, {
            "year": year, "status": "pending", "expected_records": input_entry["records_downloaded"],
            "input_raw_path": input_entry["raw_path"], "input_sha256": input_entry["sha256"], "errors": [],
        })
        manifest["blocks"] = list(entries.values())
        write_manifest(args.manifest, manifest)
        if args.check:
            ok, message = verify_block(entry, args.output, deep=True)
            if ok:
                entry["status"] = "complete"; entry["checked_at"] = utc_now(); entry["errors"] = []
                print(f"EGIF {year}: comprobado", flush=True)
            else:
                entry["status"] = "failed"; entry["errors"] = [message]; failures += 1
                print(f"EGIF {year}: inválido — {message}", file=sys.stderr, flush=True)
            write_manifest(args.manifest, manifest)
            continue
        if entry.get("status") == "complete" and not args.force:
            ok, _ = verify_block(entry, args.output, deep=False)
            if ok:
                print(f"EGIF {year}: reutilizado", flush=True)
                continue
        entry.update({"status": "processing", "started_at": utc_now(), "errors": []})
        write_manifest(args.manifest, manifest)
        try:
            source_id_counts = source_record_id_counts(input_path)
            duplicate_source_ids = {key for key, count in source_id_counts.items() if count > 1}
            records, checksum, byte_size, peak_rss = write_jsonl_atomic(
                output_path(args.output, year),
                iter_normalized(input_path, input_entry, duplicate_source_ids),
            )
            if records != entry["expected_records"]:
                raise PipelineError(f"{year}: output={records}, expected={entry['expected_records']}")
            entry.update({"status": "complete", "processed_at": utc_now(), "records": records, "bytes": byte_size, "output_sha256": checksum, "peak_rss_bytes": peak_rss, "duplicate_source_record_id_values": len(duplicate_source_ids), "errors": []})
            print(f"EGIF {year}: completo ({records:,} registros; {byte_size:,} B)", flush=True)
        except KeyboardInterrupt:
            entry.update({"status": "failed", "errors": ["interrupted; retry with --resume"]}); write_manifest(args.manifest, manifest); raise
        except (OSError, PipelineError, ValueError) as exc:
            entry.update({"status": "failed", "errors": [str(exc)]}); failures += 1
            print(f"EGIF {year}: fallo — {exc}", file=sys.stderr, flush=True)
        finally:
            write_manifest(args.manifest, manifest)
    return {"failures": failures, "manifest": manifest, "selected_blocks": len(years)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=RAW_MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=OUTPUT_MANIFEST)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--period", action="append", type=parse_period)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--resume", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.all and not args.period:
        parser.error("indica --all o al menos un --period")
    args.input_manifest = args.input_manifest.resolve(); args.output = args.output.resolve(); args.manifest = args.manifest.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv); result = run(args)
    except KeyboardInterrupt:
        return 130
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    print(json.dumps({"selected_blocks": result["selected_blocks"], "failures": result["failures"], "totals": result["manifest"].get("totals", {})}, ensure_ascii=False))
    return 2 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
