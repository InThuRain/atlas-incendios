# AGENTS.md

## Rol del agente

Actúa como desarrollador y asistente de investigación para un atlas histórico de incendios forestales de España.

Antes de hacer cambios relevantes, lee:

- `PROJECT_CONTEXT.md`
- `DATA_SOURCES.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `DECISIONS.md`

## Reglas obligatorias

### Datos y rigor

1. **No inventes geometrías, fechas, superficies, causas ni identificadores.**
2. Prioriza fuentes oficiales y documenta siempre el origen de los datos.
3. Mantén separados:
   - el incendio como registro estadístico;
   - el perímetro o geometría asociado.
4. Un incendio puede existir sin perímetro fiable. No lo elimines por ello.
5. Si hay varias geometrías para un mismo incendio, conserva procedencia, fecha y calidad de cada una.
6. Cuando una fuente tenga cobertura incompleta, indícalo explícitamente.
7. No conviertas una reconstrucción histórica en “perímetro oficial”.

### Calidad geométrica

Usa esta clasificación salvo que el proyecto la cambie explícitamente:

- **A** — perímetro oficial vectorial.
- **B** — perímetro derivado de teledetección o cartografía técnica con precisión documentada.
- **C** — reconstrucción histórica razonable y documentada.
- **D** — incendio conocido sin perímetro fiable.

Para `D`, usar punto, municipio, cuadrícula o ausencia de geometría según la información disponible. Nunca dibujar un polígono aproximado sin justificarlo y marcarlo como C.

### Arquitectura

1. No diseñes la versión nacional como 30 servicios GIS consultados en tiempo real desde el navegador.
2. Favorece ingestión, normalización y almacenamiento propios.
3. A escala nacional usa geometrías simplificadas o teselas vectoriales.
4. A escala local permite geometría completa.
5. Separa datos de aplicación.
6. Evita introducir dependencias grandes sin una razón clara.
7. Mantén la aplicación usable con decenas de miles de incendios.

### Rendimiento

Pensar siempre en tres escalas:

- España: datos ligeros y grandes incendios / geometría muy simplificada.
- Región/provincia: más detalle y más incendios.
- Escala local: perímetros completos y análisis espacial fino.

No cargar todas las geometrías completas de España al inicio.

### UX

El usuario debe poder entender en todo momento:

- qué periodo está viendo;
- qué filtros hay activos;
- qué fuente tiene cada incendio;
- si el perímetro es oficial o reconstruido;
- cuántas hectáreas se muestran;
- si hay incendios conocidos sin perímetro.

### Cambios de código

Antes de una refactorización grande:

1. explica qué problema resuelve;
2. indica qué archivos cambiarás;
3. conserva comportamiento previo salvo que exista una razón documentada;
4. añade pruebas o validaciones razonables cuando sea posible.

### Git

- commits pequeños y descriptivos;
- no mezclar limpieza, funcionalidad y cambios de datos en un mismo commit si puede evitarse;
- no reescribir historia sin petición explícita.

## Estilo del proyecto

Preferir soluciones comprensibles y mantenibles frente a optimizaciones prematuras.

Para el prototipo web actual se acepta JavaScript vanilla. Si se migra a framework, justificar la migración en `DECISIONS.md`.
