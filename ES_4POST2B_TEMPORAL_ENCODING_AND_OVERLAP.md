# ES-4POST2B — Codificación temporal y lectura de solapes

## Resultado humano

Sí. Una persona puede volver a distinguir, sin abrir una ficha, perímetros
antiguos y recientes y reconocer zonas potencialmente recurrentes mediante el
mapa. Los perímetros se representan de azul (más antiguo dentro del periodo
visible) a rojo (más reciente), con una leyenda que explica los años exactos.
La fuente sigue disponible, pero como lectura secundaria.

```text
TEMPORAL_VISUAL_ENCODING = PARITY
OVERLAP_READABILITY = PARITY
TEMPORAL_LEGEND_STATUS = PASS
MAP_FIRST_TEMPORAL_DISCOVERY = PASS
MAP_EXPLORATION_PARITY = STILL_FAILS_PENDING_DIRECT_POPUP
PATCH_BUNDLE_RECOMMENDATION = CONTINUE_TO_POST2C_BEFORE_DEPLOY
RELEASE_TAG_STATUS = HOLD
```

No se modificó producción, staging, datos, PMTiles, el esquema
`es4c-state-v1` ni el permalink GVA `#v=1`.

## Algoritmo GVA histórico exacto

La referencia es `f7a3532f633a247f33dee3ebba9fbcc316c0e534`, función
`yearColor()` de `js/app.js`:

```js
ratio = clamp((year - years.min) / Math.max(1, years.max - years.min), 0, 1)
old = [44, 123, 182]
recent = [240, 82, 46]
rgb[channel] = Math.round(old[channel] + (recent[channel] - old[channel]) * ratio)
```

`years` era el mínimo/máximo de las fuentes con geometría del manifest:
**1985–2026** en el perfil final. No había una rama especial de año único; el
filtro quitaba features, pero mantenía el dominio global. Por ejemplo, 1995
resultaba `rgb(92,113,149)`. `Math.max(1, …)` sólo prevenía una división por
cero si ese dominio geométrico llegaba a colapsar.

Los fills históricos eran ICV `.28`, ESFire30 `.20` y EFFIS `.20`; los fills
seleccionados `.50`, `.46` y `.42`. ICV tenía borde temporal de 1,2 px;
ESFire30 `#875b20`, 2 px, guiones `2 5`; EFFIS borde temporal, 2 px, guiones
`7 5`. Leaflet conservaba el orden de la colección cargada: no establecía un
territorio ni fuente principal por orden.

## Implementación nacional

`prototypes/es4c/temporal_style.mjs` conserva exactamente la paleta y la
interpolación RGB:

```text
más antiguo = rgb(44,123,182)
más reciente = rgb(240,82,46)
```

La adaptación explícita para MapLibre es el dominio: se usa la intersección
entre el periodo solicitado y cobertura geométrica nacional **1985–2026**. Es
distinta del dominio fijo antiguo para que `1993–2024` y después `2015–2020`
muestren en la leyenda extremos comprensibles para la consulta. No depende de
teselas, resultados cargados ni filtros por área/GIF/causa.

Para un único año se usa el extremo azul histórico. Todos los perímetros de
ese año comparten valor, sin inventar precisión subanual ni dividir por cero.
MapLibre aplica `interpolate` a la propiedad canónica `year`; los fills se
ordenan con `fill-sort-key` ascendente por año dentro de cada source. El color,
no el orden, es la señal cronológica primaria.

| Fuente geométrica | Fill | Contorno secundario | Semántica preservada |
| --- | --- | --- | --- |
| ICV | temporal, `.28` | temporal, 1,2 px | perímetros oficiales |
| ESFire30 | temporal, `.20` | `#875b20`, 2 px, `2 5` | perímetros Landsat |
| EFFIS | temporal, `.20` | temporal, 2 px, `7 5` | perímetros provisionales |

El orden de capas es ESFire30 fill/outline, ICV fill/outline, EFFIS
fill/outline y, encima, outlines de selección y hover. Los fills transparentes
y contornos dejan distinguir solapes, incluidos los del mismo año. Selección y
hover sólo añaden contorno oscuro y ancho; nunca sustituyen el fill temporal.
EGIF no entra porque no tiene geometría individual.

## Leyenda y accesibilidad

La leyenda primaria dice **«Año del perímetro»**, presenta los años extremos,
el gradiente azul→rojo y «Más antiguo ← → más reciente». Para un único año
muestra «Año seleccionado». Límite y fuentes quedan debajo bajo **«Capas»**.
Esto aporta señal textual y numérica, no sólo color. No constituye una
auditoría completa de daltonismo; esa limitación queda documentada.

## Validación focalizada

El smoke construyó sólo el frontend y enlazó assets locales aceptados. No
reconstruyó fuentes. Pasaron, sin errores de runtime ni Chromium:

| Escenario | Resultado |
| --- | --- |
| GVA 1995 | 467 registros / 467 geometrías; dominio `1995–1995`; selección conserva fill temporal. |
| 2016–2019 recuperados | 341/341, 346/346, 375/375 y 272/272; misma ruta temporal y seleccionable. |
| GVA 1993–2024 | 13.738 registros / 13.739 geometrías; dominio largo y lectura azul/rojo. Las 186 features renderizadas son sólo el viewport, no un total territorial. |
| GVA 2000–2020 | prueba de recurrencia: colores y transparencia permiten localizar un ámbito con perímetros de distintas edades sin abrir ficha. |
| 2015–2020 | dominio y leyenda actualizados sin reload. |
| `2024AL0005` | un `fire_id`, dos `geometry_id`; ambas tienen año 2024 y una se selecciona individualmente. |
| Filtros ICV | área ≥1 ha, GIF y causa `negligence` mantienen dominio `2015–2020`. |
| Histograma | clic 2016 cambia estado, mapa y leyenda a `2016–2016`. |
| Móvil | 390×844; colores y leyenda compacta legibles, sin tapar desproporcionadamente el mapa. |

Capturas de comparación:

- Antes: `data/audit/product/es4post1/legacy-gva-1995.png`,
  `data/audit/product/es4post1/national-1995.png` y
  `data/audit/product/es4post1/national-overlap-1993-2024.png`.
- Después: `data/audit/product/es4post2b/national-after-1995.png`,
  `data/audit/product/es4post2b/national-after-overlap-1993-2024.png` y
  `data/audit/product/es4post2b/national-after-mobile-1995.png`.

El rango largo recupera la lectura de recurrencia que el fill ICV verde
uniforme del nacional anterior no ofrecía. La captura se toma antes de abrir
ficha para aislar este cambio de POST2B del popup directo pendiente.

## Permalinks, rendimiento y decisión

La paleta y leyenda derivan de `from`/`to`; no añaden campos a
`es4c-state-v1`. Pasan los tests focalizados de serialización nativa y
adaptación legacy `#v=1`. Los filtros humanos no redefinen el dominio.

La actualización usa una expresión y un número constante de
`setPaintProperty`; no recrea colecciones ni datasets. Los smokes end-to-end
tardaron aproximadamente 5,4–9,2 s, incluyendo navegador, assets y mapa
estable; son diagnóstico, no benchmark aislado de estilo.

La paridad visual temporal queda recuperada. La regresión restante es el
popup humano directo. Se recomienda **continuar a POST2C antes de desplegar**
y agrupar POST2A, POST2B y POST2C en un patch futuro. Producción sigue con el
artifact nacional anterior a POST2A y el tag continúa en `HOLD`.

## Evidencia y siguiente fase

- Evidencia: `data/audit/product/es4post2b_temporal_encoding_and_overlap.json`.
- Auditor: `scripts/audit/product/es4post2b_temporal_encoding_and_overlap.py`.
- Tests focalizados POST2B, POST2A, permalink GVA y serialización nativa:
  **18 PASS**; auditor `--check`, build ligero y `git diff --check`: **PASS**.

Siguiente fase exacta: `ES-4POST2C_DIRECT_HUMAN_POPUP`. No se inicia aquí.
