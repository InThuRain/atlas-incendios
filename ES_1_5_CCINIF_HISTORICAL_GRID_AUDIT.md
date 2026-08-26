# ES-1.5 — Auditoría nacional de la malla histórica EGIF / CCINIF

Fecha de corte: **26/08/2026**

Estado: auditoría local. No se ha modificado el frontend, no se ha publicado
ningún activo y los KMZ recibidos permanecen fuera de Git. Los partes EGIF
mantienen `geometry=null`.

## 1. Conclusión ejecutiva

La entrega directa de `HOJAS.kmz` y `CUADRICULAS.kmz` por el Centro de
Coordinación de la Información Nacional sobre Incendios Forestales (CCINIF /
MITECO) resuelve la clave espacial para la mayor parte de EGIF nacional sin
reconstruir la malla ni inferir coordenadas.

El cruce conservador de **646.887 partes** EGIF 1968–2023 obtiene:

| Estado | Partes | Significado |
|---|---:|---|
| `A_CONFIRMED` | 626.957 | `HOJA+CUAD` exacto en una celda con geometría entregada por CCINIF |
| `B_PROBABLE` | 0 | no se necesita una categoría intermedia para los enlaces exactos |
| `C_AMBIGUOUS` | 3.465 | 2 referencias parciales y 3.463 casos canarios cuyo `CUAD` existe en geometrías sin `HOJA` |
| `D_UNUSABLE` | 1.515 | referencia completa sin clave exacta utilizable en el activo |
| `NO_REFERENCE` | 14.950 | no hay ni `HOJA` ni `CUADRICULA` |

En total hay **631.935** partes con ambos componentes, **5.426** pares
distintos y **626.957** enlaces exactos a **5.183** celdas distintas. La
clasificación A confirma exclusivamente la relación documental
parte→celda; no confirma la ubicación exacta, el perímetro, la superficie
quemada ni la identidad de un episodio.

El control del País Valencià reproduce exactamente CV-3.5: 9.175 partes,
8.565 con ambos códigos, 610 sin referencia y 270 pares únicos. Los 270 pares
aparecen en el KMZ, por lo que esos 8.565 enlaces pasan a `A_CONFIRMED`.

## 2. Procedencia y preservación

El responsable del proyecto recibió ambos ficheros directamente de CCINIF y
aportó la siguiente explicación institucional:

- son referencias históricas usadas desde los primeros años de la
  estadística;
- se basan en hojas y cuadrículas nominales de 10 × 10 km de la Cartografía
  Militar de España 1:250.000;
- servían para localizar incendios desde aviones anfibios;
- `HOJA/CUADRICULA` se mantuvo en los partes por continuidad histórica desde
  1968.

No se conserva el correo ni ningún dato personal. La fecha de recepción
registrada es 26/08/2026, coherente con los metadatos locales de los ficheros.

| Activo | Bytes | SHA-256 |
|---|---:|---|
| `HOJAS.kmz` | 720.069 | `205454dbc043c0873afb0f4ef2e85fe9e877b133e8f5b9240e8f23125d5c79ce` |
| `CUADRICULAS.kmz` | 1.461.962 | `dd1a3193c0362e2ee5b027ca401cbe85b4d27a52af791157a117d819be6a66a3` |

Se preservan bajo
`data/raw/ccinif/historical_grid/received_2026-08-26/`, ruta ignorada. Cada KMZ
contiene un único `doc.kml`; la prueba CRC de ZIP es correcta.

## 3. Método reproducible

Para no descargar los ~3,5 GiB estimados del XML completo, el descargador pide
al exportador público de EGIF solo el capítulo `Localización`. El exportador
conserva además identidad y año del parte. Los recuentos esperados proceden de
ES-1, no de una lista año–archivo recodificada.

```bash
python scripts/ingest/egif/download_national_locations.py
python scripts/audit/spain/es1_5_ccinif_historical_grid.py
python -m unittest tests.test_es1_5_ccinif_historical_grid -v
```

La extracción nacional genera 15 ZIP entre 1968 y 2023: **646.887 partes** y
23.723.927 bytes comprimidos. Cada bloque se valida contra el total y los
recuentos anuales de ES-1, se firma con SHA-256 y se reutiliza solo si su
checksum y contenido siguen siendo válidos.

El enlace aplica exclusivamente:

```text
strip + uppercase(EGIF.HOJA) + ":" + strip + uppercase(EGIF.CUADRICULA)
                                  =
strip + uppercase(CCINIF.HOJA) + ":" + strip + uppercase(CCINIF.CUAD)
```

No se rellenan ceros, no se corrigen erratas y no se usa `fuzzy matching`.
Por ejemplo, `704:C11` no equivale a `0704:C11`.

Fuentes públicas de contraste:

- [estadística oficial EGIF de MITECO](https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-incendios.html);
- [buscador/exportador público EGIF](https://servicio.mapa.gob.es/incendios/Search/Publico);
- [unidades administrativas IGN/CNIG](https://centrodedescargas.cnig.es/CentroDescargas/detalleArchivo?sec=9000029),
  usadas solo para validar compatibilidad territorial;
- delimitaciones municipales ICV ya auditadas para el control valenciano.

## 4. Estructura exacta de los KMZ

### 4.1 `HOJAS.kmz`

- 1.404 `Placemark`;
- 702 polígonos y 702 puntos auxiliares de etiqueta;
- 43 valores distintos de `HOJA`;
- 702 fragmentos poligonales: las hojas se recortan en partes terrestres;
- extensión KML: `[-9.324240275, 36.005511743, 4.328947122,
  43.799449383]`;
- 86 anillos interiores;
- dos fragmentos tienen invalidez OGC por interior desconectado; no se
  reparan y no afectan al enlace, que usa `CUADRICULAS.kmz`.

Los puntos son rótulos auxiliares, no hojas adicionales ni localizaciones de
incendio.

### 4.2 `CUADRICULAS.kmz`

- 12.440 `Placemark`;
- 6.220 polígonos y 6.220 puntos auxiliares de etiqueta;
- 6.063 fragmentos descritos con `HOJA+CUAD`;
- 5.286 celdas lógicas con clave exacta;
- 157 fragmentos en la carpeta `CUADcanarias`, con 109 etiquetas locales de
  cuadrícula pero sin atributos `HOJA`, `HUSO` o `CUTM10`;
- extensión KML: `[-18.247820299, 27.626223920, 4.328947122,
  43.786336066]`;
- 75.903 vértices, un anillo interior y ninguna geometría inválida OGC.

Las 157 geometrías canarias no permiten un enlace exacto: la misma etiqueta
local se repite en distintas islas y elegir mediante provincia o proximidad
violaría el contrato del cruce.

### 4.3 Atributos

En los 6.063 fragmentos descritos aparecen:

| Grupo | Campos | Observación demostrada |
|---|---|---|
| identidad/código | `FID`, `HOJA`, `CUAD`, `COD250`, `ID` | `HOJA+CUAD` es la clave operativa; `COD250` no es estrictamente único (`0406:O02` y `0406:P02` comparten `460215`) |
| UTM auxiliar | `X_COORD`, `Y_COORD`, `HUSO`, `ZONA`, `C29`, `C30`, `C31`, `C10`, `C100`, `CUTM10` | se preservan como atributos/procedencia; no regeneran la malla |
| medidas del fragmento | `AREA`, `PERIMETER`, `HECTARES` | describen la geometría cartográfica, nunca superficie de incendio |

`CUTM10` coincide literalmente con `HUSO+ZONA+C100+C10` en 6.059 fragmentos.
Los cuatro restantes tienen valores auxiliares vacíos/cero. No se ha
inventado semántica para `FID`, `ID`, `COD250` ni los componentes `Cxx` más
allá de estas relaciones observables.

## 5. Celdas con varios fragmentos

De las 5.286 celdas con clave, **118** tienen más de un polígono. La
distribución empieza con 47 celdas de dos fragmentos, 21 de tres y 9 de cuatro;
el máximo es 46 fragmentos (`0904:F06`, Illes Balears). La mayor fragmentación
se concentra en islas y costa: 62 de las celdas multiframe intersectan Illes
Balears, 20 Galicia y 13 Andalucía.

Una celda se modela una sola vez:

```text
historical_grid_cell 1 ──> 1..N geometry_parts
EGIF source record   N ──> 0..1 historical_grid_cell
```

Los fragmentos nunca son celdas ni incendios distintos. En 68 claves cambian
`X_COORD/Y_COORD` entre fragmentos; en 8 cambia `CUTM10` y en 2 `ZONA` al
cruzar una banda. Esos atributos se conservan por fragmento y no invalidan la
clave oficial `HOJA+CUAD`.

## 6. Cobertura nacional EGIF

### 6.1 Resumen por CCAA

| CCAA EGIF | Partes | A | C | D | Sin referencia |
|---|---:|---:|---:|---:|---:|
| Euskadi | 7.199 | 7.018 | 0 | 7 | 174 |
| Cataluña | 31.319 | 29.261 | 0 | 29 | 2.029 |
| Galicia | 264.313 | 257.592 | 0 | 1.323 | 5.398 |
| Andalucía | 45.512 | 44.428 | 0 | 29 | 1.055 |
| Asturias | 54.898 | 54.304 | 2 | 12 | 580 |
| Cantabria | 21.320 | 20.557 | 0 | 1 | 762 |
| La Rioja | 3.996 | 3.889 | 0 | 4 | 103 |
| Murcia | 4.642 | 4.608 | 0 | 2 | 32 |
| C. Valenciana | 22.108 | 21.495 | 0 | 3 | 610 |
| Aragón | 15.194 | 14.901 | 0 | 9 | 284 |
| Castilla-La Mancha | 28.735 | 28.256 | 0 | 1 | 478 |
| Canarias | 3.770 | 0 | 3.463 | 25 | 282 |
| Navarra | 9.572 | 9.567 | 0 | 5 | 0 |
| Extremadura | 35.465 | 35.134 | 0 | 14 | 317 |
| Illes Balears | 5.933 | 5.719 | 0 | 0 | 214 |
| Madrid | 11.451 | 10.990 | 0 | 0 | 461 |
| Castilla y León | 81.438 | 79.238 | 0 | 29 | 2.171 |
| Ceuta | 22 | 0 | 0 | 22 | 0 |

El manifiesto contiene además los 56 recuentos anuales y los recuentos por
provincia. Melilla y `OTRO PAIS` no aparecen en el snapshot EGIF observado.

### 6.2 Evolución temporal

- En 1968 existe un único par completo (`0000:000`), no enlazable; 1969–1973
  no contienen pares completos.
- El primer enlace exacto aparece en **1974**: 3.655 de 3.920 partes.
- Desde 1983 el par está poblado en prácticamente todos los registros; las
  discrepancias con la malla se conservan.
- `X/Y` empieza a coexistir en **1998** (1.713 partes) y llega a todos los
  registros desde 2016 en este snapshot.
- `HOJA+CUAD` sigue usándose hasta el último año disponible, **2023**.

Esto matiza la frase «desde 1968»: el campo existe por continuidad del sistema,
pero los datos observados no muestran uso efectivo generalizado hasta 1974.

## 7. Control del País Valencià

| Medida | Resultado |
|---|---:|
| partes 1968–1992 | 9.175 |
| `HOJA+CUAD` | 8.565 |
| sin referencia | 610 |
| pares únicos | 270 |
| pares presentes en CCINIF | 270 |
| partes `A_CONFIRMED` | 8.565 |

Casos de control:

| Parte | Caso | Par | Resultado |
|---|---|---|---|
| `1992460250` | Marines | `0704:C11` | A, un fragmento |
| `1992120403` | Altura | `0804:B01` | A, un fragmento |
| `1992469001` | Marines–Altura, municipio no identificado | `0804:B01` | A, un fragmento; incompatible con la provincia declarada y retenido como anomalía |
| `1990030079` | Castell de Castells | `0804:N04` | A, un fragmento |

La malla no resuelve Marines–Altura como un solo episodio. Solo demuestra qué
celda citó cada parte.

De los registros valencianos A con código municipal no cero, 5.244 celdas
intersectan el municipio actual, 10 no lo intersectan y una no pudo probarse
contra el catálogo. Esta comparación usa límites actuales, no históricos, por lo
que es diagnóstica y no modifica ni municipio ni celda.

## 8. Validación territorial nacional

Sobre los 626.957 enlaces A:

- 626.452 celdas intersectan la provincia declarada; 505 no;
- 626.779 intersectan la CCAA declarada; 178 no;
- las incompatibilidades se concentran en 149 combinaciones celda–provincia y
  78 celda–CCAA distintas.

Una celda puede cruzar límites y no se espera relación 1:1. La prueba exige
solo alguna intersección. Un resultado negativo queda como anomalía del
conjunto (código histórico, dato erróneo o límite actual incompatible), nunca
como corrección automática. La certeza A describe el enlace exacto con el
activo oficial, no la coherencia de todos los atributos administrativos.

## 9. CRS, husos y campos UTM

La geometría entregada está codificada como KML 2.2, es decir, coordenadas
longitud/latitud con semántica WGS 84. Para los fragmentos con atributos:

- huso 29: 1.089;
- huso 30: 3.674;
- huso 31: 1.300;
- `ZONA` usa `S`/`T`, con un valor vacío;
- Canarias carece de estos atributos en el KMZ.

En 3.359 fragmentos de 100.000.000 m² nominales, el centro `X/Y` queda a una
mediana de 76,47 m del centro KML bajo ETRS89/UTM, frente a 171,39 m bajo
ED50/UTM. Es un contraste de consistencia del activo convertido, no prueba del
datum histórico original. El KMZ no declara ese datum y no se reconstruye ni
transforma la malla desde `X/Y`.

No hay geometrías con atributos de husos 27/28 en `CUADRICULAS.kmz`; los
valores anómalos de `huso` observados en algunos partes EGIF se conservan como
datos fuente, no se emplean para el cruce.

## 10. Modelo normalizado recomendado para ES-2

`historical_grid_cell` debe ser una entidad espacial documental reutilizable e
independiente tanto de la jerarquía territorial como de `fire_geometry`:

```json
{
  "grid_cell_id": "ccinif-grid:0704:C11",
  "reference_system": "CCINIF historical EGIF 10 km grid",
  "hoja": "0704",
  "cuadricula": "C11",
  "geometry_parts": [],
  "original_attributes_by_part": [],
  "source": "CCINIF / MITECO",
  "provenance": {},
  "publishable": false
}
```

La relación del parte contendrá `spatial_reference_id`,
`interpretation_status` y banderas de compatibilidad administrativa. No copia
la geometría en el parte, no rellena `geometry` y no crea `episode_id`.

ES-2 debe contemplar desde el comienzo canales separados:

```text
source record
├─ fire geometries (0..N)
├─ historical spatial references (0..N)
└─ territory relations (0..N)
```

La malla es transversal a CCAA/provincia/municipio: puede intersectar varios
territorios, pero no pertenece conceptualmente a ninguno de ellos.

## 11. Tamaño y formato web futuro

Una estimación sin simplificación para las celdas realmente enlazadas da:

| Activo conceptual | Elementos | Raw | gzip |
|---|---:|---:|---:|
| celdas únicas GeoJSON | 5.183 celdas / 5.941 fragmentos / 73.335 vértices | 3.441.963 B | 881.459 B |
| relaciones parte→celda JSON | 626.957 | 23.824.367 B | 2.442.355 B |

La arquitectura adecuada es, por tanto, **celdas únicas + relaciones**. Repetir
la geometría en cada parte multiplicaría innecesariamente tamaño y memoria.
No se ha creado ninguno de estos assets de producción.

## 12. Contrato semántico y UX futura

Sería legítimo mostrar:

- «Referencia cartográfica histórica: cuadrícula nominal de 10 × 10 km»;
- «Este parte EGIF tiene como referencia histórica esta cuadrícula»;
- «N partes citan esta celda».

No sería legítimo afirmar:

- que la celda es el perímetro o que ardieron 100 km²;
- que el centro de la celda es el punto de incendio;
- que un punto dentro de la celda ardió N veces;
- que partes con la misma celda son el mismo episodio.

Una futura visualización usaría borde discontinuo y trama/relleno muy tenue,
una capa separada llamada «Referencia histórica 10 × 10 km» y un tooltip que
repita «no representa el perímetro del incendio». `Historia de un lugar` no la
incorporaría a recurrencia ni contención de incendios; podría ofrecer una
sección documental aparte. El permalink identificaría la celda como entidad
de referencia, no como geometría de incendio.

## 13. Licencia y consulta pendiente

Las [condiciones generales de MITECO](https://www.datosabiertos.miteco.gob.es/es/aviso-legal.html)
permiten reutilizar información sometida a ellas con atribución y sin sugerir
respaldo oficial, pero exceptúan contenidos con derechos de terceros. La
entrega directa no incluyó licencia expresa y la base declarada es cartografía
militar. Por tanto:

```text
publishable = false
license_status = false_pending_permission
```

Consulta breve propuesta a CCINIF:

> **Asunto: permiso de reutilización de la malla histórica EGIF**
>
> Muchas gracias por facilitarnos `HOJAS.kmz` y `CUADRICULAS.kmz`. Estamos
> documentando su uso como referencia histórica de los partes EGIF, siempre
> separada de los perímetros de incendio. ¿Podrían confirmarnos por escrito si
> podemos publicar en el Atlas de Incendios de España un derivado de estas
> geometrías que: (1) convierta KML a GeoJSON, (2) seleccione las celdas
> citadas por EGIF y (3), si fuera necesario, simplifique sus vértices sin
> cambiar la cuadrícula? Rogamos indiquen la licencia aplicable, la fórmula de
> atribución deseada, la fecha/versión que debemos citar y si la procedencia de
> la Cartografía Militar 1:250.000 impone alguna condición adicional. También
> agradeceríamos confirmación de si pueden redistribuirse el subconjunto
> GeoJSON y las relaciones parte→celda, dejando claro que la celda no es el
> perímetro ni la superficie quemada.

No debe enviarse ningún KMZ ni derivado a GitHub, Pages o un Release antes de
recibir esa respuesta.

## 14. Problemas abiertos y recomendación

Problemas que permanecen:

1. 157 fragmentos de Canarias carecen de `HOJA`; 3.463 partes solo pueden
   clasificarse C y no deben enlazarse por etiqueta/provincia.
2. 1.515 partes tienen pares completos no utilizables, principalmente valores
   ausentes de la malla o anómalos; no se corrigen.
3. Hay 505 incompatibilidades de provincia y 178 de CCAA que requieren
   auditoría de calidad, no corrección automática.
4. El datum histórico de los atributos auxiliares no está declarado; no es
   necesario para usar el KML recibido, pero sí debe conservarse como
   desconocido.
5. Falta permiso expreso de redistribución/transformación.

**Recomendación para ES-2:** incorporar ya al diseño nacional la entidad
`historical_grid_cell` y la relación parte→referencia, pero mantener las
geometrías fuera del frontend y de los perfiles de publicación. Preparar el
pipeline de celdas únicas de forma fail-closed; activarlo en una fase posterior
solo tras permiso escrito y una revisión específica de Canarias y de las
incompatibilidades administrativas.
