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
4.0 con atribución y aviso de transformación. El perfil público distribuye
únicamente los derivados ICV y EFFIS permitidos.

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
