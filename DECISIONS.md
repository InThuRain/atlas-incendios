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

## Plantilla para nuevas decisiones

```markdown
## YYYY-MM-DD — Título

Decisión.

**Motivo:** ...

**Consecuencias:** ...
```
