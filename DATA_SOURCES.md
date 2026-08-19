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
citar la procedencia en lugar visible. Para este producto se propone conservar
la siguiente fórmula, basada en el modelo de cita del ICV y en el crédito del
registro ISO:

> Incendios forestales de la Comunitat Valenciana (1993–2024) CC BY 4.0
> © Institut Cartogràfic Valencià, Generalitat. Servicio de Prevención de
> Incendios Forestales, DGPIF, Generalitat Valenciana.

Los derivados del atlas deben añadir que han sido normalizados, reproyectados,
particionados y simplificados, enlazar la ficha y las condiciones oficiales,
conservar la fecha de revisión y no sugerir respaldo de la Generalitat.

### Publicación de derivados: estado CV-1.5b

La documentación oficial también establece que la redistribución total,
parcial o de un producto derivado, comercial o no comercial, requiere la
aceptación expresa de las condiciones por el nuevo usuario. Las
[condiciones generales de reutilización de la
GVA](https://portaldadesobertes.gva.es/es/avis-legal) añaden que no debe
alterarse ni desnaturalizarse la información y que han de conservarse sin
alteración los metadatos de actualización y reutilización.

No se ha encontrado en la documentación oficial una explicación de cómo
cumplir la aceptación expresa cuando los GeoJSON se sirven mediante URLs
públicas directas, ni una confirmación de que la simplificación geométrica
documentada sea compatible con la condición de no alteración. Por ello,
**CV-1.5b no autoriza todavía la publicación**: antes se solicitará confirmación
escrita al ICV o al órgano titular. El detalle y el texto propuesto figuran en
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
que no debe tratarse como cobertura corriente completa. La semántica y CRS de
`X1`/`Y1` requieren confirmación.

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

Los avances MITECO sirven para contrastar agregados provisionales y grandes
incendios. El buscador EGIF contiene partes revisados y cerrados, pero en la
revisión no ofrecía registros 2024–2026. El inventario, las comprobaciones y la
propuesta de incorporación están en `CV_2_1_SOURCE_INVENTORY.md` y
`data/sources/gva_recent_fires_inventory.json`.

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
