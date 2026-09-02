# ES-4E3C1 — Filtros seguros y fichas humanas

## Resultado

`SAFE_FILTERS_STATUS = PASS`, `HUMAN_DETAIL_STATUS = PASS` y
`FILTER_STATE_STATUS = PASS`.

El frontend nacional permite afinar resultados sin aplicar una propiedad de
una fuente a otra y presenta las cuatro selecciones con una ficha legible. La
arquitectura, los IDs y la separación EGIF/ESFire30/ICV/EFFIS se conservan. No
se han creado relaciones, ontologías, datasets, PMTiles ni métricas conjuntas.

## Contrato de filtros

Cada filtro se guarda como un objeto con `filter_id`, `filter_type`, `source`,
`metric_id`, `value` y `unit`. Los objetos se validan contra una lista cerrada,
se deduplican por `filter_id` y se ordenan de forma determinista.

| Fuente | Filtros públicos seguros | Campo/criterio |
| --- | --- | --- |
| EGIF | superficie mínima; GIF | `reported_forest_area_ha`; `is_gif_forest_ge_500_ha` |
| ICV | superficie mínima; GIF; causa | superficie forestal declarada; criterio ICV documentado de 500 ha; `cause_code` aprobado |
| EFFIS | área mínima del perímetro | `mapped_area_ha` del snapshot provisional |
| ESFire30 | ninguno de magnitud/GIF/causa | `DEFERRED_NO_SAFE_TERRITORIAL_AREA` |

Los controles de superficie ofrecen 10, 100, 500 y 1.000 ha, además de valor
positivo personalizado. El texto identifica siempre métrica y fuente. Un
valor ausente queda fuera de un mínimo positivo: `unknown != 0`. EGIF no
expone causa pública (`DEFERRED_PENDING_ONTOLOGY`) y EFFIS no ofrece GIF.

Los controles se muestran solo si la fuente tiene cobertura, está activa y es
válida en el territorio. Los chips permiten quitar filtros por separado o
limpiarlos todos. Pasar de GVA con una causa ICV a Galicia retira el filtro y
anuncia de forma humana que dejó de estar disponible.

## Efecto por fuente

- EGIF filtra las columnas INITIAL ya cargadas en CCAA/provincia/municipio;
  lista, lookup, selección, conteo, superficie conocida, GIF e histograma usan
  exactamente el mismo subconjunto. DETAIL sigue cargándose solo al abrir una
  ficha.
- España continúa con cero INITIAL nacional. Para GIF y mínimo exacto de 500
  ha el conteo anual se obtiene exactamente del agregado administrativo GIF.
  Otras combinaciones nacionales no se simulan: se oculta la tarjeta afectada
  y el histograma, si se consulta, se etiqueta expresamente como no filtrado.
- ICV filtra `fires.json`, ya necesario en el runtime, y después sus
  geometrías por `fire_id`. Produce agregados anuales exactos de registros,
  perímetros, superficie conocida y GIF.
- EFFIS filtra sus 25 features. Con filtro carga los dos assets anuales para
  poder mantener una serie 2025–2026 exacta; es una decisión acotada al
  snapshot pequeño y provisional.
- ESFire30 no recibe estos filtros. Tampoco se busca una correspondencia entre
  registros y perímetros.

Las tarjetas y el histograma muestran `EXACT_RUNTIME` o `EXACT_DERIVED`
cuando procede. Si el cálculo no es posible con el summary actual se aplica
`HIDE_WHILE_FILTERED` a la tarjeta y un label explícito a la serie. Un cero
exacto dice “No hay resultados que cumplan estos filtros”; falta de cobertura
mantiene el mensaje de indisponibilidad.

## Estado, URL y legado

Los filtros viven en `state.filters`; no hay segundo store. El serializer
existente añade `analysis.filters` a `es4c-state-v1`, por lo que los hashes
anteriores siguen abriendo con lista vacía. La representación canónica permite
Copy Link, reload y back/forward mediante la misma restauración ya aceptada.

El permalink valenciano `#v=1` solo se traduce si `src` identifica una única
fuente compatible:

| Campo legacy | Traducción exacta | Política restante |
| --- | --- | --- |
| `min_area` | EGIF, ICV o EFFIS cuando es la única fuente; cero es no-op | `IGNORED_SAFE` si es ambiguo/no compatible |
| `gif=1` | EGIF o ICV como única fuente; falso es no-op | `IGNORED_SAFE` en los demás casos |
| `cause` | código aprobado ICV con ICV como única fuente | `IGNORED_SAFE` en los demás casos |

No se reinterpreta ningún enlace histórico por aproximación.

## Fichas humanas

La información primaria sigue fecha, lugar, magnitud, causa, GIF y avisos. Los
campos opcionales ausentes no producen filas `null`, `undefined`, `unknown` o
`N/A`. “Más sobre estos datos” permanece cerrado y contiene identificadores,
campos de procedencia y detalles técnicos.

- **EGIF:** “Registro de incendio”, fechas, municipio resuelto, provincia,
  paraje, superficie forestal declarada y GIF. Si el municipio no se enlazó,
  la ficha no inventa uno y lo explica discretamente. El código de causa no
  interpretado queda en el panel técnico. Se recuerda que no hay perímetro
  individual.
- **ESFire30:** “Perímetro Landsat”, año, territorio consultado y fuente. No
  muestra área inexistente y dice que procede de imágenes Landsat y no es
  cartografía oficial.
- **ICV:** fechas, municipio, provincia, paraje, superficie declarada, causa,
  GIF y número de perímetros. La ficha de `2024AL0005` conserva un incendio
  documentado con dos perímetros, sin convertirlo en dos incendios.
- **EFFIS:** fechas, territorio, área cartografiada, snapshot y aviso de
  provisionalidad; no se presenta como incendio oficial.

Seleccionar una fuente abre solo su ficha. Las selecciones continúan siendo
independientes. Los resultados EGIF se simplificaron a año, acción “Ver
ficha”, superficie y GIF: el identificador deja de ser el título público.

## Móvil y accesibilidad

En 390×844 el botón muestra `Filtros · N`; el panel se abre como bottom sheet
y se cierra tras aplicar. Las fichas seleccionadas son sheets que se pueden
minimizar o cerrar sin inutilizar el mapa.

Los filtros tienen labels, `fieldset/legend`, `aria-expanded`, estado live y
chips eliminables con nombre accesible. Las fichas tienen headings enfocables:
una selección desde teclado/lista puede llevar el foco, mientras un toque o
clic en el mapa no lo roba continuamente. Color y badges no son la única señal.

## Errores y carga

Un error de filtro muestra “No se han podido aplicar estos filtros” y conserva
el mapa y las demás fuentes. Los loaders mantienen `AbortController`, tokens de
generación y caches existentes; una selección que sale del subconjunto se
invalida solo en su fuente.

Esto no fue un benchmark. No se cargó INITIAL/DETAIL nacional, provincias o
municipios ajenos ni el PMTiles completo. EGIF reutiliza sus assets por bloque,
ICV reutiliza `fires.json`, EFFIS examina como máximo 25 features y DETAIL
permanece lazy.

## Smokes dirigidos

Pasaron 14/14: 12 desktop y dos viewports Chromium emulados a 390×844.

| Escenario | Resultado humano verificable |
| --- | --- |
| España 1995 · EGIF ≥500 ha | 26 registros; `EXACT_DERIVED`; 0 INITIAL nacional |
| Galicia 1995 · EGIF GIF | 4 registros; tarjeta, lista e histograma exactos |
| GVA 1995 · ICV ≥100 ha | 5 incendios documentados; EGIF/ESFire30 intactos |
| GVA 1995 · ICV rayo | 75 incendios documentados; 42,1 ha conocidas |
| GVA 1995 · ICV negligencia | 0 y mensaje de filtro, no “sin datos” |
| GVA 2024 | ficha ICV de `2024AL0005`: 1 registro, 2 perímetros |
| Galicia 1995 | fichas EGIF y ESFire30 humanas separadas |
| Elx 2025 · EFFIS ≥0,01 ha | 1 perímetro, 7 ha y ficha provisional |
| Canarias 1995 | EGIF disponible; ausencia de perímetros cartografiados, no cero |
| GVA → Galicia | filtro ICV retirado con aviso; estado consistente |
| permalink de filtro | recarga, atrás y adelante restauran de forma determinista el filtro o su ausencia |
| móvil GVA / Elx | panel de filtros y ficha minimizable correctos |

No hubo errores de bootstrap/runtime. También pasaron cinco tests específicos
de semántica, `null != 0`, estado/round-trip, legacy, agregación exacta,
independencia, DOM accesible, DETAIL lazy y ensamblado sin datos nuevos.

## Pendiente deliberado

- `HISTOGRAM_BRUSH_STATUS = DEFERRED_P1`; click de año sigue siendo P0.
- `BASEMAP_GAP = OPEN_NO_APPROVED_LOCAL_PROVIDER`; E3C1 no añade proveedor.
- Highlights/top-N y pulido de contexto del mapa pertenecen a E3C2.
- Si E3C2 necesita tarjetas nacionales exactas para umbrales EGIF arbitrarios o
  combinaciones de filtros, hará falta un agregado pequeño y específico; no un
  cubo combinatorio. No es necesario para el flujo validado de 500 ha/GIF.
- Causas EGIF permanecen bloqueadas por la ontología documental MITECO.

## Comparación de producto

GVA estableció la referencia de filtros y fichas legibles; D4B conservaba toda
la potencia pero enseñaba demasiada terminología interna. E3A recuperó la
jerarquía, E3B2 el resumen y la evolución, y E3C1 recupera exploración y detalle
sin perder tipado de fuente. Falta E3C2 (destacados seguros y pulido del mapa)
antes de aceptar el producto.

## Validación reproducible

```bash
python3 -m unittest tests.test_es4e3c1_safe_filters_human_details
python3 benchmarks/es4e3c1/run_smoke.py --all --output /tmp/es4e3c1-smokes.json
python3 benchmarks/es4e3c1/run_smoke.py --check --output /tmp/es4e3c1-smokes.json
```

No se ejecutaron suite completa, benchmark ni staging.

## Estado

- `SAFE_FILTERS_STATUS = PASS`
- `HUMAN_DETAIL_STATUS = PASS`
- `FILTER_STATE_STATUS = PASS`
- `TECHNICAL_RUNTIME_REGRESSION = false`
- `PRODUCT_RELEASE_CANDIDATE = false`
- `D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`
- `NEXT_PHASE = ES-4E3C2_NATIONAL_HIGHLIGHTS_MAP_POLISH`
