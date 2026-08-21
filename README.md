# Atlas Histórico de Incendios Forestales

Visor público: <https://inthurain.github.io/atlas-incendios/>

## Objetivo

Construir un atlas interactivo de incendios forestales que permita explorar la
historia del fuego en España. El País Valencià es el primer territorio
implementado; el proyecto nació como piloto en Serra de Mariola – Carrascar de
la Font Roja.

El proyecto debe combinar dos tipos de información que no son equivalentes:

1. **Inventario estadístico de incendios**: qué incendios ocurrieron, cuándo, dónde, superficie, causa, etc.
2. **Geometría del incendio**: perímetro vectorial o localización espacial con un nivel de calidad conocido.

La ausencia de perímetro no implica que el incendio no existiera.

## Origen del proyecto

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

Esta área conserva valor como caso de prueba técnico e histórico, pero ya no es
un acceso territorial principal: el visor actual cubre todo el País Valencià.
El trabajo inicial permitió validar:

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
- perfil público con perímetros ICV/Generalitat 1993–2024 y perímetros
  satelitales provisionales EFFIS 2025–2026, estrictamente separados;
- perfil local de desarrollo que añade los registros administrativos
  provisionales SIGIF 2025–2026 y candidatos SIGIF–EFFIS sin fusionarlos;
- filtro por intervalo de años;
- filtro por superficie mínima;
- filtro por causa;
- municipios y causas canónicos, conservando sus valores de origen;
- enlaces compartibles que restauran mapa, periodo, fuentes y filtros;
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

La licencia y procedencia de los datos se documentan en `LICENSE_DATA.md`; las
fuentes, cartografía base y bibliotecas de terceros se recogen en
`THIRD_PARTY_LICENSES.md`.

### Ejecutar el visor local

El visor usa módulos JavaScript y `fetch`, por lo que no debe abrirse mediante
`file://`. Con los datasets locales generados:

```bash
.venv/bin/python scripts/build_frontend_profile.py --profile development
.venv/bin/python -m http.server 8000
```

Después se abre <http://localhost:8000/>. Este perfil puede usar ICV, SIGIF y
EFFIS locales; ningún dataset ignorado se incorpora por ello a Git.

Si se regeneran los derivados web desde processed, la capa canónica de filtros
se aplica después de los builders de ICV y recientes:

```bash
.venv/bin/python scripts/build_frontend_assets.py
.venv/bin/python scripts/build_recent_frontend_assets.py
.venv/bin/python scripts/filter_vocabularies.py
.venv/bin/python scripts/build_frontend_profile.py --profile development
```

El último comando de transformación usa el catálogo municipal oficial ICV del
snapshot CV-2.2, conserva los textos originales y deja sin resolver cualquier
correspondencia no demostrable.

### Reproducir el perfil público

El perfil público se rige exclusivamente por `config/sources-gva.json`: incluye
ICV y EFFIS y rechaza SIGIF porque continúa con `publishable=false`. El bundle
de datos permitido se publica como asset de la Release `public-data-v2`; su
tamaño, SHA-256 y lista exacta de 41 entradas están fijados en
`config/public-data-bundle.json`.

```bash
.venv/bin/python scripts/download_public_data_bundle.py
.venv/bin/python scripts/build_frontend_profile.py --profile public \
  --output data/web/gva/manifest.json
.venv/bin/python scripts/validate_frontend_assets.py
.venv/bin/python scripts/validate_recent_frontend_assets.py --public-only
.venv/bin/python scripts/build_public_site.py \
  --output data/derived/gva/publication/site
.venv/bin/python scripts/validate_public_site.py \
  --site data/derived/gva/publication/site
```

El resultado es un directorio estático autocontenido compatible con el subpath
`/atlas-incendios/`. Contiene 40 assets de datos: 38 ICV y 2 EFFIS. No contiene
snapshots raw, datos processed, benchmarks, SIGIF ni candidatos SIGIF–EFFIS.

### Despliegue

`.github/workflows/pages.yml` descarga y verifica el bundle de la Release,
compone únicamente el perfil `public`, ejecuta validadores, tests Python y
pruebas de navegador, construye un único artifact y lo despliega con GitHub
Pages. El workflow usa permisos mínimos de lectura de contenidos, escritura de
Pages e identidad OIDC; no necesita secretos del proyecto.

Los aproximadamente 73 MB sin comprimir de datos web no forman parte del
historial de `main`. Para actualizar datos públicos se debe generar un nuevo
bundle reproducible, revisar su manifiesto y publicar explícitamente una nueva
Release/versionar su referencia antes de desplegarlo.

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
