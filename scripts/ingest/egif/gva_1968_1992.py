#!/usr/bin/env python3
"""Descarga, conserva y normaliza el snapshot EGIF valenciano 1968-1992.

El exportador XML es el que ofrece el buscador público oficial de EGIF. El
programa conserva cada ZIP sin alterarlo, valida los recuentos antes de
publicar el manifiesto y genera incendios administrativos sin geometría.

Uso habitual::

    python scripts/ingest/egif/gva_1968_1992.py all
    python scripts/ingest/egif/gva_1968_1992.py process

Las salidas raw y processed están ignoradas por Git. El manifiesto contiene
checksums y permite reutilizar snapshots válidos salvo con ``--force``.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import http.cookiejar
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator
from xml.etree import ElementTree as ET


SCHEMA_VERSION = 1
PIPELINE_VERSION = "cv-3.2-1"
BASE_URL = "https://servicio.mapa.gob.es/incendios"
SEARCH_URL = f"{BASE_URL}/Search/Publico"
EXPORT_URL = f"{BASE_URL}/Search/Public_XmlZip"
DOWNLOAD_URL = f"{BASE_URL}/Search/DescargaZipXml"
SPARQL_URL = "https://datos.iepnb.es/sparql"
REUSE_URL = "https://www.datosabiertos.miteco.gob.es/es/aviso-legal.html"
ATTRIBUTION = (
    "Origen de los datos: Ministerio para la Transición Ecológica y el "
    "Reto Demográfico."
)
PROVINCES = {
    "Alicante": {"search_id": 3, "code": "03", "expected": 2514},
    "Castellon": {"search_id": 12, "code": "12", "expected": 2600},
    "Valencia": {"search_id": 46, "code": "46", "expected": 4061},
}
FORM_PERIODS = (
    (1968, 1971, "historical_form_1"),
    (1972, 1979, "historical_form_2"),
    (1980, 1982, "historical_form_3"),
    (1983, 1988, "historical_form_4"),
    (1989, 1989, "historical_form_5"),
    (1990, 1992, "historical_form_6"),
)
ANNUAL_REPORT_1992_URL = (
    "https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/"
    "incendios-forestales/incendios_forestales_espania_1992_tcm30-132589.pdf"
)
COORDINATE_KEYS = (
    "x", "y", "coordx", "coordy", "coordenadax", "coordenaday",
    "utmx", "utmy", "longitud", "latitud", "huso", "iddatum", "datum",
)
IGNORED_DUPLICATE_FINGERPRINT_KEYS = {"idpif", "numeroparte"}


class PipelineError(RuntimeError):
    """Error que impide considerar completa o fiable una salida."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
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


def atomic_write_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")
    atomic_write_bytes(path, payload)


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class SearchPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: dict[str, str] = {}
        self.search_criteria: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "input":
            key = values.get("name") or values.get("id")
            if key:
                self.inputs[key] = values.get("value", "")
        criteria = values.get("data-busqueda")
        if criteria:
            self.search_criteria = criteria


@dataclass
class HttpClient:
    timeout: float
    attempts: int

    def __post_init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, request: urllib.request.Request) -> bytes:
        last_error: BaseException | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    payload = response.read()
                    if response.status < 200 or response.status >= 300:
                        raise PipelineError(f"HTTP {response.status}: {request.full_url}")
                    return payload
            except (urllib.error.URLError, TimeoutError, OSError, PipelineError) as exc:
                last_error = exc
                if attempt == self.attempts:
                    break
                time.sleep(min(2 ** (attempt - 1), 8))
        raise PipelineError(f"Fallo HTTP tras {self.attempts} intentos: {request.full_url}: {last_error}")

    def get(self, url: str, headers: dict[str, str] | None = None) -> bytes:
        request = urllib.request.Request(url, headers=headers or {"User-Agent": "atlas-incendios-cv3.2/1"})
        return self.request(request)

    def post_form(self, url: str, fields: dict[str, Any]) -> bytes:
        body = urllib.parse.urlencode({key: str(value) for key, value in fields.items()}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "atlas-incendios-cv3.2/1",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        return self.request(request)

    def post_multipart(self, url: str, fields: dict[str, Any]) -> bytes:
        boundary = f"----atlas-incendios-{int(time.time() * 1000)}"
        chunks: list[bytes] = []
        for key, value in fields.items():
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ])
        chunks.append(f"--{boundary}--\r\n".encode())
        request = urllib.request.Request(
            url,
            data=b"".join(chunks),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "atlas-incendios-cv3.2/1",
            },
        )
        return self.request(request)


def search_fields(province_id: int, pin: str) -> dict[str, Any]:
    return {
        "txtNumAnioDesde": 1968,
        "txtNumAnioHasta": 1992,
        "cbxCCAA_Common2": 9,
        "cbxProvincias_Common2": province_id,
        "hdd_ca2": 9,
        "hdd_pr2": province_id,
        "hdd_pr2Aux": province_id,
        "hdd_soypm": 0,
        "egif_pin": pin,
        "cbxNumPaginas": 100,
    }


def parse_search_page(payload: bytes) -> tuple[str, int, str, str]:
    parser = SearchPageParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    token = parser.inputs.get("__RequestVerificationToken")
    total_text = parser.inputs.get("hddPifTotal")
    pin = parser.inputs.get("egif_pin")
    if not token or total_text is None or not pin or not parser.search_criteria:
        raise PipelineError("La respuesta del buscador no contiene token, total, PIN o criterios")
    try:
        total = int(total_text)
    except ValueError as exc:
        raise PipelineError(f"Total EGIF inválido: {total_text!r}") from exc
    return token, total, pin, parser.search_criteria


def validate_zip(payload: bytes) -> dict[str, Any]:
    if len(payload) < 4 or payload[:4] != b"PK\x03\x04":
        raise PipelineError("La descarga EGIF no es un ZIP")
    province_counts: Counter[str] = Counter()
    annual_counts: Counter[int] = Counter()
    record_count = 0
    members: list[dict[str, Any]] = []
    xsd_schemas: list[dict[str, Any]] = []
    source_generated_at: list[str] = []
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        bad = archive.testzip()
        if bad:
            raise PipelineError(f"Miembro ZIP corrupto: {bad}")
        xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
        if not xml_names:
            raise PipelineError("El ZIP EGIF no contiene XML")
        for name in xml_names:
            info = archive.getinfo(name)
            if info.file_size > 500 * 1024 * 1024:
                raise PipelineError(f"XML descomprimido excesivo: {name}")
            with archive.open(name) as handle:
                for _, element in ET.iterparse(handle, events=("end",)):
                    local_tag = strip_namespace(element.tag)
                    if local_tag == "schema" and element.tag.startswith("{http://www.w3.org/2001/XMLSchema}"):
                        serialized = ET.tostring(element, encoding="utf-8")
                        declarations = [
                            child.attrib.get("name") for child in element.iter()
                            if strip_namespace(child.tag) == "element" and child.attrib.get("name")
                        ]
                        xsd_schemas.append({
                            "xml_member": name,
                            "sha256": sha256_bytes(serialized),
                            "element_declaration_count": len(declarations),
                        })
                        continue
                    if local_tag == "pifs" and element.attrib.get("generated"):
                        source_generated_at.append(element.attrib["generated"])
                        continue
                    if local_tag != "Pif":
                        continue
                    record_count += 1
                    year = child_text(first_child(element, "pif_comun"), "anio")
                    province = child_text(first_child(element, "pif_localizacion"), "idprovincia")
                    if year and year.isdigit():
                        annual_counts[int(year)] += 1
                    if province:
                        province_counts[province] += 1
                    element.clear()
            members.append({
                "name": name,
                "size_bytes": info.file_size,
                "compressed_size_bytes": info.compress_size,
                "crc32": f"{info.CRC:08x}",
            })
    return {
        "record_count": record_count,
        "annual_counts": {str(year): annual_counts[year] for year in range(1968, 1993)},
        "province_counts": dict(sorted(province_counts.items())),
        "members": members,
        "xsd_schemas": xsd_schemas,
        "source_generated_at": source_generated_at,
    }


def first_child(element: ET.Element | None, tag: str) -> ET.Element | None:
    if element is None:
        return None
    return next((child for child in element if strip_namespace(child.tag) == tag), None)


def child_text(element: ET.Element | None, tag: str) -> str | None:
    child = first_child(element, tag)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def download_province(client: HttpClient, name: str, config: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    initial = client.get(SEARCH_URL)
    initial_parser = SearchPageParser()
    initial_parser.feed(initial.decode("utf-8", errors="replace"))
    pin = initial_parser.inputs.get("egif_pin")
    if not pin:
        raise PipelineError("No se obtuvo egif_pin del buscador público")
    result_page = client.post_multipart(SEARCH_URL, search_fields(config["search_id"], pin))
    token, total, returned_pin, criteria = parse_search_page(result_page)
    if total != config["expected"]:
        raise PipelineError(f"{name}: el servicio devuelve {total}; se esperaban {config['expected']}")

    state: dict[str, Any] = {
        "sBusqueda": criteria,
        "capitulos": "|".join(["1"] * 17),
        "bloque": 40000,
        "skip": 0,
        "total": total,
        "sguid": returned_pin,
        "procesado": 0,
        "enpaketado": 0,
        "pakete": "",
        "tipo": "",
    }
    export_responses: list[dict[str, Any]] = []
    for _ in range(1000):
        raw_response = client.post_form(EXPORT_URL, {
            "__RequestVerificationToken": token,
            "jsonCriterios": json.dumps(state, ensure_ascii=False, separators=(",", ":")),
        })
        try:
            response = json.loads(raw_response)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PipelineError(f"{name}: respuesta de exportación no JSON") from exc
        export_responses.append(response)
        if response.get("IsError"):
            raise PipelineError(f"{name}: error EGIF en exportación: {response}")
        state.update({
            "skip": response.get("Skip", state["skip"]),
            "bloque": response.get("Bloque", state["bloque"]),
            "sguid": response.get("Guid", state["sguid"]),
            "procesado": response.get("Procesado", state["procesado"]),
            "enpaketado": response.get("Empaketado", state["enpaketado"]),
            "pakete": response.get("Paquete", state["pakete"]),
        })
        if response.get("IsFin"):
            guid = response.get("Guid")
            package = response.get("Paquete", "")
            if not guid:
                raise PipelineError(f"{name}: exportación final sin GUID")
            url = DOWNLOAD_URL + "?" + urllib.parse.urlencode({"guid": guid, "pakete": package})
            payload = client.get(url)
            validation = validate_zip(payload)
            validation.update({
                "service_total": total,
                "search_criteria": criteria,
                "search_parameters": search_fields(config["search_id"], "<session-pin>"),
                "export_iterations": len(export_responses),
                "download_url_template": DOWNLOAD_URL + "?guid=<session-guid>&pakete=<package>",
            })
            return payload, validation
    raise PipelineError(f"{name}: exportación no finalizada tras 1000 iteraciones")


def sparql_query(client: HttpClient, query: str) -> bytes:
    url = SPARQL_URL + "?" + urllib.parse.urlencode({"query": query, "format": "application/sparql-results+json"})
    payload = client.get(url, headers={
        "Accept": "application/sparql-results+json",
        "User-Agent": "atlas-incendios-cv3.2/1",
    })
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PipelineError("El endpoint SPARQL oficial no devolvió JSON") from exc
    if "results" not in parsed:
        raise PipelineError("Respuesta SPARQL sin results")
    return payload


MUNICIPALITY_QUERY = """
SELECT DISTINCT ?municipality ?name ?code WHERE {
  ?municipality <http://www.geonames.org/ontology#officialName> ?name ;
    <http://vocab.linkeddata.es/datosabiertos/def/sector-publico/territorio#codigoINE> ?code .
  FILTER(STRSTARTS(STR(?municipality),
    "https://datos.iepnb.es/recurso/sector-publico/medio-ambiente/incendios-forestales/Municipio/CODINE/"))
  FILTER(STRSTARTS(STR(?municipality),
    "https://datos.iepnb.es/recurso/sector-publico/medio-ambiente/incendios-forestales/Municipio/CODINE/03") ||
    STRSTARTS(STR(?municipality),
    "https://datos.iepnb.es/recurso/sector-publico/medio-ambiente/incendios-forestales/Municipio/CODINE/12") ||
    STRSTARTS(STR(?municipality),
    "https://datos.iepnb.es/recurso/sector-publico/medio-ambiente/incendios-forestales/Municipio/CODINE/46"))
}
ORDER BY ?municipality
""".strip()

CAUSE_QUERY = """
SELECT DISTINCT ?cause ?label ?description WHERE {
  ?cause <http://www.w3.org/2000/01/rdf-schema#label> ?label .
  OPTIONAL {
    ?cause <http://purl.org/dc/elements/1.1/description> ?description .
    FILTER(LANG(?description) = "es")
  }
  FILTER(STRSTARTS(STR(?cause),
    "https://datos.iepnb.es/recurso/sector-publico/medio-ambiente/incendios-forestales/Causa/España/"))
}
ORDER BY ?cause
""".strip()


def expected_annual_counts(inventory: dict[str, Any], province: str) -> dict[str, int]:
    return {str(row["year"]): int(row[province]) for row in inventory["counts"]["by_year"]}


def download_all(args: argparse.Namespace, inventory: dict[str, Any]) -> dict[str, Any]:
    raw_dir = args.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    previous: dict[str, Any] = {}
    if args.manifest.exists():
        try:
            previous = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
    previous_provinces = {item.get("province"): item for item in previous.get("provinces", [])}
    client = HttpClient(args.timeout, args.attempts)
    entries: list[dict[str, Any]] = []
    acquired_at = utc_now()

    for name, config in PROVINCES.items():
        path = raw_dir / f"egif_{config['code']}_1968_1992.zip"
        cached = previous_provinces.get(name)
        if not args.force and cached and path.exists():
            checksum_ok = sha256_file(path) == cached.get("sha256")
            validation = validate_zip(path.read_bytes()) if checksum_ok else {}
            count_ok = validation.get("record_count") == config["expected"]
            annual_ok = validation.get("annual_counts") == expected_annual_counts(inventory, name)
            province_ok = validation.get("province_counts") == {str(config["search_id"]): config["expected"]}
            if checksum_ok and count_ok and annual_ok and province_ok and cached.get("validation_status") == "complete":
                cached = copy.deepcopy(cached)
                try:
                    cached["raw_path"] = str(path.resolve().relative_to(args.inventory.resolve().parents[2]))
                except ValueError:
                    cached["raw_path"] = str(path)
                cached["members"] = validation["members"]
                cached["xsd_schemas"] = validation["xsd_schemas"]
                cached["source_generated_at"] = validation["source_generated_at"]
                entries.append(cached)
                print(f"{name}: snapshot válido reutilizado ({config['expected']} registros)")
                continue
        print(f"{name}: solicitando exportación XML oficial…")
        payload, validation = download_province(client, name, config)
        if validation["record_count"] != config["expected"]:
            raise PipelineError(
                f"{name}: ZIP contiene {validation['record_count']}; esperados {config['expected']}"
            )
        annual_expected = expected_annual_counts(inventory, name)
        if validation["annual_counts"] != annual_expected:
            raise PipelineError(
                f"{name}: recuento anual no coincide: {validation['annual_counts']} != {annual_expected}"
            )
        if validation["province_counts"] != {str(config["search_id"]): config["expected"]}:
            raise PipelineError(
                f"{name}: códigos provinciales inesperados: {validation['province_counts']}"
            )
        atomic_write_bytes(path, payload)
        try:
            stored_path = str(path.resolve().relative_to(args.inventory.resolve().parents[2]))
        except ValueError:
            stored_path = str(path)
        entries.append({
            "province": name,
            "province_code": config["code"],
            "search_province_id": config["search_id"],
            "period": {"start_year": 1968, "end_year": 1992},
            "source_url": SEARCH_URL,
            "export_endpoint": EXPORT_URL,
            "retrieved_at": acquired_at,
            "raw_path": stored_path,
            "format": "ZIP containing complete EGIF XML export",
            "size_bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "feature_count_expected": config["expected"],
            "feature_count_service": validation["service_total"],
            "feature_count_downloaded": validation["record_count"],
            "annual_counts_expected": annual_expected,
            "annual_counts_downloaded": validation["annual_counts"],
            "province_counts_in_xml": validation["province_counts"],
            "members": validation["members"],
            "xsd_schemas": validation["xsd_schemas"],
            "source_generated_at": validation["source_generated_at"],
            "search_criteria": validation["search_criteria"],
            "search_parameters": validation["search_parameters"],
            "export_iterations": validation["export_iterations"],
            "download_url_template": validation["download_url_template"],
            "validation_status": "complete",
            "errors": [],
            "warnings": [],
        })

    dictionary_entries: dict[str, Any] = {}
    dictionary_dir = raw_dir / "dictionaries"
    for name, query in (("municipalities", MUNICIPALITY_QUERY), ("causes", CAUSE_QUERY)):
        path = dictionary_dir / f"{name}.sparql.json"
        try:
            if not args.force and path.exists() and previous.get("dictionaries", {}).get(name):
                old = previous["dictionaries"][name]
                if old.get("row_count", 0) > 0 and sha256_file(path) == old.get("sha256"):
                    old = copy.deepcopy(old)
                    try:
                        old["raw_path"] = str(path.resolve().relative_to(args.inventory.resolve().parents[2]))
                    except ValueError:
                        old["raw_path"] = str(path)
                    dictionary_entries[name] = old
                    continue
            payload = sparql_query(client, query)
            atomic_write_bytes(path, payload)
            row_count = len(json.loads(payload)["results"]["bindings"])
            try:
                stored_dictionary_path = str(path.resolve().relative_to(args.inventory.resolve().parents[2]))
            except ValueError:
                stored_dictionary_path = str(path)
            dictionary_entries[name] = {
                "source_url": SPARQL_URL,
                "query": query,
                "retrieved_at": acquired_at,
                "raw_path": stored_dictionary_path,
                "format": "SPARQL Results JSON",
                "row_count": row_count,
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "license": "CC BY 4.0 for the linked EGIF dataset (1983-2015)",
            }
        except PipelineError as exc:
            dictionary_entries[name] = {
                "source_url": SPARQL_URL,
                "query": query,
                "retrieved_at": acquired_at,
                "status": "unavailable",
                "error": str(exc),
            }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "phase": "CV-3.2",
        "dataset": "EGIF Comunitat Valenciana 1968-1992",
        "created_at": acquired_at,
        "source_authority": "Ministerio para la Transición Ecológica y el Reto Demográfico",
        "source_system": "Estadística General de Incendios Forestales (EGIF)",
        "period": {"start_year": 1968, "end_year": 1992},
        "expected_total": 9175,
        "downloaded_total": sum(entry["feature_count_downloaded"] for entry in entries),
        "validation_status": "complete",
        "provinces": entries,
        "dictionaries": dictionary_entries,
        "reuse": {
            "terms_url": REUSE_URL,
            "attribution": ATTRIBUTION,
            "summary": "General MITECO open-data reuse terms; linked dictionary snapshot is CC BY 4.0.",
            "redistribution_assessment": "allowed_with_attribution_and_preserved_reuse_metadata",
            "publication_action": "withheld_by_project_during_CV-3.2",
        },
        "notes": [
            "Raw ZIP snapshots are byte-for-byte responses from the public EGIF exporter.",
            "The current XML exporter maps historical records to one current hierarchical XML/XSD representation.",
            "No geometries are created or inferred by this pipeline.",
        ],
    }
    if manifest["downloaded_total"] != manifest["expected_total"]:
        raise PipelineError("El total descargado no coincide con 9.175")
    atomic_write_json(args.manifest, manifest)
    return manifest


def element_to_value(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        text = element.text.strip() if element.text else None
        if element.attrib:
            value: dict[str, Any] = {"_attributes": dict(element.attrib)}
            if text:
                value["_text"] = text
            return value
        return text or None
    result: dict[str, Any] = {}
    if element.attrib:
        result["_attributes"] = dict(element.attrib)
    for child in children:
        key = strip_namespace(child.tag)
        value = element_to_value(child)
        if key in result:
            if not isinstance(result[key], list):
                result[key] = [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    return result


def iter_records(path: Path) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".xml"):
                continue
            with archive.open(name) as handle:
                for _, element in ET.iterparse(handle, events=("end",)):
                    if strip_namespace(element.tag) != "Pif":
                        continue
                    value = element_to_value(element)
                    if not isinstance(value, dict):
                        raise PipelineError(f"Registro Pif no estructurado en {path}:{name}")
                    yield value, {"xml_member": name}
                    element.clear()


def nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if isinstance(current, list):
            current = current[0] if current else None
    return current


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None
    return None


def as_int(value: Any) -> int | None:
    text = as_text(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def as_decimal(value: Any) -> Decimal | None:
    text = as_text(value)
    if text is None:
        return None
    try:
        result = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def decimal_json(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def parse_datetime(value: Any) -> dt.datetime | None:
    text = as_text(value)
    if not text:
        return None
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def model_for_year(year: int | None) -> str:
    if year is not None:
        for start, end, model in FORM_PERIODS:
            if start <= year <= end:
                return model
    return "unknown"


def coverage_for_year(year: int | None) -> str:
    if year is None:
        return "unknown"
    if year <= 1979:
        return "selective"
    if year <= 1991:
        return "transitional"
    return "systematic_or_near_systematic"


def load_sparql_dictionary(path: Path, resource_key: str, label_keys: tuple[str, ...]) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for row in payload.get("results", {}).get("bindings", []):
        resource = row.get(resource_key, {}).get("value", "")
        code = resource.rstrip("/").rsplit("/", 1)[-1]
        label = next((row.get(key, {}).get("value") for key in label_keys if row.get(key, {}).get("value")), None)
        if code and label:
            result[code] = label
    return result


def walk_leaf_paths(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            yield from walk_leaf_paths(child, child_prefix)
    elif isinstance(value, list):
        for child in value:
            yield from walk_leaf_paths(child, prefix)
    else:
        yield prefix, value


def lexical_type(value: Any) -> str:
    text = as_text(value)
    if text is None:
        return "null"
    if text in {"True", "False", "true", "false"}:
        return "boolean"
    if re.fullmatch(r"[-+]?\d+", text):
        return "integer"
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)", text):
        return "decimal"
    if parse_datetime(text):
        return "datetime"
    return "string"


def remove_identity_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: remove_identity_fields(child) for key, child in value.items() if key not in IGNORED_DUPLICATE_FINGERPRINT_KEYS}
    if isinstance(value, list):
        return [remove_identity_fields(child) for child in value]
    return value


def normalized_record(
    original: dict[str, Any],
    province_name: str,
    province_code: str,
    manifest_entry: dict[str, Any],
    member: str,
    municipality_names: dict[str, str],
    cause_names: dict[str, str],
) -> dict[str, Any]:
    common = nested(original, "pif_comun") or {}
    location = nested(original, "pif_localizacion") or {}
    times = nested(original, "pif_tiempos") or {}
    losses = nested(original, "pif_perdidas") or {}
    cause_source = nested(original, "pif_causa") or {}
    source_record_id = as_text(original.get("numeroparte")) or as_text(nested(common, "numeroparte"))
    source_database_id = as_text(original.get("idpif")) or as_text(nested(common, "idpif"))
    year = as_int(nested(common, "anio"))
    if year is None and source_record_id and source_record_id[:4].isdigit():
        year = int(source_record_id[:4])
    municipality_code_raw = as_int(nested(location, "idmunicipio"))
    codine = None
    if municipality_code_raw is not None and municipality_code_raw > 0:
        codine = f"{province_code}{municipality_code_raw:03d}"
    municipality = municipality_names.get(codine) if codine else None
    cause_code = as_text(nested(cause_source, "idcausa"))
    cause = cause_names.get(cause_code) if cause_code and cause_code != "0" else None
    cause_status = "unknown" if cause_code in {None, "0", "500"} else "reported"
    wooded = as_decimal(nested(losses, "superficiearboladatotal"))
    nonwooded = as_decimal(nested(losses, "superficienoarboladatotal"))
    forest = wooded + nonwooded if wooded is not None and nonwooded is not None else wooded or nonwooded
    agricultural = as_decimal(nested(losses, "superficienoarboladaagricola"))
    other_nonforest = as_decimal(nested(losses, "superficienoarboladaotras"))
    total_parts = [part for part in (forest, agricultural, other_nonforest) if part is not None]
    total_area = sum(total_parts, Decimal("0")) if total_parts else None
    detection_text = as_text(nested(times, "deteccion"))
    extinction_text = as_text(nested(times, "extinguido"))
    paraje = as_text(nested(location, "paraje")) or as_text(nested(location, "nombreparaje"))
    hoja = as_text(nested(location, "hoja"))
    cuadricula = as_text(nested(location, "cuadricula"))
    raw_coordinates = {key: as_text(nested(location, key)) for key in COORDINATE_KEYS}
    raw_coordinates = {key: value for key, value in raw_coordinates.items() if value is not None}
    spatial_text_available = any([municipality, municipality_code_raw not in (None, 0), paraje, hoja, cuadricula, raw_coordinates])
    if raw_coordinates:
        location_quality = "raw_coordinate_unvalidated"
    elif hoja or cuadricula:
        location_quality = "map_sheet_or_grid"
    elif municipality:
        location_quality = "municipality"
    elif paraje:
        location_quality = "textual"
    else:
        location_quality = "none"
    return {
        "fire_id": None,
        "identity_status": None,
        "episode_identity_status": "unresolved",
        "source_record_id": source_record_id,
        "source_database_id": source_database_id,
        "year": year,
        "detection_date": detection_text,
        "extinction_date": extinction_text,
        "province": province_name,
        "province_code": province_code,
        "municipality": municipality,
        "municipality_source_code": municipality_code_raw,
        "municipality_codine": codine,
        "paraje": paraje,
        "reported_total_area_ha": decimal_json(total_area),
        "reported_forest_area_ha": decimal_json(forest),
        "reported_wooded_area_ha": decimal_json(wooded),
        "reported_nonwooded_area_ha": decimal_json(nonwooded),
        "reported_agricultural_area_ha": decimal_json(agricultural),
        "reported_other_nonforest_area_ha": decimal_json(other_nonforest),
        "cause": cause,
        "cause_source_code": cause_code,
        "cause_status": cause_status,
        "is_gif_ge_500_ha": bool(forest is not None and forest >= Decimal("500")),
        "location_original": {
            "coordinates": raw_coordinates or None,
            "map_sheet": hoja,
            "grid": cuadricula,
            "municipality_code": municipality_code_raw,
            "paraje": paraje,
            "affected_municipalities_count": as_int(nested(location, "nummunicipiosafectados")),
            "parte_monte": original.get("ParteMonte"),
        },
        "coordinate_status": "raw_unvalidated" if raw_coordinates else "absent",
        "coordinate_quality": "unknown" if raw_coordinates else "not_available",
        "derived_coordinates_epsg4326": None,
        "location_quality": location_quality,
        "has_any_spatial_information": bool(spatial_text_available),
        "geometry": None,
        "geometry_availability": "none",
        "historical_geometry_candidates": [],
        "form_model": model_for_year(year),
        "form_model_assignment_basis": "documented year range; not an explicit XML field",
        "coverage_status": coverage_for_year(year),
        "source": "MITECO_EGIF",
        "provenance": {
            "source_system": "EGIF public complete XML export",
            "source_url": manifest_entry["source_url"],
            "raw_path": manifest_entry["raw_path"],
            "raw_sha256": manifest_entry["sha256"],
            "retrieved_at": manifest_entry["retrieved_at"],
            "xml_member": member,
            "normalization_pipeline": PIPELINE_VERSION,
        },
        "original_attributes": original,
    }


def assign_identity(records: list[dict[str, Any]]) -> dict[str, Any]:
    report_ids = Counter(record["source_record_id"] for record in records if record["source_record_id"])
    database_ids = Counter(record["source_database_id"] for record in records if record["source_database_id"])
    ambiguous = 0
    for index, record in enumerate(records):
        report_id = record["source_record_id"]
        database_id = record["source_database_id"]
        structurally_valid = bool(
            report_id
            and re.fullmatch(r"\d{10}", report_id)
            and record["year"] == int(report_id[:4])
            and record["province_code"] == report_id[4:6]
        )
        if report_id and report_ids[report_id] == 1 and structurally_valid:
            record["fire_id"] = f"egif-record:{report_id}"
            record["identity_status"] = "source_record_only"
        else:
            basis = f"{record['province_code']}|{report_id}|{database_id}|{index}"
            record["fire_id"] = "egif-record:" + hashlib.sha256(basis.encode()).hexdigest()[:20]
            record["identity_status"] = "ambiguous"
            ambiguous += 1
    return {
        "source_report_id_unique": len(report_ids),
        "source_report_id_duplicate_values": sorted(key for key, count in report_ids.items() if count > 1),
        "source_database_id_unique": len(database_ids),
        "source_database_id_duplicate_values": sorted(key for key, count in database_ids.items() if count > 1),
        "ambiguous_records": ambiguous,
        "source_record_only_records": len(records) - ambiguous,
        "incident_level_identity_available": False,
        "rule": "egif-record:<NumeroParte> identifies a unique administrative report when NumeroParte agrees with year and province; it does not assert a unique physical wildfire episode. Invalid or duplicated keys use a stable hashed per-record ID with identity_status=ambiguous.",
        "reason": "The 1992 definitive publication describes the Marines/Altura fire as one cross-province episode while the current XML contains several administrative reports compatible with parts of that episode.",
    }


def metrics_template() -> dict[str, int]:
    return {
        "records": 0,
        "gif_ge_500_ha": 0,
        "with_municipality": 0,
        "with_paraje": 0,
        "with_surface": 0,
        "with_cause": 0,
        "with_known_cause": 0,
        "with_any_spatial_information": 0,
        "with_map_sheet_or_grid": 0,
        "with_raw_coordinates": 0,
        "with_safely_transformable_coordinates": 0,
        "without_usable_spatial_location": 0,
    }


def update_metrics(metrics: dict[str, int], record: dict[str, Any]) -> None:
    metrics["records"] += 1
    metrics["gif_ge_500_ha"] += int(record["is_gif_ge_500_ha"])
    metrics["with_municipality"] += int(record["municipality"] is not None)
    metrics["with_paraje"] += int(record["paraje"] is not None)
    metrics["with_surface"] += int(record["reported_forest_area_ha"] is not None)
    metrics["with_cause"] += int(record["cause_source_code"] is not None)
    metrics["with_known_cause"] += int(record["cause_status"] == "reported")
    metrics["with_any_spatial_information"] += int(record["has_any_spatial_information"])
    metrics["with_map_sheet_or_grid"] += int(
        record["location_original"]["map_sheet"] is not None
        or record["location_original"]["grid"] is not None
    )
    metrics["with_raw_coordinates"] += int(record["coordinate_status"] == "raw_unvalidated")
    metrics["with_safely_transformable_coordinates"] += int(record["derived_coordinates_epsg4326"] is not None)
    metrics["without_usable_spatial_location"] += int(not record["has_any_spatial_information"])


def audit_records(records: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    totals = metrics_template()
    by_year_province: dict[tuple[int, str], dict[str, int]] = {}
    anomalies: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    schema: dict[str, dict[str, Any]] = defaultdict(lambda: defaultdict(lambda: {
        "records_with_value": 0, "lexical_types": Counter(), "examples": []
    }))
    model_totals = Counter(record["form_model"] for record in records)
    fingerprints: defaultdict[str, list[str]] = defaultdict(list)
    forest_gif_by_year_province: Counter[tuple[int, str]] = Counter()
    total_area_gif_by_year_province: Counter[tuple[int, str]] = Counter()
    gif_basis_differences: list[dict[str, Any]] = []
    records_with_parte_monte = 0
    parte_monte_entry_count = 0
    max_parte_monte_entries = 0
    parte_monte_catalog_code_entries = 0

    for record in records:
        update_metrics(totals, record)
        key = (record["year"], record["province"])
        if key not in by_year_province:
            by_year_province[key] = metrics_template()
        update_metrics(by_year_province[key], record)
        rid = record["source_record_id"]
        forest_is_gif = record["reported_forest_area_ha"] is not None and record["reported_forest_area_ha"] >= 500
        total_is_gif = record["reported_total_area_ha"] is not None and record["reported_total_area_ha"] >= 500
        forest_gif_by_year_province[key] += int(forest_is_gif)
        total_area_gif_by_year_province[key] += int(total_is_gif)
        if forest_is_gif != total_is_gif:
            gif_basis_differences.append({
                "source_record_id": rid,
                "year": record["year"],
                "province": record["province"],
                "reported_forest_area_ha": record["reported_forest_area_ha"],
                "reported_total_area_ha": record["reported_total_area_ha"],
            })
        detection = parse_datetime(record["detection_date"])
        extinction = parse_datetime(record["extinction_date"])
        if record["detection_date"] and detection is None:
            anomalies["invalid_detection_date"].append({"source_record_id": rid, "value": record["detection_date"]})
        if record["extinction_date"] and extinction is None:
            anomalies["invalid_extinction_date"].append({"source_record_id": rid, "value": record["extinction_date"]})
        if detection and extinction and extinction < detection:
            anomalies["extinction_before_detection"].append({"source_record_id": rid, "detection": record["detection_date"], "extinction": record["extinction_date"]})
        if detection and record["year"] != detection.year:
            anomalies["detection_year_mismatch"].append({"source_record_id": rid, "record_year": record["year"], "detection": record["detection_date"]})
        if rid and re.fullmatch(r"\d{10}", rid):
            if rid[:4] != str(record["year"]) or rid[4:6] != record["province_code"]:
                anomalies["source_report_id_year_or_province_mismatch"].append({"source_record_id": rid, "year": record["year"], "province_code": record["province_code"]})
        source_province = as_int(nested(record["original_attributes"], "pif_localizacion", "idprovincia"))
        if source_province != int(record["province_code"]):
            anomalies["source_province_mismatch"].append({
                "source_record_id": rid, "expected": record["province_code"], "observed": source_province,
            })
        if record["municipality_source_code"] not in (None, 0) and record["municipality"] is None:
            anomalies["unresolved_municipality_code"].append({
                "source_record_id": rid,
                "province": record["province"],
                "municipality_source_code": record["municipality_source_code"],
            })
        surface = record["reported_forest_area_ha"]
        if surface is not None and surface < 0:
            anomalies["negative_surface"].append({"source_record_id": rid, "surface_ha": surface})
        elif surface == 0:
            anomalies["zero_surface"].append({"source_record_id": rid})
        elif surface is not None and surface > 100000:
            anomalies["surface_over_100000_ha"].append({"source_record_id": rid, "surface_ha": surface})
        original = record["original_attributes"]
        parte_monte = original.get("ParteMonte")
        parte_monte_values = parte_monte if isinstance(parte_monte, list) else [parte_monte]
        parte_monte_values = [monte for monte in parte_monte_values if isinstance(monte, dict)]
        if parte_monte_values:
            records_with_parte_monte += 1
            parte_monte_entry_count += len(parte_monte_values)
            max_parte_monte_entries = max(max_parte_monte_entries, len(parte_monte_values))
            parte_monte_catalog_code_entries += sum(
                as_text(monte.get("idcatalogomonte")) not in (None, "0")
                for monte in parte_monte_values
            )
        for monte in parte_monte_values:
            duplicated_scalar = monte.get("daniosconaprovechamiento") if isinstance(monte, dict) else None
            if isinstance(duplicated_scalar, list):
                anomalies["source_export_repeated_scalar"].append({
                    "source_record_id": rid,
                    "source_path": "ParteMonte.daniosconaprovechamiento",
                    "values": duplicated_scalar,
                    "values_equal": len({str(value) for value in duplicated_scalar}) == 1,
                })
        fingerprint = hashlib.sha256(json.dumps(remove_identity_fields(original), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        fingerprints[fingerprint].append(rid or record["fire_id"])
        model = record["form_model"]
        seen_paths: set[str] = set()
        for path, value in walk_leaf_paths(original):
            if not path or path in seen_paths or value is None:
                continue
            seen_paths.add(path)
            entry = schema[model][path]
            entry["records_with_value"] += 1
            entry["lexical_types"][lexical_type(value)] += 1
            text = as_text(value)
            if text and text not in entry["examples"] and len(entry["examples"]) < 3:
                entry["examples"].append(text)

    duplicate_groups = [values for values in fingerprints.values() if len(values) > 1]
    expected_rows = {(row["year"], province): row[province] for row in inventory["counts"]["by_year"] for province in PROVINCES}
    annual_discrepancies = []
    for key, expected in sorted(expected_rows.items()):
        observed = by_year_province.get(key, metrics_template())["records"]
        if observed != expected:
            annual_discrepancies.append({"year": key[0], "province": key[1], "expected": expected, "observed": observed})
    expected_gif_rows = {
        (row["year"], province): row[province]
        for row in inventory["counts"]["gif_ge_500_ha_by_year_and_province"]
        for province in PROVINCES
    }
    gif_discrepancies = []
    for key, expected in sorted(expected_gif_rows.items()):
        forest_observed = forest_gif_by_year_province[key]
        total_observed = total_area_gif_by_year_province[key]
        if forest_observed != expected or total_observed != expected:
            gif_discrepancies.append({
                "year": key[0], "province": key[1], "public_search_expected": expected,
                "forest_area_ge_500": forest_observed, "total_area_ge_500": total_observed,
            })

    schema_matrix = []
    all_paths = sorted({path for model in schema.values() for path in model})
    for path in all_paths:
        row: dict[str, Any] = {"source_path": path, "models": {}}
        for _, _, model in FORM_PERIODS:
            entry = schema[model].get(path)
            row["models"][model] = {
                "records": model_totals[model],
                "records_with_value": entry["records_with_value"] if entry else 0,
                "lexical_types": dict(entry["lexical_types"]) if entry else {},
                "examples": entry["examples"] if entry else [],
            }
        schema_matrix.append(row)
    lexical_type_change_paths = []
    for row in schema_matrix:
        observed = {
            tuple(sorted(model["lexical_types"]))
            for model in row["models"].values()
            if model["records_with_value"]
        }
        if len(observed) > 1:
            lexical_type_change_paths.append(row["source_path"])

    publication_1992 = {
        "Alicante": {"records": 201, "wooded_area_ha": 981.4, "nonwooded_area_ha": 3298.5, "forest_area_ha": 4279.9},
        "Castellon": {"records": 214, "wooded_area_ha": 4542.5, "nonwooded_area_ha": 2689.8, "forest_area_ha": 7232.3},
        "Valencia": {"records": 354, "wooded_area_ha": 8816.0, "nonwooded_area_ha": 5860.3, "forest_area_ha": 14676.3},
    }
    xml_1992: dict[str, dict[str, float | int]] = {}
    for province in PROVINCES:
        selected = [record for record in records if record["year"] == 1992 and record["province"] == province]
        xml_1992[province] = {
            "records": len(selected),
            "wooded_area_ha": round(sum(record["reported_wooded_area_ha"] or 0 for record in selected), 1),
            "nonwooded_area_ha": round(sum(record["reported_nonwooded_area_ha"] or 0 for record in selected), 1),
            "forest_area_ha": round(sum(record["reported_forest_area_ha"] or 0 for record in selected), 1),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": utc_now(),
        "scope": {"years": [1968, 1992], "provinces": list(PROVINCES)},
        "totals": totals,
        "by_year_and_province": [
            {"year": year, "province": province, **metrics}
            for (year, province), metrics in sorted(by_year_province.items())
        ],
        "expected_count_comparison": {
            "expected_total": 9175,
            "observed_total": len(records),
            "difference": len(records) - 9175,
            "annual_discrepancies": annual_discrepancies,
        },
        "gif_threshold_audit": {
            "public_search_total": sum(expected_gif_rows.values()),
            "forest_area_ge_500_total": sum(forest_gif_by_year_province.values()),
            "total_area_ge_500_total": sum(total_area_gif_by_year_province.values()),
            "year_province_discrepancies": gif_discrepancies,
            "records_where_threshold_depends_on_area_definition": gif_basis_differences,
            "normalized_rule": "is_gif_ge_500_ha uses reported forest area only",
        },
        "schema_inventory": {
            "documented_historical_models": 6,
            "observed_export_representation": "one current hierarchical XML/XSD representation",
            "limitation": "The exporter does not expose the original form model as a record field; models are assigned only by documented year ranges.",
            "model_record_counts": dict(model_totals),
            "field_matrix": schema_matrix,
            "observed_lexical_type_change_count": len(lexical_type_change_paths),
            "observed_lexical_type_change_paths": lexical_type_change_paths,
            "equivalences": [],
            "unproven_equivalences_forced": False,
        },
        "apparent_duplicate_core_groups": duplicate_groups,
        "apparent_duplicate_core_group_count": len(duplicate_groups),
        "apparent_duplicate_core_record_count": sum(len(group) for group in duplicate_groups),
        "anomalies": {
            key: {
                "count": len(anomalies[key]),
                "affected_record_count": len({
                    item.get("source_record_id") for item in anomalies[key]
                    if item.get("source_record_id")
                }),
                "records": anomalies[key],
            }
            for key in (
                "invalid_detection_date", "invalid_extinction_date", "extinction_before_detection",
                "detection_year_mismatch", "source_report_id_year_or_province_mismatch",
                "source_province_mismatch", "unresolved_municipality_code",
                "negative_surface", "zero_surface", "surface_over_100000_ha",
                "source_export_repeated_scalar",
            )
        },
        "spatial_audit": {
            "safely_transformable_coordinates": totals["with_safely_transformable_coordinates"],
            "geometry_created": 0,
            "coordinate_rule": "No 1968-1992 coordinate is transformed without demonstrated datum, zone, units and semantics per record/form.",
            "official_linked_data_point_validation_start_year": 2005,
            "coordinate_outside_province_check": "not_applicable_without_safely_transformable_coordinates",
            "location_fields": {
                "records_with_municipality_resolved": totals["with_municipality"],
                "records_with_paraje": totals["with_paraje"],
                "records_with_map_sheet_or_grid": totals["with_map_sheet_or_grid"],
                "records_with_raw_coordinates": totals["with_raw_coordinates"],
                "records_with_parte_monte": records_with_parte_monte,
                "parte_monte_entries": parte_monte_entry_count,
                "maximum_parte_monte_entries_in_one_record": max_parte_monte_entries,
                "parte_monte_entries_with_catalog_code": parte_monte_catalog_code_entries,
                "parte_monte_interpretation": "affected-mountain/report relations preserved as source attributes, not point or polygon geometry",
            },
        },
        "statistical_contrast": {
            "public_search_inventory_comparison": "complete" if not annual_discrepancies else "discrepancies",
            "annual_publications_catalogued": 25,
            "annual_publications_format": "scanned image PDFs without an extractable text layer",
            "ocr_candidate_report": "data/processed/egif/gva/annual_publication_ocr.json",
            "definitive_1992": {
                "source_url": ANNUAL_REPORT_1992_URL,
                "publication_table_pdf_page": 11,
                "publication_gif_narrative_pdf_page": 5,
                "publication": publication_1992,
                "current_xml": xml_1992,
                "record_count_differences_xml_minus_publication": {
                    province: xml_1992[province]["records"] - publication_1992[province]["records"]
                    for province in PROVINCES
                },
                "publication_total_records": 769,
                "current_xml_total_records": sum(value["records"] for value in xml_1992.values()),
                "publication_cv_large_fires": 8,
                "current_xml_forest_area_ge_500_reports": sum(
                    1 for record in records if record["year"] == 1992 and record["reported_forest_area_ha"] >= 500
                ),
                "finding": "Provincial forest-area totals agree, but administrative report counts and the large-fire count do not. No records were changed to force agreement.",
                "cross_province_episode_candidate": {
                    "publication_description": "One fire began in Marines (Valencia) and crossed into Castellon through Altura; 9,299 ha in total.",
                    "candidate_source_record_ids": ["1992460250", "1992120403", "1992469001"],
                    "link_status": "candidate_not_merged",
                },
            },
            "remaining_1968_1991_comparison": "OCR excerpts generated for human review; no unreviewed OCR number is treated as authoritative.",
            "dataset_was_not_modified_to_force_agreement": True,
        },
    }


def process_all(args: argparse.Namespace, inventory: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("validation_status") != "complete" or manifest.get("downloaded_total") != 9175:
        raise PipelineError("El manifiesto raw no acredita una descarga completa de 9.175 registros")
    entries = {entry["province"]: entry for entry in manifest["provinces"]}
    municipality_names = load_sparql_dictionary(args.raw_dir / "dictionaries/municipalities.sparql.json", "municipality", ("name",))
    cause_names = load_sparql_dictionary(args.raw_dir / "dictionaries/causes.sparql.json", "cause", ("description", "label"))
    records: list[dict[str, Any]] = []
    for province, config in PROVINCES.items():
        entry = entries.get(province)
        if not entry:
            raise PipelineError(f"Falta {province} en el manifiesto")
        path = Path(entry["raw_path"])
        if not path.is_absolute():
            path = args.inventory.resolve().parents[2] / path
        if not path.exists() or sha256_file(path) != entry["sha256"]:
            raise PipelineError(f"Snapshot ausente o checksum inválido: {path}")
        for original, source in iter_records(path):
            records.append(normalized_record(
                original, province, config["code"], entry, source["xml_member"], municipality_names, cause_names
            ))
    if len(records) != 9175:
        raise PipelineError(f"Se normalizaron {len(records)} registros, no 9.175")
    identity = assign_identity(records)
    report = audit_records(records, inventory)
    report["identity_audit"] = identity
    report["dictionary_coverage"] = {
        "municipality_dictionary_entries": len(municipality_names),
        "cause_dictionary_entries": len(cause_names),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "fires_1968_1992.jsonl"
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".part", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    try:
        stored_output_path = str(output.resolve().relative_to(args.inventory.resolve().parents[2]))
    except ValueError:
        stored_output_path = str(output)
    report["output"] = {
        "path": stored_output_path,
        "format": "JSON Lines UTF-8",
        "record_count": len(records),
        "size_bytes": output.stat().st_size,
        "sha256": sha256_file(output),
    }
    atomic_write_json(args.output_dir / "report.json", report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("all", "download", "process"), default="all")
    parser.add_argument("--inventory", type=Path, default=repo / "data/sources/gva_historical_inventory.json")
    parser.add_argument("--raw-dir", type=Path, default=repo / "data/raw/egif/gva/1968_1992")
    parser.add_argument("--manifest", type=Path, default=repo / "data/sources/egif_gva_1968_1992_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=repo / "data/processed/egif/gva")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.attempts < 1 or args.timeout <= 0:
        parser.error("--attempts y --timeout deben ser positivos")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        manifest: dict[str, Any]
        if args.command in {"all", "download"}:
            manifest = download_all(args, inventory)
        else:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.command in {"all", "process"}:
            report = process_all(args, inventory, manifest)
            print(json.dumps({
                "records": report["totals"]["records"],
                "gif": report["totals"]["gif_ge_500_ha"],
                "output": report["output"],
            }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError, PipelineError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
