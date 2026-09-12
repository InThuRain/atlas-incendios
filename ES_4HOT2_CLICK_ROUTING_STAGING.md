# ES-4HOT2 — Click routing staging

Does a real remote click on a visible fire now consume the gesture before
territorial navigation?

**Pendiente de validación remota.** El paquete local pasa; no se ha desplegado
HOT2. No confundir la aceptación local con aceptación de staging.

## Checkpoint de reanudación

El control de permisos rechazó crear la nueva prerelease y subir el TAR de
431.671.665 B al repositorio de staging: pide autorización explícita del usuario
para ese destino/payload. No se eludió el rechazo. Un intento previo con SHA
abreviado fue rechazado por GitHub (422, `target_commitish`); se comprobó después
que la release sigue sin existir. No se ejecutó ningún deploy.

Sí se preparó y publicó exclusivamente en el repositorio **de staging** el
workflow manual `pages-hot2.yml`, commit
`2643e2a4f38725b0c6918f5bd80a9c6ee3cbcf12`. No hubo auto-deploy: el último run
sigue siendo POST4 `34528201012`. Los workflows anteriores se conservan.

## Fuente e identidad local

- Fuente de producto: `d98810048994d90bf0a99a883dee94c29a1abb5e`.
- `origin/main`: `b8949f99c88118e1091a83bc1853184246374c21`.
- Precheck: ahead 1 / behind 0; sin cambios tracked, solo `build/` no seguido.
- Paquete: `build/national-product-hot1-candidate`.
- Segunda construcción limpia: `build/national-product-hot1-candidate-repro`.
- 501 archivos / **812.542.848 B**; payload 499 / **812.322.370 B**.
- Fingerprint: `7d85b4f07dd5901452b028831d8d33c4cbf8567a9732aca74d44981ba60fc992`.
- Manifest SHA: `5e0610b121f54550b852460053b9c1d5c35e6be2311363f53fcbe9817762f3a9`.
- Site identity SHA: `6ae69340c9fb676d2331e9afbf1dd98569873b43119f73e2672665122fc4e30a`.
- Reproducibilidad: PASS en los siete campos de identidad.
- TAR: `build/national-product-hot1-candidate.tar.gz`, **431.671.665 B**.
- TAR SHA: `0ba62338927b76c56f5bcde5446cfd62a712d92e5edbeaf6815c1200383e9cba`.
- Extracción a `build/national-product-hot1-extracted`: gate físico PASS,
  cero referencias a rutas staging.

Incremento frente a v1.0.0: **2.225 B** de site y **1.869 B** de payload.
Solo cambian `runtime/app.js`, el nuevo `runtime/map_click_routing.mjs` y los
tres controladores administrativos. Todos los archivos `data/` conservan SHA,
incluidos ambos PMTiles y los nueve rangos glyph. No se reconstruyeron datos.

## Aceptación local realizada

13/13 escenarios con eventos CDP reales contra el artifact empaquetado:
ICV, provincia, municipio, multi-hit, 2016AL0074, ambas geometrías 2024AL0005,
ESFire30, EFFIS, móvil 390×844, superficie, fuente oculta y periodo.
Cada clic visible abre popup/chooser sin cambiar territorio. Los clics de fondo
mantienen el drill provincial y municipal; los perímetros excluidos no consumen
el gesto. Cero errores observados. No se llamó al helper interno de apertura.

ICV conserva **13.738 registros / 13.739 geometrías**. Periodo 2000–2020:
8.519/8.519, dominio y leyenda temporal correctos, azul antiguo/rojo reciente.
Permalink nativo en nueva pestaña y reload conserva estado y cámara. Los enlaces
legacy histórico y Elx/EFFIS conservan periodo/cámara; en el reciente la selección
de 7 ha se invalida por el filtro de 10 ha, como corresponde.

Ambos PMTiles: probes locales 0–0 y 0–16383 correctos; glyphs 9/9.
Estas pruebas locales **no sustituyen** el gate HTTP y browser remoto pendiente.
La ampliación del observador registra texto del popup y recursos nuevos para
la próxima ejecución remota, sin alterar el producto construido.

Tests: **24 existentes + 4 del harness HOT2, todos PASS**. Node 22.18.0 temporal,
archivo oficial verificado por SHA; no se modificó Node 10 del sistema ni el
producto para adaptarlo. La limitación antigua de Node 10 no es regresión.

## Qué valida esta aceptación

POST2 validó la funcionalidad del popup, pero no el arbitraje global del clic.
HOT2 recorre `REAL POINTER EVENT → SINGLE ARBITER → FIRE/BACKGROUND → FINAL STATE`.
La evidencia local registra estado antes/después, selección, territorio y cursor.
Faltan los mismos controles **remotos** y la segunda pasada de perfil limpio.

## Reanudación sin repetir trabajo

No reconstruir ni recomprimir el candidato. Reutilizar identidad, TAR, extracción,
tests y evidencia local bajo `build/es4hot2/`.

Tras autorización explícita de upload:

1. Comprobar que sigue ausente la release nueva y que producción permanece v1.0.0.
2. Crear prerelease `national-product-v1.0.1-staging-hot2` en
   `InThuRain/atlas-incendios-es4c3d4-pages-staging`, apuntando al SHA completo
   `2643e2a4f38725b0c6918f5bd80a9c6ee3cbcf12`, con este TAR exacto.
3. Verificar bytes/digest remoto antes de despachar `pages-hot2.yml`.
4. El runner descarga TAR fijo → verifica SHA/bytes → extracción segura →
   gate físico/identidad → Pages. No construye fuentes ni datos.
5. Verificar identidad nueva remota; ejecutar `es4hot2_packaged_clicks.py --base`
   y `es4hot2_regressions.py --base`, guardando outputs nuevos. Segunda pasada
   solo `--cases icv province mobile` (incluyen fondo).
6. Revisar campos humanos, ausencia de DETAIL necesario, Range y errores. Confirmar
   producción/tag intactos. Solo entonces emitir aceptación y cierre HOT2.

La producción observada conserva site SHA
`f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1`.
El tag `national-product-v1.0.0` sigue apuntando a
`534cfe37a7120904f48c87bba71b4fcb7423bb5f`. No hubo push a main de producción,
deploy de producción ni creación de tag v1.0.1.

```text
HOTFIX_STAGING_STATUS = PENDING_EXPLICIT_UPLOAD_AUTHORIZATION
REMOTE_CLICK_ROUTING = NOT_RUN
PRODUCTION_HOTFIX_CANDIDATE = NOT_YET_ACCEPTED
NEXT_PHASE = ES-4HOT2_CLICK_ROUTING_STAGING (continuation)
AFTER_PASS_NEXT_PHASE = ES-4HOT3_V1_0_1_PRODUCTION_EXECUTION
```

HOT3 no iniciado. Este documento es checkpoint, no informe de cierre PASS.
