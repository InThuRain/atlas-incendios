# CV-3.5 — Auditoría de referencias espaciales EGIF 1968–1992

Fecha de auditoría: 23/08/2026  
Ámbito: Alicante, Castellón y Valencia; 1968–1992  
Unidad analizada: 9.175 partes administrativos EGIF  
Resultado cartográfico: **0 geometrías creadas; `geometry=null` se conserva en los 9.175 partes**

## Resultado ejecutivo

Los campos `hoja` y `cuadricula` forman una referencia cartográfica histórica
conjunta en 8.565 partes. No son dos sistemas independientes: siempre aparecen
juntos, no hay ningún registro con solo uno de ellos y producen 270 pares
distintos. Otros 610 partes no tienen ninguno.

La documentación oficial de MITECO permite afirmar que el sistema inicial EGIF
asignaba el incendio a una **cuadrícula nominal UTM de 10 × 10 km**, referida a
una hoja 1:200.000 del Instituto Geográfico del Ejército (IGE). El sistema se
cambió a hojas 1:250.000 del IGN a mediados de los años noventa, fuera del
periodo auditado.

No se ha encontrado una fuente oficial que documente, para los códigos
históricos descargados, la tabla hoja+cuadrícula→límites, datum, huso, origen y
sentido de filas/columnas o tratamiento de celdas en bordes de hoja, huso y
costa. Sin esos elementos no existe una transformación reproducible y no se
puede comprobar geométricamente la compatibilidad con municipios o provincias.

La clasificación conservadora resultante es:

| Estado | Partes | Representable en una fase posterior |
|---|---:|---|
| `A_CONFIRMED` | 0 | Sí, solo cuando exista conversión oficial completa |
| `B_PROBABLE` | 8.565 | No; semántica y resolución nominal conocidas, conversión incompleta |
| `C_AMBIGUOUS` | 0 | No |
| `D_UNUSABLE` | 0 | No |
| `NO_REFERENCE` | 610 | No |

Por tanto, **actualmente no puede representarse responsablemente ninguna de las
referencias como hoja o celda**. Esto no invalida los partes ni la información
estadística ya integrada en el visor.

## Método y reproducibilidad

La auditoría se regenera con:

```bash
python3 scripts/ingest/egif/audit_spatial_references.py
python3 scripts/ingest/egif/audit_spatial_references.py --check
```

Entradas locales, preservadas e ignoradas por Git:

- `data/processed/egif/gva/fires_1968_1992.jsonl` de CV-3.2;
- los tres ZIP XML provinciales de `data/raw/egif/gva/1968_1992/`;
- `data/sources/egif_gva_1968_1992_manifest.json`.

Salida versionable: `data/sources/egif_spatial_reference_audit.json`. Incluye
matrices completas por año, provincia y periodo, los 270 pares y sus frecuencias,
inventario de campos, checksums de los XSD, fuentes y restricciones de uso. El
script comprueba exactamente 9.175 partes, rechaza cualquier `geometry` no nula
y escribe de forma atómica.

El XSD embebido por el exportador es el mismo en los tres ZIP y es un esquema
actual de exportación, no los seis XSD originales de los formularios históricos.
Por eso los tipos XSD describen la serialización recibida; la población real por
periodo es la evidencia para comparar los seis modelos.

## Inventario completo de campos potencialmente espaciales

Las rutas son las del árbol normalizado que reproduce los elementos XML. La
columna «partes con valor» cuenta también ceros explícitos del exportador; no
debe confundirse con un dato informativo. El JSON de auditoría añade
`zero_value_occurrences` y `nonzero_value_occurrences`.

| Ruta XML/normalizada | Tipo XSD | Partes serializadas | Valores únicos | Periodos con valor | Ejemplos | Papel |
|---|---|---:|---:|---|---|---|
| `pif_localizacion.idcomunidad` | `xsd:short` | 9.175 | 1 | todos | `9` | administración de origen |
| `pif_localizacion.idprovincia` | `xsd:short` | 9.175 | 3 | todos | `3`, `12`, `46` | administración de origen |
| `pif_localizacion.idmunicipio` | `xsd:short` | 9.175 | 236 | todos | `0`, `33`, `102`, `106` | municipio de origen; 5.255 códigos no cero |
| `pif_localizacion.idcomarcaisla` | `xsd:short` | 5.256 | 35 | 1978 y 1983–1992 | `330`, `1205`, `4624` | comarca administrativa |
| `pif_localizacion.identidadmenor` | `xsd:short` | 0 | 0 | — | — | entidad menor, no disponible |
| `pif_localizacion.paraje` | `xsd:string` | 0 | 0 | — | — | topónimo de origen, no disponible |
| `pif_localizacion.nummunicipiosafectados` | `xsd:short` | 9.175 | 10 | todos | `1`, `2`, `3`, `4` | recuento, no localizador |
| `pif_localizacion.puntosinicioincendio` | `xsd:short` | 0 | 0 | — | — | recuento, no localizador |
| `pif_localizacion.huso` | `xsd:short` | 0 | 0 | — | — | componente UTM no disponible |
| `pif_localizacion.x` | `xsd:string` | 0 | 0 | — | — | componente UTM no disponible |
| `pif_localizacion.y` | `xsd:string` | 0 | 0 | — | — | componente UTM no disponible |
| `pif_localizacion.iddatum` | `xsd:short` | 0 | 0 | — | — | datum no disponible |
| `pif_localizacion.hoja` | `xsd:string`, máximo 4 | 8.565 | 6 | 1974–1992 | `0703`…`0805` | componente de referencia histórica |
| `pif_localizacion.cuadricula` | `xsd:string`, máximo 3 | 8.565 | 166 | 1974–1992 | `A01`…`O12` | componente de referencia histórica |
| `pif_localizacion.latitud` | `xsd:string` | 0 | 0 | — | — | coordenada no disponible |
| `pif_localizacion.longitud` | `xsd:string` | 0 | 0 | — | — | coordenada no disponible |
| `pif_condiciones.idestacionmeteorologica` | `xsd:string` | 9.175 | 1 | todos | `0` | contexto meteorológico; no localiza el origen |
| `pif_deteccion.idvigilantefijo` | `xsd:short` | 3.102 | 32 | todos | `0`, `5`, `24` | detector; no localiza el origen sin diccionario/posición |
| `pif_deteccion.RelIniciadoJuntoAPif.idiniciadojuntoa` | `xsd:unsignedByte` | 9.175 | 5 | todos | `1`, `3`, `4`, `10` | tipo de elemento próximo, no localizador |
| `pif_deteccion.RelTipoAreaIniciadoPif.idtipoarea` | `xsd:unsignedByte` | 0 | 0 | — | — | tipo de área, no disponible |
| `pif_anexo.RelEspacioProtegidoPif.idespacioprotegido` | `xsd:string` | 0 | 0 | — | — | recurso afectado, no origen |
| `pif_anexo.RelTeselaAfectadaPif.idtesela` | `xsd:int` | 0 | 0 | — | — | tesela afectada, no disponible |
| `pif_anexo.RelTeselaAfectadaPif.idteselamfe` | `xsd:int` | 0 | 0 | — | — | tesela MFE afectada, no disponible |
| `pif_incidencias.afectoespacionnatprot` | `xsd:boolean` | 9.175 | 1 | todos | `False` | indicador negativo, no identifica un espacio |
| `pif_perdidas.RelPerdidaMontePif.idtitularidadmonte` | `xsd:unsignedByte` | 8.094 | 3 | todos | `1`, `4`, `5` | categoría de titularidad, no localizador |
| `ParteMonte.idpartemonte` | `xsd:unsignedByte` | 9.175 | 18 | todos | `1`, `2`, `3`, `4` | identificador interno de relación, no localizador |
| `ParteMonte.idcomunidad` | `xsd:unsignedByte` | 9.175 | 1 | todos | `9` | administración del monte afectado |
| `ParteMonte.idprovincia` | `xsd:unsignedByte` | 9.175 | 3 | todos | `3`, `12`, `46` | administración del monte afectado |
| `ParteMonte.idcomarcaisla` | `xsd:short` | 9.175 | 37 | todos | `300`, `1200`, `4600` | comarca del monte afectado |
| `ParteMonte.idmunicipio` | `xsd:short` | 9.175 | 235 | todos | `0`, `33`, `102` | municipio del monte afectado, no punto de inicio |
| `ParteMonte.idcatalogomonte` | `xsd:int` | 9.175 | 1 | todos | `57084` | identificador exportado constante; sin semántica demostrada |
| `ParteMonte.iddemanialmonte` | `xsd:unsignedByte` | 9.175 | 3 | todos | `1`, `3`, `4` | categoría demanial, no localizador |
| `ParteMonte.idtitularidadmonte` | `xsd:unsignedByte` | 9.175 | 3 | todos | `1`, `3`, `5` | categoría de titularidad, no localizador |
| `ParteMonte.cup` | `xsd:string` | 0 | 0 | — | — | CUP no disponible |
| `ParteMonte.propietario` | `xsd:string` | 0 | 0 | — | — | texto del recurso, no disponible |

`ParteMonte` contiene 9.887 relaciones para 9.175 partes; sus campos describen
montes afectados y pueden repetirse. No se han tratado como localización del
inicio. Tampoco se ha interpretado el valor constante `57084` como un monte
real sin su diccionario.

Al descontar el centinela literal `0`, `pif_localizacion.idmunicipio` tiene
5.255 partes informativos, `idvigilantefijo` 611 y
`idestacionmeteorologica` ninguno. `ParteMonte.idmunicipio` tiene valor no cero
en los mismos 5.255 partes, aunque suma 5.630 ocurrencias por la cardinalidad de
la relación. Para los demás campos de la tabla, «serializado» y «no cero»
coinciden o el campo no está poblado. Estas dos coberturas quedan separadas en
el JSON mediante `records_with_value` y `records_with_nonzero_value`.

## Evolución entre los seis modelos

| Modelo documental | Partes | Hoja+cuadrícula | Sin pareja | Municipio de origen no cero | Observación |
|---|---:|---:|---:|---:|---|
| 1968–1971 | 404 | 0 | 404 | 0 | el exportador no conserva hoja/cuadrícula ni municipio informativo |
| 1972–1979 | 1.991 | 1.794 | 197 | 0 | pareja presente desde 1974; una comarca aislada en 1978 |
| 1980–1982 | 1.525 | 1.516 | 9 | 0 | pareja casi completa; sin municipio informativo |
| 1983–1988 | 2.598 | 2.598 | 0 | 2.598 | pareja y municipio de origen poblados |
| 1989 | 392 | 392 | 0 | 392 | mismo patrón espacial observado |
| 1990–1992 | 2.265 | 2.265 | 0 | 2.265 | mismo patrón; un código municipal `999` no resuelto |

La ruptura observada no coincide exactamente con el inicio nominal del segundo
modelo: 1972 y 1973 no tienen pares, y la población comienza en 1974. No se ha
inferido si los vacíos significan «no recogido», «no migrado» o «desconocido».

## Descomposición exacta de las 8.565 referencias

### Por año

| Año | Partes | `B_PROBABLE` | Sin referencia |
|---:|---:|---:|---:|
| 1968 | 113 | 0 | 113 |
| 1969 | 73 | 0 | 73 |
| 1970 | 138 | 0 | 138 |
| 1971 | 80 | 0 | 80 |
| 1972 | 30 | 0 | 30 |
| 1973 | 150 | 0 | 150 |
| 1974 | 293 | 284 | 9 |
| 1975 | 256 | 253 | 3 |
| 1976 | 242 | 242 | 0 |
| 1977 | 199 | 198 | 1 |
| 1978 | 558 | 556 | 2 |
| 1979 | 263 | 261 | 2 |
| 1980 | 453 | 450 | 3 |
| 1981 | 707 | 703 | 4 |
| 1982 | 365 | 363 | 2 |
| 1983 | 494 | 494 | 0 |
| 1984 | 470 | 470 | 0 |
| 1985 | 523 | 523 | 0 |
| 1986 | 385 | 385 | 0 |
| 1987 | 406 | 406 | 0 |
| 1988 | 320 | 320 | 0 |
| 1989 | 392 | 392 | 0 |
| 1990 | 626 | 626 | 0 |
| 1991 | 869 | 869 | 0 |
| 1992 | 770 | 770 | 0 |

### Por provincia

| Provincia | Partes | `B_PROBABLE` | Sin referencia |
|---|---:|---:|---:|
| Alicante | 2.514 | 2.338 | 176 |
| Castellón | 2.600 | 2.437 | 163 |
| Valencia | 4.061 | 3.790 | 271 |

Las seis hojas son `0703` (127 partes), `0704` (2.322), `0705` (271),
`0803` (1.653), `0804` (3.998) y `0805` (194). Las cuadrículas siguen el patrón
léxico letra `A`–`O` + dos dígitos y hay 166 valores observados. La combinación
produce 270 pares únicos. Esta regularidad demuestra consistencia formal, no la
posición de las celdas.

## Evidencia documental y límites de interpretación

| Documento | Organismo / fecha | Sección | Interpretación respaldada |
|---|---|---|---|
| [Estadística General de Incendios Forestales](https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html) | MITECO, consulta 23/08/2026 | Base de datos nacional | EGIF comienza en 1968 y se alimenta de partes normalizados; calidad ligada a cumplimentación y consolidación |
| [La restauración forestal de España: 75 años de una ilusión](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/desertificacion-restauracion/libro75anosdeunailusion_b_tcm30-530962.pdf) | MAPAMA / SECF, 2017 | capítulo «Las repoblaciones y los incendios forestales», pp. 347–348 | sistema inicial: celda UTM 10×10 km referida a hoja IGE 1:200.000; cambio a IGN 1:250.000 a mediados de los noventa |
| [Instrucciones del Parte de Incendio Forestal v3.6](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/instrucciones_parte_incendio_tcm30-512355.pdf) | CLIF/MITECO, versión 3.6 | p. 10, 3.1 Localización | en el modelo actual hoja/cuadrícula y X/Y UTM son campos distintos; X/Y es el punto de inicio y exige datum |
| [Interpretación de la base EGIFWEB](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/estad%C3%ADstica-iiff/Interpretaci%C3%B3n%20BD_Egifweb.pdf) | ADCIF/MITECO | p. 1 | capítulos/tablas del parte y relaciones múltiples; necesidad de diccionarios |
| [Orden FOM/2807/2015](https://www.boe.es/buscar/act.php?id=BOE-A-2015-14129) | BOE / Ministerio de Fomento, 26/12/2015 | arts. 2, 4, 5 y 7 | régimen de productos digitales IGN, incluidas cuadrículas cartográficas oficiales |
| [Política de datos del IGN](https://www.ign.es/web/politica-datos) | IGN/CNIG, consulta 23/08/2026 | licencia y reconocimiento | licencia compatible con CC BY 4.0 y atribución de productos y derivados IGN |

La instrucción v3.6 documenta el sistema posterior 1:250.000 y no puede usarse
retroactivamente para decodificar 1968–1992. Tampoco se ha encontrado evidencia
de que los códigos sean hojas MTN50, MTN25 o una malla moderna IGN. El parecido
formal no basta.

### Lo demostrado

- la referencia conjunta es una celda nominal UTM de 10×10 km;
- depende de una hoja IGE 1:200.000;
- `hoja` y `cuadricula` son campos diferenciados y simultáneos;
- la resolución nominal es 100 km² por celda, no un área quemada ni precisión
  estadística;
- el periodo auditado precede al cambio de sistema de mediados de los noventa.

### Lo que falta

- serie/edición exacta de hojas IGE usada por EGIF;
- tabla oficial de los seis códigos de hoja y las 166 subcuadrículas;
- datum geodésico original;
- huso o regla para celdas que cruzan husos;
- origen y dirección de letras/números;
- reglas de bordes de hoja, costa y solapamiento;
- significado documental de pares ausentes antes de 1974.

No hay base para escoger ED50, ETRS89, WGS84 u otro datum. No se ha transformado
nada a EPSG:4326.

## Clasificación y validación geográfica

`A_CONFIRMED` exige semántica, tabla de conversión, CRS/datum/huso y geometría
reproducible documentados. `B_PROBABLE` exige semántica y resolución nominal
documentadas, aunque falte al menos un componente esencial. `C_AMBIGUOUS`
reserva referencias parciales, mal formadas o con varias interpretaciones.
`D_UNUSABLE` reserva referencias existentes que no permiten una representación
responsable.

Todos los pares observados son completos y bien formados; por eso los 8.565
quedan en B, no en C/D. Ninguno alcanza A. Al no existir geometría A, no se han
calculado intersecciones con municipio o provincia, ni casos interiores,
exteriores o fronterizos. Generar celdas para hacer esa comprobación habría
requerido elegir precisamente los parámetros que faltan.

El municipio se conserva como control independiente para una futura validación,
nunca para seleccionar o desplazar una celda. Los casos de control preservados
son:

| Parte | Municipio | Referencia | Resultado actual |
|---|---|---|---|
| `1992460250` | Marines | `0704:C11` | preservada, no probada geométricamente |
| `1992120403` | Altura | `0804:B01` | preservada, no probada geométricamente |
| `1992469001` | sin municipio resuelto | `0804:B01` | preservada, no probada geométricamente |
| `1990030079` | Castell de Castells | `0804:N04` | preservada, no probada geométricamente |

Esto conserva Marines–Altura como caso multiparte sin adaptar el sistema para
que encaje ni resolver la identidad del episodio.

## Modelo conceptual propuesto

No se modifica `fires_1968_1992.jsonl`. Una incorporación futura podría añadir
una relación separada:

```json
{
  "source_record_id": "1992460250",
  "fire_geometry": null,
  "spatial_reference": {
    "source_type": "egif_historical_sheet_grid",
    "original_fields": {"sheet": "0704", "grid": "C11"},
    "reference_system": "IGE_1_200000_UTM_10KM",
    "sheet_id": "0704",
    "grid_id": "C11",
    "crs_original": null,
    "datum": null,
    "zone": null,
    "nominal_resolution_m": [10000, 10000],
    "interpretation_status": "B_PROBABLE",
    "evidence_ids": ["miteco_forest_history_book"],
    "geometry_status": "not_constructed"
  }
}
```

`spatial_reference_geometry`, si algún día existe, seguirá siendo distinta de
`fire_geometry`/perímetro. La ausencia de la primera tampoco invalida el parte.

## Representación futura y tamaño

Si una tabla oficial elevara referencias a `A_CONFIRMED`, convendría almacenar:

1. **270 celdas únicas** con su geometría y procedencia;
2. **8.565 relaciones** parte→celda.

No conviene repetir el polígono en cada parte. Para rectángulos simples serían
1.080 vértices distintos y 1.350 posiciones GeoJSON contando el cierre de cada
anillo. La relación compacta medida ocupa 222.691 bytes sin comprimir y 33.456
bytes gzip; el catálogo alfanumérico de celdas y recuentos, 4.795 y 1.077 bytes.
Una capa GeoJSON de 270 rectángulos se estima en 45–90 kB y 8–25 kB gzip. Es una
estimación estructural: **no se generaron coordenadas ni polígonos**.

La simbología futura debería usar borde discontinuo, relleno tenue o trama y la
etiqueta: «Referencia cartográfica histórica: cuadrícula nominal de 10 × 10 km.
No representa el perímetro del incendio». Nunca debe compartir el estilo de los
perímetros ICV/EFFIS ni participar en Historia de un lugar como contención
puntual.

## Usos legítimos y no legítimos

Solo si la referencia llegara a A sería legítimo:

- mostrar la celda como área documental de referencia;
- contar «X partes EGIF referidos a esta celda»;
- filtrar o resumir partes por celda, con resolución y limitaciones visibles.

No sería legítimo, ni siquiera entonces:

- tratar la celda como superficie quemada o perímetro;
- asignar su centroide como punto de inicio;
- afirmar que un punto ardió porque pertenece a la celda;
- calcular recurrencia exacta o superficie única quemada;
- reconstruir el incendio mediante celda, municipio, buffer o heatmap;
- deduplicar partes o resolver episodios multiparte por compartir referencia.

## Licencias

Los atributos EGIF siguen bajo las condiciones MITECO ya auditadas, con la
atribución: «Origen de los datos: Ministerio para la Transición Ecológica y el
Reto Demográfico.»

Si se utiliza en el futuro una cuadrícula **digital del IGN**, la Orden
FOM/2807/2015 y la política IGN permiten uso y transformación con reconocimiento
del origen y declaración de obra derivada, compatible con CC BY 4.0. Esto no
autoriza automáticamente cualquier mapa histórico del IGE/Centro Geográfico del
Ejército. La ficha exacta de Biblioteca Virtual de Defensa o el producto que se
use deberá auditarse; algunas copias digitales tienen su propia fórmula de
atribución. En CV-3.5 no se ha copiado, transformado ni redistribuido ningún
producto cartográfico.

## Propuesta concreta para CV-3.6

CV-3.6 debería ser una fase documental de **obtención y validación de la clave
histórica**, no una implementación frontend:

1. solicitar a MITECO/ADCIF el diccionario o capa GIS histórica que convierte
   `hoja`+`cuadricula` del sistema IGE 1:200.000;
2. pedir datum, husos, orientación/origen de ejes y reglas de borde;
3. consultar al Centro Geográfico del Ejército/IGN sobre el índice digital de
   la serie exacta y su licencia;
4. confirmar qué significan los blancos de 1968–1973;
5. solo si se obtiene una conversión oficial, generar celdas diagnósticas,
   contrastarlas con municipio/provincia y promover únicamente los casos
   reproducibles a A.

Sin esa documentación, la recomendación es cerrar CV-3.6 sin capa espacial y
mantener el visor histórico tal como está: partes administrativos sin geometría.
