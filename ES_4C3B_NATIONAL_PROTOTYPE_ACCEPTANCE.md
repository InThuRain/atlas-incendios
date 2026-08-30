# ES-4C3B — Aceptación funcional del prototipo nacional

## Alcance y entorno

QA del runtime aislado `prototypes/es4c/`; no se cambió su comportamiento ni
se regeneraron assets. Chromium local (`/usr/bin/google-chrome`), servidor
HTTP Range local y viewport desktop 1280×800 / móvil emulado 390×844. Los
fallos 503 se inyectan exclusivamente en el harness por ruta, sin alterar
ficheros reales. Range local no equivale a hosting real.

## Matriz de aceptación

| Scenario | Expected | Actual | PASS/FAIL | Evidence | Severity | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| clean_spain | España limpia, 0 INITIAL/municipal/index | Correcto | PASS | harness | — | PMTiles Range, sin descarga completa |
| spain_1975 | EGIF; ESFire30 fuera de cobertura | Correcto | PASS | harness | — | No se presenta como cero |
| elx_end_to_end | 49 partes, 6 IDs, doble selección/restore | Correcto | PASS | harness | — | BDLJE actual explícito |
| galicia_ourense | slots CCAA/prov y shard municipal | Correcto | PASS | harness | — | No lista Galicia de 38.645 IDs |
| cangas | 2.610 IDs, selección estable | Correcto | PASS | harness | — | Sin hang/crash |
| agost_zero_relations | Cobertura, 0 relaciones municipales | Correcto | PASS | harness | — | No dice sin cobertura |
| canarias_no_coverage | Territorio/EGIF, sin ESFire30 | Correcto | PASS | harness | — | Sin “0 incendios” |
| ceuta_hierarchy | Ciudad autónoma → municipio | Correcto | PASS | harness | — | Sin provincia ficticia |
| multi_province / multi_ccaa | Feature en ambos territorios | Correcto | PASS | IDs 1985:268 / 1985:1037 | — | Sin territorio principal |
| selector_click | Estado equivalente | Correcto | PASS | harness | — | Ruta territorial común |
| legacy_url / invalid_hash | Restore v1 y fallback seguro | Correcto | PASS | harness | — | Compatibilidad C1C2 |
| stale_galicia_to_elx | Última transición gana | Correcto | PASS | harness | — | Galicia stale; Elx final |
| cache_municipal_parent | Reutiliza shard Asturias | Correcto | PASS | harness | — | Sin eviction requerida |
| detail_lazy | DETAIL solo al seleccionar y cache | Correcto | PASS | harness | — | INITIAL preservado |
| fault_egif_initial | EGIF error; mapa operativo | Correcto | PASS | 503 inyectado | — | Error aislado |
| fault_detail | Ficha error; INITIAL/mapa operativos | Correcto | PASS | 503 inyectado | — | Error localizado |
| fault_municipal_geojson | Error localizado sin colapso | Parcial | PASS con issue | 503 inyectado | MAJOR | BUG-01 |
| fault_municipal_index | EGIF/límite siguen; ESFire municipal error | Correcto | PASS | 503 inyectado | — | No cae a filtro provincial |
| fault_pmtiles | ESFire30 debe pasar a error | Sigue `ready` | FAIL | 503 inyectado | MAJOR | BUG-02 |
| mobile_elx / mobile_cangas | Controles críticos utilizables | Correcto | PASS | 390×844 | — | No prueba de teléfono físico |

## Bugs reales

### BUG-01 — Scope municipal aparente tras fallo del GeoJSON municipal

- **Severity:** MAJOR.
- **Reproduction:** seleccionar Elx con el shard `ES-PROV-03.geojson` en 503.
- **Expected:** error municipal localizado; el runtime no debe presentar que
  entró correctamente al municipio si no dispone de su geometría actual.
- **Actual:** `municipality` queda seleccionado y EGIF/índice municipal siguen
  operativos, pero la capa municipal no puede cargarse.
- **Affected scope:** navegación/fit/highlight municipal ante error de red.
- **Proposed fix:** definir estado municipal degradado o rechazar la transición
  visual hasta cargar el shard, conservando el error aislado.

### BUG-02 — Fallo PMTiles no se refleja como estado ESFire30 error

- **Severity:** MAJOR.
- **Reproduction:** responder 503 al PMTiles en scope España.
- **Expected:** mapa/territorio/EGIF permanecen operativos y ESFire30 muestra
  estado `error`.
- **Actual:** MapLibre registra `Bad response code: 503`, pero la UI/estado
  derivado conserva ESFire30 `ready`/cobertura disponible.
- **Affected scope:** aislamiento y comunicación de fallo de geometría.
- **Proposed fix:** conectar eventos de error del source PMTiles con el estado
  aislado ESFire30 y limpiar solo su selección.

No se hallaron BLOCKER, MINOR ni COSMETIC adicionales en la matriz ejecutada.

## Semántica y cobertura

EGIF conserva “partes administrativos”; ESFire30, “perímetros derivados de
teledetección Landsat”. No hay contador conjunto ni enlace implícito entre
`record_id` y `geometry_id`. Municipio significa límite BDLJE actual; EGIF es
enlace documental al municipio canónico cuando resoluble y ESFire30 es
intersección con ese límite actual. Las causas canónicas siguen bloqueadas por
el diccionario MITECO; CCINIF no se carga.

Canarias, Baleares, Ceuta y Melilla se tratan como **sin cobertura ESFire30**.
Agost es “cobertura con cero relaciones municipales”. Las 83 geometrías sin
municipio continúan sin asignación artificial.

## Estado, carga y red

El hash `es4c-state-v1`, URL antigua C1C2 y hash inválido restauran/fallan de
forma segura. La doble selección de Elx se restaura sin `fitBounds`; selección
EGIF y ESFire30 son independientes. El harness confirma Range 206 local,
ninguna descarga PMTiles completa, ningún INITIAL EGIF nacional automático,
ningún GeoJSON municipal nacional ni índice municipal nacional por defecto.

Back/forward, toggles y cambios temporales conservan las reglas ya cubiertas
por los tests/smokes C1C1/C1C2 y C3A; requieren revalidación tras resolver los
dos MAJOR. La aceptación no valida HTTP Range en hosting real: sigue siendo un
gap de release.

## Accesibilidad básica y móvil

Los controles principales usan `label`, `legend`, botones y regiones
`aria-live`; selector, breadcrumb, panel de fuentes, lista/ficha funcionan en
los smokes. No se hizo auditoría WCAG ni rediseño responsive.

## Release gap list

| Item | Category | Priority | Blocks release? | Owner/dependency | Recommended phase |
| --- | --- | --- | --- | --- |
| BUG-01 GeoJSON municipal degradado | MUST_FIX_BEFORE_NATIONAL_RELEASE | Alta | Sí | Runtime | ES-4C3C |
| BUG-02 estado error PMTiles | MUST_FIX_BEFORE_NATIONAL_RELEASE | Alta | Sí | Runtime | ES-4C3C |
| HTTP Range/caché en hosting real | MUST_FIX_BEFORE_NATIONAL_RELEASE | Alta | Sí | Hosting | fase posterior de hosting |
| QA producción, migración y compatibilidad GVA | SHOULD_FIX | Alta | Sí antes de publicar | Producto | ES-4D1 |
| Política de memoria/eviction | CAN_WAIT | Media | No | Runtime | posterior |
| Ontología causas MITECO | EXTERNAL_BLOCKER | Media | No para geometría | MITECO | externo |
| Licencia CCINIF | EXTERNAL_BLOCKER | Media | No para este runtime | CCINIF/MITECO | externo |
| Municipios históricos, EGIF↔ESFire30, 71.490 null | OUT_OF_SCOPE | — | No | investigación | fase futura |

## Decisión

**ACCEPTED_WITH_REQUIRED_FIXES**.

1. Recorrido nacional, territorio, cargas y semántica pasan la aceptación.
2. EGIF INITIAL/DETAIL y filtros ESFire30 funcionan de forma independiente.
3. El aislamiento EGIF, DETAIL e índice municipal funciona.
4. BUG-01 y BUG-02 impiden afirmar una degradación correcta ante fallos de
   geometría municipal/PMTiles.
5. HTTP Range solo está validado localmente.

No se debe iniciar ES-4D1 todavía. La siguiente fase recomendada es
**ES-4C3C_ACCEPTANCE_FIXES**, limitada a BUG-01 y BUG-02, seguida de
reaceptación dirigida.
