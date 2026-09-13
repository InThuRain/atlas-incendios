# ES-4HOT3 — v1.0.1 production execution

Does a real production click on a visible fire now consume the gesture
before territorial navigation?

**Sí. PASS.** Producción sirve el artifact HOT2 exacto. Clics y taps reales
abren popup/chooser sin cambiar territorio; el fondo conserva la navegación.
No se requirió rollback. No se creó el tag v1.0.1 ni se inició HOT4.

## Git y autorización

Precheck tras fetch:
- HEAD: 3866054a6239c8ef10cbef5e0a878a14865ffef1.
- Origin/main: b8949f99c88118e1091a83bc1853184246374c21.
- Ahead/behind: 3/0.
- Sin cambios tracked; build/ local no seguido.
- Commits inspeccionados: d988100 (HOT1), b52b3b7 (checkpoint HOT2),
  3866054 (cierre HOT2). Sin cambios ajenos.

HOT3_PREDEPLOY_COMMIT / MAIN_COMMIT:
**5cffab72499f74ea6d1f76b516adaef291eceaf7**.

Contiene únicamente workflow nacional actualizado, rollback v1.0.0 y tests.
La fuente de producto sigue siendo d98810048994d90bf0a99a883dee94c29a1abb5e.

Segundo fetch: origen intacto, ahead 4 / behind 0. El control de permisos pidió
autorización explícita en chat para el push; se detuvo sin eludirlo. Tras
autorizar el usuario se revalidaron origen y ambas webs. Solo las notas de
cierre HOT3 estaban sin commit; no entraron en el push ni en el artifact.

Push normal: **b8949f9..5cffab7** (d988100, b52b3b7, 3866054, 5cffab7).
Después: origin/main = MAIN_COMMIT, ahead/behind 0/0.
No hubo auto-deploy: el último run continuaba siendo 34620607559 y la identidad
v1.0.0 seguía publicada antes del dispatch manual.

## Prechecks y rollback

Producción previa HTTP 200:
- Manifest SHA: 557c662dd23df2207f68b6ef36ddae35f0d06b069864ffbb8b3b53ded7a59bd0.
- Site SHA: f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1.
- Deployment anterior: 6397065009.

Staging conservaba la identidad HOT2 aceptada. Se verificaron bytes/digest del
asset HOT2 y del TAR v1.0.0 mediante la metadata de Release.

Jerarquía de rollback, todos disponibles y manuales:

1. pages-national-v1-0-0-rollback.yml: copia exacta del workflow anterior salvo
   título; contrato post2-patch y TAR duradero fijo, 431670756 B,
   SHA 8903bc91de088e82b7c3410d6b2d2e0a5eda64889ffdcc02569319fcc14e45af.
2. pages-national-pre-post2-rollback.yml: preservado.
3. pages-legacy-gva-rollback.yml: preservado.

Todos comparten group pages, cancel-in-progress false. El primario no reconstruye
v1.0.0. Ningún rollback se ejecutó.

## Workflow y transporte

pages-national-product.yml es únicamente workflow_dispatch, sin inputs libres.
Consume exclusivamente este [TAR HOT2 fijo](https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-v1.0.1-staging-hot2/national-product-hot1-candidate.tar.gz):

- Bytes: **431671665**.
- SHA-256: **0ba62338927b76c56f5bcde5446cfd62a712d92e5edbeaf6815c1200383e9cba**.
- Contrato: config/national-product-hot1-candidate-identity.json.

Orden: descarga → bytes/SHA → extracción segura → gate físico e identidad
versionada → upload Pages → deploy. Se preservaron contratos v1.0.0 y PRE-POST2.

Siete tests específicos estáticos/negativos PASS: YAML, manualidad, concurrencia,
URL/contrato fijo, orden antes de deploy, SHA TAR erróneo e identidad errónea.
No suite completa. No reconstrucción de site, datos, PMTiles ni glyphs.

## Runner y producción exacta

[Run 34717913721](https://github.com/InThuRain/atlas-incendios/actions/runs/34717913721),
trigger MAIN_COMMIT, resultado success. Duración total: aproximadamente 60 s
(20:43:14–20:44:14 UTC, 12/09/2026).

- Artifact Pages: **10305721504**.
- Artifact evidencia runner: **10305756487**.
- Pages deployment: **6414182725**.
- Runner TAR gate: PASS.
- Runner site gate: PASS; cero fallos y cero referencias staging en payload.

| Campo | Resultado |
|---|---|
| Site files / bytes | 501 / 812542848 |
| Payload files / bytes | 499 / 812322370 |
| Fingerprint | 7d85b4f07dd5901452b028831d8d33c4cbf8567a9732aca74d44981ba60fc992 |
| Manifest SHA | 5e0610b121f54550b852460053b9c1d5c35e6be2311363f53fcbe9817762f3a9 |
| Site identity SHA | 6ae69340c9fb676d2331e9afbf1dd98569873b43119f73e2672665122fc4e30a |

Identidades HTTP sin caché comprobadas tras deployment y de nuevo al cerrar.
Root /atlas-incendios/: HTTP 200, sin fuga de base path staging.
Dominios runtime externos observados: [].

Protomaps: 293324998 B,
SHA 72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729.
ESFire30: 63052056 B,
SHA 3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe.
El checker del runner conserva estos gates y los nueve rangos glyph.

## Aceptación de interacción en producción

13/13 escenarios mediante eventos CDP mousePressed/mouseReleased o touchStart/
touchEnd sobre píxeles pintados, nunca invocando el helper de apertura:

- ICV individual: popup y selección exacta; territorio/provincia/municipio intactos.
- Provincia: popup sin elegir municipio.
- Municipio: ES:MUN:03042 conservado.
- Fondo amplio: drill a ES:PROV:12.
- Fondo provincial: drill a ES:MUN:03082 bajo ES:PROV:03.
- Multi-hit: chooser de dos candidatos independientes, sin navegar.
- 2016AL0074: popup del perímetro recuperado, territorio intacto.
- 2024AL0005: ambas geometrías seleccionadas pulsando sus botones reales del chooser,
  gva:geometry:2024:121:13587 y gva:geometry:2024:121:13606.
- ESFire30: popup Landsat, sin convertirlo en cartografía oficial.
- EFFIS: popup provisional, Elx 2025, 7 ha.
- Superficie/periodo excluyente y fuente oculta: el perímetro no consume el clic.
- Hover pointer coherente en todos los casos visibles.
- Móvil 390×844 emulado: tap de incendio y tap de fondo PASS.
- Segunda pasada con perfiles nuevos: ICV/provincia/móvil y respectivos fondos,
  3/3 PASS. No se reutilizó caché JS de POST2.

Cero errores inesperados en casos válidos y ninguna petición DETAIL necesaria
para abrir el popup. Campos humanos conservados. El observador traza listeners
originales sin sustituir el árbitro del runtime.

## Regresiones dirigidas

- ICV total: 13738 registros / 13739 geometrías.
- GVA 1995: 467 / 467.
- Periodo 2000–2020: 8519 / 8519; colores, dominio y leyenda temporal PASS.
- Elx 2025: scope ES:MUN:03065, 1 perímetro EFFIS / 7 ha.
- España 1995: 5035 ESFire30 y 25557 partes EGIF, separados; 141082,17 ha EGIF.
- Canarias 1995: 56 partes EGIF; ESFire30 no_source_coverage, no «0 incendios».
- Nativo es4c-state-v1: nueva pestaña y reload conservan estado/cámara/selección.
- Legacy #v=1: histórico y Elx/EFFIS PASS; selección excluida por min_area se invalida.
- Protomaps y ESFire30: 206, slices 0–0 y 0–16383 idénticos al local.
- Lecturas PMTiles capturadas: todas 206; ninguna descarga completa observada.
- Glyphs: 9/9 HTTP 200, cero 404.

Una primera llamada suplementaria Elx usó erróneamente territory_select con ID
municipal; ese parámetro es de CCAA. Se corrigió solo el harness a
municipality_select y se repitió únicamente Elx. No fue fallo de producto,
no se cambió runtime ni se relajó un gate. La cuota interrumpió esa reanudación;
las evidencias previas se conservaron y la llamada correcta terminó PASS.

## Cierre y versionado

Staging HOT2 sigue HTTP 200 con su misma identidad. El tag national-product-v1.0.0
sigue en 534cfe37a7120904f48c87bba71b4fcb7423bb5f (objeto anotado
9c951b0c6bc2e66cd3e1613fd8f6a14e0fd101aa). No rollback requerido ni ejecutado.

```text
HOTFIX_PRODUCTION_EXECUTION = PASS
NATIONAL_PRODUCT_STATUS = LIVE_V1_0_1_UNTAGGED
REMOTE_CLICK_ROUTING = PASS
MAP_EXPLORATION_PARITY = PASS
V1_0_0_ROLLBACK_READY = true
ROLLBACK_REQUIRED = false
RELEASE_TAG_STATUS = READY_FOR_V1_0_1_TAG
NEXT_PHASE = ES-4HOT4_V1_0_1_POST_RELEASE_CHECKPOINT
```

El futuro tag national-product-v1.0.1 debe apuntar a
**5cffab72499f74ea6d1f76b516adaef291eceaf7**, el commit desplegado, nunca al commit
documental de cierre posterior. No se ha creado ese tag. HOT4 no iniciado.
El commit de cierre contiene solo informe, agregado y checkpoint y no se empuja.
