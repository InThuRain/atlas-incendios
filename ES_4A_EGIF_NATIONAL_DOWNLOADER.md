# ES-4A — Downloader nacional EGIF reanudable

Fecha: 27/08/2026  
Estado: adquisición nacional completa ejecutada externamente y comprobada íntegramente.

## Propósito y límites

ES-4A prepara la adquisición reproducible del XML completo de la Estadística
General de Incendios Forestales (EGIF) nacional. No normaliza partes, no crea
geometrías, no genera assets web ni modifica el frontend.

La cobertura observada en el inventario ES-1 es 1968–2023: 646.887 partes con
recuento anual positivo. Esto no afirma cobertura posterior a 2023. Cada ZIP
es un snapshot raw local ignorado por Git.

La adquisición completa fue ejecutada fuera de Codex y verificada el
27/08/2026 con:

```bash
python3 scripts/ingest/egif/download_national_full.py --check --all
```

El manifiesto local confirma 56 bloques `complete`, sin fallos, con 646.887
partes entre 1968 y 2023 y 182.604.038 B de ZIP. La suma de los bloques y los
totales del manifiesto coinciden exactamente. El manifiesto y los 56 ZIP no se
versionan.

## Reutilización

El programa nuevo
`scripts/ingest/egif/download_national_full.py` reutiliza:

- el protocolo público EGIF, cliente HTTP con timeout y reintentos, escritura
  atómica y SHA-256 de `gva_1968_1992.py`;
- el inventario anual nacional de
  `data/sources/spain_source_inventory.json`;
- la búsqueda/exportación estatal ya implementada en
  `download_national_locations.py`. Esta última ahora acepta una máscara de
  capítulos parametrizada y continúa usando por defecto el capítulo mínimo de
  localización de ES-1.5.

Para ES-4A se solicita la máscara completa de 17 capítulos. Las URLs con GUID
o paquete de sesión no se escriben en el manifiesto: solo se conserva la
plantilla pública de descarga y los parámetros reproducibles no efímeros.

## Bloques y reanudación

La unidad atómica es **un año natural**. El mayor recuento observado es 25.557
partes (1995), inferior al máximo de 50.000 del exportador. Hay 56 bloques
anuales, por lo que cada bloque:

- tiene un único recuento esperado verificable;
- limita una interrupción o error a un año;
- evita mezclar versiones de modelos de parte en la descarga;
- puede reintentarse sin sobrescribir un ZIP válido.

La salida por defecto es:

```text
data/raw/egif/spain/full/2026-08-27/
  egif_full_YYYY.zip
  manifest.json
```

El `manifest.json` se actualiza atómicamente antes de iniciar cada bloque y
al terminarlo. Cada entrada conserva `pending`, `downloading`, `complete` o
`failed`, los años/parámetros, URL/endpoint, timestamps UTC, bytes, SHA-256,
recuentos de servicio y ZIP, recuentos anuales/provinciales y resultado de la
validación. Un ZIP solo pasa a `complete` después de validar que es ZIP/XML,
que su recuento total y anual coincide con el inventario y de escribirlo
atómicamente.

`--resume` reutiliza exclusivamente un bloque `complete` cuyo archivo y
checksum sigan siendo válidos y cuyos recuentos registrados coincidan.
`--check` reabre y valida los ZIP sin red. `--force` vuelve a pedir los años
seleccionados. Una interrupción marca el bloque en curso como `failed` con una
nota y conserva todos los anteriores; `--resume` lo reintenta.

## Muestra ejecutada

Se ejecutó contra el servicio oficial:

```bash
.venv/bin/python scripts/ingest/egif/download_national_full.py \
  --resume --period 1968 --period 2023
```

Después se verificó sin red con `--check` y se repitió con `--resume`, que
reutilizó ambos ZIP. Resultado:

| Bloque | Partes esperadas/descargadas | ZIP | SHA-256 |
|---|---:|---:|---|
| 1968 | 2.038 / 2.038 | 392.539 B | `34d18c5a135a59f53be4cc8a45fa0dd6b6ccd7c81e382bc48bc13e3c527a4a0e` |
| 2023 | 5.223 / 5.223 | 2.028.728 B | `747e23ca68477e68edb55cefc4bd0168dfefdfa01856e4e5b07fb48bc8ea0b48` |

Los ZIP contienen respectivamente 10.129.339 B y 38.864.667 B de XML sin
comprimir. El manifest local es la evidencia completa de adquisición y no se
versiona.

## Espacio y ejecución manual

La estimación ES-1 para los 646.887 registros es ~3,5 GiB de XML sin comprimir
y ~151 MiB de ZIP raw. Es una estimación de planificación previa, no una cuota
garantizada; reservar al menos 5 GiB permite conservar ZIP, XML temporal del
validador y margen de filesystem.

Desde la raíz del repositorio, la descarga nacional completa reanudable es:

```bash
python3 scripts/ingest/egif/download_national_full.py --resume --all
```

Se puede detener con `Ctrl+C` y ejecutar el mismo comando de nuevo. Para una
validación íntegra posterior sin red:

```bash
python3 scripts/ingest/egif/download_national_full.py --check --all
```

Tras acabar, se debe compartir el resumen final del comando y el archivo local
`data/raw/egif/spain/full/2026-08-27/manifest.json` (o, como mínimo, sus
`totals`, estados, SHA-256 y fallos) para iniciar ES-4B. ES-4B podrá inventariar
esquemas y normalizar, pero no debe empezar antes de que todos los bloques
necesarios estén `complete` y el `--check --all` termine sin errores.

La ejecución completa ya satisface ese requisito. ES-4B1 puede usar el
snapshot raw local como entrada, conservándolo intacto.

## Pruebas específicas

```bash
.venv/bin/python -m unittest tests.test_es4a_egif_national_downloader -v
```

Cubren sintaxis de períodos, los 56 bloques y 646.887 partes, límite del
exportador, ZIP de esquema genérico (incluido 2023), estado `pending` anterior
a cualquier red y reutilización condicionada a checksum y recuento.
