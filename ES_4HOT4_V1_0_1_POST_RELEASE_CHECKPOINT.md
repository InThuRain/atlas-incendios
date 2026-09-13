# ES-4HOT4 — Cierre formal v1.0.1

Resultado: **PASS · LIVE_V1_0_1 · HOTFIX_CYCLE COMPLETE**.
Observaciones renovadas el 13/09/2026. No rebuild, deploy, dispatch, cambio de
producto/datos ni implementación del backlog.

## Git y versión

- Precheck tras fetch: HEAD `a314fcefee6659c216213fff782d9fe85c57a0ad`,
  origin/main `5cffab72499f74ea6d1f76b516adaef291eceaf7`; ahead 1 / behind 0.
- Árbol versionado limpio; `build/` contenía salidas locales no versionadas,
  excluidas del commit. No se afirma que `git status` completo estuviera vacío.
- El único commit pendiente contenía informe HOT3, evidencia HOT3 y checkpoint.
  Push normal de ese cierre: origin/main quedó en `a314fce…`; ahead/behind 0/0.
- Tag anotado `national-product-v1.0.1`, antes ausente local/remoto, creado y
  publicado únicamente sobre **`5cffab72499f74ea6d1f76b516adaef291eceaf7`**.
  Target pelado comprobado local y remotamente; no se etiquetó el cierre documental.
  Objeto anotado: `ac8ce8af9831c8e95e3ff77bd8cc8a68979311a8`.
- `national-product-v1.0.0` permanece local/remotamente en
  `534cfe37a7120904f48c87bba71b4fcb7423bb5f`, sin modificar su objeto anotado.
- Ningún nuevo run/deployment observado después del push de main ni del tag.
  El commit final HOT4 es **solo local**, sin push automático.

v1.0.0 es la primera release nacional formal con paridad de exploración GVA.
v1.0.1 corrige el arbitraje del clic entre geometrías de incendios y navegación
territorial; no cambia datos. v1.0.0 queda inmutable y disponible como rollback.

## Identidad de producción

URL: https://inthurain.github.io/atlas-incendios/

```text
MAIN_COMMIT = 5cffab72499f74ea6d1f76b516adaef291eceaf7
PAGES_DEPLOYMENT = 6414182725
PAGES_RUN = 34717913721
MANIFEST_SHA256 = 5e0610b121f54550b852460053b9c1d5c35e6be2311363f53fcbe9817762f3a9
SITE_IDENTITY_SHA256 = 6ae69340c9fb676d2331e9afbf1dd98569873b43119f73e2672665122fc4e30a
SITE = 501 files / 812542848 B
PAYLOAD = 499 files / 812322370 B
PAYLOAD_FINGERPRINT = 7d85b4f07dd5901452b028831d8d33c4cbf8567a9732aca74d44981ba60fc992
TAR = 431671665 B
TAR_SHA256 = 0ba62338927b76c56f5bcde5446cfd62a712d92e5edbeaf6815c1200383e9cba
```

Root, manifest e identidad: HTTP 200 mediante solicitudes no-cache antes del
push y después del tag, hashes exactos. Staging HOT2 mantiene HTTP 200 y la
misma identidad; no se modifica.

## Salud breve real

Se reutilizaron los auditores existentes contra producción, sin repetir la
batería HOT3 completa ni la suite. Evidencia detallada en
`data/audit/product/es4hot4_v1_0_1_post_release_checkpoint.json`.

| Control | Resultado |
|---|---|
| Clic ICV visible | Popup; territorio sin cambio |
| Clic provincial | Sin drill municipal accidental |
| Fondo administrativo | Drill territorial correcto |
| Multi-hit | Chooser; territorio sin cambio |
| Tap móvil 390×844 | Incendio y fondo correctos; emulación, no equipo físico |
| ICV completo | 13738 registros / 13739 geometrías |
| GVA 1995 | 467 / 467 |
| Leyenda temporal y control 2000–2020 | PASS |
| Elx EFFIS 2025 | 1 perímetro / 7 ha |
| Native + reload; legacy histórico/reciente | PASS |
| Protomaps / ESFire30 | Range 206, slices iniciales idénticos al local |
| Glyphs | 9/9; ningún 404 |

Cuatro casos de clic/tap pasan; sin errores inesperados. Las lecturas PMTiles
capturadas en esos casos son 206; no se observó descarga completa. Los controles
Range fueron 0–0 y 0–16383 para cada PMTiles. No se midió un nuevo benchmark.

## Rollbacks preservados

Los tres workflows están activos y son manuales (`workflow_dispatch`), sin
ejecución en HOT4:

- Principal: `pages-national-v1-0-0-rollback.yml` — READY.
- Secundario: `pages-national-pre-post2-rollback.yml` — READY.
- Profundo: `pages-legacy-gva-rollback.yml` — READY.

## Contrato permanente de interacción

Prioridad: **consulta puntual si existe → geometría de incendio visible →
drill territorial de fondo → mapa vacío**.

Aserción obligatoria en futuras releases: **clic sobre incendio visible →
territorio sin cambios**. El trabajo territorial no puede saltarse esta regla.
Se preservan exploración centrada en mapa, lectura temporal y de solapamientos,
popup directo y jerarquía humana de información.

## Backlog, sin iniciar

- P1: feedback de carga municipal en frío; blancos táctiles del histograma
  móvil; brush del histograma.
- P2: z13 / relieve / POI; ranking ESFire30 seguro; ajustes móviles menores.

`NEXT_PHASE = POST_RELEASE_BACKLOG`. No hay trabajo HOT4 pendiente tras el
commit documental local; no se inicia la siguiente fase.
