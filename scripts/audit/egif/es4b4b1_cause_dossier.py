#!/usr/bin/env python3
"""Build a compact, deterministic dossier from ES-4B4A EGIF cause aggregates.

This script reads only aggregated ES-4B4A outputs and locally saved official
EGIF dictionary material.  It does not re-read national normalized records or
derive new canonical mappings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AGGREGATE = ROOT / "data/derived/spain/es4b4a/causes/2026-08-27"
DEFAULT_DICTIONARY = ROOT / "data/raw/egif/gva/1968_1992/dictionaries/causes.sparql.json"
DEFAULT_OUTPUT = ROOT / "data/audit/egif/es4b4b1_cause_codes.json"
DEFAULT_REPORT = ROOT / "ES_4B4B1_EGIF_CAUSE_CODE_DOSSIER.md"
PRIMARY_FIELD = "pif_causa.idcausa"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> str:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
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
    return hashlib.sha256(payload).hexdigest()


def compact_values(field: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "source_value": item["source_value"],
        "frequency": item["frequency"],
        "first_year": item["years"][0],
        "last_year": item["years"][-1],
        "years": item["years"],
        "example_record_id": item["example_record_id"],
    } for item in field["values"]]


def source_dictionary(path: Path) -> dict[str, dict[str, str]]:
    payload = read_json(path)
    entries = {}
    for binding in payload.get("results", {}).get("bindings", []):
        uri = binding.get("cause", {}).get("value", "")
        code = uri.rsplit("/", 1)[-1]
        if code:
            entries[code] = {
                "label": binding.get("label", {}).get("value"),
                "description": binding.get("description", {}).get("value"),
            }
    return entries


def signatures_by_year(schema_periods: dict[str, Any]) -> tuple[dict[int, str], dict[str, dict[str, Any]]]:
    by_year, signatures = {}, {}
    for index, item in enumerate(schema_periods["field_signatures"], start=1):
        signature_id = f"egif_cause_schema_{index}"
        definition = {"schema_id": signature_id, "years": item["years"], "source_fields": item["fields"]}
        signatures[signature_id] = definition
        by_year.update({year: signature_id for year in item["years"]})
    return by_year, signatures


def source_documentation(code: str, dictionary: dict[str, dict[str, str]]) -> dict[str, Any] | None:
    entry = dictionary.get(code)
    if not entry:
        return None
    return {
        "document": "data/raw/egif/gva/1968_1992/dictionaries/causes.sparql.json",
        "document_type": "snapshot of official public IEPNB/EGIF linked-data cause dictionary",
        "section": f"Causa/España/{code}",
        "source_label_exact": entry["label"],
        "source_description_exact": entry["description"],
        "period_applicability": "The local dictionary snapshot does not version meanings by historical EGIF form; do not generalize it to every year without further documentation.",
    }


def build_dossier(global_values: dict[str, Any], schema_periods: dict[str, Any], dictionary: dict[str, dict[str, str]], *, input_provenance: dict[str, Any]) -> dict[str, Any]:
    fields = {item["source_path"]: item for item in global_values["fields"]}
    primary = fields[PRIMARY_FIELD]
    records = global_values["records"]
    years_to_schema, schema_definitions = signatures_by_year(schema_periods)
    codes = []
    gaps = []
    for item in primary["values"]:
        code = item["source_value"]
        schema_ids = sorted({years_to_schema[year] for year in item["years"]})
        documented = source_documentation(code, dictionary)
        output = {
            "source_path": PRIMARY_FIELD,
            "cause_source_code": code,
            "cause_source_value": code,
            "frequency": item["frequency"],
            "national_percentage": round(item["frequency"] * 100 / records, 8),
            "first_year": item["years"][0],
            "last_year": item["years"][-1],
            "years": item["years"],
            "source_schema_ids": schema_ids,
            "mapping_status": item["mapping_status"],
            "canonical_code": item["canonical_code"],
            "mapping_provenance": item["mapping_basis"],
            "example_record_ids": [item["example_record_id"]],
            "communities": item["communities"],
            "provinces": item["provinces"],
            "documentation": documented,
            "semantic_change_possible": False,
            "semantic_change_note": "No local source versions a code label by period; schema changes alone are not evidence that this code changed meaning.",
            "secondary_context": {
                "available_source_fields_in_code_years": sorted({field for year in item["years"] for field in schema_definitions[years_to_schema[year]]["source_fields"] if field != PRIMARY_FIELD}),
                "association_status": "schema_coavailability_only; ES-4B4A aggregates do not retain record-level idcausa-to-secondary-value combinations",
            },
        }
        codes.append(output)
        if item["mapping_status"] == "unmapped":
            gaps.append({
                "cause_source_code": code,
                "frequency": item["frequency"],
                "years": item["years"],
                "meaning_to_confirm": "literal source-code meaning and, separately, whether a canonical mapping is justified for each affected historical regime",
                "local_label_available": documented is not None,
                "sources_to_locate": ["official EGIF code dictionary versioned by period", "EGIF form manual or codebook for the affected years"],
                "question": f"What did EGIF idcausa={code} mean in the listed years, and did that meaning change between form regimes?",
            })
    secondary = []
    for path, field in sorted(fields.items()):
        if path == PRIMARY_FIELD:
            continue
        secondary.append({
            "source_path": path,
            "field_role": "secondary_source_dimension_not_interpreted",
            "records_present": field["records_present"],
            "records_null": field["records_null"],
            "records_blank": field["records_blank"],
            "distinct_source_values": field.get("distinct_source_values", len(field["values"])),
            "values": compact_values(field),
            "documentation": None,
            "relationship_to_idcausa": "Not computed at record level in ES-4B4A; only schema co-availability is recorded per code.",
        })
    documented_count = sum(1 for item in codes if item["mapping_status"] == "documented")
    documented_frequency = sum(item["frequency"] for item in codes if item["mapping_status"] == "documented")
    return {
        "schema_version": 1,
        "phase": "ES-4B4B1",
        "scope": "EGIF national 1968-2023 source cause-code dossier; no new mappings",
        "input_provenance": input_provenance,
        "semantic_contract": [
            "null is not unknown",
            "unknown is not under investigation",
            "primary cause is not causante",
            "primary cause is not motivation",
            "certainty is not cause",
            "secondary fields are not collapsed into canonical cause categories",
        ],
        "source_schema_regimes": list(schema_definitions.values()),
        "summary": {
            "records": records,
            "primary_cause_present": global_values["records_with_primary_cause"],
            "primary_cause_missing": global_values["records_without_primary_cause"],
            "idcausa_distinct_codes": len(codes),
            "documented_code_count": documented_count,
            "unmapped_code_count": len(codes) - documented_count,
            "documented_frequency": documented_frequency,
            "unmapped_frequency": records - documented_frequency,
            "source_cause_field_count": len(fields),
        },
        "idcausa_codes": codes,
        "secondary_fields": secondary,
        "documentation_gaps": gaps,
    }


def markdown_escape(value: str | None) -> str:
    return (value or "—").replace("|", "\\|").replace("\n", " ")


def render_report(dossier: dict[str, Any]) -> str:
    summary = dossier["summary"]
    lines = [
        "# ES-4B4B1 — Dossier de códigos de causa EGIF",
        "",
        "## Alcance",
        "",
        "Dossier determinista construido exclusivamente desde los agregados de ES-4B4A y documentación local ya conservada. No relee los 646.887 registros normalizados, no crea mappings nuevos y no convierte dimensiones secundarias en una causa canónica.",
        "",
        "## Resumen",
        "",
        f"- Registros: **{summary['records']:,}**.",
        f"- Códigos `pif_causa.idcausa`: **{summary['idcausa_distinct_codes']}**.",
        f"- Códigos `documented`: **{summary['documented_code_count']}**; frecuencia: **{summary['documented_frequency']:,}**.",
        f"- Códigos `unmapped`: **{summary['unmapped_code_count']}**; frecuencia: **{summary['unmapped_frequency']:,}**.",
        "- No hay evidencia documental local de cambio semántico de un mismo código entre regímenes; por ello ningún código queda marcado `semantic_change_possible=true`.",
        "",
        "## Contrato semántico",
        "",
        "- `null` no equivale a desconocida; desconocida no equivale a en investigación.",
        "- Causa primaria, causante, motivación y certidumbre permanecen como dimensiones fuente separadas.",
        "- La coincidencia de un código en más de un esquema no demuestra por sí misma que su significado haya cambiado ni que se mantenga idéntico.",
        "",
        "## Regímenes de campos observados",
        "",
    ]
    for item in dossier["source_schema_regimes"]:
        years = item["years"]
        lines.append(f"- `{item['schema_id']}`: {years[0]}–{years[-1]} ({len(years)} años observados), campos: {', '.join('`' + field + '`' for field in item['source_fields'])}.")
    lines.extend([
        "",
        "## Tabla completa de `idcausa`",
        "",
        "Las listas completas de años, provincias/CCAA, ejemplos y la referencia documental de cada código se conservan en `data/audit/egif/es4b4b1_cause_codes.json`.",
        "",
        "| Código | Etiqueta fuente local | Frecuencia | % nacional | Primero–último | Estado | Canónica actual | Ejemplo |",
        "|---:|---|---:|---:|---|---|---|---|",
    ])
    for item in dossier["idcausa_codes"]:
        label = item["documentation"]["source_label_exact"] if item["documentation"] else None
        lines.append("| {code} | {label} | {frequency:,} | {percentage:.6f}% | {first}–{last} | {status} | {canonical} | `{example}` |".format(
            code=item["cause_source_code"], label=markdown_escape(label), frequency=item["frequency"], percentage=item["national_percentage"], first=item["first_year"], last=item["last_year"], status=item["mapping_status"], canonical=markdown_escape(item["canonical_code"]), example=item["example_record_ids"][0]))
    lines.extend([
        "",
        "## Campos secundarios",
        "",
        "El agregado nacional permite inventariar sus valores, pero no conserva la asociación registro a registro con un código `idcausa`; por tanto, no se presenta una relación causal inferida.",
        "",
        "| Campo | Presente | Valores distintos | Primero–último |",
        "|---|---:|---:|---|",
    ])
    for item in dossier["secondary_fields"]:
        values = item["values"]
        first = min(value["first_year"] for value in values) if values else "—"
        last = max(value["last_year"] for value in values) if values else "—"
        lines.append(f"| `{item['source_path']}` | {item['records_present']:,} | {item['distinct_source_values']} | {first}–{last} |")
    lines.extend([
        "",
        "## Documentación local reutilizada",
        "",
        "- `data/raw/egif/gva/1968_1992/dictionaries/causes.sparql.json`: snapshot del diccionario público enlazado IEPNB/EGIF. Aporta etiqueta literal para 35 de los 87 códigos observados, pero no versiona el significado por formulario o año.",
        "- `config/egif-web.json`: conserva 15 mappings exactos ya documentados para el mismo campo `idcausa`. Este dossier los reproduce como metadatos y no añade ninguno.",
        "- `CV_3_2_EGIF_AUDIT.md` y `ES_4B1_EGIF_NATIONAL_NORMALIZER.md`: documentan la procedencia y la conservación de la causa fuente, no una ontología nacional definitiva.",
        "",
        "## DOCUMENTATION_GAPS",
        "",
        "Cada código siguiente sigue sin mapping canónico. La pregunta común es confirmar su significado literal y su vigencia por régimen; tener una etiqueta contemporánea no autoriza por sí solo una equivalencia canónica histórica.",
        "",
    ])
    for item in dossier["documentation_gaps"]:
        label = next(code["documentation"] for code in dossier["idcausa_codes"] if code["cause_source_code"] == item["cause_source_code"])
        text = label["source_label_exact"] if label else "sin etiqueta local"
        lines.append(f"- `{item['cause_source_code']}` — {item['frequency']:,} registros, {item['years'][0]}–{item['years'][-1]}, {markdown_escape(text)}. Necesitamos: manual/diccionario EGIF versionado para esos años y confirmación de la equivalencia canónica, si procede.")
    return "\n".join(lines) + "\n"


def atomic_text(path: Path, value: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate-dir", type=Path, default=DEFAULT_AGGREGATE)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    aggregate = args.aggregate_dir / "cause_values_global.json"
    schemas = args.aggregate_dir / "cause_schema_periods.json"
    input_provenance = {
        "cause_values_global": str(aggregate.relative_to(ROOT)),
        "cause_values_global_sha256": sha256(aggregate),
        "cause_schema_periods": str(schemas.relative_to(ROOT)),
        "cause_schema_periods_sha256": sha256(schemas),
        "local_dictionary": str(args.dictionary.relative_to(ROOT)),
        "local_dictionary_sha256": sha256(args.dictionary),
    }
    dossier = build_dossier(read_json(aggregate), read_json(schemas), source_dictionary(args.dictionary), input_provenance=input_provenance)
    checksum = atomic_json(args.output, dossier)
    report_checksum = atomic_text(args.report, render_report(dossier))
    print(json.dumps({"output": str(args.output), "sha256": checksum, "report": str(args.report), "report_sha256": report_checksum, "summary": dossier["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
