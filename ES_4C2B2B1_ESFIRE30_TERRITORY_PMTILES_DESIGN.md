# ES-4C2B2B1 — Muestra PMTiles ESFire30 con atributos territoriales

## Alcance y entradas cerradas

Esta fase no recalcula intersecciones ni modifica el PMTiles de fidelidad de
ES-3 (`61.347.888 B`, SHA-256
`92f0f081131932075f54a89d86fc8aa7e5879d56ca4d7177c64562f9612751b4`).
El builder [`scripts/build/esfire30/territory_pmtiles.py`](scripts/build/esfire30/territory_pmtiles.py)
parte del NDJSON de teselas ES-3 y del manifiesto/JSONL de relaciones
ES-4C2B1A. El único join es `geometry_id → memberships` ya auditado; incluye
las 120.847 relaciones CCAA y 121.887 provinciales, incluidos todos los
slivers de área positiva.

La muestra local e ignorada combina Galicia completa, País Valencià, Alacant,
València, Ourense y controles N:M. Tiene 40.849 geometrías, 41.415 relaciones
CCAA y 42.019 provinciales. Por ello prueba de forma realista el caso Galicia,
no una selección artificial pequeña.

## Encoding elegido

La variante recomendada para el siguiente build es **slots escalares enteros
MVT**:

```text
geometry_id, year,
ccaa_1?, ccaa_2?, ccaa_3?,
prov_1?, prov_2?, prov_3?
```

Los valores son códigos de transporte, no IDs canónicos: `10` representa
`ES:CCAA:10` y `3` representa `ES:PROV:03`. Las propiedades ausentes no se
escriben; no hay sentinel. Cuando existen varias relaciones se ordenan por
código ascendente, sin crear territorio principal. El máximo nacional
auditado es tres para ambos niveles.

MVT no ofrece arrays de propiedades como una representación portable y
MapLibre. Se probó también `ccaa_codes="|…|"` / `prov_codes="|…|"`, con
delimitadores para no confundir `1` con `10`: funciona mediante una expresión
`in(concat(...), property)`, pero pesa más y añade una convención de parsing.
Por tanto los slots son simultáneamente la opción A y la alternativa
scalar-native C; las strings delimitadas no son la elegida.

La semántica de cualquier slot es exclusivamente **«el perímetro ESFire30
intersecta este territorio»**. No implica origen, pertenencia administrativa,
ignición ni vínculo con un parte EGIF.

## Tamaño de muestra

| Variante | PMTiles | Incremento frente a baseline |
| --- | ---: | ---: |
| Fidelity baseline, mismos 40.849 features | 19.948.673 B | — |
| Slots escalares | 20.725.434 B | 776.761 B · 3,8938 % |
| Strings delimitadas | 20.833.473 B | 884.800 B · 4,4354 % |

El incremento de slots equivale a unos 19,02 B por geometría en esta muestra.
Aplicado con prudencia al PMTiles fidelity nacional existente, sugiere un
archivo de aproximadamente 63,6–63,7 MB (+2,3–2,4 MB), no una medición de
build nacional.

## Filtro MapLibre probado

Para CCAA, la expresión es de tamaño constante; para provincia se sustituye
el prefijo `ccaa` por `prov`:

```js
["all",
  [">=", ["to-number", ["get", "year"]], from],
  ["<=", ["to-number", ["get", "year"]], to],
  ["any",
    ["==", ["get", "ccaa_1"], selectedCode],
    ["==", ["get", "ccaa_2"], selectedCode],
    ["==", ["get", "ccaa_3"], selectedCode]]]
```

No transmite miles de `geometry_id` a `setFilter`. Mantiene `geometry_id` y
`year` como propiedades, por lo que selección, resaltado y la futura
restauración siguen teniendo identidad estable.

## Runtime aislado y resultados

[`prototypes/es4c/territory_pmtiles_sample.html`](prototypes/es4c/territory_pmtiles_sample.html)
usa MapLibre 5.16.0 y PMTiles 4.3.0 exclusivamente sobre la muestra.
Sus smokes locales usan HTTP Range y verifican que todas las features
renderizadas satisfacen el filtro de slots (0 mismatches).

| Caso desktop | Renderizadas | setFilter + idle* | Range transfer | Heap diagnóstico |
| --- | ---: | ---: | ---: | ---: |
| País Valencià | 2.166 | 483,0 ms | 143.991 B | 12,7 MB |
| Alacant | 489 | 455,0 ms | 143.991 B | 11,8 MB |
| València | 949 | 460,3 ms | 143.991 B | 13,0 MB |
| Galicia | 38.177 | 590,3 ms | 921.926 B | 54,4 MB |
| Ourense | 16.214 | 591,3 ms | 1.091.776 B | 45,7 MB |
| Galicia, 1993–2002 | 12.026 | 541,6 ms | 921.926 B | 35,1 MB |

\* Incluye el siguiente `idle` del mapa y 120 ms de estabilización; no es un
microbenchmark aislado de `setFilter`. Heap es Chromium headless local, no un
presupuesto de teléfono físico.

### Distinción de conteos

Los valores de esta tabla **no son inventarios territoriales completos**:
`38.177` para Galicia y `16.214` para Ourense son features que MapLibre tenía
cargadas y renderizadas en el viewport/zoom concreto del smoke. Una geometría
puede no estar en las teselas solicitadas para esa vista y, además, la misma
geometría puede aparecer en más de una tesela cargada.

Los conteos nacionales auditados de relaciones siguen siendo los de
ES-4C2B1B: **38.645 `geometry_id` que intersectan Galicia** y **16.265 que
intersectan Ourense**. Esos valores proceden del JSONL de relaciones positivas
de área, no de MapLibre, y son los que deben usarse para cobertura territorial.

También pasaron los controles `esfire30:v1:1985:268` (Alacant + València) en
ambas provincias y `esfire30:v1:1985:1037` en las dos CCAA que intersecta.
Los tres controles de selección conservaron el mismo `geometry_id` después de
subir un zoom sobre la tesela enriquecida.
El viewport móvil 390×844 de Galicia completó (38.177 features renderizadas
en esa vista, no geometrías territoriales totales,
Range 921.926 B, heap diagnóstico 54,7 MB), sin el crash observado con el
índice externo de 38.645 IDs.

La versión string delimitada pasó Alacant, pero no aporta ventaja: 489
features, 458,5 ms y 143.451 B de transfer en ese caso local; queda descartada
frente a slots.

## Decisión

Los atributos embebidos con slots son **RECOMMENDED como candidato para el
build nacional**: Galicia se filtra con una expresión MapLibre constante y
estable, a diferencia del índice externo que requería una literal de 38.645
IDs y resultó marginal. El índice externo se conserva para auditoría e
inspección, no como filtro cartográfico principal.

No se ha reconstruido el PMTiles nacional ni se ha modificado el runtime
principal del prototipo. La siguiente subfase debe auditar un build nacional
externo antes de sustituir ningún asset del runtime.

## Comandos reproducibles para ejecución externa

```bash
python3 scripts/build/esfire30/territory_pmtiles.py --all \
  --resume \
  --output data/derived/spain/es4c2b/pmtiles

python3 scripts/build/esfire30/territory_pmtiles.py --all --check \
  --output data/derived/spain/es4c2b/pmtiles
```

`--all` genera únicamente el PMTiles enriquecido y su input/manifest; las dos
variantes comparativas existen solo en `--sample`. La comprobación exige
119.498 `geometry_id`, 120.847 relaciones CCAA, 121.887 provinciales,
cardinalidad máxima tres, checksums y preservación de `geometry_id`/`year`.
Con los 40.849 features de la muestra los tres artefactos comparativos tardaron
unos 20–25 s en esta máquina. Para el build nacional único se estima del orden
de 1–3 min y menos de 0,2 GB de trabajo local, pero debe registrarse el tiempo
real externo.

Si una ejecución termina después de generar el PMTiles pero antes de escribir
el manifest, `--resume` valida el NDJSON enriquecido determinista y reutiliza
el binario existente; no vuelve a invocar Tippecanoe. Las rutas relativas de
`--output` se resuelven desde la raíz del repositorio.

## Validación

Se ejecutaron los dos tests específicos del builder, `--sample --check`, y
diez smokes desktop más un smoke móvil de Galicia. No se ejecutó ninguna
batería ES-3 ni un build nacional.
