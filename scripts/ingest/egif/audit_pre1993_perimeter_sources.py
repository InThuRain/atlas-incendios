#!/usr/bin/env python3
"""Regenera el inventario CV-4.1 y audita ESFire30 sin crear geometrías.

La entrada EGIF normalizada y el límite municipal son snapshots locales ya
auditados. ESFire30 se inspecciona directamente desde el ZIP de Zenodo; el
resultado versionable contiene metadatos y candidatos, nunca geometrías.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EGIF = ROOT / "data/processed/egif/gva/fires_1968_1992.jsonl"
DEFAULT_BOUNDARY = (
    ROOT
    / "data/raw/recent/gva/snapshots/20260819T174426Z/boundary/icv_municipalities.geojson"
)
DEFAULT_OUTPUT = ROOT / "data/sources/gva_pre1993_perimeter_sources.json"
RESEARCH_CUTOFF = "2026-08-25"
EXPECTED_GIF = 180
ESFIRE_SHA256 = "150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8"

QUALITY = {
    "A_OFFICIAL_VECTOR": "Perímetro vectorial oficial disponible.",
    "B_DOCUMENTED_REMOTE_SENSING": "Perímetro de teledetección con método y procedencia documentados.",
    "C_DOCUMENTED_CARTOGRAPHIC_RECONSTRUCTION": "Cartografía suficiente para reconstrucción documentada futura.",
    "D_MAP_ONLY_UNCERTAIN": "Representación gráfica sin base suficiente para digitalizar responsablemente.",
    "E_REFERENCE_ONLY": "El activo está documentado, pero no se ha localizado.",
    "F_UNUSABLE": "No proporciona perímetros individuales utilizables para esta fase.",
}

SOURCES: tuple[dict[str, Any], ...] = (
    {
        "id": "esfire30_causes",
        "title": "ESFire30 Causes: Spatial dataset of wildfire ignition causes in Spain (1985–2021)",
        "authority": "Universidad de Alcalá / CSIC",
        "authors": ["Ángela García Lázaro", "Emilio Chuvieco", "Adrián Jiménez-Ruano"],
        "date": "2026",
        "url": "https://zenodo.org/records/18449006",
        "method_url": "https://doi.org/10.3390/fire9040138",
        "territory": "España peninsular; intersección diagnóstica con el País Valencià",
        "years": [1985, 1992],
        "resource_type": "dataset_vector",
        "format": "SHP anual dentro de ZIP",
        "quality": "B_DOCUMENTED_REMOTE_SENSING",
        "method": "Perímetros anuales ESFire30 derivados de Landsat; asignación posterior de causa por enlace o modelo, no identidad administrativa.",
        "nominal_resolution": "30 m según el artículo metodológico",
        "crs": "El .prj declara ED50 / UTM zona 30N (EPSG:23030)",
        "license": "CC BY 4.0",
        "asset_available": True,
        "redistribution": "Permitida con atribución conforme a CC BY 4.0.",
        "derivative_allowed": True,
        "cautions": [
            "El README dice EPSG:25830, en conflicto con el .prj ED50/UTM30.",
            "El README escribe 30 km donde el artículo documenta 30 m; requiere aclaración editorial.",
            "No contiene fecha, municipio ni identificador EGIF; no confirma enlaces de episodios.",
        ],
        "next_action": "Solicitar a los autores aclaración del CRS y usar fecha/municipio o archivo maestro si existe antes de enlazar a EGIF.",
    },
    {
        "id": "gva_annual_perimeter_archive_1978_valencia",
        "title": "Cartografía anual de perímetros de incendios de la Conselleria",
        "authority": "Generalitat Valenciana / Conselleria competente en medio ambiente",
        "date": "1978–actualidad (alcance documentado para Valencia)",
        "url": "https://secforestales.org/publicaciones/index.php/cuadernos_secf/article/download/17385/17214/0",
        "territory": "Provincia de Valencia desde 1978; Alicante y Castellón desde 1993",
        "years": [1978, 1992],
        "resource_type": "referenced_official_vector_archive",
        "format": "vector anual, formato original no localizado",
        "quality": "E_REFERENCE_ONLY",
        "method": "Perímetros elaborados anualmente por la administración; precisión inicial menor y mejora posterior con GPS/teledetección.",
        "license": "No determinada para el activo subyacente",
        "asset_available": False,
        "redistribution": "Requiere confirmación del custodio; la licencia del artículo no licencia el archivo vectorial.",
        "derivative_allowed": None,
        "next_action": "Solicitar a Generalitat el archivo 1978–1992 de Valencia, metadatos, CRS, escala y condiciones de reutilización.",
    },
    {
        "id": "gva_burned_forest_register",
        "title": "Certificado del Registro de Terrenos Forestales Incendiados",
        "authority": "Generalitat Valenciana",
        "date": "trámite vigente consultado en 2026",
        "url": "https://sede.gva.es/es/detall-tramit?id_proc=3261",
        "territory": "Comunitat Valenciana",
        "years": None,
        "resource_type": "official_request_route",
        "format": "certificado; puede incorporar plano/georreferenciación",
        "quality": "E_REFERENCE_ONLY",
        "method": "Consulta oficial por parcela, municipio y año; no acredita por sí sola cobertura pre-1993.",
        "license": "No determinada para redistribución masiva",
        "asset_available": False,
        "redistribution": "Debe aclararse para cada entrega.",
        "derivative_allowed": None,
        "next_action": "Consultar al registro si conserva expedientes y cartografía individual 1968–1992 y si existe acceso masivo para investigación.",
    },
    {
        "id": "gva_chera_sot_prevention_plan",
        "title": "Plan de prevención de incendios de Chera–Sot de Chera: análisis histórico",
        "authority": "Generalitat Valenciana",
        "date": "2006 (documento del plan)",
        "url": "https://mediambient.gva.es/auto/prevencion-incendios/Red-espacios-protegidos/Chera-Sot%20de%20Chera/Documentacion%20en%20castellano/Plan%20de%20prevencion/01-Analisis_historico_incendios/Analisis_hist_informe.pdf",
        "territory": "Parque Natural de Chera–Sot de Chera",
        "years": [1978, 2004],
        "resource_type": "map_pdf",
        "format": "PDF con mapas temáticos",
        "quality": "D_MAP_ONLY_UNCERTAIN",
        "method": "Síntesis cartográfica del plan; el propio documento advierte que superficies antiguas son aproximadas.",
        "scale": "No documentada de forma suficiente para digitalización",
        "license": "Consulta pública; reutilización del mapa/derivado no aclarada",
        "asset_available": True,
        "redistribution": "No asumida.",
        "derivative_allowed": None,
        "digitalization": {
            "georeferenced": False,
            "control_points_visible": True,
            "base_identifiable": "parcialmente",
            "perimeter_clear": "variable",
            "expected_error": "desconocido y potencialmente alto",
        },
        "next_action": "Solicitar la cartografía fuente y su ficha técnica, no digitalizar el PDF actual.",
    },
    {
        "id": "martin_chuvieco_1995_noaa",
        "title": "Cartografía de grandes incendios forestales en la España mediterránea a partir de imágenes NOAA-AVHRR",
        "authority": "MITECO, revista Ecología",
        "authors": ["M. Pilar Martín", "Emilio Chuvieco"],
        "date": "1995",
        "url": "https://www.miteco.gob.es/content/dam/miteco/es/parques-nacionales-oapn/publicaciones/ecologia_09_02_tcm30-100709.pdf",
        "territory": "España mediterránea; incluye Valencia",
        "years": [1991, 1991],
        "resource_type": "technical_article_maps",
        "format": "PDF; mapas/figuras, activos digitales no localizados",
        "quality": "B_DOCUMENTED_REMOTE_SENSING",
        "method": "NOAA-AVHRR, píxel nominal 1,1 km, validación con cartografía DGCN y trabajo de campo; el perímetro de Buñol tuvo apoyo GPS más completo.",
        "license": "Reutilización del artículo y de los activos digitales no determinada",
        "asset_available": True,
        "digital_asset_available": False,
        "redistribution": "No determinada.",
        "derivative_allowed": None,
        "next_action": "Solicitar capas/ráster originales y metadatos de los incendios valencianos de 1991.",
    },
    {
        "id": "martin_chuvieco_1998_noaa",
        "title": "Cartografía de grandes incendios forestales en la Península Ibérica a partir de NOAA-AVHRR",
        "authority": "Universidad de Alcalá / CSIC",
        "authors": ["M. Pilar Martín", "Emilio Chuvieco"],
        "date": "1998",
        "url": "https://digital.csic.es/bitstream/10261/6426/1/Martin_Isabel_Serie_Geografica.pdf",
        "territory": "Península Ibérica",
        "years": [1991, 1995],
        "resource_type": "technical_article_maps",
        "format": "PDF; mapa digital descrito, activo no localizado",
        "quality": "B_DOCUMENTED_REMOTE_SENSING",
        "method": "NOAA-AVHRR; 1,1 km en nadir y degradación hacia bordes; contraste limitado por escasez de perímetros fiables.",
        "license": "Reutilización del activo no determinada",
        "asset_available": True,
        "digital_asset_available": False,
        "redistribution": "No determinada.",
        "derivative_allowed": None,
        "next_action": "Pedir el mapa digital, tabla de escenas/incendios y licencia.",
    },
    {
        "id": "martin_thesis_noaa",
        "title": "Cartografía e inventario de incendios forestales en la Península Ibérica a partir de imágenes NOAA-AVHRR",
        "authority": "Universidad de Alcalá / CSIC",
        "authors": ["M. Pilar Martín"],
        "date": "1998/1999",
        "url": "https://ebuah.uah.es/dspace/handle/10017/43674",
        "territory": "Península Ibérica",
        "years": None,
        "resource_type": "doctoral_thesis_and_referenced_assets",
        "format": "tesis; ficheros digitales no recibidos",
        "quality": "E_REFERENCE_ONLY",
        "method": "Teledetección NOAA-AVHRR y validación de campo; existencia de cartografía confirmada por comunicación directa de la autora.",
        "license": "Licencia de los ficheros aún no determinada",
        "asset_available": False,
        "redistribution": "No autorizada todavía.",
        "derivative_allowed": None,
        "next_action": "Solicitar inventario, formatos, metadatos, procedencia de validación y autorización de reutilización.",
    },
    {
        "id": "viedma_chuvieco_1993_hoya_bunol",
        "title": "Evaluación de daños causados por incendios forestales mediante imágenes Landsat-TM",
        "authority": "Universidad de Alcalá",
        "authors": ["O. Viedma", "Emilio Chuvieco"],
        "date": "1993",
        "url": "https://infomadera.net/uploads/articulos/archivo_2154_11506.pdf",
        "territory": "Hoya de Buñol, Valencia",
        "years": [1991, 1991],
        "resource_type": "technical_article_maps",
        "format": "PDF; resultados raster/vectoriales no localizados",
        "quality": "B_DOCUMENTED_REMOTE_SENSING",
        "method": "Landsat TM de 30 m antes/después; registro UTM con RMSE de 0,8 píxeles y parcelas de campo; comparación con perímetro de la Unidad Forestal de Valencia.",
        "license": "Reutilización del artículo/activos no determinada",
        "asset_available": True,
        "digital_asset_available": False,
        "redistribution": "No determinada.",
        "derivative_allowed": None,
        "next_action": "Solicitar los resultados digitales y el perímetro oficial de contraste para Yátova y Chiva 1991.",
    },
    {
        "id": "lopez_caselles_1991_landsat",
        "title": "Mapping burns and natural reforestation using Thematic Mapper data",
        "authority": "Universitat de València",
        "authors": ["M. J. López García", "V. Caselles"],
        "date": "1991",
        "url": "https://doi.org/10.1080/10106049109354290",
        "territory": "Provincia de Valencia",
        "years": None,
        "resource_type": "scientific_article_maps",
        "format": "artículo; activos digitales no localizados",
        "quality": "B_DOCUMENTED_REMOTE_SENSING",
        "method": "Cartografía de áreas quemadas y regeneración mediante Landsat 5 TM.",
        "license": "Copyright editorial; licencia de datos no localizada",
        "asset_available": True,
        "digital_asset_available": False,
        "redistribution": "No determinada.",
        "derivative_allowed": None,
        "next_action": "Obtener texto completo autorizado, identificar incendios/años y preguntar por archivos digitales.",
    },
    {
        "id": "gva_goiif_archive",
        "title": "Archivo de investigación de causas del GOIIF y grupos precursores",
        "authority": "Generalitat Valenciana",
        "date": "antecedentes operativos desde 1991–1992",
        "url": "https://mediambient.gva.es/es/web/prevencion-de-incendios/investigacion-de-incendios-forestales",
        "territory": "Comunitat Valenciana",
        "years": [1991, 1992],
        "resource_type": "referenced_administrative_archive",
        "format": "informes/croquis potenciales; colección no localizada públicamente",
        "quality": "E_REFERENCE_ONLY",
        "method": "Investigación administrativa de incendios; la página acredita antecedentes, no inventaría cartografía conservada.",
        "license": "No determinada",
        "asset_available": False,
        "redistribution": "No determinada.",
        "derivative_allowed": None,
        "next_action": "Preguntar por expedientes 1991–1992 con croquis o perímetros, acceso y reutilización.",
    },
    {
        "id": "icv_1977_orthophoto",
        "title": "Ortofoto de 1977 (Interministerial) de la Comunitat Valenciana",
        "authority": "Institut Cartogràfic Valencià / Generalitat",
        "date": "vuelo 1976–1978; ortofoto publicada posteriormente",
        "url": "https://datos.gob.es/es/catalogo/a10002983-ortofoto-de-1977-interministerial-de-la-comunitat-valenciana-pancromatica-y-de-25-cm-de-resoluc",
        "territory": "Comunitat Valenciana",
        "years": [1976, 1978],
        "resource_type": "reference_orthophoto",
        "format": "TIFF/ECW/WMS georreferenciado",
        "quality": "F_UNUSABLE",
        "method": "Base ortofotográfica, no inventario de incendios ni perímetros individuales.",
        "crs": "ETRS89 / UTM zona 30N",
        "license": "CC BY 4.0",
        "asset_available": True,
        "redistribution": "Permitida con atribución, pero no convierte manchas visibles en perímetros documentados.",
        "derivative_allowed": True,
        "next_action": "Usar solo como base/control en una reconstrucción C respaldada por otra fuente de evento.",
    },
    {
        "id": "esa_fireccilt11",
        "title": "FireCCI51/FireCCILT11 burned area products",
        "authority": "ESA Climate Change Initiative",
        "date": "producto histórico",
        "url": "https://catalogue.ceda.ac.uk/uuid/4b7a36e1564a4c5784e8d667c810d27f",
        "territory": "global",
        "years": [1982, 2018],
        "resource_type": "coarse_burned_area_raster",
        "format": "NetCDF raster 0,05° / grid agregado 0,25°",
        "quality": "F_UNUSABLE",
        "method": "Área quemada mensual de baja resolución; no perímetros individuales de episodios.",
        "license": "Licencia del producto ESA/CEDA",
        "asset_available": True,
        "redistribution": "Sujeta a sus condiciones; no es adecuado al objetivo CV-4.1.",
        "derivative_allowed": None,
        "next_action": "No usar para reconstruir perímetros individuales.",
    },
    {
        "id": "ceam_postfire",
        "title": "PostFire — visor de incendios forestales",
        "authority": "Fundación CEAM",
        "date": "cobertura publicada desde 1993",
        "url": "https://postfire.es/",
        "territory": "Comunitat Valenciana",
        "years": [1993, 2019],
        "resource_type": "out_of_period_perimeter_portal",
        "format": "visor/dataset de perímetros",
        "quality": "F_UNUSABLE",
        "method": "Producto posterior a 1992; útil como referencia metodológica, no como fuente pre-1993 localizada.",
        "license": "Consultar portal",
        "asset_available": True,
        "redistribution": "No evaluada porque queda fuera del periodo.",
        "derivative_allowed": None,
        "next_action": "Preguntar solo si conservan antecedentes o escenas previas a 1993.",
    },
    {
        "id": "miteco_egif_annual_maps",
        "title": "Anuarios y mapas agregados de la Estadística General de Incendios Forestales",
        "authority": "MITECO / antiguos ICONA y DGB",
        "date": "1968–1992",
        "url": "https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html",
        "territory": "España",
        "years": [1968, 1992],
        "resource_type": "statistics_and_grid_maps",
        "format": "PDF/tablas/mapas agregados",
        "quality": "F_UNUSABLE",
        "method": "Estadística y referencias de cuadrícula; no perímetros individuales.",
        "license": "Condiciones generales de reutilización MITECO",
        "asset_available": True,
        "redistribution": "Permitida con las condiciones MITECO, sin desnaturalizar.",
        "derivative_allowed": True,
        "next_action": "Conservar para contraste documental, nunca como perímetro.",
    },
)

MANUAL_LINKS: dict[str, list[dict[str, str]]] = {
    "1986461220": [
        {"source_id": "gva_chera_sot_prevention_plan", "status": "strong_candidate", "reason": "Misma fecha (18/05/1986), municipio Sot de Chera y superficie aproximada del plan; el mapa no permite enlace confirmado."},
    ],
    "1992460251": [
        {"source_id": "gva_chera_sot_prevention_plan", "status": "strong_candidate", "reason": "Misma fecha (31/08/1992), municipio y superficie aproximada ~1.092 ha; falta cartografía fuente."},
    ],
    "1991460176": [
        {"source_id": "viedma_chuvieco_1993_hoya_bunol", "status": "strong_candidate", "reason": "Yátova, 28/07/1991 y escala compatible con el incendio cartografiado; faltan IDs en el activo."},
        {"source_id": "martin_chuvieco_1995_noaa", "status": "strong_candidate", "reason": "El artículo identifica Yátova en la campaña 1991; no aporta NumeroParte."},
    ],
    "1991460188": [
        {"source_id": "viedma_chuvieco_1993_hoya_bunol", "status": "strong_candidate", "reason": "Chiva, 31/07/1991 y escala compatible; falta identificador fuente común."},
        {"source_id": "martin_chuvieco_1995_noaa", "status": "strong_candidate", "reason": "El artículo identifica Chiva en 1991; no aporta NumeroParte."},
    ],
    "1991460131": [
        {"source_id": "martin_chuvieco_1995_noaa", "status": "possible_candidate", "reason": "El mapa nombra Llutxent, pero el artículo no publica NumeroParte/fecha inequívocos."},
    ],
    "1991460181": [
        {"source_id": "martin_chuvieco_1995_noaa", "status": "possible_candidate", "reason": "El mapa nombra Tavernes, pero no publica NumeroParte."},
    ],
    "1991460184": [
        {"source_id": "martin_chuvieco_1995_noaa", "status": "possible_candidate", "reason": "El mapa nombra Villalonga, pero no publica NumeroParte."},
    ],
    "1992460250": [
        {"source_id": "gva_annual_perimeter_archive_1978_valencia", "status": "possible_candidate", "reason": "Marines está dentro del periodo/territorio del archivo, pero el activo no está disponible."},
    ],
    "1992120403": [
        {"source_id": "gva_goiif_archive", "status": "possible_candidate", "reason": "Parte de Altura compatible con el episodio interprovincial documentado; no se ha localizado croquis/perímetro."},
    ],
    "1992469001": [
        {"source_id": "gva_annual_perimeter_archive_1978_valencia", "status": "possible_candidate", "reason": "Parte valenciano compatible con Marines–Altura; identidad multiparte continúa sin resolver."},
    ],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_gif_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record["geometry"] is not None:
                raise ValueError(f"EGIF contiene geometría inesperada: {record['source_record_id']}")
            if record["is_gif_ge_500_ha"]:
                records.append(record)
    if len(records) != EXPECTED_GIF:
        raise ValueError(f"Se esperaban {EXPECTED_GIF} partes GIF y se obtuvieron {len(records)}")
    return records


def province_name(raw: str) -> str:
    if raw.startswith("Alacant"):
        return "Alicante"
    if raw.startswith("Castelló"):
        return "Castellón"
    if raw.startswith("València"):
        return "Valencia"
    raise ValueError(f"Provincia ICV desconocida: {raw}")


def inspect_esfire30(zip_path: Path, boundary_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        import shapefile
        from pyproj import CRS, Transformer
        from shapely.geometry import shape
        from shapely.ops import transform, unary_union
        from shapely.prepared import prep
    except ImportError as error:  # pragma: no cover - mensaje para ejecución manual
        raise RuntimeError("Instala requirements-dev.txt para auditar ESFire30") from error

    digest = sha256_file(zip_path)
    if digest != ESFIRE_SHA256:
        raise ValueError(f"SHA-256 ESFire30 inesperado: {digest}")

    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    by_province: dict[str, list[Any]] = defaultdict(list)
    for feature in boundary["features"]:
        by_province[province_name(feature["properties"]["provincia"])].append(shape(feature["geometry"]))
    wgs84_provinces = {name: unary_union(parts) for name, parts in by_province.items()}

    selected: list[dict[str, Any]] = []
    geometry_hashes: set[str] = set()
    total_vertices = 0
    geojson_features: list[bytes] = []
    prj_values: set[str] = set()
    with zipfile.ZipFile(zip_path) as archive:
        reference_prj = archive.read("RF_jja/predicciones_1985.prj").decode("utf-8").strip()
        reference_crs = CRS.from_wkt(reference_prj)
        transformer = Transformer.from_crs("EPSG:4326", reference_crs, always_xy=True)
        provinces = {name: transform(transformer.transform, geom) for name, geom in wgs84_provinces.items()}
        prepared_provinces = {name: prep(geometry) for name, geometry in provinces.items()}
        min_x = min(geometry.bounds[0] for geometry in provinces.values())
        min_y = min(geometry.bounds[1] for geometry in provinces.values())
        max_x = max(geometry.bounds[2] for geometry in provinces.values())
        max_y = max(geometry.bounds[3] for geometry in provinces.values())
        for year in range(1985, 1993):
            base = f"RF_jja/predicciones_{year}"
            prj = archive.read(base + ".prj").decode("utf-8").strip()
            prj_values.add(prj)
            reader = shapefile.Reader(
                shp=io.BytesIO(archive.read(base + ".shp")),
                shx=io.BytesIO(archive.read(base + ".shx")),
                dbf=io.BytesIO(archive.read(base + ".dbf")),
                encoding="utf-8",
            )
            for index, shape_record in enumerate(reader.iterShapeRecords()):
                shape_bbox = shape_record.shape.bbox
                if (
                    shape_bbox[2] < min_x
                    or shape_bbox[0] > max_x
                    or shape_bbox[3] < min_y
                    or shape_bbox[1] > max_y
                ):
                    continue
                geometry = shape(shape_record.shape.__geo_interface__)
                hits = [name for name, province in prepared_provinces.items() if province.intersects(geometry)]
                if not hits:
                    continue
                if len(hits) == 1:
                    primary = hits[0]
                else:
                    overlaps = {name: geometry.intersection(provinces[name]).area for name in hits}
                    primary = max(overlaps, key=overlaps.get)
                row = shape_record.record.as_dict()
                total_vertices += len(shape_record.shape.points)
                geometry_hashes.add(hashlib.sha256(geometry.wkb).hexdigest())
                compact_feature = {
                    "type": "Feature",
                    "geometry": shape_record.shape.__geo_interface__,
                    "properties": {
                        "id": f"esfire30:{year}:{index}",
                        "year": year,
                        "area_ha": round(float(row["area_ha"]), 4),
                    },
                }
                geojson_features.append(
                    json.dumps(compact_feature, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                )
                selected.append(
                    {
                        "candidate_id": f"esfire30:{year}:{index}",
                        "year": year,
                        "source_record_index": index,
                        "id_cuad": row.get("Id_cuad"),
                        "area_ha": round(float(row["area_ha"]), 4),
                        "cause_assignment_method": int(row["Method"]) if row.get("Method") is not None else None,
                        "primary_province_by_overlap": primary,
                        "intersected_provinces": sorted(hits),
                    }
                )

    if len(prj_values) != 1:
        raise ValueError("Los SHP 1985–1992 no comparten el mismo .prj")
    declared_crs = CRS.from_wkt(next(iter(prj_values)))
    by_year = Counter(row["year"] for row in selected)
    by_province_count = Counter(row["primary_province_by_overlap"] for row in selected)
    by_year_province: dict[int, Counter[str]] = defaultdict(Counter)
    for row in selected:
        by_year_province[row["year"]][row["primary_province_by_overlap"]] += 1
    geojson = b'{"type":"FeatureCollection","features":[' + b",".join(geojson_features) + b"]}"
    summary = {
        "snapshot": {
            "url": "https://zenodo.org/records/18449006/files/ESFire30_Causes.zip",
            "bytes": zip_path.stat().st_size,
            "sha256": digest,
            "downloaded_to_repository": False,
        },
        "years_inspected": [1985, 1992],
        "selection_rule": "Intersección geométrica real con la unión de límites municipales oficiales ICV; provincia asignada por mayor área de intersección.",
        "boundary": {
            "path_local_ignored": str(boundary_path.relative_to(ROOT)),
            "source": "ICV/Generalitat, capa oficial de municipios",
            "crs": "EPSG:4326 en el snapshot",
            "features": len(boundary["features"]),
        },
        "shapefile_crs": {"name": declared_crs.name, "epsg": declared_crs.to_epsg(), "prj": next(iter(prj_values))},
        "metadata_crs_conflict": "README: EPSG:25830; .prj: ED50 / UTM 30N (EPSG:23030). Se utilizó el .prj para la inspección y el conflicto queda abierto.",
        "selected_polygons": len(selected),
        "by_year": dict(sorted(by_year.items())),
        "by_primary_province": dict(sorted(by_province_count.items())),
        "by_year_and_primary_province": {
            str(year): dict(sorted(counts.items())) for year, counts in sorted(by_year_province.items())
        },
        "cross_province_polygons": sum(len(row["intersected_provinces"]) > 1 for row in selected),
        "source_area_ha_sum_unclipped": round(sum(row["area_ha"] for row in selected), 2),
        "geometry_complexity": {
            "unique_geometry_wkb_hashes": len(geometry_hashes),
            "vertices": total_vertices,
            "minimal_geojson_estimate_bytes": len(geojson),
            "minimal_geojson_estimate_gzip_bytes": len(gzip.compress(geojson, compresslevel=9, mtime=0)),
            "note": "Estimación diagnóstica con geometría original y solo id/año/área; no es un asset generado ni publicable en esta fase.",
        },
        "geometry_exported": False,
    }
    return summary, selected


def candidate_matrix(gif_records: list[dict[str, Any]], esfire: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_grid: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for feature in esfire:
        by_grid[(feature["year"], feature["id_cuad"])].append(feature)

    matrix: list[dict[str, Any]] = []
    for record in sorted(gif_records, key=lambda item: item["source_record_id"]):
        location = record["location_original"]
        grid_id = None
        if location.get("map_sheet") and location.get("grid"):
            grid_id = f"{location['map_sheet']}{location['grid']}"
        candidates = by_grid.get((record["year"], grid_id), []) if grid_id else []
        total_area = record["reported_total_area_ha"]
        candidate_details = []
        for feature in sorted(candidates, key=lambda item: item["area_ha"], reverse=True):
            difference = abs(feature["area_ha"] - total_area) if total_area is not None else None
            candidate_details.append(
                {
                    "candidate_id": feature["candidate_id"],
                    "area_ha": feature["area_ha"],
                    "absolute_area_difference_ha": round(difference, 4) if difference is not None else None,
                    "status": "possible_candidate",
                    "basis": "mismo año y mismo Id_cuad; no prueba identidad ni igualdad de perímetro",
                }
            )
        links = list(MANUAL_LINKS.get(record["source_record_id"], []))
        if record["province"] == "Valencia" and 1978 <= record["year"] <= 1992:
            links.append(
                {
                    "source_id": "gva_annual_perimeter_archive_1978_valencia",
                    "status": "unlinked_scope_candidate",
                    "reason": "El parte cae en el alcance provincia/año documentado; se desconoce si existe una feature individual.",
                }
            )
        statuses = [link["status"] for link in links] + [item["status"] for item in candidate_details]
        overall = "strong_candidate" if "strong_candidate" in statuses else "possible_candidate" if "possible_candidate" in statuses else "unlinked"
        matrix.append(
            {
                "source_record_id": record["source_record_id"],
                "year": record["year"],
                "province": record["province"],
                "municipality": record["municipality"],
                "detection_date": record["detection_date"],
                "reported_forest_area_ha": record["reported_forest_area_ha"],
                "reported_total_area_ha": record["reported_total_area_ha"],
                "egif_sheet_grid": grid_id,
                "link_status": overall,
                "documentary_candidates": links,
                "esfire30_same_year_grid_candidates": candidate_details,
            }
        )
    return matrix


def build_inventory(egif_path: Path, boundary_path: Path, esfire_zip: Path) -> dict[str, Any]:
    gif_records = load_gif_records(egif_path)
    esfire_summary, esfire_features = inspect_esfire30(esfire_zip, boundary_path)
    matrix = candidate_matrix(gif_records, esfire_features)
    quality_counts = Counter(source["quality"] for source in SOURCES)
    link_counts = Counter(row["link_status"] for row in matrix)
    same_grid = sum(bool(row["esfire30_same_year_grid_candidates"]) for row in matrix)
    exact_ten = sum(
        any(candidate["absolute_area_difference_ha"] <= 10 for candidate in row["esfire30_same_year_grid_candidates"])
        for row in matrix
    )
    by_province = Counter(record["province"] for record in gif_records)
    by_decade = Counter("1968-1969" if record["year"] < 1970 else f"{record['year'] // 10 * 10}s" for record in gif_records)
    source_defaults = {
        "territory": None,
        "years": None,
        "resource_type": None,
        "format": None,
        "scale": None,
        "crs": None,
        "georeferenced": None,
        "method": None,
        "original_source": None,
        "license": "No determinada",
        "asset_available": False,
        "digital_asset_available": None,
        "redistribution": "No determinada.",
        "derivative_allowed": None,
        "precision_known": None,
        "possible_egif_link": "candidate_only",
        "next_action": None,
    }
    normalized_sources = [{**source_defaults, **source} for source in SOURCES]
    return {
        "schema_version": "cv-4.1-1",
        "research_cutoff": RESEARCH_CUTOFF,
        "scope": {
            "territory": ["Alicante", "Castellón", "Valencia"],
            "priority_period": [1968, 1992],
            "geometry_created": 0,
            "frontend_modified": False,
            "public_bundle_modified": False,
        },
        "classification_policy": QUALITY,
        "sources": normalized_sources,
        "source_summary": {
            "relevant_sources": len(SOURCES),
            "by_quality": {state: quality_counts.get(state, 0) for state in QUALITY},
            "accessible_vector_datasets": 1,
            "referenced_unavailable_official_vector_archives": 1,
            "map_or_remote_sensing_documents": 5,
        },
        "esfire30_diagnostic": esfire_summary,
        "egif_gif_matrix": matrix,
        "egif_gif_summary": {
            "parts": len(matrix),
            "by_province": dict(sorted(by_province.items())),
            "by_decade": dict(sorted(by_decade.items())),
            "by_link_status": {key: link_counts.get(key, 0) for key in ("strong_candidate", "possible_candidate", "unlinked")},
            "with_esfire30_same_year_grid_candidate": same_grid,
            "with_esfire30_area_difference_le_10_ha": exact_ten,
            "confirmed_links": 0,
            "official_valencia_archive_scope_parts_1978_1992": sum(
                row["province"] == "Valencia" and 1978 <= row["year"] <= 1992 for row in matrix
            ),
        },
        "license_finding": "Solo ESFire30 y la ortofoto ICV declaran CC BY 4.0 de forma suficiente para redistribuir sus propios activos/derivados con atribución; la licencia no se transfiere a documentos o archivos fuente de terceros.",
        "next_phase": "CV-4.2 debe adquirir y auditar primero ESFire30 y solicitar el archivo oficial valenciano 1978–1992, los activos NOAA/Landsat y sus licencias; cualquier enlace EGIF permanece candidato.",
    }


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(serialized)
        temporary = Path(stream.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--egif", type=Path, default=DEFAULT_EGIF)
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--esfire30-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build_inventory(args.egif, args.boundary, args.esfire30_zip)
    if args.check:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        normalized_result = json.loads(json.dumps(result, ensure_ascii=False))
        if existing != normalized_result:
            raise SystemExit("El inventario versionado no coincide con la regeneración")
        print(f"OK: {args.output}")
        return 0
    atomic_write(args.output, result)
    print(f"Escrito {args.output}: {len(result['sources'])} fuentes, {len(result['egif_gif_matrix'])} partes GIF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
