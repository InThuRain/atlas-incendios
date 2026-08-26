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
- [x] CV-3.3: generar derivados web ligeros de los partes EGIF históricos e
  integrarlos en timeline, métricas y listados como registros sin geometría,
  mostrando régimen de cobertura y sin contar partes como episodios físicos
  únicos. Implementación y perfil público candidato validados localmente el
  23/08/2026; el bundle y despliegue se realizan separadamente en CV-3.4.
- [x] CV-3.4: publicar el perfil histórico 1968–2026 mediante el bundle
  inmutable `public-data-v4`, con EGIF + ICV + EFFIS y verificación real de
  GitHub Pages el 23/08/2026; SIGIF y candidatos permanecen excluidos.
- [x] CV-3.5: auditar los campos espaciales EGIF 1968–1992 y documentar que
  8.565 partes conservan pares hoja/cuadrícula nominales de 10 × 10 km, pero
  ninguno es representable todavía al faltar la clave cartográfica histórica,
  datum, husos y reglas de borde; no se han creado geometrías.
- [x] CV-3.6: investigar documentalmente la clave hoja/cuadrícula histórica.
  Se confirma la base UTM/ED50 de la serie militar y la existencia de un patrón
  ICONA, pero el patrón y la migración de códigos no están disponibles. CV-3.6b
  identifica la capa operativa `Hc250LL` y corrige la lectura de numeración: los
  valores `0704`/`0804` son compatibles con la serie 5L 1:250.000. No se ha
  localizado el activo, su CRS ni la clave `A01`–`O12`; se preparan consultas,
  sin enviarlas, y no se crean geometrías.
- [x] Resolver la clave operativa mediante entrega directa de CCINIF: ES-1.5
  recibe y audita `HOJAS.kmz`/`CUADRICULAS.kmz` y permite relaciones exactas
  `HOJA+CUAD`→celda. La posible genealogía con `Hc250LL`, `.csf` o `COD_INB`
  queda como contexto histórico, no como requisito para usar el activo oficial
  recibido. La licencia de redistribución sigue pendiente por separado.
- [ ] Completar la transcripción y contraste controlado de los anuarios
  definitivos 1968–1991; el OCR de CV-3.2 solo localiza tablas candidatas.
- [ ] Auditar identidad de episodios multiparte, empezando por Marines–Altura
  1992 y los seis pares de atributos idénticos, sin fusionar por proximidad.
- [ ] Identificar cuáles tienen perímetro histórico recuperable.
- [ ] Buscar planes de prevención y cartografía histórica.
- [x] CV-4.1: inventariar fuentes de perímetros anteriores a 1993. Se localizan
  710 polígonos Landsat ESFire30 para 1985–1992 y se documenta un archivo
  oficial valenciano desde 1978 aún no disponible; no se crean geometrías ni
  enlaces EGIF confirmados.
- [x] CV-4.2: adquirir y auditar ESFire30 v1. Se resuelve EPSG:23030 frente al
  EPSG:25830 erróneo del README mediante `.prj` y 450 controles ICV; los 710
  polígonos valencianos 1985–1992 son topológicamente utilizables y candidatos
  B de teledetección bajo CC BY 4.0. EGIF permanece separado: 3 enlaces fuertes,
  34 posibles, 3 débiles y 0 confirmados. No se integra ni publica geometría.
- [x] CV-4.3: integrar localmente ESFire30 1985–1992 como 710 perímetros B
  independientes, con identidad estable por contenido, transformación
  EPSG:23030 fail-closed, tres LOD, relaciones territoriales derivadas,
  simbología y métricas separadas. Development y public candidato pasan tests
  y benchmarks; no se ha creado bundle ni publicado.
- [x] CV-4.4: publicar EGIF + ESFire30 + ICV + EFFIS mediante el bundle
  inmutable `public-data-v5`, reproducido dos veces con el mismo SHA-256 y
  verificado en GitHub Pages el 26/08/2026. SIGIF, candidatos, raw, processed,
  diagnósticos y benchmarks permanecen fuera.
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

- [x] ES-1: auditar viabilidad nacional sin modificar el piloto; contar
  646.887 partes EGIF expuestos para 1968–2023, medir los 119.498 polígonos
  ESFire30, inventariar fuentes oficiales de 19 territorios y proponer ES-v1.
- [x] ES-1.5: auditar la malla histórica entregada por CCINIF. El cruce exacto
  enlaza 626.957 partes a 5.183 celdas oficiales distintas; los 270 pares
  valencianos quedan confirmados. Las celdas son referencias documentales,
  nunca perímetros, y permanecen fuera de publicación.
- [x] ES-2: definir contratos nacionales v1 para registros, geometrías,
  referencias históricas, territorios, relaciones, candidatos, fuentes y
  assets; versionar el snapshot nominal INE de 01/01/2026 (8.132 municipios),
  generalizar el guard fail-closed y validar País Valencià, Navarra y Canarias
  sin modificar el visor público.
- [ ] ES-3: prototipo nacional aislado de ESFire30 con geometrías únicas,
  relaciones territoriales y benchmark GeoJSON particionado frente a
  PMTiles/vector tiles; no publicar ni migrar el piloto antes de decidir con
  medidas.
- [ ] Obtener de CCINIF permiso escrito y atribución para redistribuir una
  selección GeoJSON/derivada de la malla; mantener
  `publishable=false_pending_permission` hasta entonces.
- [ ] Auditar con CCINIF la ausencia de `HOJA` en `CUADcanarias` antes de
  intentar resolver los 3.463 partes que quedan `C_AMBIGUOUS`.
- [ ] Obtener EGIF en formato procesable.
- [ ] Diseñar identificador estable `fire_id`.
- [ ] Crear tabla nacional `fires`.
- [ ] Inventariar fuentes de perímetros por CCAA.
- [ ] Crear tabla `geometries`.
- [ ] Documentar cobertura y calidad por comunidad/año.

## Fase 5 — Rendimiento nacional

- [x] ES-1: benchmark diagnóstico Leaflet + GeoJSON nacional, territorial,
  anual y móvil; el overview monolítico añade ~459 MiB de heap y justifica
  probar teselas en ES-3 sin migrar todavía el visor.
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
  inicial. Publicada y verificada en GitHub Pages el 21/08/2026 mediante el
  bundle reproducible `public-data-v3`.
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
- [x] Versión pública 1968–2026 desplegada y comprobada en
  <https://inthurain.github.io/atlas-incendios/> mediante GitHub Actions y el
  perfil `public` y `public-data-v4`; SIGIF, candidatos y datasets internos
  quedan excluidos.
