# ES-4D5 — Preparación local de workflows de release

## Resultado

```text
ROOT_SWITCH_WORKFLOW_STATUS = READY
NATIONAL_DEPLOY_WORKFLOW_STATUS = READY
ROLLBACK_WORKFLOW_STATUS = READY
PRODUCTION_SWITCH_READY = true
NEXT_PHASE = ES-4D5_ROOT_SWITCH_EXECUTION
```

Esta fase corrige únicamente el bloqueo preventivo del primer intento D5B. No
se hizo `push`, `workflow_dispatch`, despliegue, tag ni cambio en producción o
staging.

## Motivo del stop anterior

`pages.yml` sigue siendo el workflow GVA histórico: es manual, pero construye
el perfil público GVA y no podía desplegar el artifact nacional E4B. Por ello
el intento se detuvo antes de cualquier mutación remota.

## Transporte nacional fijo

El TAR E4A sigue disponible como asset de la prerelease de staging, no como
artifact efímero de Actions:

```text
location  = GitHub Release asset, InThuRain/atlas-incendios-es4c3d4-pages-staging
URL       = https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-staging-es4e4a/national-product-staging.tar
availability = DURABLE
bytes     = 812902400
SHA-256   = 4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7
```

También existe una copia local de la misma identidad bajo `build/es4e4a/`,
pero el futuro runner descarga el asset durable. No usa `latest`, un artifact
de rama ni un input libre del operador.

## Deploy nacional

`.github/workflows/pages-national-product.yml` es exclusivamente
`workflow_dispatch`, sin inputs y con permisos mínimos `contents: read`,
`pages: write`, `id-token: write`. Comparte `concurrency.group: pages` y
`cancel-in-progress: false` con los workflows Pages existentes: un rollback no
puede ser cancelado por otro despliegue.

Su orden es obligatorio:

```text
download TAR fijo
-> bytes + SHA del archive
-> inspección segura y extracción a site/
-> checker físico + identidad golden + ausencia de ruta staging
-> upload Pages artifact
-> deploy Pages
```

`scripts/check_national_product_release_gate.py` fija tanto el TAR como la
identidad de site: 497 archivos / 812.510.441 B; 495 payload / 812.291.384 B;
fingerprint `10582ec0…c51b18df3`; manifest `377b5655…69cf96e`; site identity
`f5e80a72…813da04e`. Reutiliza el checker E3D1, que además verifica los
PMTiles Protomaps (293.324.998 B, SHA `72bb270f…aeb729`), ESFire30 (63.052.056
B, SHA `3c6eb10…013cfe`) y los nueve glyph ranges.

No construye datasets, Protomaps, summary, highlights ni site nacional.
Acciones fijadas al patrón E4A: `checkout@v5`, `configure-pages@v5`,
`upload-pages-artifact@v3`, `deploy-pages@v4`; la evidencia del runner usa
`upload-artifact@v4`. El aviso Node 20→24 sigue siendo
`NON_BLOCKING_INFRA_WARNING`.

## Rollback GVA fijo

`.github/workflows/pages-legacy-gva-rollback.yml` también es sólo manual,
comparte la concurrencia `pages` y hace checkout explícito de:

```text
f7a3532f633a247f33dee3ebba9fbcc316c0e534
```

No consulta `main`, `HEAD`, `HEAD~`, tags mutables ni resetea Git. Ejecuta el
flujo histórico comprobado:

```bash
python scripts/download_public_data_bundle.py
python scripts/build_frontend_profile.py --profile public --output data/web/gva/manifest.json
python scripts/validate_frontend_assets.py
python scripts/validate_recent_frontend_assets.py --public-only
python scripts/validate_egif_frontend_assets.py
python scripts/validate_esfire30_frontend_assets.py
python scripts/build_public_site.py --output data/derived/gva/publication/site
python scripts/validate_public_site.py --site data/derived/gva/publication/site
```

El input `public-data-v5/atlas-public-data-v5.tar.gz` continúa durable y
verificable: 13.399.633 B, SHA
`622030c9d0d6b52b94a4796d75aaa7bf125df132c7034935531b0a64c8c98e4c`.
Fuente ancla, Python 3.11, dependencias exactas (`Shapely 2.0.7`, `pyproj
3.5.0`, `pyshp 2.3.1`) y bundle están fijados. El estado es
`REPRODUCIBLE_WITH_PINNED_INPUTS`: el GVA antiguo no tenía un
`site-identity.json` comparable, por lo que no se inventa uno retroactivamente.
Su gate real es `validate_public_site.py`, con 44 assets públicos exactos,
perfil/fuentes permitidos, atribución y ausencia de assets prohibidos.

Se validó esta ruta en un worktree temporal del ancla; el bundle se descargó y
verificó (47 ficheros), y el site GVA resultante se validó correctamente. El
worktree temporal se eliminó después.

## Validación local

- PyYAML validó la estructura de ambos YAML; `actionlint` no estaba instalado.
- `tests/test_es4d5_release_workflows_preparation.py`: PASS.
- Pruebas negativas sintéticas: SHA TAR erróneo, `site_total_bytes` erróneo y
  `site_identity_sha256` erróneo fallan antes del paso lógico de deploy.
- Gate seco nacional real: TAR local exacto → extracción temporal → checker
  E3D1 + identidad golden → PASS; `staging_references = 0`.
- Producción GVA y staging E4B conservaron HTTP 200 durante la preparación.

## Reanudación exacta

La siguiente ejecución debe volver a empezar desde los prechecks D5B: `fetch`,
SHA local/remoto, árbol limpio, producción GVA, staging E4B y checker del
artifact. Sólo entonces podrá hacer el push autorizado y, tras verificar que
no hubo auto-deploy, disparar `pages-national-product.yml`. El rollback sigue
siendo manual y explícito: D5B decide si despachar
`pages-legacy-gva-rollback.yml` después de los gates remotos.
