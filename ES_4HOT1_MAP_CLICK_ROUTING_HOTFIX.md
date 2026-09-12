# ES-4HOT1 — Prioridad del click sobre perímetros

**Causa exacta:** `COMPETING_CLICK_HANDLERS` +
`STATE_INVALIDATION_AFTER_FIRE_CLICK`. El listener global de incendios abre
correctamente el popup, pero los listeners administrativos delegados procesan
el mismo gesto. `set_province`/`set_municipality` invalidan entonces el popup.

**Antes:** click real sobre perímetro → selección/popup transitorios → cambio
de provincia o municipio → popup cerrado. Reproducido en producción en **7/7**
casos, incluidos las tres fuentes, provincia, solapes y tap móvil.

**Después, sólo local:** un árbitro decide el propietario del gesto. Un
perímetro visible consume el click, conserva el territorio y abre popup o
chooser; únicamente el fondo administrativo permite navegar. **10/10** casos
de click y **3/3** casos de ocultación/filtro/periodo pasan.

## Demostración y orden real

Se utilizó Chromium sobre la URL pública, con `Input.dispatchMouseEvent`
(movimiento, press, release) o `Input.dispatchTouchEvent` (start/end). El
punto procede de una consulta exacta a una feature pintada; `elementFromPoint`
confirma que no está tapado por un panel. No se invoca el helper de popup.

La traza de listeners preserva el orden y delega en sus funciones originales:

| Orden observado antes | Acción |
| --- | --- |
| 0: `handleMapPopupClick` | encuentra el incendio y abre popup; territorio intacto |
| 1: delegado CCAA | mismo padre: no cambia el ámbito |
| 2: delegado provincia | cambia provincia y cierra popup |
| 3: delegado municipio | cuando hay shard municipal, puede completar el descenso asíncrono |

El global se registra sincrónicamente. Los delegados se añaden después de
cargar CCAA, provincia y municipio. La traza demuestra, para ICV general y el
recuperado de 2016, `popup false → true → false`, con cambio territorial en
el delegado provincial. En provincia se observa la llegada al municipio.

Casos productivos: ICV 1995 con cursor pointer, `2016AL0074` general y en
Alacant, solape ICV/ESFire30, ESFire30, EFFIS y móvil 390×844. Cada fila del
agregado conserva punto, candidatos fuego/territorio, estado anterior y
posterior, selección, popup y secuencia de eventos.

### El caso aislado donde sobrevivía el popup

No se ha reproducido un caso positivo aislado del usuario. Un intento acotado
de encontrar píxel pintado sin candidato administrativo en el perímetro costero
`2016AL0074` no encontró punto válido. La causa demuestra que el popup puede
persistir si ningún delegado posterior provoca transición (por ejemplo, sin
hit administrativo); no demuestra cuál fue el caso concreto observado por el
usuario. No se atribuye a azar ni a una fuente específica.

## Implementación local

- `map_click_routing.mjs`: decisión exclusiva, sin depender del orden de
  registro. Si el host proporciona modo puntual activo, éste se resuelve
  primero; después fuego, territorio y vacío.
- `app.js`: el único listener global usa el árbitro. Consulta fuego antes de
  consultar fondo, y devuelve sin navegación tanto con uno como con N hits.
- `territory_layer.mjs`, `province_layer.mjs`, `municipality_layer.mjs`:
  se eliminan los listeners click competidores; se mantienen los controllers,
  callbacks `selectFromFeature`, bounds, resaltado y filtros existentes.
- Fondo: se consulta primero municipio, luego provincia, luego CCAA. Se elige
  antes de mutar estado; el cambio de ámbito no puede alterar el destino de ese
  mismo gesto. Se conserva navegación basada en códigos administrativos.
- Consulta exacta, **0 px de tolerancia añadida**. Se incluyen fill, outline,
  selected y hover de ICV, ESFire30 y EFFIS cuando la fuente/capa está visible.
  La deduplicación existente conserva `source + geometry_id`. No se consultan
  polígonos administrativos, basemap ni etiquetas como candidatos a incendio.
- Hover y pointer existentes se conservan. Los gestos con pointer sobre
  perímetro ahora realizan la interacción que anuncian. No se altera POST2B.
- El builder copia el nuevo módulo; sólo se compone frontend ligero temporal
  y se enlazan datos existentes, sin rebuild del artifact de release.

El resto de listeners son acciones explícitas: selector/breadcrumb territorial,
chooser de popup (stopPropagation, geometría exacta), cierre y «Ver detalles».
No se suprimen ni mezclan selecciones entre fuentes.

### Consulta puntual: diferencia comprobada

«Consultar un punto del mapa» y `state.pointMode` existen en **`js/app.js` del
visor GVA legacy**, no en `src/national` ni en el artifact nacional v1.0.0.
Ese código legacy queda intacto: en modo puntual no abre ficha y llama a
`queryPoint`. La precedencia puntual del árbitro tiene test unitario, pero no
se presenta como una prueba E2E de un modo nacional inexistente. No se añade
una herramienta ni un estado serializado nuevo para simularla.

## Validación y hueco de las pruebas anteriores

POST2C `map_click` llamaba directamente a
`window.__es4cRuntime.handleMapPopupClick(...)`. Su comentario decía que
ejercitaba el listener real, pero **no emitía el gesto del navegador ni los
delegados administrativos**. POST2D/POST4/POST5 reutilizaron ese camino y no
tenían la aserción `TERRITORY_BEFORE == TERRITORY_AFTER`.

El nuevo auditor CDP falla en v1.0.0 y pasa localmente; nunca llama al helper:

| Gate local | Resultado |
| --- | --- |
| ICV general + hover/click | popup, selección exacta, provincia/municipio intactos |
| `2016AL0074`, general / Alacant / `ES:MUN:03042` | PASS en los tres niveles |
| `2024AL0005` | ambas geometrías seleccionadas individualmente |
| ESFire30 / EFFIS | popup y territorio intacto |
| Multi-hit | chooser, sin navegación ni fusión |
| Fondo general / provincial | navega a provincia / municipio |
| Tap móvil 390×844 | popup; tap de fondo navega |
| Fuente oculta / filtro excluyente / año 1968 | popup invalidado; 0 hits ICV; el mismo punto permite fondo |

Pruebas específicas: **21 PASS** (5 árbitro, 7 popup, 7 temporal, 2
serialización). Pruebas antiguas de provincias: dos pasan y una queda bloqueada
por Node 10.19.0, que no entiende el optional chaining preexistente del módulo.
Se adapta su fixture al controller sin listener y se añade `getLayer` al mock;
la ruta provincial real sí pasa en Chromium. No se instala otra dependencia ni
se ejecuta la suite completa.

Dos correcciones fueron del harness, no del producto: el filtro de prueba 1e9
era rechazado por el máximo documentado 1e6 (se repitió sólo con valor válido);
el INE5 ICV `03042` se convirtió al ID ES-2 `ES:MUN:03042` para llamar al API
territorial. No se cambian límites del filtro ni identificadores fuente.

Reproducción acotada del test nuevo:

```bash
# Antes del despliegue de cualquier hotfix: evidencia del fallo v1.0.0.
python3 scripts/audit/product/es4hot1_map_click_routing.py \
  --base https://inthurain.github.io/atlas-incendios/ \
  --cases recovered province multi mobile --expect-bug \
  --output build/es4hot1/repro.json

# Frontend local temporal + datos existentes: mismos gestos y aserciones.
python3 scripts/audit/product/es4hot1_map_click_routing.py \
  --cases icv recovered province municipality multi esfire30 effis mobile double0 double1 hidden filtered period \
  --output build/es4hot1/local-check.json
```

## Integridad, límites y siguiente paso

No cambian datasets, PMTiles, relaciones, counts fuente, summary/highlights,
estilo temporal ni esquemas `es4c-state-v1`/`#v=1`. No se repite el inventario
nacional: los cambios versionados se limitan a interacción, empaquetado del
módulo, pruebas y documentación. Los smokes móviles son emulación, no hardware.

```text
CLICK_ROUTING_HOTFIX = PASS
DIRECT_CLICK_PRODUCTION_BUG = FIXED_LOCALLY
BASIC_POPUP_BUG = FIXED_LOCALLY
TERRITORY_BACKGROUND_DRILL = PRESERVED
MAP_EXPLORATION_PARITY = READY_FOR_HOTFIX_STAGING
PRODUCTION_CLICK_ROUTING = FAIL (v1.0.0 todavía sin modificar)
RELEASE_TAG national-product-v1.0.0 = UNCHANGED
NEXT_PHASE = ES-4HOT2_CLICK_ROUTING_STAGING
```

Tag conservado en `534cfe37a7120904f48c87bba71b4fcb7423bb5f`. Si el hotfix
supera posteriormente staging y producción, la versión recomendada será
`national-product-v1.0.1`. No se crea ahora. Commit **sólo local**, sin push,
deploy ni inicio de HOT2 o del backlog.
