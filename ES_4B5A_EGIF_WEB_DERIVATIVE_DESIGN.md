# ES-4B5A — Diseño del derivado web compacto EGIF nacional

Fecha de medición: 27/08/2026. Esta subfase es un laboratorio de formato y
particionado. No genera ni publica el derivado nacional completo y no modifica
el frontend.

## Alcance e inputs

Se reutilizan sin volver a normalizarlos:

- ES-4B1: 646.887 registros normalizados, 3.780.517.990 B; el registro sigue
  siendo `administrative_record` y `geometry=null`.
- ES-4B2: relaciones EGIF→CCINIF, que continúan bloqueadas para publicación.
- ES-4B3: auditorías y relaciones territoriales por `record_id`.
- ES-4B4A y ES-4B4B2A: inventario de `pif_causa.idcausa`; hay 35 etiquetas
  oficiales recuperadas parcialmente, pero faltan 52 de los 87 códigos y no
  existe todavía un diccionario/vigencia suficiente para una ontología.

El script de esta fase lee únicamente 1974, 1995 y 2023 y escribe muestras
locales ignoradas en `data/derived/spain/es4b5a/`. El resultado reproducible de
las mediciones sí queda versionado en
`data/audit/egif/es4b5a_web_derivative_benchmark.json`.

## Contrato web v1 propuesto

Cada asset inicial declara en su manifest, una sola vez:

```text
source_id=egif
entity_type=administrative_record
geometry_availability=none
geometry_semantics=none
```

El registro compacto lleva solo estos campos:

| Clase | Campos |
| --- | --- |
| Identidad y tiempo | `record_id`, `year`, `identity_status`, `episode_identity_status` |
| Territorio canónico | `autonomous_community_id`, `province_id`, `municipality_id` |
| Métrica EGIF | `reported_forest_area_ha`, `is_gif_forest_ge_500_ha`, `coverage_status` |
| Causa | `cause_source_code`, `canonical_cause`, `cause_mapping_status` |

`record_id` conserva sin cambio `egif-record:<NumeroParte>`. Los nombres de
CCAA, provincia y municipio proceden de un catálogo territorial separado. Los
valores no resueltos quedan como `null`; no se deducen a partir de una celda,
nombre ni geometría.

`is_gif_forest_ge_500_ha` expresa la métrica administrativa ya normalizada:
`reported_forest_area_ha >= 500`. Es `null` si falta superficie forestal, para
no convertir información desconocida en «no GIF».

La ficha bajo demanda, separada y asociada por `record_id`, puede incluir:
`source_record_id`, fechas de detección/extinción, superficie total/arbolada/no
arbolada, municipio y paraje declarados, modelo de parte e ID de base fuente.
`original_attributes`, XML raw y cualquier detalle no necesario para la ficha
permanecen en archivo/pipeline, nunca en el payload web.

### Causas y CCINIF

Hasta recibir el diccionario oficial MITECO/EGIF:

```json
{"cause_source_code":"211","canonical_cause":null,"cause_mapping_status":"unmapped"}
```

Esto conserva el código fuente sin fabricar equivalencias y permite añadir un
diccionario posterior sin cambiar ni el `record_id` ni la partición.

CCINIF tiene `publishable=false_pending_permission`. Por tanto el asset público
no contiene `spatial_reference_id`, geometrías de celda ni relaciones
EGIF→CCINIF. El contrato conserva la extensión como un asset relacional
independiente, disponible solo cuando una licencia/perfil futuro lo autorice.

## Campos por fase de carga

| Uso | Campos |
| --- | --- |
| INITIAL | Los 13 campos del contrato compacto anterior. |
| ON_SELECTION | Los diez campos de ficha descritos arriba, cargados por bloque y con lookup por `record_id`. |
| BACKEND / ARCHIVE_ONLY | `original_attributes`, XML, URLs y checksums por registro, campos meteorológicos/operativos, coordenadas crudas y relaciones CCINIF bloqueadas. |

La provenance de adquisición, checksums de entrada y transformaciones se
declara en el manifest del asset/bloque, no se replica 646.887 veces.

## Particionado propuesto

La unidad de entrega recomendada es:

```text
source_id × autonomous_community_id × temporal_block
```

Un parte se asigna a una única CCAA administrativa canónica/declarada de
ES-4B3. Una intersección futura de celda CCINIF o geometría no genera una copia
adicional del registro.

Los bloques temporales se derivan de los recuentos del manifest ES-4B1:

| Bloque | Partes nacionales |
| --- | ---: |
| 1968–1979 | 42.967 |
| 1980–1992 | 136.534 |
| 1993–2002 | 200.513 |
| 2003–2012 | 164.204 |
| 2013–2023 | 102.669 |

El build futuro omitirá combinaciones CCAA×bloque vacías y producirá manifests
con recuento, tamaño, gzip, checksum, rango temporal y perfil publicable. La
ficha será un segundo asset del mismo bloque: no se descarga al inicio.

## Formatos medidos

Se compararon serializaciones JSON deterministas (`ensure_ascii=false`, claves
ordenadas, separadores compactos) con gzip nivel 9 y mtime fijo. Los tiempos y
heap proceden de Python/tracemalloc: sirven para comparar formatos, no son una
medición de heap de navegador.

| Muestra | Partes | Array raw/gzip | JSONL raw/gzip | Columnar raw/gzip |
| --- | ---: | ---: | ---: | ---: |
| 1974 nacional | 3.920 | 554.648 / 23.708 B | 1.542.165 / 27.457 B | 547.086 / 20.794 B |
| 1995 nacional | 25.557 | 3.885.804 / 158.249 B | 10.325.845 / 187.370 B | 3.834.968 / 143.817 B |
| 2023 nacional | 5.223 | 799.503 / 42.160 B | 2.115.376 / 49.740 B | 789.335 / 39.795 B |
| Galicia 1995 | 15.254 | 2.318.344 / 89.964 B | 6.162.029 / 106.077 B | 2.288.114 / 83.010 B |
| País Valencià 1995 | 467 | 71.334 / 3.720 B | 188.695 / 4.252 B | 70.678 / 3.750 B |
| La Rioja 1995 | 177 | 27.235 / 1.609 B | 71.516 / 1.824 B | 27.159 / 1.718 B |

En la muestra nacional alta de 1995, el array necesitó 69,0 ms de parseo y
22,9 MiB de pico Python; el formato columnar 46,2 ms y 21,0 MiB. JSONL necesitó
250,3 ms y 61,9 MiB. La ventaja de columna se repite en los tres años
nacionales; en bloques muy pequeños la diferencia gzip es irrelevante.

Extrapolación prudente a 646.887 partes, usando únicamente los tres años
nacionales sin solapar muestras territoriales:

| Formato | Raw | gzip | Pico de parseo Python extrapolado |
| --- | ---: | ---: | ---: |
| Array | 93,16 MiB | 3,98 MiB | 574,82 MiB |
| JSONL | 248,61 MiB | 4,70 MiB | 1.561,08 MiB |
| JSON columnar | 91,94 MiB | 3,63 MiB | 524,82 MiB |

La extrapolación no autoriza cargar España completa: el overhead de objetos es
alto y no equivale al motor JS. Refuerza precisamente la entrega por CCAA y
bloque temporal.

### Decisión de formato para ES-4B5B

Se recomienda **JSON columnar compacto**, aún legible y sin dependencia
binaria, con nombres de campos declarados y arrays por columna. Reduce raw y
gzip frente al array en los bloques nacionales, hace más barato el parseo de
las muestras grandes y permite filtrar sin reconstruir objetos. El índice de
selección es `record_id → ordinal` de columna.

JSON array queda como alternativa simple para debug/fixtures. JSONL no se
recomienda: no aporta streaming útil al navegador para estos filtros y aumenta
tamaño, parseo y heap.

## Ficha bajo demanda

En 1995 nacional el INITIAL columnar ocupa 143.817 B gzip. El detalle separado
de la misma muestra ocupa 489.464 B gzip; si se combina todo inicialmente son
646.997 B gzip. Separar ficha evita descargar aproximadamente el 78 % de ese
payload antes de que alguien seleccione un parte. Con partición CCAA×bloque el
detalle descargado será menor que el total nacional de la tabla.

## Validación

El test específico `tests/test_es4b5a_egif_web_derivative_design.py` comprueba:

- identidad `egif-record:<NumeroParte>` y GIF administrativo;
- municipio no resuelto como `null`;
- ausencia de `geometry` y `spatial_reference_id` en perfil público;
- serializaciones deterministas y lookup round-trip;
- separación efectiva de campos de ficha y payload inicial.

Resultado: 5/5 pruebas superadas. El script de muestra procesó 50.598 filas
en total (con solapamiento intencional entre la muestra nacional 1995 y sus
submuestras), sin crear assets nacionales.

## Pipeline propuesto para ES-4B5B (no ejecutado aquí)

El siguiente paso debería implementar un build reanudable nuevo, no reutilizar
estas muestras como producción:

```bash
python3 scripts/build/egif/national_web.py \
  --resume --profile development \
  --input-manifest data/processed/egif/spain/2026-08-27/manifest.json \
  --territory-manifest data/derived/spain/es4b3/territory_relations/2026-08-27/manifest.json \
  --output data/web/spain/egif
```

El perfil `public` deberá aplicar publication guard y excluir de forma cerrada
CCINIF y cualquier relación suya hasta contar con permiso explícito. Este
comando es una propuesta de interfaz para ES-4B5B; el script no existe todavía.

## Límites pendientes

- Diccionario oficial completo y vigencia histórica de causas EGIF.
- Licencia y atribución para las relaciones/celdas CCINIF.
- Medición de navegador real sobre assets ya particionados, que corresponde a
  ES-4B5B y no se ha adelantado en esta fase.
