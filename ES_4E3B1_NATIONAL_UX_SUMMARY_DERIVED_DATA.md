# ES-4E3B1 — `national-ux-summary-v1`

## Resultado

`UX_SUMMARY_STATUS = PASS` y `HISTOGRAM_DATA_STATUS = READY_FOR_UI`.

Se ha construido un resumen anual, territorial, tipado y separado por fuente
sin modificar la UI nacional, el runtime técnico, el artifact D4B ni ningún
dataset de origen. El builder usa exclusivamente derivados aceptados: columnas
INITIAL EGIF, registros ICV, los dos GeoJSON EFFIS y las relaciones
positive-area ESFire30 ya calculadas. No abre geometrías ni PMTiles.

Los totales reconciliados son:

- EGIF: 646.887 partes administrativos;
- ESFire30: 119.498 `geometry_id`;
- ICV: 13.738 registros y 13.739 geometrías;
- EFFIS: 9 perímetros en 2025 y 16 en 2026.

No existe ninguna métrica conjunta ni se deduplican entidades entre fuentes.

## Contratos e inputs

Mandaron los contratos E2:

- `ES_4E2_NATIONAL_UX_REDESIGN_SPEC.md`;
- `data/audit/product/es4e2_metric_contracts.json`;
- `data/audit/product/es4e2_data_requirements.json`.

Inputs de datos:

| Fuente | Input aceptado | Uso |
| --- | --- | --- |
| EGIF | manifest 2026-08-27 y 88 INITIAL columnares | año, CCAA, provincia, municipio, superficie forestal nullable y GIF |
| ESFire30 | 37 JSONL territoriales y 37 municipales | conteo anual de `geometry_id` por intersección positive-area |
| ICV | `fires.json` publicado | `fire_id`, `geometry_ids`, año, territorio, superficie declarada |
| EFFIS | snapshot `20260819T174426Z`, 2025/2026 | `geometry_id`, año, territorio y `mapped_area_ha` |
| ES-2 | snapshot territorial 2026-01-01 y catálogo municipal | identidad, jerarquía y shards |

El manifest de salida inventaría y fija por SHA-256 los 175 inputs efectivos,
incluidos todos los INITIAL y JSONL que se agregaron. `--check` detecta cambios
en esos inputs además de validar los outputs.

## Schema

La versión es `national-ux-summary-v1`; su schema está en
`schemas/national/v1/national-ux-summary.schema.json`.

Cada territorio contiene `source_summaries` independientes. Cada summary
declara:

- `source_id` y `entity_type`;
- cobertura propia y estado `available` o `no_source_coverage`;
- eje anual denso dentro de la cobertura;
- métricas con `metric_id`, unidad y valores;
- conteos known/unknown cuando existe una magnitud nullable.

Los índices de `values` se interpretan mediante `year_axis.from/to`. No se
crean posiciones fuera de cobertura. Un cero significa cobertura y valor
medido cero; `null` significa que existen registros cubiertos pero la magnitud
es desconocida. En el snapshot actual todas las superficies EGIF, ICV y EFFIS
agregadas resultaron conocidas, pero el contrato y el builder conservan la
diferencia y tienen una prueba específica para `null != 0`.

## Métricas

### EGIF

- `egif_record_count`;
- `egif_declared_forest_area_ha`, con `known_value_count` y
  `unknown_value_count`;
- `egif_administrative_gif_count`, con conteos false/unknown;
- `quality_counts.municipality_unresolved`, como calidad del enlace y no como
  métrica de producto independiente.

España suma 646.887 partes, 8.230.839,0949 ha forestales declaradas conocidas y
2.192 partes GIF. Los 71.490 partes sin municipio canónico permanecen en
España/CCAA/provincia cuando esos niveles están documentados y no se asignan a
ningún municipio.

### ESFire30

- `esfire30_perimeter_count`.

España cuenta cada `geometry_id` una vez por año. En CCAA, provincia y
municipio cuenta una vez dentro de cada territorio con el que existe relación
positive-area. Una geometría multi-territorio figura en cada territorio; eso no
la convierte en varios incendios. Se preservan todos los slivers aceptados y
las 83 geometrías sin municipio siguen presentes en niveles superiores.

`esfire30_mapped_area_ha = DEFERRED`. Las relaciones no proporcionan una suma
territorial libre de solapes y sumar el área completa de un perímetro que solo
intersecta parcialmente un territorio violaría E2.

### ICV

- `icv_fire_record_count`;
- `icv_perimeter_count`;
- `icv_declared_forest_area_ha`, con known/unknown;
- `icv_gif_count` según el criterio ICV aprobado de 500 ha forestales
  declaradas, sin usar área geométrica.

Solo se entrega para GVA y sus provincias/municipios documentados. El control
`2024AL0005` aporta exactamente un registro y dos geometrías. El total conserva
13.738/13.739; no se fuerza una relación 1:1.

### EFFIS

- `effis_perimeter_count`;
- `effis_mapped_area_ha`, con known/unknown.

Solo se entrega para GVA y sus provincias/municipios documentados. Mantiene la
semántica de perímetro satelital provisional y el snapshot fechado; 2026 sigue
siendo parcial, no un cierre anual.

### Métricas aplazadas

- área cartografiada ESFire30: falta derivado territorial seguro;
- causas EGIF: bloqueadas por la ontología nacional MITECO;
- destacados/top-N: corresponden a E3C, no al histograma P0;
- distribuciones de causas ICV: disponibles en la fuente, pero no necesarias
  para E3B1/E3B2 P0.

## Cobertura

El rango global potencial es 1968–2026, pero cada serie conserva el suyo:

| Fuente | Cobertura del summary |
| --- | --- |
| EGIF | 1968–2023 |
| ESFire30 | 1985–2021 |
| ICV | 1993–2024, solo GVA |
| EFFIS | 2025–2026, solo GVA, snapshot parcial |

Illes Balears, Canarias, Ceuta y Melilla declaran para ESFire30
`no_source_coverage` y no reciben una serie de ceros. En cambio Agost declara
`available` y su serie ESFire30 suma cero: es un cero cubierto, no ausencia de
cobertura.

## Layout y política de carga E3B2

La salida contiene 122 payloads y un manifest:

- `national.json` para España;
- 19 assets `ccaa/ES-CCAA-xx.json`;
- 50 assets `provinces/ES-PROV-xx.json`;
- 52 shards `municipalities/by-parent/*.json`, uno por provincia o ciudad
  autónoma padre.

Política propuesta:

- España: `national.json`;
- CCAA/ciudad autónoma: un asset CCAA;
- provincia: un asset provincial;
- municipio: el shard de su padre ya conocido.

Así el navegador no recorre 646.887 EGIF, 119.498 ESFire30 ni solicita un
archivo por municipio. El manifest decide rutas y checksums; E3B2 no debe
adivinar filenames.

## Tamaño

| Medida | Resultado |
| --- | ---: |
| Payload files | 122 |
| Ficheros físicos, incluido manifest | 123 |
| Payload raw | 17.175.032 B |
| Payload gzip | 911.539 B |
| Total físico raw | 17.255.181 B |
| Total físico gzip | 930.003 B |
| Fingerprint de payload | `2546247b68ef8e27fed3334cf5fb4a027056f094e36420213080c431bfb850e4` |

La contabilidad lógica de fragmentos por fuente —no sumable al gzip físico,
porque cada fragmento se comprime por separado— es:

| Fuente | Summaries territoriales | Raw fragmentos | Gzip fragmentos |
| --- | ---: | ---: | ---: |
| EGIF | 8.202 | 12.216.799 B | 2.969.675 B |
| ESFire30 | 8.202 | 2.804.642 B | 1.636.408 B |
| ICV | 546 | 610.075 B | 178.577 B |
| EFFIS | 546 | 234.814 B | 136.100 B |

El gzip físico es mucho menor porque los shards comprimen conjuntamente
territorios y series repetitivas. El derivado es razonable para incorporarlo en
un artifact futuro, pero E3B1 no modifica el artifact D4B.

## Reconciliación territorial dirigida

| Territorio | EGIF | ESFire30 | ICV | EFFIS |
| --- | ---: | ---: | ---: | ---: |
| País Valencià, total de cobertura | 22.108 partes | 2.203 perímetros | 13.738 registros / 13.739 perímetros | 25 perímetros |
| Galicia | 264.313 partes | 38.645 perímetros | no aplicable | no aplicable |
| Ourense | 81.943 partes | 16.265 perímetros | no aplicable | no aplicable |
| Elx | 194 partes | 6 perímetros | 178 registros / 178 perímetros | 1 perímetro |
| Cangas del Narcea | 3.172 partes | 2.610 perímetros | no aplicable | no aplicable |

Además pasan los ejemplos E2: España EGIF 1975=4.128, España EGIF
1995=25.557, GVA EGIF/ICV 1995=467/467, GVA ICV 2024=472, GVA EFFIS
2026=16 y Elx EFFIS 2025=1. La igualdad 467/467 no afirma identidad.

## Histogramas y filtros

Las cuatro fuentes tienen series anuales listas para E3B2 en los territorios
donde son aplicables. El histograma debe mostrar una métrica/fuente cada vez y
nunca apilar o sumar fuentes.

El summary no crea un cubo de filtros. Para E3C:

- EGIF área/GIF: datos base disponibles en INITIAL;
- ICV área/GIF/causa: datos base disponibles en `fires.json`;
- EFFIS área: disponible en los pequeños GeoJSON;
- ESFire30 área mínima: aplazada con su área cartografiada;
- causa EGIF canónica: bloqueada externamente.

## Reproducibilidad y validación

Build:

```bash
python3 scripts/build_national_ux_summary.py
```

Check:

```bash
python3 scripts/build_national_ux_summary.py --check
```

Tests específicos:

```bash
python3 -m unittest tests.test_es4e3b1_national_ux_summary
```

Dos builds finales limpios, uno en la ruta final y otro en `/tmp`, produjeron
123 ficheros byte-idénticos, el mismo manifest SHA-256
`b09e69648b6b2dee03265f12a00624de72d4006301b04d796889c1bf151a8e7b` y el
mismo fingerprint. Duraron 19,671 s y 9,769 s, con picos RSS de 264.790.016 B
y 264.769.536 B respectivamente.

Los cinco tests dirigidos y `--check` pasan. No se ejecutó Chromium ni la suite
completa.

## Estado

- `UX_SUMMARY_STATUS = PASS`
- `HISTOGRAM_DATA_STATUS = READY_FOR_UI`
- `PRODUCT_RELEASE_CANDIDATE = false`
- `D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`
- `NEXT_PHASE = ES-4E3B2_NATIONAL_METRICS_HISTOGRAM_UI`

E3B2 no se inicia en esta fase.
