# ES-4C2A2 — Provincias oficiales y navegación CCAA → provincia

## Alcance

ES-4C2A2 amplía exclusivamente `prototypes/es4c/`: límites administrativos oficiales provinciales, navegación España → CCAA → provincia, `fitBounds` administrativo y filtro de partes EGIF por `province_id`.

No modifica el visor valenciano publicado, `public-data-v5`, Pages, assets EGIF ni el PMTiles ESFire30. Seleccionar una provincia **no** filtra ESFire30: sus teselas continúan respondiendo solo a viewport y periodo.

## Fuente y procedencia

- Producto: IGN/CNIG BDLJE / Límites y Unidades Administrativas Actuales, colección OGC API Features `administrativeunit`, nivel `Provincia`.
- URL: `https://api-features.ign.es/collections/administrativeunit/items?f=json&limit=100&nationallevelname=Provincia`
- Recuperación OGC: 2026-08-26; catálogo consultado: 2026-08-28. Metadatos de catálogo: Shapefile 2026-07-28; GML 2026-08-10.
- Raw local fuera de Git: `data/raw/territories/spain/ign-ogc-2026-08-26/province-level.geojson`; 187.127.244 B; SHA-256 `58e4f68f4efc324dd9dfd0c1df0ea755846e3b717676b7137456577dc2083290`.
- Entrega: GeoJSON CRS84/WGS84-compatible. BDLJE distingue ETRS89 geográfico para península, Baleares, Ceuta y Melilla, y REGCAN95 geográfico para Canarias. El derivado web se expresa explícitamente en EPSG:4326.
- Licencia: CC BY 4.0. Atribución: **“Obra derivada de BDLJE CC-BY 4.0 ign.es”**.

El derivado es local y exclusivo del prototipo; no es un asset de producción.

## Inventario de las 53 features fuente

Las 53 features de `nationallevelname = Provincia` no son 53 provincias canónicas:

| Rol fuente | Features | Tratamiento ES-2 |
| --- | ---: | --- |
| Provincias | 50 | `ES:PROV:01` … `ES:PROV:50` |
| Ceuta | 1 | unidad estadística 51 → `ES:CCAA:18`, ciudad autónoma |
| Melilla | 1 | unidad estadística 52 → `ES:CCAA:19`, ciudad autónoma |
| Territorios no asociados a ninguna provincia | 1 | excluida (`34205400000`) |

España se modela como **50 provincias + 2 ciudades autónomas con códigos estadísticos equivalentes de nivel provincial**, no como “53 provincias”. Los campos inspeccionados incluyen `nationalcode`, `nameunit`, `nationallevelname`, `nationallevel`, `codnut1`, `codnut2`, `codnut3` y `country`; el crosswalk usa solo `nationalcode`, nunca nombres.

La estructura aplicada es `34` + código CCAA + código provincial/equivalente + ceros. Para las 50 provincias, el código CCAA se contrasta con `parent_id` del snapshot ES-2. `34185100000` y `34195200000` quedan inventariados como representaciones fuente de Ceuta/Melilla, sin crear IDs `ES:PROV:51/52`.

## Derivado local

`scripts/territories/build_provinces_prototype.py` produce `data/derived/spain/es4c2a/provinces.geojson` (ignorado por Git), `data/sources/spain_province_territories_manifest.json` (provenance y crosswalk) y `prototypes/es4c/province_catalog.mjs` (catálogo ES-2 determinista de 50 provincias y su `parent_id`).

Cada feature contiene `territory_id`, `parent_id`, `source_code`, `official_name`, `source_name`, `territory_type`, `bounds` y geometría. Se preservan `MultiPolygon`, islas y enclaves; no se recorta ni reconstruye nada desde incendios. La simplificación de topología preservada usa 10 m en EPSG:3857 y retorna EPSG:4326:

- 50 provincias lógicas, sin IDs repetidos, geometrías nulas o inválidas.
- 10.781.436 B raw; 3.552.897 B gzip.
- SHA-256: `98502078e51899fb113539b073c522c954da849841c428e6e41289f6bafc2f01`.
- 1.186.185 → 315.159 vértices (−73,43 %).
- Error relativo de área: p95 0,001552 %; máximo 0,002207 %.

Los bounds administrativos son la única base de `fitBounds`.

## Runtime y estado

`es4c-state-v1` incorpora `province_id` como campo aditivo: los enlaces C1C2 sin él siguen restaurándose. Estados válidos:

```text
ES                   → autonomous_community_id = null, province_id = null
autonomous_community → CCAA válida, province_id = null
province             → CCAA padre válida + ES:PROV:NN válida
```

La relación `province_id → parent_id` se valida contra el catálogo ES-2. Una URL con provincia inválida o parent incoherente se sanea a defaults seguros, sin interpretación por nombre.

Al seleccionar provincia el prototipo resalta el límite BDLJE, hace `fitBounds`, mantiene la CCAA padre y carga EGIF por `CCAA × bloque` como antes. Después filtra INITIAL por igualdad exacta `province_id`, recalculando partes, GIF administrativos, superficies conocidas/desconocidas, municipios y distribución anual. Si una ficha EGIF sale del ámbito provincial se limpia; una selección ESFire30 no se toca. Alacant → València reutiliza el INITIAL CCAA en caché. Ceuta/Melilla no muestran provincia ficticia.

El breadcrumb permite Provincia → CCAA → España. Al volver a España, EGIF usa solo el resumen de manifest sin INITIAL nacional. El restore preserva center/zoom y solo resalta límites; no hace `fitBounds` durante restauración.

## Validación dirigida

Tests específicos correctos: inventario 53/50, crosswalk, ciudades autónomas, geometría/bounds/multipartes, reducer y serializer `province_id`, filtro columnar EGIF, caché de misma CCAA y aislamiento de producción.

Smokes Chromium locales correctos, sin benchmark:

- Comunitat Valenciana → Alacant: 1.421 partes EGIF en 1993–2002.
- Alacant → València: 2.323 partes; una petición INITIAL antes y después del cambio (sin refetch).
- Galicia → A Coruña: 26.586; Andalucía → Sevilla: 1.429.
- Canarias: Las Palmas 8 y Santa Cruz de Tenerife 48 en 1995; la falta de ESFire30 no se trata como error territorial.
- Baleares, Ceuta (3 partes) y Melilla (0) comprobadas.
- URL provincial restaurada; breadcrumb a España; móvil 390×844 utilizable.

Todos los requests PMTiles observados conservaron HTTP 206 y no hubo descarga completa. ESFire30 sigue sin filtro CCAA/provincia por decisión explícita.

## Límite y siguiente requisito

No se añaden municipios, relaciones ESFire30-territorio, geometrías EGIF, CCINIF, causas ni producción. ES-4C2A3 deberá adquirir y auditar el nivel municipal oficial y su vigencia histórica, sin inferir municipios desde perímetros o registros sin resolver.
