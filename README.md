# Atlas Histórico de Incendios Forestales

## Objetivo

Construir un atlas interactivo de incendios forestales que permita explorar la historia del fuego en el territorio español, comenzando por el área piloto de Serra de Mariola – Carrascar de la Font Roja y ampliando progresivamente a Comunitat Valenciana y España.

El proyecto debe combinar dos tipos de información que no son equivalentes:

1. **Inventario estadístico de incendios**: qué incendios ocurrieron, cuándo, dónde, superficie, causa, etc.
2. **Geometría del incendio**: perímetro vectorial o localización espacial con un nivel de calidad conocido.

La ausencia de perímetro no implica que el incendio no existiera.

## Área piloto

Zona inicial ampliada alrededor de:

- Serra de Mariola
- Carrascar de la Font Roja
- Alcoi
- Cocentaina
- Muro
- Agres
- Alfafara
- Bocairent
- Banyeres de Mariola
- Ibi
- Onil
- sierras y valles próximos

El área piloto sirve para validar:

- carga y visualización de perímetros;
- filtros temporales y por superficie;
- clasificación de Grandes Incendios Forestales (GIF >= 500 ha);
- consulta por causa;
- estadísticas por año;
- recurrencia del fuego;
- consulta “Historia de un lugar”;
- arquitectura de datos reutilizable a escala nacional.

## Estado actual

Existe un visor estático basado en HTML, JavaScript, Leaflet 1.9.4, Canvas y
Turf.js. El navegador no consulta servicios ArcGIS en tiempo real.

Funcionalidades ya planteadas/probadas:

- mapa interactivo;
- histórico ICV 1993–2024 y colecciones recientes SIGIF/EFFIS 2025–2026
  estrictamente separadas;
- filtro por intervalo de años;
- filtro por superficie mínima;
- filtro por causa;
- identificación de GIF >= 500 ha;
- histograma anual;
- listado de incendios visibles;
- consulta de recurrencia en un punto mediante intersección con polígonos;
- distinción conceptual entre inventario estadístico y geometría.

## Cómo continuar con Codex

Antes de modificar código, leer en este orden:

1. `AGENTS.md`
2. `PROJECT_CONTEXT.md`
3. `DATA_SOURCES.md`
4. `ARCHITECTURE.md`
5. `ROADMAP.md`
6. `DECISIONS.md`

En una sesión nueva se puede empezar con:

> Lee AGENTS.md, PROJECT_CONTEXT.md, DATA_SOURCES.md, ARCHITECTURE.md, ROADMAP.md y DECISIONS.md antes de hacer cambios. Resume el estado actual y propón el siguiente paso sin modificar archivos todavía.

## Repositorio recomendado

Inicializar Git desde el primer momento:

```bash
git init
git add .
git commit -m "Initial wildfire atlas pilot"
```

Después, hacer commits pequeños por funcionalidad o bloque de datos.

## Entorno de desarrollo y tests

Las dependencias Python de desarrollo están fijadas en `requirements-dev.txt`.
Para crear un entorno reproducible y ejecutar la suite:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
```

Los tests de navegador requieren además Google Chrome o Chromium. Los datasets
locales necesarios para los validadores continúan ignorados por Git.

### Pipeline histórico EGIF 1968–1992

La descarga y normalización valenciana de CV-3.2 se ejecuta con:

```bash
.venv/bin/python scripts/ingest/egif/gva_1968_1992.py all
```

Genera un manifiesto verificable y 9.175 partes administrativos con geometría
nula. Los ZIP raw y las salidas procesadas se mantienen fuera de Git; véase
`CV_3_2_EGIF_AUDIT.md` para alcance, identidad y limitaciones.

## Principio fundamental

**Nunca dibujar un perímetro inventado.**

Cuando la geometría no sea oficial o sea una reconstrucción histórica, debe quedar etiquetada explícitamente con su fuente y calidad.
