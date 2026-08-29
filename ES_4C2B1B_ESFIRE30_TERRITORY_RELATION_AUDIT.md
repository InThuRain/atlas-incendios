# ES-4C2B1B — Auditoría nacional ESFire30 ↔ territorio

## Alcance

Esta auditoría lee exclusivamente los 37 JSONL de relaciones y contactos generados por ES-4C2B1A, su manifest, el catálogo ES-2 y el resumen ES-3. No abre geometrías ESFire30 originales, no calcula nuevas intersecciones, no modifica PMTiles, el runtime ni fuentes publicadas.

La semántica permanece estricta: una relación `spatial_intersection` significa que la geometría ESFire30 intersecta un territorio administrativo con área positiva; no asigna el incendio, su origen ni un registro EGIF a ese territorio.

## Integridad de entrada

- 37/37 bloques, 1985–2021.
- 119.498 `geometry_id` únicos.
- 242.734 relaciones positivas, 168.450.360 B raw.
- Checksums de los 37 JSONL de relaciones y los 37 JSONL de contactos verificados contra el manifest.
- 0 claves lógicas repetidas (`geometry_id`, `territory_id`, `relation_type`).
- 0 geometrías sin CCAA, provincia o ambas.
- 0 contactos de borde y 0 incoherencias provincia → CCAA.

El agregado reproducible está en [`data/audit/esfire30/es4c2b1b_territory_relations.json`](data/audit/esfire30/es4c2b1b_territory_relations.json), SHA-256 lógico `a2017844d714428d45e833a87cc2635d8536b027cc155570da8759c0ae95d953`.

## Baseline y relaciones adicionales

Con una CCAA y una provincia por cada geometría, el baseline es `119.498 × 2 = 238.996`. El resultado contiene 242.734, es decir **3.738 relaciones adicionales**:

| Nivel | Relaciones | Baseline | Exceso |
| --- | ---: | ---: | ---: |
| CCAA/ciudad autónoma | 120.847 | 119.498 | 1.349 |
| Provincia | 121.887 | 119.498 | 2.389 |
| Total | 242.734 | 238.996 | **3.738** |

El exceso se explica exactamente por la cardinalidad, no por duplicados:

- CCAA: 1.337 geometrías con 2 CCAA aportan 1.337 relaciones extra; 6 con 3 aportan 12 más; total 1.349.
- Provincias: 2.343 geometrías con 2 provincias aportan 2.343 extras; 23 con 3 aportan 46 más; total 2.389.

## Cardinalidad N:M

| Territorios por geometría | CCAA | Provincias |
| --- | ---: | ---: |
| 0 | 0 | 0 |
| 1 | 118.155 | 117.132 |
| 2 | 1.337 | 2.343 |
| 3 | 6 | 23 |
| 4+ | 0 | 0 |
| Multi-territorio | 1.343 | 2.366 |
| Máximo | 3 | 3 |

Los seis máximos CCAA incluyen, por ejemplo, `esfire30:v1:1985:4358` y `esfire30:v1:2000:2115`, que intersectan Asturias, Castilla y León y Galicia. Los extremos provinciales completos se conservan en el agregado; ninguno supera tres provincias.

## Reconciliación con ES-3

| Métrica | ES-3 | C2B1A auditado | Diferencia | Estado |
| --- | ---: | ---: | ---: | --- |
| Geometrías multi-CCAA | 1.342 | 1.343 | +1 | `EXPLAINED_DIFFERENCE` |
| Geometrías multi-provincia | 2.364 | 2.366 | +2 | `EXPLAINED_DIFFERENCE` |
| Sin CCAA | 0 | 0 | 0 | `MATCH` |
| Sin provincia | 0 | 0 | 0 | `MATCH` |

ES-3 hizo el test tras llevar BDLJE a EPSG:23030; C2B1A transformó las geometrías con la operación documentada ED50/WGS84 (41) y evaluó área positiva en EPSG:3035. Se usó el mismo snapshot BDLJE y la misma regla de área positiva. La diferencia mínima se conserva, sin forzar coincidencia: es explicable por la ruta CRS/topología y no hay evidencia de pérdida, duplicado o incoherencia. ES-3 no almacenó la lista completa de hits, por lo que identificar los tres casos exactos requeriría repetir su intersección y no se hace en esta fase.

## Touches, slivers y dominancia

No hay contactos de borde de área cero: 0 CCAA, 0 provincias, 0 geometrías touch-only. Nunca se promueven a `territory_relation`.

Distribución de las 242.734 relaciones de área positiva por fracción de la geometría:

| `intersection_fraction` | Relaciones |
| --- | ---: |
| `[0, 1e-6)` | 6 |
| `[1e-6, 1e-5)` | 15 |
| `[1e-5, 1e-4)` | 41 |
| `[1e-4, 1e-3)` | 165 |
| `[1e-3, 1e-2)` | 506 |
| `[1e-2, 1]` | 242.001 |

No se elimina ninguna relación. El mínimo es `esfire30:v1:1989:1858` en Cantabria/provincia 39: 0,031 m² y fracción `1,40574e-7`. Son candidatos claros para una futura revisión cartográfica, no para exclusión automática.

Entre geometrías multi-territorio, el máximo de fracción territorial se reparte así (bandas exclusivas):

| Dominancia máxima | CCAA | Provincias |
| --- | ---: | ---: |
| >99 % | 273 | 449 |
| >95–99 % | 263 | 448 |
| >90–95 % | 148 | 266 |
| ≤90 % | 659 | 1.203 |

Esto confirma que no todas las relaciones múltiples son slivers: una proporción amplia tiene reparto material entre territorios.

## Jerarquía y territorios especiales

Las 121.887 relaciones provinciales tienen la correspondiente relación positiva con su CCAA padre: 121.887 coherentes, 0 inconsistentes.

- Illes Balears / provincia 07: **sin cobertura ESFire30**. El inventario ES-1 describe este snapshot como `mainland Spain`; sus 0 relaciones no implican 0 incendios y tampoco hay asociaciones espurias con la península.
- Ceuta y Melilla: **sin cobertura ESFire30** bajo el mismo alcance `mainland Spain`; tienen 0 relaciones, permanecen `autonomous_city` y no se crean provincias ficticias 51/52.
- Canarias: **sin cobertura ESFire30**; sus 0 geometrías/relaciones no implican ausencia de incendios.

La CCAA con más geometrías intersectadas es Galicia (38.645; 38.112 exclusivas y 533 compartidas). La provincia con más es Ourense (16.265; 15.666 exclusivas y 599 compartidas). Las tablas completas CCAA/provincia se incluyen en el agregado JSON; son cobertura espacial de geometrías, no inventario administrativo de incendios.

## Tamaño de una futura relación para runtime

Se midieron formatos conceptuales sobre las relaciones ya generadas. Todos preservan `geometry_id`; B–D excluyen intencionadamente área, fracción, QA y provenance, que quedan en el JSONL de auditoría.

| Variante | Raw | Gzip | Gzip/geometría |
| --- | ---: | ---: | ---: |
| A. JSONL completo de auditoría | 168.450.360 B | 7.547.953 B | 63,16 B |
| B. `geometry_id → [territory_id…]` | 6.224.334 B | 348.245 B | 2,91 B |
| C. Maps CCAA/provincia separados | 9.293.147 B | 649.281 B | 5,43 B |
| D. IDs territoriales dictionary-encoded | 4.142.442 B | 318.535 B | 2,67 B |

La diferencia B/D es pequeña tras gzip. Para un runtime mantenible, B es suficiente si una única lista de territorios basta; C es más explícita y permite filtros independientes, pero duplica claves. D es la opción más pequeña y exige documentar el diccionario. Ninguna sustituye el JSONL de auditoría.

## PMTiles frente a índice externo

No se altera aún ningún PMTiles.

- Añadir IDs territoriales a atributos PMTiles facilitaría una expresión de filtro nativa en MapLibre, pero obliga a regenerar el PMTiles nacional y repite atributos en múltiples teselas/zooms.
- Un índice externo `geometry_id → territorios` mantiene intactas teselas, permite selección/permalink estable y tiene un coste gzip estimado de 0,32–0,65 MB. No permite por sí solo que MapLibre descarte features antes de recibir una tesela: el runtime deberá decidir cómo aplicar el filtrado por viewport/selección.

Recomendación para **ES-4C2B2**: evaluar un índice externo C (maps separados y legibles) como primera integración aislada, midiendo su filtrado real contra las features PMTiles. Solo decidir si un rebuild con atributos territoriales aporta una ganancia medible después de esa prueba. No usar el JSONL de auditoría en navegador.

## Validación

Los tests específicos cubren agregación/cardinalidad, duplicados, jerarquía, touches, buckets de slivers, estimador compacto y determinismo. No se ejecutó cálculo espacial ni Chromium. El auditor se comprobó con:

```bash
python3 scripts/audit/esfire30/es4c2b1b_territory_relations.py --check
```
