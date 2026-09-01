# ES-4E1 — Auditoría UX/producto GVA frente al staging nacional

## Decisión

`ROOT_SWITCH_UX_STATUS = BLOCKED_BY_MAJOR_PRODUCT_REGRESSIONS`.

El release candidate nacional es una base técnica válida, pero todavía no es
un producto público mejor que el visor valenciano. La dirección recomendada es
**recuperar sustancialmente el layout, la jerarquía y el flujo exploratorio de
GVA sobre el runtime nacional**, preservando la navegación territorial, la
carga progresiva, las identidades, coberturas y fuentes independientes del
nacional.

No se propone volver al backend valenciano ni fusionar fuentes. Se propone que
la complejidad del motor deje de ocupar el primer nivel de lectura.

## Método y límites

El 1 de septiembre de 2026 se abrieron en Chromium las dos aplicaciones reales:

- producción GVA: <https://inthurain.github.io/atlas-incendios/>;
- staging nacional: <https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/>.

Se observaron las primeras pantallas desktop 1440×1000 y móvil 390×844. Se
usaron controles reales para seleccionar 2022 y superficie mínima de 500 ha en
GVA, recorrer España → País Valencià → Alacant → Elx en nacional y abrir en
ambos el fixture compartido `2024AL0005`. También se inspeccionaron periodo,
histograma, filtros, métricas, fichas, fuentes, atribución y enlace compartido.

Esta es una auditoría de producto, no un test de rendimiento ni una revisión
del modelo de datos. No se modificó ninguna aplicación.

## Primera pantalla

### GVA

En desktop el usuario ve simultáneamente un mapa cartográfico reconocible, el
territorio, el periodo 1968–2026, los filtros de ámbito/municipio/superficie/
causa/GIF, el histograma y parte del control de fuentes. El mapa ocupa la mayor
parte de la pantalla, incorpora topónimos y una leyenda visible. Aunque la
barra lateral es larga, sus primeras secciones responden a preguntas humanas.

En la carga observada se muestran, por fuente y sin fusionarlas, 9.175 partes
EGIF, 710 perímetros ESFire30, 13.738 incendios ICV, 13.739 perímetros ICV y 25
perímetros EFFIS, además de superficies y GIF. Estas métricas quedan algo por
debajo del primer pliegue, pero los filtros y el histograma anuncian de forma
inmediata qué puede explorarse.

### Nacional

En desktop la primera columna está dominada por tres selectores territoriales,
dos campos numéricos con botón Aplicar, cuatro checkboxes de fuentes, un texto
metodológico y el comienzo de “Estado de fuentes”. El mapa no tiene mapa base
ni topónimos: España aparece como silueta y nube de perímetros sobre fondo
neutro, sin una leyenda pública equivalente a GVA.

El primer resumen nacional observado dice, entre otros, “fuentes: ESFire30
ready, EGIF ready, municipios idle”, “EGIF INITIAL: 0 asset(s)” y “visibles en
viewport: 31.541”. Son datos útiles para validar el runtime, pero desplazan la
respuesta a “qué ocurrió, cuándo y cuánto”.

En móvil GVA abre con el mapa, leyenda y atribución antes del panel. El nacional
abre con una tarjeta que ocupa prácticamente todo el viewport; el mapa queda
oculto detrás del formulario y el usuario empieza gestionando fuentes.

## Tareas de usuario

| Tarea | GVA | Nacional | Motivo principal |
| --- | --- | --- | --- |
| Ver los incendios de un año | EASY | ACCEPTABLE | GVA: barra de histograma o sliders; nacional: escribir año dos veces y Aplicar. |
| Saber cuántos hay | EASY | DIFFICULT | GVA muestra métricas separadas; nacional mezcla resumen EGIF, elementos cargados y visibles en viewport en texto técnico. |
| Ver superficie afectada | EASY | DIFFICULT | GVA ofrece totales por fuente; nacional solo expone bien la superficie EGIF al bajar a CCAA/provincia/municipio. |
| Identificar grandes incendios | EASY | NOT_AVAILABLE | GVA tiene filtro, GIF y lista ordenada; nacional no ofrece flujo equivalente. |
| Ver causas | EASY | NOT_AVAILABLE | GVA filtra y muestra causa; nacional no tiene exploración de causas y la ficha ICV omite un dato disponible. |
| Entender evolución temporal | EASY | DIFFICULT | GVA tiene histograma interactivo; nacional ofrece distribución EGIF como texto largo solo en ámbitos cargados. |
| Seleccionar y entender ficha | EASY | DIFFICULT | La selección nacional funciona, pero presenta identidad técnica antes que información humana. |
| Filtrar por superficie | EASY | NOT_AVAILABLE | No existe control nacional. |
| Filtrar GIF | EASY | NOT_AVAILABLE | El booleano aparece en registros EGIF, pero no como filtro nacional. |
| Navegar provincia/municipio | ACCEPTABLE | EASY | El nacional aporta jerarquía oficial, límites, bounds, breadcrumb y estado serializable. |
| Cambiar periodo | EASY | ACCEPTABLE | Sliders/histograma frente a campos numéricos + Aplicar. |
| Entender el mapa | EASY | DIFFICULT | GVA tiene mapa base y leyenda; nacional exige conocer fuentes y carece de contexto cartográfico suficiente. |
| Saber de dónde vienen los datos | ACCEPTABLE | EASY | Nacional es más riguroso y explícito, pero da demasiado protagonismo a esta capa. |
| Compartir estado | EASY | ACCEPTABLE | Ambos funcionan; el nacional preserva más estado y compatibilidad legacy, pero el control está más abajo. |

No se usa “NOT_AVAILABLE” para negar que el dato exista: significa que la
tarea no puede realizarse en la interfaz actual de forma funcional.

## Métricas, histograma y filtros

### Conteos

GVA presenta tarjetas separadas por fuente. No construye un falso total: habla
de partes EGIF, perímetros ESFire30, incendios/perímetros ICV y perímetros
EFFIS. Esta es la referencia correcta para el nacional.

El nacional conserva la separación semántica, pero la expresa como estado del
runtime. En España se observó “554.384 partes EGIF disponibles” y 0 INITIAL;
para Elx, 178 partes EGIF, 12 geometrías ESFire30 visibles en viewport y 157
perímetros ICV. “Visibles en viewport” no equivale al total territorial y no
debería ser la cifra principal.

### Superficie

GVA muestra superficies por fuente y cambia los resultados con los filtros. Al
seleccionar 2022 mostró 292 incendios/perímetros ICV y 30.113,78 ha declaradas;
con mínimo 500 ha, 4 y 29.491,9 ha. La interacción comunica de inmediato el
efecto del filtro.

El nacional puede sumar correctamente superficie forestal EGIF conocida y
preserva `null != 0`, pero no ofrece una experiencia equivalente para las
otras fuentes. Debe evitarse un total combinado: superficie administrativa
declarada y área cartografiada son métricas distintas.

### Histograma

El histograma GVA tiene 59 años, series por fuente sin sumarlas, tooltips
semánticos y selección de año con un clic. Aporta contexto histórico, detecta
años graves y convierte el tiempo en navegación. Debe recuperarse como elemento
principal del nacional, con series y etiquetas explícitas por fuente.

El listado textual nacional “1985: 1 · 1986: 1…” es auditable, pero no sirve
como instrumento principal de exploración.

### Superficie mínima y GIF

`min_area` de GVA ofrece todas, ≥10, ≥100, ≥500 y ≥1.000 ha. Filtra mapa,
conteos, superficie y destacados. Su utilidad es alta, pero la futura versión
nacional debe aplicarlo por magnitud documentada y mostrar si se trata de
superficie EGIF declarada o área de perímetro cartografiada.

El control GIF usa el umbral administrativo de 500 ha forestales en EGIF y el
campo/criterio aprobado para ICV. Debe volver como **SECONDARY**, con la etiqueta
pública “Grandes incendios (GIF, ≥500 ha según la fuente)” y explicación por
fuente. No debe inferirse desde ESFire30/EFFIS.

### Causas

GVA ofrece filtro, recuento indirecto y causa en ficha/destacados. Las categorías
son útiles, aunque ya advierten separaciones como “Accidental” frente a
“Negligencias y causas accidentales”.

La necesidad de usuario es nacional; la capacidad actual es parcial. ICV tiene
causa documentada, EGIF conserva `cause_source_code` pero la ontología nacional
definitiva sigue bloqueada, y ESFire30/EFFIS no deben presentar una causa de
episodio. E2 debe diseñar el hueco y los estados, no inventar el diccionario.

## Ficha: humana frente a técnica

Para `2024AL0005`, GVA muestra primero:

- ICV · oficial consolidado;
- fechas de inicio y extinción;
- municipio, provincia y paraje;
- causa;
- superficie forestal;
- advertencia de geometría duplicada;
- “Más información técnica”.

El nacional muestra primero `geometry_id`, `source record`, códigos internos y
calidad geométrica. Después aparecen fecha, territorio, paraje y superficie;
la causa “Intencionado”, disponible en GVA para el mismo dato, no aparece. La
ficha nacional es mejor para auditar identidad, pero peor para comprender el
incendio.

Modelo recomendado de ficha humana, sin crear un episodio canónico:

1. fecha/año, lugar, superficie y causa cuando existan;
2. tipo de elemento y fuente en una línea corta;
3. aviso relevante de cobertura/calidad;
4. panel expandible con IDs, semántica, método, licencia y provenance;
5. relaciones o geometrías alternativas como elementos independientes, nunca
   como fusión implícita.

## Fuentes y estados

| Elemento nacional actual | Jerarquía recomendada |
| --- | --- |
| Fuente aplicable al elemento y carácter oficial/provisional | PRIMARY, en una línea breve |
| Cobertura temporal disponible y ausencia relevante | SECONDARY |
| Toggles de fuentes | ADVANCED, salvo una selección contextual simple |
| Atribución/licencia y metodología | ADVANCED/METHODOLOGY |
| `ready`, `idle`, `loading`, asset/shard/INITIAL/DETAIL | DEBUG-LIKE; solo loading/error debe traducirse a lenguaje público |
| `source_record`, `geometry_id`, códigos, semántica geométrica | ADVANCED |
| Error de una fuente | SECONDARY y aislado, redactado en lenguaje humano |

“Sin cobertura para este periodo” debe traducirse como “No disponemos de este
tipo de dato para 2024” y conservar el enlace metodológico. “No integrado para
este territorio” puede ser “Esta fuente todavía no está disponible aquí”. Un
municipio continental con cobertura y cero relaciones sí puede decir “No hay
perímetros disponibles para este periodo y municipio”.

## Fortalezas y regresiones

### GVA_STRENGTHS, por prioridad

1. resumen histórico y mapa comprensible desde los primeros segundos;
2. histograma temporal accionable;
3. filtros de superficie, causa y GIF;
4. métricas separadas por fuente y respuesta visible al filtro;
5. ficha centrada en fecha, lugar, superficie y causa;
6. lista de grandes elementos destacados;
7. mapa base, leyenda y simbología temporal;
8. compartir vista visible y lenguaje generalmente humano.

### NATIONAL_STRENGTHS

1. navegación España → CCAA → provincia → municipio con límites oficiales;
2. arquitectura nacional progresiva y estable;
3. separación rigurosa de registros, geometrías, fuentes e identidades;
4. coberturas temporales y territoriales explícitas;
5. filtros ESFire30 nacionales por CCAA/provincia/municipio;
6. EGIF columnar, selección y DETAIL lazy;
7. estado serializado completo, restore y compatibilidad `#v=1`;
8. cancelación, caché, errores aislados y provenance completa;
9. soporte correcto de datos parciales y territorios sin ESFire30.

### NATIONAL_PRODUCT_REGRESSIONS

**MAJOR**

- no hay overview humano con conteos/superficies/grandes incendios;
- desaparecen histograma, superficie mínima, GIF y causas como herramientas;
- el mapa pierde base cartográfica, topónimos y leyenda clara;
- la ficha prioriza IDs y semántica técnica y omite información útil disponible;
- fuentes y estados del runtime dominan la primera pantalla;
- en móvil el formulario cubre casi todo el mapa.

**MODERATE**

- cambio temporal menos directo y sin contexto histórico;
- distribución anual como texto difícil de escanear;
- “visibles en viewport” compite con conteos territoriales;
- Copy Link y la información útil aparecen tras controles técnicos.

**MINOR**

- aspecto de formulario/prototipo;
- redundancia entre explicación territorial, fuentes y estado;
- términos ingleses/internos visibles.

La navegación territorial, cobertura precisa, permalinks y separación de
fuentes son `IMPROVEMENT`, no regresiones.

## Matriz global

| Feature | GVA | Nacional | Mejor versión | Importancia | Dirección |
| --- | --- | --- | --- | --- | --- |
| Overview | fuerte | técnico | GVA | crítica | recrear sobre métricas nacionales separadas |
| Conteos | por fuente | fragmentados | GVA | crítica | tarjetas semánticas por fuente/contexto |
| Superficie | por fuente | EGIF parcial en UI | GVA | alta | magnitudes separadas y etiquetadas |
| Histograma | interactivo | ausente | GVA | crítica | recuperar como navegación principal |
| Min area | sí | no | GVA | alta | filtro contextual por magnitud válida |
| GIF | filtro | dato sin filtro | GVA | media-alta | control secundario, definición por fuente |
| Causa | filtro/ficha | no exploración | GVA | alta | diseño parcial y honesto |
| Territorio | GVA | España→municipio | nacional | crítica | conservar íntegro |
| Tiempo | sliders + histograma | inputs | GVA | alta | combinar rango nacional e histograma |
| Mapa | base + leyenda | geometría sin contexto | GVA | crítica | base sobria, leyenda y territorio oficial |
| Ficha | humana | técnica | GVA | crítica | ficha humana + detalle técnico plegable |
| Fuentes/metodología | accesible | protagonista | combinación | alta | resumen corto + panel avanzado |
| Cobertura | extensa | precisa | nacional | alta | conservar lógica, simplificar lenguaje |
| Permalink | simple | completo/legacy | nacional | alta | conservar motor, elevar Compartir |
| Mobile | mapa primero | panel primero | GVA | alta | mapa y resumen accesibles, controles plegables |
| Atribución | completa | completa | empate | obligatoria | conservar |

## Disponibilidad de datos para el diseño

**AVAILABLE_NATIONALLY**

- territorio actual y navegación administrativa;
- periodo solicitado y coberturas por fuente;
- conteos EGIF de partes y GIF administrativos;
- superficie forestal EGIF conocida/desconocida;
- distribución anual EGIF;
- perímetros ESFire30, año e intersecciones territoriales;
- selección, identidad, provenance, permalink y atribución.

**PARTIALLY_AVAILABLE / AVAILABLE_ONLY_SOME_SOURCES**

- superficie: declarada EGIF/ICV frente a cartografiada ESFire30/EFFIS;
- fecha exacta, municipio, paraje y causa;
- GIF;
- conteo de incendios identificados frente a partes/perímetros;
- datos oficiales valencianos ICV 1993–2024 y EFFIS reciente valenciano.

**AVAILABLE_ONLY_GVA EN LA EXPERIENCIA ACTUAL**

- histograma interactivo multi-fuente;
- filtros públicos de superficie, causa y GIF;
- overview de métricas por fuente;
- lista de grandes elementos;
- ficha humana ICV con causa;
- mapa base/leyenda actual integrada.

**BLOCKED_BY_DATA**

- ontología canónica nacional de causas pendiente de MITECO;
- episodio/incendio único cross-source;
- equivalencia automática EGIF ↔ ESFire30/ICV/EFFIS;
- geometrías municipales históricas;
- convertir los 71.490 municipios EGIF no resueltos;
- total nacional único de “incendios” o de “superficie quemada” mezclando
  magnitudes incompatibles.

## Jerarquía propuesta

### PRIMARY UI

- territorio y periodo;
- mapa con contexto cartográfico y leyenda;
- resumen con métricas humanas disponibles y claramente tipadas;
- histograma/timeline;
- filtros de exploración aplicables;
- lista breve de grandes elementos/resultados;
- ficha humana del elemento seleccionado;
- Compartir.

### SECONDARY UI

- selector territorial detallado y breadcrumb;
- desglose por fuente de conteos/superficies;
- cobertura/ausencia explicada en lenguaje humano;
- GIF y filtros que no aplican a todas las fuentes;
- fuentes complementarias/alternativas para el elemento;
- avisos de provisionalidad y límites históricos.

### ADVANCED / METHODOLOGY UI

- toggles individuales de datasets;
- IDs, `source_record`, `geometry_id` y códigos;
- calidad/semántica geométrica completa;
- cobertura técnica, licencia, transformaciones y provenance;
- estados de loader, assets, shards, INITIAL/DETAIL y diagnóstico.

## Wireframe conceptual

```text
┌ Atlas histórico de incendios ─ Territorio ▾ ─ 1968—2026 ─ Compartir ┐
├───────────────────────────────────────────────┬───────────────────────┤
│                                               │ RESUMEN               │
│ MAPA + TOPÓNIMOS + LÍMITE + LEYENDA           │ partes registrados    │
│                                               │ perímetros disponibles│
│                                               │ superficie (tipada)   │
│                                               │ grandes incendios     │
├───────────────────────────────────────────────┴───────────────────────┤
│ HISTOGRAMA POR FUENTE · seleccionar año/rango                        │
├ Filtros: superficie · grandes incendios · causa disponible           ┤
├ RESULTADOS DESTACADOS / LISTA                                        ┤
├ FICHA HUMANA: fecha · lugar · superficie · causa · fuente breve      ┤
└ ▸ Fuentes, cobertura y metodología                                   ┘
```

En móvil: mapa/resumen primero, una barra compacta de territorio-periodo y un
panel inferior o secciones plegables. La navegación territorial nacional se
conserva; no debe ocupar el viewport completo antes de ver el mapa.

## Alcance exacto recomendado para ES-4E2

E2 debe ser una especificación de diseño, todavía sin implementación:

1. modelo de información y vocabulario público por nivel;
2. definición semántica de cada tarjeta/contador, sin métricas cross-source;
3. comportamiento del histograma y sus series;
4. contrato de filtros de superficie, GIF y causa por fuente/contexto;
5. ficha humana unificada visualmente pero sin entidad fusionada;
6. layout desktop/móvil y navegación territorial;
7. vista recomendada por defecto y acceso avanzado a fuentes;
8. estados de cobertura/loading/error en lenguaje público;
9. wireframes y flujos de tareas prioritarias;
10. criterios de aceptación y trazabilidad hacia datos disponibles/bloqueados.

`D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`. El staging D4B permanece
`TECHNICAL_BASELINE`; GVA permanece `PRODUCT_REFERENCE` y producción actual.
No debe iniciarse el root switch hasta aprobar diseño e implementación UX y
repetir una aceptación de producto.
