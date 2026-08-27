# ES-4B5C1 — Harness de benchmark de navegador EGIF nacional

Fecha: 28/08/2026. Esta subfase crea un laboratorio aislado para medir los
assets EGIF de ES-4B5B1 en Chromium. No modifica el frontend, no reconstruye
assets, no abre el normalizado nacional ni publica nada.

## Arquitectura

```text
benchmarks/es4b5c/scenarios.json
        ↓
benchmarks/es4b5c/run.py
        ├── servidor HTTP local, solo lectura, sobre la raíz del repositorio
        ├── Chromium headless mediante el cliente CDP ya existente
        └── benchmarks/es4b5c/egif_benchmark.html
                    ↓
              manifest ES-4B5B1 + initial/detail.json existentes
                    ↓
              results.json local e ignorado
```

El servidor envía `Cache-Control: public, max-age=31536000, immutable` solo a
los assets `data/web/spain/egif/.../assets/`; el manifest y el harness usan
`no-store`. Así se puede comparar una carga fría —perfil Chromium nuevo— con
una carga caliente: el harness realiza un primer pase descartado y mide el
segundo en ese mismo perfil. Esto mide caché HTTP local/memoria de Chromium,
no una CDN ni GitHub Pages.

La batería principal contiene los escenarios aprobados A–J:

| ID | Alcance |
| --- | --- |
| A | La Rioja, completo |
| B | País Valencià, completo |
| C | Cataluña, completo |
| D | Andalucía, completo |
| E | Castilla y León, completo |
| F | Galicia, completo |
| G | Galicia, 1993–2002 |
| H | España, 1993–2002 |
| I | España, 2013–2023 |
| J | España, todos los bloques INITIAL |

Existe además `smoke_la_rioja_2013_2023`, que no se ejecuta con `--all`.

## Métricas disponibles

Por ejecución se guardan, sin fabricar valores no expuestos por Chromium:

- assets y partes INITIAL seleccionados;
- requests, cuerpo raw recibido, `transferSize` de Resource Timing cuando
  Chromium lo expone, y gzip estimado desde el manifest;
- tiempo de fetch, `JSON.parse`, preparación y creación del `Map`
  `record_id → ordinal`;
- filtro columnar por año, rango, provincia, municipio resuelto y municipio
  `null`;
- lookup estable por `record_id`;
- selección inicial, DETAIL lazy, segunda selección del mismo asset sin nueva
  request y, cuando hay otro asset INITIAL, selección que carga un segundo
  DETAIL;
- `performance.memory.usedJSHeapSize` antes, tras INITIAL y tras DETAIL, o
  `unavailable` si Chromium no lo facilita;
- comparación puntual en un asset pequeño: filtro columnar frente a
  materializar objetos, limitada a 1.000 filas como máximo.

No se materializan objetos JS para el conjunto completo. La lectura normal
opera sobre columnas. `record_id` conserva su columna y el harness mide el
coste real de crear su lookup, sin probar alternativas de hash o compresión.

## Smoke test ejecutado

Se ejecutó exclusivamente la carga fría de La Rioja 2013–2023, un asset y 702
partes. Resultado en el `results.json` local:

| Métrica | Resultado |
| --- | ---: |
| Requests INITIAL / DETAIL | 1 / 1 |
| INITIAL body raw / gzip manifest | 106.646 B / 5.901 B |
| DETAIL body raw / gzip manifest | 101.718 B / 17.864 B |
| Fetch INITIAL / parse | 5,1 ms / 0,3 ms |
| Preparar lookup | 0,3 ms |
| Filtros | 0,4 ms |
| Primera selección DETAIL | 7,1 ms |
| Segunda selección mismo asset | 0,0 ms y 0 requests adicionales |
| Heap antes / tras INITIAL / tras DETAIL | 3.213.230 / 3.689.931 / 4.109.506 B |

El lookup devolvió `egif-record:2013260001 → ordinal 0`; los filtros probaron
un municipio resuelto y un registro con municipio `null`. La comparación sobre
702 filas fue 0,1 ms columnar frente a 0,8 ms para materializar y filtrar
objetos. Son resultados de localhost/headless, no un presupuesto de
producción.

El smoke se validó también con `--check`. Las pruebas específicas del harness
comprueban los diez escenarios A–J, el plan desktop/móvil/frío/caliente y el
contrato de `results.json` usado por `--resume`/`--check`.

## Ejecución completa por terminal

Desde la raíz del repositorio:

```bash
python3 benchmarks/es4b5c/run.py \
  --all --desktop --mobile --cold --warm --resume \
  --output benchmarks/es4b5c/results.json
```

Validación posterior sin abrir Chromium:

```bash
python3 benchmarks/es4b5c/run.py \
  --all --desktop --mobile --cold --warm --check \
  --output benchmarks/es4b5c/results.json
```

La ejecución completa son 40 resultados medidos: 10 escenarios × 2 viewports
× 2 estados de caché. Cada estado `warm` realiza además un pase de calentamiento
descartado. En una máquina comparable al smoke, prever aproximadamente
10–30 minutos; Galicia/España, el rendimiento del disco y el arranque de
Chromium pueden aumentar ese tiempo. `--resume` conserva resultados completos
con el mismo SHA-256 del manifest y reintenta solo los faltantes/fallidos.

## Límites conocidos

- El servidor local no comprime HTTP, no tiene TLS ni reproduce CDN/GitHub
  Pages. Por eso se guardan tanto el cuerpo raw local como el gzip calculado
  por el manifest.
- El viewport móvil es 390×844, pero no simula CPU, red ni agente de usuario
  de un teléfono.
- `usedJSHeapSize` es una métrica específica de Chromium; queda marcada como
  no disponible si desaparece.
- La caché caliente no es una medición de caché de CDN: representa una segunda
  lectura con cache HTTP en un perfil Chromium local recién creado.
- ES-4B5C1 no decide arquitectura, no optimiza `record_id` y no ejecuta la
  batería completa. Esos resultados serán el input de ES-4B5C2.
