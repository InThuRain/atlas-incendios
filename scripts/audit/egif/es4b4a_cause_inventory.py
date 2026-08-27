#!/usr/bin/env python3
"""Inventory source cause fields in normalized national EGIF by annual block.

This is deliberately an inventory, not a national cause ontology. It preserves
the exact values held in ``original_attributes.pif_causa`` and records existing
documented EGIF mappings only as metadata for the same ``idcausa`` field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ingest/egif"))
from gva_1968_1992 import atomic_write_json, sha256_file, utc_now  # type: ignore

INPUT_DIR = ROOT / "data/processed/egif/spain/2026-08-27"
INPUT_MANIFEST = INPUT_DIR / "manifest.json"
EXISTING_MAPPING = ROOT / "config/egif-web.json"
OUTPUT_DIR = ROOT / "data/derived/spain/es4b4a/causes/2026-08-27"
OUTPUT_MANIFEST = OUTPUT_DIR / "manifest.json"
PIPELINE_VERSION = "es-4b4a-egif-cause-inventory-1"
PRIMARY_FIELD = "pif_causa.idcausa"
IGNORED_CAUSE_FIELDS = {"numeroparte", "idpif"}


def parse_period(value: str) -> tuple[int, int]:
    try:
        start, end = map(int, re.split("[:-]", value, maxsplit=1)) if re.search("[:-]", value) else (int(value), int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value}") from exc
    if start > end:
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value}")
    return start, end


def portable(path: Path) -> str:
    try: return str(path.relative_to(ROOT))
    except ValueError: return str(path)


def text(value: Any) -> str | None:
    if value is None: return None
    value = str(value).strip()
    return value or None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Any) -> tuple[int, str]:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise
    return len(payload), hashlib.sha256(payload).hexdigest()


def load_input(path: Path) -> dict[int, dict[str, Any]]:
    return {int(item["year"]): item for item in read_json(path)["blocks"] if item.get("status") == "complete"}


def documented_mapping(value: str | None, mappings: dict[str, str]) -> dict[str, Any]:
    """Only reuse the already documented EGIF ``idcausa`` mapping metadata."""
    canonical = mappings.get(value or "")
    return {
        "mapping_status": "documented" if canonical else "unmapped",
        "canonical_code": canonical,
        "mapping_basis": "config/egif-web.json exact EGIF idcausa mapping and official public dictionary" if canonical else None,
    }


def value_entry(bucket: dict[str, Any], value: str, record: dict[str, Any], *, field: str, mappings: dict[str, str]) -> None:
    entry = bucket.setdefault(value, {
        "source_value": value, "frequency": 0, "provinces": Counter(), "communities": Counter(),
        "example_record_id": record["record_id"],
        **(documented_mapping(value, mappings) if field == PRIMARY_FIELD else {"mapping_status": "unmapped", "canonical_code": None, "mapping_basis": None}),
    })
    entry["frequency"] += 1
    location = record.get("source_declared_location") or {}
    if text(location.get("province_code")): entry["provinces"][text(location.get("province_code"))] += 1
    if text(location.get("community_code")): entry["communities"][text(location.get("community_code"))] += 1


def finalize_values(values: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item in values.values():
        item = dict(item)
        item["provinces"] = dict(sorted(item["provinces"].items()))
        item["communities"] = dict(sorted(item["communities"].items()))
        result.append(item)
    return sorted(result, key=lambda item: item["source_value"])


def inventory_year(path: Path, year: int, mappings: dict[str, str]) -> dict[str, Any]:
    fields: dict[str, dict[str, Any]] = {}
    combinations: Counter[tuple[str, ...]] = Counter()
    total = with_primary = without_primary = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line); total += 1
            raw = record.get("original_attributes") or {}
            cause = raw.get("pif_causa") if isinstance(raw.get("pif_causa"), dict) else {}
            observed = []
            for key, raw_value in sorted(cause.items()):
                if key in IGNORED_CAUSE_FIELDS: continue
                field = f"pif_causa.{key}"; observed.append(field)
                bucket = fields.setdefault(field, {"source_path": field, "records_present": 0, "records_null": 0, "records_blank": 0, "values": {}})
                bucket["records_present"] += 1
                value = text(raw_value)
                if raw_value is None: bucket["records_null"] += 1
                elif value is None: bucket["records_blank"] += 1
                else: value_entry(bucket["values"], value, record, field=field, mappings=mappings)
            combinations[tuple(observed)] += 1
            primary = text(cause.get("idcausa"))
            with_primary += int(primary is not None); without_primary += int(primary is None)
    field_output = []
    for field, bucket in sorted(fields.items()):
        field_output.append({**{key: value for key, value in bucket.items() if key != "values"}, "distinct_source_values": len(bucket["values"]), "values": finalize_values(bucket["values"])})
    return {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "year": year, "records": total, "records_with_primary_cause": with_primary, "records_without_primary_cause": without_primary, "primary_field": PRIMARY_FIELD, "fields": field_output, "field_combinations": [{"fields": list(keys), "frequency": count} for keys, count in sorted(combinations.items())]}


def aggregate(blocks: list[dict[str, Any]], output: Path) -> None:
    global_fields: dict[str, dict[str, Any]] = {}
    schemas: dict[tuple[str, ...], dict[str, Any]] = {}
    by_year = []
    for block in sorted(blocks, key=lambda item: item["year"]):
        payload = read_json(output / block["output_path"])
        by_year.append({key: payload[key] for key in ("year", "records", "records_with_primary_cause", "records_without_primary_cause", "primary_field")})
        signature = tuple(field["source_path"] for field in payload["fields"])
        schemas.setdefault(signature, {"fields": list(signature), "years": []})["years"].append(payload["year"])
        for field in payload["fields"]:
            target = global_fields.setdefault(field["source_path"], {"source_path": field["source_path"], "records_present": 0, "records_null": 0, "records_blank": 0, "values": {}})
            for key in ("records_present", "records_null", "records_blank"): target[key] += field[key]
            for value in field["values"]:
                entry = target["values"].setdefault(value["source_value"], {"source_value": value["source_value"], "frequency": 0, "years": set(), "provinces": Counter(), "communities": Counter(), "example_record_id": value["example_record_id"], "mapping_status": value["mapping_status"], "canonical_code": value["canonical_code"], "mapping_basis": value["mapping_basis"]})
                entry["frequency"] += value["frequency"]; entry["years"].add(payload["year"])
                entry["provinces"].update(value["provinces"]); entry["communities"].update(value["communities"])
    fields = []
    for field, data in sorted(global_fields.items()):
        values = []
        for item in data["values"].values():
            item = dict(item); item["years"] = sorted(item["years"]); item["provinces"] = dict(sorted(item["provinces"].items())); item["communities"] = dict(sorted(item["communities"].items())); values.append(item)
        fields.append({"source_path": field, "records_present": data["records_present"], "records_null": data["records_null"], "records_blank": data["records_blank"], "distinct_source_values": len(values), "values": sorted(values, key=lambda item: item["source_value"])})
    atomic_json(output / "cause_values_by_year.json", {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "years": by_year})
    atomic_json(output / "cause_values_global.json", {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "records": sum(item["records"] for item in by_year), "records_with_primary_cause": sum(item["records_with_primary_cause"] for item in by_year), "records_without_primary_cause": sum(item["records_without_primary_cause"] for item in by_year), "fields": fields})
    atomic_json(output / "cause_schema_periods.json", {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "field_signatures": sorted(schemas.values(), key=lambda item: (item["years"][0], item["fields"]))})


def block_path(output: Path, year: int) -> Path:
    return output / f"cause_values_{year}.json"


def verify(entry: dict[str, Any], output: Path) -> tuple[bool, str]:
    path = output / entry["output_path"]
    if not path.exists() or sha256_file(path) != entry.get("output_sha256"): return False, "output missing or checksum mismatch"
    payload = read_json(path)
    if payload.get("records") != entry.get("records") or payload.get("year") != entry.get("year"): return False, "record/year mismatch"
    return True, "ok"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=INPUT_MANIFEST); parser.add_argument("--existing-mapping", type=Path, default=EXISTING_MAPPING); parser.add_argument("--output", type=Path, default=OUTPUT_DIR); parser.add_argument("--manifest", type=Path, default=OUTPUT_MANIFEST)
    parser.add_argument("--all", action="store_true"); parser.add_argument("--period", action="append", type=parse_period)
    mode = parser.add_mutually_exclusive_group(required=True); mode.add_argument("--resume", action="store_true"); mode.add_argument("--check", action="store_true"); mode.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not args.all and not args.period: parser.error("indica --all o --period")
    args.input_manifest=args.input_manifest.resolve(); args.existing_mapping=args.existing_mapping.resolve(); args.output=args.output.resolve(); args.manifest=args.manifest.resolve(); args.output.mkdir(parents=True, exist_ok=True)
    inputs = load_input(args.input_manifest); years = sorted(inputs) if args.all else sorted({year for start, end in args.period for year in range(start, end + 1)})
    missing = set(years) - set(inputs)
    if missing: raise SystemExit("Años sin input normalizado complete: " + ", ".join(map(str, sorted(missing))))
    existing = read_json(args.existing_mapping)["causes"]["source_code_mapping"]
    manifest = read_json(args.manifest) if args.manifest.exists() else {"schema_version": 1, "pipeline_version": PIPELINE_VERSION, "blocks": []}
    if manifest.get("pipeline_version") != PIPELINE_VERSION: raise SystemExit("El manifest existente pertenece a otro pipeline; usa otra ruta --manifest")
    entries = {item["year"]: item for item in manifest["blocks"]}; input_dir = args.input_manifest.parent

    def persist() -> None:
        manifest["blocks"] = sorted(entries.values(), key=lambda item: item["year"])
        complete = [item for item in manifest["blocks"] if item.get("status") == "complete"]
        manifest.update({"updated_at": utc_now(), "input_manifest": portable(args.input_manifest), "existing_mapping": portable(args.existing_mapping), "existing_mapping_sha256": sha256_file(args.existing_mapping), "mapping_policy": "Only exact pif_causa.idcausa values already documented for EGIF are annotated; all other dimensions/values remain unmapped.", "totals": {"configured_blocks": len(manifest["blocks"]), "complete_blocks": len(complete), "records": sum(item["records"] for item in complete), "with_primary_cause": sum(item["records_with_primary_cause"] for item in complete), "without_primary_cause": sum(item["records_without_primary_cause"] for item in complete), "bytes": sum(item.get("bytes", 0) for item in complete)}})
        atomic_write_json(args.manifest, manifest)

    failures = 0
    for year in years:
        source = inputs[year]; entry = entries.setdefault(year, {"year": year, "status": "pending", "records": source["records"], "input_sha256": source["output_sha256"], "output_path": block_path(args.output, year).name, "errors": []})
        if args.check:
            entry.update({"status": "processing", "errors": []}); persist(); ok, message = verify(entry, args.output); entry.update({"status": "complete" if ok else "failed", "errors": [] if ok else [message]}); persist(); failures += int(not ok); print(f"EGIF {year}: {'comprobado' if ok else 'inválido'}", flush=True); continue
        if entry.get("status") == "complete" and not args.force and verify(entry, args.output)[0]: print(f"EGIF {year}: reutilizado", flush=True); continue
        entry.update({"status": "processing", "errors": []}); persist()
        try:
            input_path = input_dir / f"egif_records_{year}.jsonl"
            if sha256_file(input_path) != source["output_sha256"]: raise RuntimeError("input checksum mismatch")
            payload = inventory_year(input_path, year, existing)
            size, checksum = atomic_json(block_path(args.output, year), payload)
            entry.update({"status": "complete", "records": payload["records"], "records_with_primary_cause": payload["records_with_primary_cause"], "records_without_primary_cause": payload["records_without_primary_cause"], "bytes": size, "output_sha256": checksum, "input_sha256": source["output_sha256"], "output_path": block_path(args.output, year).name, "fields": [item["source_path"] for item in payload["fields"]], "errors": []}); persist(); print(f"EGIF {year}: completo ({payload['records']:,})", flush=True)
        except BaseException as exc:
            entry.update({"status": "failed", "errors": [str(exc) or type(exc).__name__]}); persist(); raise
    persist(); aggregate([item for item in manifest["blocks"] if item.get("status") == "complete"], args.output)
    print(json.dumps({"failures": failures, "totals": manifest["totals"]}, ensure_ascii=False)); return 2 if failures else 0


if __name__ == "__main__": raise SystemExit(main())
