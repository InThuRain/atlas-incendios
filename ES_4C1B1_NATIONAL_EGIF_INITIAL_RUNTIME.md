# ES-4C1B1 — Loader EGIF INITIAL en el prototipo nacional

Fecha: 28/08/2026  
Estado: prototipo local aislado; pendiente de revisión. No publicado.

## Alcance

Esta subfase incorpora exclusivamente los registros columnarios `INITIAL` de
EGIF al laboratorio `prototypes/es4c/`. No añade DETAIL, ficha o selección de
partes, geometrías EGIF, CCINIF, relaciones territoriales, municipios/provincias
como filtros ni vínculo alguno con ESFire30.

La separación visible se conserva:

| Fuente | Qué representa |
|---|---|
| ESFire30 | perímetros Landsat de teledetección; no oficiales |
| EGIF | partes administrativos; sin geometría en este runtime |

El panel nunca suma ambos como «incendios totales».

## Política de carga

El manifest local reutilizado es
`data/web/spain/egif/2026-08-27/manifest.json` (88 assets, 646.887 partes).
No se regenera ni modifica. El loader aplica estas reglas explícitas:

- **España:** suma exactamente los `year_spools` del manifest para el rango
  solicitado y muestra bloques implicados. No solicita ningún `initial.json`.
- **CCAA o ciudad autónoma:** resuelve solo `EGIF × territorio × bloque` que
  intersecten `[from, to]`, solicita solo sus `initial.json` y filtra después
  por año exacto sobre la columna `year`.
- Los bloques son 1968–1979, 1980–1992, 1993–2002, 2003–2012 y 2013–2023.
  Así 1995–1998 carga solo 1993–2002 y 2000–2005 cargaría dos bloques.
- La partición se determina por la CCAA administrativa del parte. No depende
  de geometrías ni de relaciones CCINIF.

La lista mínima de CCAA/ciudades autónomas es un derivado de nombres e IDs del
snapshot territorial ES-2; no carga los 3,7 MB de municipios del snapshot para
este control simple.

## Implementación

`prototypes/es4c/egif_initial_loader.mjs` mantiene el formato columnar:

```text
asset INITIAL
  columns.record_id ──► Map(record_id → ordinal)
  columns.year / GIF / superficie forestal / municipality_id
                    └──► estadísticas y filtro directo por ordinal
```

No materializa un array de objetos por parte. El `Map` se crea una vez al
cargar el asset y queda en una cache de sesión por `asset_id`; una segunda
consulta compatible reutiliza el asset mientras siga presente. La cache no
implementa aún eviction.

Cada `loadScope` incrementa un token de generación y aborta el `fetch` previo
mediante `AbortController`. Una respuesta obsoleta devuelve `status=stale` y
no puede reemplazar el ámbito más reciente. En localhost una transferencia ya
iniciada puede haber terminado en el servidor antes de que el aborto la corte;
la garantía de esta fase es de estado, no de ahorro retroactivo de bytes.

Un fallo de manifest/asset EGIF muestra un error en su panel sin detener el
mapa ESFire30. El loader solo referencia `initial.path`; no existe una ruta a
`detail.path` en esta subfase.

## Estado y filtros

El estado aislado queda preparado con:

```text
center, zoom, from, to,
territory_scope, autonomous_community_id,
selected_geometry_id
```

El rango común ahora admite 1968–2023. Afecta independientemente a:

- ESFire30: expresión de filtro MVT limitada a su cobertura 1985–2021.
- EGIF: selección de bloques y filtro columnar exacto hasta 2023.

Compartir rango no establece identidad entre fuentes. No hay
`selected_egif_record_id` ni permalink nacional todavía.

Para una CCAA cargada el panel muestra partes, GIF administrativos (basados
solo en superficie forestal EGIF >=500 ha), suma de superficie forestal de
valores conocidos, partes con superficie desconocida, partes con municipio
resuelto/no resuelto y distribución anual. `null`/unknown no se convierte en
0 ha: el contrato conserva `known_forest_area_sum`,
`records_with_known_forest_area` y `records_with_unknown_forest_area`. Los
códigos de causa se conservan en columnas pero no se exponen como selector ni
UX final mientras el diccionario MITECO siga pendiente.

## Smokes locales ejecutados

Las salidas locales están ignoradas en `prototypes/es4c/*-smoke-results.json`.
Se ejecutaron solo los seis casos solicitados; no se repitió ES-3 ni B5C.

| Caso | Resultado EGIF | INITIAL | Raw local | Gzip manifest | Fetch / parse | Heap Δ tras carga |
|---|---:|---:|---:|---:|---:|---:|
| España 1993–2002 | 200.513 partes desde manifest | 0 | 0 B | 0 B | no aplica | no aislado |
| País Valencià 1993–2002 | 5.159 partes | 1 | 775.913 B | 35.816 B | 93,9 / 3,7 ms | 37.529.655 B |
| Galicia 1993–2002 | 110.605 partes | 1 | 16.610.507 B | 572.974 B | 160,6 / 80,9 ms | 79.431.286 B |
| Galicia 2013–2023 | 20.850 partes | 1 | 3.143.799 B | 129.108 B | 70,3 / 12,9 ms | 46.136.816 B |
| Galicia → La Rioja rápido, 1993–2002 | 1.191 partes finales (La Rioja) | 2 iniciados | 16.790.228 B | 8.932 B final | 100,4 / 0,8 ms final | no comparable |
| País Valencià 1993–2002, 390×844 | 5.159 partes | 1 | 775.913 B | 35.816 B | 99,1 / 3,2 ms | 37.411.903 B |

En los seis casos, `DETAIL requests = 0`; el mapa PMTiles siguió usando Range
sin descargar el archivo completo. El caso rápido confirmó
`obsolete_status=stale`, `current_status=complete` y ámbito final
`ES:CCAA:17`. El segundo request Galicia ya había comenzado en localhost, por
lo que el servidor contó ambos INITIAL; no actualizó el estado ni se incluyó
en las estadísticas finales de La Rioja.

La medición de heap no se convierte en benchmark nuevo: C1B1 registra tamaños,
fetch y parse de los dos casos significativos y conserva B5C como referencia
de rendimiento. En particular, no hay excepción hardcoded para Galicia: el
intervalo determina siempre los bloques solicitados.

## Validación

```bash
python3 -m unittest tests/test_es4c1b1_egif_initial_loader.py -q
python3 prototypes/es4c/run_smoke.py --all-egif-smokes \
  --output prototypes/es4c/egif-initial-smoke-results.json
python3 prototypes/es4c/run_smoke.py --check \
  --output prototypes/es4c/egif-initial-smoke-results.json
```

Las dos pruebas específicas verifican intersección de bloques, resolver del
manifest, resumen, filtros columnares, lookup, cache, cancelación y ausencia
de DETAIL/producción. Los seis smokes completaron sin errores funcionales.

## Siguiente fase

ES-4C1B2 deberá añadir exclusivamente selección de una parte EGIF y DETAIL
lazy por el mismo ordinal del INITIAL. Deberá conservar la separación con
`geometry_id` ESFire30, no crear geometrías ni enlaces, y medir primera y
segunda selección sin cambiar la política de carga de C1B1.
