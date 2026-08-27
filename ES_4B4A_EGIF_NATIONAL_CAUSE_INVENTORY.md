# ES-4B4A — Inventario nacional de causas EGIF

## Alcance

Esta subfase prepara un inventario reproducible de los campos de causa de
los 646.887 registros EGIF nacionales normalizados por ES-4B1. No crea una
ontología nacional, no modifica `cause_raw`, no asigna causas canónicas en
masa y no genera assets web. Cada valor se conserva exactamente como aparece
en `original_attributes.pif_causa`.

La unidad de ejecución es un año. Es coherente con el snapshot nacional
inmutable de ES-4B1, permite interrupción entre bloques y conserva el coste
de una reanudación pequeño. El agregador no reescribe un bloque `complete`
cuyo checksum siga siendo válido, salvo con `--force`.

## Campos fuente observados en la muestra

La muestra reproducible incluye 1974, 1983, 1992, 2000, 2010 y 2023
(65.130 registros). En todos ellos existieron los campos básicos:

- `pif_causa.idcausa` — campo primario de código de causa;
- `pif_causa.idcausante`;
- `pif_causa.idcertidumbrecausa`;
- `pif_causa.idclasedia`.

`pif_causa.idmotivacion` está presente en los esquemas de la muestra de
1974–2023, aunque solo poblado en 36.037 registros. `diastormenta` aparece
en el esquema de 2010 y 2023. El esquema de 2023 añade
`idautorizacionactividad`, `idgradoresponsabilidad`,
`idinvestigacioncausa`, `motivacionotros` y `causaotros`. El inventario
registra firmas de campos por año: no interpreta esa diferencia como
equivalencia administrativa entre modelos.

Los identificadores técnicos `pif_causa.numeroparte` e `pif_causa.idpif`
se excluyen deliberadamente: identifican el parte, no una dimensión de causa.

## Null, blanco, desconocido y compuesto

Para cada campo el resultado mantiene por separado:

- campo ausente del modelo;
- campo presente con `null`;
- campo presente pero blanco tras `strip()`;
- valores fuente no vacíos y su frecuencia.

Un código fuente como `500` no se confunde con `null`: sigue siendo el valor
exacto `"500"`. De igual modo, textos como `Desconocida` de `causaotros`
quedan como valor fuente sin convertirlos en la categoría canónica
`unknown`. Los campos compuestos —por ejemplo `idcausa` junto con
`idcausante`, `idcertidumbrecausa` o `motivacionotros`— se inventarían por
separado y las combinaciones de campos disponibles se conservan por año.

## Mapeos reutilizados, sin ampliarlos

Solo `pif_causa.idcausa` recibe una anotación de mapeo, y únicamente cuando
coincide exactamente con un código ya documentado para ese mismo campo EGIF
en `config/egif-web.json` y su diccionario público. La anotación contiene
`mapping_status=documented`, `canonical_code` y la base documental. Los
demás valores, campos y códigos nuevos quedan con `mapping_status=unmapped`.

En la muestra, el campo principal contiene 78 valores distintos. Se anotan
como documentados `100`, `210`, `220`, `230`, `240`, `250`, `260`, `290`,
`310`, `320`, `330`, `340`, `400`, `500` y `600`; los subcódigos observados
como `211`, `270`, `300` o `399` permanecen sin mapeo. Esta diferencia es
intencional: ES-4B4A no infiere que un subcódigo herede la semántica de su
familia.

## Salidas locales e integridad

Las salidas se generan en la ruta ignorada:

`data/derived/spain/es4b4a/causes/2026-08-27/`

- `manifest.json`: estado por año, checksum de entrada y salida, recuentos y
  errores;
- `cause_values_<AAAA>.json`: inventario completo de ese bloque anual;
- `cause_values_by_year.json`: resumen anual compacto;
- `cause_values_global.json`: frecuencias y distribución acumulada;
- `cause_schema_periods.json`: firmas de campos observadas por años.

La muestra produjo 171.671 bytes de bloques anuales y 284 KiB de directorio
completo (incluidos agregados). Las salidas no se versionan en Git.

## Ejecución y comprobación

Muestra ejecutada en ES-4B4A:

```bash
.venv/bin/python scripts/audit/egif/es4b4a_cause_inventory.py --resume \
  --period 1974 --period 1983 --period 1992 --period 2000 --period 2010 --period 2023

.venv/bin/python scripts/audit/egif/es4b4a_cause_inventory.py --check \
  --period 1974 --period 1983 --period 1992 --period 2000 --period 2010 --period 2023
```

Resultado: seis bloques completos, 65.130 registros, 65.130 con
`idcausa` no vacío, 0 fallos de comprobación. El manifiesto guarda el SHA-256
de cada JSONL normalizado de entrada y de cada bloque de salida.

Tras revisión, la ejecución nacional reanudable es:

```bash
python3 scripts/audit/egif/es4b4a_cause_inventory.py --resume --all
python3 scripts/audit/egif/es4b4a_cause_inventory.py --check --all
```

También funciona con el intérprete del entorno del proyecto sustituyendo
`python3` por `.venv/bin/python`.

`Ctrl+C` conserva los bloques ya completados y el manifiesto de estado. Para
regenerar deliberadamente un rango validado:

```bash
.venv/bin/python scripts/audit/egif/es4b4a_cause_inventory.py --force --period 1968:1979
```

## Límites y siguiente subfase

## Ejecución nacional externa confirmada

El usuario ejecutó el comando nacional el 27 de agosto de 2026 y comprobó
todos los bloques sin que Codex repitiera el procesamiento. El manifiesto
local confirma:

- 56/56 bloques `complete`;
- 646.887 registros auditados;
- 646.887 con `pif_causa.idcausa` no vacío y 0 sin causa primaria;
- 1.771.374 bytes de bloques anuales;
- 2,3 MiB para el directorio de salidas completo;
- 0 fallos en `--check --all`.

El agregado nacional contiene 11 campos de causa, 87 códigos distintos en
`idcausa`, 609.964 apariciones anotadas como `documented` y 36.923 aún
`unmapped`. Este último recuento no es un fallo: identifica códigos fuente
que deberán investigarse sin heredar automáticamente el significado de otros
códigos de su misma familia.

Se observan tres firmas de esquema:

1. esquema básico: 1968–2000 y 2002–2004;
2. básico más `diastormenta`: 2001 y 2005–2015;
3. esquema ampliado: 2016–2023.

La discontinuidad de 2001–2004 es una observación del inventario, no una
interpretación de su significado administrativo. Los valores más frecuentes
de `idcausa` son `400` (335.852), `500` (139.963), `100` (27.989), `210`
(20.405) y `250` (14.958), siempre conservados como códigos fuente.

La siguiente fase, ES-4B4B, deberá revisar el inventario completo,
documentar los cambios de esquema y proponer cualquier mapeo adicional
únicamente con evidencia documental explícita. No debe convertir `unmapped`
en `documented` por similitud de código o etiqueta.
