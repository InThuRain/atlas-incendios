# ES-4C2A1 — Fundación territorial nacional: CCAA oficiales

Estado: implementado localmente y pendiente de revisión. Esta fase solo
modifica el prototipo aislado `prototypes/es4c/`; no cambia el visor público,
sus permalinks v1, bundles ni publicación.

## Fuente y snapshot

La fuente es IGN/CNIG, producto **BDLJE / Límites y Unidades Administrativas
Actuales**, colección OGC API Features `administrativeunit`:

```text
https://api-features.ign.es/collections/administrativeunit/items?f=json&limit=100&nationallevelname=Comunidad%20aut%C3%B3noma
```

Se reutiliza el snapshot local adquirido el 26-08-2026:

| Elemento | Valor |
|---|---|
| Raw | `data/raw/territories/spain/ign-ogc-2026-08-26/autonomous-territories.geojson` |
| Formato | GeoJSON `FeatureCollection` de OGC API Features |
| Tamaño | 156.859.995 B |
| SHA-256 | `48d1cd7b1cc2a3a98f6d02a0043fddc8db43ba28aaa8789d6b030243417bf757` |
| Metadato de release CNIG | SHP 28-07-2026; GML 10-08-2026 |
| CRS nativo BDLJE | ETRS89 geográfico en península, Baleares, Ceuta y Melilla; REGCAN95 geográfico en Canarias |
| Entrega OGC usada | GeoJSON CRS84 / longitudes-latitudes compatible con WGS84 |
| Licencia | CC BY 4.0 |
| Atribución | “Obra derivada de BDLJE CC-BY 4.0 ign.es” |

El catálogo del producto declara recintos municipales y líneas límite
municipales, provinciales y autonómicas. En el snapshot local se inspeccionaron
dos consultas de la misma colección: `nationallevelname=Comunidad autónoma`
(20 features) y `nationallevelname=Provincia` (53 features). Los atributos
observados son `nationalcode`, `nameunit`, `nationallevelname`, `country` y
códigos NUTS. La consulta de municipios no se adquiere ni se presupone en esta
fase: provincias y municipios quedan para ES-4C2A2 y posteriores.

## Crosswalk ES-2

El derivado usa únicamente features de `nationallevelname=Comunidad autónoma`.
`nationalcode` sigue el patrón BDLJE documentado `34` + código ES-2 de dos
posiciones + sufijo. Por tanto, por ejemplo, `34100000000` enlaza de forma
explícita con `ES:CCAA:10`; no se usa similitud de nombres.

Los 19 códigos `01`–`19` tienen correspondencia exacta en el snapshot ES-2
`territories-2026-01-01.json`. La tabla completa `source_code → territory_id →
nombre fuente → nombre canónico → tipo` queda versionada en
`data/sources/spain_ccaa_territories_manifest.json`.

La vigésima feature, `34200000000`, se denomina “Territorios no asociados a
ninguna autonomía”; no representa una CCAA/ciudad autónoma ES-2 y se excluye de
forma explícita. Ceuta (`ES:CCAA:18`) y Melilla (`ES:CCAA:19`) conservan
`territory_type=autonomous_city`; no se convierten conceptualmente en
provincias.

## Derivado web local

El builder reproducible es:

```bash
python3 scripts/territories/build_ccaa_prototype.py \
  --derived-at 2026-08-28T00:00:00Z
python3 scripts/territories/build_ccaa_prototype.py --check
```

Produce, fuera de Git:

```text
data/derived/spain/es4c2a/ccaa.geojson
```

Cada feature contiene exclusivamente `territory_id`, `source_code`,
`official_name`, `source_name`, `territory_type`, `bounds` y geometría. No
arrastra atributos de BDLJE ni relaciones de incendios.

| Propiedad | Resultado |
|---|---:|
| Territorios lógicos | 19 |
| Geometrías null | 0 |
| IDs únicos | 19 |
| Tamaño raw | 8.211.747 B |
| Tamaño gzip | 2.661.917 B |
| SHA-256 | `86fa15441605a0a95784fde45d1feffb302b6defc79b44665a64e02e5805535d` |
| Simplificación | 10 m, topológica, en EPSG:3857; salida EPSG:4326 |
| Reducción de vértices | 996.614 → 240.004 (75,9 %) |
| Error relativo de área | p95 0,02583 %; máximo 0,05452 % |

La prueba diagnóstica descartó 25 m: podía producir shells anidados en
Andalucía. Con 10 m se mantienen válidas todas las geometrías y se conserva el
número de partes de cada multipolígono, incluidas islas Canarias y Baleares.
La transformación de simplificación se declara explícitamente: CRS84/EPSG:4326
→ EPSG:3857 → simplificación topológica → EPSG:4326. No se mezclan los CRS
nativos ETRS89/REGCAN95 de forma silenciosa.

Los bounds se derivan de la geometría administrativa y son los únicos bounds
usados para `fitBounds`. El bounds nacional del derivado es
`[-18.1611787, 27.6377231, 4.3277840, 43.7923796]`.

## Runtime del prototipo

El controlador `territory_layer.mjs` añade límite base, highlight y capa de
clic. Selector y clic reutilizan el mismo `territory_id` oficial:

1. actualizan el estado central ES-4C;
2. resaltan el límite BDLJE;
3. hacen `fitBounds` administrativo con padding;
4. cargan o resumen EGIF mediante la política ya existente.

Al volver a España se retira el highlight, se encuadran los bounds nacionales y
EGIF vuelve al resumen de manifest sin cargar INITIAL nacional.

Una URL `es4c-state-v1` con CCAA solo resalta el límite. Conserva su
centro/zoom serializado y **no** aplica `fitBounds` durante la restauración.

ESFire30 sigue independiente: seleccionar una CCAA dibuja y encuadra el límite
oficial y filtra/carga EGIF administrativo, pero **no filtra ESFire30 por
CCAA**. El PMTiles no contiene aún una relación `geometry_id → territory`
validada; no se deduce desde incendios ni desde el cursor.

## Validación

Pasaron tres tests específicos: esquema/crosswalk/bounds, capa de clic y
`fitBounds`, y contrato explícito de no filtrar ESFire30 territorialmente.

Pasaron diez smokes Chromium dirigidos: España; País Valencià por clic; Galicia,
Andalucía, Canarias, Baleares, Ceuta y Melilla por selector; restauración C1C2
con País Valencià; y viewport móvil 390×844. Todos cargaron la capa oficial sin
errores. Canarias conservó el archipiélago aunque ESFire30 no ofreciese
geometrías visibles; Melilla se mantuvo como territorio válido incluso sin
asset INITIAL para ese rango.

No se ejecutaron benchmarks, no se reconstruyó PMTiles y no se generaron
relaciones ESFire30–CCAA.

## Límite y siguiente fase

ES-4C2A2 deberá adquirir/validar provincias con el mismo contrato de
territorios y sin convertir Ceuta/Melilla en provincias. La relación espacial
de ESFire30 con territorios es un trabajo distinto: necesitará un asset o
relación documentada N:M y no debe inferirse al implementar provincias.
