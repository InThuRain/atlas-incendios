# UX-2 — Simplificación y pulido de la interfaz

Fecha: 21 de agosto de 2026.

## Alcance

UX-2 no cambia fuentes, metodología, cobertura, datasets ni arquitectura de
distribución. Los perfiles siguen siendo ICV + SIGIF + EFFIS en development e
ICV + EFFIS en public. No se integra EGIF.

## Columna lateral

Se elimina por completo el panel «Ir a». La cabecera reúne estado de carga,
nivel geométrico y «Compartir vista». Después aparecen:

1. Periodo y controles Desde/Hasta.
2. Filtros, comenzando por Ámbito y Municipio.
3. Histograma anual interactivo.
4. Fuentes visibles y cobertura.
5. Métricas, historia puntual, ficha, listado y metodología.

El control Ámbito contiene Todo el País Valencià, Castelló, València y Alacant.
Al cambiarlo centra el mapa, fija la provincia de carga y reconstruye el selector
municipal únicamente con los municipios de ese ámbito. Los permalinks conservan
centro y zoom propios; `?view=mariola_font_roja` continúa siendo compatible.

## Histograma: causa y restauración

El historial muestra que `577fac3` introdujo el histograma en CV-1.5 y ningún
commit posterior lo eliminó. Había dos causas acumuladas de su desaparición
visual:

- se construía solo entre `from` y `to`; el inicio en 2026 y el clic en una
  barra reducían el componente a una única barra;
- la altura de cada barra era porcentual, pero el contenedor solo tenía
  `min-height`; Chromium podía resolver esas alturas como colapsadas.

UX-2 fija una altura compacta explícita, conserva siempre el eje completo del
manifiesto y mantiene en memoria los recuentos ya cargados. Las barras apilan
visualmente ICV, SIGIF y EFFIS sin fusionar identidades. El intervalo activo se
resalta; pulsar un año fija `from=to=YYYY` sin hacer desaparecer las demás
barras.

## Selección compartida

El fallo estaba demostrado. `DatasetLoader.loadAsset()` añade un `entity_id`
auxiliar que, en geometrías ICV, puede ser el propio `geometry_id`. El estilo
anterior evaluaba `entity_id || fire_id` frente al `fire_id` seleccionado. La
ficha podía restaurarse, pero la geometría ICV no recibía el estilo destacado.

La selección visual ahora se calcula sobre el registro normalizado:
`record.entityId` debe coincidir con `entity` y, cuando existe,
`record.geometryId` con `geometry`. Los tests disparan el evento de clic de una
geometría real, ejecutan «Compartir vista», abren el hash resultante en otra
instancia de Chrome y comprueban centro/zoom, filtros, entidad, geometry_id,
estilo de la capa, ficha y popup real en el DOM del mapa. El clic y la
restauración llaman a `selectEntity()`, que elige la geometría exacta, calcula
un punto interior con Turf cuando no existe coordenada de clic y abre el mismo
popup. En restauración se desactiva únicamente el auto-pan para preservar
lat/lng/z del hash.

## Autoencuadre municipal

El evento manual `change` de Municipio vuelve a aplicar los filtros y agrega
los bounds de todas las capas poligonales resultantes. Por tanto intervienen
periodo, fuentes activas, provincia, municipio, superficie mínima, GIF y causa;
los puntos SIGIF no se usan para fingir una extensión municipal. Se aplica
`fitBounds` con 42 px de padding y `maxZoom=13`.

El comportamiento no se dispara al restaurar un permalink ni al cambiar
posteriormente otro filtro. El manifiesto actual no contiene geometrías ni
bounds municipales oficiales. Si no hay perímetros visibles, se conserva el
encuadre y se informa al usuario. Un posible fallback queda pospuesto hasta que
el manifiesto incorpore un contrato explícito para bounds oficiales, sin
centroides inventados ni claves especulativas en el frontend.

Casos de aceptación medidos en development: Elx encuadró 179 perímetros con un
margen mínimo renderizado de 218 px; el municipio 03002 en 1994 encuadró su
único perímetro y quedó limitado a zoom 13; Elx en 1994 con superficie mínima de
1.000 ha no tenía perímetros, mantuvo exactamente centro y zoom y mostró el
aviso. El cambio no añadió peticiones de datos (11 antes y después en el caso
Elx) durante el cálculo: recorre solamente las capas ya filtradas. Como cualquier
zoom manual, el `fitBounds` puede activar después la carga progresiva del nivel
local; esa actualización conserva el encuadre calculado y no vuelve a
autoajustarlo. En la prueba Elx el paso regional → local añadió cuatro bloques
ICV no cacheados: 6,34 MB servidos localmente, 1,18 MB gzip estimados y 10,1 ms
de carga. Los assets recientes ya estaban en caché.

La auditoría DATA-UX-1 contabilizaba 181 registros canónicos para Elx. El
desglose reproducible es 178 incendios/perímetros ICV, dos registros puntuales
SIGIF y un perímetro EFFIS. El autoencuadre suma únicamente polígonos: 178 + 1 =
179. No se ha perdido ni deduplicado ningún registro; se mantienen separadas la
identidad administrativa y la representación geométrica.

## Estado inicial y rendimiento

Sin hash ni periodo legacy explícito, la aplicación usa `years.min` y
`years.max`; actualmente 1993–2026. No hay años codificados en el componente.

Medianas de tres ejecuciones limpias del perfil public, servidas localmente sin
compresión HTTP. Los bytes gzip son la estimación contenida en los manifiestos;
teselas y bibliotecas CDN quedan fuera de las métricas del loader.

| Vista | App | Carga geom. | Render | Heap | Respuesta local | gzip estimado |
|---|---:|---:|---:|---:|---:|---:|
| Escritorio · 2026 | 64,5 ms | 11,7 ms | 15,9 ms | 5,80 MiB | 236 KiB | 65,1 KiB |
| Escritorio · 1993–2026 | 650,1 ms | 268,3 ms | 336,6 ms | 173,76 MiB | 24,98 MiB | 2,99 MiB |
| Móvil 390×844 · 2026 | 59,0 ms | 9,4 ms | 12,4 ms | 5,63 MiB | 236 KiB | 65,1 KiB |
| Móvil 390×844 · 1993–2026 | 630,8 ms | 229,2 ms | 336,9 ms | 166,28 MiB | 24,98 MiB | 2,99 MiB |

La ejecución pública final necesitó un reintento controlado por un timeout
transitorio al arrancar una de las tres instancias móviles; las tres mediciones
válidas completaron el visor. No hubo cierres ni bloqueos de la aplicación; se
conserva el inicio completo. El heap de aproximadamente 166–174 MiB exige
cautela y una futura prueba en dispositivos físicos de gama baja, pero no
justifica por sí solo una arquitectura nueva en esta fase.

Los reportes reproducibles quedan ignorados en
`data/derived/gva/frontend/ux2-final-performance-public.json` y
`ux2-performance-development.json`.

## Bundle público reproducible

UX-2 referencia `public-data-v3` / `atlas-public-data-v3.tar.gz`: 41 entradas,
74.770.947 bytes sin comprimir y 11.681.915 bytes de archivo. Dos ejecuciones
consecutivas produjeron el mismo SHA-256
`0e8ccf5edb1e04d369c3aa6b78bab47cb2ff13a9d09bc12a089ed4f2a572e4b2`.
El hash coincide con v2 porque no cambió ningún dataset; el nuevo tag versiona
la entrega de UX-2, no una revisión de fuentes o cobertura.

## Identidad futura

No se crea logo ni favicon. La cabecera y `<head>` incluyen únicamente puntos
de extensión y metadatos Open Graph textuales. Un futuro diseño podrá añadir
logo, `favicon.svg`, fallback ICO/PNG y `og:image` sin reestructurar la cabecera
ni generar ahora peticiones a ficheros inexistentes.

## Validación

Se comprueban perfiles development/public, subpath `/atlas-incendios/`, cuatro
ámbitos, municipio limitado por provincia, 34 barras, clic de año, intervalos,
hash v1 anterior, parámetros inválidos, selección compartida visual, SVG local,
inicio completo y responsive 390×844. Las capturas y reportes quedan ignorados
en `data/derived/gva/frontend/`.

Resultado final: 18 pruebas Python, 34 escenarios Chrome development y 33
escenarios Chrome public, todos superados. El guard público continúa rechazando
SIGIF y candidatos.

## Publicación verificada

UX-2 se publicó desde `main` mediante `.github/workflows/pages.yml`, ejecución
`32506336949`: build 1 min 30 s y deploy 11 s, ambos correctos. La Release
`public-data-v3` expone `atlas-public-data-v3.tar.gz` con el tamaño y SHA-256
fijados en `config/public-data-bundle.json`.

La comprobación posterior abrió realmente
`https://inthurain.github.io/atlas-incendios/` en instancias limpias de Chrome y
validó: inicio 1993–2026, 34 barras y clic en 1994, autoencuadre de los 179
perímetros de Elx, centro/zoom de permalink intactos, ficha/resaltado/popup de la
geometría seleccionada, las dos geometrías de `2024AL0005`, layout móvil y
ausencia de SIGIF. El inicio realizó 16 peticiones del loader, recibió 26.191.875
bytes sin compresión en la instrumentación y declaró 3.135.507 bytes gzip
estimados; `appElapsedMs` fue 33,1 ms en esa ejecución headless contra GitHub
Pages. Esta última cifra depende de caché de borde y no sustituye las medianas
locales controladas de la tabla anterior.

GitHub Actions emitió una advertencia no bloqueante: algunas acciones oficiales
de Pages aún declaran Node.js 20 y el runner las fuerza a Node.js 24. No afectó
al build ni al despliegue, pero conviene vigilar futuras versiones de esas
acciones.
