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

El perfil `development` habilita los assets locales ICV, SIGIF y EFFIS. El
perfil `public` solo admite fuentes con `publishable=true` y falla si se intenta
forzar una fuente bloqueada. Componer un perfil no publica ni copia datos.

Las entidades siguen separadas también en el navegador: `fire_id` ICV,
`sigif_record_id` y `geometry_id`/`effis_id`. Los candidatos son relaciones
puntuadas con estado `candidate`; nunca sustituyen esas identidades. Los
puntos SIGIF y los polígonos EFFIS se cargan por año. Los atributos y perímetros
ICV continúan con carga diferida por provincia, bloque temporal y zoom.

## Timeline con cobertura heterogénea

La futura extensión 1968–2026 debe representar la madurez de los datos además
del año. El frontend contará por separado registros administrativos y
perímetros disponibles y mostrará bandas visibles: histórico temprano EGIF
1968–1979, transición 1980–1991, EGIF sistematizado desde 1992, cartografía ICV
consolidada 1993–2024 y fuentes provisionales separadas 2025–2026. Que un año
sea seleccionable no implica que tenga geometría ni la misma completitud que
los demás.
