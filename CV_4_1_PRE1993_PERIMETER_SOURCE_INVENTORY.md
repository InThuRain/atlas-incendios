# CV-4.1 — Inventario de fuentes de perímetros anteriores a 1993

Fecha de corte de la investigación: **25/08/2026**

Ámbito: Alicante, Castellón y Valencia, con prioridad 1968–1992

Resultado técnico: **0 geometrías creadas, 0 cambios de frontend y 0 cambios del bundle público**

## Resultado ejecutivo

Se han inventariado **14 fuentes o rutas de acceso relevantes**. El principal
hallazgo es [ESFire30 Causes](https://zenodo.org/records/18449006), un dataset
vectorial CC BY 4.0 basado en Landsat. La intersección reproducible de sus capas
1985–1992 con el límite municipal oficial del País Valencià localiza **710
polígonos**: 195 asignados a Alicante, 206 a Castellón y 309 a Valencia por
mayor área de intersección. Son perímetros de área quemada obtenidos por
teledetección, no perímetros oficiales EGIF ni enlaces a partes administrativos.

Existe además evidencia técnica sólida de que la Generalitat conserva o
conservó una **cartografía vectorial anual oficial desde 1978 para la provincia
de Valencia**. El artículo que la describe afirma que Alicante y Castellón solo
disponen de esa serie desde 1993. El activo 1978–1992, su esquema y su licencia
no se han localizado, por lo que se clasifica `E_REFERENCE_ONLY`, no
`A_OFFICIAL_VECTOR`.

La literatura NOAA-AVHRR y Landsat documenta cartografías de incendios
valencianos, especialmente en 1991. Se han localizado artículos y mapas, pero no
los ficheros digitales originales. La tesis de M. Pilar Martín y la confirmación
directa de la autora refuerzan que esos activos existieron; su disponibilidad y
licencia siguen pendientes.

La clasificación conservadora de **fuentes** es:

| Calidad | Fuentes | Interpretación en CV-4.1 |
|---|---:|---|
| `A_OFFICIAL_VECTOR` | 0 | Ningún vector oficial pre-1993 está disponible y auditado |
| `B_DOCUMENTED_REMOTE_SENSING` | 5 | ESFire30 y cuatro trabajos Landsat/NOAA con método documentado |
| `C_DOCUMENTED_CARTOGRAPHIC_RECONSTRUCTION` | 0 | Ningún mapa alcanza aún base suficiente para digitalización responsable |
| `D_MAP_ONLY_UNCERTAIN` | 1 | Mapa histórico del plan Chera–Sot de Chera |
| `E_REFERENCE_ONLY` | 4 | Archivos oficiales o científicos cuya existencia consta, pero no están disponibles |
| `F_UNUSABLE` | 4 | Productos de contexto, agregados o fuera de periodo |

Esta clasificación es de la **fuente**, no una asignación automática de calidad
a cada incendio. Los 710 polígonos ESFire30 son candidatos B independientes;
ninguno se ha añadido a EGIF ni al visor.

## Reproducibilidad y límites

El inventario estructurado se regenera desde entradas locales ignoradas:

```bash
python3 scripts/ingest/egif/audit_pre1993_perimeter_sources.py \
  --esfire30-zip /ruta/a/ESFire30_Causes.zip

python3 scripts/ingest/egif/audit_pre1993_perimeter_sources.py \
  --esfire30-zip /ruta/a/ESFire30_Causes.zip --check
```

Entradas:

- `data/processed/egif/gva/fires_1968_1992.jsonl`, 9.175 partes normalizados;
- límite oficial de 542 municipios ICV conservado en raw;
- `ESFire30_Causes.zip`, 93.127.811 bytes, SHA-256
  `150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8`.

Salida versionable:
`data/sources/gva_pre1993_perimeter_sources.json`. Incluye las 14 fuentes, el
diagnóstico de ESFire30, los 180 partes EGIF GIF y todos sus candidatos. No
contiene coordenadas ni geometrías.

El script lee los SHP del ZIP, transforma el límite oficial al CRS declarado en
el `.prj`, intersecta espacialmente y descarta las geometrías al terminar. El
ZIP y los límites raw no entran en Git.

## Inventario de fuentes

| ID | Fuente | Periodo/ámbito útil | Formato disponible | Calidad | Activo original | Licencia/reutilización |
|---|---|---|---|---|---|---|
| `esfire30_causes` | UAH/CSIC, ESFire30 Causes | 1985–1992, toda la CV | SHP anual | B | Sí | CC BY 4.0 |
| `gva_annual_perimeter_archive_1978_valencia` | Cartografía anual Conselleria | Valencia 1978–1992 | vector citado | E | No localizado | sin aclarar |
| `gva_burned_forest_register` | Registro de Terrenos Forestales Incendiados | CV, periodo por consultar | certificado/plano | E | acceso por trámite | sin aclarar para descarga masiva |
| `gva_chera_sot_prevention_plan` | Plan Chera–Sot de Chera | 1978–1992 y posterior, local | mapa PDF | D | PDF sí; fuente no | sin aclarar |
| `martin_chuvieco_1995_noaa` | Martín y Chuvieco, *Ecología* | grandes incendios de 1991 | figuras PDF | B | mapa sí; GIS no | sin aclarar |
| `martin_chuvieco_1998_noaa` | Martín y Chuvieco | 1991, 1994, 1995 | figuras PDF | B | GIS no localizado | sin aclarar |
| `martin_thesis_noaa` | Tesis de M. Pilar Martín | varios años/incendios | tesis; archivos citados | E | no recibido | pendiente de autora/custodio |
| `viedma_chuvieco_1993_hoya_bunol` | Estudio Landsat Hoya de Buñol | Yátova/Chiva 1991 | mapas/figuras PDF | B | GIS no localizado | sin aclarar |
| `lopez_caselles_1991_landsat` | López García y Caselles | Valencia, año exacto por completar | artículo | B | GIS no localizado | copyright editorial/datos sin aclarar |
| `gva_goiif_archive` | GOIIF y grupos precursores | 1991–1992, CV | expedientes/croquis posibles | E | no inventariado públicamente | sin aclarar |
| `icv_1977_orthophoto` | Ortofoto Interministerial | 1976–1978, CV | TIFF/ECW/WMS | F | Sí | CC BY 4.0 |
| `esa_fireccilt11` | ESA CCI burned area | 1982–1992 | raster 0,05°/0,25° | F | Sí | licencia ESA/CEDA |
| `ceam_postfire` | PostFire CEAM | empieza en 1993 | portal/vector | F | Sí, fuera de periodo | no auditada para CV-4.1 |
| `miteco_egif_annual_maps` | anuarios y mapas EGIF | 1968–1992 | PDF/tablas/celdas | F | Sí | condiciones MITECO |

Los metadatos completos —URL, autores, método, formato, disponibilidad,
licencia, cautelas y próxima acción— están en el JSON.

## Hallazgo 1: ESFire30

### Qué aporta

El [registro Zenodo](https://zenodo.org/records/18449006) publica SHP anuales y
el [artículo metodológico](https://doi.org/10.3390/fire9040138) describe
perímetros ESFire30 derivados de Landsat. La resolución nominal documentada es
30 m y el método combina detección semiautomática y posprocesado. El producto de
causas asigna causas posteriormente mediante enlace/similitud o modelo; ese
atributo no convierte el polígono en registro administrativo ni confirma EGIF.

Resultado de intersección:

| Año | Alicante | Castellón | Valencia | Total |
|---:|---:|---:|---:|---:|
| 1985 | 13 | 52 | 62 | 127 |
| 1986 | 16 | 18 | 29 | 63 |
| 1987 | 3 | 7 | 9 | 19 |
| 1988 | 9 | 5 | 11 | 25 |
| 1989 | 13 | 4 | 6 | 23 |
| 1990 | 52 | 21 | 27 | 100 |
| 1991 | 46 | 38 | 87 | 171 |
| 1992 | 43 | 61 | 78 | 182 |
| **Total** | **195** | **206** | **309** | **710** |

Hay 29 polígonos que intersectan más de una provincia. La provincia de la tabla
es la de mayor área de solape; no se ha recortado ni atribuido un incendio a una
provincia administrativa. La suma de `area_ha` de los polígonos completos es
127.083,78 ha y no equivale a superficie quemada dentro del País Valencià.

### Anomalías abiertas

- El README dice EPSG:25830, mientras todos los `.prj` 1985–1992 declaran
  `ED_1950_UTM_Zone_30N`, identificable como EPSG:23030. Para la inspección se
  respetó el `.prj`; antes de producir derivados debe confirmarlo el proveedor.
- El README contiene «30 km» donde el artículo metodológico documenta 30 m. No
  se ha corregido el fichero fuente ni se ha ocultado la discrepancia.
- Los polígonos no traen fecha del episodio, municipio ni identificador EGIF.
  `Id_cuad` sirve para buscar candidatos, no para demostrar identidad.

Las 710 geometrías tienen hashes WKB distintos y suman 84.894 vértices. Una
futura capa GeoJSON mínima, sin simplificar y con solo ID/año/área, se estima en
3.310.903 bytes y 1.135.689 bytes gzip. Es pequeño para una capa diferida, pero
CV-4.1 no ha generado ni publicado ese asset.

## Hallazgo 2: archivo oficial valenciano desde 1978

El trabajo técnico [*Caracterización de los incendios forestales en la provincia
de Valencia*](https://secforestales.org/publicaciones/index.php/cuadernos_secf/article/download/17385/17214/0)
declara que la Conselleria suministró la cartografía de perímetros elaborada
anualmente. La serie está disponible desde 1978 para Valencia, mientras para
Alicante y Castellón comienza en 1993. También advierte que los primeros años
tienen menor precisión y que las técnicas mejoraron con GPS y teledetección.

Esto demuestra la existencia y alcance territorial de un archivo oficial, pero
no su disponibilidad actual, número de features, formato, CRS, escala ni
licencia. Dentro de su alcance provincia/año hay 3.256 partes EGIF y 58 de los
180 partes GIF. **No puede afirmarse que existan 3.256 o 58 perímetros:** son
solo el universo de partes que habría que contrastar al recibir el archivo.

La [sede GVA del Registro de Terrenos Forestales
Incendiados](https://sede.gva.es/es/detall-tramit?id_proc=3261) es una segunda
ruta oficial. Un certificado ampliado puede incluir plano o georreferenciación,
pero el trámite exige una solicitud concreta y no prueba que custodie una serie
masiva 1968–1992.

## Hallazgo 3: NOAA-AVHRR y M. Pilar Martín

El artículo oficial de MITECO de [Martín y Chuvieco
(1995)](https://www.miteco.gob.es/content/dam/miteco/es/parques-nacionales-oapn/publicaciones/ecologia_09_02_tcm30-100709.pdf)
documenta cartografía NOAA-AVHRR de grandes incendios mediterráneos de 1991.
Para Valencia nombra Yátova, Chiva, Tavernes, Carcaixent, Llutxent y Villalonga.
El píxel nominal es de 1,1 km y la validación se apoyó en cartografía DGCN y
trabajo de campo; el incendio de Buñol dispuso de un perímetro/GPS más completo.

El trabajo posterior conservado por
[Digital.CSIC](https://digital.csic.es/bitstream/10261/6426/1/Martin_Isabel_Serie_Geografica.pdf)
explica que la resolución se degrada hacia los extremos de escena y reconoce la
escasez de perímetros reales para validar. La tesis de M. Pilar Martín amplía el
inventario y la autora ha confirmado directamente al proyecto que cartografió
numerosos incendios y realizó validación de campo. No se han recibido los
ficheros, inventario de escenas/perímetros ni licencia.

Por ello:

- los artículos con método y mapas son fuentes B;
- los ficheros de tesis no localizados son E;
- no se debe digitalizar una figura NOAA como si tuviera precisión Landsat;
- la prioridad es recuperar los activos digitales y sus metadatos.

## Hallazgo 4: Hoya de Buñol y Chera–Sot de Chera

El estudio [Viedma y Chuvieco
(1993)](https://infomadera.net/uploads/articulos/archivo_2154_11506.pdf) usa
Landsat TM de 30 m antes y después de los incendios de la Hoya de Buñol. Registra
las imágenes en UTM con RMSE 0,8 píxeles —aproximadamente 25 m—, usa parcelas de
campo y compara el resultado con el perímetro de la Unidad Forestal de Valencia.
La coincidencia publicada es 74,07 %, lo que demuestra método y contraste, no
identidad geométrica perfecta.

Los partes `1991460176` (Yátova, 28/07/1991) y `1991460188` (Chiva,
31/07/1991) son candidatos fuertes por municipio, fecha, magnitud y
documentación. Siguen sin ser enlaces confirmados porque el artículo no publica
`NumeroParte` ni se ha recuperado el activo.

El plan oficial de Chera–Sot de Chera contiene mapas de los años 1978, 1980,
1986, 1990 y 1992. Los controles:

- `1986461220`, Sot de Chera, 18/05/1986, 877 ha forestales;
- `1992460251`, Sot de Chera, 31/08/1992, 1.072,6 ha forestales y 1.092,6 ha
  totales;

son candidatos fuertes a las manchas de 1986 y 1992. El documento caracteriza
las superficies antiguas como aproximadas y no aporta escala, CRS ni metodología
suficientes. El PDF queda D y no debe digitalizarse; debe pedirse su capa fuente.

## Matriz de los 180 partes EGIF GIF

El umbral se mantiene sobre **superficie forestal ≥500 ha**, exactamente como
CV-3.2:

| Provincia EGIF | Partes GIF |
|---|---:|
| Alicante | 40 |
| Castellón | 61 |
| Valencia | 79 |
| **Total** | **180** |

| Periodo | Partes GIF |
|---|---:|
| 1968–1969 | 4 |
| 1970–1979 | 80 |
| 1980–1989 | 65 |
| 1990–1992 | 31 |

Resultado de candidatos:

| Estado | Partes | Regla |
|---|---:|---|
| `confirmed_link` | 0 | Ninguna fuente comparte evidencia suficiente |
| `strong_candidate` | 4 | Yátova, Chiva y dos Sot de Chera con documentación independiente |
| `possible_candidate` | 36 | ESFire30 mismo año+cuadrícula o referencia documental parcial |
| `unlinked` | 140 | Sin candidato individual localizado |

ESFire30 ofrece uno o más polígonos del mismo año y `Id_cuad` para 40 partes
GIF. **Cero** tienen diferencia de superficie total ≤10 ha. Esto es compatible
con divisiones/uniones, distinta metodología, borde de cuadrícula o episodios
distintos, pero los datos no permiten elegir una explicación. No se realiza
matching por ajuste de superficie.

Los tres partes compatibles con Marines–Altura 1992 (`1992460250`,
`1992120403`, `1992469001`) permanecen como posibles candidatos separados. Un
polígono ESFire30 de 5.926,68 ha cruza Castellón/Valencia, pero no resuelve la
identidad multiparte ni se asigna automáticamente al episodio.

La matriz completa conserva por parte: fecha, provincia, municipio, superficies,
hoja/cuadrícula, candidatos documentales, candidatos ESFire30 y diferencia de
área. No contiene geometría.

## Cobertura territorial y temporal

### Alicante

- 195 polígonos ESFire30 B entre 1985 y 1992.
- 40 partes GIF en 1968–1992; 9 en 1990–1992.
- No se ha localizado archivo oficial pre-1993; la serie Conselleria citada
  comienza en 1993.
- Landsat/NOAA localizados se concentran en Valencia, por lo que Alicante tiene
  la mayor laguna documental cualitativa pese a ESFire30.

### Castellón

- 206 polígonos ESFire30 B entre 1985 y 1992.
- 61 partes GIF; la documentación oficial anual citada comienza en 1993.
- Marines–Altura 1992 es control prioritario, pero sigue sin perímetro oficial
  recuperado ni episodio multiparte resuelto.

### Valencia

- 309 polígonos ESFire30 B entre 1985 y 1992.
- evidencia de archivo vectorial oficial desde 1978;
- trabajos NOAA/Landsat de 1991 y mapa histórico Chera–Sot;
- 79 partes GIF, de los que 58 caen en el alcance temporal/territorial del
  archivo oficial aún no recibido.

Valencia tiene claramente mejor documentación histórica. Todas las provincias
carecen de fuente de perímetros localizada para 1968–1977. Para 1978–1984 solo
Valencia tiene una ruta oficial prometedora. Desde 1985 ESFire30 aporta cobertura
homogénea de teledetección en las tres.

## Viabilidad de digitalización futura

| Fuente | Georreferenciada | Controles/base | Delimitación | Decisión CV-4.1 |
|---|---|---|---|---|
| ESFire30 | Sí, con conflicto documental de CRS | geometría vectorial | existente | no digitalizar; auditar/copiar el vector tras aclarar CRS |
| archivo anual GVA | presumiblemente, sin activo | desconocidos | vector citado | solicitar original |
| NOAA 1991 | producto digital descrito | DGCN/campo; resolución km | figura general | solicitar original, no vectorizar figura |
| Landsat Hoya de Buñol | UTM y RMSE publicados | imágenes/parcelas/perímetro oficial | clara en artículo | solicitar resultados y perímetro de contraste |
| Plan Chera–Sot | no | base visible parcial | variable | no digitalizar PDF; solicitar capa fuente |
| ortofoto 1977 | sí | base oficial 25 cm | no contiene perímetros identificados | solo control contextual con otra evidencia |

Ningún mapa PDF alcanza hoy `C_DOCUMENTED_CARTOGRAPHIC_RECONSTRUCTION`.

## Licencias

- **ESFire30:** CC BY 4.0 permite reutilizar y redistribuir el dataset y
  derivados con atribución e indicación de cambios. Antes de usarlo debe
  aclararse el conflicto de CRS, que es un problema de calidad, no de licencia.
- **Ortofoto ICV 1977:** CC BY 4.0; su uso exige atribución y no legitima por sí
  solo identificar o trazar un incendio.
- **MITECO EGIF/anuarios:** se aplican las condiciones generales ya auditadas,
  con origen, fecha y metadatos, sin desnaturalizar ni sugerir respaldo.
- **Artículo público ≠ datos licenciados:** la licencia o acceso de un PDF no
  se extiende automáticamente a un SHP, ráster, croquis administrativo o
  digitalización derivada.
- **GVA/Conselleria, NOAA/Landsat, tesis y GOIIF:** hace falta autorización o
  licencia específica del activo antes de redistribuir raster, vector o
  derivado digitalizado.

## Activos prioritarios a solicitar

1. A Generalitat/Conselleria: serie vectorial anual Valencia 1978–1992,
   diccionario, CRS, método por periodo, calidad, identificadores y licencia.
2. Al Registro de Terrenos Forestales Incendiados: inventario histórico y
   posibilidad de acceso de investigación a cartografía 1968–1992.
3. A M. Pilar Martín/UAH/CSIC: capas NOAA-AVHRR, tabla de incendios/escenas,
   validación de campo, formatos y licencia.
4. A UAH/CSIC y autores de ESFire30: aclaración EPSG:25830 frente a `.prj`
   EPSG:23030, semántica de cada feature y eventual archivo con fecha/ID.
5. A autores/archivo forestal: resultados digitales Landsat de Hoya de Buñol y
   perímetro oficial usado para contraste.
6. A Generalitat/GOIIF y responsables de planes: cartografía fuente Chera–Sot
   y expedientes/croquis 1991–1992, incluido Marines–Altura.

## Recomendación para CV-4.2

Realizar una fase de **adquisición y auditoría de activos**, no de integración:

1. conservar snapshot reproducible de ESFire30 con licencia y hashes;
2. resolver por escrito su CRS y auditar geometrías/topología/metadatos;
3. diseñar `historical_geometry_candidate` separado de EGIF;
4. evaluar enlaces con fecha, municipio, superficie y evidencia documental,
   manteniendo `candidate` salvo identificador común o confirmación externa;
5. tramitar las solicitudes prioritarias anteriores;
6. no producir una capa pública ni modificar el visor hasta revisar calidad,
   identidad y atribución de cada activo.

CV-4.2 puede preparar candidatos B y A, pero no debe reparar, simplificar,
fusionar partes ni promover un perímetro a oficial sin procedencia inequívoca.
