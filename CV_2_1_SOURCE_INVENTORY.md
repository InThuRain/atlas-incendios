# CV-2.1 — Inventario y diseño para incendios 2025–2026

Fecha de comprobación: **2026-08-19**. Esta fase no descarga ni consolida
datos 2025–2026 y no modifica el visor ni los datasets 1993–2024.

## Resultado ejecutivo

No existe todavía una única fuente pública que ofrezca para 2025 y 2026 el
mismo producto que el ICV publica hasta 2024: registro administrativo,
identificadores de parte y perímetro oficial vectorial en una misma capa.

La combinación técnicamente más útil es:

1. **SIGIF/GVA** como fuente administrativa provisional de incendios;
2. **EFFIS RDA** como fuente independiente de geometrías satelitales
   provisionales;
3. **ICV** como futura fuente preferente de perímetros oficiales cuando
   aparezcan las capas anuales;
4. **EGIF/MITECO** como futura consolidación estadística y, mientras tanto,
   sus avances solo como contraste agregado.

EFFIS no sustituye a SIGIF, ICV ni EGIF. Su producto representa cicatrices
detectadas por satélite, puede omitir incendios pequeños y no distingue entre
incendios forestales, quemas ambientales y quemas prescritas.

## Tabla comparativa

Leyenda: **sí** significa que el dato se publica en la fuente; **parcial** que
solo existe para subconjuntos o como contexto; **no** que no se publica en el
producto revisado.

| Fuente / estado a 2026-08-19 | Cobertura y actualización | Formato / identificador | Incendio administrativo | Perímetro | Punto | Superficie | Fechas | Causa | Municipio / provincia | Licencia y calidad |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **ICV, capas anuales de incendios** | 1993–2024. Los dos MapServer oficiales revisados terminan en la capa 2024; no hay capas 2025 ni 2026. | ArcGIS REST, JSON/GeoJSON; `NumPIF_CV`, `NumPIF_Min`, `OBJECTID`. | Parcial: atributos de parte asociados al inventario cartográfico, no inventario estadístico completo. | Sí, polígono. | Sí, coordenadas en atributos históricos. | Sí. | Sí. | Sí. | Sí / sí. | CC BY 4.0 en el registro ICV; calidad A cuando es perímetro oficial. La redistribución del proyecto sigue pendiente de la aclaración CV-1.5b. |
| **SIGIF, estadística provisional GVA** | 2017–actualidad según GVA. Consulta del 19-08-2026: 281 filas para 2025 y 143 para 2026; la última fecha visible de 2026 es 30-06-2026. El portal avisa de problemas en algunos servicios. | Tabla HTML y exportación PDF. No expone identificador de parte. Columnas: fecha, municipio, paraje, causa, superficies rasa/arbolada/total, horas, detección, alerta, comarca y `X1`/`Y1`. | Sí, provisional. | No. | Parcial: publica `X1`/`Y1`, pero la propia tabla no documenta su semántica ni CRS. | Sí, declarada. | Sí, con limitaciones del esquema público. | Sí, agrupada. | Sí / provincia solo como filtro. | El aviso legal SIGIF limita el uso a personal y no comercial y no autoriza extenderlo a terceros; requiere aclaración antes de redistribuir. Sin perímetro: D; el posible punto requiere confirmar semántica/CRS. |
| **Página estadística y panel semanal GVA** | Gráficas cerradas en diciembre de 2025; el panel 2026 enlazado desde SIGIF declara actualización semanal. | HTML, PDF, gráficas/StoryMap; sin ID individual reutilizable. | No a nivel de fila; agregados administrativos. | No. | No. | Sí, agregada. | Periodos. | Sí, agregada. | Parcial, según tabla/gráfica. | La página de la Conselleria declara CC BY 4.0 salvo indicación contraria. Útil para control de totales, no para crear incendios individuales. |
| **EFFIS Rapid Damage Assessment** | Casi tiempo real durante la campaña. La documentación indica actualizaciones diarias y el WFS se ofrece como base de áreas quemadas actualizada en tiempo real. Instantánea valenciana por `PROVINCE`: 9 polígonos de 2025 y 16 de 2026; son recuentos observados, no cobertura esperada. | WFS/WMS, Shapefile y SpatiaLite; polígono y `id`, `FIREDATE`, `FINALDATE`, `LASTUPDATE`, `COUNTRY`, `PROVINCE`, `COMMUNE`, `AREA_HA`. | No. | Sí, cicatriz satelital. | No como producto separado. | Sí, satelital. | Sí, pero EFFIS advierte que no equivalen necesariamente a ignición/extinción. | No. | Sí, contexto espacial. | CC BY 4.0, atribución e indicación de cambios. Calidad B: MODIS 250 m refinado con Sentinel-2 20 m; desde 2018 puede incluir incendios menores de 30 ha, pero no todos. |
| **MITECO, avances informativos** | 2025: informe provisional de año completo publicado en mayo de 2026. Último revisado de 2026: 01-01 a 09-08, publicado 14-08-2026. Semanal de junio a 15 de octubre y mensual el resto del año. | PDF; totales nacionales/regionales y relación de GIF en el informe anual. Sin ID público de incendio en las tablas de avance. | Parcial: agregados y algunos GIF, no todos los partes individuales. | No. | No. | Sí. | Sí. | No. | Solo para GIF listados; no aporta desglose valenciano completo. | Reutilización MITECO permitida con cita, fecha y metadatos. Es control agregado provisional, no base de ingestión de eventos valencianos. |
| **EGIF Web, partes consolidados** | El buscador ofrece datos que estén consolidados provincialmente. En comprobación directa hubo resultados hasta 2023 y cero resultados para 2024–2026. La publicación definitiva anual más reciente enlazada es 2021. | Consulta HTML, resumen Excel y parte completo XML; identificador de parte y más de 150 campos cuando existe registro. | Sí, consolidado. | No como serie homogénea de polígonos. | Puede contener localización del parte, no perímetro. | Sí. | Sí. | Sí. | Sí / sí. | Condiciones generales de reutilización MITECO. Será la referencia estadística consolidada, pero hoy no cubre 2025–2026. |
| **112CV / información operativa** | Situación presente y avisos, sin archivo público versionado localizado para construir la serie 2025–2026. | Página/aplicación operativa. Sin interfaz histórica documentada. | No como inventario reproducible. | No localizado. | No evaluable como serie. | No. | Operativas. | No. | Parcial. | No se recomienda como fuente de ingestión; solo como contraste durante una emergencia. |

## Comprobaciones reproducibles y hechos observados

### ICV

Se revisaron los servicios:

- <https://carto.icv.gva.es/arcgis/rest/services/Prevencion_de_incendios2/MapServer>
- <https://carto.icv.gva.es/arcgis/rest/services/tm_medio_ambiente/prevencion_de_incendios/MapServer>

Ambos exponen como última capa anual `Incendios 2024` (`layer_id=121`).
La ficha vigente sigue siendo [Incendios forestales de la Comunitat Valenciana
1993–2024](https://dadesobertes.gva.es/dataset/incendios-forestales-de-la-comunitat-valenciana-1993-2024).

### SIGIF y estadística GVA

La [página estadística de la
GVA](https://mediambient.gva.es/es/web/prevencion-de-incendios/estadistica-de-incendios-forestales)
explica que los datos provisionales se recogen inmediatamente en las centrales
provinciales y que posteriormente se elabora el parte normalizado. Declara
datos provisionales desde 2017 hasta la actualidad y gráficas actualizadas
hasta diciembre de 2025.

El formulario público [Estadísticas de incendios
SIGIF](https://prevencionincendiosgva.es/Incendios/EstadisticasIncendios)
acepta 2017–2026. Las consultas de esta auditoría devolvieron:

| Año | Filas | Filas distintas en las 14 columnas visibles | Superficie rasa (ha) | Arbolada (ha) | Total (ha) | Primera / última fecha visible |
|---:|---:|---:|---:|---:|---:|---|
| 2025 | 281 | 280 | 305,5766 | 480,1972 | 785,7738 | 03-01 / 31-12-2025 |
| 2026 | 143 | 143 | 107,9654 | 13,9635 | 121,9289 | 11-01 / 30-06-2026 |

La repetición exacta de 2025 no se interpreta como duplicado real: al no
publicarse un identificador, las columnas visibles no permiten saber si son dos
partes, una duplicidad de presentación o dos registros indistinguibles.

La documentación técnica oficial sobre planificación indica que los años
recientes registran el punto de inicio mediante coordenadas UTM. Sin embargo,
la tabla pública solo rotula `X1` y `Y1`; antes de usarlas se debe confirmar si
son el punto de inicio, el datum y el huso. No se asumirá EPSG:25830 únicamente
por el rango numérico.

El [aviso legal de
SIGIF](https://prevencionincendiosgva.es/AvisoLegal) es más restrictivo que la
licencia general mostrada en la página de la Conselleria: autoriza visualización
y carga para uso personal y no comercial y prohíbe extenderla a terceros. No se
presupone que la licencia de una página externa prevalezca sobre estas
condiciones específicas.

### EFFIS/Copernicus

La [documentación de Rapid Damage
Assessment](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment)
establece que:

- el producto se deriva de MODIS a 250 m y Sentinel-2 a 20 m;
- desde 2018 Sentinel-2 permite detectar algunos incendios inferiores a 30 ha;
- solo se cartografía una fracción del número total de incendios, aunque EFFIS
  estima que representa aproximadamente el 95 % del área quemada anual de la
  UE;
- no distingue incendios forestales, quemas ambientales y quemas prescritas;
- `Start date` y `Last update` no tienen por qué ser ignición y extinción;
- no representa necesariamente pequeñas islas quemadas/no quemadas bajo la
  resolución del sensor.

La [página de datos y
servicios](https://forest-fire.emergency.copernicus.eu/applications/data-and-services)
publica un WFS y descargas Shapefile/SpatiaLite de la base de áreas quemadas
actualizada en tiempo real. El esquema WFS observado incluye `id`, fechas,
provincia, municipio, área y geometría poligonal. La consulta se recortó a una
caja valenciana y después se filtró por los nombres oficiales de provincia; la
caja también devolvió incendios de Albacete, Murcia, Tarragona y Teruel, por lo
que **un BBOX no basta para asignar territorio**.

Los recuentos de 9 (2025) y 16 (2026) son una instantánea dinámica, no el total
de incendios. EFFIS publica los contenidos propios de la UE bajo [CC BY
4.0](https://forest-fire.emergency.copernicus.eu/about-effis/data-license): hay
que atribuir e indicar modificaciones.

### MITECO / EGIF

Los [avances
informativos](https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-avances.html)
se construyen con datos provisionales remitidos por las comunidades. El avance
de 2026 cerrado a 9 de agosto señala además que las superficies de incendios no
extinguidos no entran en el total administrativo y aporta una estimación EFFIS
separada. Esta separación confirma que ambas fuentes no tienen igual naturaleza
ni deben fusionarse sin etiqueta.

El [buscador público
EGIF](https://servicio.mapa.gob.es/incendios/Search/Publico) permite Excel y
XML de los partes consolidados. Su ayuda dice expresamente que muestra datos
revisados y cerrados. En esta revisión no devolvió registros de 2024, 2025 ni
2026, así que no resuelve la incorporación reciente aunque debe monitorizarse.

Las [condiciones de reutilización de datos abiertos
MITECO](https://www.datosabiertos.miteco.gob.es/es/aviso-legal.html) permiten
copiar, difundir, modificar, adaptar y combinar, con atribución, fecha de
actualización, conservación de metadatos y sin sugerir respaldo ministerial.

## Diseño propuesto

### Tres estados visibles, no tres autoridades equivalentes

1. **Histórico consolidado**: snapshot ICV 1993–2024 ya normalizado. Etiqueta
   temporal `consolidated_snapshot`; la cartografía sigue siendo informativa y
   no equivale a cobertura estadística completa.
2. **Reciente oficial**: filas administrativas provisionales de SIGIF/GVA.
   Etiqueta `provisional_administrative`; pueden existir sin perímetro y no se
   incorporan al histórico consolidado hasta una promoción explícita.
3. **Reciente satelital/provisional**: áreas quemadas EFFIS. Etiqueta
   `provisional_satellite`; pueden estar sin enlazar a un incendio
   administrativo y nunca heredan autoridad ICV/GVA.

### Estado y procedencia independientes

En `fires`, además de los campos ya existentes, los futuros derivados recientes
deberían conservar:

```text
record_maturity         consolidated | provisional | operational
authority_type          regional_administrative | national_administrative | satellite
source_record_id        identificador oficial, nullable
source_observation_id   identificador interno de la observación/snapshot
retrieved_at
source_updated_at       nullable
coverage_start
coverage_end
coverage_complete       boolean
identity_status         unlinked | candidate | verified
```

La ausencia de ID en SIGIF obliga a tratar cada fila como **observación de
fuente**, no como identidad demostrada. Puede calcularse un hash de los campos
visibles para detectar igualdad, pero no usarlo como prueba de que dos
observaciones son el mismo incendio. Un `source_observation_id` reproducible
debe incluir el checksum del snapshot y la posición original; las filas
idénticas se conservan.

En `geometries`:

```text
geometry_maturity       provisional | final
geometry_method         official_vector | satellite_rda | reported_point
geometry_quality        A | B | C | D
preference_status       candidate | preferred | superseded
preferred_from
preferred_until         nullable
superseded_by            geometry_id nullable
match_method             official_id | reviewed_spatiotemporal | unlinked
match_confidence         nullable
```

`preferred` es una selección derivada, no un borrado. Cuando llegue un
perímetro ICV oficial:

1. se ingiere como una geometría nueva;
2. se enlaza por identificador oficial cuando sea posible;
3. pasa a ser la geometría preferida;
4. el perímetro EFFIS queda conservado con su procedencia y marcado como
   `superseded`, no eliminado;
5. las diferencias de área o forma se registran como auditoría.

La prioridad inicial es:

```text
ICV oficial (A) > otra geometría oficial documentada > EFFIS RDA (B)
```

Esta prioridad solo elige representación. No demuestra identidad entre
registros: un enlace EFFIS–SIGIF exige coincidencia espacial/temporal revisada
y nunca se basa únicamente en municipio o área.

## Recomendación de incorporación

### Primero 2025

1. Solicitar aclaración escrita sobre la reutilización de las filas SIGIF y
   sobre el CRS/semántica de `X1`/`Y1`.
2. Preparar una ingesta local reproducible de la tabla 2025 como snapshot
   **administrativo provisional**, manteniendo las 281 filas, la fila visible
   repetida y los valores sin corregir. No publicarla mientras la licencia no
   esté aclarada.
3. Ingerir en una colección separada el snapshot EFFIS 2025, filtrado por
   intersección con el límite autonómico y auditado también por `PROVINCE`.
   Asignar calidad B y conservar su `id` y `LASTUPDATE`.
4. Generar candidatos de enlace por fecha, proximidad/intersección y área, con
   revisión humana; no convertir el `id` EFFIS en `fire_id` administrativo.
5. Monitorizar ICV. Cuando publique 2025, usar el pipeline ICV existente y
   promover su geometría a preferida sin eliminar la EFFIS.

### Después 2026

1. Tratar 2026 como colección móvil e incompleta: la consulta SIGIF llega solo
   al 30 de junio pese a haberse realizado el 19 de agosto.
2. Crear snapshots fechados, como máximo semanales, sin sobrescribir los
   anteriores. Registrar `coverage_end` e `is_complete_year=false`.
3. Capturar EFFIS por separado con la misma política de snapshots. Sus 16
   polígonos valencianos observados hoy no representan el inventario completo.
4. Usar el panel semanal GVA y el avance MITECO únicamente para controles de
   totales y desfases.
5. Cerrar un snapshot provisional tras finalizar el año y promoverlo solo
   cuando llegue una fuente oficial consolidada/ICV, manteniendo todas las
   versiones anteriores.

## Incertidumbres que requieren seguimiento

- licencia efectiva para redistribuir filas o PDFs generados por SIGIF;
- significado y CRS exactos de `X1`/`Y1`;
- causa del desfase de SIGIF 2026 y calendario real de actualización;
- fecha prevista de publicación ICV 2025;
- estabilidad histórica de los `id` del WFS EFFIS y política de sustitución de
  clases móviles como `30DAYS`/`FireSeason`;
- reglas de enlace entre NumPIF, EGIF, SIGIF y EFFIS.
