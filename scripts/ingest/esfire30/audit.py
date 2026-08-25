#!/usr/bin/env python3
"""Auditoría reproducible de ESFire30 Causes para CV-4.2.

Lee el snapshot Zenodo preservado, audita el archivo completo y contrasta las
hipótesis EPSG:23030/EPSG:25830 con ICV. Ninguna geometría se repara. La salida
versionable contiene estadísticas y candidatos; el derivado con coordenadas es
diagnóstico, local e ignorado por Git.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import statistics
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data/raw/esfire30/18449006"
DEFAULT_ZIP = RAW / "ESFire30_Causes.zip"
DEFAULT_README = RAW / "read_me.txt"
DEFAULT_ZENODO = RAW / "zenodo-record.json"
DEFAULT_GRID = ROOT / "data/raw/esfire30/proj-grids/es_ign_SPED2ETV2.tif"
DEFAULT_BOUNDARY = (
    ROOT / "data/raw/recent/gva/snapshots/20260819T174426Z/boundary/icv_municipalities.geojson"
)
DEFAULT_ICV_GEOMETRIES = ROOT / "data/processed/gva/geometries.jsonl"
DEFAULT_ICV_FIRES = ROOT / "data/web/gva/fires.json"
DEFAULT_EGIF = ROOT / "data/processed/egif/gva/fires_1968_1992.jsonl"
DEFAULT_OUTPUT = ROOT / "data/sources/esfire30_audit.json"
DEFAULT_DIAGNOSTIC = ROOT / "data/processed/esfire30/gva/esfire30_1985_1992_diagnostic.jsonl"

PIPELINE_VERSION = "cv-4.2-1"
ACQUIRED_AT = "2026-08-25T10:08:29Z"
ZENODO_RECORD = 18_449_006
ZENODO_DOI = "10.5281/zenodo.18449006"
EXPECTED_ZIP_BYTES = 93_127_811
EXPECTED_ZIP_SHA256 = "150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8"
EXPECTED_ZIP_MD5 = "0e196c9a3445261d8fc02f2c5b89f691"
EXPECTED_README_SHA256 = "f1de630a5b4eef2723aa7f8d9504e78b6c33bf2900868a0e7526a96da626f94d"
EXPECTED_GRID_SHA256 = "61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961"
EXPECTED_TOTAL = 119_498
EXPECTED_GVA_PRE1993 = 710
EXPECTED_GIF = 180
YEARS = tuple(range(1985, 2022))
PRE1993_YEARS = tuple(range(1985, 1993))
OVERLAP_YEARS = tuple(range(1993, 2022))

CONTROL_RECORDS = {
    "1986461220": {"label": "Sot de Chera 1986", "expected_esfire_id": "esfire30:v1:1986:412"},
    "1991460176": {"label": "Yátova 1991", "expected_esfire_id": "esfire30:v1:1991:214"},
    "1991460188": {"label": "Chiva 1991", "expected_esfire_id": "esfire30:v1:1991:219"},
    "1992460251": {"label": "Sot de Chera 1992", "expected_esfire_id": "esfire30:v1:1992:180"},
    "1992460250": {"label": "Marines 1992", "expected_esfire_id": None},
    "1992120403": {"label": "Altura 1992", "expected_esfire_id": None},
    "1992469001": {"label": "Parte valenciano sin municipio, Marines–Altura", "expected_esfire_id": None},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - checksum de proveedor, no uso criptográfico
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    if not ordered:
        return None
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def distribution(values: Iterable[float]) -> dict[str, Any]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return {
        "count": len(clean),
        "sum": round(sum(clean), 6),
        "min": round(min(clean), 6) if clean else None,
        "p05": round(percentile(clean, 0.05), 6) if clean else None,
        "p25": round(percentile(clean, 0.25), 6) if clean else None,
        "median": round(percentile(clean, 0.50), 6) if clean else None,
        "p75": round(percentile(clean, 0.75), 6) if clean else None,
        "p95": round(percentile(clean, 0.95), 6) if clean else None,
        "max": round(max(clean), 6) if clean else None,
        "mean": round(statistics.fmean(clean), 6) if clean else None,
    }


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(serialized)
        temporary = Path(stream.name)
    temporary.replace(path)


def province_name(raw: str) -> str:
    if raw.startswith("Alacant"):
        return "Alicante"
    if raw.startswith("Castelló"):
        return "Castellón"
    if raw.startswith("València"):
        return "Valencia"
    raise ValueError(f"Provincia ICV desconocida: {raw}")


def signed_ring_area(coordinates: list[tuple[float, float]]) -> float:
    return sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(coordinates, coordinates[1:])
    ) / 2.0


def construct_icv_geometry(esri_geometry: dict[str, Any]):
    """Construye una vista OGC por orientación Esri; nunca repara."""
    from shapely.geometry import MultiPolygon, Polygon

    shells: list[dict[str, Any]] = []
    holes: list[dict[str, Any]] = []
    for index, raw_ring in enumerate(esri_geometry.get("rings") or []):
        coordinates = [(position[0], position[1]) for position in raw_ring]
        item = {"index": index, "coordinates": coordinates, "polygon": Polygon(coordinates)}
        (shells if signed_ring_area(coordinates) < 0 else holes).append(item)
    if not shells:
        return None
    shell_holes = {shell["index"]: [] for shell in shells}
    for hole in holes:
        candidates = [shell for shell in shells if shell["polygon"].covers(hole["polygon"])]
        if not candidates:
            return None
        parent = min(candidates, key=lambda shell: abs(shell["polygon"].area))
        shell_holes[parent["index"]].append(hole["coordinates"])
    polygons = [Polygon(shell["coordinates"], shell_holes[shell["index"]]) for shell in shells]
    return polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)


def archive_reader(archive: zipfile.ZipFile, year: int):
    import shapefile

    base = f"RF_jja/predicciones_{year}"
    return shapefile.Reader(
        shp=io.BytesIO(archive.read(base + ".shp")),
        shx=io.BytesIO(archive.read(base + ".shx")),
        dbf=io.BytesIO(archive.read(base + ".dbf")),
        encoding="utf-8",
    )


def split_rings(raw_shape) -> list[list[tuple[float, float]]]:
    starts = list(raw_shape.parts) + [len(raw_shape.points)]
    return [
        [(float(x), float(y)) for x, y in raw_shape.points[starts[index] : starts[index + 1]]]
        for index in range(len(starts) - 1)
    ]


def raw_geometry_checksum(raw_shape) -> str:
    payload = {
        "shape_type": raw_shape.shapeType,
        "parts": list(raw_shape.parts),
        "points": [[float(x), float(y)] for x, y in raw_shape.points],
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def prepare_transformations(grid_path: Path):
    import pyproj
    from pyproj.transformer import AreaOfInterest, TransformerGroup

    if sha256_file(grid_path) != EXPECTED_GRID_SHA256:
        raise ValueError("Checksum inesperado para es_ign_SPED2ETV2.tif")
    pyproj.datadir.append_data_dir(str(grid_path.parent))
    area = AreaOfInterest(-1.7, 37.6, 1.4, 41.2)
    group_4326 = TransformerGroup("EPSG:23030", "EPSG:4326", always_xy=True, area_of_interest=area)
    group_3857 = TransformerGroup("EPSG:23030", "EPSG:3857", always_xy=True, area_of_interest=area)
    group_25830 = TransformerGroup("EPSG:23030", "EPSG:25830", always_xy=True, area_of_interest=area)
    if not group_4326.best_available or not group_3857.best_available or not group_25830.best_available:
        raise RuntimeError("La transformación ED50 no dispone de la rejilla oficial")
    ed50_to_4326 = group_4326.transformers[0]
    ed50_to_3857 = group_3857.transformers[0]
    return {
        "ed50_to_4326": ed50_to_4326,
        "ed50_to_3857": ed50_to_3857,
        "ed50_to_25830": group_25830.transformers[0],
        "etrs89_to_4326": pyproj.Transformer.from_crs(25830, 4326, always_xy=True),
        "etrs89_to_3857": pyproj.Transformer.from_crs(25830, 3857, always_xy=True),
        "webmercator_to_25830": pyproj.Transformer.from_crs(3857, 25830, always_xy=True),
        "wgs84_to_3857": pyproj.Transformer.from_crs(4326, 3857, always_xy=True),
        "wgs84_to_ed50": TransformerGroup("EPSG:4326", "EPSG:23030", always_xy=True, area_of_interest=area).transformers[0],
        "wgs84_to_etrs89": pyproj.Transformer.from_crs(4326, 25830, always_xy=True),
        "metadata": {
            "pyproj_version": pyproj.__version__,
            "proj_version": pyproj.proj_version_str,
            "proj_data_configuration": (
                "Datos PROJ incluidos con pyproj más la rejilla local reproducible "
                "data/raw/esfire30/proj-grids/es_ign_SPED2ETV2.tif"
            ),
            "selected_operation_4326": ed50_to_4326.description,
            "selected_operation_3857": ed50_to_3857.description,
            "selected_operation_25830": group_25830.transformers[0].description,
            "declared_accuracy_m": ed50_to_4326.accuracy,
            "declared_accuracy_ed50_to_etrs89_m": group_25830.transformers[0].accuracy,
            "grid": {
                "filename": grid_path.name,
                "source_url": "https://cdn.proj.org/es_ign_SPED2ETV2.tif",
                "sha256": EXPECTED_GRID_SHA256,
                "bytes": grid_path.stat().st_size,
            },
            "best_available": True,
        },
    }


def load_boundaries(boundary_path: Path, transforms: dict[str, Any]) -> dict[str, Any]:
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union
    from shapely.prepared import prep

    source = json.loads(boundary_path.read_text(encoding="utf-8"))
    by_province: dict[str, list[Any]] = defaultdict(list)
    by_municipality: dict[str, Any] = {}
    for feature in source["features"]:
        geometry = shape(feature["geometry"])
        properties = feature["properties"]
        by_province[province_name(properties["provincia"])].append(geometry)
        by_municipality[str(properties["cod_ine_mun"])] = geometry
    provinces_wgs = {name: unary_union(parts) for name, parts in by_province.items()}
    provinces_ed50 = {
        name: transform(transforms["wgs84_to_ed50"].transform, geometry)
        for name, geometry in provinces_wgs.items()
    }
    provinces_etrs = {
        name: transform(transforms["wgs84_to_etrs89"].transform, geometry)
        for name, geometry in provinces_wgs.items()
    }
    municipalities_ed50 = {
        code: transform(transforms["wgs84_to_ed50"].transform, geometry)
        for code, geometry in by_municipality.items()
    }
    provinces_25830 = {
        name: transform(transforms["wgs84_to_etrs89"].transform, geometry)
        for name, geometry in provinces_wgs.items()
    }
    municipalities_25830 = {
        code: transform(transforms["wgs84_to_etrs89"].transform, geometry)
        for code, geometry in by_municipality.items()
    }
    return {
        "feature_count": len(source["features"]),
        "provinces_wgs": provinces_wgs,
        "provinces_ed50": provinces_ed50,
        "provinces_etrs": provinces_etrs,
        "provinces_25830": provinces_25830,
        "prepared_ed50": {name: prep(geometry) for name, geometry in provinces_ed50.items()},
        "prepared_etrs": {name: prep(geometry) for name, geometry in provinces_etrs.items()},
        "municipalities_ed50": municipalities_ed50,
        "municipalities_25830": municipalities_25830,
        "prepared_municipalities_ed50": {
            code: prep(geometry) for code, geometry in municipalities_ed50.items()
        },
    }


def intersects_any(geometry, prepared: dict[str, Any]) -> list[str]:
    return [name for name, candidate in prepared.items() if candidate.intersects(geometry)]


def primary_province(geometry, hits: list[str], provinces: dict[str, Any]) -> str:
    if len(hits) == 1:
        return hits[0]
    areas = {name: geometry.intersection(provinces[name]).area for name in hits}
    return max(areas, key=areas.get)


def inspect_archive(
    zip_path: Path,
    boundaries: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Inventaría 1985–2021 y audita topología nacional 1985–1992."""
    from shapely.geometry import shape
    from shapely.validation import explain_validity

    year_inventory: list[dict[str, Any]] = []
    selected_cv: list[dict[str, Any]] = []
    national_topology = Counter()
    invalid_reasons = Counter()
    raw_hashes: dict[str, list[tuple[int, int]]] = defaultdict(list)
    prj_values: dict[str, list[int]] = defaultdict(list)
    cpg_values: dict[str, list[int]] = defaultdict(list)
    schemas: dict[str, dict[str, Any]] = {}
    coordinate_min_x = math.inf
    coordinate_min_y = math.inf
    coordinate_max_x = -math.inf
    coordinate_max_y = -math.inf

    with zipfile.ZipFile(zip_path) as archive:
        members = [
            {
                "path": info.filename,
                "bytes_uncompressed": info.file_size,
                "bytes_compressed": info.compress_size,
                "crc32": f"{info.CRC:08x}",
            }
            for info in archive.infolist()
            if not info.is_dir()
        ]
        for year in YEARS:
            base = f"RF_jja/predicciones_{year}"
            reader = archive_reader(archive, year)
            fields = [
                {"name": field[0], "type": field[1], "length": field[2], "decimals": field[3]}
                for field in reader.fields[1:]
            ]
            schema_hash = hashlib.sha256(
                json.dumps(fields, separators=(",", ":"), sort_keys=True).encode("utf-8")
            ).hexdigest()
            schemas.setdefault(schema_hash, {"sha256": schema_hash, "fields": fields, "years": []})["years"].append(year)
            prj = archive.read(base + ".prj").decode("utf-8").strip()
            cpg = archive.read(base + ".cpg").decode("ascii").strip()
            prj_values[prj].append(year)
            cpg_values[cpg].append(year)
            attribute_counters = {
                "year_mismatch": 0,
                "null_area": 0,
                "null_grid": 0,
                "null_cause": 0,
                "method": Counter(),
                "shape_types": Counter(),
            }
            for index, shape_record in enumerate(reader.iterShapeRecords()):
                raw_shape = shape_record.shape
                attributes = shape_record.record.as_dict()
                attribute_counters["year_mismatch"] += int(attributes.get("year") != year)
                attribute_counters["null_area"] += int(attributes.get("area_ha") is None)
                attribute_counters["null_grid"] += int(not attributes.get("Id_cuad"))
                attribute_counters["null_cause"] += int(attributes.get("idcausa") is None)
                attribute_counters["method"][str(attributes.get("Method"))] += 1
                attribute_counters["shape_types"][str(raw_shape.shapeType)] += 1
                if raw_shape.points:
                    xs = [point[0] for point in raw_shape.points]
                    ys = [point[1] for point in raw_shape.points]
                    coordinate_min_x = min(coordinate_min_x, min(xs))
                    coordinate_min_y = min(coordinate_min_y, min(ys))
                    coordinate_max_x = max(coordinate_max_x, max(xs))
                    coordinate_max_y = max(coordinate_max_y, max(ys))
                try:
                    geometry = shape(raw_shape.__geo_interface__)
                except Exception:
                    geometry = None

                source_record_id = f"esfire30:v1:{year}:{index}"
                geometry_checksum = raw_geometry_checksum(raw_shape)
                if year in PRE1993_YEARS:
                    national_topology["geometries"] += 1
                    national_topology["null_shapes"] += int(raw_shape.shapeType == 0)
                    national_topology["empty"] += int(geometry is None or geometry.is_empty)
                    rings = split_rings(raw_shape)
                    national_topology["rings"] += len(rings)
                    national_topology["unclosed_rings"] += sum(
                        bool(ring) and ring[0] != ring[-1] for ring in rings
                    )
                    national_topology["vertices"] += len(raw_shape.points)
                    raw_hashes[geometry_checksum].append((year, index))
                    if geometry is not None and not geometry.is_empty:
                        national_topology[f"type_{geometry.geom_type}"] += 1
                        national_topology["multipart"] += int(geometry.geom_type == "MultiPolygon")
                        holes = (
                            sum(len(part.interiors) for part in geometry.geoms)
                            if geometry.geom_type == "MultiPolygon"
                            else len(geometry.interiors)
                        )
                        national_topology["holes"] += holes
                        national_topology["with_holes"] += int(holes > 0)
                        national_topology["zero_area"] += int(geometry.area == 0)
                        national_topology["invalid"] += int(not geometry.is_valid)
                        if not geometry.is_valid:
                            invalid_reasons[explain_validity(geometry).split("[")[0].strip()] += 1

                if geometry is None or geometry.is_empty:
                    continue
                hits_ed50 = intersects_any(geometry, boundaries["prepared_ed50"])
                if not hits_ed50:
                    continue
                province = primary_province(geometry, hits_ed50, boundaries["provinces_ed50"])
                selected_cv.append(
                    {
                        "source_record_id": source_record_id,
                        "geometry_id": f"esfire30:geometry:v1:{year}:{index}:{geometry_checksum[:16]}",
                        "year": year,
                        "record_index": index,
                        "geometry_checksum_sha256": geometry_checksum,
                        "geometry": geometry,
                        "raw_shape": raw_shape,
                        "area_ha": float(attributes["area_ha"]),
                        "id_cuad": attributes.get("Id_cuad"),
                        "idcausa": attributes.get("idcausa"),
                        "idcausa_ma": attributes.get("idcausa_ma"),
                        "method": attributes.get("Method"),
                        "predicted_cause": attributes.get("predicted_"),
                        "primary_province": province,
                        "intersected_provinces": sorted(hits_ed50),
                        "geometry_type": geometry.geom_type,
                        "is_valid": geometry.is_valid,
                        "validity_reason": explain_validity(geometry),
                        "vertices": len(raw_shape.points),
                        "holes": (
                            sum(len(part.interiors) for part in geometry.geoms)
                            if geometry.geom_type == "MultiPolygon"
                            else len(geometry.interiors)
                        ),
                        "geometric_area_ha_raw": geometry.area / 10_000,
                    }
                )
            year_inventory.append(
                {
                    "year": year,
                    "records": len(reader),
                    "bbox_raw": list(reader.bbox),
                    "schema_sha256": schema_hash,
                    "prj_sha256": hashlib.sha256(prj.encode("utf-8")).hexdigest(),
                    "cpg": cpg,
                    "year_attribute_mismatch": attribute_counters["year_mismatch"],
                    "null_area": attribute_counters["null_area"],
                    "null_id_cuad": attribute_counters["null_grid"],
                    "null_idcausa": attribute_counters["null_cause"],
                    "method_counts": dict(sorted(attribute_counters["method"].items())),
                    "shape_type_counts": dict(sorted(attribute_counters["shape_types"].items())),
                }
            )

    duplicates = [locations for locations in raw_hashes.values() if len(locations) > 1]
    topology = {
        **dict(national_topology),
        "valid": national_topology["geometries"] - national_topology["invalid"] - national_topology["empty"],
        "invalid_reason_counts": dict(sorted(invalid_reasons.items())),
        "duplicated_geometry_groups": len(duplicates),
        "duplicated_geometry_records": sum(len(group) for group in duplicates),
        "duplicated_across_year_groups": sum(len({year for year, _ in group}) > 1 for group in duplicates),
        "duplicate_examples": [
            [{"year": year, "record_index": index} for year, index in group]
            for group in sorted(duplicates, key=lambda item: (-len(item), item))[:20]
        ],
    }
    inventory = {
        "zip_members": members,
        "member_count": len(members),
        "uncompressed_bytes": sum(member["bytes_uncompressed"] for member in members),
        "compressed_member_bytes": sum(member["bytes_compressed"] for member in members),
        "years": [min(YEARS), max(YEARS)],
        "year_inventory": year_inventory,
        "total_records": sum(row["records"] for row in year_inventory),
        "schemas": list(schemas.values()),
        "prj_variants": [
            {"text": text, "years": years, "sha256": hashlib.sha256(text.encode()).hexdigest()}
            for text, years in prj_values.items()
        ],
        "cpg_variants": [{"value": value, "years": years} for value, years in cpg_values.items()],
        "coordinate_range_raw": {
            "min_x": coordinate_min_x,
            "min_y": coordinate_min_y,
            "max_x": coordinate_max_x,
            "max_y": coordinate_max_y,
        },
        "contains_xml": any(member["path"].lower().endswith(".xml") for member in members),
        "contains_readme": any("read" in member["path"].lower() for member in members),
    }
    return inventory, selected_cv, topology


def cv_pre1993_summary(features: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [feature for feature in features if feature["year"] in PRE1993_YEARS]
    by_year_province: dict[int, Counter[str]] = defaultdict(Counter)
    for feature in selected:
        by_year_province[feature["year"]][feature["primary_province"]] += 1
    geometry_hash_counts = Counter(feature["geometry_checksum_sha256"] for feature in selected)
    return {
        "polygons": len(selected),
        "by_primary_province": dict(sorted(Counter(feature["primary_province"] for feature in selected).items())),
        "by_year": dict(sorted(Counter(feature["year"] for feature in selected).items())),
        "by_year_and_primary_province": {
            str(year): dict(sorted(counts.items())) for year, counts in sorted(by_year_province.items())
        },
        "cross_province": sum(len(feature["intersected_provinces"]) > 1 for feature in selected),
        "source_area_ha": distribution(feature["area_ha"] for feature in selected),
        "geometric_area_ha_raw": distribution(feature["geometric_area_ha_raw"] for feature in selected),
        "source_area_geometric_relative_difference": distribution(
            abs(feature["area_ha"] - feature["geometric_area_ha_raw"]) / max(feature["area_ha"], 1e-9)
            for feature in selected
        ),
        "source_area_ge_500_ha": sum(feature["area_ha"] >= 500 for feature in selected),
        "source_area_lt_500_ha": sum(feature["area_ha"] < 500 for feature in selected),
        "vertices": sum(feature["vertices"] for feature in selected),
        "polygon": sum(feature["geometry_type"] == "Polygon" for feature in selected),
        "multipolygon": sum(feature["geometry_type"] == "MultiPolygon" for feature in selected),
        "invalid": sum(not feature["is_valid"] for feature in selected),
        "with_holes": sum(feature["holes"] > 0 for feature in selected),
        "holes": sum(feature["holes"] for feature in selected),
        "unique_geometry_checksums": len(geometry_hash_counts),
        "duplicate_geometry_groups": sum(count > 1 for count in geometry_hash_counts.values()),
    }


def load_icv(
    icv_geometry_path: Path,
    icv_fires_path: Path,
    transforms: dict[str, Any],
) -> tuple[dict[int, list[dict[str, Any]]], dict[str, Any]]:
    from shapely.ops import transform

    fire_rows = json.loads(icv_fires_path.read_text(encoding="utf-8"))["fires"]
    fires = {row["fire_id"]: row for row in fire_rows}
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    counts = Counter()
    with icv_geometry_path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            year = int(row["source_year"])
            if year not in OVERLAP_YEARS:
                continue
            counts["records"] += 1
            try:
                geometry = construct_icv_geometry(row["geometry"])
            except Exception:
                geometry = None
            if geometry is None or geometry.is_empty:
                counts["construction_failed"] += 1
                continue
            if not geometry.is_valid:
                counts["invalid_excluded"] += 1
                continue
            geometry = transform(transforms["webmercator_to_25830"].transform, geometry)
            fire = fires.get(row["fire_id"], {})
            by_year[year].append(
                {
                    "geometry": geometry,
                    "geometry_id": row["geometry_id"],
                    "fire_id": row["fire_id"],
                    "municipality_id": fire.get("municipality_id"),
                    "municipality_name": fire.get("municipality_name"),
                    "province": fire.get("province"),
                    "start_date": fire.get("start_date"),
                    "reported_forest_area_ha": fire.get("reported_forest_area_ha"),
                }
            )
            counts["usable"] += 1
    return by_year, dict(counts)


def metric_for_pair(es_geometry, icv_geometry) -> dict[str, float]:
    intersection = es_geometry.intersection(icv_geometry).area
    union = es_geometry.union(icv_geometry).area
    return {
        "intersection_m2_epsg25830": intersection,
        "union_m2_epsg25830": union,
        "iou": intersection / union if union else 0.0,
        "centroid_distance_m": es_geometry.centroid.distance(icv_geometry.centroid),
        "hausdorff_distance_m": es_geometry.hausdorff_distance(icv_geometry),
    }


def compare_crs(
    features: list[dict[str, Any]],
    icv_by_year: dict[int, list[dict[str, Any]]],
    transforms: dict[str, Any],
    boundaries: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from shapely.geometry import box
    from shapely.ops import transform
    from shapely.strtree import STRtree

    trees: dict[int, tuple[Any, list[dict[str, Any]]]] = {}
    for year, rows in icv_by_year.items():
        trees[year] = (STRtree([row["geometry"] for row in rows]), rows)

    matched: list[dict[str, Any]] = []
    hypothesis_offset = []
    for feature in features:
        if feature["year"] not in OVERLAP_YEARS or feature["year"] not in trees:
            continue
        raw_geometry = feature["geometry"]
        geometries = {
            "epsg23030": transform(transforms["ed50_to_25830"].transform, raw_geometry),
            "epsg25830": raw_geometry,
        }
        hypothesis_offset.append(
            geometries["epsg23030"].centroid.distance(geometries["epsg25830"].centroid)
        )
        tree, rows = trees[feature["year"]]
        candidates: set[int] = set()
        for geometry in geometries.values():
            min_x, min_y, max_x, max_y = geometry.bounds
            candidates.update(int(index) for index in tree.query(box(min_x - 5000, min_y - 5000, max_x + 5000, max_y + 5000)))
        if not candidates:
            continue
        scored: list[tuple[float, int, dict[str, Any], dict[str, Any]]] = []
        for index in candidates:
            icv = rows[index]
            try:
                metrics = {
                    name: metric_for_pair(geometry, icv["geometry"])
                    for name, geometry in geometries.items()
                }
            except Exception:
                continue
            best_iou = max(metric["iou"] for metric in metrics.values())
            best_distance = min(metric["centroid_distance_m"] for metric in metrics.values())
            scored.append((best_iou, -best_distance, icv, metrics))
        if not scored:
            continue
        _, _, icv, metrics = max(scored, key=lambda item: (item[0], item[1]))
        area_ratio = raw_geometry.area / max(icv["geometry"].area, 1e-9)
        validation_pair = max(value["iou"] for value in metrics.values()) >= 0.20 and 0.25 <= area_ratio <= 4.0
        municipality_compatibility = {}
        province_compatibility = {}
        municipality_id = icv.get("municipality_id")
        for name, geometry in geometries.items():
            municipality = boundaries["municipalities_25830"].get(str(municipality_id))
            municipality_compatibility[name] = (
                geometry.intersects(municipality) if municipality is not None else None
            )
            province_text = str(icv.get("province") or "")
            province = (
                "Alicante" if "Alicante" in province_text else
                "Castellón" if "Castell" in province_text else
                "Valencia" if "Val" in province_text else None
            )
            province_geometry = boundaries["provinces_25830"].get(province) if province else None
            province_compatibility[name] = (
                geometry.intersects(province_geometry) if province_geometry is not None else None
            )
        matched.append(
            {
                "source_record_id": feature["source_record_id"],
                "year": feature["year"],
                "area_ha": feature["area_ha"],
                "icv_geometry_id": icv["geometry_id"],
                "icv_fire_id": icv["fire_id"],
                "icv_start_date": icv.get("start_date"),
                "icv_municipality_id": municipality_id,
                "icv_municipality_name": icv.get("municipality_name"),
                "icv_reported_forest_area_ha": icv.get("reported_forest_area_ha"),
                "geometry_area_ratio_esfire_to_icv_epsg25830": area_ratio,
                "validation_pair": validation_pair,
                "metrics": metrics,
                "municipality_compatible": municipality_compatibility,
                "province_compatible": province_compatibility,
            }
        )

    validation = [row for row in matched if row["validation_pair"]]
    hypothesis_summary = {}
    for hypothesis in ("epsg23030", "epsg25830"):
        hypothesis_summary[hypothesis] = {
            "pairs": len(validation),
            "iou": distribution(row["metrics"][hypothesis]["iou"] for row in validation),
            "centroid_distance_m": distribution(
                row["metrics"][hypothesis]["centroid_distance_m"] for row in validation
            ),
            "hausdorff_distance_m": distribution(
                row["metrics"][hypothesis]["hausdorff_distance_m"] for row in validation
            ),
            "municipality_compatible": sum(
                row["municipality_compatible"][hypothesis] is True for row in validation
            ),
            "municipality_incompatible": sum(
                row["municipality_compatible"][hypothesis] is False for row in validation
            ),
            "municipality_unavailable": sum(
                row["municipality_compatible"][hypothesis] is None for row in validation
            ),
            "province_compatible": sum(
                row["province_compatible"][hypothesis] is True for row in validation
            ),
            "province_incompatible": sum(
                row["province_compatible"][hypothesis] is False for row in validation
            ),
            "province_unavailable": sum(
                row["province_compatible"][hypothesis] is None for row in validation
            ),
            "iou_ge_0_5": sum(row["metrics"][hypothesis]["iou"] >= 0.5 for row in validation),
            "iou_ge_0_25": sum(row["metrics"][hypothesis]["iou"] >= 0.25 for row in validation),
        }
    ed50_wins_iou = sum(
        row["metrics"]["epsg23030"]["iou"] > row["metrics"]["epsg25830"]["iou"]
        for row in validation
    )
    etrs_wins_iou = sum(
        row["metrics"]["epsg25830"]["iou"] > row["metrics"]["epsg23030"]["iou"]
        for row in validation
    )
    ed50_wins_distance = sum(
        row["metrics"]["epsg23030"]["centroid_distance_m"]
        < row["metrics"]["epsg25830"]["centroid_distance_m"]
        for row in validation
    )
    etrs_wins_distance = sum(
        row["metrics"]["epsg25830"]["centroid_distance_m"]
        < row["metrics"]["epsg23030"]["centroid_distance_m"]
        for row in validation
    )
    evidence = {
        "candidate_rows": len(matched),
        "validation_pairs": len(validation),
        "pair_definition": "Mismo año, candidato espacial a <=5 km, IoU máximo >=0,20 bajo alguna hipótesis y razón de áreas geométricas 0,25–4; no implica identidad.",
        "hypotheses": hypothesis_summary,
        "paired_wins": {
            "iou_epsg23030": ed50_wins_iou,
            "iou_epsg25830": etrs_wins_iou,
            "iou_ties": len(validation) - ed50_wins_iou - etrs_wins_iou,
            "centroid_distance_epsg23030": ed50_wins_distance,
            "centroid_distance_epsg25830": etrs_wins_distance,
            "centroid_distance_ties": len(validation) - ed50_wins_distance - etrs_wins_distance,
        },
        "hypothesis_centroid_offset_m": distribution(hypothesis_offset),
        "limitations": [
            "ESFire30 Causes no publica fecha, municipio ni ID de evento; el matching ICV usa año y geometría como control de datum, no identidad.",
            "IoU, áreas y distancias se calculan en EPSG:25830; las hipótesis solo difieren en aplicar o no la transformación de datum ED50→ETRS89.",
            "La precisión de los perímetros ICV cambia por periodo y no es verdad terreno homogénea.",
        ],
    }
    return evidence, validation


def load_egif(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    gif_rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            location = row["location_original"]
            sheet_grid = None
            if location.get("map_sheet") and location.get("grid"):
                sheet_grid = f"{location['map_sheet']}{location['grid']}"
            item = {
                "source_record_id": row["source_record_id"],
                "year": row["year"],
                "province": row["province"],
                "municipality": row["municipality"],
                "municipality_codine": row["municipality_codine"],
                "detection_date": row["detection_date"],
                "forest_area_ha": row["reported_forest_area_ha"],
                "total_area_ha": row["reported_total_area_ha"],
                "sheet_grid": sheet_grid,
                "is_gif": row["is_gif_ge_500_ha"],
            }
            if item["year"] in PRE1993_YEARS:
                all_rows.append(item)
            if item["is_gif"]:
                gif_rows.append(item)
    if len(gif_rows) != EXPECTED_GIF:
        raise ValueError(f"Se esperaban {EXPECTED_GIF} partes GIF; se obtuvieron {len(gif_rows)}")
    return all_rows, gif_rows


def match_egif(
    features: list[dict[str, Any]],
    egif_rows: list[dict[str, Any]],
    gif_rows: list[dict[str, Any]],
    boundaries: dict[str, Any],
) -> dict[str, Any]:
    by_year_grid: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    feature_lookup = {feature["source_record_id"]: feature for feature in features if feature["year"] in PRE1993_YEARS}
    for feature in feature_lookup.values():
        by_year_grid[(feature["year"], feature["id_cuad"])].append(feature)

    matrix: list[dict[str, Any]] = []
    for row in gif_rows:
        candidates = by_year_grid.get((row["year"], row["sheet_grid"]), []) if row["sheet_grid"] else []
        evaluated = []
        for feature in candidates:
            reference_area = row["total_area_ha"] if row["total_area_ha"] is not None else row["forest_area_ha"]
            relative_difference = (
                abs(feature["area_ha"] - reference_area) / max(reference_area, 1e-9)
                if reference_area is not None
                else None
            )
            municipality_compatible = None
            municipality_code = row["municipality_codine"]
            if municipality_code and str(municipality_code) in boundaries["prepared_municipalities_ed50"]:
                municipality_compatible = boundaries["prepared_municipalities_ed50"][str(municipality_code)].intersects(
                    feature["geometry"]
                )
            evaluated.append(
                {
                    "source_record_id": feature["source_record_id"],
                    "geometry_id": feature["geometry_id"],
                    "area_ha": feature["area_ha"],
                    "relative_area_difference_total": relative_difference,
                    "province_compatible": feature["primary_province"].replace("ó", "o") == row["province"].replace("ó", "o"),
                    "municipality_compatible": municipality_compatible,
                }
            )
        evaluated.sort(
            key=lambda item: (
                item["municipality_compatible"] is not True,
                item["relative_area_difference_total"] if item["relative_area_difference_total"] is not None else math.inf,
            )
        )
        control = CONTROL_RECORDS.get(row["source_record_id"])
        expected = control.get("expected_esfire_id") if control else None
        expected_present = expected is not None and any(item["source_record_id"] == expected for item in evaluated)
        best = evaluated[0] if evaluated else None
        if expected_present and row["source_record_id"] in {"1986461220", "1991460176", "1991460188"}:
            status = "strong"
        elif best and (best["municipality_compatible"] is True or best["relative_area_difference_total"] <= 0.50):
            status = "possible"
        elif best:
            status = "weak"
        else:
            status = "none"
        matrix.append(
            {
                **row,
                "status": status,
                "control_label": control.get("label") if control else None,
                "expected_control_candidate_present": expected_present,
                "candidates": evaluated,
            }
        )

    best_relative = [
        row["candidates"][0]["relative_area_difference_total"]
        for row in matrix
        if row["candidates"] and row["candidates"][0]["relative_area_difference_total"] is not None
    ]
    all_same_grid_rel = [
        candidate["relative_area_difference_total"]
        for row in matrix
        for candidate in row["candidates"]
        if candidate["relative_area_difference_total"] is not None
    ]
    statuses = Counter(row["status"] for row in matrix)
    return {
        "administrative_records_1985_1992": len(egif_rows),
        "gif_parts": len(matrix),
        "confirmed": 0,
        "status_counts": {state: statuses.get(state, 0) for state in ("strong", "possible", "weak", "none")},
        "with_same_year_grid_candidate": sum(bool(row["candidates"]) for row in matrix),
        "best_candidate_relative_area_difference": distribution(best_relative),
        "all_same_year_grid_relative_area_difference": distribution(all_same_grid_rel),
        "matrix": matrix,
        "identity_warning": "Id_cuad y causa del producto ESFire30 Causes ya incorporan información derivada de EGIF; no son evidencia independiente ni permiten confirmed.",
    }


def estimate_web(features: list[dict[str, Any]], transforms: dict[str, Any]) -> dict[str, Any]:
    from shapely.geometry import mapping
    from shapely.ops import transform

    blobs: list[bytes] = []
    original_vertices = 0
    simplified_vertices = Counter()
    collapsed = Counter()
    tolerances_m = (10, 30, 60)
    for feature in features:
        if feature["year"] not in PRE1993_YEARS:
            continue
        geometry = transform(transforms["ed50_to_4326"].transform, feature["geometry"])
        compact = {
            "type": "Feature",
            "geometry": mapping(geometry),
            "properties": {
                "geometry_id": feature["geometry_id"],
                "year": feature["year"],
                "area_ha": feature["area_ha"],
                "source": "esfire30",
                "quality": "B_DOCUMENTED_REMOTE_SENSING",
            },
        }
        blobs.append(json.dumps(compact, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        original_vertices += feature["vertices"]
        for tolerance in tolerances_m:
            simplified = feature["geometry"].simplify(tolerance, preserve_topology=True)
            if simplified.is_empty:
                collapsed[tolerance] += 1
            if simplified.geom_type == "Polygon":
                simplified_vertices[tolerance] += len(simplified.exterior.coords) + sum(
                    len(ring.coords) for ring in simplified.interiors
                )
            elif simplified.geom_type == "MultiPolygon":
                simplified_vertices[tolerance] += sum(
                    len(part.exterior.coords) + sum(len(ring.coords) for ring in part.interiors)
                    for part in simplified.geoms
                )
    geojson = b'{"type":"FeatureCollection","features":[' + b",".join(blobs) + b"]}"
    return {
        "features": len(blobs),
        "vertices_original": original_vertices,
        "geojson_bytes": len(geojson),
        "geojson_gzip_bytes": len(gzip.compress(geojson, compresslevel=9, mtime=0)),
        "simplification_diagnostic": {
            str(tolerance): {
                "vertices": simplified_vertices[tolerance],
                "reduction_percent": round(100 * (1 - simplified_vertices[tolerance] / original_vertices), 3),
                "collapsed": collapsed[tolerance],
            }
            for tolerance in tolerances_m
        },
        "leaflet_assessment": "710 polígonos y menos de 100.000 vértices originales son compatibles con carga diferida Leaflet+Canvas; no justifican PMTiles.",
    }


def write_diagnostic(
    path: Path,
    features: list[dict[str, Any]],
    transforms: dict[str, Any],
    quality_eligible: bool,
) -> dict[str, Any]:
    from shapely.geometry import mapping
    from shapely.ops import transform

    if not quality_eligible:
        return {"written": False, "reason": "Los criterios CRS/metodología/licencia/topología no permiten derivado."}
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    count = 0
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        for feature in features:
            if feature["year"] not in PRE1993_YEARS:
                continue
            derived = transform(transforms["ed50_to_4326"].transform, feature["geometry"])
            row = {
                "source_record_id": feature["source_record_id"],
                "geometry_id": feature["geometry_id"],
                "source": "ESFire30_Causes_Zenodo_18449006",
                "source_year": feature["year"],
                "source_record_index": feature["record_index"],
                "source_id_cuad": feature["id_cuad"],
                "source_area_ha": feature["area_ha"],
                "source_geometry_checksum_sha256": feature["geometry_checksum_sha256"],
                "geometry_original_crs": "EPSG:23030",
                "geometry_original": mapping(feature["geometry"]),
                "geometry_epsg4326": mapping(derived),
                "geometry_quality": "B_DOCUMENTED_REMOTE_SENSING",
                "geometry_quality_status": "provisional_cv_4_2_diagnostic",
                "episode_identity_status": "unresolved_polygon_event_claim_not_verified",
                "topology_valid": feature["is_valid"],
                "topology_reason": feature["validity_reason"],
                "provenance": {
                    "doi": ZENODO_DOI,
                    "snapshot_sha256": EXPECTED_ZIP_SHA256,
                    "pipeline": PIPELINE_VERSION,
                    "transformation": transforms["metadata"]["selected_operation_4326"],
                    "grid_sha256": EXPECTED_GRID_SHA256,
                },
            }
            serialized = json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
            stream.write(serialized)
            digest.update(serialized)
            count += 1
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    return {
        "written": True,
        "path_local_ignored": str(path.relative_to(ROOT)),
        "records": count,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "published": False,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    if args.zip.stat().st_size != EXPECTED_ZIP_BYTES:
        raise ValueError("Tamaño ZIP inesperado")
    if sha256_file(args.zip) != EXPECTED_ZIP_SHA256 or md5_file(args.zip) != EXPECTED_ZIP_MD5:
        raise ValueError("Checksum ZIP inesperado")
    if sha256_file(args.readme) != EXPECTED_README_SHA256:
        raise ValueError("Checksum README inesperado")
    zenodo = json.loads(args.zenodo.read_text(encoding="utf-8"))
    if zenodo["id"] != ZENODO_RECORD or zenodo["doi"] != ZENODO_DOI:
        raise ValueError("Metadatos Zenodo inesperados")

    transforms = prepare_transformations(args.grid)
    boundaries = load_boundaries(args.boundary, transforms)
    archive, features, national_topology = inspect_archive(args.zip, boundaries)
    if archive["total_records"] != EXPECTED_TOTAL:
        raise ValueError(f"Total ESFire30 inesperado: {archive['total_records']}")
    cv_summary = cv_pre1993_summary(features)
    if cv_summary["polygons"] != EXPECTED_GVA_PRE1993:
        raise ValueError(f"Selección CV pre-1993 inesperada: {cv_summary['polygons']}")

    icv_by_year, icv_load = load_icv(args.icv_geometries, args.icv_fires, transforms)
    crs_comparison, icv_pairs = compare_crs(features, icv_by_year, transforms, boundaries)
    ed50_iou = crs_comparison["hypotheses"]["epsg23030"]["iou"]["median"] or 0
    etrs_iou = crs_comparison["hypotheses"]["epsg25830"]["iou"]["median"] or 0
    wins = crs_comparison["paired_wins"]
    crs_resolved = (
        crs_comparison["validation_pairs"] >= 30
        and wins["iou_epsg23030"] > wins["iou_epsg25830"] * 1.5
        and ed50_iou > etrs_iou
        and wins["centroid_distance_epsg23030"] > wins["centroid_distance_epsg25830"] * 1.5
    )

    egif_rows, gif_rows = load_egif(args.egif)
    egif_match = match_egif(features, egif_rows, gif_rows, boundaries)
    web = estimate_web(features, transforms)

    methodology_sufficient = True
    license_allows = zenodo["metadata"]["license"]["id"] == "cc-by-4.0"
    topology_usable = (
        cv_summary["polygons"] == EXPECTED_GVA_PRE1993
        and cv_summary["invalid"] / cv_summary["polygons"] <= 0.05
        and national_topology["null_shapes"] == 0
        and national_topology["empty"] == 0
    )
    quality_eligible = crs_resolved and methodology_sufficient and license_allows and topology_usable
    diagnostic = write_diagnostic(args.diagnostic, features, transforms, quality_eligible) if args.write_diagnostic else {"written": False, "reason": "Opción --write-diagnostic no solicitada"}

    return {
        "schema_version": PIPELINE_VERSION,
        "generated_from": {
            "zenodo_record": ZENODO_RECORD,
            "doi": ZENODO_DOI,
            "version": "v1",
            "publication_date": zenodo["metadata"]["publication_date"],
            "record_created": zenodo["created"],
            "record_modified": zenodo["updated"],
            "acquired_at": ACQUIRED_AT,
            "authors": zenodo["metadata"]["creators"],
            "license": "CC BY 4.0",
            "files": [
                {
                    "name": args.zip.name,
                    "url": "https://zenodo.org/records/18449006/files/ESFire30_Causes.zip",
                    "bytes": args.zip.stat().st_size,
                    "sha256": EXPECTED_ZIP_SHA256,
                    "md5_provider": EXPECTED_ZIP_MD5,
                    "path_local_ignored": str(args.zip.relative_to(ROOT)),
                },
                {
                    "name": args.readme.name,
                    "url": "https://zenodo.org/records/18449006/files/read_me.txt",
                    "bytes": args.readme.stat().st_size,
                    "sha256": EXPECTED_README_SHA256,
                    "md5_provider": "84ddfd1b96c1de3547fef4a70132f281",
                    "path_local_ignored": str(args.readme.relative_to(ROOT)),
                },
            ],
        },
        "archive_inventory": archive,
        "crs": {
            "readme_claim": "EPSG:25830",
            "prj_claim": "ED50 / UTM zone 30N (EPSG:23030)",
            "zenodo_metadata_claim": None,
            "code_repository_found": False,
            "coordinate_range": archive["coordinate_range_raw"],
            "comparison_with_icv": crs_comparison,
            "resolved": crs_resolved,
            "resolved_crs": "EPSG:23030" if crs_resolved else None,
            "decision": "El .prj y el contraste pareado ICV respaldan EPSG:23030; el README se considera error de metadatos." if crs_resolved else "Contradicción no resuelta; no integrar.",
            "transformation": transforms["metadata"],
        },
        "topology_national_1985_1992": national_topology,
        "gva_1985_1992": cv_summary,
        "icv_validation": {
            "icv_load": icv_load,
            "validation_pair_count": len(icv_pairs),
            "pairs": icv_pairs,
            "identity_status": "diagnostic_spatial_candidate_not_confirmed",
        },
        "egif_validation": egif_match,
        "methodology": {
            "dataset_period_actual": [1985, 2021],
            "paper_claim_period": [1985, 2023],
            "sensor": "Landsat",
            "native_resolution_m": 30,
            "minimum_area_claim_ha": 5,
            "detection": "Algoritmo semiautomático con refinamiento posterior; el artículo primario de ESFire30 se cita como under review y no está incluido en el depósito.",
            "polygon_semantics": "El depósito afirma burned-area event/perimeter; no demuestra que cada feature sea un episodio físico único ni que agrupe todas las manchas de un incendio.",
            "cause_assignment": "Method=1: similitud de superficie con EGIF dentro de la cuadrícula; Method=2: causa mayoritaria de la cuadrícula; predicted_: Random Forest.",
            "validation_documented": "El artículo de causas documenta armonización y análisis comparativo, pero no publica una validación geométrica exhaustiva del producto base ESFire30.",
            "primary_sources": [
                {"title": "ESFire30 Causes", "url": "https://zenodo.org/records/18449006", "sections": "Description, Files, Rights, Technical metadata"},
                {"title": "Inferring Wildfire Ignition Causes in Spain Using Machine Learning and Explainable AI", "url": "https://doi.org/10.3390/fire9040138", "sections": "2.2, 2.3, Data Availability, Conclusions"},
            ],
        },
        "identity": {
            "source_stable_id_available": False,
            "id_cuad_unique": False,
            "year_unique": False,
            "source_record_id_rule": "esfire30:v1:<year>:<zero-based DBF/SHP record index>",
            "geometry_id_rule": "esfire30:geometry:v1:<year>:<record index>:<first 16 chars raw geometry SHA-256>",
            "episode_identity_status": "unresolved_polygon_event_claim_not_verified",
            "warning": "El orden de registro es localizador estable solo para el snapshot v1, no identificador publicado por el proveedor.",
        },
        "quality_decision": {
            "crs_resolved": crs_resolved,
            "topology_usable": topology_usable,
            "methodology_sufficient_for_remote_sensing_provenance": methodology_sufficient,
            "license_allows_derivative": license_allows,
            "eligible_as_B_DOCUMENTED_REMOTE_SENSING": quality_eligible,
            "conditions": [
                "Atribuir Zenodo v1 y DOI 10.5281/zenodo.18449006 bajo CC BY 4.0.",
                "Declarar reproyección, selección territorial y cualquier simplificación.",
                "Mantener source_record_id/geometry_id/provenance y coordenadas originales EPSG:23030.",
                "No presentar los polígonos como oficiales ni como episodios EGIF confirmados.",
                "Mantener geometrías inválidas sin reparar o excluirlas explícitamente en producción con informe.",
                "Solicitar aclaración escrita del error EPSG:25830 y del artículo base ESFire30 aún no publicado.",
            ],
        },
        "license": {
            "dataset": "CC BY 4.0",
            "redistribution_allowed": True,
            "transformation_allowed": True,
            "attribution_required": True,
            "source_imagery_license_scope": "La licencia del derivado ESFire30 no relicencia las imágenes Landsat originales; publicar el vector derivado no exige redistribuir escenas.",
            "proposed_attribution": "ESFire30 Causes, Ochoa, Chuvieco, Rodrigues y Franquesa (2026), versión v1, CC BY 4.0, DOI 10.5281/zenodo.18449006. Datos transformados para el Atlas mediante selección territorial, reproyección a EPSG:4326, selección de atributos y, cuando proceda, simplificación geométrica.",
        },
        "web_estimate": web,
        "diagnostic_derivative": diagnostic,
        "publication": {"published": False, "frontend_modified": False, "public_profile_modified": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--zenodo", type=Path, default=DEFAULT_ZENODO)
    parser.add_argument("--grid", type=Path, default=DEFAULT_GRID)
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--icv-geometries", type=Path, default=DEFAULT_ICV_GEOMETRIES)
    parser.add_argument("--icv-fires", type=Path, default=DEFAULT_ICV_FIRES)
    parser.add_argument("--egif", type=Path, default=DEFAULT_EGIF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--diagnostic", type=Path, default=DEFAULT_DIAGNOSTIC)
    parser.add_argument("--write-diagnostic", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build(args)
    if args.check:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        normalized = json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False))
        if existing != normalized:
            raise SystemExit("La auditoría versionada no coincide con la regeneración")
        print(f"OK: {args.output}")
        return 0
    atomic_json(args.output, result)
    print(
        f"Escrito {args.output}: {result['archive_inventory']['total_records']} polígonos; "
        f"CV 1985–1992={result['gva_1985_1992']['polygons']}; "
        f"CRS={result['crs']['resolved_crs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
