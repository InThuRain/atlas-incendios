# ES-4C3D3 — Revalidación real R2 Range/CORS/browser

## Decisión

`R2_DEV_STAGING_VALIDATION = PASS` y
`REAL_BROWSER_RANGE_CORS = PASS` para el staging técnico. La conclusión se
limita deliberadamente a `RECOMMENDED_FOR_TECHNICAL_STAGING`: `r2.dev` no es
un endpoint de producción y no permite validar su futura política de CDN,
dominio, costes u operación.

## Asset y endpoint

| Campo | Valor |
| --- | --- |
| Endpoint | `https://pub-96622990cd314a1c8431ce65ec2c25ca.r2.dev/esfire30-national-fidelity-territories.pmtiles` |
| Tipo | Cloudflare R2 Public Development URL (`r2.dev`), staging |
| Asset local contrastado | `data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles` |
| Tamaño | 63.052.056 B |
| SHA-256 | `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe` |
| Harness local | `http://127.0.0.1:8765` |

El asset local se comprobó una vez al inicio. El runtime normal conserva su
URL local; el endpoint remoto se inyectó sólo mediante el parámetro efímero
`pmtiles_url` del harness.

## HTTP, integridad y CORS

`HEAD` respondió `200`, `Content-Type: application/octet-stream`,
`Content-Length: 63052056`, `Accept-Ranges: bytes`, ETag
`"6f45635b1c54780e05382587820599f8"` y Last-Modified
`Mon, 31 Aug 2026 14:08:01 GMT`.

Los cuatro slices, solicitados con `Origin: http://127.0.0.1:8765`, fueron
`206`, tuvieron `Content-Range` correcto y coincidieron byte a byte con el
asset local:

| Control | Rango | Bytes |
| --- | --- | ---: |
| Inicial mínimo | `0-0` | 1 |
| Inicial | `0-16383` | 16.384 |
| Intermedio fijo | `1048576-1064959` | 16.384 |
| Final | `63035672-63052055` | 16.384 |

La respuesta expuso `Access-Control-Allow-Origin:
http://127.0.0.1:8765` y los headers Range necesarios. Antes de MapLibre,
Chromium realizó por JavaScript un `fetch` con `Range: bytes=0-0`: obtuvo
`206`, un byte (`0x50`) y leyó `Content-Range` sin error CORS.

## PMTiles/MapLibre y telemetría aislada

El protocolo PMTiles y MapLibre llegaron a `ready` en todos los casos. La
instrumentación de laboratorio envuelve `fetch` sólo cuando recibe
`pmtiles_telemetry=1`; registra únicamente el endpoint PMTiles R2, no EGIF,
GeoJSON municipal ni índice municipal. Ningún GET funcional devolvió `200` con
el cuerpo de 63 MB: `FULL_DOWNLOAD_OBSERVED = false`.

| Escenario | Requests R2 | Range 206 | Bytes de respuesta PMTiles | Nota |
| --- | ---: | ---: | ---: | --- |
| España cold | 11 | 11 | 1.817.016 | filtro nacional temporal |
| Galicia | 18 | 18 | 5.673.313 | slots `ccaa_1..3` |
| Ourense | 30 | 25 | 8.512.165 | slots `prov_1..3`; 5 aborts esperados |
| Cangas del Narcea | 22 | 19 | 2.373.938 | índice municipal provincial, 2.610 IDs; 3 aborts esperados |
| Elx | 26 | 22 | 761.464 | índice municipal, 6 IDs; selecciones EGIF/ESFire30 independientes |
| Recarga Elx, primera | 24 | 19 | 2.217.306 | perfil Chromium efímero compartido |
| Recarga Elx, segunda | 24 | 20 | 2.218.518 | sin descarga completa; 4 aborts esperados |
| España → Galicia → España → Galicia | 10/19/10/19 | 10/19/10/19 | 1.817.015 / 4.244.690 / 1.817.015 / 4.244.690 | diagnóstico de repetición territorial |
| Móvil 390×844, Elx | 17 | 15 | 714.369 | utilizable; 2 aborts esperados |
| Móvil 390×844, Cangas | 16 | 16 | 3.181.225 | utilizable |

Los aborts son cancelaciones controladas de solicitudes PMTiles durante
transiciones/idle de MapLibre (`AbortError`), no errores CORS, de protocolo ni
de fuente: no generan `map_error_events`, y los escenarios alcanzaron
`ready`. La evidencia no convierte estos números en una estimación de factura.

Los conteos son peticiones y bytes efectivamente observados en este harness;
pueden variar con viewport, teselas, estado de mapa y cachés. No representan
tráfico EGIF ni una previsión mensual.

## Recarga, caché y limitaciones

La recarga y la repetición territorial se ejecutaron dentro de un perfil
Chromium efímero compartido para conservar la caché del navegador durante la
secuencia. No se exige cero requests: el criterio es que no haya descarga
completa ni comportamiento patológico. PMTiles también conserva su caché de
sesión mientras el mapa vive.

`R2_DEV_CDN_CACHE_VALIDATION = NOT_APPLICABLE`. El objeto creado desde
Dashboard no expone `Cache-Control`; queda como `STAGING_WARNING`, no como
fallo de Range, CORS, integridad o navegador. Este staging no prueba CDN de
producción, custom domain, DNS, política cacheable inmutable ni coste real.

## Comparación con GitHub Releases

GitHub Releases había pasado Range e integridad, pero Chromium bloqueó la
lectura cross-origin por CORS. R2 `r2.dev` pasó Range, integridad, CORS,
`fetch`, PMTiles y MapLibre; queda demostrado que el problema C3D era de
delivery/CORS, no del PMTiles ni del runtime territorial.

## Próximo paso recomendado

No se inicia automáticamente. Antes de producción hay que decidir
explícitamente entre:

- GitHub Pages same-origin; o
- R2 de producción con custom domain y política de caché/operación.

La decisión debe usar esta telemetría observada, la simplicidad operativa, el
riesgo de facturación y un posterior smoke de hosting real de producción.
