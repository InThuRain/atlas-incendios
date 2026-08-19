# Licencia y procedencia de los datos

Este archivo se refiere a los datos valencianos utilizados por el Atlas de
Incendios. No concede una licencia sobre el código del proyecto ni sustituye las
condiciones establecidas por la Generalitat Valenciana.

## Estado de publicación

**Los datasets web derivados no están publicados.** La revisión CV-1.5b confirmó
la licencia y la atribución, pero dejó pendientes dos aclaraciones operativas
necesarias para una distribución pública mediante GitHub Pages:

1. cómo obtener la aceptación expresa de las condiciones por cada receptor de
   una copia o producto derivado;
2. si la simplificación geométrica multiescala documentada es compatible con la
   condición general de no alterar ni desnaturalizar la información.

Hasta obtener respuesta escrita del ICV o del órgano titular, este archivo no
debe interpretarse como autorización para añadir `data/web/gva/` a Git.

## Dataset de origen

- **Título:** Incendios forestales de la Comunitat Valenciana (1993–2024).
- **Identificador:** `spa_icv_ince_incendios`.
- **Órgano titular:** Servicio de Prevención de Incendios Forestales, Dirección
  General de Prevención de Incendios Forestales, Generalitat Valenciana.
- **Publicador:** Institut Cartogràfic Valencià, Generalitat Valenciana.
- **Licencia declarada:** Creative Commons Atribución 4.0 Internacional
  (CC BY 4.0).
- **Revisión de metadatos consultada:** 27 de julio de 2026.
- **Ficha oficial:**
  https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024
- **Metadatos ISO:**
  https://catalogo.icv.gva.es/geonetwork/srv/api/records/spa_icv_ince_incendios/formatters/xml
- **Condiciones ICV:**
  https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv
- **Condiciones generales GVA:**
  https://portaldadesobertes.gva.es/es/avis-legal

La fuente indica que la cartografía es informativa y no vinculante, no contiene
todos los incendios del periodo y, en caso de discrepancia, prevalece el parte
estadístico salvo error u omisión.

## Condiciones documentadas

La documentación oficial consultada establece:

- atribución de la procedencia en un lugar visible;
- conservación de la fecha de actualización y de las condiciones de
  reutilización incluidas en los metadatos originales;
- prohibición de alterar o desnaturalizar el contenido de la información;
- prohibición de sugerir participación, patrocinio o apoyo de la Generalitat si
  no existe un acuerdo expreso;
- responsabilidad exclusiva del reutilizador por el uso de los datos;
- prohibición de usos ilícitos o contrarios a derechos de terceros;
- aceptación expresa de las condiciones por el nuevo usuario cuando se
  reproduce o distribuye el total, una parte o un producto derivado, con o sin
  finalidad comercial.

## Derivados preparados por el atlas

Los assets candidatos a publicación no son copias originales. El pipeline:

- separa las entidades incendio y geometría;
- normaliza y selecciona atributos para el visor;
- transforma las geometrías servidas por ArcGIS a EPSG:4326;
- divide los datos por provincia y bloque temporal;
- genera niveles `local`, `regional` y `overview` mediante simplificación
  topológicamente conservadora y redondeo adaptativo;
- no repara ni deduplica geometrías y no modifica los snapshots raw.

Los límites máximos usados son 1 m y 1 % de error relativo de área para
`local`, 10 m y 5 % para `regional`, y 50 m y 15 % para `overview`. Si una
geometría no cumple la salvaguarda individual se conserva con mayor detalle.

## Atribución visible propuesta

Si el ICV confirma la publicación, el visor mostrará permanentemente:

> Datos de origen: “Incendios forestales de la Comunitat Valenciana
> (1993–2024)” CC BY 4.0 © Institut Cartogràfic Valencià, Generalitat. Servicio
> de Prevención de Incendios Forestales, DGPIF, Generalitat Valenciana.
> Derivado modificado por Atlas de Incendios: normalización, reproyección a
> EPSG:4326, selección de atributos, particionado y simplificación geométrica
> multiescala. No es un producto oficial del ICV ni implica respaldo de la
> Generalitat Valenciana. [Ficha oficial](https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024) ·
> [Condiciones de uso](https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv)

Esta redacción amplía prudentemente la fórmula publicada por el ICV. La fórmula
definitiva debe confirmarse porque el registro atribuye la titularidad y la
publicación a organismos distintos.

## Metadatos que deben acompañar una publicación futura

El manifiesto distribuido junto a los assets debe conservar como mínimo:

- título e identificador del dataset original;
- titular, publicador y crédito;
- licencia, URL de licencia y URL de condiciones ICV;
- ficha oficial y URL de metadatos ISO;
- fecha de revisión oficial;
- fecha de descarga de cada capa, URL y `layer_id` de origen;
- `fire_id`, `geometry_id`, identificadores originales y `provenance_id`;
- operaciones y parámetros de transformación;
- indicación inequívoca de que el derivado ha sido modificado;
- checksums y tamaños de cada archivo;
- carácter informativo, cobertura incompleta y ausencia de respaldo oficial.

Los GeoJSON, su manifiesto, este archivo y la ficha de metodología deberán
distribuirse como un conjunto. Esto mejora la trazabilidad, pero no resuelve por
sí solo la aceptación expresa exigida por las condiciones ICV.

## Aclaración necesaria

La consulta debería dirigirse a `responde_icv@gva.es`, con copia al órgano
titular en `dgpif@gva.es`, preguntando expresamente:

1. si se permite alojar públicamente en GitHub Pages GeoJSON reproyectados,
   particionados y simplificados bajo CC BY 4.0;
2. si una atribución visible y enlaces a estas condiciones satisfacen la
   aceptación expresa o se exige un mecanismo de consentimiento previo;
3. si las URLs directas de los assets pueden ser públicas sin un control de
   aceptación;
4. si las simplificaciones descritas respetan la condición de no alteración o
   desnaturalización;
5. qué fórmula exacta de crédito debe usarse para este dataset concreto.
