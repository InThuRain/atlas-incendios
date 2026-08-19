# CV-1.5b — Licencia, atribución y redistribución ICV

Fecha de revisión: 2026-08-19.

## Conclusión ejecutiva

La licencia concreta está suficientemente documentada: **Creative Commons
Atribución 4.0 Internacional (CC BY 4.0)**. También están documentadas la
atribución visible, la conservación de metadatos, el carácter informativo del
dataset y las condiciones generales de reutilización.

Sin embargo, la información encontrada **no es todavía suficiente para publicar
los derivados mediante GitHub Pages con seguridad documental**. Las condiciones
ICV exigen aceptación expresa por cada nuevo receptor cuando se reproduce o
distribuye cualquier parte o producto derivado. Una URL pública de GitHub Pages
puede descargarse sin pasar por la interfaz. Además, la documentación GVA exige
no alterar ni desnaturalizar la información y no aclara expresamente cómo aplica
esa regla a una simplificación geométrica multiescala declarada.

La recomendación es mantener `data/web/gva/` sin publicar y solicitar una
confirmación escrita al ICV o al órgano titular antes de cambiar ese estado.

## Fuentes oficiales consultadas

Solo se han usado fuentes del ICV o de la Generalitat Valenciana:

1. [Ficha del dataset en Dades Obertes GVA](https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024).
2. [API oficial de la ficha CKAN](https://dadesobertes.gva.es/api/3/action/package_show?id=84ea3b70-2cbb-4f94-bf3b-4cad6f53d4df).
3. [Registro ISO `spa_icv_ince_incendios`](https://catalogo.icv.gva.es/geonetwork/srv/api/records/spa_icv_ince_incendios/formatters/xml).
4. [Condiciones de uso de la geoinformación ICV](https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv).
5. [Información para reutilizadores GVA](https://portaldadesobertes.gva.es/es/informacio-per-a-reutilitzadors).
6. [Aviso legal y condiciones generales de reutilización GVA](https://portaldadesobertes.gva.es/es/avis-legal).

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

## Interpretación razonable

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

Estas son interpretaciones operativas del proyecto, no afirmaciones atribuidas
al ICV.

## Cuestiones no resueltas

1. ¿Basta una atribución visible y un enlace a las condiciones para considerar
   que el visitante las acepta expresamente?
2. ¿Deben bloquearse las URLs hasta que el usuario acepte? Si es así, GitHub
   Pages puro no puede imponerlo a cada descarga directa.
3. ¿Admite el ICV la simplificación topológicamente conservadora descrita por
   CV-1.4 bajo la regla de no alteración/desnaturalización?
4. ¿Debe usarse la fórmula de producto ICV, la de departamento GVA o ambas?
5. ¿Exige el ICV una redacción concreta para identificar las modificaciones?

## Propuesta de atribución visible

> Datos de origen: “Incendios forestales de la Comunitat Valenciana
> (1993–2024)” CC BY 4.0 © Institut Cartogràfic Valencià, Generalitat. Servicio
> de Prevención de Incendios Forestales, DGPIF, Generalitat Valenciana.
> Derivado modificado por Atlas de Incendios: normalización, reproyección a
> EPSG:4326, selección de atributos, particionado y simplificación geométrica
> multiescala. No es un producto oficial del ICV ni implica respaldo de la
> Generalitat Valenciana. Ficha oficial · Condiciones de uso.

`Ficha oficial` debe enlazar al catálogo del dataset y `Condiciones de uso` a la
página ICV. Es una propuesta pendiente de confirmación, no una fórmula aprobada
por la fuente.

## Metadatos y archivos propuestos

- `LICENSE_DATA.md`, accesible desde el visor y distribuido con los assets;
- `config/datasets-gva.json` con licencia, titular, publicador, crédito, URLs,
  fecha de revisión, atribución, transformaciones y estado de bloqueo;
- `provenance.json` por capa/año con URL, `layer_id`, fecha de recuperación,
  checksum raw y `provenance_id`;
- manifiesto por asset con nivel, partición, recuento, tamaño y SHA-256;
- `fire_id`, `geometry_id`, identificadores de origen y marca de geometría
  reutilizada en los datos derivados;
- aviso de modificación y de cobertura incompleta en visor y documentación.

La procedencia existente ya cubre la mayor parte de los campos técnicos. Antes
de publicar debe incorporarse el bloque de licencia y transformaciones al mismo
paquete descargable y verificarse que nunca quede separado de los GeoJSON.

## Acción necesaria

Enviar a `responde_icv@gva.es`, con copia a `dgpif@gva.es`, las cinco preguntas
de `LICENSE_DATA.md` y conservar la respuesta como evidencia del proyecto. Solo
una contestación que confirme redistribución estática, acceso directo,
simplificación y atribución permitirá cambiar el manifiesto a `ready` y añadir
los assets a Git.

Texto propuesto para la consulta:

> Asunto: Consulta sobre redistribución de derivados del dataset
> `spa_icv_ince_incendios`
>
> Estamos preparando un visor público y gratuito en GitHub Pages a partir de
> “Incendios forestales de la Comunitat Valenciana (1993–2024)”. El navegador
> descargaría GeoJSON derivados mediante URLs públicas directas. Conservamos
> identificadores y procedencia, pero normalizamos atributos, transformamos a
> EPSG:4326, dividimos por provincia/periodo y generamos tres niveles mediante
> simplificación topológicamente conservadora (1, 10 y 50 m, con salvaguardas de
> error de área). No publicaremos los snapshots originales.
>
> Solicitamos confirmación escrita de que esta redistribución es admisible bajo
> CC BY 4.0; de cómo cumplir la aceptación expresa del punto 7 para visitantes y
> descargas directas; de que la simplificación descrita no vulnera la condición
> de no alteración/desnaturalización; y de la fórmula exacta de atribución y del
> aviso de modificaciones que debemos mostrar.

## Lista de comprobación previa a una publicación futura

Después de recibir una respuesta favorable todavía habrá que:

1. archivar la respuesta con fecha, remitente y alcance;
2. ajustar la atribución a la fórmula confirmada;
3. mostrarla de forma permanente en el visor y enlazar `LICENSE_DATA.md`, la
   ficha oficial y las condiciones ICV;
4. incorporar licencia y transformaciones al paquete de provenance accesible
   junto a cada partición;
5. cambiar `publication.status` a `ready` y
   `license_review_required` a `false` en el generador, nunca solo en el JSON
   generado;
6. reconstruir y validar checksums, tamaños y recuentos;
7. revisar que solo entren los 38 assets de producción y no raw, processed ni la
   matriz de benchmark;
8. efectuar una revisión final del visor ya servido desde el subdirectorio de
   GitHub Pages.
