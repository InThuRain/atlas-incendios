# ES-4E3D1 — Artifact nacional de producto

## Resultado final

La segunda construcción cierra el bloqueo de glyphs sin cambiar el basemap,
el fontstack, el estilo, los datasets ni el producto:

- `PRODUCT_ARTIFACT_STATUS = READY_FOR_LOCAL_ACCEPTANCE`
- `ARTIFACT_IDENTITY_STATUS = PASS`
- `GLYPH_COVERAGE_STATUS = PASS`
- `GLYPH_RANGE_DISCOVERY_STABLE = true`
- `GLYPH_404_COUNT = 0`
- `GLYPH_UNBUNDLED_RANGE_COUNT = 0`
- `PAGES_CAPACITY_STATUS = LIMITED_BUT_ACCEPTABLE`
- `PRODUCT_RELEASE_CANDIDATE = false`
- `D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`
- `NEXT_PHASE = ES-4E3D2_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE`

El artifact está en `build/national-product-staging/`, es local, está ignorado
por Git y no se ha desplegado. ES-4E3D2 no se ha iniciado.

## Historial de intentos

### ATTEMPT 1 — `BLOCKED_GLYPH_COVERAGE`

Se conserva como evidencia del gate que funcionó correctamente. El artifact
contenía solo `Noto Sans Regular/0-255.pbf`; Chromium solicitó además
`256-511`, `512-767`, `768-1023`, `1024-1279`, `1536-1791`, `7680-7935`
(en Asturias) y `11520-11775`. La identidad física era válida, pero el producto
no podía pasar a aceptación.

| Magnitud | ATTEMPT 1 |
|---|---:|
| `SITE_FILE_COUNT` | 489 |
| `SITE_TOTAL_BYTES` | 811,665,494 |
| `PAYLOAD_FILE_COUNT` | 487 |
| `PAYLOAD_TOTAL_BYTES` | 811,455,504 |
| `PAYLOAD_FINGERPRINT` | `a9bb511c353c5dff8104239572b88d2c2ed2755436abdbadc664790eb4ffa2cf` |
| `asset-manifest.json` SHA-256 | `f6d1e3b2945f979e6515ca5881bb9aae528f4ddcceaec2e6912adc87346286db` |
| `site-identity.json` SHA-256 | `5bdfaa23d771c7b0accef5d58cf25a64cef82b63d6f1652bb1bd8fb6f17561be` |
| Pages restantes | 188,334,506 B |

### ATTEMPT 2 — `READY_FOR_LOCAL_ACCEPTANCE`

El fix amplía el contrato de glyphs, los incorpora al ensamblado y hace que el
checker verifique todos. Se construyó dos veces desde outputs limpios y ambas
identidades coinciden exactamente.

| Magnitud | Build 1 | Build 2 |
|---|---:|---:|
| `SITE_FILE_COUNT` | 497 | 497 |
| `SITE_TOTAL_BYTES` | 812,510,441 | 812,510,441 |
| `PAYLOAD_FILE_COUNT` | 495 | 495 |
| `PAYLOAD_TOTAL_BYTES` | 812,291,384 | 812,291,384 |
| `PAYLOAD_FINGERPRINT` | `10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3` | igual |
| `asset-manifest.json` SHA-256 | `377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e` | igual |
| `site-identity.json` SHA-256 | `f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e` | igual |

El incremento físico total frente al intento bloqueado es 844,947 B. De
ellos, 833,330 B son glyphs adicionales; los 11,617 B restantes corresponden
al manifest ampliado, metadata de identidad/configuración y pequeños cambios
del frontend ensamblado. Quedan 187,489,559 B frente al límite físico de
1,000,000,000 B usado por el proyecto.

## Método de cobertura glyph

Se eligió `ACCEPTANCE_MATRIX_COMPLETE`. Derivar exhaustivamente los codepoints
renderizables habría requerido recorrer y decodificar todo el PMTiles exacto,
incluidas etiquetas visibles fuera de España, con un coste desproporcionado
para este fix. En su lugar, el harness usa `PerformanceResourceTiming` de
Chromium —que conserva también peticiones 404— y recorre una matriz bounded y
determinista:

- 16 contextos: España, Galicia, Asturias, Cantabria, País Vasco, Navarra,
  Catalunya, Comunitat Valenciana, Illes Balears, Andalucía, Ceuta, Melilla,
  Canarias y tres interiores (Madrid/Toledo, Castilla y León, Aragón);
- zooms 5, 7, 9, 12 y 14;
- 80 vistas por ejecución;
- dos ejecuciones limpias completas.

Ambas ejecuciones solicitaron la misma unión de 9 rangos. La segunda no
descubrió ninguno nuevo: `GLYPH_RANGE_DISCOVERY_STABLE = true`. Esta es una
garantía bounded para la matriz de aceptación, no “cobertura Unicode completa”.

## Fuente, licencia y adquisición

Se mantiene exclusivamente `Noto Sans Regular`, sin bold, serif, fallback,
fuentes del sistema, sprites ni CDN runtime. Los assets proceden del repositorio
`protomaps/basemaps-assets`, fijado al commit
`028c18f713baecad011301ff7a69acc39bcc2ae7`, bajo SIL OFL 1.1. El primer rango
descargado desde esa revisión es byte-idéntico al asset aprobado previamente.

La adquisición es explícita:

```bash
python3 scripts/basemaps/acquire_protomaps_glyphs.py --download \
  --output build/es4e3d1/glyph-acquisition.json
```

Sin `--download`, el helper solo verifica inputs locales. Los tests y el
assembler nunca descargan; un input ausente o con identidad incorrecta bloquea
el build como `MISSING_STAGING_INPUT`. Cada PBF se valida como protobuf glyph,
incluido el rango declarado, y se rechazan respuestas HTML. `OFL.txt` se
empaqueta una sola vez.

| Rango | Bytes | SHA-256 |
|---|---:|---|
| `0-255` | 76,044 | `62c6d49b15fa836eb6aa45e259c7ca6762f44b011b09e47776efbe4a6db1b397` |
| `256-511` | 127,726 | `2eca7561f9f566bcacfda5dd04fb5880baec1328ec0f5484678289a13994de8a` |
| `512-767` | 94,728 | `6abc80badad0e823e228ab739515be257c8b33bc68bb077dd873030e9b2d143a` |
| `768-1023` | 77,034 | `537ccbee79180f4f8b3f6d2bdd27df979260ce1a0358c40d7aa7db505d9b03aa` |
| `1024-1279` | 125,320 | `302231023f7048d9694a7b3f3b737c8bc378f5af0175aed5bb4f2f3b6188919a` |
| `1536-1791` | 110,716 | `f46850e6574d817d58d96b91196739c77c1b570a7b4f992ff1380d2b4d5d631f` |
| `7680-7935` | 135,449 | `b9100ec886dff647198802c41d1ca6df9e6f82325179d8d71e3d377b5fe8682e` |
| `8192-8447` | 64,220 | `8ea977a587352fe31b4159ffdbc9a40be79056f2472017c742ea1e4a931864b9` |
| `11520-11775` | 98,137 | `59d1bc7f5596128a7ffb6ce801a784d3c2dbf8c9f0736fca85a38cb634a8b6e7` |

Antes: 1 fichero, 76,044 B. Después: 9 ficheros, 909,374 B. Delta:
833,330 B. El rango `8192-8447`, no presente en los siete hallazgos iniciales,
fue descubierto al ampliar la matriz en Comunitat Valenciana; por eso no se
cerró el fix limitándose a copiar aquellos siete.

## Inputs que permanecen intactos

- Protomaps: 293,324,998 B; SHA-256
  `72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729`.
- ESFire30: 63,052,056 B; SHA-256
  `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`.
- `national-ux-summary-v1`: fingerprint
  `2546247b68ef8e27fed3334cf5fb4a027056f094e36420213080c431bfb850e4`;
  manifest SHA-256
  `b09e69648b6b2dee03265f12a00624de72d4006301b04d796889c1bf151a8e7b`.
- `national-highlights-v1`: manifest SHA-256
  `578cddd7a3d341d0fd7aa72382b7159c603724155798309fc338a515fdc2762a`;
  payload SHA-256
  `c09a92afd184ee46cca0e417a2a9ae3e0b5fc8b193c0b54bb9201f6f02197059`.

Ambos PMTiles pasan `pmtiles verify`; el fix no los reconstruye ni los
reextrae.

## Ensamblado, autocontención y checker

Los builds reproducibles fueron:

```bash
python3 scripts/build_national_pages_artifact.py --profile product \
  --output build/national-product-staging
python3 scripts/build_national_pages_artifact.py --profile product \
  --output build/national-product-staging-repro
```

El checker independiente recorre el output físico, verifica manifest,
fingerprint, site identity, los dos PMTiles, summary, highlights y cada glyph
declarado (existencia, bytes y SHA). Un fichero extra, incluido un glyph no
declarado, se detecta mediante el inventario físico. Resultado: PASS en ambos
outputs y coincidencia de las siete magnitudes de identidad.

El artifact se sirvió como docroot aislado. No hay referencias a `/src/`,
`/prototypes/`, `/data/derived/`, `/work/` ni dependencias de datos externas.
Todos los glyphs se resuelven same-origin bajo el template versionado.

## Range y smokes de packaging

Los cuatro slices (0-0, inicial, medio y final) de ambos PMTiles devolvieron
HTTP 206, `Content-Range` correcto y bytes idénticos al input. No hubo descarga
completa.

Los siete quick smokes pasaron con `basemap = ready`, cero errores runtime,
cero dominios externos y solo Range para ambos PMTiles:

| Escenario | Viewport | Resultado |
|---|---:|---|
| root | 1440×757 | PASS |
| España | 1440×757 | PASS |
| GVA 1995 | 1440×757 | PASS |
| Elx 1993–2002 | 1440×757 | PASS |
| España móvil | 390×844 | PASS |
| Elx móvil | 390×844 | PASS |
| Asturias móvil | 390×844 | PASS |

España conserva labels, BDLJE, summary e histograma. Galicia no presenta
errores glyph; Asturias solicita y sirve correctamente `7680-7935`; País
Vasco/Navarra, Catalunya/GVA/Balears, Ceuta/Melilla, Canarias y los contextos
interiores pasan sin 404. Los labels transfronterizos se preservan. La prueba
de fallo del PMTiles Protomaps termina en `fallback_bdlje_only`, manteniendo
BDLJE y ESFire30 operativos.

Son smokes de packaging y cobertura tipográfica, no la aceptación integral
del producto. No se han tocado summary, histograma, filtros, destacados,
fichas, permalinks ni vista recomendada.

## Evidencia reproducible

- `config/national-basemap-protomaps-20260902-z12.json`: fuente, revisión,
  licencia, paths, bytes y SHA por rango.
- `data/audit/product/es4e3d1_glyph_coverage.json`: matriz, dos ejecuciones,
  rangos y estabilidad.
- `data/audit/product/es4e3d1_national_product_artifact.json`: ATTEMPT 1,
  ATTEMPT 2 e identidad final.
- `benchmarks/es4e3d1/run_glyph_coverage.py`: discovery mediante recursos del
  navegador.
- `benchmarks/es4e3d1/run_packaging_smoke.py`: quick smokes, Range, glyphs y
  fallback.

## Siguiente paso permitido

Solo `ES-4E3D2_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE`. E3D1 deja el artifact
preparado, pero `PRODUCT_RELEASE_CANDIDATE` sigue siendo `false` y D5 continúa
pausado. No se ha iniciado E3D2, no se ha desplegado y no se ha modificado
producción.
