# Fuentes y licencias de terceros

Este archivo documenta las fuentes de datos, la cartografía base y las
bibliotecas cargadas por el visor. Complementa `LICENSE_DATA.md`; no sustituye
los textos legales enlazados ni concede derechos adicionales.

## Perfil público de datos

### Incendios forestales de la Comunitat Valenciana 1993–2024

- **Fuente/publicador técnico:** Institut Cartogràfic Valencià / Generalitat.
- **Propiedad y atribución confirmada:** Generalitat.
- **Licencia:** Creative Commons Atribución 4.0 Internacional (CC BY 4.0).
- **Ficha oficial:**
  <https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024>
- **Condiciones:**
  <https://icv.gva.es/es/condiciones-de-uso-de-la-geoinformacion-icv>
- **Texto de atribución y transformación propuesto por el ICV:**

> Incendios forestales de la Comunitat Valenciana (1993–2024) CC BY 4.0,
> Generalitat. Datos transformados para su visualización mediante reproyección,
> selección de atributos, particionado y simplificación geométrica.

El ICV confirmó por escrito el 20 de agosto de 2026 que la redistribución
pública y los productos transformados están permitidos bajo CC BY 4.0, que la
aceptación es tácita y que deben atribuirse la fuente y las modificaciones.

### EFFIS / Copernicus EMS

- **Fuente:** European Forest Fire Information System, Copernicus Emergency
  Management Service.
- **Titular indicado por la fuente:** European Union.
- **Licencia:** CC BY 4.0 para el contenido de la UE salvo indicación contraria;
  exige crédito apropiado e indicación de cambios.
- **Licencia oficial:**
  <https://forest-fire.emergency.copernicus.eu/about-effis/data-license>
- **Atribución del atlas:** European Union, Copernicus EMS / EFFIS (CC BY
  4.0); selección espacial y reducción de atributos realizadas por el Atlas.

Los perímetros EFFIS se presentan como detecciones satelitales provisionales,
no como perímetros administrativos oficiales.

### SIGIF/GVA

SIGIF no forma parte del perfil público. Sus snapshots, registros y derivados
continúan con `publishable=false` hasta recibir una aclaración específica de sus
condiciones. La confirmación ICV no se extrapola a SIGIF.

## Cartografía base

El visor utiliza teselas de OpenStreetMap y muestra la atribución
`© OpenStreetMap contributors` en el mapa.

- **Datos:** Open Data Commons Open Database License (ODbL).
- **Copyright y licencia:** <https://www.openstreetmap.org/copyright>
- **Política de teselas:**
  <https://operations.osmfoundation.org/policies/tiles/>

La publicación del atlas debe respetar también la política operativa del
servidor de teselas o sustituirlo por un proveedor adecuado.

## Bibliotecas web

El frontend carga estas bibliotecas sin incorporarlas a los datasets:

- **Leaflet 1.9.4** — BSD 2-Clause License:
  <https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE>
- **Turf.js 7.2.0** — MIT License:
  <https://github.com/Turfjs/turf/blob/v7.2.0/LICENSE>

Sus avisos y condiciones pertenecen a sus respectivos titulares. Las versiones
se fijan explícitamente en `index.html`.
