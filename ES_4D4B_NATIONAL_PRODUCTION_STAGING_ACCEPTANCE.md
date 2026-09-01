# ES-4D4B — Despliegue y aceptación remota del staging nacional

## Resultado

`D4B_ATTEMPT_2 = PASS`. El staging nacional se publicó exclusivamente en
<https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/>. La raíz
pública de producción no se modificó.

| Contrato D4A1 | Valor local, runner y remoto |
| --- | --- |
| Ficheros físicos | 350 |
| Bytes físicos | 500.450.914 |
| Ficheros / bytes de payload | 348 / 500.301.758 |
| Payload fingerprint | `bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8` |
| SHA `asset-manifest.json` | `c2c57a70130fd2e4527ac6a50ebb1c86e73bb667d6c5c5940f9b015b9823aceb` |
| SHA `site-identity.json` | `df9b4206eea460942717705559a9705a9fae7fc3039436c199e09118a2019401` |

## Historia de los intentos

### Intento 1 — `FAIL_ARTIFACT_IDENTITY`

- Commit fuente `ab31782`; workflow
  [33516317541](https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/actions/runs/33516317541).
- El gate observó 349 ficheros y `500449871` B frente a `500449810` B
  declarados: +61 B tras la serialización final del manifest.
- Se detuvo antes de `upload-pages-artifact` y `deploy-pages`: no hubo deploy
  ni aceptación browser atribuible a ese artifact.

### Intento 2 — `PASS`

- Corrección D4A1: `a7c3c4d`.
- Commit de workflow del repo staging:
  `99b38f409e6affc219a15b2b37cfd48bfd83b706`.
- Workflow
  [33525357443](https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/actions/runs/33525357443)
  comprobó en el runner los 350 ficheros, 500.450.914 B, payload fingerprint y
  ambos SHA antes del upload.
- Upload: 15 s (15:22:51–15:23:06 UTC); deploy: 17 s
  (15:23:14–15:23:31 UTC); workflow completo: 54 s
  (15:22:39–15:23:33 UTC).

## Entrega Pages y PMTiles

La raíz de staging sirve directamente el `index.html` nacional. Los metadatos
remotos son byte-idénticos a D4A1 y se validó una muestra de frontend, EGIF,
límites, geometría/índice municipal, ICV, EFFIS y PMTiles contra el manifest.
Todas se resuelven bajo el origin de staging:
`UNEXPECTED_EXTERNAL_DATA_DOMAINS = []`.

PMTiles territorial:

- `HEAD 200`, `Content-Length: 63052056`, `Accept-Ranges: bytes`,
  `Content-Type: application/octet-stream`.
- `bytes=0-0`, `0-16383`, `1048576-1064959` y `63035672-63052055` dieron
  `206`, `Content-Range` correcto e identidad byte a byte frente al local.
- `FULL_PMTILES_DOWNLOAD_OBSERVED = false` en todos los smokes; las lecturas
  funcionales fueron Range `206`.

Las cabeceras observadas para HTML, JS, JSON, GeoJSON y PMTiles incluyen
`Cache-Control: max-age=600`, `ETag`, `Last-Modified` y `Accept-Ranges` cuando
aplica. Son observación de staging, no una política de caché de producción.

## Aceptación Chromium

Todos los escenarios pasaron sin CORS, errores PMTiles, excepciones no
controladas ni 404 inesperados. Los bytes son solamente respuestas PMTiles
Range observadas en cada perfil; no son el tamaño del asset ni consumo de
producción.

| Escenario | Resultado | Range / bytes PMTiles |
| --- | --- | ---: |
| España 1968–2026 | resumen EGIF y ESFire30 navegable | 11 / 1.817.016 B |
| Galicia | EGIF y filtro CCAA ESFire30 | 19 / 5.673.314 B |
| Ourense | filtro provincial | 25 / 7.263.651 B |
| Cangas del Narcea | índice municipal, 2.610 IDs, sin hang | 23 / 3.163.989 B |
| GVA 1995 | EGIF, ESFire30 e ICV; EFFIS sin cobertura temporal | 19 / 327.494 B |
| GVA 2024 | ICV; EGIF/ESFire30/EFFIS sin cobertura temporal | 18 / 258.804 B |
| Elx / GVA 2025 | EFFIS: un perímetro snapshot | 22 / 241.238 B |
| GVA 2026 | EFFIS snapshot `20260819T174426Z`, 16 geometrías | 16 / 739.924 B |
| Alacant | filtros ESFire30/ICV/EFFIS coherentes | 24 / 817.255 B |
| Permalink nacional Elx | 6 IDs municipales ESFire30 | 7 / 25.586 B |
| Canarias | ausencia de cobertura ESFire30/ICV/EFFIS, no cero | 7 / 526.208 B |
| Elx móvil 390×844 | mapa, estado de fuentes y permalink utilizables | 14 / 156.349 B |

`2024AL0005` conserva un source record y dos geometrías: geometry-specific
restaura la indicada; record-only conserva únicamente el record y no elige una
geometría arbitraria. Los fixtures `#v=1` de GVA/Elx se restauran sin rewrite
automático. Tras interacción explícita pasan a `#es4c-state-v1`; Back vuelve
al legacy y Forward al nacional. Copy Link usa el formato nacional (fallback
headless permitido). Un permalink nacional directo restaura territorio,
fuentes y selección.

Se verificaron además recarga de Elx 2025 y España → Galicia → España →
Galicia en un perfil Chromium efímero: no hubo estado stale, errores ni
descarga completa. Es diagnóstico de browser/runtime cache, no validación CDN.

## Límites y siguiente paso

- `PRODUCTION_ROOT_INTACT = true`: solo `HEAD` a
  <https://inthurain.github.io/atlas-incendios/>; no se desplegó ni cambió.
- `STAGING_DEPLOYMENT_STATUS = PASS`.
- `REMOTE_ACCEPTANCE_STATUS = PASS`.
- `NATIONAL_RELEASE_CANDIDATE = READY_FOR_ROOT_DECISION`.
- `PRODUCTION_SWITCH_READY = false`.

Warnings no bloqueantes: TTL observado de 600 s y ausencia de decisión sobre
operación/cache de producción. La siguiente fase permitida es
**ES-4D5_ROOT_SWITCH_DECISION**; requiere una decisión explícita y no autoriza
el cambio del root por sí misma.

Evidencia: `data/audit/production/es4d4b_national_production_staging_acceptance.json`.
