# ES-4B5C2 — Análisis de rendimiento EGIF en navegador

Fecha: 28/08/2026. El análisis consume exclusivamente
`benchmarks/es4b5c/results.json`; no abre Chromium, no ejecuta benchmarks y no
modifica ningún asset. El agregado reproducible de las 40 observaciones
comparables está en `data/audit/egif/es4b5c2_browser_summary.json`.

## Integridad de la matriz

`results.json` contiene **41** runs completos y sin errores. La matriz A–J
tiene diez escenarios × escritorio/móvil × cold/warm = **40**. El run restante
es `smoke_la_rioja_2013_2023::desktop::cold`, ejecutado antes de la batería;
se conserva como evidencia de smoke, pero se excluye de todos los agregados
comparativos para no duplicar La Rioja.

Cada combinación principal se midió una sola vez. No hay base estadística para
mediana, p95 ni intervalos: este informe muestra observaciones individuales.

Las cifras `fetchΣ` suman el tiempo de los fetch paralelos y por ello pueden
superar el tiempo de pared `wall`. `raw body`, `transferSize` y `gzip manifest`
se conservan separados: el servidor local no comprimía HTTP.

## Matriz compacta: escritorio frío

Todos los rows de la tabla tienen `errors=[]`. `heap` está en bytes y DETAIL
es una **sonda de selección**, no una precarga: en escenarios con varios assets
la sonda carga dos DETAILS (el seleccionado y uno de otro asset).

| Escenario | Records/assets | INITIAL gzip / raw | Req | fetchΣ / wall / parse / prepare / filtro / lookup ms | Heap antes → INITIAL (Δ) | DETAIL gzip/raw/req | Heap tras DETAIL (Δ desde INITIAL) |
| --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| La Rioja | 3.996 / 5 | 31.011 / 601.684 | 5 | 38,6 / 9,3 / 0,7 / 0,8 / 0,6 / 0 | 3.213.083 → 5.731.708 (+2.518.625) | 19.095 / 132.010 / 2 | 6.312.494 (+580.786) |
| País Valencià | 22.108 / 5 | 149.247 / 3.300.714 | 5 | 76,0 / 24,7 / 6,3 / 6,3 / 2,2 / 0 | 3.213.346 → 16.032.943 (+12.819.597) | 125.040 / 998.564 / 2 | 19.794.223 (+3.761.280) |
| Cataluña | 31.319 / 5 | 209.248 / 4.663.170 | 5 | 91,8 / 30,1 / 13,0 / 4,6 / 2,4 / 0 | 3.213.135 → 21.227.248 (+18.014.113) | 149.217 / 1.308.599 / 2 | 26.558.042 (+5.330.794) |
| Andalucía | 45.512 / 5 | 292.005 / 6.820.965 | 5 | 115,8 / 38,8 / 15,8 / 6,4 / 3,9 / 0 | 3.213.086 → 30.857.289 (+27.644.203) | 222.814 / 1.549.901 / 2 | 36.630.215 (+5.772.926) |
| Castilla y León | 81.438 / 5 | 514.891 / 12.201.742 | 5 | 180,7 / 66,3 / 29,6 / 13,7 / 5,2 / 0 | 3.213.512 → 51.157.549 (+47.944.037) | 334.516 / 2.743.861 / 2 | 62.500.456 (+11.342.907) |
| Galicia completo | 264.313 / 5 | 1.400.126 / 39.521.202 | 5 | 570,5 / 210,0 / 106,6 / 42,1 / 8,4 / 0 | 3.213.328 → 153.747.605 (+150.534.277) | 872.981 / 6.211.893 / 2 | 181.277.463 (+27.529.858) |
| Galicia 1993–2002 | 110.605 / 1 | 572.974 / 16.610.507 | 1 | 21,9 / 81,1 / 44,7 / 14,3 / 4,5 / 0,1 | 3.213.147 → 72.835.474 (+69.622.327) | 1.439.929 / 14.855.021 / 1 | 123.086.961 (+50.251.487) |
| España 1993–2002 | 200.513 / 18 | 1.147.093 / 30.135.204 | 18 | 1.073,8 / 154,0 / 73,9 / 32,4 / 7,0 / 0 | 3.213.089 → 122.223.020 (+119.009.931) | 246.214 / 2.016.175 / 2 | 123.928.444 (+1.705.424) |
| España 2013–2023 | 102.669 / 18 | 719.901 / 15.497.839 | 18 | 945,6 / 87,9 / 38,0 / 15,3 / 4,7 / 0 | 3.213.109 → 64.430.918 (+61.217.809) | 282.106 / 1.811.695 / 2 | 68.520.323 (+4.089.405) |
| España all INITIAL | 646.887 / 88 | 3.901.303 / 96.883.738 | 88 | 27.319,6 / 661,0 / 300,9 / 166,8 / 17,8 / 0 | 3.212.819 → 267.971.678 (+264.758.859) | 222.814 / 1.843.651 / 2 | 195.363.483 (GC observado) |

La tabla equivalente para móvil frío, escritorio warm y móvil warm —incluidos
heap antes/después, transferencias y errores— está como 40 rows explícitos en
el JSON auditado. El resumen móvil frío relevante es: Galicia completo añade
152.829.045 B, Galicia 1993–2002 69.622.467 B, España 1993–2002 118.966.911 B,
España 2013–2023 61.221.857 B y España completa 193.267.719 B de heap INITIAL.

## Cold, warm y viewport móvil

En los 20 pares cold/warm, `resource_transfer_bytes` de INITIAL pasa de un
valor positivo en frío a **0** en caliente: la caché HTTP local sí funcionó.
El cuerpo decodificado sigue apareciendo igual porque el harness lo lee y
parsea de nuevo; parseo, preparación y lookup no desaparecen por estar el
archivo en caché.

La mejora de `wall` no es uniforme. Por ejemplo, España completa escritorio
pasa de 661,0 ms cold a 472,2 ms warm; Galicia completa de 210,0 a 172,9 ms.
España 1993–2002 queda prácticamente igual (154,0 frente a 155,8 ms). No debe
atribuirse el detalle a una CDN: es caché de Chromium con servidor localhost.

El viewport móvil 390×844 completa todos los escenarios sin error y muestra
parse/preparación/filtro cercanos a escritorio. No simula CPU, red, UA ni un
teléfono físico: se puede afirmar que funciona en Chromium con viewport móvil
emulado, no que sea apto para móviles de gama baja. Los heaps warm tampoco son
comparables con cold: cada warm incluye un pase de calentamiento previo y el
recolector de basura no está controlado.

## Casos decisivos

### Galicia

- **Completo (F): MARGINAL como carga inicial por defecto.** 264.313 partes,
  1.400.126 B gzip INITIAL y +150,53/+152,83 MB cold en escritorio/móvil. El
  parseo es 106,6/102,3 ms; preparación 42,1/37,5 ms; el paquete de filtros
  columnares 8,4/8,5 ms.
- **1993–2002 (G): ACCEPTABLE.** 110.605 partes, 572.974 B gzip, +69,62 MB
  cold y 44,7 ms de parseo. El DETAIL del único asset es deliberadamente
  grande (1.439.929 B gzip): la primera selección tarda 78,3 ms y eleva el
  heap observado +50,25 MB. Es evidencia fuerte para mantener DETAIL lazy.

La comparación usa el presupuesto diagnóstico ES-3 para una vista CCAA
(≤85 MiB de heap de geometría). EGIF no trae geometría y debe dejar margen para
ella; por eso Galicia completa no es una carga regional predeterminada aunque
funcione técnicamente.

### España por bloque y España completa

- **H, 1993–2002:** 200.513 partes, 18 assets, 1.147.093 B gzip, +119,01 MB
  cold, 73,9 ms parse y 32,4 ms de preparación. Es **VIABLE bajo demanda**,
  pero **MARGINAL** junto a una vista geométrica pesada.
- **I, 2013–2023:** 102.669 partes, 18 assets, 719.901 B gzip, +61,22 MB,
  38,0 ms parse y 15,3 ms preparación. Es **VIABLE/ACCEPTABLE** bajo demanda.
- **J, todo INITIAL:** 646.887 partes y 88 assets, 3.901.303 B gzip,
  +264,76 MB escritorio y +193,27 MB viewport móvil en frío. Parseo
  300,9/228,5 ms, preparación 166,8/160,2 ms y filtro agregado 17,8/16,0 ms.
  Completa sin error, pero queda **VIABLE_BUT_NOT_DEFAULT**: no debe ser la
  carga inicial de un visor que además tendrá geometría y UI.

## Lookup, filtros y formato columnar

`record_id` ocupa 1.587.210 B gzip (40,68 % de INITIAL), pero no muestra un
problema práctico en esta medición. Crear los Maps de todos los assets tarda
42,1 ms en Galicia completa, 32,4 ms en España 1993–2002 y 166,8 ms en España
completa. La consulta individual redondea a 0 ms (0,1 ms en Galicia
1993–2002). El harness no aísla su heap respecto de las demás columnas, por lo
que no puede cuantificar una parte exacta; no hay evidencia para eliminar o
transformar `record_id`.

`filter_bundle_ms` es el tiempo conjunto de cinco escaneos columnares (año,
rango, provincia, municipio resuelto y `null`), no el tiempo individual de
cada filtro. Se mantiene en 8,5 ms en Galicia completa, 7,3 ms en España
1993–2002 y 16,0–17,8 ms en España completa fría. Operar directamente en
columnas se mantiene recomendado.

La muestra <=1.000 filas de La Rioja, País Valencià, Cataluña, Andalucía,
Castilla y León y España completa da filtro columnar 0–0,1 ms frente a
0,3–1,3 ms para materializar y filtrar objetos. No hay heap aislado ni es una
extrapolación nacional, pero confirma direccionalmente evitar materializar
646.887 objetos de entrada.

## DETAIL lazy

**DETAIL lazy sigue RECOMMENDED.** INITIAL y DETAIL se descargan en fases
separadas en los 40 runs; no hay precarga de DETAIL. Una selección usa solo el
asset correspondiente, con el caso más costoso observado en G. La segunda
selección del mismo asset es 0,0–0,3 ms en los resultados.

Hay una limitación de instrumentación: en escenarios con varios INITIAL assets
el contador `second_same_asset_additional_detail_requests` se calculó después
de solicitar otro DETAIL y aparece como 1. No se usa como evidencia de una
segunda descarga. El smoke de La Rioja 2013–2023, con un único asset, confirma
correctamente 0 requests adicionales; y el código del harness usa una caché
por asset. La métrica debe corregirse antes de una nueva ronda, pero no se
repite esta ronda ni se invalida la separación INITIAL/DETAIL.

## Presupuestos y decisión

No se introduce un SLA nuevo. Los valores observados delimitan el presupuesto
del siguiente runtime:

- una CCAA × bloque puede usar como referencia el peor bloque medido: Galicia
  1993–2002, +69,62 MB INITIAL y 44,7 ms de parseo; queda por debajo del
  presupuesto ES-3 de 85 MiB para CCAA, dejando solo ~15 MiB de margen antes
  de sumar geometría;
- una CCAA completa es cómoda hasta Castilla y León (+47,94 MB), pero Galicia
  completa (+152,83 MB) exige carga por bloque;
- un bloque nacional reciente (I) consume +61,22 MB; el bloque 1993–2002 (H)
  +119,01 MB exige una vista explícita de registros sin geometría pesada;
- toda España INITIAL consume +193,27–264,76 MB cold antes de geometría y no
  es comportamiento inicial.

| Estrategia | Decisión |
| --- | --- |
| CCAA × bloque + INITIAL columnar | **RECOMMENDED** |
| CCAA periodo completo | **VIABLE**; no predeterminado para Galicia |
| España × bloque | **VIABLE** bajo demanda; 1993–2002 marginal con geometría |
| España todo INITIAL | **VIABLE_BUT_NOT_DEFAULT**; no recomendado como inicio |
| DETAIL bajo selección | **RECOMMENDED** |

No hace falta una optimización antes de un primer runtime nacional. La primera
política debe ser: España abre geometría overview mediante PMTiles (conforme a
ES-3) y carga EGIF INITIAL únicamente para el rango/bloque explícitamente
requerido; al entrar en una CCAA carga sus bloques necesarios; al seleccionar
un parte, carga el DETAIL correspondiente. El usuario no debe recibir toda
España INITIAL por defecto.

Esto encaja con ES-3: PMTiles para geometría overview/regional, GeoJSON de
detalle local donde proceda, registros administrativos EGIF en JSON columnar
particionado y ficha en DETAIL lazy. La posible mejora futura no es inmediata:
corregir el contador de segunda selección antes de otra ronda y, solo si un
runtime real lo exige, evaluar partición adicional de Galicia o lookup diferido.
