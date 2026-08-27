#!/usr/bin/env python3
"""Descarga EGIF nacional con el capítulo mínimo de localización.

ES-1.5 necesita identificar ``HOJA`` + ``CUADRICULA`` sin adquirir los
aproximadamente 3,5 GiB del XML completo. El exportador público permite pedir
solo ``Localización``; identidad y año se conservan siempre en cada ``Pif``.

Los ZIP producidos son snapshots raw y deben permanecer fuera de Git. El
manifiesto local registra recuentos, cobertura, checksums y parámetros.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.parse
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

try:  # ejecución como módulo
    from .gva_1968_1992 import (
        DOWNLOAD_URL,
        EXPORT_URL,
        SEARCH_URL,
        HttpClient,
        PipelineError,
        SearchPageParser,
        atomic_write_bytes,
        atomic_write_json,
        parse_search_page,
        sha256_bytes,
        sha256_file,
        utc_now,
    )
except ImportError:  # ejecución directa desde el repositorio
    from gva_1968_1992 import (  # type: ignore
        DOWNLOAD_URL,
        EXPORT_URL,
        SEARCH_URL,
        HttpClient,
        PipelineError,
        SearchPageParser,
        atomic_write_bytes,
        atomic_write_json,
        parse_search_page,
        sha256_bytes,
        sha256_file,
        utc_now,
    )


ROOT = Path(__file__).resolve().parents[3]
COUNTS_PATH = ROOT / "data/sources/spain_source_inventory.json"
OUTPUT_DIR = ROOT / "data/raw/egif/spain/location_only/2026-08-26"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
PIPELINE_VERSION = "es-1.5-location-only-1"
CHAPTERS = "1|" + "|".join(["0"] * 16)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first_child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    return next((child for child in element if local_name(child.tag) == name), None)


def child_text(element: ET.Element | None, name: str) -> str | None:
    child = first_child(element, name)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def expected_counts(path: Path) -> dict[int, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    egif = next(item for item in payload["sources"] if item["id"] == "egif")
    return {
        int(year): int(count)
        for year, count in egif["annual_counts"].items()
        if int(count) > 0
    }


def contiguous_blocks(counts: dict[int, int], limit: int) -> list[dict[str, int]]:
    """Agrupa años contiguos sin superar el límite oficial del exportador."""
    if limit <= 0:
        raise ValueError("limit debe ser positivo")
    blocks: list[dict[str, int]] = []
    start: int | None = None
    end: int | None = None
    total = 0
    previous: int | None = None
    for year, count in sorted(counts.items()):
        if count > limit:
            raise ValueError(f"{year} contiene {count} partes, por encima de {limit}")
        must_close = start is not None and (
            total + count > limit or previous is None or year != previous + 1
        )
        if must_close:
            blocks.append({"year_from": start, "year_to": int(end), "expected": total})
            start = None
            total = 0
        if start is None:
            start = year
        end = year
        total += count
        previous = year
    if start is not None:
        blocks.append({"year_from": start, "year_to": int(end), "expected": total})
    return blocks


def search_fields(year_from: int, year_to: int, pin: str) -> dict[str, Any]:
    return {
        "txtNumAnioDesde": year_from,
        "txtNumAnioHasta": year_to,
        "hdd_soypm": 0,
        "egif_pin": pin,
        "cbxNumPaginas": 100,
    }


def validate_location_zip(payload: bytes) -> dict[str, Any]:
    if payload[:4] != b"PK\x03\x04":
        raise PipelineError("La descarga EGIF no es ZIP")
    annual = Counter()
    provinces = Counter()
    communities = Counter()
    municipality_present = Counter()
    pairs = Counter()
    sheet_only = 0
    grid_only = 0
    neither = 0
    with_xy = 0
    ids = set()
    duplicate_ids = 0
    records = 0
    members = []
    generated_at = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        bad = archive.testzip()
        if bad:
            raise PipelineError(f"Miembro ZIP corrupto: {bad}")
        xml_members = [name for name in archive.namelist() if name.lower().endswith(".xml")]
        if not xml_members:
            raise PipelineError("El ZIP no contiene XML")
        for name in xml_members:
            info = archive.getinfo(name)
            members.append(
                {
                    "name": name,
                    "size_bytes": info.file_size,
                    "compressed_size_bytes": info.compress_size,
                    "crc32": f"{info.CRC:08x}",
                }
            )
            with archive.open(name) as handle:
                for _, element in ET.iterparse(handle, events=("end",)):
                    tag = local_name(element.tag)
                    if tag == "pifs" and element.attrib.get("generated"):
                        generated_at.append(element.attrib["generated"])
                        continue
                    if tag != "Pif":
                        continue
                    records += 1
                    record_id = child_text(element, "numeroparte")
                    common = first_child(element, "pif_comun")
                    location = first_child(element, "pif_localizacion")
                    year = child_text(common, "anio")
                    if year and year.isdigit():
                        annual[int(year)] += 1
                    province = child_text(location, "idprovincia")
                    community = child_text(location, "idcomunidad")
                    municipality = child_text(location, "idmunicipio")
                    if province:
                        provinces[province] += 1
                    if community:
                        communities[community] += 1
                    if municipality and municipality != "0":
                        municipality_present[province or "unknown"] += 1
                    sheet = child_text(location, "hoja")
                    grid = child_text(location, "cuadricula")
                    if sheet and grid:
                        pairs[(sheet.strip().upper(), grid.strip().upper())] += 1
                    elif sheet:
                        sheet_only += 1
                    elif grid:
                        grid_only += 1
                    else:
                        neither += 1
                    x = child_text(location, "x")
                    y = child_text(location, "y")
                    with_xy += int(bool(x and y))
                    if record_id:
                        duplicate_ids += int(record_id in ids)
                        ids.add(record_id)
                    element.clear()
    return {
        "record_count": records,
        "annual_counts": {str(year): annual[year] for year in sorted(annual)},
        "province_counts": dict(sorted(provinces.items(), key=lambda item: int(item[0]))),
        "community_counts": dict(sorted(communities.items(), key=lambda item: int(item[0]))),
        "municipality_nonzero_by_province": dict(
            sorted(municipality_present.items(), key=lambda item: item[0])
        ),
        "records_with_sheet_and_grid": sum(pairs.values()),
        "records_with_sheet_only": sheet_only,
        "records_with_grid_only": grid_only,
        "records_without_sheet_or_grid": neither,
        "records_with_xy": with_xy,
        "unique_sheet_grid_pairs": len(pairs),
        "duplicate_source_record_ids": duplicate_ids,
        "members": members,
        "source_generated_at": generated_at,
    }


def download_block(
    client: HttpClient,
    year_from: int,
    year_to: int,
    expected: int,
    *,
    chapters: str = CHAPTERS,
    export_block_size: int = 50_000,
) -> tuple[bytes, dict[str, Any]]:
    """Download one national EGIF query using the requested chapter mask.

    ``location_only`` keeps the historical ES-1.5 default.  ES-4A reuses the
    same public search/export protocol with the complete chapter mask; keeping
    the transport in one function avoids two subtly different implementations
    of the stateful exporter.
    """
    initial = client.get(SEARCH_URL)
    parser = SearchPageParser()
    parser.feed(initial.decode("utf-8", errors="replace"))
    pin = parser.inputs.get("egif_pin")
    if not pin:
        raise PipelineError("El buscador no devolvió egif_pin")
    page = client.post_multipart(SEARCH_URL, search_fields(year_from, year_to, pin))
    token, total, returned_pin, criteria = parse_search_page(page)
    if total != expected:
        raise PipelineError(
            f"EGIF {year_from}-{year_to}: buscador={total}, inventario={expected}"
        )
    state: dict[str, Any] = {
        "sBusqueda": criteria,
        "capitulos": chapters,
        "bloque": export_block_size,
        "skip": 0,
        "total": total,
        "sguid": returned_pin,
        "procesado": 0,
        "enpaketado": 0,
        "pakete": "",
        "tipo": "",
    }
    responses = []
    for _ in range(2_000):
        response = json.loads(
            client.post_form(
                EXPORT_URL,
                {
                    "__RequestVerificationToken": token,
                    "jsonCriterios": json.dumps(
                        state, ensure_ascii=False, separators=(",", ":")
                    ),
                },
            )
        )
        responses.append(response)
        if response.get("IsError"):
            raise PipelineError(f"Error del exportador EGIF: {response}")
        state.update(
            {
                "skip": response.get("Skip", state["skip"]),
                "bloque": response.get("Bloque", state["bloque"]),
                "sguid": response.get("Guid", state["sguid"]),
                "procesado": response.get("Procesado", state["procesado"]),
                "enpaketado": response.get("Empaketado", state["enpaketado"]),
                "pakete": response.get("Paquete", state["pakete"]),
            }
        )
        if response.get("IsFin"):
            guid = response.get("Guid") or state["sguid"]
            package = response.get("Paquete") or state["pakete"]
            url = DOWNLOAD_URL + "?" + urllib.parse.urlencode(
                {"guid": guid, "pakete": package}
            )
            payload = client.get(url)
            return payload, {
                "search_url": SEARCH_URL,
                "export_endpoint": EXPORT_URL,
                "download_url_template": DOWNLOAD_URL
                + "?guid=<session-guid>&pakete=<package>",
                "search_criteria": criteria,
                "chapters": chapters,
                "chapter_semantics": (
                    "Localización only; PIF identity/common fields retained by exporter"
                    if chapters == CHAPTERS
                    else "Requested EGIF chapter mask"
                ),
                "export_responses": responses,
            }
    raise PipelineError(f"EGIF {year_from}-{year_to}: exportación no finalizada")


def run(args: argparse.Namespace) -> dict[str, Any]:
    counts = expected_counts(args.counts)
    blocks = contiguous_blocks(counts, args.block_limit)
    args.output.mkdir(parents=True, exist_ok=True)
    previous = {}
    if args.manifest.exists():
        previous = json.loads(args.manifest.read_text(encoding="utf-8"))
    previous_blocks = {
        (item["year_from"], item["year_to"]): item
        for item in previous.get("blocks", [])
    }
    client = HttpClient(args.timeout, args.attempts)
    entries = []
    for block in blocks:
        year_from = block["year_from"]
        year_to = block["year_to"]
        expected = block["expected"]
        path = args.output / f"egif_locations_{year_from}_{year_to}.zip"
        cached = previous_blocks.get((year_from, year_to))
        if path.exists() and cached and not args.force:
            checksum_ok = sha256_file(path) == cached.get("sha256")
            validation = validate_location_zip(path.read_bytes()) if checksum_ok else {}
            if checksum_ok and validation.get("record_count") == expected:
                print(f"EGIF {year_from}-{year_to}: reutilizado", flush=True)
                entries.append(cached)
                continue
        print(f"EGIF {year_from}-{year_to}: descargando {expected}", flush=True)
        payload, source = download_block(client, year_from, year_to, expected)
        validation = validate_location_zip(payload)
        if validation["record_count"] != expected:
            raise PipelineError(
                f"EGIF {year_from}-{year_to}: ZIP={validation['record_count']}, esperado={expected}"
            )
        expected_annual = {
            str(year): counts[year] for year in range(year_from, year_to + 1)
        }
        if validation["annual_counts"] != expected_annual:
            raise PipelineError(
                f"EGIF {year_from}-{year_to}: discrepancia en recuentos anuales"
            )
        atomic_write_bytes(path, payload)
        entries.append(
            {
                "year_from": year_from,
                "year_to": year_to,
                "expected": expected,
                "retrieved_at": utc_now(),
                "raw_path": str(path.relative_to(ROOT)),
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "source": source,
                "validation": validation,
                "validation_status": "complete",
            }
        )
        atomic_write_json(
            args.manifest,
            {
                "schema_version": 1,
                "pipeline_version": PIPELINE_VERSION,
                "updated_at": utc_now(),
                "source": "MITECO public EGIF XML exporter",
                "selection": "national; Localización chapter only",
                "counts_source": str(args.counts.relative_to(ROOT)),
                "blocks": entries,
            },
        )
    payload = {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "updated_at": utc_now(),
        "source": "MITECO public EGIF XML exporter",
        "selection": "national; Localización chapter only",
        "counts_source": str(args.counts.relative_to(ROOT)),
        "blocks": entries,
        "totals": {
            "records": sum(item["validation"]["record_count"] for item in entries),
            "size_bytes": sum(item["size_bytes"] for item in entries),
            "blocks": len(entries),
        },
    }
    atomic_write_json(args.manifest, payload)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", type=Path, default=COUNTS_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--block-limit", type=int, default=50_000)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args)
    print(json.dumps(result["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
