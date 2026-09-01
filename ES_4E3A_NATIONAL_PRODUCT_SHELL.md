# ES-4E3A — National product shell and information hierarchy

## Resultado

`PRODUCT_SHELL_STATUS = PASS`.

La entrada nacional de producción adopta una shell orientada a producto sin
modificar el motor compartido de ES-4C. El mapa vuelve a dominar, territorio y
periodo son los controles principales, el resumen usa únicamente datos EGIF ya
disponibles y seguros, y los controles completos de fuentes, metodología e
identificadores quedan en niveles secundarios o avanzados.

`TECHNICAL_RUNTIME_REGRESSION = false`. Los 13 smokes Chromium dirigidos y los
12 tests de contrato ejecutados no observaron errores de runtime, descargas
PMTiles completas ni roturas de los formatos de enlace. Esta fase no modifica
el staging D4B, producción GVA, `prototypes/es4c/` ni datasets.

## Alcance de los cambios

- `src/national/index.html`: nueva jerarquía semántica de cabecera, mapa,
  exploración, resumen, slots, resultados y metodología.
- `src/national/styles.css`: layout desktop 71/29 y layout móvil con mapa en el
  primer viewport.
- `src/national/product-shell.mjs`: capa de presentación para vista
  recomendada, copy humano, leyenda, métricas EGIF seguras y ficha progresiva.
- `src/national/bootstrap.js`: inicia la shell después del runtime congelado.
- `scripts/build_national_frontend.py`: incorpora los dos módulos de shell al
  artifact ligero y reproducible.
- `benchmarks/es4e3a/run_smoke.py`: harness local que superpone la nueva shell
  sobre el artifact D4B congelado mediante enlaces temporales.

No se ha cambiado ningún estado, reducer, serializer, loader, relación,
identidad ni contrato de fuente. Todos los IDs DOM que consume
`prototypes/es4c/app.js` continúan presentes.

## Estructura desktop

En Chromium a 1440 px de ancho útil:

- cabecera: 68 px;
- mapa: 1022,41 px (71,00 %);
- panel: 417,59 px (29,00 %);
- scroll limitado al panel; mapa y cabecera permanecen visibles.

El panel sigue el orden E2:

1. territorio y periodo;
2. resumen humano;
3. evolución temporal;
4. filtros;
5. resultados y fichas;
6. fuentes y metodología, plegado.

La UI anterior superponía un panel técnico sobre el mapa. La nueva cuadrícula
no tapa el mapa y llama a `map.resize()` en cambios de viewport y al desplegar
secciones.

## Estructura móvil

La emulación exacta 390×844 midió:

- cabecera: `0–58,44 px`;
- mapa: `58,44–412,91 px`, 354,47 px (42,00 % de la altura);
- panel de exploración a partir de `412,91 px`.

El primer viewport contiene cabecera humana, territorio/periodo resumidos, mapa
y leyenda. El formulario y el contenido aparecen después del mapa. La sección
de fuentes sigue plegada y los controles táctiles tienen un mínimo de 44 CSS
px.

## Territorio y periodo

Se conserva la ruta España → CCAA → provincia → municipio, incluidos
Ceuta/Melilla. El breadcrumb y la cabecera presentan nombres humanos; los IDs
ES-2 no aparecen en PRIMARY. Desde/Hasta conserva el rango global 1968–2026 y
no se sustituye por la intersección de cobertura de una fuente.

En scope municipal se mantiene, dentro de metodología, el aviso de que el
límite corresponde a la división administrativa actual.

## Vista recomendada

La función pura `recommendedView(state)` aplica las reglas E2:

| Contexto | Presentación geométrica recomendada |
| --- | --- |
| Fuera de GVA, 1985–2021 y con cobertura territorial | ESFire30 |
| Fuera de cobertura ESFire30 | ninguna; EGIF si está disponible |
| GVA 1985–1992 | ESFire30 |
| GVA 1993–2024 | ICV |
| GVA 2025–2026 | EFFIS provisional |
| Rango GVA con varios regímenes | fuentes aplicables separadas, sin suma ni enlace |

En una entrada sin estado serializado, la shell ajusta los toggles a esa vista.
Si el usuario modifica una fuente, deja de aplicar automatismos durante la
sesión. Una URL `#v=1` o `#es4c-state-v1` conserva exactamente las visibilidades
serializadas y nunca es sobrescrita por la recomendación.

Para rangos GVA que atraviesan varios regímenes, E3A presenta y activa por
separado las fuentes aplicables. No añade un filtro temporal nuevo por capa al
motor compartido: la segmentación cartográfica más fina se mantiene como
trabajo posterior y no altera la separación semántica actual.

## Resumen y métricas seguras

El resumen PRIMARY puede mostrar:

- recuento de registros EGIF desde manifest o INITIAL según el ámbito;
- superficie forestal declarada EGIF solo cuando existen valores conocidos;
- número de registros con superficie conocida;
- GIF administrativo EGIF cuando el resumen lo proporciona.

No usa `queryRenderedFeatures`, features en viewport ni placeholders `0 ha` o
`— incendios`. `null` no se convierte en cero. No hay tarjeta `Total` y se
explica que registros administrativos y perímetros no deben sumarse.

Ejemplos observados:

- España 1985–2021: 554.384 registros administrativos;
- Galicia 1995: 15.254;
- GVA 1995: 467;
- España 1975: 4.128;
- Canarias 1995: 56.

Son recuentos EGIF, no recuentos cross-source.

## Slots E3B/E3C

E3A crea la ubicación y contrato visual de evolución temporal y filtros. Ambos
permanecen en estado vacío explícito; no se dibujan series ni métricas falsas.

- E3B conectará `national-ux-summary-v1`, métricas tipadas e histograma.
- E3C añadirá `min_area`, GIF, causas seguras, destacados y completará las
  fichas humanas.

## Copy de disponibilidad, cero y error

La shell traduce estados sin modificar el runtime:

- ausencia: «Disponemos de registros administrativos, pero no de perímetros
  cartografiados para este territorio y periodo»;
- cero cubierto: «No hay perímetros Landsat que intersecten este territorio en
  el periodo seleccionado»;
- error: «No se han podido cargar estos datos. El resto del Atlas sigue
  disponible»;
- cobertura parcial: conserva el periodo solicitado y muestra la parte
  disponible.

Canarias 1995 activa EGIF y desactiva la capa ESFire30 recomendada. Agost
1985–2021 conserva cobertura de fuente y comunica cero relaciones; no se
confunde con ausencia de cobertura.

`idle`, `ready`, `complete`, `no_coverage`,
`not_integrated_for_territory`, `INITIAL`, `DETAIL`, `asset` y `shard` no son
visibles en PRIMARY. Los nodos técnicos que necesita el harness permanecen
ocultos con `hidden` y `aria-hidden`.

## Leyenda y fuentes

La leyenda enumera solo capas realmente dibujadas:

- límite administrativo actual;
- perímetros oficiales ICV;
- perímetros Landsat ESFire30;
- perímetros satelitales provisionales EFFIS.

EGIF no recibe símbolo porque no aporta geometría individual. La fuente
recomendada aparece primero.

“Fuentes y metodología” es un `<details>` cerrado inicialmente. Conserva los
cuatro toggles, coberturas documentadas, semántica, provisionalidad y las
atribuciones exactas existentes. Los estados de loader no se muestran.

## Fichas y revelado progresivo

Las selecciones múltiples e independientes continúan en el estado. La shell
crea una zona humana por fuente y copia únicamente campos ya documentados como
año/fecha, territorio, paraje, superficie, GIF y cardinalidad ICV. Campos
ausentes no se sustituyen por IDs. Identificadores y textos técnicos existentes
permanecen bajo “Más sobre estos datos”, cerrado por defecto.

E3C debe terminar la prioridad contractual de la ficha, especialmente causa
ICV, omisión fina de ausentes y navegación entre resultados. E3A no cambia la
relación ICV 1:N ni asocia EGIF con geometrías.

## Mapa base

`BASEMAP_GAP_FOR_E3B_OR_E3C = true`.

El runtime disponible solo contiene el lienzo MapLibre, límites BDLJE y capas
de incendios. No existe un basemap local aprobado con costa, carreteras y
topónimos. E3A mejora fondo, contraste, límites y leyenda, pero no introduce un
proveedor externo ni adopta automáticamente el endpoint OSM del visor GVA. La
decisión de proveedor/licencia/operación sigue pendiente.

## Accesibilidad básica

- estructura con `header`, `nav`, `section`, `aside`, `fieldset` y headings;
- labels explícitos y regiones `aria-live` para cambios humanos;
- foco visible de 3 px;
- targets mínimos de 44 px;
- leyenda con texto y variación de trazo, no solo color;
- `aria-expanded` sincronizado en todos los collapsibles;
- respeto a `prefers-reduced-motion`.

No es una auditoría WCAG completa.

## Smokes dirigidos

| Caso | Resultado principal |
| --- | --- |
| España default | ESFire30 + EGIF; mapa 71 %; 0 errores |
| Galicia 1995 | ESFire30 recomendado; 15.254 registros EGIF |
| GVA 1995 | ICV recomendado; ESFire30 complementario apagado |
| GVA 2024 | ICV completo; EGIF fuera de su periodo sin ruido PRIMARY |
| GVA 2026 | EFFIS completo y provisional |
| Elx 2025 | municipio restaurado, EFFIS recomendado |
| España 1975 | 4.128 EGIF y copy de ausencia de perímetros |
| Canarias 1995 | 56 EGIF y ausencia de cobertura ESFire30 |
| Agost | cero relaciones comunicado como resultado cubierto |
| Legacy `#v=1` | Elx 2025 y selección EFFIS restaurados |
| Native v1 | Elx 1993 y `geometry_id` ESFire30 restaurados |
| Móvil España | mapa 390×354,47 dentro del primer viewport |
| Móvil Elx 2025 | mismo orden; EFFIS listo; 0 errores |

Los 13 runs terminaron con `errors=[]`. Se observaron exclusivamente respuestas
PMTiles Range 206 y ninguna descarga completa; estos datos solo confirman la
ausencia de regresión, no forman un benchmark nuevo.

## Comparación post-E3A

| Criterio | GVA público | D4B nacional | E3A local | Estado |
| --- | --- | --- | --- | --- |
| Primer viewport | lectura inmediata | formulario técnico dominante | cabecera + mapa + contexto | `IMPROVED_MATCH` |
| Protagonismo del mapa | alto | panel superpuesto | 71 % desktop, 42 % alto móvil | `PASS` |
| Territorio | solo GVA | nacional completo | nacional completo y humano | `NATIONAL_BETTER` |
| Periodo | simple + histograma | inputs técnicos | control simple; histograma pendiente | `PARTIAL` |
| Complejidad de fuentes | baja | dominante | plegada y contextual | `PASS` |
| Lenguaje de disponibilidad | implícito | técnico | humano y distingue cero/ausencia | `PASS` |
| Jerarquía móvil | mapa visible | mapa oculto al inicio | mapa desde 58 px hasta 413 px | `PASS` |
| Ficha | humana | IDs primero | progresiva básica | `PARTIAL_E3C` |
| Contexto cartográfico | OSM | sin basemap | sin proveedor nuevo; mejor leyenda | `BASEMAP_GAP` |

## Validación reproducible

Tests dirigidos:

```bash
python3 -m unittest \
  tests.test_es4e3a_national_product_shell \
  tests.test_es4d2_national_frontend_extraction \
  tests.test_es4d3c_gva_permalink_compatibility
```

Build ligero:

```bash
python3 scripts/build_national_frontend.py --output /tmp/es4e3a-national
python3 scripts/build_national_frontend.py --check --output /tmp/es4e3a-national
```

Smokes locales (requieren el artifact D4B local ya aceptado):

```bash
python3 benchmarks/es4e3a/run_smoke.py --all --output /tmp/es4e3a-smokes.json
python3 benchmarks/es4e3a/run_smoke.py --check --output /tmp/es4e3a-smokes.json
```

## Estado y continuación

- `PRODUCT_SHELL_STATUS = PASS`
- `TECHNICAL_RUNTIME_REGRESSION = false`
- `PRODUCT_RELEASE_CANDIDATE = false`
- `D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`
- `NEXT_PHASE = ES-4E3B_NATIONAL_METRICS_HISTOGRAM`

E3B no se inicia en esta fase.
