# ES-4C3D2 — Rediseño de delivery del PMTiles nacional

## Resultado de diseño

| Rol | Opción |
| --- | --- |
| `PREFERRED` para el siguiente staging | Cloudflare R2 mediante URL pública de desarrollo, con CORS explícito |
| `FALLBACK` | GitHub Pages en un staging same-origin aislado |
| Estado | `STAGING_READY_FOR_REVALIDATION` |
| Siguiente fase, tras aportar la URL | `ES-4C3D3_REAL_HOSTING_REVALIDATION` |

No se ha creado bucket, dominio, DNS, repositorio de staging ni upload. No se
ha modificado GitHub Pages, producción, el runtime, el PMTiles ni la prerelease
de C3D.

La afirmación anterior queda actualizada por el staging que el usuario creó
externamente el 31/08/2026: existe bucket R2 de desarrollo y un único objeto
con el PMTiles aprobado. No se ha modificado GitHub Pages, producción, runtime
ni el PMTiles.

## Por qué GitHub Releases no sirve como origin PMTiles de navegador

La prerelease C3D sirvió correctamente el asset exacto: `HEAD`, todos los
rangos deterministas y `If-Range` devolvieron `206`; los bytes coincidieron con
el PMTiles local. La URL estable redirige a `release-assets.githubusercontent.com`.

La respuesta final no incluyó `Access-Control-Allow-Origin` ni
`Access-Control-Expose-Headers`. Chromium, ejecutando el prototipo local con
la URL remota inyectada, falló en España, Galicia, Ourense, Cangas y Elx antes
de que PMTiles/MapLibre pudiera leer el archivo. Es un fallo CORS de delivery,
no de datos, Range, MapLibre ni filtros territoriales.

GitHub Releases se conserva como fuente inmutable de descarga y evidencia,
pero queda `NOT_RECOMMENDED` como origin cross-origin de PMTiles.

## Delivery actual y escala Pages

El Atlas actual se publica desde `.github/workflows/pages.yml`: Actions descarga
el bundle inmutable `public-data-v5` desde una Release, verifica sus checksums,
monta un artifact autocontenido y lo despliega con GitHub Pages. El origin
público actual es `https://inthurain.github.io`, bajo
`/atlas-incendios/`. El binario nacional no está en Git.

El artifact local actual mide 84.200.549 B. Al incorporar exclusivamente este
PMTiles mediría aproximadamente 147.252.605 B (140,43 MiB): sigue por debajo
del límite publicado de 1 GB de GitHub Pages, pero consume ~14,73 % de ese
presupuesto con un solo PMTiles. El artifact de Actions admite un tar inferior
a 10 GB. GitHub Pages también declara un límite blando de 100 GB/mes; por ello
su idoneidad para un Atlas nacional con más assets debe medirse antes de asumir
que es suficiente para tráfico público sostenido.

Los ranges previos muestran que una sesión no equivale a 63 MB: España observó
~1,48 MB, Galicia ~5,67 MB, Cangas ~3,05 MB y Elx ~0,88 MB en entornos locales
distintos. Son órdenes de magnitud diagnósticos, no previsiones de tráfico ni
garantías de caché/CDN.

## Matriz de candidatos

| Candidato | Range | CORS / same-origin | Caché | Complejidad / repo | Fit de producción | Riesgo principal |
| --- | --- | --- | --- | --- | --- | --- |
| R2 URL pública de desarrollo | Requiere C3D3 | CORS configurable | `r2.dev` no sirve para validar caché de producción | Medio / binario fuera de Git | Alto con custom domain posterior | Nueva cuenta/configuración; `r2.dev` rate-limited |
| Pages same-origin aislado | Requiere staging real | CORS no necesario para el PMTiles | Requiere medición real | Medio / workflow descarga y verifica Release | Viable inicialmente | Range sin probar y límite blando de ancho de banda |

No hay tercer candidato: el proyecto no usa actualmente otra infraestructura
de objetos/CDN cuya evaluación aportase evidencia más útil que estos dos.

## Opción preferida: R2 para staging

R2 permite probar el mismo contrato que falló en C3D sin desplegar el prototipo
nacional: navegador local → URL remota → PMTiles. Por tanto reutiliza el
auditor C3D, el override `pmtiles_url` y los smokes España/Galicia/Ourense/
Cangas/Elx. La URL `r2.dev` se usará solo para staging; la documentación de
Cloudflare la considera de desarrollo y con rate limiting. Si C3D3 pasa, una
decisión posterior de producción requerirá custom domain, política de caché y
un nuevo smoke real; esta fase no lo presupone.

### Asset y URL esperada

| Campo | Valor |
| --- | --- |
| Asset fuente | `data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles` |
| Tamaño | 63.052.056 B |
| SHA-256 obligatorio | `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe` |
| Bucket propuesto | `atlas-incendios-es4c3d-staging` |
| Object key inmutable | `esfire30/v1/3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe/esfire30-national-fidelity-territories.pmtiles` |
| URL esperada | `https://<public-development-url>/esfire30/v1/<sha256>/esfire30-national-fidelity-territories.pmtiles` |
| Metadata cache de objeto | `public, max-age=31536000, immutable` |

El path contiene el SHA; nunca se sobrescribe. Una versión futura debe usar
otro directorio/hash y otro manifiesto, no cambiar bytes bajo la misma URL.

### Staging real preparado

| Comprobación de preflight | Resultado |
| --- | --- |
| URL | `https://pub-96622990cd314a1c8431ce65ec2c25ca.r2.dev/esfire30-national-fidelity-territories.pmtiles` |
| `HEAD` | `200`, `Content-Length: 63052056`, `Accept-Ranges: bytes` |
| Tipo | `application/octet-stream` |
| `Range: bytes=0-0` | `206`, `Content-Range: bytes 0-0/63052056` |
| CORS para `http://127.0.0.1:8765` | correcto; origin y headers expuestos presentes |
| ETag / Last-Modified | presentes |
| Cache-Control | ausente en el upload de Dashboard; warning de staging |

El objeto se ha subido con el filename original en la raíz, no bajo el path
SHA-addressed inicialmente propuesto. Es aceptable **solo para este bucket
aislado de staging** porque C3D3 volverá a comprobar sus slices frente al SHA
local y el objeto no se sobrescribirá. La publicación futura deberá recuperar
la URL/key inmutable versionada recomendada.

Este preflight no valida aún los ranges inicial/intermedio/final, la igualdad
byte a byte, MapLibre, la recarga ni el comportamiento de caché del navegador.

### CORS de staging mínimo

La política preparada en
`benchmarks/es4c3d2/r2-cors-staging.json` no usa `*`. Autoriza únicamente el
origin fijo del harness C3D3 (`http://127.0.0.1:8765` y su alias `localhost`)
y el origin público actual del Atlas. Autoriza `GET`/`HEAD`, los headers de
lectura condicional/range y expone `Content-Range`, tamaño, ETag y metadatos de
caché útiles para auditoría.

C3D3 debe servir el harness en ese puerto fijo. El runner C3D actual elige un
puerto aleatorio; usarlo sin esa adaptación obligaría a un wildcard CORS y no
es aceptable para este staging restringido.

## Incidencia de compatibilidad local y ruta de Dashboard

El 30/08/2026 se comprobó que este equipo usa Ubuntu GLIBC 2.31 y Node 10.19.0.
La versión actual de Wrangler descargada con `npx` intenta ejecutar `workerd`,
que exige `GLIBC_2.32` a `GLIBC_2.35`; todos los comandos fallaron antes de
autenticarse o de contactar con R2. No hay evidencia de bucket, upload ni CORS
creados parcialmente. Instalar `libc++1` no resuelve una incompatibilidad de
versión de `libc.so.6`.

No se actualizará el sistema operativo ni se instalarán dependencias globales
para esta subfase. La alternativa operativa equivalente es el panel de
Cloudflare, que no depende del binario local de Wrangler:

1. Entrar en **R2 Object Storage** y crear el bucket
   `atlas-incendios-es4c3d-staging`.
2. Subir el PMTiles ya verificado. Si el panel permite elegir key, usar el key
   SHA-addressed de la tabla anterior; si no, subir el filename original en la
   raíz del bucket, registrar la URL exacta en C3D3 y no sobrescribirlo.
3. En **Settings → Public access**, habilitar únicamente la **Public Development
   URL** para este bucket de staging.
4. En **Settings → CORS Policy**, pegar el contenido de
   `benchmarks/es4c3d2/r2-cors-staging-dashboard.json`. Este es el formato del
   Dashboard; `r2-cors-staging.json` mantiene el formato de Wrangler y no debe
   pegarse directamente allí.
5. Registrar la URL pública que ofrece el panel, sin crear custom domain ni DNS.

Para el upload desde Dashboard no se puede fijar de forma portátil la metadata
`Cache-Control`; es un warning aceptado exclusivamente para C3D3. Esa
revalidación comprobará Range, CORS y navegador. La metadata `immutable` sigue
siendo la recomendación obligatoria para una futura carga por CLI soportado o
por el pipeline de producción, no un criterio para bloquear este staging.

## Fallback: Pages same-origin aislado

Si R2 no está disponible o C3D3 no pasa, crear un repositorio Pages de staging
separado, nunca el Pages público del Atlas. Su workflow deberá descargar el
asset desde la prerelease C3D, verificar el SHA, copiarlo al artifact Pages y
servirlo desde una ruta versionada como:

```text
https://inthurain.github.io/atlas-incendios-es4c3d-pages-staging/data/esfire30/v1/<sha256>/esfire30-national-fidelity-territories.pmtiles
```

El binario no entra en Git. El staging necesita además un harness MapLibre
mínimo same-origin, distinto del prototipo público, para verificar Range,
filtros y selección antes de considerar Pages. No se ha creado ese repositorio
ni harness remoto en C3D2.

## Comandos externos para el staging preferido (solo entorno compatible)

Estos comandos crean estado externo y los debe ejecutar el usuario desde la
raíz del repositorio, después de iniciar sesión en la cuenta Cloudflare elegida.
No guardan tokens en el repositorio.

```bash
sha256sum data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles
stat --printf='%s\n' data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles

npx wrangler login
npx wrangler r2 bucket create atlas-incendios-es4c3d-staging
npx wrangler r2 bucket dev-url enable atlas-incendios-es4c3d-staging
npx wrangler r2 bucket cors set atlas-incendios-es4c3d-staging --file benchmarks/es4c3d2/r2-cors-staging.json
npx wrangler r2 bucket cors list atlas-incendios-es4c3d-staging

npx wrangler r2 object put \
  atlas-incendios-es4c3d-staging/esfire30/v1/3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe/esfire30-national-fidelity-territories.pmtiles \
  --file data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles \
  --content-type application/octet-stream \
  --cache-control 'public, max-age=31536000, immutable'

npx wrangler r2 bucket dev-url get atlas-incendios-es4c3d-staging
```

El SHA esperado debe coincidir exactamente antes del `put`; cualquier otra
salida aborta el staging. La URL dev resultante es pública y solo sirve para la
validación C3D3; no debe usarse como URL de producción ni apuntarse desde
GitHub Pages.

En este equipo, no repetir esos comandos `npx wrangler`: seguir la ruta de
Dashboard anterior. En una máquina con GLIBC/Node compatibles siguen siendo la
alternativa reproducible por CLI. El staging actual ya está creado, de modo que
estos comandos se conservan únicamente como receta reproducible y no deben
ejecutarse contra el bucket existente.

## Qué aportar para C3D3

Pegar, sin tokens ni URLs firmadas:

1. captura o transcripción de la CORS Policy guardada en Dashboard;
2. la URL pública final completa del objeto;
3. la salida de `curl -sSIL -H 'Origin: http://127.0.0.1:8765' <URL>`;
4. la salida de `curl -sSIL -H 'Range: bytes=0-0' -H 'Origin: http://127.0.0.1:8765' <URL>`.

Los puntos 2–4 ya se comprobaron directamente contra el staging actual; la
captura de la política sigue siendo útil como evidencia administrativa, pero
no bloquea C3D3 porque el CORS efectivo ya se observó en respuesta.

No ejecutar todavía el auditor C3D con `--browser`: C3D3 fijará primero el
origin local del harness para que coincida con la política CORS restringida.

## Riesgos y límites

- La documentación de R2 configura CORS, pero Range, bytes y navegador solo
  cuentan como válidos tras el mismo smoke real C3D3.
- `r2.dev` no aporta caché/WAF/bot management de producción; un custom domain
  posterior es necesario antes de adoptar R2 para público.
- Cambiar una política CORS detrás de un custom domain puede requerir purge de
  caché; por eso el object key staging es inmutable.
- Pages sigue siendo alternativa razonable para una fase inicial, pero no se
  debe asumir Range ni ignorar su límite blando de ancho de banda.

## Cierre de C3D2

C3D2 está funcionalmente terminado: diseñó dos candidatos, seleccionó R2 como
staging preferido, dejó Pages como fallback, preparó políticas reproducibles y
comprobó que el endpoint R2 real responde con Range/CORS mínimos. La única
tarea pendiente pertenece a C3D3: adaptar el harness a origen fijo y ejecutar
la batería real completa contra esta URL. No se inicia automáticamente.

## Fuentes consultadas

- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Cloudflare R2 CORS](https://developers.cloudflare.com/r2/buckets/cors/)
- [Cloudflare R2 public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/)
- [Cloudflare R2 cache/custom domains](https://developers.cloudflare.com/cache/interaction-cloudflare-products/r2/)
- [Wrangler R2 commands](https://developers.cloudflare.com/workers/wrangler/commands/r2/)
