# ES-4HOT2 — Click routing staging

Does a real remote click on a visible fire now consume the gesture before
territorial navigation?

**Sí: PASS.** Clics y taps CDP reales contra el paquete remoto abren popup o
selector sin cambiar territorio. El fondo sigue permitiendo drill administrativo.
Producción permanece LIVE_V1_0_0; HOT3 no se ha iniciado.

## Fuente y construcción

Fuente de producto: `d98810048994d90bf0a99a883dee94c29a1abb5e`.
Precheck: origin/main `b8949f99c88118e1091a83bc1853184246374c21`,
ahead 1 / behind 0; sin cambios tracked, solo build/ no seguido.
El checkpoint documental posterior b52b3b7 no altera el producto.
Antes del commit de cierre: ahead 2 / behind 0.

Dos ensamblados canónicos limpios: `build/national-product-hot1-candidate` y
`build/national-product-hot1-candidate-repro`. Los siete campos coinciden:

| Campo | Valor |
|---|---|
| Archivos site | 501 |
| Bytes site | 812542848 |
| Archivos payload | 499 |
| Bytes payload | 812322370 |
| Fingerprint | 7d85b4f07dd5901452b028831d8d33c4cbf8567a9732aca74d44981ba60fc992 |
| Manifest SHA-256 | 5e0610b121f54550b852460053b9c1d5c35e6be2311363f53fcbe9817762f3a9 |
| Site identity SHA-256 | 6ae69340c9fb676d2331e9afbf1dd98569873b43119f73e2672665122fc4e30a |

Delta v1.0.0: +1 archivo, **+2225 B site / +1869 B payload**. Cambian únicamente
runtime/app.js, el nuevo map_click_routing.mjs y los tres controladores territoriales.
Todos los archivos data/ mantienen SHA: ningún dataset reconstruido.

Protomaps: 293324998 B, SHA
`72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729`.
ESFire30: 63052056 B, SHA
`3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`.
Glyphs: mismos nueve rangos.

## Transporte y deployment

TAR fijo `build/national-product-hot1-candidate.tar.gz`: **431671665 B**,
SHA `0ba62338927b76c56f5bcde5446cfd62a712d92e5edbeaf6815c1200383e9cba`.
Extracción local independiente: PASS, cero referencias de ruta staging.
No se recomprimió entre aceptación y upload.

- Repositorio: InThuRain/atlas-incendios-es4c3d4-pages-staging.
- Prerelease nueva: national-product-v1.0.1-staging-hot2.
- [TAR exacto](https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/releases/download/national-product-v1.0.1-staging-hot2/national-product-hot1-candidate.tar.gz).
- Asset GitHub: 559387877; digest y tamaño remotos idénticos.
- Workflow manual pages-hot2.yml, sin inputs libres.
- Commit staging: 2643e2a4f38725b0c6918f5bd80a9c6ee3cbcf12.
- [Run 34699143697](https://github.com/InThuRain/atlas-incendios-es4c3d4-pages-staging/actions/runs/34699143697): success.
- Pages deployment: **6410645351**, success.
- Runner: descarga TAR fijo → SHA/bytes → extracción segura → gate físico
  y golden identity → Pages. No build de fuente/datos en runner.
- HTTP remoto: manifest/site SHA exactos del candidato nuevo, no los de POST2.

El primer intento con target SHA abreviado recibió 422 sin crear release.
Después auto-review pidió autorización explícita de upload. El usuario la concedió;
se reanudó con SHA completo, sin eludir permisos ni repetir build/tests caros.
Se conserva b52b3b7 como checkpoint de esa pausa. El push fue exclusivamente al
repositorio staging; ninguna release previa se sobrescribió. No hubo auto-deploy.

## Clics reales: evidencia principal

13/13 escenarios locales empaquetados y 13/13 remotos: ICV, provincia,
municipio, multi-hit, recuperado 2016, ambas geometrías 2024, ESFire30, EFFIS,
móvil, filtro de superficie, fuente oculta y periodo.

La prueba obtiene píxeles pintados y no tapados por UI, envía mousePressed/
mouseReleased o touchStart/touchEnd mediante CDP y registra estado antes/después.
El observador envuelve listeners solo para trazarlos, delegando a los originales;
no invoca el helper interno de apertura.

- ICV: incendio 11/05/1995, Arañuel, 5 ha, Rayo; selección exacta.
- Provincia: 2016AL0074 abre ficha, provincia conservada y municipio null.
- Municipio: mismo control, ES:MUN:03042 conservado.
- Fondo CCAA: drill a ES:PROV:12.
- Fondo provincial: drill a ES:MUN:03082 bajo ES:PROV:03.
- Multi-hit: chooser de dos perímetros, sin drill ni fusión de fuentes.
- 2016AL0074: Cumbres del Sol, 04/09/2016, 689,3 ha, Negligencia, GIF.
- 2024AL0005: dos entradas reales del chooser. Una comprobación suplementaria
  pulsa cada botón real y selecciona por separado
  `gva:geometry:2024:121:13587` y `gva:geometry:2024:121:13606`.
  No basta con considerar abierto el chooser: ambas selecciones individuales PASS.
- ESFire30: popup «Perímetro Landsat», año 1995; no cartografía oficial.
- EFFIS Elx: 30/10/2025, 7 ha, «Dato satelital provisional».
- Cursor pointer coherente en todos los controles visibles.
- Filtro, fuente oculta y periodo excluyente: cero hits del perímetro excluido;
  no consume el gesto y el fondo sigue navegando.
- Móvil 390×844 emulado: tap real en incendio y fondo, PASS.
- Segunda pasada independiente con perfiles limpios: ICV, provincia y móvil,
  con fondos en los tres escenarios, 3/3 PASS.
- Point-query nacional no añadido; precedencia del hook cubierta por unidad.

## Regresiones y entrega

ICV mantiene **13738 registros / 13739 geometrías**.
2000–2020 mantiene 8519/8519, dominio temporal, azul antiguo/rojo reciente y
leyenda «Año del perímetro». El caso real multi-hit conserva legibilidad de
solapamientos y chooser; no se repitió la campaña visual POST4 completa.

Campos humanos del popup conservados. Cero peticiones DETAIL al abrir los
popups observados; «Ver detalles» sigue siendo acción explícita.
Nativo: nueva pestaña y reload conservan selección/estado/cámara.
Legacy histórico y Elx/EFFIS: periodo/cámara preservados; el reciente invalida
correctamente una selección de 7 ha con filtro de 10 ha.

Protomaps y ESFire30: Range 206 y slices 0–0/0–16383 idénticos al local.
Lecturas PMTiles capturadas en browser: 206; ninguna descarga completa observada.
Glyphs remotos: 9/9 HTTP 200. Cero errores inesperados capturados.
Estas mediciones son aceptación funcional, no un nuevo benchmark de rendimiento.

**28 tests específicos PASS**, con Node 22.18.0 temporal verificado por checksum:
24 existentes y 4 del harness HOT2. No se cambió producto para Node 10.
La suite completa no se ejecutó.

## Diferencia respecto a aceptación anterior

POST2 comprobó funcionalidad del popup pero no el arbitraje global del gesto.
HOT2 comprueba explícitamente:

`REAL POINTER EVENT → SINGLE ARBITER → FIRE/BACKGROUND DECISION → FINAL STATE`.

Se preserva evidencia machine-readable con estados, IDs, texto de popup,
traza de listeners, recursos Range, identidad y recibos del runner.

## Producción y decisión

Producción continúa con site SHA
`f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1`.
Main remoto sigue en b8949f99c88118e1091a83bc1853184246374c21.
Tag national-product-v1.0.0 intacto: objeto anotado
9c951b0c6bc2e66cd3e1613fd8f6a14e0fd101aa, destino
534cfe37a7120904f48c87bba71b4fcb7423bb5f.

```text
HOTFIX_STAGING_STATUS = PASS
REMOTE_CLICK_ROUTING = PASS
PRODUCTION_HOTFIX_CANDIDATE = READY_FOR_V1_0_1_PRODUCTION
RECOMMENDED_HOTFIX_VERSION = national-product-v1.0.1
NEXT_PHASE = ES-4HOT3_V1_0_1_PRODUCTION_EXECUTION
```

No se creó el tag de producción v1.0.1, no se modificó ningún workflow de
producción ni se despachó producción. HOT3 no iniciado.
