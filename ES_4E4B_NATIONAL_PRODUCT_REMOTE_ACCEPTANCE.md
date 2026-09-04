# ES-4E4B — Aceptación remota del producto nacional

## Alcance y decisión

Se auditó exclusivamente el staging nacional ya desplegado en GitHub Pages:

`https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/`

No se modificaron runtime, assets, staging, producción ni despliegues. La
identidad remota coincide con el artefacto E4A: 497 ficheros / 812.510.441 B;
payload de 495 ficheros / 812.291.384 B; fingerprint
`10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3`;
manifest `377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e`;
site identity `f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e`.

Resultado: **PASS_WITH_MINOR_GAPS**. No hay un bloqueo técnico ni funcional
para reanudar la decisión de raíz; quedan tres mejoras P1 post-release y los
bloqueos externos de datos ya conocidos.

## Recorridos humanos remotos

| Escenario | Resultado observado |
| --- | --- |
| España 1968–2026 | 119.498 perímetros ESFire30; 646.887 registros EGIF; 8.230.839 ha EGIF conocidas. Las fuentes se muestran por separado. |
| España 1975 | 4.128 registros y 180.137 ha EGIF; no se presenta una ausencia ESFire30 como cero. |
| España 1995 | 5.035 perímetros, 25.557 registros EGIF y 141.082 ha conocidas. |
| Galicia 1995 | 1.989 perímetros, 15.254 registros EGIF y 46.670 ha conocidas. |
| Ourense 1995 | 746 perímetros, 3.605 registros EGIF y 18.207 ha conocidas. |
| Cangas del Narcea | 2.610 `geometry_id` ESFire30 —no 2.610 incendios—; interfaz estable. |
| País Valencià 1995 | 467 incendios oficiales ICV, 467 registros EGIF, 25 perímetros ESFire30 y 2.220 ha ICV; ICV es la fuente recomendada. |
| ICV ≥500 ha / GIF | Un resultado ICV, GIF y 502 ha; EGIF y ESFire30 se mantienen independientes. |
| País Valencià 2024 | 472 incendios oficiales ICV y 1.428 ha ICV. `2024AL0005` conserva su relación 1 registro → 2 perímetros. |
| País Valencià 2026 | 16 perímetros EFFIS y 10.265 ha; aviso explícito de snapshot 19/08/2026, no cierre anual. |
| Elx 2025 | 1 perímetro EFFIS y 7 ha; tarjeta y ficha utilizables. |
| Canarias 1995 | 56 registros EGIF y 3.631 ha; el texto dice que no hay perímetros cartografiados, no «0 incendios». |

Los 59 años del histograma y la tabla accesible se cargaron en cada escenario.
Un clic de año coordinó 1995 y el cambio de serie ESFire30 funcionó. Los
filtros EGIF de superficie/GIF, ICV de superficie/causa/GIF y EFFIS fueron
aplicados exactamente a su fuente, con chip y estado serializado. Un filtro
que deja ICV en cero se expresa como cero de resultado, no como ausencia de
cobertura. Las tarjetas y fichas de EGIF, ESFire30, ICV y EFFIS se abren sin
mezclar identidades.

## Estado, enlaces y navegación

El enlace nativo complejo conserva, en sesión Chromium nueva y tras reload:
territorio País Valencià, 1995, visibilidades, filtro ICV ≥500 ha y selección
ICV `gva:pif-cv:1995AL0076`. El control de copia mostró la URL alternativa en
headless por ausencia de Clipboard API, pero el enlace completo se restauró.

El adaptador GVA v1 se mantiene por identidad exacta del artefacto y por la
aceptación ES-4D3C; no se alteró entre esa aceptación y el staging auditado.
La interacción histórica remota separada no se volvió a recorrer porque el
artefacto, el adaptador y el hash no cambiaron. No es un cambio de producto.

La navegación caliente España → Galicia → Ourense → Galicia y País Valencià
→ Alacant → Elx → País Valencià limpió selecciones incompatibles, conservó
cachés y no produjo errores. Los cambios regionales/provinciales estuvieron
aproximadamente entre 1,9 y 2,7 s hasta mapa estable; Galicia repetida pidió
solo dos ranges ESFire30 adicionales (398.056 B en esa sesión).

## Entrega y red

Todos los requests funcionales PMTiles observados fueron `206` Range. No se
observó una descarga completa del PMTiles de Protomaps ni de ESFire30.

| Escenario frío | Estable | ESFire30 | Protomaps | Descarga completa |
| --- | ---: | ---: | ---: | --- |
| España 1995 | 5.476 ms | 10 requests / 1.811.399 B | 10 / 496.979 B | no |
| Galicia | 11.263 ms | 18 / 5.670.097 B | 18 / 1.299.772 B | no |
| Ourense | 8.869 ms | 24 / 7.262.234 B | 24 / 1.986.926 B | no |
| Cangas | 10.475 ms | 18 / 3.332.074 B | 18 / 1.276.658 B | no |
| Elx | 6.720 ms | 24 / 738.636 B | 25 / 1.091.144 B | no |

Los bytes son `PerformanceResourceTiming.transferSize` de una ejecución
Chrome limpia, diagnósticos dependientes de viewport/red/caché, no un
presupuesto de producción. Se comprobó también el asset Protomaps, los nueve
glyph PBF y ESFire30 mediante la puerta E4A: 0-0, initial, middle y final son
206 e idénticos a los bytes locales. No hay dominios de runtime externos.
La caché CDN de producción sigue **NOT_VALIDATED**: GitHub Pages staging no
permite concluir una política CDN productiva más allá de lo observado en el
navegador.

## Aislamiento y accesibilidad

Los fallos se simularon bloqueando solicitudes sólo en Chromium:

- summary nacional bloqueado: mapa y shell disponibles; mensaje de resumen
  recuperable;
- `basemap.pmtiles` bloqueado: fallback `bdlje_only`, sin error de bootstrap;
- DETAIL EGIF bloqueado: mapa y lista siguen disponibles y la ficha explica el
  fallo.

En desktop, País Valencià y Elx móvil no hubo controles sin nombre ni errores
de runtime; el mapa ocupa el primer viewport móvil y «Fuentes y metodología»
permanece plegado. El auditor enumera controles de barras y atribución por
debajo de 32 px; no son una regresión funcional, pero confirma el P1 de
objetivos táctiles del histograma y enlaces de atribución.

## Reconciliación de producto

Las siete regresiones E1 quedan **RESOLVED_REMOTE**: visión inicial, histograma,
filtros humanos, contexto del mapa, fichas, reducción de ruido técnico y
jerarquía móvil. Las tarjetas etiquetan siempre la fuente y el texto confirma
que no se suman datasets distintos.

P1 se mantiene para después de release:

1. brush/rango continuo del histograma;
2. objetivo táctil de barras anuales estrechas en móvil;
3. indicación más anticipada de carga municipal fría.

P2 permanece fuera de esta aceptación: revisión z13 del relieve/POI,
criterio seguro para ranking ESFire30 y pulido móvil menor. Siguen bloqueados
externamente la ontología de causas MITECO/ADCIF, licencia CCINIF y límites
municipales históricos. No se convierten en defectos del staging.

## Resultado siguiente

`NATIONAL_RELEASE_CANDIDATE = READY_FOR_ROOT_DECISION`.
`D5_STATUS = READY_TO_RESUME`, pero **no se inicia ES-4D5** en esta fase. La
siguiente decisión debe ser únicamente `ES-4D5_ROOT_SWITCH_DECISION`.

## Reproducibilidad

El harness remoto es:

```bash
python3 benchmarks/es4e4b/run_remote_acceptance.py \
  --output build/es4e4b/remote-acceptance.json \
  --compact-output data/audit/product/es4e4b_national_product_remote_acceptance.json
python3 benchmarks/es4e4b/run_remote_acceptance.py --check \
  --output build/es4e4b/remote-acceptance.json
```

La evidencia versionada es compacta; el JSON crudo de CDP queda bajo `build/`
e ignorado por Git.
