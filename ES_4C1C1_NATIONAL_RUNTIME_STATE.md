# ES-4C1C1 — Estado coordinado y coberturas temporales

Estado: implementado localmente; pendiente de revisión antes de ES-4C1C2.

## Contrato de estado

El prototipo aislado `prototypes/es4c/` usa un estado central explícito:

```text
from, to,
territory_scope, autonomous_community_id,
esfire30_visible, egif_visible,
selected_geometry_id, selected_egif_record_id
```

El estado conserva también los años de las selecciones exclusivamente para
invalidarlas cuando dejan de ser visibles. No son una identidad adicional ni
forman parte de un permalink.

`runtime_state.mjs` centraliza el reducer y las intersecciones de cobertura.
Los controles HTML, el filtro MapLibre, el cargador INITIAL y las selecciones
actualizan o leen este estado; no mantienen rangos independientes.

## Cobertura y semántica

| Fuente | Cobertura declarada | Entidad | Comportamiento |
|---|---|---|---|
| EGIF | 1968–2023 | partes administrativos | INITIAL por CCAA × bloque; España usa solo manifest |
| ESFire30 | 1985–2021 | perímetros Landsat de teledetección | filtro temporal dentro de PMTiles |

Cada fuente calcula por separado `intersection(user_range, source_coverage)`.
El rango solicitado no se modifica: para 1980–1990, EGIF trabaja 1980–1990 y
ESFire30 1985–1990. La interfaz conserva el intervalo pedido y declara la
cobertura efectiva de cada fuente. Sin intersección se muestra “sin cobertura”,
nunca “0 incendios”.

Los toggles son independientes:

- desactivar ESFire30 oculta sus geometrías y limpia solo
  `selected_geometry_id`;
- desactivar EGIF aborta/cancela su carga, oculta su panel/lista/ficha y limpia
  solo `selected_egif_record_id`;
- ninguno modifica el periodo solicitado ni crea enlaces entre fuentes.

Al modificar rango, ámbito o visibilidad, el reducer invalida una selección
solo cuando ya no pertenece a la cobertura, periodo o ámbito correspondiente.
AbortController, token de generación y cachés de C1B1/C1B2 permanecen activos;
una respuesta INITIAL o DETAIL obsoleta no puede sobrescribir el estado nuevo.

## Ámbito territorial actual

El selector mantiene España y CCAA/ciudad autónoma. En esta fase el ámbito
controla la partición administrativa de EGIF y sus resúmenes/cargas. El PMTiles
ESFire30 de fidelidad solo conserva `geometry_id` y `year`; no incluye una
relación administrativa reutilizable. Por rigor, C1C1 **no finge** filtrar los
perímetros ESFire30 por CCAA ni calcula límites a partir de incendios.

Por tanto, el ámbito es estado compartido del runtime, pero el efecto espacial
administrativo de ESFire30 queda pendiente de una relación territorial
documentada en una fase posterior. ESFire30 continúa como capa nacional en el
viewport, filtrada por cobertura y año.

## Casos validados

| Caso | EGIF | ESFire30 | INITIAL EGIF |
|---|---|---|---:|
| España · 1975 | manifest 1975 | sin cobertura | 0 |
| País Valencià · 1975 | parte cargada del bloque 1968–1979 | sin cobertura | 1 |
| País Valencià · 1995 | parte cargada | perímetros 1995 | 1 |
| País Valencià · 2023 | parte cargada | sin cobertura | 1 |
| País Valencià · 1980–1990 | 1980–1990 | cobertura efectiva 1985–1990 | 1 |

También pasaron los toggles EGIF/ESFire30, cambio rápido 1975→1995 y un caso
mixto con viewport 390×844. No se repitieron ES-3, B5C ni builds de assets.

## Límites mantenidos

- no hay nuevas fuentes, relaciones EGIF–ESFire30 ni candidate links;
- no hay CCINIF, límites, provincias, municipios ni auto-fit;
- no hay permalink nacional ni cambios de producción;
- no hay contador conjunto denominado “incendios”.

## Próxima fase

ES-4C1C2 debe abordar, como máximo, serialización/restauración de este estado
o el siguiente contrato explícito aprobado. Antes de filtrar ESFire30 por CCAA
debe existir una relación territorial documentada para sus geometrías; no se
debe inferir desde la cobertura de incendios.
