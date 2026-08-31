# ES-4C3D4 — GitHub Pages same-origin staging validation

## Estado

`PENDING_EXTERNAL_STAGING`. La inspección read-only confirma que sólo existe
el Pages público `https://inthurain.github.io/atlas-incendios/`; no hay un
staging aislado autorizado. No se ha cambiado su workflow, configuración ni
deployment.

## Artifact preparado

`scripts/build_es4c3d4_pages_staging.py` parte del artifact público actual y
añade un harness aislado en `/es4c3d4/`, los vendor MapLibre/PMTiles, los tres
shards municipales estrictamente necesarios (03, 32 y 33) y el PMTiles bajo
`/data/esfire30-national-fidelity-territories.pmtiles`.

Antes de copiar el binario, el builder aborta salvo que mida 63.052.056 B y
tenga SHA-256 `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`.
No se añade el binario a Git.

El site público de referencia mide 84.200.549 B. Sólo con el PMTiles sumaría
147.252.605 B (140,43 MiB); el manifest generado por el staging registrará el
tamaño real, que incluye el pequeño harness y sus vendors.

El harness usa una URL relativa same-origin, aplica exactamente los filtros
MVT CCAA/provincia y emplea el índice municipal por padre para Cangas del
Narcea (2.610 IDs) y Elx (6 IDs). No carga EGIF ni modifica el runtime normal.

## Acción externa requerida

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
publica únicamente el artifact de ese staging. Al terminar, aportar la URL
Pages exacta y el enlace al run para realizar los controles C3D4. No subir ni
configurar CORS: la prueba es same-origin.
