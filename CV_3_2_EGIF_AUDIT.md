# CV-3.2 — Descarga y auditoría EGIF 1968–1992

Fecha de adquisición del snapshot: **2026-08-19 UTC**  
Ámbito: Alicante, Castellón y Valencia; 1968–1992.  
Estado: descarga y normalización completas; sin integración en el frontend y
sin publicación de datos.

## Resultado ejecutivo

- El exportador XML completo del buscador público EGIF entregó **9.175 de
  9.175 partes**: Alicante 2.514, Castellón 2.600 y Valencia 4.061.
- Coinciden los 75 recuentos provincia × año inventariados en CV-3.1. No se
  alteró ningún registro para obtener esa coincidencia.
- `NumeroParte` e `IdPif` son únicos en los 9.175 registros y los 9.175
  `NumeroParte` concuerdan con su año y código provincial.
- Eso identifica con seguridad un **parte administrativo**, no necesariamente
  un episodio físico único. El identificador interno es por tanto
  `egif-record:<NumeroParte>` y todos conservan
  `episode_identity_status=unresolved`.
- La colección normalizada contiene 9.175 registros y **cero geometrías**. No
  hay X/Y en el XML del periodo; no se ha transformado ni inventado ningún
  punto.
- Hay municipio oficial resuelto para 5.254 registros, hoja/cuadrícula para
  8.565 y ninguna localización espacial para 610. Una hoja/cuadrícula no se
  presenta como coordenada precisa.
- Hay 180 partes con superficie forestal declarada mayor o igual a 500 ha.
  El filtro de superficie total del buscador daba 181: el único caso distinto
  es `1992030104`, con 400 ha forestales y 100 ha agrícolas.
- Se localizaron seis pares de partes con atributos sustantivos idénticos salvo
  los identificadores. Se conservaron los doce registros.
- No hay fechas de extinción anteriores a detección, superficies negativas,
  identificadores repetidos ni incongruencias entre el año/provincia y
  `NumeroParte`. Sí hay 1.081 superficies forestales iguales a cero.
- El exportador repite literalmente
  `ParteMonte.daniosconaprovechamiento` 744 veces en 581 registros; todas las
  apariciones se conservan en `original_attributes`.

## Reproducción

El pipeline usa únicamente la biblioteca estándar de Python:

```bash
python3 scripts/ingest/egif/gva_1968_1992.py all
python3 scripts/ingest/egif/gva_1968_1992.py process
python3 -m unittest tests.test_egif_pipeline -v
```

`all` consulta el buscador oficial, solicita el parte completo XML, espera la
finalización del exportador, descarga el ZIP y verifica antes de escribir:

1. total declarado por el servicio;
2. número real de elementos `Pif` del XML;
3. provincia de los registros;
4. distribución anual de CV-3.1;
5. integridad ZIP/XML y SHA-256.

La escritura es temporal y atómica. Un ZIP ya acreditado por el manifiesto se
reutiliza salvo con `--force`. Una descarga incompleta finaliza con código de
salida distinto de cero.

Los diccionarios de municipio y causa proceden del endpoint SPARQL oficial del
IEPNB y se conservan como snapshots separados. El OCR opcional de los anuarios
escaneados se reproduce con:

```bash
python3 scripts/ingest/egif/audit_annual_publications.py PDF_DIR OUTPUT.json \
  --tesseract /ruta/a/tesseract --tessdata-prefix /ruta/a/tessdata
```

El OCR solo localiza páginas candidatas. Ninguna cifra no revisada se toma como
dato oficial.

## Snapshot raw

| Provincia | Registros | ZIP | XML sin comprimir | SHA-256 ZIP |
|---|---:|---:|---:|---|
| Alicante | 2.514 | 565.322 B | 14.069.001 B | `4c41efead6f26c2a5e7c1d0be96d3266262cd0e8d4eeb27325ab396e60deb98b` |
| Castellón | 2.600 | 614.194 B | 14.474.014 B | `3ff4f7149666b572a2c898975e4876bae677ad4352a11101f359c3c04e713f45` |
| Valencia | 4.061 | 963.591 B | 23.648.175 B | `6c691ac49a4351d4eacc0dde7caf5f27221df65eb91ce1ed42787d97078f45f4` |
| **Total** | **9.175** | **2.143.107 B** | **52.191.190 B** | — |

El ZIP es la respuesta original, conservada byte a byte. Los nombres internos
y la fecha `generated` del XML constan en
`data/sources/egif_gva_1968_1992_manifest.json`.

## Esquema histórico

La documentación EGIF distingue seis modelos de parte. El snapshot contiene
registros de todos sus periodos:

| Periodo | Modelo documental | Registros |
|---|---|---:|
| 1968–1971 | 1 | 404 |
| 1972–1979 | 2 | 1.991 |
| 1980–1982 | 3 | 1.525 |
| 1983–1988 | 4 | 2.598 |
| 1989 | 5 | 392 |
| 1990–1992 | 6 | 2.265 |

El XML no conserva seis XSD originales. Los tres ZIP incorporan el mismo XSD
actual, con 299 declaraciones y SHA-256
`8f7de846d6c9a3f2a2c0f0ee9546dfdc7e2f1a44c0fbc66fb5332df874d1a04a`.
Por ello `form_model` se asigna solo por el periodo documentado; no se presenta
como un campo explícito de la fuente.

La matriz completa de 183 rutas fuente × seis periodos está en `report.json`.
Cambios observables importantes:

- año, fechas, causa y superficies forestales aparecen poblados en los seis
  periodos del exportador actual;
- hoja y cuadrícula no aparecen en 1968–1971, están presentes en 1.794 de
  1.991 registros de 1972–1979 y son casi/completamente sistemáticas después;
- la superficie agrícola empieza a aparecer en 1989, coherente con el cambio
  documental del modelo 5;
- no se observa ningún cambio de tipo léxico para una misma ruta entre
  periodos, consecuencia de la serialización común del exportador actual;
- no se ha declarado ninguna equivalencia entre nombres antiguos porque el
  exportador actual no expone esos nombres.

## Modelo normalizado e identidad

La salida es JSON Lines porque conserva la jerarquía completa del XML en
`original_attributes`, admite escritura por registros y no introduce una
dependencia geoespacial innecesaria.

Cada registro conserva `NumeroParte`, `IdPif`, año, fechas, provincia,
municipio, paraje cuando existe, causa, superficies arbolada/no arbolada,
superficie forestal, superficie agrícola/no forestal, hoja/cuadrícula,
`ParteMonte`, modelo documental, régimen de cobertura y procedencia.

La regla es deliberadamente de alcance administrativo:

```text
fire_id = egif-record:<NumeroParte>
identity_status = source_record_only
episode_identity_status = unresolved
```

Si en otro snapshot un `NumeroParte` faltase, se repitiese o no concordase con
año/provincia, el script produciría un ID estable por registro y
`identity_status=ambiguous`. No se relacionan registros por proximidad.

La cautela está justificada por la publicación definitiva de 1992: describe el
incendio de Marines–Altura como un único episodio que cruzó provincias, mientras
el XML actual contiene varios partes compatibles con componentes de ese caso
(`1992460250`, `1992120403`, `1992469001`). Se registra como candidato
documental y no se fusiona.

## Completitud

| Métrica | Alicante | Castellón | Valencia | Total |
|---|---:|---:|---:|---:|
| Registros | 2.514 | 2.600 | 4.061 | 9.175 |
| Municipio resuelto | 1.441 | 1.504 | 2.309 | 5.254 |
| Paraje poblado | 0 | 0 | 0 | 0 |
| Campos de superficie presentes | 2.514 | 2.600 | 4.061 | 9.175 |
| Causa fuente presente | 2.514 | 2.600 | 4.061 | 9.175 |
| Causa conocida, excluida “Desconocida” | 1.429 | 1.469 | 2.048 | 4.946 |
| Algún dato espacial | 2.338 | 2.437 | 3.790 | 8.565 |
| Hoja/cuadrícula | 2.338 | 2.437 | 3.790 | 8.565 |
| Coordenadas X/Y originales | 0 | 0 | 0 | 0 |
| Coordenada transformable con seguridad | 0 | 0 | 0 | 0 |
| Sin localización espacial utilizable | 176 | 163 | 271 | 610 |
| Partes con superficie forestal ≥500 ha | 40 | 61 | 79 | 180 |

“Superficie presente” significa que los dos totales forestales del exportador
están informados; 1.081 suman cero y se mantienen como cero fuente. No se usa
cero para campos ausentes.

## Localización espacial

No aparece ningún campo X/Y poblado en 1968–1992. Tampoco se encontró en esos
registros datum, huso o unidades que permitiesen una transformación. La
documentación enlazada oficial solo considera validados sus puntos desde 2005.
En consecuencia:

- `geometry = null` para 9.175 registros;
- `derived_coordinates_epsg4326 = null` para 9.175;
- hoja/cuadrícula se conserva como referencia cartográfica gruesa;
- municipio se conserva como localización administrativa;
- un código municipal `999` de Valencia no se resolvió y no se corrigió;
- no procede comprobar “coordenada fuera de provincia” al no haber coordenadas
  transformables.

Todos los registros contienen al menos una relación `ParteMonte`: 9.887
entradas en total, entre una y 18 por parte, y 9.887 códigos de catálogo de
monte no nulos. Se conservan como relaciones administrativas/de afección de la
fuente; no se interpretan como puntos ni perímetros.

Distribución por régimen:

| Régimen | Registros | Hoja/cuadrícula | Sin localización | Punto seguro |
|---|---:|---:|---:|---:|
| `selective` 1968–1979 | 2.395 | 1.794 | 601 | 0 |
| `transitional` 1980–1991 | 6.010 | 6.001 | 9 | 0 |
| `systematic_or_near_systematic` 1992 | 770 | 770 | 0 | 0 |

Esto mide disponibilidad de localización, no disponibilidad geométrica. Ningún
registro tiene perímetro y `historical_geometry_candidates` queda vacío.

## Duplicados y anomalías

No hay duplicados de `NumeroParte` ni `IdPif`. Seis grupos de dos partes tienen
el resto de atributos fuente idénticos:

- `1970121014` / `1970121417`
- `1979122667` / `1979123518`
- `1980123537` / `1980123538`
- `1982464016` / `1982464017`
- `1985464714` / `1985464715`
- `1991120152` / `1991120153`

Son **posibles duplicados**, no duplicados confirmados. No se eliminó ninguno.

| Anomalía | Casos |
|---|---:|
| Extinción anterior a detección | 0 |
| Fecha inválida o año de detección discordante | 0 |
| `NumeroParte` discordante con año/provincia | 0 |
| Código provincial interno discordante | 0 |
| Código municipal no resoluble (`999`) | 1 |
| Superficie forestal negativa | 0 |
| Superficie forestal igual a cero | 1.081 |
| Superficie forestal mayor de 100.000 ha | 0 |
| Campo escalar repetido por el exportador | 744 apariciones en 581 registros |

## Contraste con publicaciones definitivas

La página oficial enlaza 25 anuarios, uno por año. Son PDF escaneados sin capa
de texto. Se generó un índice OCR reproducible de páginas candidatas, pero solo
se incorporan cifras revisadas visualmente.

El contraste completo realizado para 1992 muestra:

| Provincia | Anuario: partes | XML actual | Diferencia XML | Superficie forestal anuario/XML |
|---|---:|---:|---:|---:|
| Alicante | 201 | 201 | 0 | 4.279,9 ha / 4.279,9 ha |
| Castellón | 214 | 213 | −1 | 7.232,3 ha / 7.232,3 ha |
| Valencia | 354 | 356 | +2 | 14.676,3 ha / 14.676,3 ha |
| **Total CV** | **769** | **770** | **+1** | **26.188,5 ha / 26.188,5 ha** |

El texto del anuario cuenta ocho grandes incendios valencianos en 1992; el XML
contiene nueve partes con superficie forestal ≥500 ha. Esto es compatible con
que un episodio interprovincial tenga varios partes, pero no demuestra una regla
general de agrupación. No se ha forzado la coincidencia.

La transcripción y contraste completo de 1968–1991 queda como trabajo separado:
el OCR es un localizador, no una fuente suficientemente fiable para incorporar
automáticamente cifras.

## Licencia y redistribución

Las condiciones generales de reutilización de MITECO permiten reproducción,
distribución, modificación, adaptación, extracción y combinación, con estas
obligaciones principales:

- no desnaturalizar el sentido de la información;
- citar `Origen de los datos: Ministerio para la Transición Ecológica y el
  Reto Demográfico`;
- conservar fecha de actualización y metadatos de reutilización;
- no sugerir participación, patrocinio o respaldo ministerial.

El subconjunto enlazado EGIF 1983–2015 usado solo para diccionarios declara CC
BY 4.0. Con esta documentación, los derivados normalizados pueden
redistribuirse cumpliendo atribución, fecha y metadatos; no se ha publicado
ningún snapshot ni asset en CV-3.2 por instrucción del proyecto.

## Tamaño y archivos

- `fires_1968_1992.jsonl`: 57.577.231 B (aprox. 2.594.314 B gzip), SHA-256
  `aa7d39115650e534661d9f639f2e4d7f0cfbc68c3fc2371cc7bef4510855de4e`.
- `report.json`: informe reproducible, matriz de campos, métricas y anomalías.
- `annual_publication_ocr.json`: índice OCR auxiliar ignorado por Git.
- Los ZIP raw y todos los procesados permanecen ignorados por Git.

## Recomendación para CV-3.3

CV-3.3 debería integrar **primero los registros sin geometría** en derivados web
separados, no buscar perímetros todavía:

1. construir un asset ligero de 9.175 registros sin `original_attributes`;
2. representar 1968–1992 en histogramas, métricas y listados, con cobertura y
   localización visibles, pero sin marcador cuando solo exista hoja/cuadrícula;
3. contar “partes EGIF” y no “incendios físicos únicos” mientras
   `episode_identity_status` sea `unresolved`;
4. revisar el candidato Marines–Altura y los seis pares aparentes en una fase
   de identidad específica, sin usar proximidad como prueba;
5. completar la transcripción controlada de los anuarios antes de publicar una
   serie comparativa definitiva;
6. abordar perímetros históricos en una fase posterior, desde las fuentes
   independientes inventariadas en CV-3.1.
