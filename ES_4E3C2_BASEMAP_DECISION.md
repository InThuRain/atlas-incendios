# ES-4E3C2 — Decisión de mapa base Protomaps autoalojado

Fecha de evaluación: 2026-09-03
Alcance: experimento local y reversible; no se modifica `src/national`, el artifact, staging ni producción.

## Decisión

`BASEMAP_RECOMMENDATION = ADOPT_PROTOMAPS_Z12`

`BASEMAP_STATUS = CANDIDATE_VALIDATED`

`Z12_VISUAL_QUALITY = SUFFICIENT`

`PROTOMAPS_ADOPTION = NOT_AUTHORIZED_YET`

`PRODUCT_RELEASE_CANDIDATE = false`

`D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`

La muestra z12 devuelve el contexto que faltaba —costa y agua, topónimos,
carreteras y orientación rural— sin competir de forma apreciable con los
incendios. Elx y Cangas del Narcea siguen siendo comprensibles al sobrezoom,
por lo que no se justifica descargar z13. El coste físico completo es
293.411.976 B y el sitio proyectado queda en 811.600.291 B: 188.399.709 B por
debajo del límite conservador de 1.000.000.000 B ya usado por el proyecto.

Es una recomendación de producto, no una adopción. La integración permanente
requiere aprobación humana y una subfase separada.

## Fuentes oficiales y versión fijada

La evaluación se apoya en la documentación primaria de Protomaps:

- [Basemap Downloads](https://docs.protomaps.com/basemaps/downloads): el
  basemap es contexto vectorial derivado de OpenStreetMap, se distribuye como
  Produced Work ODbL y exige atribución OSM. La documentación desaconseja
  hotlinking y remite a `pmtiles extract` para recortes.
- [pmtiles CLI](https://docs.protomaps.com/pmtiles/cli): `extract` acepta
  Polygon, MultiPolygon, Feature o FeatureCollection, fuente HTTP remota y
  `--maxzoom`; `verify` valida orden y cabecera.
- [Basemaps for MapLibre](https://docs.protomaps.com/basemaps/maplibre): los
  textos requieren glyphs; los sprites solo son necesarios para townspots,
  shields y POI que este subset no utiliza.
- [Licencia de basemaps](https://github.com/protomaps/basemaps/blob/main/LICENSE.md)
  y [basemaps-assets](https://github.com/protomaps/basemaps-assets): código
  BSD-3-Clause, estilo visual CC0, tiles como Produced Work ODbL, fuentes Noto
  bajo SIL Open Font License y sprites bajo MIT cuando se usan.

Identidad fijada:

| Elemento | Identidad |
|---|---|
| Build fuente | `20260902.pmtiles` |
| URL fuente | `https://build.protomaps.com/20260902.pmtiles` |
| Tamaño planet publicado | 137.702.823.565 B; nunca descargado completo |
| Hash planet publicado | BLAKE3 `0f7860f75647583b49cd22fc344298023b501892d8d8f2c8466337072d0c1062` |
| MD5 publicado | base64 `2g4/86Ho38Zp2gZd7e9N1Q==` |
| Schema/tileset | Protomaps Basemap `4.15.2` |
| OSM replication time | `2026-09-02T04:00:00Z` |
| Planetiler | `0.10.2`, git `0e5588c4a6e8c29a270a33afe8df62027d889604` |
| Style package inspeccionado | `@protomaps/basemaps@5.7.2`, gitHead `3ea8293a28131c3dc63f1bb20827bdb8a76df06f` |
| PMTiles CLI | `1.31.2`, commit `a3e495…`; binario oficial SHA-256 `3ed7…` registrado en ES-3 |

El paquete de estilo se inspeccionó como referencia de schema y licencia. El
runtime del experimento usa un subset propio de 11 capas y no carga ese paquete.

## Región y extracción

La máscara es el FeatureCollection BDLJE actual ya aceptado en C2A1:

- `data/derived/spain/es4c2a/ccaa.geojson`;
- 19 unidades lógicas: península, Illes Balears, Canarias, Ceuta y Melilla
  incluidas como polígonos/multipartes reales, sin una bbox atlántica;
- 8.211.747 B;
- SHA-256 `86fa15441605a0a95784fde45d1feffb302b6defc79b44665a64e02e5805535d`.

Comando reproducible empleado:

```bash
data/derived/spain/es3/tools/pmtiles-bin/pmtiles extract \
  https://build.protomaps.com/20260902.pmtiles \
  build/es4e3c2-basemap/protomaps-spain-z12.pmtiles \
  --region=data/derived/spain/es4c2a/ccaa.geojson \
  --maxzoom=12 \
  --download-threads=4
```

El dry-run previo contabilizó 13.228 tiles, 79 peticiones, unos 308 MB de
transferencia, 293 MB estimados de salida, 10,831 s y 68.148 KiB de RSS máxima.
La duración de la extracción efectiva no quedó preservada por el rollover del
ejecutor; no se repitieron 293 MB solo para reconstruir esa métrica. Esta es la
única laguna de telemetría de adquisición y no afecta a identidad, integridad,
tamaño ni resultado visual.

Resultado conservado localmente e ignorado por Git:

- `build/es4e3c2-basemap/protomaps-spain-z12.pmtiles`;
- 293.324.998 B;
- SHA-256 `72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729`;
- MVT gzip, zoom 0–12;
- bounds `[-18.1611787, 27.6377231, 4.327784, 43.7923795]`;
- `pmtiles verify`: PASS.

No se descargó el planet y no se extrajo z13.

## Inventario completo del candidato

| Asset | Bytes físicos | SHA-256 / nota |
|---|---:|---|
| PMTiles z12 | 293.324.998 | `72bb270f…eb729` |
| `Noto Sans Regular/0-255.pbf` | 76.044 | `62c6d49b…b397` |
| `OFL.txt` | 4.374 | `7713cfc8…e7c2d` |
| subset de estilo/harness | 6.560 | `6a6e64c…f262e` |
| sprites | 0 | no se usan iconos, POI ni shields |
| **Total autoalojado** | **293.411.976** | mismo origen previsto |

Solo se solicitó el rango `0-255` del fontstack `Noto Sans Regular` en todos
los casos. Contiene los caracteres necesarios observados para castellano,
valenciano/catalán, gallego y euskera. No se empaquetaron fontstacks ni rangos
mundiales innecesarios. El archivo OFL debe acompañar al glyph si se adopta.

## Estilo y semántica cartográfica

El subset incluye fondo terrestre, cobertura/uso natural muy tenue, agua,
ríos desde z7, carreteras principales desde z5, secundarias desde z9, nombres
de regiones/localidades y nombres de vías principales desde z9. Excluye POI,
edificios, comercios, símbolos turísticos y shields.

Estrategia de nombres: `name` local documentado primero, después `name:es` y
`name:en`. Así aparecen formas locales/combinadas como `Elx/Elche` sin
reemplazar los nombres canónicos BDLJE de los controles administrativos.

Orden comprobado:

1. contexto Protomaps;
2. límites y selección BDLJE/IGN;
3. geometrías de incendio;
4. selección/highlight.

BDLJE sigue siendo la autoridad territorial. Protomaps/OSM solo aporta
contexto visual y no modifica límites, IDs, filtros ni bounds.

## Revisión visual humana

Capturas locales comparables, ignoradas por Git, están en
`build/es4e3c2-basemap/comparisons/` y conservan la misma viewport, periodo y
capas de incendio para cada par.

| Criterio | Protomaps z12 frente a BDLJE-only | Evidencia |
|---|---|---|
| Orientación geográfica | BETTER | costa, países/ciudades próximas y agua hacen legible España y Canarias |
| Utilidad de topónimos | BETTER | localidades visibles en España, GVA, Elx, Ourense y Cangas |
| Contexto viario | BETTER | red principal nacional y vías locales suficientes al sobrezoom |
| Contraste del fuego | SIMILAR | el rojo/verde continúa por encima; el fondo es claro y desaturado |
| Ruido visual | SIMILAR | hay más contexto, pero sin POI, edificios, shields ni iconos |
| Contexto municipal | BETTER | Elx y Cangas dejan de ser polígonos aislados sobre fondo vacío |
| Lectura móvil | BETTER | costa, topónimos y vías siguen legibles a 390×844 sin tapar el mapa |

Hallazgos por caso:

- **España:** BDLJE-only comunica límites e incendios, pero el territorio flota
  sobre un fondo vacío. Protomaps aporta Iberia, Europa, norte de África,
  ciudades, agua y red principal sin perder el protagonismo de los perímetros.
- **GVA 1995:** ICV, ESFire30 y el límite seleccionado siguen distinguibles;
  carreteras y topónimos explican mejor dónde están los perímetros.
- **Elx:** `Elx/Elche`, Crevillent, Santa Pola, Aspe, Dolores, costa, agua y
  carreteras dan contexto municipal suficiente con z12 sobrezoomed.
- **Ourense:** la red rural y localidades ayudan a leer una escena densa sin
  convertir el mapa base en protagonista.
- **Cangas del Narcea:** carreteras, río, cubierta tenue y el topónimo aportan
  orientación en un caso rural/montañoso; z12 es suficiente para la finalidad
  del Atlas, aunque no pretende navegación calle a calle.
- **Canarias:** nombres de islas y localidades, costa y agua eliminan la
  sensación de islas sin contexto. La falta de cobertura ESFire30 no cambia.

## Red y navegador

El harness construye dos frontends temporales —BDLJE-only y candidato— y
sirve el PMTiles con HTTP Range. No toca el runtime permanente. Se ejecutaron
15 escenarios dirigidos y dos recorridos secuenciales en perfiles Chromium
limpios. Resultado global: PASS, 0 errores browser/runtime y 0 descargas
completas.

Todos los requests al PMTiles candidato fueron `206`; todos los assets fueron
same-origin y `EXTERNAL_RUNTIME_DOMAINS = []`.

### Cargas frías independientes

| Escenario | Range requests | PMTiles B | Glyph requests/B | Tiempo diagnóstico | Heap aprox. |
|---|---:|---:|---:|---:|---:|
| España | 6 | 263.919 | 1 / 76.044 | 4.211 ms | 61 MB aprox. |
| Galicia | 10 | 582.568 | 1 / 76.044 | 5.253 ms | diagnóstico variable |
| Ourense | 12 | 949.273 | 1 / 76.044 | 5.279 ms | diagnóstico variable |
| GVA 1995 | 10 | 520.989 | 1 / 76.044 | 4.755 ms | diagnóstico variable |
| Elx | 16 | 862.700 | 1 / 76.044 | 5.079 ms | diagnóstico variable |
| Cangas del Narcea | 14 | 1.141.082 | 1 / 76.044 | 6.462 ms | diagnóstico variable |
| Canarias | 9 | 304.755 | 1 / 76.044 | 4.314 ms | diagnóstico variable |

Los tiempos incluyen frontend, datos de incendio/territorio, composición y
espera estable; no son un SLA ni aíslan solo el basemap.

### Navegación en una misma sesión

| Recorrido/etapa | Range adicionales | PMTiles B adicionales | Glyph B adicionales |
|---|---:|---:|---:|
| España inicial | 6 | 263.919 | 76.044 |
| España → Galicia | 4 | 318.649 | 0 |
| Galicia → Ourense | 6 | 685.354 | 0 |
| España inicial | 6 | 263.919 | 76.044 |
| España → País Valencià | 4 | 257.070 | 0 |
| País Valencià → Alacant | 6 | 388.096 | 0 |
| Alacant → Elx | 4 | 210.685 | 0 |

La reutilización es visible: el glyph se solicita una vez por sesión; PMTiles
solo añade rangos correspondientes a los nuevos tiles. España→Galicia→Ourense
acumula 1.267.922 B de PMTiles; España→GVA→Alacant→Elx, 1.119.770 B. No se
leyeron los 293 MB completos.

En 390×844, España transfirió 263.919 B de PMTiles y Elx frío 849.533 B, ambos
con un glyph de 76.044 B, mapa inmediato, labels legibles, 0 errores y 0 full
downloads. Es emulación de viewport, no CPU/red móvil.

## Tamaño del sitio y margen Pages

Se reconstruyó un artifact E3 actual para evitar reutilizar el valor D4A. El
builder actual incorpora frontend, highlights y el resto de assets, pero aún
no copia físicamente `national-ux-summary-v1`; por ello se sumó ese árbol una
sola vez de forma explícita.

| Componente | Bytes | % del total z12 |
|---|---:|---:|
| Artifact E3 actual sin summary | 500.933.134 | — |
| `national-ux-summary-v1` | 17.255.181 | — |
| **CURRENT_E3_PRE_BASEMAP_PROJECTED_SITE_BYTES** | **518.188.315** | **63,847724 %** |
| PMTiles Protomaps z12 | 293.324.998 | 36,141559 % |
| glyph | 76.044 | 0,009370 % |
| licencia de fuente | 4.374 | 0,000539 % |
| estilo/helper | 6.560 | 0,000808 % |
| sprites/other | 0 | 0 % |
| **PROJECTED_SITE_BYTES_WITH_Z12** | **811.600.291** | **100 %** |
| **PAGES_BYTES_REMAINING** | **188.399.709** | **18,839971 % del límite** |

La cuenta es física/raw, no gzip. GitHub documenta actualmente un sitio
publicado máximo de 1 GB, repositorio fuente recomendado de 1 GB, despliegue
de hasta 10 minutos y límite blando de 100 GB/mes en
[GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
El margen permite esta adopción, pero queda ajustado para crecimientos grandes:
el PMTiles pasa a ser el 36,14 % del sitio y cada despliegue movería ~293 MB
adicionales. La carga del navegador sigue siendo por rangos, no por tamaño
total. No se afirma que Pages sea gratis o ilimitado.

Z13 no se probó: sus bytes, total proyectado y margen son `NOT_TESTED` /
`NOT_APPLICABLE`. La documentación indica que cada zoom adicional aproxima un
doble de tamaño; no se usa esa aproximación como cifra de decisión porque z12
ya resuelve la necesidad visual.

## Licencias, atribución y privacidad

Contrato si se adopta:

- tiles Protomaps derivados de OSM: Produced Work ODbL; atribución visible a
  OpenStreetMap obligatoria;
- código `@protomaps/basemaps`: BSD-3-Clause; el subset propio no carga el
  paquete en runtime;
- diseño visual Protomaps de referencia: CC0;
- glyph Noto: SIL Open Font License, con `OFL.txt` distribuido;
- sprites: no usados;
- límites BDLJE/IGN: conserva CC-BY 4.0 y su atribución actual.

Texto propuesto, visible en el mapa:

> Protomaps · © OpenStreetMap contributors · Obra derivada de BDLJE CC-BY 4.0 ign.es

Los enlaces deben apuntar respectivamente a Protomaps, copyright de OSM e
IGN. `Protomaps` es atribución recomendada del producto/style; `© OpenStreetMap
contributors` es la exigida por los datos. El experimento confirma cero
dominios runtime externos: PMTiles, glyph, estilo y límites pueden servirse
same-origin, sin API key ni telemetría de proveedor.

## Operación y actualización

Adoptar z12 implicaría:

- versionar en el manifest el build fuente, schema, máscara y hashes;
- incorporar un PMTiles inmutable de 293.324.998 B al artifact Pages;
- servirlo con Range same-origin, igual que ESFire30;
- incluir glyph y OFL; ningún sprite;
- asumir más tiempo/tráfico de deploy y consumo de la cuota blanda de Pages;
- mantener una política manual conservadora: revisar/actualizar el snapshot
  como máximo de forma anual o cuando cambios relevantes de carreteras y
  topónimos lo justifiquen, nunca seguir `latest` ni automatizar builds diarios.

El snapshot es contexto actual; no representa la cartografía histórica de la
fecha de cada incendio.

## Matriz de decisión

| Opción | Calidad visual | Self-hosted | Runtime externo | Raw B | Total Pages proyectado | Privacidad | Coste | Licencia | Riesgo operativo | Recomendación |
|---|---|---|---|---:|---:|---|---|---|---|---|
| BDLJE_ONLY | insuficiente para contexto humano | sí | no | 0 nuevos | 518.188.315 | alta | ancho de banda actual | BDLJE CC-BY 4.0 | bajo | no resuelve el gap |
| PROTOMAPS_Z12 | suficiente | sí | no | 293.411.976 | 811.600.291 | alta | sin API billing; tamaño/bandwidth Pages | ODbL Produced Work + OSM; BSD/CC0; OFL | medio por tamaño/update | **ADOPT_PROTOMAPS_Z12**, tras aprobación |
| OpenFreeMap | no evaluada | no | sí | no medido | no medido | menor | servicio externo sin SLA contractual del proyecto | pendiente de futura revisión | dependencia runtime | fallback externo |
| MapTiler | no evaluada | gestionado | sí | no medido | no medido | depende del servicio | límites/precio de servicio | pendiente de futura revisión | cuenta/API key | fallback gestionado |

No hay fila z13 porque no se extrajo ni probó.

## Limitaciones y siguiente fase

- La duración del extract real no se conservó; sí se conservaron comando,
  fuente, máscara, hashes, tamaño y `verify`.
- Las métricas son locales y diagnósticas; no validan aún el artifact Pages
  enriquecido ni su ancho de banda remoto.
- El fontstack mínimo se validó en los escenarios españoles dirigidos, no en
  todos los nombres Unicode del dataset mundial.
- Quedan 188.399.709 B de margen conservador; datasets futuros grandes deben
  reevaluarlo.
- No se ha cambiado `src/national`, staging, producción ni D5.

Tras aprobación humana, la siguiente fase exacta recomendada es
`ES-4E3C2_BASEMAP_INTEGRATION`: convertir este candidato validado en asset
versionado del artifact, integrar el subset/atribución de forma permanente y
revalidar tamaño, Range y regresiones. No se inicia aquí.
