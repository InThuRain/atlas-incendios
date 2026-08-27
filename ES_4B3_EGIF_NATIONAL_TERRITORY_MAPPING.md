# ES-4B3 — Normalización territorial nacional EGIF

Estado: normalización territorial nacional completada localmente; pendiente de
revisión y definición explícita de ES-4B4.

## Contrato semántico

El pipeline no modifica nunca el JSONL normalizado ni sus valores territoriales
fuente:

```text
source_declared != canonical_mapping
historical_mapping != canonical_mapping
spatial_reference != administrative_location
```

Los valores `idcomunidad`, `idprovincia`, `idmunicipio` y el nombre municipal
fuente, cuando existe, se conservan en `source_declared` dentro de la auditoría
por registro. Un mapeo posterior hacia `ES:CCAA:*`, `ES:PROV:*` o `ES:MUN:*`
no los sustituye ni corrige.

EGIF sigue teniendo `geometry = null`. Las relaciones CCINIF no se usan para
elegir municipios y las coordenadas X/Y no se transforman ni usan como
evidencia territorial en esta fase; ambos quedan como `not_used_for_mapping`.

## Entradas verificadas

Se reutilizan, sin redescarga:

- normalizado EGIF ES-4B1, 646.887 partes, 1968–2023;
- snapshot INE ES-2 `ine-rel-2026-01-01`, SHA-256
  `e812559a5d9a779b52d5ef3c503609aefd9647a2fb226be5ff8fb932db2f1799`;
- 8.132 municipios, 50 provincias y 2 ciudades autónomas con códigos
  estadísticos equivalentes de nivel provincial (51 y 52), no “52 provincias”.

`config/egif-territory-crosswalk-v1.json` versiona la tabla explícita de los
códigos de comunidad propios de EGIF hacia los códigos INE. No hay matching de
nombres. El código municipal EGIF se trata exclusivamente como código local a
la provincia: solo se intenta la clave actual `provincia(2) + municipio(3)` si
existe en el snapshot y su padre coincide. `0` significa que la fuente no
declaró municipio.

La tabla `config/egif-historical-municipality-mappings-v1.json` está vacía. El
pipeline admite `historical_resolved` únicamente si ese fichero incorpora una
equivalencia documentada con evidencia explícita; no inventa genealogías.

## Salidas locales, separadas y reanudables

`scripts/relations/egif/territories.py` genera, por año, dentro de
`data/derived/spain/es4b3/territory_relations/2026-08-27/` (ignorado):

1. `record_to_territory_relations_YYYY.jsonl`: relaciones ES-2 con destino
   territorial conocido. Para una resolución se conservan por separado
   `source_declared` y `canonical_mapping`; un histórico documentado usaría
   `historical_mapping`.
2. `territory_mapping_audit_YYYY.jsonl`: una auditoría por parte con valores
   fuente, resultado por nivel, método, candidatos y QA. Los casos sin destino
   (`candidate`, `unresolved`, `invalid_source_value`) viven aquí sin crear una
   falsa relación territorial.

Los estados de la auditoría son:

| Estado | Regla |
|---|---|
| `resolved` | código fuente y catálogo INE vigente compatibles |
| `historical_resolved` | equivalencia documental declarada explícitamente |
| `candidate` | coincidencia exacta de nombre actual, sin promoción automática |
| `unresolved` | falta de dato, código actual inexistente o sin equivalencia documentada |
| `invalid_source_value` | formato o código fuente incompatible |

Cada bloque registra checksums del input, snapshot, crosswalk, outputs,
recuentos, bytes y estados. Se escribe temporalmente y se sustituye de forma
atómica; el manifest se actualiza antes y después de cada bloque. `--resume`
reutiliza únicamente bloques completos y validados; `--check` relee ambos
JSONL, sus checksums y el contrato de estados.

## Muestra ejecutada

La muestra 1974, 1992, 1995 y 2023 cubre periodo antiguo, transición,
volumen alto y periodo moderno:

| Año | Partes | Relaciones | Municipio resolved | Municipio unresolved |
|---|---:|---:|---:|---:|
| 1974 | 3.920 | 15.680 | 0 | 3.920 |
| 1992 | 15.956 | 95.436 | 15.806 | 150 |
| 1995 | 25.557 | 152.616 | 25.194 | 363 |
| 2023 | 5.223 | 31.288 | 5.198 | 25 |
| **Total** | **50.656** | **295.020** | **46.198** | **4.458** |

CCAA y provincia se resolvieron por código en los 50.656 registros de muestra.
No hubo candidatos, valores inválidos ni conflictos código/nombre; el nombre
municipal fuente estaba ausente en esta muestra, por lo que no se activó la
ruta de candidato textual exacto. `--check` pasó en los cuatro bloques.

La muestra ocupa 219.112.505 B raw y 7.859.603 B gzip. Una extrapolación
lineal conservadora estima aproximadamente 2,80 GB raw y 100 MB gzip para los
646.887 registros; es un derivado técnico local, no un asset web.

## Ejecución nacional confirmada

La ejecución externa completó los 56 años y el `--check --all` local volvió a
verificar los dos JSONL de cada bloque sin errores:

| Métrica | Resultado |
|---|---:|
| Bloques complete | 56 / 56 |
| Partes auditadas | 646.887 |
| Relaciones territoriales | 3.738.342 |
| Tamaño de ambos outputs | 2.782.544.923 B |
| Checksums de relaciones / auditorías | 56 / 56 |
| CCAA resuelta | 646.887 |
| Provincia resuelta | 646.887 |
| Municipio resuelto | 575.397 |
| Municipio sin resolver | 71.490 |
| Municipio histórico / candidato / inválido | 0 / 0 / 0 |

El tamaño real se aproxima a la proyección de la muestra. Los 71.490 casos
municipales sin resolver quedan conservados para una auditoría posterior; no
se deducen a partir de nombre, CCINIF ni X/Y.

## Controles

- Elx: EGIF `9 / 3 / 65` → `ES:CCAA:10`, `ES:PROV:03`, `ES:MUN:03065`.
- Herbers: EGIF `9 / 12 / 68` → `ES:MUN:12068`.
- Ceuta/Melilla: los códigos estadísticos 51/52 resuelven a ciudades autónomas
  y sus municipios, sin crear provincias conceptuales. No se inventa un código
  EGIF de comunidad para Melilla: si apareciera uno no documentado, quedaría
  explícitamente inválido hasta auditarlo.
- Valores históricos solo se resuelven mediante una tabla de evidencia; los
  candidatos o no resueltos no obtienen relación canónica.

## Ejecución manual nacional

```bash
.venv/bin/python scripts/relations/egif/territories.py --resume --all
.venv/bin/python scripts/relations/egif/territories.py --check --all
```

El manifest local ya acredita la ejecución completa, sin errores y con
checksums en los 112 outputs anuales. ES-4B4 no debe comenzar sin una
instrucción específica.
