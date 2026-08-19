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
