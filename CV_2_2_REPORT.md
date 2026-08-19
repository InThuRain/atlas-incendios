# CV-2.2 — Colecciones recientes provisionales SIGIF y EFFIS

Fecha de ejecución final: **2026-08-19**. Snapshot vigente:
`20260819T174426Z`.

Esta fase no modifica el frontend ni los datasets ICV consolidados 1993–2024.
Los snapshots y sus derivados están ignorados por Git y no deben publicarse.

## Resultado

El pipeline mantiene dos colecciones independientes:

- observaciones administrativas provisionales SIGIF/GVA en JSON Lines;
- geometrías satelitales provisionales EFFIS RDA en GeoJSON.

Un tercer archivo contiene únicamente candidatos puntuados. No fusiona las
fuentes, no crea una identidad administrativa a partir de EFFIS y no usa la
palabra `confirmed`.

| Año | Filas SIGIF | Filas visibles distintas | Periodo SIGIF observado | `coverage_complete` | EFFIS en BBOX | EFFIS que intersectan realmente CV | Suma EFFIS (ha) | Candidatos fuertes / posibles / débiles |
|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 2025 | 281 | 280 | 03-01 a 31-12-2025 | `true` | 13 | 9 | 698 | 4 / 4 / 28 |
| 2026 | 143 | 143 | 11-01 a 30-06-2026 | `false` | 22 | 16 | 10.265 | 3 / 0 / 14 |

La suma EFFIS es superficie satelital y no equivale a superficie administrativa
oficial. En 2026 EFFIS contiene observaciones hasta el 8 de agosto mientras
SIGIF termina el 30 de junio: esta diferencia confirma que 2026 está incompleto
y que las dos fuentes no pueden compararse como inventarios equivalentes.

## Ejecución reproducible

Dependencias aisladas:

```bash
python3 -m venv /tmp/atlas-recent-venv
/tmp/atlas-recent-venv/bin/pip install -r scripts/ingest/comunitat_valenciana/requirements-recent.txt
```

Descarga y validación:

```bash
/tmp/atlas-recent-venv/bin/python scripts/ingest/comunitat_valenciana/download_recent.py
/tmp/atlas-recent-venv/bin/python scripts/ingest/comunitat_valenciana/download_recent.py --validate-snapshot 20260819T174426Z
```

Cada ejecución crea directorios fechados bajo
`data/raw/recent/gva/snapshots/` y
`data/processed/recent/gva/snapshots/`; `latest.json` señala el último. El
manifiesto conserva URL, método/parámetros, fecha UTC, recuentos, tamaño y
SHA-256. La validación final confirmó todos sus checksums.

## SIGIF

Se guarda la respuesta HTML original y se procesa la tabla en el mismo orden.
Cada observación conserva las 14 columnas, la fila original, `X1`/`Y1` como
texto y la posición de fuente. El ID interno es el hash de la fila más un
ordinal de ocurrencia; por ello dos filas iguales siguen siendo dos
observaciones.

La repetición exacta de 2025 se conserva: son las filas 1 y 2 del 3 de enero,
Estivella, paraje «castillo beselga». Comparten los 14 valores visibles y
reciben IDs terminados en `:1` y `:2`. No se afirma si es duplicidad
administrativa o de presentación.

Anomalías de la tabla, sin corregir:

- `Hora fin` no forma una hora válida en 172/281 filas de 2025 y 95/143 de
  2026 (`0:71`, `0:60`, `0:81`, etc.); es un patrón sistemático, no un caso
  aislado;
- no hay superficies totales negativas;
- todos los puntos transformados caen dentro del límite oficial valenciano;
- la denominación SIGIF coincide exactamente con alguno de los nombres del
  municipio oficial en 257/281 casos de 2025 y 127/143 de 2026. Las demás
  diferencias se conservan y suelen involucrar variantes bilingües o de
  denominación, pero no se normalizan silenciosamente.

## Evidencia sobre X1/Y1

La evidencia combinada permite usar los campos como **punto de inicio en
ETRS89 / UTM huso 30N (EPSG:25830), X=easting, Y=northing, metros**:

1. La [Orden 30/2017 y sus normas técnicas
   PLPIF](https://prevencionincendiosgva.es/Documents/PlanesVigilancia/legislacion/Orden%2030-2017%20normas%20t%C3%A9cnicas%20PLPIF.pdf)
   indican que los años recientes localizan el punto de inicio de cada incendio
   con coordenadas UTM.
2. La capa oficial ICV 2024 declara `sourceSpatialReference=25830` y publica
   atributos `x`/`y`.
3. La comparación reproducible de 473 filas SIGIF 2024 con 473 features ICV
   encontró 387 coincidencias por fecha y municipio normalizado y, dentro de
   ellas, **351 pares X/Y exactamente iguales**.

Las diferencias restantes no se corrigen. La transformación EPSG:4326 es un
campo derivado; los textos `X1`/`Y1` originales permanecen intactos.

## Límite administrativo y selección EFFIS

El límite procede de la capa oficial [Municipios del
ICV](https://carto.icv.gva.es/arcgis/rest/services/0105_delimitaciones/0105_Delimitaciones/MapServer/0).
Se descargaron sus 542 features, cuyo CRS fuente declarado es EPSG:25830, se
solicitaron en EPSG:4326 y se disolvieron mediante unión. No se dibujó ni
aproximó el contorno.

EFFIS se consulta por el BBOX exacto de ese límite. El pipeline comprueba el
recuento WFS `hits`, conserva la respuesta recibida y solo después selecciona
el año y ejecuta una intersección geométrica con el límite disuelto. El campo
`PROVINCE` no participa en la selección. Los 13/22 elementos anuales del BBOX
se reducen respectivamente a 9/16 intersecciones reales.

Las 25 geometrías seleccionadas son topológicamente válidas según Shapely/OGC.
EFFIS publica `AREA_HA=0` para los IDs `279366` (2025) y `561262` (2026); se
conservan sin reinterpretar. En 2026 aparecen dos áreas mayores de 500 ha sin
candidato SIGIF: `570518` (Nules, 9.222 ha, 25-07) y `612812` (Tírig, 726 ha,
07-08). Ambas son posteriores al final observado de SIGIF, por lo que la
ausencia de candidato no demuestra ausencia de incendio administrativo.

## Candidatos SIGIF–EFFIS

Solo se consideran pares del mismo año, a un máximo de 20 km y 14 días. La
puntuación registra:

- distancia del punto SIGIF al perímetro EFFIS;
- diferencia entre fecha SIGIF y `FIREDATE`, sin llamar ignición a esta última;
- igualdad normalizada municipio/`COMMUNE`;
- similitud orientativa de superficies.

La clasificación es fuerte desde 75 puntos, posible desde 50 y débil por
debajo. Todas las salidas tienen `link_status="candidate"`. Hay 36 pares en
2025 que afectan a 34 registros SIGIF y 17 en 2026 que afectan a 16; 247 y 127
filas SIGIF, respectivamente, no tienen candidato.

Los candidatos débiles son deliberadamente amplios para auditoría humana y no
deben mostrarse como enlaces. Incluso los fuertes requieren revisión o una
evidencia independiente antes de consolidarse.

### Ibi / Font Roja, julio de 2025

El sistema genera un candidato fuerte de 90 puntos:

- SIGIF: 18-07-2025, Ibi, Sant Pasqual, 183,4198 ha;
- EFFIS `id=275862`: `FIREDATE` 18-07-2025, `COMMUNE=Ibi`, 185 ha;
- distancia del punto SIGIF al borde EFFIS: 13,184 m;
- similitud de superficies: 0,991458.

Es un caso de prueba muy consistente, pero permanece `candidate`; no se ha
encontrado un identificador público común ni otra evidencia independiente que
permita marcarlo confirmado.

## Licencias y publicación

- **SIGIF:** su [aviso legal](https://prevencionincendiosgva.es/AvisoLegal) es
  restrictivo. Los HTML y JSONL no se publican y sigue pendiente una
  aclaración escrita.
- **EFFIS:** [CC BY 4.0](https://forest-fire.emergency.copernicus.eu/about-effis/data-license),
  con atribución e indicación de transformaciones. La metodología y sus
  limitaciones se documentan en [Rapid Damage
  Assessment](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment).
- **Límite ICV:** se documentan fuente, CRS, fecha, capa y [condiciones de uso
  de geoinformación ICV](https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv)
  por separado. El límite disuelto tampoco se publica en esta fase.

## Archivos y volumen

Código/configuración versionables:

- `scripts/ingest/comunitat_valenciana/download_recent.py`;
- `scripts/ingest/comunitat_valenciana/requirements-recent.txt`;
- `data/sources/gva_recent_pipeline.json`;
- `tests/test_recent_pipeline.py`.

El snapshot final ocupa:

- raw: **24.952.118 bytes** (23,80 MiB);
- processed: **16.097.690 bytes** (15,35 MiB);
- total: **41.049.808 bytes** (39,15 MiB).

Las cuatro colecciones principales ocupan 1.142.099 bytes sin comprimir y
180.198 bytes con `gzip`: SIGIF 2025/2026, 572.122/291.662 bytes; EFFIS
2025/2026, 45.695/232.620 bytes. El resto corresponde sobre todo al límite
municipal original y disuelto, conservados para reproducibilidad.

## Recomendación para CV-2.3

Puede iniciarse una integración **local y reversible** con tres estados
visibles: ICV consolidado, SIGIF administrativo provisional y EFFIS satelital
provisional. El frontend debe leer un manifiesto reciente, marcar 2026 como
incompleto y mantener los candidatos como metadatos de revisión, no como
uniones.

La publicación pública de SIGIF sigue bloqueada por licencia. Por tanto,
CV-2.3 puede preparar el código y validarlo localmente, pero no debe desplegar
los JSONL SIGIF ni una colección derivada que reproduzca sus filas hasta recibir
la autorización. La capa EFFIS podría publicarse separadamente cumpliendo CC BY
4.0, aunque no debe presentarse como inventario oficial GVA.
