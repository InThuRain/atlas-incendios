# ES-4C3D — Validación HTTP Range / caché en hosting real

## Resultado

`REAL_HOSTING_RANGE_VALIDATION = FAIL`.

El asset exacto funciona correctamente como objeto HTTP con peticiones Range,
pero GitHub Releases no expone los encabezados CORS necesarios para que el
prototipo servido desde `localhost` lo lea con PMTiles en Chromium. Por tanto
este staging es `NOT_RECOMMENDED` como hosting directo de PMTiles para el
runtime web. No se ha modificado Pages, el visor público, el PMTiles ni la
release existente.

Esta es una decisión de entrega, no una conclusión sobre la validez del
PMTiles ni sobre la arquitectura territorial ya aprobada.

## Asset y staging evaluados

| Campo | Valor |
| --- | --- |
| Hosting probado | GitHub Releases, prerelease `national-prototype-staging-es4c3d` |
| URL estable | `https://github.com/InThuRain/atlas-incendios/releases/download/national-prototype-staging-es4c3d/esfire30-national-fidelity-territories.pmtiles` |
| Asset | `esfire30-national-fidelity-territories.pmtiles` |
| Tamaño | 63.052.056 B |
| SHA-256 | `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe` |
| Geometrías | 119.498 |
| Última modificación remota | 2026-08-30 09:12:12 UTC |
| ETag remoto | `"0x8DF0676C71229B3"` |

La URL estable redirige con `302` a `release-assets.githubusercontent.com`.
Las URLs firmadas transitorias no se conservan en el agregado ni en este
informe.

## Pruebas HTTP directas

Se enviaron solamente `HEAD` y seis peticiones parciales con
`Accept-Encoding: identity`; no se descargó el fichero completo.

| Solicitud | Resultado | Identidad frente al asset local |
| --- | --- | --- |
| `HEAD` | `200`, `Content-Length: 63052056`, `Accept-Ranges: bytes` | metadatos coherentes |
| `Range: bytes=0-0` | `206`, `Content-Range: bytes 0-0/63052056` | idéntico |
| `Range: bytes=0-16383` | `206` | idéntico |
| `Range: bytes=1048576-1064959` | `206` | idéntico |
| `Range: bytes=63035672-63052055` | `206` | idéntico |
| repetición `bytes=0-16383` | `206` | idéntico |
| `If-Range` con el ETag | `206`, `bytes=16384-32767` | idéntico |

Las respuestas no declararon `Content-Encoding`; los cuerpos de cada slice
coinciden byte a byte con el PMTiles local aprobado. Se observaron `ETag`,
`Last-Modified`, `Age` y `X-Cache: MISS, HIT`; son una señal de caché del CDN,
no una demostración suficiente de la política de caché de navegador del
runtime.

## CORS y navegador

La respuesta Range no contiene `Access-Control-Allow-Origin` ni
`Access-Control-Expose-Headers`. Los cinco smokes Chromium contra la URL
remota fallaron con `TypeError: Failed to fetch`:

| Smoke | Resultado |
| --- | --- |
| España cold | FAIL por CORS/fetch |
| Galicia | FAIL por CORS/fetch |
| Ourense | FAIL por CORS/fetch |
| Cangas del Narcea | FAIL por CORS/fetch |
| Elx | FAIL por CORS/fetch |

No hubo transferencia de PMTiles observada por el servidor local durante esos
smokes: el recurso remoto no llegó a ser legible por el navegador. Por ello no
se puede validar navegación MapLibre, filtros territoriales, reload/cache de
navegador ni la ausencia de descarga completa mediante este hosting. El
resultado `full_download_observed = false` se limita a las requests directas
parciales y a que los fetch del navegador fallaron antes de transferir datos;
no equivale a una validación de navegador satisfactoria.

## Procedimiento reproducible

El auditor `scripts/audit/hosting/es4c3d_real_hosting_range.py` conserva las
cabeceras pertinentes y sanitiza los redirects antes de escribir el resultado.
Con el asset ya existente, el comando ejecutado fue:

```bash
python3 scripts/audit/hosting/es4c3d_real_hosting_range.py \
  --url https://github.com/InThuRain/atlas-incendios/releases/download/national-prototype-staging-es4c3d/esfire30-national-fidelity-territories.pmtiles \
  --browser \
  --output data/audit/hosting/es4c3d_real_hosting_range_validation.json
```

Su salida estructurada es
`data/audit/hosting/es4c3d_real_hosting_range_validation.json`. El comando de
comprobación preserva el FAIL como resultado correcto de esta evidencia:

```bash
python3 scripts/audit/hosting/es4c3d_real_hosting_range.py \
  --url https://github.com/InThuRain/atlas-incendios/releases/download/national-prototype-staging-es4c3d/esfire30-national-fidelity-territories.pmtiles \
  --check \
  --output data/audit/hosting/es4c3d_real_hosting_range_validation.json
```

## Decisión y siguiente paso

GitHub Releases queda validado únicamente para el transporte HTTP Range directo
del asset exacto, pero no como origin cross-origin para PMTiles en navegador.
No es apto para cerrar el gate de release nacional.

La siguiente subfase necesaria es `ES-4C3D2_HOSTING_DELIVERY_REDESIGN`: elegir
y probar un origin que ofrezca simultáneamente Range `206` correcto, CORS
explícito para el prototipo, tipos de contenido estables y una política de
caché verificable. `ES-4D1` no debe comenzar todavía.
