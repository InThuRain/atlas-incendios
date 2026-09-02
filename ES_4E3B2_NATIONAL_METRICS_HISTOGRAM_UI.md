# ES-4E3B2 — Métricas nacionales e histograma funcional

## Resultado

`METRICS_UI_STATUS = PASS`, `HISTOGRAM_UI_STATUS = PASS` y
`PRODUCT_OVERVIEW_STATUS = PASS`.

La shell humana E3A consume ahora `national-ux-summary-v1` y permite responder
sin abrir metodología cuántos registros o perímetros documenta cada fuente,
qué superficie segura existe y cómo evoluciona una métrica anual. No se ha
modificado el summary, su schema, fingerprint ni semántica territorial; tampoco
se han creado métricas conjuntas, filtros, rankings, destacados o enlaces entre
fuentes.

## Loader y política de carga

`src/national/ux-summary-loader.mjs` carga primero el manifest y resuelve dentro
de su inventario un único payload según el estado central:

| Ámbito | Payload |
| --- | --- |
| España | `national.json` |
| CCAA/ciudad autónoma | `ccaa/ES-CCAA-xx.json` |
| Provincia | `provinces/ES-PROV-xx.json` |
| Municipio | municipio dentro de `municipalities/by-parent/<padre>.json` |

No se descarga el conjunto de 122 payloads. Los assets completados se cachean
por path; un token de generación y `AbortController` impiden que una respuesta
obsoleta sustituya el territorio actual. `missing`, respuesta malformada,
`no_source_coverage`, año cubierto con cero y error de red mantienen estados
distintos. Un error muestra “No se ha podido cargar el resumen de este
territorio” y no toca MapLibre, PMTiles ni los loaders EGIF/ICV/EFFIS.

El builder declara de forma host-neutral
`data/summary/national-ux-summary-v1/manifest.json`. E3B2 no ensambla ni
despliega Pages; la copia del derivado corresponderá al ensamblado futuro.

## Tarjetas humanas

Las tarjetas muestran valor, etiqueta completa y fuente. Se ordenan primero los
conteos independientes aplicables —comenzando por la fuente recomendada— y
después las superficies; nunca hay más de cuatro. No existe tarjeta `Total`.

- EGIF: “Registros administrativos de incendios” y “Superficie forestal
  declarada conocida”.
- ESFire30: “Perímetros derivados de imágenes Landsat”; no se ofrece un área
  territorial inexistente.
- ICV: “Incendios oficiales documentados” y superficie forestal declarada. El
  número de perímetros y el GIF quedan en “Más datos”.
- EFFIS: “Perímetros satelitales provisionales” y área del perímetro satelital;
  2026 incluye la fecha del snapshot y avisa de que no es cierre anual.

Superficie desconocida no se convierte en cero. La suma contiene solo valores
conocidos y el nivel secundario indica `N de M registros con valor conocido`.
Los GIF EGIF/ICV se muestran como métricas secundarias de su propia fuente, sin
filtro en esta fase.

Los números usan agrupación española forzada también en cuatro cifras
(`4.128`), hectáreas enteras desde 100 ha y un decimal por debajo. El valor
interno no se redondea.

## Histograma

El slot “Evolución” contiene un histograma DOM accesible, sin librería gráfica:

- una única serie visible;
- eje fijo 1968–2026 con 59 años;
- pestañas por fuente/métrica, nunca series apiladas;
- escala Y independiente para conteos o hectáreas;
- tooltip/foco/tap con año, valor, unidad, fuente y territorio;
- tramado para gap/unknown y marca separada para cero cubierto;
- rango solicitado delimitado mediante fondo y contorno, no solo color;
- botón accesible por año y tabla anual alternativa.

Un click/tap en un año escribe `from = to = year` y llama a
`runtime.applyYears()`: mapa, sources, tarjetas, cobertura e histograma usan el
mismo estado. Los controles Desde/Hasta actualizan el sombreado sin reiniciar
una serie explícita que siga disponible. El drag/brush queda como P1: el click
de año era el P0 obligatorio y evitar un gesto complejo reduce riesgo en móvil.

### Serie inicial

Se aplica literalmente E2:

1. GVA dentro de 1993–2024: registros ICV.
2. GVA dentro de 2025–2026: perímetros EFFIS.
3. Cualquier otro contexto con cobertura EGIF: registros EGIF.
4. Sin EGIF, la fuente geométrica disponible.
5. Sin serie, eje y mensaje de indisponibilidad.

Una elección explícita se conserva al cambiar periodo mientras exista en el
territorio; si el nuevo territorio no la ofrece, se selecciona el fallback
determinista. La serie del histograma no se serializa en E3B2: E2 no la fijó
como campo compartible y añadirla no es necesario para restaurar el significado
del estado. `#es4c-state-v1`, `#v=1`, Compartir y back/forward permanecen sin
cambios; al restaurar se elige la serie contextual.

## Smokes dirigidos

Los 13 smokes Chromium pasaron, con 11 desktop y 2 viewports emulados 390×844:

| Caso | Tarjetas principales del periodo | Serie inicial |
| --- | --- | --- |
| España 1968–2026 | 119.498 ESFire30; 646.887 EGIF; 8.230.839 ha EGIF | EGIF registros |
| España 1975 | 4.128 EGIF; 180.137 ha EGIF | EGIF registros |
| España 1995 | 5.035 ESFire30; 25.557 EGIF; 141.082 ha EGIF | EGIF registros |
| Galicia 1995 | 1.989 ESFire30; 15.254 EGIF; 46.670 ha EGIF | EGIF registros |
| Ourense 1995 | 746 ESFire30; 3.605 EGIF; 18.207 ha EGIF | EGIF registros |
| GVA 1995 | 467 ICV; 467 EGIF; 25 ESFire30; 2.220 ha ICV | ICV incendios |
| GVA 2024 | 472 ICV; 1.428 ha ICV | ICV incendios |
| GVA 2026 | 16 EFFIS; 10.265 ha EFFIS | EFFIS perímetros |
| Elx 2025 | 1 EFFIS; 7 ha EFFIS | EFFIS perímetros |
| Cangas 1985–2021 | 2.610 ESFire30; 3.044 EGIF; 47.392 ha EGIF | EGIF registros |
| Canarias 1995 | 56 EGIF; 3.631 ha EGIF | EGIF registros |

Canarias no presenta una tarjeta ESFire30 a cero: conserva
`no_source_coverage`. Cangas usa 2.610 relaciones ESFire30 durante toda su
cobertura, pero sus 3.044 registros EGIF corresponden exactamente al periodo
1985–2021; no se sustituye una métrica por la otra.

El control ICV `2024AL0005` continúa aportando un registro y dos geometrías al
summary 13.738/13.739. La UI usa `icv_fire_record_count` como tarjeta principal
y `icv_perimeter_count` como magnitud separada, sin forzar 1:1.

También pasaron en navegador:

- click 1995: `from=to=1995` y barra resaltada;
- cambio explícito ICV → ESFire30 con `aria-selected=true`;
- Compartir conserva el hash nacional (en headless se ejercitó el fallback de
  copia manual);
- mapa en el primer viewport móvil, tarjetas a dos columnas e histograma sin
  scroll horizontal obligatorio;
- 59 botones de año y 59 filas de tabla accesible en todos los casos;
- cero errores de runtime y bootstrap.

## Rendimiento diagnóstico

No es un benchmark. En el servidor local sin compresión HTTP, manifest más
payload final supusieron aproximadamente 82–85 KB para país/CCAA; los cambios
intermedios de navegación provincial/municipal pueden solicitar y cancelar
resúmenes padre antes del shard final.

| Payload final | Raw | Gzip declarado |
| --- | ---: | ---: |
| España | 3.301 B | 1.390 B |
| Galicia | 3.112 B | 1.283 B |
| Ourense | 2.877 B | 1.147 B |
| Elx, shard Alacant | 497.719 B | 19.932 B |
| Cangas, shard Asturias | 165.411 B | 17.126 B |

El manifest mide 80.149 B raw y aproximadamente 18,5 KB gzip dentro de la
contabilidad E3B1. La mediana observada hasta summary visible fue 2,52 s,
incluyendo inicialización completa del runtime/mapa y carga de sus fuentes; el
intervalo fue 1,73–7,22 s, con el máximo en Cangas y sus loaders territoriales.
No se descargaron todos los summaries, EGIF DETAIL ni shards municipales
ajenos al estado.

## Comparación de producto

| Capacidad | GVA | D4B nacional | E3A | E3B2 |
| --- | --- | --- | --- | --- |
| Overview inmediato | fuerte | técnico | jerarquía humana | humano y cuantificado |
| Conteos | visibles | fragmentados | placeholder | tipados por fuente |
| Superficie | visible | técnica | placeholder | declarada/cartografiada sin mezcla |
| Evolución | histograma | ausente | slot | funcional, una serie |
| Claridad de fuente | contextual | dominante/técnica | progresiva | junto a cada cifra/serie |
| Mapa dominante | sí | comprometido por panel | sí | sí |
| Ruido técnico | bajo | alto | plegado | sigue plegado |
| Móvil | compacto | funcional/técnico | mapa primero | resumen e histograma usables |

E3B2 cierra la regresión principal de overview, métricas e historia anual, pero
no completa todavía el producto.

## Pendiente para E3C

- filtros `min_area`, GIF y causa donde el contrato sea seguro;
- destacados/top-N por una sola fuente y métrica;
- ficha humana final;
- coordinación de filtros con tarjetas/histograma/mapa;
- decidir el brush de rango P1;
- basemap contextual (`BASEMAP_GAP`) sigue sin proveedor local aprobado.

No se tocó producción, staging D4B, PMTiles, datasets fuente ni derivados B1.

## Validación

```bash
python3 -m unittest tests.test_es4e3b2_metrics_histogram_ui
python3 benchmarks/es4e3b2/run_smoke.py --all --output /tmp/es4e3b2-smokes.json
python3 benchmarks/es4e3b2/run_smoke.py --check --output /tmp/es4e3b2-smokes.json
```

Resultados: 5 tests específicos y 13/13 smokes correctos. No se ejecutó la
suite completa ni un benchmark.

## Estado

- `METRICS_UI_STATUS = PASS`
- `HISTOGRAM_UI_STATUS = PASS`
- `PRODUCT_OVERVIEW_STATUS = PASS`
- `TECHNICAL_RUNTIME_REGRESSION = false`
- `PRODUCT_RELEASE_CANDIDATE = false`
- `D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`
- `NEXT_PHASE = ES-4E3C_NATIONAL_FILTERS_HIGHLIGHTS_DETAILS`
