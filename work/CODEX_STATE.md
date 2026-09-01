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
