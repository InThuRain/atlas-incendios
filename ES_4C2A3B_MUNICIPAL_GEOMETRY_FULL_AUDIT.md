# ES-4C2A3B — Auditoría completa de geometría municipal actual

## Alcance

Se audita exclusivamente el GeoJSON BDLJE municipal nacional adquirido de
forma externa. Esta fase crea shards administrativos actuales sin
simplificación y un catálogo con bounds. No integra runtime municipal, no
modifica EGIF, no calcula relaciones ESFire30→municipio y no publica assets.

## Snapshot cerrado

- Fuente: IGN/CNIG, BDLJE — Límites y Unidades Administrativas Actuales.
- Input: `data/raw/territories/spain/ign-ogc-2026-08-26/municipalities/municipality-level.geojson`.
- Formato/CRS web: GeoJSON CRS84 / EPSG:4326-compatible.
- Tamaño: **147.400.597 B**.
- SHA-256: `ca052a7592c45c03ea765e12e706652741964b80e8acd34e79978c31e9fe9dfc`.
- Licencia/atribución: CC-BY 4.0; «Obra derivada de BDLJE CC-BY 4.0 ign.es».

No se volvió a descargar ni a consultar la OGC API.

## Reconciliación ES-2

| Concepto | Resultado |
| --- | ---: |
| Features BDLJE | 8.213 |
| `MATCHED_CURRENT` | 8.132 |
| `NON_MUNICIPAL_UNIT` (53xxx) | 81 |
| `UNMATCHED_SOURCE` / `AMBIGUOUS` | 0 / 0 |
| Municipios duplicados entre shards | 0 |
| Discrepancias municipio → provincia → CCAA | 0 |

Las 81 unidades se conservan como provenance de fuente, fuera del catálogo y
de los shards canónicos. La agrupación por prefijo literal —no taxonomía
oficial nueva— cuenta 42 `Comunidad`, 6 `Facería`, 4 `Ledanía`, 4
`Mancomunidad`, 3 `Monte`, 2 variantes `Parzonería/Parzoneria` y 20 otros.

## Geometría de los 8.132 municipios canónicos

BDLJE entrega ya las 8.132 features canónicas como `MultiPolygon`: hay 8.132
MultiPolygon y 0 Polygon, null, empty o inválidas. El derivado 0 m conserva
directamente `feature["geometry"]`; no normaliza Polygon → MultiPolygon. Cada
MultiPolygon se conserva como una sola feature lógica aunque tenga varias
partes. El total es **4.434.537
vértices**; por municipio: mínimo 9, mediana 249, p95 1.906 y máximo 18.225
(Cartagena).

Se preservan los casos dirigidos: Llívia, Condado de Treviño, La Puebla de
Arganzón, Ademuz/Rincón de Ademuz y Llocnou de la Corona. Canarias y Baleares
mantienen sus multipartes e islas. Ceuta y Melilla generan respectivamente
`ES-CCAA-18.geojson` y `ES-CCAA-19.geojson`: son assets de ciudades autónomas,
no provincias ficticias.

## Shards 0 m y catálogo

Se generaron 52 assets locales: 50 por provincia y 2 por ciudad autónoma. Cada
feature conserva solamente `municipality_id`, `province_id` (null en Ceuta y
Melilla), `autonomous_community_id`, `official_name` y geometría fuente 0 m.

| Derivado | Raw | Gzip |
| --- | ---: | ---: |
| Source BDLJE nacional | 147.400.597 B | no medido separadamente |
| GeoJSON nacional canónico hipotético 0 m | 146.192.799 B | 46.636.931 B |
| 52 shards provincia/ciudad 0 m | 146.194.941 B | 46.664.000 B |
| Catálogo nacional con bounds exactos | 1.984.280 B | 327.282 B |

La selección de atributos reduce solo 1.205.656 B raw frente al source:
la geometría domina el tamaño. La suma de shards conserva toda la geometría
canónica; su pequeño sobrecoste gzip frente al GeoJSON único procede de la
compresión independiente por asset.

El catálogo, versionable y sin geometría, contiene 8.132 filas con
`municipality_id`, `province_id`, `autonomous_community_id`, `official_name`,
`bounds` exactos 0 m y `asset_id`: 244,01 B raw y 40,25 B gzip por municipio.
Los bounds describen exclusivamente el límite BDLJE actual y son aptos para un
futuro `fitBounds` administrativo.

## Tamaños relevantes

| Asset 0 m | Municipios | Raw | Gzip |
| --- | ---: | ---: | ---: |
| Alacant | 141 | 2.454.561 B | 759.493 B |
| Castelló | 135 | 1.801.679 B | 575.509 B |
| València | 266 | 3.022.353 B | 932.366 B |
| A Coruña | 93 | 4.506.045 B | 1.433.846 B |
| Ourense | 92 | 983.027 B | 324.138 B |
| Sevilla | 106 | 2.397.891 B | 795.718 B |
| Burgos | 371 | 2.199.840 B | 715.232 B |
| Girona | 221 | 9.034.136 B | 2.853.565 B |
| Illes Balears | 67 | 3.700.318 B | 1.194.764 B |
| Las Palmas | 34 | 6.011.735 B | 1.752.114 B |
| Santa Cruz de Tenerife | 54 | 4.580.711 B | 1.312.686 B |

La provincia más pesada es Barcelona: 311 municipios, 325.017 vértices,
10.490.788 B raw y **3.334.456 B gzip**. Los diez mayores por raw, gzip y
vértices coinciden: Barcelona, Girona, Lleida, Tarragona, Las Palmas, Madrid,
Cáceres, A Coruña/Santa Cruz de Tenerife (según métrica) e Illes Balears o
Murcia. El agregado reproducible contiene los cuatro rankings completos.

## Comparación de entrega

- **GeoJSON nacional único:** 46,64 MB gzip; no recomendado como carga
  inicial.
- **GeoJSON por CCAA:** conserva la geometría, pero Castilla y León alcanza
  33.506.211 B raw / 10.690.626 B gzip; marginal para una entrada normal.
- **GeoJSON 0 m por provincia:** máximo 3,33 MB gzip y descargado solo después
  de seleccionar provincia; **RECOMMENDED** para la futura navegación actual.
- **PMTiles administrativo:** no medido ni construido. Sigue siendo candidato
  solo si se exige navegación municipal continua a escala de España.

Por tanto se mantiene geometría **0 m**. No existe una medida que justifique
la simplificación nacional 5/10 m; en particular Llocnou de la Corona conserva
la evidencia ES-4C2A3A de 2,2117 % de error de área. La fidelidad se compra con
particionado, no con simplificación global.

## Semántica y siguientes límites

La geometría BDLJE representa un municipio administrativo actual.
`current_municipality_geometry != historical_municipality_geometry`. Un futuro
filtro EGIF por `municipality_id` contará partes enlazados documentalmente al
municipio canónico actual; no afirmará que un evento histórico ocurrió dentro
del polígono actual. Los 71.490 EGIF con municipio null permanecen sin cambio.

No hay relaciones ESFire30→municipio. Su cardinalidad puede superar tres, por
lo que no se usarán slots `mun_1..mun_3`; una fase separada deberá evaluar
índice inverso, teselas locales o consulta espacial sobre geometrías cargadas.

## Validación y outputs

- Script reproducible: `scripts/territories/audit_municipality_geometry_full.py`.
- Agregado: `data/audit/territories/es4c2a3b_municipal_geometry_full_audit.json`.
- Catálogo: `data/territories/spain/municipality_catalog_2026-08-29.json`.
- Shards locales ignorados: `data/derived/spain/es4c2a3/municipalities/`.
- Check: `python3 scripts/territories/audit_municipality_geometry_full.py --check`.

La siguiente fase recomendada es `ES-4C2A3C_MUNICIPAL_RUNTIME_FOUNDATION`:
integrar catálogo y carga provincial bajo demanda en el prototipo, conservando
las advertencias históricas y sin calcular aún relaciones ESFire30→municipio.
