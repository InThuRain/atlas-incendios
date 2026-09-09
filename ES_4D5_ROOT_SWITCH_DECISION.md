# ES-4D5 — Decisión de cambio de raíz pública

## Decisión

```text
ROOT_SWITCH_DECISION       = GO
PRODUCTION_SWITCH_READY    = true
PRODUCT_RELEASE_CANDIDATE  = READY_FOR_PRODUCTION_SWITCH
NEXT_PHASE                 = ES-4D5_ROOT_SWITCH_EXECUTION
```

Esta decisión no publica nada. Autoriza preparar y ejecutar posteriormente el
runbook D5B, sujeto a todas sus puertas de preproducción.

## Estado auditado

| Elemento | Valor |
| --- | --- |
| Rama local | `main` |
| HEAD local | `201c3a93956e153ff356dcf2a127482b9af7f420` |
| `origin/main` tras `fetch --prune` | `7b6520bd3f9c6729580bb48692dd5f7a3afa79ca` |
| Divergencia inicial | 4 commits ahead, 0 behind; árbol limpio |
| Producción actual | `InThuRain/atlas-incendios`, Pages desde `main`, raíz `/atlas-incendios/` |
| URL actual | <https://inthurain.github.io/atlas-incendios/> (`200`) |
| Despliegue GVA actual | workflow `pages.yml`, run `32943744421`, deployment `6099343480`, status `17347149751` (`success`) |
| Commit GVA servido | `f7a3532f633a247f33dee3ebba9fbcc316c0e534` |
| Workflow actual | sólo `workflow_dispatch`; un `git push origin main` no despliega Pages |

El artifact de Pages de aquel despliegue ya expiró. Por ello el rollback no
puede depender de reusar un artifact efímero: se hará con un workflow manual
dedicado que checkoutará exactamente el commit GVA ancla y ejecutará su build
histórico, que descarga el bundle público inmutable ya fijado por ese commit.
No es una reconstrucción manual ni una búsqueda durante un incidente.

Los cuatro commits locales pendientes son:

```text
57e946d Validate exact national product staging deployment
e7e41ff Record E4A staging checkpoint
f375be7 Accept national product remotely
201c3a9 Complete remote acceptance evidence
```

## Candidato y portabilidad

El único candidato permitido es el artifact E4B ya aceptado, idéntico al
staging <https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/>:

```text
site files / bytes       = 497 / 812510441
payload files / bytes    = 495 / 812291384
payload fingerprint      = 10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3
asset-manifest SHA-256   = 377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e
site-identity SHA-256    = f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e
runtime external domains = []
```

El checker local pasa. No hay referencias a
`atlas-incendios-es4c3d4-pages-staging` en el artifact. El builder también las
prohíbe explícitamente. El staging ya validó el mismo frontend bajo un base
path de Pages; el objetivo productivo es el path relativo
`/atlas-incendios/`, sin cambio de semántica ni de asset.

El TAR aceptado sigue disponible como transporte inmutable de staging:

```text
URL     = https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-staging-es4e4a/national-product-staging.tar
bytes   = 812902400
SHA-256 = 4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7
```

Se reutiliza ese mismo transporte: D5B no genera datasets, Protomaps,
resúmenes, destacados ni un artifact equivalente.

## Compatibilidad y capacidad

- Los enlaces GVA `#v=1…` siguen pasando por el adaptador explícito y se
  validaron en el candidato aceptado; no se reescriben silenciosamente.
- Los enlaces nacionales `#es4c-state-v1…` se mantienen nativos.
- El artifact no usa datos externos en runtime; PMTiles, glyphs y datos se
  sirven same-origin.
- Capacidad Pages: `812510441 B`, con margen conservador de `187489559 B`:
  `LIMITED_BUT_ACCEPTABLE`.
- El aviso observado de acciones Node 20 ejecutadas temporalmente sobre Node
  24 queda como `NON_BLOCKING_INFRA_WARNING`; no se actualizan Actions durante
  la release.

## Estrategia D5B

La separación entre sincronizar código y desplegar es obligatoria y ya es
posible: `pages.yml` sólo tiene `workflow_dispatch`.

1. **PRECHECK.** Hacer `fetch --prune`; exigir árbol limpio, SHA esperado,
   cero commits inesperados detrás, checker local PASS, staging E4B PASS,
   disponibilidad de Pages y permisos `contents: read`, `pages: write`,
   `id-token: write`.
2. **SYNC CODE.** Añadir en un commit D5B dos workflows manuales y revisados:
   `pages-national-product.yml` y `pages-legacy-gva-rollback.yml`. El primero
   será la plantilla E4A: descarga el TAR con URL/tamaño/SHA explícitos,
   extrae, ejecuta `scripts/check_national_product_artifact.py`, guarda la
   identidad del runner y sólo entonces usa `upload-pages-artifact` y
   `deploy-pages`. El segundo hará checkout fijo de
   `f7a3532f633a247f33dee3ebba9fbcc316c0e534` y ejecutará el flujo GVA
   histórico reproducible. No se reemplaza ni se dispara `pages.yml`.
3. **PUSH CODE.** Tras revisar esos workflows, publicar los cuatro commits
   E4A/E4B más el commit D5B. Este push no despliega: el trigger es manual.
4. **ARTIFACT GATE.** El workflow nacional rechazará cualquier valor que no
   coincida con los cinco valores de identidad anteriores y con el TAR
   `812902400 B` / `4bcc80f…781edb7`.
5. **DEPLOY.** Disparar sólo `pages-national-product.yml` desde `main` con el
   SHA ya publicado y el transporte E4A. No se admite build desde fuentes.
6. **REMOTE IDENTITY.** Tras finalizar, comparar en root
   `asset-manifest.json` y `site-identity.json` con los SHA aprobados y
   registrar run/deployment/commit.
7. **SMOKES.** En perfil limpio: raíz, España 1995, GVA 1995, Elx 2025,
   Canarias, `#v=1`, `#es4c-state-v1`, móvil 390×844, glyphs y Range de
   Protomaps y ESFire30. Se repite una comprobación corta tras refresh con
   cache-busting; no se espera una ventana arbitraria.
8. **ACCEPTANCE.** Sólo declarar producción aceptada si identidad, base path,
   enlaces, glyphs y ambos PMTiles pasan y no se observa descarga completa.

## Rollback

```text
ROLLBACK_ANCHOR = f7a3532f633a247f33dee3ebba9fbcc316c0e534
```

El workflow `pages-legacy-gva-rollback.yml`, incorporado y comprobado antes
del switch, contendrá ese SHA como constante revisable. Su único propósito es
desplegar el build GVA del ancla mediante un `workflow_dispatch` manual. Así el
comando de incidente será inequívoco:

```bash
gh workflow run pages-legacy-gva-rollback.yml \
  --repo InThuRain/atlas-incendios --ref main
gh run watch <RUN_ID> --repo InThuRain/atlas-incendios
```

Después se comprueba `https://inthurain.github.io/atlas-incendios/` y se
registra el nuevo deployment. No se hace `reset`, force-push ni reconstrucción
local. El staging E4B y su Release se conservan durante la transición; tampoco
se borra código, bundle ni historial GVA.

Los triggers objetivos de rollback son: root no carga; identidad del artifact
incorrecta; Range de Protomaps o ESFire30 roto; fallo de glyph; fallo de base
path; regresión grave de permalink; o crash grave de mapa/runtime.

## Riesgos controlados

| Riesgo | Control |
| --- | --- |
| Despliegue accidental al sincronizar código | `workflow_dispatch` solamente; comprobar trigger antes de push. |
| Artifact distinto | TAR inmutable + tamaño/SHA + checker de identidad antes de upload. |
| Confusión de caché `max-age=600` | perfil limpio, cabeceras/ETag, cache-busting y segunda comprobación breve. |
| Rollback sin artifact anterior | workflow manual fijo al SHA GVA y a su bundle inmutable. |
| Capacidad Pages | gate `LIMITED_BUT_ACCEPTABLE`; no se añaden assets. |

## Marcado y trazabilidad posterior

Tras aceptación, se recomienda un tag anotado de release nacional, con nombre
acordado entonces (no se inventa ni crea ahora). La identidad productiva será:
commit Git del workflow + run/deployment Pages + `site-identity` SHA +
`asset-manifest` SHA. El tag no sustituye esas cuatro pruebas.
