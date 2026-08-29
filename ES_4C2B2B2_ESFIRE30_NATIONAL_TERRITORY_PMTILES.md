# ES-4C2B2B2 — PMTiles nacional ESFire30 con filtro territorial

## Asset auditado

Esta fase integra exclusivamente en `prototypes/es4c/` el PMTiles nacional ya
construido externamente. No reconstruye el archivo, no recalcula relaciones y
no modifica producción, publicación ni el permalink público.

| Elemento | Valor |
| --- | --- |
| Asset | `data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles` |
| Formato | PMTiles/MVT, capa `esfire30`, zoom 4–14 |
| Tamaño | 63.052.056 B |
| SHA-256 | `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe` |
| Geometrías | 119.498 |
| Input ES-3 | `esfire30-tiles-input.ndjson`, SHA-256 `cae1209d7fb0f0daa232f600ccc015c59eabda79be5ddbee5b0978ddf8a487d8` |
| Input relaciones | manifest ES-4C2B1A, SHA-256 `969a5439f706147bb0f691056f4a55dda6653c814a7549c7b972bf0174415981` |

Frente al PMTiles fidelity de ES-3 (61.347.888 B, SHA-256
`92f0f081131932075f54a89d86fc8aa7e5879d56ca4d7177c64562f9612751b4`),
el enriquecimiento añade **1.704.168 B (2,7779 %)**. El resultado de 63,05 MB
queda dentro de la estimación ES-4C2B2B1 de aproximadamente 63,6–63,7 MB.

El `--check` externo y la verificación específica confirman 119.498
geometrías, 120.847 relaciones CCAA y 121.887 relaciones provincia. No hay
IDs añadidos o perdidos, no hay duplicados y la cardinalidad por nivel no
supera tres.

## Atributos MVT y semántica

Cada feature mantiene `geometry_id` y `year`, y añade slots enteros:

```text
ccaa_1?, ccaa_2?, ccaa_3?
prov_1?, prov_2?, prov_3?
```

Los slots ausentes se omiten en MVT. Los valores están ordenados por código
territorial ascendente y son códigos de transporte: `10` representa
`ES:CCAA:10` y `3` representa `ES:PROV:03`; no sustituyen IDs canónicos ES-2.

Todo slot significa exclusivamente **«el perímetro ESFire30 intersecta este
territorio administrativo»**. No declara origen, pertenencia administrativa
del incendio, ignición ni relación con un parte EGIF.

Los controles del binario nacional leyeron estas propiedades:

```text
esfire30:v1:1985:268
  ccaa_1=10; prov_1=3; prov_2=46

esfire30:v1:1985:1037
  ccaa_1=7; ccaa_2=17; prov_1=9; prov_2=26
```

Ambos aparecen bajo cualquiera de sus territorios relacionados, sin territorio
principal. Se preservan todos los slivers positive-area auditados, sin umbral.

## Runtime aislado

`prototypes/es4c/app.js` usa ahora el PMTiles territorial. Para CCAA MapLibre
recibe una expresión constante como:

```js
["all", yearFilter(),
  ["any",
    ["==", ["get", "ccaa_1"], selectedCode],
    ["==", ["get", "ccaa_2"], selectedCode],
    ["==", ["get", "ccaa_3"], selectedCode]]]
```

Para provincias se sustituye `ccaa` por `prov`. El resultado es siempre
`periodo ESFire30 AND territorio`, sin transmitir miles de `geometry_id`.
España no añade condición territorial. EGIF mantiene su filtro administrativo
independiente y no se crea ningún enlace EGIF–ESFire30.

El índice externo ES-4C2B2A sigue disponible para auditoría, pero el runtime
no lo importa ni solicita: los smokes informan `external_index_loaded: false`.
Si una selección ESFire30 ya no cumple periodo, visibilidad o slots, se limpia
solo `selected_geometry_id`; la selección EGIF permanece independiente.

La restauración de una URL con Alacant, 1985 y
`esfire30:v1:1985:268` recuperó límite, centro/zoom y geometría al cumplir
ambos filtros.

## Smokes dirigidos

Pasaron España, País Valencià, Alacant, València, Galicia, Ourense, Sevilla,
multi-provincia, multi-CCAA, año+territorio, Balears, Canarias, restauración y
viewport móvil 390×844 para Galicia y Alacant. Todos los requests PMTiles
observados fueron HTTP 206; no hubo descarga completa ni errores JavaScript.

| Caso desktop | Filtro MVT | Range final | Requests | Heap diagnóstico |
| --- | ---: | ---: | ---: | ---: |
| España, 1995 | nacional | 1.817.015 B | 10 | 144.286.728 B |
| País Valencià, 1993–2002 | `ccaa=10` | 1.796.929 B | 24 | 156.545.326 B |
| Alacant, 1993–2002 | `prov=03` | 1.798.308 B | 27 | 138.408.547 B |
| València, 1993–2002 | `prov=46` | 2.321.968 B | 32 | 153.200.250 B |
| Galicia, 1993–2002 | `ccaa=12` | 5.673.313 B | 18 | 151.370.627 B |
| Ourense, 1993–2002 | `prov=32` | 9.535.023 B | 30 | 150.626.360 B |

El establecimiento de `setFilter` tomó aproximadamente 0,1–0,4 ms. Eso mide
la expresión, no la descarga ni el render posterior. En viewport móvil,
Galicia completó con 5.451.544 B Range y 123.609.887 B de heap diagnóstico;
Alacant con 1.911.368 B y 155.280.456 B. Es Chromium emulado, no teléfono
físico.

La transferencia inicial de España observada fue 526.207 B Range antes de
navegar/seleccionar. **No debe compararse directamente** con los
aproximadamente 1.477.128 B de C1A como una mejora de compresión o de
rendimiento: viewport, teselas solicitadas y estado de caché pueden diferir.
La conclusión válida es que HTTP Range sigue funcionando, no hay descarga
completa y el coste total del PMTiles aumenta solo 2,7779 %. Estas mediciones
locales no reemplazan ES-3.

Los conteos de features renderizadas no son inventarios territoriales. Galicia
conserva **38.645 `geometry_id` relacionados** y Ourense **16.265**, según la
auditoría nacional; lo renderizado depende de viewport y zoom.

## Cobertura

Illes Balears, Canarias, Ceuta y Melilla están **sin cobertura ESFire30** en
este snapshot de alcance continental. Al seleccionarlos, límites oficiales y
EGIF pueden operar; ESFire30 indica ausencia de cobertura, nunca «0
incendios». Ceuta y Melilla permanecen ciudades autónomas conforme a ES-2.

## Decisión

El PMTiles territorial es **RECOMMENDED** como filtro cartográfico ESFire30:
resuelve Galicia con una expresión constante, mantiene `geometry_id`, conserva
HTTP Range y no requiere el índice externo de 616 KB para filtrar el mapa. El
coste nacional es +2,7779 % respecto a fidelity. El índice externo se conserva
solo para auditoría e inspección.

No hay municipio, cambios de producción ni publicación. La siguiente fase
recomendada es **ES-4C2A3 — municipios nacionales**, manteniendo la distinción
entre filtro administrativo EGIF e intersección territorial ESFire30.

## Validación ejecutada

```bash
python3 -m unittest tests.test_es4c1a_pmtiles_runtime \
  tests.test_es4c2b2b2_territory_pmtiles

python3 scripts/build/esfire30/territory_pmtiles.py --all --check \
  --output data/derived/spain/es4c2b/pmtiles
```

Resultado: seis tests específicos correctos y `--check` válido, sin fallos.
Los resultados de smoke son locales e ignorados por Git.
