# ES-4C2A3C — Runtime municipal nacional (prototipo aislado)

## Resultado

Se incorpora en `prototypes/es4c/` la navegación municipal actual BDLJE sin
modificar el visor público, datos públicos, PMTiles ni relaciones ESFire30.
La estrategia **catálogo ligero nacional + GeoJSON 0 m por provincia bajo
demanda** queda `RECOMMENDED` para este runtime experimental.

## Inputs cerrados

Se reutilizan únicamente los derivados ES-4C2A3B:

- catálogo: `data/territories/spain/municipality_catalog_2026-08-29.json`;
  8.132 municipios, 1.984.280 B raw / 327.282 B gzip;
- 52 shards GeoJSON BDLJE actuales 0 m: 50 provinciales y los específicos de
  Ceuta y Melilla; total 146.194.941 B raw / 46.664.000 B gzip;
- geometrías BDLJE entregadas ya como `MultiPolygon`. El runtime conserva
  literalmente el GeoJSON 0 m, sin simplificación ni normalización.

No se carga `municipality-level.geojson` nacional en el navegador.

## Carga y caché

`municipality_loader.mjs` carga el catálogo la primera vez que una provincia,
ciudad autónoma o URL municipal lo requiere; España y una CCAA sin provincia
no lo cargan por defecto. Resuelve `asset_id` a un único shard y mantiene una
caché de sesión `asset_id → GeoJSON`.

Una provincia carga solo su shard. Ceuta y Melilla cargan sus propios shards,
sin crear una provincia ficticia. `AbortController` y un token de generación
impiden que una respuesta antigua reemplace el estado nuevo; el test unitario
verifica esa condición y el smoke Barcelona→Girona termina en Girona.

La capa GeoJSON municipal es independiente de PMTiles. Presenta límites,
click, resaltado y `fitBounds` con los bounds exactos 0 m guardados en el
catálogo, no con incendios, centroides ni geometrías ESFire30.

## Estado y URL

`es4c-state-v1` admite el campo opcional compatible `municipality_id`:

- `ES`: CCAA, provincia y municipio nulos;
- `autonomous_community`: solo CCAA;
- `province`: CCAA y provincia;
- `municipality`: municipio y sus padres canónicos.

Una URL antigua sigue siendo válida. Al restaurar una URL municipal se valida
el crosswalk catálogo/ES-2, carga exclusivamente el shard padre, restaura el
resaltado y conserva el `center`/`zoom` de la URL: no ejecuta `fitBounds`.

## EGIF y semántica histórica

EGIF conserva `source_record` sin geometría. Tras cargar el INITIAL existente
`CCAA × bloque`, el filtro aplica exactamente `año AND province_id (si existe)
AND municipality_id`. Un `municipality_id = null` no coincide con ningún
municipio y no se infiere por nombre, geometría, CCINIF ni coordenadas.

El texto del prototipo dice: **“Partes EGIF enlazadas documentalmente al
municipio canónico.”** No significa que todos los hechos estuvieran dentro del
polígono actual. Cuando se consulta historia, los límites BDLJE mostrados son
la división administrativa actual, no una geometría municipal histórica.

Para Elx (`ES:MUN:03065`), 1993–2002, el smoke obtiene 49 partes, 0 GIF,
71,86 ha forestales conocidas, 49 con municipio resuelto y 0 nulas. La suma
solo agrega superficies conocidas: `null` nunca se convierte en cero.

## ESFire30 en ámbito municipal

No existe todavía una relación validada `geometry_id → municipality_id`.
En ámbito municipal el límite y EGIF son municipales actuales; ESFire30 sigue
con el filtro territorial validado del padre provincial (o CCAA para una ciudad
autónoma). La UI lo explicita: **“ESFire30: filtrado territorial disponible
hasta provincia; filtrado municipal pendiente.”** Entrar en municipio no
desactiva ESFire30 ni afirma que un perímetro interseca ese municipio. Las
selecciones `geometry_id` y `record_id` permanecen independientes.

## Diagnóstico local

Smokes Chromium locales dirigidos:

- Alacant → Elx: shard `ES:PROV:03`, 775.913 B raw INITIAL EGIF; límite,
  bounds, filtro municipal y Range PMTiles correctos.
- Barcelona: shard municipal mayor, 10.490.788 B raw / 3.334.456 B gzip;
  fetch local ~155,7 ms, parse ~45,9 ms; límite utilizable sin error. El heap
  observado (~249 MB delta desde el arranque) es diagnóstico de Chromium local,
  no presupuesto de producto.
- Barcelona → Girona: el estado final pertenece a Girona; no hubo error.
- Elx en viewport emulado 390×844: selector, breadcrumb, límite y mapa
  utilizables.

No son un benchmark nacional ni emulan CPU, red o dispositivos físicos.

Los controles de geometría preservan 0 m: Llocnou de la Corona, Ademuz,
Llívia, Condado de Treviño y La Puebla de Arganzón. La Puebla es
`ES:MUN:09276`, provincia de Burgos (`ES:PROV:09`), no Álava; el runtime usa
el crosswalk documental y no la reasigna por proximidad.

## Límites y continuación

No hay filtro ESFire30 municipal, relaciones espaciales municipales, municipios
históricos ni resolución de los 71.490 partes EGIF con municipio nulo. El
siguiente diseño, si se revisa este prototipo, es
`ES-4C2B3A_ESFIRE30_MUNICIPAL_RELATION_DESIGN`; deberá tratar la cardinalidad
municipal N:M sin asumir slots fijos `mun_1..mun_3`.
