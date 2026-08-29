# ES-4C2B3A2 — Auditoría nacional ESFire30 ↔ municipio actual

## Alcance

Esta auditoría lee las relaciones C2B3A1 ya calculadas. No recalcula el join
municipal nacional, no modifica PMTiles ni el runtime. Una lectura geométrica
dirigida se limita a las 83 geometrías sin relación municipal, frente a las 81
unidades BDLJE no municipales y sus provincias padre.

Una relación significa que un perímetro ESFire30 intersecta un municipio BDLJE
**actual**. No identifica un municipio histórico, administrativo EGIF, de
origen ni de ignición.

## Reconciliación

| Métrica | Resultado |
| --- | ---: |
| `geometry_id` ESFire30 | 119.498 |
| relaciones positivas | 143.477 |
| municipios canónicos posibles | 8.132 |
| duplicados lógicos | 0 |
| incoherencias municipio → provincia → CCAA | 0 |
| contactos de borde | 0 |
| geometrías sin municipio | 83 |

Todos los 143.477 enlaces tienen además relación positiva C2B1A con la
provincia y CCAA padre. Un perímetro multi-provincia o multi-CCAA conserva
todas sus relaciones; no existe territorio municipal principal.

## Cardinalidad geometría → municipio

| Municipios relacionados | Geometrías |
| --- | ---: |
| 0 | 83 |
| 1 | 98.376 |
| 2 | 18.783 |
| 3 | 1.874 |
| 4 | 250 |
| 5 | 53 |
| 6–10 | 65 |
| 11–15 | 11 |
| 16–19 | 3 |
| 20+ | 0 |

Media: 1,2007; mediana: 1; p95: 2; p99: 3; máximo: 19.

Los extremos son `esfire30:v1:1994:1091` (19; ~79,84 km²),
`esfire30:v1:1994:1241` (18; ~150,44 km²) y `esfire30:v1:1986:662`
(16; ~139,88 km²). Los cuatro grandes controles siguen por debajo del máximo:
1994:2841 → 13, 2004:2622 → 12, 2012:24 → 12 y 2021:1311 → 14. Es una
asociación descriptiva, no causal.

## Cardinalidad municipio → geometría

| Perímetros relacionados | Municipios |
| --- | ---: |
| 0 | 1.966 |
| 1–10 | 4.188 |
| 11–50 | 1.439 |
| 51–100 | 241 |
| 101–250 | 189 |
| 251–500 | 81 |
| 501–1.000 | 23 |
| 1.001–2.500 | 4 |
| 2.501–5.000 | 1 |
| >5.000 | 0 |

Media: 17,64; mediana: 3; p95: 70; p99: 297; máximo: 2.610 en
`ES:MUN:33011` Cangas del Narcea. Los conteos son **perímetros ESFire30 que
intersectan el municipio actual**, no incidencia administrativa de incendios.

Casos dirigidos: Elx 6, Alacant/Alicante 2, València 6, Barcelona 20, Ourense
152, A Coruña 61, Sevilla 26, Girona 8, Llívia 1, Condado de Treviño 73, La
Puebla de Arganzón 7 y Ademuz 1. El agregado contiene el top 25 completo; los
cinco primeros son Cangas del Narcea (2.610), Allande (1.306), Tineo (1.225),
Viana do Bolo (1.178) y Chandrexa de Queixa (1.062).

## Las 83 sin municipio

Las 83/83 intersectan positivamente una o más de las 81 entidades BDLJE con
código municipal `53xxx`, clasificadas en C2A3 como unidades no municipales.
No se encontró un caso que exija nearest municipality ni se convirtió una de
esas entidades en `ES:MUN`.

Se usaron 14 unidades distintas; hay 84 intersecciones porque una geometría
alcanza dos unidades. Las 83 geometrías permanecen visibles en España, CCAA y
provincia cuando corresponda, pero no aparecen al filtrar un municipio
canónico. Esta es evidencia de auditoría, no una nueva UX de facerías,
parzonerías, comunidades u otras unidades 53xxx.

## Slivers y fracciones

| Fracción del perímetro | Relaciones |
| --- | ---: |
| <1e-6 | 43 |
| 1e-6–1e-5 | 91 |
| 1e-5–1e-4 | 312 |
| 1e-4–1e-3 | 930 |
| 1e-3–1e-2 | 2.698 |
| >=1e-2 | 139.403 |

No se elimina ningún sliver. `intersection_fraction_municipality` existe para
las 143.477 filas: mínimo ~9,29e-14, p50 ~0,001021 y p95 ~0,015255. No debe
confundirse con la fracción del perímetro.

La corrección de C2B3A1 queda preservada: un único sliver positivo de 1990 se
había serializado con área redondeada a `0.0`. Se conservó la precisión del
valor numérico; no se editó ninguna geometría ni se modificó la semántica de
intersección positiva.

## Cobertura espacial agregada

Galicia concentra 38.645 `geometry_id` y 45.931 relaciones municipales;
Castilla y León, 29.763 y 35.383. Por provincia, Ourense encabeza las
relaciones (19.230; 16.265 geometrías), seguida por León (15.656) y Asturias
(15.532). Son coberturas de intersección espacial, no estadísticas
administrativas de incendios.

Los controles transfronterizos permanecen N:M: `2011:88` tiene municipios de
Alacant y València; `1985:1037` conserva municipios en ambas CCAA relacionadas.

## Índices compactos medidos, no integrados

| Representación | Raw | gzip |
| --- | ---: | ---: |
| inverso nacional `municipality_id → geometry_id[]` | 3.537.410 B | 430.182 B |
| forward nacional `geometry_id → municipality_id[]` | 5.218.816 B | 520.358 B |
| inverso separado por provincia (50 assets) | 3.537.423 B | 434.383 B |
| inverso separado por CCAA (19 assets) | 3.537.428 B | 430.783 B |

El shard provincial mayor es Ourense: 457.404 B raw / 53.687 B gzip. La mayor
entrada individual, Cangas del Narcea, ocupa 62.270 B raw / 6.298 B gzip para
2.610 IDs. El particionado provincial encaja con la carga municipal actual y
añade solo ~4,2 KB gzip frente al índice nacional.

El máximo municipal (2.610) es 6,75 % de los 38.645 IDs de Galicia que hicieron
marginal el filtro externo regional, unas 14,8 veces menor. Esto justifica una
**prueba de runtime** del índice inverso municipal, no una afirmación todavía
sobre rendimiento MapLibre. Tamaños observados: 5.868 municipios con 1–100
IDs (pequeños), 270 con 101–500 (medios) y 28 con más de 500 (grandes).

Alternativas si el runtime no fuese estable: índices por shard municipal, tiles
locales especializados, `geometry_id` dictionary/numeric encoding o
feature-state. No se implementa ninguna aquí y no se proponen slots `mun_N`.

## Entregables y validación

- Agregado: `data/audit/esfire30/es4c2b3a2_municipal_relations.json`.
- Script: `scripts/audit/esfire30/es4c2b3a2_municipal_relations.py`.

```bash
python3 scripts/audit/esfire30/es4c2b3a2_municipal_relations.py --check
```

Los tests específicos verifican reconciliación, cardinalidad, unidades no
municipales, buckets de slivers, orden determinista y tamaño de índices. La
siguiente fase recomendada es
`ES-4C2B3B1_ESFIRE30_MUNICIPAL_RUNTIME_INDEX`: probar el índice inverso
provincial sin PMTiles nuevo ni frontend de producción.
