# CV-1.5b — Licencia, atribución y redistribución ICV

Fecha de revisión inicial: 2026-08-19. Aclaración escrita recibida: 2026-08-20.

## Conclusión ejecutiva

La licencia concreta es **Creative Commons Atribución 4.0 Internacional
(CC BY 4.0)**. La aclaración escrita del ICV recibida el 20 de agosto de 2026
confirma la redistribución pública, la aceptación tácita de las condiciones y
la publicación de transformaciones si se indican. Para este dataset, la
propiedad y atribución corresponde a Generalitat, no al ICV. El proveedor
propuso además una fórmula literal de atribución y aviso de transformación.

La información es ahora documentalmente suficiente para publicar en GitHub
Pages los derivados descritos por CV-1.4/CV-1.5, acompañados por atribución,
aviso de modificaciones, metadatos y ausencia de respaldo oficial. Los assets
siguen sin publicarse hasta una acción técnica explícita.

## Fuentes oficiales consultadas

Solo se han usado fuentes del ICV o de la Generalitat Valenciana:

1. [Ficha del dataset en Dades Obertes GVA](https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024).
2. [API oficial de la ficha CKAN](https://dadesobertes.gva.es/api/3/action/package_show?id=84ea3b70-2cbb-4f94-bf3b-4cad6f53d4df).
3. [Registro ISO `spa_icv_ince_incendios`](https://catalogo.icv.gva.es/geonetwork/srv/api/records/spa_icv_ince_incendios/formatters/xml).
4. [Condiciones de uso de la geoinformación ICV](https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv).
5. [Información para reutilizadores GVA](https://portaldadesobertes.gva.es/es/informacio-per-a-reutilitzadors).
6. [Aviso legal y condiciones generales de reutilización GVA](https://portaldadesobertes.gva.es/es/avis-legal).
7. Respuesta escrita del Institut Cartogràfic Valencià recibida por el
   responsable del proyecto el 20 de agosto de 2026. El mensaje original no se
   versiona en el repositorio público.

## Hechos documentados

### Licencia y responsables

- La ficha CKAN identifica la licencia como `cc-by` y sus metadatos específicos
  como `CC BY 4.0`.
- El registro ISO y la página del ICV confirman Atribución 4.0 Internacional.
- El registro ISO identifica como titular al Servicio de Prevención de Incendios
  Forestales/DGPIF y como publicador al ICV.
- El acceso público figura sin limitaciones.

### Atribución

El ICV exige citar la procedencia en lugar visible. Su modelo para productos ICV
es: `Producto año CC BY 4.0 © Institut Cartogràfic Valencià, Generalitat`. Para
productos de departamentos de la Generalitat usa una fórmula distinta. El
registro de incendios acredita conjuntamente al servicio forestal y al ICV.

### Reutilización general

Las condiciones GVA establecen que se debe:

- citar la fuente;
- mencionar la última actualización cuando figure en el original;
- conservar sin alteración los metadatos de actualización y reutilización;
- no alterar ni desnaturalizar el contenido;
- no sugerir participación, patrocinio o respaldo público;
- reutilizar bajo responsabilidad propia y no para fines ilícitos.

### Redistribución

El punto 7 de las condiciones ICV incluye expresamente la reproducción o
distribución del total, una parte o cualquier producto derivado, para usos
comerciales o no comerciales. Exige que el nuevo usuario acepte expresamente las
condiciones.

### Transformación

La documentación contempla que pueden existir productos derivados, pero no
define parámetros técnicos admisibles de simplificación. Tampoco contiene una
excepción específica para reproyección, selección de atributos, particionado o
generalización geométrica.

## Interpretación previa a la respuesta

- Servir los GeoJSON desde GitHub Pages es redistribución aunque el proyecto sea
  gratuito y el usuario solo los consuma desde el mapa.
- GitHub Pages no está prohibido expresamente, no requiere claves ni cambia la
  licencia, pero permite acceder directamente a cada archivo.
- Una pantalla de aceptación dentro del visor no cubriría necesariamente las
  descargas directas ni clones del repositorio.
- Declarar todas las transformaciones, conservar identificadores y provenance,
  enlazar las condiciones y negar respaldo oficial es una implementación
  prudente de atribución y trazabilidad.
- Etiquetar el resultado como modificado es recomendable y evita presentarlo
  como cartografía oficial sin cambios. En las páginas GVA revisadas no se ha
  localizado una fórmula específica para ese aviso.

Estas fueron las interpretaciones prudentes adoptadas el 19 de agosto. Las
dudas sobre consentimiento, transformación y crédito quedaron sustituidas por
la aclaración escrita del día 20.

## Cuestiones resueltas por la aclaración de 20/08/2026

1. No se necesita una pantalla de consentimiento: la aceptación es tácita.
2. Las URLs públicas pueden redistribuir derivados bajo CC BY 4.0.
3. Los datos transformados pueden publicarse si se indican las modificaciones.
4. La propiedad y atribución corresponde a Generalitat, no al ICV.
5. El proveedor propuso la fórmula literal reproducida a continuación.

## Atribución visible resultante

> Incendios forestales de la Comunitat Valenciana (1993–2024) CC BY 4.0,
> Generalitat. Datos transformados para su visualización mediante reproyección,
> selección de atributos, particionado y simplificación geométrica.

La fórmula anterior es la propuesta expresamente por el ICV. `Ficha oficial`
debe enlazar al catálogo del dataset y `Condiciones de uso` a la página ICV. El
ICV se conserva como publicador en la procedencia técnica; la propiedad y el
crédito visible se asignan a Generalitat.

## Metadatos y archivos propuestos

- `LICENSE_DATA.md`, accesible desde el visor y distribuido con los assets;
- `THIRD_PARTY_LICENSES.md`, con ICV, EFFIS, cartografía base y dependencias;
- `config/datasets-gva.json` con licencia, titular, publicador, crédito, URLs,
  fecha de revisión, atribución, transformaciones y estado de publicación;
- `provenance.json` por capa/año con URL, `layer_id`, fecha de recuperación,
  checksum raw y `provenance_id`;
- manifiesto por asset con nivel, partición, recuento, tamaño y SHA-256;
- `fire_id`, `geometry_id`, identificadores de origen y marca de geometría
  reutilizada en los datos derivados;
- aviso de modificación y de cobertura incompleta en visor y documentación.

La procedencia existente ya cubre la mayor parte de los campos técnicos. Antes
de publicar debe incorporarse el bloque de licencia y transformaciones al mismo
paquete descargable y verificarse que nunca quede separado de los GeoJSON.

## Acción completada

La consulta fue respondida por el ICV el 20 de agosto de 2026 y permite cambiar
el manifiesto a `ready`. El correo original debe conservarse en el archivo
documental privado del proyecto; este repositorio registra únicamente su fecha,
organismo y alcance.

## Lista de comprobación previa a una publicación futura

Antes de publicar todavía habrá que:

1. conservar la respuesta original fuera del repositorio público;
2. mostrar la atribución de forma permanente en el visor y enlazar
   `LICENSE_DATA.md`, la ficha oficial y las condiciones ICV;
3. incorporar licencia y transformaciones al paquete de provenance accesible
   junto a cada partición;
4. reconstruir y validar checksums, tamaños y recuentos;
5. revisar que solo entren los 38 assets de producción y no raw, processed ni la
   matriz de benchmark;
6. efectuar una revisión final del visor ya servido desde el subdirectorio de
   GitHub Pages.
