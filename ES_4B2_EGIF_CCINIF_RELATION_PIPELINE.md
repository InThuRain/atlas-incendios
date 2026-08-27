# ES-4B2 — Auditoría nacional EGIF y preparador de relaciones CCINIF

Estado: auditoría y cruce nacional terminados localmente; pendiente de
revisión y de la definición explícita de ES-4B3.

## Contrato semántico

El registro EGIF sigue siendo un parte administrativo sin geometría:

```text
EGIF.geometry = null
historical_grid_cell != fire_geometry
```

La malla CCINIF recibida es una referencia histórica de localización de 10 ×
10 km. Su licencia sigue siendo `false_pending_permission`; todos los outputs
de esta fase quedan bajo `data/derived/spain/es4b2/`, ignorados por Git y fuera
de cualquier perfil público.

## Pipeline

`scripts/relations/egif/ccinif.py` reutiliza el parser y normalización exacta
de ES-1.5. Construye una vez `historical_grid_cells.json` con 5.286 celdas
lógicas y sus 6.063 fragmentos geométricos; los registros anuales solo guardan
la relación:

```text
record_id -> spatial_reference_id
```

No duplica geometrías de celda por parte. El estado se decide exclusivamente
con `HOJA + CUADRICULA` normalizados por espacios/caja, sin padding ni fuzzy
matching:

| Estado | Regla |
|---|---|
| `confirmed` | par exacto presente en celda CCINIF keyed |
| `ambiguous` | solo una componente, o etiqueta canaria sin HOJA que no identifica una celda única |
| `unusable` | par completo ausente de la malla keyed |
| `no_reference` | ni HOJA ni CUADRICULA |

Canarias sin HOJA permanece explícitamente `ambiguous`: no se inventa una
hoja ni se elige una geometría entre etiquetas locales repetidas.

Cada año es un bloque reanudable con checksum del JSONL EGIF input, checksum
de la malla/celdas, recuento, bytes, distribución de estados y checksum del
JSONL de relaciones. El manifest se reescribe atómicamente antes y después de
cada bloque: una interrupción deja el bloque anterior `complete` intacto y el
interrumpido como `downloading` o `failed`. `--resume` reutiliza bloques
completos; `--check` relee la salida y verifica checksum, semántica y recuento.

## Muestra

Se procesaron 1968, 1974, 1983, 1998 y 2023: 37.920 partes. La muestra cubre
un año sin referencias útiles, cobertura histórica parcial, cobertura alta,
coexistencia X/Y y un año reciente. La celda única local pesa 6.655.806 B,
959.632 B gzip; las cinco relaciones pesan 18.566.218 B, 558.473 B gzip.

| Año | Partes | `confirmed` | `ambiguous` | `unusable` | `no_reference` |
|---|---:|---:|---:|---:|---:|
| 1968 | 2.038 | 0 | 0 | 1 | 2.037 |
| 1974 | 3.920 | 3.655 | 48 | 1 | 216 |
| 1983 | 4.736 | 4.637 | 99 | 0 | 0 |
| 1998 | 22.003 | 21.923 | 80 | 0 | 0 |
| 2023 | 5.223 | 5.223 | 0 | 0 | 0 |

Una segunda ejecución con `--resume` reutilizó los cinco bloques y `--check`
los verificó sin errores. El control País Valencià de ES-1.5 se conserva sin
alterar: para 1968–1992, 9.175 partes, 8.565 referencias confirmadas, 610 sin
referencia y 270 pares únicos.

El fixture ES-1.5 conserva el control País Valencià: 9.175 partes de
1968–1992, 8.565 referencias exactas y 610 sin referencia, con 270 pares
únicos. No se recalcula ni se modifica esa relación en ES-4B2.

## Auditoría normalizada

`scripts/audit/spain/es4b2_egif_normalized_audit.py` recorrió los JSONL por
streaming y produjo `data/derived/spain/es4b2/normalized_audit.json` (local e
ignorado). Reconciliación obtenida:

| Control | Resultado |
|---|---:|
| Registros / manifest | 646.887 / 646.887 |
| Años | 1968–2023 (56) |
| `record_id`, `source_record_id`, `IdPif` repetidos | 0 / 0 / 0 |
| Grupos / partes sustancialmente iguales con IDs distintos | 1.212 / 2.458 |
| Geometrías no nulas o `geometry_ids` no vacíos | 0 |
| HOJA / CUADRICULA pobladas | 631.937 / 631.935 |
| Pares HOJA+CUAD completos distintos | 5.426 |
| X e Y simultáneos | 292.447 |
| Provincia, CCAA, municipio, causa y detección fuente | 646.887 cada uno |
| Extinción fuente | 646.885 |

`reported_forest_area_ha` es no nulo en los 646.887 registros porque el
normalizador la deriva únicamente cuando existe alguno de sus componentes
declarados; no debe confundirse con que ambos campos fuente arbolada/no
arbolada estén completos en todos los años.

Los 1.212 grupos (2.458 partes) de similitud se detectan con un hash de año,
fechas, localización declarada, causa raw, superficies declaradas y modelo de
parte, excluyendo identificadores, procedencia y `original_attributes`. Son
anomalías candidatas a revisión, no una regla de identidad: esta fase no
deduplica ni infiere episodios físicos a partir de ellas.

El auditor no rehace la adquisición ni el cruce nacional ES-1.5: vincula la
salida al SHA-256 del manifest normalizado y al SHA-256 del manifest de
crosswalk ES-1.5. Ese crosswalk verificable conserva 631.935 pares completos,
626.957 `A_CONFIRMED`, 3.465 `C_AMBIGUOUS`, 1.515 `D_UNUSABLE` y 14.950
`NO_REFERENCE` (sin `B_PROBABLE`). En el pipeline nuevo equivalen,
respectivamente, a `confirmed`, `ambiguous`, `unusable` y `no_reference`.
No fusiona partes ni recalcula la malla.

El cruce nacional completo se ejecutó después de la muestra: 56/56 bloques
`complete`, 646.887 relaciones, 317.291.434 B de JSONL y 56 checksums de
salida. `--check --all` verificó individualmente los 56 bloques sin fallos.
La distribución coincide exactamente con ES-1.5: 626.957 `confirmed`, 3.465
`ambiguous`, 1.515 `unusable` y 14.950 `no_reference`. Las celdas únicas
continúan pesando 6,7 MB raw (1,0 MB gzip); los tamaños gzip de las relaciones
pueden medirse en una fase de entrega posterior, pero no se generan assets web
en ES-4B2.

## Ejecución manual

```bash
.venv/bin/python scripts/relations/egif/ccinif.py --resume --all
.venv/bin/python scripts/relations/egif/ccinif.py --check --all
```

El parser de los KMZ utiliza Shapely, fijado en `requirements-dev.txt`. Si no
existe aún el entorno reproducible:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

El manifest local confirma que los 56 bloques están `complete`, que no hay
errores y que todos tienen checksum. ES-4B3 no debe empezar sin un objetivo
aprobado explícitamente.

Para repetir solo un rango o rehacerlo explícitamente:

```bash
.venv/bin/python scripts/relations/egif/ccinif.py --resume --period 1985:1992
.venv/bin/python scripts/relations/egif/ccinif.py --force --period 1985:1992
```
