# ES-4POST2C — Popup humano directo sobre el mapa

## ¿Puede una persona pulsar un incendio y entender inmediatamente qué es?

Sí. Un click o tap sobre un perímetro visible abre ahora una burbuja compacta
anclada al punto real del mapa. Muestra datos humanos disponibles de esa
fuente y ofrece **Ver detalles** para reutilizar la ficha nacional completa.
No se ha creado un incendio canónico ni se han fusionado fuentes.

```text
DIRECT_CLICK = PARITY
BASIC_POPUP = PARITY
HUMAN_FIELD_AVAILABILITY = PARITY
MULTI_HIT_EXPLORATION = PARITY
MOBILE_POPUP = PARITY
MAP_FIRST_CLICK_DISCOVERY = PASS
MAP_EXPLORATION_PARITY = READY_FOR_FINAL_ACCEPTANCE
PRODUCTION_PATCH_BUNDLE = POST2A_POST2B_POST2C
PRODUCTION_STATUS = LIVE_PRE_POST2A
RELEASE_TAG_STATUS = HOLD
NEXT_PHASE = ES-4POST2D_MAP_EXPLORATION_FINAL_ACCEPTANCE
```

No se hizo push, despliegue, tag, cambio de datos, rebuild de PMTiles ni
cambio del formato `es4c-state-v1` o del permalink legado `#v=1`.

## Referencia y flujo nuevo

En el ancla GVA histórica
`f7a3532f633a247f33dee3ebba9fbcc316c0e534`, el flujo era:

```text
click de capa Leaflet → selectEntity → openSelectionPopup(latlng) → detailsHtml
```

Su valor a recuperar era la inmediatez. El nacional anterior seleccionaba una
geometría y llevaba la lectura a la ficha lateral/inferior. El nuevo flujo es:

```text
un click MapLibre
→ queryRenderedFeatures sobre fills y outlines visibles
→ deduplicación source_id + geometry_id
→ popup directo, o selector si hay varios
→ selección exacta de la geometría
→ “Ver detalles” reutiliza la ficha ya existente
```

La burbuja usa `event.lngLat`; no calcula ni usa centroides. Se construye con
nodos DOM y `textContent`, por lo que los campos de procedencia no se
interpolan como HTML. Se incorporó el CSS mínimo de `maplibregl-popup` en el
artefacto autocontenido: sin él el DOM y el estado existían, pero la burbuja
no se veía. Las tres capturas finales verifican la presentación real.

## Campos por fuente

| Fuente | Popup inmediato | No se afirma ni inventa |
| --- | --- | --- |
| ICV | Fecha, paraje cuando existe, municipio, provincia, superficie forestal declarada, causa y GIF cuando el criterio documentado ICV (≥500 ha) aplica. Etiqueta `ICV · Generalitat Valenciana`. | No se muestra ningún identificador técnico. |
| ESFire30 | Año, territorio consultado, `Perímetro Landsat`, `ESFire30` y una nota breve de no oficialidad. | No causa, GIF, superficie mapeada, incendio administrativo ni perímetro oficial: esos datos no están disponibles con seguridad en la tesela. |
| EFFIS | Fecha, municipio/provincia cuando constan, territorio, superficie y `EFFIS · Copernicus`. | No se presenta como dato definitivo: «Dato satelital provisional». |
| EGIF | Ninguno: no tiene geometría individual para un popup cartográfico. | No se fabrica una geometría ni un popup falso. |

El ICV toma los campos básicos de `latestIcvResult.fires_by_id`, ya cargado en
memoria junto a la geometría. Abrir la burbuja no realiza fetch ni DETAIL. La
ficha completa, incluida su información técnica, sigue siendo lazy y sólo se
activa mediante **Ver detalles**.

## Selección, solapes y estado

- Abrir una burbuja conserva el fill temporal y añade el outline de selección
  existente.
- Cerrar con el botón, Escape o click en un punto vacío cierra sólo la
  burbuja; una selección válida permanece. Un nuevo hit sustituye la burbuja
  anterior.
- Pan y zoom no crean ni cierran una burbuja válida; MapLibre conserva su
  ancla geográfica.
- Se consultan fill y outline de ICV, ESFire30 y EFFIS. Se elimina únicamente
  el duplicado fill/outline de una misma `source_id + geometry_id`.
- Si hay varias candidatas se muestra «N perímetros en este punto», ordenadas
  de año más reciente a más antiguo. Los empates conservan el orden del
  renderer; no se ordenan por ID ni se inventa un perímetro principal.
- Un solape real de 1995 produjo dos candidatas: ICV y ESFire30. Ambas se
  muestran separadas con su fuente; no se deduce que sean el mismo incendio.
- El hit-test usa solamente `queryRenderedFeatures`: una geometría eliminada
  por un filtro activo no es pulsable. Cambiar filtros, periodo, territorio o
  visibilidad cierra el popup antes de que el reducer y los loaders validen la
  selección. Esto evita un popup stale.

El popup visual no se serializa. Las selecciones existentes continúan en
`es4c-state-v1`; las rutas nativa y `#v=1` permanecen sin cambios.

## Evidencia dirigida

La pasada de Chromium construyó sólo el frontend y enlazó assets ya aceptados
en modo lectura. El harness utiliza un `Point` real de MapLibre y confirma el
pixel mediante `queryRenderedFeatures`; no usa una lista sintética para el
hit-test.

| Caso | Resultado |
| --- | --- |
| ICV GVA 1995 | Hit único real; popup ICV inmediato con fecha, municipio, superficie y causa. Diagnóstico handler→popup: 104,43 ms. |
| ICV recuperado 2016 | `gva:pif-cv:2016AL0074`, geometría `gva:geometry:2016:24:11828`; popup idéntico, 106,42 ms. |
| `2024AL0005` | Un record y dos geometrías. Se pulsaron y seleccionaron individualmente `…13587` y `…13606`, sin sustituir una por la otra. |
| ESFire30 1995 | Hit único real; `Perímetro Landsat`, año y territorio, 137,76 ms; sin afirmaciones administrativas. |
| ICV + ESFire30 | Hit real con 2 fuentes; selector humano de dos candidatas, 8,21 ms hasta selector. |
| EFFIS 2025 | Hit único real con fecha, lugar, superficie y nota provisional, 131,97 ms. Ocultar de forma simulada la superficie DETAIL no cerró el popup. |
| Cierre | Popup cerrado; la selección ICV siguió vigente. |
| Móvil 390×844 | Popup compacto y desplazable sobre el mapa, sin forzar la ficha como bottom sheet; 66,71 ms. |

Las cifras son diagnóstico local de handler a popup visible, no un benchmark.
No hubo errores no intencionados de navegador. La leyenda y el fill temporal
de POST2B siguen activos bajo el popup.

Capturas limitadas:

- [Popup ICV de escritorio](data/audit/product/es4post2c_direct_human_popup/desktop-icv-popup.png)
- [Selector real ICV–ESFire30](data/audit/product/es4post2c_direct_human_popup/desktop-multi-hit.png)
- [Popup ICV móvil](data/audit/product/es4post2c_direct_human_popup/mobile-icv-popup.png)

## Validación focalizada

Pasaron 30 tests específicos, sin suite completa, más el adaptador legado
ejecutado directamente con el cargador ESM disponible:

```text
tests/test_es4post2c_direct_human_popup.py                 7 PASS
tests/test_es4post2a_icv_geometry_completeness.py          5 PASS
tests/test_es4post2b_temporal_encoding_and_overlap.py      7 PASS
tests/test_es4c1c2_state_serialization.py                  2 PASS
tests/test_es4d3c_gva_permalink_compatibility.py           4 PASS
tests/test_es4e3c1_safe_filters_human_details.py           5 PASS
tests/gva_permalink_v1_adapter.mjs                          PASS
scripts/audit/product/es4post2c_direct_human_popup.py --check  PASS
```

Los tests cubren modelos humanos, campos vacíos, deduplicación y orden de
solapes, una única ruta de click, close/empty-click, reutilización de ficha,
CSS visible del popup, construcción del frontend e invalidación de selección
ICV por periodo, territorio y toggle. POST2A mantiene **13.738 records /
13.739 geometrías**, incluidas 341/346/375/272 en 2016–2019. POST2B mantiene
la paleta temporal, la leyenda y la legibilidad de solapes.

## Decisión

La regresión de exploración primaria queda reparada localmente. El bundle de
un futuro parche de producción debe incluir conjuntamente **POST2A + POST2B +
POST2C**, pero no se despliega aquí. La siguiente fase exacta es
`ES-4POST2D_MAP_EXPLORATION_FINAL_ACCEPTANCE`; debe validar el conjunto antes
de levantar el `HOLD` del tag o tocar producción.
