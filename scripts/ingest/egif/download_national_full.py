#!/usr/bin/env python3
"""Reanudable downloader de snapshots XML EGIF nacionales completos.

Este programa prepara ES-4A; no normaliza datos ni genera assets web.  El
exportador público de EGIF permite hasta 50.000 partes por consulta, pero se
usa un bloque atómico por año: el recuento se puede contrastar de forma exacta,
una interrupción afecta como máximo a un año y no se mezclan años con modelos
de parte distintos.  Los ZIP y su manifiesto viven bajo ``data/raw/`` y están
ignorados por Git.

Ejemplos::

    # Muestra pequeña, reanudable
    python scripts/ingest/egif/download_national_full.py --resume \
      --period 1968 --period 1992 --period 2023

    # Adquisición completa que puede interrumpirse con Ctrl+C
    python scripts/ingest/egif/download_national_full.py --resume --all

    # Revalidar archivos ya adquiridos sin solicitar nada al servicio
    python scripts/ingest/egif/download_national_full.py --check --all
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

try:  # ejecución como módulo
    from .download_national_locations import (
        ROOT,
        download_block,
        expected_counts,
    )
    from .gva_1968_1992 import (
        DOWNLOAD_URL,
        EXPORT_URL,
        SEARCH_URL,
        HttpClient,
        PipelineError,
        atomic_write_bytes,
        atomic_write_json,
        sha256_bytes,
        sha256_file,
        utc_now,
    )
except ImportError:  # ejecución directa desde el repositorio
    from download_national_locations import ROOT, download_block, expected_counts  # type: ignore
    from gva_1968_1992 import (  # type: ignore
        DOWNLOAD_URL,
        EXPORT_URL,
        SEARCH_URL,
        HttpClient,
        PipelineError,
        atomic_write_bytes,
        atomic_write_json,
        sha256_bytes,
        sha256_file,
        utc_now,
    )


COUNTS_PATH = ROOT / "data/sources/spain_source_inventory.json"
OUTPUT_DIR = ROOT / "data/raw/egif/spain/full/2026-08-27"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
PIPELINE_VERSION = "es-4a-national-full-1"
FULL_CHAPTERS = "|".join(["1"] * 17)
SOURCE_LABEL = "MITECO public EGIF XML exporter"


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


def parse_period(value: str) -> tuple[int, int]:
    """Parse ``YYYY``, ``YYYY-YYYY`` or ``YYYY:YYYY`` inclusively."""
    text = value.strip()
    separator = ":" if ":" in text else "-" if "-" in text else None
    try:
        if separator:
            left, right = text.split(separator, 1)
            start, end = int(left), int(right)
        else:
            start = end = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value!r}") from exc
    if not (1900 <= start <= end <= 2100):
        raise argparse.ArgumentTypeError(f"Periodo inválido: {value!r}")
    return start, end


def annual_blocks(counts: dict[int, int], years: Iterable[int]) -> list[dict[str, Any]]:
    """Build stable one-year blocks and fail before a source-limit violation."""
    blocks = []
    for year in sorted(set(years)):
        if year not in counts:
            raise PipelineError(
                f"{year}: no existe un recuento nacional positivo en {COUNTS_PATH.name}"
            )
        expected = counts[year]
        if expected > 50_000:
            raise PipelineError(f"{year}: {expected} partes supera el límite oficial de 50.000")
        blocks.append(
            {
                "block_id": f"year-{year}",
                "year_from": year,
                "year_to": year,
                "expected_records": expected,
            }
        )
    return blocks


def selected_years(args: argparse.Namespace, counts: dict[int, int]) -> list[int]:
    if args.all:
        return sorted(counts)
    result: set[int] = set()
    for start, end in args.period or []:
        result.update(range(start, end + 1))
    if not result:
        raise PipelineError("Indica --all o al menos un --period")
    unavailable = sorted(year for year in result if year not in counts)
    if unavailable:
        raise PipelineError(
            "Sin recuento EGIF nacional positivo para: " + ", ".join(map(str, unavailable))
        )
    return sorted(result)


def validate_full_zip(payload: bytes) -> dict[str, Any]:
    """Validate a complete export without assuming a fixed historical schema.

    It only reads identity/common/location fields needed to prove the block
    count and year.  All original chapters remain untouched in the raw ZIP.
    """
    if len(payload) < 4 or payload[:4] != b"PK\x03\x04":
        raise PipelineError("La descarga EGIF no es un ZIP")
    annual: Counter[int] = Counter()
    provinces: Counter[str] = Counter()
    records = 0
    members: list[dict[str, Any]] = []
    generated_at: list[str] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        bad = archive.testzip()
        if bad:
            raise PipelineError(f"Miembro ZIP corrupto: {bad}")
        xml_members = [name for name in archive.namelist() if name.lower().endswith(".xml")]
        if not xml_members:
            raise PipelineError("El ZIP EGIF no contiene XML")
        for name in xml_members:
            info = archive.getinfo(name)
            if info.file_size > 750 * 1024 * 1024:
                raise PipelineError(f"XML descomprimido excesivo: {name}")
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
                    common = first_child(element, "pif_comun")
                    location = first_child(element, "pif_localizacion")
                    year = child_text(common, "anio")
                    province = child_text(location, "idprovincia")
                    if year and year.isdigit():
                        annual[int(year)] += 1
                    if province:
                        provinces[province] += 1
                    element.clear()
    return {
        "record_count": records,
        "annual_counts": {str(year): annual[year] for year in sorted(annual)},
        "province_counts": dict(sorted(provinces.items(), key=lambda item: item[0])),
        "members": members,
        "source_generated_at": generated_at,
    }


def empty_manifest(counts_path: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "source": SOURCE_LABEL,
        "source_urls": {
            "search": SEARCH_URL,
            "export": EXPORT_URL,
            "download_template": DOWNLOAD_URL + "?guid=<session-guid>&pakete=<package>",
        },
        "selection": "national complete EGIF XML; one calendar year per atomic block",
        "chapters": FULL_CHAPTERS,
        "counts_source": str(counts_path.relative_to(ROOT)),
        "blocks": [],
        "updated_at": utc_now(),
    }


def load_manifest(path: Path, counts_path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_manifest(counts_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Manifiesto ilegible: {path}: {exc}") from exc
    if payload.get("pipeline_version") != PIPELINE_VERSION:
        raise PipelineError(
            f"Manifiesto incompatible ({payload.get('pipeline_version')!r}); "
            "elige otro --manifest o conserva el snapshot original"
        )
    if not isinstance(payload.get("blocks"), list):
        raise PipelineError("Manifiesto sin lista blocks")
    return payload


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = utc_now()
    manifest["blocks"] = sorted(manifest["blocks"], key=lambda item: item["year_from"])
    complete = [item for item in manifest["blocks"] if item.get("status") == "complete"]
    manifest["totals"] = {
        "configured_blocks": len(manifest["blocks"]),
        "complete_blocks": len(complete),
        "complete_records": sum(int(item.get("records_downloaded", 0)) for item in complete),
        "complete_size_bytes": sum(int(item.get("size_bytes", 0)) for item in complete),
    }
    atomic_write_json(path, manifest)


def block_path(output: Path, block: dict[str, Any]) -> Path:
    return output / f"egif_full_{block['year_from']}.zip"


def portable_raw_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def new_entry(block: dict[str, Any], output: Path) -> dict[str, Any]:
    path = block_path(output, block)
    return {
        **block,
        "status": "pending",
        "parameters": {
            "year_from": block["year_from"],
            "year_to": block["year_to"],
            "chapter_mask": FULL_CHAPTERS,
            "export_block_size": 50_000,
        },
        "source_urls": {
            "search": SEARCH_URL,
            "export": EXPORT_URL,
            "download_template": DOWNLOAD_URL + "?guid=<session-guid>&pakete=<package>",
        },
        "raw_path": portable_raw_path(path),
        "errors": [],
        "warnings": [],
    }


def entry_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["block_id"]: item for item in manifest["blocks"]}


def validation_matches(entry: dict[str, Any], validation: dict[str, Any]) -> bool:
    expected = int(entry["expected_records"])
    year = str(entry["year_from"])
    return (
        validation.get("record_count") == expected
        and validation.get("annual_counts") == {year: expected}
    )


def verify_entry(entry: dict[str, Any], output: Path, *, deep: bool) -> tuple[bool, str, dict[str, Any] | None]:
    path = block_path(output, entry)
    if not path.exists():
        return False, "archivo raw ausente", None
    checksum = sha256_file(path)
    if checksum != entry.get("sha256"):
        return False, "checksum SHA-256 distinto", None
    if not deep:
        counts_ok = (
            entry.get("records_downloaded") == entry.get("expected_records")
            and entry.get("annual_counts_downloaded") == {str(entry["year_from"]): entry["expected_records"]}
        )
        return (counts_ok, "recuento manifest inválido" if not counts_ok else "ok", None)
    try:
        validation = validate_full_zip(path.read_bytes())
    except (OSError, PipelineError, zipfile.BadZipFile) as exc:
        return False, f"validación ZIP fallida: {exc}", None
    return validation_matches(entry, validation), "ok" if validation_matches(entry, validation) else "recuento ZIP inválido", validation


def mark_failed(entry: dict[str, Any], message: str) -> None:
    entry["status"] = "failed"
    entry["failed_at"] = utc_now()
    entry["errors"] = [message]


def run(args: argparse.Namespace) -> dict[str, Any]:
    counts = expected_counts(args.counts)
    years = selected_years(args, counts)
    blocks = annual_blocks(counts, years)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(args.manifest, args.counts)
    entries = entry_map(manifest)
    for block in blocks:
        entries.setdefault(block["block_id"], new_entry(block, args.output))
    manifest["blocks"] = list(entries.values())
    write_manifest(args.manifest, manifest)

    failures = 0
    client = HttpClient(args.timeout, args.attempts)
    for block in blocks:
        entry = entries[block["block_id"]]
        path = block_path(args.output, entry)
        if args.check:
            ok, message, validation = verify_entry(entry, args.output, deep=True)
            if ok:
                entry["status"] = "complete"
                if validation is not None:
                    entry["records_downloaded"] = validation["record_count"]
                    entry["annual_counts_downloaded"] = validation["annual_counts"]
                    entry["province_counts_downloaded"] = validation["province_counts"]
                    entry["validation"] = validation
                entry["checked_at"] = utc_now()
                entry["errors"] = []
                print(f"EGIF {block['year_from']}: comprobado", flush=True)
            else:
                mark_failed(entry, message)
                failures += 1
                print(f"EGIF {block['year_from']}: inválido — {message}", file=sys.stderr, flush=True)
            write_manifest(args.manifest, manifest)
            continue

        if entry.get("status") == "complete" and not args.force:
            ok, message, _ = verify_entry(entry, args.output, deep=False)
            if ok:
                print(f"EGIF {block['year_from']}: reutilizado", flush=True)
                continue
            mark_failed(entry, message)
            write_manifest(args.manifest, manifest)

        entry["status"] = "downloading"
        entry["started_at"] = utc_now()
        entry["errors"] = []
        write_manifest(args.manifest, manifest)
        print(
            f"EGIF {block['year_from']}: descargando {block['expected_records']:,} partes completas…",
            flush=True,
        )
        try:
            payload, source = download_block(
                client,
                block["year_from"],
                block["year_to"],
                block["expected_records"],
                chapters=FULL_CHAPTERS,
                export_block_size=50_000,
            )
            validation = validate_full_zip(payload)
            if not validation_matches(entry, validation):
                raise PipelineError(
                    f"recuento descargado {validation['record_count']} / {validation['annual_counts']} "
                    f"no coincide con {block['expected_records']}"
                )
            atomic_write_bytes(path, payload)
            entry.update(
                {
                    "status": "complete",
                    "retrieved_at": utc_now(),
                    "size_bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                    "records_service": block["expected_records"],
                    "records_downloaded": validation["record_count"],
                    "annual_counts_downloaded": validation["annual_counts"],
                    "province_counts_downloaded": validation["province_counts"],
                    "validation": validation,
                    "source": {
                        "search_url": source["search_url"],
                        "export_endpoint": source["export_endpoint"],
                        "download_url_template": source["download_url_template"],
                        "chapter_semantics": "Complete EGIF XML export (17 chapters)",
                        "export_iterations": len(source["export_responses"]),
                    },
                    "errors": [],
                }
            )
            print(f"EGIF {block['year_from']}: completo ({len(payload):,} bytes)", flush=True)
        except KeyboardInterrupt:
            mark_failed(entry, "interrumpido por usuario; se puede reanudar con --resume")
            write_manifest(args.manifest, manifest)
            raise
        except (OSError, PipelineError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            mark_failed(entry, str(exc))
            failures += 1
            print(f"EGIF {block['year_from']}: fallo — {exc}", file=sys.stderr, flush=True)
        finally:
            write_manifest(args.manifest, manifest)

    return {"manifest": manifest, "failures": failures, "selected_blocks": len(blocks)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=Path, default=COUNTS_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    selection = parser.add_mutually_exclusive_group(required=False)
    selection.add_argument("--all", action="store_true", help="todos los años con recuento nacional")
    parser.add_argument("--period", action="append", type=parse_period, help="año o intervalo inclusivo; repetible")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--resume", action="store_true", help="descarga o reutiliza bloques completos válidos")
    action.add_argument("--check", action="store_true", help="valida ZIP, checksum y recuento sin red")
    action.add_argument("--force", action="store_true", help="vuelve a descargar los bloques seleccionados")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--attempts", type=int, default=4)
    args = parser.parse_args(argv)
    if not args.all and not args.period:
        parser.error("indica --all o al menos un --period")
    # Mantener rutas absolutas hace que ``raw_path`` sea reproducible respecto
    # al repositorio incluso si quien ejecuta el comando está en otro cwd.
    args.counts = args.counts.resolve()
    args.output = args.output.resolve()
    args.manifest = args.manifest.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run(args)
    except KeyboardInterrupt:
        print("Interrumpido; los bloques completos permanecen reutilizables.", file=sys.stderr)
        return 130
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "selected_blocks": result["selected_blocks"],
                "failures": result["failures"],
                "totals": result["manifest"].get("totals", {}),
            },
            ensure_ascii=False,
        )
    )
    return 2 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
