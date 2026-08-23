#!/usr/bin/env python3
"""Audita las referencias espaciales EGIF valencianas de 1968-1992.

La auditoría es deliberadamente alfanumérica. Lee el normalizado preservado por
CV-3.2 y el XSD embebido en los ZIP originales, pero no construye geometrías ni
transforma coordenadas. El resultado reproducible es documentación de cobertura,
estructura y confianza; no un asset cartográfico.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


PIPELINE_VERSION = "cv-3.5-1"
EXPECTED_RECORDS = 9_175
SHEET_PATTERN = re.compile(r"^\d{4}$")
GRID_PATTERN = re.compile(r"^[A-O]\d{2}$")
XSD_NS = "{http://www.w3.org/2001/XMLSchema}"
CLASSIFICATION_STATES = (
    "A_CONFIRMED",
    "B_PROBABLE",
    "C_AMBIGUOUS",
    "D_UNUSABLE",
    "NO_REFERENCE",
)

FORM_PERIODS = (
    (1968, 1971, "historical_form_1", "1968-1971"),
    (1972, 1979, "historical_form_2", "1972-1979"),
    (1980, 1982, "historical_form_3", "1980-1982"),
    (1983, 1988, "historical_form_4", "1983-1988"),
    (1989, 1989, "historical_form_5", "1989"),
    (1990, 1992, "historical_form_6", "1990-1992"),
)

# Los campos se incluyen por su posible relación espacial, no porque todos
# localicen el punto de inicio. ``role`` impide confundir códigos administrativos,
# recursos afectados o contexto del parte con una referencia cartográfica.
FIELD_DEFINITIONS = (
    ("pif_localizacion.idcomunidad", "administrative_origin", "Código de comunidad del parte"),
    ("pif_localizacion.idprovincia", "administrative_origin", "Código de provincia del parte"),
    ("pif_localizacion.idmunicipio", "administrative_origin", "Término municipal de origen cuando está codificado"),
    ("pif_localizacion.idcomarcaisla", "administrative_origin", "Comarca o isla codificada"),
    ("pif_localizacion.identidadmenor", "administrative_origin", "Entidad menor"),
    ("pif_localizacion.paraje", "textual_origin", "Nombre textual del paraje de inicio"),
    ("pif_localizacion.nummunicipiosafectados", "count_not_locator", "Número de municipios afectados"),
    ("pif_localizacion.puntosinicioincendio", "count_not_locator", "Número de puntos de inicio"),
    ("pif_localizacion.huso", "coordinate_component", "Huso UTM"),
    ("pif_localizacion.x", "coordinate_component", "Coordenada X"),
    ("pif_localizacion.y", "coordinate_component", "Coordenada Y"),
    ("pif_localizacion.iddatum", "coordinate_component", "Código de datum"),
    ("pif_localizacion.hoja", "historical_grid_component", "Hoja cartográfica histórica"),
    ("pif_localizacion.cuadricula", "historical_grid_component", "Subcuadrícula histórica"),
    ("pif_localizacion.latitud", "coordinate_component", "Latitud"),
    ("pif_localizacion.longitud", "coordinate_component", "Longitud"),
    ("pif_condiciones.idestacionmeteorologica", "context_not_origin", "Estación meteorológica usada en condiciones"),
    ("pif_deteccion.idvigilantefijo", "context_not_origin", "Código de vigilante fijo detector"),
    ("pif_deteccion.RelIniciadoJuntoAPif.idiniciadojuntoa", "context_not_locator", "Tipo de elemento junto al que se inició"),
    ("pif_deteccion.RelTipoAreaIniciadoPif.idtipoarea", "context_not_locator", "Tipo de área de inicio"),
    ("pif_anexo.RelEspacioProtegidoPif.idespacioprotegido", "affected_resource_not_origin", "Espacio protegido afectado"),
    ("pif_anexo.RelTeselaAfectadaPif.idtesela", "affected_resource_not_origin", "Tesela MFE afectada"),
    ("pif_anexo.RelTeselaAfectadaPif.idteselamfe", "affected_resource_not_origin", "Identificador MFE de tesela afectada"),
    ("pif_incidencias.afectoespacionnatprot", "affected_resource_flag", "Indicador de afección a espacio natural protegido"),
    ("pif_perdidas.RelPerdidaMontePif.idtitularidadmonte", "affected_resource_category", "Titularidad del monte en pérdidas"),
    ("ParteMonte.idpartemonte", "relationship_identifier", "Identificador interno de la relación de monte afectado"),
    ("ParteMonte.idcomunidad", "affected_resource_administration", "Comunidad del monte afectado"),
    ("ParteMonte.idprovincia", "affected_resource_administration", "Provincia del monte afectado"),
    ("ParteMonte.idcomarcaisla", "affected_resource_administration", "Comarca del monte afectado"),
    ("ParteMonte.idmunicipio", "affected_resource_administration", "Municipio del monte afectado"),
    ("ParteMonte.idcatalogomonte", "affected_resource_identifier", "Código de catálogo de monte exportado"),
    ("ParteMonte.iddemanialmonte", "affected_resource_category", "Carácter demanial del monte afectado"),
    ("ParteMonte.idtitularidadmonte", "affected_resource_category", "Titularidad del monte afectado"),
    ("ParteMonte.cup", "affected_resource_identifier", "Código CUP del monte"),
    ("ParteMonte.propietario", "affected_resource_text", "Propietario del monte"),
)

PRIMARY_EVIDENCE = (
    {
        "id": "miteco_egif_portal",
        "title": "Estadística General de Incendios Forestales (EGIF)",
        "authority": "Ministerio para la Transición Ecológica y el Reto Demográfico",
        "url": "https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html",
        "section": "Base de datos nacional de incendios forestales",
        "supports": "EGIF comienza en 1968, se alimenta de partes normalizados y la calidad depende de la cumplimentación y consolidación provincial.",
    },
    {
        "id": "miteco_forest_history_book",
        "title": "La restauracion forestal de Espana: 75 anos de una ilusion",
        "authority": "Ministerio de Agricultura y Pesca, Alimentacion y Medio Ambiente / Sociedad Espanola de Ciencias Forestales",
        "publication_date": "2017",
        "url": "https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/desertificacion-restauracion/libro75anosdeunailusion_b_tcm30-530962.pdf",
        "pages": "347-348 del PDF",
        "section": "Las repoblaciones y los incendios forestales, 3.1 y 3.3",
        "supports": "El sistema inicial asignaba cada incendio a una cuadrícula UTM de 10 x 10 km referida a hojas 1:200.000 del Instituto Geográfico del Ejército; el cambio a hojas 1:250.000 del IGN ocurrió a mediados de los años noventa.",
    },
    {
        "id": "miteco_current_form_instructions",
        "title": "Parte de Incendio Forestal, instrucciones de relleno v3.6",
        "authority": "Comité de Lucha contra Incendios Forestales / MITECO",
        "url": "https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/instrucciones_parte_incendio_tcm30-512355.pdf",
        "page": "10 del PDF",
        "section": "3.1 Localización",
        "supports": "En el modelo actual hoja/cuadrícula y UTM son sistemas distintos; las coordenadas X/Y representan el punto de inicio y datum es obligatorio cuando se rellenan.",
        "limitation": "El modelo actual usa hojas 1:250.000 y no demuestra por sí solo la decodificación histórica 1968-1992.",
    },
    {
        "id": "miteco_database_interpretation",
        "title": "Interpretación de la base de datos de incendios forestales EGIFWEB",
        "authority": "Área de Defensa contra Incendios Forestales / MITECO",
        "url": "https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/estad%C3%ADstica-iiff/Interpretaci%C3%B3n%20BD_Egifweb.pdf",
        "page": "1",
        "supports": "Las tablas PIF representan capítulos del parte; ParteMonte y relaciones pueden ser múltiples y los códigos requieren tablas de diccionario.",
    },
    {
        "id": "boe_fom_2807_2015",
        "title": "Orden FOM/2807/2015, política de difusión pública de información geográfica del IGN",
        "authority": "Boletín Oficial del Estado",
        "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2015-14129",
        "sections": "artículos 2, 4, 5 y 7",
        "supports": "Las cuadrículas cartográficas oficiales digitales del IGN están incluidas; su uso es libre y gratuito con reconocimiento del origen y propiedad según licencia.",
    },
    {
        "id": "ign_data_policy",
        "title": "Política de datos del IGN",
        "authority": "Instituto Geográfico Nacional / CNIG",
        "url": "https://www.ign.es/web/politica-datos",
        "section": "Licencia y reconocimiento",
        "supports": "La licencia de productos IGN y derivados es compatible con CC BY 4.0 y exige reconocimiento; un producto nuevo debe identificarse como obra derivada del producto empleado.",
    },
)


def model_for_year(year: int) -> tuple[str, str]:
    for start, end, model, label in FORM_PERIODS:
        if start <= year <= end:
            return model, label
    raise ValueError(f"Año fuera del alcance CV-3.5: {year}")


def values_at_path(value: Any, path: str) -> list[str]:
    """Devuelve todos los valores hoja de una ruta, atravesando listas."""

    parts = path.split(".")

    def visit(current: Any, index: int) -> Iterable[Any]:
        if isinstance(current, list):
            for child in current:
                yield from visit(child, index)
            return
        if index == len(parts):
            yield current
            return
        if isinstance(current, dict):
            key = parts[index]
            match = next((candidate for candidate in current if candidate.lower() == key.lower()), None)
            if match is not None:
                yield from visit(current[match], index + 1)

    result: list[str] = []
    for item in visit(value, 0):
        if isinstance(item, (dict, list)) or item is None:
            continue
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def xsd_declarations(raw_paths: Iterable[Path]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Extrae tipos del XSD embebido y prueba que los tres ZIP concuerdan."""

    schemas: list[dict[str, Any]] = []
    declarations: dict[str, dict[str, Any]] = {}
    for path in raw_paths:
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if not member.lower().endswith(".xml"):
                    continue
                root = ET.fromstring(archive.read(member))
                schema = next((child for child in root if child.tag == XSD_NS + "schema"), None)
                if schema is None:
                    raise ValueError(f"{path}:{member} no contiene XSD embebido")
                serialized = ET.tostring(schema, encoding="utf-8")
                digest = hashlib.sha256(serialized).hexdigest()
                schemas.append({"raw_path": str(path), "xml_member": member, "xsd_sha256": digest})
                for parent in schema.findall(XSD_NS + "element"):
                    parent_name = parent.attrib.get("name")
                    if not parent_name:
                        continue
                    for child in parent.iter(XSD_NS + "element"):
                        if child is parent or not child.attrib.get("name"):
                            continue
                        child_name = child.attrib["name"]
                        restriction = child.find(".//" + XSD_NS + "restriction")
                        declared_type = child.attrib.get("type")
                        max_length = None
                        if restriction is not None:
                            declared_type = restriction.attrib.get("base", declared_type)
                            length_node = restriction.find(XSD_NS + "maxLength")
                            max_length = length_node.attrib.get("value") if length_node is not None else None
                        key = f"{parent_name}.{child_name}".lower()
                        declarations[key] = {
                            "xsd_declaration_path": f"{parent_name}.{child_name}",
                            "xsd_type": declared_type,
                            "xsd_max_length": int(max_length) if max_length and max_length.isdigit() else None,
                            "min_occurs": int(child.attrib.get("minOccurs", "1")),
                            "max_occurs": child.attrib.get("maxOccurs", "1"),
                        }
    if len({item["xsd_sha256"] for item in schemas}) != 1:
        raise ValueError("Los XSD embebidos en los snapshots provinciales no coinciden")
    return declarations, schemas


def lexical_pattern(values: list[str]) -> str:
    if not values:
        return "not_populated"
    if all(SHEET_PATTERN.fullmatch(item) for item in values):
        return "four_digits"
    if all(GRID_PATTERN.fullmatch(item) for item in values):
        return "letter_A_O_plus_two_digits"
    if all(re.fullmatch(r"\d+", item) for item in values):
        return "unsigned_integer_text"
    if all(re.fullmatch(r"-?\d+(?:\.\d+)?", item) for item in values):
        return "numeric_text"
    return "mixed_or_text"


def numeric_range(values: Iterable[str]) -> dict[str, float] | None:
    numbers: list[float] = []
    for value in values:
        try:
            number = float(value)
        except ValueError:
            return None
        if not math.isfinite(number):
            return None
        numbers.append(number)
    if not numbers:
        return None
    return {"min": min(numbers), "max": max(numbers)}


def confidence_for(sheet: str | None, grid: str | None) -> str:
    """Clasificación conservadora: ninguna pareja se convierte en geometría."""

    if sheet is None and grid is None:
        return "NO_REFERENCE"
    if sheet and grid and SHEET_PATTERN.fullmatch(sheet) and GRID_PATTERN.fullmatch(grid):
        # Semántica/tamaño documentados, pero faltan tabla de decodificación,
        # datum, huso y tratamiento oficial de bordes/intersecciones.
        return "B_PROBABLE"
    if sheet or grid:
        return "C_AMBIGUOUS"
    return "D_UNUSABLE"


def compact_size_estimate(relations: list[tuple[str, str]]) -> dict[str, int]:
    """Estima serialización de relaciones sin producir geometrías."""

    payload = json.dumps(relations, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {"raw_bytes": len(payload), "gzip_bytes": len(gzip.compress(payload, compresslevel=9))}


def audit(
    normalized_path: Path,
    raw_paths: list[Path],
    source_manifest_path: Path,
) -> dict[str, Any]:
    definitions = {path: {"role": role, "interpretation": text} for path, role, text in FIELD_DEFINITIONS}
    field_records = {path: 0 for path in definitions}
    field_informative_records = {path: 0 for path in definitions}
    field_values: dict[str, Counter[str]] = {path: Counter() for path in definitions}
    field_years: dict[str, Counter[int]] = {path: Counter() for path in definitions}
    field_informative_years: dict[str, Counter[int]] = {path: Counter() for path in definitions}
    field_models: dict[str, Counter[str]] = {path: Counter() for path in definitions}
    field_provinces: dict[str, Counter[str]] = {path: Counter() for path in definitions}
    classification = Counter()
    by_year: dict[int, Counter[str]] = defaultdict(Counter)
    by_province: dict[str, Counter[str]] = defaultdict(Counter)
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    combination_counts = Counter()
    sheets = Counter()
    grids = Counter()
    cells = Counter()
    relations: list[tuple[str, str]] = []
    geometry_non_null = 0
    canonical_municipality = 0
    source_municipality_nonzero = 0
    source_municipality_special = Counter()
    records = 0

    with normalized_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            record = json.loads(line)
            records += 1
            if record.get("geometry") is not None:
                geometry_non_null += 1
            year = int(record["year"])
            model, period = model_for_year(year)
            province = record["province"]
            original = record["original_attributes"]
            sheet_values = values_at_path(original, "pif_localizacion.hoja")
            grid_values = values_at_path(original, "pif_localizacion.cuadricula")
            if len(sheet_values) > 1 or len(grid_values) > 1:
                raise ValueError(f"Más de una hoja/cuadrícula en registro {line_number}")
            sheet = sheet_values[0] if sheet_values else None
            grid = grid_values[0] if grid_values else None
            status = confidence_for(sheet, grid)
            classification[status] += 1
            for aggregate in (by_year[year], by_province[province], by_model[period]):
                aggregate[status] += 1
                aggregate["records"] += 1
            combination = "sheet_and_grid" if sheet and grid else "sheet_only" if sheet else "grid_only" if grid else "none"
            combination_counts[combination] += 1
            if sheet:
                sheets[sheet] += 1
            if grid:
                grids[grid] += 1
            if sheet and grid:
                cell_id = f"{sheet}:{grid}"
                cells[cell_id] += 1
                relations.append((record["source_record_id"], cell_id))
            if record.get("municipality"):
                canonical_municipality += 1
            municipality_values = values_at_path(original, "pif_localizacion.idmunicipio")
            if municipality_values:
                code = municipality_values[0]
                if code.isdigit() and int(code) > 0:
                    source_municipality_nonzero += 1
                    if int(code) >= 900:
                        source_municipality_special[code] += 1

            for path in definitions:
                values = values_at_path(original, path)
                if not values:
                    continue
                field_records[path] += 1
                field_values[path].update(values)
                field_years[path][year] += 1
                if any(value != "0" for value in values):
                    field_informative_records[path] += 1
                    field_informative_years[path][year] += 1
                field_models[path][period] += 1
                field_provinces[path][province] += 1

    if records != EXPECTED_RECORDS:
        raise ValueError(f"Se leyeron {records} registros; se esperaban {EXPECTED_RECORDS}")
    if geometry_non_null:
        raise ValueError(f"Se encontraron {geometry_non_null} geometrías EGIF no nulas")

    declarations, schemas = xsd_declarations(raw_paths)
    field_inventory: list[dict[str, Any]] = []
    for path, metadata in definitions.items():
        counts = field_values[path]
        values = sorted(counts)
        xsd = declarations.get(path.lower(), {})
        if not xsd and len(path.split(".")) > 2:
            # Las relaciones anidadas tienen declaración XSD global propia. El
            # XML observado conserva la ruta completa bajo su capítulo PIF.
            xsd = declarations.get(".".join(path.split(".")[-2:]).lower(), {})
        field_inventory.append({
            "xml_path_observed": f"Pif/{path.replace('.', '/')}",
            "normalized_source_path": path,
            **xsd,
            **metadata,
            "records_with_value": field_records[path],
            "records_with_nonzero_value": field_informative_records[path],
            "value_occurrences": sum(counts.values()),
            "zero_value_occurrences": counts.get("0", 0),
            "nonzero_value_occurrences": sum(count for value, count in counts.items() if value != "0"),
            "unique_values": len(counts),
            "examples": [item for item, _ in counts.most_common(8)],
            "lexical_min": min(values) if values else None,
            "lexical_max": max(values) if values else None,
            "numeric_range": numeric_range(values),
            "format_pattern": lexical_pattern(list(counts.elements())),
            "populated_years": sorted(field_years[path]),
            "nonzero_populated_years": sorted(field_informative_years[path]),
            "by_period": dict(sorted(field_models[path].items())),
            "by_province": dict(sorted(field_provinces[path].items())),
        })

    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    relation_size = compact_size_estimate(relations)
    unique_cell_relation_size = compact_size_estimate([(cell, str(count)) for cell, count in sorted(cells.items())])
    result = {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "phase": "CV-3.5",
        "scope": {
            "territory": "Alicante, Castellon and Valencia",
            "years": [1968, 1992],
            "records": records,
            "source_normalized_path": str(normalized_path),
            "source_normalized_sha256": hashlib.sha256(normalized_path.read_bytes()).hexdigest(),
            "source_manifest_path": str(source_manifest_path),
            "source_manifest_pipeline_version": source_manifest.get("pipeline_version"),
            "frontend_modified": False,
            "geometry_created": 0,
        },
        "core_finding": {
            "documented_reference": "Nominal 10 x 10 km UTM grid cell referenced to a 1:200,000 Instituto Geografico del Ejercito sheet",
            "geometry_status": "not_constructed",
            "reason": "No official code-to-bounds table, original datum, UTM zone assignment, axis orientation, sheet origin or boundary/intersection rules were located for the historical identifiers.",
            "future_representation_eligible_records": 0,
            "only_A_CONFIRMED_is_eligible": True,
        },
        "classification_policy": {
            "A_CONFIRMED": "Semantics, code conversion, CRS/datum/zone and reproducible geometry all documented.",
            "B_PROBABLE": "Semantics and nominal resolution documented, but at least one essential conversion element is missing.",
            "C_AMBIGUOUS": "Partial/malformed reference or multiple plausible interpretations.",
            "D_UNUSABLE": "A raw reference exists but cannot support responsible spatial representation.",
            "NO_REFERENCE": "Neither historical sheet nor grid value is present.",
        },
        "classification_totals": {key: classification.get(key, 0) for key in CLASSIFICATION_STATES},
        "reference_coverage": {
            "with_sheet_and_grid": combination_counts["sheet_and_grid"],
            "sheet_only": combination_counts["sheet_only"],
            "grid_only": combination_counts["grid_only"],
            "without_sheet_or_grid": combination_counts["none"],
            "sheet_values": dict(sorted(sheets.items())),
            "unique_sheet_values": len(sheets),
            "unique_grid_values": len(grids),
            "unique_sheet_grid_pairs": len(cells),
            "sheet_grid_pairs": dict(sorted(cells.items())),
            "records_with_source_municipality_code_nonzero": source_municipality_nonzero,
            "records_with_canonical_municipality": canonical_municipality,
            "special_source_municipality_codes": dict(source_municipality_special),
        },
        "by_year": [
            {
                "year": year,
                "records": by_year[year]["records"],
                **{status: by_year[year].get(status, 0) for status in CLASSIFICATION_STATES},
            }
            for year in sorted(by_year)
        ],
        "by_province": [
            {
                "province": province,
                "records": by_province[province]["records"],
                **{status: by_province[province].get(status, 0) for status in CLASSIFICATION_STATES},
            }
            for province in sorted(by_province)
        ],
        "by_documented_period": [
            {
                "period": period,
                "records": by_model[period]["records"],
                **{status: by_model[period].get(status, 0) for status in CLASSIFICATION_STATES},
            }
            for period in sorted(by_model)
        ],
        "field_inventory": field_inventory,
        "xsd_audit": {
            "representation": "one current exporter XSD, not six original historical schemas",
            "snapshots": schemas,
            "unique_xsd_sha256": sorted({item["xsd_sha256"] for item in schemas}),
            "case_note": "Observed XML element case differs from some embedded XSD declaration names; paths are matched case-insensitively and both are reported.",
        },
        "evidence": list(PRIMARY_EVIDENCE),
        "geographic_validation": {
            "performed": False,
            "municipality_or_province_intersection_counts": None,
            "reason": "Mathematical validation would require constructing a cell from an undocumented conversion; municipality was not used to choose or fit an interpretation.",
            "known_case_checks": [
                {"source_record_id": "1992460250", "municipality": "Marines", "sheet_grid": "0704:C11", "result": "raw_reference_preserved_not_geometrically_tested"},
                {"source_record_id": "1992120403", "municipality": "Altura", "sheet_grid": "0804:B01", "result": "raw_reference_preserved_not_geometrically_tested"},
                {"source_record_id": "1992469001", "municipality": None, "sheet_grid": "0804:B01", "result": "raw_reference_preserved_not_geometrically_tested"},
                {"source_record_id": "1990030079", "municipality": "Castell de Castells", "sheet_grid": "0804:N04", "result": "raw_reference_preserved_not_geometrically_tested"},
            ],
        },
        "future_storage_estimate": {
            "recommended_model": "unique_cells_plus_record_to_cell_relations",
            "unique_cells": len(cells),
            "relations": len(relations),
            "rectangle_distinct_vertices_if_confirmed": len(cells) * 4,
            "geojson_coordinate_positions_if_confirmed": len(cells) * 5,
            "compact_relation_json_estimate": relation_size,
            "compact_unique_cell_count_json_estimate": unique_cell_relation_size,
            "geometry_geojson_estimate": {
                "raw_bytes_range": [45_000, 90_000],
                "gzip_bytes_range": [8_000, 25_000],
                "method": "Structural estimate for 270 simple five-position polygons with short identifiers; no coordinates or geometry were generated.",
            },
        },
        "license_audit": {
            "egif": {
                "authority": "Ministerio para la Transición Ecológica y el Reto Demográfico",
                "status": "existing_project_audit_allows_derived_EGIF_with_attribution",
                "attribution": "Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico.",
            },
            "future_grid_definition": {
                "status": "depends_on_source_eventually_used",
                "ign_digital_products": "Order FOM/2807/2015 / license compatible with CC BY 4.0; attribution and derived-work wording required.",
                "historical_ige_sheet_material": "Not covered automatically merely because modern IGN products are open; audit the exact Centro Geografico del Ejercito/Biblioteca Virtual de Defensa item if used.",
                "current_phase": "No cartographic product copied, transformed or redistributed.",
            },
        },
        "legitimate_future_uses_if_A_confirmed": [
            "Display a clearly styled historical documentary reference cell, never a fire perimeter.",
            "Count EGIF reports associated with the same documented cell.",
            "Filter or summarize reports by cell with explicit 10 x 10 km nominal resolution and source caveats.",
        ],
        "prohibited_inferences": [
            "Burned area equal to the cell area.",
            "Exact point location or point containment history.",
            "Exact recurrence or number of times a point burned.",
            "Wildfire perimeter, centroid, buffer or reconstructed geometry.",
            "Choosing a cell interpretation because it best matches a municipality or known fire.",
        ],
        "human_follow_up": [
            "Request from MITECO/ADCIF the historical codebook or GIS layer that maps hoja+cuadricula to cell bounds for the pre-mid-1990s 1:200,000 IGE system.",
            "Request the datum, UTM-zone rules, row/column orientation, sheet origins and treatment of cells at sheet/zone/coast boundaries.",
            "Ask Centro Geografico del Ejercito/IGN whether a digital index of the exact historical 1:200,000 series and its license is available.",
            "Confirm whether blank hoja/cuadricula in 1968-1973 means not collected, not migrated or unknown.",
        ],
    }
    return result


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized", type=Path, default=Path("data/processed/egif/gva/fires_1968_1992.jsonl"))
    parser.add_argument("--source-manifest", type=Path, default=Path("data/sources/egif_gva_1968_1992_manifest.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/egif/gva/1968_1992"))
    parser.add_argument("--output", type=Path, default=Path("data/sources/egif_spatial_reference_audit.json"))
    parser.add_argument("--check", action="store_true", help="Comprueba que la salida existente es idéntica sin reescribirla")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_paths = sorted(args.raw_dir.glob("egif_*_1968_1992.zip"))
    if len(raw_paths) != 3:
        raise SystemExit(f"Se esperaban 3 ZIP provinciales en {args.raw_dir}; encontrados {len(raw_paths)}")
    result = audit(args.normalized, raw_paths, args.source_manifest)
    if args.check:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing != result:
            raise SystemExit("La auditoría versionada no coincide con la regenerada")
        print(f"CV-3.5 OK: {result['scope']['records']} partes; salida reproducible")
        return 0
    atomic_write_json(args.output, result)
    totals = result["classification_totals"]
    print(
        "CV-3.5 generado: "
        f"A={totals['A_CONFIRMED']} B={totals['B_PROBABLE']} "
        f"C={totals['C_AMBIGUOUS']} D={totals['D_UNUSABLE']} "
        f"sin referencia={totals['NO_REFERENCE']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
