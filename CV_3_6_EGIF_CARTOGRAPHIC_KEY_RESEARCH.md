# CV-3.6 — Recuperación de la clave cartográfica histórica EGIF

Fecha de investigación: 23/08/2026
Ámbito: partes EGIF de Alicante, Castellón y Valencia, 1968–1992
Resultado: **la clave no alcanza `A_CONFIRMED`; no se ha generado ninguna geometría**

> **Revisión CV-3.6b (23/08/2026).** La comparación inicial con el índice
> temático IGME 1:200.000 no era válida para interpretar la numeración de la
> serie militar 5L. El índice original 5L sitúa `7-4` y `8-4` en el este
> peninsular, de forma compatible con `0704` y `0804`. Esta corrección no
> permite aún decodificar `A01`–`O12` ni promover registros a `A_CONFIRMED`.
> La investigación del activo GIS se documenta en
> `CV_3_6B_HISTORICAL_GRID_ASSET_SEARCH.md`.

## Conclusión ejecutiva

La investigación ha mejorado sustancialmente la descripción documental del
sistema, pero no permite transformar responsablemente códigos como
`0704:C11`, `0804:B01` o `0804:N04` en límites UTM.

Está demostrado que:

- el sistema inicial de localización EGIF asignaba el parte a una celda UTM
  nominal de 10 × 10 km, referida a una hoja 1:200.000 del Instituto
  Geográfico del Ejército;
- la cartografía militar aprobada en 1968 utilizaba el elipsoide internacional
  de Hayford, datum europeo de Potsdam, proyección UTM y su cuadrícula;
- las hojas generales se numeraban mediante columna y fila desde el noroeste de
  la cuadrícula nacional;
- el manual ICONA de 1993 identifica una cuadrícula mediante letra y número en
  los márgenes de la hoja, siguiendo un «patrón del ICONA» que debía solicitarse
  al organismo si no estaba impreso;
- EGIF cambió a hojas IGN 1:250.000 a mediados de los noventa, fuera del periodo
  auditado.

Sin embargo, no se ha localizado el patrón ICONA, una tabla oficial
`hoja + cuadrícula → coordenadas/límites`, ni documentación de la migración de
los registros históricos al sistema informático actual. La subfase CV-3.6b ha
demostrado que `0704` y `0804` son compatibles con la numeración de la serie
militar 5L 1:250.000, no con la lectura que se hizo inicialmente del índice
temático IGME. Esa compatibilidad no demuestra si el XML fue recodificado ni
permite obtener los límites de `C11`, `B01` o `N04`.

Los 8.565 pares permanecen en `B_PROBABLE`, los 610 partes restantes en
`NO_REFERENCE` y los 9.175 partes mantienen `geometry=null`. La fase termina
correctamente sin geometrías: falta evidencia institucional concreta.

## Pregunta y criterio de confirmación

La pregunta de CV-3.6 es si existe una regla documental y reproducible que
permita obtener, para cada código histórico, el rectángulo nominal de 10 km por
10 km en su CRS original.

Para promover un par a `A_CONFIRMED` deben conocerse conjuntamente:

1. significado y versión del campo `hoja` almacenado en el XML;
2. significado, origen y sentido de letra y número de `cuadricula`;
3. relación de ambos códigos con coordenadas UTM o límites de celda;
4. datum, huso y unidades;
5. reglas de costa, borde de hoja y cambio de huso;
6. trazabilidad de cualquier recodificación histórica realizada por
   EGIF/NEGIF/EGIFWEB.

El ajuste visual a municipios o incendios conocidos no satisface estos
criterios.

## Evidencia primaria localizada

### 1. Base geodésica y numeración de la cartografía militar

El [Decreto 2992/1968, de 21 de noviembre](https://www.boe.es/buscar/doc.php?id=BOE-A-1968-1421),
Ministerio del Ejército, BOE 293 de 06/12/1968, pp. 17474–17476, aprueba las
bases de la nueva cartografía militar. En su base tercera incluye el mapa
1:200.000; en la base cuarta establece:

- elipsoide internacional de Hayford;
- datum europeo de Potsdam;
- proyección Universal Transversa Mercator;
- cuadrícula UTM correspondiente.

La base sexta indica que la designación numérica de las hojas generales se
forma con dos números —columna y fila, por ese orden— contados desde el extremo
noroeste de la cuadrícula nacional. La norma describe la cartografía base, pero
no el patrón añadido por ICONA para codificar las subcuadrículas de incendios.

El [Real Decreto 1071/2007](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-15822)
confirma retrospectivamente que ED50 usa Hayford 1924, datum Potsdam 1950 y UTM,
y que fue el sistema oficial español desde 1970 hasta su sustitución por
ETRS89. Esto respalda el contexto de la serie militar, pero no demuestra por sí
solo que el campo exportado por EGIF conserve coordenadas directamente
decodificables en ED50.

### 2. Semántica EGIF de la celda

El capítulo sobre incendios de
[*La restauración forestal de España: 75 años de una ilusión*](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/desertificacion-restauracion/libro75anosdeunailusion_b_tcm30-530962.pdf),
MAPAMA/SECF, 2017, pp. 347–348, documenta que la referencia inicial del ICONA
asignaba cada incendio a una cuadrícula UTM de 10 × 10 km referida a hojas
1:200.000 del Instituto Geográfico del Ejército. También sitúa a mediados de
los noventa el cambio a hojas IGN 1:250.000.

Esta fuente demuestra la resolución nominal (100 km²) y la cartografía de
referencia, no la clave alfanumérica.

### 3. Manual ICONA y «patrón del ICONA»

El *Manual de operaciones contra incendios forestales*, ICONA, Madrid, 1993,
depósito legal M. 35125-1993, sección 9 «Identificación de la localización»,
p. 8.38, explica que:

- la hoja 1:200.000 se identifica con dos números situados en la esquina
  superior derecha (ejemplo del manual: `2-7`);
- la hoja contiene una cuadrícula azul de cuadrados de 10 km;
- la cuadrícula se identifica por la intersección de una letra y un número
  impresos en los márgenes (ejemplo: `B-5`);
- las marcas se colocan normalmente de acuerdo con un patrón del ICONA; si la
  hoja no está marcada, el usuario debe solicitar dicho patrón al ICONA.

La edición y autoría se verifican en el
[registro bibliográfico de Fundación MAPFRE](https://documentacion.fundacionmapfre.org/documentacion/publico/es/bib/23555.do?format=mods).
El contenido de la sección se consultó en una copia digital de la publicación,
pero no se ha encontrado una reproducción oficial abierta del manual. Por
ello, la referencia bibliográfica es sólida, mientras que el patrón ausente
debe solicitarse al custodio institucional antes de usarlo como clave de
producción.

La mención expresa al patrón ICONA explica por qué no basta con conocer la
cuadrícula UTM estándar: letra y número son una convención documental añadida.

### 4. Índices cartográficos: corrección de la comparación inicial

El portal oficial del
[Mapa Geotécnico General 1:200.000 del IGME](https://info.igme.es/cartografiadigital/tematica/Geotecnico200.aspx)
declara que su base topográfica procede del Mapa Militar de España 1:200.000 y
publica un índice columna-fila. Para el entorno valenciano aparecen:

| Hoja 1:200.000 | Nombre oficial del índice |
|---|---|
| `7-6` | Teruel |
| `8-6` | Vinaroz |
| `7-7` | Liria |
| `8-7` | Valencia |
| `7-8` | Onteniente |
| `8-8` | Alcoy |
| `7-9` | Elche |
| `8-9` | Alicante |

En ese mismo índice, `7-4` es Zaragoza y `8-4` Lérida. CV-3.6 interpretó
incorrectamente esa coincidencia formal como un conflicto con el XML. Un mapa
temático IGME y la serie militar 5L son productos diferentes y sus claves no
son intercambiables automáticamente.

El índice original de la *Cartografía militar de España, mapa general, serie
5L, escala 1:250.000*, Servicio Geográfico del Ejército, conservado por la
[University of California, Berkeley](https://digicoll.lib.berkeley.edu/record/104943),
sitúa `7-4` y `8-4` en el este peninsular. Los valores valencianos
`0703`…`0805` son compatibles con esa malla 5L cuando se escriben con cero de
relleno. Esto refuerza la hipótesis de que el XML actual guarda identificadores
1:250.000, pero sigue sin demostrar:

- si los partes 1968–1992 fueron recodificados al migrar el inventario;
- cuál es la clave/orientación de `A01`–`O12`;
- el CRS y las reglas de borde del activo GIS utilizado por DGB.

### 5. Cambio de serie y posible migración

Fuentes oficiales describen la coexistencia histórica de varias series:

- la documentación militar y el Decreto de 1968 denominan 2C a la serie
  1:200.000;
- la historia cartográfica del IGN sitúa la finalización de la serie militar
  1:250.000 (5L) en 1993;
- MITECO documenta el cambio de EGIF desde IGE 1:200.000 a IGN 1:250.000 a
  mediados de los noventa;
- las instrucciones actuales del parte usan hojas 1:250.000 y almacenan por
  separado hoja/cuadrícula y coordenadas UTM del punto de inicio.

Un artículo de la revista oficial *Ecología* (MITECO/OAPN, 2003), que estudia
1988–1999, describe las cuadrículas como pertenecientes al Mapa Militar
1:250.000. No invalida la fuente de 2017: puede describir el esquema vigente al
extraer los datos o una recodificación. CV-3.6b ha encontrado además la capa
operativa `Hc250LL`, usada para enlazar por `HOJA + CUAD` los registros DGB
1995–2004, pero no su fichero ni su CRS. Sin documentación de migración no se
puede proyectar esa descripción hacia atrás.

## Códigos prioritarios

| Código | Parte de control | Municipio documentado | Lo demostrado | Lo pendiente |
|---|---|---|---|---|
| `0704:C11` | `1992460250` | Marines | sintaxis válida y celda nominal 10 km | hoja real, origen, ejes, huso y límites |
| `0804:B01` | `1992120403` | Altura | sintaxis válida y celda nominal 10 km | idem; relación con otro parte del episodio Marines–Altura no se resuelve |
| `0804:B01` | `1992469001` | sin municipio resuelto | mismo par raw | idem; no usar municipio para elegir celda |
| `0804:N04` | `1990030079` | Castell de Castells | sintaxis válida y celda nominal 10 km | idem |

No se han calculado celdas diagnósticas ni se han usado estos municipios para
escoger una interpretación.

## Rango `A01`–`O12`

Los datos observan 166 códigos de los 180 posibles de la expresión formal
`[A-O][01-12]`. El manual de 1993 demuestra que la letra y el número se leen en
los márgenes de la cuadrícula azul, pero no especifica en la sección disponible:

- qué eje corresponde a la letra y cuál al número;
- desde qué esquina empiezan;
- si avanzan de oeste a este / norte a sur o a la inversa;
- por qué existen 15 letras y 12 números;
- si todas las hojas usan el mismo patrón o recortes variables;
- cómo se identifican celdas parciales de costa o borde.

Por tanto, el rango es una regularidad del dataset, no una clave espacial.

## Datum, proyección, husos y bordes

El Decreto de 1968 documenta como nuevo marco militar Hayford/datum europeo y
UTM. No basta para fechar la adopción efectiva en cada edición: el catálogo de
la Cartoteca IGN conserva un conjunto del Mapa Militar Itinerario 1:200.000 de
1967–1970 descrito con cuadrícula Lambert, mientras la historia IGN sitúa la
conversión del mapa itinerario en serie 2C entre 1967 y 1971. La transición
atraviesa, por tanto, el inicio de EGIF y requiere identificar el ejemplar o
activo realmente utilizado.

En UTM peninsular intervienen los husos 29, 30 y 31; el territorio valenciano
se encuentra principalmente en el 30, pero una regla de ámbito no sustituye el
huso del documento fuente.

No está documentado para el valor XML:

- si el patrón ICONA usa coordenadas de un único huso por hoja;
- si una celda se recorta en un límite de huso o se mantiene en el huso de la
  hoja;
- cómo se resuelven solapes o discontinuidades;
- si celdas costeras conservan el cuadrado nominal completo;
- si la posterior migración a 1:250.000 conservó el datum original o solo el
  identificador categórico.

No se asigna EPSG ni se transforma a EPSG:4326.

## Estado de evidencia

| Componente | Estado | Motivo |
|---|---|---|
| celda nominal 10 × 10 km | confirmado | documentación MITECO/ICONA |
| referencia original a hoja IGE 1:200.000 | confirmado para el sistema inicial | documentación MITECO |
| base geodésica de la serie militar de 1968 | confirmada | Decreto 2992/1968 |
| letra + número en márgenes | confirmado | manual ICONA 1993 |
| clave/origen/orientación del patrón ICONA | no localizada | el manual remite al patrón, pero no lo reproduce |
| semántica de `0703`…`0805` en el XML actual | probable 5L, no confirmada por diccionario DGB | compatible con el índice original 5L; migración histórica no documentada |
| migración 2C → 1:250.000 / EGIFWEB | no documentada | falta historial de transformación |
| tabla a límites UTM | no localizada | necesaria para `A_CONFIRMED` |
| husos y reglas de borde | no localizados | necesarias para geometría reproducible |

Clasificación final de los registros, sin cambios respecto a CV-3.5:

| Estado | Partes |
|---|---:|
| `A_CONFIRMED` | 0 |
| `B_PROBABLE` | 8.565 |
| `C_AMBIGUOUS` | 0 |
| `D_UNUSABLE` | 0 |
| `NO_REFERENCE` | 610 |

La nueva evidencia confirma parámetros del contexto cartográfico y elimina el
supuesto conflicto de numeración. La ausencia de activo, CRS, clave de
subcuadrícula e historial de migración sigue impidiendo promover los pares a A.

## Documento o dato concreto que falta

Una respuesta útil de MITECO/ADCIF o del custodio cartográfico debería aportar
al menos uno de estos elementos:

1. plantilla o «patrón del ICONA» usado para rotular la cuadrícula azul de las
   hojas 1:200.000;
2. manual/instrucción de cumplimentación del parte vigente entre 1972 y 1992;
3. tabla de correspondencia histórica `hoja + cuadrícula → huso, Xmin, Ymin,
   Xmax, Ymax`;
4. diccionario de `hoja` de NEGIF/EGIFWEB, con fecha y versión;
5. documentación de migración desde 1:200.000 a 1:250.000 que explique si los
   registros anteriores fueron recodificados;
6. ejemplar de una hoja 2C con la sobreimpresión o anotación ICONA completa y
   su leyenda;
7. reglas para costa, límites de hoja y cambios de huso.

## Licencia y conservación documental

No se ha descargado ni redistribuido cartografía militar, plantillas ni copias
del manual. Se han registrado enlaces, organismo, edición y páginas.

El Decreto 2992/1968 declaró la cartografía militar de libre difusión en
beneficio de la utilidad pública; la posterior
[Orden DEF/277/2003](https://www.boe.es/eli/es/o/2003/02/04/def277)
regula difusión y comercialización de productos geográficos de Defensa. Eso no
autoriza automáticamente a publicar una digitalización histórica concreta ni
una plantilla ICONA: antes de incorporar una malla derivada habrá que confirmar
las condiciones del ejemplar y atribuir separadamente:

- EGIF: MITECO/ADCIF;
- patrón o tabla ICONA: organismo custodio y condiciones indicadas;
- definición/cartografía militar: Centro Geográfico del Ejército/Defensa;
- cualquier producto IGN/CNIG usado para transformación o validación.

## Próximo paso propuesto

No debe iniciarse representación cartográfica ni una CV-3.7. El paso siguiente
es enviar —tras revisión humana— las dos consultas preparadas en
`CV_3_6_RESEARCH_CONTACT_PACKET.md`:

1. MITECO/ADCIF o Banco de Datos de la Naturaleza, para localizar `Hc250LL` o
   su sucesora, el diccionario, el `.csf`, un crosswalk a `COD_INB` y la
   trazabilidad de migración EGIF;
2. Centro Geográfico del Ejército, con apoyo de la Cartoteca IGN/CNIG, para
   localizar hojas 2C/5L anotadas y especificaciones del patrón/cuadrícula;
3. CCHS-CSIC o responsables del proyecto UPM, como vía complementaria para
   recuperar el almacén ArcView suministrado.

Si se recibe una clave oficial completa, el proyecto debe detenerse de nuevo
antes de crear geometrías, registrar la evidencia y someter la promoción a
`A_CONFIRMED` a revisión.
