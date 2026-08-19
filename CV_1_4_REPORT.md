# CV-1.4 — Derivados web y benchmark de la Comunitat Valenciana

Fecha de ejecución: 2026-08-19.

## Resultado

CV-1.4 genera tres resoluciones web reproducibles en EPSG:4326, conserva las 13.739 geometrías y los 13.738 incendios normalizados, no deduplica features y marca explícitamente las 1.823 geometrías incluidas en grupos equivalentes de CV-1.3b.

La recomendación para la fase valenciana es:

- GeoJSON con atributos de incendio en archivos separados;
- geometrías divididas por provincia y bloque temporal (12 particiones posibles);
- `local` a 1 m, `regional` a 10 m y `overview` a 50 m, siempre con salvaguarda individual de área;
- Leaflet 1.9.4 con Canvas y carga progresiva;
- no adoptar todavía PMTiles, MapLibre, JSON compacto ni TopoJSON en producción.

`index.html` no se ha modificado. Los archivos `raw`, `fires.jsonl` y `geometries.jsonl` tampoco se han modificado.

## Entradas y línea base

| Métrica | Resultado |
|---|---:|
| Incendios | 13.738 |
| Geometrías | 13.739 |
| Vértices originales | 1.390.308 |
| Anillos originales | 18.132 |
| Vértices por geometría (mediana / p95 / máximo) | 19 / 196,1 / 72.448 |
| Tamaño de `fires.jsonl` | 20.892.151 bytes |
| Tamaño de `geometries.jsonl` | 72.042.637 bytes |
| Total normalizado | 92.934.788 bytes |
| Geometrías con marca de equivalencia CV-1.3b | 1.823 |

Checksums de las entradas, verificados antes y después:

- `fires.jsonl`: `a37f86a001adbbde1f812e16b13200bbbc7e16a74064b37312b3468b3bdb41ec`;
- `geometries.jsonl`: `85d9e06f34966d24b2e329a1bde3a280eaeef8db87c6704ee8b19bd66ca4b772`.

El área se compara en el CRS de origen EPSG:3857. Es una comparación relativa entre original y derivado, no una medición geodésica de hectáreas.

## Comparación de tolerancias sin salvaguarda de área

Esta tabla muestra por qué no basta con escoger la colección más pequeña. `Fallback` significa que el resultado vacío, no poligonal o inseguro se sustituyó por el original solo para poder completar la medición; esas tolerancias no se aceptan sin una política explícita.

| Tolerancia | Vértices | Reducción | Fallback | Error área p95 | Hausdorff p95 | GeoJSON gzip |
|---:|---:|---:|---:|---:|---:|---:|
| 0 m | 1.390.308 | 0,0 % | 0 | 0,0 % | 0,00 m | 7.518.961 B |
| 1 m | 744.885 | 46,4 % | 0 | 9,1 % | 0,99 m | 4.980.042 B |
| 2 m | 593.024 | 57,4 % | 0 | 21,7 % | 1,98 m | 4.093.252 B |
| 5 m | 391.829 | 71,8 % | 1 | 36,0 % | 4,96 m | 2.888.375 B |
| 10 m | 283.152 | 79,6 % | 2 | 36,3 % | 9,87 m | 2.287.444 B |
| 20 m | 200.135 | 85,6 % | 2 | 38,6 % | 19,59 m | 1.719.346 B |
| 50 m | 133.342 | 90,4 % | 6 | 43,5 % | 47,25 m | 1.207.272 B |
| 100 m | 237.618 | 82,9 % | 12 | 47,6 % | 84,52 m | 1.941.865 B |
| 200 m | 315.498 | 77,3 % | 28 | 49,8 % | 119,57 m | 2.395.859 B |
| 500 m | 392.468 | 71,8 % | 52 | 50,6 % | 123,46 m | 2.959.903 B |

A partir de 50 m el peso vuelve a crecer: más tolerancia colapsa algunas geometrías muy complejas y obliga a conservar originales grandes. La relación tolerancia–tamaño no es monótona.

## Niveles recomendados con protección de geometrías pequeñas

La simplificación se hace con `Shapely.simplify(preserve_topology=True)`. Para cada geometría se conserva el original si el resultado es vacío/inválido/no poligonal o si supera el límite individual de error de área. Ningún incendio pequeño desaparece silenciosamente.

| Nivel | Tolerancia máxima | Límite individual de área | Vértices | Reducción | Originales protegidos | Error área p95 / máximo | Hausdorff p95 / máximo | GeoJSON gzip |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `local` | 1 m | 1 % | 1.027.584 | 26,1 % | 3.039 | 0,66 % / 1,00 % | 0,99 / 1,00 m | 5.329.966 B |
| `regional` | 10 m | 5 % | 673.348 | 51,6 % | 7.042 | 3,51 % / 5,00 % | 9,83 / 10,00 m | 3.215.786 B |
| `overview` | 50 m | 15 % | 582.430 | 58,1 % | 7.860 | 11,59 % / 15,00 % | 45,74 / 50,00 m | 2.485.374 B |

La gran cantidad de originales protegidos se debe a que el inventario contiene muchos polígonos minúsculos: la mediana geométrica en EPSG:3857 es 3.715 m². La superficie forestal declarada sigue siendo un atributo del incendio separado de la geometría.

### Precisión de coordenadas

Redondear todo a seis decimales invalidó entre 37 y 39 microgeometrías. Redondear todo a nueve decimales mantenía la validez, pero casi duplicaba el peso comprimido. La salida definitiva usa precisión adaptativa y vuelve a validar cada feature:

- `local`: 13.702 geometrías a 6 decimales y 37 a 9;
- `regional`: 13.701 a 6 y 38 a 9;
- `overview`: 13.700 a 6 y 39 a 9.

Resultado final en cada nivel: 13.739 válidas, 0 inválidas y 0 vacías después de transformar y serializar.

Checksums SHA-256 de las colecciones completas definitivas:

- `local`: `f15cfdba7b0cbcd9606f62b726192ff2f468cd46b19ea342ffff1b21b54f32f4`;
- `regional`: `280814ea004fd22399d96b611d2025378b3a044d780fa17d2061aa74aa8a23c5`;
- `overview`: `d063969b38d7357baeb0d33c9100cd029cbe8434a3e9f6c901daf93721dde62e`;
- informe de construcción: `a7698800b1bd93fbb7e0d82f3baea4b33271ecfee1f76d5140dc38d60f8a3c9e`.

## Formatos

Comparación de las colecciones completas; gzip se calculó con nivel 9 y cabecera determinista. Los tiempos son medianas de siete ejecuciones en Node 10.19.0 y sirven como comparación relativa del entorno local.

| Nivel/formato | Bytes | Gzip | Parseo | Decodificación adicional |
|---|---:|---:|---:|---:|
| `local` GeoJSON | 28.143.207 | 5.329.966 | 334 ms | — |
| `local` JSON compacto | 25.300.168 | 5.246.101 | 324 ms | aplicación propia |
| `local` TopoJSON sin cuantizar | 27.559.423 | 5.229.706 | 317 ms | 40 ms |
| `regional` GeoJSON | 20.438.816 | 3.215.786 | 250 ms | — |
| `regional` JSON compacto | 17.595.777 | 3.135.023 | 215 ms | aplicación propia |
| `regional` TopoJSON sin cuantizar | 19.887.559 | 3.136.529 | 225 ms | 23 ms |
| `overview` GeoJSON | 18.253.918 | 2.485.374 | 217 ms | — |
| `overview` JSON compacto | 15.410.879 | 2.408.534 | 190 ms | aplicación propia |
| `overview` TopoJSON sin cuantizar | 17.710.920 | 2.415.468 | 200 ms | 22 ms |

El ahorro comprimido de JSON compacto frente a GeoJSON en `overview` es 3,1 %. TopoJSON sin cuantización ahorra 2,8 % y añade dependencia/decodificación. No compensan la pérdida de simplicidad.

TopoJSON cuantizado a 1.000.000 reduce `overview` a 1.268.393 bytes gzip, pero al decodificar produce 75 geometrías OGC inválidas. Pruebas adicionales a 10⁷, 10⁸ y 10⁹ tampoco ofrecieron una garantía monotónica de validez. TopoJSON solo se conserva como comparación técnica.

## Particionado

El peso gzip total apenas cambia al dividir; la ventaja es limitar cada descarga y, sobre todo, no materializar geometrías que no corresponden al filtro activo.

| Estrategia | Archivos | Mayor `local` | Mayor `regional` | Mayor `overview` |
|---|---:|---:|---:|---:|
| Toda la Comunitat | 1 | 5,33 MB | 3,22 MB | 2,49 MB |
| Por año | 32 | 0,81 MB | 0,42 MB | 0,21 MB |
| Por bloque temporal | 4 | 2,04 MB | 1,27 MB | 0,96 MB |
| Por provincia | 3 | 2,67 MB | 1,71 MB | 1,30 MB |
| Provincia × bloque | 12 | 1,32 MB | 0,84 MB | 0,54 MB |

Se recomienda provincia × bloque temporal para geometrías. Permite cargar todo el territorio para un periodo, o una provincia para varios periodos, sin multiplicar la complejidad del cliente. Los atributos mínimos de los 13.738 incendios pueden cargarse aparte en un solo archivo: 5.848.959 bytes sin comprimir y 492.721 bytes gzip.

La normalización conserva seis etiquetas provinciales históricas/bilingües. Solo la clave de partición derivada agrupa esas variantes en `alicante`, `castellon` y `valencia`; los atributos originales no se cambian.

## Leaflet 1.9.4

Benchmark aislado en Chrome headless, tres repeticiones, `preferCanvas: true`, sin teselas base. El servidor local no aplicó gzip; “bytes transferidos” en navegador corresponde por tanto al tamaño bruto. Los tamaños gzip anteriores representan el volumen esperable si el servidor aplica compresión y deben verificarse en el despliegue real.

| Escenario | Cargadas / renderizadas | Parseo mediano | Crear y dibujar | Heap aproximado |
|---|---:|---:|---:|---:|
| `overview`, toda CV | 13.739 / 13.739 | 70 ms | 218 ms | 143.414.897 B |
| `regional`, toda CV | 13.739 / 13.739 | 81 ms | 236 ms | 161.320.945 B |
| `regional`, bloque 2010–2019 | 3.716 / 3.716 | 29 ms | 73 ms | 53.951.368 B |
| `local`, partición Alicante y recorte Mariola–Font Roja | 3.669 / 1.462 | 27 ms | 51 ms | 51.399.542 B |

Leaflet es suficientemente fluido para esta fase en el entorno medido. La carga monolítica empieza a ser problemática por memoria alrededor de las 13.700 features, especialmente para móviles; el particionado reduce claramente coste y latencia. No hay evidencia que justifique migrar el visor valenciano a MapLibre.

## Escalado orientativo a España

No se conoce todavía el número y complejidad homogénea de geometrías nacionales, por lo que no se inventa una cifra. Como prueba lineal —no como predicción del inventario— multiplicar el `overview` valenciano daría:

| Factor de features/complejidad | Gzip aproximado | Heap aproximado | Render aproximado |
|---:|---:|---:|---:|
| 5× | 12,4 MB | 717 MB | 1,09 s |
| 10× | 24,9 MB | 1,43 GB | 2,18 s |
| 20× | 49,7 MB | 2,87 GB | 4,36 s |

Esto descarta un GeoJSON nacional monolítico. Para España habrá que medir particionado espacial/temporal y teselas vectoriales o PMTiles con el inventario real. TopoJSON solo reduce transferencia; una vez decodificado no resuelve el número de capas ni la memoria de render.

## Reproducción

```bash
python3 -m venv .venv-cv14
.venv-cv14/bin/pip install -r scripts/ingest/comunitat_valenciana/requirements-web.txt
.venv-cv14/bin/python scripts/ingest/comunitat_valenciana/build_web_datasets.py
.venv-cv14/bin/python scripts/ingest/comunitat_valenciana/validate_web_datasets.py

npm ci --prefix benchmarks/gva_web
.venv-cv14/bin/python benchmarks/gva_web/run_format_benchmarks.py
python3 benchmarks/gva_web/run_leaflet_benchmark.py
```

El benchmark de Leaflet necesita Chrome y acceso a la misma CDN de Leaflet 1.9.4 que usa el prototipo. Los resultados de máquina quedan en:

- `data/derived/gva/web/build_report.json`;
- `data/derived/gva/web/validation_report.json`;
- `data/derived/gva/web/format_benchmark.json`;
- `data/derived/gva/web/leaflet_benchmark.json`.

La matriz local completa ocupa aproximadamente 677 MB porque conserva todas las combinaciones de tres niveles, cinco particionados y dos formatos. Es material de benchmark redundante, no un paquete de producción.

## Publicación y licencia

`data/derived/gva/web/` se mantiene fuera de Git. Algunos perfiles protegidos conservan geometría prácticamente completa y todos derivan del snapshot ICV, por lo que no deben redistribuirse hasta resolver la tarea pendiente de licencia/reutilización. Cuando se confirme la licencia, debe generarse y publicar solo la variante elegida, no los 677 MB de comparaciones.
