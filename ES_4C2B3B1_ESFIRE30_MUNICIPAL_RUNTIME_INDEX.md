# ES-4C2B3B1 — Prueba runtime del índice municipal ESFire30

## Alcance y semántica

Esta fase prueba exclusivamente, dentro de `prototypes/es4c/`, el filtrado cartográfico municipal de ESFire30. No recalcula intersecciones, no modifica el PMTiles, no cambia EGIF ni toca producción.

Una lista municipal significa: **perímetros ESFire30 (1985–2021) que intersectan con área positiva el límite municipal BDLJE actual (snapshot 2026)**. No designa municipio EGIF, municipio histórico, origen, ignición ni territorio principal. EGIF conserva en paralelo su filtro administrativo documental por `municipality_id`.

Las 83 geometrías ESFire30 sin relación con los 8.132 municipios canónicos actuales se explican en ES-4C2B3A2 por unidades BDLJE no municipales 53xxx. No entran en ninguna lista municipal; permanecen en España, CCAA y provincia. `83 geometrías sin municipio != 83 incendios sin localizar`.

## Input y entrega experimental

`scripts/build/esfire30/municipality_runtime_index.py` sólo serializa los JSONL positive-area cerrados en ES-4C2B3A2. No abre geometrías ESFire30 o municipales ni ejecuta joins espaciales.

```text
python3 scripts/build/esfire30/municipality_runtime_index.py --resume
python3 scripts/build/esfire30/municipality_runtime_index.py --check
```

El manifest local e ignorado queda en `data/derived/spain/es4c2b/runtime/municipality-index/manifest.json`. Reconcilia 119.498 `geometry_id`, 143.477 relaciones, 6.166 municipios con lista y 1.966 municipios de lista vacía implícita; el máximo es Cangas del Narcea, con 2.610 IDs.

El índice nacional auditado ES-4C2B3A2 incluía las 1.966 claves vacías y medía 3.537.410 B raw / 430.182 B gzip. El runtime omite esas claves y las interpreta como `[]`: 3.502.136 B raw / 423.526 B gzip. No se pierde ninguna relación. Por la misma razón materializa 47 shards padre no vacíos, no 50: Illes Balears, Las Palmas y Santa Cruz de Tenerife no tienen entradas y están fuera de cobertura ESFire30.

Los 47 shards suman 3.507.708 B raw / 434.620 B gzip. Ejemplos: Alacant 17.129 B raw / 2.316 B gzip; Asturias 371.007 B / 42.658 B; Ourense 457.524 B / 53.867 B. El servidor local de smoke no comprime HTTP: las mediciones de red del índice son raw; gzip es una referencia de manifest.

## Estrategias comparadas

| Estrategia | Carga fría | Caché | Clasificación |
| --- | --- | --- | --- |
| Nacional | manifest + 3.502.136 B raw (423.526 B gzip) | una carga para todo el país | VIABLE |
| Shard padre provincial | manifest + shard del padre | reutilizable entre municipios de la misma provincia | RECOMMENDED |

El nacional de Cangas tardó 10,4 ms en parsearse, frente a 1,8 ms para Asturias. Ambos aplicaron la misma expresión de 2.610 IDs sin error. El shard evita transferir y retener el índice nacional para una navegación provincial ya existente. Cangas → Allande reutilizó Asturias sin refetch; Cangas → Ourense solicitó sólo Ourense.

## Filtro MapLibre y estado

`prototypes/es4c/municipality_esfire_index.mjs` mantiene la caché por asset. Sólo para `territory_scope = municipality`, `app.js` compone:

```js
["all", yearFilter(), ["in", ["get", "geometry_id"], ["literal", geometryIds]]]
```

No combina simultáneamente una lista provincial/CCAA masiva. Al volver a provincia, CCAA o España retorna a `prov_1..3`, `ccaa_1..3` o sin filtro territorial. Las listas tienen orden determinista y no expresan una pertenencia primaria; todos los slivers positive-area se conservan.

Si una selección ESFire30 deja de estar en la nueva lista se limpia sólo `selected_geometry_id`; EGIF sigue independiente. Restore recupera un `geometry_id` exclusivamente cuando figura en la lista municipal y es compatible con fuente y año, sin cambiar el municipio guardado.

Un municipio continental con lista vacía (Agost, `ES:MUN:03002`) muestra “Sin perímetros ESFire30 que intersecten este municipio para la cobertura disponible”; no se confunde con ausencia de cobertura. Baleares, Canarias, Ceuta y Melilla mantienen la indicación “sin cobertura ESFire30”.

## Smokes dirigidos

Se ejecutaron 17 smokes Chromium locales y su `--check`: Elx, Barcelona, Ourense, Treviño, Cangas, Allande, Viana do Bolo, Agost sin relación, multi-municipio, rango anual, caché, cambio provincial, invalidación, restore y Cangas 390×844. Todos terminaron sin errores. El output local ignorado es `prototypes/es4c/c2b3b1-smoke-results.json`.

| Caso | IDs auditados | Expresión | setFilter | filtro→idle | features renderizadas* |
| --- | ---: | ---: | ---: | ---: | ---: |
| Elx | 6 | 180 B | 0,4 ms | 567,1 ms | 6 |
| Barcelona | 20 | 514 B | 0,4 ms | 378,5 ms | 20 |
| Ourense | 152 | 3.673 B | 0,7 ms | 510,3 ms | 165 |
| Treviño | 73 | 1.782 B | 0,4 ms | 410,0 ms | 75 |
| Cangas, shard Asturias | 2.610 | 62.294 B | 0,8 ms | 338,0 ms | 6.074 |
| Cangas, nacional | 2.610 | 62.294 B | 0,7 ms | 538,2 ms | 6.074 |
| Allande | 1.306 | 31.180 B | 0,6 ms | 306,0 ms | 5.551 |
| Viana do Bolo | 1.178 | 27.762 B | 0,7 ms | 534,6 ms | 1.243 |

\* Son features cargadas/renderizadas en el viewport/zoom del smoke, no el total de `geometry_id` relacionados y no una reconciliación territorial.

Los tiempos filtro→idle incluyen tiles del viewport local y son una sola observación, no percentiles. Cangas no reproduce el fallo del filtro externo Galicia (38.645 IDs): la lista de 2.610 funciona en escritorio y en viewport móvil sin hang o crash. Esto no fija un umbral universal.

Los PMTiles continúan con HTTP 206 y sin descarga completa. Cangas/shard observó 3.048.053 B Range y heap diagnóstico ~97,2 MB; Cangas/nacional tuvo el mismo Range y ~97,9 MB. Viewport, teselas y caché afectan estas cifras. Los 385.697 B parent y 3.516.826 B nacionales servidos localmente incluyen manifest + JSON raw, no transferencias CDN gzip.

La control multi-municipio `esfire30:v1:2011:88` aparece en `ES:MUN:03084` y `ES:MUN:46255`, sin municipio principal. El control 1993 de Elx confirma lista municipal **AND** año. Restore de `esfire30:v1:1993:777` en Elx recupera ámbito, año, límite y selección compatible. Cangas → Allande limpia la selección incompatible antes de la selección posterior del smoke.

## Decisión

**Índice nacional: VIABLE.** Es correcto y pequeño en gzip, útil para inspección o sesiones que ya requieran todo el país, pero añade ~3,5 MB raw y parsea más que lo necesario para una selección municipal.

**Índice por padre provincial: RECOMMENDED.** Sigue la navegación existente, limita transferencia, reutiliza caché dentro de provincia y supera Cangas en escritorio y 390×844. Es el default del prototipo experimental.

Siguiente fase recomendada: `ES-4C3_NATIONAL_PROTOTYPE_CONSOLIDATION`. No hacen falta PMTiles municipales, conversión de IDs a enteros ni rediseño antes de consolidar; la limitación pendiente es histórica/semántica, no un cuello de botella medido.
