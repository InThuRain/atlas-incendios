# Hoja de ruta

## Fase 0 — Repositorio y documentación

- [ ] Inicializar Git.
- [ ] Incorporar este kit de contexto.
- [ ] Guardar el prototipo actual como baseline.
- [ ] Crear estructura de carpetas estable.

## Fase 1 — Consolidar Mariola–Font Roja

Objetivo: tener un piloto local fiable y agradable de usar.

- [ ] Verificar que 1993–2024 carga correctamente.
- [ ] Corregir cualquier cambio de endpoint/campos del ICV.
- [ ] Descargar los datos del piloto a archivos locales para no depender del servicio en cada apertura.
- [ ] Normalizar atributos.
- [ ] Añadir selector de incendio.
- [ ] Mejorar “Historia de un lugar”.
- [ ] Calcular recurrencia en el área piloto.
- [ ] Mostrar fuente/calidad de geometría.
- [ ] Añadir URL/estado compartible si es razonable.

## Fase 2 — Completar cronología local

- [ ] Inventariar incendios 1976–1992 mediante EGIF.
- [ ] Identificar cuáles tienen perímetro histórico recuperable.
- [ ] Buscar planes de prevención y cartografía histórica.
- [x] CV-2.1: inventariar y diseñar la incorporación 2025–2026 sin alterar el
  consolidado 1993–2024.
- [x] CV-2.2: construir snapshots locales separados SIGIF/EFFIS para 2025–2026,
  demostrar `X1`/`Y1` como punto de inicio EPSG:25830, intersectar EFFIS con el
  límite oficial y generar únicamente candidatos puntuados.
- [ ] Obtener autorización escrita para redistribuir filas o derivados SIGIF;
  los snapshots CV-2.2 permanecen locales e ignorados por Git.
- [x] CV-2.3: integrar localmente 2025 como reciente administrativo provisional y EFFIS
  como geometría B separada; promover el perímetro ICV cuando se publique.
- [x] CV-2.3: integrar localmente 2026 como snapshot fechado e incompleto; cerrar el año y
  promoverlo solo cuando existan datos consolidados.
- [ ] Marcar calidad A/B/C/D.

## Fase 3 — Comunitat Valenciana

- [x] Descargar todas las capas 1993–2024.
- [x] Crear dataset único normalizado.
- [x] Auditar identidad, geometrías equivalentes y validez topológica del snapshot ICV normalizado.
- [ ] Cerrar con el ICV la redistribución de derivados: CV-1.5b verificó CC BY
  4.0 y la atribución, pero queda confirmar por escrito la aceptación expresa
  de cada receptor y la simplificación geométrica antes de publicar.
- [ ] Relacionar con EGIF cuando sea posible.
- [x] Probar rendimiento regional (CV-1.4: GeoJSON derivado, tres niveles,
  particionado y benchmark reproducible con Leaflet 1.9.4).
- [x] Sustituir el prototipo Mariola–Font Roja por el primer visor estático de
  toda la Comunitat Valenciana (CV-1.5: manifiesto, carga progresiva por zoom,
  provincia y bloque temporal, sin consultas ArcGIS en el navegador).
- [ ] Incorporar incendios sin geometría al modelo.

## Fase 4 — Modelo nacional

- [ ] Obtener EGIF en formato procesable.
- [ ] Diseñar identificador estable `fire_id`.
- [ ] Crear tabla nacional `fires`.
- [ ] Inventariar fuentes de perímetros por CCAA.
- [ ] Crear tabla `geometries`.
- [ ] Documentar cobertura y calidad por comunidad/año.

## Fase 5 — Rendimiento nacional

- [ ] Probar simplificación de geometrías.
- [ ] Probar PMTiles/vector tiles.
- [ ] Definir reglas por nivel de zoom.
- [ ] Medir tiempo de carga y memoria.
- [ ] Precalcular agregaciones.

## Fase 6 — Funciones avanzadas

- [ ] Historia de un territorio dibujado.
- [ ] Comparador temporal.
- [ ] Recurrencia continua.
- [ ] Estadísticas por municipio/provincia/CCAA.
- [ ] Buscador de incendios.
- [ ] Cruce con Mapa Forestal de España.
- [ ] Cruce con espacios protegidos.

## Fase 7 — Publicación

- [ ] Licencias y atribución.
- [ ] Página de metodología.
- [ ] Limitaciones conocidas.
- [ ] Política de actualización.
- [ ] Despliegue público.
