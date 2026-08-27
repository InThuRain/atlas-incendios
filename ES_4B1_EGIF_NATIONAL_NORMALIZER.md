# ES-4B1 — Inventario de esquemas y normalizador nacional EGIF

Fecha: 27/08/2026  
Estado: normalización nacional completa ejecutada externamente y comprobada íntegramente.

## Alcance

El input es el snapshot raw EGIF nacional ES-4A de 56 ZIP anuales, 1968–2023,
con 646.887 partes. ES-4B1 produce exclusivamente `source_record` de tipo
`administrative_record`, compatible con el contrato nacional ES-2. No crea
geometrías, perímetros, puntos, relaciones CCINIF, municipios canónicos ni
identidades de episodio.

La ejecución nacional externa terminó con 56/56 bloques `complete`, 646.887
registros entre 1968 y 2023, 3.780.517.990 B de JSONL y cero fallos. El
manifiesto local confirma además SHA-256 de salida para los 56 bloques. La
comprobación `python3 scripts/normalize/egif/national.py --check --all` pasó
individualmente para todos los años. Los JSONL y el manifiesto de trabajo
siguen ignorados y no se publican.

En todos los registros normalizados:

```text
geometry = null
geometry_ids = []
geometry_id = null
spatial_reference_id = null
episode_id = null
episode_identity_status = unresolved
```

`HOJA`, `CUADRICULA`, `X`, `Y`, huso, datum y latitud/longitud se conservan
como valores fuente en `source_declared_location`. No se interpretan ni se
transforman en esta fase.

## Inventario de esquema

El exportador vigente ofrece una representación XML jerárquica común con los
contenedores `pif_comun`, `pif_localizacion`, `pif_tiempos`, `pif_deteccion`,
`pif_causa`, `pif_condiciones`, `pif_propagacion`, `pif_medios`,
`pif_tecnicas`, `pif_perdidas`, `pif_incidencias`, `pif_anexo` y relaciones
repetibles como `ParteMonte`. Esto no demuestra que los formularios históricos
fueran iguales: CV-3.2 ya documentó seis modelos por periodo.

El auditor streaming
`scripts/audit/spain/es4b1_egif_schema_inventory.py` recorre los 56 ZIP sin
retener el XML, registra paths, tipo léxico, ejemplos, cardinalidad, presencia
por año y firmas de población. El resultado local ignorado es:

```text
data/processed/egif/spain/2026-08-27/schema_inventory.json
```

La ejecución completa recorrió los 646.887 `Pif` de 56 ZIP y encontró 253
paths hoja de datos y 34 firmas distintas de presencia por año. Las firmas no
equivalen automáticamente a 34 formularios: un mismo XML actual representa
campos sin poblar de modos distintos según año, territorio y parte. La matriz
conserva la evidencia por año; los resultados que afectan al normalizador son:

| Grupo de campos | Presencia observada | Interpretación ES-4B1 |
|---|---:|---|
| `numeroparte`, `idpif`, `pif_comun.anio`, CCAA/provincia/municipio | 646.887 | conservar como identificadores/códigos fuente |
| detección | 646.887 | conservar sin corregir |
| extinción | 646.885 | conservar `null` en los 2 ausentes |
| causa `idcausa` | 646.887 | `cause_raw`; sin ontología aún |
| arbolada/no arbolada total | 646.579 / 646.802 | superficies separadas; no rellenar ausencias |
| agrícola / otras no forestales | 90.131 desde 1985 / 66.986 desde 2001 | campos opcionales |
| hoja / cuadrícula | 631.937 / 631.935 | referencia fuente; no geometría |
| X / Y | 292.448 / 292.447 desde 1998 | coordenadas fuente no interpretadas |
| huso / datum | 298.266 desde 1998 / 67.909 desde 2001 | conservar tal cual; no transformación |
| latitud / longitud | 292.447 desde 1998 | no asumir precisión/CRS por esta sola observación |
| `ParteMonte` | 681.181 valores, máximo 78 por parte | relación repetible preservada en `original_attributes` |

La primera cobertura observada de `HOJA+CUADRICULA` no es uniforme entre los
primeros años; por ejemplo, 1968 contiene ambos paths y 1969–1973 no los
pueblan. Esto es evidencia de población del exportador, no una revisión de las
conclusiones históricas de CV-3.5/ES-1.5. La relación CCINIF se mantiene fuera
del normalizador hasta la fase que la trate explícitamente.

Los modelos históricos se conservan sin inferir nuevas equivalencias:

| Años | `form_model` |
|---|---|
| 1968–1971 | `historical_form_1` |
| 1972–1979 | `historical_form_2` |
| 1980–1982 | `historical_form_3` |
| 1983–1988 | `historical_form_4` |
| 1989 | `historical_form_5` |
| 1990–1992 | `historical_form_6` |
| 1993–2023 | `post_1992_export_schema_not_yet_periodized` |

La última etiqueta es intencionadamente conservadora: ES-4B1 no convierte los
cambios de población observados en una nueva ontología de formularios.

## Modelo normalizado

El programa [national.py](scripts/normalize/egif/national.py) conserva:

- `record_id` y `fire_id`: `egif-record:<NumeroParte>` si el número es
  estructuralmente válido para año/provincia; un hash reproducible por registro
  cuando no lo es;
- `source_record_id` (`NumeroParte`) e `source_database_id` (`IdPif`);
- año, detección y extinción fuente;
- CCAA/provincia/municipio/paraje fuente sin normalización territorial;
- superficies declaradas, con `reported_forest_area_ha` separada de total;
- causa fuente en `cause_raw`, con `cause_code=null` y
  `cause_mapping_status=unmapped`;
- hoja, cuadrícula, X/Y, huso, datum y latitud/longitud como texto fuente;
- `provenance` con ZIP, SHA-256, XML member, adquisición y transformación;
- `original_attributes` completo.

El ID identifica un parte administrativo, no un episodio físico. La regla
mantiene compatibilidad con los IDs `egif-record:…` ya publicados para el
piloto valenciano y no intenta resolver Marines–Altura ni otros multiparte.
Si un `NumeroParte` se repite dentro de un bloque, ambos valores fuente se
conservan, pero los registros reciben IDs hash reproducibles con
`identity_status=ambiguous`; nunca se deduplican ni se fuerza una identidad.

## Procesamiento por bloques

Cada año es un bloque de salida independiente:

```text
data/processed/egif/spain/2026-08-27/
  egif_records_YYYY.jsonl
  manifest.json
```

El manifest local registra checksum del ZIP de entrada, checksum/bytes/recuento
del JSONL, pico RSS del proceso y los estados `pending`, `processing`,
`complete` o `failed`. La escritura del JSONL es temporal y atómica. Un bloque
`complete` solo se reutiliza si input y output mantienen sus checksums y
recuentos; `--check` relee el JSONL y valida invariantes del contrato sin usar
red.

## Muestra ejecutada

Se eligieron 1968, 1974, 1983, 1992, 1998 y 2023: cubren los cortes conocidos
1968/1972/1983/1990, el primer año sistemático documentado, la coexistencia
posterior de ubicación/campos más ricos y el final del snapshot disponible.

| Año | Partes input/output | JSONL |
|---|---:|---:|
| 1968 | 2.038 / 2.038 | 10.443.732 B |
| 1974 | 3.920 / 3.920 | 20.587.447 B |
| 1983 | 4.736 / 4.736 | 25.557.607 B |
| 1992 | 15.956 / 15.956 | 88.208.981 B |
| 1998 | 22.003 / 22.003 | 124.411.391 B |
| 2023 | 5.223 / 5.223 | 35.027.746 B |
| **Total** | **53.876 / 53.876** | **304.236.904 B** |

El pico RSS observado fue 31.928.320 B (~30,5 MiB), incluyendo la comprobación
previa de identificadores repetidos dentro del año, sin cargar varios XML ni
varios años en memoria. `--check` pasó para los seis bloques; `--resume` los
reutilizó; una repetición con `--force` produjo los mismos seis SHA-256 de
output, confirmando determinismo del JSONL.

La ejecución completa confirmó 3.780.517.990 B (~3,52 GiB) de JSONL. Es un
resultado de procesamiento interno, no un asset web ni una autorización para
publicar el derivado.

## Ejecución manual completa

Desde la raíz del repositorio:

```bash
python3 scripts/normalize/egif/national.py --resume --all
```

Después, sin red:

```bash
python3 scripts/normalize/egif/national.py --check --all
```

La ejecución completa ya satisface este cierre y permite iniciar ES-4B2.

## Pruebas específicas

```bash
.venv/bin/python -m unittest \
  tests.test_es4b1_egif_national_normalizer \
  tests.test_es4a_egif_national_downloader -v
```

Estas pruebas cubren identidad, conservación de atributos, ausencia obligada
de geometría, contrato administrativo, periodos documentados, JSONL atómico y
determinista, recuentos de bloques y reanudación de la descarga previa.
