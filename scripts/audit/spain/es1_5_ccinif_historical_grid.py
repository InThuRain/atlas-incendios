#!/usr/bin/env python3
"""Audita la malla histórica EGIF entregada por CCINIF.

El script mantiene separadas tres cosas:

* el parte administrativo EGIF (sin geometría de incendio);
* la celda de referencia histórica ``HOJA`` + ``CUAD``;
* los fragmentos KML que componen la geometría documental de esa celda.

Los KMZ y los XML mínimos nacionales son entradas raw ignoradas por Git. La
salida diagnóstica detallada también se ignora; el manifiesto resumido y
reproducible puede versionarse sin redistribuir las geometrías recibidas.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import html
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
RAW_CCINIF = ROOT / "data/raw/ccinif/historical_grid/received_2026-08-26"
RAW_EGIF = ROOT / "data/raw/egif/spain/location_only/2026-08-26"
LOCAL_EGIF_MANIFEST = RAW_EGIF / "manifest.json"
OUTPUT = ROOT / "data/derived/spain/es1_5/ccinif_grid_audit.json"
MANIFEST = ROOT / "data/sources/ccinif_historical_grid_manifest.json"
IGN_CCAA = Path("/tmp/es1_ign_try_Comunidad_autónoma.json")
IGN_PROVINCES = Path("/tmp/es1_ign_Provincia.json")
ICV_MUNICIPALITIES = (
    ROOT
    / "data/raw/recent/gva/snapshots/20260819T174426Z/boundary/icv_municipalities.geojson"
)

KML_NS = "http://www.opengis.net/kml/2.2"
DESCRIPTION_FIELD = re.compile(r"\s*([^=<]+?)\s*=\s*(.*?)\s*$")

# Diccionario devuelto por el endpoint público de EGIF el 26/08/2026.
# El código de la izquierda es interno de EGIF; el de la derecha es el código
# de comunidad que usa IGN en ``nationalcode``.
EGIF_COMMUNITIES = {
    "1": ("EUSKADI", "16"),
    "2": ("CATALUÑA", "09"),
    "3": ("GALICIA", "12"),
    "4": ("ANDALUCIA", "01"),
    "5": ("ASTURIAS", "03"),
    "6": ("CANTABRIA", "06"),
    "7": ("LA RIOJA", "17"),
    "8": ("MURCIA", "14"),
    "9": ("C. VALENCIANA", "10"),
    "10": ("ARAGON", "02"),
    "11": ("CASTILLA-MANCHA", "08"),
    "12": ("CANARIAS", "05"),
    "13": ("NAVARRA", "15"),
    "14": ("EXTREMADURA", "11"),
    "15": ("ILLES BALEARS", "04"),
    "16": ("MADRID", "13"),
    "17": ("CASTILLA Y LEON", "07"),
    "18": ("CEUTA", "18"),
    "19": ("MELILLA", "19"),
    "99": ("OTRO PAIS", None),
}

CONTROL_RECORDS = {
    "1992460250": {"label": "Marines", "pair": "0704:C11"},
    "1992120403": {"label": "Altura", "pair": "0804:B01"},
    "1992469001": {"label": "Marines–Altura, municipio no identificado", "pair": "0804:B01"},
    "1990030079": {"label": "Castell de Castells", "pair": "0804:N04"},
}


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element | None, name: str) -> str | None:
    if element is None:
        return None
    child = next((item for item in element if local_name(item.tag) == name), None)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def first_child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    return next((item for item in element if local_name(item.tag) == name), None)


def normalize_component(value: str | None) -> str | None:
    """Normalización conservadora: espacios y caja, sin fuzzy/padding."""
    if value is None:
        return None
    result = value.strip().upper()
    return result or None


def pair_key(sheet: str | None, grid: str | None) -> str | None:
    sheet = normalize_component(sheet)
    grid = normalize_component(grid)
    if not sheet or not grid:
        return None
    return f"{sheet}:{grid}"


def parse_description(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    text = html.unescape(value)
    result: dict[str, str] = {}
    for row in re.split(r"<br\s*/?>", text, flags=re.IGNORECASE):
        match = DESCRIPTION_FIELD.match(row)
        if match:
            result[match.group(1).strip()] = match.group(2).strip()
    return result


def parse_coordinates(value: str | None) -> list[tuple[float, float]]:
    coordinates = []
    for token in (value or "").split():
        parts = token.split(",")
        if len(parts) >= 2:
            coordinates.append((float(parts[0]), float(parts[1])))
    return coordinates


def polygon_from_kml(element: ET.Element):
    from shapely.geometry import Polygon

    outer = element.find(
        f"{{{KML_NS}}}outerBoundaryIs/{{{KML_NS}}}LinearRing/{{{KML_NS}}}coordinates"
    )
    inners = element.findall(
        f"{{{KML_NS}}}innerBoundaryIs/{{{KML_NS}}}LinearRing/{{{KML_NS}}}coordinates"
    )
    exterior = parse_coordinates(outer.text if outer is not None else None)
    holes = [parse_coordinates(item.text) for item in inners]
    return Polygon(exterior, holes)


def folder_path(placemark: ET.Element, parents: dict[ET.Element, ET.Element]) -> str:
    names = []
    current = parents.get(placemark)
    while current is not None:
        if local_name(current.tag) in {"Folder", "Document"}:
            name = current.find(f"{{{KML_NS}}}name")
            if name is not None and name.text:
                names.append(name.text.strip())
        current = parents.get(current)
    return "/".join(reversed(names))


def inspect_kmz(path: Path, kind: str) -> dict[str, Any]:
    from shapely.validation import explain_validity

    with zipfile.ZipFile(path) as archive:
        members = [
            {
                "name": info.filename,
                "size_bytes": info.file_size,
                "compressed_size_bytes": info.compress_size,
                "crc32": f"{info.CRC:08x}",
            }
            for info in archive.infolist()
        ]
        bad_member = archive.testzip()
        kml_names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
        if len(kml_names) != 1 or bad_member:
            raise RuntimeError(f"KMZ inválido {path}: kml={kml_names}, bad={bad_member}")
        root = ET.fromstring(archive.read(kml_names[0]))

    parents = {child: parent for parent in root.iter() for child in parent}
    placemarks = root.findall(f".//{{{KML_NS}}}Placemark")
    folder_counts = Counter()
    geometry_counts = Counter()
    field_coverage = Counter()
    unique_fields: dict[str, set[str]] = defaultdict(set)
    polygons = []
    points = 0
    empty_placemarks = 0
    invalid = Counter()
    vertices = 0
    holes = 0
    bounds = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    for placemark in placemarks:
        path_name = folder_path(placemark, parents)
        folder_counts[path_name] += 1
        polygon_elements = placemark.findall(f".//{{{KML_NS}}}Polygon")
        point_elements = placemark.findall(f".//{{{KML_NS}}}Point")
        geometry_counts["Polygon"] += len(polygon_elements)
        geometry_counts["Point"] += len(point_elements)
        geometry_counts["MultiGeometry"] += len(
            placemark.findall(f".//{{{KML_NS}}}MultiGeometry")
        )
        points += len(point_elements)
        if not polygon_elements and not point_elements:
            empty_placemarks += 1
        name = placemark.find(f"{{{KML_NS}}}name")
        description = placemark.find(f"{{{KML_NS}}}description")
        fields = parse_description(description.text if description is not None else None)
        for field, value in fields.items():
            field_coverage[field] += 1
            unique_fields[field].add(value)
        for polygon_element in polygon_elements:
            geometry = polygon_from_kml(polygon_element)
            vertices += len(geometry.exterior.coords) + sum(
                len(ring.coords) for ring in geometry.interiors
            )
            holes += len(geometry.interiors)
            if not geometry.is_valid:
                invalid[explain_validity(geometry)] += 1
            min_x, min_y, max_x, max_y = geometry.bounds
            bounds = [
                min(bounds[0], min_x),
                min(bounds[1], min_y),
                max(bounds[2], max_x),
                max(bounds[3], max_y),
            ]
            polygons.append(
                {
                    "name": normalize_component(name.text if name is not None else None),
                    "folder": path_name,
                    "fields": fields,
                    "geometry": geometry,
                }
            )

    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unkeyed = []
    for polygon in polygons:
        key = pair_key(polygon["fields"].get("HOJA"), polygon["fields"].get("CUAD"))
        if key:
            by_pair[key].append(polygon)
        else:
            unkeyed.append(polygon)
    multi = Counter(len(parts) for parts in by_pair.values())
    inconsistent = Counter()
    for parts in by_pair.values():
        for field in ("COD250", "HUSO", "ZONA", "CUTM10", "X_COORD", "Y_COORD"):
            values = {part["fields"].get(field) for part in parts}
            if len(values) > 1:
                inconsistent[field] += 1

    return {
        "kind": kind,
        "path": str(path.relative_to(ROOT)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "members": members,
        "placemarks": len(placemarks),
        "folder_counts": dict(sorted(folder_counts.items())),
        "geometry_counts": dict(sorted(geometry_counts.items())),
        "empty_placemarks": empty_placemarks,
        "polygon_parts": len(polygons),
        "point_labels": points,
        "vertices": vertices,
        "holes": holes,
        "bbox_wgs84": [round(value, 9) for value in bounds],
        "invalid_geometry_reasons": dict(invalid),
        "fields": {
            field: {
                "populated_features": field_coverage[field],
                "unique_values": len(unique_fields[field]),
                "examples": sorted(unique_fields[field])[:8],
            }
            for field in sorted(field_coverage)
        },
        "keyed_logical_cells": len(by_pair),
        "keyed_geometry_parts": sum(len(parts) for parts in by_pair.values()),
        "unkeyed_geometry_parts": len(unkeyed),
        "unkeyed_local_labels": len({item["name"] for item in unkeyed}),
        "parts_per_key_distribution": {
            str(count): cells for count, cells in sorted(multi.items())
        },
        "cells_with_multiple_parts": sum(cells for count, cells in multi.items() if count > 1),
        "maximum_parts_per_cell": max(multi, default=0),
        "inconsistent_part_attributes": dict(inconsistent),
        "_polygons_by_pair": by_pair,
        "_unkeyed": unkeyed,
    }


def iter_egif_records(manifest_path: Path) -> Iterable[dict[str, str | None]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for block in manifest["blocks"]:
        archive_path = ROOT / block["raw_path"]
        if sha256_file(archive_path) != block["sha256"]:
            raise RuntimeError(f"Checksum EGIF inesperado: {archive_path}")
        with zipfile.ZipFile(archive_path) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                with archive.open(name) as stream:
                    for _, element in ET.iterparse(stream, events=("end",)):
                        if local_name(element.tag) != "Pif":
                            continue
                        common = first_child(element, "pif_comun")
                        location = first_child(element, "pif_localizacion")
                        yield {
                            "record_id": child_text(element, "numeroparte"),
                            "year": child_text(common, "anio"),
                            "community": child_text(location, "idcomunidad"),
                            "province": child_text(location, "idprovincia"),
                            "municipality": child_text(location, "idmunicipio"),
                            "sheet": child_text(location, "hoja"),
                            "grid": child_text(location, "cuadricula"),
                            "x": child_text(location, "x"),
                            "y": child_text(location, "y"),
                            "zone": child_text(location, "huso"),
                            "datum": child_text(location, "iddatum"),
                        }
                        element.clear()


def load_ign_units(path: Path, level: str) -> tuple[dict[str, Any], dict[str, str]]:
    from shapely.geometry import shape

    if not path.exists():
        return {}, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    geometries = {}
    names = {}
    for feature in payload["features"]:
        properties = feature["properties"]
        nationalcode = str(properties.get("nationalcode") or "")
        if len(nationalcode) < 6:
            continue
        code = nationalcode[2:4] if level == "community" else nationalcode[4:6]
        geometries[code] = shape(feature["geometry"])
        names[code] = properties.get("nameunit")
    return geometries, names


def load_gva_municipalities(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    from shapely.geometry import shape

    if not path.exists():
        return {}, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    geometries = {}
    names = {}
    for feature in payload["features"]:
        properties = feature["properties"]
        code = str(properties.get("cod_ine_mun") or "")
        if len(code) == 5:
            geometries[code] = shape(feature["geometry"])
            names[code] = properties.get("nom_mun")
    return geometries, names


def compact_bytes(cells: dict[str, list[dict[str, Any]]], used: set[str], relations: list[tuple[str, str]]):
    from shapely.geometry import mapping
    from shapely.ops import unary_union

    features = []
    vertex_count = 0
    fragment_count = 0
    for key in sorted(used):
        parts = cells[key]
        fragment_count += len(parts)
        geometry = unary_union([part["geometry"] for part in parts])
        if geometry.geom_type == "Polygon":
            vertex_count += len(geometry.exterior.coords) + sum(
                len(ring.coords) for ring in geometry.interiors
            )
        else:
            for polygon in geometry.geoms:
                vertex_count += len(polygon.exterior.coords) + sum(
                    len(ring.coords) for ring in polygon.interiors
                )
        features.append(
            {
                "type": "Feature",
                "id": f"ccinif-grid:{key}",
                "properties": {"grid_cell_id": f"ccinif-grid:{key}"},
                "geometry": mapping(geometry),
            }
        )
    grid_payload = json.dumps(
        {"type": "FeatureCollection", "features": features},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    relation_payload = json.dumps(
        [[record_id, f"ccinif-grid:{key}"] for record_id, key in relations],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "unique_cells": len(used),
        "geometry_parts": fragment_count,
        "vertices": vertex_count,
        "grid_geojson_raw_bytes": len(grid_payload),
        "grid_geojson_gzip_bytes": len(gzip.compress(grid_payload, mtime=0)),
        "relations": len(relations),
        "relation_json_raw_bytes": len(relation_payload),
        "relation_json_gzip_bytes": len(gzip.compress(relation_payload, mtime=0)),
    }


def validate_grid_auxiliary_fields(cells: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Contrasta atributos auxiliares sin reconstruir la malla desde ellos."""
    import statistics

    from pyproj import Transformer
    from shapely.ops import transform

    cutm = Counter()
    zones = Counter()
    full_square_distances: dict[str, list[float]] = {"ETRS89": [], "ED50": []}
    transformers = {
        (label, zone): Transformer.from_crs(4326, base + zone, always_xy=True)
        for label, base in (("ETRS89", 25800), ("ED50", 23000))
        for zone in (29, 30, 31)
    }
    full_nominal_squares = 0
    zero_area_attributes = 0
    for parts in cells.values():
        for part in parts:
            fields = part["fields"]
            zone = fields.get("HUSO")
            zones[zone or "blank"] += 1
            expected_cutm = "".join(
                fields.get(field, "") for field in ("HUSO", "ZONA", "C100", "C10")
            )
            observed_cutm = fields.get("CUTM10", "")
            cutm["exact_composition"] += int(observed_cutm == expected_cutm)
            cutm["different_composition"] += int(observed_cutm != expected_cutm)
            cutm["blank"] += int(not observed_cutm)
            area = fields.get("AREA")
            zero_area_attributes += int(area == "0")
            if area != "100000000" or zone not in {"29", "30", "31"}:
                continue
            try:
                x = float(fields["X_COORD"].replace(",", "."))
                y = float(fields["Y_COORD"].replace(",", "."))
            except (KeyError, ValueError):
                continue
            full_nominal_squares += 1
            for label in ("ETRS89", "ED50"):
                projected = transform(
                    transformers[(label, int(zone))].transform,
                    part["geometry"],
                )
                centroid = projected.centroid
                full_square_distances[label].append(
                    ((centroid.x - x) ** 2 + (centroid.y - y) ** 2) ** 0.5
                )

    distance_summary = {}
    for label, values in full_square_distances.items():
        ordered = sorted(values)
        distance_summary[label] = {
            "samples": len(values),
            "median_m": round(statistics.median(values), 3),
            "p95_m": round(ordered[int(0.95 * (len(ordered) - 1))], 3),
            "maximum_m": round(max(values), 3),
        }
    return {
        "kml_crs": "OGC KML 2.2 longitude/latitude/altitude (WGS 84 semantics)",
        "huso_on_keyed_parts": dict(zones),
        "cutm10_composition_check": dict(cutm),
        "full_nominal_100km2_parts": full_nominal_squares,
        "zero_area_attribute_parts": zero_area_attributes,
        "xy_to_kml_centroid_diagnostic": distance_summary,
        "interpretation": (
            "For complete nominal squares, auxiliary X/Y centroids are closer to "
            "ETRS89 UTM than ED50 UTM, but the asset does not state an original datum. "
            "KML geometry remains authoritative; no grid is regenerated from X/Y."
        ),
        "canary_islands": (
            "157 polygon parts in CUADcanarias have local labels but no HOJA, HUSO, "
            "CUTM10 or other description fields; they cannot support exact EGIF links."
        ),
    }


def temporal_summary(by_year: dict[str, dict[str, int]]) -> dict[str, Any]:
    populated = []
    exact_years = []
    xy_years = []
    rows = []
    for year_text, counts in sorted(by_year.items(), key=lambda item: int(item[0])):
        records = counts["records"]
        complete = counts.get("with_sheet_and_grid", 0)
        if complete:
            populated.append(int(year_text))
        if counts.get("A_CONFIRMED", 0):
            exact_years.append(int(year_text))
        if counts.get("with_xy", 0):
            xy_years.append(int(year_text))
        rows.append(
            {
                "year": int(year_text),
                "records": records,
                "complete_sheet_grid": complete,
                "complete_sheet_grid_percent": round(100 * complete / records, 3),
                "exact_match": counts.get("A_CONFIRMED", 0),
                "xy": counts.get("with_xy", 0),
            }
        )
    return {
        "first_year_with_complete_sheet_grid": min(populated) if populated else None,
        "last_year_with_complete_sheet_grid": max(populated) if populated else None,
        "first_year_with_exact_ccinif_match": min(exact_years) if exact_years else None,
        "last_year_with_exact_ccinif_match": max(exact_years) if exact_years else None,
        "first_year_with_xy": min(xy_years) if xy_years else None,
        "last_year_with_xy": max(xy_years) if xy_years else None,
        "by_year": rows,
    }


def multiple_part_distribution(
    cells: dict[str, list[dict[str, Any]]],
    ccaa_boundaries: dict[str, Any],
    ccaa_names: dict[str, str],
) -> dict[str, Any]:
    from shapely.ops import unary_union

    by_community = Counter()
    top = []
    for key, parts in cells.items():
        if len(parts) <= 1:
            continue
        geometry = unary_union([part["geometry"] for part in parts])
        hits = []
        for code, boundary in ccaa_boundaries.items():
            if geometry.intersects(boundary):
                by_community[code] += 1
                hits.append({"code": code, "name": ccaa_names.get(code)})
        top.append({"pair": key, "parts": len(parts), "communities": hits})
    return {
        "cells": len(top),
        "by_intersected_autonomous_community": {
            code: {"name": ccaa_names.get(code), "cells": count}
            for code, count in sorted(by_community.items())
        },
        "largest": sorted(top, key=lambda item: (-item["parts"], item["pair"]))[:30],
        "semantics": "multiple KML polygons retained as geometry parts of one HOJA+CUAD cell",
    }


def audit_egif(
    manifest_path: Path,
    cells: dict[str, list[dict[str, Any]]],
    unkeyed_grid_labels: set[str],
    ccaa_boundaries: dict[str, Any],
    province_boundaries: dict[str, Any],
    municipality_boundaries: dict[str, Any],
) -> dict[str, Any]:
    by_year: dict[int, Counter[str]] = defaultdict(Counter)
    by_province: dict[str, Counter[str]] = defaultdict(Counter)
    by_community: dict[str, Counter[str]] = defaultdict(Counter)
    totals = Counter()
    pairs = Counter()
    matched_pairs = Counter()
    relations: list[tuple[str, str]] = []
    control_results = {}
    pair_territory_cache: dict[tuple[str, str, str], bool | None] = {}
    admin = Counter()
    admin_distinct: dict[str, set[tuple[str, str]]] = defaultdict(set)
    admin_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    gva_municipality = Counter()
    zone_counts = Counter()
    datum_counts = Counter()
    gva_pairs = set()
    gva_totals = Counter()

    def territory_intersects(key: str, level: str, code: str, boundary: Any) -> bool | None:
        cache_key = (key, level, code)
        if cache_key not in pair_territory_cache:
            if boundary is None:
                pair_territory_cache[cache_key] = None
            else:
                pair_territory_cache[cache_key] = any(
                    part["geometry"].intersects(boundary) for part in cells[key]
                )
        return pair_territory_cache[cache_key]

    for record in iter_egif_records(manifest_path):
        year = int(record["year"] or 0)
        province = str(record["province"] or "unknown")
        community = str(record["community"] or "unknown")
        record_id = str(record["record_id"] or "")
        sheet = normalize_component(record["sheet"])
        grid = normalize_component(record["grid"])
        key = pair_key(sheet, grid)
        totals["records"] += 1
        by_year[year]["records"] += 1
        by_province[province]["records"] += 1
        by_community[community]["records"] += 1
        if sheet and grid:
            if key in cells:
                status = "A_CONFIRMED"
            elif community == "12" and grid in unkeyed_grid_labels:
                # CUADcanarias conserva varias geometrías con la misma etiqueta
                # local, pero omite HOJA y no permite elegir una de forma exacta.
                status = "C_AMBIGUOUS"
                totals["complete_pair_with_ambiguous_unkeyed_grid_label"] += 1
            else:
                status = "D_UNUSABLE"
            pairs[key] += 1
            totals["with_sheet_and_grid"] += 1
            by_year[year]["with_sheet_and_grid"] += 1
            by_province[province]["with_sheet_and_grid"] += 1
            by_community[community]["with_sheet_and_grid"] += 1
            if key not in cells:
                totals["complete_pair_without_exact_key"] += 1
            if key in cells:
                matched_pairs[key] += 1
                relations.append((record_id, key))
                totals["exact_matches"] += 1
            elif status == "D_UNUSABLE":
                totals["complete_pair_unusable"] += 1
        elif sheet or grid:
            status = "C_AMBIGUOUS"
            totals["partial_reference"] += 1
        else:
            status = "NO_REFERENCE"
            totals["no_reference"] += 1
        by_year[year][status] += 1
        by_province[province][status] += 1
        by_community[community][status] += 1
        totals[status] += 1
        if record["x"] and record["y"]:
            totals["with_xy"] += 1
            by_year[year]["with_xy"] += 1
        if record["zone"]:
            zone_counts[str(record["zone"])] += 1
        if record["datum"]:
            datum_counts[str(record["datum"])] += 1

        if status == "A_CONFIRMED":
            province_code = province.zfill(2)
            result = territory_intersects(
                key, "province", province_code, province_boundaries.get(province_code)
            )
            province_result = f"province_{'compatible' if result else 'incompatible' if result is False else 'not_tested'}"
            admin[province_result] += 1
            admin_distinct[province_result].add((key, province_code))
            if result is False and len(admin_examples[province_result]) < 25:
                admin_examples[province_result].append(
                    {"record_id": record_id, "year": year, "pair": key, "province": province_code}
                )
            ign_community = EGIF_COMMUNITIES.get(community, (None, None))[1]
            result = territory_intersects(
                key, "community", ign_community or "", ccaa_boundaries.get(ign_community or "")
            )
            community_result = f"community_{'compatible' if result else 'incompatible' if result is False else 'not_tested'}"
            admin[community_result] += 1
            admin_distinct[community_result].add((key, ign_community or community))
            if result is False and len(admin_examples[community_result]) < 25:
                admin_examples[community_result].append(
                    {"record_id": record_id, "year": year, "pair": key, "community": community}
                )

        is_gva_historical = year <= 1992 and province in {"3", "12", "46"}
        if is_gva_historical:
            gva_totals["records"] += 1
            gva_totals[status] += 1
            if sheet and grid:
                gva_totals["with_sheet_and_grid"] += 1
                gva_pairs.add(key)
            else:
                gva_totals["without_complete_pair"] += 1
            municipality = record["municipality"]
            if status == "A_CONFIRMED" and municipality and municipality != "0":
                municipality_code = province.zfill(2) + str(municipality).zfill(3)
                result = territory_intersects(
                    key,
                    "municipality",
                    municipality_code,
                    municipality_boundaries.get(municipality_code),
                )
                gva_municipality[
                    "compatible" if result else "incompatible" if result is False else "not_tested"
                ] += 1
                if result is False and len(admin_examples["gva_municipality_incompatible"]) < 25:
                    admin_examples["gva_municipality_incompatible"].append(
                        {
                            "record_id": record_id,
                            "year": year,
                            "pair": key,
                            "municipality_id": municipality_code,
                        }
                    )
        if record_id in CONTROL_RECORDS:
            expected = CONTROL_RECORDS[record_id]
            control_results[record_id] = {
                **expected,
                "observed_pair": key,
                "pair_matches_expected": key == expected["pair"],
                "present_in_ccinif": key in cells if key else False,
                "classification": status,
                "geometry_parts": len(cells.get(key, [])) if key else 0,
            }

    unique_pairs = set(pairs)
    missing_pairs = sorted(unique_pairs - set(cells))
    future = compact_bytes(cells, set(matched_pairs), relations)
    temporal = temporal_summary(
        {str(year): dict(counts) for year, counts in sorted(by_year.items())}
    )
    return {
        "totals": dict(totals),
        "unique_complete_references": len(unique_pairs),
        "unique_exact_matches": len(matched_pairs),
        "unique_complete_pairs_not_found": len(missing_pairs),
        "missing_pair_examples": missing_pairs[:100],
        "by_year": {str(year): dict(counts) for year, counts in sorted(by_year.items())},
        "by_province": {key: dict(value) for key, value in sorted(by_province.items())},
        "by_community": {
            key: {
                "name": EGIF_COMMUNITIES.get(key, ("UNKNOWN", None))[0],
                **dict(value),
            }
            for key, value in sorted(by_community.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 999)
        },
        "temporal_coverage": temporal,
        "field_values": {
            "huso": dict(zone_counts),
            "iddatum": dict(datum_counts),
        },
        "administrative_validation": {
            "record_counts": dict(admin),
            "distinct_pair_territory_combinations": {
                key: len(value) for key, value in sorted(admin_distinct.items())
            },
            "incompatible_examples": dict(admin_examples),
            "interpretation": "independent compatibility check; incompatibility is retained as an anomaly and never used to alter source values",
        },
        "gva_1968_1992": {
            **dict(gva_totals),
            "unique_complete_references": len(gva_pairs),
            "unique_exact_matches": len(gva_pairs & set(cells)),
            "municipality_validation": dict(gva_municipality),
        },
        "controls": control_results,
        "future_web_estimate": future,
        "relations_semantics": "EGIF source record -> historical grid cell; never fire geometry",
    }


def public_kmz_summary(audit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in audit.items() if not key.startswith("_")}


def run(args: argparse.Namespace) -> dict[str, Any]:
    sheets = inspect_kmz(args.sheets, "historical_sheet_reference")
    grids = inspect_kmz(args.grids, "historical_10km_grid_reference")
    ccaa, ccaa_names = load_ign_units(args.ccaa, "community")
    provinces, province_names = load_ign_units(args.provinces, "province")
    municipalities, municipality_names = load_gva_municipalities(args.gva_municipalities)
    egif = audit_egif(
        args.egif_manifest,
        grids["_polygons_by_pair"],
        {item["name"] for item in grids["_unkeyed"] if item["name"]},
        ccaa,
        provinces,
        municipalities,
    )
    auxiliary_validation = validate_grid_auxiliary_fields(grids["_polygons_by_pair"])
    multi_part = multiple_part_distribution(
        grids["_polygons_by_pair"], ccaa, ccaa_names
    )
    local_manifest = json.loads(args.egif_manifest.read_text(encoding="utf-8"))
    result = {
        "schema_version": 1,
        "audit": "ES-1.5 CCINIF historical EGIF grid",
        "generated_at": utc_now(),
        "semantics": {
            "egif_geometry": None,
            "reference_entity": "historical_grid_cell",
            "relation": "EGIF source record -> historical_grid_cell",
            "prohibited_interpretations": [
                "grid cell as fire perimeter",
                "grid cell area as burned area",
                "point containment as recurrence",
                "grid cell as exact fire location",
            ],
        },
        "source_assets": {
            "sheets": public_kmz_summary(sheets),
            "grids": public_kmz_summary(grids),
            "delivery": {
                "provider": "CCINIF / MITECO",
                "received_on": "2026-08-26",
                "receipt_basis": "direct delivery reported by project owner; no email or personal data preserved",
                "provider_description": "Historical references based on 1:250,000 Military Cartography of Spain and nominal 10 x 10 km grid",
                "license_status": "false_pending_permission",
                "publishable": False,
            },
        },
        "egif_input": {
            "manifest_path": str(args.egif_manifest.relative_to(ROOT)),
            "selection": local_manifest["selection"],
            "blocks": local_manifest["totals"]["blocks"],
            "size_bytes": local_manifest["totals"]["size_bytes"],
            "records": local_manifest["totals"]["records"],
        },
        "egif_crosswalk": egif,
        "grid_auxiliary_field_validation": auxiliary_validation,
        "multiple_part_cells": multi_part,
        "territory_sources": {
            "ign_ccaa": {
                "path": str(args.ccaa),
                "available": bool(ccaa),
                "units": len(ccaa),
                "names": ccaa_names,
            },
            "ign_provinces": {
                "path": str(args.provinces),
                "available": bool(provinces),
                "units": len(provinces),
                "names": province_names,
            },
            "icv_gva_municipalities": {
                "path": display_path(args.gva_municipalities),
                "available": bool(municipalities),
                "units": len(municipalities),
                "names_count": len(municipality_names),
            },
        },
        "classification_contract": {
            "A_CONFIRMED": "Exact normalized HOJA+CUAD match to a keyed geometry in the CCINIF asset",
            "B_PROBABLE": "Strong evidence but an essential unverified element remains",
            "C_AMBIGUOUS": "Only one EGIF component is populated, or CUADcanarias offers repeated local labels without HOJA",
            "D_UNUSABLE": "Complete source reference is absent from the keyed CCINIF asset",
            "NO_REFERENCE": "Neither HOJA nor CUAD is populated",
        },
    }
    write_json(args.output, result)
    manifest = {
        "schema_version": 1,
        "dataset_id": "ccinif_historical_grid",
        "audit": "ES-1.5",
        "generated_at": result["generated_at"],
        "source": result["source_assets"]["grids"]["kind"],
        "provider": "CCINIF / MITECO",
        "received_on": "2026-08-26",
        "license_status": "false_pending_permission",
        "publishable": False,
        "raw_assets": {
            "HOJAS.kmz": {
                "format": "KMZ containing OGC KML 2.2",
                "member": sheets["members"][0]["name"],
                "size_bytes": sheets["size_bytes"],
                "sha256": sheets["sha256"],
                "git_status": "ignored_not_redistributed",
            },
            "CUADRICULAS.kmz": {
                "format": "KMZ containing OGC KML 2.2",
                "member": grids["members"][0]["name"],
                "size_bytes": grids["size_bytes"],
                "sha256": grids["sha256"],
                "git_status": "ignored_not_redistributed",
            },
        },
        "structure": {
            "sheet_polygon_parts": sheets["polygon_parts"],
            "logical_sheets": sheets["fields"].get("HOJA", {}).get("unique_values"),
            "grid_polygon_parts": grids["polygon_parts"],
            "keyed_grid_geometry_parts": grids["keyed_geometry_parts"],
            "keyed_logical_cells": grids["keyed_logical_cells"],
            "unkeyed_geometry_parts": grids["unkeyed_geometry_parts"],
            "cells_with_multiple_parts": grids["cells_with_multiple_parts"],
            "maximum_parts_per_cell": grids["maximum_parts_per_cell"],
        },
        "kml_inventory": {
            "sheets": public_kmz_summary(sheets),
            "grids": public_kmz_summary(grids),
        },
        "egif_crosswalk": {
            "records": egif["totals"]["records"],
            "records_with_complete_reference": egif["totals"]["with_sheet_and_grid"],
            "unique_complete_references": egif["unique_complete_references"],
            "exact_matches": egif["totals"]["exact_matches"],
            "unique_exact_matches": egif["unique_exact_matches"],
            "classification": {
                key: egif["totals"].get(key, 0)
                for key in ("A_CONFIRMED", "B_PROBABLE", "C_AMBIGUOUS", "D_UNUSABLE", "NO_REFERENCE")
            },
            "by_year": egif["by_year"],
            "by_province": egif["by_province"],
            "by_community": egif["by_community"],
        },
        "gva_control": egif["gva_1968_1992"],
        "control_records": egif["controls"],
        "administrative_validation": egif["administrative_validation"],
        "temporal_coverage": egif["temporal_coverage"],
        "grid_auxiliary_field_validation": auxiliary_validation,
        "multiple_part_cells": multi_part,
        "future_web_estimate": egif["future_web_estimate"],
        "semantics": result["semantics"],
        "full_ignored_audit": str(args.output.relative_to(ROOT)),
    }
    write_json(args.manifest, manifest)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheets", type=Path, default=RAW_CCINIF / "HOJAS.kmz")
    parser.add_argument("--grids", type=Path, default=RAW_CCINIF / "CUADRICULAS.kmz")
    parser.add_argument("--egif-manifest", type=Path, default=LOCAL_EGIF_MANIFEST)
    parser.add_argument("--ccaa", type=Path, default=IGN_CCAA)
    parser.add_argument("--provinces", type=Path, default=IGN_PROVINCES)
    parser.add_argument("--gva-municipalities", type=Path, default=ICV_MUNICIPALITIES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args)
    crosswalk = result["egif_crosswalk"]
    print(
        json.dumps(
            {
                "records": crosswalk["totals"]["records"],
                "exact_matches": crosswalk["totals"]["exact_matches"],
                "unique_exact_matches": crosswalk["unique_exact_matches"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
