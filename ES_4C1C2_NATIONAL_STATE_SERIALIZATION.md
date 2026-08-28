# ES-4C1C2 — Serialización y restauración del estado nacional

Estado: implementado localmente; pendiente de revisión antes de la base
territorial ES-4C2A. Solo afecta al prototipo aislado `prototypes/es4c/`.
No modifica el permalink v1 ni ningún archivo del visor público valenciano.

## Formato

El hash del prototipo usa un contrato versionado, canónico y autocontenido:

```text
#es4c-state-v1=<JSON codificado en base64url>
```

El payload, antes de codificar, es:

```json
{
  "v": "es4c-state-v1",
  "map": { "lat": 39.3, "lon": -0.7, "z": 8 },
  "time": { "from": 1995, "to": 1995 },
  "territory": {
    "scope": "autonomous_community",
    "autonomous_community_id": "ES:CCAA:10"
  },
  "sources": { "esfire30": true, "egif": true },
  "selections": {
    "geometry_id": "esfire30:v1:1995:86",
    "egif_record_id": "egif-record:1995030001"
  }
}
```

Las coordenadas se redondean a cinco decimales y el zoom a dos. El orden de
las propiedades es fijo: el mismo estado lógico produce el mismo hash. La
implementación vive en `prototypes/es4c/state_serialization.mjs`.

Se serializan exclusivamente centro, zoom, rango solicitado, ámbito y CCAA,
visibilidad de fuente y las dos identidades de selección. No se serializan
cachés, assets cargados, ordinals, índices, métricas, errores ni estados de
cancelación.

## Restauración segura

Al cargar un hash reconocido, el runtime valida primero versión, años
1968–2023, orden del rango, coordenadas, zoom, territorio, booleanos e IDs.
Los valores corruptos se sustituyen por defaults seguros y las selecciones
malformadas se limpian. Una versión desconocida no se interpreta como v1: el
prototipo conserva sus defaults. Una URL sin hash abre los defaults actuales.

La restauración aplica rango, ámbito, fuentes y vista del mapa; después carga
solo los INITIAL EGIF que correspondan a la CCAA y bloques temporales del
rango. España continúa usando el resumen del manifest y no carga los
646.887 registros.

`selected_egif_record_id` se restaura únicamente si pertenece al INITIAL
cargado y al rango/ámbito activo. Entonces se resuelve `record_id → ordinal`,
se pide el DETAIL de su asset y se abre la ficha administrativa. Si falla,
solo se limpia esa selección.

`selected_geometry_id` se restaura únicamente si ESFire30 está visible, el
rango intersecta 1985–2021 y la geometría está disponible en las teselas
cargadas. No se infiere ni se busca una relación con EGIF. Ambas selecciones
pueden coexistir y se invalidan independientemente.

El ámbito CCAA sigue controlando solamente EGIF. ESFire30 no se presenta como
filtrado territorialmente porque el PMTiles de fidelidad aún no aporta una
relación administrativa documentada.

## URL e historial

Los cambios normales actualizan el hash mediante `history.replaceState`, sin
llenar el historial al mover el mapa. `hashchange` y `popstate` restauran el
estado de forma segura para atrás/adelante. El control de prototipo «Copiar
enlace» usa Clipboard API y muestra una URL seleccionable como fallback si el
navegador no concede permisos.

## Validación local

Pasaron los tests unitarios de serialización y los smokes dirigidos para:

- País Valencià 1995, España 1975 y País Valencià 2023;
- selección EGIF, DETAIL lazy y restauración de ficha;
- selección ESFire30 y ambas selecciones coexistentes;
- hash corrupto, atrás/adelante y viewport móvil 390×844.

Los resultados locales de Chromium son ignorados por Git. No se repitieron
benchmarks B5C, builds nacionales ni se regeneraron assets.

## Compatibilidad y límites

`es4c-state-v1` es deliberadamente independiente del permalink v1 publicado
del País Valencià. Una versión posterior podrá añadir, de forma opcional,
provincia, municipio, capas territoriales, otras fuentes y filtros de causa;
v1 nunca deberá interpretar esos campos como si ya los conociera.

La siguiente fase territorial necesita aportar un catálogo y relaciones
administrativas reutilizables, no derivar límites ni filtros a partir de los
incendios.
