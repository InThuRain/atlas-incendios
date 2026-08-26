# CV-4.2 — Paquete de consultas sobre perímetros históricos

Fecha: 25/08/2026. **Borradores no enviados.**

## Contexto común

El Atlas de Incendios es un proyecto independiente que documenta incendios y
geometrías con procedencia explícita. Para 1968–1992 publica partes EGIF sin
inventar geometrías. Estamos evaluando fuentes históricas reales para Alicante,
Castellón y Valencia. Una geometría científica, una oficial y un registro EGIF
permanecen como entidades separadas mientras no exista evidencia de enlace.

## A. Autores de ESFire30

**Asunto:** Consulta de CRS, identificadores y metodología de ESFire30 Causes v1

Estimadas/os autoras/es:

Estamos auditando ESFire30 Causes v1 (DOI 10.5281/zenodo.18449006) para una
posible incorporación al Atlas de Incendios como cartografía histórica de
teledetección, siempre separada de los registros administrativos EGIF.

Hemos observado que `read_me.txt` declara EPSG:25830, mientras los `.prj` de
1985–2021 declaran `ED_1950_UTM_Zone_30N` (EPSG:23030). Un contraste diagnóstico
de ambas hipótesis con 450 candidatos ICV del mismo año favorece EPSG:23030 en
448/450 IoU y 411/450 distancias de centroide.

¿Podrían confirmar por escrito:

1. el CRS/datum real de las coordenadas SHP de v1;
2. si la mención EPSG:25830 y “30 km” del README son erratas;
3. si existe un identificador estable de perímetro/evento no incluido en DBF;
4. si una feature representa un episodio completo, una mancha detectada o
   puede haber varias features para un episodio;
5. qué sensores Landsat y fechas/ventanas se usaron por año;
6. dónde puede consultarse el artículo o documentación del producto geométrico
   ESFire30 citado como *under review*;
7. si prevén publicar una versión corregida o un changelog?
8. qué regla recomiendan para reconocer la misma feature entre futuras
   versiones, dado que v1 no publica un identificador estable?

No solicitamos autorización adicional sobre CC BY 4.0, sino precisión técnica
para describir responsablemente el producto y sus transformaciones.

CV-4.3 ha demostrado localmente una integración reversible de 710 polígonos,
con IDs por contenido, sin enlaces EGIF y sin publicación. La respuesta se
usaría para mejorar la trazabilidad entre versiones, no para confirmar matches.

## B. Generalitat Valenciana — archivo anual 1978–1992

**Asunto:** Solicitud de información sobre cartografía anual de incendios de Valencia 1978–1992

Un trabajo técnico de caracterización de incendios de la provincia de Valencia
indica que la Conselleria suministró cartografía de perímetros elaborada
anualmente desde 1978, mientras Alicante y Castellón comenzarían en 1993.

¿Se conserva esa serie 1978–1992 y, en caso afirmativo, podrían indicar:

1. unidad/archivo custodio y procedimiento de acceso;
2. años y cobertura territorial reales;
3. formato original y actual, CRS/datum, escala o precisión;
4. identificadores y posibilidad de relación con partes EGIF;
5. metodología de levantamiento y cambios históricos;
6. licencia, atribución y permiso para redistribuir derivados reproyectados o
   simplificados?

Nos interesa el activo original y sus metadatos, no reconstruir perímetros por
aproximación.

## C. M. Pilar Martín / CSIC — NOAA-AVHRR

**Asunto:** Inventario y disponibilidad de cartografía NOAA-AVHRR de incendios históricos

Gracias por confirmar que su tesis cartografió numerosos incendios históricos
con NOAA-AVHRR y validación de campo. Para evaluar responsablemente esas capas,
¿sería posible conocer o recuperar:

1. inventario de incendios/años/provincias cartografiados;
2. ficheros raster o vectoriales y metadatos conservados;
3. CRS, resolución, escenas y método de delimitación;
4. cartografía o trabajo de campo usado para validar;
5. correspondencia, si existe, con identificadores EGIF;
6. titularidad/licencia de los resultados y condiciones para publicar un
   derivado con atribución?

Los resultados se presentarían como teledetección histórica, nunca como
perímetros oficiales.

## D. Estudio Landsat Hoya de Buñol

**Asunto:** Localización de cartografía digital Landsat de los incendios de Hoya de Buñol de 1991

Estamos inventariando perímetros históricos anteriores a 1993 en el País
Valencià. El estudio sobre la Hoya de Buñol documenta cartografía Landsat de
incendios como Yátova/Chiva en 1991.

¿Se conservan las capas o rasters de trabajo originales? En caso afirmativo,
solicitamos metadatos sobre escenas, fechas, CRS, resolución, validación,
identificadores y licencia para consulta, transformación y publicación de un
derivado. También agradeceríamos la referencia del custodio actual si los
archivos se transfirieron a otra institución.

## E. Cartografía fuente Chera–Sot de Chera

**Asunto:** Fuente de los perímetros históricos incluidos en el plan de Chera–Sot de Chera

El plan de prevención de Chera–Sot de Chera incluye mapas de incendios
históricos, entre ellos registros de 1986 y 1992. Para no digitalizar una figura
sin procedencia suficiente, necesitamos conocer:

1. qué cartografía o expedientes originales se usaron;
2. si existen capas GIS, mapas georreferenciados o croquis a mayor resolución;
3. escala, CRS/datum, método y precisión;
4. fecha/municipio/superficie o ID de cada episodio representado;
5. titularidad y licencia para digitalizar y publicar un derivado.

## Evidencia que se adjuntaría bajo petición

- tabla de los 710 polígonos ESFire30 1985–1992 por año/provincia;
- checksums y WKT literal de los `.prj`;
- estadística comparativa EPSG:23030/EPSG:25830 sin compartir datos ICV raw;
- referencias de CV-4.1 y CV-4.2;
- ejemplos EGIF de Sot de Chera, Yátova, Chiva y Marines–Altura, claramente
  etiquetados como candidatos no confirmados.
