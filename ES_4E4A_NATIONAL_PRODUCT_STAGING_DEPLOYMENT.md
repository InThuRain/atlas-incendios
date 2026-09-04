# ES-4E4A — Despliegue exacto del producto nacional en staging

## Resultado

**PASS.** El artefacto de producto aceptado localmente en E3D1/E3D2 se ha
publicado en el staging Pages ya existente sin reconstruirlo. La producción
valenciana sigue separada e intacta.

- Staging: <https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/>
- Repositorio / rama: `InThuRain/atlas-incendios-es4c3d4-pages-staging` / `main`.
- Commit previo de staging: `99b38f409e6affc219a15b2b37cfd48bfd83b706`.
- Commit nuevo de staging: `a210ab94812aab85686ef76ef4654b954426bc75`.
- Workflow: [33853441734](https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/actions/runs/33853441734), `success`, 64 s (08:26:32–08:27:36 UTC, 04/09/2026).

E4A no es una aceptación completa de producto remoto. Esa revisión queda para
`ES-4E4B_NATIONAL_PRODUCT_REMOTE_ACCEPTANCE`.

## Gate de identidad y transporte

El único objeto desplegado fue `build/national-product-staging/`, previamente
validado por `scripts/check_national_product_artifact.py`:

| Contrato | Local | Runner extraído | Remoto |
| --- | ---: | ---: | ---: |
| Ficheros físicos | 497 | 497 | 497 (`site-identity.json`) |
| Bytes físicos | 812.510.441 | 812.510.441 | 812.510.441 |
| Ficheros payload | 495 | 495 | 495 |
| Bytes payload | 812.291.384 | 812.291.384 | 812.291.384 |
| Payload fingerprint | `10582ec0…c51b18df3` | igual | igual |
| SHA `asset-manifest.json` | `377b5655…69cf96e` | igual | igual |
| SHA `site-identity.json` | `f5e80a72…813da04e` | igual | igual |

El transport fue un TAR temporal de Release, no contenido Git:

- release prerelease: `national-product-staging-es4e4a`;
- archivo: `national-product-staging.tar`;
- bytes: `812.902.400`;
- SHA-256: `4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7`.

El workflow descargó el TAR, comprobó tamaño y SHA, lo extrajo y ejecutó el
checker independiente antes de `upload-pages-artifact` y `deploy-pages`. Por
tanto no hubo build, regeneración de assets ni inclusión de los 812 MB en el
historial Git. GitHub Pages aceptó el tamaño físico del sitio; el estado de
capacidad permanece `LIMITED_BUT_ACCEPTABLE` (187.489.559 B bajo el límite
conservador usado en E3D2).

## Identidad y rutas remotas

`GET /` devolvió `200`. Las dos identidades remotas descargadas son byte a byte
las aprobadas:

- `asset-manifest.json`: SHA-256 `377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e`.
- `site-identity.json`: SHA-256 `f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e`.

Las muestras de frontend, resumen, destacados, territorios, ICV y EFFIS
devolvieron `200` con tamaño y SHA coincidentes con el manifest. Las nueve
fuentes de glyph de Noto Sans empaquetadas devolvieron `200`, incluidos
`0-255`, `8192-8447` y `11520-11775`. No hubo rutas a árboles fuente, staging
D4B antiguo ni dominios externos de datos/runtime: `[]`.

## PMTiles, Range y cabeceras

Los dos PMTiles usan rutas relativas y versionadas bajo el mismo origin Pages.
Cada `HEAD` fue `200`, con `Accept-Ranges: bytes`, tipo
`application/octet-stream` y el tamaño esperado. Los cuatro cortes (`0-0`,
16 KiB inicial, 16 KiB medio determinista y 16 KiB final) respondieron `206`,
`Content-Range` correcto y bytes idénticos al archivo local.

| Asset | Bytes | SHA-256 | Resultado Range |
| --- | ---: | --- | --- |
| Protomaps | 293.324.998 | `72bb270f…aeb729` | PASS |
| ESFire30 territorial | 63.052.056 | `3c6eb10…013cfe` | PASS |

Ejemplos ESFire30: `0-0/63052056`, `0-16383`,
`31517836-31534219` y `63035672-63052055`; todos `206` y byte-idénticos. El
fetch Range directo en Chromium devolvió `206` y un byte legible. Los recursos
PMTiles observados por Chromium fueron `206`; no se observó descarga completa.

Las cabeceras observadas para HTML, CSS, JS, JSON, glyph y ambos PMTiles fueron
`Cache-Control: max-age=600`, `ETag` y `Last-Modified`; `Accept-Ranges` aparece
para los objetos consultados. Son una observación de staging Pages, no una
política de caché final de producción. La advertencia del runner sobre acciones
Node 20 forzadas temporalmente a Node 24 no afectó al resultado del deploy.

## Smokes rápidos remotos

Todos pasaron con perfil Chromium limpio, sin errores runtime ni dominios
externos de runtime:

| Caso | Validación E4A |
| --- | --- |
| España 1995 | base Protomaps, límites BDLJE, resumen EGIF, ESFire30 e histograma disponibles. |
| País Valencià 1995 | ICV, EGIF, ESFire30 activado explícitamente, base y resumen disponibles. |
| Elx 2025 | municipio, EFFIS, base y resumen disponibles; no se presenta ESFire30 fuera de su cobertura. |
| Móvil 390×844 | raíz abre, mapa visible primero, sin crash ni error de assets. |

La atribución visible incluye Protomaps, © OpenStreetMap contributors y
“Obra derivada de BDLJE CC-BY 4.0 ign.es”, además de las atribuciones de fuente
que corresponden a cada estado. Esta fase no profundiza en UX ni en recorridos
humanos completos.

## Producción y decisión

El control no destructivo a <https://inthurain.github.io/atlas-incendios/>
devolvió `200`, con el HTML previo (última modificación observada: 26/08/2026).
No se modificaron raíz, DNS, Pages de producción, redirecciones ni D5.

```text
STAGING_DEPLOYMENT_STATUS       = PASS
REMOTE_ARTIFACT_IDENTITY_STATUS = PASS
REMOTE_RANGE_STATUS             = PASS
REMOTE_PACKAGING_SMOKE_STATUS   = PASS
PRODUCT_RELEASE_CANDIDATE       = READY_FOR_REMOTE_PRODUCT_ACCEPTANCE
D5_STATUS                       = PAUSED_FOR_PRODUCT_RECONCILIATION
NEXT_PHASE                      = ES-4E4B_NATIONAL_PRODUCT_REMOTE_ACCEPTANCE
```

No se establece `PRODUCTION_SWITCH_READY`: requiere E4B y una decisión D5
separada.

## Evidencia y reproducibilidad

- Agregado: `data/audit/product/es4e4a_national_product_staging_deployment.json`.
- Workflow versionable: `benchmarks/es4e4a/pages-staging-workflow.yml`.
- Empaquetador sin rebuild: `scripts/package_national_product_artifact.py`.
- Auditor remoto: `scripts/audit/hosting/es4e4a_national_product_staging.py`.

El transport puede recrearse localmente desde el mismo artefacto aceptado con:

```bash
python3 scripts/package_national_product_artifact.py \
  --artifact build/national-product-staging \
  --output build/es4e4a/national-product-staging.tar
```

El workflow debe recibir explícitamente la URL, bytes y SHA del resultado; no
acepta ni ejecuta un rebuild en el runner.
