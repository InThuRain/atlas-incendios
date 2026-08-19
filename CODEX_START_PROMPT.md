# Prompt de inicio para Codex

Usa este texto al abrir el proyecto en una sesión nueva de Codex:

> Lee primero `AGENTS.md`, `PROJECT_CONTEXT.md`, `DATA_SOURCES.md`, `ARCHITECTURE.md`, `ROADMAP.md` y `DECISIONS.md`. Después inspecciona el código actual sin modificar nada. Resume en 10-15 puntos qué hace el proyecto, qué decisiones arquitectónicas están fijadas, qué riesgos detectas y cuál debería ser el siguiente cambio pequeño y verificable. No inventes fuentes ni datos. Mantén separada la información estadística de los incendios y sus geometrías.

## Prompt para continuar desarrollo

> Continúa desde la documentación del repositorio. Antes de tocar código, indica brevemente qué archivos vas a cambiar y qué criterio usarás para verificar que no rompes el comportamiento existente. Implementa un solo objetivo del ROADMAP por vez y actualiza `DECISIONS.md` únicamente si introduces una decisión arquitectónica nueva.

## Prompt para una sesión de datos

> Lee la documentación del proyecto. Trabaja solo en el pipeline de datos. Conserva siempre la procedencia, no inventes geometrías y registra cobertura y calidad. Si encuentras discrepancias entre fuentes, no las resuelvas silenciosamente: documenta ambas y propone una regla explícita.
