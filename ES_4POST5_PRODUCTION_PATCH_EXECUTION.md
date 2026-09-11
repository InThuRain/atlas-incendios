# ES-4POST5 — Ejecución del parche nacional POST2

El artifact POST2 aprobado en POST4 está servido en
https://inthurain.github.io/atlas-incendios/. Se desplegó el TAR exacto, sin
reconstruir datos ni frontend. La aceptación remota confirma completitud ICV,
lectura temporal, popup directo y capacidades nacionales preservadas.

```text
PRODUCTION_PATCH_EXECUTION = PASS
PRODUCTION_PATCH_STATUS = LIVE
REMOTE_PRODUCTION_PATCH_IDENTITY = PASS
MAP_EXPLORATION_PARITY = PASS
NATIONAL_PRODUCT_STATUS = LIVE_POST2
PRODUCTION_PATCH_READY = false
PATCH_PRIORITY = RESOLVED
ROLLBACK_REQUIRED = false
RELEASE_TAG_STATUS = READY_FOR_DECISION
NEXT_PHASE = ES-4POST6_POST_RELEASE_CHECKPOINT
```

## Prechecks y push

Tras `git fetch`, HEAD era `5c5db1b1f33e7bfe64107972ab2dbe66165856a3` y
origin/main `84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c`: ahead 8 / behind 0.
No había cambios versionados; `build/` contenía los artifacts locales sin
versionar y permaneció fuera de los commits. La captura ampliada del precheck
se hizo después de preparar los workflows y registra también esos cambios.

Producción respondió 200 con identidad PRE-POST2
`f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e`.
Staging respondió 200 con la identidad POST2 aceptada. El asset durable y el
gate físico local confirmaron bytes, hashes y ausencia de referencias staging.

El commit predeploy es **`534cfe37a7120904f48c87bba71b4fcb7423bb5f`**.
Un segundo fetch confirmó origin/main sin cambios. El push normal autorizado
incluyó estos nueve commits, en orden:

```text
acdd04a Record national root switch execution
7868a85 Audit GVA map exploration parity
ab71839 Fix ICV province crosswalk completeness
405046a Restore temporal map encoding and overlap readability
c9fe184 Restore direct human map popups
f984c66 Accept national map exploration parity
fca9132 Build reproducible POST2 patch artifact
5c5db1b Validate POST2 patch on remote staging
534cfe3 Prepare fixed POST2 production patch and national rollback
```

Después del push: origin/main = `534cfe3`, ahead/behind = 0/0. No hubo
auto-deploy; se comprobó nuevamente la identidad PRE-POST2 antes del dispatch.

## Contratos de despliegue y rollback

`pages-national-product.yml` sigue siendo exclusivamente manual, sin inputs.
Consume `config/national-product-post2-patch-identity.json`. Descarga la URL
registrada en POST4:

```text
https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-post2-staging-es4post4/national-product-post2-patch.tar.gz
bytes  = 431670756
sha256 = 8903bc91de088e82b7c3410d6b2d2e0a5eda64889ffdcc02569319fcc14e45af
```

El gate verifica TAR antes de extraer y site antes de subir a Pages:

| Identidad POST2 | Valor exacto |
| --- | --- |
| Site | 500 archivos / 812540623 B |
| Payload | 498 archivos / 812320501 B |
| Fingerprint | `97821c6cf3a6282a6304a0ac02c8eb0c0fff762a293de655dde64511c3169d82` |
| Manifest SHA | `557c662dd23df2207f68b6ef36ddae35f0d06b069864ffbb8b3b53ded7a59bd0` |
| Site identity SHA | `f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1` |

`PRE_POST2_ROLLBACK_STATUS = READY`. El nuevo workflow manual
`pages-national-pre-post2-rollback.yml` conserva mecánicamente el anterior
workflow nacional y su contrato por defecto: TAR E4A de 812902400 B, SHA
`4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7` y site
PRE-POST2. No se reconstruyó ese artifact.

El rollback profundo GVA permanece intacto en
`pages-legacy-gva-rollback.yml`, anclado a
`f7a3532f633a247f33dee3ebba9fbcc316c0e534`. Los tres workflows comparten
`concurrency: pages` y `cancel-in-progress: false`. Ambos rollbacks estaban
activos en GitHub antes del dispatch; ninguno fue necesario ni ejecutado.

## Despliegue e identidad pública

| Campo | Valor |
| --- | --- |
| MAIN_COMMIT / trigger | `534cfe37a7120904f48c87bba71b4fcb7423bb5f` |
| Run | [34620607559](https://github.com/InThuRain/atlas-incendios/actions/runs/34620607559) |
| Resultado | success |
| Inicio / fin UTC | 2026-09-11 16:12:05 / 16:13:12 |
| Duración total | 67 s |
| Artifact Pages | `10271688978` |
| Deployment Pages | `6397065009` |
| Artifact evidencia runner | `10272143449` |

El recibo del runner contiene gate TAR PASS, gate site PASS y cero referencias
staging. Protomaps (293324998 B, SHA `72bb270f…aeb729`), ESFire30 (63052056 B,
SHA `3c6eb10…013cfe`) y los nueve glyph ranges conservan sus identidades.

Producción respondió HTTP 200 bajo `/atlas-incendios/`, con manifest y
site-identity exactamente iguales a POST4. Ambos PMTiles pasaron 0-0,
inicial, intermedio y final: HTTP 206, Content-Range correcto y slices
byte-idénticos al archivo local. No se observó descarga completa. Glyphs 9/9,
sin 404 de glyphs; dominios externos runtime observados: `[]`.

## Aceptación funcional en producción

- ICV 1993–2024: **13738 registros / 13739 geometrías**; 1995: **467/467**;
  2024: **472/473**. Se mantiene la recuperación de 1334 geometrías aceptada
  en POST2A/POST4, sin repetir el inventario anual.
- `gva:pif-cv:2016AL0074` aparece, se selecciona y abre popup: 04/09/2016,
  Cumbres del Sol, el Poble Nou de Benitatxell, 689,3 ha, negligencia, GIF.
- `2024AL0005` mantiene un registro y dos geometrías seleccionables:
  `gva:geometry:2024:121:13587` y `gva:geometry:2024:121:13606`.
- Paleta `rgb(44,123,182)` → `rgb(240,82,46)` y leyenda «Año del perímetro»
  dinámicas. La captura 2000–2020 conserva lectura de antigüedad y solapes;
  no representa un cálculo nuevo de recurrencia.
- Popup ICV inmediato: diagnóstico 133 ms; recuperado 115 ms; ESFire30
  144 ms; EFFIS 126 ms. Son observaciones aisladas, no presupuestos de latencia.
- Multi-hit real ICV/ESFire30 muestra dos candidatos por separado. La muestra
  comparte año 1995; no demuestra por sí sola orden entre años distintos.
  La implementación aceptada de orden no se modificó.
- ESFire30 conserva «Perímetro Landsat». Elx/EFFIS 2025 conserva un perímetro
  de 7 ha y aviso provisional; ninguna fuente se fusiona con EGIF.
- España 1995: 5035 ESFire30, 25557 EGIF, 141082,17 ha EGIF conocidas.
  Canarias conserva EGIF y ESFire30 sin cobertura. No se suma un total común.
- Filtros ICV de superficie/GIF/causa y click del histograma pasan. El cambio
  anual actualiza mapa y leyenda y elimina el popup obsoleto.
- Móvil emulado 390×844: mapa, leyenda, elección en multi-hit, popup y
  «Ver detalles» comprobados; no se simuló hardware/red móvil.

## Enlaces, caché y límite de la observación

El enlace nativo conserva periodo, territorio, filtro, selección y cámara en
pestaña nueva y reload. Los enlaces GVA `#v=1` siguen restaurándose. El observer
espera al mapa real, sin depender del nodo antiguo de tests.

En el enlace legado reciente, la carga municipal es asíncrona. El parámetro
`smoke=pais_valencia` activa además una cámara de prueba, por lo que se retiró
del smoke de permalink público. El enlace real se comprobó tras completar las
fuentes y estabilizar el mapa. El perímetro EFFIS de 7 ha no queda seleccionado
si el propio enlace impone un mínimo de 10 ha: es invalidación coherente.

La segunda pasada solicitada utilizó perfiles Chromium nuevos para ICV
1993–2024, lectura temporal y popup, más identidad HTTP sin caché. Staging
POST4 conserva HTTP 200 y el mismo SHA PATCH. Los errores JavaScript capturados
en los smokes son cero. La telemetría agrupa algún HTTP 404 en «other», también
presente en POST4; no se presenta como cero absoluto de respuestas HTTP 404.
No hay fallos de glyphs, de los PMTiles ni bloqueo de producto.

## Pruebas y cierre

Se ejecutaron seis tests específicos de workflows: YAML manual, orden de
gates, concurrencia, contrato fijo, rechazo de SHA TAR erróneo antes de extraer
y rechazo de site identity errónea antes del deploy. El gate físico local y
el runner real pasaron. No se ejecutó la suite completa.

El auditor reanudable guarda cada escenario por separado. Su `--group check`
valida cobertura de casos sin abrir Chromium ni red; `--group finalize` reúne
los recibos y genera `data/audit/product/es4post5_production_patch_execution.json`.
Las capturas y observaciones de trabajo permanecen en `build/es4post5/`.

El commit de cierre es sólo local. No se crea tag ni se inicia POST6.
Se recomienda **`national-product-v1.0.0`** para decisión explícita: no existe
todavía un tag de versión nacional; el breve despliegue previo sin versión se
conserva por SHA y deployment. `v1.0.1` sugeriría un `v1.0.0` ya publicado.

Pendientes P1/P2, fuera de este parche: brush de histograma, blancos táctiles
del histograma móvil, feedback de carga municipal fría, z13/relieve/POI y
ranking ESFire30. Siguiente fase: `ES-4POST6_POST_RELEASE_CHECKPOINT`.
