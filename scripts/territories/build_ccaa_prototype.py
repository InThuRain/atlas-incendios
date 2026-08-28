#!/usr/bin/env python3
"""Construye el derivado CCAA oficial, pequeño y exclusivo de ES-4C2A1.

El GeoJSON de entrada procede de la colección `administrativeunit` de
IGN/CNIG. Este builder no deduce territorios desde incendios: cruza el código
documentado `nationalcode` con el snapshot canónico ES-2, conserva una sola
feature lógica por CCAA/ciudad autónoma y excluye el registro nacional 20 de
territorios no asociados.

La salida se deja bajo data/derived (ignorada): es un asset local de prototipo,
no un bundle público ni un límite de producción.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/autonomous-territories.geojson"
DEFAULT_SNAPSHOT = ROOT / "data/territories/spain/territories-2026-01-01.json"
DEFAULT_OUTPUT = ROOT / "data/derived/spain/es4c2a/ccaa.geojson"
DEFAULT_MANIFEST = ROOT / "data/sources/spain_ccaa_territories_manifest.json"
SOURCE_URL = (
    "https://api-features.ign.es/collections/administrativeunit/items?"
    "f=json&limit=100&nationallevelname=Comunidad%20aut%C3%B3noma"
)
SOURCE_SHA256 = "48d1cd7b1cc2a3a98f6d02a0043fddc8db43ba28aaa8789d6b030243417bf757"
EXPECTED_LOGICAL_TERRITORIES = 19
EXCLUDED_NATIONAL_CODE = "34200000000"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gzip_size(path: Path) -> int:
    destination = path.with_suffix(path.suffix + ".gz.tmp")
    with path.open("rb") as source, gzip.GzipFile(destination, "wb", mtime=0) as target:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            target.write(block)
    size = destination.stat().st_size
    destination.unlink()
    return size


def display_path(path: Path) -> str:
    """Ruta reproducible sin requerir Path.is_relative_to (Python 3.8)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def canonical_territories(snapshot_path: Path) -> dict[str, dict[str, Any]]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    territories = {
        row["official_code"]: row
        for row in snapshot["territories"]
        if row.get("territory_type") in {"autonomous_community", "autonomous_city"}
    }
    if len(territories) != EXPECTED_LOGICAL_TERRITORIES:
        raise ValueError(f"ES-2 expected {EXPECTED_LOGICAL_TERRITORIES} first-level territories, got {len(territories)}")
    return territories


def source_code(properties: dict[str, Any]) -> str:
    code = str(properties.get("nationalcode") or "")
    # BDLJE/INSPIRE: 34 (España) + código CCAA de dos posiciones + …
    if len(code) != 11 or not code.startswith("34") or not code[2:4].isdigit():
        raise ValueError(f"nationalcode BDLJE inválido: {code!r}")
    return code[2:4]


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


def inspect_source(source_path: Path, snapshot_path: Path) -> dict[str, Any]:
    from shapely.geometry import shape

    collection = json.loads(source_path.read_text(encoding="utf-8"))
    if collection.get("type") != "FeatureCollection":
        raise ValueError("La fuente IGN no es FeatureCollection")
    expected = canonical_territories(snapshot_path)
    selected: dict[str, dict[str, Any]] = {}
    excluded = []
    for feature in collection.get("features", []):
        properties = feature.get("properties") or {}
        missing = {"nationalcode", "nameunit", "nationallevelname"} - set(properties)
        if missing:
            raise ValueError(f"Faltan campos BDLJE: {sorted(missing)}")
        if properties["nationallevelname"] != "Comunidad autónoma":
            raise ValueError(f"Nivel BDLJE inesperado: {properties['nationallevelname']!r}")
        national_code = str(properties["nationalcode"])
        if national_code == EXCLUDED_NATIONAL_CODE:
            excluded.append(national_code)
            continue
        code = source_code(properties)
        if code not in expected:
            raise ValueError(f"Código BDLJE sin correspondencia ES-2: {national_code}")
        if code in selected:
            raise ValueError(f"Más de una feature BDLJE para código {code}")
        geom = shape(feature.get("geometry"))
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"Geometría BDLJE inválida para {national_code}")
        selected[code] = {"properties": properties, "geometry": geom}
    if set(selected) != set(expected):
        raise ValueError(f"Crosswalk incompleto: source={sorted(selected)}, ES-2={sorted(expected)}")
    if excluded != [EXCLUDED_NATIONAL_CODE]:
        raise ValueError(f"Registro BDLJE excluido inesperado: {excluded!r}")
    return {"collection": collection, "expected": expected, "selected": selected, "excluded": excluded}


def build(source_path: Path, snapshot_path: Path, output_path: Path, manifest_path: Path, tolerance_m: float, derived_at: str) -> dict[str, Any]:
    try:
        from pyproj import Transformer
        from shapely.geometry import mapping
        from shapely.ops import transform
    except ImportError as error:
        raise RuntimeError("ES-4C2A1 requiere PyProj y Shapely para simplificar y validar topología") from error

    if source_path.resolve() == DEFAULT_SOURCE.resolve() and sha256(source_path) != SOURCE_SHA256:
        raise ValueError("Checksum inesperado del snapshot IGN/OGC reutilizado")
    inspected = inspect_source(source_path, snapshot_path)
    to_web_meters = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    from_web_meters = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
    features = []
    territory_rows = []
    original_vertices = 0
    derived_vertices = 0
    area_errors = []
    for code in sorted(inspected["selected"]):
        source = inspected["selected"][code]
        original = source["geometry"]
        original_m = transform(to_web_meters, original)
        simplified_m = original_m.simplify(tolerance_m, preserve_topology=True)
        simplified = transform(from_web_meters, simplified_m)
        if simplified.is_empty or not simplified.is_valid:
            raise ValueError(f"Simplificación inválida para ES:CCAA:{code}")
        original_parts = geometry_parts(original)
        simplified_parts = geometry_parts(simplified)
        if simplified_parts != original_parts:
            raise ValueError(f"Simplificación perdió partes para ES:CCAA:{code}: {original_parts} -> {simplified_parts}")
        territory = inspected["expected"][code]
        original_vertex_count = geometry_vertices(original)
        simplified_vertex_count = geometry_vertices(simplified)
        original_vertices += original_vertex_count
        derived_vertices += simplified_vertex_count
        area_error = abs(simplified_m.area - original_m.area) / original_m.area * 100 if original_m.area else 0.0
        area_errors.append(area_error)
        west, south, east, north = simplified.bounds
        properties = {
            "territory_id": territory["territory_id"],
            "source_code": source["properties"]["nationalcode"],
            "official_name": territory["official_name"],
            "source_name": source["properties"]["nameunit"],
            "territory_type": territory["territory_type"],
            "bounds": [round(west, 7), round(south, 7), round(east, 7), round(north, 7)],
        }
        features.append({"type": "Feature", "id": territory["territory_id"], "properties": properties, "geometry": mapping(simplified)})
        territory_rows.append({
            "territory_id": territory["territory_id"], "source_code": source["properties"]["nationalcode"],
            "source_name": source["properties"]["nameunit"], "official_name": territory["official_name"],
            "territory_type": territory["territory_type"], "geometry_type": simplified.geom_type,
            "geometry_parts": simplified_parts, "bounds": properties["bounds"],
            "original_vertices": original_vertex_count, "derived_vertices": simplified_vertex_count,
            "relative_area_error_percent": area_error,
        })
    if len(features) != EXPECTED_LOGICAL_TERRITORIES or len({row["id"] for row in features}) != EXPECTED_LOGICAL_TERRITORIES:
        raise ValueError("El derivado no contiene 19 IDs territoriales únicos")
    national_bounds = [
        min(row["bounds"][0] for row in territory_rows), min(row["bounds"][1] for row in territory_rows),
        max(row["bounds"][2] for row in territory_rows), max(row["bounds"][3] for row in territory_rows),
    ]
    output = {
        "type": "FeatureCollection",
        "schema_version": "es4c2a1-ccaa-v1",
        "metadata": {
            "source_id": "ign_cnig_bdlje_administrativeunit",
            "source_url": SOURCE_URL,
            "source_retrieved_at": "2026-08-26",
            "source_coordinate_representation": "GeoJSON CRS84 / WGS84-compatible longitude-latitude",
            "source_native_crs": "ETRS89 geographic (península, Baleares, Ceuta y Melilla); REGCAN95 geographic (Canarias)",
            "web_crs": "EPSG:4326 longitude-latitude",
            "transformations": [
                "select official first-level CCAA/autonomous-city features only",
                "exclude BDLJE nationalcode 34200000000 (territorios no asociados a ninguna autonomía)",
                f"topology-preserving simplification in EPSG:3857 at {tolerance_m:g} m",
                "inverse transform to EPSG:4326 for web delivery",
            ],
            "attribution": "Obra derivada de BDLJE CC-BY 4.0 ign.es",
            "national_bounds": [round(value, 7) for value in national_bounds],
        },
        "features": features,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "es4c2a1-ccaa-manifest-v1",
        "phase": "ES-4C2A1 prototype only",
        "generated_at": derived_at,
        "source": {
            "organization": "IGN / CNIG",
            "product": "BDLJE / Límites y Unidades Administrativas Actuales · collection administrativeunit",
            "url": SOURCE_URL,
            "retrieved_at": "2026-08-26",
            "raw_path": display_path(source_path),
            "raw_bytes": source_path.stat().st_size,
            "raw_sha256": sha256(source_path),
            "format": "GeoJSON FeatureCollection via OGC API Features",
            "release_metadata": {"shapefile": "2026-07-28", "gml": "2026-08-10"},
            "native_crs": output["metadata"]["source_native_crs"],
            "license": "CC BY 4.0",
            "attribution": "Obra derivada de BDLJE CC-BY 4.0 ign.es",
        },
        "source_schema": {
            "layer": "administrativeunit",
            "source_features": len(inspected["collection"]["features"]),
            "used_features": EXPECTED_LOGICAL_TERRITORIES,
            "excluded_features": [{"nationalcode": EXCLUDED_NATIONAL_CODE, "reason": "territorios no asociados a ninguna autonomía"}],
            "fields_used": ["nationalcode", "nameunit", "nationallevelname"],
        },
        "crosswalk": territory_rows,
        "derived": {
            "path": display_path(output_path),
            "format": "GeoJSON FeatureCollection",
            "web_crs": "EPSG:4326",
            "logical_territories": len(territory_rows),
            "raw_bytes": output_path.stat().st_size,
            "gzip_bytes": gzip_size(output_path),
            "sha256": sha256(output_path),
            "simplification_tolerance_m": tolerance_m,
            "vertices": {
                "original": original_vertices,
                "derived": derived_vertices,
                "reduction_percent": (1 - derived_vertices / original_vertices) * 100,
            },
            "simplification_error": {
                "relative_area_error_percent": {"max": max(area_errors), "p95": percentile(area_errors, .95)},
            },
            "national_bounds": output["metadata"]["national_bounds"],
        },
        "validation": {
            "unique_territory_ids": len({row["territory_id"] for row in territory_rows}),
            "all_geometry_valid": True,
            "all_geometry_non_null": True,
            "canarias_present": any(row["territory_id"] == "ES:CCAA:05" for row in territory_rows),
            "baleares_present": any(row["territory_id"] == "ES:CCAA:04" for row in territory_rows),
            "ceuta_present": any(row["territory_id"] == "ES:CCAA:18" for row in territory_rows),
            "melilla_present": any(row["territory_id"] == "ES:CCAA:19" for row in territory_rows),
            "multiparts_preserved": True,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def validate(manifest_path: Path) -> dict[str, Any]:
    from shapely.geometry import shape

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    derived = Path(manifest["derived"]["path"])
    if not derived.is_absolute():
        derived = ROOT / derived
    if not derived.is_file() or sha256(derived) != manifest["derived"]["sha256"]:
        raise ValueError("Checksum del derivado CCAA no coincide")
    collection = json.loads(derived.read_text(encoding="utf-8"))
    features = collection.get("features", [])
    ids = [feature.get("properties", {}).get("territory_id") for feature in features]
    if len(features) != EXPECTED_LOGICAL_TERRITORIES or len(set(ids)) != EXPECTED_LOGICAL_TERRITORIES:
        raise ValueError("El derivado CCAA no conserva 19 territorios lógicos")
    if any(feature.get("geometry") is None for feature in features):
        raise ValueError("El derivado CCAA contiene geometría null")
    if any(shape(feature["geometry"]).is_empty or not shape(feature["geometry"]).is_valid for feature in features):
        raise ValueError("El derivado CCAA contiene geometría inválida")
    return {"valid": True, "logical_territories": len(features), "sha256": manifest["derived"]["sha256"], "geometry_valid": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    # 10 m conserva todas las partes y las geometrías válidas del snapshot
    # oficial; a 25 m Andalucía produce shells anidados tras simplificar.
    parser.add_argument("--tolerance-m", type=float, default=10.0)
    parser.add_argument("--derived-at", default="2026-08-28T00:00:00Z")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(validate(args.manifest), ensure_ascii=False))
        return 0
    manifest = build(args.source, args.snapshot, args.output, args.manifest, args.tolerance_m, args.derived_at)
    print(json.dumps({"valid": True, "logical_territories": manifest["derived"]["logical_territories"], "derived": manifest["derived"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
