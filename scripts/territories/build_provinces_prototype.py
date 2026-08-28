#!/usr/bin/env python3
"""Construye límites provinciales oficiales, exclusivos del prototipo ES-4C2A2.

La entrada es la capa BDLJE ``Provincia`` ya adquirida para ES-4C2A1. No se
deduce ninguna unidad a partir de incendios. El nivel fuente tiene 53
features: las 50 provincias canónicas, Ceuta y Melilla como unidades
estadísticas equivalentes de nivel provincial, y la geometría técnica de
territorios no asociados. El contrato ES-2 conserva solo las primeras como
provincias; las dos ciudades siguen siendo CCAA/ciudades autónomas.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/province-level.geojson"
DEFAULT_SNAPSHOT = ROOT / "data/territories/spain/territories-2026-01-01.json"
DEFAULT_OUTPUT = ROOT / "data/derived/spain/es4c2a/provinces.geojson"
DEFAULT_MANIFEST = ROOT / "data/sources/spain_province_territories_manifest.json"
DEFAULT_CATALOG = ROOT / "prototypes/es4c/province_catalog.mjs"
SOURCE_URL = (
    "https://api-features.ign.es/collections/administrativeunit/items?"
    "f=json&limit=100&nationallevelname=Provincia"
)
SOURCE_SHA256 = "58e4f68f4efc324dd9dfd0c1df0ea755846e3b717676b7137456577dc2083290"
EXCLUDED_NATIONAL_CODE = "34205400000"
CITY_SOURCE_TO_TERRITORY = {"51": "ES:CCAA:18", "52": "ES:CCAA:19"}
EXPECTED_PROVINCES = 50


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gzip_size(path: Path) -> int:
    temporary = path.with_suffix(path.suffix + ".gz.tmp")
    with path.open("rb") as source, gzip.GzipFile(temporary, "wb", mtime=0) as target:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            target.write(block)
    size = temporary.stat().st_size
    temporary.unlink()
    return size


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def province_code(properties: dict[str, Any]) -> str:
    code = str(properties.get("nationalcode") or "")
    # BDLJE/INSPIRE: 34 + CCAA(2) + provincia/equivalente(2) + 00000.
    if len(code) != 11 or not code.startswith("34") or not code[2:6].isdigit():
        raise ValueError(f"nationalcode BDLJE inválido: {code!r}")
    return code[4:6]


def autonomous_community_code(properties: dict[str, Any]) -> str:
    return str(properties["nationalcode"])[2:4]


def geometry_parts(geometry: Any) -> int:
    if geometry.geom_type == "Polygon":
        return 1
    if geometry.geom_type == "MultiPolygon":
        return len(geometry.geoms)
    raise ValueError(f"Tipo de geometría administrativa no soportado: {geometry.geom_type}")


def geometry_vertices(geometry: Any) -> int:
    polygons = geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry]
    return sum(len(polygon.exterior.coords) + sum(len(ring.coords) for ring in polygon.interiors) for polygon in polygons)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def canonical_snapshot(snapshot_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    provinces = {row["official_code"]: row for row in snapshot["territories"] if row.get("territory_type") == "province"}
    cities = {row["official_code"]: row for row in snapshot["territories"] if row.get("territory_type") == "autonomous_city"}
    if len(provinces) != EXPECTED_PROVINCES or set(cities) != {"18", "19"}:
        raise ValueError("Snapshot ES-2 no conserva 50 provincias y dos ciudades autónomas")
    return provinces, cities


def inspect_source(source_path: Path, snapshot_path: Path) -> dict[str, Any]:
    from shapely.geometry import shape

    collection = json.loads(source_path.read_text(encoding="utf-8"))
    if collection.get("type") != "FeatureCollection":
        raise ValueError("La fuente IGN no es FeatureCollection")
    provinces, cities = canonical_snapshot(snapshot_path)
    selected: dict[str, dict[str, Any]] = {}
    city_equivalents: list[dict[str, Any]] = []
    excluded: list[str] = []
    for feature in collection.get("features", []):
        properties = feature.get("properties") or {}
        required = {"nationalcode", "nameunit", "nationallevelname"}
        if required - set(properties):
            raise ValueError(f"Faltan campos BDLJE: {sorted(required - set(properties))}")
        if properties["nationallevelname"] != "Provincia":
            raise ValueError(f"Nivel BDLJE inesperado: {properties['nationallevelname']!r}")
        national_code = str(properties["nationalcode"])
        geom = shape(feature.get("geometry"))
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"Geometría BDLJE inválida para {national_code}")
        if national_code == EXCLUDED_NATIONAL_CODE:
            excluded.append(national_code)
            continue
        code = province_code(properties)
        if code in provinces:
            if code in selected:
                raise ValueError(f"Más de una feature BDLJE para provincia {code}")
            province = provinces[code]
            parent_code = autonomous_community_code(properties)
            if province.get("parent_id") != f"ES:CCAA:{parent_code}":
                raise ValueError(f"Parent BDLJE/ES-2 incoherente para provincia {code}")
            selected[code] = {"properties": properties, "geometry": geom, "territory": province}
            continue
        if code in CITY_SOURCE_TO_TERRITORY:
            city = cities.get(autonomous_community_code(properties))
            expected = CITY_SOURCE_TO_TERRITORY[code]
            if not city or city["territory_id"] != expected:
                raise ValueError(f"Ciudad autónoma BDLJE/ES-2 incoherente: {national_code}")
            city_equivalents.append({
                "source_code": national_code, "province_equivalent_code": code,
                "territory_id": expected, "source_name": properties["nameunit"],
                "territory_type": "autonomous_city",
            })
            continue
        raise ValueError(f"Código provincial BDLJE sin correspondencia ES-2: {national_code}")
    if set(selected) != set(provinces):
        raise ValueError(f"Crosswalk provincial incompleto: source={sorted(selected)} ES-2={sorted(provinces)}")
    if sorted(excluded) != [EXCLUDED_NATIONAL_CODE] or len(city_equivalents) != 2:
        raise ValueError("Inventario BDLJE de 53 features inesperado")
    return {"collection": collection, "selected": selected, "cities": city_equivalents, "excluded": excluded}


def catalog_module(rows: list[dict[str, Any]]) -> str:
    payload = [{key: row[key] for key in ("territory_id", "parent_id", "official_name")} for row in rows]
    return (
        "// Generado reproduciblemente desde el snapshot territorial ES-2 por\n"
        "// scripts/territories/build_provinces_prototype.py. No representa\n"
        "// Ceuta/Melilla como provincias: son ciudades autónomas sin hijos.\n"
        f"export const PROVINCE_OPTIONS = {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))};\n"
        "export const PROVINCES_BY_COMMUNITY = new Map();\n"
        "for (const province of PROVINCE_OPTIONS) {\n"
        "  const rows = PROVINCES_BY_COMMUNITY.get(province.parent_id) || [];\n"
        "  rows.push(province); PROVINCES_BY_COMMUNITY.set(province.parent_id, rows);\n"
        "}\n"
    )


def build(source_path: Path, snapshot_path: Path, output_path: Path, manifest_path: Path, catalog_path: Path, tolerance_m: float, generated_at: str) -> dict[str, Any]:
    from pyproj import Transformer
    from shapely.geometry import mapping
    from shapely.ops import transform

    if source_path.resolve() == DEFAULT_SOURCE.resolve() and sha256(source_path) != SOURCE_SHA256:
        raise ValueError("Checksum inesperado del snapshot IGN/OGC provincial reutilizado")
    inspected = inspect_source(source_path, snapshot_path)
    to_meters = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    from_meters = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
    features, rows, errors = [], [], []
    original_vertices = derived_vertices = 0
    for code in sorted(inspected["selected"]):
        source = inspected["selected"][code]
        original = source["geometry"]
        original_m = transform(to_meters, original)
        simplified_m = original_m.simplify(tolerance_m, preserve_topology=True)
        simplified = transform(from_meters, simplified_m)
        if simplified.is_empty or not simplified.is_valid or geometry_parts(simplified) != geometry_parts(original):
            raise ValueError(f"Simplificación provincial inválida o pierde partes: {code}")
        territory = source["territory"]
        west, south, east, north = simplified.bounds
        original_count, derived_count = geometry_vertices(original), geometry_vertices(simplified)
        error = abs(simplified_m.area - original_m.area) / original_m.area * 100 if original_m.area else 0.0
        original_vertices += original_count; derived_vertices += derived_count; errors.append(error)
        properties = {
            "territory_id": territory["territory_id"], "parent_id": territory["parent_id"],
            "source_code": source["properties"]["nationalcode"], "official_name": territory["official_name"],
            "source_name": source["properties"]["nameunit"], "territory_type": "province",
            "bounds": [round(west, 7), round(south, 7), round(east, 7), round(north, 7)],
        }
        features.append({"type": "Feature", "id": territory["territory_id"], "properties": properties, "geometry": mapping(simplified)})
        rows.append({**properties, "geometry_type": simplified.geom_type, "geometry_parts": geometry_parts(simplified),
                     "original_vertices": original_count, "derived_vertices": derived_count, "relative_area_error_percent": error})
    output = {
        "type": "FeatureCollection", "schema_version": "es4c2a2-provinces-v1",
        "metadata": {"source_id": "ign_cnig_bdlje_administrativeunit", "source_url": SOURCE_URL,
          "source_retrieved_at": "2026-08-26", "web_crs": "EPSG:4326 longitude-latitude",
          "source_coordinate_representation": "GeoJSON CRS84 / WGS84-compatible longitude-latitude",
          "source_native_crs": "ETRS89 geographic (península, Baleares, Ceuta y Melilla); REGCAN95 geographic (Canarias)",
          "transformations": ["select 50 official ES-2 province features only", f"topology-preserving simplification in EPSG:3857 at {tolerance_m:g} m", "inverse transform to EPSG:4326 for web delivery"],
          "attribution": "Obra derivada de BDLJE CC-BY 4.0 ign.es"}, "features": features,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(catalog_module(rows), encoding="utf-8")
    manifest = {
      "schema_version": "es4c2a2-province-manifest-v1", "phase": "ES-4C2A2 prototype only", "generated_at": generated_at,
      "source": {"organization": "IGN / CNIG", "product": "BDLJE / Límites y Unidades Administrativas Actuales · collection administrativeunit", "url": SOURCE_URL,
        "retrieved_at": "2026-08-26", "raw_path": display_path(source_path), "raw_bytes": source_path.stat().st_size, "raw_sha256": sha256(source_path),
        "format": "GeoJSON FeatureCollection via OGC API Features", "release_metadata": {"shapefile": "2026-07-28", "gml": "2026-08-10"},
        "native_crs": output["metadata"]["source_native_crs"], "license": "CC BY 4.0", "attribution": "Obra derivada de BDLJE CC-BY 4.0 ign.es"},
      "source_schema": {"layer": "administrativeunit", "source_features": len(inspected["collection"]["features"]), "features_by_role": {"canonical_province": 50, "autonomous_city_province_equivalent": 2, "unassociated": 1}, "fields_used": ["nationalcode", "nameunit", "nationallevelname"]},
      "crosswalk": rows, "province_equivalent_source_units": inspected["cities"],
      "excluded_features": [{"nationalcode": EXCLUDED_NATIONAL_CODE, "reason": "territorios no asociados a ninguna provincia"}],
      "derived": {"path": display_path(output_path), "catalog_path": display_path(catalog_path), "format": "GeoJSON FeatureCollection", "web_crs": "EPSG:4326", "logical_provinces": len(rows),
        "raw_bytes": output_path.stat().st_size, "gzip_bytes": gzip_size(output_path), "sha256": sha256(output_path), "simplification_tolerance_m": tolerance_m,
        "vertices": {"original": original_vertices, "derived": derived_vertices, "reduction_percent": (1 - derived_vertices / original_vertices) * 100},
        "simplification_error": {"relative_area_error_percent": {"max": max(errors), "p95": percentile(errors, .95)}}},
      "validation": {"unique_territory_ids": len({row["territory_id"] for row in rows}), "all_geometry_valid": True, "all_geometry_non_null": True, "canarias_provinces_present": all(any(row["territory_id"] == code for row in rows) for code in ("ES:PROV:35", "ES:PROV:38")), "multiparts_preserved": True},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def validate(manifest_path: Path) -> dict[str, Any]:
    from shapely.geometry import shape
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = ROOT / manifest["derived"]["path"]
    if not output.is_file() or sha256(output) != manifest["derived"]["sha256"]:
        raise ValueError("Checksum del derivado provincial no coincide")
    collection = json.loads(output.read_text(encoding="utf-8")); features = collection.get("features", [])
    ids = [feature.get("properties", {}).get("territory_id") for feature in features]
    if len(features) != EXPECTED_PROVINCES or len(set(ids)) != EXPECTED_PROVINCES:
        raise ValueError("El derivado provincial no conserva 50 IDs únicos")
    if any(feature.get("geometry") is None or shape(feature["geometry"]).is_empty or not shape(feature["geometry"]).is_valid for feature in features):
        raise ValueError("El derivado provincial contiene geometría null o inválida")
    return {"valid": True, "logical_provinces": len(features), "sha256": manifest["derived"]["sha256"], "geometry_valid": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE); parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST); parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--tolerance-m", type=float, default=10.0); parser.add_argument("--generated-at", default="2026-08-28T00:00:00Z"); parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(validate(args.manifest), ensure_ascii=False)); return 0
    manifest = build(args.source, args.snapshot, args.output, args.manifest, args.catalog, args.tolerance_m, args.generated_at)
    print(json.dumps({"valid": True, "logical_provinces": manifest["derived"]["logical_provinces"], "derived": manifest["derived"]}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
