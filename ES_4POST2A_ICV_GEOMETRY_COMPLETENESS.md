# ES-4POST2A — Completitud geométrica ICV

## Resultado

```text
ICV_GEOMETRY_COMPLETENESS = PASS
GEOMETRY_COMPLETENESS     = PARITY
PRODUCTION_PATCH_PRIORITY = HIGH
RELEASE_TAG_STATUS        = HOLD
MAP_EXPLORATION_PARITY    = STILL_FAILS_PENDING_VISUAL_INTERACTION
NEXT_PHASE                = ES-4POST2B_TEMPORAL_ENCODING_AND_OVERLAP
```

Esta corrección recupera en el runtime nacional las geometrías ICV oficiales
que ya existían en el snapshot publicado. No modifica los datos fuente, no
fusiona ICV con ESFire30 y no introduce la codificación temporal, popups,
leyenda ni cambios móviles de POST2B–D.

## Regresión reproducida

El fixture conserva exactamente el comportamiento anterior del loader:

| Rango ICV 1993–2024 | Registros | Geometrías |
| --- | ---: | ---: |
| Crosswalk runtime anterior | 12.404 | 12.405 |
| Snapshot ICV canónico | 13.738 | 13.739 |
| Recuperado | 1.334 | 1.334 |

La prueba enfocada calcula ambas rutas sobre el mismo `fires.json`: con los
tres literales antiguos obtiene 12.404/12.405; con el crosswalk explícito
actual reconcilia 13.738/13.739. Habría fallado antes del fix al exigir las
siete grafías documentadas.

## Causa y crosswalk

`build_national_ux_summary.py` ya tenía siete alias explícitos. En cambio,
`icv_loader.mjs` filtraba el mapa mediante un objeto distinto de sólo tres
claves, sensible a grafía, mayúsculas y acentos. Por ello el resumen era
correcto y el mapa excluía valores 2016–2019 antes de cargar su colección
GeoJSON.

El nuevo módulo [icv_territory_crosswalk.mjs](prototypes/es4c/icv_territory_crosswalk.mjs)
es la única normalización usada por el loader del mapa. Es un crosswalk
exacto, no una coincidencia difusa: un valor no documentado devuelve `null`,
no se resuelve por municipio, cercanía ni geometría.

| Valor fuente | Normalizado | Provincia ES-2 | Registros / geometrías |
| --- | --- | --- | ---: |
| `ALICANTE` | Alicante/Alacant | `ES:PROV:03` | 338 / 338 |
| `Alicante/Alacant` | Alicante/Alacant | `ES:PROV:03` | 3.330 / 3.331 |
| `CASTELLON` | Castellón/Castelló | `ES:PROV:12` | 273 / 273 |
| `Castellon` | Castellón/Castelló | `ES:PROV:12` | 1 / 1 |
| `Castellón/Castelló` | Castellón/Castelló | `ES:PROV:12` | 3.070 / 3.070 |
| `VALENCIA` | Valencia/València | `ES:PROV:46` | 722 / 722 |
| `Valencia/València` | Valencia/València | `ES:PROV:46` | 6.004 / 6.004 |

Las siete grafías enlazan además explícitamente a `ES:CCAA:10`. El loader
expone `province_id`, `autonomous_community_id` y `year` en las features
renderizables; el municipio mantiene exclusivamente el enlace documental
preexistente de ICV, sin fallback espacial.

## Distribución afectada

| Año | Registros recuperados | Geometrías recuperadas |
| --- | ---: | ---: |
| 2016 | 341 | 341 |
| 2017 | 346 | 346 |
| 2018 | 375 | 375 |
| 2019 | 272 | 272 |
| Total | 1.334 | 1.334 |

No hay otros valores fuente observados sin crosswalk. Los totales territoriales
finales son Comunitat Valenciana 13.738/13.739, Alacant 3.668/3.669,
Castelló 3.344/3.344 y València 6.726/6.726.

## Regresiones preservadas

- 1995 conserva 467 registros y 467 geometrías.
- 2024 conserva 472 registros y 473 geometrías.
- `gva:pif-cv:2024AL0005` conserva un único registro con dos `geometry_id`.
- El estado/permalink `es4c-state-v1` no cambia.
- Los filtros ICV de superficie, GIF y causa se aplican después de resolver
  provincia; se probaron también sobre un registro recuperado (`2016AL0074`).
- EGIF, ESFire30 y EFFIS no cambian ni se relacionan con ICV.

## Verificación local del producto

Se construyó sólo el frontend ligero y se enlazaron, en modo lectura, los
assets ya aceptados de `build/national-product-staging/data`. No se regeneró
ningún GeoJSON ICV, resumen, PMTiles, Protomaps, EGIF, EFFIS ni límite
administrativo.

En Chromium local, con viewport encuadrado sobre una feature recuperada:

| Escenario | Cargados registros/geometrías | Renderizados viewport | Selección/ficha | Filtro área ≥500 / restauración |
| --- | ---: | ---: | --- | --- |
| GVA 2016 | 341 / 341 | 6 | PASS | 4 / 341 |
| GVA 2017 | 346 / 346 | 4 | PASS | 2 / 346 |
| GVA 2018 | 375 / 375 | 4 | PASS | 1 / 375 |
| GVA 2019 | 272 / 272 | 1 | PASS | 1 / 272 |
| GVA 1993–2024 | 13.738 / 13.739 | 186 | PASS | 74 / 13.738 |

Los conteos renderizados son subconjuntos de un viewport concreto; los de
carga son los que reconcilian el snapshot. No hubo errores runtime. Cada
feature de control mantiene `year`, por lo que POST2B puede aplicar una
codificación temporal sin cambiar el modelo ni esta corrección.

Los tiempos locales de cada escenario quedaron entre 4,86 s y 7,52 s,
incluyendo cold start de Chromium y carga del producto local. Se añaden 1.334
features que ya existían en assets ICV de alcance valenciano: no hay carga
nacional eager ni descarga completa de PMTiles.

## Assets y validaciones

Sólo se modifican/copian al frontend:

- `prototypes/es4c/icv_territory_crosswalk.mjs`;
- `prototypes/es4c/icv_loader.mjs`;
- la lista de módulos runtime de `scripts/build_national_frontend.py`.

El auditor reproducible y la evidencia son:

```bash
python3 -m unittest tests/test_es4post2a_icv_geometry_completeness.py -v
python3 scripts/audit/product/es4post2a_icv_geometry_completeness.py --runtime-smoke
python3 scripts/audit/product/es4post2a_icv_geometry_completeness.py --check
python3 scripts/build_national_frontend.py --output build/es4post2a-frontend
python3 scripts/build_national_frontend.py --check --output build/es4post2a-frontend
```

Las cinco pruebas enfocadas pasan: fixture pre-fix, alias explícitos y valor
desconocido negativo, años afectados/cardinalidades 1995–2024, empaquetado del
runtime y filtros área/GIF/causa sobre un registro recuperado. El auditor
registra además la interacción real del mapa.

## Producción

La producción nacional actual sigue viva y sin cambios durante esta fase, pero
omite 1.334 perímetros ICV oficiales en 2016–2019. Por ello este cambio es un
parche de corrección de prioridad **HIGH**. No se hizo push, deploy, tag ni
release. `RELEASE_TAG_STATUS` sigue en `HOLD` hasta completar las regresiones
de exploración visual pendientes.

Sigue pendiente únicamente en la familia POST2: color temporal/lectura de
solapes (POST2B), popup humano directo (POST2C) y aceptación móvil/final
(POST2D). Esta fase no implementa ninguna de ellas.
