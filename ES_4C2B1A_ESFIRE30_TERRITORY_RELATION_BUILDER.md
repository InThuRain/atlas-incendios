# ES-4C2B1A — Generador de relaciones territoriales ESFire30

## Alcance y contrato semántico

Esta subfase prepara, pero no ejecuta nacionalmente, un generador reanudable de relaciones espaciales N:M entre geometrías canónicas ESFire30 y territorios administrativos oficiales ES-2.

Una fila significa únicamente:

> La geometría ESFire30 indicada intersecta con área positiva este territorio administrativo BDLJE.

No afirma adscripción administrativa del incendio, origen/ignición, identidad física de episodio ni relación alguna con un `source_record` EGIF. No se crean, recortan, simplifican ni copian geometrías. La salida sigue el contrato `territory_relation` de [`schemas/national/v1/atlas-contracts.schema.json`](schemas/national/v1/atlas-contracts.schema.json): `subject_id = geometry_id`, `relation_type = spatial_intersection`, `mapping_status = confirmed` y `qa_status = not_checkable`.

## Entradas reproducibles

- ESFire30 v1, DOI `10.5281/zenodo.18449006`, geometrías originales del ZIP `data/raw/esfire30/18449006/ESFire30_Causes.zip`, SHA-256 `150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8`. Son 119.498 geometrías de 1985–2021 y sus IDs estables son `esfire30:v1:<año>:<ordinal-fuente>`.
- Transformación ya validada en ES-3: EPSG:23030 → operación PROJ **ED50 to WGS 84 (41)** (grid `es_ign_SPED2ETV2.tif`, SHA-256 `61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961`) → EPSG:4326 → EPSG:3035.
- CCAA/ciudades autónomas BDLJE/IGN-CNIG: `autonomous-territories.geojson`, SHA-256 `48d1cd7b1cc2a3a98f6d02a0043fddc8db43ba28aaa8789d6b030243417bf757`.
- Provincias BDLJE/IGN-CNIG: `province-level.geojson`, SHA-256 `58e4f68f4efc324dd9dfd0c1df0ea755846e3b717676b7137456577dc2083290`.
- Snapshot y crosswalk ES-2, junto con los manifests C2A1/C2A2, verifican que los códigos BDLJE se traducen por código a `ES:CCAA:<NN>` y `ES:PROV:<NN>`.

El cálculo de área e intersección ocurre en **EPSG:3035**; no se calculan hectáreas en EPSG:4326. Se usa un índice `STRtree` para candidatos espaciales. Ceuta y Melilla conservan su tipo canónico de ciudades autónomas; las representaciones BDLJE de nivel provincial 51/52 no crean provincias canónicas. ESFire30 no cubre Canarias: una ausencia de relación canaria será ausencia de cobertura de fuente, no cero incendios.

## Política de intersección

- `positive_area_intersection`: `intersection_area_m2 > 0`; se emite una relación N:M.
- `boundary_touch_only`: área exactamente cero; se conserva en un JSONL diagnóstico separado y **no** se emite como `territory_relation`.
- No hay umbral que descarte slivers: toda intersección positiva conserva `intersection_area_m2` e `intersection_fraction` para su auditoría posterior.
- Cada relación provincial exige y verifica la presencia de la relación positiva de su `parent_id` CCAA. Las incoherencias se contabilizan en manifest, nunca se corrigen ni se suprimen.

Las geometrías transfronterizas preservan todas sus relaciones; el generador no elige una provincia/CCAA principal por centroide, área máxima, municipio o punto de ignición.

## Salida local ignorada

El destino por defecto es `data/derived/spain/es4c2b/esfire30_territory_relations/`, ignorado por Git. Para cada año produce de forma atómica:

- `relations-<año>.jsonl`: relaciones con área positiva.
- `boundary-touches-<año>.jsonl`: contactos de borde, exclusivamente diagnósticos.
- `manifest.json`: versión, entrada y checksums, CRS/operación, política, bloques, recuentos, hashes y bytes.

Cada fila positiva incluye `territory_relation_id` determinista, `geometry_id`, `subject_id`, `territory_id`, `territory_type`, `territory_level`, `relation_type`, estado del contrato, área/fracción y procedencia mínima. El manifest concentra los checksums, URLs y operación detallada para no repetirlos innecesariamente en cada relación N:M.

`--resume` reutiliza solo un bloque `complete` cuyo checksum y número de geometrías coinciden; una muestra parcial no puede hacerse pasar por un año nacional. `--check` verifica checksums, recuentos, clases, unicidad `(geometry_id, territory_id, relation_type)` y la reconciliación de 119.498 geometrías cuando se ejecuta `--all`.

## Muestras ejecutadas

No se ejecutó el cruce nacional. Se procesaron siete geometrías dirigidas, con 19 relaciones positivas, cero contactos de borde y cero incoherencias jerárquicas:

| Caso | `geometry_id` | Relaciones positivas observadas |
| --- | --- | --- |
| Interior valenciano | `esfire30:v1:2011:77` | CCAA 10 + provincia 46; fracción 1 |
| CV / Castilla-La Mancha; multi-CCAA | `esfire30:v1:2014:930` | CCAA 10 (0,620213) + 08 (0,379787); provincias 46 + 02 |
| CV / Aragón | `esfire30:v1:2019:421` | CCAA 10 (0,918754) + 02 (0,081246); provincias 12 + 44 |
| Galicia | `esfire30:v1:1985:2938` | CCAA 12 + provincia 32; fracción 1 |
| Andalucía | `esfire30:v1:1985:0` | CCAA 01 + provincia 11; fracción 1 |
| Costa/Baleares | `esfire30:v1:2000:3321` | CCAA 10 + provincia 12 (0,999998); ninguna relación espuria con Baleares |
| Multi-provincia | `esfire30:v1:2011:88` | CCAA 10; provincias 03 (0,984625) + 46 (0,015375) |

Los candidatos multi-CCAA/provincia fueron localizados solo para seleccionar la muestra mediante los diagnósticos ES-3; el cálculo de esta subfase los deriva de la geometría cruda ESFire30 y BDLJE oficiales. La corrida nacional deberá reconciliar 119.498 geometrías y contrastar sus recuentos multi-CCAA/multi-provincia con la referencia ES-3 (1.342 y 2.364, respectivamente). Puede haber diferencias de borde/sliver explicables porque ES-3 usó su partición diagnóstica y C2B conserva toda intersección positiva sobre BDLJE sin umbral; cualquier diferencia deberá quedar cuantificada, no asumida.

## Ejecución nacional externa

No ejecutar con Codex:

```bash
python3 scripts/relations/esfire30/territories.py --resume --all
python3 scripts/relations/esfire30/territories.py --check --all
```

El primer comando es reanudable por año y deja checkpoint de cada bloque correcto en el manifest. ES-3 procesó las 119.498 geometrías en 876,799 s en su propio pipeline; esta tarea añade intersecciones completas y métricas de área, por lo que esa cifra solo es una referencia inferior histórica, no una estimación garantizada. El espacio final depende de la cardinalidad N:M y debe informarse desde el manifest, no extrapolarse a partir de siete muestras.

Tras ejecutarlo, compartir el JSON final del builder y de `--check`, además de `manifest.json` o sus totales: bloques completos, geometrías, relaciones positivas, contactos de borde, multi-CCAA, multi-provincia, cero-relación, incoherencias jerárquicas, bytes y SHA-256 de salida. ES-4C2B1B auditará esos resultados antes de modificar PMTiles o el runtime.
