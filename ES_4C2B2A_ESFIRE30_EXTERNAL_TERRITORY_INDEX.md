# ES-4C2B2A — Índice territorial externo ESFire30

## Derivado y contrato

El generador [`scripts/build/esfire30/territory_runtime_index.py`](scripts/build/esfire30/territory_runtime_index.py) consume exclusivamente los JSONL auditados C2B1A/B. No abre geometrías, no recalcula intersecciones y conserva las 242.734 relaciones positivas, incluidos todos los slivers.

El derivado local ignorado `data/derived/spain/es4c2b/runtime/territory-index.json` contiene únicamente arrays ordenados:

```text
ccaa_id      → [geometry_id…]
province_id  → [geometry_id…]
```

Se reconcilia exactamente con 119.498 `geometry_id`, 120.847 relaciones CCAA y 121.887 provinciales, sin duplicados. Significa “perímetro ESFire30 que intersecta el territorio”, nunca pertenencia administrativa o vínculo EGIF.

## Tamaños medidos

| Variante | Raw | Gzip |
| --- | ---: | ---: |
| Runtime inverso directo C/D | 5.749.424 B | 616.317 B |
| Forward `geometry_id → IDs` A/B | 9.293.179 B | 649.345 B |
| Forward con diccionario territorial | 4.159.765 B | 319.352 B |

Se eligió el índice inverso directo: los IDs territoriales aparecen una sola vez como claves, los arrays son deterministas y permite resolver inmediatamente CCAA/provincia → IDs. El dictionary encoding ahorra poco gzip pero no resuelve el cuello de botella de MapLibre: la lista de `geometry_id` sigue siendo grande.

## Prueba aislada de runtime

`prototypes/es4c/` carga el índice solo al seleccionar una CCAA/provincia; España no lo solicita ni filtra ESFire30. Combina el filtro territorial y el temporal mediante una expresión MapLibre `in(geometry_id, literal(ids))`. Si no hay cobertura documentada, el texto es **“sin cobertura ESFire30”**, no “0 incendios”. Baleares, Canarias, Ceuta y Melilla siguen permitiendo límite administrativo y EGIF sin error.

La prueba Alacant (1993–2002) completó: 468 IDs territoriales, 122 features renderizadas en el viewport, selección estable y cero errores. El índice cargado mide 5,75 MB raw; en esa repetición la métrica final estaba en caché, por lo que no permite separar fetch/parse iniciales.

La secuencia dirigida llegó correctamente a España, País Valencià, Alacant y València, pero al aplicar Galicia (38.645 IDs) Chromium terminó antes de entregar el resultado o archivo de smoke. Una repetición aislada de Galicia reprodujo el mismo comportamiento. No se observa un proceso residual ni un error JS estructurado: se trata como fallo del mecanismo experimental `setFilter` con una lista masiva, no como fallo de datos.

Por esa razón no se afirma rendimiento para Galicia/Ourense, móvil, restore o listas de 16.265–38.645 IDs. No se repiten intentos: el resultado ya basta para decidir que el filtro externo por listas no es seguro a escala regional grande.

## Decisión

El índice externo es **MARGINAL**: válido como relación compacta, auditoría, selección y quizá ámbitos pequeños; no es recomendable como filtro MapLibre nacional/regional basado en una expresión literal de decenas de miles de IDs.

La siguiente fase recomendada es **ES-4C2B2B_ESFIRE30_TERRITORY_PMTILES**: evaluar atributos territoriales compactos embebidos al reconstruir PMTiles. Con cardinalidad máxima tres, una feature podría portar `ccaa_ids`/`province_ids`; el filtro sería nativo, pero hay que medir coste del rebuild y duplicación en teselas. No se ha construido ese PMTiles aquí.

## Validación

El builder y su `--check` validan reconcilación y unicidad. Los tests específicos cubren el índice existente y serialización determinista. Los smokes pequeños completados no cambian el visor público; el fallo Galicia queda documentado sin intentar degradar, truncar o eliminar relaciones.
