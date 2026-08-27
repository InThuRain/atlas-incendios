#!/usr/bin/env python3
"""Inventario streaming de paths y cardinalidades del snapshot EGIF nacional.

No normaliza ni modifica XML. El resultado permite distinguir la forma XML
actual del exportador de los cambios de población y de modelo histórico.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/ingest/egif"))
from gva_1968_1992 import iter_records, lexical_type, walk_leaf_paths, atomic_write_json, utc_now  # type: ignore

RAW_MANIFEST = ROOT / "data/raw/egif/spain/full/2026-08-27/manifest.json"
OUTPUT = ROOT / "data/processed/egif/spain/2026-08-27/schema_inventory.json"
PIPELINE_VERSION = "es-4b1-egif-schema-inventory-1"


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


def selected_years(raw: dict[str, Any], periods: list[tuple[int, int]] | None) -> list[int]:
    available = {int(item["year_from"]): item for item in raw["blocks"] if item.get("status") == "complete"}
    if not periods:
        return sorted(available)
    years = {year for start, end in periods for year in range(start, end + 1)}
    missing = sorted(years - available.keys())
    if missing:
        raise RuntimeError("Bloques raw no disponibles: " + ", ".join(map(str, missing)))
    return sorted(years)


def scan(raw_manifest: Path, years: list[int]) -> dict[str, Any]:
    raw = json.loads(raw_manifest.read_text(encoding="utf-8"))
    entries = {int(item["year_from"]): item for item in raw["blocks"]}
    global_paths: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "non_null_records": 0, "years": set(), "lexical_types": Counter(), "examples": [], "max_cardinality_per_record": 0
    })
    by_year: dict[str, Any] = {}
    total = 0
    for year in years:
        path = ROOT / entries[year]["raw_path"]
        counts: Counter[str] = Counter()
        non_null: Counter[str] = Counter()
        types: dict[str, Counter[str]] = defaultdict(Counter)
        records = 0
        for original, _ in iter_records(path):
            records += 1
            per_record: Counter[str] = Counter()
            for field_path, value in walk_leaf_paths(original):
                counts[field_path] += 1
                per_record[field_path] += 1
                if value is None:
                    continue
                non_null[field_path] += 1
                types[field_path][lexical_type(value)] += 1
                item = global_paths[field_path]
                item["non_null_records"] += 1
                item["years"].add(year)
                item["lexical_types"][lexical_type(value)] += 1
                if len(item["examples"]) < 3 and str(value) not in item["examples"]:
                    item["examples"].append(str(value))
            for field_path, cardinality in per_record.items():
                global_paths[field_path]["max_cardinality_per_record"] = max(global_paths[field_path]["max_cardinality_per_record"], cardinality)
        total += records
        by_year[str(year)] = {
            "records": records,
            "paths_present": sorted(non_null),
            "fields": {
                field_path: {"non_null_records": non_null[field_path], "lexical_types": dict(types[field_path]), "max_cardinality_per_record": max(1, counts[field_path] // records) if records else 0}
                for field_path in sorted(counts)
            },
        }
    signature_groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for year, row in by_year.items():
        signature_groups[tuple(row["paths_present"])].append(int(year))
    variants = [
        {"years": values, "path_count": len(signature), "paths": list(signature)}
        for signature, values in sorted(signature_groups.items(), key=lambda item: item[1][0])
    ]
    return {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": utc_now(),
        "input_manifest": str(raw_manifest.relative_to(ROOT)),
        "years": years,
        "record_count": total,
        "xml_shape_note": "The current exporter uses one hierarchical XML representation; variants below describe observed field population, not proof of original paper-form schemas.",
        "fields": {
            field_path: {
                "non_null_records": item["non_null_records"], "years": sorted(item["years"]),
                "lexical_types": dict(sorted(item["lexical_types"].items())), "examples": item["examples"],
                "max_cardinality_per_record": item["max_cardinality_per_record"],
            }
            for field_path, item in sorted(global_paths.items())
        },
        "by_year": by_year,
        "observed_presence_variants": variants,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, default=RAW_MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--period", action="append", type=parse_period)
    args = parser.parse_args(argv)
    raw_manifest = args.input_manifest.resolve()
    raw = json.loads(raw_manifest.read_text(encoding="utf-8"))
    result = scan(raw_manifest, selected_years(raw, args.period))
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(args.output.resolve(), result)
    print(json.dumps({"records": result["record_count"], "years": len(result["years"]), "fields": len(result["fields"]), "variants": len(result["observed_presence_variants"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
