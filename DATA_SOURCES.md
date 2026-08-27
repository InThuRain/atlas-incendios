# Fuentes de datos

## Principio general

Priorizar fuentes oficiales. Registrar para cada importación:

- organismo;
- nombre del conjunto;
- URL de origen;
- fecha de descarga;
- licencia si está disponible;
- cobertura temporal;
- cobertura espacial;
- campos relevantes;
- limitaciones conocidas.

## 1. EGIF / MITECO

**Estadística General de Incendios Forestales (EGIF)**.

Función prevista en el proyecto:

- columna vertebral estadística nacional;
- identificación de incendios desde 1968;
- atributos de cada evento;
- detección de incendios que no tienen geometría disponible.

No asumir que EGIF proporciona un perímetro vectorial histórico homogéneo para cada evento.

Fuente de referencia:

https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html

También revisar recursos del Banco de Datos de la Naturaleza y servicios IDE del MITECO.

### Inventario histórico valenciano CV-3.1

La revisión de 1968–1992 identificó **9.175 registros** en el buscador público:
2.514 en Alicante, 2.600 en Castellón y 4.061 en Valencia; 181 superan el umbral
de 500 ha si se usa superficie total. Son recuentos del snapshot consultado el
19 de agosto de 2026, no una afirmación de cobertura histórica uniforme.

La documentación oficial establece una ruptura metodológica importante. Entre
1968 y 1979 se recogían principalmente incendios de montes con intervención
pública, especialmente repoblaciones. La recogida de todos los siniestros
comienza durante los años ochenta y se sistematiza para todas las comunidades y
provincias en 1992. Los modelos de parte cambian en 1968, 1972, 1980, 1983,
1989 y 1990.

El buscador permite resumen Excel y parte completo XML. El producto enlazado
publicado cubre 1983–2015 bajo CC BY 4.0, pero la ontología oficial indica que
los registros codificados comienzan en 1983 y que las geometrías puntuales solo
están validadas desde 2005. Por ello ninguna coordenada de 1968–1992 se tratará
como punto fiable sin una auditoría por modelo de parte, CRS, datum, huso,
unidades y rango. EGIF no aporta una serie homogénea de perímetros.

Las [condiciones generales MITECO](https://www.datosabiertos.miteco.gob.es/es/aviso-legal.html)
permiten copia, difusión, modificación, adaptación y combinación, con cita de
origen, fecha de actualización y metadatos, sin desnaturalizar la información
ni sugerir respaldo ministerial.

El detalle, los recuentos anuales, las lagunas y las fuentes cartográficas
revisadas están en `CV_3_1_HISTORICAL_INVENTORY.md` y
`data/sources/gva_historical_inventory.json`.

### Snapshot normalizado CV-3.2

El 19 de agosto de 2026 se descargaron mediante el exportador oficial los tres
ZIP de parte completo XML. El contenido suma **9.175 registros** y coincide con
todos los recuentos provincia × año de CV-3.1. El manifiesto conserva URL,
parámetros, fechas, tamaños, miembros XML y SHA-256 en
`data/sources/egif_gva_1968_1992_manifest.json`.

El exportador actual aplica un mismo XSD jerárquico a los seis periodos
históricos. La matriz de campos confirma diferencias de población —por ejemplo,
hoja/cuadrícula no aparece en 1968–1971 y la superficie agrícola empieza en
1989—, pero no permite recuperar sin inferencia los nombres originales de los
seis formularios.

`NumeroParte` e `IdPif` son únicos, aunque `NumeroParte` identifica un parte
administrativo y no garantiza un episodio físico único. La salida usa
`egif-record:<NumeroParte>`, `identity_status=source_record_only` y
`episode_identity_status=unresolved`. La publicación definitiva de 1992
describe Marines–Altura como un incendio interprovincial mientras el XML
contiene varios partes compatibles; no se han fusionado.

No hay coordenadas X/Y pobladas en el periodo. Hay hoja/cuadrícula en 8.565
registros y municipio oficial resuelto en 5.254, pero las 9.175 geometrías son
`null`. El umbral de GIF se calcula sobre superficie forestal: da 180 partes.
El valor 181 de CV-3.1 corresponde a superficie total; la única diferencia es
`1992030104` (400 ha forestales y 100 ha agrícolas).

El detalle, contraste 1992, anomalías y límites están en
`CV_3_2_EGIF_AUDIT.md`. Los snapshots raw y normalizados continúan ignorados y
no se han publicado.

### Derivado web CV-3.3

CV-3.3 reduce los 9.175 partes normalizados a un JSON web sin
`original_attributes` y conserva `geometry=null` en todos los registros. El
derivado mantiene identidad del parte, año, provincia, municipio canónico solo
cuando CODINE ya estaba resuelto documentalmente, superficies, GIF forestal,
causa codificada, régimen de cobertura y disponibilidad de hoja/cuadrícula.

Los códigos EGIF se traducen de forma explícita: `100` rayo; `2xx`
negligencias; `3xx` causas accidentales; `400` intencionado; `500` desconocida;
`600` reproducido. La interfaz mantiene las causas accidentales históricas como
categoría propia y no las fusiona con una etiqueta ICV. La tabla completa y los
recuentos quedan en `CV_3_3_HISTORICAL_WEB_INTEGRATION.md` y en el manifiesto
reproducible `data/web/gva/egif/assets-manifest.json` (salida ignorada).

### Referencias espaciales históricas CV-3.5

La cifra de CV-3.2 de 8.565 partes con dato espacial corresponde exactamente a
8.565 pares simultáneos `hoja` + `cuadricula`; no hay casos con un solo
componente. Los otros 610 partes carecen de ambos. Se observan seis hojas, 166
códigos de cuadrícula y 270 pares únicos.

La documentación oficial de MITECO identifica el sistema inicial EGIF como una
cuadrícula nominal UTM de 10 × 10 km referida a hojas 1:200.000 del Instituto
Geográfico del Ejército. Sin embargo, no se ha localizado la tabla histórica de
conversión, datum, husos, orientación/origen de la cuadrícula ni reglas de borde.
Por ello los 8.565 pares quedan como `B_PROBABLE`, ninguno alcanza
`A_CONFIRMED` y no se ha creado ninguna geometría. `geometry=null` se mantiene
para los 9.175 partes.

El inventario completo, la evidencia y la clasificación reproducible están en
`CV_3_5_EGIF_SPATIAL_REFERENCE_AUDIT.md` y
`data/sources/egif_spatial_reference_audit.json`. Una futura cartografía exige
obtener de MITECO/ADCIF o del organismo cartográfico competente la clave oficial
del sistema; el municipio solo podrá utilizarse como contraste independiente,
nunca para elegir una celda.

### Investigación de la clave cartográfica CV-3.6

CV-3.6 ha documentado el marco geodésico adoptado para la nueva cartografía
militar de 1968 (Hayford, datum europeo Potsdam y UTM), la existencia de
ediciones 1:200.000 durante la transición desde cuadrícula Lambert y un patrón
específico del ICONA para rotular con letra y número las celdas de 10 km. No se
ha localizado el patrón ni una tabla a coordenadas.

CV-3.6b corrige la comparación inicial con el índice temático del IGME: el
índice original de la serie militar 5L 1:250.000 sitúa `7-4` y `8-4` en el este
peninsular, de modo compatible con los valores XML valencianos `0704` y `0804`.
La compatibilidad no demuestra la migración histórica ni resuelve las
subcuadrículas `A01`–`O12`.

La misma subfase documenta una capa operativa ArcView importada como
`Hc250LL`, con geometría, `HOJA`, `CUAD`, `COD250` e `ID1`, utilizada en 2010
para enlazar registros DGB 1995–2004. La malla fue realizada por investigadores
del Instituto de Economía, Geografía y Demografía del CSIC y suministrada por
el CCHS-CSIC; llegó sin fichero de coordenadas y no se ha localizado el activo
ni el `.csf` creado en el proyecto. La malla actual de MITECO/BDN conserva un
campo `COD_INB` ED50 H30 y documenta una migración desde una malla antigua
ED50, pero no contiene `HOJA`/`CUAD` ni demuestra ser sucesora de `Hc250LL`.

Los 8.565 pares seguían en `B_PROBABLE` al cierre de CV-3.6b y no se generó
geometría. Esta conclusión queda superada, para el enlace documental, por la
entrega directa de la malla oficial auditada en ES-1.5; la geometría de
incendio continúa siendo `null`.

La evidencia, discrepancia y documentos concretos pendientes se recogen en
`CV_3_6_EGIF_CARTOGRAPHIC_KEY_RESEARCH.md`. Las consultas no enviadas para
MITECO/ADCIF y CEGET/IGN-CNIG están en `CV_3_6_RESEARCH_CONTACT_PACKET.md`.
La búsqueda del activo y la corrección de numeración se detallan en
`CV_3_6B_HISTORICAL_GRID_ASSET_SEARCH.md`.

### Malla histórica oficial CCINIF (ES-1.5)

El 26/08/2026 CCINIF/MITECO entregó directamente `HOJAS.kmz` y
`CUADRICULAS.kmz` y confirmó que son las referencias históricas basadas en la
Cartografía Militar de España 1:250.000 y cuadrículas nominales de 10 × 10 km
conservadas en EGIF por continuidad desde 1968. Los activos raw permanecen
ignorados y sus checksums se fijan en
`data/sources/ccinif_historical_grid_manifest.json`.

El cruce nacional exacto de 646.887 partes 1968–2023 obtiene 626.957 enlaces
`A_CONFIRMED` a 5.183 celdas distintas. A significa únicamente que el par
`HOJA+CUAD` apunta sin ambigüedad a la geometría documental entregada; no
convierte la celda en perímetro, superficie quemada, ubicación exacta o
episodio. Canarias conserva 157 fragmentos sin `HOJA`: 3.463 partes quedan
`C_AMBIGUOUS`, no se fuerzan mediante municipio o semejanza.

Para el País Valencià, los 270 pares de CV-3.5 aparecen exactamente: 8.565
partes pasan a A como referencias y 610 siguen sin referencia. Los partes EGIF
mantienen `geometry=null`.

La licencia de redistribución de los KMZ o derivados no se incluyó en la
entrega. Aunque MITECO publica condiciones generales de reutilización, la
procedencia cartográfica militar aconseja confirmación específica. La fuente se
mantiene `publishable=false` / `false_pending_permission`. La auditoría,
restricciones y consulta propuesta están en
`ES_1_5_CCINIF_HISTORICAL_GRID_AUDIT.md`.

### Inventario de perímetros históricos CV-4.1

CV-4.1 localiza un primer vector de teledetección reutilizable: **ESFire30
Causes**, UAH/CSIC, CC BY 4.0. La intersección diagnóstica de sus capas
1985–1992 con el límite oficial localiza 710 polígonos en el País Valencià. Son
áreas quemadas Landsat independientes, no perímetros EGIF ni enlaces
administrativos confirmados. El README declara EPSG:25830 pero los `.prj`
declaran ED50 / UTM 30N (EPSG:23030); el conflicto debe resolverse antes de
crear derivados.

También se documenta la existencia de una cartografía vectorial oficial anual
de la Conselleria desde 1978 en la provincia de Valencia; para Alicante y
Castellón la serie citada comienza en 1993. El activo 1978–1992 no está
disponible y su licencia no se deduce de la del artículo que lo describe.

Los trabajos NOAA-AVHRR y Landsat aportan metodología y mapas para incendios
valencianos, especialmente en 1991, pero no se han localizado sus ficheros
digitales ni licencias. El plan Chera–Sot contiene mapas de 1978–1992 con
precisión histórica aproximada, insuficientes para digitalización responsable.

El inventario, las 14 fuentes, el diagnóstico ESFire30 y la matriz de los 180
partes GIF están en `CV_4_1_PRE1993_PERIMETER_SOURCE_INVENTORY.md` y
`data/sources/gva_pre1993_perimeter_sources.json`. No se ha creado geometría ni
modificado el visor.

### Auditoría ESFire30 CV-4.2

CV-4.2 adquiere y verifica el snapshot exacto **ESFire30 Causes v1**, DOI
`10.5281/zenodo.18449006`, CC BY 4.0. El archivo contiene 119.498 polígonos
anuales 1985–2021; el periodo real del ZIP no alcanza 2023 aunque el artículo
asociado describa ese alcance para el producto base.

La contradicción del CRS queda resuelta: los 37 `.prj` y un contraste pareado
con 450 candidatos ICV demuestran que las coordenadas almacenadas están en
**ED50 / UTM 30N (EPSG:23030)**. La referencia EPSG:25830 del README se registra
como error de metadatos. La transformación diagnóstica usa la rejilla oficial
IGN `es_ign_SPED2ETV2.tif`, fijada por checksum.

Se reconcilian **710 polígonos** 1985–1992 que intersectan el País Valencià:
195 Alicante, 206 Castellón y 309 Valencia. Los 710 son válidos OGC y únicos
por checksum; suman 84.894 vértices. Se consideran candidatos
`B_DOCUMENTED_REMOTE_SENSING`, no perímetros oficiales ni episodios físicos
confirmados. ESFire30 carece de fecha, municipio e ID estable de evento, y sus
causas ya incorporan EGIF mediante cuadrícula/modelado.

El cruce diagnóstico con los 180 partes EGIF GIF produce 3 candidatos fuertes,
34 posibles, 3 débiles, 140 sin candidato y **0 confirmados**. La licencia
permite derivados transformados con atribución e indicación de cambios, pero
ningún asset se incorpora todavía al perfil público. Resultados, condiciones y
limitaciones: `CV_4_2_ESFIRE30_AUDIT.md` y
`data/sources/esfire30_audit.json`.

### Integración web local ESFire30 CV-4.3

CV-4.3 genera reproduciblemente un normalizado ignorado y tres GeoJSON web
1985–1992, todos con 710 perímetros. La transformación parte de EPSG:23030 y usa
exclusivamente la rejilla IGN auditada; el pipeline falla si cambian snapshot,
`.prj`, rejilla u operación PROJ. Los niveles local/regional/overview aplican
0/20/30 m de tolerancia, conservan todas las geometrías válidas y no colapsan
incendios pequeños.

Cada polígono mantiene una identidad derivada del contenido y checksum de la
geometría original, separada del índice del SHP. Las 1.110 relaciones con 268
municipios y las relaciones provinciales son intersecciones espaciales
derivadas, no atributos administrativos ni enlaces EGIF. Los 3 candidatos
fuertes, 34 posibles y 3 débiles de CV-4.2 no se sirven al navegador.

La licencia CC BY 4.0 permite marcar ESFire30 `publishable=true` con atribución
y aviso de selección, reproyección, reducción de atributos y simplificación.
El perfil público incluye EGIF + ESFire30 + ICV + EFFIS y rechaza SIGIF.
CV-4.4 publica los tres LOD ESFire30 mediante `public-data-v5` el 26/08/2026;
no publica candidatos EGIF–ESFire30 ni datos fuente/diagnósticos. Véase
`CV_4_3_ESFIRE30_WEB_INTEGRATION.md`.

## 2. Generalitat Valenciana / ICV

Fuente muy importante para el piloto.

Servicio ArcGIS utilizado durante el prototipo:

https://carto.icv.gva.es/arcgis/rest/services/Prevencion_de_incendios2/MapServer

También se localizó previamente un servicio con estructura equivalente bajo:

`tm_medio_ambiente/prevencion_de_incendios/MapServer`

Antes de automatizar una ingestión, verificar cuál es el endpoint vigente y estable.

### Cobertura observada

Capas anuales de perímetros entre 1993 y 2024.

Campos vistos en capas del servicio:

- `NumPIF_CV`
- `NumPIF_Min`
- `anyo`
- `nom_mun`
- `paraje`
- `f_detec`
- `fextinc`
- `g_caus_txt`
- `sup_f`
- otros campos de superficies y clasificación

### Advertencia

La cartografía valenciana es informativa y puede no contener todos los incendios del periodo. No usar el número de polígonos como sustituto directo de EGIF.

### Metadatos oficiales revisados en CV-1.3b

El registro oficial `spa_icv_ince_incendios` del catálogo ICV, revisado el 27 de julio de 2026, documenta métodos de producción distintos por periodo: toma GPS para 1993–1995, teledetección para 1996–2012 y homogeneización a partir de los ficheros anuales y la estadística de incendios para 2013–2024. También registra la sustitución en 2026 del antiguo campo `numparte` por los códigos autonómico y ministerial.

La ficha no explica por qué una misma secuencia de coordenadas puede aparecer con identificadores distintos ni en años diferentes. Por tanto, no se debe interpretar esa igualdad como republicación, duplicado administrativo o recurrencia real sin otra evidencia.

El registro declara licencia **Creative Commons Atribución 4.0 Internacional
(CC BY 4.0)** y no registra limitaciones al acceso público. La página oficial de
[condiciones de uso de la geoinformación
ICV](https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv) exige
citar la procedencia en lugar visible. Una aclaración escrita del ICV recibida
el 20 de agosto de 2026 confirmó que, para este dataset, la atribución
corresponde a **Generalitat**. El atlas empleará la fórmula propuesta
expresamente por el proveedor:

> Incendios forestales de la Comunitat Valenciana (1993–2024) CC BY 4.0,
> Generalitat. Datos transformados para su visualización mediante reproyección,
> selección de atributos, particionado y simplificación geométrica.

Los derivados del atlas deben añadir que han sido normalizados, reproyectados,
particionados y simplificados, enlazar la ficha y las condiciones oficiales,
conservar la fecha de revisión y no sugerir respaldo de la Generalitat.

### Publicación de derivados: CV-1.5b resuelta

La documentación oficial también establece que la redistribución total,
parcial o de un producto derivado, comercial o no comercial, requiere la
aceptación expresa de las condiciones por el nuevo usuario. Las
[condiciones generales de reutilización de la
GVA](https://portaldadesobertes.gva.es/es/avis-legal) añaden que no debe
alterarse ni desnaturalizarse la información y que han de conservarse sin
alteración los metadatos de actualización y reutilización.

La aclaración escrita del ICV recibida el 20 de agosto de 2026 confirmó que la
aceptación de esas condiciones es tácita, que CC BY 4.0 permite la
redistribución pública y que los datos transformados pueden publicarse siempre
que se indiquen las modificaciones. Con esa evidencia, los derivados ICV están
documentalmente habilitados para publicación. Esto no autoriza los datos SIGIF
ni ejecuta por sí mismo ningún despliegue. El detalle figura en
`LICENSE_DATA.md` y `CV_1_5B_LICENSE_REPORT.md`.

Fuentes verificadas:

- [registro del catálogo de datos abiertos GVA](https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024);
- [metadatos ISO del ICV](https://catalogo.icv.gva.es/geonetwork/srv/api/records/spa_icv_ince_incendios/formatters/xml).
- [información oficial para reutilizadores de la GVA](https://portaldadesobertes.gva.es/es/informacio-per-a-reutilitzadors);
- [aviso legal y condiciones generales de reutilización de la GVA](https://portaldadesobertes.gva.es/es/avis-legal).

### Fuentes recientes 2025–2026: inventario CV-2.1

A 19 de agosto de 2026, los servicios cartográficos ICV revisados siguen
terminando en 2024. Para años recientes no existe aún una fuente pública única
equivalente al producto ICV histórico.

SIGIF publica estadísticas administrativas provisionales desde 2017 hasta la
actualidad mediante una tabla con fecha, municipio, paraje, causa, superficies,
horas, comarca y coordenadas `X1`/`Y1`. No publica un identificador de parte en
esa vista ni un perímetro. En la comprobación CV-2.1 devolvió 281 filas para
2025 y 143 para 2026; la última fecha visible de 2026 era 30 de junio, por lo
que no debe tratarse como cobertura corriente completa.

CV-2.2 demostró técnicamente la semántica de `X1`/`Y1`: la norma GVA describe
el punto de inicio en UTM y 351 filas SIGIF 2024 coinciden exactamente en fecha,
municipio y coordenadas con la capa ICV 2024, cuyo CRS fuente es EPSG:25830.
Por ello se conservan como punto de inicio ETRS89/UTM 30N y se genera EPSG:4326
solo como derivado, sin borrar los valores originales.

El aviso legal específico de SIGIF limita la carga a uso personal y no
comercial y no autoriza hacerla extensiva a terceros. No se asumirá que la
licencia CC BY 4.0 de la página estadística general de la Conselleria elimina
esa condición particular. Antes de redistribuir filas o PDFs SIGIF se pedirá
confirmación al organismo responsable.

EFFIS Rapid Damage Assessment aporta polígonos satelitales recientes, no partes
administrativos. Se conservará como fuente independiente de calidad B: MODIS
250 m refinado con Sentinel-2 20 m, cobertura parcial del número de incendios y
sin garantía de que sus fechas sean ignición/extinción. Su identificador solo
es enlazable dentro de EFFIS y no sustituye `NumPIF_CV` ni el identificador
EGIF.

El snapshot CV-2.2 filtrado mediante intersección con la unión de los 542
municipios oficiales ICV contiene 9 geometrías EFFIS de 2025 y 16 de 2026. No
se usó el atributo provincia. SIGIF y EFFIS permanecen en colecciones separadas
y los 53 pares espaciales/temporales resultantes son solo candidatos puntuados.

Los avances MITECO sirven para contrastar agregados provisionales y grandes
incendios. El buscador EGIF contiene partes revisados y cerrados, pero en la
revisión no ofrecía registros 2024–2026. El inventario, las comprobaciones y la
propuesta de incorporación están en `CV_2_1_SOURCE_INVENTORY.md` y
`data/sources/gva_recent_fires_inventory.json`. La ejecución, anomalías,
licencias y caso Ibi–Font Roja se documentan en `CV_2_2_REPORT.md`; el pipeline
usa `data/sources/gva_recent_pipeline.json`.

### Derivados locales para el visor (CV-2.3)

`scripts/build_recent_frontend_assets.py` reduce los campos del último snapshot
procesado de CV-2.2 y genera GeoJSON web separados por fuente y año. Conserva
identificadores internos y de fuente, adquisición, cobertura, provisionalidad y
procedencia mínima. No incluye `original_attributes` ni sirve snapshots raw.

El punto SIGIF se toma exclusivamente del campo derivado EPSG:4326 demostrado
en CV-2.2; `X1`/`Y1` originales se mantienen como referencia. La geometría EFFIS
no se simplifica en esta fase y se etiqueta `B_provisional_satellite`. Los
candidatos strong/possible forman un asset de interfaz y los weak otro asset que
solo se solicita con `quality_debug=1`.

La aclaración ICV del 20 de agosto de 2026 permite marcar ICV como
`publishable=true`, con atribución a Generalitat y aviso de
transformación. SIGIF continúa con `publishable=false`; EFFIS figura como CC BY
4.0 con atribución y aviso de transformación. Desde CV-3.4, el perfil público
distribuye únicamente los derivados permitidos EGIF, ICV y EFFIS.

### Catálogo municipal y vocabularios de interfaz (DATA-UX-1)

La normalización municipal usa la capa oficial de términos municipales del
ICV empleada ya como límite espacial en CV-2.2. El snapshot contiene 542
municipios y conserva `cod_ine_mun`, denominación principal y variantes
castellanas, valencianas, bilingües y anteriores. La fuente es el servicio
oficial [0105 Delimitaciones, capa de municipios](https://carto.icv.gva.es/arcgis/rest/services/0105_delimitaciones/0105_Delimitaciones/MapServer/0).

Solo se asigna un código cuando existe un código de fuente validado, un
componente exacto de una denominación oficial bilingüe que converge en un único
municipio de la provincia o una equivalencia histórica documentada. La
auditoría final incorporó dos cambios de denominación acreditados en el BOE:
[Herbés → Herbers (BOE-A-2020-12459)](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2020-12459)
y [Villanueva de Castellón → Castelló (BOE-A-2020-12460)](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2020-12460).
La capitalización y el orden de una denominación bilingüe pueden normalizarse;
los nombres no encontrados o con un candidato meramente textual no se fuerzan.
Los valores originales permanecen en `municipality_raw`. De los 244 registros
inicialmente no resueltos, 223 quedan asociados con evidencia y 21 permanecen
sin municipio oficial asignado; el detalle reproducible está en
`DATA_UX_1_REPORT.md`.

Para causas, ICV aporta el texto `g_caus_txt` sin dominio codificado en las
capas inventariadas; SIGIF publica una columna textual `Causa`; el snapshot
EFFIS RDA usado por el atlas no contiene causa. El mapeo explícito y sus
separaciones semánticas están en `config/ui-vocabularies.json`. En particular,
«En investigación» no equivale a «Desconocida», y «Negligencia» no se funde con
la categoría histórica más amplia «Negligencias y causas accidentales».

## 3. Fuentes autonómicas

Para la versión española será necesario localizar las fuentes oficiales de cada comunidad autónoma.

Para cada una, documentar:

- API/servicio GIS;
- formato de descarga;
- años disponibles;
- completitud;
- identificadores que permitan enlazar con EGIF;
- licencia y condiciones de reutilización.

No construir aún una capa nacional mezclando fuentes sin conservar su procedencia.

### Catálogo territorial nacional de referencia (ES-2)

El snapshot nominal `ine-rel-2026-01-01` procede de la relación oficial de
municipios, provincias, comunidades y ciudades autónomas del INE referida al
1 de enero de 2026. Contiene 8.132 municipios, 50 provincias y 19 territorios
autonómicos: 17 comunidades y 2 ciudades autónomas. Los códigos estadísticos
51/52 se conservan como equivalentes al nivel provincial para Ceuta y Melilla,
pero no convierten esas ciudades autónomas en provincias. El código INE de cinco cifras es la identidad municipal;
el nombre y sus aliases no lo sustituyen.

Los límites/bounds nacionales futuros procederán de Límites y Unidades
Administrativas Actuales de IGN/CNIG. La ficha auditada el 26/08/2026 declara
ETRS89 para península, Baleares, Ceuta y Melilla y REGCAN95 para Canarias,
coordenadas geográficas compatibles con WGS84 y licencia compatible CC BY 4.0.
ES-2 no incluye esas geometrías: registra producto, versión, CRS, licencia y
checksum de la ficha para una adquisición posterior controlada.

Fuentes oficiales:

- INE: <https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx>
- relación CCAA/provincias: <https://www.ine.es/daco/daco42/codmun/cod_ccaa_provincia.htm>
- IGN/CNIG: <https://centrodedescargas.cnig.es/CentroDescargas/limites-municipales-provinciales-autonomicos>

El raw queda en `data/raw/territories/spain/` ignorado. El snapshot canónico y
su manifiesto se regeneran con `scripts/territories/build_spain_snapshot.py`.

ES-3 adquirió únicamente para cruce diagnóstico dos respuestas de la API OGC
Features `administrativeunit` del IGN, el 26/08/2026: nivel comunidad autónoma
(20 features, SHA-256 `48d1cd7b1cc2a3a98f6d02a0043fddc8db43ba28aaa8789d6b030243417bf757`)
y provincia (53 features, SHA-256
`58e4f68f4efc324dd9dfd0c1df0ea755846e3b717676b7137456577dc2083290`).
La API entrega esas respuestas en CRS84; se mantienen raw e ignoradas y no
forman parte del Atlas público. URLs reproducibles:

- <https://api-features.ign.es/collections/administrativeunit/items?f=json&limit=100&nationallevelname=Comunidad%20aut%C3%B3noma>
- <https://api-features.ign.es/collections/administrativeunit/items?f=json&limit=100&nationallevelname=Provincia>

## 4. Teledetección

Posibles fuentes complementarias:

- EFFIS / Copernicus;
- productos satelitales nacionales o autonómicos;
- capas de áreas quemadas.

Uso previsto:

- completar geometrías recientes;
- validar perímetros;
- cubrir eventos sin cartografía autonómica.

Asignar normalmente calidad B, salvo que la fuente tenga consideración oficial equivalente a A en el contexto del proyecto.

## 5. Fuentes históricas

Para periodos antiguos pueden utilizarse:

- planes locales de prevención de incendios;
- planes de parques naturales;
- cartografía histórica;
- memorias administrativas;
- informes técnicos;
- ortofotografía histórica;
- hemeroteca como apoyo documental, nunca como única base geométrica si no existe información espacial suficiente.

Las reconstrucciones deben marcarse como calidad C.

CV-3.1 confirmó que el servicio vectorial ICV comienza en 1993. El plan oficial
de Chera–Sot de Chera publica cartografía de terreno recorrido/recurrencia para
1978–2004 y contiene evidencia para 1978, 1980, 1986, 1990 y 1992, pero declara
superficies aproximadas y no ofrece los vectores anuales fuente. El PDF solo es
base potencial C; la cartografía original podría evaluarse como B si se recupera
con método, escala, CRS y licencia documentados. No se ha localizado un
perímetro oficial público pre-1993 para Mariola–Font Roja; el informe de Serra
de Mariola encontrado empieza en 1994.

Los mapas MITECO 1983–1992 agregados por hoja/cuadrícula 1:200.000 y los mapas
de cambios del Mapa Forestal sirven como contexto o pistas de investigación,
no como perímetros de evento. Ninguna fuente histórica se digitalizará o
clasificará para un incendio concreto sin evidencia suficiente.

## 6. Capas ambientales complementarias

Posibles cruces futuros:

- Mapa Forestal de España;
- espacios naturales protegidos;
- Red Natura 2000;
- términos municipales;
- pendientes/orografía;
- usos del suelo;
- clima;
- interfaz urbano-forestal.

Estas capas no forman parte del núcleo mínimo del atlas y deben añadirse sin degradar rendimiento.

## Campos mínimos normalizados propuestos

```text
fire_id
source_fire_id
start_date
end_date
year
municipality
province
autonomous_community
reported_area_ha
cause
fire_source
geometry_id
geometry_source
geometry_quality
geometry_method
geometry_date
geometry
notes
```

Para varias geometrías por incendio, separar tabla/colección `fires` de `geometries`.
