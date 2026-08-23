# CV-3.6 — Paquete de investigación y contacto

Estado: borradores preparados; **ningún mensaje enviado**
Fecha: 23/08/2026

## Resumen breve del proyecto

El Atlas de Incendios es un proyecto independiente de investigación y
visualización histórica. Para el País Valencià integra 9.175 partes EGIF de
1968–1992 como registros administrativos sin geometría. No interpreta cada
parte como un episodio físico único y no inventa puntos ni perímetros.

En 8.565 partes aparecen conjuntamente los campos XML:

- `pif_localizacion.hoja`: uno de `0703`, `0704`, `0705`, `0803`, `0804`,
  `0805`;
- `pif_localizacion.cuadricula`: letra `A`–`O` y número `01`–`12`.

La documentación MITECO indica que el sistema inicial EGIF usó celdas UTM
nominales de 10 × 10 km referidas a hojas IGE 1:200.000. El manual ICONA de
1993 menciona una cuadrícula azul rotulada mediante un «patrón del ICONA».

CV-3.6b ha documentado además una capa operativa usada con la DGB en 2010. Una
base ArcView de cuadrículas, realizada por investigadores del Instituto de
Economía, Geografía y Demografía del CSIC y suministrada por el CCHS-CSIC, se
importó a GeoMedia como `Hc250LL`. Sus campos incluían geometría, `HOJA`,
`CUAD`, `COD250` e `ID1`, y se enlazó con la BD DGB por
`HOJA + CUADRICULA`. La capa se recibió sin definición de coordenadas; la
memoria menciona `Cuadricula ArcView.csf`, pero no conserva sus parámetros.

El activo no se ha localizado. La malla 10 × 10 actual de MITECO/BDN conserva
un `COD_INB` ED50 H30 «para poder establecer relaciones con datos antiguos» y
su metadato documenta la migración desde una malla antigua ED50 H30. Falta
saber si era `Hc250LL` o su sucesora y si existe un crosswalk a `HOJA+CUAD`.

No se pretende representar un perímetro de incendio. Solo se estudia si la
referencia documental puede convertirse, con evidencia suficiente, en el área
nominal de la hoja/celda y etiquetarse inequívocamente como tal.

## Ejemplos reales

| Parte EGIF | Año | Provincia | Municipio | Hoja | Cuadrícula |
|---|---:|---|---|---|---|
| `1992460250` | 1992 | Valencia | Marines | `0704` | `C11` |
| `1992120403` | 1992 | Castellón | Altura | `0804` | `B01` |
| `1992469001` | 1992 | Valencia | no resuelto | `0804` | `B01` |
| `1990030079` | 1990 | Alicante | Castell de Castells | `0804` | `N04` |

Los municipios se usarían únicamente para comprobar una clave obtenida de una
fuente documental, nunca para inferirla.

## Referencias ya localizadas

1. MITECO/MAPAMA, *La restauración forestal de España: 75 años de una
   ilusión*, 2017, pp. 347–348: celda UTM 10 × 10 km en hoja IGE 1:200.000 y
   cambio a IGN 1:250.000 a mediados de los noventa.
2. ICONA, *Manual de operaciones contra incendios forestales*, Madrid, 1993,
   D.L. M. 35125-1993, sección 9, p. 8.38: hoja 1:200.000, cuadrícula azul de
   10 km, letra+número en márgenes y referencia a un «patrón del ICONA».
3. Decreto 2992/1968, BOE-A-1968-1421: Hayford, datum europeo Potsdam, UTM,
   serie 1:200.000 y numeración columna-fila desde el noroeste.
4. Seco Granja, UPM, 2010, secciones 2.5, 3.3.5 y 5.1: existencia, procedencia,
   preparación y join de `Hc250LL`; el PDF no define su CRS ni `COD250`.
5. MITECO/BDN, *Malla 10 × 10 km*, metadato y diccionario de 2012: migración
   desde una malla antigua ED50 H30 y campo `COD_INB` para datos antiguos.
6. Índice original de la serie militar 5L 1:250.000, Servicio Geográfico del
   Ejército, 1990–, conservado por UC Berkeley: `7-4` y `8-4` están en el este
   peninsular. Queda retirada la comparación automática anterior con el índice
   temático 1:200.000 del IGME.
7. Instrucciones actuales del Parte de Incendio Forestal v3.6: hoja/cuadrícula
   1:250.000 y coordenadas UTM del punto de inicio son campos distintos.

## Preguntas exactas comunes

1. ¿Qué representa el campo `hoja` de cuatro dígitos en las exportaciones EGIF
   para partes 1968–1992?
2. ¿Conserva la hoja original 1:200.000 o fue recodificado al migrar a
   NEGIF/EGIFWEB o al sistema 1:250.000?
3. ¿Existe una tabla oficial de `hoja + cuadrícula` a huso y límites UTM?
4. ¿Existe el «patrón del ICONA» mencionado por el manual de 1993?
5. En `A01`–`O12`, ¿qué eje representa la letra y cuál el número, desde qué
   esquina se numeran y en qué sentido avanzan?
6. ¿Cuál es el datum exacto del valor almacenado y qué reglas se aplicaban en
   cambios de huso, límites de hoja y costa?
7. ¿Se conserva documentación de las transformaciones o imputaciones aplicadas
   al digitalizar los partes históricos?
8. ¿Qué condiciones de reutilización y atribución tendría una tabla o malla
   facilitada para publicar celdas derivadas no confundibles con perímetros?
9. ¿Se conserva la capa ArcView o tabla `Hc250LL`, con `HOJA`, `CUAD`,
   `COD250` e `ID1`, o el fichero `Cuadricula ArcView.csf`?
10. ¿Era esa capa la «malla antigua ED50_H30» migrada por BDN en 2012 y existe
    una relación `HOJA+CUAD` / `COD250` → `COD_INB`?
11. ¿Qué significa exactamente `COD250`?
12. ¿Se conoce `Muncuad10x10.shp`, citada en un plan de defensa de La Jara, y
    si deriva o no de la malla nacional?

## A) Borrador para MITECO / ADCIF

Canal recomendado: formulario oficial del
[Banco de Datos de la Naturaleza](https://www.miteco.gob.es/es/biodiversidad/servicios/banco-datos-naturaleza/contacto-banco-datos-naturaleza.html),
solicitando derivación al Área de Defensa contra Incendios Forestales. No se
presupone que direcciones históricas de correo sigan operativas.

**Asunto:** Consulta sobre la clave histórica hoja/cuadrícula de EGIF
1968–1992

> Buenos días:
>
> Estamos desarrollando un atlas histórico independiente y de acceso público
> sobre incendios forestales. Hemos incorporado como registros administrativos,
> y por ahora sin geometría, los 9.175 partes EGIF de Alicante, Castellón y
> Valencia de 1968 a 1992.
>
> En 8.565 registros aparecen conjuntamente los campos `hoja` y `cuadricula`.
> Algunos ejemplos reales son `0704:C11` (parte 1992460250, Marines),
> `0804:B01` (parte 1992120403, Altura) y `0804:N04` (parte 1990030079,
> Castell de Castells).
>
> La publicación de MITECO *La restauración forestal de España: 75 años de una
> ilusión* (2017, pp. 347–348) describe el sistema inicial como una celda UTM de
> 10 × 10 km referida a una hoja 1:200.000 del Instituto Geográfico del
> Ejército. El *Manual de operaciones contra incendios forestales* de ICONA
> (1993, sección 9, p. 8.38) indica que las letras y números se marcaban según
> un «patrón del ICONA».
>
> Tenemos además constancia de que la antigua DGB utilizó una capa ArcView
> denominada en su importación a GeoMedia `Hc250LL`, con campos `HOJA`, `CUAD`,
> `COD250` e `ID1`, para relacionar su Estadística General de Incendios
> Forestales con la cuadrícula 10 × 10 km. La describe el proyecto de Rosa
> Almudena Seco Granja (UPM, 2010, secciones 2.5, 3.3.5 y 5.1). La malla fue
> suministrada por el CCHS-CSIC y llegó sin fichero de coordenadas; el proyecto
> creó localmente `Cuadricula ArcView.csf`.
>
> ¿Conserva MITECO/BDN una copia de esa capa, del almacén ArcView original, del
> `.csf` o de una sucesora? El metadato de la malla 10 × 10 actual de BDN
> documenta una migración desde una malla antigua `ED50_H30` y el diccionario
> mantiene `COD_INB` para relacionar datos antiguos. Nos sería especialmente
> útil saber si esa malla antigua era `Hc250LL` y si existe una correspondencia
> `HOJA + CUAD` o `COD250` hacia `COD_INB` o límites UTM. También necesitamos
> conocer el significado exacto de `COD250`.
>
> Quisiéramos saber si conservan el patrón, las instrucciones históricas de
> cumplimentación o una tabla de correspondencia entre `hoja + cuadrícula` y
> los límites UTM. También necesitamos confirmar si el campo de cuatro dígitos
> del XML conserva la hoja original 1:200.000 o si los registros fueron
> recodificados al migrarse a NEGIF/EGIFWEB o al sistema 1:250.000.
>
> En concreto, agradeceríamos información sobre datum, huso, orientación y
> origen de filas/columnas, reglas de costa/borde/cambio de huso y cualquier
> transformación o valor por defecto aplicado durante la digitalización.
> Conocemos asimismo la referencia `Muncuad10x10.shp` en el Plan Comarcal de
> Defensa contra Incendios Forestales de La Jara (Toledo); agradeceríamos
> confirmación de si tiene alguna relación con la malla nacional DGB o si es
> únicamente una intersección municipal elaborada para aquel plan.
>
> No pretendemos reconstruir perímetros. Si la clave puede documentarse, la
> futura visualización mostraría únicamente el cuadrado nominal como
> «referencia cartográfica histórica de 10 × 10 km», con advertencia explícita
> de que no representa el perímetro ni permite inferir que ardiera cada punto.
>
> Por último, agradeceríamos que nos indicaran las condiciones de reutilización
> y la atribución aplicable a la tabla, plantilla o documentación que pudieran
> facilitarnos.
>
> Muchas gracias por su ayuda.

Adjuntos propuestos tras revisión: este resumen, los cuatro ejemplos y la tabla
de frecuencias de `data/sources/egif_spatial_reference_audit.json`; no adjuntar
XML completo ni datos personales.

## B) Borrador para Centro Geográfico del Ejército / IGN-CNIG

Destinatario principal oficial:
[Archivo Cartográfico y de Estudios Geográficos del CEGET](https://patrimoniocultural.defensa.gob.es/es/centros/archivo-cartografico-geografico-ejercito),
`ceget@et.mde.es`. Consulta complementaria:
[Cartoteca y Archivo Topográfico del IGN/CNIG](https://www.ign.es/web/menu-contactar),
`atencioncartoteca@cnig.es` o `documentacionign@transportes.gob.es`.

**Asunto:** Consulta sobre clave ICONA/DGB en series militares 2C y 5L

> Buenos días:
>
> Investigamos la referencia cartográfica utilizada en los partes históricos
> de incendios forestales EGIF/ICONA entre 1968 y 1992. La documentación de
> MITECO describe celdas UTM nominales de 10 × 10 km referidas a hojas del
> Instituto Geográfico del Ejército a escala 1:200.000.
>
> El *Manual de operaciones contra incendios forestales* de ICONA (Madrid,
> 1993, sección 9, p. 8.38) explica que la hoja llevaba una cuadrícula azul de
> 10 km, identificada por una letra y un número en los márgenes, y que esas
> marcas seguían un «patrón del ICONA» que debía solicitarse al organismo si no
> estaba impreso.
>
> ¿Conserva el Archivo algún ejemplar de la serie 2C 1:200.000 con esa
> sobreimpresión/anotación, una plantilla ICONA, su leyenda o instrucciones que
> permitan relacionar hoja y código alfanumérico con límites UTM?
>
> En el XML EGIF valenciano observamos códigos como `0704:C11`, `0804:B01` y
> `0804:N04`. Tras distinguir el índice temático 1:200.000 del IGME del índice
> original de la serie militar 5L, hemos comprobado que en 5L las hojas `7-4`
> y `8-4` se sitúan en el este peninsular. La antigua DGB utilizó además una
> capa ArcView importada como `Hc250LL`, con `HOJA`, `CUAD` y `COD250`, para
> enlazar sus registros 1995–2004. No conocemos, sin embargo, la historia de
> recodificación de los partes 1968–1992 ni la definición de `COD250`.
>
> ¿Podrían confirmar si `0704`/`0804` son identificadores 5L con cero de
> relleno, cómo se relacionan con las hojas 2C originales y si existe una tabla
> o leyenda oficial para las subcuadrículas `A01`–`O12`? También agradeceríamos
> saber si conservan una copia de `Hc250LL`, del patrón ICONA o de sus
> especificaciones.
>
> También agradeceríamos cualquier especificación sobre datum, husos,
> orientación de las letras A–O, números 01–12, origen de la subdivisión y
> tratamiento de celdas en costa, bordes de hoja o cambios de huso. El inicio
> de EGIF coincide con la transición cartográfica de 1968: agradeceríamos
> precisar qué ediciones 1:200.000 usaban todavía cuadrícula Lambert y cuáles
> aplicaban ya Hayford/datum europeo/UTM.
>
> El objetivo no es crear perímetros de incendios: únicamente evaluar si puede
> mostrarse el área nominal de referencia, claramente diferenciada y con la
> atribución correspondiente. Les agradeceríamos también información sobre las
> condiciones para consultar, reproducir y derivar digitalmente esa plantilla o
> cartografía.
>
> Muchas gracias por su orientación y, en su caso, por indicarnos la signatura
> o unidad responsable más adecuada.

## Qué respuesta permitiría continuar

Una contestación narrativa que solo confirme «UTM 10 × 10 km» no basta, porque
eso ya está documentado. Para alcanzar `A_CONFIRMED` se necesita una clave
reproducible o un documento del que pueda transcribirse sin ambigüedad:

- identificador y edición de hoja;
- huso/datum;
- límites UTM o fórmula completa;
- ejes, origen y sentido de letra/número;
- historial de recodificación del campo XML.

Toda respuesta deberá archivarse con fecha, remitente institucional, alcance y
condiciones de reutilización antes de modificar datos o crear geometrías.
