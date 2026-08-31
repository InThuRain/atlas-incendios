# ES-4C3D5 — Decisión de hosting de producción

## Decisión

`INITIAL_PRODUCTION_HOSTING = GITHUB_PAGES`.

`FALLBACK_HOSTING = CLOUDFLARE_R2_CUSTOM_DOMAIN`.

La decisión es inicial y reversible: no implica desplegar el prototipo ni el
PMTiles en el Pages público actual. El criterio decisivo es que GitHub Pages
same-origin ya supera las pruebas de Range, integridad, Chromium, PMTiles y
MapLibre, y minimiza a la vez complejidad operativa y el riesgo de facturación
variable para el volumen actual.

R2 conserva una validación técnica positiva en `r2.dev`, pero su custom domain
de producción no se ha creado ni validado. Debe mantenerse como alternativa de
escalado, no como dependencia inicial obligatoria.

## Evidencia utilizada

No se repitieron smokes C3D3/C3D4. La decisión reutiliza:

- C3D4: Pages same-origin pasó HEAD, cuatro slices `206` byte-idénticos,
  fetch Chromium, PMTiles, MapLibre, Galicia, Ourense, Cangas, Elx, recarga y
  móvil; no hubo descarga completa.
- C3D3: R2 `r2.dev` pasó Range, integridad, CORS explícito, Chromium y
  MapLibre; no valida el cache CDN de producción.
- C3D: GitHub Releases pasó Range e integridad, pero falló como fuente PMTiles
  cross-origin en navegador por CORS. Puede seguir como origen versionado del
  build, no como URL de runtime.

El PMTiles es de 63.052.056 B. El artifact Pages estimado con el activo es
147.252.605 B (≈140,43 MiB), muy por debajo del límite publicado de 1 GB; no
debe interpretarse ese margen actual como garantía para cualquier crecimiento.

## Matriz

| Criterio | GitHub Pages same-origin | R2 con custom domain | Decisión |
| --- | --- | --- | --- |
| Range / integridad | PASS real | PASS en `r2.dev` | Empate técnico actual |
| Navegador / MapLibre | PASS same-origin | PASS con CORS | Pages simplifica |
| CORS | No es necesario | Debe configurarse y mantenerse | Pages |
| Integración actual | Actions + artifact ya existentes | nuevo bucket, credenciales y pipeline | Pages |
| Riesgo de coste variable | no es su modelo de despliegue actual; aplican límites de uso | storage y operaciones por uso tras free tier | Pages |
| Escalado / assets independientes | menor flexibilidad | object storage específico | R2 a futuro |
| Cache-control / purga | control limitado observado | control más explícito posible | R2 a futuro |
| Operación | una plataforma principal | proveedor, pago, CORS, DNS y secretos extra | Pages |
| Dominios de fallo | frontend y asset juntos | frontend y datos separados, pero dos dependencias | contextual |
| Migración futura | viable con manifest | viable si se conserva abstracción URL | empate si se diseña ahora |

Clasificación final:

- GitHub Pages: `RECOMMENDED_FOR_INITIAL_PRODUCTION`.
- Cloudflare R2 con custom domain: `VIABLE` y `FUTURE_SCALING_OPTION`.
- GitHub Releases directo cross-origin: `NOT_RECOMMENDED_FOR_BROWSER_PMTILES`.

## Límites, riesgo económico y tráfico

Consulta oficial realizada el 31/08/2026:

- GitHub Pages documenta un site publicado de hasta 1 GB, un límite blando de
  100 GB/mes de bandwidth y timeout de deploy de 10 minutos. Si se superan las
  cuotas, GitHub puede dejar de servir el site o contactar para reducir el
  impacto; no es un coste monetario automático. [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- R2 Standard incluye 10 GB-mes, 1 millón de operaciones Class A y 10 millones
  de Class B al mes; por encima, los precios documentados son $0,015/GB-mes,
  $4,50/millón Class A y $0,36/millón Class B. El egress directo de R2 es
  gratuito. Activar R2 exige una suscripción y, por tanto, un método de pago.
  [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/), [R2 subscription setup](https://developers.cloudflare.com/r2/get-started/)

Los smokes no son visitas reales, pero delimitan órdenes de magnitud útiles:

- `LIGHT`: alrededor de 0,5 MB PMTiles y 6 Range (overview España).
- `NORMAL`: aproximadamente 1,7–2,6 MB y 6–8 Range (Cangas/Galicia/Ourense
  en los recorridos medidos).
- `HEAVY`: aproximadamente 5,7–8,5 MB y hasta unas decenas de Range, observado
  en recorridos R2 C3D3 con otro harness/viewport.

No se comparan los bytes o requests exactos entre proveedores como benchmark:
cache, viewport, orden de carga y harness no fueron iguales. Como cociente
mecánico —no previsión de usuarios— los 100 GB/mes blandos de Pages equivalen
a unas ~200.000 sesiones de 0,5 MB o ~12.000 de 8,5 MB sin cache compartida.
Para R2, 10 millones de lecturas Class B divididos por 6–30 requests dan un
orden de ~0,33–1,67 millones de sesiones tipo smoke; una sesión real puede
usar cache, recorridos y assets distintos.

## Cache, versionado y URL

El staging Pages respondió `Cache-Control: max-age=600`; no es un blocker. La
producción debe publicar un path inmutable versionado, por ejemplo
`data/esfire30/v1/<sha>/...pmtiles`, y resolverlo desde un manifest o una
configuración de asset base URL. El runtime no debe dispersar URLs hardcoded.

Así una migración Pages → R2 cambia el manifest/configuración y el pipeline de
deployment, no los filtros MVT, `geometry_id` ni la lógica territorial. La QA
de producción deberá volver a comprobar Range, contenido, navegador y cache
del endpoint realmente elegido.

## Flujos conceptuales

### Pages inicial

1. Obtener el asset inmutable desde Release/origen versionado.
2. Verificar tamaño y SHA-256 en GitHub Actions.
3. Copiarlo al artifact Pages con path versionado.
4. Desplegar.
5. Ejecutar smoke post-deploy de Range y navegador same-origin.

### R2 de escalado

1. Preparar object key inmutable y SHA gate.
2. Subir mediante un pipeline autenticado.
3. Fijar cache policy, CORS y custom domain.
4. Ejecutar smoke post-deploy de Range, CORS y navegador.
5. Registrar operaciones/bytes y revisar consumo.

Ninguno se implementa en esta fase.

## Cuándo revisar la decisión

Reconsiderar Pages si la telemetría real se aproxima al límite blando de
bandwidth, el artifact se aproxima al límite de site publicado, varios PMTiles
hacen incómodo el artifact/deploy, los deploys pierden fiabilidad o se necesita
control explícito de cache/purga/dominio. También puede justificarse R2 si el
tráfico y la necesidad operativa compensan aceptar suscripción, monitorización
y facturación por uso. Son triggers, no predicciones.

## Staging y bloqueos

- Conservar temporalmente el repositorio Pages aislado como evidencia técnica;
  revisar su housekeeping tras decidir el diseño de migración, sin tocar el
  Pages público.
- Conservar temporalmente el objeto `r2.dev` como staging técnico; no es
  producción y no se elimina ni modifica ahora.
- No queda un blocker técnico de hosting para diseñar una migración Pages.
  Siguen fuera de alcance causas EGIF/MITECO, permiso CCINIF y municipios
  históricos; no bloquean esta decisión.

## Siguiente fase

Puede iniciarse `ES-4D1_NATIONAL_PRODUCTION_MIGRATION_DESIGN` como diseño,
sin desplegar producción.
