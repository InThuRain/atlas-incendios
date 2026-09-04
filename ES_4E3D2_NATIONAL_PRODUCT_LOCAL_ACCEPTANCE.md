# ES-4E3D2 — Aceptación local del producto nacional

## Decisión

`PRODUCT_LOCAL_ACCEPTANCE = PASS_WITH_MINOR_GAPS`.

El artefacto E3D1 ya se comporta como una aplicación de consulta y no como un
panel de diagnóstico. La primera pantalla explica qué territorio y periodo se
están viendo, el mapa domina, las magnitudes se leen por fuente y la metodología
queda plegada. La experiencia conserva las fortalezas del visor GVA —resumen,
histograma, filtros, destacados, fichas y enlace— y suma navegación nacional
hasta municipio, coberturas explícitas y separación rigurosa de fuentes.

No se ha encontrado ningún blocker. Quedan tres mejoras P1 no bloqueantes: el
brush del histograma, un objetivo táctil mejor para escoger barras anuales en
móvil y afinar el feedback de cargas frías exigentes como Cangas del Narcea.

Por tanto:

- `PRODUCT_RELEASE_CANDIDATE = READY_FOR_REMOTE_PRODUCT_STAGING`;
- `D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`;
- `NEXT_PHASE = ES-4E4_NATIONAL_PRODUCT_STAGING`.

Esto no constituye aceptación de producción ni autoriza un cambio de raíz.

## Artefacto y método

Se sirvió exclusivamente `build/national-product-staging/` como docroot. El
harness no construye el frontend ni enlaza `src/`, `data/derived/`,
`prototypes/`, `work/` o el root del repositorio.

El checker físico confirmó:

| Identidad | Resultado |
| --- | ---: |
| Ficheros site | 497 |
| Bytes site | 812.510.441 |
| Ficheros payload | 495 |
| Bytes payload | 812.291.384 |
| Fingerprint payload | `10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3` |
| SHA-256 manifest | `377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e` |
| SHA-256 identidad site | `f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e` |

La observación combinó 13 recorridos de métricas/histograma, 14 de
filtros/fichas, 10 de destacados, cuatro de red/mapa, dos enlaces legacy, un
round-trip native en sesión nueva, tres viewports de accesibilidad y fallos
controlados de summary, basemap y DETAIL. Se realizaron tres capturas locales
del propio artefacto para juicio visual. El visor GVA público se abrió una sola
vez en desktop como referencia cualitativa, complementando la auditoría E1; no
se hizo una batería sobre producción.

## Juicio de primera impresión

**PASS.** En 1440×900 el mapa ocupa aproximadamente el 71 % del ancho, incluye
topónimos, carreteras, costa y límites, y mantiene los perímetros como capa
principal. La cabecera comunica Atlas, territorio, periodo y compartir. El
panel contiguo empieza por territorio y periodo, seguido por una explicación
breve y tarjetas tipadas; no exige abrir fuentes para comprender las cifras.

GVA continúa siendo especialmente compacto para filtros e histograma: ambos
aparecen pronto en su barra lateral. E3 distribuye mejor el espacio entre mapa
y explorador y ofrece un contexto territorial mucho más amplio, aunque las
tarjetas y el histograma requieren algo más de scroll. La diferencia ya es una
preferencia de densidad, no una regresión de producto.

## Recorridos humanos

### España

- **1968–2026:** muestra por separado 119.498 perímetros Landsat, 646.887
  registros EGIF y 8.230.839 ha de superficie forestal EGIF conocida. No crea
  total combinado. El rango pedido se conserva aunque cada fuente tenga su
  propia cobertura.
- **1975:** aparecen 4.128 registros EGIF y 180.137 ha conocidas. El texto
  comunica que no disponemos de perímetros para ese periodo; no muestra un
  cero falso.
- **1995:** aparecen 5.035 perímetros Landsat, 25.557 registros EGIF y
  141.082 ha EGIF conocidas. Histograma, mapa y controles se comprenden sin
  abrir metodología.

### Galicia, Ourense y Cangas del Narcea

- **Galicia 1995:** 1.989 perímetros Landsat, 15.254 registros EGIF y 46.670
  ha EGIF conocidas. El primer destacado fue Laza, Ourense, 2.029 ha y abrió
  su ficha administrativa sin inventar geometría.
- **Ourense 1995:** 746 perímetros Landsat, 3.605 registros EGIF y 18.207 ha.
  El cambio provincial coordinó mapa, límite, resumen, histograma, filtros y
  destacados.
- **Cangas del Narcea 1985–2021:** el índice municipal resolvió 2.610
  `geometry_id`, que la interfaz denomina perímetros y nunca incendios. EGIF
  mostró 3.044 registros y 47.392 ha conocidas. La navegación y el mapa fueron
  estables; la carga fría fue la más lenta del diagnóstico.

### País Valencià

- **1995:** ICV es la referencia regional recomendada: 467 incendios oficiales
  documentados y 2.220 ha conocidas. EGIF muestra 467 registros administrativos
  y ESFire30 25 perímetros Landsat como información independiente; la igualdad
  accidental de los dos primeros conteos no se presenta como correspondencia.
- **ICV ≥500 ha:** queda un resultado, Sella, 13/07/1995, 502 ha. El
  destacado y el resumen ICV se actualizan; EGIF y ESFire30 no reciben el
  filtro ICV.
- **2024:** 472 incendios ICV y 1.428 ha conocidas, sin ruido de fuentes fuera
  de cobertura.
- **`2024AL0005`:** un incendio documentado conserva dos perímetros. La ficha
  muestra fechas, San Miguel de Salinas, Alicante/Alacant, paraje, 0,01 ha,
  causa Intencionado, GIF y la cardinalidad 1:2. Una selección solo de registro
  no elige una geometría arbitraria; una selección geométrica es exacta.
- **2026:** 16 perímetros EFFIS y 10.265 ha cartografiadas. Se ve la
  provisionalidad y el snapshot de 19/08/2026 sin convertir el aviso en el
  contenido principal ni afirmar cierre anual.
- **Elx 2025:** un perímetro EFFIS de 7 ha. Breadcrumb, mapa, destacado, ficha
  provisional, filtro EFFIS y compartir funcionaron.

### Canarias 1995

El territorio, Protomaps, BDLJE y EGIF funcionan: 56 registros y 3.631 ha
conocidas. ESFire30 se comunica como no disponible en Canarias, no como cero
incendios o cero perímetros observados.

## Exploración

### Resumen e histograma

Las tarjetas hablan de registros, incendios documentados o perímetros según
corresponda y nombran siempre la fuente. El histograma presenta 59 años,
selecciona una serie inicial contextual —EGIF, ICV o EFFIS—, permite cambiarla,
distingue hueco de cero, ofrece tooltip, marca el rango y actualiza periodo con
clic sobre un año. Su tabla alternativa también contiene las 59 filas.

Cumple el papel exploratorio esencial de GVA. `HISTOGRAM_BRUSH_STATUS =
DEFERRED_P1`; su ausencia no bloquea porque clic de año y Desde/Hasta cubren la
tarea. En 390 px las barras miden cerca de 4,7 px de ancho, de modo que no son
un objetivo táctil cómodo: es el gap móvil principal.

### Filtros

Se comprobaron superficie y GIF administrativos EGIF, superficie, GIF y causa
ICV, y superficie cartografiada EFFIS. Los filtros son territoriales,
temporales y source-aware. Un filtro ICV al pasar a Galicia se retira con el
mensaje: “Se ha retirado un filtro porque ya no está disponible en este
territorio, periodo o fuente”.

El resultado cero válido dice: “No hay resultados que cumplan estos filtros en
la fuente indicada. Las demás fuentes permanecen independientes”. No se
confunde con ausencia de datos.

### Destacados

Los destacados son útiles y breves: como máximo cinco en la vista inicial,
con fecha/año, lugar, magnitud y fuente. EGIF, ICV y EFFIS abren su ficha.
ESFire30 permanece correctamente sin ranking porque no dispone de una
magnitud segura para ordenarlo; no se penaliza ni se inventa una.

## Fichas humanas

- **EGIF:** fecha, territorio, superficie forestal declarada y GIF cuando
  existen. Dice que es un registro administrativo sin perímetro individual.
- **ESFire30:** año y procedencia como perímetro obtenido mediante Landsat;
  declara que no es cartografía oficial ni registro administrativo.
- **ICV:** fecha, lugar, paraje, superficie, causa, GIF y número de perímetros.
  Recupera la calidad de lectura del visor GVA y conserva la relación 1:N.
- **EFFIS:** fecha, lugar, área cartografiada, snapshot y provisionalidad en
  lenguaje humano.

Los IDs, licencias y explicaciones metodológicas quedan bajo “Más sobre estos
datos”. `source_record`, `geometry_id`, `INITIAL`, `DETAIL`, `ready`, `shard`,
`not_integrated_for_territory` y `no_coverage` no aparecieron en el nivel
principal observado.

## Fuentes y metodología

El panel comienza plegado y no es necesario para explorar. Al abrirlo ofrece
toggles, cobertura, procedencia, licencias e identidades para quien las
necesite. De este modo conserva el rigor de D4B sin dejar que los estados del
runtime gobiernen la primera pantalla.

## Mapa y entrega

Protomaps y BDLJE forman un contexto suficiente: topónimos, carreteras,
costas, límites y territorio activo se leen sin competir con las capas de
incendios. La leyenda cambia con las fuentes visibles. No hubo 404 de glyphs
ni rangos tipográficos no empaquetados.

En cuatro sesiones frías diagnósticas, ambos PMTiles respondieron solo por
Range y no hubo descarga completa:

| Escenario | Tiempo estable | Heap | Protomaps Range / bytes | ESFire30 Range / bytes |
| --- | ---: | ---: | ---: | ---: |
| España | 4.553 ms | 65.756.982 B | 6 / 263.919 B | 6 / 526.207 B |
| Galicia | 6.003 ms | 138.038.496 B | 10 / 582.568 B | 10 / 2.343.832 B |
| Cangas | 7.203 ms | 173.527.153 B | 14 / 1.141.082 B | 14 / 3.135.688 B |
| Elx | 8.274 ms | 198.376.852 B | 16 / 862.700 B | 16 / 663.763 B |

Estas cifras dependen de viewport, tiles y caché; son diagnósticas, no
presupuestos ni comparaciones contractuales. La disponibilidad completa del
summary tardó entre 2,36 y 10,65 s en los recorridos fríos; Cangas fue el
extremo. Los estados de carga evitan que parezca un bloqueo, pero conviene
seguir afinando el feedback después del release.

La telemetría del summary registró 2 requests / 83.450 B en España completa,
2 / 83.261 B en Galicia 1995 y 7 / 587.138 B en Elx 2025; las respuestas stale
se ignoraron. Los destacados nacionales EGIF de España necesitaron 2 requests
y 344.502 B; Galicia EGIF y Elx EFFIS reutilizaron datos ya cargados y no
hicieron requests adicionales. En la sesión fría de España, Protomaps,
ESFire30 y glyphs sumaron 1.499.831 B observados; no es el total contractual de
la aplicación ni incluye todos los JSON auxiliares.

## Móvil y accesibilidad

`MOBILE_PRODUCT_FEEL = ACCEPTABLE`. En 390×844 el mapa ocupa la primera mitad
del viewport; breadcrumb y selectores aparecen inmediatamente después. España
1995, el drawer de filtros GVA 1995 y la ficha minimizable/compartible de Elx
2025 fueron utilizables. El título territorial largo se trunca visualmente en
cabecera, pero el breadcrumb lo presenta completo.

La comprobación ligera encontró cero controles visibles sin nombre, foco de
3 px, labels de filtros, botones y plegables nombrados, tabla alternativa del
histograma y fichas anunciadas. No es una auditoría WCAG. Las barras densas y
los enlaces pequeños de atribución quedan fuera de un objetivo táctil ideal;
la navegación esencial conserva controles mayores.

## Compartir, legacy e historial

Un estado native GVA 1995 con fuentes, filtro ICV ≥500 ha, selección
`gva:pif-cv:1995AL0076`, mapa y periodo se copió mediante fallback visible,
se recargó y se abrió en un perfil Chromium limpio con round-trip exacto.

Dos entradas GVA `#v=1` —1995 histórico y Elx/EFFIS 2025— restauraron el
estado humano, se promovieron a `es4c-state-v1` tras una interacción y
Back/Forward alternó correctamente ambas representaciones. El fixture Elx
incluye `min_area=10` para un perímetro de 7 ha; por ello la selección queda
invalidada al aplicar el filtro, de forma correcta, en vez de conservar una
ficha incompatible.

## Aislamiento de errores

- Al fallar el summary se mantienen shell, mapa y destacados, con “No se ha
  podido cargar el resumen de este territorio”.
- Se reutilizó el fault controlado E3D1 del basemap: queda BDLJE-only y
  ESFire30 sigue operativo.
- Al fallar un DETAIL EGIF de Galicia se mantienen mapa, INITIAL y lista; la
  ficha explica que no pudo cargar la información ampliada y que mapa/lista
  continúan disponibles.

No hubo excepciones inesperadas, errores del runtime ni fallos de bootstrap.

## Matriz de producto

| Criterio | GVA | D4B técnico | E3 producto | Estado | Nota |
| --- | --- | --- | --- | --- | --- |
| Primera impresión | fuerte | débil | fuerte | PASS | mapa y lenguaje humano |
| Mapa/contexto | fuerte | insuficiente | fuerte | PASS | Protomaps + BDLJE |
| Territorio | regional | nacional potente | nacional hasta municipio | PASS | E3 es superior |
| Tiempo | histograma/sliders | inputs | histograma + rango | MINOR | brush pendiente |
| Resumen | claro por fuente | debug-like | tarjetas tipadas | PASS | sin total falso |
| Histograma | fuerte | ausente | fuerte | PASS | touch móvil mejorable |
| Filtros | fuerte regional | ausentes | seguros por fuente | PASS | capacidades dependen de fuente |
| Destacados | fuerte | ausentes | seguros por fuente | PASS | ESFire30 sin ranking inventado |
| Ficha | humana | técnica | humana + metodología | PASS | ICV recupera paridad |
| Fuentes | claras | dominantes | secundarias | PASS | toggles conservados |
| Metodología | secundaria | dominante | progresiva | PASS | suficiente para avanzado |
| Permalink | simple | completo | completo + legacy | PASS | fresh session validada |
| Móvil | bueno | mala jerarquía | aceptable | MINOR | mapa primero; barras densas |
| Ruido técnico | bajo | alto | bajo | PASS | cero términos internos principales |

## Cierre de regresiones E1

| Regresión E1 | Estado | Evidencia |
| --- | --- | --- |
| A. Ausencia de overview humano | RESOLVED | tarjetas por fuente y magnitud |
| B. Sin histograma | RESOLVED | 59 años, series, tooltip y clic |
| C. Sin filtros útiles | RESOLVED | EGIF/ICV/EFFIS source-aware |
| D. Mapa sin contexto | RESOLVED | Protomaps, topónimos, vías y BDLJE |
| E. Fichas técnicas | RESOLVED | cuatro contratos humanos |
| F. Estados runtime dominantes | RESOLVED | fuentes/metodología plegadas |
| G. Mala jerarquía móvil | RESOLVED | mapa en primer viewport y sheets |

`RESOLVED` significa que la regresión mayor ya no bloquea; no afirma que el
diseño no admita refinamiento.

## Gaps

### BLOCKER

Ninguno.

### P1_POST_RELEASE

- brush de rango en histograma;
- selección táctil más cómoda de años en histograma móvil;
- feedback/latencia percibida de cargas frías municipales exigentes.

### P2_FUTURE

- contexto opcional z13, relieve y POI;
- ranking ESFire30 solo si aparece una magnitud segura;
- espaciado y truncado de cabecera en pantallas estrechas.

### EXTERNAL_BLOCKED

- ontología nacional de causas EGIF: documentación MITECO/ADCIF;
- publicación CCINIF: permiso;
- límites y correspondencias municipales históricas.

## Archivos de evidencia

- agregado estable:
  `data/audit/product/es4e3d2_national_product_local_acceptance.json`;
- traza Chromium local ignorada:
  `build/es4e3d2/product-acceptance-raw.json`;
- harness:
  `benchmarks/es4e3d2/run_product_acceptance.py`.

No se modificaron runtime, datasets, mapa base, staging ni producción.
