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

## 2026-08-20 — EGIF histórico identifica partes, no episodios físicos únicos

Los registros EGIF 1968–1992 se normalizan en JSON Lines conservando el XML
completo en `original_attributes` y siempre con `geometry=null`. Cuando
`NumeroParte` es único y concuerda con año/provincia, el identificador interno
es `egif-record:<NumeroParte>`, con `identity_status=source_record_only` y
`episode_identity_status=unresolved`.

**Motivo:** los 9.175 `NumeroParte` y `IdPif` del snapshot CV-3.2 son únicos,
pero la publicación definitiva de 1992 describe Marines–Altura como un solo
incendio interprovincial mientras el XML actual contiene varios partes
compatibles con componentes de ese episodio. Un identificador único de parte no
demuestra una relación uno a uno con el incendio físico.

**Consecuencias:** no se deduplican los seis pares de atributos idénticos ni se
fusionan partes por fecha, municipio, cuadrícula o proximidad. Hasta una
auditoría de identidad posterior, el visor deberá contar “partes EGIF”, no
“incendios únicos”. Los GIF se calculan con superficie forestal declarada; la
superficie agrícola/no forestal se conserva separada.

## 2026-08-19 — Datos recientes estratificados y sustitución no destructiva

Los años recientes se representarán con autoridad y madurez independientes:
histórico consolidado, registro administrativo provisional y geometría
satelital provisional. EFFIS no se tratará como si tuviera la misma autoridad
que ICV, SIGIF o EGIF.

La geometría preferente será una selección derivada. Si llega un perímetro
oficial para un incendio que ya tiene geometría EFFIS, se añadirá la oficial y
la provisional quedará conservada, enlazada y marcada como sustituida, no
borrada.

**Motivo:** a 19 de agosto de 2026, SIGIF aporta registros administrativos sin
perímetro ni identificador público, EFFIS aporta cicatrices satelitales sin
identidad administrativa y el ICV no tiene capas posteriores a 2024.

**Consecuencias:** los enlaces recientes deben registrar método y estado de
revisión; un `id` EFFIS nunca se convierte por sí solo en `fire_id`, y la
promoción de una fuente posterior no elimina la procedencia histórica.

## 2026-08-19 — Catálogo de fuentes y perfiles de distribución cerrados por defecto

La disponibilidad técnica de una fuente se separa de su permiso de
redistribución en `config/sources-gva.json`. El build `development` puede
referenciar los tres conjuntos locales; el build `public` incluye únicamente
fuentes con `publishable=true` y termina con error si se fuerza una fuente
bloqueada.

Los registros ICV, SIGIF y EFFIS conservan entidades, métricas y simbología
independientes. Las relaciones SIGIF–EFFIS siguen siendo candidatos puntuados,
no fusiones ni confirmaciones. El timeline obtiene sus límites de los
manifiestos y no contiene un `maxYear` fijado en el componente.

**Motivo:** al adoptar esta decisión, ICV y SIGIF estaban técnicamente
disponibles en local pero todavía no había base documental suficiente para
redistribuir sus derivados. EFFIS tiene otra autoridad y metodología.
Centralizar el control evita publicar por error una fuente bloqueada o
presentar varias medidas como una sola. El estado ICV fue actualizado por la
decisión de 20/08/2026; SIGIF sigue bloqueado.

**Consecuencias:** añadir un año o fuente exige actualizar datos y catálogo, no
reescribir el timeline. Cualquier perfil público futuro falla de forma segura
hasta que el estado legal se cambie explícitamente. Promover una geometría
oficial posterior no borrará la geometría EFFIS ni su procedencia.

## 2026-08-19 — EGIF histórico sin geometría implícita y cobertura por regímenes

Los partes EGIF 1968–1992 se incorporarán como registros administrativos
históricos con geometría nullable. Una geometría solo se asociará desde una
fuente independiente y documentada; municipio, hoja/cuadrícula o coordenada no
permiten construir un perímetro.

La cobertura se expondrá mediante los regímenes documentados
`early_selective` (1968–1979), `transition` (1980–1991) y `systematic` (1992),
además del periodo de formulario. Las coordenadas históricas se conservarán
como `raw_unverified` hasta auditar semántica y CRS, porque el producto enlazado
oficial solo declara geometrías puntuales validadas desde 2005.

**Motivo:** EGIF contiene 9.175 partes valencianos en el periodo, pero la propia
documentación describe cobertura selectiva antes de 1980, seis modelos de
parte y sistematización en 1992. El servicio ICV empieza en 1993 y no se ha
localizado una serie vectorial oficial homogénea anterior.

**Consecuencias:** el timeline futuro 1968–2026 mostrará por separado madurez
administrativa, disponibilidad espacial y calidad geométrica. Los histogramas
podrán contar registros EGIF, pero no presentarlos como perímetros ni como una
serie exhaustiva homogénea.

## 2026-08-20 — Derivados ICV habilitados para publicación pública

Los derivados ICV 1993–2024 pasan a `publishable=true`. El perfil público puede
incluirlos bajo CC BY 4.0 con atribución a Generalitat y un aviso
explícito de las transformaciones realizadas. La aceptación de las condiciones
se considera tácita.

**Motivo:** el Institut Cartogràfic Valencià confirmó por correo el 20 de agosto
de 2026 que CC BY 4.0 permite la redistribución pública, que la aceptación es
tácita, que pueden publicarse datos transformados si se indican las
modificaciones y que la atribución de este dataset corresponde a Generalitat.

**Consecuencias:** queda resuelto el bloqueo documental de CV-1.5b para ICV. El
perfil público incluye ICV y EFFIS y sigue rechazando SIGIF, cuya licencia es
independiente y continúa pendiente. Este cambio de estado no publica assets ni
autoriza a incluir snapshots raw o matrices de benchmark en Git.

## 2026-08-21 — GitHub Pages desde artifact y bundle público de Release

El visor público se despliega mediante GitHub Actions y el mecanismo oficial de
artifacts de GitHub Pages. Los datos permitidos se suministran a CI mediante un
bundle inmutable de GitHub Release cuya lista, tamaño y SHA-256 están fijados en
`config/public-data-bundle.json`; no se añaden los aproximadamente 73 MB de
assets generados al historial ordinario de `main`.

**Motivo:** raw, processed y web son salidas locales ignoradas, por lo que CI no
puede reconstruir los derivados desde cero sin depender accidentalmente del
equipo de desarrollo. El bundle permite verificar exactamente ICV + EFFIS,
mantener fuera SIGIF y candidatos y conservar un despliegue reproducible.

**Consecuencias:** el workflow descarga y verifica el bundle, vuelve a ejecutar
el guard `publishable`, los validadores y pruebas, y solo entonces crea el
artifact autocontenido de Pages. Actualizar los datos exige versionar y revisar
explícitamente un nuevo bundle; un push ordinario no publica datasets locales.
La Release y el despliegue son pasos separados: Pages se lanza mediante
`workflow_dispatch` desde `main`, porque la protección del entorno rechaza jobs
de despliegue cuyo origen sea directamente un tag.

## 2026-08-21 — Estado compartible en hash y filtros canónicos

El estado del visor se comparte mediante un fragmento de URL versionado y los
filtros de municipio y causa operan sobre identificadores canónicos generados
en el pipeline, no sobre textos libres en `app.js`.

**Motivo:** un fragmento funciona bajo GitHub Pages sin backend, permite
actualizar la URL con `replaceState` y mantiene compatible cualquier URL
anterior sin hash. Los identificadores municipales oficiales y un vocabulario
de causas explícito evitan opciones duplicadas sin borrar el texto fuente ni
inventar equivalencias.

**Consecuencias:** la restauración ignora parámetros inválidos; una selección
se recupera solo si su entidad está disponible en los bloques de la vista. Los
municipios se resuelven por identificador, componente exacto inequívoco del
catálogo oficial o equivalencia histórica documentada; una semejanza textual no
basta. Los casos no demostrados conservan una clave local basada en el valor raw
y quedan registrados para revisión. Los contadores en opciones se posponen
porque «N» no tendría una semántica única al combinar incendios ICV, registros
SIGIF y perímetros EFFIS.

## Plantilla para nuevas decisiones

```markdown
## YYYY-MM-DD — Título

Decisión.

**Motivo:** ...

**Consecuencias:** ...
```
