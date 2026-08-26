#!/usr/bin/env python3
"""Build the lightweight ES-2 national territory snapshot from official sources.

The INE workbook is the canonical source for current codes and names. IGN/CNIG
is recorded as the future geometry/bounds source, but no geometry is embedded.
All raw inputs remain ignored; deterministic outputs require --retrieved-at.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
INE_XLSX_URL = "https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx"
INE_HIERARCHY_URL = "https://www.ine.es/daco/daco42/codmun/cod_ccaa_provincia.htm"
CNIG_CATALOG_URL = "https://centrodedescargas.cnig.es/CentroDescargas/limites-municipales-provinciales-autonomicos"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None


def parse_hierarchy(path: Path) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    parser = TableParser()
    parser.feed(path.read_bytes().decode("iso-8859-1"))
    communities: dict[str, str] = {}
    provinces: dict[str, tuple[str, str]] = {}
    for row in parser.rows:
        if len(row) != 4 or not re.fullmatch(r"\d{2}", row[0]) or not re.fullmatch(r"\d{2}", row[2]):
            continue
        ccaa_code, ccaa_name, province_code, province_name = row
        communities[ccaa_code] = html.unescape(ccaa_name)
        provinces[province_code] = (html.unescape(province_name), ccaa_code)
    if len(communities) != 19 or len(provinces) != 52:
        raise ValueError(f"Unexpected INE hierarchy counts: {len(communities)} CCAA/cities, {len(provinces)} provinces")
    return communities, provinces


def column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref)
    if not letters:
        raise ValueError(f"Invalid XLSX cell reference: {cell_ref}")
    value = 0
    for letter in letters.group(0):
        value = value * 26 + ord(letter) - 64
    return value - 1


def parse_municipalities(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = [
            "".join(node.text or "" for node in item.iter(f"{{{NS['m']}}}t"))
            for item in shared_root.findall("m:si", NS)
        ]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows: list[list[str]] = []
    for row in sheet.findall(".//m:sheetData/m:row", NS):
        values = [""] * 5
        for cell in row.findall("m:c", NS):
            index = column_index(cell.attrib["r"])
            if index >= len(values):
                continue
            node = cell.find("m:v", NS)
            value = "" if node is None or node.text is None else node.text
            if cell.attrib.get("t") == "s" and value:
                value = shared[int(value)]
            values[index] = value.strip()
        rows.append(values)
    if rows[1] != ["CODAUTO", "CPRO", "CMUN", "DC", "NOMBRE"]:
        raise ValueError(f"Unexpected INE workbook header: {rows[1]!r}")
    municipalities = []
    for ccaa, province, municipality, check_digit, name in rows[2:]:
        if not (re.fullmatch(r"\d{2}", ccaa) and re.fullmatch(r"\d{2}", province) and re.fullmatch(r"\d{3}", municipality)):
            raise ValueError(f"Invalid municipality row: {(ccaa, province, municipality, check_digit, name)!r}")
        municipalities.append({
            "ccaa_code": ccaa,
            "province_code": province,
            "municipality_code": f"{province}{municipality}",
            "check_digit": check_digit,
            "name": name,
        })
    if len(municipalities) != 8132:
        raise ValueError(f"Expected 8,132 municipalities, got {len(municipalities)}")
    return municipalities


def provenance(source_record_id: str, retrieved_at: str) -> dict:
    return {
        "source_id": "ine_rel_2026_01_01",
        "source_record_id": source_record_id,
        "retrieved_at": retrieved_at,
        "transformations": ["selection_of_codes_names_and_hierarchy", "no_geometry_embedded"],
    }


def territory(
    territory_id: str,
    territory_type: str,
    code: str,
    name: str,
    parent_id: str | None,
    retrieved_at: str,
    check_digit: str | None = None,
    province_equivalent_code: str | None = None,
) -> dict:
    item = {
        "territory_id": territory_id,
        "territory_type": territory_type,
        "official_code": code,
        "official_name": name,
        "parent_id": parent_id,
        "aliases": [],
        "valid_from": "2026-01-01",
        "valid_to": None,
        "predecessor_ids": [],
        "successor_ids": [],
        "provenance": provenance(code, retrieved_at),
    }
    if check_digit is not None:
        item["check_digit"] = check_digit
    if province_equivalent_code is not None:
        item["province_equivalent_code"] = province_equivalent_code
    return item


def validate_cnig_catalog(path: Path) -> dict:
    text = path.read_bytes().decode("utf-8", errors="replace")
    expected = ["28/07/2026", "10/08/2026", "ETRS89", "REGCAN95", "CC-BY 4.0"]
    missing = [token for token in expected if token not in text]
    if missing:
        raise ValueError(f"IGN/CNIG catalog no longer contains expected metadata: {missing}")
    return {
        "source_url": CNIG_CATALOG_URL,
        "catalog_sha256": sha256(path),
        "current_shapefile_release": "2026-07-28",
        "current_gml_release": "2026-08-10",
        "crs": {
            "mainland_balearic_ceuta_melilla": "ETRS89 geographic longitude/latitude",
            "canary_islands": "REGCAN95 geographic longitude/latitude",
            "wgs84_compatibility": True
        },
        "license": {
            "compatibility": "CC-BY-4.0-compatible",
            "derived_attribution": "Obra derivada de BDLJE CC-BY 4.0 ign.es"
        },
        "geometry_included_in_snapshot": False,
        "reason": "ES-2 versions the canonical hierarchy only; official geometries/bounds remain a separately acquired asset."
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--municipalities-xlsx", type=Path, required=True)
    parser.add_argument("--hierarchy-html", type=Path, required=True)
    parser.add_argument("--cnig-catalog-html", type=Path, required=True)
    parser.add_argument("--retrieved-at", required=True, help="UTC ISO-8601 timestamp fixed for reproducible output")
    parser.add_argument("--snapshot", type=Path, default=Path("data/territories/spain/territories-2026-01-01.json"))
    parser.add_argument("--manifest", type=Path, default=Path("data/sources/spain_territory_snapshot_manifest.json"))
    args = parser.parse_args()

    communities, provinces = parse_hierarchy(args.hierarchy_html)
    municipalities = parse_municipalities(args.municipalities_xlsx)
    autonomous_city_codes = {"18": "51", "19": "52"}
    records = [territory("ES", "country", "ES", "España", None, args.retrieved_at)]
    records.extend(
        territory(
            f"ES:CCAA:{code}",
            "autonomous_city" if code in autonomous_city_codes else "autonomous_community",
            code,
            name,
            "ES",
            args.retrieved_at,
            province_equivalent_code=autonomous_city_codes.get(code),
        )
        for code, name in sorted(communities.items())
    )
    records.extend(
        territory(f"ES:PROV:{code}", "province", code, name, f"ES:CCAA:{ccaa}", args.retrieved_at)
        for code, (name, ccaa) in sorted(provinces.items())
        if code not in autonomous_city_codes.values()
    )
    records.extend(
        territory(
            f"ES:MUN:{row['municipality_code']}",
            "municipality",
            row["municipality_code"],
            row["name"],
            f"ES:CCAA:{row['ccaa_code']}" if row["province_code"] in autonomous_city_codes.values() else f"ES:PROV:{row['province_code']}",
            args.retrieved_at,
            row["check_digit"],
            row["province_code"] if row["province_code"] in autonomous_city_codes.values() else None,
        )
        for row in municipalities
    )
    if len({record["territory_id"] for record in records}) != len(records):
        raise ValueError("Duplicate territory_id")
    snapshot = {
        "schema_version": 1,
        "snapshot_id": "ine-rel-2026-01-01",
        "reference_date": "2026-01-01",
        "country": "ES",
        "geometry_embedded": False,
        "territories": records,
    }
    write_json(args.snapshot, snapshot)
    snapshot_hash = sha256(args.snapshot)
    manifest = {
        "schema_version": 1,
        "manifest_type": "territory",
        "generated_at": args.retrieved_at,
        "snapshot_id": snapshot["snapshot_id"],
        "reference_date": snapshot["reference_date"],
        "retrieved_at": args.retrieved_at,
        "sources": {
            "ine_municipalities": {
                "source_url": INE_XLSX_URL,
                "source_sha256": sha256(args.municipalities_xlsx),
                "format": "XLSX",
                "authority": "Instituto Nacional de Estadística",
                "basis": "Registro de Entidades Locales"
            },
            "ine_hierarchy": {
                "source_url": INE_HIERARCHY_URL,
                "source_sha256": sha256(args.hierarchy_html),
                "format": "HTML",
                "authority": "Instituto Nacional de Estadística"
            },
            "ign_cnig_boundaries": validate_cnig_catalog(args.cnig_catalog_html)
        },
        "counts": {
            "country": 1,
            "autonomous_communities": len(communities) - len(autonomous_city_codes),
            "autonomous_cities": len(autonomous_city_codes),
            "provinces": len(provinces) - len(autonomous_city_codes),
            "province_equivalent_codes_for_autonomous_cities": len(autonomous_city_codes),
            "statistical_codes_at_province_level": len(provinces),
            "municipalities": len(municipalities),
            "total_territories": len(records)
        },
        "output": {
            "path": str(args.snapshot),
            "format": "compact JSON",
            "byte_size": args.snapshot.stat().st_size,
            "sha256": snapshot_hash,
            "geometry_embedded": False
        },
        "partitions": [{
            "partition_id": "territories:ES:2026-01-01",
            "source_id": "ine_rel_2026_01_01",
            "territory_ids": ["ES"],
            "period": {"start": "2026-01-01", "end": None},
            "lod": "none",
            "geometry_semantics": "none",
            "feature_count": len(records),
            "byte_size": args.snapshot.stat().st_size,
            "sha256": snapshot_hash,
            "url": "../territories/spain/territories-2026-01-01.json",
            "publication_profiles": []
        }],
        "historical_scope": {
            "included": False,
            "policy": "Current 2026 hierarchy is a reference snapshot. Historical predecessor/successor relations require separate documented releases and are never inferred."
        }
    }
    write_json(args.manifest, manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True))
    print(f"snapshot_sha256={snapshot_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
