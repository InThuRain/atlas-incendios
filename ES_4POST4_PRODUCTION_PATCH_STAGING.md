# ES-4POST4 — Staging remoto del parche POST2

## ¿El artifact POST2 exacto conserva la paridad de exploración cartográfica al servirse remotamente?

Sí. El mismo TAR reproducible aprobado en POST3 fue publicado como asset
inmutable de **staging**, pasó el gate dentro del runner de Pages y la web
remota conserva tanto la identidad física como las capacidades de exploración
recuperadas en POST2A+B+C.

```text
PATCH_STAGING_STATUS                 = PASS
REMOTE_PATCH_IDENTITY_STATUS         = PASS
REMOTE_PATCH_MAP_PARITY              = PASS
PRODUCTION_PATCH_RELEASE_CANDIDATE  = READY_FOR_PRODUCTION_PATCH
PATCH_PRIORITY                       = HIGH
RELEASE_TAG_STATUS                   = HOLD
NEXT_PHASE                           = ES-4POST5_PRODUCTION_PATCH_EXECUTION
```

POST4 modificó únicamente el repositorio de staging. No hubo `push` a
`InThuRain/atlas-incendios`, workflow productivo, despliegue productivo ni tag
de producto. La producción continúa con la identidad pre-POST2.

## Transporte y despliegue de staging

| Elemento | Valor |
| --- | --- |
| Repo de staging | `InThuRain/atlas-incendios-es4c3d4-pages-staging` |
| URL desplegada | `https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/` |
| Golden anterior preservado | `national-product-staging-es4e4a` / `national-product-staging.tar` |
| Golden anterior | 812.902.400 B, `4bcc80f…781edb7` |
| Release PATCH | `national-product-post2-staging-es4post4` (prerelease) |
| Asset PATCH | `national-product-post2-patch.tar.gz` |
| Asset PATCH | 431.670.756 B, `8903bc91de088e82b7c3410d6b2d2e0a5eda64889ffdcc02569319fcc14e45af` |
| Asset URL | `https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-post2-staging-es4post4/national-product-post2-patch.tar.gz` |
| Commit de workflow de staging | `f856121f8f8f72f85acd38134bf223cef221c14f` |
| Run manual | `34528201012` |
| Duración | 79 s (20:44:50Z–20:46:09Z) |
| Artifact Pages | `10172427825` (432.204.597 B comprimidos) |
| Deployment Pages | `6380784035` |
| Evidencia de identidad del runner | artifact `10172412486` |

El workflow no admite URL, tag ni artifact introducidos por operador: descarga
el TAR anterior por URL fija, verifica bytes/SHA, lo extrae de forma segura y
verifica la identidad POST2 antes de `upload-pages-artifact` y deploy. No
reconstruye datasets, summaries, PMTiles ni frontend.

## Gates de identidad

| Propiedad | POST2 esperado | Runner | Pages remoto |
| --- | ---: | ---: | ---: |
| Ficheros de site | 500 | 500 | 500 |
| Bytes de site | 812.540.623 | 812.540.623 | 812.540.623 |
| Ficheros payload | 498 | 498 | 498 |
| Bytes payload | 812.320.501 | 812.320.501 | 812.320.501 |
| Payload fingerprint | `97821c6…c3169d82` | igual | igual |
| `asset-manifest.json` | `557c662d…d7a59bd0` | igual | igual |
| `site-identity.json` | `f8fe88d6…8ba785a1` | igual | igual |

El runner verificó además Protomaps (293.324.998 B,
`72bb270f…aeb729`), ESFire30 (63.052.056 B, `3c6eb10…013cfe`) y los nueve
ranges de glyphs.

Producción fue consultada con `Cache-Control: no-cache`: respondió HTTP 200 y
conserva `site-identity.json` SHA
`f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e`.
Por tanto sigue siendo `LIVE_PRE_POST2` y no se alteró por POST4.

## Assets remotos

La raíz de staging respondió HTTP 200. El manifest declara cero dependencias
runtime externas y cero dominios externos de datos. Los 9/9 glyph ranges
resolvieron; no hubo 404 ni ranges fuera de bundle.

Las cuatro lecturas de cada PMTiles devolvieron HTTP 206, `Content-Range`
coherente y bytes idénticos al slice local; no hubo descarga completa:

| Asset | 0–0 | Inicial 16 KiB | Intermedio 16 KiB | Final 16 KiB |
| --- | --- | --- | --- | --- |
| Protomaps 293.324.998 B | `0-0` | `0-16383` | `146654307-146670690` | `293308614-293324997` |
| ESFire30 63.052.056 B | `0-0` | `0-16383` | `31517836-31534219` | `63035672-63052055` |

## Aceptación de producto remota

### ICV y lectura temporal

- Comunitat Valenciana 1993–2024: **13.738 records / 13.739 geometrías**.
  No reapareció la regresión 12.404/12.405.
- Recuperadas 2016–2019: **341 / 346 / 375 / 272** respectivamente.
- 1995: **467 / 467**; 2024: **472 / 473**.
- `gva:pif-cv:2024AL0005` mantiene un record con las dos geometrías
  `gva:geometry:2024:121:13587` y `gva:geometry:2024:121:13606`, ambas
  seleccionables de forma independiente.
- El estilo remoto sigue interpolando por año desde
  `rgb(44,123,182)` (antiguo) a `rgb(240,82,46)` (reciente). La leyenda dice
  **“Año del perímetro”**, muestra los extremos del rango y cambia a un año
  único después de seleccionar una barra del histograma.
- El rango 2000–2020 cargó 8.519 perímetros ICV y permite inferir antigüedad
  y recurrencia visual por color más leyenda, sin abrir una barra lateral:
  `RECURRENCE_HUMAN_TEST = PASS`.

### Click, popup y solapes

El click abre un popup humano inmediato sin solicitar DETAIL. En 1995 el ICV
muestra fecha, municipio, provincia, superficie, causa y **Ver detalles**.
El perímetro recuperado `gva:pif-cv:2016AL0074` apareció y abrió su popup:
04/09/2016, el Poble Nou de Benitatxell, 689,3 ha, negligencia y GIF.

Las latencias de diagnóstico fueron ICV 1995 **87,36 ms**, ICV recuperado
2016 **99,64 ms**, ESFire30 **108,44 ms**, EFFIS **129,26 ms** y popup ICV en
390×844 **63,28 ms**. No son SLA, pero mantienen la respuesta perceptiblemente
inmediata.

En un solape real, el chooser anunció **“2 perímetros en este punto”** y
presentó por separado `1995 · Cocentaina / ICV · Generalitat Valenciana` y
`1995 · Perímetro Landsat / ESFire30`. No se fusionan fuentes. El popup
ESFire30 dice explícitamente **“Perímetro Landsat”** y no inventa atributos
administrativos. En Elx 2025, EFFIS sigue siendo un perímetro satelital
provisional de 7 ha.

El recorrido periodo → mapa → color/solape → click → popup → **Ver detalles**
se completó sin tener que conocer antes los datasets: `MAP_FIRST_HUMAN_JOURNEY
= PASS`.

### Filtros, histograma y regresiones nacionales

Los filtros ICV de superficie mínima, GIF y causa se aplicaron sin alterar el
dominio temporal. Un click de histograma cambió 2016→2017, actualizó la
leyenda y eliminó el popup anterior, por lo que no queda selección stale.

España 1995 conserva las series sin sumarlas: **5.035 perímetros ESFire30**,
**25.557 registros EGIF** y **141.082,17 ha EGIF conocidas**. Canarias conserva
EGIF y comunica ESFire30 como **sin cobertura**, no como “0 incendios”.

En móvil (390×844) el mapa, leyenda temporal, tap, popup, multi-hit y
**Ver detalles** funcionan; `MOBILE_MAP_EXPLORATION = PARITY`.

## Estado, enlaces y errores

El permalink nativo `es4c-state-v1` preservó el estado completo en pestaña
nueva y tras recarga, incluidos territorio, periodo, filtro mínimo ICV,
selección y centro/zoom. Los enlaces GVA heredados `#v=1` histórico y reciente
restauraron mapa y estado sin errores; pueden conservar el hash legado en vez
de reescribirse, comportamiento compatible y deliberado.

Las sesiones Chromium fueron perfiles aislados y efímeros. Una segunda
comprobación limpia de identidad, GVA 1993–2024, mapa temporal y popup pasó.
No hubo errores runtime/browser inesperados ni descargas PMTiles completas.

## Validaciones ejecutadas

```bash
python3 -m unittest \
  tests/test_es4post4_production_patch_staging.py \
  tests/test_es4post2a_icv_geometry_completeness.py \
  tests/test_es4post2b_temporal_encoding_and_overlap.py \
  tests/test_es4post2c_direct_human_popup.py
# 21 tests OK

python3 scripts/audit/product/es4post4_production_patch_staging.py \
  --check --output data/audit/product/es4post4_production_patch_staging.json
# valid: true; failures: []
```

La evidencia completa —identidad local/remota, release, runner, Pages,
HTTP Range, CDP y resultados de cada escenario— está en
`data/audit/product/es4post4_production_patch_staging.json`.

## Decisión y límite de fase

El candidate PATCH está preparado para la decisión y ejecución explícita de
producción en `ES-4POST5_PRODUCTION_PATCH_EXECUTION`. Esa fase no se inicia
aquí. El tag de release de producción permanece en **HOLD** y el rollback GVA
no se ha modificado.
