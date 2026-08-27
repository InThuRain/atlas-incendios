# ES-4B5B2 — Auditoría de assets web EGIF nacionales

Fecha de auditoría: 27/08/2026. Esta fase examina los assets existentes de
ES-4B5B1; **no** ejecuta el builder, no reabre los 3.780.517.990 B del
normalizado EGIF, no modifica frontend ni publica datos.

El resultado estructurado completo es
`data/audit/egif/es4b5b2_web_assets.json`. Conserva los 88 assets y sus
metadatos, ordenados de forma determinista, para que se puedan revisar sin
versionar los assets nacionales ignorados.

## Método y alcance

La auditoría utiliza como prueba primaria el manifest local del builder
`data/web/spain/egif/2026-08-27/manifest.json` y sus checksums. Verifica los
tamaños, SHA-256 y tamaño gzip reproducible de los 176 ficheros
`initial.json`/`detail.json`. Deserializa los 88 `initial.json` (96.883.738 B)
para comprobar IDs únicos, años, CCAA/provincia/municipio, causas y GIF. No
deserializa los `detail.json` de forma masiva: comprueba estructura, ordinal y
primer/último ID en una muestra determinista de cuatro assets; el `--check`
de ES-4B5B1 ya valida todos los detalles y sus checksums.

Los recuentos anuales se contrastan contra el manifest ES-4B1 de 56 bloques.
La compatibilidad territorial se prueba por la cadena de checksums ES-4B3 que
el builder guardó por año, y porque cada valor
`autonomous_community_id` del asset coincide con la CCAA de su partición. No
se reconstruyen relaciones territoriales ni se leen sus 2,78 GB.

## Integridad y alcance de fuentes

| Comprobación | Resultado |
| --- | ---: |
| Assets completos | 88 / 88 |
| IDs `egif-record:<NumeroParte>` únicos | 646.887 |
| Duplicados entre assets | 0 |
| Reconciliación anual con ES-4B1 | 646.887 / 646.887; 0 diferencias |
| Reconciliación con total ES-4B3 | 646.887 / 646.887 |
| Checksums/tamaños/gzip de assets | 176 / 176 correctos |
| Perfil | `development` |
| Fuente incluida | solo `egif` |
| Fuentes excluidas | `ccinif_grid`, `gva_sigif` |

El dataset sigue siendo de registros administrativos sin geometría. La malla
CCINIF, sus relaciones y cualquier `spatial_reference_id` están excluidos.

## Tamaño y separación de cargas

| Carga | Raw | gzip | Raw/parte | gzip/parte | % gzip total |
| --- | ---: | ---: | ---: | ---: | ---: |
| INITIAL | 96.883.738 B | 3.901.303 B | 149,769 B | 6,031 B | 27,208 % |
| DETAIL bajo selección | 85.008.219 B | 10.437.489 B | 131,411 B | 16,135 B | 72,792 % |
| Total | 181.891.957 B | 14.338.792 B | 281,180 B | 22,166 B | 100 % |

Una vista normal solo necesita `initial.json`. El detalle se descarga por
asset únicamente cuando se seleccione una ficha: la separación evita llevar
de inicio casi el 73 % del gzip total de todo el conjunto.

No existe un fichero lookup adicional. El navegador crea
`record_id → ordinal` desde la columna `record_id` de INITIAL. Esa columna
cuesta 16.172.284 B raw y 1.587.210 B gzip: 16,692 % del raw INITIAL y
40,684 % de su gzip. El heap concreto de un `Map` JavaScript queda para el
benchmark de navegador ES-4B5C.

## Distribución territorial

| Territorio | Partes | Assets | gzip total | gzip INITIAL | % nacional |
| --- | ---: | ---: | ---: | ---: | ---: |
| Galicia | 264.313 | 5 | 5.007.567 B | 1.400.126 B | 40,859 % |
| Castilla y León | 81.438 | 5 | 1.877.995 B | 514.891 B | 12,589 % |
| Andalucía | 45.512 | 5 | 1.090.825 B | 292.005 B | 7,036 % |
| Cataluña | 31.319 | 5 | 753.043 B | 209.248 B | 4,841 % |
| País Valencià (`ES:CCAA:10`) | 22.108 | 5 | 541.312 B | 149.247 B | 3,418 % |
| La Rioja | 3.996 | 5 | 111.791 B | 31.011 B | 0,618 % |
| Ceuta (ciudad autónoma) | 22 | 4 | 4.937 B | 2.147 B | 0,003 % |

Galicia es el caso prioritario de rendimiento: contiene el 40,9 % de los
registros. Ceuta comprime peor por el overhead fijo de cuatro assets muy
pequeños; no es un riesgo de navegador material.

## Distribución temporal

| Bloque | Partes | Assets | raw | gzip | gzip/parte |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1968–1979 | 42.967 | 16 | 10.696.577 B | 810.055 B | 18,853 B |
| 1980–1992 | 136.534 | 18 | 35.363.344 B | 2.518.783 B | 18,448 B |
| 1993–2002 | 200.513 | 18 | 57.412.820 B | 4.086.857 B | 20,382 B |
| 2003–2012 | 164.204 | 18 | 48.021.294 B | 4.027.607 B | 24,528 B |
| 2013–2023 | 102.669 | 18 | 30.397.922 B | 2.895.490 B | 28,202 B |

Los registros más modernos son materialmente más pesados: el gzip por parte
pasa de 18,45 B en 1980–1992 a 28,20 B en 2013–2023 (+52,9 %). Es coherente
con mayor presencia/variedad de campos de ficha, sin que se haya alterado la
semántica fuente.

El asset más pesado, y también el que contiene más registros, es
`egif:ES:CCAA:12:1993-2002` (Galicia): 110.605 partes, 31.465.528 B raw,
2.012.903 B gzip (572.974 B INITIAL + 1.439.929 B DETAIL). El listado de los
diez mayores, de los diez con más registros y de los diez con peor ratio está
en el JSON auditado. Los cuatro peores ratios son los cuatro assets de Ceuta
(1–8 registros); fuera de ese caso, el peor es Murcia 1968–1979, con 94
registros y ratio gzip/raw 13,728 %.

## Causas, territorio y GIF

| Campo | Resultado |
| --- | ---: |
| `cause_source_code` presente | 646.887 |
| `canonical_cause=null` | 646.887 |
| `cause_mapping_status=unmapped` | 646.887 |
| CCAA no nula | 646.887 |
| Provincia no nula | 646.887 |
| Municipio resuelto | 575.397 |
| Municipio `null` | 71.490 |
| GIF administrativo `true` | 2.192 |
| GIF administrativo `false` | 644.695 |
| GIF administrativo `unknown` | 0 |

No se introdujo ninguna equivalencia nueva para causas y no se reintentó la
resolución municipal. La clasificación GIF procede exclusivamente del campo
administrativo EGIF `reported_forest_area_ha >= 500`; no depende de ESFire30
ni de una geometría.

## Diferencia frente a la estimación ES-4B5A

ES-4B5A extrapoló **solo la carga INITIAL** a partir de muestras nacionales:
~91,94 MiB raw y ~3,63 MiB gzip. La implementación real INITIAL mide 92,40
MiB raw y 3,72 MiB gzip: +0,50 % raw y +2,48 % gzip, una desviación pequeña y
compatible con la extrapolación y la compresión por 88 particiones.

El aparente exceso del total real (173,47 MiB raw y 13,67 MiB gzip) procede
principalmente de DETAIL bajo demanda: 81,07 MiB raw y 9,95 MiB gzip. No es
transferencia inicial. El resto de la diferencia INITIAL se explica por el
overhead estructural de múltiples JSON/streams gzip y por la distribución real
de strings/campos en los bloques, no por campos no aprobados. La columna
`record_id`, necesaria para selección estable, representa 1,51 MiB gzip de
INITIAL; no hay una segunda copia serializada del lookup.

No hay un defecto que justifique rediseñar el formato antes de medir un
navegador: 14,34 MB gzip nacional no equivale a la descarga inicial de una
vista particionada.

## Escenarios obligatorios para ES-4B5C

El benchmark de navegador debe medir INITIAL y, separadamente, la primera
carga DETAIL por selección para:

1. La Rioja, 2013–2023: 702 partes; 5.901 B INITIAL gzip y 17.864 B DETAIL.
2. País Valencià, periodo completo: 22.108 partes; 149.247 B INITIAL y
   392.065 B DETAIL gzip.
3. Cataluña, periodo completo: 31.319 partes; 209.248 B INITIAL y 543.795 B
   DETAIL gzip.
4. Andalucía, periodo completo: 45.512 partes; 292.005 B INITIAL y 798.820 B
   DETAIL gzip.
5. Galicia, periodo completo: 264.313 partes; 1.400.126 B INITIAL y
   3.607.441 B DETAIL gzip.
6. Galicia 1993–2002, el bloque más pesado: 110.605 partes; 572.974 B
   INITIAL y 1.439.929 B DETAIL gzip.
7. España, solo 1993–2002: 18 requests INITIAL, 200.513 partes y
   1.147.093 B INITIAL gzip (4.086.857 B incluyendo todos los DETAILS).

ES-4B5C debe además medir creación del lookup `record_id → ordinal`, filtrado
temporal/territorial y heap en escritorio/móvil. Esta auditoría no adelanta
esas pruebas.

## Límites

- La ontología EGIF continúa bloqueada hasta recibir el diccionario oficial
  MITECO/EGIF; `unmapped` es intencional.
- CCINIF sigue excluido y no publicable.
- No se ha hecho benchmark de navegador ni se ha decidido un perfil público
  nacional.
