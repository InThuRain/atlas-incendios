# ES-4C3C — Acceptance fixes

## Alcance

Corrección acotada de los dos hallazgos MAJOR de ES-4C3B en el runtime aislado
`prototypes/es4c/`. No se modificaron datasets, relaciones espaciales,
PMTiles, producción ni hosting.

## BUG-01 — transición municipal sin geometría disponible

### Causa raíz

`setMunicipalityScope` aplicaba `set_municipality` al estado central antes de
cargar y validar el shard GeoJSON BDLJE del padre. Un 503 dejaba
`municipality_id` confirmado sin límite municipal actual.

### Corrección

La entrada en municipio es transaccional:

1. valida catálogo, municipio y padres ES-2;
2. confirma primero el padre válido (provincia o ciudad autónoma);
3. carga el shard BDLJE y comprueba que contiene el `municipality_id`;
4. sólo entonces confirma el scope municipal y su highlight.

Si el shard falla, el estado final queda en el padre, con
`municipality_id = null`, error municipal aislado y EGIF/ESFire30 del padre
operativos. Selector y clic de capa usan la misma función. La URL municipal se
restaura primero en el padre; si falla el shard se conserva centro/zoom y el
hash se normaliza al estado padre mediante el mecanismo `replaceState` ya
existente. Un fallo no se cachea como asset válido, por lo que un reintento
posterior puede completar la transición.

### Regresión comprobada

- selector Elx con shard 503;
- clic Elx con shard 503;
- restore URL Elx con shard 503;
- 503 único y reintento correcto en la misma sesión;
- transición rápida Galicia → País Valencià → Alacant → Elx.

## BUG-02 — error PMTiles no propagado al estado de fuente

### Causa raíz

El listener de MapLibre guardaba `Bad response code: 503` únicamente en el
array diagnóstico `errors`. El ciclo de filtro ya había marcado ESFire30 como
`ready`, por lo que la interfaz podía comunicar cobertura disponible aunque el
source PMTiles no se hubiese servido.

### Corrección

Los errores de MapLibre atribuibles al source `esfire30` o al protocolo PMTiles
se propagan a `esfireTransportError`, `esfireTerritory.status = error` y
`sourceLoadState.esfire30 = error`. La selección de geometría se invalida sin
tocar EGIF. `error`, `no_coverage` y municipio con cero relaciones se mantienen
como estados distintos.

No existe promoción automática `error → ready` por `idle`. Una interacción que
solicite ESFire30 de nuevo (periodo, territorio o reactivación de fuente) es un
reintento explícito; si la lectura funciona, la fuente vuelve a `ready`.

### Regresión comprobada

- PMTiles 503 → ESFire30 `error`, sin crash global;
- EGIF sigue `ready` durante el 503;
- 503 único → reactivación explícita → `error → loading → ready`;
- Canarias sigue siendo `no_coverage`, no error.

## Reaceptación dirigida

El harness permanente
`tests/acceptance/es4c_national_prototype_acceptance.py` conservó los casos de
fallo y los hace pasar contra el contrato corregido. La salida local ignorada
`prototypes/es4c/c3c-acceptance-results.json` registra 13/13 escenarios PASS:

- seis regresiones de fallo/reintento (municipio y PMTiles);
- Elx normal;
- Canarias sin cobertura;
- Agost con cero relaciones municipales;
- transición stale Galicia → País Valencià → Alacant → Elx;
- back/forward de Elx;
- Cangas del Narcea;
- Elx en viewport móvil 390×844.

Además, 13 tests específicos de estado, serialización, carga municipal, índice
municipal y C3C pasan. No se repitió la matriz completa C3B ni benchmarks.

## Estado tras C3C

**LOCAL_ACCEPTANCE_STATUS = FUNCTIONALLY_ACCEPTED_LOCAL**.

No quedan bugs locales MUST_FIX conocidos en este prototipo. Esto no autoriza
una publicación nacional: el servidor local confirma HTTP 206 Range y ausencia
de descarga completa, pero no reproduce GitHub Pages/CDN ni una caché real.

## Gap list

| Categoría | Elemento |
| --- | --- |
| MUST_FIX_LOCAL | Ninguno conocido tras la reaceptación dirigida. |
| RELEASE_GATE | Validación HTTP Range y caché en hosting real. |
| SHOULD_FIX | QA de producción, migración y compatibilidad con el visor valenciano. |
| EXTERNAL_BLOCKER | Diccionario de causas MITECO; permiso de redistribución CCINIF. |
| OUT_OF_SCOPE | Municipios históricos; enlaces EGIF↔ESFire30; 71.490 `municipality_id` EGIF nulos. |

La siguiente fase es exclusivamente
**ES-4C3D_REAL_HOSTING_RANGE_VALIDATION**.
