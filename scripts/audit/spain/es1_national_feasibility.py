#!/usr/bin/env python3
"""Mediciones reproducibles para ES-1 sin generar assets de producción.

El script tiene dos recorridos independientes:

``egif-counts``
    Consulta solamente los recuentos del buscador público EGIF. Lee la
    respuesta hasta encontrar ``hddPifTotal`` y cierra la conexión; no exporta
    partes ni descarga XML.

``esfire30``
    Inventaría el snapshot ESFire30 v1 preservado localmente y estima tres
    niveles GeoJSON nacionales. Los bytes GeoJSON se calculan por streaming y
    no se conserva ningún derivado cartográfico.

Las salidas diagnósticas deben escribirse bajo ``data/derived/`` o ``/tmp``;
ambas ubicaciones quedan fuera del bundle público.
"""

from __future__ import annotations

import argparse
import gc
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
EGIF_SEARCH_URL = "https://servicio.mapa.gob.es/incendios/Search/PublicoPag"
ESFIRE30_ZIP = ROOT / "data/raw/esfire30/18449006/ESFire30_Causes.zip"
ESFIRE30_GRID = ROOT / "data/raw/esfire30/proj-grids/es_ign_SPED2ETV2.tif"
ESFIRE30_SHA256 = "150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8"
ESFIRE30_GRID_SHA256 = "61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961"
ESFIRE30_YEARS = tuple(range(1985, 2022))
ESFIRE30_EXPECTED = 119_498
COUNT_PATTERN = re.compile(rb'id="hddPifTotal"\s+value="([0-9]+)"')
VISIBLE_COUNT_PATTERN = re.compile(
    rb"<strong\s*>\s*([0-9.]+)\s*</strong>\s*PIFs encontrados",
    re.IGNORECASE,
)


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def egif_count_url(year_from: int, year_to: int) -> str:
    criteria = (
        f"soypm=0&AD={year_from}&AH={year_to}&ZIF=&TI=&AEP=-1"
    )
    return EGIF_SEARCH_URL + "?" + urllib.parse.urlencode(
        {
            "NumPag": 10,
            "sBusqueda": criteria,
            "sortOrder": "SuperfTotal",
        }
    )


def fetch_egif_count(
    year_from: int,
    year_to: int,
    *,
    timeout: float,
    attempts: int,
) -> int:
    """Obtiene un total sin descargar la página completa del buscador."""
    url = egif_count_url(year_from, year_to)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "atlas-incendios-es1/1"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = bytearray()
                while len(payload) < 256_000:
                    block = response.read(16_384)
                    if not block:
                        break
                    payload.extend(block)
                    match = COUNT_PATTERN.search(payload)
                    if match:
                        return int(match.group(1))
                    visible = VISIBLE_COUNT_PATTERN.search(payload)
                    if visible:
                        return int(visible.group(1).replace(b".", b""))
            raise RuntimeError(
                f"EGIF no devolvió hddPifTotal para {year_from}-{year_to}"
            )
        except Exception as exc:  # reintento de red, HTTP o respuesta truncada
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(min(2**attempt, 8))
    raise RuntimeError(
        f"No se pudo obtener el recuento EGIF {year_from}-{year_to}: {last_error}"
    )


def build_egif_counts(args: argparse.Namespace) -> dict[str, Any]:
    rows = []
    for year in range(args.year_from, args.year_to + 1):
        count = fetch_egif_count(
            year,
            year,
            timeout=args.timeout,
            attempts=args.attempts,
        )
        rows.append({"year": year, "records": count})
        print(f"EGIF {year}: {count}", flush=True)
    interval_count = fetch_egif_count(
        args.year_from,
        args.year_to,
        timeout=args.timeout,
        attempts=args.attempts,
    )
    annual_sum = sum(row["records"] for row in rows)
    return {
        "schema_version": 1,
        "audit": "ES-1 national EGIF count-only inventory",
        "retrieved_at": utc_now(),
        "source": {
            "title": "Estadística General de Incendios Forestales (EGIF)",
            "provider": "Ministerio para la Transición Ecológica y el Reto Demográfico",
            "url": EGIF_SEARCH_URL,
            "method": "Public search result count; no XML export",
        },
        "scope": {"year_from": args.year_from, "year_to": args.year_to},
        "by_year": rows,
        "annual_sum": annual_sum,
        "interval_count": interval_count,
        "validation": {
            "annual_sum_matches_interval": annual_sum == interval_count,
            "status": "complete" if annual_sum == interval_count else "mismatch",
        },
    }


def archive_reader(archive: zipfile.ZipFile, year: int):
    import shapefile

    base = f"RF_jja/predicciones_{year}"
    return shapefile.Reader(
        shp=io.BytesIO(archive.read(base + ".shp")),
        shx=io.BytesIO(archive.read(base + ".shx")),
        dbf=io.BytesIO(archive.read(base + ".dbf")),
        encoding="utf-8",
    )


class GeoJsonMeasure:
    """Cuenta bytes raw/gzip de una FeatureCollection escrita por streaming."""

    def __init__(self, output: Path | None = None) -> None:
        self.raw_bytes = 0
        self._sink = io.BytesIO()
        self._gzip = gzip.GzipFile(fileobj=self._sink, mode="wb", mtime=0)
        self._output = None
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            self._output = output.open("wb")
        self._first = True
        self.write(b'{"type":"FeatureCollection","features":[')

    def write(self, value: bytes) -> None:
        self.raw_bytes += len(value)
        self._gzip.write(value)
        if self._output is not None:
            self._output.write(value)

    def add(self, feature: dict[str, Any]) -> None:
        if not self._first:
            self.write(b",")
        self._first = False
        self.write(
            json.dumps(
                feature,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )

    def finish(self) -> dict[str, int]:
        self.write(b"]}")
        self._gzip.close()
        if self._output is not None:
            self._output.close()
        return {"raw_bytes": self.raw_bytes, "gzip_bytes": len(self._sink.getvalue())}


def geometry_vertices(geometry: Any) -> int:
    if geometry.geom_type == "Polygon":
        return len(geometry.exterior.coords) + sum(
            len(ring.coords) for ring in geometry.interiors
        )
    if geometry.geom_type == "MultiPolygon":
        return sum(geometry_vertices(part) for part in geometry.geoms)
    return 0


def transformed_mapping(geometry: Any, transformer: Any) -> dict[str, Any]:
    from shapely.geometry import mapping
    from shapely.ops import transform

    return mapping(transform(transformer.transform, geometry))


def load_ign_units(path: Path, transformer: Any, simplify_m: float) -> list[dict[str, Any]]:
    """Carga solo CCAA/provincias oficiales y libera el GeoJSON detallado."""
    from shapely.geometry import shape
    from shapely.ops import transform

    payload = json.loads(path.read_text(encoding="utf-8"))
    units = []
    for feature in payload["features"]:
        properties = feature["properties"]
        nationalcode = str(properties.get("nationalcode") or "")
        # ESFire30 v1 se limita a España peninsular. 04/05/18/19 son Illes
        # Balears, Canarias, Ceuta y Melilla; 20 son territorios no asociados.
        if len(nationalcode) < 6 or nationalcode[2:4] in {"04", "05", "18", "19", "20"}:
            continue
        geometry = transform(transformer.transform, shape(feature["geometry"]))
        if simplify_m:
            geometry = geometry.simplify(simplify_m, preserve_topology=True)
        units.append(
            {
                "name": properties["nameunit"],
                "nationalcode": nationalcode,
                "autonomous_community_code": nationalcode[2:4],
                "province_code": nationalcode[4:6],
                "nuts2": properties.get("codnut2"),
                "geometry": geometry,
            }
        )
    del payload
    gc.collect()
    return units


def temporal_block(year: int) -> str:
    for start, end in ((1985, 1989), (1990, 1999), (2000, 2009), (2010, 2019), (2020, 2021)):
        if start <= year <= end:
            return f"{start}-{end}"
    raise ValueError(year)


def build_esfire30_territories(args: argparse.Namespace) -> dict[str, Any]:
    import pyproj
    from pyproj.transformer import AreaOfInterest, TransformerGroup
    from shapely.geometry import shape
    from shapely.strtree import STRtree

    if sha256_file(args.zip) != ESFIRE30_SHA256:
        raise RuntimeError("Checksum inesperado para ESFire30 v1")
    if sha256_file(ESFIRE30_GRID) != ESFIRE30_GRID_SHA256:
        raise RuntimeError("Checksum inesperado para la rejilla IGN ED50")
    pyproj.datadir.append_data_dir(str(ESFIRE30_GRID.parent))
    group = TransformerGroup(
        "EPSG:4326",
        "EPSG:23030",
        always_xy=True,
        area_of_interest=AreaOfInterest(-10.0, 35.0, 4.5, 44.5),
    )
    transformer = next(
        (item for item in group.transformers if "ED50 to WGS 84 (41)" in item.description),
        None,
    )
    if transformer is None:
        raise RuntimeError("No está disponible la inversa ED50 to WGS 84 (41)")

    ccaa = load_ign_units(args.ccaa, transformer, args.boundary_simplify)
    provinces = load_ign_units(args.provinces, transformer, args.boundary_simplify)
    ccaa_tree = STRtree([unit["geometry"] for unit in ccaa])
    province_tree = STRtree([unit["geometry"] for unit in provinces])
    primary_ccaa = Counter()
    primary_province = Counter()
    relation_ccaa = Counter()
    relation_province = Counter()
    by_year_ccaa: dict[int, Counter[str]] = defaultdict(Counter)
    by_year_province: dict[int, Counter[str]] = defaultdict(Counter)
    by_ccaa_block = Counter()
    by_province_block = Counter()
    multiple_ccaa = 0
    multiple_province = 0
    without_ccaa = 0
    without_province = 0
    total = 0

    def hits(tree: STRtree, units: list[dict[str, Any]], geometry: Any) -> list[int]:
        return [
            int(index)
            for index in tree.query(geometry, predicate="intersects")
            if geometry.intersection(units[int(index)]["geometry"]).area > 0
        ]

    with zipfile.ZipFile(args.zip) as archive:
        for year in ESFIRE30_YEARS:
            reader = archive_reader(archive, year)
            for shape_record in reader.iterShapeRecords():
                geometry = shape(shape_record.shape.__geo_interface__)
                total += 1
                ccaa_hits = hits(ccaa_tree, ccaa, geometry)
                province_hits = hits(province_tree, provinces, geometry)
                if not ccaa_hits:
                    without_ccaa += 1
                else:
                    multiple_ccaa += int(len(ccaa_hits) > 1)
                    winner = max(
                        ccaa_hits,
                        key=lambda index: geometry.intersection(ccaa[index]["geometry"]).area,
                    )
                    code = ccaa[winner]["autonomous_community_code"]
                    primary_ccaa[code] += 1
                    by_year_ccaa[year][code] += 1
                    by_ccaa_block[(code, temporal_block(year))] += 1
                    for index in ccaa_hits:
                        relation_ccaa[ccaa[index]["autonomous_community_code"]] += 1
                if not province_hits:
                    without_province += 1
                else:
                    multiple_province += int(len(province_hits) > 1)
                    winner = max(
                        province_hits,
                        key=lambda index: geometry.intersection(provinces[index]["geometry"]).area,
                    )
                    code = provinces[winner]["province_code"]
                    primary_province[code] += 1
                    by_year_province[year][code] += 1
                    by_province_block[(code, temporal_block(year))] += 1
                    for index in province_hits:
                        relation_province[provinces[index]["province_code"]] += 1
            print(f"ESFire30 territorios {year}: {len(reader)}", flush=True)

    if total != ESFIRE30_EXPECTED:
        raise RuntimeError(f"ESFire30: {total} != {ESFIRE30_EXPECTED}")
    ccaa_names = {unit["autonomous_community_code"]: unit["name"] for unit in ccaa}
    province_names = {unit["province_code"]: unit["name"] for unit in provinces}
    return {
        "schema_version": 1,
        "audit": "ES-1 ESFire30 territory relation benchmark",
        "measured_at": utc_now(),
        "source": {
            "esfire30_sha256": ESFIRE30_SHA256,
            "territories": "IGN/CNIG OGC API Features administrativeunit",
            "ccaa_url": "https://api-features.ign.es/collections/administrativeunit/items?f=json&limit=100&nationallevelname=Comunidad%20aut%C3%B3noma",
            "province_url": "https://api-features.ign.es/collections/administrativeunit/items?f=json&limit=100&nationallevelname=Provincia",
            "boundary_simplify_m_diagnostic": args.boundary_simplify,
            "transformation": transformer.description,
            "grid_sha256": ESFIRE30_GRID_SHA256,
        },
        "records": total,
        "primary_autonomous_community": {
            code: {"name": ccaa_names.get(code), "records": primary_ccaa[code]}
            for code in sorted(primary_ccaa)
        },
        "all_autonomous_community_relations": dict(sorted(relation_ccaa.items())),
        "primary_province": {
            code: {"name": province_names.get(code), "records": primary_province[code]}
            for code in sorted(primary_province)
        },
        "all_province_relations": dict(sorted(relation_province.items())),
        "by_year_and_autonomous_community": {
            str(year): dict(sorted(counts.items())) for year, counts in sorted(by_year_ccaa.items())
        },
        "by_year_and_province": {
            str(year): dict(sorted(counts.items())) for year, counts in sorted(by_year_province.items())
        },
        "partition_feature_counts": {
            "autonomous_community_x_block": {
                f"{code}:{block}": count
                for (code, block), count in sorted(by_ccaa_block.items())
            },
            "province_x_block": {
                f"{code}:{block}": count
                for (code, block), count in sorted(by_province_block.items())
            },
        },
        "cross_boundary": {
            "multiple_autonomous_communities": multiple_ccaa,
            "multiple_provinces": multiple_province,
            "without_autonomous_community": without_ccaa,
            "without_province": without_province,
        },
        "semantics": {
            "primary_assignment": "largest positive intersection area; diagnostic partition only",
            "relations": "all positive-area intersections; no clipping and no geometry duplication",
        },
    }


def build_esfire30(args: argparse.Namespace) -> dict[str, Any]:
    import pyproj
    from pyproj.transformer import AreaOfInterest, TransformerGroup
    from shapely.geometry import shape

    if sha256_file(args.zip) != ESFIRE30_SHA256:
        raise RuntimeError("Checksum inesperado para ESFire30 v1")
    if sha256_file(ESFIRE30_GRID) != ESFIRE30_GRID_SHA256:
        raise RuntimeError("Checksum inesperado para la rejilla IGN ED50")
    pyproj.datadir.append_data_dir(str(ESFIRE30_GRID.parent))

    group = TransformerGroup(
        "EPSG:23030",
        "EPSG:4326",
        always_xy=True,
        area_of_interest=AreaOfInterest(-10.0, 35.0, 4.5, 44.5),
    )
    transformer = next(
        (item for item in group.transformers if "ED50 to WGS 84 (41)" in item.description),
        None,
    )
    if transformer is None:
        raise RuntimeError("No está disponible la operación ED50 to WGS 84 (41)")
    lods = {
        "local": 0.0,
        "regional": float(args.regional_tolerance),
        "overview": float(args.overview_tolerance),
    }
    measures = {
        name: GeoJsonMeasure(args.write_overview if name == "overview" else None)
        for name in lods
    }
    lod_vertices = Counter()
    lod_empty = Counter()
    by_year = Counter()
    geometry_types = Counter()
    original_vertices = 0
    source_area_ha = 0.0
    total = 0
    started = time.perf_counter()

    with zipfile.ZipFile(args.zip) as archive:
        for year in ESFIRE30_YEARS:
            reader = archive_reader(archive, year)
            for index, shape_record in enumerate(reader.iterShapeRecords()):
                geometry = shape(shape_record.shape.__geo_interface__)
                attributes = shape_record.record.as_dict()
                by_year[year] += 1
                total += 1
                original_vertices += len(shape_record.shape.points)
                geometry_types[geometry.geom_type] += 1
                source_area_ha += float(attributes["area_ha"])
                fingerprint = hashlib.sha256(
                    f"v1|{year}|{index}|{attributes.get('area_ha')}|{attributes.get('Id_cuad')}".encode()
                ).hexdigest()[:24]
                for name, tolerance in lods.items():
                    candidate = (
                        geometry
                        if tolerance == 0
                        else geometry.simplify(tolerance, preserve_topology=True)
                    )
                    if candidate.is_empty:
                        lod_empty[name] += 1
                        continue
                    lod_vertices[name] += geometry_vertices(candidate)
                    measures[name].add(
                        {
                            "type": "Feature",
                            "id": f"esfire30:v1:{fingerprint}",
                            "properties": {
                                "source": "esfire30",
                                "year": year,
                                "area_ha": float(attributes["area_ha"]),
                            },
                            "geometry": transformed_mapping(candidate, transformer),
                        }
                    )
            print(f"ESFire30 {year}: {len(reader)}", flush=True)

    if total != ESFIRE30_EXPECTED:
        raise RuntimeError(f"ESFire30: {total} != {ESFIRE30_EXPECTED}")
    lod_results = {}
    for name, measure in measures.items():
        size = measure.finish()
        lod_results[name] = {
            "tolerance_m": lods[name],
            "vertices": lod_vertices[name],
            "vertex_reduction_percent": round(
                (1 - lod_vertices[name] / original_vertices) * 100, 3
            ),
            "empty_or_collapsed": lod_empty[name],
            **size,
        }
    return {
        "schema_version": 1,
        "audit": "ES-1 whole ESFire30 diagnostic measurement",
        "measured_at": utc_now(),
        "source": {
            "snapshot": "ESFire30 Causes v1",
            "doi": "10.5281/zenodo.18449006",
            "zip": str(args.zip.relative_to(ROOT)),
            "sha256": ESFIRE30_SHA256,
            "source_crs": "EPSG:23030",
            "transformation": transformer.description,
            "transformation_accuracy_m": transformer.accuracy,
            "grid_sha256": ESFIRE30_GRID_SHA256,
        },
        "records": total,
        "years": [min(ESFIRE30_YEARS), max(ESFIRE30_YEARS)],
        "by_year": {str(year): by_year[year] for year in ESFIRE30_YEARS},
        "geometry_types": dict(sorted(geometry_types.items())),
        "source_area_ha_sum": round(source_area_ha, 6),
        "original_vertices": original_vertices,
        "zip_bytes": args.zip.stat().st_size,
        "lods": lod_results,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "limitations": [
            "GeoJSON estimates contain production-like minimal properties but are not production assets.",
            "No autonomous-community or province assignment is made by this subcommand.",
            "No vector-tile archive is generated in ES-1.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    egif = subparsers.add_parser("egif-counts")
    egif.add_argument("--year-from", type=int, default=1968)
    egif.add_argument("--year-to", type=int, default=2025)
    egif.add_argument("--timeout", type=float, default=45)
    egif.add_argument("--attempts", type=int, default=3)
    egif.add_argument("--output", type=Path, required=True)

    esfire = subparsers.add_parser("esfire30")
    esfire.add_argument("--zip", type=Path, default=ESFIRE30_ZIP)
    esfire.add_argument("--regional-tolerance", type=float, default=30)
    esfire.add_argument("--overview-tolerance", type=float, default=100)
    esfire.add_argument("--write-overview", type=Path)
    esfire.add_argument("--output", type=Path, required=True)

    territories = subparsers.add_parser("esfire30-territories")
    territories.add_argument("--zip", type=Path, default=ESFIRE30_ZIP)
    territories.add_argument("--ccaa", type=Path, required=True)
    territories.add_argument("--provinces", type=Path, required=True)
    territories.add_argument("--boundary-simplify", type=float, default=5.0)
    territories.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "egif-counts":
        result = build_egif_counts(args)
    elif args.command == "esfire30":
        result = build_esfire30(args)
    else:
        result = build_esfire30_territories(args)
    write_json(args.output, result)
    if result.get("validation", {}).get("status") == "mismatch":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
