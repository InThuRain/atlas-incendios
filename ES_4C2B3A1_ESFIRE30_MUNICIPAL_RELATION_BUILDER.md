# ES-4C2B3A1 — Builder de relaciones ESFire30 ↔ municipio actual

## Alcance y contrato semántico

Este builder deriva `territory_relation` N:M entre la geometría canónica de
alta fidelidad de ESFire30 y los municipios actuales BDLJE del snapshot
2026-08. Una fila positiva significa exclusivamente:

> el perímetro ESFire30 intersecta con área positiva el límite municipal
> actual BDLJE.

No expresa municipio histórico, municipio administrativo EGIF, origen,
ignición, episodio ni pertenencia exclusiva. En particular,
`current_municipality_intersection != historical_municipality_containment`.
EGIF no participa en el cálculo.

Las relaciones siguen
`schemas/national/v1/atlas-contracts.schema.json#/territoryRelation`, con
`relation_type = spatial_intersection`, `mapping_status = confirmed` y
`qa_status = not_checkable`. Se conserva `geometry_id` exactamente como
`esfire30:v1:<year>:<source-feature-ordinal>`.

## Inputs cerrados

| Input | Identidad / checksum |
| --- | --- |
| ESFire30 canónico | Zenodo DOI `10.5281/zenodo.18449006`; `ESFire30_Causes.zip` SHA-256 `150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8` |
| Grid de transformación ES-3 | `es_ign_SPED2ETV2.tif`, SHA-256 `61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961` |
| Municipios BDLJE actuales | 8.213 features de fuente, 8.132 municipios canónicos; GeoJSON fuente SHA-256 `ca052a7592c45c03ea765e12e706652741964b80e8acd34e79978c31e9fe9dfc` |
| Catálogo municipal ES-2 | `data/territories/spain/municipality_catalog_2026-08-29.json`, SHA-256 `51174a29f166b194fa9d95e9b3bfc91521b0a189d193fe3a49efde58d35377c8` |
| Shards municipales | C2A3B, geometría BDLJE actual sin simplificación (0 m); 81 unidades `53xxx` no municipales excluidas |
| Prefiltro provincial | Relaciones C2B1A completas, 119.498 geometrías, SHA-256 del manifest registrado en el manifest de salida |

El builder verifica el catálogo, la auditoría C2A3B y el manifest C2B1A antes
de procesar. Cada bloque además verifica el checksum del JSONL provincial que
utiliza como prefiltro.

## Método reproducible

1. Lee una geometría ESFire30 canónica, conserva su ordinal y la transforma
   EPSG:23030 → EPSG:4326 mediante la operación ES-3 documentada.
2. La transforma a EPSG:3035; los municipios BDLJE CRS84/EPSG:4326 se
   transforman igualmente a EPSG:3035. Todas las áreas se calculan allí.
3. Reutiliza **todas** las provincias positivas C2B1A de esa geometría como
   prefiltro seguro. No selecciona una provincia principal.
4. Carga solo los shards municipales de esas provincias y consulta su índice
   `STRtree`; realiza después la intersección exacta con cada candidato.
5. Emite una relación solo con `intersection_area_m2 > 0`; un contacto con
   área cero va al JSONL `boundary-touches` y nunca se promociona.

No hay umbral de fracción: todos los slivers de área positiva se preservan.
Cada relación incluye área, fracción del perímetro y fracción del municipio,
además de sus padres canónicos. Se comprueba que el padre provincial y el
padre CCAA ya estén entre las relaciones C2B1A de la misma geometría.

La partición es por año ESFire30 (1985–2021), atómica, determinista y
reanudable. Los `geometry_id`, las provincias y las filas se recorren en orden
determinista. La cardinalidad municipal es deliberadamente abierta: no existe
ningún campo `mun_N`.

## Salida local ignorada

Por defecto:

`data/derived/spain/es4c2b/esfire30_municipality_relations/`

- `relations-YYYY.jsonl`: relaciones de área positiva;
- `boundary-touches-YYYY.jsonl`: auditoría de contactos de área cero;
- `manifest.json`: inputs, política, checksums, CRS, estado, recuentos,
  candidatos, tiempo y RSS máximo de proceso diagnóstico.

No se duplican geometrías. El manifest nacional final deberá reconciliar
119.498 geometrías y 8.132 municipios canónicos, informar relaciones,
geometrías sin municipio, contactos, máximo de municipios y checksum de cada
bloque.

## Ejecución nacional externa y corrección de precisión

La adquisición nacional fue ejecutada externamente, por año, y reconciliada:

| Métrica | Resultado |
| --- | ---: |
| bloques completos | 37 / 37 |
| geometrías ESFire30 | 119.498 |
| relaciones municipales positivas | 143.477 |
| geometrías sin relación municipal | 83 |
| contactos de borde | 0 |
| máximo de municipios por geometría | 19 |
| JSONL de salida | 125.199.288 B |

La primera comprobación detectó en `relations-1990.jsonl` una falsa anomalía
de validación: la relación positiva `esfire30:v1:1990:1901` →
`ES:MUN:39074` tenía una fracción de `2.7e-11`, pero
`intersection_area_m2` se había redondeado a `0.0` al serializar. No era un
duplicado ni un touch. El builder conserva ahora las áreas y fracciones como
`float` sin redondeo de transporte; se regeneró **solo** el bloque 1990. El
`--check --all` posterior es válido, no queda ninguna relación positiva con
área serializada no positiva y los totales nacionales permanecen conciliados.

Los 83 casos sin municipio son resultado de la política sin nearest fallback;
su clasificación y la cardinalidad/inversa municipal quedan expresamente para
la auditoría ES-4C2B3A2, no para esta fase de builder.

## Muestras ejecutadas

La muestra local `/tmp/es4c2b3a1-sample/` procesó diez geometrías repartidas
en siete años. No es output nacional ni se versiona.

| Control | `geometry_id` | municipios | Observación |
| --- | --- | ---: | --- |
| Andalucía | `esfire30:v1:1985:0` | 1 | Provincia 11 / CCAA 01 |
| Multi-CCAA | `esfire30:v1:1985:1037` | 3 | Provincias 09 y 26; CCAA 07 y 17 |
| Galicia / Ourense | `esfire30:v1:1985:2938` | 1 | Provincia 32 / CCAA 12 |
| Gran perímetro | `esfire30:v1:1994:2841` | 13 | Provincia 46; sliver mínimo observado `0.000094635744` |
| Burgos | `esfire30:v1:2002:105` | 1 | Provincia 09; el procedimiento trata Treviño/La Puebla por su geometría real, sin regla de nombres |
| Cataluña / Girona | `esfire30:v1:2002:1515` | 1 | Provincia 17 / CCAA 09; misma vía geométrica para Llívia, sin excepción por enclave |
| Gran multi-provincia | `esfire30:v1:2004:2622` | 12 | Provincias 21 y 41 |
| País Valencià multi-provincia | `esfire30:v1:2011:88` | 2 | Alacant (03) y València (46) |
| Gran perímetro | `esfire30:v1:2012:24` | 12 | Provincia 46 |
| Gran perímetro | `esfire30:v1:2021:1311` | 14 | Provincia 05; máximo de la muestra |

Resultado agregado: 10 geometrías, 60 relaciones, 0 `boundary_touch`, 0
geometrías sin relación y 0 inconsistencias jerárquicas. El prefiltro presentó
2.647 municipios candidatos (suma de todas las provincias C2B1A aplicables),
que el índice espacial redujo a 60 candidatos de intersección exacta. La
muestra confirma N:M, multi-provincia y multi-CCAA, pero no pretende estimar
la cardinalidad nacional final.

Canarias no se muestrea porque **ESFire30 no tiene cobertura allí**. La
ausencia no significa ausencia de incendios. El tratamiento geométrico de
Llívia, Treviño, La Puebla de Arganzón y Rincón de Ademuz es puramente espacial
cuando una geometría los alcanza; no hay excepciones por nombre ni nearest
municipality.

La ejecución de muestra fue de unos 5 s en la máquina local, con un pico RSS
de proceso de 148.078.592 B. Este tiempo incluye lectura secuencial de años del
ZIP y no se extrapola linealmente. El build nacional recorrerá 37 años, leerá
las relaciones C2B1A locales y escribirá JSONL; debe ejecutarse externamente y
su tamaño/tiempo finales se medirán, no se infieren de nueve controles sesgados
hacia perímetros grandes.

## Validación y comandos externos

Tests específicos:

```bash
python3 -m unittest tests.test_es4c2b3a1_esfire30_municipality_relations
```

Construcción nacional (externa; no ejecutada por Codex):

```bash
python3 scripts/relations/esfire30/municipalities.py --resume --all
```

Comprobación posterior:

```bash
python3 scripts/relations/esfire30/municipalities.py --check --all
```

La ejecución nacional ya queda disponible para auditoría. ES-4C2B3A2 deberá
analizar cardinalidades, los 83 ceros, slivers e índices inversos antes de
escoger un mecanismo de runtime municipal; este builder no altera runtime,
PMTiles ni el mensaje actual de filtro municipal pendiente.
