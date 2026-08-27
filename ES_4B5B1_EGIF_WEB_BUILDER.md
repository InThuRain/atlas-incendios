# ES-4B5B1 — Generador reproducible de assets web EGIF nacionales

Fecha: 27/08/2026. Esta fase implementa el builder del contrato ES-4B5A y lo valida con una muestra territorial. No ha generado el derivado nacional completo, no modifica el frontend y no publica assets.

## Alcance y exclusiones

El builder solo acepta `--profile development` y su manifest declara `source_ids=["egif"]`, `excluded_source_ids=["ccinif_grid", "gva_sigif"]` y `publication_status=development_only_no_national_public_profile`.

No lee relaciones CCINIF ni copia `spatial_reference_id`, geometría, `geometry_ids`, coordenadas, XML u `original_attributes` a un asset web. `geometry=null` sigue siendo la semántica de EGIF.

## Formato columnar v1

Cada partición produce dos JSON compactos deterministas. `initial.json` declara `schema_version`, `source_id`, `entity_type`, `asset_id`, `territory_id`, rango temporal, rol, `fields`, representación de nulos, dictionary encoding y `columns`.

Sus columnas, en este orden fijo, son:

```text
record_id
year
autonomous_community_id
province_id
municipality_id
reported_forest_area_ha
is_gif_forest_ge_500_ha
cause_source_code
canonical_cause
cause_mapping_status
coverage_status
identity_status
episode_identity_status
```

`record_id` es siempre `egif-record:<NumeroParte>`. Los valores nulos son `null` JSON; no existe dictionary encoding en esta versión. `canonical_cause` es `null` y `cause_mapping_status` es `unmapped` hasta recibir el diccionario oficial. El GIF es trivalente: `true`, `false` o `null` si no hay superficie forestal para evaluarlo.

`detail.json` contiene, en idéntico ordinal que `initial.json`: `source_record_id`, fechas de detección/extinción, superficies total/arbolada/no arbolada, municipio/paraje declarados, modelo de parte e ID de base fuente. No repite `record_id`: incluye `initial_record_id_order_sha256` y `ordinal_alignment`; el cliente crea `record_id → ordinal` desde el asset inicial.

## Particionado y reanudación

Las unidades son `egif × CCAA × bloque temporal`:

| Bloque | Años |
| --- | --- |
| Histórico temprano | 1968–1979 |
| Histórico/transición | 1980–1992 |
| Consolidación 1 | 1993–2002 |
| Consolidación 2 | 2003–2012 |
| Reciente disponible | 2013–2023 |

`--period` debe cubrir bloques completos: evita crear un asset etiquetado 1968–1979 que contenga solamente 1974.

El builder guarda dos checkpoints: primero por año escribe spools compactos con checksum por asset; después combina los spools, ordena por `record_id`, escribe ambos JSON atómicamente y registra sus checksums. `--resume` reutiliza spools/assets válidos. `--check` verifica tamaños, SHA-256, gzip calculado, longitudes de columnas, IDs únicos, contrato causa/GIF y alineación initial/detail.

Cada entrada de manifest incluye `asset_id`, `source_id`, `territory_id`, rango, recuento, formato, schema, perfil, checksums de entrada, estado, paths, tamaños raw/gzip, SHA-256 y métricas de build.

## Muestra ejecutada

Se generaron solo seis assets locales ignorados:

```text
CCAA: País Valencià (ES:CCAA:10), Galicia (ES:CCAA:12), La Rioja (ES:CCAA:17)
Bloques: 1968–1979 y 2013–2023
```

| Asset | Partes | Initial raw/gzip | Detail raw/gzip |
| --- | ---: | ---: | ---: |
| País Valencià 1968–1979 | 2.395 | 334.755 / 13.371 B | 262.053 / 35.059 B |
| País Valencià 2013–2023 | 3.360 | 508.419 / 26.094 B | 499.717 / 81.468 B |
| Galicia 1968–1979 | 17.880 | 2.493.679 / 79.951 B | 1.948.170 / 227.539 B |
| Galicia 2013–2023 | 20.850 | 3.143.799 / 129.108 B | 2.923.527 / 379.835 B |
| La Rioja 1968–1979 | 249 | 35.531 / 2.134 B | 27.997 / 4.547 B |
| La Rioja 2013–2023 | 702 | 106.646 / 5.901 B | 101.718 / 17.864 B |

Resultado reconciliado: **45.436 partes**, seis assets completos, sin pérdidas ni duplicados. Tamaño final raw: **12.386.011 B**; gzip calculado: **1.002.871 B** (**272,603 raw B/parte**, **22,072 gzip B/parte**).

El build forzado leyó 23 bloques anuales, tardó 27,827 s y tuvo pico RSS de 178.958.336 B. El directorio de trabajo, con spools reanudables, ocupó 48.126.897 B. La repetición con `--resume` reutilizó los 23 spools y los seis assets; `--check` validó los seis sin errores.

## Validación automatizada

`tests/test_es4b5b1_egif_web_builder.py` pasó 3/3 casos: contrato/determinismo/alineación; rechazo de periodos parciales; y build-resume-check de fixture de doce años con reconciliación, municipio `null`, causa no mapeada, ID estable y exclusión CCINIF.

## Ejecución nacional completa confirmada

```bash
python3 scripts/build/egif/national_web.py \
  --resume \
  --profile development \
  --all
```

Y, al terminar:

```bash
python3 scripts/build/egif/national_web.py \
  --check \
  --profile development \
  --all
```

El usuario ejecutó ambos comandos el 27/08/2026. El manifest local confirma:

| Métrica | Resultado |
| --- | ---: |
| Assets configurados/completos | 88 / 88 |
| Partes EGIF | 646.887 |
| Tamaño raw final | 181.891.957 B |
| Gzip calculado | 14.338.792 B |
| Tiempo de build | 286,045 s |
| Pico RSS | 817.565.696 B |
| Directorio con spools | 668 MB |

La reconciliación independiente de los 56 recuentos anuales del manifest
normalizado vuelve a sumar 646.887. Los 88 assets tienen estado `complete`,
checksums y tamaños verificados; el `--check --all` externo terminó con
`failures=0`. El perfil contiene únicamente `egif` y excluye explícitamente
`ccinif_grid` y `gva_sigif`.

El output es `data/web/spain/egif/2026-08-27/` y permanece ignorado por Git.

## Siguiente paso propuesto

Prompt mínimo para ES-4B5B2, tras la ejecución externa:

> ES-4B5B1 está aprobado. El build nacional y `--check --all` han terminado. Revisa el manifest y los resultados pegados, reconcilia los 646.887 registros y realiza únicamente la auditoría de assets y preparación de integración posterior; no modifiques frontend ni publiques.
