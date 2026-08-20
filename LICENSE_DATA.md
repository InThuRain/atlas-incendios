# Licencia y procedencia de los datos

Este archivo se refiere a los datos valencianos utilizados por el Atlas de
Incendios. No concede una licencia sobre el código del proyecto ni sustituye las
condiciones establecidas por la Generalitat Valenciana.

## Estado de publicación

**Los datasets web derivados todavía no están publicados.** Una aclaración
escrita del Institut Cartogràfic Valencià, recibida el 20 de agosto de 2026,
resolvió los bloqueos documentales de CV-1.5b:

1. CC BY 4.0 permite la redistribución pública;
2. la aceptación de las condiciones es tácita;
3. pueden publicarse datos transformados indicando las modificaciones;
4. la propiedad y atribución de este dataset corresponde a Generalitat, no al
   ICV.

Por tanto, los derivados ICV pueden incorporarse a un futuro perfil público con
la atribución y el aviso de modificación indicados aquí. Este cambio no publica
archivos automáticamente ni alcanza a SIGIF, que mantiene condiciones propias.

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
- aceptación de las condiciones por el nuevo usuario cuando se reproduce o
  distribuye el total, una parte o un producto derivado, con o sin finalidad
  comercial. El ICV aclaró por escrito que esta aceptación es tácita.

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

## Atribución visible

El visor mostrará permanentemente:

> Incendios forestales de la Comunitat Valenciana (1993–2024) CC BY 4.0,
> Generalitat. Datos transformados para su visualización mediante reproyección,
> selección de atributos, particionado y simplificación geométrica.
>
> No es un producto oficial del ICV ni implica respaldo de la Generalitat.
> [Ficha oficial](https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024) ·
> [Condiciones de uso](https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv)

Esta fórmula fue propuesta expresamente por el ICV en su aclaración escrita de
20 de agosto de 2026. La atribución a Generalitat y la obligación de indicar
las modificaciones siguen esa respuesta.
La identificación del ICV como publicador se conserva en los metadatos de
procedencia, pero no sustituye el crédito visible confirmado.

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
distribuirse como un conjunto. Así se mantienen unidos la atribución, el aviso
de transformaciones y la trazabilidad requerida.

## Evidencia de la aclaración

El responsable del proyecto recibió por correo una respuesta del Institut
Cartogràfic Valencià el 20 de agosto de 2026. Este repositorio registra la fecha,
el organismo y el alcance comunicado, pero no incorpora el mensaje original ni
datos personales del correo. Conviene conservar el original en el archivo
documental privado del proyecto.

La aclaración se refiere al dataset ICV y a sus derivados. No debe extrapolarse
a estadísticas SIGIF ni a otras fuentes de la Generalitat con condiciones
específicas.

Las demás fuentes y bibliotecas del perfil público se documentan en
`THIRD_PARTY_LICENSES.md`, siguiendo la recomendación del ICV.
