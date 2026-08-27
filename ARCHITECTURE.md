# Arquitectura propuesta

## Objetivo

Poder explorar decenas de miles de incendios y geometrías sin bloquear el navegador.

## Principio

**No usar la arquitectura actual del piloto —consultas anuales directas a ArcGIS— como arquitectura nacional definitiva.**

El piloto sirve para validar UX y lógica.

## Pipeline

### 1. Ingesta

Scripts independientes por fuente:

```text
scripts/ingest/
    egif/
    comunitat_valenciana/
    ...
```

Cada script debe guardar una copia normalizada y metadatos de procedencia.

### 2. Normalización

Modelo lógico recomendado:

```text
fires
  fire_id
  fechas
  atributos estadísticos
  territorio
  causa
  fuente

geometries
  geometry_id
  fire_id
  geometry
  source
  quality
  method
  date
```

Esto permite varios perímetros para un mismo incendio y registros sin perímetro.

### 2.1. Ciclo de vida de datos recientes

Los datos recientes mantendrán dos ejes distintos: autoridad de la fuente y
madurez del registro. No se utilizará una única bandera "oficial" que mezcle
ambos conceptos.

```text
record_maturity
  consolidated | provisional | operational

authority_type
  regional_administrative | national_administrative | satellite

identity_status
  unlinked | candidate | verified
```

El histórico ICV 1993–2024 se mantiene como snapshot consolidado. Los registros
SIGIF 2025–2026 serán observaciones administrativas provisionales y los
perímetros EFFIS serán geometrías satelitales provisionales independientes.

La geometría preferente se resolverá como estado derivado, no mediante
sobrescritura. Cada geometría conservará `source`, identificador de fuente,
fechas de adquisición/actualización, método, calidad y estado de preferencia.
Cuando una geometría oficial sustituya visualmente a una provisional, la
anterior quedará marcada como `superseded` y enlazada mediante
`superseded_by`; nunca se borrará.

Una propuesta de enlace espacial/temporal no basta para fusionar incendios. El
enlace tendrá método, confianza y estado de revisión propios. Los identificadores
EFFIS no se usarán como `fire_id` administrativo.

### 2.2. Registros históricos 1968–1992

EGIF será la entidad administrativa histórica, pero no una fuente de perímetros.
Los partes se cargarán en `fires` aunque no exista geometría. Municipio,
hoja/cuadrícula y coordenadas originales son tipos de localización distintos y
no se convertirán entre sí. Una coordenada anterior a 2005 se conservará como
`raw_unverified` hasta validar por registro su semántica, CRS, datum, huso,
unidades y rango.

La cobertura histórica se modelará separada de la calidad geométrica:

```text
collection_regime
  selective                    1968-1979
  transitional                 1980-1991
  systematic_or_near_systematic 1992

location_type
  none | municipality | sheet_grid | reported_point

coordinate_status
  absent | raw_unverified | validated
```

Estos cortes proceden de cambios documentados en la recogida EGIF y no asignan
automáticamente calidad a cada parte. Los seis periodos de formulario se
conservarán mediante `schema_period`, evitando forzar a los años antiguos a un
esquema moderno.

CV-3.2 confirmó que el exportador aplica un XSD actual único a los seis
periodos. Por ello `form_model` expresa el periodo documental, no un esquema
original recuperado del registro. `fire_id=egif-record:<NumeroParte>` identifica
el parte administrativo; `episode_identity_status=unresolved` impide usarlo
como afirmación de que cada parte equivale a un episodio físico distinto. Los
recuentos de frontend deberán denominarse “partes EGIF” hasta resolver esa
identidad.

Una geometría histórica solo entrará en `geometries` desde una fuente
independiente, con método, escala, CRS, licencia y procedencia. El enlace con un
parte EGIF será `candidate` hasta disponer de identificador o revisión
documental suficiente. Un mapa agregado, un municipio o un punto nunca se
usarán para fabricar un polígono.

### 3. Validación

Comprobar:

- geometrías inválidas;
- duplicados;
- superficies absurdas;
- fechas inconsistentes;
- identificadores duplicados;
- discrepancia entre superficie declarada y superficie geométrica;
- geometrías fuera del territorio esperado.

No corregir automáticamente discrepancias sin registrar qué se ha hecho.

### 4. Generalización espacial

Generar varias resoluciones de geometría.

Ejemplo conceptual:

- `geometry_full`
- `geometry_medium`
- `geometry_low`

Usar simplificación topológica adecuada.

Nunca sobrescribir la geometría original.

### 5. Distribución

Para España, evaluar seriamente:

- PMTiles;
- vector tiles;
- FlatGeobuf para subconjuntos;
- GeoParquet para análisis offline/backend;
- SQLite/SpatiaLite o DuckDB como almacenamiento local de procesamiento.

La elección final debe documentarse mediante una ADR/entrada en `DECISIONS.md`.

## Estrategia por zoom

### Zoom nacional

- solo incendios grandes o agregaciones;
- geometría muy simplificada;
- estadísticas agregadas.

### Zoom regional

- más incendios;
- geometría media;
- filtros completos.

### Zoom local

- todos los incendios disponibles;
- geometría completa;
- recurrencia precisa;
- historia del lugar.

## Recurrencia

Hay dos problemas distintos:

### Consulta puntual

Dado un punto, obtener todos los polígonos que lo contienen.

En el piloto se puede resolver en cliente con Turf.js.

A escala nacional evaluar índices espaciales o consultas preprocesadas.

### Mapa continuo de recurrencia

No calcular en cada render mediante intersección de todos los polígonos.

Precalcular:

- raster de recurrencia; o
- polígonos derivados; o
- teselas agregadas.

## Frontend

El prototipo actual puede continuar en JavaScript vanilla.

Antes de migrar a React/Vue/Svelte, demostrar que la complejidad lo justifica.

El estado compartible se serializa en un fragmento de URL versionado. El módulo
`js/url-state.js` es independiente del territorio: recibe años, fuentes y
provincias válidas desde el manifiesto y no codifica reglas GVA. El hash se
actualiza con `history.replaceState`, de modo que GitHub Pages no necesita
routing de servidor ni se llena el historial al mover el mapa.

Sin estado explícito, el timeline toma `min` y `max` del manifiesto y muestra el
periodo completo. El histograma mantiene ese eje íntegro aunque el intervalo
activo sea un solo año. La selección compartida se valida en dos niveles:
identidad (`entity`) y representación concreta (`geometry`); restaurar los
parámetros sin aplicar el estilo destacado, la ficha y el popup de la geometría
exacta no se considera éxito. El popup usa un punto interior representativo y
no desplaza el centro restaurado por el permalink.

El cambio manual de municipio encuadra los perímetros que han superado el resto
de filtros, con padding y zoom máximo. Este autoencuadre no se ejecuta al
restaurar un hash ni se repite al cambiar otros filtros. Si no existen
perímetros, el catálogo actual no ofrece límites municipales: se conserva la
vista, sin inventar centroides. Un futuro fallback requerirá incorporar al
manifiesto un límite oficial con procedencia documentada.

Los filtros no operan sobre etiquetas libres. Los derivados web separan
`municipality_raw`/`municipality_id`/`municipality_name` y
`cause_raw`/`cause_code`/`cause_label`. El código municipal procede del catálogo
oficial y las equivalencias de causa están declaradas en
`config/ui-vocabularies.json`; los valores no demostrados permanecen sin
resolver. Este patrón deberá admitir catálogos territoriales distintos al
generalizar el atlas a España.

CV-3.3 añade registros administrativos sin geometría a un canal separado de
las features cartográficas. `DatasetLoader` entrega `features` y
`administrativeRecords`; solo las primeras llegan a `L.geoJSON`. De este modo
EGIF participa en timeline, filtros, métricas y listado sin fabricar una capa
Leaflet. Un parte seleccionado abre ficha lateral, pero no popup ni
autoencuadre. La consulta puntual ignora esos registros y explica por qué no
pueden evaluarse espacialmente.

Las referencias históricas EGIF `hoja` + `cuadricula` pertenecen a un canal
conceptual adicional y no alteran este contrato:

```text
administrative record (EGIF) ──0..1──> spatial reference
                                  ≠ fire geometry / perimeter
```

Solo una referencia con semántica, clave y límites documentados
(`A_CONFIRMED`) podrá producir en el futuro una
`spatial_reference_geometry`. CV-3.5 no encontró ninguna, pero ES-1.5 recibió
de CCINIF la malla histórica oficial y confirmó por igualdad exacta 626.957
relaciones nacionales, incluidas las 8.565 valencianas. Esto promueve el enlace
documental, no `geometry`: los partes continúan sin geometría de incendio. Una
celda se almacena una sola vez y los partes se relacionan con ella, sin repetir
geometría ni usarla en recurrencia puntual, superficie quemada o Historia de
un lugar. Su publicación sigue bloqueada por licencia.

La cabecera admite una futura identidad gráfica sin solicitar assets todavía.
`index.html` contiene metadatos Open Graph textuales y puntos de extensión
documentados para logo, `favicon.svg` y `og:image`; no se enlazará ningún recurso
hasta disponer de un diseño aprobado, evitando placeholders y respuestas 404.

Componentes funcionales deseables:

```text
Map
Timeline
Filters
FireDetails
TerritoryAnalysis
PointHistory
Legend
SourceQuality
Stats
```

## Backend

No es imprescindible para el primer prototipo nacional si los datos se sirven como archivos estáticos y teselas.

Agregar backend solo cuando aporte valor claro:

- consultas complejas;
- áreas dibujadas por usuario;
- estadísticas dinámicas costosas;
- actualización automatizada;
- búsqueda avanzada.

## Despliegue

Objetivo deseable: proyecto desplegable como web estática siempre que sea posible.

Posibles plataformas:

- GitHub Pages;
- Cloudflare Pages;
- Vercel;
- servidor propio.

Los archivos de datos grandes pueden requerir almacenamiento independiente.

## Integración reciente y perfiles de build (CV-2.3)

El frontend consume un manifiesto de ejecución compuesto a partir de
`config/sources-gva.json`. La configuración concentra rango temporal, estado,
licencia, permiso de redistribución y rol de cada fuente. No hay decisiones de
publicación dispersas en el JavaScript.

El recorrido de datos recientes es:

```text
raw CV-2.2 -> processed CV-2.2 -> web reducido CV-2.3 -> perfil de ejecución
```

El perfil `development` habilita los assets locales EGIF, ESFire30, ICV, SIGIF y EFFIS. El
perfil `public` solo admite fuentes con `publishable=true` y falla si se intenta
forzar una fuente bloqueada. Desde la aclaración escrita del ICV de 20/08/2026,
el perfil público incluye EGIF, ESFire30, ICV y EFFIS; SIGIF permanece
bloqueado. Componer un perfil no publica ni copia datos. CV-4.4 publica esa
combinación mediante `public-data-v5` sin modificar `public-data-v4`.

Las entidades siguen separadas también en el navegador: `fire_id` ICV,
`sigif_record_id` y `geometry_id`/`effis_id`. Los candidatos son relaciones
puntuadas con estado `candidate`; nunca sustituyen esas identidades. Los
puntos SIGIF y los polígonos EFFIS se cargan por año. Los atributos y perímetros
ICV continúan con carga diferida por provincia, bloque temporal y zoom.

ESFire30 sigue el canal `raw -> normalized -> web` con una colección autonómica
por LOD. Los polígonos fronterizos no se recortan ni se repiten: cada feature
contiene relaciones muchos-a-muchos a provincias y municipios oficiales, que
los filtros interpretan como intersecciones derivadas. `entity_id` se calcula
por contenido; el índice del SHP solo es procedencia. EGIF conserva
`geometry=null` y no recibe esos polígonos como geometría preferente.

## Publicación estática en GitHub Pages

El sitio público se construye en GitHub Actions, pero los datos web permitidos
no se regeneran allí desde raw/processed: esas entradas son locales, están
ignoradas y no serían reproducibles en CI. En su lugar, el bundle inmutable
`public-data-v5` contiene únicamente los 38 assets ICV, los 3 ESFire30, los 2
EFFIS, el asset EGIF compacto y tres manifiestos fuente saneados/necesarios. En
total son 44 assets de datos y 47 entradas. `config/public-data-bundle.json` fija lista,
tamaños y checksums; CI descarga, verifica y extrae el bundle antes de componer
el perfil.

El pipeline vuelve a aplicar el guard de `config/sources-gva.json`, ejecuta los
validadores, monta un directorio estático autocontenido y lo entrega como
artifact de Pages. SIGIF, candidatos, raw, processed y matrices de benchmark no
forman parte ni del bundle ni del artifact. Las rutas relativas mantienen el
funcionamiento bajo `/atlas-incendios/` sin una configuración específica de
servidor.

## Timeline con cobertura heterogénea

La extensión 1968–2026 representa la madurez de los datos además
del año. El frontend contará por separado registros administrativos y
perímetros disponibles y mostrará bandas visibles: histórico temprano EGIF
1968–1979, transición 1980–1991, EGIF sistematizado desde 1992, cartografía ICV
consolidada 1993–2024 y fuentes provisionales separadas 2025–2026. Que un año
sea seleccionable no implica que tenga geometría ni la misma completitud que
los demás.

## Escala nacional y territorio (ES-1)

El País Valencià es el primer territorio implementado y un piloto de
compatibilidad, no una frontera del modelo. Las fuentes se organizan en tres
niveles independientes: nacionales (EGIF, ESFire30), autonómicas oficiales y
complementarias (EFFIS, teledetección o reconstrucciones documentadas). Una
geometría autonómica preferente no borra el registro o la geometría nacional.

La jerarquía territorial genérica usa códigos INE y límites/bounds IGN-CNIG:

```text
España -> comunidad autónoma -> provincia -> municipio
España -> ciudad autónoma -> municipio
```

Las geometrías mantienen una relación muchos-a-muchos con territorios. Se
almacena una sola geometría fuente y no se recorta para asignarla a CCAA o
provincia; 1.342 polígonos ESFire30 cruzan CCAA y 2.364 cruzan provincias. Los
índices territoriales y las teselas de representación deben conservar el mismo
`geometry_id`.

ES-1 mide que un GeoJSON overview nacional ESFire30 mínimo (119.498 features)
ocupa 71,44 MB raw / 22,92 MB gzip y añade aproximadamente 459 MiB de heap en
Leaflet. Leaflet + Canvas y GeoJSON siguen siendo válidos para el piloto,
territorios y periodos acotados; la vista nacional deberá comparar en un
prototipo aislado teselas vectoriales/PMTiles antes de elegir entrega y
renderer. No se ha migrado el frontend.

## Referencias espaciales históricas nacionales (ES-1.5)

La arquitectura nacional incorpora un tercer canal espacial independiente de
geometrías de incendio y territorios administrativos:

```text
source record (EGIF) ──0..1──> historical_grid_cell
historical_grid_cell  ──1..N──> geometry_part
historical_grid_cell                   != fire_geometry
```

`historical_grid_cell` es una entidad nacional reutilizable identificada por
la fuente y `HOJA+CUAD`. Conserva todos los fragmentos costeros/insulares y sus
atributos originales. Las relaciones territoriales son comprobaciones
muchos-a-muchos independientes; municipio o provincia no eligen ni corrigen
la celda.

El contrato de uso permite contar partes que citan una celda y mostrar el área
de referencia con simbología inequívoca. Prohíbe tratarla como perímetro,
superficie quemada, centro del incendio, recurrencia o prueba de identidad de
episodio. El perfil de publicación debe excluirla mientras
`publishable=false_pending_permission`.

## Contratos canónicos nacionales (ES-2)

La transición nacional se construye en paralelo al piloto. Los contratos v1 de
`schemas/national/v1/` separan `source_record`, `fire_geometry`,
`historical_spatial_reference`, `territory`, `territory_relation`,
`candidate_link`, `source` y `publication_asset`. Ninguno de esos canales se
deduce o fusiona automáticamente con otro.

El territorio usa `territory_type + parent_id`, sin profundidad fija, e IDs por
códigos oficiales (`ES`, `ES:CCAA:10`, `ES:PROV:46`, `ES:MUN:46001`). Ceuta y
Melilla son ciudades autónomas; `51/52` se preservan solo como códigos
estadísticos equivalentes al nivel provincial. Nombres, aliases y vigencia son atributos. Las
geometrías se almacenan una vez y sus relaciones territoriales N:M distinguen
lo declarado por la fuente de una intersección espacial. Una referencia CCINIF
puede tener varios fragmentos, pero conserva
`geometry_status=not_fire_geometry` y el parte EGIF mantiene `geometry=null`.

`config/sources-spain.json` generaliza licencia, publicación, semántica,
cobertura y actualización sin sustituir todavía `sources-gva.json`. El guard
nacional exige licencia, atribución, provenance y permiso tanto en la fuente
como en cada asset; SIGIF y CCINIF fallan de forma cerrada. La compatibilidad
de IDs, permalink `v=1` y `public-data-v5` queda declarada y probada en
`config/compatibility-gva-v1.json`.

Los registros nacionales se particionarán por fuente × CCAA × periodo. Una
geometría transfronteriza no se duplica: los manifests territoriales referencian
su `geometry_id` compartido. ES-2 no decide formato de tesela ni renderer.

## Entrega geométrica nacional (ES-3)

El laboratorio ES-3 confirma que GeoJSON ESFire30 nacional monolítico es
**NOT_RECOMMENDED** como carga inicial (~560 MiB de heap para 119.498
features). GeoJSON por CCAA × bloque temporal es **RECOMMENDED** para
provincia/local; la vista España/overview/regional debe usar
PMTiles/vector tiles, también **RECOMMENDED**. Las fichas recuperarán el
`geometry_id` desde atributos mínimos del tile y un lookup separado.

La variante PMTiles de fidelidad queda como referencia experimental del
siguiente pipeline. No se migra todavía el frontend ni se abandona Leaflet; la
arquitectura candidata es híbrida, vector tiles para overview/regional y
GeoJSON de detalle para provincia/local. La simplificación de 100 m no es
adecuada para detalle. Los manifests deben resolver transfronterizas mediante
referencias compartidas, sin clipping ni identidad duplicada. PMTiles exige
HTTP Range: Range/caché en GitHub Pages continúa pendiente de un smoke test
real antes de un despliegue.
