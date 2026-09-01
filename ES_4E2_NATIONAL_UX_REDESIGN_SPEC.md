# ES-4E2 — Especificación del rediseño UX nacional

## Estado y decisión

`UX_REDESIGN_SPEC_STATUS = READY_FOR_IMPLEMENTATION`.

La dirección aprobada es recuperar la lectura inmediata, el mapa dominante y
el flujo exploratorio del visor GVA sobre el runtime nacional aceptado. No se
recupera su arquitectura antigua ni se crea una entidad incendio transversal.

`ROOT_SWITCH_UX_STATUS = NEEDS_RECONCILIATION` y
`D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`. El staging D4B permanece
congelado como `TECHNICAL_BASELINE`; E2 no modifica ninguna aplicación.

## 1. Contrato de producto

La primera lectura debe responder, por este orden:

1. qué territorio y periodo se están consultando;
2. qué registros o perímetros están documentados;
3. dónde se encuentran los perímetros disponibles;
4. qué magnitud documenta cada fuente;
5. cómo se distribuyen en el tiempo;
6. qué elementos destacan según una métrica explícita;
7. qué se sabe del elemento seleccionado.

La fuente debe acompañar discretamente cada cifra, serie, ranking y ficha. La
calidad, identificadores, licencia y metodología se mantienen a un clic, pero
no compiten con fecha, lugar, magnitud o causa.

Quedan prohibidos en toda la interfaz:

- sumar EGIF, ESFire30, ICV y EFFIS como un total de incendios;
- sumar superficies declaradas y áreas cartografiadas;
- deduplicar, enlazar o fusionar entidades sin evidencia;
- inferir causa, GIF, municipio histórico o territorio de ignición;
- utilizar features cargadas o visibles como total territorial.

## 2. Vista recomendada

La vista inicial no presenta un formulario de fuentes. Activa una configuración
contextual reproducible y ofrece “Fuentes y metodología” para cambiarla.

### Fuente cartográfica recomendada

| Contexto | Geometría destacada por defecto | Tratamiento de las demás |
| --- | --- | --- |
| España o territorio fuera de GVA, 1985–2021 | ESFire30 | EGIF aparece como información administrativa sin geometría. |
| Territorio fuera de GVA, fuera de 1985–2021 | ninguna geometría de incendio | Se muestran los registros disponibles y un mensaje humano sobre la ausencia de perímetros. |
| GVA, 1985–1992 | ESFire30 | EGIF es complementario. |
| GVA, 1993–2024 | ICV | ESFire30 1993–2021 queda como capa complementaria, apagada en la vista recomendada. |
| GVA, 2025–2026 | EFFIS | Se marca como provisional y se muestra la fecha del snapshot. |

Si un rango GVA atraviesa varios regímenes, la vista recomendada usa ESFire30
solo en 1985–1992, ICV en 1993–2024 y EFFIS en 2025–2026. No superpone por
defecto ESFire30 sobre ICV entre 1993 y 2021. El usuario puede activar esa capa
complementaria desde “Fuentes y metodología”. Esta prioridad opera por fuente
y tramo temporal, nunca enlaza features ni decide que dos elementos sean el
mismo incendio.

BDLJE permanece siempre como contexto territorial. EGIF se ofrece cuando su
cobertura intersecta el periodo, aunque no pinte geometrías.

### Información recomendada

- Una tarjeta principal corresponde a la fuente contextual de análisis.
- Las fuentes independientes aplicables aparecen como tarjetas
  complementarias, nunca como sumandos.
- Cada tarjeta lleva una etiqueta corta: `EGIF`, `ICV`, `ESFire30` o `EFFIS`.
- Un selector discreto sobre el histograma permite cambiar la fuente analizada.
- Los toggles completos y las fuentes no aplicables viven en el panel avanzado.

## 3. Jerarquía en tres niveles

### PRIMARY

- nombre humano del territorio y breadcrumb;
- periodo solicitado;
- mapa base, límite administrativo, perímetros recomendados y leyenda;
- tarjetas de conteos y magnitudes con tipo y fuente explícitos;
- histograma de una única métrica/fuente a la vez;
- filtros aplicables a la fuente de análisis;
- destacados de esa misma fuente y métrica;
- ficha humana del elemento seleccionado;
- acción “Compartir”.

### SECONDARY

- desglose por fuentes aplicables;
- cambio de fuente de análisis o de capa complementaria;
- cobertura efectiva y advertencias de parcialidad;
- filtro GIF y filtros que solo algunas fuentes soportan;
- número de valores conocidos/desconocidos cuando afecte a una magnitud;
- aviso de límite municipal actual frente a registros históricos;
- estado provisional EFFIS y fecha de snapshot;
- errores recuperables de una fuente.

### ADVANCED

- toggles completos de fuentes;
- cobertura detallada y regímenes documentales;
- `record_id`, `geometry_id`, códigos fuente y cardinalidad geométrica;
- semántica y calidad geométrica;
- método de obtención, transformaciones, provenance y licencias;
- estado técnico solo cuando ayude a diagnosticar un error descargable.

`idle`, `ready`, número de assets, shards, `INITIAL`, `DETAIL` y features en
viewport no forman parte de la UX pública, ni siquiera del modo avanzado
normal. Pueden permanecer en un harness de desarrollo independiente.

## 4. Layout desktop

El mapa debe ocupar entre dos tercios y tres cuartos del ancho útil y toda la
altura bajo la cabecera. Un panel de exploración de 360–440 px ocupa el resto;
no tapa el mapa.

1. **Cabecera fija y compacta:** marca, breadcrumb territorial, periodo resumido
   y Compartir.
2. **Mapa persistente:** mapa base, límites, capas activas, leyenda y selección.
3. **Panel de exploración:** resumen → histograma → filtros → destacados.
4. **Selección:** abre una ficha en el panel, con botón claro para volver a los
   resultados; no sustituye ni bloquea el mapa.
5. **Final del panel:** “Fuentes y metodología”, plegado inicialmente.

El scroll pertenece al panel, no a toda la aplicación. Territorio, periodo y
mapa permanecen visibles durante la exploración.

## 5. Layout móvil, 390×844

1. Cabecera de una línea con territorio, periodo y compartir.
2. Mapa visible inmediatamente, de aproximadamente 38–45 % de la altura del
   viewport y nunca oculto por el formulario inicial.
3. Resumen compacto en dos columnas o carrusel accesible.
4. Histograma horizontal con selector de fuente encima.
5. Botón “Filtros” que abre un panel inferior; los filtros activos permanecen
   visibles como chips.
6. Destacados/lista debajo del histograma.
7. La ficha seleccionada abre un bottom sheet que puede reducirse para volver a
   ver el mapa.
8. “Fuentes y metodología” queda al final, plegado.

Todos los controles táctiles deben tener al menos 44×44 CSS px. No se usa un
panel absoluto que ocupe casi todo el primer viewport.

## 6. Territorio

Se conserva España → CCAA → provincia → municipio y la jerarquía especial de
Ceuta/Melilla.

- La cabecera muestra `España / Galicia / Ourense / Cualedro` con los ancestros
  como botones y el actual como texto.
- Un único botón “Cambiar territorio” abre búsqueda/lista jerárquica; no hay
  tres selects permanentes en la primera pantalla.
- El click sobre límite y el selector llaman a la misma transición de estado.
- Un cambio explícito ejecuta `fitBounds` administrativos; un restore conserva
  center/zoom.
- Los IDs ES-2 nunca aparecen en PRIMARY.
- En municipio se muestra: “Los límites corresponden a la división
  administrativa actual”.

## 7. Periodo

La cobertura global de la UI sigue siendo 1968–2026. El estado conserva el
rango solicitado aunque una fuente cubra solo parte.

- La cabecera muestra un año (`1995`) o rango (`1993–2002`).
- Al abrir el control aparecen Desde, Hasta, un brush del histograma y
  “Periodo completo”.
- Click en una barra selecciona año único.
- Arrastrar sobre barras selecciona un rango inclusivo.
- Los inputs manuales aceptan años completos y se sincronizan con el brush.
- Escape/cancelar restaura el rango anterior; Aplicar confirma la edición
  manual. Click/drag se aplica inmediatamente y es reversible.
- La fuente sin cobertura no altera el rango ni fuerza otro año.

La selección temporal actual se representa con fondo/contorno, no solo color.

## 8. Histograma: dirección cerrada

Se elige **C: pestañas por métrica/fuente, con una sola serie visible cada vez**.
No se apilan ni suman fuentes. Las pestañas se llaman:

- `Registros EGIF`;
- `Incendios ICV` cuando aplique;
- `Perímetros Landsat`;
- `Perímetros provisionales EFFIS` cuando aplique.

### Selección de pestaña inicial

1. GVA y rango íntegro 1993–2024: ICV.
2. GVA y rango íntegro 2025–2026: EFFIS.
3. En cualquier otro rango con EGIF: EGIF.
4. Sin EGIF pero con geometría disponible: la fuente cartográfica recomendada.
5. Sin serie: se conserva el eje temporal con mensaje de disponibilidad.

Una selección explícita del usuario se mantiene mientras esa fuente sea
aplicable al territorio, aunque parte del rango quede fuera de cobertura. No
se cambia de pestaña silenciosamente.

### Representación e interacción

- Una barra = número de entidades del tipo nombrado en ese año y territorio.
- El eje no cambia de unidad dentro de la serie.
- Tooltip: `1995 · 467 incendios oficiales ICV · Comunitat Valenciana`.
- Los años fuera de cobertura tienen tramado y tooltip “sin datos de esta
  fuente”, no altura cero.
- Los años cubiertos sin resultados tienen barra cero y texto “0 resultados”.
- El rango activo queda sombreado; año único tiene foco reforzado.
- Click selecciona año; drag/teclado selecciona rango.
- Los filtros de fuente compatibles recalculan la serie; el tooltip enumera los
  filtros activos.
- El selector incluye etiqueta de fuente y enlace a metodología.

## 9. Contrato de conteos

El resumen no tiene una tarjeta `Total`.

Copy recomendado:

- `4.128 registros administrativos de incendios` — `Fuente: EGIF`;
- `467 incendios oficiales documentados` — `Fuente: ICV`;
- `N perímetros derivados de imágenes Landsat` — `Fuente: ESFire30`;
- `16 perímetros satelitales provisionales` — `Fuente: EFFIS · snapshot`;
- si ICV tiene más de una geometría por registro: `467 incendios documentados ·
  N perímetros oficiales`, en dos valores relacionados por el contrato ICV.

`Registros EGIF` y `perímetros ESFire30` se presentan en tarjetas hermanas con
una nota: “Son conjuntos distintos y no deben sumarse”. La coincidencia de
recuentos tampoco implica correspondencia uno a uno.

## 10. Contrato de superficie

Se usan etiquetas completas:

- `Superficie forestal declarada` para EGIF;
- `Superficie forestal declarada` para ICV;
- `Área del perímetro cartografiado` para ESFire30;
- `Área del perímetro satelital provisional` para EFFIS.

Cada valor incluye fuente. `null` no cuenta como cero: junto a sumas EGIF se
ofrece en SECONDARY `N de M registros con superficie conocida`. Un total solo
agrega filas de la misma fuente, misma métrica y filtros. Las cuatro magnitudes
no son combinables.

El PMTiles ESFire30 nacional actual no transporta área; esta métrica no puede
aparecer como total nacional hasta disponer del derivado pequeño especificado
en la sección de datos.

## 11. Filtro de superficie mínima

El filtro siempre pertenece a un `METRIC_ID` y una fuente. La UI muestra, por
ejemplo, `Superficie forestal declarada · ICV` o `Área cartografiada · EFFIS`.

- Presets: Todas, ≥10, ≥100, ≥500 y ≥1.000 ha.
- Campo numérico opcional para un umbral personalizado, con unidad ha.
- Nunca se aplica un mismo umbral simultáneamente a magnitudes incompatibles.
- Recalcula capa, tarjeta, histograma y destacados de la fuente objetivo.
- Las fuentes complementarias permanecen sin ese filtro y lo indican en su
  tarjeta; no se alteran silenciosamente.
- Si cambia el contexto y la fuente deja de aplicar, se retira el filtro con un
  aviso accesible: “El filtro de superficie ICV no se aplica en este territorio
  y se ha retirado”.

ESFire30 no ofrece `min_area` en P0 mientras el runtime solo tenga
`geometry_id`, año y códigos territoriales.

## 12. GIF

Jerarquía `SECONDARY`. Copy:

`Grandes incendios (GIF, ≥500 ha forestales según la fuente)`.

- EGIF usa exclusivamente `is_gif_forest_ge_500_ha`.
- ICV usa su criterio documentado sobre superficie forestal declarada.
- ESFire30 y EFFIS muestran “GIF no aplicable a esta fuente”; no se infiere a
  partir del área del polígono.
- El control se muestra solo con EGIF o ICV como fuente de análisis.
- Ayuda breve: “Clasificación administrativa; no equivale a perímetro de más de
  500 ha”.

## 13. Causas

- **ICV:** filtro y ficha con `cause_code`/literal documentado.
- **EGIF con causa canónica aprobada futura:** filtro por categoría y literal de
  fuente en metodología.
- **EGIF con literal fiable pero sin categoría:** muestra el literal en ficha,
  sin agruparlo ni ofrecer filtro nacional.
- **EGIF con solo código:** el código queda en ADVANCED; PRIMARY dice “Causa no
  interpretada” solo si el usuario consulta ese dato.
- **Sin interpretación segura:** no se muestra filtro.
- **ESFire30/EFFIS:** no se hereda causa de otra fuente.

La espera de MITECO no bloquea E3: P0 incluye causas ICV y estados parciales;
EGIF nacional sigue sin filtro canónico.

## 14. Filtros contextuales

Los controles no aplicables se ocultan en PRIMARY. El panel “Fuentes y
metodología” explica qué fuente carece del campo; no se llena la pantalla de
controles deshabilitados.

Todo filtro activo aparece como chip con fuente: `≥500 ha · ICV`, `GIF · EGIF`,
`Rayo · ICV`. Cambiar fuente de análisis no migra el filtro. Si deja de ser
válido se limpia con anuncio, nunca en silencio.

Periodo y territorio son globales. Superficie, GIF y causa son filtros de una
fuente/métrica concreta.

## 15. Destacados

La sección muestra como máximo 10 elementos de la fuente de análisis y tiene un
enlace “Ver todos”. Rankings permitidos:

- mayor superficie forestal declarada EGIF;
- mayor superficie forestal declarada ICV;
- mayor área cartografiada ESFire30 cuando exista el derivado;
- mayor área provisional EFFIS;
- GIF EGIF o ICV;
- años con más entidades de la serie activa.

El encabezado siempre nombra métrica y fuente: `Mayores superficies forestales
declaradas · ICV`. No hay ranking cross-source. Cada fila es seleccionable y
muestra año, lugar cuando exista, valor y fuente.

## 16. Ficha humana

Orden exacto:

1. **Cabecera:** fecha/año y lugar humano disponible.
2. **Tipo y fuente:** `Registro administrativo · EGIF`, `Incendio oficial ·
   ICV`, `Perímetro Landsat · ESFire30` o `Perímetro satelital provisional ·
   EFFIS`.
3. **Cuándo:** inicio y final/extinción cuando existan.
4. **Dónde:** municipio, provincia y paraje documentados; el territorio
   seleccionado puede darse como contexto, no como atributo de ignición.
5. **Magnitud:** label semántico completo y ha.
6. **Causa:** solo interpretación segura.
7. **GIF:** solo clasificación documentada.
8. **Aviso relevante:** provisionalidad, múltiple geometría, límites actuales o
   ausencia de geometría.
9. **Fuente:** una línea con entidad proveedora.
10. **“Más sobre estos datos”:** panel técnico plegado.

### Campos ausentes

- Nunca se imprime `null`, `unknown`, `No det.` ni un ID como sustituto.
- Se omite un campo opcional sin valor.
- `Causa no disponible` se muestra solo para un registro administrativo donde
  la ausencia sea informativamente relevante o si hay un filtro de causa.
- En fuentes geométricas sin causa se omite el campo y la metodología explica
  que la fuente no aporta información administrativa.
- `Municipio no resuelto en la normalización` se conserva para EGIF; el literal
  original puede aparecer separado si existe.

### Panel “Más sobre estos datos”

- fuente y nombre del producto;
- tipo de dato;
- método de obtención;
- calidad y semántica geométrica;
- identificadores de registro/geometría;
- número de geometrías documentadas cuando proceda;
- cobertura y snapshot;
- licencia, atribución y provenance.

## 17. Presentación por fuente

### EGIF

PRIMARY: año/fecha disponible, municipio/provincia, superficie forestal
declarada conocida, GIF y causa solo cuando sea interpretable. SECONDARY:
`Registro administrativo EGIF` y aviso de que no es un perímetro. ADVANCED:
`record_id`, código de causa, versión de parte y provenance.

### ESFire30

PRIMARY: perímetro, año, territorio intersectado y área cartografiada solo si
el derivado la proporciona. SECONDARY: `Perímetro obtenido mediante imágenes
Landsat. No constituye cartografía oficial`. ADVANCED: `geometry_id`, calidad
B y semántica de intersección territorial actual.

### ICV

PRIMARY: fecha, municipio/provincia/paraje, superficie forestal declarada,
causa, GIF y perímetro oficial cuando existan. SECONDARY: `Datos oficiales de
la Generalitat Valenciana`. ADVANCED: IDs, relación 1:N registro-geometrías,
provenance y atribución.

### EFFIS

PRIMARY: fecha, lugar documentado, área del perímetro y geometría. SECONDARY:
`Perímetro satelital provisional` y fecha de snapshot; para 2026: `Datos
provisionales; no representan el cierre anual`. ADVANCED: `geometry_id`, ID
EFFIS, snapshot, método, provenance y licencia.

## 18. Resto de España: EGIF + ESFire30

La experiencia normal presenta dos bloques:

> **X registros administrativos de incendios**
>
> Fuente: EGIF · No contienen perímetro individual.

> **Y perímetros derivados de imágenes Landsat**
>
> Fuente: ESFire30 · Pueden intersectar más de un territorio.

Nota común: `Los registros y los perímetros son conjuntos independientes; no
se suman ni existe correspondencia automática entre ellos.`

El mapa usa ESFire30 cuando tiene cobertura. La lista EGIF sigue siendo
seleccionable y su DETAIL continúa lazy.

## 19. Coverage, carga, cero y errores

| Estado interno | Copy público | Visibilidad |
| --- | --- | --- |
| `idle` | nada | oculto |
| `loading` | `Cargando registros…`, `Cargando perímetros…` | solo en el bloque afectado |
| `ready` | nada; aparece el contenido | oculto |
| `error` | `No hemos podido cargar [dato]. El resto del Atlas sigue disponible.` + Reintentar | bloque afectado |
| `no_coverage` | `No disponemos de [tipo de dato] para este periodo.` | resumen secundario si es relevante |
| `not_integrated` | `Esta fuente todavía no está disponible en este territorio.` | solo panel de fuentes |
| `zero_relations` | `No hay perímetros de esta fuente que intersecten el territorio en el periodo seleccionado.` | resultado principal de esa fuente |

Reglas:

- 0 cubierto: `No hay registros que cumplan estos filtros.`
- Sin datos: `No disponemos de registros de esta fuente para este periodo.`
- Cobertura parcial: `Periodo solicitado: 1980–1990. Perímetros Landsat
  disponibles: 1985–1990.`
- España 1975: `Disponemos de registros administrativos, pero no de perímetros
  cartografiados para este periodo.`
- ICV/EFFIS fuera de GVA no generan avisos permanentes; aparecen como no
  disponibles solo al abrir “Fuentes y metodología”.

## 20. Mapa base y leyenda

GVA usa Leaflet 1.9.4 y teselas estándar OpenStreetMap con atribución. Se
recupera su **contexto**, no se prescribe copiar sin revisión el endpoint:

- fondo claro y poco saturado;
- costa, poblaciones, carreteras principales y topónimos legibles;
- límites BDLJE actuales con contraste moderado;
- perímetros por encima del fondo;
- selección con contorno y patrón, no solo color;
- atribución siempre visible.

E3 debe usar una fuente cartográfica compatible con MapLibre y revisar las
condiciones operativas del proveedor antes de E4. No se contrata un proveedor
en E2 ni se vuelve a Leaflet.

### Leyenda

La leyenda visible contiene solo capas dibujadas:

- límite del territorio actual;
- perímetro oficial ICV;
- perímetro Landsat ESFire30;
- perímetro provisional EFFIS;
- gradiente temporal o selección, si se usa;
- elemento seleccionado.

Cada ítem combina color, trazo/patrón y texto. EGIF se explica junto a sus
tarjetas/lista, no con un símbolo geométrico inexistente. Cobertura, licencias
y estado del loader no pertenecen a la leyenda.

## 21. Panel “Fuentes y metodología”

Plegado por defecto. Para cada fuente:

- nombre público y proveedor;
- tipo de entidad;
- periodo y territorio disponibles;
- activa/inactiva y control de visibilidad;
- explicación corta de lo que aporta y lo que no;
- enlace a método/licencia/provenance;
- advertencia de provisionalidad o cobertura histórica.

El modo avanzado añade IDs y calidad al detalle seleccionado, pero no muestra
diagnósticos internos de desarrollo. Activar una fuente complementaria cambia
solo su capa/tarjeta; no crea relaciones con las demás.

## 22. Interacción mapa ↔ histograma ↔ filtros

1. Cambiar territorio actualiza límite, fuente recomendada, resumen,
   histograma, filtros aplicables, destacados y mapa.
2. Cambiar periodo actualiza todas las fuentes por sus intersecciones de
   cobertura; nunca cambia el rango solicitado.
3. Cambiar pestaña de histograma cambia la fuente de análisis, los filtros y
   destacados, no las identidades ni el periodo.
4. Aplicar un filtro recalcula solo la fuente/métrica indicada en mapa,
   tarjeta, histograma y destacados.
5. Seleccionar un elemento en mapa o lista abre su ficha independiente.
6. Una selección invalidada por tiempo, territorio, filtro o visibilidad se
   limpia solo dentro de su fuente.
7. Compartir serializa territorio, periodo, mapa, fuentes, fuente de análisis,
   filtros y selecciones válidas.

Las tarjetas principales siempre representan territorio + periodo + filtros.
Un dato basado en viewport debe llamarse explícitamente `Visibles en el mapa`
y queda como diagnóstico secundario, nunca como KPI.

## 23. Data contracts y rendimiento UX

### Histograma

| Fuente | Estado | Contrato |
| --- | --- | --- |
| EGIF | `READY` | España/CCAA desde manifest (`scan_blocks`/`year_spools`); provincia/municipio desde INITIAL ya requerido. |
| ICV | `DERIVABLE_CHEAPLY` | `fires.json` contiene 13.738 registros y año; conviene resumen pequeño para evitar cargar 7,66 MB solo por el primer histograma. |
| EFFIS | `READY` | manifest y 25 features publican año/recuento/área; provincia/municipio se agregan tras su carga pequeña. |
| ESFire30 | `NEEDS_NEW_DERIVED_ASSET` | PMTiles permite filtrar mapa, pero no contar todo el territorio; derivar año × territorio desde relaciones cerradas, sin intersección nueva. |

### Resumen

| Métrica | Estado | Acción E3 |
| --- | --- | --- |
| EGIF count | `READY` | usar manifest/INITIAL según ámbito. |
| EGIF superficie/GIF | `READY_AFTER_INITIAL` fuera de España | crear resumen nacional/CCAA pequeño para primer paint y España. |
| EGIF causas | `BLOCKED_EXTERNAL` para categorías nacionales | no bloquear UI; solo ICV y futuros valores aprobados. |
| ICV count/superficie/GIF/causa | `DERIVABLE_CHEAPLY` | agregar `fires.json`; resumen pequeño recomendado. |
| EFFIS count/área | `READY` | manifest/features pequeños. |
| ESFire30 count anual/territorial | `NEEDS_NEW_DERIVED_ASSET` | agregar relaciones existentes + año. |
| ESFire30 área/destacados | `NEW_PIPELINE_WORK` | derivar de geometría canónica/atributos, sin modificar PMTiles ni recalcular territorio. |

### Derivado pequeño requerido

Contrato conceptual `national-ux-summary-v1`, determinista y versionado:

- fuente, territorio, año y tipo de entidad;
- count;
- suma de la magnitud documentada y known/unknown cuando proceda;
- GIF count solo para fuente válida;
- cause counts solo para mapeos aprobados;
- top-N de IDs propios por métrica válida;
- cobertura/snapshot y checksums de inputs.

Se publica nacional/CCAA en un asset pequeño y los resúmenes
provincia/municipio se shardean por provincia cuando no se puedan calcular del
asset ya cargado. No contiene geometrías ni relaciones cross-source.

## 24. Vocabulario público

| Técnico | Público principal |
| --- | --- |
| `source_record` | registro |
| `fire_geometry` | perímetro |
| `coverage` | datos disponibles |
| `no_coverage` | no disponemos de este tipo de dato para el periodo |
| `not_integrated_for_territory` | oculto; “fuente todavía no disponible aquí” en metodología |
| `geometry quality` | cómo se obtuvo el perímetro |
| `intersection relation` | perímetro que intersecta el territorio |
| `declared area` | superficie forestal declarada |
| `mapped area` | área del perímetro cartografiado |
| `provisional` | datos provisionales; indicar snapshot/corte |
| `INITIAL/DETAIL` | no visible |

### Política de “incendio”

- Título y prosa: `Atlas de incendios` y `Explora incendios registrados y
  perímetros disponibles` son comprensibles.
- EGIF: `registros administrativos de incendios` o `incendios registrados en
  EGIF`, siempre con fuente.
- ICV: `incendios oficiales documentados por la Generalitat` para sus source
  records; `perímetros oficiales ICV` para geometrías.
- ESFire30: `perímetros Landsat`, nunca “incendios ESFire30”.
- EFFIS: `perímetros satelitales provisionales`, no un cierre de incendios.
- Nunca: `Total de incendios` sumando fuentes.

## 25. Wireframe desktop

```text
┌ Atlas histórico ─ España / Galicia / Ourense ─ 1995 ─ [Compartir] ┐
├──────────────────────────────────────────────┬─────────────────────┤
│ MAPA BASE + TOPÓNIMOS                        │ RESUMEN             │
│ límite administrativo                        │ fuente principal    │
│ perímetros recomendados                      │ tarjetas separadas  │
│ selección                                    ├─────────────────────┤
│                                              │ EVOLUCIÓN           │
│ LEYENDA humana                               │ [EGIF][ESFire30]    │
│                                              │ histograma + brush  │
│                                              ├─────────────────────┤
│                                              │ FILTROS aplicables  │
│                                              ├─────────────────────┤
│                                              │ DESTACADOS / LISTA  │
│                                              ├─────────────────────┤
│                                              │ ▸ Fuentes y método  │
└──────────────────────────────────────────────┴─────────────────────┘

Al seleccionar: RESUMEN/EVOLUCIÓN se mantienen accesibles y la zona
DESTACADOS se convierte en FICHA HUMANA con “Más sobre estos datos” plegado.
```

## 26. Wireframe móvil

```text
┌ España / Galicia ▾      1995 ▾       Compartir ┐
├────────────────────────────────────────────────┤
│ MAPA + LÍMITE + PERÍMETROS                     │
│ Leyenda compacta                               │
├────────────────────────────────────────────────┤
│ RESUMEN: tarjetas tipadas por fuente           │
├ [EGIF] [ESFire30] ─ HISTOGRAMA / rango ────────┤
├ [Filtros (2)]  chips: GIF · EGIF               ┤
├ DESTACADOS / RESULTADOS                        ┤
├ ▸ Fuentes y metodología                        ┤
└────────────────────────────────────────────────┘

Selección → bottom sheet: cabecera humana, campos principales,
▸ Más sobre estos datos. Se puede minimizar sin perder la selección.
```

## 27. Estados de ejemplo

### A. España · 1975

- `4.128 registros administrativos de incendios · EGIF` (dato manifest).
- Histograma: EGIF, barra 1975 = 4.128.
- Mapa: límites y base, sin perímetro de incendio.
- Mensaje: `Disponemos de registros administrativos, pero no de perímetros
  cartografiados para este periodo.`

### B. España · 1995

- `25.557 registros administrativos · EGIF` (dato manifest).
- `<N> perímetros Landsat · ESFire30` desde el nuevo resumen.
- Histograma inicial EGIF; pestaña ESFire30 disponible.
- Ningún total combinado.

### C. Comunitat Valenciana · 1995

- `467 incendios oficiales documentados · ICV` (dato existente).
- `467 registros administrativos · EGIF` (dato manifest nacional).
- `<N> perímetros Landsat · ESFire30` como complementario.
- ICV es mapa/histograma recomendado. La coincidencia 467/467 no expresa
  correspondencia entre registros.

### D. Comunitat Valenciana · 2024

- `472 incendios oficiales documentados · ICV`.
- Mapa e histograma ICV.
- EGIF y ESFire30 no generan tarjetas negativas en PRIMARY.

### E. Comunitat Valenciana · 2026

- `16 perímetros satelitales provisionales · EFFIS`.
- Aviso: snapshot adquirido el 19/08/2026, con observaciones hasta el
  08/08/2026; no es cierre anual.
- Histograma y mapa EFFIS.

### F. Elx · 2025

- `1 perímetro satelital provisional · EFFIS` en el snapshot actual.
- Límite municipal actual y aviso histórico.
- No se presentan como cero EGIF/ICV/ESFire30 fuera de cobertura.

### G. Canarias · 1995

- `56 registros administrativos · EGIF` para la CCAA (dato manifest).
- `ESFire30 no cubre Canarias`; copy principal: `Disponemos de registros
  administrativos, pero esta fuente no ofrece perímetros para Canarias.`
- Límite administrativo actual y mapa base siguen operativos.

## 28. Flujos prioritarios

### España → Galicia → 1995 → GIF → ficha → compartir

1. El usuario abre España y ve mapa, resumen e histograma EGIF.
2. “Cambiar territorio” → Galicia; el mapa hace fit administrativo.
3. Click en 1995; todas las fuentes conservan sus coberturas independientes.
4. Fuente de análisis EGIF → filtro `Grandes incendios (GIF)`.
5. Histograma, tarjeta y lista EGIF se actualizan; ESFire30 permanece como
   perímetro independiente y no recibe el filtro GIF.
6. Selecciona un registro; DETAIL se carga lazy y abre ficha humana.
7. Compartir serializa territorio, año, fuente de análisis, GIF y selección.

### Permalink GVA antiguo → ficha → enlace nacional

1. Compatibilidad `#v=1` traduce periodo, territorio, filtros y selección.
2. El mapa conserva center/zoom restaurados y no ejecuta fitBounds.
3. La ficha ICV se presenta en formato humano; causa y superficie disponibles
   no quedan ocultas tras IDs.
4. Compartir crea el estado nacional actual con filtros y selección, sin
   reescribir el enlace antiguo.

## 29. Accesibilidad mínima obligatoria

- contraste AA para texto y controles; contraste suficiente de líneas sobre el
  mapa;
- color acompañado de patrón, trazo, icono o label;
- headings y landmarks coherentes;
- labels visibles para territorio, periodo y filtros;
- navegación por teclado de breadcrumb, tabs, histograma, resultados y ficha;
- barras del histograma con `aria-label` completo y selección con
  `aria-pressed`/equivalente;
- foco visible y retorno de foco al cerrar drawer/ficha;
- regiones `aria-live` para cargas, retirada de filtros y errores;
- objetivos táctiles mínimos de 44×44 CSS px;
- alternativa textual al mapa mediante lista y resumen.

## 30. GVA_ELEMENTS_NOT_TO_REINTRODUCE

- arquitectura limitada al País Valencià;
- descarga/representación GeoJSON completa como estrategia nacional;
- filtro `min_area` único aplicado a magnitudes distintas;
- abstracción visual que haga parecer equivalentes registros y perímetros;
- cálculo de conteos desde lo cargado/visible;
- fit territorial derivado de incendios en lugar de límites oficiales;
- pérdida de `null != 0`;
- dependencia de geometría para poder listar un registro;
- badge `overview` y estados de depuración públicos;
- endpoint de teselas OSM estándar como decisión de hosting no revisada;
- ficha y lista sin paginación/virtualización a escala nacional.

## 31. NATIONAL_CAPABILITIES_MUST_PRESERVE

- España → CCAA → provincia → municipio y bounds BDLJE;
- estado central e invariantes territoriales;
- rango solicitado y cobertura independiente por fuente;
- separación `record_id` / `geometry_id` y selecciones independientes;
- EGIF CCAA × bloque, columnar y DETAIL lazy;
- PMTiles ESFire30 por Range y filtros CCAA/provincia embebidos;
- índice municipal ESFire30 por shard provincial;
- geometría municipal lazy y semántica de límite actual;
- ICV 1:N y EFFIS provisional sin enlaces cross-source;
- caché, AbortController, generation tokens y errores aislados;
- serializer nacional, restore exacto, back/forward y compatibilidad GVA v1;
- provenance, licencias, calidad y atribución;
- semántica `sin cobertura != cero`;
- 83 geometrías ESFire30 sin municipio sin asignación artificial.

## 32. Prioridad de implementación

### P0 — producto válido

- shell desktop/móvil con mapa dominante;
- territorio, periodo y compartir visibles;
- mapa base contextual y leyenda humana;
- vista recomendada por contexto;
- tarjetas separadas y mensajes humanos;
- histograma con tabs y selección año/rango;
- contratos de filtros contextuales, al menos superficie/GIF/causa donde ya son
  seguros;
- ficha humana para las cuatro fuentes;
- fuentes/metodología plegadas;
- estados loading/error/cobertura/cero traducidos;
- serialización/restauración de nueva fuente de análisis y filtros;
- derivado pequeño imprescindible para conteos ESFire30 territoriales;
- accesibilidad y móvil utilizables;
- todas las capacidades nacionales listadas en la sección 31.

### P1 — exploración completa

- rankings/destacados para todas las magnitudes disponibles;
- resumen compacto ICV/EGIF para acelerar first paint;
- área y filtro `min_area` ESFire30 mediante derivado aprobado;
- desglose known/unknown y cobertura histórica ampliados;
- transiciones refinadas, comparación visual de fuentes complementarias y
  lista completa de resultados.

### P2 — mejoras posteriores

- más visualizaciones temporales sin mezclar fuentes;
- preferencias persistentes de vista avanzada;
- comparación lado a lado de dos series;
- mejoras editoriales/animaciones no necesarias para comprender los datos;
- futuras causas EGIF canónicas cuando exista contrato externo.

## 33. Clasificación del trabajo de datos

### UX_ONLY

- jerarquía, layouts, copy, cards, paneles plegables y leyenda;
- ocultar estados internos;
- orden de ficha y política de ausencias;
- mensajes coverage/cero/error;
- wireframes y vista recomendada.

### FRONTEND_LOGIC

- resolver fuente recomendada por contexto;
- tabs y brush del histograma;
- filtros con `metric_id` y fuente;
- coordinación mapa/resumen/histograma/destacados;
- ficha humana y panel técnico;
- nueva lista/destacados sin materializar objetos masivos;
- serialización de análisis/filtros y compatibilidad legacy;
- accesibilidad, focus y drawers móviles.

### SMALL_DERIVED_DATA

- annual count ESFire30 por territorio;
- resúmenes EGIF nacionales/CCAA de count, superficie known/unknown y GIF;
- resumen ICV anual/territorial compacto para no depender de 7,66 MB en first
  paint;
- top-N por fuente y métrica válida;
- sharding provincial para resúmenes municipales cuando el asset existente no
  baste.

### DATA_PIPELINE_CHANGE

- builder determinista `national-ux-summary-v1`, con manifest, checksums,
  `--resume` y `--check`;
- unión por IDs propios con año/territorio ya calculados, sin nueva
  intersección;
- obtención de área ESFire30 desde geometría/atributo canónico para agregados y
  destacados, sin alterar PMTiles;
- publicación del derivado pequeño en el futuro artifact E3/E4.

### BLOCKED_EXTERNAL

- ontología canónica nacional EGIF pendiente de MITECO;
- CCINIF y su permiso/publicación;
- geometría y equivalencias municipales históricas;
- resolución documental de 71.490 `municipality_id = null` EGIF;
- modelo de episodio y links cross-source.

Ningún bloqueo externo impide implementar P0. Las funcionalidades afectadas se
ocultan o se presentan como parciales.

## 34. Alcance exacto de ES-4E3

E3 debe implementar P0 sobre una copia/evolución local del frontend nacional:

1. shell y responsive nuevos;
2. vista recomendada contextual;
3. mapa base y leyenda;
4. resumen tipado por fuente;
5. histograma de pestaña única con año/rango;
6. filtros source-aware ya seguros;
7. destacados mínimos y fichas humanas;
8. fuentes/metodología progresivas;
9. mensajes públicos y accesibilidad;
10. extensión compatible del estado/permalink;
11. builder y consumo de los derivados P0 pequeños;
12. tests unitarios/integación y candidato local separado.

E3 no autoriza cambios de raíz, producción, staging D4B, source linking,
ontología, PMTiles, geometrías ni datasets fuente. Tras E3 se requiere
`ES-4E4_PRODUCT_STAGING_ACCEPTANCE`; solo después puede reconsiderarse D5.

## 35. Criterios de aceptación de E3 derivados de esta especificación

- Un usuario puede resolver las tareas E1 A–N sin abrir metodología, salvo
  provenance detallada.
- No existe métrica cross-source sumada.
- El mapa es visible en el primer viewport desktop y móvil.
- Todas las cifras principales son territoriales, no de viewport.
- Histograma, filtros, tarjetas y destacados comparten fuente/métrica explícita.
- Ausencia de cobertura y cero resultados producen mensajes distintos.
- Las cuatro fichas ocultan IDs inicialmente y preservan sus semánticas.
- Restauración legacy y nacional mantiene center/zoom y filtros válidos.
- El panel avanzado conserva la potencia técnica sin dominar la vista.
- El runtime sigue cargando datos de forma progresiva y con errores aislados.

`NEXT_PHASE = ES-4E3_NATIONAL_UX_IMPLEMENTATION`. No se inicia en E2.
