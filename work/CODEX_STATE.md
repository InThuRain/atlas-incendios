# Estado local de ejecución

PHASE = ES-4C2A3C

STATUS = DONE (runtime municipal aislado: catálogo lazy, shards 0 m por provincia/ciudad, navegación, límites/bounds y filtro EGIF); PENDING (revisión antes de relaciones ESFire30→municipio).

DONE

- ES-4B2 terminado y aprobado: 56 relaciones CCINIF completas, 646.887
  partes; CCINIF no publicable.
- Pipeline EGIF→territorio ES-2 creado con salidas separadas de relaciones y
  auditoría por parte.
- Muestra comprobada: 1974, 1992, 1995 y 2023; 50.656 partes y 295.020
  relaciones, sin candidatos ni valores inválidos en esos años.
- Ejecución nacional comprobada: 56/56 bloques, 646.887 partes, 3.738.342
  relaciones, 2.782.544.923 B, 112 checksums y `--check --all` sin fallos.
- ES-4B4A: agregador anual de valores `pif_causa` creado. Muestra 1974,
  1983, 1992, 2000, 2010 y 2023: 6/6 bloques, 65.130 partes, 0 fallos de
  comprobación; las salidas locales conservan valores, nulos y blancos sin
  crear una ontología nacional.
- Ejecución nacional ES-4B4A comprobada externamente: 56/56 bloques,
  646.887 partes, 646.887 con causa primaria, 0 sin ella, 1.771.374 B de
  bloques y `--check --all` sin fallos.
- ES-4B4B1: dossier reproducible de 87 `idcausa` creado sin releer los
  normalizados. Incluye 15 códigos documented (609.964 apariciones), 72
  unmapped (36.923), campos secundarios y 72 preguntas documentales.
- ES-4B4B2A: se extrajeron 35 etiquetas literales de un snapshot oficial
  IEPNB/EGIF; 52 de los 87 códigos no aparecen en él. La tabla Access
  CodXXXXX e IdIdioma no se localizaron en los XML/ZIP ni en la documentación
  pública revisada.
- ES-4B5A: seis muestras (1974, 1995, 2023, Galicia, País Valencià y La
  Rioja) comparan JSON array, JSONL y JSON columnar. Se recomienda columnar
  compacto, CCAA × bloque temporal y ficha separada por `record_id`.
- ES-4B5B1: builder `source × CCAA × bloque temporal` con spool anual,
  serialización columnar initial/detail, resume/check y manifest. Muestra
  1968–1979 + 2013–2023 en País Valencià, Galicia y La Rioja: 45.436 partes,
  seis assets y check sin fallos.
- ES-4B5B1 nacional ejecutado externamente: 88/88 assets, 646.887 partes,
  181.891.957 B raw, 14.338.792 B gzip y `--check --all` sin fallos.
- ES-4B5B2: 88/88 assets y 646.887 `record_id` únicos auditados; 0 pérdidas,
  0 duplicados y reconciliación exacta con los 56 recuentos ES-4B1 y el total
  ES-4B3. INITIAL suma 3.901.303 B gzip y DETAIL bajo selección 10.437.489 B.
  Se validaron checksums/tamaños/gzip de los 176 ficheros y una muestra
  estructural de cuatro pares initial/detail.
- ES-4B5C1: harness aislado Chromium/CDP con diez escenarios A–J, desktop,
  viewport móvil 390×844 y modos cold/warm. Smoke La Rioja 2013–2023: 702
  partes, un INITIAL y un DETAIL lazy, lookup/filtros/segunda selección
  correctos. No se ejecutó la batería completa.
- ES-4B5C1 batería externa: 40/40 combinaciones A–J correctas más un smoke
  histórico (41 runs); check correcto. ES-4B5C2 confirma JSON columnar
  CCAA×bloque e INITIAL/DETAIL lazy como estrategia recomendada. España all
  INITIAL completa técnicamente, pero no es una carga inicial por defecto.
- ES-4C1A: runtime local MapLibre + PMTiles aislado del visor público. Reutiliza
  el PMTiles ES-3 de fidelidad (61.347.888 B,
  `92f0f081131932075f54a89d86fc8aa7e5879d56ca4d7177c64562f9612751b4`).
  Seis smokes (España, Galicia y País Valencià; escritorio y 390×844) pasaron
  con Range 206, cero descargas completas, selección/resaltado estable por
  `geometry_id` después de zoom y sin errores.
- ES-4C1B1: loader EGIF INITIAL por `CCAA × bloque` con manifest exacto para
  España, filtro columnar por año, cache por asset, `record_id → ordinal` y
  cancelación por AbortController/token. Seis smokes pasaron: España 1993–2002
  sin INITIAL; País Valencià 5.159; Galicia 110.605 en 1993–2002 y 20.850 en
  2013–2023; cambio Galicia→La Rioja sin estado obsoleto; móvil País Valencià.
  DETAIL se mantuvo en cero requests.
- ES-4C1B2: lista paginada (50 filas), búsqueda directa por `record_id` y
  ficha administrativa DETAIL perezosa. Ocho smokes locales pasaron: primera
  selección, caché en el mismo asset, cambio de bloque, municipio null,
  causa sin mapping, cancelación A→B, independencia EGIF/ESFire30 y viewport
  390×844. CCINIF, relaciones entre fuentes y geometrías EGIF siguen fuera.
- ES-4C1C1: estado único para periodo, ámbito, visibilidad y selecciones;
  coberturas EGIF 1968–2023 y ESFire30 1985–2021 por intersección explícita.
  Nueve smokes pasaron (1975 España/GVA, 1995, 2023, rango parcial, toggles,
  cambio rápido y móvil). El ámbito carga EGIF; ESFire30 aún no recibe filtro
  administrativo porque el PMTiles de fidelidad no contiene esa relación.
- ES-4C2B1A: generador ESFire30 → `territory_relation` reanudable validado
  con muestras y ejecutado externamente para los 37 años; 119.498 geometrías
  y 242.734 relaciones, sin modificar PMTiles ni el runtime.
- ES-4C2B2B2: PMTiles territorial nacional validado: 63.052.056 B, SHA-256
  `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`,
  119.498 geometrías, 120.847 relaciones CCAA y 121.887 provinciales. El
  prototipo filtra por slots MVT constantes sin cargar el índice externo;
  Galicia y Ourense pasaron smokes dirigidos con HTTP 206.
- ES-4C2A3A: inventario BDLJE Municipio auditado: 8.213 features fuente,
  8.132 municipios canónicos ES-2 enlazados y 81 unidades 53xxx no
  municipales; sin unmatched ni discrepancias jerárquicas. Diez provincias
  de muestra (1.448 geometrías) son válidas, sin nulls; la geometría nacional
  completa no se ha descargado con Codex.
- ES-4C2A3B: snapshot municipal nacional ejecutado externamente y verificado:
  147.400.597 B, SHA-256 `ca052a7592c45c03ea765e12e706652741964b80e8acd34e79978c31e9fe9dfc`.
  Los 8.132 municipios producen 52 shards BDLJE actuales 0 m: 146.194.941 B
  raw / 46.664.000 B gzip, sin geometrías null/empty/inválidas ni duplicados.
  Se recomienda catálogo nacional ligero + GeoJSON 0 m por provincia bajo
  demanda; no se integra runtime aún.

PENDING

- Solicitar a MITECO/ADCIF la tabla CodXXXXX de `pif_causa.idcausa`, sus
  versiones/vigencias e IdIdioma, siguiendo el borrador no enviado.
- No iniciar ontología ni investigación individual de los 52 códigos sin
  respuesta documental explícita.
- ES-4C1C2: serializer exclusivo del prototipo (`es4c-state-v1`) con
  hash canónico, `replaceState`, copia de enlace, restauración segura de
  rango/ámbito/fuentes/mapa y selección independiente EGIF/ESFire30. Pasaron
  los tests específicos y nueve smokes, incluida sesión Chromium nueva,
  URL corrupta, back/forward y viewport 390×844. Sigue pendiente de revisión;
  no cambia el permalink público valenciano.
- ES-4C2A1 aprobado y comprometido (`de50e18`): capa local BDLJE de 19
  CCAA/ciudades autónomas con crosswalk, bounds y highlight.
- ES-4C2B1B: auditoría de JSONL nacionales terminada: 0 duplicados, touches,
  ceros e incoherencias; 3.738 relaciones extra explicadas por cardinalidad
  N:M. El índice dictionary-encoded se estima en 318.535 B gzip; no se ha
  integrado ni reconstruido PMTiles.

OUTPUTS

- `data/processed/egif/spain/2026-08-27/manifest.json` (ignorado por Git)
- `data/derived/spain/es4b3/territory_relations/2026-08-27/manifest.json` (ignorado por Git)
- `ES_4B3_EGIF_NATIONAL_TERRITORY_MAPPING.md`
- `data/derived/spain/es4b4a/causes/2026-08-27/manifest.json` (se creará localmente e ignorado por Git)
- `data/audit/egif/es4b4b1_cause_codes.json`
- `ES_4B4B1_EGIF_CAUSE_CODE_DOSSIER.md`
- `data/reference/egif/idcausa_official_code_table.json`
- `ES_4B4B2A_EGIF_OFFICIAL_CAUSE_DICTIONARY.md`
- `data/audit/egif/es4b5a_web_derivative_benchmark.json`
- `ES_4B5A_EGIF_WEB_DERIVATIVE_DESIGN.md`
- `ES_4B5B1_EGIF_WEB_BUILDER.md`
- `ES_4B5B2_EGIF_WEB_ASSET_AUDIT.md`
- `data/audit/egif/es4b5b2_web_assets.json`
- `ES_4B5C1_EGIF_BROWSER_BENCHMARK_HARNESS.md`
- `benchmarks/es4b5c/results.json` (local e ignorado)
- `ES_4B5C2_EGIF_BROWSER_BENCHMARK_ANALYSIS.md`
- `data/audit/egif/es4b5c2_browser_summary.json`
- `data/web/spain/egif/es4b5b1-sample/manifest.json` (ignorado por Git)
- `ES_4C1A_NATIONAL_PMTILES_RUNTIME.md`
- `prototypes/es4c/` (runtime y servidor Range versionados)
- `prototypes/es4c/smoke-results.json` (local e ignorado)
- `ES_4C1B1_NATIONAL_EGIF_INITIAL_RUNTIME.md`
- `prototypes/es4c/egif_initial_loader.mjs`
- `prototypes/es4c/territory_catalog.mjs`
- `prototypes/es4c/egif-*-smoke-results.json` (locales e ignorados)
- `ES_4C2B1A_ESFIRE30_TERRITORY_RELATION_BUILDER.md`
- `data/derived/spain/es4c2b/esfire30_territory_relations/manifest.json`
  (se generará localmente e ignorado por Git)
- `ES_4C2B1B_ESFIRE30_TERRITORY_RELATION_AUDIT.md`
- `data/audit/esfire30/es4c2b1b_territory_relations.json`

INPUT_TOTAL = 646887

OUTPUT_MANIFEST = data/web/spain/egif/2026-08-27/manifest.json

EXPECTED_RECORDS = 646887

EXPECTED_GEOMETRIES = 119498

PHASE = ES-4D3C

STATUS = DONE (adapter aislado de permalink público GVA `#v=1`, fixtures, aceptación dirigida ICV/EFFIS y restore legacy↔native; no se modificó producción ni staging).

CURRENT_HOSTING = GITHUB_RELEASES (download evidence) + R2 R2.DEV (technical staging)

CURRENT_HOSTING_STATUS = GITHUB_RELEASES_RANGE_OK_CORS_FAIL; R2_DEV_RANGE_CORS_BROWSER_PASS

HOSTING_DECISION = GITHUB_PAGES_INITIAL_WITH_R2_CUSTOM_DOMAIN_FALLBACK

INITIAL_PRODUCTION_HOSTING = GITHUB_PAGES

PREFERRED_HOSTING = GITHUB_PAGES (same-origin; asset inmutable incorporado mediante Action/artifact)

FALLBACK_HOSTING = CLOUDFLARE_R2_CUSTOM_DOMAIN (futuro; no creado ni validado en producción)

NEXT_EXTERNAL_ACTION = Iniciar únicamente ES-4D4_NATIONAL_PRODUCTION_STAGING; no autorizar cambio de raíz hasta completar su staging y aceptación explícita.

NEXT_COMMAND = python3 scripts/build_national_frontend.py --output build/national

NEXT_CHECK_COMMAND = python3 scripts/build_national_frontend.py --check --output build/national

SOURCE = ESFire30 canónico Zenodo 10.5281/zenodo.18449006 + BDLJE municipal actual 2026-08 (0 m)

SOURCE_SHA256 = ESFire30:150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8; BDLJE:ca052a7592c45c03ea765e12e706652741964b80e8acd34e79978c31e9fe9dfc

EXPECTED_MUNICIPALITIES = 8132

BUG_01 = FIXED (scope municipal transaccional; padre válido si falla GeoJSON)
BUG_02 = FIXED (503 PMTiles propaga error ESFire30; reintento explícito recupera)
LOCAL_ACCEPTANCE_STATUS = FUNCTIONALLY_ACCEPTED_LOCAL
REAL_HOSTING_RANGE_VALIDATION = PASS (R2 r2.dev technical staging; no full download)
HOSTING_CLASSIFICATION = R2_DEV_RECOMMENDED_FOR_TECHNICAL_STAGING; GITHUB_RELEASES_NOT_RECOMMENDED_FOR_CROSS_ORIGIN_PMTILES
RELEASE_GATE_PENDING = NONE (hosting inicial decidido; migración de producción pendiente de diseño)
REGRESSIONS = 0 (13/13 smokes ES-4C3C)
ACCEPTANCE_STATUS = FUNCTIONALLY_ACCEPTED_LOCAL
BLOCKERS = 0
MAJOR_ISSUES = none_local
MUST_FIX_COUNT = 0 (la revalidación Range/CORS real se cerró; falta decisión explícita de hosting de producción)
EXTERNAL_BLOCKERS = causa MITECO; permiso CCINIF
PMTILES_PATH = data/derived/spain/es4c2b/pmtiles/esfire30-national-fidelity-territories.pmtiles

PROTOTYPE_PATH = prototypes/es4c/

RESULTS_PATH = ES_4D3C_GVA_PERMALINK_COMPATIBILITY.md; data/audit/production/es4d3c_gva_permalink_compatibility.json; data/audit/production/es4d3c_gva_final_parity.json

PAGES_SAME_ORIGIN_VALIDATION = PASS
R2_DEV_STAGING_VALIDATION = PASS
REAL_BROWSER_RANGE_CORS = PASS (same-origin; CORS not required)
CDN_CACHE_VALIDATION = NOT_VALIDATED
FULL_DOWNLOAD_OBSERVED = false
MIGRATION_DESIGN_STATUS = MIGRATION_DESIGN_READY_WITH_PARITY_GAPS
PRODUCTION_FRONTEND_STATUS = PRODUCTION_FRONTEND_EXTRACTED
ICV_PARITY_STATUS = PASS
EFFIS_PARITY_STATUS = PASS
GLOBAL_TIME_RANGE = 1968–2026
GVA_PERMALINK_V1 = PASS
GVA_COMPATIBILITY_STATUS = PASS
GVA_PARITY_READY_FOR_STAGING = true
MUST_HAVE_PARITY_GAPS = []
PRODUCTION_SWITCH_READY = false (D4 production staging + acceptance pendiente)
PRODUCTION_ROOT_SWITCH_AUTHORIZED = false
INITIAL_PRODUCTION_HOSTING = GITHUB_PAGES
FALLBACK_HOSTING = CLOUDFLARE_R2_CUSTOM_DOMAIN
PAGES_SAME_ORIGIN_VALIDATION = PASS
REMAINING_GAPS = D4_PRODUCTION_STAGING_ACCEPTANCE
NEXT_PHASE = ES-4D4_NATIONAL_PRODUCTION_STAGING

PHASE = ES-4D4A

STATUS = DONE (artifact nacional estático autocontenido ensamblado, integridad y 11 smokes locales correctos); PENDING (despliegue y aceptación remota exclusivamente en ES-4D4B).

STAGING_ARTIFACT_STATUS = READY_FOR_REMOTE_STAGING

ARTIFACT_PATH = build/national-pages-staging/

ARTIFACT_FILE_COUNT = 349

ARTIFACT_BYTES = 500449810

ARTIFACT_FINGERPRINT = bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8

ARTIFACT_MANIFEST = build/national-pages-staging/asset-manifest.json

RESULTS_PATH = ES_4D4A_NATIONAL_PRODUCTION_STAGING_ARTIFACT.md; data/audit/production/es4d4a_staging_artifact.json

NEXT_COMMAND = python3 scripts/build_national_pages_artifact.py --output build/national-pages-staging

NEXT_CHECK_COMMAND = python3 scripts/build_national_pages_artifact.py --check --output build/national-pages-staging

STAGING_REPO_CANDIDATE = InThuRain/atlas-incendios-es4c3d4-pages-staging

PRODUCTION_SWITCH_READY = false

PRODUCTION_ROOT_SWITCH_AUTHORIZED = false

NEXT_PHASE = ES-4D4B_NATIONAL_PRODUCTION_STAGING_DEPLOYMENT_ACCEPTANCE

PHASE = ES-4D4B

STATUS = BLOCKED_ARTIFACT_IDENTITY_MISMATCH (el workflow staging verificó el SHA de transporte y se detuvo antes de upload/deploy: manifest D4A declara 500449810 B, árbol extraído 500449871 B).

PRE_DEPLOY_STAGING_COMMIT = d8e6f84cfeb9597dc0f4327f427912b97ae93c3e

STAGING_WORKFLOW_COMMIT = f58eb3f778ccd953c00a127e5d1b6bc8e9d9bde6

STAGING_DEPLOYMENT_RUN = 33516317541

STAGING_DEPLOYMENT_STATUS = FAIL (PAGES_ARTIFACT / ARTIFACT_IDENTITY_MISMATCH; no upload-pages-artifact ni deploy-pages)

REMOTE_ACCEPTANCE_STATUS = NOT_RUN

NATIONAL_RELEASE_CANDIDATE = NOT_READY

PRODUCTION_SWITCH_READY = false

PRODUCTION_ROOT_SWITCH_AUTHORIZED = false

RESULTS_PATH = ES_4D4B_NATIONAL_PRODUCTION_STAGING_ACCEPTANCE.md; data/audit/production/es4d4b_national_production_staging_acceptance.json

NEXT_PHASE = ES-4D4B_CONTINUE (requiere decisión explícita para reabrir ES-4D4A, corregir el cálculo estable del manifest y aprobar un nuevo artifact).

PHASE = ES-4D4A1

STATUS = DONE (ARTIFACT_IDENTITY_FIX_STATUS = PASS; contrato físico/payload separado, dos builds limpios idénticos y gate local D4B PASS).

ORIGINAL_D4A_IDENTITY = declared 500449810 B; observed physical 500449871 B; delta +61 B; fingerprint bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8.

ROOT_CAUSE = asset-manifest.json was counted after first 148052-B serialization, then rewritten to 148113 B with final bookkeeping fields without recalculating the physical total; only this metadata path was affected.

ARTIFACT_PATH = build/national-pages-staging/

SITE_FILE_COUNT = 350

SITE_TOTAL_BYTES = 500450914

PAYLOAD_FILE_COUNT = 348

PAYLOAD_TOTAL_BYTES = 500301758

PAYLOAD_FINGERPRINT = bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8

ASSET_MANIFEST_SHA256 = c2c57a70130fd2e4527ac6a50ebb1c86e73bb667d6c5c5940f9b015b9823aceb

PMTILES_BYTES = 63052056

PMTILES_SHA256 = 3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe

STAGING_ARTIFACT_STATUS = READY_FOR_REMOTE_STAGING

REMOTE_ACCEPTANCE_STATUS = NOT_RUN

PRODUCTION_SWITCH_READY = false

RESULTS_PATH = ES_4D4A_NATIONAL_PRODUCTION_STAGING_ARTIFACT.md; data/audit/production/es4d4a1_artifact_identity_fix.json

NEXT_COMMAND = python3 scripts/build_national_pages_artifact.py --output build/national-pages-staging

NEXT_CHECK_COMMAND = python3 scripts/build_national_pages_artifact.py --check --output build/national-pages-staging

NEXT_PHASE = ES-4D4B_CONTINUE

PHASE = ES-4D4B

STATUS = DONE (D4B_ATTEMPT_1 = FAIL_IDENTITY_GATE conservado; D4B_ATTEMPT_2 = PASS con GitHub Pages staging y aceptación remota).

D4A1_IDENTITY = PASS

D4B_ATTEMPT_1 = FAIL_IDENTITY_GATE (workflow 33516317541; no upload/deploy)

D4B_ATTEMPT_2 = PASS (workflow 33525357443)

STAGING_REPO = InThuRain/atlas-incendios-es4c3d4-pages-staging

STAGING_WORKFLOW_COMMIT = 99b38f409e6affc219a15b2b37cfd48bfd83b706

STAGING_URL = https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/

STAGING_DEPLOYMENT_STATUS = PASS

REMOTE_ACCEPTANCE_STATUS = PASS

NATIONAL_RELEASE_CANDIDATE = READY_FOR_ROOT_DECISION

PRODUCTION_ROOT_INTACT = true

PRODUCTION_SWITCH_READY = false

PRODUCTION_ROOT_SWITCH_AUTHORIZED = false

FULL_PMTILES_DOWNLOAD_OBSERVED = false

RESULTS_PATH = ES_4D4B_NATIONAL_PRODUCTION_STAGING_ACCEPTANCE.md; data/audit/production/es4d4b_national_production_staging_acceptance.json

NEXT_PHASE = ES-4D5_ROOT_SWITCH_DECISION

PHASE = ES-4D5_ROOT_SWITCH_DECISION

STATUS = DONE (decisión y runbook locales; sin push, deploy ni mutación remota).

LOCAL_HEAD_AT_AUDIT = 201c3a93956e153ff356dcf2a127482b9af7f420

ORIGIN_MAIN_AT_AUDIT = 7b6520bd3f9c6729580bb48692dd5f7a3afa79ca

LOCAL_DIVERGENCE = 4 ahead / 0 behind; working tree clean al iniciar la auditoría.

CURRENT_PRODUCTION_GIT_COMMIT = f7a3532f633a247f33dee3ebba9fbcc316c0e534

CURRENT_PRODUCTION_WORKFLOW = .github/workflows/pages.yml; workflow_dispatch only; run 32943744421; deployment 6099343480 / status 17347149751 success.

ROLLBACK_ANCHOR = f7a3532f633a247f33dee3ebba9fbcc316c0e534

ACCEPTED_ARTIFACT = 497 files / 812510441 B / payload 10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3 / manifest 377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e / site f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e.

ROOT_SWITCH_DECISION = GO

PRODUCTION_SWITCH_READY = true

PRODUCT_RELEASE_CANDIDATE = READY_FOR_PRODUCTION_SWITCH

NEXT_PHASE = ES-4D5_ROOT_SWITCH_EXECUTION

PHASE = ES-4D5_RELEASE_WORKFLOWS_PREPARATION

STATUS = DONE (workflows locales preparados; no push, dispatch ni deploy).

GOLDEN_TAR_LOCATION = GitHub Release asset InThuRain/atlas-incendios-es4c3d4-pages-staging / national-product-staging-es4e4a / national-product-staging.tar

GOLDEN_TAR_AVAILABILITY = DURABLE

GOLDEN_TAR_BYTES = 812902400

GOLDEN_TAR_SHA256 = 4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7

NATIONAL_DEPLOY_WORKFLOW_STATUS = READY

ROLLBACK_WORKFLOW_STATUS = READY

LEGACY_ROLLBACK_BUILD_STATUS = REPRODUCIBLE_WITH_PINNED_INPUTS (anchor f7a3532f633a247f33dee3ebba9fbcc316c0e534; public-data-v5 verificado; build/validate local temporal PASS).

ROOT_SWITCH_WORKFLOW_STATUS = READY

PRODUCTION_SWITCH_READY = true

PRODUCT_RELEASE_CANDIDATE = READY_FOR_PRODUCTION_SWITCH

D5_STATUS = READY_TO_RESUME_EXECUTION

NEXT_PHASE = ES-4D5_ROOT_SWITCH_EXECUTION

PHASE = ES-4E1

STATUS = DONE (auditoría comparativa de producto GVA vs staging nacional completada; sin cambios de runtime, producción, staging ni datos).

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

ROOT_SWITCH_UX_STATUS = BLOCKED_BY_MAJOR_PRODUCT_REGRESSIONS

TECHNICAL_RELEASE_CANDIDATE = PASS

PRODUCT_RELEASE_CANDIDATE = false

GVA_ROLE = PRODUCT_REFERENCE_AND_CURRENT_PRODUCTION

NATIONAL_STAGING_ROLE = TECHNICAL_BASELINE

RECOMMENDED_PRODUCT_DIRECTION = recuperar sustancialmente el layout, la jerarquía y el flujo exploratorio GVA sobre el runtime nacional, preservando su arquitectura y la separación semántica de fuentes.

RESULTS_PATH = ES_4E1_GVA_NATIONAL_UX_PRODUCT_AUDIT.md; data/audit/product/es4e1_gva_national_ux_product_audit.json

NEXT_PHASE = ES-4E2_NATIONAL_UX_REDESIGN_SPEC

PHASE = ES-4E2

STATUS = DONE (especificación de producto nacional cerrada; sin cambios de runtime, HTML/CSS/JS, datos, staging ni producción).

UX_REDESIGN_SPEC_STATUS = READY_FOR_IMPLEMENTATION

ROOT_SWITCH_UX_STATUS = NEEDS_RECONCILIATION

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

TECHNICAL_RELEASE_CANDIDATE = PASS

PRODUCT_RELEASE_CANDIDATE = false

TECHNICAL_BASELINE = D4B staging congelado

PRODUCT_DIRECTION = recuperar layout, legibilidad y flujo GVA sobre el runtime nacional, con métricas tipadas y fuentes independientes.

HISTOGRAM_DESIGN = pestañas por métrica/fuente; una serie visible cada vez; nunca suma ni apila fuentes.

P0_DATA_REQUIREMENT = national-ux-summary-v1 pequeño y determinista, especialmente conteos anuales ESFire30 por territorio; sin nuevas intersecciones ni rebuild PMTiles.

RESULTS_PATH = ES_4E2_NATIONAL_UX_REDESIGN_SPEC.md; data/audit/product/es4e2_metric_contracts.json; data/audit/product/es4e2_information_hierarchy.json; data/audit/product/es4e2_feature_priorities.json; data/audit/product/es4e2_data_requirements.json

NEXT_PHASE = ES-4E3_NATIONAL_UX_IMPLEMENTATION

PHASE = ES-4E3A

STATUS = DONE (shell nacional orientada a producto implementada localmente; mapa dominante, jerarquía humana, vista recomendada, metodología plegada y runtime técnico preservado).

PRODUCT_SHELL_STATUS = PASS

TECHNICAL_RUNTIME_REGRESSION = false

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

TECHNICAL_BASELINE = D4B staging congelado y no modificado

BASEMAP_GAP_FOR_E3B_OR_E3C = no existe basemap local aprobado; E3A no incorpora proveedor externo

CHROMIUM_SMOKES = 13 directed PASS; desktop + exact 390x844 mobile; #v=1 + #es4c-state-v1 PASS

TARGETED_TESTS = 12 PASS (E3A shell + D2 extraction + D3C permalink compatibility)

RESULTS_PATH = ES_4E3A_NATIONAL_PRODUCT_SHELL.md; data/audit/product/es4e3a_national_product_shell.json

NEXT_PHASE = ES-4E3B_NATIONAL_METRICS_HISTOGRAM

PHASE = ES-4E3B1

STATUS = DONE (`national-ux-summary-v1` determinista construido exclusivamente desde derivados aceptados; 122 payloads + manifest, series anuales tipadas por fuente y territorio, sin cambios de UI/runtime/artifact D4B).

UX_SUMMARY_STATUS = PASS

HISTOGRAM_DATA_STATUS = READY_FOR_UI

OUTPUT_ROOT = data/derived/spain/national-ux-summary-v1/

OUTPUT_PHYSICAL_FILE_COUNT = 123

OUTPUT_BYTES = 17255181

OUTPUT_GZIP_BYTES = 930003

OUTPUT_FINGERPRINT = 2546247b68ef8e27fed3334cf5fb4a027056f094e36420213080c431bfb850e4

SOURCE_RECONCILIATION = EGIF 646887; ESFire30 119498; ICV 13738 records / 13739 geometries; EFFIS 2025=9 / 2026=16

DEFERRED_METRICS = ESFire30 mapped area (no territorial sum safe); EGIF canonical causes (MITECO ontology); highlights/top-N (E3C)

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

NEXT_COMMAND = python3 scripts/build_national_ux_summary.py

NEXT_CHECK_COMMAND = python3 scripts/build_national_ux_summary.py --check

RESULTS_PATH = ES_4E3B1_NATIONAL_UX_SUMMARY_DERIVED_DATA.md; data/audit/product/es4e3b1_national_ux_summary.json

NEXT_PHASE = ES-4E3B2_NATIONAL_METRICS_HISTOGRAM_UI

PHASE = ES-4E3B2

STATUS = DONE (national-ux-summary-v1 integrado de forma lazy; tarjetas humanas tipadas e histograma anual funcional de una sola serie; sin filtros, destacados, ficha final ni basemap nuevo).

METRICS_UI_STATUS = PASS

HISTOGRAM_UI_STATUS = PASS

PRODUCT_OVERVIEW_STATUS = PASS

SUMMARY_LOAD_POLICY = Spain national.json; CCAA one CCAA payload; province one province payload; municipality one parent shard.

SUMMARY_CACHE_CANCELLATION = completed assets cached by manifest path; AbortController + generation token; error isolated from map/runtime.

HISTOGRAM_INTERACTION = one source/metric at a time; global 1968-2026 axis; click year updates canonical from/to; drag range deferred P1.

CHROMIUM_SMOKES = 13/13 PASS (11 desktop + Spain/Elx exact 390x844 mobile; year click, source switch and copy-link fallback included).

TARGETED_TESTS = 5 PASS

TECHNICAL_RUNTIME_REGRESSION = false

BASEMAP_GAP = no approved local basemap; unchanged and deferred.

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3B2_NATIONAL_METRICS_HISTOGRAM_UI.md; data/audit/product/es4e3b2_national_metrics_histogram_ui.json

NEXT_PHASE = ES-4E3C_NATIONAL_FILTERS_HIGHLIGHTS_DETAILS

PHASE = ES-4E3C1

STATUS = DONE (filtros seguros tipados por fuente, estado/permalink aditivo y cuatro fichas humanas con detalle técnico plegado; sin nuevos datos, relaciones, PMTiles ni staging).

SAFE_FILTERS_STATUS = PASS

HUMAN_DETAIL_STATUS = PASS

FILTER_STATE_STATUS = PASS

FILTERS = EGIF minimum declared forest area + administrative GIF; ICV minimum declared forest area + documented GIF criterion + approved cause; EFFIS minimum mapped perimeter area; ESFire30 none.

ESFIRE30_AREA_FILTER_STATUS = DEFERRED_NO_SAFE_TERRITORIAL_AREA

EGIF_CAUSE_FILTER_STATUS = DEFERRED_PENDING_ONTOLOGY

FILTERED_SUMMARY = EXACT_RUNTIME for loaded EGIF/ICV/EFFIS; EXACT_DERIVED for Spain EGIF GIF or exact 500 ha; otherwise HIDE_WHILE_FILTERED / explicit unfiltered histogram.

FILTER_STATE = canonical runtime filters[]; serialized additively as es4c-state-v1 analysis.filters; contextual invalidation by territory/time/source.

CHROMIUM_SMOKES = 14/14 PASS (12 desktop + 2 exact 390x844; filter independence, zero/no-data, invalidation, four source cards, 2024AL0005 1:N and filter permalink reload/back-forward).

TARGETED_TESTS = 5 PASS

HISTOGRAM_BRUSH_STATUS = DEFERRED_P1

BASEMAP_GAP = OPEN_NO_APPROVED_LOCAL_PROVIDER

TECHNICAL_RUNTIME_REGRESSION = false

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3C1_NATIONAL_SAFE_FILTERS_HUMAN_DETAILS.md; data/audit/product/es4e3c1_national_safe_filters_human_details.json

NEXT_PHASE = ES-4E3C2_NATIONAL_HIGHLIGHTS_MAP_POLISH

PHASE = ES-4E3C2

STATUS = DONE (destacados source-aware y pulido cartográfico local completados; el mapa mejora con BDLJE, pero la decisión de mapa base/topónimos sigue abierta).

HIGHLIGHTS_STATUS = PASS

PRODUCT_POLISH_STATUS = PASS

ESFIRE30_HIGHLIGHTS_STATUS = DEFERRED_NO_SAFE_RANKING_METRIC

HIGHLIGHTS_DERIVED = data/derived/spain/national-highlights-v1/ (manifest 794 B; EGIF payload 343708 B raw / 17011 B gzip; 646887 registros fuente comprobados; sin DETAIL ni geometría).

MAP_CONTEXT = BDLJE same-origin reutilizado; costa/fondo/límites bajo incendios, selección territorial enfatizada y nombre del ámbito visible; sin nuevo asset cartográfico.

LOCAL_CONTEXT_SUFFICIENT = false

BASEMAP_STATUS = PENDING_USER_DECISION

ROADS_STATUS = P1_OPTIONAL

HISTOGRAM_BRUSH_STATUS = DEFERRED_P1

BASEMAP_OPTIONS_AUDITED = Protomaps PMTiles autoalojado; OpenFreeMap público; MapTiler Cloud. Ninguno seleccionado ni incorporado.

CHROMIUM_SMOKES = 10/10 directed PASS + Spain final cache/detail recheck PASS; desktop + exact 390x844 mobile.

TARGETED_TESTS = 7 JS assertions + 3 Python tests + national frontend build/check PASS

TECHNICAL_RUNTIME_REGRESSION = false

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3C2_NATIONAL_HIGHLIGHTS_MAP_POLISH.md; data/audit/product/es4e3c2_national_highlights_map_polish.json

NEXT_PHASE = ES-4E3C2_BASEMAP_DECISION

PHASE = ES-4E3C2_BASEMAP_DECISION

STATUS = DONE (Protomaps self-hosted z12 evaluado en harness aislado; contexto visual suficiente, Range 206, cero dominios runtime externos y cabida física conservadora en Pages; no integrado ni desplegado).

BASEMAP_RECOMMENDATION = ADOPT_PROTOMAPS_Z12

BASEMAP_STATUS = CANDIDATE_VALIDATED

PROTOMAPS_ADOPTION = NOT_AUTHORIZED_YET

Z12_VISUAL_QUALITY = SUFFICIENT

Z12_PMTILES_BYTES = 293324998

Z12_COMPLETE_BASEMAP_BYTES = 293411976

Z12_SHA256 = 72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729

Z13_STATUS = NOT_TESTED (z12 suficiente)

CURRENT_E3_PRE_BASEMAP_PROJECTED_SITE_BYTES = 518188315

PROJECTED_SITE_BYTES_WITH_Z12 = 811600291

PAGES_BYTES_REMAINING = 188399709 (cuenta física conservadora respecto a 1000000000 B)

RUNTIME_NETWORK = all candidate PMTiles requests HTTP 206; full downloads 0; external runtime domains 0; one 76044 B glyph range per clean session.

VISUAL_RESULT = topónimos/costa/agua/carreteras restauran contexto nacional, municipal y rural; incendios mantienen protagonismo; Elx y Cangas son suficientes con z12 sobrezoomed.

LICENSE = OSM-derived Protomaps Produced Work ODbL + visible OSM attribution; basemaps code BSD-3-Clause; visual style CC0; Noto glyph SIL OFL; BDLJE CC-BY 4.0.

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3C2_BASEMAP_DECISION.md; data/audit/product/es4e3c2_basemap_decision.json

NEXT_PHASE = ES-4E3C2_BASEMAP_INTEGRATION (solo tras aprobación humana)

PHASE = ES-4E3C2_BASEMAP_INTEGRATION

STATUS = DONE (candidato Protomaps z12 exacto integrado productivamente en local; same-origin, Range y fallback BDLJE-only validados; sin staging ni producción).

BASEMAP_INTEGRATION_STATUS = PASS

BASEMAP_STATUS = PASS_PROTOMAPS_Z12

MAP_CONTEXT_STATUS = PASS

BASEMAP_VERSION = protomaps-20260902-z12

BASEMAP_SOURCE = build/es4e3c2-basemap/protomaps-spain-z12.pmtiles (derived/ignored; 293324998 B; SHA-256 72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729; pmtiles verify PASS).

BASEMAP_RUNTIME_PATH = data/basemap/protomaps/20260902-z12/72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729/basemap.pmtiles

BASEMAP_MANIFEST = config/national-basemap-protomaps-20260902-z12.json

GLYPH = Noto Sans Regular/0-255.pbf (76044 B; SHA-256 62c6d49b15fa836eb6aa45e259c7ca6762f44b011b09e47776efbe4a6db1b397; 1 request/clean smoke; 0 404).

SPRITES = none

RUNTIME_EXTERNAL_DOMAINS = []

API_KEYS_REQUIRED = false

BDLJE_ROLE = canonical administrative authority; Protomaps is cartographic context only.

LAYER_ORDER = Protomaps context -> BDLJE context -> selected territory -> fire geometries -> selected fire geometry.

CHROMIUM_SMOKES = 9/9 directed PASS (Spain, Galicia, Ourense, Cangas, GVA 1995, Elx, Canarias, mobile Spain, mobile Elx) + basemap 404 fallback PASS.

RANGE = all Protomaps and ESFire30 PMTiles functional requests HTTP 206; full downloads false; telemetry separated by PMTiles role.

CURRENT_PRODUCT_PROJECTED_SITE_BYTES = 811608504

PAGES_BYTES_REMAINING = 188391496 (raw projection against 1000000000 B).

PAGES_CAPACITY_STATUS = LIMITED_BUT_ACCEPTABLE

TECHNICAL_RUNTIME_REGRESSION = false

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3C2_BASEMAP_INTEGRATION.md; data/audit/product/es4e3c2_basemap_integration.json

NEXT_PHASE = ES-4E3D_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE

PHASE = ES-4E3D1

STATUS = BLOCKED_GLYPH_COVERAGE (artifact completo, autocontenido, reproducible y con identidad física válida; Chromium solicita rangos Noto Sans no incluidos, por lo que no puede pasar a aceptación E3D2).

PRODUCT_ARTIFACT_STATUS = BLOCKED_GLYPH_COVERAGE

ARTIFACT_IDENTITY_STATUS = PASS

GLYPH_COVERAGE_STATUS = INCOMPLETE

GLYPH_INCLUDED = Noto Sans Regular/0-255.pbf (76044 B; SHA-256 62c6d49b15fa836eb6aa45e259c7ca6762f44b011b09e47776efbe4a6db1b397)

GLYPH_ADDITIONAL_RANGES_REQUESTED = 256-511.pbf; 512-767.pbf; 768-1023.pbf; 1024-1279.pbf; 1536-1791.pbf; 7680-7935.pbf (Asturias); 11520-11775.pbf

ARTIFACT_PATH = build/national-product-staging/

PAYLOAD_FILE_COUNT = 487

PAYLOAD_TOTAL_BYTES = 811455504

PAYLOAD_FINGERPRINT = a9bb511c353c5dff8104239572b88d2c2ed2755436abdbadc664790eb4ffa2cf

ASSET_MANIFEST_SHA256 = f6d1e3b2945f979e6515ca5881bb9aae528f4ddcceaec2e6912adc87346286db

SITE_FILE_COUNT = 489

SITE_TOTAL_BYTES = 811665494

SITE_IDENTITY_SHA256 = 5bdfaa23d771c7b0accef5d58cf25a64cef82b63d6f1652bb1bd8fb6f17561be

PAGES_BYTES_REMAINING = 188334506

PAGES_CAPACITY_STATUS = LIMITED_BUT_ACCEPTABLE

REPRODUCIBILITY = PASS (dos outputs limpios; siete magnitudes de identidad idénticas)

SELF_CONTAINED = PASS

RUNTIME_EXTERNAL_DOMAINS = []

PMTILES_RANGE = PASS (Protomaps + ESFire30; 0-0, initial, middle y final HTTP 206; bytes idénticos; sin descarga completa)

PACKAGING_SMOKES = root/Spain/GVA 1995/Elx/mobile PASS; BDLJE-only fallback PASS; global BLOCKED solo por glyph coverage.

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3D1_NATIONAL_PRODUCT_ARTIFACT.md; data/audit/product/es4e3d1_national_product_artifact.json

NEXT_COMMAND = definir y autorizar adquisición verificable de los rangos glyph necesarios; no descargar automáticamente

NEXT_CHECK_COMMAND = reejecutar benchmarks/es4e3d1/run_packaging_smoke.py tras incorporar glyphs autorizados

NEXT_PHASE = ES-4E3D1_GLYPH_FIX

PHASE = ES-4E3D1

STATUS = DONE (ATTEMPT_1 = BLOCKED_GLYPH_COVERAGE preservado; ATTEMPT_2 = READY_FOR_LOCAL_ACCEPTANCE).

ATTEMPT_1 = BLOCKED_GLYPH_COVERAGE; SITE 489 files / 811665494 B / SHA 5bdfaa23d771c7b0accef5d58cf25a64cef82b63d6f1652bb1bd8fb6f17561be; PAYLOAD 487 files / 811455504 B / fingerprint a9bb511c353c5dff8104239572b88d2c2ed2755436abdbadc664790eb4ffa2cf.

ATTEMPT_2 = READY_FOR_LOCAL_ACCEPTANCE; glyph fix reproducible y matriz estable.

PRODUCT_ARTIFACT_STATUS = READY_FOR_LOCAL_ACCEPTANCE

ARTIFACT_IDENTITY_STATUS = PASS

GLYPH_COVERAGE_STATUS = PASS

GLYPH_RANGE_DISCOVERY_STABLE = true

GLYPH_DISCOVERY_METHOD = ACCEPTANCE_MATRIX_COMPLETE (16 contextos × 5 zooms × 2 ejecuciones; no implica cobertura Unicode universal).

GLYPH_FONTSTACK = Noto Sans Regular

GLYPH_SOURCE = protomaps/basemaps-assets@028c18f713baecad011301ff7a69acc39bcc2ae7; SIL OFL 1.1.

GLYPH_RANGES = 0-255; 256-511; 512-767; 768-1023; 1024-1279; 1536-1791; 7680-7935; 8192-8447; 11520-11775

GLYPH_FILE_COUNT = 9

GLYPH_TOTAL_BYTES = 909374

GLYPH_DELTA_BYTES = 833330 (desde 1 file / 76044 B).

GLYPH_404_COUNT = 0

GLYPH_UNBUNDLED_RANGE_COUNT = 0

ARTIFACT_PATH = build/national-product-staging/

PAYLOAD_FILE_COUNT = 495

PAYLOAD_TOTAL_BYTES = 812291384

PAYLOAD_FINGERPRINT = 10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3

ASSET_MANIFEST_SHA256 = 377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e

SITE_FILE_COUNT = 497

SITE_TOTAL_BYTES = 812510441

SITE_IDENTITY_SHA256 = f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e

ARTIFACT_DELTA_FROM_ATTEMPT_1_BYTES = 844947

PAGES_BYTES_REMAINING = 187489559

PAGES_CAPACITY_STATUS = LIMITED_BUT_ACCEPTABLE

REPRODUCIBILITY = PASS (dos outputs limpios; siete magnitudes de identidad idénticas).

CHECKER = PASS (inventario físico, manifest, fingerprint, site identity, inputs y 9 glyph ranges).

SELF_CONTAINED = PASS

RUNTIME_EXTERNAL_DOMAINS = []

PMTILES_RANGE = PASS (Protomaps + ESFire30; 0-0, initial, middle y final HTTP 206; bytes idénticos; sin descarga completa).

PACKAGING_SMOKES = 7 quick PASS (root, Spain, GVA 1995, Elx, mobile Spain, mobile Elx, mobile Asturias); 8 contextos glyph PASS; BDLJE-only fallback PASS; 0 runtime errors.

PRODUCT_RELEASE_CANDIDATE = false

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3D1_NATIONAL_PRODUCT_ARTIFACT.md; data/audit/product/es4e3d1_national_product_artifact.json; data/audit/product/es4e3d1_glyph_coverage.json

NEXT_PHASE = ES-4E3D2_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE

PHASE = ES-4E3D2

STATUS = DONE (aceptación local de producto sobre el artifact E3D1 aislado; recorridos humanos, métricas, histograma, filtros, destacados, fichas, enlaces, móvil, Range y fallos controlados validados).

ARTIFACT_PATH = build/national-product-staging/

ARTIFACT_IDENTITY_STATUS = PASS (497 ficheros; 812510441 B; payload fingerprint 10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3; manifest SHA-256 377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e; site identity SHA-256 f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e).

PRODUCT_LOCAL_ACCEPTANCE = PASS_WITH_MINOR_GAPS

BLOCKERS = 0

E1_REGRESSIONS = A overview RESOLVED; B histogram RESOLVED; C filters RESOLVED; D map context RESOLVED; E human detail RESOLVED; F runtime dominance RESOLVED; G mobile hierarchy RESOLVED.

HISTOGRAM_BRUSH_STATUS = DEFERRED_P1_NOT_BLOCKER

MOBILE_PRODUCT_FEEL = ACCEPTABLE (map first; filters/detail/share usable; dense annual bars remain a touch-target P1).

PMTILES_RANGE = PASS (Protomaps + ESFire30; Range-only in directed sessions; no full download).

GLYPH_404_COUNT = 0

RUNTIME_UNEXPECTED_ERRORS = 0

PRODUCT_RELEASE_CANDIDATE = READY_FOR_REMOTE_PRODUCT_STAGING

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E3D2_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE.md; data/audit/product/es4e3d2_national_product_local_acceptance.json

PAGES_BYTES_REMAINING = 187489559

PAGES_CAPACITY_STATUS = LIMITED_BUT_ACCEPTABLE

NEXT_PHASE = ES-4E4_NATIONAL_PRODUCT_STAGING

PHASE = ES-4E4A

STATUS = DONE (artifact nacional de producto E3D1/E3D2 desplegado exactamente en GitHub Pages staging mediante transport TAR con gate de identidad local, runner y remoto; Range Protomaps/ESFire30, glyphs, base path y 4 smokes rápidos PASS; producción GVA intacta).

STAGING_REPOSITORY = InThuRain/atlas-incendios-es4c3d4-pages-staging

STAGING_BRANCH = main

PREVIOUS_STAGING_COMMIT = 99b38f409e6affc219a15b2b37cfd48bfd83b706

NEW_STAGING_COMMIT = a210ab94812aab85686ef76ef4654b954426bc75

WORKFLOW_RUN_ID = 33853441734

DEPLOYMENT_URL = https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/

TRANSPORT = national-product-staging.tar; 812902400 B; SHA-256 4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7; GitHub Release prerelease national-product-staging-es4e4a

LOCAL_ACCEPTED_SITE_IDENTITY = PASS (497 files; 812510441 B; payload fingerprint 10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3; asset-manifest SHA 377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e; site-identity SHA f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e).

RUNNER_SITE_IDENTITY = PASS (mismo contrato tras extracción, antes de upload-pages-artifact).

REMOTE_ARTIFACT_IDENTITY_STATUS = PASS

STAGING_DEPLOYMENT_STATUS = PASS

REMOTE_RANGE_STATUS = PASS (Protomaps + ESFire30; 0-0, initial, middle, final = 206 byte-idénticos; full download false).

REMOTE_PACKAGING_SMOKE_STATUS = PASS (España 1995, GVA 1995, Elx 2025, móvil 390×844; glyphs 9/9; external runtime domains []).

PRODUCTION_UNCHANGED = true

PRODUCT_RELEASE_CANDIDATE = READY_FOR_REMOTE_PRODUCT_ACCEPTANCE

D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION

RESULTS_PATH = ES_4E4A_NATIONAL_PRODUCT_STAGING_DEPLOYMENT.md; data/audit/product/es4e4a_national_product_staging_deployment.json

NEXT_PHASE = ES-4E4B_NATIONAL_PRODUCT_REMOTE_ACCEPTANCE

PHASE = ES-4E4B

STATUS = DONE (aceptación remota de producto sobre GitHub Pages staging exacto: identidad, métricas, histograma, filtros, fichas, navegación territorial, enlaces nativos, Range, caché de sesión, móvil y aislamiento de errores comprobados; sin modificaciones remotas).

REMOTE_PRODUCT_ACCEPTANCE = PASS_WITH_MINOR_GAPS

REMOTE_STAGING_URL = https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/

REMOTE_ARTIFACT_IDENTITY = PASS (497 ficheros; 812510441 B; payload fingerprint 10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3; manifest SHA-256 377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e; site identity SHA-256 f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e).

REMOTE_PM_TILES_RANGE = PASS (Protomaps + ESFire30 Range 206; no descarga completa observada).

E1_REMOTE_REGRESSIONS = RESOLVED_REMOTE (overview, histograma, filtros, contexto, fichas, ruido técnico y jerarquía móvil).

P1_POST_RELEASE = histograma brush; objetivo táctil anual móvil; feedback de carga municipal fría.

CDN_CACHE_VALIDATION = NOT_VALIDATED

PRODUCTION_UNCHANGED = true

NATIONAL_RELEASE_CANDIDATE = READY_FOR_ROOT_DECISION

D5_STATUS = READY_TO_RESUME (no autorizado/iniciado en E4B)

RESULTS_PATH = ES_4E4B_NATIONAL_PRODUCT_REMOTE_ACCEPTANCE.md; data/audit/product/es4e4b_national_product_remote_acceptance.json

NEXT_PHASE = ES-4D5_ROOT_SWITCH_DECISION

PHASE = ES-4D5_ROOT_SWITCH_EXECUTION

STATUS = DONE (push normal autorizado, workflow nacional manual y deployment Pages remoto ejecutados; root nacional con identidad exacta, Range, producto, enlaces y móvil aceptados).

ROOT_SWITCH_EXECUTION = PASS

PRODUCTION_SWITCH_STATUS = PASS

REMOTE_PRODUCTION_IDENTITY_STATUS = PASS

NATIONAL_PRODUCT_STATUS = LIVE

PRODUCT_RELEASE_CANDIDATE = RELEASED

D5_STATUS = COMPLETE

ROLLBACK_REQUIRED = false

PRODUCTION_URL = https://inthurain.github.io/atlas-incendios/

STAGING_URL = https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/

PUSHED_HEAD = 84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c

WORKFLOW_RUN_ID = 34373964522

PAGES_ARTIFACT_ID = 10113096632

PAGES_DEPLOYMENT_ID = 6353961987

REMOTE_SITE_IDENTITY = f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e

REMOTE_ASSET_MANIFEST = 377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e

PMTILES_RANGE = PASS (Protomaps + ESFire30: 0-0, initial, middle and final HTTP 206 byte-identical; no full download).

GLYPH_404_COUNT = 0

RUNTIME_UNEXPECTED_ERRORS = 0

LEGACY_GVA_V1 = PASS_DIRECT (historic and EFFIS hashes restore state/map; the old test-node observer is not applicable after v1 restoration).

CDN_CACHE_VALIDATION = NOT_VALIDATED_INDEPENDENTLY

RESULTS_PATH = ES_4D5_ROOT_SWITCH_EXECUTION.md; data/audit/product/es4d5_root_switch_execution.json

NEXT_PHASE = POST_RELEASE_CHECKPOINT

PHASE = ES-4POST1_GVA_MAP_EXPLORATION_PARITY_AUDIT

STATUS = DONE

POST_RELEASE_PRODUCT_PARITY_REVIEW = FAILED_NEEDS_FIX

MAP_EXPLORATION_PARITY = FAIL

GEOMETRY_COMPLETENESS = FAIL (ICV 1993–2024: asset 13738 parts / 13739 geometries; national runtime loads 12404 / 12405. 1334 2016–2019 records with historical province spellings are excluded by the current ICV province-value crosswalk.)

TEMPORAL_VISUAL_ENCODING = FAIL

DIRECT_MAP_POPUP = FAIL

RELEASE_TAG_STATUS = HOLD

PRODUCTION_STATUS = LIVE_UNCHANGED

RESULTS_PATH = ES_4POST1_GVA_MAP_EXPLORATION_PARITY_AUDIT.md; data/audit/product/es4post1_gva_map_exploration_parity_audit.json

NEXT_PHASE = ES-4POST2_GVA_MAP_EXPLORATION_PARITY_IMPLEMENTATION

PHASE = ES-4POST2A_ICV_GEOMETRY_COMPLETENESS

STATUS = DONE (crosswalk ICV explícito de siete grafías fuente; 1.334 registros/perímetros 2016–2019 recuperados en el runtime nacional sin reconstruir datos ni cambiar semántica de fuentes).

ICV_GEOMETRY_COMPLETENESS = PASS

GEOMETRY_COMPLETENESS = PARITY (ICV 1993–2024: 13.738 registros; 13.739 geometrías)

PRODUCTION_PATCH_PRIORITY = HIGH

MAP_EXPLORATION_PARITY = STILL_FAILS_PENDING_VISUAL_INTERACTION

RELEASE_TAG_STATUS = HOLD

PRODUCTION_STATUS = LIVE_UNCHANGED (no push, deploy ni tag durante POST2A)

RESULTS_PATH = ES_4POST2A_ICV_GEOMETRY_COMPLETENESS.md; data/audit/product/es4post2a_icv_geometry_completeness.json

NEXT_PHASE = ES-4POST2B_TEMPORAL_ENCODING_AND_OVERLAP

PHASE = ES-4POST2B_TEMPORAL_ENCODING_AND_OVERLAP

STATUS = DONE (estilo temporal azul antiguo → rojo reciente recuperado sobre las geometrías ICV, ESFire30 y EFFIS; dominio explícito por periodo solicitado, leyenda primaria y solapes legibles; sin datasets, despliegue ni cambios de permalink).

TEMPORAL_VISUAL_ENCODING = PARITY

OVERLAP_READABILITY = PARITY

TEMPORAL_LEGEND_STATUS = PASS

MAP_FIRST_TEMPORAL_DISCOVERY = PASS

MAP_EXPLORATION_PARITY = STILL_FAILS_PENDING_DIRECT_POPUP

ICV_1993_2024 = PASS (13738 records; 13739 geometries)

ICV_RECOVERED_2016_2019 = PASS (341/341; 346/346; 375/375; 272/272)

ICV_2024AL0005 = PASS (1 fire_id; 2 geometry_id; selección individual)

FILTERS_TEMPORAL_DOMAIN = PASS (ICV área, GIF y causa no redefinen el dominio)

HISTOGRAM_TEMPORAL_UPDATE = PASS (clic anual 2016 → estado y leyenda 2016–2016)

PERMALINKS = PASS (es4c-state-v1 y GVA #v=1 sin cambios de contrato)

PRODUCTION_STATUS = LIVE_PRE_POST2A

PATCH_BUNDLE_RECOMMENDATION = CONTINUE_TO_POST2C_BEFORE_DEPLOY

RELEASE_TAG_STATUS = HOLD

RESULTS_PATH = ES_4POST2B_TEMPORAL_ENCODING_AND_OVERLAP.md; data/audit/product/es4post2b_temporal_encoding_and_overlap.json

NEXT_PHASE = ES-4POST2C_DIRECT_HUMAN_POPUP

PHASE = ES-4POST2C_DIRECT_HUMAN_POPUP

STATUS = DONE (popup humano directo MapLibre, con selección exacta, selector de solapes fuente-separado, ficha reutilizada y evidencia Chromium desktop/móvil; sin datasets, deploy, push ni tag).

DIRECT_CLICK = PARITY

BASIC_POPUP = PARITY

HUMAN_FIELD_AVAILABILITY = PARITY

MULTI_HIT_EXPLORATION = PARITY

MOBILE_POPUP = PARITY

MAP_FIRST_CLICK_DISCOVERY = PASS

MAP_EXPLORATION_PARITY = READY_FOR_FINAL_ACCEPTANCE

ICV_1993_2024 = PASS (13.738 records; 13.739 geometrías; recuperados 2016–2019 conservados).

ICV_2024AL0005 = PASS (un source record, dos geometry_id, popup/selección individual).

TEMPORAL_VISUAL_ENCODING = PARITY

OVERLAP_READABILITY = PARITY

PERMALINKS = PASS (es4c-state-v1 y GVA #v=1 sin cambio de contrato; popup visual no serializado).

PRODUCTION_PATCH_BUNDLE = POST2A_POST2B_POST2C

PRODUCTION_STATUS = LIVE_PRE_POST2A (sin push ni despliegue durante POST2C).

RELEASE_TAG_STATUS = HOLD

RESULTS_PATH = ES_4POST2C_DIRECT_HUMAN_POPUP.md; data/audit/product/es4post2c_direct_human_popup.json

NEXT_PHASE = ES-4POST2D_MAP_EXPLORATION_FINAL_ACCEPTANCE

PHASE = ES-4POST2D_MAP_EXPLORATION_FINAL_ACCEPTANCE

STATUS = DONE (aceptación local comparativa GVA anclado frente a nacional POST2A+B+C; sin push, deploy, tag, datos ni PMTiles).

MAP_EXPLORATION_PARITY = PASS

POST2_PRODUCT_RECONCILIATION = PASS

PRODUCTION_PATCH_READY = true

PRODUCTION_PATCH_BUNDLE = POST2A_POST2B_POST2C

PRODUCTION_PATCH_RECOMMENDATION = DEPLOY_POST2A_POST2B_POST2C

PATCH_PRIORITY = HIGH

PRODUCTION_STATUS = LIVE_PRE_POST2A

RELEASE_TAG_STATUS = HOLD

RESULTS_PATH = ES_4POST2D_MAP_EXPLORATION_FINAL_ACCEPTANCE.md; data/audit/product/es4post2d_map_exploration_final_acceptance.json

NEXT_PHASE = ES-4POST3_PRODUCTION_PATCH_ARTIFACT

PHASE = ES-4POST3_PRODUCTION_PATCH_ARTIFACT

STATUS = DONE (artifact nacional POST2A+B+C reproducible, TAR y extracción segura validados localmente; sin push, deploy, upload ni tag).

PATCH_ARTIFACT_STATUS = READY_FOR_REMOTE_STAGING

PATCH_ARTIFACT_REPRODUCIBILITY = PASS

MAP_EXPLORATION_PARITY = PASS

PRODUCTION_PATCH_READY = true

PRODUCTION_PATCH_BUNDLE = POST2A_POST2B_POST2C

PATCH_PRIORITY = HIGH

RELEASE_TAG_STATUS = HOLD

RESULTS_PATH = ES_4POST3_PRODUCTION_PATCH_ARTIFACT.md; data/audit/product/es4post3_production_patch_artifact.json

NEXT_PHASE = ES-4POST4_PRODUCTION_PATCH_STAGING
