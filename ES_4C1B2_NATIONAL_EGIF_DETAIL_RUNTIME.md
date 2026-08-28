# ES-4C1B2 — Selección EGIF y DETAIL lazy

Estado: implementado localmente; pendiente de revisión antes de ES-4C1C.

## Alcance

Este cambio vive exclusivamente en `prototypes/es4c/`. No modifica el visor
público valenciano, `public-data-v5`, workflows, GitHub Pages ni los assets
nacionales ya generados.

EGIF sigue modelado como `source_record` administrativo. Sus partes no tienen
geometría en este runtime. Una selección EGIF (`selected_egif_record_id`) es
independiente de una selección ESFire30 (`selected_geometry_id`): no se crea
ningún enlace, resaltado ni inferencia entre ambas.

CCINIF y sus relaciones siguen excluidos: no se leen ni se exponen referencias
espaciales históricas.

## Flujo de datos

1. C1B1 carga solo los assets `INITIAL` necesarios para `CCAA × bloque`.
2. La lista técnica opera sobre columnas y muestra 50 filas por página; no
   materializa todos los registros en objetos JavaScript.
3. El clic o la búsqueda directa usa el `record_id` estable
   `egif-record:<NumeroParte>` para resolver `asset_id → ordinal`.
4. Solo entonces `EGIFDetailLoader` solicita el `detail.json` del mismo asset.
   Valida `asset_id`, el hash del orden de `record_id`, la alineación ordinal y
   la longitud de las columnas antes de extraer una única fila.
5. DETAIL se conserva en caché de sesión por `asset_id`: una segunda selección
   del mismo asset no genera otra descarga.

La carga DETAIL usa `AbortController` y un token de generación. Si A y B se
seleccionan rápidamente, la respuesta de A puede acabar en red, pero nunca
puede sustituir la ficha de B. Cambiar CCAA o periodo limpia la selección EGIF
si deja de pertenecer al ámbito activo. Un fallo DETAIL queda restringido a la
ficha: INITIAL y ESFire30 permanecen operativos.

## Ficha administrativa mínima

La ficha muestra solo campos aprobados para selección:

- identidad, año, `NumeroParte`/ID fuente y fuente EGIF;
- fechas disponibles;
- CCAA, provincia y municipio canónicos desde el snapshot territorial ES-2,
  cargado bajo demanda; el nombre municipal original queda separado;
- paraje y superficies declaradas disponibles;
- GIF administrativo EGIF, sin inferirlo de ESFire30;
- `cause_source_code` como código EGIF, `canonical_cause = null` y
  `cause_mapping_status = unmapped` mientras no haya diccionario MITECO;
- modelo de parte, ID de base fuente e identidad de episodio no resuelta.

Una superficie `null` se presenta como no disponible y no como `0 ha`. Un
municipio `null` se muestra como “Municipio no resuelto en la normalización”;
si la fuente conserva un nombre declarado se muestra como dato original, sin
intentar resolverlo de nuevo.

## Validación local dirigida

Se ejecutaron ocho smokes Chromium, no la batería B5C:

| Caso | Resultado |
|---|---|
| País Valencià 1993–2002, primera selección | 1 INITIAL + 1 DETAIL; ficha correcta |
| Segunda selección del mismo asset | 0 descargas DETAIL adicionales; caché usada |
| Cambio a 2003–2012 | carga solo el DETAIL del bloque nuevo |
| Municipio null | conserva `null`; no se inventa municipio |
| Causa sin mapping | `canonical_cause = null`, `unmapped` |
| Selección rápida A → B | la ficha final corresponde a B |
| ESFire30 + EGIF | `geometry_id` y `record_id` coexisten sin enlace |
| 390×844 | lista paginada y ficha visibles y operables |

Para el asset valenciano 1993–2002, el primer DETAIL observado fue 712.599 B
raw / 89.549 B gzip; fetch local ~89 ms y parse ~7,4 ms. El delta de heap fue
diagnóstico y no estable por GC, por lo que no se usa para una conclusión de
rendimiento. El bloque valenciano 2003–2012 midió 645.760 B raw. No se ha
optimizado ningún formato.

## Límites mantenidos

- no hay popup, punto ni perímetro EGIF;
- no hay geometría, cuadrícula, relación candidate ni identidad compartida;
- no hay filtro profundo de provincia/municipio ni permalink público;
- la tabla y ficha son herramientas técnicas del prototipo, no UX final.

## Próxima fase necesaria

ES-4C1C deberá decidir de forma separada cómo evolucionar estado y controles
territoriales sin cambiar estos contratos ni convertir partes EGIF en
geometrías.
