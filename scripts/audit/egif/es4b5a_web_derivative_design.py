#!/usr/bin/env python3
"""Mide diseños web compactos EGIF nacionales sobre muestras acotadas.

ES-4B5A es deliberadamente un laboratorio: lee únicamente los años definidos
en ``SAMPLE_SPECS`` y nunca ofrece una opción ``--all``. No crea el derivado
nacional ni distribuye relaciones o geometrías CCINIF, que siguen bloqueadas
por licencia. Las relaciones territoriales ES-4B3 se unen por ``record_id``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import tracemalloc
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[3]
NORMALIZED = ROOT / "data/processed/egif/spain/2026-08-27"
TERRITORY_RELATIONS = ROOT / "data/derived/spain/es4b3/territory_relations/2026-08-27"
CCINIF_RELATIONS = ROOT / "data/derived/spain/es4b2/ccinif_relations/2026-08-27"
DEFAULT_OUTPUT = ROOT / "data/derived/spain/es4b5a/samples/2026-08-27"
DEFAULT_RESULTS = ROOT / "data/audit/egif/es4b5a_web_derivative_benchmark.json"

SCHEMA_VERSION = "egif-national-web-v1-design"
# Intentional sample-only coverage: old, high-volume, modern and three
# territorial scopes. The source CCAA code is used only to select a sample;
# resulting canonical IDs always come from ES-4B3's mapping audit.
SAMPLE_SPECS: tuple[dict[str, Any], ...] = (
    {"id": "old_national_1974", "year": 1974, "community_code": None, "purpose": "año histórico"},
    {"id": "high_national_1995", "year": 1995, "community_code": None, "purpose": "año de máximo volumen de muestra"},
    {"id": "modern_national_2023", "year": 2023, "community_code": None, "purpose": "año moderno"},
    {"id": "galicia_1995", "year": 1995, "community_code": "3", "purpose": "CCAA de gran volumen"},
    {"id": "valencian_country_1995", "year": 1995, "community_code": "9", "purpose": "control País Valencià"},
    {"id": "small_ccaa_la_rioja_1995", "year": 1995, "community_code": "7", "purpose": "CCAA pequeña"},
)

# This is the proposed public initial payload. Field order is the serialization
# contract for array and columnar variants; no fields are renamed by position.
INITIAL_FIELDS = (
    "record_id",
    "year",
    "autonomous_community_id",
    "province_id",
    "municipality_id",
    "reported_forest_area_ha",
    "is_gif_forest_ge_500_ha",
    "cause_source_code",
    "canonical_cause",
    "cause_mapping_status",
    "coverage_status",
    "identity_status",
    "episode_identity_status",
)

DETAIL_FIELDS = (
    "source_record_id",
    "detection_date",
    "extinction_date",
    "reported_total_area_ha",
    "reported_wooded_area_ha",
    "reported_nonwooded_area_ha",
    "source_municipality_name",
    "source_paraje",
    "form_model",
    "source_database_id",
)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def gzip_bytes(payload: bytes) -> bytes:
    return gzip.compress(payload, compresslevel=9, mtime=0)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def mappings_by_level(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["level"]: item for item in audit["mappings"]}


def resolved_id(mapping: dict[str, Any] | None) -> str | None:
    if not mapping or mapping.get("resolution_status") not in {"resolved", "historical_resolved"}:
        return None
    return mapping.get("territory_id")


def initial_record(record: dict[str, Any], audit: dict[str, Any], *, profile: str = "public") -> dict[str, Any]:
    """Project one normalized EGIF record to the public initial contract.

    ``profile`` is deliberately accepted only for contract tests. Both public
    and development records omit CCINIF IDs here: the relationship is its own
    dataset and must not be accidentally bundled by a public record build.
    """
    if profile not in {"public", "development"}:
        raise ValueError(f"unsupported profile: {profile}")
    if record.get("source_id") != "egif" or record.get("entity_type") != "administrative_record":
        raise ValueError("expected an EGIF administrative record")
    if record.get("geometry") is not None or record.get("geometry_ids") not in ([], None):
        raise ValueError("EGIF fire geometry must remain absent")
    if audit.get("record_id") != record.get("record_id"):
        raise ValueError("territory audit record_id mismatch")
    levels = mappings_by_level(audit)
    temporal = record.get("temporal_validity") or {}
    forest_area = record.get("reported_forest_area_ha")
    return {
        "record_id": record["record_id"],
        "year": record.get("year"),
        "autonomous_community_id": resolved_id(levels.get("autonomous_community")),
        "province_id": resolved_id(levels.get("province")),
        "municipality_id": resolved_id(levels.get("municipality")),
        "reported_forest_area_ha": forest_area,
        # Null means the source did not supply enough forest-area data to
        # evaluate the administrative >=500 ha condition; it is not false.
        "is_gif_forest_ge_500_ha": None if forest_area is None else bool(record.get("is_gif_forest_ge_500_ha")),
        "cause_source_code": record.get("cause_raw"),
        "canonical_cause": None,
        "cause_mapping_status": "unmapped",
        "coverage_status": temporal.get("coverage_status"),
        "identity_status": record.get("identity_status"),
        "episode_identity_status": record.get("episode_identity_status"),
    }


def detail_record(record: dict[str, Any]) -> dict[str, Any]:
    location = record.get("source_declared_location") or {}
    return {
        "source_record_id": record.get("source_record_id"),
        "detection_date": record.get("detection_date"),
        "extinction_date": record.get("extinction_date"),
        "reported_total_area_ha": record.get("reported_total_area_ha"),
        "reported_wooded_area_ha": record.get("reported_wooded_area_ha"),
        "reported_nonwooded_area_ha": record.get("reported_nonwooded_area_ha"),
        "source_municipality_name": location.get("municipality_name"),
        "source_paraje": location.get("paraje"),
        "form_model": record.get("form_model"),
        "source_database_id": record.get("source_database_id"),
    }


def array_payload(rows: list[dict[str, Any]]) -> bytes:
    return canonical_json({"schema_version": SCHEMA_VERSION, "fields": list(INITIAL_FIELDS), "records": [[row[field] for field in INITIAL_FIELDS] for row in rows]})


def jsonl_payload(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def columnar_payload(rows: list[dict[str, Any]]) -> bytes:
    return canonical_json({"schema_version": SCHEMA_VERSION, "fields": list(INITIAL_FIELDS), "columns": {field: [row[field] for row in rows] for field in INITIAL_FIELDS}})


def details_payload(details: dict[str, dict[str, Any]]) -> bytes:
    return canonical_json({"schema_version": SCHEMA_VERSION, "details": details})


def combined_payload(rows: list[dict[str, Any]], details: dict[str, dict[str, Any]]) -> bytes:
    return canonical_json({"schema_version": SCHEMA_VERSION, "records": [{**row, "detail": details[row["record_id"]]} for row in rows]})


def parse_array(payload: bytes) -> dict[str, Any]:
    return json.loads(payload)


def parse_jsonl(payload: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in payload.splitlines() if line]


def parse_columnar(payload: bytes) -> dict[str, Any]:
    return json.loads(payload)


def lookup_from_array(value: dict[str, Any]) -> dict[str, int]:
    fields = value["fields"]
    index = fields.index("record_id")
    return {row[index]: ordinal for ordinal, row in enumerate(value["records"])}


def lookup_from_rows(value: list[dict[str, Any]]) -> dict[str, int]:
    return {row["record_id"]: ordinal for ordinal, row in enumerate(value)}


def lookup_from_columnar(value: dict[str, Any]) -> dict[str, int]:
    return {record_id: ordinal for ordinal, record_id in enumerate(value["columns"]["record_id"])}


def measure(payload: bytes, parser: Callable[[bytes], Any], indexer: Callable[[Any], dict[str, int]]) -> dict[str, Any]:
    tracemalloc.start()
    started = time.perf_counter()
    decoded = parser(payload)
    parse_ms = (time.perf_counter() - started) * 1000
    parse_current, parse_peak = tracemalloc.get_traced_memory()
    lookup_started = time.perf_counter()
    lookup = indexer(decoded)
    lookup_ms = (time.perf_counter() - lookup_started) * 1000
    _, lookup_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "raw_bytes": len(payload),
        "gzip_bytes": len(gzip_bytes(payload)),
        "sha256": sha256(payload),
        "parse_ms_python": round(parse_ms, 3),
        "lookup_build_ms_python": round(lookup_ms, 3),
        "parse_peak_bytes_python": parse_peak,
        "lookup_peak_bytes_python": lookup_peak,
        "lookup_size": len(lookup),
    }


def iter_joined_year(normalized: Path, territory_audit: Path) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    with normalized.open(encoding="utf-8") as record_handle, territory_audit.open(encoding="utf-8") as audit_handle:
        for ordinal, (record_line, audit_line) in enumerate(zip(record_handle, audit_handle), 1):
            record, audit = json.loads(record_line), json.loads(audit_line)
            if record.get("record_id") != audit.get("record_id"):
                raise ValueError(f"record/audit order mismatch at row {ordinal}")
            yield record, audit
        if record_handle.readline() or audit_handle.readline():
            raise ValueError("record and territory audit line counts differ")


def select_sample(spec: dict[str, Any], normalized_dir: Path, territory_dir: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    year = spec["year"]
    normalized = normalized_dir / f"egif_records_{year}.jsonl"
    territory = territory_dir / f"territory_mapping_audit_{year}.jsonl"
    if not normalized.exists() or not territory.exists():
        raise FileNotFoundError(f"missing normalized or territorial input for {year}")
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record, audit in iter_joined_year(normalized, territory):
        source_location = record.get("source_declared_location") or {}
        if spec["community_code"] is not None and source_location.get("community_code") != spec["community_code"]:
            continue
        selected.append((record, audit))
    selected.sort(key=lambda item: item[0]["record_id"])
    rows = [initial_record(record, audit) for record, audit in selected]
    details = {record["record_id"]: detail_record(record) for record, _ in selected}
    if len(rows) != len({row["record_id"] for row in rows}):
        raise ValueError(f"duplicate record ID in {spec['id']}")
    return rows, details


def byte_per_record(value: int, count: int) -> float | None:
    return round(value / count, 3) if count else None


def sample_result(spec: dict[str, Any], rows: list[dict[str, Any]], details: dict[str, dict[str, Any]], output: Path) -> dict[str, Any]:
    payloads = {
        "json_array": (array_payload(rows), parse_array, lookup_from_array, "records.json"),
        "jsonl": (jsonl_payload(rows), parse_jsonl, lookup_from_rows, "records.jsonl"),
        "columnar_json": (columnar_payload(rows), parse_columnar, lookup_from_columnar, "records-columnar.json"),
    }
    result: dict[str, Any] = {
        "sample_id": spec["id"], "purpose": spec["purpose"], "year": spec["year"], "source_community_code_filter": spec["community_code"],
        "record_count": len(rows), "formats": {},
        "territorial_resolution": {
            "autonomous_community_resolved": sum(row["autonomous_community_id"] is not None for row in rows),
            "province_resolved": sum(row["province_id"] is not None for row in rows),
            "municipality_resolved": sum(row["municipality_id"] is not None for row in rows),
        },
    }
    sample_dir = output / spec["id"]
    for name, (payload, parser, indexer, filename) in payloads.items():
        atomic_write(sample_dir / filename, payload)
        metadata = measure(payload, parser, indexer)
        metadata.update({"raw_bytes_per_record": byte_per_record(metadata["raw_bytes"], len(rows)), "gzip_bytes_per_record": byte_per_record(metadata["gzip_bytes"], len(rows))})
        result["formats"][name] = metadata
    detail = details_payload(details)
    combined = combined_payload(rows, details)
    atomic_write(sample_dir / "details-on-selection.json", detail)
    result["details_on_selection"] = {**measure(detail, parse_array, lambda value: value["details"]), "raw_bytes_per_record": byte_per_record(len(detail), len(rows)), "gzip_bytes_per_record": byte_per_record(len(gzip_bytes(detail)), len(rows))}
    result["combined_initial_and_detail"] = {**measure(combined, parse_array, lambda value: {row["record_id"]: ordinal for ordinal, row in enumerate(value["records"])}), "raw_bytes_per_record": byte_per_record(len(combined), len(rows)), "gzip_bytes_per_record": byte_per_record(len(gzip_bytes(combined)), len(rows))}
    return result


def source_total(normalized_dir: Path) -> int:
    manifest = json.loads((normalized_dir / "manifest.json").read_text(encoding="utf-8"))
    return int(manifest["totals"]["records"])


def annual_blocks(normalized_dir: Path) -> list[dict[str, int]]:
    manifest = json.loads((normalized_dir / "manifest.json").read_text(encoding="utf-8"))
    totals = {int(item["year"]): int(item["records"]) for item in manifest["blocks"] if item.get("status") == "complete"}
    ranges = ((1968, 1979), (1980, 1992), (1993, 2002), (2003, 2012), (2013, 2023))
    return [{"start_year": start, "end_year": end, "national_records": sum(totals.get(year, 0) for year in range(start, end + 1))} for start, end in ranges]


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    result_samples = []
    for spec in SAMPLE_SPECS:
        rows, details = select_sample(spec, args.normalized_dir, args.territory_dir)
        result_samples.append(sample_result(spec, rows, details, output))
    # Territorial sample rows overlap the 1995 national row by design. They
    # are useful for partition sizing but must not bias the national estimate.
    national_samples = [item for item in result_samples if item["source_community_code_filter"] is None]
    weighted_rows = sum(item["record_count"] for item in national_samples)
    total = source_total(args.normalized_dir)
    extrapolated_formats = {}
    for format_name in ("json_array", "jsonl", "columnar_json"):
        raw_per_record = sum(item["formats"][format_name]["raw_bytes"] for item in national_samples) / weighted_rows
        gzip_per_record = sum(item["formats"][format_name]["gzip_bytes"] for item in national_samples) / weighted_rows
        peak_per_record = sum(item["formats"][format_name]["parse_peak_bytes_python"] for item in national_samples) / weighted_rows
        extrapolated_formats[format_name] = {
            "raw_bytes": round(raw_per_record * total), "gzip_bytes": round(gzip_per_record * total),
            "raw_mib": round(raw_per_record * total / 1024 / 1024, 2), "gzip_mib": round(gzip_per_record * total / 1024 / 1024, 2),
            "estimated_full_national_parse_heap_python_mib": round(peak_per_record * total / 1024 / 1024, 2),
        }
    result = {
        "schema_version": 1,
        "phase": "ES-4B5A compact EGIF national web derivative design",
        "execution_scope": "sample_only; no national web asset generated",
        "input": {"normalized_records": total, "normalized_manifest": str(args.normalized_dir.relative_to(ROOT)), "territory_relation_audits": str(args.territory_dir.relative_to(ROOT)), "ccinif_relation_status": "blocked_not_included_in_web_record"},
        "initial_contract": {"schema_version": SCHEMA_VERSION, "fields": list(INITIAL_FIELDS), "constants_in_asset_manifest": {"source_id": "egif", "entity_type": "administrative_record", "geometry_availability": "none", "geometry_semantics": "none"}, "ccinif_policy": "No spatial_reference_id, cell geometry or EGIF-to-CCINIF relation is emitted by a public web record; keep a separate optional relationship asset for a future authorized development/public profile."},
        "selection_detail_contract": {"fields": list(DETAIL_FIELDS), "delivery": "separate source×CCAA×temporal-block lookup keyed by record_id", "excludes": ["original_attributes", "raw XML", "CCINIF geometry", "unpublished CCINIF relationship"]},
        "partition_proposal": {"key": "source_id × autonomous_community_id × temporal_block", "temporal_blocks": annual_blocks(args.normalized_dir), "record_assignment": "one canonical/source-declared administrative CCAA only; no replication from CCINIF or future spatial intersections", "catalogues": "territory names and aliases are separate catalogues, not repeated in records"},
        "samples": result_samples,
        "extrapolation_cautious": {"basis": "weighted bytes per record from the three non-overlapping national year samples; actual national distribution, gzip dictionary effects and browser heap will vary", "records": total, "formats": extrapolated_formats},
        "constraints": ["canonical_cause remains null until an official EGIF/MITECO dictionary is available", "CCINIF is publishable=false_pending_permission and is excluded from public web records", "EGIF geometry remains null", "record_id remains egif-record:<NumeroParte>; no order-dependent IDs"],
    }
    atomic_write(args.results, canonical_json(result) + b"\n")
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-dir", type=Path, default=NORMALIZED)
    parser.add_argument("--territory-dir", type=Path, default=TERRITORY_RELATIONS)
    parser.add_argument("--ccinif-dir", type=Path, default=CCINIF_RELATIONS, help="Recorded only to make its non-public exclusion explicit.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.normalized_dir = args.normalized_dir.resolve(); args.territory_dir = args.territory_dir.resolve(); args.output = args.output.resolve(); args.results = args.results.resolve()
    if not args.ccinif_dir.exists():
        raise SystemExit("No se encontró el directorio CCINIF local; no se puede documentar su exclusión bloqueada.")
    result = build(args)
    print(json.dumps({"samples": len(result["samples"]), "records_in_samples": sum(item["record_count"] for item in result["samples"]), "national_records": result["input"]["normalized_records"], "results": str(args.results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
