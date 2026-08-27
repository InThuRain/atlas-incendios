#!/usr/bin/env python3
"""Map normalized EGIF administrative codes to ES-2 territories by annual block.

This pipeline never mutates EGIF records. It produces strict, target-bearing
ES-2 ``territory_relation`` rows separately from a one-row-per-record mapping
audit. Source declarations are retained verbatim in the audit; a current INE
mapping is made only from explicit code crosswalks and documented history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ingest/egif"))
from gva_1968_1992 import atomic_write_json, sha256_file, utc_now  # type: ignore

INPUT_DIR = ROOT / "data/processed/egif/spain/2026-08-27"
INPUT_MANIFEST = INPUT_DIR / "manifest.json"
SNAPSHOT = ROOT / "data/territories/spain/territories-2026-01-01.json"
SNAPSHOT_MANIFEST = ROOT / "data/sources/spain_territory_snapshot_manifest.json"
CROSSWALK = ROOT / "config/egif-territory-crosswalk-v1.json"
HISTORICAL = ROOT / "config/egif-historical-municipality-mappings-v1.json"
OUTPUT_DIR = ROOT / "data/derived/spain/es4b3/territory_relations/2026-08-27"
OUTPUT_MANIFEST = OUTPUT_DIR / "manifest.json"
PIPELINE_VERSION = "es-4b3-egif-territory-relations-1"
RESOLUTION_STATUSES = {"resolved", "historical_resolved", "candidate", "unresolved", "invalid_source_value"}
SOURCE_NULLS = {None, "", "0", "00", "000"}


def parse_period(value: str) -> tuple[int, int]:
    try:
        start, end = map(int, re.split("[:-]", value, maxsplit=1)) if re.search("[:-]", value) else (int(value), int(value))
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


def clean(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def numeric_code(value: Any, width: int) -> str | None:
    value = clean(value)
    if value is None or not value.isdigit() or len(value) > width:
        return None
    return value.zfill(width)


def stable_id(record_id: str, level: str, relation_type: str, territory_id: str) -> str:
    digest = hashlib.sha256(f"{record_id}|{level}|{relation_type}|{territory_id}".encode()).hexdigest()[:24]
    return f"territory-relation:egif:{digest}"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_input(path: Path) -> dict[int, dict[str, Any]]:
    return {int(item["year"]): item for item in read_json(path)["blocks"] if item.get("status") == "complete"}


def load_territories(snapshot: Path, manifest: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, str], dict[str, str], str]:
    payload, metadata = read_json(snapshot), read_json(manifest)
    expected = metadata["output"]["sha256"]
    actual = sha256_file(snapshot)
    if expected != actual:
        raise ValueError("territory snapshot checksum mismatch")
    territories = {item["territory_id"]: item for item in payload["territories"]}
    by_ccaa = {item["official_code"]: item["territory_id"] for item in territories.values() if item["territory_type"] in {"autonomous_community", "autonomous_city"}}
    by_province = {item["official_code"]: item["territory_id"] for item in territories.values() if item["territory_type"] == "province"}
    equivalents = {item["province_equivalent_code"]: item["territory_id"] for item in territories.values() if item["territory_type"] == "autonomous_city"}
    by_municipality = {item["official_code"]: item["territory_id"] for item in territories.values() if item["territory_type"] == "municipality"}
    return territories, by_ccaa, {**by_province, **equivalents}, by_municipality, actual


def historical_index(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in payload.get("mappings", []):
        key = (str(item["source_province_code"]), str(item["source_municipality_code"]))
        if key in result:
            raise ValueError(f"duplicate historical municipality mapping {key}")
        if not item.get("territory_id") or not item.get("evidence"):
            raise ValueError(f"historical municipality mapping {key} lacks territory_id/evidence")
        result[key] = item
    return result


def mapping(level: str, source_value: Any, territory_id: str | None, status: str, method: str, *, reason: str | None = None, candidate_ids: list[str] | None = None, qa_status: str = "not_checkable") -> dict[str, Any]:
    if status not in RESOLUTION_STATUSES:
        raise ValueError(f"unsupported resolution status {status}")
    return {
        "level": level, "source_value": clean(source_value), "territory_id": territory_id,
        "resolution_status": status, "mapping_method": method, "reason": reason,
        "candidate_territory_ids": candidate_ids or [], "qa_status": qa_status,
    }


def resolve_record(record: dict[str, Any], *, territories: dict[str, dict[str, Any]], by_ccaa: dict[str, str], by_province: dict[str, str], by_municipality: dict[str, str], crosswalk: dict[str, Any], historical: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    location = record.get("source_declared_location") or {}
    community_raw, province_raw, municipality_raw = (location.get(key) for key in ("community_code", "province_code", "municipality_code"))
    community_key = clean(community_raw)
    source_community = crosswalk["community_code_to_ine_ccaa_code"].get(community_key or "")
    if community_key is None:
        community = mapping("autonomous_community", community_raw, None, "unresolved", "source_value_absent", reason="missing_egif_community_code")
    elif source_community is None or source_community["ine_ccaa_code"] not in by_ccaa:
        community = mapping("autonomous_community", community_raw, None, "invalid_source_value", "egif_community_crosswalk", reason="unknown_egif_community_code")
    else:
        community = mapping("autonomous_community", community_raw, by_ccaa[source_community["ine_ccaa_code"]], "resolved", "egif_community_code_crosswalk")

    province_code = numeric_code(province_raw, 2)
    if clean(province_raw) is None:
        province = mapping("province", province_raw, None, "unresolved", "source_value_absent", reason="missing_egif_province_code")
    elif province_code is None:
        province = mapping("province", province_raw, None, "invalid_source_value", "two_digit_numeric_province_code", reason="non_numeric_or_out_of_range")
    elif province_code not in by_province:
        province = mapping("province", province_raw, None, "invalid_source_value", "ine_snapshot_lookup", reason="unknown_current_province_or_equivalent_code")
    else:
        province_id = by_province[province_code]
        parent = territories[province_id]["parent_id"] if territories[province_id]["territory_type"] == "province" else province_id
        qa = "autonomous_community_match" if community["territory_id"] == parent else "autonomous_community_mismatch" if community["territory_id"] else "not_checkable"
        province = mapping("province", province_raw, province_id, "resolved", "egif_province_code_to_ine", qa_status=qa)

    municipality_code = numeric_code(municipality_raw, 3)
    if clean(municipality_raw) in SOURCE_NULLS:
        municipality = mapping("municipality", municipality_raw, None, "unresolved", "source_no_municipality", reason="source_uses_zero_or_empty_municipality")
    elif municipality_code is None:
        municipality = mapping("municipality", municipality_raw, None, "invalid_source_value", "three_digit_numeric_municipality_code", reason="non_numeric_or_out_of_range")
    elif province_code is None:
        municipality = mapping("municipality", municipality_raw, None, "unresolved", "requires_valid_source_province", reason="province_not_resolved")
    elif (province_code, municipality_code) in historical:
        item = historical[(province_code, municipality_code)]
        municipality = mapping("municipality", municipality_raw, item["territory_id"], "historical_resolved", "documented_historical_mapping", reason=item.get("evidence"))
    else:
        target_code = province_code + municipality_code
        target_id = by_municipality.get(target_code)
        expected_parent = province["territory_id"]
        if target_id and territories[target_id]["parent_id"] == expected_parent:
            municipality = mapping("municipality", municipality_raw, target_id, "resolved", "source_province_plus_municipality_code_to_current_ine")
        elif target_id:
            municipality = mapping("municipality", municipality_raw, None, "candidate", "current_code_parent_conflict", reason="current_municipality_parent_conflicts_with_source_province", candidate_ids=[target_id])
        else:
            name = clean(location.get("municipality_name"))
            candidates = []
            if name and province["territory_id"]:
                normalized = name.casefold()
                candidates = [item["territory_id"] for item in territories.values() if item["territory_type"] == "municipality" and item["parent_id"] == province["territory_id"] and normalized in {item["official_name"].casefold(), *(alias.casefold() for alias in item.get("aliases", []))}]
            municipality = mapping("municipality", municipality_raw, None, "candidate" if candidates else "unresolved", "exact_current_name_candidate" if candidates else "current_ine_code_not_found", reason="source_name_matches_current_catalog_but_is_not_auto_promoted" if candidates else "no_documented_current_or_historical_equivalence", candidate_ids=sorted(candidates))

    conflict = False
    name = clean(location.get("municipality_name"))
    if municipality["territory_id"] and name:
        item = territories[municipality["territory_id"]]
        conflict = name.casefold() not in {item["official_name"].casefold(), *(alias.casefold() for alias in item.get("aliases", []))}
    return {"record_id": record["record_id"], "source_record_id": record.get("source_record_id"), "year": record.get("year"), "source_declared": {"community_code": community_raw, "province_code": province_raw, "municipality_code": municipality_raw, "municipality_name": location.get("municipality_name")}, "mappings": [community, province, municipality], "qa": {"province_community": province["qa_status"], "municipality_code_name_conflict": conflict, "spatial_reference": "not_used_for_mapping"}, "provenance": {"source_id": "egif", "source_record_id": record.get("source_record_id"), "retrieved_at": record["provenance"]["retrieved_at"], "transformations": ["source_declared preserved; code-only ES-2 territorial mapping; no spatial inference"]}}


def strict_relations(audit: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for item in audit["mappings"]:
        if item["resolution_status"] not in {"resolved", "historical_resolved"} or not item["territory_id"]:
            continue
        relation_type = "historical_mapping" if item["resolution_status"] == "historical_resolved" else "canonical_mapping"
        for emitted_type in ("source_declared", relation_type):
            territory_id = item["territory_id"]
            yield {"territory_relation_id": stable_id(audit["record_id"], item["level"], emitted_type, territory_id), "subject_id": audit["record_id"], "territory_id": territory_id, "relation_type": emitted_type, "mapping_status": "confirmed", "qa_status": item["qa_status"], "mapping_method": item["mapping_method"], "source_value": item["source_value"], "provenance": audit["provenance"]}


def atomic_outputs(relation_path: Path, audit_path: Path, records: Iterable[dict[str, Any]], **resolver: Any) -> tuple[int, int, int, str, str, dict[str, dict[str, int]]]:
    """Stream one annual block to both outputs without retaining its records."""
    relation_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    relation_fd, relation_tmp = tempfile.mkstemp(prefix=f".{relation_path.name}.", suffix=".part", dir=relation_path.parent)
    audit_fd, audit_tmp = tempfile.mkstemp(prefix=f".{audit_path.name}.", suffix=".part", dir=audit_path.parent)
    relation_digest, audit_digest, records_count, relation_count = hashlib.sha256(), hashlib.sha256(), 0, 0
    statuses = {level: Counter() for level in ("autonomous_community", "province", "municipality")}
    try:
        with os.fdopen(relation_fd, "wb") as relation_handle, os.fdopen(audit_fd, "wb") as audit_handle:
            for record in records:
                audit = resolve_record(record, **resolver)
                audit_line = (json.dumps(audit, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
                audit_handle.write(audit_line); audit_digest.update(audit_line); records_count += 1
                for item in audit["mappings"]:
                    statuses[item["level"]][item["resolution_status"]] += 1
                for relation in strict_relations(audit):
                    relation_line = (json.dumps(relation, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
                    relation_handle.write(relation_line); relation_digest.update(relation_line); relation_count += 1
            relation_handle.flush(); os.fsync(relation_handle.fileno())
            audit_handle.flush(); os.fsync(audit_handle.fileno())
        os.replace(relation_tmp, relation_path); os.replace(audit_tmp, audit_path)
    except BaseException:
        for path in (relation_tmp, audit_tmp):
            try: os.unlink(path)
            except FileNotFoundError: pass
        raise
    return records_count, relation_count, relation_path.stat().st_size + audit_path.stat().st_size, relation_digest.hexdigest(), audit_digest.hexdigest(), {level: dict(value) for level, value in statuses.items()}


def output_paths(output: Path, year: int) -> tuple[Path, Path]:
    return output / f"record_to_territory_relations_{year}.jsonl", output / f"territory_mapping_audit_{year}.jsonl"


def verify(entry: dict[str, Any], output: Path) -> tuple[bool, str]:
    relations, audit = output_paths(output, entry["year"])
    for path, checksum_key, count_key in ((relations, "relations_sha256", "relation_count"), (audit, "audit_sha256", "records")):
        if not path.exists() or sha256_file(path) != entry.get(checksum_key):
            return False, f"{path.name}: missing or checksum mismatch"
        count = sum(1 for _ in path.open(encoding="utf-8"))
        if count != entry.get(count_key):
            return False, f"{path.name}: count mismatch"
    with audit.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if set(item["resolution_status"] for item in row["mappings"]) - RESOLUTION_STATUSES:
                return False, "invalid mapping status"
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=INPUT_MANIFEST); parser.add_argument("--snapshot", type=Path, default=SNAPSHOT); parser.add_argument("--snapshot-manifest", type=Path, default=SNAPSHOT_MANIFEST)
    parser.add_argument("--crosswalk", type=Path, default=CROSSWALK); parser.add_argument("--historical-mappings", type=Path, default=HISTORICAL); parser.add_argument("--output", type=Path, default=OUTPUT_DIR); parser.add_argument("--manifest", type=Path, default=OUTPUT_MANIFEST)
    parser.add_argument("--all", action="store_true"); parser.add_argument("--period", action="append", type=parse_period)
    mode = parser.add_mutually_exclusive_group(required=True); mode.add_argument("--resume", action="store_true"); mode.add_argument("--check", action="store_true"); mode.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.all and not args.period: parser.error("indica --all o --period")
    args.input_manifest=args.input_manifest.resolve(); args.snapshot=args.snapshot.resolve(); args.snapshot_manifest=args.snapshot_manifest.resolve(); args.crosswalk=args.crosswalk.resolve(); args.historical_mappings=args.historical_mappings.resolve(); args.output=args.output.resolve(); args.manifest=args.manifest.resolve(); args.output.mkdir(parents=True, exist_ok=True)
    inputs = load_input(args.input_manifest); years = sorted(inputs) if args.all else sorted({year for start, end in args.period for year in range(start, end + 1)})
    missing = set(years) - set(inputs)
    if missing: raise SystemExit("Años sin input normalizado complete: " + ", ".join(map(str, sorted(missing))))
    territories, by_ccaa, by_province, by_municipality, snapshot_checksum = load_territories(args.snapshot, args.snapshot_manifest)
    crosswalk, historical_payload = read_json(args.crosswalk), read_json(args.historical_mappings)
    historical = historical_index(historical_payload)
    manifest = read_json(args.manifest) if args.manifest.exists() else {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "blocks": []}
    if manifest.get("pipeline_version") != PIPELINE_VERSION: raise SystemExit("El manifest existente pertenece a otro pipeline; usa otra ruta --manifest")
    entries = {item["year"]: item for item in manifest["blocks"]}
    input_dir = args.input_manifest.parent

    def persist() -> None:
        manifest["blocks"] = sorted(entries.values(), key=lambda item: item["year"])
        complete = [item for item in manifest["blocks"] if item.get("status") == "complete"]
        manifest.update({"updated_at": utc_now(), "input_manifest": portable(args.input_manifest), "territory_snapshot": portable(args.snapshot), "territory_snapshot_sha256": snapshot_checksum, "crosswalk": portable(args.crosswalk), "crosswalk_sha256": sha256_file(args.crosswalk), "historical_mappings": portable(args.historical_mappings), "historical_mappings_sha256": sha256_file(args.historical_mappings), "totals": {"configured_blocks": len(manifest["blocks"]), "complete_blocks": len(complete), "records": sum(item["records"] for item in complete), "relation_count": sum(item.get("relation_count", 0) for item in complete), "bytes": sum(item.get("bytes", 0) for item in complete)}})
        atomic_write_json(args.manifest, manifest)

    failures = 0
    for year in years:
        source = inputs[year]; entry = entries.setdefault(year, {"year": year, "status": "pending", "records": source["records"], "input_sha256": source["output_sha256"], "errors": []})
        if args.check:
            entry.update({"status": "processing", "errors": []}); persist(); ok, message = verify(entry, args.output); entry.update({"status": "complete" if ok else "failed", "errors": [] if ok else [message]}); persist(); failures += int(not ok); print(f"EGIF {year}: {'comprobado' if ok else 'inválido'}", flush=True); continue
        if entry.get("status") == "complete" and not args.force and verify(entry, args.output)[0]: print(f"EGIF {year}: reutilizado", flush=True); continue
        entry.update({"status": "processing", "errors": []}); persist()
        try:
            input_path = input_dir / f"egif_records_{year}.jsonl"
            if sha256_file(input_path) != source["output_sha256"]: raise RuntimeError("input checksum mismatch")
            relation_path, audit_path = output_paths(args.output, year)
            with input_path.open(encoding="utf-8") as handle:
                count, relation_count, size, relation_sha, audit_sha, statuses = atomic_outputs(relation_path, audit_path, (json.loads(line) for line in handle), territories=territories, by_ccaa=by_ccaa, by_province=by_province, by_municipality=by_municipality, crosswalk=crosswalk, historical=historical)
            entry.update({"status": "complete", "records": count, "relation_count": relation_count, "bytes": size, "relations_sha256": relation_sha, "audit_sha256": audit_sha, "input_sha256": source["output_sha256"], "territory_snapshot_sha256": snapshot_checksum, "statuses": statuses, "errors": []}); persist(); print(f"EGIF {year}: completo ({count:,} auditorías, {relation_count:,} relaciones)", flush=True)
        except BaseException as exc:
            entry.update({"status": "failed", "errors": [str(exc) or type(exc).__name__]}); persist(); raise
    persist(); print(json.dumps({"failures": failures, "totals": manifest["totals"]}, ensure_ascii=False)); return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
