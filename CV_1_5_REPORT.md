# CV-1.5 — Primer visor de la Comunitat Valenciana

Fecha de ejecución: 2026-08-19.

## Resultado

El prototipo local se ha transformado en una aplicación estática para toda la
Comunitat Valenciana. El navegador ya no consulta ArcGIS. Leaflet 1.9.4 renderiza
en Canvas los GeoJSON optimizados de CV-1.4 y descarga solo el nivel, las
provincias visibles y los bloques temporales necesarios.

Los datos candidatos a producción no se han publicado ni añadido a Git. La
revisión operativa de licencia, atribución y redistribución del ICV continúa
siendo un requisito previo.

## Organización del frontend

```text
index.html
css/
  app.css
js/
  app.js
  data-loader.js
config/
  datasets-gva.json
data/web/gva/                 # generado, ignorado hasta cerrar licencia
  fires.json
  provenance.json
  geometry/<nivel>/<provincia>/<bloque>.geojson
```

`data-loader.js` resuelve el manifiesto, selecciona particiones y mantiene una
caché de promesas por URL. `app.js` contiene el estado, mapa, filtros, métricas,
histograma, ficha e historia puntual. Esta separación evita duplicar rutas o
metadatos de datasets en la aplicación sin fragmentar el frontend en módulos
demasiado pequeños.

## Carga progresiva

| Zoom | Nivel | Uso |
|---:|---|---|
| 0–8 | `overview` | vista autonómica y regional amplia |
| 9–10 | `regional` | provincia y comarca |
| 11–20 | `local` | municipio y consulta local |

Al cruzar un umbral se descargan los bloques que falten, se construye la capa
nueva y se sustituye la anterior. No quedan dos niveles dibujados a la vez. Los
filtros y la selección permanecen en el estado de la aplicación y los bloques
descargados se reutilizan durante la sesión.

El particionado efectivo es provincia × bloque temporal, con cuatro bloques:
`1993-1999`, `2000-2009`, `2010-2019` y `2020-2024`. La vista inicial usa 2024 y
toda la Comunitat: necesita tres bloques `overview`, no las 36 particiones
geométricas. El periodo máximo se toma del manifiesto para poder incorporar años
posteriores sin rehacer el selector.

## Funcionalidad

- accesos a Comunitat Valenciana, Castellón, Valencia, Alicante y Mariola–Font
  Roja;
- periodo inicial/final, periodo completo y selección desde el histograma;
- filtros de superficie mínima, causa, GIF, provincia y municipio; los selectores
  se construyen con atributos de incendio y no fuerzan descargas geométricas;
- métricas separadas de incendios únicos, perímetros, superficie forestal
  declarada y GIF;
- ficha con identificadores, fuente, procedencia, atributos del incendio y número
  de geometrías;
- advertencia para geometrías reutilizadas, sin inferir identidad ni recurrencia;
- historia puntual agrupada por `fire_id`, con el texto “Incendios identificados
  cuyos perímetros contienen este punto”;
- instrumentación disponible en consola y mediante `window.__atlasDebug`.

## Subconjunto de producción

El generador selecciona exactamente 38 archivos:

| Tipo | Archivos | Sin comprimir | Gzip nivel 9 |
|---|---:|---:|---:|
| Geometrías: 3 niveles × 3 provincias × 4 bloques | 36 | 66.837.327 B | 11.030.673 B |
| Atributos de incendios | 1 | 5.848.959 B | 492.721 B |
| Procedencia para ficha, con carga diferida | 1 | 17.333 B | 2.453 B |
| **Total de datos** | **38** | **72.703.619 B** | **11.525.847 B** |

El shell versionable —HTML, CSS, dos módulos JavaScript y manifiesto— ocupa
68.467 B, o 18.163 B gzip. Datos y shell suman 72.772.086 B sin comprimir y
11.544.010 B gzip, sin contar Leaflet/Turf externos ni teselas base.

No se incluye ningún archivo de la matriz de benchmark de 677 MB. El manifiesto
registra URL, nivel, provincia, bloque, recuento, tamaño, tamaño gzip y SHA-256 de
cada asset. `scripts/validate_frontend_assets.py` exige que no haya archivos de
más ni de menos y vuelve a comprobar todos esos valores.

## Peticiones y rendimiento

La vista inicial realiza cinco peticiones de datos: manifiesto, atributos de
incendio y tres GeoJSON `overview`. La procedencia se solicita solo al abrir una
ficha. Incluyendo el documento, CSS y módulos propios son nueve peticiones
first-party antes de las teselas; Leaflet CSS/JS y Turf añaden tres recursos CDN.

Medianas de tres ejecuciones en Chrome headless, servidor local sin compresión:

| Escenario | Incendios / perímetros | Assets geom. | Carga geom. | Render | Heap | Datos gzip estimados |
|---|---:|---:|---:|---:|---:|---:|
| Escritorio, 2024 | 472 / 473 | 3 | 20,7 ms | 21,9 ms | 33,1 MiB | 908.710 B |
| Escritorio, 1993–2024 | 13.738 / 13.739 | 12 | 161,4 ms | 249,2 ms | 160,9 MiB | 2.977.633 B |
| Móvil 390×844, 2024 | 472 / 473 | 3 | 18,6 ms | 23,6 ms | 33,0 MiB | 908.710 B |

Los tiempos proceden de archivos locales y no modelan latencia de red ni el
tiempo de descarga de librerías/teselas. El layout móvil fue probado en 390×844:
mapa superior y controles debajo, con carga inicial fluida. La vista completa de
32 años es funcional en escritorio, pero su heap confirma que no conviene usarla
como arranque ni asumir el mismo margen en móviles reales de gama baja.

## Validación

`benchmarks/gva_frontend/run_smoke.py` ejecutó 12 escenarios y terminó con estado
`passed`. Se sirvió el repositorio bajo `/atlas-incendios/`, equivalente al
subdirectorio de GitHub Pages. Se comprobaron:

- vista completa, cada provincia y Mariola–Font Roja;
- 2024 y 1993–2024;
- filtro GIF;
- sustitución `overview` → `regional` → `local` sin duplicar entidades;
- historia puntual agrupada por incendio y señal de geometría reutilizada;
- `2024AL0005` como un incendio con dos perímetros;
- layout y carga inicial móvil.

El validador de assets confirmó 13.738 `fire_id`, 13.739 `geometry_id` distintos
en cada nivel y 1.823 geometrías marcadas como reutilizadas. El manifiesto se
reconstruyó dos veces con el mismo SHA-256:
`25c06c5bd3efe8d74344fdc261a61b98b1dc723d92e0f08a7a36d172188e7a02`.

Los informes detallados de smoke, rendimiento y validación se generan en
`data/derived/gva/frontend/` y permanecen ignorados por Git.

## Diferencias respecto al prototipo Mariola

La aplicación deja de estar limitada por un rectángulo piloto y arranca en toda
la Comunitat. Sustituye las consultas ArcGIS por derivados estáticos, incorpora
carga progresiva y caché, añade navegación provincial, municipio, métricas con
terminología corregida y procedencia trazable. El histograma y la historia
cuentan incendios únicos, mientras que mapa y métricas distinguen los perímetros.
La recurrencia territorial definitiva y la “superficie única quemada” siguen
deliberadamente fuera de alcance.

## Reproducción

```bash
python3 scripts/build_frontend_assets.py --copy-assets
python3 scripts/validate_frontend_assets.py
python3 benchmarks/gva_frontend/run_smoke.py
python3 benchmarks/gva_frontend/run_performance.py
```

Las dos últimas órdenes requieren Chrome y poder abrir un servidor HTTP local.
