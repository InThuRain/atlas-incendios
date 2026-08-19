#!/usr/bin/env python3
"""Build immutable CV-2.2 snapshots from SIGIF/GVA and EFFIS.

The pipeline deliberately keeps administrative SIGIF observations and EFFIS
satellite geometries in separate collections.  Its link output contains only
scored candidates.  It never changes the consolidated ICV 1993-2024 files.
"""

import argparse
import collections
import hashlib
import http.client
import json
import os
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path

try:
    from pyproj import Transformer
    from shapely.geometry import Point, mapping, shape
    from shapely.ops import transform, unary_union
except ImportError as error:  # pragma: no cover - exercised by environment setup
    raise SystemExit(
        "Missing geospatial dependencies. Install requirements-recent.txt: {}".format(
            error
        )
    )


USER_AGENT = "atlas-incendios-cv-recent/1.0"
SNAPSHOT_SCHEMA_VERSION = 1
EXPECTED_SIGIF_COLUMNS = (
    "Fecha",
    "Municipio",
    "Paraje",
    "Causa",
    "Rasa",
    "Arbolada",
    "Total",
    "Hora ini",
    "Hora fin",
    "Deteccion",
    "Alerta",
    "Comarca",
    "X1",
    "Y1",
)


class RecentDataError(RuntimeError):
    """Raised when a snapshot cannot be downloaded or validated."""


class TableParser(HTMLParser):
    """Extract one HTML table while retaining displayed row order."""

    def __init__(self, table_id):
        super().__init__(convert_charrefs=True)
        self.table_id = table_id
        self.in_table = False
        self.in_cell = False
        self.row = None
        self.cell_parts = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == self.table_id:
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.row = []
        elif self.in_table and tag in ("td", "th") and self.row is not None:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag):
        if self.in_table and tag in ("td", "th") and self.in_cell:
            self.row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif self.in_table and tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif self.in_table and tag == "table":
            self.in_table = False


class TokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "__RequestVerificationToken":
            self.token = attributes.get("value")


def repository_root():
    return Path(__file__).resolve().parents[3]


def now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_snapshot_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RecentDataError("Invalid JSON {}: {}".format(path, error))


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_bytes_atomic(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def write_json_atomic(path, value, compact=False):
    if compact:
        text = json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )
    else:
        text = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
    write_bytes_atomic(path, (text + "\n").encode("utf-8"))


def write_jsonl_atomic(path, records):
    raw = "".join(canonical_json(record) + "\n" for record in records).encode("utf-8")
    write_bytes_atomic(path, raw)


def file_metadata(path, base):
    return {
        "path": str(path.relative_to(base)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def request_bytes(opener, url, data=None, headers=None, timeout=60, attempts=3):
    last_error = None
    request_headers = {"User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    for attempt in range(attempts):
        request = urllib.request.Request(url, data=data, headers=request_headers)
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
            if not raw:
                raise RecentDataError("Empty response from {}".format(url))
            return raw, content_type
        except (
            ConnectionError,
            ConnectionResetError,
            TimeoutError,
            http.client.IncompleteRead,
            socket.timeout,
            urllib.error.HTTPError,
            urllib.error.URLError,
            RecentDataError,
        ) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RecentDataError(
        "Request failed after {} attempts for {}: {}".format(attempts, url, last_error)
    )


def request_json(opener, url, params, timeout, attempts):
    request_url = "{}?{}".format(url, urllib.parse.urlencode(params))
    raw, _ = request_bytes(opener, request_url, timeout=timeout, attempts=attempts)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RecentDataError("Invalid JSON from {}: {}".format(url, error))
    if isinstance(payload, dict) and payload.get("error"):
        raise RecentDataError("ArcGIS error from {}: {}".format(url, payload["error"]))
    return payload, raw, request_url


def normalize_label(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_date_es(value):
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except (AttributeError, ValueError):
        return None


def parse_effis_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_decimal(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).strip().replace(".", "").replace(",", "."))
    except ValueError:
        return None


def parse_number(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_sigif_table(raw, table_id):
    try:
        document = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RecentDataError("SIGIF response is not UTF-8: {}".format(error))
    parser = TableParser(table_id)
    parser.feed(document)
    if len(parser.rows) < 2:
        raise RecentDataError("SIGIF response contains no data table rows")
    columns = parser.rows[0]
    normalized = tuple(normalize_label(value) for value in columns)
    expected = tuple(normalize_label(value) for value in EXPECTED_SIGIF_COLUMNS)
    if normalized != expected:
        raise RecentDataError(
            "Unexpected SIGIF columns: {}".format(json.dumps(columns, ensure_ascii=False))
        )
    rows = parser.rows[1:]
    malformed = [index for index, row in enumerate(rows, 1) if len(row) != len(columns)]
    if malformed:
        raise RecentDataError("Malformed SIGIF rows: {}".format(malformed[:20]))
    return columns, rows


def download_sigif_year(config, year, timeout, attempts):
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    form_url = config["sigif"]["form_url"]
    raw_form, _ = request_bytes(opener, form_url, timeout=timeout, attempts=attempts)
    token_parser = TokenParser()
    token_parser.feed(raw_form.decode("utf-8"))
    if not token_parser.token:
        raise RecentDataError("SIGIF form has no anti-forgery token")
    form = {
        "__RequestVerificationToken": token_parser.token,
        "FechaDesde": "01/01/{}".format(year),
        "FechaHasta": "31/12/{}".format(year),
        "TipoInformeID": "2",
        "ProvinciaID": "",
        "CausaProvisionalID": "",
        "ComarcasSeleccionadas": "",
        "MunicipiosSeleccionados": "",
    }
    encoded = urllib.parse.urlencode(form).encode("ascii")
    raw, content_type = request_bytes(
        opener,
        config["sigif"]["provisional_results_url"],
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": form_url,
        },
        timeout=timeout,
        attempts=attempts,
    )
    columns, rows = parse_sigif_table(raw, config["sigif"]["table_id"])
    return {
        "raw": raw,
        "content_type": content_type,
        "columns": columns,
        "rows": rows,
        "parameters": {key: value for key, value in form.items() if not key.startswith("__")},
    }


def download_boundary(config, opener, timeout, attempts):
    layer_url = config["administrative_boundary"]["layer_url"]
    metadata, metadata_raw, metadata_url = request_json(
        opener, layer_url, {"f": "pjson"}, timeout, attempts
    )
    source_reference = metadata.get("sourceSpatialReference") or {}
    if source_reference.get("latestWkid", source_reference.get("wkid")) != 25830:
        raise RecentDataError("Official boundary source no longer declares EPSG:25830")
    count_before, _, count_url = request_json(
        opener,
        layer_url + "/query",
        {"f": "json", "where": "1=1", "returnCountOnly": "true"},
        timeout,
        attempts,
    )
    count_before = count_before.get("count")
    params = {
        "f": "geojson",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "orderByFields": "ESRI_OID ASC",
        "resultOffset": 0,
        "resultRecordCount": metadata.get("maxRecordCount", 2000),
    }
    collection, raw, query_url = request_json(
        opener, layer_url + "/query", params, timeout, attempts
    )
    features = collection.get("features")
    if not isinstance(count_before, int) or not isinstance(features, list):
        raise RecentDataError("Invalid official boundary response")
    count_after, _, _ = request_json(
        opener,
        layer_url + "/query",
        {"f": "json", "where": "1=1", "returnCountOnly": "true"},
        timeout,
        attempts,
    )
    count_after = count_after.get("count")
    if count_before != count_after or len(features) != count_after:
        raise RecentDataError(
            "Incomplete/changing boundary: before {}, downloaded {}, after {}".format(
                count_before, len(features), count_after
            )
        )
    municipality_geometries = [shape(feature["geometry"]) for feature in features]
    boundary = unary_union(municipality_geometries)
    if boundary.is_empty:
        raise RecentDataError("The dissolved official boundary is empty")
    return {
        "metadata": metadata,
        "metadata_raw": metadata_raw,
        "metadata_url": metadata_url,
        "raw": raw,
        "query_url": query_url,
        "count_url": count_url,
        "collection": collection,
        "boundary": boundary,
        "count": len(features),
    }


def parse_wfs_hits(raw):
    match = re.search(br'numberOfFeatures=["\'](\d+)["\']', raw)
    if not match:
        raise RecentDataError("EFFIS hits response has no numberOfFeatures")
    return int(match.group(1))


def download_effis_bbox(config, boundary, opener, timeout, attempts):
    min_x, min_y, max_x, max_y = boundary.bounds
    # WFS 1.1 follows EPSG:4326 latitude/longitude axis order in BBOX.
    bbox = "{},{},{},{},EPSG:4326".format(min_y, min_x, max_y, max_x)
    base_params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": config["effis"]["type_name"],
        "BBOX": bbox,
    }
    hits_url = "{}?{}".format(
        config["effis"]["wfs_url"],
        urllib.parse.urlencode(dict(base_params, resultType="hits")),
    )
    hits_raw, _ = request_bytes(opener, hits_url, timeout=timeout, attempts=attempts)
    expected = parse_wfs_hits(hits_raw)
    data_params = dict(base_params, outputFormat="geojson", srsName="EPSG:4326")
    data_url = "{}?{}".format(
        config["effis"]["wfs_url"], urllib.parse.urlencode(data_params)
    )
    raw, _ = request_bytes(opener, data_url, timeout=timeout, attempts=attempts)
    try:
        collection = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RecentDataError("Invalid EFFIS GeoJSON: {}".format(error))
    features = collection.get("features")
    if collection.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise RecentDataError("EFFIS response is not a GeoJSON FeatureCollection")
    if len(features) != expected:
        raise RecentDataError(
            "Incomplete EFFIS BBOX response: expected {}, downloaded {}".format(
                expected, len(features)
            )
        )
    return {
        "raw": raw,
        "collection": collection,
        "expected": expected,
        "bbox_wfs_axis_order": bbox,
        "hits_url": hits_url,
        "data_url": data_url,
    }


def download_icv_coordinate_reference(config, opener, timeout, attempts):
    layer_url = config["coordinate_evidence"]["icv_layer_url"]
    metadata, metadata_raw, metadata_url = request_json(
        opener, layer_url, {"f": "pjson"}, timeout, attempts
    )
    source_reference = metadata.get("sourceSpatialReference") or {}
    source_wkid = source_reference.get("latestWkid", source_reference.get("wkid"))
    if source_wkid != 25830:
        raise RecentDataError("ICV coordinate reference layer is not EPSG:25830")
    count_payload, _, _ = request_json(
        opener,
        layer_url + "/query",
        {"f": "json", "where": "1=1", "returnCountOnly": "true"},
        timeout,
        attempts,
    )
    expected_count = count_payload.get("count")
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": "OBJECTID,NumPIF_CV,nom_mun,paraje,x,y,f_detec",
        "returnGeometry": "false",
        "orderByFields": "OBJECTID ASC",
        "resultRecordCount": metadata.get("maxRecordCount", 2000),
    }
    payload, raw, query_url = request_json(
        opener, layer_url + "/query", params, timeout, attempts
    )
    features = payload.get("features")
    if not isinstance(features, list):
        raise RecentDataError("Invalid ICV coordinate reference response")
    if not isinstance(expected_count, int) or len(features) != expected_count:
        raise RecentDataError(
            "Incomplete ICV coordinate reference: expected {}, downloaded {}".format(
                expected_count, len(features)
            )
        )
    return {
        "metadata": metadata,
        "metadata_raw": metadata_raw,
        "metadata_url": metadata_url,
        "payload": payload,
        "raw": raw,
        "query_url": query_url,
        "source_wkid": source_wkid,
        "feature_count_expected_and_downloaded": expected_count,
    }


def coordinate_evidence(sigif_2024, icv_reference):
    icv = [feature.get("attributes", {}) for feature in icv_reference["payload"]["features"]]
    date_municipality_matches = 0
    exact_coordinate_matches = 0
    differing_examples = []
    for row in sigif_2024["rows"]:
        row_date, row_municipality = row[0], normalize_label(row[1])
        candidates = [
            attributes
            for attributes in icv
            if attributes.get("f_detec") == row_date
            and normalize_label(attributes.get("nom_mun")) == row_municipality
        ]
        if candidates:
            date_municipality_matches += 1
        x_value = parse_number(row[12])
        y_value = parse_number(row[13])
        exact = [
            attributes
            for attributes in candidates
            if parse_number(attributes.get("x")) == x_value
            and parse_number(attributes.get("y")) == y_value
        ]
        if exact:
            exact_coordinate_matches += 1
        elif candidates and len(differing_examples) < 20:
            differing_examples.append(
                {
                    "date": row_date,
                    "municipality": row[1],
                    "sigif_x1": row[12],
                    "sigif_y1": row[13],
                    "icv_candidates": [
                        {
                            "NumPIF_CV": candidate.get("NumPIF_CV"),
                            "x": candidate.get("x"),
                            "y": candidate.get("y"),
                        }
                        for candidate in candidates
                    ],
                }
            )
    sufficient = exact_coordinate_matches >= 100 and icv_reference["source_wkid"] == 25830
    return {
        "status": "demonstrated" if sufficient else "insufficient",
        "coordinate_semantics": "wildfire_start_point" if sufficient else "unknown",
        "crs": "EPSG:25830" if sufficient else None,
        "axis_order": "X=easting, Y=northing" if sufficient else "unknown",
        "units": "metres" if sufficient else "unknown",
        "reference_year": 2024,
        "sigif_rows": len(sigif_2024["rows"]),
        "icv_features": len(icv),
        "date_and_normalized_municipality_matches": date_municipality_matches,
        "exact_x_y_matches_within_date_municipality": exact_coordinate_matches,
        "differing_examples": differing_examples,
        "evidence": [
            {
                "type": "official_methodology",
                "url": "https://prevencionincendiosgva.es/Documents/PlanesVigilancia/legislacion/Orden%2030-2017%20normas%20t%C3%A9cnicas%20PLPIF.pdf",
                "finding": "The GVA methodology locates recent wildfire start points with UTM coordinates.",
            },
            {
                "type": "official_layer_metadata",
                "url": icv_reference["metadata_url"],
                "finding": "The official ICV 2024 layer declares sourceSpatialReference EPSG:25830 and exposes x/y attributes.",
            },
            {
                "type": "reproducible_cross_source_comparison",
                "finding": "SIGIF 2024 X1/Y1 values were compared with ICV 2024 x/y after matching date and normalized municipality.",
            },
        ],
        "caveat": "Coordinate equality establishes the public field lineage for most records; differences are retained and not corrected.",
    }


def municipality_for_point(point, municipality_features):
    matches = []
    for feature, geometry in municipality_features:
        if geometry.covers(point):
            matches.append(feature.get("properties", {}))
    if not matches:
        return None
    matches.sort(key=lambda item: str(item.get("cod_ine_mun", "")))
    return matches[0]


def transform_sigif_rows(year, result, evidence, acquired_at, municipality_features):
    columns = result["columns"]
    occurrences = collections.Counter()
    records = []
    point_transformer = Transformer.from_crs(25830, 4326, always_xy=True)
    coordinate_diagnostics = collections.Counter()
    for source_index, row in enumerate(result["rows"], 1):
        original = dict(zip(columns, row))
        row_hash = hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest()
        occurrences[row_hash] += 1
        record_id = "sigif:gva:{}:{}:{}".format(
            year, row_hash[:20], occurrences[row_hash]
        )
        observed_date = parse_date_es(row[0])
        x_value, y_value = parse_number(row[12]), parse_number(row[13])
        point_geojson = None
        admin = None
        if evidence["status"] == "demonstrated" and x_value is not None and y_value is not None:
            longitude, latitude = point_transformer.transform(x_value, y_value)
            point_geojson = {"type": "Point", "coordinates": [longitude, latitude]}
            admin = municipality_for_point(Point(longitude, latitude), municipality_features)
            if admin:
                coordinate_diagnostics["inside_official_cv_boundary"] += 1
                point_municipality_names = {
                    normalize_label(admin.get(key))
                    for key in ("nom_mun", "nom_mun_cas", "nom_mun_val", "noms_mun")
                    if admin.get(key)
                }
                if normalize_label(row[1]) in point_municipality_names:
                    coordinate_diagnostics["official_municipality_name_match"] += 1
                else:
                    coordinate_diagnostics["official_municipality_name_difference"] += 1
            else:
                coordinate_diagnostics["outside_official_cv_boundary"] += 1
        record = {
            "sigif_record_id": record_id,
            "source": "SIGIF_GVA",
            "source_year": year,
            "source_row_index": source_index,
            "source_row_hash_sha256": row_hash,
            "record_maturity": "provisional",
            "authority_type": "regional_administrative",
            "identity_status": "unlinked",
            "observed_date": observed_date.isoformat() if observed_date else None,
            "municipality": row[1],
            "place_name": row[2],
            "cause": row[3],
            "reported_shrub_grass_area_ha": parse_decimal(row[4]),
            "reported_wooded_area_ha": parse_decimal(row[5]),
            "reported_total_area_ha": parse_decimal(row[6]),
            "start_time_reported": row[7] or None,
            "end_time_reported": row[8] or None,
            "detection_method": row[9],
            "alert_value": row[10],
            "comarca": row[11],
            "x1_original": row[12],
            "y1_original": row[13],
            "coordinate_semantics": evidence["coordinate_semantics"],
            "coordinate_crs": evidence["crs"],
            "coordinate_axis_order": evidence["axis_order"],
            "point_epsg4326": point_geojson,
            "derived_admin_at_point": (
                {
                    "municipality": admin.get("nom_mun"),
                    "municipality_ine_code": admin.get("cod_ine_mun"),
                    "province": admin.get("provincia"),
                }
                if admin
                else None
            ),
            "original_columns": columns,
            "original_row": row,
            "original_attributes": original,
            "provenance": {
                "source_url": "https://prevencionincendiosgva.es/Incendios/EstadisticasProvisionalesList",
                "acquired_at": acquired_at,
                "coverage_start_requested": "{}-01-01".format(year),
                "coverage_end_requested": "{}-12-31".format(year),
                "coverage_complete": year == 2025,
                "snapshot_row_preserved": True,
                "redistribution_status": "blocked_pending_written_clarification",
            },
        }
        records.append(record)
    return records, dict(coordinate_diagnostics)


def effis_year(feature):
    observed = parse_effis_date(feature.get("properties", {}).get("FIREDATE"))
    return observed.year if observed else None


def transform_effis_features(year, raw_features, boundary, acquired_at, config):
    selected = []
    invalid_geometry_count = 0
    for source_index, feature in enumerate(raw_features, 1):
        if effis_year(feature) != year:
            continue
        geometry = shape(feature.get("geometry"))
        if not geometry.is_valid:
            invalid_geometry_count += 1
        if not geometry.intersects(boundary):
            continue
        properties = feature.get("properties") or {}
        geometry_hash = hashlib.sha256(
            canonical_json(feature.get("geometry")).encode("utf-8")
        ).hexdigest()
        effis_id = str(properties.get("id")) if properties.get("id") is not None else None
        geometry_id = "effis:rda:{}:{}".format(effis_id or "missing", geometry_hash[:16])
        normalized = {
            "geometry_id": geometry_id,
            "effis_id": effis_id,
            "source": "EFFIS_RDA",
            "source_year": year,
            "source_feature_index_in_bbox_response": source_index,
            "geometry_source": config["effis"]["geometry_source"],
            "geometry_quality": config["effis"]["geometry_quality"],
            "geometry_maturity": "provisional",
            "geometry_method": "satellite_rda",
            "administrative_fire_identity": None,
            "identity_status": "unlinked",
            "effis_fire_date": properties.get("FIREDATE"),
            "effis_final_date": properties.get("FINALDATE"),
            "effis_last_update": properties.get("LASTUPDATE"),
            "effis_area_ha": parse_number(properties.get("AREA_HA")),
            "effis_country": properties.get("COUNTRY"),
            "effis_province": properties.get("PROVINCE"),
            "effis_commune": properties.get("COMMUNE"),
            "original_attributes": properties,
            "geometry_checksum_sha256": geometry_hash,
            "provenance": {
                "source_url": config["effis"]["wfs_url"],
                "source_type_name": config["effis"]["type_name"],
                "acquired_at": acquired_at,
                "request_crs": config["effis"]["request_crs"],
                "selection": "FIREDATE year then true intersection with dissolved official ICV municipal boundary",
                "province_attribute_used_for_selection": False,
                "dates_warning": "EFFIS dates are not automatically interpreted as ignition/extinction.",
                "license": config["effis"]["license"],
                "attribution": config["effis"]["attribution"],
            },
        }
        selected.append(
            {
                "type": "Feature",
                "id": geometry_id,
                "properties": normalized,
                "geometry": feature.get("geometry"),
            }
        )
    return selected, invalid_geometry_count


def surface_similarity(sigif_area, effis_area):
    if sigif_area is None or effis_area is None or sigif_area <= 0 or effis_area <= 0:
        return None
    return min(sigif_area, effis_area) / max(sigif_area, effis_area)


def bilingual_label_match(left, right):
    left_tokens = set(normalize_label(left).split())
    right_tokens = set(normalize_label(right).split())
    if not left_tokens or not right_tokens:
        return None
    return bool(left_tokens.intersection(right_tokens))


def score_candidate(record, feature, distance_m, day_difference):
    score = 0
    reasons_for = []
    reasons_against = []
    if distance_m == 0:
        score += 50
        reasons_for.append("SIGIF start point is inside or on the EFFIS perimeter")
    elif distance_m <= 1000:
        score += 40
        reasons_for.append("SIGIF point is at most 1 km from the EFFIS perimeter")
    elif distance_m <= 5000:
        score += 25
        reasons_for.append("SIGIF point is at most 5 km from the EFFIS perimeter")
    else:
        score += 10
        reasons_against.append("SIGIF point is more than 5 km from the EFFIS perimeter")
    if day_difference == 0:
        score += 30
        reasons_for.append("SIGIF date and EFFIS FIREDATE have the same calendar date")
    elif day_difference <= 1:
        score += 25
        reasons_for.append("Dates differ by at most one day")
    elif day_difference <= 3:
        score += 18
        reasons_for.append("Dates differ by at most three days")
    elif day_difference <= 7:
        score += 10
        reasons_for.append("Dates differ by at most seven days")
    else:
        score += 4
        reasons_against.append("Dates differ by more than seven days")
    effis_properties = feature["properties"]
    municipality_match = normalize_label(record.get("municipality")) == normalize_label(
        effis_properties.get("effis_commune")
    )
    if municipality_match:
        score += 15
        reasons_for.append("Published municipality/commune labels agree after normalization")
    else:
        reasons_against.append("Published municipality/commune labels do not agree exactly")
    sigif_province = (record.get("derived_admin_at_point") or {}).get("province")
    effis_province = effis_properties.get("effis_province")
    province_match = bilingual_label_match(sigif_province, effis_province)
    if province_match is True:
        reasons_for.append("Province labels have a shared normalized bilingual name")
    elif province_match is False:
        reasons_against.append("Province labels have no shared normalized name")
    similarity = surface_similarity(
        record.get("reported_total_area_ha"), effis_properties.get("effis_area_ha")
    )
    if similarity is not None and similarity >= 0.5:
        score += 5
        reasons_for.append("Reported and satellite areas are within a factor of two")
    elif similarity is not None and similarity < 0.2:
        reasons_against.append("Reported and satellite areas differ by more than a factor of five")
    return (
        min(score, 100),
        municipality_match,
        province_match,
        similarity,
        reasons_for,
        reasons_against,
    )


def candidate_links(year, sigif_records, effis_features, config):
    transformer = Transformer.from_crs(4326, 25830, always_xy=True)
    project = transformer.transform
    effis_projected = [
        (feature, transform(project, shape(feature["geometry"])))
        for feature in effis_features
    ]
    maximum_distance = config["candidate_linking"]["maximum_distance_m"]
    maximum_days = config["candidate_linking"]["maximum_date_difference_days"]
    candidates = []
    records_with_candidates = set()
    for record in sigif_records:
        point_geojson = record.get("point_epsg4326")
        record_date = date.fromisoformat(record["observed_date"]) if record.get("observed_date") else None
        if not point_geojson or not record_date:
            continue
        point_projected = transform(project, shape(point_geojson))
        for feature, polygon_projected in effis_projected:
            effis_date = parse_effis_date(feature["properties"].get("effis_fire_date"))
            if not effis_date:
                continue
            day_difference = abs((record_date - effis_date).days)
            if day_difference > maximum_days:
                continue
            distance_m = point_projected.distance(polygon_projected)
            if distance_m > maximum_distance:
                continue
            (
                score,
                municipality_match,
                province_match,
                similarity,
                reasons_for,
                reasons_against,
            ) = score_candidate(record, feature, distance_m, day_difference)
            if score >= config["candidate_linking"]["strong_score_min"]:
                strength = "strong_candidate"
            elif score >= config["candidate_linking"]["possible_score_min"]:
                strength = "possible_candidate"
            else:
                strength = "weak_candidate"
            candidate_key = "{}|{}".format(
                record["sigif_record_id"], feature["properties"]["effis_id"]
            )
            candidate_id = "candidate:{}:{}".format(
                year, hashlib.sha256(candidate_key.encode("utf-8")).hexdigest()[:20]
            )
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "link_status": "candidate",
                    "candidate_strength": strength,
                    "score": score,
                    "sigif_record_id": record["sigif_record_id"],
                    "effis_id": feature["properties"]["effis_id"],
                    "effis_geometry_id": feature["properties"]["geometry_id"],
                    "distance_to_effis_perimeter_m": round(distance_m, 3),
                    "sigif_point_inside_effis_perimeter": distance_m == 0,
                    "date_difference_days": day_difference,
                    "sigif_date": record["observed_date"],
                    "effis_fire_date": (
                        effis_date.isoformat() if effis_date else None
                    ),
                    "municipality_label_match": municipality_match,
                    "sigif_derived_province": (
                        record.get("derived_admin_at_point") or {}
                    ).get("province"),
                    "effis_province": feature["properties"].get("effis_province"),
                    "province_label_match": province_match,
                    "sigif_reported_area_ha": record.get("reported_total_area_ha"),
                    "effis_area_ha": feature["properties"].get("effis_area_ha"),
                    "area_similarity_ratio": (
                        round(similarity, 6) if similarity is not None else None
                    ),
                    "reasons_for": reasons_for,
                    "reasons_against": reasons_against,
                    "method": "scored spatial-temporal candidate; no identity confirmation",
                }
            )
            records_with_candidates.add(record["sigif_record_id"])
    candidates.sort(key=lambda item: (item["sigif_date"], -item["score"], item["candidate_id"]))
    return candidates, records_with_candidates


def representative_cases(sigif_by_year, effis_by_year, candidates_by_year):
    result = {
        "ibi_font_roja_2025": [],
        "large_effis_candidate_cases": [],
        "large_effis_without_administrative_candidate": [],
    }
    records_by_id = {
        record["sigif_record_id"]: record
        for records in sigif_by_year.values()
        for record in records
    }
    features_by_id = {
        feature["properties"]["geometry_id"]: feature
        for features in effis_by_year.values()
        for feature in features
    }
    for candidate in candidates_by_year.get(2025, []):
        record = records_by_id[candidate["sigif_record_id"]]
        if (
            normalize_label(record.get("municipality")) == "ibi"
            and record.get("observed_date", "").startswith("2025-07")
        ):
            result["ibi_font_roja_2025"].append(
                {"sigif_record": record, "candidate": candidate}
            )
    for year, candidates in candidates_by_year.items():
        for candidate in candidates:
            feature = features_by_id[candidate["effis_geometry_id"]]
            if (
                feature["properties"].get("effis_area_ha") is not None
                and feature["properties"]["effis_area_ha"] >= 500
                and candidate["candidate_strength"] in ("strong_candidate", "possible_candidate")
            ):
                result["large_effis_candidate_cases"].append(
                    {
                        "year": year,
                        "sigif_record": records_by_id[candidate["sigif_record_id"]],
                        "effis_properties": feature["properties"],
                        "candidate": candidate,
                    }
                )
        candidate_geometry_ids = {
            candidate["effis_geometry_id"] for candidate in candidates
        }
        for feature in effis_by_year[year]:
            properties = feature["properties"]
            if (
                (properties.get("effis_area_ha") or 0) >= 500
                and properties["geometry_id"] not in candidate_geometry_ids
            ):
                result["large_effis_without_administrative_candidate"].append(
                    {
                        "year": year,
                        "effis_properties": properties,
                        "reason": "No SIGIF row passed the configured 14-day/20-km candidate window; this is not evidence that no administrative fire exists.",
                    }
                )
    return result


def sigif_anomalies(records):
    duplicate_hashes = collections.Counter(
        record["source_row_hash_sha256"] for record in records
    )
    duplicate_groups = [
        {
            "source_row_hash_sha256": row_hash,
            "count": count,
            "record_ids": [
                record["sigif_record_id"]
                for record in records
                if record["source_row_hash_sha256"] == row_hash
            ],
        }
        for row_hash, count in sorted(duplicate_hashes.items())
        if count > 1
    ]
    invalid_time_values = []
    for record in records:
        for field in ("start_time_reported", "end_time_reported"):
            value = record.get(field)
            if not value:
                continue
            match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
            if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
                invalid_time_values.append(
                    {
                        "sigif_record_id": record["sigif_record_id"],
                        "source_row_index": record["source_row_index"],
                        "field": field,
                        "value": value,
                    }
                )
    negative_surfaces = [
        {
            "sigif_record_id": record["sigif_record_id"],
            "reported_total_area_ha": record["reported_total_area_ha"],
        }
        for record in records
        if record.get("reported_total_area_ha") is not None
        and record["reported_total_area_ha"] < 0
    ]
    return {
        "duplicate_visible_row_group_count": len(duplicate_groups),
        "duplicate_visible_row_groups": duplicate_groups,
        "invalid_clock_value_count": len(invalid_time_values),
        "invalid_clock_value_counts_by_field": dict(
            sorted(collections.Counter(item["field"] for item in invalid_time_values).items())
        ),
        "invalid_clock_value_examples": invalid_time_values[:20],
        "negative_reported_surface_count": len(negative_surfaces),
        "negative_reported_surfaces": negative_surfaces,
        "interpretation_warning": "Values are reported exactly as published and are not corrected; widespread invalid Hora fin values may indicate a source presentation/formatting defect.",
    }


def validate_expected_sigif(config, year, rows):
    warnings = []
    expected = config["years"][str(year)].get("expected_sigif_rows_at_2026_08_19")
    distinct_expected = config["years"][str(year)].get(
        "expected_distinct_visible_rows_at_2026_08_19"
    )
    distinct = len({canonical_json(row) for row in rows})
    if len(rows) != expected:
        warnings.append(
            "SIGIF row count changed from audited {} to {}".format(expected, len(rows))
        )
    if distinct != distinct_expected:
        warnings.append(
            "SIGIF distinct visible row count changed from audited {} to {}".format(
                distinct_expected, distinct
            )
        )
    return distinct, warnings


def build_snapshot(args):
    root = repository_root()
    config_path = (root / args.config).resolve()
    config = load_json(config_path)
    snapshot_id = args.snapshot_id or default_snapshot_id()
    raw_dir = root / "data" / "raw" / "recent" / "gva" / "snapshots" / snapshot_id
    processed_dir = (
        root / "data" / "processed" / "recent" / "gva" / "snapshots" / snapshot_id
    )
    if (raw_dir.exists() or processed_dir.exists()) and not args.force:
        raise RecentDataError(
            "Snapshot {} already exists; choose another --snapshot-id or use --force".format(
                snapshot_id
            )
        )
    acquired_at = now_utc()
    opener = urllib.request.build_opener()
    raw_files = []
    processed_files = []

    print("Downloading official ICV municipal boundary...", flush=True)
    boundary_result = download_boundary(config, opener, args.timeout, args.attempts)
    boundary_metadata_path = raw_dir / "boundary" / "icv_municipalities.metadata.json"
    boundary_raw_path = raw_dir / "boundary" / "icv_municipalities.geojson"
    write_bytes_atomic(boundary_metadata_path, boundary_result["metadata_raw"])
    write_bytes_atomic(boundary_raw_path, boundary_result["raw"])
    raw_files.extend([boundary_metadata_path, boundary_raw_path])
    dissolved_boundary = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "source": "ICV official municipality layer",
                    "derivation": config["administrative_boundary"]["derivation"],
                    "source_feature_count": boundary_result["count"],
                    "acquired_at": acquired_at,
                    "crs": "EPSG:4326",
                },
                "geometry": mapping(boundary_result["boundary"]),
            }
        ],
    }
    dissolved_path = processed_dir / "gva_boundary.geojson"
    write_json_atomic(dissolved_path, dissolved_boundary, compact=True)
    processed_files.append(dissolved_path)

    municipality_features = [
        (feature, shape(feature["geometry"]))
        for feature in boundary_result["collection"]["features"]
    ]

    print("Downloading SIGIF coordinate evidence for 2024...", flush=True)
    sigif_2024 = download_sigif_year(config, 2024, args.timeout, args.attempts)
    sigif_2024_path = raw_dir / "evidence" / "sigif_2024.html"
    write_bytes_atomic(sigif_2024_path, sigif_2024["raw"])
    raw_files.append(sigif_2024_path)
    icv_reference = download_icv_coordinate_reference(
        config, opener, args.timeout, args.attempts
    )
    icv_metadata_path = raw_dir / "evidence" / "icv_2024.metadata.json"
    icv_points_path = raw_dir / "evidence" / "icv_2024_points.json"
    write_bytes_atomic(icv_metadata_path, icv_reference["metadata_raw"])
    write_bytes_atomic(icv_points_path, icv_reference["raw"])
    raw_files.extend([icv_metadata_path, icv_points_path])
    evidence = coordinate_evidence(sigif_2024, icv_reference)
    evidence_path = processed_dir / "coordinate_evidence.json"
    write_json_atomic(evidence_path, evidence)
    processed_files.append(evidence_path)
    if evidence["status"] != "demonstrated":
        print("X1/Y1 evidence is insufficient; spatial matching will be skipped.", flush=True)

    sigif_by_year = {}
    sigif_source_results = {}
    coordinate_diagnostics = {}
    coverage_entries = {}
    for year in (2025, 2026):
        print("Downloading SIGIF {}...".format(year), flush=True)
        result = download_sigif_year(config, year, args.timeout, args.attempts)
        sigif_source_results[year] = result
        raw_path = raw_dir / "sigif" / "{}.html".format(year)
        write_bytes_atomic(raw_path, result["raw"])
        raw_files.append(raw_path)
        records, diagnostics = transform_sigif_rows(
            year, result, evidence, acquired_at, municipality_features
        )
        sigif_by_year[year] = records
        coordinate_diagnostics[year] = diagnostics
        output_path = processed_dir / "sigif_fires_{}.jsonl".format(year)
        write_jsonl_atomic(output_path, records)
        processed_files.append(output_path)
        distinct, warnings = validate_expected_sigif(config, year, result["rows"])
        observed_dates = [record["observed_date"] for record in records if record["observed_date"]]
        coverage_entries[year] = {
            "year": year,
            "sigif_row_count": len(records),
            "sigif_distinct_visible_rows": distinct,
            "sigif_min_date": min(observed_dates) if observed_dates else None,
            "sigif_max_date": max(observed_dates) if observed_dates else None,
            "coverage_start_requested": config["years"][str(year)]["coverage_start_requested"],
            "coverage_end_requested": config["years"][str(year)]["coverage_end_requested"],
            "coverage_complete": config["years"][str(year)]["coverage_complete"],
            "acquired_at": acquired_at,
            "warnings": warnings,
            "sigif_anomalies": sigif_anomalies(records),
        }

    print("Downloading the EFFIS WFS BBOX snapshot...", flush=True)
    effis_bbox = download_effis_bbox(
        config, boundary_result["boundary"], opener, args.timeout, args.attempts
    )
    effis_bbox_path = raw_dir / "effis" / "bbox_all_years.geojson"
    write_bytes_atomic(effis_bbox_path, effis_bbox["raw"])
    raw_files.append(effis_bbox_path)
    effis_by_year = {}
    for year in (2025, 2026):
        source_subset = [
            feature
            for feature in effis_bbox["collection"]["features"]
            if effis_year(feature) == year
        ]
        source_subset_collection = {
            "type": "FeatureCollection",
            "name": "effis_bbox_source_subset_{}".format(year),
            "features": source_subset,
        }
        raw_subset_path = raw_dir / "effis" / "{}_bbox_source_subset.geojson".format(year)
        write_json_atomic(raw_subset_path, source_subset_collection, compact=True)
        raw_files.append(raw_subset_path)
        processed, invalid_count = transform_effis_features(
            year,
            effis_bbox["collection"]["features"],
            boundary_result["boundary"],
            acquired_at,
            config,
        )
        effis_by_year[year] = processed
        output_path = processed_dir / "effis_geometries_{}.geojson".format(year)
        write_json_atomic(
            output_path,
            {
                "type": "FeatureCollection",
                "name": "effis_geometries_{}".format(year),
                "features": processed,
            },
            compact=True,
        )
        processed_files.append(output_path)
        coverage_entries[year].update(
            {
                "effis_bbox_year_feature_count": len(source_subset),
                "effis_true_cv_intersection_count": len(processed),
                "effis_min_firedate": min(
                    (
                        feature["properties"]["effis_fire_date"]
                        for feature in processed
                        if feature["properties"].get("effis_fire_date")
                    ),
                    default=None,
                ),
                "effis_max_firedate": max(
                    (
                        feature["properties"]["effis_fire_date"]
                        for feature in processed
                        if feature["properties"].get("effis_fire_date")
                    ),
                    default=None,
                ),
                "effis_total_area_ha": round(
                    sum(
                        feature["properties"].get("effis_area_ha") or 0
                        for feature in processed
                    ),
                    6,
                ),
                "effis_invalid_geometry_count": invalid_count,
                "effis_nonpositive_area_records": [
                    {
                        "effis_id": feature["properties"]["effis_id"],
                        "area_ha": feature["properties"].get("effis_area_ha"),
                    }
                    for feature in processed
                    if (feature["properties"].get("effis_area_ha") or 0) <= 0
                ],
                "effis_area_warning": "Satellite-derived sum; not official administrative burned area.",
            }
        )

    candidates_by_year = {2025: [], 2026: []}
    if evidence["status"] == "demonstrated":
        for year in (2025, 2026):
            candidates, linked_records = candidate_links(
                year, sigif_by_year[year], effis_by_year[year], config
            )
            candidates_by_year[year] = candidates
            coverage_entries[year].update(
                {
                    "link_candidate_count": len(candidates),
                    "sigif_records_with_candidate": len(linked_records),
                    "sigif_records_without_candidate": len(sigif_by_year[year])
                    - len(linked_records),
                    "candidate_strength_counts": dict(
                        sorted(
                            collections.Counter(
                                candidate["candidate_strength"] for candidate in candidates
                            ).items()
                        )
                    ),
                }
            )
    else:
        for year in (2025, 2026):
            coverage_entries[year].update(
                {
                    "link_candidate_count": 0,
                    "sigif_records_with_candidate": 0,
                    "sigif_records_without_candidate": len(sigif_by_year[year]),
                    "candidate_strength_counts": {},
                    "candidate_generation_skipped": "X1/Y1 evidence insufficient",
                }
            )
    all_candidates = candidates_by_year[2025] + candidates_by_year[2026]
    candidates_path = processed_dir / "sigif_effis_link_candidates.jsonl"
    write_jsonl_atomic(candidates_path, all_candidates)
    processed_files.append(candidates_path)

    cases = representative_cases(sigif_by_year, effis_by_year, candidates_by_year)
    cases_path = processed_dir / "representative_cases.json"
    write_json_atomic(cases_path, cases)
    processed_files.append(cases_path)

    coverage_report = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "phase": "CV-2.2",
        "snapshot_id": snapshot_id,
        "acquired_at": acquired_at,
        "coordinate_evidence_status": evidence["status"],
        "years": [coverage_entries[2025], coverage_entries[2026]],
        "coordinate_diagnostics": {
            str(year): coordinate_diagnostics[year] for year in (2025, 2026)
        },
        "methodological_warnings": [
            config["sigif"]["warning"],
            config["effis"]["warning"],
            "Candidates are not confirmed links and source records remain separate.",
            "2026 coverage_complete=false.",
        ],
    }
    coverage_path = processed_dir / "coverage_report.json"
    write_json_atomic(coverage_path, coverage_report)
    processed_files.append(coverage_path)

    manifest = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "phase": "CV-2.2",
        "snapshot_id": snapshot_id,
        "acquired_at": acquired_at,
        "config_path": str(config_path.relative_to(root)),
        "config_sha256": sha256_file(config_path),
        "raw_snapshot_directory": str(raw_dir.relative_to(root)),
        "processed_snapshot_directory": str(processed_dir.relative_to(root)),
        "source_requests": {
            "sigif": {
                str(year): {
                    "url": config["sigif"]["provisional_results_url"],
                    "method": "POST",
                    "parameters": sigif_source_results[year]["parameters"],
                    "row_count": len(sigif_source_results[year]["rows"]),
                }
                for year in (2025, 2026)
            },
            "coordinate_evidence": {
                "sigif_reference_year": 2024,
                "icv_query_url": icv_reference["query_url"],
                "official_methodology_url": config["coordinate_evidence"][
                    "official_methodology_url"
                ],
            },
            "boundary": {
                "metadata_url": boundary_result["metadata_url"],
                "query_url": boundary_result["query_url"],
                "feature_count": boundary_result["count"],
                "license_url": config["administrative_boundary"]["license_url"],
            },
            "effis": {
                "hits_url": effis_bbox["hits_url"],
                "data_url": effis_bbox["data_url"],
                "bbox_wfs_1_1_axis_order": effis_bbox["bbox_wfs_axis_order"],
                "feature_count_expected_and_downloaded": effis_bbox["expected"],
                "license": config["effis"]["license"],
            },
        },
        "raw_files": [file_metadata(path, root) for path in sorted(raw_files)],
        "processed_files": [
            file_metadata(path, root) for path in sorted(processed_files)
        ],
        "validation_status": "complete",
        "redistribution": {
            "snapshot_publication_allowed": False,
            "sigif": "blocked_pending_written_clarification",
            "effis": "CC BY 4.0; keep attribution and indicate transformations",
            "boundary": "ICV terms apply; source is documented separately",
        },
    }
    manifest_path = processed_dir / "manifest.json"
    write_json_atomic(manifest_path, manifest)
    latest_path = root / "data" / "processed" / "recent" / "gva" / "latest.json"
    write_json_atomic(
        latest_path,
        {
            "snapshot_id": snapshot_id,
            "manifest": str(manifest_path.relative_to(root)),
            "updated_at": acquired_at,
        },
    )
    print("Snapshot {} complete.".format(snapshot_id), flush=True)
    print(json.dumps(coverage_report, ensure_ascii=False, indent=2), flush=True)
    return 0


def validate_snapshot(args):
    root = repository_root()
    snapshot_id = args.validate_snapshot
    manifest_path = (
        root
        / "data"
        / "processed"
        / "recent"
        / "gva"
        / "snapshots"
        / snapshot_id
        / "manifest.json"
    )
    manifest = load_json(manifest_path)
    errors = []
    for entry in manifest.get("raw_files", []) + manifest.get("processed_files", []):
        path = root / entry["path"]
        if not path.is_file():
            errors.append("missing {}".format(entry["path"]))
            continue
        if path.stat().st_size != entry["size_bytes"]:
            errors.append("size mismatch {}".format(entry["path"]))
        if sha256_file(path) != entry["sha256"]:
            errors.append("checksum mismatch {}".format(entry["path"]))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Snapshot {}: all manifest checksums valid".format(snapshot_id))
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default="data/sources/gva_recent_pipeline.json", help="Repository-relative config"
    )
    parser.add_argument("--snapshot-id", help="Immutable snapshot identifier")
    parser.add_argument("--force", action="store_true", help="Replace an existing named snapshot")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--validate-snapshot", metavar="ID", help="Validate an existing snapshot offline")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        if args.validate_snapshot:
            return validate_snapshot(args)
        return build_snapshot(args)
    except (RecentDataError, OSError, ValueError) as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
