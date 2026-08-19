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

El registro declara licencia CC BY 4.0 y remite a las [condiciones de uso de la geoinformación ICV](https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv), que exigen atribución visible e incluyen condiciones para la redistribución. Antes de publicar snapshots se debe concretar la atribución y cómo cumplir esas condiciones.

Fuentes verificadas:

- [registro del catálogo de datos abiertos GVA](https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024);
- [metadatos ISO del ICV](https://catalogo.icv.gva.es/geonetwork/srv/api/records/spa_icv_ince_incendios/formatters/xml).

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
