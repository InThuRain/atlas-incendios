# ES-4C1A — Primer runtime visual nacional ESFire30/PMTiles

Fecha: 28/08/2026  
Estado: prototipo local aislado; pendiente de revisión. No publicado.

## Propósito y límites

Este experimento verifica la primera pieza visual nacional: un mapa navegable
de España que muestra ESFire30 mediante vector tiles PMTiles, mantiene una
selección estable por `geometry_id` y usa HTTP Range. No forma parte del visor
del País Valencià ni carga EGIF, CCINIF, relaciones territoriales, causas o
municipios.

ESFire30 se presenta exclusivamente como
`documented_remote_sensing_perimeter`: perímetros derivados de teledetección
Landsat, con resolución nominal de 30 m, y no como cartografía oficial de
incendios. Su cobertura declarada en este snapshot es 1985–2021; Canarias queda
sin cobertura y el prototipo lo declara expresamente.

## Reutilización verificable de ES-3

Se reutiliza, sin regeneración, el PMTiles de fidelidad de ES-3:

| Campo | Valor |
|---|---|
| Ruta local ignorada | `data/derived/spain/es3/assets/esfire30-national-fidelity.pmtiles` |
| Tamaño | 61.347.888 B |
| SHA-256 | `92f0f081131932075f54a89d86fc8aa7e5879d56ca4d7177c64562f9612751b4` |
| Zooms | 4–14 |
| Renderer de laboratorio | MapLibre GL JS 5.16.0 + PMTiles 4.3.0 |
| Capa MVT | `esfire30` |
| Propiedades de tesela | `geometry_id`, `year` |

El checksum y el tamaño se contrastan contra `benchmarks/es3/results.json` antes
de iniciar el servidor o los smokes. Las librerías locales ya usadas por ES-3
permanecen bajo `data/derived/spain/es3/tools/browser/`, también ignoradas.

## Estructura y estado mínimo

```
prototypes/es4c/
  index.html       página aislada, nunca referenciada por el Atlas público
  app.js           MapLibre, filtro temporal, selección y API de smoke
  styles.css       interfaz mínima del laboratorio
  run_smoke.py     servidor Range local y comprobación Chromium/CDP
```

El estado interno preparado para las fases posteriores es:

```text
center
zoom
from
to
selected_geometry_id
```

No actualiza URLs ni implementa aún un permalink nacional. El filtro mínimo
`from`/`to` usa el atributo MVT `year`; no genera PMTiles por año. La superficie
no está en los atributos de esta tesela diagnóstica y la selección lo indica en
lugar de inventarla.

El clic/tap de una geometría y el smoke usan la misma función `selectFeature`.
La capa de resaltado filtra por la propiedad estable `geometry_id`; no utiliza
el ID numérico efímero MVT, la posición dentro de una tesela ni el zoom.

## HTTP Range local

Python 3.8 no implementa por sí solo Range para `SimpleHTTPRequestHandler`.
`run_smoke.py` incorpora un servidor local mínimo que responde `206`,
`Content-Range` y `Accept-Ranges: bytes`, contabilizando únicamente las
peticiones PMTiles. Es un control del requisito del archivo PMTiles, no una
afirmación sobre GitHub Pages ni una prueba de CDN.

Para abrir el prototipo de forma manual:

```bash
python3 prototypes/es4c/run_smoke.py --serve
```

El comando muestra una URL `http://127.0.0.1:PUERTO/prototypes/es4c/index.html`.
Se detiene con `Ctrl+C`.

## Smoke tests ejecutados

El resultado detallado queda local e ignorado en
`prototypes/es4c/smoke-results.json`. Se ejecutaron seis smokes, sin repetir la
batería ES-3:

| Vista | Dispositivo | Usable inicial | Range inicial | Bytes Range inicial | Heap inicial Δ | Range tras selección/zoom | Bytes finales | Heap final Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| España | escritorio | 870,0 ms | 6 | 1.477.128 | 30.624.778 | 10 | 3.338.784 | 169.944.873 |
| España | 390×844 | 752,0 ms | 6 | 1.477.128 | 27.864.782 | 10 | 3.338.784 | 150.522.295 |
| Galicia | escritorio | 817,2 ms | 6 | 1.477.128 | 28.472.494 | 15 | 5.908.185 | 198.211.581 |
| Galicia | 390×844 | 808,6 ms | 6 | 1.477.128 | 27.879.458 | 14 | 5.739.119 | 154.970.243 |
| País Valencià | escritorio | 872,6 ms | 6 | 1.477.128 | 30.311.886 | 23 | 1.744.350 | 94.458.269 |
| País Valencià | 390×844 | 795,8 ms | 6 | 1.477.128 | 27.457.286 | 12 | 1.649.590 | 61.565.818 |

Todos los requests PMTiles recibieron `206`; en los seis casos
`full_pmtiles_requests=0`. La navegación y el zoom solicitaron rangos
adicionales sin transferir el archivo de 61,3 MB completo. Cada caso seleccionó
un `geometry_id` estable y lo encontró de nuevo en la capa de resaltado tras un
zoom adicional:

- España: `esfire30:v1:2005:360`.
- Galicia: `esfire30:v1:2003:2073`.
- País Valencià: `esfire30:v1:1994:2874` en escritorio y
  `esfire30:v1:1985:387` en el viewport móvil.

Los valores de heap son `performance.memory` de Chromium headless con memoria
precisa habilitada. Incluyen MapLibre y datos que siguen residentes después de
la navegación/zoom; son smokes diagnósticos, no presupuestos de producción ni
una simulación de CPU, red o teléfono físico.

## Validación automatizada

```bash
python3 -m unittest tests/test_es4c1a_pmtiles_runtime.py -q
python3 prototypes/es4c/run_smoke.py --all-smokes --desktop --mobile \
  --output prototypes/es4c/smoke-results.json
python3 prototypes/es4c/run_smoke.py --check \
  --output prototypes/es4c/smoke-results.json
```

Las tres pruebas unitarias validan la procedencia/checksum ES-3, el parser
Range y las garantías estáticas de semántica, `geometry_id` y aislamiento del
frontend público. Los seis smokes anteriores completaron sin errores.

## Límites y siguiente fase

Este prototipo confirma que el asset PMTiles de fidelidad puede sostener un
runtime visual aislado y una selección estable, pero no decide aún el renderer
del Atlas público ni migra Leaflet. Falta ES-4C1B para incorporar de forma
separada los assets EGIF INITIAL/DETAIL y su estado, sin confundir partes
administrativos con perímetros ESFire30. Antes de alojamiento real también
sigue pendiente un smoke HTTP Range en GitHub Pages/CDN.
