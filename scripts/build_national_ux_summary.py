#!/usr/bin/env python3
"""Construye ``national-ux-summary-v1`` desde derivados ya aceptados.

El builder no abre geometrías ni crea relaciones. Agrega por año las columnas
EGIF, los registros ICV, los pequeños assets EFFIS y las relaciones positivas
ESFire30 ya cerradas. Las métricas permanecen separadas por fuente.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import resource
import shutil
import tempfile
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = Path(__file__).resolve()
DEFAULT_OUTPUT = ROOT / "data/derived/spain/national-ux-summary-v1"
SCHEMA_PATH = ROOT / "schemas/national/v1/national-ux-summary.schema.json"
METRIC_CONTRACT = ROOT / "data/audit/product/es4e2_metric_contracts.json"
DATA_REQUIREMENTS = ROOT / "data/audit/product/es4e2_data_requirements.json"
EGIF_MANIFEST = ROOT / "build/national-pages-staging/data/egif/v1/2026-08-27/manifest.json"
GVA_MANIFEST = ROOT / "build/national-pages-staging/data/web/gva/manifest.json"
ICV_FIRES = ROOT / "build/national-pages-staging/data/web/gva/fires.json"
TERRITORY_CATALOG = ROOT / "build/national-pages-staging/data/territories/spain/territories-2026-01-01.json"
MUNICIPALITY_CATALOG = ROOT / "build/national-pages-staging/data/territories/spain/v1/municipality-catalog.json"
ESFIRE_TERRITORY_MANIFEST = ROOT / "data/derived/spain/es4c2b/esfire30_territory_relations/manifest.json"
ESFIRE_MUNICIPALITY_MANIFEST = ROOT / "data/derived/spain/es4c2b/esfire30_municipality_relations/manifest.json"

SCHEMA_VERSION = "national-ux-summary-v1"
DATASET_VERSION = "2026-09-02"
EXPECTED = {"egif": 646_887, "esfire30": 119_498, "icv_records": 13_738, "icv_geometries": 13_739, "effis_2025": 9, "effis_2026": 16}
SOURCE_COVERAGE = {"egif": (1968, 2023), "esfire30": (1985, 2021), "icv": (1993, 2024), "effis": (2025, 2026)}
ESFIRE_NO_COVERAGE_CCAA = {"ES:CCAA:04", "ES:CCAA:05", "ES:CCAA:18", "ES:CCAA:19"}
ICV_PROVINCES = {"alicante": "ES:PROV:03", "castellon": "ES:PROV:12", "valencia": "ES:PROV:46"}
ICV_PROVINCE_ALIASES = {
    "ALICANTE": "ES:PROV:03", "Alicante/Alacant": "ES:PROV:03",
    "CASTELLON": "ES:PROV:12", "Castellon": "ES:PROV:12", "Castellón/Castelló": "ES:PROV:12",
    "VALENCIA": "ES:PROV:46", "Valencia/València": "ES:PROV:46",
}
ALLOWED_METRICS = {
    "egif_record_count", "egif_declared_forest_area_ha", "egif_administrative_gif_count",
    "esfire30_perimeter_count", "icv_fire_record_count", "icv_perimeter_count",
    "icv_declared_forest_area_ha", "icv_gif_count", "effis_perimeter_count", "effis_mapped_area_ha",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def gzip_size(raw: bytes) -> int:
    return len(gzip.compress(raw, compresslevel=9, mtime=0))


def portable(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def atomic_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def check_sha(path: Path, expected: str, label: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"Checksum inesperado para {label}: {actual}")


def blank_stats() -> dict[str, Any]:
    return {
        "records": 0, "geometries": 0, "area_sum": Decimal("0"), "area_known": 0,
        "area_unknown": 0, "gif_true": 0, "gif_false": 0, "gif_unknown": 0,
        "municipality_unresolved": 0,
    }


def stats_slot(aggregate: dict, source_id: str, territory_id: str, year: int) -> dict[str, Any]:
    return aggregate[source_id][territory_id][year]


def update_record(slot: dict[str, Any], area: Any, gif: Any, municipality_id: str | None = "not-applicable", geometries: int = 0) -> None:
    slot["records"] += 1
    slot["geometries"] += geometries
    if area is None:
        slot["area_unknown"] += 1
    else:
        slot["area_known"] += 1
        slot["area_sum"] += Decimal(str(area))
    if gif is True:
        slot["gif_true"] += 1
    elif gif is False:
        slot["gif_false"] += 1
    else:
        slot["gif_unknown"] += 1
    if municipality_id is None:
        slot["municipality_unresolved"] += 1


def update_geometry(slot: dict[str, Any], area: Any = "not-applicable") -> None:
    slot["geometries"] += 1
    if area != "not-applicable":
        if area is None:
            slot["area_unknown"] += 1
        else:
            slot["area_known"] += 1
            slot["area_sum"] += Decimal(str(area))


def load_territories() -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    payload = load_json(TERRITORY_CATALOG)
    territories = {row["territory_id"]: row for row in payload["territories"]}
    municipalities = load_json(MUNICIPALITY_CATALOG)["municipalities"]
    if len(municipalities) != 8132:
        raise ValueError("El catálogo municipal no contiene 8132 municipios")
    by_parent: dict[str, list[str]] = defaultdict(list)
    for row in municipalities:
        if row["municipality_id"] not in territories:
            raise ValueError(f"Municipio ausente del catálogo ES-2: {row['municipality_id']}")
        parent = row["province_id"] or row["autonomous_community_id"]
        by_parent[parent].append(row["municipality_id"])
    return territories, {key: sorted(value) for key, value in sorted(by_parent.items())}


def input_asset_path(manifest_path: Path, relative: str) -> Path:
    candidate = manifest_path.parent / relative
    if candidate.is_file():
        return candidate
    candidate = ROOT / relative
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(relative)


def input_inventory(required: list[Path]) -> list[dict[str, Any]]:
    """Expande los manifests para que ``--check`` cubra cada input agregado."""
    rows: dict[str, dict[str, Any]] = {}

    def add(path: Path, expected_sha: str | None = None, source_id: str = "contract") -> None:
        label = portable(path)
        actual_sha = sha256(path)
        if expected_sha and actual_sha != expected_sha:
            raise ValueError(f"Checksum inesperado para {label}")
        rows[label] = {"path": label, "source_id": source_id, "bytes": path.stat().st_size, "sha256": actual_sha}

    for path in required:
        add(path)
    egif = load_json(EGIF_MANIFEST)
    for asset in egif["assets"]:
        add(input_asset_path(EGIF_MANIFEST, asset["initial"]["path"]), asset["initial"]["sha256"], "egif")
    gva = load_json(GVA_MANIFEST)
    add(ICV_FIRES, gva["icv"]["attributes"]["fires"]["sha256"], "icv")
    for asset in gva["recent"]["assets"]:
        if asset["kind"] == "effis_perimeters":
            add(input_asset_path(GVA_MANIFEST, asset["url"]), asset["sha256"], "effis")
    for manifest_path in (ESFIRE_TERRITORY_MANIFEST, ESFIRE_MUNICIPALITY_MANIFEST):
        manifest = load_json(manifest_path)
        for block in manifest["blocks"]:
            add(ROOT / block["relations_path"], block["relations_sha256"], "esfire30")
    return [rows[key] for key in sorted(rows)]


def aggregate_egif(aggregate: dict) -> dict[str, Any]:
    manifest = load_json(EGIF_MANIFEST)
    if manifest.get("totals", {}).get("records") != EXPECTED["egif"]:
        raise ValueError("Manifest EGIF no reconcilia 646887 registros")
    records = 0
    unresolved = 0
    for asset in sorted(manifest["assets"], key=lambda row: row["asset_id"]):
        path = input_asset_path(EGIF_MANIFEST, asset["initial"]["path"])
        check_sha(path, asset["initial"]["sha256"], asset["asset_id"])
        columns = load_json(path)["columns"]
        size = len(columns["record_id"])
        if size != asset["record_count"] or any(len(values) != size for values in columns.values()):
            raise ValueError(f"Columnas EGIF desalineadas: {asset['asset_id']}")
        for ordinal in range(size):
            year = int(columns["year"][ordinal])
            ccaa = columns["autonomous_community_id"][ordinal]
            province = columns["province_id"][ordinal]
            municipality = columns["municipality_id"][ordinal]
            area = columns["reported_forest_area_ha"][ordinal]
            gif = columns["is_gif_forest_ge_500_ha"][ordinal]
            targets = ["ES", ccaa]
            if province:
                targets.append(province)
            if municipality:
                targets.append(municipality)
            for territory_id in targets:
                update_record(stats_slot(aggregate, "egif", territory_id, year), area, gif, municipality)
            records += 1
            unresolved += municipality is None
    if records != EXPECTED["egif"] or unresolved != 71_490:
        raise ValueError(f"Reconciliación EGIF inesperada: {records} / unresolved {unresolved}")
    return {"source_records": records, "municipality_unresolved": unresolved}


def aggregate_icv(aggregate: dict) -> dict[str, Any]:
    manifest = load_json(GVA_MANIFEST)
    fires_asset = manifest["icv"]["attributes"]["fires"]
    check_sha(ICV_FIRES, fires_asset["sha256"], "ICV fires.json")
    rows = load_json(ICV_FIRES)["fires"]
    ids, geometry_ids = set(), set()
    control = None
    for row in rows:
        fire_id = row["fire_id"]
        if fire_id in ids:
            raise ValueError(f"fire_id ICV duplicado: {fire_id}")
        ids.add(fire_id)
        province = ICV_PROVINCE_ALIASES.get(row["province"])
        if not province:
            raise ValueError(f"Provincia ICV no documentada: {row['province']}")
        municipality = f"ES:MUN:{row['municipality_id']}" if row.get("municipality_id") else None
        year = int(row["year"])
        area = row.get("reported_forest_area_ha")
        gif = None if area is None else Decimal(str(area)) >= Decimal("500")
        geometries = row.get("geometry_ids") or []
        if any(geometry_id in geometry_ids for geometry_id in geometries):
            raise ValueError(f"geometry_id ICV duplicado: {fire_id}")
        geometry_ids.update(geometries)
        targets = ["ES:CCAA:10", province]
        if municipality:
            targets.append(municipality)
        for territory_id in targets:
            update_record(stats_slot(aggregate, "icv", territory_id, year), area, gif, municipality, len(geometries))
        if fire_id == "gva:pif-cv:2024AL0005":
            control = {"fire_record_count": 1, "geometry_count": len(geometries)}
    if len(ids) != EXPECTED["icv_records"] or len(geometry_ids) != EXPECTED["icv_geometries"]:
        raise ValueError("Reconciliación ICV 13738/13739 fallida")
    if control != {"fire_record_count": 1, "geometry_count": 2}:
        raise ValueError("Caso ICV 2024AL0005 no conserva 1:2")
    return {"fire_records": len(ids), "geometries": len(geometry_ids), "control_2024AL0005": control}


def aggregate_effis(aggregate: dict) -> dict[str, Any]:
    manifest = load_json(GVA_MANIFEST)
    counts: dict[int, int] = {}
    geometry_ids = set()
    for asset in sorted((row for row in manifest["recent"]["assets"] if row["kind"] == "effis_perimeters"), key=lambda row: row["year"]):
        path = input_asset_path(GVA_MANIFEST, asset["url"])
        check_sha(path, asset["sha256"], f"EFFIS {asset['year']}")
        features = load_json(path)["features"]
        if len(features) != asset["feature_count"]:
            raise ValueError(f"Recuento EFFIS inesperado: {asset['year']}")
        counts[int(asset["year"])] = len(features)
        for feature in features:
            row = feature["properties"]
            geometry_id = row["geometry_id"]
            if geometry_id in geometry_ids:
                raise ValueError(f"geometry_id EFFIS duplicado: {geometry_id}")
            geometry_ids.add(geometry_id)
            province = ICV_PROVINCES[row["province_key"]]
            municipality = f"ES:MUN:{row['municipality_id']}" if row.get("municipality_id") else None
            for territory_id in ["ES:CCAA:10", province] + ([municipality] if municipality else []):
                update_geometry(stats_slot(aggregate, "effis", territory_id, int(row["year"])), row.get("mapped_area_ha"))
    if counts != {2025: EXPECTED["effis_2025"], 2026: EXPECTED["effis_2026"]}:
        raise ValueError(f"Reconciliación EFFIS inesperada: {counts}")
    return {"snapshot": manifest["recent"]["snapshot_id"], "annual_geometries": {str(key): value for key, value in sorted(counts.items())}, "geometries": len(geometry_ids)}


def read_jsonl_verified(path: Path, expected_sha: str) -> Iterable[dict[str, Any]]:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for line in source:
            digest.update(line)
            if line.strip():
                yield json.loads(line)
    if digest.hexdigest() != expected_sha:
        raise ValueError(f"Checksum de relaciones inesperado: {portable(path)}")


def aggregate_esfire30(aggregate: dict) -> dict[str, Any]:
    territory_manifest = load_json(ESFIRE_TERRITORY_MANIFEST)
    municipality_manifest = load_json(ESFIRE_MUNICIPALITY_MANIFEST)
    geometry_ids: set[str] = set()
    territory_relations = 0
    level_relations = defaultdict(int)
    municipality_relations = 0
    annual: dict[str, int] = {}
    for block in sorted(territory_manifest["blocks"], key=lambda row: row["year"]):
        year = int(block["year"])
        year_ids: set[str] = set()
        path = ROOT / block["relations_path"]
        for relation in read_jsonl_verified(path, block["relations_sha256"]):
            if relation["intersection_class"] != "positive_area_intersection":
                raise ValueError("Relación ESFire30 territorial no positiva")
            geometry_id, territory_id = relation["geometry_id"], relation["territory_id"]
            if geometry_id in year_ids and relation["territory_level"] not in ("autonomous_community", "province"):
                raise ValueError("Nivel territorial ESFire30 inesperado")
            year_ids.add(geometry_id)
            update_geometry(stats_slot(aggregate, "esfire30", territory_id, year))
            territory_relations += 1
            level_relations[relation["territory_level"]] += 1
        if len(year_ids) != block["geometry_count"]:
            raise ValueError(f"Geometrías ESFire30 inesperadas en {year}")
        if geometry_ids.intersection(year_ids):
            raise ValueError(f"geometry_id ESFire30 repetido entre años: {year}")
        geometry_ids.update(year_ids)
        annual[str(year)] = len(year_ids)
        aggregate["esfire30"]["ES"][year]["geometries"] = len(year_ids)
    for block in sorted(municipality_manifest["blocks"], key=lambda row: row["year"]):
        year = int(block["year"])
        path = ROOT / block["relations_path"]
        seen = set()
        for relation in read_jsonl_verified(path, block["relations_sha256"]):
            if relation["intersection_class"] != "positive_area_intersection":
                raise ValueError("Relación ESFire30 municipal no positiva")
            key = (relation["geometry_id"], relation["municipality_id"])
            if key in seen:
                raise ValueError(f"Relación ESFire30 municipal duplicada: {key}")
            if relation["geometry_id"] not in geometry_ids:
                raise ValueError(f"Relación municipal con geometry_id desconocido: {relation['geometry_id']}")
            seen.add(key)
            update_geometry(stats_slot(aggregate, "esfire30", relation["municipality_id"], year))
            municipality_relations += 1
    if len(geometry_ids) != EXPECTED["esfire30"]:
        raise ValueError("ESFire30 no reconcilia 119498 geometry_id")
    if territory_relations != 242_734 or municipality_relations != 143_477:
        raise ValueError(f"Relaciones ESFire30 inesperadas: {territory_relations}/{municipality_relations}")
    if dict(level_relations) != {"autonomous_community": 120_847, "province": 121_887}:
        raise ValueError(f"Reconciliación territorial ESFire30 inesperada: {dict(level_relations)}")
    return {
        "geometries": len(geometry_ids), "annual_geometries": annual,
        "ccaa_relations": level_relations["autonomous_community"], "province_relations": level_relations["province"],
        "municipality_relations": municipality_relations,
        "municipality_unresolved_geometries": municipality_manifest["totals"]["zero_relation_count"],
    }


def decimal_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def annual_values(stats: dict[int, dict[str, Any]], coverage: tuple[int, int], key: str, area: bool = False) -> list[Any]:
    values = []
    for year in range(coverage[0], coverage[1] + 1):
        row = stats.get(year, blank_stats())
        if area:
            if row["area_known"]:
                values.append(decimal_number(row["area_sum"]))
            elif row["area_unknown"]:
                values.append(None)
            else:
                values.append(0)
        else:
            values.append(row[key])
    return values


def metric(metric_id: str, unit: str, values: list[Any], **metadata: Any) -> dict[str, Any]:
    if metric_id not in ALLOWED_METRICS:
        raise ValueError(f"Métrica no autorizada por E2: {metric_id}")
    return {"metric_id": metric_id, "unit": unit, "values": values, **metadata}


def source_summary(source_id: str, stats: dict[int, dict[str, Any]], availability: str = "available", snapshot: str | None = None) -> dict[str, Any]:
    coverage = SOURCE_COVERAGE[source_id]
    result: dict[str, Any] = {
        "source_id": source_id,
        "entity_type": {"egif": "administrative_source_record", "esfire30": "landsat_perimeter", "icv": "official_fire_record_and_perimeter", "effis": "provisional_satellite_perimeter"}[source_id],
        "coverage": {"from": coverage[0], "to": coverage[1], "status": availability},
        "year_axis": {"from": coverage[0], "to": coverage[1], "semantics": "dense_within_coverage"},
        "metrics": [],
    }
    if snapshot:
        result["snapshot"] = snapshot
    if availability != "available":
        return result
    if source_id == "egif":
        result["metrics"] = [
            metric("egif_record_count", "records", annual_values(stats, coverage, "records")),
            metric("egif_declared_forest_area_ha", "ha", annual_values(stats, coverage, "area_sum", area=True),
                   known_value_count=annual_values(stats, coverage, "area_known"), unknown_value_count=annual_values(stats, coverage, "area_unknown")),
            metric("egif_administrative_gif_count", "records", annual_values(stats, coverage, "gif_true"),
                   false_value_count=annual_values(stats, coverage, "gif_false"), unknown_value_count=annual_values(stats, coverage, "gif_unknown")),
        ]
        result["quality_counts"] = {"municipality_unresolved": annual_values(stats, coverage, "municipality_unresolved")}
    elif source_id == "esfire30":
        result["metrics"] = [metric("esfire30_perimeter_count", "perimeters", annual_values(stats, coverage, "geometries"))]
    elif source_id == "icv":
        result["metrics"] = [
            metric("icv_fire_record_count", "fire_records", annual_values(stats, coverage, "records")),
            metric("icv_perimeter_count", "perimeters", annual_values(stats, coverage, "geometries")),
            metric("icv_declared_forest_area_ha", "ha", annual_values(stats, coverage, "area_sum", area=True),
                   known_value_count=annual_values(stats, coverage, "area_known"), unknown_value_count=annual_values(stats, coverage, "area_unknown")),
            metric("icv_gif_count", "fire_records", annual_values(stats, coverage, "gif_true"),
                   false_value_count=annual_values(stats, coverage, "gif_false"), unknown_value_count=annual_values(stats, coverage, "gif_unknown")),
        ]
    elif source_id == "effis":
        result["metrics"] = [
            metric("effis_perimeter_count", "perimeters", annual_values(stats, coverage, "geometries")),
            metric("effis_mapped_area_ha", "ha", annual_values(stats, coverage, "area_sum", area=True),
                   known_value_count=annual_values(stats, coverage, "area_known"), unknown_value_count=annual_values(stats, coverage, "area_unknown")),
        ]
    return result


def source_applicable(source_id: str, territory_id: str, territories: dict[str, dict[str, Any]]) -> bool:
    if source_id in ("egif", "esfire30"):
        return True
    if territory_id == "ES":
        return False
    row = territories[territory_id]
    if row["territory_type"] in ("autonomous_community", "autonomous_city"):
        ccaa = territory_id
    elif row["territory_type"] == "province":
        ccaa = row["parent_id"]
    else:
        province = territories[row["parent_id"]]
        ccaa = province["parent_id"] if province["territory_type"] == "province" else province["territory_id"]
    return ccaa == "ES:CCAA:10"


def esfire_has_coverage(territory_id: str, territories: dict[str, dict[str, Any]]) -> bool:
    if territory_id == "ES":
        return True
    row = territories[territory_id]
    if row["territory_type"] in ("autonomous_community", "autonomous_city"):
        ccaa = territory_id
    elif row["territory_type"] == "province":
        ccaa = row["parent_id"]
    else:
        parent = territories[row["parent_id"]]
        ccaa = parent["parent_id"] if parent["territory_type"] == "province" else parent["territory_id"]
    return ccaa not in ESFIRE_NO_COVERAGE_CCAA


def territory_payload(territory_id: str, territories: dict[str, dict[str, Any]], aggregate: dict, effis_snapshot: str) -> dict[str, Any]:
    row = territories[territory_id]
    summaries = []
    for source_id in ("egif", "esfire30", "icv", "effis"):
        if not source_applicable(source_id, territory_id, territories):
            continue
        availability = "available"
        if source_id == "esfire30" and not esfire_has_coverage(territory_id, territories):
            availability = "no_source_coverage"
        summaries.append(source_summary(source_id, aggregate[source_id][territory_id], availability, effis_snapshot if source_id == "effis" else None))
    return {
        "territory": {"territory_id": territory_id, "territory_type": row["territory_type"], "official_name": row["official_name"], "parent_id": row["parent_id"]},
        "source_summaries": summaries,
    }


def write_asset(path: Path, value: dict[str, Any], output: Path) -> dict[str, Any]:
    raw = canonical_bytes(value)
    atomic_bytes(path, raw)
    return {"path": path.relative_to(output).as_posix(), "bytes": len(raw), "gzip_bytes": gzip_size(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def account_sources(value: dict[str, Any], accounting: dict[str, dict[str, int]]) -> None:
    """Mide fragmentos lógicos; los wrappers de entrega se miden aparte."""
    for territory in value["territories"]:
        for summary in territory["source_summaries"]:
            raw = canonical_bytes(summary)
            row = accounting[summary["source_id"]]
            row["territory_summaries"] += 1
            row["raw_fragment_bytes"] += len(raw)
            row["gzip_fragment_bytes"] += gzip_size(raw)


def build(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    started = time.monotonic()
    required = [BUILDER_PATH, SCHEMA_PATH, METRIC_CONTRACT, DATA_REQUIREMENTS, EGIF_MANIFEST, GVA_MANIFEST, ICV_FIRES, TERRITORY_CATALOG, MUNICIPALITY_CATALOG, ESFIRE_TERRITORY_MANIFEST, ESFIRE_MUNICIPALITY_MANIFEST]
    missing = [portable(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Faltan inputs aceptados: " + ", ".join(missing))
    contracts = load_json(METRIC_CONTRACT)
    contract_ids = {row["metric_id"] for row in contracts["metrics"]}
    if not ALLOWED_METRICS <= contract_ids:
        raise ValueError("El builder declara métricas fuera del contrato E2")
    territories, municipalities_by_parent = load_territories()
    aggregate = defaultdict(lambda: defaultdict(lambda: defaultdict(blank_stats)))
    reconciliation = {
        "egif": aggregate_egif(aggregate),
        "icv": aggregate_icv(aggregate),
        "effis": aggregate_effis(aggregate),
        "esfire30": aggregate_esfire30(aggregate),
    }
    for source_id, by_territory in aggregate.items():
        unknown = set(by_territory) - set(territories)
        if unknown:
            raise ValueError(f"{source_id} contiene territorios ajenos a ES-2: {sorted(unknown)[:5]}")
    output = output.resolve()
    if output in (ROOT.resolve(), Path("/").resolve()):
        raise ValueError("Output demasiado amplio")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="national-ux-summary-", dir=output.parent) as directory:
        staging = Path(directory) / "summary"
        staging.mkdir()
        files = []
        source_accounting = defaultdict(lambda: {"territory_summaries": 0, "raw_fragment_bytes": 0, "gzip_fragment_bytes": 0})
        delivery: dict[str, Any] = {"country": None, "autonomous_communities": [], "provinces": [], "municipalities_by_parent": []}
        effis_snapshot = reconciliation["effis"]["snapshot"]

        country_value = {"schema_version": SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "scope": "territory", "territories": [territory_payload("ES", territories, aggregate, effis_snapshot)]}
        account_sources(country_value, source_accounting)
        country = write_asset(staging / "national.json", country_value, staging)
        files.append(country); delivery["country"] = country

        ccaa_ids = sorted(row["territory_id"] for row in territories.values() if row["territory_type"] in ("autonomous_community", "autonomous_city"))
        province_ids = sorted(row["territory_id"] for row in territories.values() if row["territory_type"] == "province")
        for territory_id, group, folder in [(item, "autonomous_communities", "ccaa") for item in ccaa_ids] + [(item, "provinces", "provinces") for item in province_ids]:
            value = {"schema_version": SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "scope": "territory", "territories": [territory_payload(territory_id, territories, aggregate, effis_snapshot)]}
            account_sources(value, source_accounting)
            entry = {"territory_id": territory_id, **write_asset(staging / folder / f"{territory_id.replace(':', '-')}.json", value, staging)}
            files.append({k: entry[k] for k in ("path", "bytes", "gzip_bytes", "sha256")}); delivery[group].append(entry)

        for parent_id, municipality_ids in municipalities_by_parent.items():
            value = {
                "schema_version": SCHEMA_VERSION, "dataset_version": DATASET_VERSION,
                "scope": "municipalities_by_parent", "parent_id": parent_id,
                "territories": [territory_payload(item, territories, aggregate, effis_snapshot) for item in municipality_ids],
            }
            account_sources(value, source_accounting)
            entry = {"parent_id": parent_id, "territory_count": len(municipality_ids), **write_asset(staging / "municipalities" / "by-parent" / f"{parent_id.replace(':', '-')}.json", value, staging)}
            files.append({k: entry[k] for k in ("path", "bytes", "gzip_bytes", "sha256")}); delivery["municipalities_by_parent"].append(entry)

        files.sort(key=lambda row: row["path"])
        fingerprint_payload = [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in files]
        fingerprint = hashlib.sha256(canonical_bytes(fingerprint_payload)).hexdigest()
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "dataset_version": DATASET_VERSION,
            "metric_contract_version": contracts["schema_version"],
            "territory_model": "ES-2 current administrative territories; municipality geometry/history is not asserted by this summary",
            "source_versions": {
                "egif": "1968-2023 pipeline 2026-08-27", "esfire30": "v1 DOI 10.5281/zenodo.18449006",
                "icv": "ICV 1993-2024 published snapshot", "effis": effis_snapshot,
            },
            "inputs": input_inventory(required),
            "semantics": {
                "cross_source_sum_allowed": False, "zero": "covered and measured zero", "null": "unknown value among covered records",
                "outside_coverage": "no series outside source coverage; no_source_coverage is explicit",
                "esfire30_territory": "unique geometry_id with positive-area intersection; a multi-territory perimeter counts once in each related territory",
            },
            "deferred_metrics": {
                "esfire30_mapped_area_ha": "DEFERRED: existing relations do not provide union-safe territorial mapped area and full perimeter area must not be mislabeled",
                "egif_cause_distribution": "BLOCKED_EXTERNAL: no approved national canonical cause ontology",
                "source_highlights": "DEFERRED_TO_E3C: not required for P0 histogram",
            },
            "delivery": delivery,
            "files": files,
            "payload_file_count": len(files),
            "payload_bytes": sum(row["bytes"] for row in files),
            "payload_gzip_bytes": sum(row["gzip_bytes"] for row in files),
            "source_size_accounting": {key: source_accounting[key] for key in sorted(source_accounting)},
            "fingerprint_algorithm": "sha256(canonical_json([{path,bytes,sha256},...]))",
            "fingerprint": fingerprint,
            "source_reconciliation": reconciliation,
        }
        atomic_bytes(staging / "manifest.json", canonical_bytes(manifest))
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(staging), str(output))
    elapsed = time.monotonic() - started
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    manifest_raw = (output / "manifest.json").read_bytes()
    return {
        "valid": True, "output": portable(output), "payload_file_count": manifest["payload_file_count"],
        "physical_file_count": manifest["payload_file_count"] + 1,
        "payload_bytes": manifest["payload_bytes"], "payload_gzip_bytes": manifest["payload_gzip_bytes"],
        "physical_bytes": manifest["payload_bytes"] + len(manifest_raw),
        "physical_gzip_bytes": manifest["payload_gzip_bytes"] + gzip_size(manifest_raw),
        "fingerprint": manifest["fingerprint"], "build_seconds": round(elapsed, 3), "peak_rss_bytes": peak_rss,
    }


def check(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output = output.resolve()
    manifest_path = output / "manifest.json"
    failures: list[str] = []
    if not manifest_path.is_file():
        return {"valid": False, "failures": [f"missing:{portable(manifest_path)}"]}
    manifest = load_json(manifest_path)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        failures.append("schema_version")
    if manifest.get("metric_contract_version") != load_json(METRIC_CONTRACT).get("schema_version"):
        failures.append("metric_contract_version")
    file_rows = manifest.get("files", [])
    if len(file_rows) != manifest.get("payload_file_count") or len({row.get("path") for row in file_rows}) != len(file_rows):
        failures.append("file_inventory")
    if sum(row.get("bytes", 0) for row in file_rows) != manifest.get("payload_bytes") or sum(row.get("gzip_bytes", 0) for row in file_rows) != manifest.get("payload_gzip_bytes"):
        failures.append("size_accounting")
    for row in file_rows:
        path = output / row["path"]
        if not path.is_file():
            failures.append(f"missing:{row['path']}"); continue
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"] or gzip_size(raw) != row["gzip_bytes"]:
            failures.append(f"identity:{row['path']}")
        try:
            payload = json.loads(raw)
            if canonical_bytes(payload) != raw:
                failures.append(f"noncanonical:{row['path']}")
            for territory in payload.get("territories", []):
                for summary in territory.get("source_summaries", []):
                    for item in summary.get("metrics", []):
                        if item.get("metric_id") not in ALLOWED_METRICS or "combined" in item.get("metric_id", ""):
                            failures.append(f"metric:{row['path']}")
        except (ValueError, TypeError, json.JSONDecodeError):
            failures.append(f"schema:{row['path']}")
    fingerprint_rows = [{"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in file_rows]
    if hashlib.sha256(canonical_bytes(fingerprint_rows)).hexdigest() != manifest.get("fingerprint"):
        failures.append("fingerprint")
    rec = manifest.get("source_reconciliation", {})
    if rec.get("egif", {}).get("source_records") != EXPECTED["egif"] or rec.get("egif", {}).get("municipality_unresolved") != 71_490:
        failures.append("egif_reconciliation")
    if (rec.get("icv", {}).get("fire_records"), rec.get("icv", {}).get("geometries")) != (EXPECTED["icv_records"], EXPECTED["icv_geometries"]):
        failures.append("icv_reconciliation")
    if rec.get("esfire30", {}).get("geometries") != EXPECTED["esfire30"]:
        failures.append("esfire30_reconciliation")
    if rec.get("effis", {}).get("annual_geometries") != {"2025": 9, "2026": 16}:
        failures.append("effis_reconciliation")
    for row in manifest.get("inputs", []):
        path = ROOT / row["path"] if not Path(row["path"]).is_absolute() else Path(row["path"])
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            failures.append(f"input:{row['path']}")
    manifest_raw = manifest_path.read_bytes()
    return {
        "valid": not failures, "failures": sorted(set(failures)), "output": portable(manifest_path),
        "payload_file_count": manifest.get("payload_file_count"), "physical_file_count": (manifest.get("payload_file_count") or 0) + 1,
        "payload_bytes": manifest.get("payload_bytes"), "payload_gzip_bytes": manifest.get("payload_gzip_bytes"),
        "physical_bytes": (manifest.get("payload_bytes") or 0) + len(manifest_raw),
        "physical_gzip_bytes": (manifest.get("payload_gzip_bytes") or 0) + gzip_size(manifest_raw),
        "fingerprint": manifest.get("fingerprint"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check(args.output) if args.check else build(args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
