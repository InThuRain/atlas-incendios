# ES-4E3C2 — Destacados nacionales y pulido cartográfico

## Resultado

`HIGHLIGHTS_STATUS = PASS` y `PRODUCT_POLISH_STATUS = PASS`.

Los destacados recuperan una vía rápida de descubrimiento sin crear un ranking
entre fuentes: la lista acompaña la métrica activa del histograma, muestra como
máximo cinco elementos inicialmente y permite ampliar hasta diez. Cada ranking
declara fuente, métrica, orden y unidad. El click abre la ficha humana existente
y conserva las identidades y selecciones independientes.

El mapa gana costa, fondo terrestre, jerarquía de límites y nombre del ámbito
actual usando exclusivamente BDLJE ya aceptado y servido same-origin. Es una
mejora clara, pero no sustituye el contexto de un mapa base con topónimos
posicionados, red viaria o relieve. Por ello:

- `LOCAL_CONTEXT_SUFFICIENT = false`;
- `BASEMAP_STATUS = PENDING_USER_DECISION`;
- `ROADS = P1 / OPTIONAL`;
- `HISTOGRAM_BRUSH_STATUS = DEFERRED_P1`.

No se ha incorporado ni seleccionado ningún proveedor, descargado cartografía
externa, modificado staging/producción o alterado un contrato de datos.

## Contratos de destacados

| Fuente | Entidad ordenada | `METRIC_ID` | Orden | Unidad | Estado |
| --- | --- | --- | --- | --- | --- |
| EGIF | `source_record` administrativo | `egif_declared_forest_area_ha` | `reported_forest_area_ha DESC`, `record_id ASC` | ha | disponible |
| ICV | incendio documentado / `fire_id` | `icv_declared_forest_area_ha` | superficie forestal declarada DESC, `fire_id ASC` | ha | disponible en GVA |
| EFFIS | perímetro provisional | `effis_mapped_area_ha` | área cartografiada DESC, `geometry_id ASC` | ha | disponible en el snapshot integrado |
| ESFire30 | perímetro Landsat | — | — | — | `DEFERRED_NO_SAFE_RANKING_METRIC` |

El PMTiles ESFire30 conserva `geometry_id`, año y membresías territoriales, pero
no una magnitud individual documentada que el producto pueda presentar como
superficie segura. No se usa la superficie agregada territorial diferida ni se
calcula área desde el tile.

### EGIF

En CCAA, provincia y municipio, el top se calcula directamente sobre las
columnas INITIAL ya cargadas. Respeta año, territorio, superficie mínima y GIF
de EGIF. Los valores `null` se excluyen y nunca se transforman en cero; un cero
conocido sigue siendo un valor documentado.

España mantiene su política de cero INITIAL automático. Se añadió
`national-highlights-v1`, un derivado anual determinista de **343.708 B raw /
17.011 B gzip** más un manifest de 794 B. Conserva solo los diez candidatos
anuales generales y GIF necesarios para obtener un top 10 exacto de cualquier
rango, IDs territoriales y nombres mínimos de presentación. Fue generado desde
los 646.887 INITIAL EGIF aceptados; no contiene DETAIL, geometría, causas
normalizadas ni relaciones con otras fuentes.

La primera lectura nacional son dos requests y 344.502 B de JSON sin comprimir
en el servidor de smoke. Varias actualizaciones concurrentes comparten una
única promesa de carga, por lo que manifest y payload se solicitan una sola vez.
Solo tras un click explícito se carga el único INITIAL que contiene el registro
y su DETAIL correspondiente. La ficha se abre sin centrar el mapa ni inventar
un punto.

### ICV y EFFIS

ICV reutiliza los incendios ya cargados y deduplica por `fire_id`: un incendio
con más de un perímetro aparece una sola vez en el ranking de registros. Abrirlo
selecciona el registro, no una geometría arbitraria.

EFFIS reutiliza las features del snapshot filtrado. Las tarjetas y la ficha
dicen `provisional`, muestran el snapshot 19/08/2026 y ordenan solo por su área
cartografiada documentada. No se denominan incendios oficiales.

## Interacción con filtros, periodo y territorio

La fuente del bloque de destacados sigue la serie activa del histograma. No se
aplica un filtro de otra fuente. Los top de CCAA/provincia/municipio se obtienen
del subconjunto runtime exacto; el derivado nacional EGIF permite exactamente
los dos filtros EGIF aprobados. GVA 1995 con ICV ≥500 ha produjo un único
destacado, coherente con el resultado filtrado.

Las tarjetas son una lista semántica ordenada con botones reales, foco visible,
fecha, lugar, magnitud y fuente. No presentan IDs técnicos. `Ver más` pasa de
cinco a un máximo de diez y vuelve a contraer la lista.

## Auditoría del contexto cartográfico local

### Activos existentes

| Activo | Contenido | Raw | Gzip diagnóstico | Uso |
| --- | --- | ---: | ---: | --- |
| `es4c2a/ccaa.geojson` | 19 CCAA/ciudades autónomas BDLJE | 8.211.747 B | 2.661.897 B | tierra, costa, límites CCAA, selección y bounds |
| `es4c2a/provinces.geojson` | 50 provincias BDLJE | 10.781.436 B | 3.552.872 B | límites contextuales dentro de la CCAA y selección |
| shards municipales | 8.132 municipios actuales en 52 shards | 146.199.037 B totales | entrega lazy | límites solo tras entrar en provincia |
| catálogo ES-2 | nombres e IDs territoriales | 3.726.695 B | 155.435 B | selectores, breadcrumb y fichas |

Estos assets ya formaban parte de la arquitectura aceptada; el pulido no añade
un nuevo asset cartográfico ni carga 8.132 municipios en España. La geometría
CCAA se pinta bajo los incendios con un fondo pálido; los límites de CCAA,
provincia y municipio usan anchura dependiente del zoom y baja opacidad; el
territorio seleccionado permanece encima con mayor contraste. En los smokes la
capa CCAA quedó antes de ESFire30 y la selección después.

La línea exterior BDLJE proporciona costa e islas. El nombre completo del
ámbito aparece sobre el mapa y procede del breadcrumb/catálogo documentado.
No se encontraron label points o centroides oficiales ya aceptados para situar
topónimos en el mapa, ni una red viaria/relieve local. No se calcularon
centroides dudosos. El resultado es más legible, pero la orientación geográfica
para público general sigue por debajo del visor GVA: de ahí
`LOCAL_CONTEXT_SUFFICIENT = false`.

### Licencia y atribución local

BDLJE se conserva bajo CC BY 4.0 con la atribución aprobada:
**«Obra derivada de BDLJE CC-BY 4.0 ign.es»**. La línea compacta del mapa se
oculta en 390×844 para no tapar el contenido, pero la atribución completa sigue
disponible en Fuentes y metodología. Los perímetros continúan usando sus
atribuciones propias.

## Matriz de opciones de mapa base (sin decisión ni implementación)

| Opción | Licencia / atribución | Coste y límites | Dependencia, privacidad, cache/CORS | Offline / Pages e impacto estimado | Valoración |
| --- | --- | --- | --- | --- | --- |
| Protomaps basemap PMTiles autoalojado | datos OSM/ODbL como Produced Work; atribución OSM/Protomaps según estilo y assets | software abierto; coste operativo es almacenamiento/transferencia | sin tercero en runtime si es same-origin; control propio de cache y CORS | posible por extracto y `maxzoom`; tamaño España **no medido** y puede consumir de forma material el margen del artifact actual de ~501 MB; planeta z0–15 ronda 120 GB y hasta z6 ronda 60 MB | candidato preferente para medir si se priorizan privacidad y control, no aprobado aún |
| OpenFreeMap público | OpenStreetMap/OpenMapTiles; exige `OpenFreeMap © OpenMapTiles Data from OpenStreetMap` | instancia pública gratuita, declara sin límites, sin cuenta ni API key; no ofrece SLA | tercero externo/CDN; política declara logs anónimos y posible retención temporal de IP por seguridad; comprobar delivery real | cero asset grande en Pages; sin garantía operativa contractual; software/datos permiten autoalojar más adelante | mejor prueba externa de bajo coste, con riesgo de dependencia/no SLA |
| MapTiler Cloud | estilos/datos conforme a sus términos y atribución del mapa | Free: 5.000 sesiones y 100.000 requests/mes, solo no comercial/testing y pausa al límite; Flex: 30 USD/mes, 25.000 sesiones y 500.000 requests, con exceso facturable | tercero gestionado; API key pública restringible; CDN/CORS gestionados; requiere revisar privacidad y operación | impacto mínimo en artifact; dependencia, clave y coste crecen con uso | opción gestionada madura, no preferida sin decisión económica/privacidad |

Fuentes de la auditoría: documentación oficial de
Protomaps (`docs.protomaps.com/basemaps/downloads`, `/basemaps/maplibre` y
`/guide/security-privacy`), MapTiler (`maptiler.com/cloud/pricing`,
`docs.maptiler.com/cloud/api/authentication-key` y términos Cloud) y
OpenFreeMap (`openfreemap.org`, `/quick_start`, `/tos` y `/privacy`). Los
precios y límites son una fotografía de 02/09/2026 y deberán verificarse al
tomar la decisión.

No se incluye el raster estándar de `tile.openstreetmap.org`: su política no lo
convierte en un backend gratuito para una aplicación nacional. Tampoco se
reutiliza a ciegas el mapa base del visor valenciano.

## Mapa, leyenda y flujo de producto

- España muestra masa terrestre/costa y límites CCAA discretos; el filtro
  temporal y los perímetros siguen siendo protagonistas.
- Galicia y Ourense conservan el filtro territorial ya aprobado y reciben
  límites jerárquicos legibles, sin listas masivas CCAA/provincia.
- En GVA 1995 ICV y ESFire30 siguen diferenciándose por estilo, texto y
  leyenda; el contexto BDLJE queda detrás y la vista recomendada no cambia.
- Elx mantiene shard municipal lazy, límite actual, EFFIS provisional y ficha.
- Canarias conserva el límite administrativo aunque ESFire30 no tenga
  cobertura; el mapa base no se confunde con evidencia de incendios.
- La leyenda sigue mostrando solo fuentes visibles, distingue ICV oficial,
  ESFire30 Landsat y EFFIS provisional, y mantiene territorio/límites como
  contexto. Los toggles completos continúan en Fuentes y metodología.

En desktop el recorrido abrir → territorio/periodo → resumen → evolución →
filtro → destacado → ficha → mapa → compartir es posible sin conocer IDs ni
INITIAL/DETAIL. En móvil 390×844 el mapa sigue visible inmediatamente (354 px
de alto en el smoke), los destacados muestran de uno a cinco botones táctiles
y la ficha existente sigue utilizable.

## Rendimiento y validación dirigida

No se ejecutó benchmark ni suite completa. El contexto reutiliza assets ya
necesarios; no añade mapa base, requests externos ni shards municipales por
defecto. Para España, el único coste automático nuevo es el índice EGIF pequeño
de dos requests / 344.502 B raw (17.011 B gzip para el payload en hosting con
compresión). ICV y EFFIS añaden cero requests: ordenan datos ya cargados. DETAIL
sigue lazy.

Los heaps de los recorridos Chromium oscilaron aproximadamente entre 47 y
206 MB y se conservan solo como observación diagnóstica, no como comparación de
rendimiento. No hubo errores de bootstrap/runtime.

Pasaron:

- 7 aserciones JS de ranking, métrica, orden, null/zero y filtro GIF;
- 3 tests Python de derivado/check, ensamblado y contexto same-origin;
- build/check dirigido del frontend (31 ficheros, sin assets grandes);
- 10 smokes Chromium dirigidos: España y Galicia EGIF 1995; GVA ICV 1995/2024;
  GVA EFFIS 2026; Elx EFFIS 2025; ICV ≥500; Ourense; Canarias; móvil Elx;
- una revalidación final de España que confirmó un único fetch de manifest y
  payload, selección EGIF y DETAIL lazy.

Los smokes previos de permalink native/legacy/filtros/selección no se
repitieron. E3C2 no modifica serializer, schema de estado ni traducción legacy;
el build dirigido pasó y no se observó regresión.

## Comparación pre-E3D

| Criterio | GVA | D4B | E3A | E3B2 | E3C1 | E3C2 |
| --- | --- | --- | --- | --- | --- | --- |
| primera impresión | clara | técnica | humana | humana + resumen | explorable | explorable + descubrimiento |
| mapa/contexto | mapa base rico | escaso | escaso | escaso | escaso | BDLJE mejorado, aún incompleto |
| resumen/histograma | fuertes | débiles | estructura | tipados y útiles | exactos con filtros | sin cambio semántico |
| filtros | útiles | técnicos | secundarios | pendientes | seguros por fuente | integrados con destacados |
| destacados | sí | no | no | no | no | sí, tipados y máximos 5/10 |
| ficha | humana | técnica | jerarquizada | igual | humana por fuente | accesible desde destacado |
| claridad de fuentes | compacta | dominante/técnica | progresiva | progresiva | progresiva | progresiva + contrato de ranking |
| ruido técnico | bajo | alto | bajo | bajo | bajo | bajo |
| móvil | sencillo | funcional/técnico | mapa primero | métricas útiles | filtros/fichas | mapa + destacados compactos |
| flujo exploratorio | fuerte | débil | recuperado | mejorado | completo | completo salvo mapa base |

## Pendiente y decisión

Quedan abiertos el mapa base/topónimos, el brush temporal P1 y causas EGIF
pendientes de ontología. No son regresiones del motor. Destacados, selección,
filtros, fichas, resumen, histograma, leyenda y navegación forman ya una
experiencia coherente.

- `TECHNICAL_RUNTIME_REGRESSION = false`
- `PRODUCT_RELEASE_CANDIDATE = false`
- `D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`
- `NEXT_PHASE = ES-4E3C2_BASEMAP_DECISION`

La siguiente fase debe decidir explícitamente entre mantener el contexto BDLJE
como producto mínimo o autorizar una de las tres familias de mapa base, medir
su impacto real para España y fijar licencia, atribución, privacidad, coste y
operación. No debe iniciar todavía E3D ni incorporar un proveedor antes de esa
decisión.

## Comandos reproducibles ejecutados

```bash
python3 scripts/build_national_highlights.py --check
node --experimental-modules tests/es4e3c2_highlights_contract.mjs
python3 -m unittest tests.test_es4e3c2_highlights_map_polish -v
python3 scripts/build_national_frontend.py --output /tmp/es4e3c2-frontend
python3 scripts/build_national_frontend.py --output /tmp/es4e3c2-frontend --check
python3 benchmarks/es4e3c2/run_smoke.py --all --output /tmp/es4e3c2-smokes.json
python3 benchmarks/es4e3c2/run_smoke.py --check --output /tmp/es4e3c2-smokes.json
```
