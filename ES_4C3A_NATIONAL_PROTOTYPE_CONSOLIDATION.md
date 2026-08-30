# ES-4C3A — Consolidación funcional del prototipo nacional

## Alcance

`prototypes/es4c/` queda consolidado como laboratorio aislado del futuro
runtime nacional. No modifica el visor valenciano público, `public-data-v5`,
workflows, Pages ni releases. Reutiliza exclusivamente PMTiles ESFire30,
assets columnares EGIF, límites BDLJE actuales, catálogo/shards municipales e
índice municipal ya auditados.

## Estado canónico y navegación

La única fuente de verdad usa `runtime_state.mjs`:

```text
time: from, to
territory: territory_scope, autonomous_community_id, province_id, municipality_id
sources: esfire30_visible, egif_visible
selection: selected_geometry_id, selected_egif_record_id
map: center, zoom
```

Los invariantes son España sin descendientes; CCAA sin provincia/municipio;
provincia con CCAA padre; y municipio con sus padres ES-2. Ceuta y Melilla
pueden llegar al municipio desde su ciudad autónoma con `province_id=null`: no
se crea una provincia ficticia. Selector, clic en límite y breadcrumb usan las
mismas transiciones. Un cambio explícito de territorio aplica `fitBounds` al
límite administrativo actual; una restauración de URL conserva el `center` y
`zoom` serializados.

## Política de carga

| Ámbito | EGIF | ESFire30 | Municipios |
| --- | --- | --- | --- |
| España | Resumen de manifest; 0 INITIAL automático | PMTiles por HTTP Range; solo año | No catálogo, shard ni índice municipal |
| CCAA | INITIAL CCAA × bloques temporales | Slots MVT `ccaa_1..3` | No geometría municipal |
| Provincia | INITIAL CCAA en caché + filtro columnar `province_id` | Slots MVT `prov_1..3` | Catálogo/shard GeoJSON del padre bajo demanda |
| Municipio | Reutiliza INITIAL y filtra `municipality_id` | Lista `geometry_id` del índice por padre provincial, más año | Reutiliza catálogo y shard del padre |

Las cachés de sesión se mantienen por asset para INITIAL EGIF, DETAIL EGIF,
catálogo y shard municipal, e índice municipal ESFire30 por padre. Los loaders
usan generación/`AbortController`; un resultado stale no puede sobrescribir el
estado más reciente. El indicador compacto por subsistema (`idle`, `loading`,
`ready`, `error`) no se serializa ni mezcla fallos de fuentes independientes.

## Semántica, cobertura y selección

- **EGIF** son partes administrativos (1968–2023); en municipio, el filtro
  significa partes enlazadas documentalmente al municipio canónico actual
  cuando se resolvieron. `municipality_id=null` no se resuelve aquí.
- **ESFire30** son perímetros Landsat derivados de teledetección (1985–2021),
  no cartografía oficial ni partes EGIF. En CCAA/provincia/municipio muestra
  perímetros que intersectan el límite administrativo seleccionado.
- Los límites municipales BDLJE son actuales (snapshot 2026): no representan
  automáticamente límites municipales históricos.
- El intervalo general se conserva siempre; cada fuente aplica su propia
  intersección de cobertura. Ausencia de cobertura no equivale a cero partes ni
  a cero perímetros.
- Illes Balears, Canarias, Ceuta y Melilla se presentan como **sin cobertura
  ESFire30**. Agost es distinto: tiene cobertura ESFire30 pero ninguna
  geometría relacionada con su municipio actual.
- Las 83 geometrías ESFire30 sin relación municipal siguen visibles en España,
  CCAA y provincia; no se inventa un municipio para ellas.

`selected_geometry_id` y `selected_egif_record_id` son independientes. La
selección EGIF se invalida al cambiar su ámbito administrativo, periodo o
visibilidad; DETAIL sigue siendo lazy. La selección ESFire30 se invalida solo
si deja de cumplir visibilidad, periodo o filtro territorial efectivo. Ninguna
selección crea una relación EGIF ↔ ESFire30.

## Estado compartible

El hash `es4c-state-v1` sigue incluyendo mapa, tiempo, territorio hasta
municipio, toggles y ambas selecciones. Sigue siendo compatible con URLs
anteriores que no incluían provincia/municipio. Copy link, reload y
back/forward usan `replaceState`; esta serialización no toca el permalink v1
del visor público valenciano.

## Smokes ES-4C3A

Se ejecutaron smokes Chromium dirigidos, no una batería de benchmark:

- **Elx, 1993–2002:** carga su shard e índice padre (6 IDs), 49 partes EGIF
  activos; una selección EGIF y `esfire30:v1:1993:777` coexisten y restauran
  desde URL con DETAIL lazy.
- **Galicia → Ourense:** usa filtro MVT CCAA/provincia y después el índice
  municipal padre (152 IDs), sin lista Galicia de 38.645 IDs.
- **Cangas del Narcea:** conserva el shard Asturias y 2.610 IDs, sin hang ni
  crash; no implica que las features renderizadas de un viewport sean ese total.
- **Canarias → Las Palmas de Gran Canaria:** límite y EGIF operativos; el
  estado ESFire30 es `no_coverage`, no cero incendios.
- **Agost:** índice municipal con lista vacía y texto de cero perímetros para
  la cobertura disponible, distinto de falta de cobertura.
- **Cambio rápido Galicia → País Valencià → Alacant → Elx:** las dos primeras
  cargas terminan stale; el resultado final conserva Elx, INITIAL valenciano y
  el índice de `ES:PROV:03`.
- **390×844:** Elx mantiene navegación, selector y panel; Cangas permite mapa
  y selección geométrica. Es emulación de viewport, no prueba de teléfono ni
  red móvil real.

Las comprobaciones locales se guardan ignoradas bajo
`prototypes/es4c/c3a-*.json`. En los smokes de referencia se observaron, solo
como diagnóstico: Elx 0,88 MB Range acumulado/63,5 MB heap aproximado;
Ourense 7,31 MB/183,7 MB; Cangas 3,16 MB/132,4 MB; y Cangas móvil
3,18 MB/89,2 MB. Son observaciones de viewport/caché local, no presupuestos ni
benchmark comparativo.

## Validación

- `tests/test_es4c3a_national_prototype_consolidation.py`
- tests específicos existentes de estado, serializer, runtime municipal e
  índice municipal.
- Ocho smokes ES-4C3A anteriores.

## Gap list

### READY

- Runtime aislado con dos fuentes y coberturas explícitas.
- Territorio administrativo actual España → CCAA → provincia → municipio.
- PMTiles ESFire30 con filtro MVT CCAA/provincia e índice municipal por padre.
- EGIF INITIAL columnar y DETAIL lazy, selección independiente y estado URL.

### NEEDS_WORK

- Aceptación funcional completa del prototipo y definición del siguiente
  corte de producto.
- Prueba real de HTTP Range/caché en hosting antes de usar PMTiles en un
  despliegue.
- Diseño visual final, accesibilidad de producción y política de memoria.

### BLOCKED_EXTERNAL

- Diccionario oficial MITECO/EGIF para ontología nacional de causas.
- Permiso/atribución de redistribución de CCINIF.

### OUT_OF_SCOPE

- Relaciones EGIF ↔ ESFire30, identidades de episodio y municipios históricos.
- Resolver los 71.490 partes EGIF con municipio nulo.
- Nuevas fuentes, assets públicos, publicación o migración del visor
  valenciano.
