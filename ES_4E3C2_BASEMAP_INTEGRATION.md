# ES-4E3C2_BASEMAP_INTEGRATION — integración local productiva Protomaps z12

## Resultado

`BASEMAP_INTEGRATION_STATUS = PASS` y
`BASEMAP_STATUS = PASS_PROTOMAPS_Z12`. El candidato cerrado en la decisión
E3C2 se ha incorporado al runtime nacional local como contexto cartográfico
same-origin. No se ha reextraído, desplegado ni incorporado el PMTiles a Git.
El release candidate de producto continúa siendo `false` y D5 permanece
pausado.

Protomaps no es una fuente de incendios. EGIF, ESFire30, ICV y EFFIS conservan
sus identidades y contratos. BDLJE/IGN sigue siendo la autoridad para límites,
jerarquía, bounds, navegación y selección administrativa.

## Identidad y adquisición reproducible

| Elemento | Valor |
|---|---|
| Build fuente | `20260902.pmtiles` |
| Protomaps Basemap schema | `4.15.2` |
| Style de referencia | `@protomaps/basemaps@5.7.2` |
| BLAKE3 publicado | `0f7860f75647583b49cd22fc344298023b501892d8d8f2c8466337072d0c1062` |
| SHA-256 de región | `86fa15441605a0a95784fde45d1feffb302b6defc79b44665a64e02e5805535d` |
| Maxzoom | 12 |
| PMTiles local | `build/es4e3c2-basemap/protomaps-spain-z12.pmtiles` |
| PMTiles bytes | **293.324.998** |
| PMTiles SHA-256 | `72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729` |
| `pmtiles verify` | PASS |

El contrato canónico está en
`config/national-basemap-protomaps-20260902-z12.json`. Incluye la orden exacta
de extracción, pero ninguna prueba rutinaria descarga o extrae 293 MB. El
helper `scripts/basemaps/prepare_protomaps_basemap.py --check` verifica los
inputs locales; con `--output DIR` prepara un bundle, sin acceder a red.

Path futuro inmutable del PMTiles:

```text
data/basemap/protomaps/20260902-z12/72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729/basemap.pmtiles
```

La política de actualización es revisión manual, como máximo anual o cuando
exista una razón cartográfica relevante. El snapshot no se sigue mediante
`latest` ni representa cartografía histórica del año del incendio.

## Glyph, estilo y recursos

Solo se entrega `Noto Sans Regular/0-255.pbf`: 76.044 B, SHA-256
`62c6d49b15fa836eb6aa45e259c7ca6762f44b011b09e47776efbe4a6db1b397`.
`OFL.txt` ocupa 4.374 B y tiene SHA-256
`7713cfc8e3c36d5ec4aa3d6cffe7500a1b3310f8a86d914b8ea09c2a9dee7c2d`.
Los nueve smokes limpios hicieron una petición de glyph, recibieron 200 y
76.044 B, sin 404. Se observaron correctamente nombres con tildes y grafías
locales, como `Alacant / Alicante`, `València`, `A Fonsagrada` y
`el Fondó de les Neus / Hondón de las Nieves`.

No hay sprites, POI, iconos, shields, comercios ni edificios. El subset
`ATLAS_CONTEXT_STYLE` contiene once capas pequeñas: tierra, cubierta natural
tenue, agua/ríos, carreteras principales y secundarias, regiones, localidades
y nombres de vías. El fondo es claro y desaturado para mantener el contraste
de ICV, ESFire30 y EFFIS.

## Integración y orden de capas

`src/national/basemap-context.mjs` reutiliza el mismo protocolo PMTiles ya
registrado por el runtime. `asset-config.mjs` y el frontend generado resuelven
PMTiles, glyph y manifest mediante el base path actual; no contienen paths de
usuario, host de staging ni URL de producción.

El orden comprobado en los nueve escenarios es:

1. contexto Protomaps;
2. rellenos y líneas administrativas BDLJE;
3. territorio seleccionado BDLJE;
4. geometrías ICV / ESFire30 / EFFIS;
5. geometría de incendio seleccionada.

Los rellenos BDLJE se atenúan cuando el contexto está disponible, pero sus
geometrías, IDs, filtros, clics y bounds no cambian. Protomaps figura en el
registro como `cartographic_context`, con `wildfire_source = false`, y no se
añade a la leyenda de fuentes de incendios.

## Fallo y degradación

La inicialización del contexto es independiente del shell. Un error de su
PMTiles o glyph elimina únicamente sus once capas, restaura las opacidades
BDLJE y deja `fallback_bdlje_only`. El smoke con el asset omitido produjo el
404 esperado y verificó:

- BDLJE disponible;
- ESFire30 disponible mediante Range;
- shell, resumen, histograma, filtros y destacados operativos;
- cero errores generales del runtime y cero errores atribuidos a ESFire30.

El fallo se conserva en `window.__atlasBasemapContext.errors` para diagnóstico,
sin mostrar un error técnico dominante al usuario.

## Atribución, licencias y privacidad

La atribución visible del mapa es:

> Protomaps · © OpenStreetMap contributors · Obra derivada de BDLJE CC-BY 4.0 ign.es

Los tres elementos tienen enlaces accesibles a Protomaps, copyright de OSM e
IGN. Las licencias permanecen separadas:

- datos OpenStreetMap: ODbL 1.0;
- código Protomaps: BSD-3-Clause;
- diseño visual de referencia: CC0;
- Noto: SIL OFL 1.1;
- BDLJE: CC-BY 4.0.

`API_KEYS_REQUIRED = false` y `EXTERNAL_RUNTIME_DOMAINS = []`. Los enlaces de
atribución solo navegan cuando el usuario los activa; no son dependencias de
datos ni telemetría.

## Network y rendimiento diagnóstico

Cada fila es una sesión local limpia. Los bytes de Protomaps y ESFire30 se
registran por separado; no son una única capa. Los tiempos incluyen shell,
datos, composición y espera de estabilidad, y el heap es diagnóstico variable.

| Escenario | Protomaps Range / B | ESFire30 Range / B | Glyph | Estable (ms) | Heap aprox. B |
|---|---:|---:|---:|---:|---:|
| España | 6 / 263.919 | 6 / 526.207 | 1 / 76.044 | 4.426 | 66.351.886 |
| Galicia | 10 / 582.568 | 10 / 2.343.832 | 1 / 76.044 | 5.530 | 192.552.017 |
| Ourense | 12 / 949.273 | 12 / 2.116.544 | 1 / 76.044 | 5.812 | 193.059.283 |
| Cangas del Narcea | 14 / 1.141.082 | 14 / 3.135.688 | 1 / 76.044 | 6.313 | 109.024.023 |
| País Valencià 1995 | 10 / 520.989 | 10 / 1.507.261 | 1 / 76.044 | 7.287 | 154.226.582 |
| Elx 1993–2002 | 16 / 862.700 | 16 / 663.763 | 1 / 76.044 | 8.223 | 124.072.711 |
| Canarias | 9 / 304.755 | 6 / 526.207 | 1 / 76.044 | 4.868 | 145.267.860 |
| móvil España | 6 / 263.919 | 6 / 526.207 | 1 / 76.044 | 5.330 | 214.999.722 |
| móvil Elx | 14 / 849.533 | 14 / 756.842 | 1 / 76.044 | 6.723 | 145.349.358 |

Todos los requests funcionales de ambos PMTiles fueron HTTP 206. Hubo cero
descargas completas, cero errores de consola/runtime y cero dominios externos.
Las cifras son smokes locales, no presupuestos ni benchmarks comparables entre
escenarios.

## Validación de producto

- España recupera costa, agua, red principal y topónimos; BDLJE y los
  perímetros permanecen por encima.
- Galicia y Ourense conservan resumen, 59 barras de histograma, filtros y
  destacados, con localidades y contexto viario rural.
- Cangas mantiene el filtro municipal ya aprobado (2.610 IDs en su contrato),
  sobrezoom z12 útil, mapa estable y sin hang/crash.
- País Valencià 1995 mostró simultáneamente Protomaps, BDLJE, ESFire30 e ICV;
  el filtro ICV ≥500 ha y la ficha destacada ICV funcionaron.
- Elx 1993–2002 preservó sus 6 IDs auditados, contexto urbano/viario y selección
  estable de `esfire30:v1:1993:777`.
- Canarias mostró contexto cartográfico y BDLJE mientras ESFire30 mantuvo su
  estado de ausencia de cobertura; cartografía disponible no significa datos
  de incendio disponibles.
- En 390×844 el mapa siguió inmediatamente tras la cabecera; pan, zoom,
  etiquetas, tarjetas, filtros y paneles conservaron su estructura.
- El basemap no entra en el permalink. Serializer nacional y compatibilidad v1
  no cambian.

### Matriz de aceptación visual

| Escenario | Contexto | Labels | Carreteras | Contraste fuego | BDLJE | PASS |
|---|---|---|---|---|---|---|
| España | costa/agua nacional | 35 | principales | sí | sí | PASS |
| Galicia | regional/rural | 65 | sí | sí | sí | PASS |
| Ourense | rural | 26 | sí | sí | sí | PASS |
| Cangas | montaña/rural | 2 útiles | sí, z12 sobrezoom | sí | sí | PASS |
| GVA 1995 | regional | 9 | sí | ICV y ESFire30 legibles | sí | PASS |
| Elx | urbano/territorial | 14 | sí | sí | municipio seleccionado | PASS |
| Canarias | insular | 11 | sí | no aplica a ESFire30 | sí | PASS |
| móvil España/Elx | inmediato | 11 / 9 | sí | sí | sí | PASS |

## Build y tamaño proyectado

El frontend ligero incorpora referencias/configuración y
`basemap-context.mjs`, pero declara `large_assets_included = false`. El assembly
completo futuro verifica y copia PMTiles, glyph, OFL y manifest al path
inmutable; también incorpora el resumen UX ya requerido. No se ha generado un
artifact Pages completo en esta fase.

Se recalculó con la misma contabilidad física/raw de la decisión anterior:

| Componente | Bytes |
|---|---:|
| Artifact E3 reconstruido de referencia | 500.933.134 |
| Delta frontend productivo (1.462.555 − 1.450.252) | 12.303 |
| `national-ux-summary-v1` | 17.255.181 |
| PMTiles Protomaps | 293.324.998 |
| Glyph | 76.044 |
| OFL | 4.374 |
| Manifest productivo | 2.470 |
| **CURRENT_PRODUCT_PROJECTED_SITE_BYTES** | **811.608.504** |
| **PAGES_BYTES_REMAINING** | **188.391.496** |

El límite conservador usado es 1.000.000.000 B y no gzip. Por tanto
`PAGES_CAPACITY_STATUS = LIMITED_BUT_ACCEPTABLE`: no bloquea la primera
publicación, pero cualquier asset futuro grande debe medirse antes de entrar.

## Comparación acumulada de producto

| Versión | Contexto/mapa | Topónimos/orientación | Funciones humanas | Ruido / protagonismo del fuego |
|---|---|---|---|---|
| GVA | buen contexto regional | claro en ámbito valenciano | referencia de producto | bajo / alto |
| D4B | BDLJE técnico | insuficiente | runtime técnico completo | bajo / alto |
| E3A | igual a D4B | insuficiente | shell humano | bajo / alto |
| E3B2 | igual a E3A | insuficiente | resumen + histograma | bajo / alto |
| E3C1 | igual a E3B2 | insuficiente | filtros + fichas humanas | bajo / alto |
| E3C2 BDLJE | límites y costa administrativa | aún insuficiente | destacados + leyenda | muy bajo / alto |
| E3C2 + Protomaps integrado | contexto nacional, insular, urbano y rural suficiente | suficiente con z12 | conserva todo E3 | controlado / alto |

## Gaps y siguiente fase

- Falta la aceptación local integral de producto E3D; esta fase solo valida la
  integración cartográfica dirigida.
- No se ha construido ni desplegado el artifact completo con el basemap.
- La validación Range es local; hosting futuro queda fuera de alcance.
- Solo se incluye el rango glyph 0–255 validado, no una cobertura Unicode
  universal.
- El brush del histograma sigue `DEFERRED_P1`.
- Las causas EGIF siguen `DEFERRED_PENDING_ONTOLOGY`.
- No hay relieve, z13, sprites, POI ni otros fontstacks.

`TECHNICAL_RUNTIME_REGRESSION = false`, `MAP_CONTEXT_STATUS = PASS`,
`PRODUCT_RELEASE_CANDIDATE = false` y
`D5_STATUS = PAUSED_FOR_PRODUCT_RECONCILIATION`.

La siguiente fase exacta es
`ES-4E3D_NATIONAL_PRODUCT_LOCAL_ACCEPTANCE`. No se inicia aquí.
