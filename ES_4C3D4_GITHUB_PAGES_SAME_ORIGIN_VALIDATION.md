# ES-4C3D4 — GitHub Pages same-origin staging validation

## Estado

`PASS` el 31/08/2026 contra el Pages aislado:

`https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/`

El repositorio de staging es independiente del Pages público
`https://inthurain.github.io/atlas-incendios/`, que no se ha modificado.

## Artifact preparado

`scripts/build_es4c3d4_pages_staging.py` parte del artifact público actual y
añade un harness aislado en `/es4c3d4/`, los bundles autocontenidos MapLibre y
PMTiles descargados en CI con versión/SHA fijados, dos fixtures municipales
exactos de smoke (Elx y Cangas del Narcea) y el PMTiles bajo
`/data/esfire30-national-fidelity-territories.pmtiles`.

Antes de copiar el binario, el builder aborta salvo que mida 63.052.056 B y
tenga SHA-256 `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`.
No se añade el binario a Git.

El site público de referencia mide 84.200.549 B. Sólo con el PMTiles sumaría
147.252.605 B (140,43 MiB); el manifest generado por el staging registrará el
tamaño real, que incluye el pequeño harness y sus vendors.

El harness usa una URL relativa same-origin, aplica exactamente los filtros
MVT CCAA/provincia y emplea fixtures extraídos de los índices municipales
provinciales auditados para Cangas del Narcea (2.610 IDs) y Elx (6 IDs). No
carga EGIF ni modifica el runtime normal.

## Deployment de staging reproducible

Crear un repositorio público aislado, por ejemplo
`InThuRain/atlas-incendios-es4c3d4-pages-staging`, y habilitar Pages con
**GitHub Actions** como fuente. No usar el repositorio ni el Pages público del
Atlas.

Tras hacer commit de esta preparación, ejecutar desde la raíz del Atlas:

```bash
git rev-parse HEAD
```

Usar el SHA impreso como `SOURCE_REF`:

```bash
STAGING_REPO=InThuRain/atlas-incendios-es4c3d4-pages-staging
SOURCE_REF=<SHA-DEL-COMMIT-DE-PREPARACION-C3D4>

gh repo create "$STAGING_REPO" --public --add-readme
git clone "https://github.com/$STAGING_REPO.git" /tmp/atlas-es4c3d4-pages-staging
mkdir -p /tmp/atlas-es4c3d4-pages-staging/.github/workflows
cp benchmarks/es4c3d4/pages-staging-workflow.yml \
  /tmp/atlas-es4c3d4-pages-staging/.github/workflows/pages-staging.yml
cd /tmp/atlas-es4c3d4-pages-staging
git add .github/workflows/pages-staging.yml
git commit -m "Add ES-4C3D4 Pages staging workflow"
git push
```

En **Settings → Pages**, seleccionar **Build and deployment → Source: GitHub
Actions** para ese repositorio nuevo. Después lanzar:

```bash
gh workflow run pages-staging.yml --repo "$STAGING_REPO" -f source_ref="$SOURCE_REF"
gh run watch --repo "$STAGING_REPO"
```

El job descarga el PMTiles de la prerelease existente, verifica tamaño/SHA y
publica únicamente el artifact de ese staging. No sube datos desde el equipo
del usuario ni cambia el Pages público.

Los runs de deployment relevantes fueron `33429196349` (artifact inicial) y
`33429628113` (harness con telemetría), ambos concluidos correctamente.

## Evidencia HTTP

El objeto same-origin es:

`/data/esfire30-national-fidelity-territories.pmtiles`

HEAD devolvió `200`, `Content-Length: 63052056`,
`Content-Type: application/octet-stream`, `Accept-Ranges: bytes`, ETag y
`Cache-Control: max-age=600`.

Los cuatro GET Range devolvieron `206`, con `Content-Range` correcto e
identidad byte a byte contra el PMTiles local aprobado:

| Rango | Bytes |
| --- | ---: |
| `0-0` | 1 |
| `0-16383` | 16.384 |
| `1048576-1064959` | 16.384 |
| `63035672-63052055` | 16.384 |

No se observó ninguna lectura funcional `200` del archivo completo de
63.052.056 B.

## Navegador y runtime

Chromium cargó el harness desde el mismo origin y el fetch Range directo, el
protocolo PMTiles y MapLibre pasaron sin errores de consola/runtime. No hace
falta CORS para este flujo same-origin; el endpoint además respondió
`Access-Control-Allow-Origin: *`, pero no es una condición de validez.

| Smoke | Range | Bytes PMTiles | Tiempo hasta ready |
| --- | ---: | ---: | ---: |
| España 1993–2002 | 6 | 526.207 | 795,2 ms |
| Galicia | 6 | 2.558.448 | 1.475,1 ms |
| Ourense | 8 | 2.296.073 | 1.482,6 ms |
| Cangas del Narcea | 8 | 1.762.175 | 2.656,4 ms |
| Elx | 9 | 27.141 | 816,4 ms |

Los filtros CCAA/provincia siguen siendo atributos MVT. Los fixtures
municipales confirmaron 2.610 `geometry_id` para Cangas y 6 para Elx. La
recarga de Elx y la secuencia España → Galicia → España → Galicia permanecieron
estables y siguieron usando Range; son observaciones de cache de navegador y
runtime, no una validación de cache CDN de producción. Los smokes dirigidos de
viewport móvil 390×844 para Elx y Cangas también pasaron.

## Decisión y límites

`PAGES_SAME_ORIGIN_VALIDATION = PASS`. GitHub Pages same-origin queda validado
como staging técnico del PMTiles nacional. No es aún una decisión de producción:
no se ha evaluado un dominio/operación de producción ni se ha convertido este
resultado en una estimación de coste. El siguiente paso recomendado sigue
siendo `ES-4C3D5_PRODUCTION_HOSTING_DECISION`.
