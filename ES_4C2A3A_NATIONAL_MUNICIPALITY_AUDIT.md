# ES-4C2A3A — Auditoría y diseño de municipios nacionales actuales

## Estado y alcance

Esta subfase audita el inventario municipal actual de BDLJE y diez muestras
geométricas provinciales. No integra municipios en el runtime, no calcula
relaciones ESFire30→municipio y no altera la resolución municipal EGIF de
ES-4B3. La descarga de la geometría nacional completa queda preparada para
ejecución externa, reanudable e idempotente.

## Fuente y procedencia

- Organismo y producto: IGN/CNIG, BDLJE — Límites y Unidades Administrativas
  Actuales, colección OGC API `administrativeunit`, nivel `Municipio`.
- Consulta de inventario: `nationallevelname=Municipio`, `skipGeometry=true`.
- Fecha de la consulta municipal: 2026-08-29. El directorio local reutiliza
  el prefijo de snapshot `ign-ogc-2026-08-26` de las capas territoriales
  anteriores, pero el agregado conserva la fecha real de obtención.
- Release BDLJE de referencia ya documentada: shapefile 2026-07-28; GML
  2026-08-10. Catálogo de fuente SHA-256:
  `6871d31a83b6253ee2ebb75aea9ba514db5a8b71c31ed6783ad9182ef1ac903a`.
- CRS: BDLJE usa ETRS89 geográfico en Península, Baleares, Ceuta y Melilla y
  REGCAN95 geográfico en Canarias; la respuesta GeoJSON OGC se consume como
  CRS84/WGS84 para auditoría y futura entrega web.
- Licencia y atribución: CC-BY 4.0; «Obra derivada de BDLJE CC-BY 4.0
  ign.es».

Las nueve páginas de inventario ocupan 2.564.156 B y su lista ordenada de
checksums SHA-256 tiene huella
`41638d035773574f214ce769fb663dfa6f81979d4089027ecf3af628e9a33871`.
Las diez muestras geométricas ocupan 58.364.203 B; su lista de checksums queda
registrada en el agregado (SHA-256 de lista
`5b41f69c84176242a9eceeeb75d9c25d368e0aadf141b7449b03333f9d4ead30`).

El agregado reproducible está en
`data/audit/territories/es4c2a3a_municipalities.json`. Conserva las páginas
locales, sus checksums y las muestras de geometría; los ficheros raw quedan
fuera de Git.

## Inventario y crosswalk ES-2

BDLJE devuelve **8.213** features al solicitar el nivel `Municipio`. El
crosswalk usa exclusivamente el código documentado: de `nationalcode`
`34CCPPMMMMM` se extrae `MMMMM` y se enlaza con `ES:MUN:MMMMM`; no hay
matching por nombre ni inferencia espacial.

| Clasificación | Features |
| --- | ---: |
| `MATCHED_CURRENT` con ES-2 | 8.132 |
| `NON_MUNICIPAL_UNIT` | 81 |
| `UNMATCHED_SOURCE` | 0 |
| `AMBIGUOUS` | 0 |

Los 81 adicionales llevan códigos 53xxx y son comunidades, facerías,
parzonerías u otras unidades no municipales que el servicio expone bajo este
nivel. Por ejemplo, `Cuarto del Madroño` y diversas comunidades de Burgos.
No se crean municipios ES-2 para ellas. Los 8.132 municipios canónicos de
`data/territories/spain/territories-2026-01-01.json` enlazan sin discrepancias
de jerarquía municipio → provincia → CCAA.

Ceuta (`ES:MUN:51001`) y Melilla (`ES:MUN:52001`) se conservan como municipios
canónicos según ES-2, bajo ciudades autónomas; no se crean municipios
ficticios ni se transforman conceptualmente en provincias.

## Muestras geométricas

Se descargaron y auditaron solo diez provincias: Álava (53 features), Alacant
(141), Illes Balears (67), Burgos (414), Girona (221), Ourense (92), Las
Palmas (34), Santa Cruz de Tenerife (54), Sevilla (106) y València (266):
**1.448 features** en total. Todas son Polygon/MultiPolygon válidos, sin
geometrías null ni inválidas. Se preservan las multipartes: 13, 15, 32, 30,
23, 2, 17, 42, 6 y 35 respectivamente.

Controles: Llívia (`34091717094`), Condado de Treviño (`34070909109`), La
Puebla de Arganzón (`34070909276`) y Ademuz, municipio del Rincón de Ademuz
(`34104646001`), están presentes y son MultiPolygon válidos. Las muestras
canarias preservan islas y multipartes; no se sustituyen por geometría de
ESFire30, que no cubre Canarias.

## Tamaño y simplificación

Las diez muestras sin simplificar suman 36.272.337 B raw y 11.149.889 B gzip.
La media por feature permite estimar, **no medir**, para las 8.132 features:

| Tolerancia topológica en EPSG:3857 | Raw estimado | Gzip estimado |
| --- | ---: | ---: |
| 0 m | 372,7 MB | 112,3 MB |
| 5 m | 120,3 MB | 38,6 MB |
| 10 m | 85,8 MB | 27,7 MB |

Las geometrías y multipartes de las muestras conservaron validez a 5 y 10 m,
pero no se recomienda simplificación global todavía: Llocnou de la Corona
(València, ~21.094 m²) llega a 2,2117 % de error de área tanto a 5 como a
10 m. La siguiente fase deberá medir el nacional completo y validar por shard;
5 m es solo candidato, no una decisión de entrega.

## Diseño de entrega recomendado

No se recomienda un GeoJSON municipal nacional único: incluso la estimación
sin simplificar es demasiado grande para una carga inicial. Se recomienda:

1. catálogo ligero nacional (`municipality_id`, `province_id`, `official_name`,
   `bounds`, `asset_id`);
2. geometría municipal actual en GeoJSON por provincia, bajo demanda;
3. PMTiles administrativos solo si en el futuro hace falta una vista municipal
   nacional continua.

El catálogo sin bounds, medido sobre los 8.132 ES-2, ocupa 1.192.246 B raw y
85.235 B gzip. Los bounds precisos de municipio y tamaños nacionales reales
requieren primero la descarga completa. Los bounds describirán siempre el
límite administrativo **actual**, por lo que son aptos para `fitBounds` pero
no prueban geometría histórica.

## Semántica histórica y fuentes

`current_municipality_geometry != historical_municipality_geometry` salvo
fuente histórica documentada. En el futuro, filtrar `ES:MUN:xxxxx` en EGIF
significará: «partes cuyo municipio administrativo pudo enlazarse
documentalmente con este municipio canónico actual». No significará que todo
evento ocurriera físicamente dentro del polígono actual. Los 71.490 registros
EGIF con municipio no resuelto se mantienen como null: BDLJE no se usa para
resolverlos.

Las relaciones ESFire30→municipio no se calculan en esta subfase. A diferencia
de CCAA/provincia, una geometría puede intersectar muchos municipios; no debe
usarse un diseño fijo `mun_1..mun_3`. Se evaluarán más adelante un índice
inverso municipal, teselas locales o consultas espaciales con geometría ya
cargada.

## Proceso nacional pendiente

No se ejecutó la descarga nacional completa. Para adquirirla de forma
reanudable fuera de Codex:

```bash
python3 scripts/territories/audit_municipalities.py --all --resume
python3 scripts/territories/audit_municipalities.py --all --check
```

El primer comando descarga páginas de 100 features, guarda checksum y estado
por página y ensambla el GeoJSON nacional local. No repite páginas completas
con `--resume`; el segundo verifica páginas, ensamblado y el inventario de
8.213 features.

La siguiente subfase recomendada es
`ES-4C2A3B_MUNICIPAL_GEOMETRY_FULL_AUDIT`: reconciliar el fichero nacional,
medir tamaño/bounds exactos y decidir shards antes de cualquier runtime.
