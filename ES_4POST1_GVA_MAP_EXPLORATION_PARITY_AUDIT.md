# ES-4POST1 — Auditoría de paridad de exploración del mapa GVA

## Conclusión

```text
MAP_EXPLORATION_PARITY = FAIL
POST_RELEASE_PRODUCT_PARITY_REVIEW = FAILED_NEEDS_FIX
RELEASE_TAG_STATUS = HOLD
NEXT_PHASE = ES-4POST2_GVA_MAP_EXPLORATION_PARITY_IMPLEMENTATION
```

El despliegue nacional sigue siendo técnicamente válido y permanece en
producción. La paridad de exploración cartográfica con el GVA histórico no lo
está: se ha comprobado una omisión de 1.334 registros/perímetros ICV al pedir
todo 1993–2024, una pérdida de la codificación temporal visible y la ausencia
de popup cartográfico inmediato. No se ha aplicado ninguna corrección en esta
fase.

La sospecha concreta de que en 1995 sólo estuviesen presentes los perímetros
ESFire30 y faltasen los oficiales ICV es falsa para ese año: el runtime
nacional cargó 467 partes ICV y 467 perímetros ICV; los 44 elementos visibles
en el viewport de la prueba son sólo la parte renderizada en ese encuadre. No
son un total territorial ni una pérdida de 423 geometrías.

## Referencias y método

- GVA histórico: worktree temporal en el ancla
  `f7a3532f633a247f33dee3ebba9fbcc316c0e534`, reconstruido con el bundle
  público v5 y validado con el flujo histórico.
- Nacional observado: `https://inthurain.github.io/atlas-incendios/`.
- Se compararon los assets ICV compartidos, el runtime y Chromium. Se separan
  siempre cuatro cosas: disponibles en el asset, cargados por el loader,
  presentes en el source/tile y renderizados en el viewport.
- No se recalcularon geometrías, no se modificaron datos ni se desplegó nada.

## Conteos ICV exactos

| Rango | Asset ICV: partes | Asset ICV: perímetros | Loader nacional actual: partes | Exclusiones actuales |
|---|---:|---:|---:|---:|
| 1993 | 715 | 715 | 715 | 0 |
| 1995 | 467 | 467 | 467 | 0 |
| 2000 | 606 | 606 | 606 | 0 |
| 2010 | 328 | 328 | 328 | 0 |
| 2020 | 253 | 253 | 253 | 0 |
| 2024 | 472 | 473 | 472 | 0 |
| 1993–2024 | 13.738 | 13.739 | 12.404 | **1.334** |
| 2000–2010 | 4.878 | 4.878 | 4.878 | 0 |
| 2015–2024 | 3.331 | 3.332 | 1.997 | **1.334** |

El GVA histórico carga y renderiza los 13.739 perímetros del rango completo.
El nacional cargó 12.405 perímetros correspondientes a 12.404 partes. En el
viewport fijo de la prueba MapLibre renderizó 1.622; ese segundo número es
necesariamente dependiente de zoom, tiles y viewport, y no debe usarse como
total de cobertura.

### Causa comprobada de la omisión

`runtime/icv_loader.mjs` enlaza provincias con tres literales title-case:
`Alicante/Alacant`, `Castellón/Castelló` y `Valencia/València`. El mismo
snapshot ICV contiene 1.334 partes de 2016–2019 con los valores fuente
`ALICANTE` (338), `CASTELLON` (273), `Castellon` (1) y `VALENCIA` (722). Esos
valores no entran en `ICV_KEY_BY_PROVINCE`; por tanto no se incluyen en
`territoryFires`, aunque sus geometrías y sus IDs existen en los assets.

Es una regresión de carga/normalización territorial, no ausencia de cobertura
ICV ni una conclusión sobre incendios. Debe arreglarse con una normalización
documentada y comprobada de códigos/valores de provincia, no deduciendo
geometría por nombre libre.

## Escenarios observados

### GVA 1995

El histórico Leaflet cargó 3.790 geometrías de los assets de bloque y filtró
467 perímetros ICV visibles; el hash con un `fire_id`/`geometry_id` válido abrió
un popup directo y resaltó `gva:geometry:1995:3:1956`.

El nacional cargó 467 partes y 467 perímetros ICV. En el mismo centro/zoom,
MapLibre expuso 168 features de source y dibujó 44. Seleccionar una feature
(`gva:geometry:1995:3:783`) abrió correctamente la ficha ICV. ESFire30 estaba
desactivado en la vista recomendada; al activarlo, se dibujaron 13 features en
ese viewport. Ese 13 tampoco es un total territorial. El GVA histórico v5 sólo
publicaba ESFire30 valenciano 1985–1992, de modo que para 1995 su recuento es
cero: no es una referencia válida para interpretar como total los elementos
ESFire30 que el PMTiles nacional dibuja a un zoom concreto.

### GVA 2024

El histórico mostró 472 partes y 473 perímetros, incluido el contrato 1:N.
El nacional cargó los mismos 472/473 y permitió selección/ficha sin errores.

### Rango de solapes 1993–2024

El histórico cargó/renderizó 13.739 perímetros ICV. El nacional cargó 12.405:
ésta es la pérdida de 1.334 arriba descrita. Se verificaron tres solapes con
área positiva, no elegidos sólo por viewport, en Bocairent:

- `gva:geometry:1993:1:1141` / `gva:geometry:1994:2:1674`;
- `gva:geometry:1993:1:1141` / `gva:geometry:1995:3:2223`;
- `gva:geometry:1993:1:1141` / `gva:geometry:2002:10:2711`.

El nacional conserva los polígonos cargados como relleno ICV verde constante,
pero no distingue visualmente año/antigüedad como hacía el GVA histórico. La
lectura de solape es por tanto materialmente peor incluso donde las geometrías
están presentes.

## Presentación e interacción

### Estilos comprobados

El GVA histórico calculaba un color RGB continuo entre azul
`rgb(44,123,182)` y rojo `rgb(240,82,46)` en función del año. Los perímetros
ICV usaban ese color para borde y relleno, con `fillOpacity .28`; ESFire30
usaba borde punteado y opacidad `.2`. Una feature Leaflet instalaba su propio
listener `click`, ejecutaba `selectEntity` y abría un `L.popup` con la ficha
humana.

El nacional aplica a toda la capa ICV `fill-color #246b55`,
`fill-opacity .38` y borde `#164a3a`, sin expresión que dependa de año. Sí
mantiene listeners MapLibre directos sobre `icv-perimeters` y la ficha ICV
humana contiene fuente, identificadores, fechas, territorio, superficie,
causa, GIF y calidad A. Sin embargo, la ficha aparece en el panel lateral o
inferior, no como popup anclado al punto del mapa: para exploración espacial
rápida es un nivel de interacción peor.

### Clasificación

| Aspecto | Estado | Motivo |
|---|---|---|
| Completitud geométrica | FAIL | 1.334 ICV se omiten en 2016–2019 para el rango completo. |
| Fuente geométrica por defecto | PARTIAL | 1995/2024 priorizan ICV, pero el rango completo no es íntegro. |
| Codificación temporal | FAIL | El nacional usa verde constante; el GVA comunica año mediante color. |
| Lectura de solapes | FAIL | Sin codificación temporal ni explicación/leyenda de solapes. |
| Click directo | PARTIAL | Funciona para geometrías cargadas; no para las 1.334 excluidas. |
| Popup humano básico | FAIL | Hay ficha humana, pero no popup inmediato sobre el mapa. |
| Mapa como primera lectura | PARTIAL | El mapa abre primero, pero la lectura rápida pierde año y ficha contextual. |
| Móvil 390×844 | PARTIAL | Se seleccionó ICV y apareció ficha; falta popup compacto y la lectura de color. |

## Información que no se debe confundir

- `loaded_geometries` es el conjunto filtrado que el loader entrega a la capa.
- `querySourceFeatures` y `queryRenderedFeatures` de MapLibre dependen de las
  teselas/materialización y del viewport; no son un recuento nacional.
- Los resultados ESFire30 dibujados al activarlo también dependen de viewport.
  No deben compararse con 467 partes/perímetros ICV ni llamarse incendios
  equivalentes.
- EGIF, ICV y ESFire30 siguen siendo fuentes independientes; esta auditoría no
  propone fusionarlas ni contar un total conjunto de incendios.

## Evidencia visual y estructurada

- [GVA histórico, 1995](data/audit/product/es4post1/legacy-gva-1995.png)
- [Nacional, 1995](data/audit/product/es4post1/national-1995.png)
- [Nacional, solapes 1993–2024](data/audit/product/es4post1/national-overlap-1993-2024.png)
- [Nacional, móvil 390×844](data/audit/product/es4post1/national-mobile-1995.png)
- [Evidencia JSON](data/audit/product/es4post1_gva_map_exploration_parity_audit.json)

## Alcance exacto de ES-4POST2 recomendado

1. Corregir y probar el crosswalk ICV de valores provinciales históricos sin
   eliminar, inventar ni reprocesar geometrías; el rango 1993–2024 debe volver
   a 13.738 partes / 13.739 perímetros.
2. Recuperar una codificación temporal legible para ICV y una leyenda humana,
   incluida una política explícita para solapes.
3. Añadir una interacción de mapa inmediata y accesible: popup/tarjeta breve
   anclada al click/tap, manteniendo la ficha completa y provenance como nivel
   secundario.
4. Repetir exactamente los escenarios de este informe en desktop y móvil, sin
   modificar el modelo de fuentes ni fusionar EGIF/ICV/ESFire30.

No se recomienda crear tag de release ni declarar paridad de producto antes de
esa implementación y de su aceptación posterior.
