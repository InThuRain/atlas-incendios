# ES-3 — Prototipo nacional de entrega geométrica ESFire30

Fecha de medición: 27/08/2026. Estado: laboratorio terminado, sin integración,
commit final ni publicación. Los resultados reproducibles están en
`benchmarks/es3/results.json`; los assets pesados se limitan a
`data/raw/`/`data/derived/spain/es3/`, ambos ignorados.

## Alcance

El benchmark usa el snapshot exacto ESFire30 v1 (DOI
`10.5281/zenodo.18449006`): 119.498 polígonos entre 1985 y 2021. No modifica
el visor del País Valencià, `public-data-v5`, workflows, IDs ni permalinks.
Las pruebas son Chrome headless sin mapa base: miden datos y render, no red
móvil real.

## Límites IGN y CRS

Se descargaron desde la API OGC Features oficial IGN el 26/08/2026, en CRS84
de almacenamiento, los niveles `Comunidad autónoma` (20 features, 149 MB,
SHA-256 `48d1cd7b…417bf757`) y `Provincia` (53, 178 MB,
`58e4f68f…2083290`). Son raw diagnósticos, no límites publicados. El producto
IGN/CNIG mantiene ETRS89 en península/Baleares/Ceuta/Melilla y REGCAN95 en
Canarias; el cruce diagnóstico transforma el límite CRS84 al CRS fuente.

El CRS nacional ESFire30 confirmado es **EPSG:23030, ED50 / UTM 30N**. Se usa
la operación `Inverse of UTM zone 30N + ED50 to WGS 84 (41) + axis order
change (2D)`, precisión declarada 1 m, con PROJ 9.2.1/pyproj 3.5.0 y la rejilla
IGN auditada. Los puntos de control oeste/centro/este tienen un error de ida y
vuelta menor de `5e-10 m`.

El rango EPSG:23030 del snapshot es x −13.459,36 a 1.019.195,59 m. Hay eastings
negativos al oeste y >1.000.000 al este; toda la colección está armonizada en
la malla declarada. Aplicar EPSG:23029/23031 por feature según longitud sería
incorrecto. Las 119.498 features intersectan CCAA y provincia IGN: 1.342
cruzan CCAA, 2.364 provincias. No aparecen features asignables a Baleares,
Canarias, Ceuta o Melilla: observación del snapshot, no inferencia de cobertura.

## Reconciliación y simplificación

| Métrica | Resultado |
|---|---:|
| Features | 119.498 |
| Tipos | 119.249 `Polygon`, 249 `MultiPolygon` |
| Vértices fuente | 6.196.709 |
| overview 100 m | 1.287.275 (−79,226 %) |
| vacías/colapsadas overview | 0 |

La muestra sistemática de 1.195 geometrías no tiene inválidas antes/después.
Pero 100 m tiene p95 de error relativo de área 25,0 % (máx. 60,66 %); 30 m p95
6,34 %; 10 m p95 0 % en la muestra (máx. 9,09 %). Por tanto 100 m es solo
overview/tesela; el detalle debe usar 10–30 m o geometría completa. Ninguna
simplificación reemplaza la fuente ni el lookup de ficha.

## GeoJSON

El control monolítico (atributos mínimos: `geometry_id`, fuente, año, área)
pesa 74,11 MB raw / 21,43 MB gzip. Leaflet 1.9.4 Canvas consume ~560,5 MB de
heap en escritorio y móvil, con render de 683/656 ms: no es aceptable como
carga inicial España.

La partición `fuente × CCAA × bloque` usa 1985–1992, 1993–2000, 2001–2010 y
2011–2021: 60 archivos, 74,11 MB raw / 21,48 MB gzip total. La mayor,
Galicia 1985–1992, son 16.133 geometrías, 3,04 MB gzip, 113 ms render y
81,8 MB heap. Andalucía equivalente: 3.225, 0,60 MB, 34 ms, 15,8 MB; Cataluña:
678, 0,13 MB, 19 ms, 5,1 MB; País Valencià: 708, 0,14 MB, 19 ms, 6,7–8,6 MB.

Para no recortar ni ocultar transfronterizas, el runtime futuro debe mantener
relaciones N:M. Hay 120.846 relaciones CCAA-feature: 1.348 más que geometrías
(~1,13 %). La opción preferida es feature primaria + overlay compartido por
bloque; la duplicación física controlada es medible pero no necesaria.

## PMTiles/vector tiles

Se construyeron dos PMTiles diagnósticos, zoom 4–14, Tippecanoe 2.79.0 y
PMTiles v3. `geometry_id` es propiedad del tile y enlaza un lookup separado; el
ID numérico MVT no se utiliza.

| Variante | tamaño | España escritorio | España móvil | Uso |
|---|---:|---:|---:|---|
| visual | 54,29 MB | 0,50 MB, 25,5 MB heap, 512 ms | 0,50 MB, 23,3 MB, 447 ms | overview, descarta pequeñas cuando necesita |
| fidelidad candidata | 61,35 MB | 1,48 MB, 72,6 MB, 715 ms | 1,48 MB, 79,5 MB, 666 ms | sin límites de tile/feature; validar presencia por zoom |

La variante visual no sirve para selección, contadores exhaustivos ni
completitud a todos los zooms. La variante de fidelidad no aplica límite de
feature/tile ni reducción de pequeños al máximo zoom, pero ES-4 deberá
validarla por zoom/viewport antes de producción. Rangos por vista de fidelidad:

| Vista | transfer escritorio | heap escritorio | transfer móvil | heap móvil |
|---|---:|---:|---:|---:|
| España z4 | 1,48 MB | 72,6 MB | 1,48 MB | 79,5 MB |
| Galicia z6 | 2,51 MB | 88,6 MB | 2,51 MB | 70,7 MB |
| Andalucía z6 | 0,71 MB | 21,9 MB | 0,69 MB | 20,3 MB |
| Cataluña z7 | 0,40 MB | 13,4 MB | 0,16 MB | 7,3 MB |
| País Valencià z8 | 0,24 MB | 9,2 MB | 0,15 MB | 6,9 MB |
| provincia/local z9 | 0,09 MB | 4,5 MB | 0,06 MB | 5,1 MB |

Se hicieron 5–11 requests HTTP Range por viewport. Esto prueba el requisito
técnico local; no prueba GitHub Pages. Antes de depender de Pages habrá que
verificar Range y caché con un asset real. Para el Atlas nacional un object
storage/CDN con Range y cache inmutable es más predecible si crece el volumen.

## Decisión

| Opción | Estado | Conclusión |
|---|---|---|
| GeoJSON monolítico | NOT_RECOMMENDED | 21,43 MB gzip, ~560 MB heap. |
| GeoJSON CCAA × bloque | RECOMMENDED para provincia/local | útil para detalle; Galicia histórica llega a 82 MB heap. |
| PMTiles/vector tiles | RECOMMENDED para España/overview/regional | 0,5–2,5 MB transferidos por vista y 5–11 ranges. |
| híbrida PMTiles overview + GeoJSON detalle | RECOMMENDED AS NEXT PROTOTYPE | conserva detalle y evita carga nacional completa. |

Leaflet + GeoJSON permanece para piloto/territorio acotado. ES-3 no migra el
visor a MapLibre; el renderer vectorial se usó solo para el benchmark. La
próxima fase debería montar un runtime nacional aislado con manifests ES-2,
PMTiles de fidelidad en España/regional, GeoJSON a escala local, transiciones
LOD sin duplicados, filtros temporales, selección estable y smoke test Range
en hosting candidato.

Presupuestos iniciales derivados: overview ≤1,5 MB y ≤80 MB heap móvil; CCAA
GeoJSON preferible ≤3,5 MB gzip/≤85 MB heap; local ≤0,25 MB/≤20 MB. Son
presupuestos de diagnóstico, no SLA de red.
