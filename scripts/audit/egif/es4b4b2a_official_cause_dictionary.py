#!/usr/bin/env python3
"""Extract the locally available official EGIF idcausa dictionary without mapping it.

The available IEPNB SPARQL snapshot is an official linked-data dictionary, but
it is not the Access ``CodXXXXX`` table described by MITECO.  This tool keeps
that distinction explicit and reconciles its literal labels with ES-4B4B1.
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
DEFAULT_DOSSIER = ROOT / "data/audit/egif/es4b4b1_cause_codes.json"
DEFAULT_DICTIONARY = ROOT / "data/raw/egif/gva/1968_1992/dictionaries/causes.sparql.json"
DEFAULT_MANIFEST = ROOT / "data/sources/egif_gva_1968_1992_manifest.json"
DEFAULT_OUTPUT = ROOT / "data/reference/egif/idcausa_official_code_table.json"
DEFAULT_REPORT = ROOT / "ES_4B4B2A_EGIF_OFFICIAL_CAUSE_DICTIONARY.md"
TOP_TEN = ("280", "212", "211", "399", "270", "294", "331", "284", "221", "334")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_rows(snapshot: dict[str, Any], source_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for binding in snapshot.get("results", {}).get("bindings", []):
        uri = binding.get("cause", {}).get("value", "")
        code = uri.rsplit("/", 1)[-1]
        label = binding.get("label", {})
        description = binding.get("description", {})
        if not code or not label.get("value"):
            continue
        rows.append({
            "source_code": code,
            "source_label": label["value"],
            "source_description": description.get("value"),
            "language": label.get("xml:lang") or label.get("lang"),
            "language_status": "not_supplied_in_snapshot" if not (label.get("xml:lang") or label.get("lang")) else "source_supplied",
            "source_table": "IEPNB linked-data resource Causa/España; not an identified EGIFWEB CodXXXXX Access table",
            "source_uri": uri,
            "source_version": f"IEPNB SPARQL snapshot retrieved {source_metadata['retrieved_at']}",
            "temporal_validity": "unknown",
            "provenance": {
                "source_url": source_metadata["source_url"],
                "query": source_metadata["query"],
                "raw_path": source_metadata["raw_path"],
                "raw_sha256": source_metadata["sha256"],
                "license": source_metadata["license"],
            },
        })
    by_key = {}
    for row in rows:
        # The source documentation says Cod tables use IdIdioma.  The local
        # linked-data snapshot omits that field, so ``None`` remains part of
        # the key rather than being silently replaced by Spanish.
        key = (row["source_code"], row["language"])
        if key in by_key:
            raise ValueError(f"duplicate official dictionary key: {key}")
        by_key[key] = row
    return sorted(rows, key=lambda row: (int(row["source_code"]) if row["source_code"].isdigit() else row["source_code"], row["language"] or "", row["source_label"]))


def build_reference(dossier: dict[str, Any], rows: list[dict[str, Any]], *, provenance: dict[str, Any]) -> dict[str, Any]:
    by_code: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_code.setdefault(row["source_code"], []).append(row)
    reconciliation = []
    for code in dossier["idcausa_codes"]:
        matching = by_code.get(code["cause_source_code"], [])
        reconciliation.append({
            "source_code": code["cause_source_code"],
            "observed_frequency": code["frequency"],
            "observed_years": code["years"],
            "dictionary_status": "exact_label_found" if matching else "not_found_in_available_partial_dictionary",
            "labels": [{"source_label": item["source_label"], "language": item["language"], "source_uri": item["source_uri"]} for item in matching],
            "multiple_labels": len(matching) > 1,
            "temporal_ambiguity": "unknown; the available dictionary snapshot has no validity dates",
        })
    by_observed = {item["source_code"]: item for item in reconciliation}
    top_ten = [by_observed[code] for code in TOP_TEN if code in by_observed]
    return {
        "schema_version": 1,
        "phase": "ES-4B4B2A",
        "recovery_status": "partial_official_linked_data_dictionary_recovered; EGIFWEB_CodXXXXX_Access_table_not_recovered",
        "scope": "Literal source labels only; no canonical cause mappings are included.",
        "provenance": provenance,
        "official_code_rows": rows,
        "reconciliation": {
            "observed_code_count": len(reconciliation),
            "exact_codes_found": sum(item["dictionary_status"] == "exact_label_found" for item in reconciliation),
            "codes_not_found": sum(item["dictionary_status"] != "exact_label_found" for item in reconciliation),
            "codes_with_multiple_labels": sum(item["multiple_labels"] for item in reconciliation),
            "observed_codes": reconciliation,
            "top_ten_unmapped_from_es4b4b1": top_ten,
        },
        "access_cod_table_search": {
            "status": "not_recovered",
            "checked": [
                "56 local EGIF public XML ZIPs: XML only, no Access table or CodXXXXX relation",
                "local repository and temporary workspace: no .accdb or .mdb EGIF template",
                "official MITECO EGIF landing page and complementary documents available at audit time",
            ],
            "official_documentation": [
                {
                    "title": "Interpretación de la base de datos de incendios forestales EGIFWEB",
                    "url": "https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/estad%C3%ADstica-iiff/Interpretaci%C3%B3n%20BD_Egifweb.pdf",
                    "support": "states that CodXXXXX tables relate numerical codes to texts and must be filtered by IdIdioma",
                },
                {
                    "title": "Parte de Incendio Forestal – Instrucciones de relleno v3.6",
                    "url": "https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/instrucciones_parte_incendio_tcm30-512355.pdf",
                    "support": "documents current cause fields and definitions, but does not publish the numerical idcausa-to-text table",
                },
            ],
        },
        "external_contact_needed": True,
    }


def markdown_cell(value: str | None) -> str:
    return (value or "—").replace("|", "\\|").replace("\n", " ")


def render_report(reference: dict[str, Any]) -> str:
    reconciliation = reference["reconciliation"]
    lines = [
        "# ES-4B4B2A — Recuperación del diccionario oficial de causas EGIF",
        "",
        "## Resultado",
        "",
        "No se ha localizado la tabla Access `CodXXXXX` que relaciona directamente `pif_causa.idcausa` con textos e `IdIdioma`. La documentación oficial confirma que esa tabla existe en la distribución Access, pero los 56 ZIP/XML públicos disponibles contienen únicamente XML de partes.",
        "",
        "Sí se ha extraído una recuperación parcial del snapshot oficial IEPNB/EGIF: 35 códigos numéricos con etiqueta literal. No se presenta como la tabla `CodXXXXX`, no contiene `IdIdioma` y su vigencia temporal es `unknown`.",
        "",
        f"- Códigos EGIF observados en ES-4B4B1: **{reconciliation['observed_code_count']}**.",
        f"- Encontrados exactamente en el diccionario parcial: **{reconciliation['exact_codes_found']}**.",
        f"- Sin etiqueta en el diccionario parcial: **{reconciliation['codes_not_found']}**.",
        f"- Códigos con más de una etiqueta en la extracción: **{reconciliation['codes_with_multiple_labels']}**.",
        "",
        "## Tabla parcial extraída",
        "",
        "| Código | Etiqueta fuente literal | Idioma fuente | Vigencia |",
        "|---:|---|---|---|",
    ]
    for row in reference["official_code_rows"]:
        lines.append(f"| {row['source_code']} | {markdown_cell(row['source_label'])} | {row['language'] or 'no suministrado'} | {row['temporal_validity']} |")
    lines.extend([
        "",
        "## Top 10 unmapped de ES-4B4B1",
        "",
        "| Código | Frecuencia | Resultado de la tabla parcial | Etiqueta literal |",
        "|---:|---:|---|---|",
    ])
    for item in reconciliation["top_ten_unmapped_from_es4b4b1"]:
        labels = "; ".join(label["source_label"] for label in item["labels"]) or "—"
        lines.append(f"| {item['source_code']} | {item['observed_frequency']:,} | {item['dictionary_status']} | {markdown_cell(labels)} |")
    lines.extend([
        "",
        "## Temporalidad",
        "",
        "El snapshot IEPNB no aporta fechas de alta, baja o cambio de texto. Por ello ningún texto recuperado se declara automáticamente válido para todos los formularios 1968–2023.",
        "",
        "## Consulta propuesta a MITECO",
        "",
        "> Asunto: Solicitud de tabla de códigos de causa EGIF (`pif_causa.idcausa`)",
        ">",
        "> Estamos documentando de forma reproducible la serie EGIF 1968–2023. La guía oficial de interpretación indica que las tablas `CodXXXXX` de la base Access relacionan los códigos numéricos con sus textos y que deben filtrarse por `IdIdioma`.",
        ">",
        "> ¿Podrían facilitar o indicar la tabla `CodXXXXX` concreta asociada a `pif_causa.idcausa`, la plantilla Access pública que la contiene y, si existen, versiones históricas/vigencias de los códigos? Necesitamos conservar `id`, `IdIdioma`, texto y fecha o versión aplicable. También agradeceríamos confirmar si la tabla puede reutilizarse y la atribución requerida.",
        "",
        "Destinatario propuesto: `bzn-egif@miteco.es` (o el contacto ADCIF que MITECO indique). No se ha enviado ningún correo.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dossier", type=Path, default=DEFAULT_DOSSIER)
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DICTIONARY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    manifest = read_json(args.manifest)["dictionaries"]["causes"]
    rows = extract_rows(read_json(args.dictionary), manifest)
    provenance = {
        "dossier_path": str(args.dossier.relative_to(ROOT)), "dossier_sha256": sha256(args.dossier),
        "dictionary_path": str(args.dictionary.relative_to(ROOT)), "dictionary_sha256": sha256(args.dictionary),
        "manifest_path": str(args.manifest.relative_to(ROOT)), "manifest_sha256": sha256(args.manifest),
    }
    reference = build_reference(read_json(args.dossier), rows, provenance=provenance)
    data_checksum = atomic_write(args.output, json.dumps(reference, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    report_checksum = atomic_write(args.report, render_report(reference))
    summary = dict(reference["reconciliation"])
    summary["observed_codes"] = "omitted"
    print(json.dumps({"output": str(args.output), "sha256": data_checksum, "report": str(args.report), "report_sha256": report_checksum, "reconciliation": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
