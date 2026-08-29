#!/usr/bin/env python3
"""Audita BDLJE municipal sin integrar el nivel municipal en el runtime.

La adquisición de inventario usa ``skipGeometry=true`` y es ligera. Las
geometrías se consultan solo para provincias de muestra mediante sus bounds
BDLJE ya adquiridos. ``--all`` queda preparado para una adquisición nacional
externa, reanudable por páginas, pero no debe ejecutarse durante ES-4C2A3A.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "data/territories/spain/territories-2026-01-01.json"
PROVINCE_SOURCE = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/province-level.geojson"
RAW_DIR = ROOT / "data/raw/territories/spain/ign-ogc-2026-08-26/municipalities"
OUTPUT = ROOT / "data/audit/territories/es4c2a3a_municipalities.json"
API_URL = "https://api-features.ign.es/collections/administrativeunit/items"
SOURCE_URL = f"{API_URL}?f=json&limit=1000&nationallevelname=Municipio"
SOURCE_RETRIEVED_AT = "2026-08-29"
SAMPLE_PROVINCES = ("03", "46", "32", "41", "09", "17", "01", "35", "38", "07")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def gzip_bytes(value: bytes) -> int:
    return len(gzip.compress(value, mtime=0))


def fetch_json(params: dict[str, Any]) -> dict[str, Any]:
    url = f"{API_URL}?{urlencode(params)}"
    with urlopen(url, timeout=90) as response:  # nosec B310: official static endpoint
        return json.loads(response.read().decode("utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def municipal_snapshot(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_json(path)["territories"]
    municipalities = {row["official_code"]: row for row in rows if row.get("territory_type") == "municipality"}
    if len(municipalities) != 8132:
        raise ValueError(f"ES-2 expected 8132 municipalities, got {len(municipalities)}")
    return municipalities


def national_code_parts(value: Any) -> tuple[str, str, str] | None:
    code = str(value or "")
    # BDLJE municipal: 34 + CCAA(2) + provincia/equivalente(2) + INE5.
    if not re.fullmatch(r"34\d{9}", code):
        return None
    return code[2:4], code[4:6], code[6:11]


def inventory_pages(raw_dir: Path, resume: bool) -> list[dict[str, Any]]:
    directory = raw_dir / "inventory-pages"; directory.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    offset = 0
    matched: int | None = None
    while matched is None or offset < matched:
        target = directory / f"{offset:05d}.json"
        if target.is_file() and resume:
            page = read_json(target)
        else:
            page = fetch_json({"f": "json", "limit": 1000, "offset": offset, "nationallevelname": "Municipio", "skipGeometry": "true"})
            target.write_bytes(canonical_json(page) + b"\n")
        if page.get("numberMatched") is None or page.get("numberReturned") is None:
            raise ValueError("Página OGC municipal sin numberMatched/numberReturned")
        matched = int(page["numberMatched"])
        features = page.get("features") or []
        if not features:
            raise ValueError(f"Página municipal vacía en offset {offset}")
        rows.extend(features)
        offset += len(features)
    if matched != len(rows):
        raise ValueError(f"Inventario municipal incompleto: {len(rows)} != {matched}")
    return rows


def local_artifacts(directory: Path) -> dict[str, Any]:
    files = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix in {".json", ".geojson"})
    rows = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in files]
    return {"files": rows, "bytes": sum(row["bytes"] for row in rows), "sha256_of_file_list": hashlib.sha256(canonical_json(rows)).hexdigest()}


def national_geometry_download(raw_dir: Path, resume: bool) -> dict[str, Any]:
    """Descarga la capa municipal completa en bloques de 100 features.

    Se reserva para una terminal externa: cada página queda inmediatamente en
    disco y ``--resume`` no vuelve a pedir una página válida. La colección
    ensamblada también queda raw e ignorada por Git.
    """
    directory = raw_dir / "geometry-pages"; directory.mkdir(parents=True, exist_ok=True)
    pages = []; offset = 0; matched: int | None = None
    while matched is None or offset < matched:
        target = directory / f"{offset:05d}.json"
        if target.is_file() and resume:
            page = read_json(target)
        else:
            page = fetch_json({"f": "json", "limit": 100, "offset": offset, "nationallevelname": "Municipio"})
            target.write_bytes(canonical_json(page) + b"\n")
        features = page.get("features") or []
        if not features or page.get("numberMatched") is None:
            raise ValueError(f"Página geométrica municipal inválida en offset {offset}")
        matched = int(page["numberMatched"])
        pages.append({"offset": offset, "path": str(target.relative_to(ROOT)), "features": len(features), "bytes": target.stat().st_size, "sha256": sha256(target)})
        offset += len(features)
    if matched != sum(page["features"] for page in pages):
        raise ValueError("Páginas geométricas municipales incompletas")
    output = raw_dir / "municipality-level.geojson"; temporary = output.with_suffix(".geojson.part")
    with temporary.open("wb") as stream:
        stream.write(b'{"type":"FeatureCollection","features":[')
        first = True
        for page in pages:
            for feature in read_json(ROOT / page["path"]).get("features") or []:
                if not first: stream.write(b",")
                stream.write(canonical_json(feature)); first = False
        stream.write(b"]}\n")
    os.replace(temporary, output)
    manifest = {"schema_version": "es4c2a3a-national-municipality-download-v1", "source_url": SOURCE_URL, "retrieved_at": SOURCE_RETRIEVED_AT, "number_matched": matched, "pages": pages, "output": {"path": str(output.relative_to(ROOT)), "bytes": output.stat().st_size, "sha256": sha256(output)}}
    target = raw_dir / "national-geometry-manifest.json"; target.write_bytes(canonical_json(manifest) + b"\n")
    return manifest


def check_national_geometry_download(raw_dir: Path) -> dict[str, Any]:
    manifest_path = raw_dir / "national-geometry-manifest.json"
    if not manifest_path.is_file():
        return {"valid": False, "failures": ["manifest_missing"]}
    manifest = read_json(manifest_path); errors = []
    if manifest.get("number_matched") != 8213: errors.append("number_matched")
    if sum(page.get("features", 0) for page in manifest.get("pages", [])) != manifest.get("number_matched"): errors.append("page_feature_count")
    for page in manifest.get("pages", []):
        path = ROOT / page["path"]
        if not path.is_file() or sha256(path) != page["sha256"]: errors.append(f"page_checksum:{page.get('offset')}")
    output = ROOT / manifest.get("output", {}).get("path", "")
    if not output.is_file() or sha256(output) != manifest.get("output", {}).get("sha256"): errors.append("output_checksum")
    return {"valid": not errors, "failures": errors, "geometry_features": manifest.get("number_matched"), "output": manifest.get("output")}


def province_bounds() -> dict[str, tuple[str, tuple[float, float, float, float]]]:
    from shapely.geometry import shape

    collection = read_json(PROVINCE_SOURCE)
    output: dict[str, tuple[str, tuple[float, float, float, float]]] = {}
    for feature in collection.get("features", []):
        props = feature.get("properties") or {}
        code = national_code_parts(props.get("nationalcode"))
        if props.get("nationallevelname") != "Provincia" or code is None:
            continue
        ccaa, province, _unused = code
        if province not in SAMPLE_PROVINCES:
            continue
        geometry = shape(feature.get("geometry"))
        if geometry.is_empty:
            raise ValueError(f"Provincia BDLJE sin geometría: {province}")
        output[province] = (ccaa, tuple(geometry.bounds))
    if set(output) != set(SAMPLE_PROVINCES):
        raise ValueError(f"Faltan bounds BDLJE para muestra: {sorted(set(SAMPLE_PROVINCES) - set(output))}")
    return output


def sample_features(raw_dir: Path, resume: bool) -> dict[str, list[dict[str, Any]]]:
    directory = raw_dir / "sample-provinces"; directory.mkdir(parents=True, exist_ok=True)
    bounds = province_bounds()
    result: dict[str, list[dict[str, Any]]] = {}
    for province in SAMPLE_PROVINCES:
        ccaa, extent = bounds[province]
        target = directory / f"{province}.geojson"
        if target.is_file() and resume:
            collection = read_json(target)
        else:
            features: list[dict[str, Any]] = []
            offset = 0
            while True:
                page = fetch_json({
                    "f": "json", "limit": 1000, "offset": offset, "nationallevelname": "Municipio",
                    "bbox": ",".join(f"{value:.8f}" for value in extent),
                })
                batch = page.get("features") or []
                features.extend(batch)
                if len(batch) < 1000:
                    break
                offset += len(batch)
            collection = {"type": "FeatureCollection", "features": features}
            target.write_bytes(canonical_json(collection) + b"\n")
        exact = []
        for feature in collection.get("features") or []:
            parts = national_code_parts((feature.get("properties") or {}).get("nationalcode"))
            if parts and parts[0] == ccaa and parts[1] == province:
                exact.append(feature)
        result[province] = exact
    return result


def source_classification(features: list[dict[str, Any]], municipalities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    classes = Counter(); matches = []; anomalies = []
    parent_mismatch = []
    for feature in features:
        props = feature.get("properties") or {}
        parsed = national_code_parts(props.get("nationalcode"))
        if props.get("nationallevelname") != "Municipio":
            classes["NON_MUNICIPAL_UNIT"] += 1; anomalies.append({"nationalcode": props.get("nationalcode"), "nameunit": props.get("nameunit"), "reason": "nationallevelname_not_municipio"}); continue
        if parsed is None:
            classes["AMBIGUOUS"] += 1; anomalies.append({"nationalcode": props.get("nationalcode"), "nameunit": props.get("nameunit"), "reason": "invalid_nationalcode"}); continue
        ccaa, province, municipality = parsed
        territory = municipalities.get(municipality)
        if territory is None:
            lower = str(props.get("nameunit") or "").casefold()
            # Los 81 códigos 53xxx son comunidades, facerías, parzonerías y
            # otras unidades no municipales que BDLJE sirve en este nivel.
            # Se inventarían, pero nunca se convierten en ES:MUN.
            label = "NON_MUNICIPAL_UNIT" if municipality.startswith("53") or "no asociado" in lower or municipality == "00000" else "UNMATCHED_SOURCE"
            classes[label] += 1; anomalies.append({"nationalcode": props.get("nationalcode"), "nameunit": props.get("nameunit"), "derived_ine5": municipality, "reason": label}); continue
        expected_parent = f"ES:CCAA:{ccaa}" if province in {"51", "52"} else f"ES:PROV:{province}"
        if territory["parent_id"] != expected_parent:
            parent_mismatch.append({"nationalcode": props.get("nationalcode"), "territory_id": territory["territory_id"], "source_parent": expected_parent, "es2_parent": territory["parent_id"]})
        classes["MATCHED_CURRENT"] += 1
        matches.append((str(props["nationalcode"]), territory["territory_id"]))
    return {"counts": dict(sorted(classes.items())), "matches": matches, "anomalies": anomalies, "parent_mismatch": parent_mismatch}


def geometry_parts(geometry: Any) -> int:
    return len(geometry.geoms) if geometry.geom_type == "MultiPolygon" else 1


def geometry_vertices(geometry: Any) -> int:
    polygons = geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry]
    return sum(len(p.exterior.coords) + sum(len(r.coords) for r in p.interiors) for p in polygons)


def percentile(values: list[float], fraction: float) -> float | None:
    return sorted(values)[round((len(values) - 1) * fraction)] if values else None


def normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if character.isalnum())


def special_case_features(features: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    lookups = {"llivia": "Llívia", "condadodetrevino": "Condado de Treviño", "lapuebladearganzon": "La Puebla de Arganzón", "ademuz": "Rincón de Ademuz (municipio de Ademuz)"}
    output = {label: [] for label in lookups.values()}
    for feature in features:
        props = feature.get("properties") or {}
        name = normalized(str(props.get("nameunit") or ""))
        for needle, label in lookups.items():
            if needle in name:
                output[label].append({"nationalcode": props.get("nationalcode"), "nameunit": props.get("nameunit")})
    return output


def measure_sample(province: str, features: list[dict[str, Any]], municipalities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from pyproj import Transformer
    from shapely.geometry import mapping, shape
    from shapely.ops import transform

    to_meters = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    from_meters = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform
    original_vertices = 0; invalid = null = multiparts = 0; area_errors: dict[str, list[float]] = {"5": [], "10": []}
    derived: dict[str, list[dict[str, Any]]] = {"0": [], "5": [], "10": []}
    for feature in features:
        props = feature.get("properties") or {}; parsed = national_code_parts(props.get("nationalcode")); geometry_data = feature.get("geometry")
        if geometry_data is None:
            null += 1; continue
        geom = shape(geometry_data)
        if geom.is_empty or not geom.is_valid:
            invalid += 1; continue
        if geom.geom_type not in {"Polygon", "MultiPolygon"}:
            invalid += 1; continue
        if geometry_parts(geom) > 1: multiparts += 1
        original_vertices += geometry_vertices(geom)
        territory = municipalities.get(parsed[2]) if parsed else None
        properties = {"territory_id": territory["territory_id"] if territory else None, "source_code": props.get("nationalcode"), "official_name": territory["official_name"] if territory else props.get("nameunit"), "parent_id": territory["parent_id"] if territory else None}
        for tolerance in (0, 5, 10):
            if tolerance:
                geom_m = transform(to_meters, geom); simplified_m = geom_m.simplify(tolerance, preserve_topology=True); simplified = transform(from_meters, simplified_m)
                if simplified.is_empty or not simplified.is_valid or geometry_parts(simplified) != geometry_parts(geom):
                    raise ValueError(f"Simplificación municipal inválida en provincia {province}")
                area_errors[str(tolerance)].append(abs(simplified_m.area - geom_m.area) / geom_m.area * 100 if geom_m.area else 0.0)
            else:
                simplified = geom
            west, south, east, north = simplified.bounds
            derived[str(tolerance)].append({"type": "Feature", "properties": {**properties, "bounds": [round(west, 7), round(south, 7), round(east, 7), round(north, 7)]}, "geometry": mapping(simplified)})
    sizes = {}
    for tolerance, rows in derived.items():
        payload = canonical_json({"type": "FeatureCollection", "features": rows})
        sizes[tolerance] = {"raw_bytes": len(payload), "gzip_bytes": gzip_bytes(payload), "vertices": sum(geometry_vertices(shape(row["geometry"])) for row in rows)}
    return {"province_id": f"ES:PROV:{province}", "source_features_after_bbox_filter": len(features), "valid_features": len(derived["0"]), "null_geometry": null, "invalid_geometry": invalid, "multipart_features": multiparts, "original_vertices": original_vertices, "sizes": sizes, "simplification": {"5m": {"p95_relative_area_error_percent": percentile(area_errors["5"], .95), "max_relative_area_error_percent": max(area_errors["5"], default=None)}, "10m": {"p95_relative_area_error_percent": percentile(area_errors["10"], .95), "max_relative_area_error_percent": max(area_errors["10"], default=None)}}, "special_cases": special_case_features(features)}


def catalog_estimate(municipalities: dict[str, dict[str, Any]]) -> dict[str, int]:
    rows = []
    for code, row in sorted(municipalities.items()):
        province = code[:2]
        asset_id = f"municipalities:ES:PROV:{province}" if province not in {"51", "52"} else f"municipalities:{row['parent_id']}"
        rows.append({"municipality_id": row["territory_id"], "province_id": row["parent_id"] if province not in {"51", "52"} else None, "official_name": row["official_name"], "bounds": None, "asset_id": asset_id})
    payload = canonical_json({"schema_version": "es4c2a3a-catalog-design-v1", "municipalities": rows})
    return {"records": len(rows), "raw_bytes_without_bounds": len(payload), "gzip_bytes_without_bounds": gzip_bytes(payload)}


def projected_national_size(samples: dict[str, dict[str, Any]], target_features: int) -> dict[str, Any]:
    rows = [sample for sample in samples.values() if sample["valid_features"]]
    output = {}
    for tolerance in ("0", "5", "10"):
        raw_per_feature = [row["sizes"][tolerance]["raw_bytes"] / row["valid_features"] for row in rows]
        gzip_per_feature = [row["sizes"][tolerance]["gzip_bytes"] / row["valid_features"] for row in rows]
        output[tolerance] = {"method": "unweighted mean from ten province samples; estimate only until full geometry acquisition", "raw_bytes": round(sum(raw_per_feature) / len(raw_per_feature) * target_features), "gzip_bytes": round(sum(gzip_per_feature) / len(gzip_per_feature) * target_features), "raw_bytes_per_feature": sum(raw_per_feature) / len(raw_per_feature), "gzip_bytes_per_feature": sum(gzip_per_feature) / len(gzip_per_feature)}
    return output


def build(args: argparse.Namespace) -> dict[str, Any]:
    municipalities = municipal_snapshot(args.snapshot)
    inventory = inventory_pages(args.raw_dir, args.resume)
    classified = source_classification(inventory, municipalities)
    samples = sample_features(args.raw_dir, args.resume) if args.sample else {}
    measurements = {province: measure_sample(province, rows, municipalities) for province, rows in sorted(samples.items())}
    result = {
        "schema_version": "es4c2a3a-municipality-audit-v1", "phase": "ES-4C2A3A audit only", "generated_at": args.generated_at,
        "source": {"organization": "IGN / CNIG", "product": "BDLJE / Límites y Unidades Administrativas Actuales · collection administrativeunit", "url": SOURCE_URL, "query": "nationallevelname=Municipio", "inventory_query": "skipGeometry=true; limit=1000; offset pagination", "retrieved_at": SOURCE_RETRIEVED_AT, "format": "OGC API Features GeoJSON", "native_crs": "ETRS89 geographic (península, Baleares, Ceuta y Melilla); REGCAN95 geographic (Canarias)", "web_crs": "GeoJSON CRS84 / EPSG:4326-compatible longitude-latitude", "license": "CC BY 4.0", "attribution": "Obra derivada de BDLJE CC-BY 4.0 ign.es", "inventory_artifacts": local_artifacts(args.raw_dir / "inventory-pages"), "sample_geometry_artifacts": local_artifacts(args.raw_dir / "sample-provinces")},
        "es2": {"snapshot": str(args.snapshot.relative_to(ROOT)), "logical_municipalities": len(municipalities), "semantics": "current 2026 hierarchy; no historical geometry asserted"},
        "inventory": {"source_features": len(inventory), "classification": classified["counts"], "parent_hierarchy_mismatches": classified["parent_mismatch"], "anomalies": classified["anomalies"]},
        "geometry_samples": measurements,
        "national_geometry_size_estimate": projected_national_size(measurements, len(municipalities)) if measurements else None,
        "runtime_catalog_estimate": catalog_estimate(municipalities),
        "delivery_design": {"recommended": "light municipal catalogue plus current-geometry GeoJSON shards by province on demand", "why": "province is already known before municipal navigation; avoids a national municipal geometry initial transfer", "shard_count": "50 province shards plus autonomous-city handling only if official source has municipal features", "esfire30_municipal_note": "Do not use fixed mun_1..mun_3 slots: a perimeter can intersect many municipalities. Future work needs a municipal inverse index, local tiles, or spatial query over loaded geometry."},
        "egif_semantics": "Filtering ES:MUN:xxxxx means source records whose administrative municipality was exactly linked to the current ES-2 canonical municipality; it does not assert that every event lies physically inside the current boundary.",
        "historical_limitation": "BDLJE geometry is current. Current municipality geometry != historical municipality geometry unless a separate documented historical boundary source establishes it. Unresolved EGIF municipalities remain unresolved.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_bytes(canonical_json(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", action="store_true", help="adquiere inventario nacional ligero con skipGeometry=true")
    parser.add_argument("--sample", action="store_true", help="adquiere y mide solo provincias de muestra")
    parser.add_argument("--all", action="store_true", help="adquisición nacional reanudable: ejecutar fuera de Codex")
    parser.add_argument("--check", action="store_true", help="comprueba checksums de la adquisición nacional ya terminada")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--generated-at", default="2026-08-29T00:00:00Z")
    args = parser.parse_args()
    if args.check:
        if not args.all: parser.error("--check requiere --all")
        result = check_national_geometry_download(args.raw_dir); print(json.dumps(result, ensure_ascii=False)); raise SystemExit(0 if result["valid"] else 1)
    if args.all:
        result = national_geometry_download(args.raw_dir, args.resume)
        print(json.dumps({"valid": True, "geometry_features": result["number_matched"], "output": result["output"]}, ensure_ascii=False)); return
    if not args.inventory and not args.sample:
        parser.error("Use --inventory --sample para la auditoría ligera")
    result = build(args)
    print(json.dumps({"source_features": result["inventory"]["source_features"], "matched": result["inventory"]["classification"].get("MATCHED_CURRENT", 0), "samples": {code: data["valid_features"] for code, data in result["geometry_samples"].items()}, "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
