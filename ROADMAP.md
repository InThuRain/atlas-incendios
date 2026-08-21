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

- [x] CV-3.1: inventariar incendios 1968–1992 mediante EGIF, cuantificar los
  9.175 registros valencianos y documentar las rupturas de cobertura y esquema.
- [x] CV-3.2: descargar un snapshot EGIF 1968–1992 reproducible, verificarlo
  contra los recuentos CV-3.1, auditar los seis esquemas históricos y crear
  registros `fires` sin inferir perímetros.
- [x] CV-3.2: cuantificar municipio, superficie, coordenadas, CRS, duplicados e
  identificadores problemáticos por provincia/año; contrastar completamente el
  anuario definitivo de 1992 y generar un índice OCR de los 25 anuarios.
- [ ] CV-3.3: generar derivados web ligeros de los partes EGIF históricos e
  integrarlos en timeline, métricas y listados como registros sin geometría,
  mostrando régimen de cobertura y sin contar partes como episodios físicos
  únicos.
- [ ] Completar la transcripción y contraste controlado de los anuarios
  definitivos 1968–1991; el OCR de CV-3.2 solo localiza tablas candidatas.
- [ ] Auditar identidad de episodios multiparte, empezando por Marines–Altura
  1992 y los seis pares de atributos idénticos, sin fusionar por proximidad.
- [ ] Identificar cuáles tienen perímetro histórico recuperable.
- [ ] Buscar planes de prevención y cartografía histórica.
- [ ] Solicitar a Generalitat/ICV y parques la cartografía histórica fuente de
  Chera–Sot de Chera y Mariola–Font Roja, incluida metodología, escala, CRS y
  condiciones de reutilización.
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
- [x] Cerrar con el ICV la redistribución de derivados: aclaración escrita del
  20/08/2026 confirma CC BY 4.0, redistribución pública, aceptación tácita,
  transformaciones declaradas y atribución a Generalitat.
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

- [x] UX-1 / DATA-UX-1: normalizar municipios y causas para filtros, añadir
  permalink versionado y retirar Mariola–Font Roja de la navegación territorial
  principal sin eliminar su acceso técnico.
- [x] Auditar los 244 registros municipales inicialmente no resueltos y cerrar
  UX-1 con un bundle público reproducible, guard de publicación y permalinks
  verificados en sesión nueva.
- [x] UX-2: simplificar la columna lateral, integrar ámbito y provincia en
  Filtros, restaurar las barras anuales, corregir la selección compartida visual
  y su popup, autoencuadrar municipios y evaluar el periodo completo como estado
  inicial.
- [ ] Historia de un territorio dibujado.
- [ ] Comparador temporal.
- [ ] Recurrencia continua.
- [ ] Estadísticas por municipio/provincia/CCAA.
- [ ] Buscador de incendios.
- [ ] Cruce con Mapa Forestal de España.
- [ ] Cruce con espacios protegidos.

## Fase 7 — Publicación

- [x] Licencias y atribución del perfil público ICV + EFFIS verificadas y
  accesibles desde el visor.
- [x] Página/panel de fuentes y metodología accesible en la primera versión.
- [x] Provisionalidad EFFIS, distinta autoridad de fuentes y limitaciones de
  recurrencia visibles.
- [ ] Política de actualización.
- [x] Primera versión pública desplegada y comprobada en
  <https://inthurain.github.io/atlas-incendios/> mediante GitHub Actions y el
  perfil `public`; SIGIF, candidatos y datasets internos quedan excluidos.
