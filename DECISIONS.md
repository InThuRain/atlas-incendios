# Decisiones del proyecto

Este archivo evita volver a discutir decisiones ya tomadas sin una razón nueva.

## 2026-08-19 — Mariola–Font Roja como área piloto

Se usará Mariola–Font Roja y su entorno ampliado para validar la aplicación antes de extenderla a toda España.

**Motivo:** escala manejable, disponibilidad de cartografía oficial valenciana y fuerte interés en recurrencia histórica.

## 2026-08-19 — EGIF como columna vertebral estadística

EGIF será la referencia principal para saber qué incendios han ocurrido a escala nacional.

**Consecuencia:** un incendio puede estar presente en el atlas aunque no exista un perímetro cartografiado.

## 2026-08-19 — Separar incendio y geometría

No se modelará el perímetro como si fuera necesariamente el propio incendio.

Se mantendrán entidades separadas para registros y geometrías.

**Motivo:** cobertura espacial incompleta, varias fuentes y diferentes niveles de precisión.

## 2026-08-19 — Calidad geométrica A/B/C/D

Se adopta provisionalmente:

- A: oficial vectorial.
- B: teledetección/cartografía técnica documentada.
- C: reconstrucción histórica.
- D: sin perímetro fiable.

## 2026-08-19 — No inventar polígonos

No se dibujarán perímetros aproximados solo para rellenar huecos visuales.

Una reconstrucción solo se incorpora si existe base documental suficiente y se marca como C.

## 2026-08-19 — Arquitectura nacional con preprocesado

La versión nacional no consultará decenas de servicios GIS autonómicos directamente desde el navegador durante cada sesión.

Se construirá un pipeline de ingestión y normalización propio.

## 2026-08-19 — Carga progresiva según zoom

La vista nacional no cargará todos los polígonos completos.

Se utilizarán geometrías simplificadas/teselas y mayor detalle al acercarse.

## 2026-08-19 — Mantener los datos separados de la interfaz

Los datos y el frontend deben poder evolucionar independientemente.

## 2026-08-19 — Primera normalización valenciana en JSON Lines

La primera salida normalizada del ICV se divide en `fires.jsonl` y `geometries.jsonl`. Las geometrías se conservan como objetos Esri JSON en su CRS original, sin conversión, simplificación ni reparación.

**Motivo:** JSON Lines se puede generar y validar por streaming con la biblioteca estándar de Python, mantiene separadas las entidades incendio y geometría y evita introducir dependencias geoespaciales en esta fase inicial.

**Consecuencias:** es un formato intermedio de análisis, no el formato de distribución definitivo. La posible adopción de GeoParquet, SQLite, FlatGeobuf o PMTiles se decidirá al medir las necesidades de análisis y publicación.

## 2026-08-19 — `fire_id` valenciano provisional basado en `NumPIF_CV`

Se usa `gva:pif-cv:<NumPIF_CV>` cuando `NumPIF_CV` está presente, mantiene una relación uno a uno con `NumPIF_Min`, pertenece a un solo año y las features repetidas no discrepan en sus atributos de incendio. Los casos que incumplan estas condiciones conservan provisionalmente un identificador por feature y se registran como ambiguos.

**Motivo:** en el snapshot ICV 1993–2024, los 13.739 registros tienen ambos identificadores; hay 13.738 valores distintos de cada uno y la única repetición es `2024AL0005` / `2024030005`, cuyas dos features comparten año y atributos de incendio.

**Consecuencias:** `2024AL0005` se representa como un incendio con dos registros geométricos separados. La regla deberá revisarse al relacionar los datos con EGIF y nunca permite fusionar incendios solo porque compartan geometría.

## 2026-08-19 — GeoJSON particionado y Leaflet para la fase valenciana

Los derivados web de la Comunitat Valenciana se servirán provisionalmente como GeoJSON en EPSG:4326, con atributos de incendio separados y geometrías disponibles en niveles `local`, `regional` y `overview`. La unidad de carga recomendada es provincia × bloque temporal; se conserva también la posibilidad de una colección `overview` única para vistas completas.

Se mantiene Leaflet 1.9.4 con render Canvas para la fase valenciana. No se adopta todavía PMTiles, MapLibre, JSON compacto ni TopoJSON como formato principal.

**Motivo:** CV-1.4 midió 13.739 geometrías. El `overview` GeoJSON completo ocupa 2,49 MB gzip y, en Chrome headless, tarda una mediana de 70 ms en parsearse y 218 ms en crear y dibujar las capas, aunque usa unos 143 MB de heap. Un bloque de 3.716 geometrías baja a 73 ms de render y 54 MB. JSON compacto solo ahorra un 3,1 % comprimido; TopoJSON sin cuantización un 2,8 % y añade decodificación. La cuantización TopoJSON que sí reducía sustancialmente el tamaño invalidó microgeometrías.

**Consecuencias:** la aplicación valenciana debe cargar particiones según periodo/provincia y evitar mantener innecesariamente las 13.739 capas completas en memoria, especialmente en móviles. Esta decisión no se extrapola a España: la escala nacional deberá volver a evaluar teselas vectoriales/PMTiles y renderizadores orientados a teselas con datos nacionales reales.

## 2026-08-19 — Frontend valenciano estático guiado por manifiesto

El visor de la Comunitat Valenciana descubre los derivados web mediante un único
manifiesto versionable. Usa `overview` hasta zoom 8, `regional` en zoom 9–10 y
`local` desde zoom 11. En cada cambio sustituye el nivel anterior y conserva en
memoria los bloques ya descargados. La unidad de carga es provincia × bloque
temporal y la sesión empieza en el último año disponible, actualmente 2024.

El navegador no consulta ArcGIS: GitHub Pages sirve el frontend y los GeoJSON
como archivos estáticos. `fire_id` y `geometry_id` permanecen separados y la
igualdad geométrica auditada solo genera una advertencia, nunca recurrencia.

**Motivo:** el arranque autonómico medido requiere tres bloques `overview` y
transfiere unos 909 kB gzip de datos de aplicación. Mantiene una mediana local de
22 ms de render tanto en escritorio como en la emulación móvil probada. La vista
completa 1993–2024 sigue siendo posible, pero eleva el heap medido a unos 161 MiB,
por lo que no debe ser la carga inicial.

**Consecuencias:** añadir años o cambiar particiones no exige reescribir el
frontend si se actualiza el manifiesto. El subconjunto candidato contiene 38
archivos y continúa ignorado por Git hasta completar la revisión operativa de
licencia, atribución y redistribución del ICV.

## Plantilla para nuevas decisiones

```markdown
## YYYY-MM-DD — Título

Decisión.

**Motivo:** ...

**Consecuencias:** ...
```
