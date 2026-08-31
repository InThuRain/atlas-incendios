# ES-4D1 — Diseño de migración del prototipo nacional a producción

## Estado y decisión

Clasificación: **`MIGRATION_DESIGN_READY_WITH_PARITY_GAPS`**.

La migración puede empezar como trabajo incremental, pero **no se recomienda
cambiar la raíz pública** hasta cerrar las paridades marcadas como
`MUST_HAVE`. Durante toda esa transición se conserva sin cambios la URL actual:

`https://inthurain.github.io/atlas-incendios/`

La estrategia recomendada es **B: una aplicación nacional nueva que reutiliza
los módulos validados de `prototypes/es4c/`, manteniendo intacto el visor
valenciano hasta una autorización explícita de cambio de raíz**. No es una
reescritura; separa el runtime nacional del shell diagnóstico y permite una
aceptación reversible.

## Inventario real actual

| Área | Implementación actual | Papel durante migración |
| --- | --- | --- |
| Visor público valenciano | `index.html`, `js/app.js`, `js/data-loader.js`, `js/url-state.js`, `css/app.css` | Se conserva en raíz durante la migración. |
| Datos públicos valencianos | `config/public-data-bundle.json`, `config/sources-gva.json`, `data/web/gva/` en bundle `public-data-v5` | Sigue siendo la fuente de producción del perfil valenciano. |
| Prototipo nacional | `prototypes/es4c/` con MapLibre, PMTiles, loaders EGIF y territorio | Base funcional que se extrae a módulos de producción. |
| Workflow Pages actual | `.github/workflows/pages.yml` | Publica solamente el perfil GVA desde un bundle verificado. |
| Staging Pages aislado | `.github/workflows/pages-staging.yml` en el repositorio de staging | Evidencia técnica C3D4; debe evolucionar a preview permanente, no sustituir producción. |
| Activo nacional PMTiles | local e ignorado: `data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles` | Se obtiene por workflow, se verifica y se copia al artifact Pages; no entra en Git. |
| Build público actual | `scripts/download_public_data_bundle.py`, `build_frontend_profile.py`, `build_public_site.py`, `validate_public_site.py` | Patrón reutilizable para un builder nacional separado. |
| Smokes actuales | `benchmarks/gva_frontend/`; `prototypes/es4c/run_smoke.py`; C3D3/C3D4 | Mantener los GVA y convertir los nacionales aceptados en gates del nuevo artifact. |

El workflow público actual es manual (`workflow_dispatch`), descarga y verifica
el bundle inmutable `public-data-v5`, compone exclusivamente las fuentes GVA
publicables (`egif`, `esfire30`, `icv`, `effis`) y valida el site antes de
`deploy-pages`. No contiene aún ningún asset nacional.

## Estrategias consideradas

| Estrategia | Ventaja | Riesgo | Decisión |
| --- | --- | --- | --- |
| A. Convertir el prototipo y mover GVA temporalmente | Menos estructura inicial | Rompe la continuidad de la raíz, URLs y UX actual; mezcla aceptación nacional con una migración de datos GVA | No recomendada. |
| **B. Nueva aplicación nacional reutilizando ES-4C** | Preserva el visor GVA, permite staging y rollback por artifact; máxima reutilización del runtime probado | Requiere un build/config nacional y cerrar la paridad de fuentes GVA antes de un posible switch de raíz | **Recomendada.** |
| C. Evolucionar gradualmente `js/app.js` actual | Mantiene una sola superficie temporalmente | Acopla Leaflet/GVA con MapLibre/PMTiles nacional y aumenta el riesgo de regresión del producto publicado | No recomendada como primera migración. |

Ruta temporal recomendada:

1. La raíz continúa siendo el Atlas valenciano actual.
2. Un futuro artifact nacional se prueba en Pages staging permanente y, una vez
   aceptado, puede exponerse de forma explícita en `/national/` sin cambiar la
   raíz.
3. El cambio de raíz solo se estudia después de paridad funcional, compatibilidad
   de enlaces y una autorización de release separada.
4. Si hay cambio de raíz, la detección del hash público GVA `#v=1…` debe cargar
   el perfil/compatibility adapter valenciano sin reinterpretar ese hash como
   estado nacional.

## Código del prototipo: destino por componente

| Componente de `prototypes/es4c/` | Clasificación | Decisión de producción |
| --- | --- | --- |
| `runtime_state.mjs` | `PROMOTE_AS_IS` | Mantener invariantes y coberturas explícitas; moverlo a módulo state. |
| `state_serialization.mjs` | `PROMOTE_WITH_CLEANUP` | Mantener `es4c-state-v1`, extraer configuración y tests; no cambiar versión por estética. |
| `egif_initial_loader.mjs` | `PROMOTE_AS_IS` | Mantener manifest, CCAA×bloque, columnas, caché y cancelación. |
| `egif_detail_loader.mjs` | `PROMOTE_AS_IS` | Mantener lookup `record_id → ordinal`, DETAIL lazy y cache por asset. |
| `territory_catalog.mjs`, `province_catalog.mjs` | `PROMOTE_WITH_CLEANUP` | Reemplazar los catálogos inline por catálogo/version manifest publicado. |
| `territory_layer.mjs`, `province_layer.mjs`, `municipality_layer.mjs` | `PROMOTE_WITH_CLEANUP` | Conservar click/highlight/bounds; recibir rutas y atribución de config única. |
| `municipality_loader.mjs` | `PROMOTE_AS_IS` | Catálogo lazy + shard 0 m por provincia/ciudad, cache por asset. |
| `municipality_esfire_index.mjs` | `PROMOTE_AS_IS` | Conservar índice inverso por padre provincial; no crear slots municipales PMTiles. |
| `esfire30_territory_index.mjs` | `DEV_ONLY` | El índice externo CCAA/provincia queda para auditoría/inspección: el filtro cartográfico definitivo usa slots MVT. |
| `app.js` | `PROMOTE_WITH_CLEANUP` | Separar bootstrap, configuración de assets, mapa, UI y diagnostics; no reescribir filtros probados. |
| `index.html`, `styles.css` | `PROMOTE_WITH_CLEANUP` | Sustituir rótulos y layout experimental; mantener controles y semántica útiles. |
| Import del protocolo PMTiles y vendor local ES-3 | `REPLACE_WITH_PRODUCTION_CONFIG` | El manifest fija versión/origen del vendor y el builder lo incluye y verifica; no depende de una ruta diagnóstica de `data/derived`. |
| `run_smoke.py` | `TEST_ONLY` | Convertir sus recorridos aceptados en smoke de artifact/staging. |
| `run_territory_pmtiles_sample_smoke.py`, `territory_pmtiles_sample.*` | `DEV_ONLY` | Mantener para diagnóstico del builder, fuera del artifact público. |
| `c*.json`, `smoke-results.json` | `TEST_ONLY` | Evidencia histórica/local; no publicar. |
| `pmtiles_url`, `pmtiles_telemetry`, `browser_range_fetch` query params C3D | `REMOVE_BEFORE_PRODUCTION` | Eran overrides e instrumentación del harness de hosting; no pertenecen al runtime. |
| `ARCHIVE_PATH`, `EGIF_MANIFEST_URL`, roots BDLJE hardcoded | `REPLACE_WITH_PRODUCTION_CONFIG` | Resolverlos únicamente mediante manifest/config nacional versionado. |
| `#debug-output`, selector por `record_id` y resumen técnico | `PROMOTE_WITH_CLEANUP` | Retener solo el diagnóstico útil tras revisión de UX; no exponer dumps ni telemetría de smoke. |

## Arquitectura objetivo sin reescritura

La estructura exacta se decide al extraer el artifact, pero las
responsabilidades deben quedar equivalentes a:

```text
national/
  index.html                 shell nacional
  app/                       bootstrap y composición
  state/                     reducer, cobertura, serializer es4c-state-v1
  map/                       MapLibre, PMTiles, filtros y selección
  territories/               CCAA, provincia, municipio, bounds/capas
  sources/
    egif/                    INITIAL, DETAIL, lista/ficha
    esfire30/                protocolo, filtros MVT, índice municipal
    gva/                     adaptadores ICV/EFFIS cuando se implemente paridad
  ui/                        controles, estado de fuentes y atribuciones
  config/                    manifest nacional de runtime
```

No se introduce framework. El shell de producción solo recibe una
configuración de runtime; los loaders no conocen el host ni URLs de release.

### Configuración única de assets

El futuro `national-runtime-manifest.json` debe ser la única autoridad para
rutas, versión, bytes, SHA-256, source/coverage, atribución y política de
carga. El runtime debe resolver rutas relativas al manifest o a un
`asset_base_url` explícito. Quedan prohibidas URLs host-specific dispersas en
JS.

Para Pages inicial, el PMTiles debe publicarse con key inmutable, por ejemplo:

```text
data/esfire30/v1/3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe/
  esfire30-national-fidelity-territories.pmtiles
```

El manifest referenciará ese path y declarará:

- bytes `63052056`;
- SHA-256 `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`;
- formato `PMTiles`, layer `esfire30`;
- slots `ccaa_1..3` y `prov_1..3`;
- semántica: intersección de área positiva, sin territorio principal.

El PMTiles nunca se añade al historial Git. El workflow descarga el origen
versionado, valida tamaño/SHA, lo copia al artifact, genera/verifica el
manifest y ejecuta un smoke Range/browser sobre el endpoint de staging.

## Inventario de assets para un artifact nacional

| Asset | Fuente / versión actual | Tamaño conocido | Política de carga | Estado de producción |
| --- | --- | --- | --- | --- |
| ESFire30 PMTiles territorial | ESFire30 v1, manifest ES-4C2B2B1 | 63.052.056 B | PMTiles por HTTP Range; España sin filtro, CCAA `ccaa_*`, provincia `prov_*` | Candidato validado; publicar versionado por workflow. |
| Manifest EGIF nacional | `2026-08-27`, 88 assets, 646.887 partes | manifest 1.296.609 B local | España: solo resumen/manifest | Requiere perfil nacional publicable y manifest de runtime. |
| EGIF INITIAL | JSON columnar por CCAA×5 bloques | total 3.901.303 B gzip | CCAA: solo bloques intersectados; provincia/municipio: filtro columnar | Candidato validado; no carga nacional automática. |
| EGIF DETAIL | JSON columnar alineado por ordinal | total 10.437.489 B gzip | Solo selección de `record_id`; cache por asset | Candidato validado; lazy obligatorio. |
| Límites CCAA BDLJE | BDLJE actual, crosswalk ES-2 | 8.217.747 B raw / 2.674.954 B gzip | Al iniciar o bajo demanda según configuración | Requiere packaging versionado. |
| Límites provincia BDLJE | BDLJE actual, crosswalk ES-2 | 10.781.436 B raw / 3.569.068 B gzip | CCAA/provincia | Requiere packaging versionado. |
| Catálogo municipal | snapshot `2026-08-29`, 8.132 municipios | 1.984.280 B raw / 327.282 B gzip | Lazy cuando entra a selección municipal | Requiere packaging versionado. |
| Shards municipales 0 m | BDLJE actual, 50 provincias + Ceuta/Melilla | 52 assets; 146.194.941 B raw / 46.664.000 B gzip; máximo Barcelona 3.334.456 B gzip | Un shard por provincia/ciudad bajo demanda | Requiere packaging versionado; no GeoJSON nacional. |
| Índice municipal ESFire30 | ES-4C2B3B1 | nacional 3.502.136 B raw / 423.526 B gzip; por padre 434.620 B gzip total | Solo índice del padre provincial | Requiere packaging versionado. |
| Índice CCAA/provincia ESFire30 | ES-4C2B2A | opcional: 616.317 B gzip reverse | Auditoría/desarrollo, no se carga en mapa | No publicar para filtro cartográfico. |
| Manifests/catálogos auxiliares | ES-2, BDLJE, EGIF y PMTiles | pequeños; con SHA por asset | Antes de cada loader | Parte obligatoria del runtime manifest. |

Los 83 perímetros ESFire30 sin relación municipal se conservan en España,
CCAA y provincia; no aparecen al seleccionar municipio y no reciben un
territorio inventado.

## Política funcional que se conserva

| Scope | EGIF | ESFire30 | Territorio municipal |
| --- | --- | --- | --- |
| España | Resumen del manifest, 0 INITIAL nacional | PMTiles Range, solo filtro temporal | 0 shards y 0 índices municipales |
| CCAA | INITIAL de CCAA×bloques | `ccaa_1..3` AND año | sin shard municipal |
| Provincia | Reutiliza INITIAL CCAA y filtra `province_id` | `prov_1..3` AND año | carga el shard padre si se necesita navegación municipal |
| Municipio | Reutiliza INITIAL y filtra `municipality_id` | lista del índice inverso del padre AND año | reutiliza el shard ya cargado |

`DETAIL` EGIF se mantiene perezoso. No hay enlace ni fusión automática entre
`record_id` y `geometry_id`.

## Semántica y coberturas que debe expresar la UI

| Elemento | Texto/contrato de producción |
| --- | --- |
| EGIF | “partes administrativos” / “partes EGIF enlazadas documentalmente cuando el municipio es resoluble”. |
| ESFire30 | “perímetros derivados de teledetección Landsat”; no cartografía oficial ni parte EGIF. |
| Filtro ESFire30 territorial | “perímetros que intersectan el territorio seleccionado”. |
| Municipio | “Límite administrativo actual BDLJE”; no representa necesariamente la división histórica. |
| Métricas | No sumar EGIF y ESFire30 bajo “incendios” ni presentarlos como identidades confirmadas. |

Coberturas nacionales: EGIF `1968–2023`; ESFire30 `1985–2021`. El rango
solicitado se conserva y cada fuente muestra su intersección o “sin cobertura”,
nunca un falso “0 incendios”. Illes Balears, Canarias, Ceuta y Melilla deben
expresar “sin cobertura ESFire30”; Agost ejemplifica el caso distinto de
cobertura ESFire30 con cero relaciones municipales.

### Fuentes valencianas que no se pueden degradar

El perfil público vigente suma capacidades que ES-4C aún no contiene:

| Fuente | Cobertura pública actual | Papel antes de un cambio de raíz |
| --- | --- | --- |
| ICV | 1993–2024, perímetros oficiales consolidados de la Comunitat Valenciana | `MUST_HAVE`: preservar su visualización, ficha, atribución y separación semántica. El nacional no lo reemplaza. |
| EFFIS | 2025–2026, perímetros satelitales provisionales de la Comunitat Valenciana | `MUST_HAVE`: mantenerlo como fuente separada o conservar el perfil GVA compatible; no sustituirlo por EGIF/ESFire30. |
| EGIF GVA actual | 1968–1992, registros administrativos | El nacional amplía la cobertura EGIF, pero debe conservar semántica y URLs GVA. |
| ESFire30 GVA actual | 1985–1992, GeoJSON LOD regional/local | El PMTiles nacional puede coexistir, pero no convierte ESFire30 en perímetro oficial ni fusiona fuentes. |
| SIGIF / CCINIF / causas canónicas | SIGIF no publicable; CCINIF pendiente de permiso; diccionario de causas pendiente de MITECO | Fuera del runtime inicial, con ausencia/pending explícitos. |

ICV y EFFIS son necesarios antes de cambiar la raíz porque ya están publicados.
No son necesarios para extraer, probar o publicar un preview nacional aislado.

## Estado URL y compatibilidad

El permalink público actual usa `#v=1` y contiene mapa, zoom, periodo,
fuentes, provincia, municipio, causa, mínimo de superficie, GIF, `entity` y
`geometry`. El hash nacional `es4c-state-v1` serializa mapa, tiempo,
territorio ES-2 hasta municipio, visibilidad EGIF/ESFire30 y ambas selecciones.
Son formatos distintos e incompatibles por diseño.

Decisión de compatibilidad: **B — dos formatos explícitos, sin conversión
silenciosa**.

- Mientras la raíz siga GVA, sus URLs continúan funcionando exactamente igual.
- En un futuro `/national/`, se retiene `es4c-state-v1` estable.
- Antes de cualquier switch de raíz, un adapter debe reconocer `#v=1` y cargar
  el perfil/compatibility path valenciano, conservando el significado de todos
  los campos; un hash nacional no debe interpretar `entity` GVA como
  `record_id` EGIF nacional ni viceversa.
- El smoke futuro debe cubrir enlace GVA antiguo, hash GVA actual, URL nacional
  CCAA/provincia/municipio, ambas selecciones y hash inválido.

## Workflow, staging, release y rollback propuestos

El workflow nacional futuro debe tener un job separado del workflow GVA actual:

```text
checkout ref inmutable
→ tests específicos de runtime/config
→ descargar activos versionados
→ comprobar bytes y SHA-256
→ construir artifact nacional
→ comprobar tamaño del artifact y manifest
→ desplegar staging Pages
→ acceptance: Range, Chromium desktop, 390×844, URLs y fuentes
→ autorización explícita
→ deploy producción
→ smoke post-deploy
```

No se fija un umbral interno inventado para Pages: se registra tamaño del
artifact y se alerta/revisa frente al límite documentado de Pages antes de
autorizar la release. El gate PMTiles exige `206`, `Content-Range` coherente,
ninguna GET funcional de 63 MB con `200`, bytes/SHA correctos y MapLibre ready.

Mantener un Pages staging permanente es recomendado. R2 `r2.dev` queda como
staging técnico/evidencia hasta revisión de retención; no es producción. La
observabilidad mínima posterior conserva Cloudflare Web Analytics existente y
añade, sin nuevo servicio, contadores de fallos de carga/range y tiempos de
fuentes si la política de privacidad lo permite. No se cambia ahora el beacon
actual.

Rollback propuesto: cada release conserva commit, manifest, checksums,
workflow run y versión de asset. El rollback despliega el artifact anterior
completo; no apunta un manifest existente a un asset mutable. La raíz GVA se
mantiene como rollback funcional hasta que una fase posterior valide su
adaptador nacional.

## Paridad, limpieza y gates

### MUST_HAVE antes de cambiar la raíz

1. Shell nacional de producción sin overrides/telemetría C3D ni controles
   técnicos expuestos.
2. Manifest nacional único y asset pipeline SHA-gated para todos los assets.
3. Preservación real de ICV y EFFIS GVA, sus atribuciones y sus URLs `#v=1`.
4. Matriz de semántica/cobertura/atribución visible para EGIF, ESFire30, ICV,
   EFFIS y BDLJE.
5. Acceptance staging: desktop, viewport 390×844, Range, no full download,
   restauración URL, error isolation y rollback ensayado.
6. Autorización explícita de cambio de raíz posterior a una aceptación de
   producción independiente.

### SHOULD_HAVE

- Homogeneizar el panel compacto de fuentes, lista/ficha y controles
  territoriales; no requiere un rediseño visual final.
- Mantener filtros GVA de causa, superficie mínima, GIF e histograma donde
  aplique, o explicar el perfil/limitación de cada fuente.
- Prueba en teléfono físico además del viewport 390×844.
- Revisión básica de accesibilidad (foco, etiquetas, contraste y teclado), sin
  declarar todavía una auditoría WCAG completa.

### CAN_WAIT / fuera de scope inicial

- Política avanzada de eviction de caché.
- Municipios históricos, inferencia de los 71.490 `municipality_id = null`,
  relación EGIF↔ESFire30 e identidad de episodio.
- Ontología canónica de causas EGIF (bloque externo MITECO).
- CCINIF (permiso/licencia pendiente).
- Refactor visual completo, frontend framework y servicios de observabilidad
  nuevos.

### Limpieza obligatoria del artifact nacional

- eliminar overrides de endpoint, fault injection y telemetría C3D;
- no incluir harnesses, fixtures, resultados de smoke, `.spool`, JSONL de
  auditoría ni índices externos CCAA/provincia no usados;
- no publicar dumps de `#debug-output`, métricas de benchmark ni búsqueda
  técnica por IDs como interfaz final;
- conservar solo diagnósticos que aporten error aislado y soporte operativo.

### Gates de release

| Gate | Condición |
| --- | --- |
| 1. Arquitectura/paridad | Invariantes, matriz de fuentes y `MUST_HAVE` revisados. |
| 2. Frontend de producción | Sin dev overrides; config única; limpieza auditada. |
| 3. Staging | Artifact inmutable desplegado separadamente, aceptación aprobada. |
| 4. Assets | Manifests, bytes, SHA y paths versionados válidos. |
| 5. Range/browser | PMTiles `206`, slices correctos, MapLibre, desktop/móvil y sin full download. |
| 6. URLs | `#v=1`, `es4c-state-v1`, enlaces inválidos y restore validados. |
| 7. Rollback | Artifact/commit previo identificado y rollback ensayado. |
| 8. Switch | Autorización explícita; ningún cambio automático desde staging. |

## Secuencia recomendada posterior (no iniciada)

1. **ES-4D2 — Extracción del runtime nacional de producción**: crear shell,
   manifest único y builder/artifact aislado, sin tocar raíz ni incorporar
   nuevas fuentes.
2. **ES-4D3 — Paridad valenciana y compatibilidad pública**: incorporar o
   adaptar ICV/EFFIS, atribuciones y compatibilidad `#v=1`; no switch.
3. **ES-4D4 — Staging nacional permanente y aceptación de artifact**: desplegar
   preview, Range/browser/URLs/rollback; sin producción.
4. **ES-4D5 — Decisión explícita de cambio de raíz**: solo si los gates pasan;
   puede decidir mantener coexistencia.

## Gap list final

| Estado | Elementos |
| --- | --- |
| READY | PMTiles territorial, filtros CCAA/provincia/municipio, EGIF INITIAL/DETAIL lazy, límites BDLJE actuales, serialización nacional, Range same-origin probado, hosting Pages inicial decidido. |
| NEEDS_WORK | Shell/configuración de producción, artifact nacional, UX limpia, paridad ICV/EFFIS, adapter `#v=1`, acceptance staging/rollback y accesibilidad básica. |
| BLOCKED_EXTERNAL | Diccionario oficial de causas MITECO/ADCIF; permiso/atribución de redistribución CCINIF. |
| OUT_OF_SCOPE | Municipio histórico, relaciones EGIF↔ESFire30, inferencia de `municipality_id` nulos, fusión de fuentes, rediseño visual final y publicación en esta fase. |

La ausencia de causas canónicas, CCINIF, municipios históricos o relaciones de
identidad **no bloquea** un preview nacional inicial si se mantienen fuera del
runtime y se comunica su ausencia. La falta de paridad ICV/EFFIS y de
compatibilidad del permalink GVA **sí bloquea** reemplazar la raíz pública.
