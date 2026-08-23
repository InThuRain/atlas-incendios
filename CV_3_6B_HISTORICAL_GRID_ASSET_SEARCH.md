# CV-3.6b — Búsqueda del activo GIS histórico EGIF

Fecha de investigación: 23/08/2026
Ámbito: clave `HOJA + CUADRICULA` de EGIF y malla nominal de 10 × 10 km
Resultado: **se ha identificado la cadena técnica de una capa operativa, pero
no se ha localizado el activo ni una tabla de conversión reutilizable**

Esta subfase es documental. No se han generado celdas, puntos ni geometrías de
incendio, no se han modificado datasets y no se ha tocado el frontend.

## Conclusión ejecutiva

`Hc250LL` era la clase de entidad o tabla espacial creada en GeoMedia al
importar una base de cuadrículas 10 × 10 km suministrada en formato ArcView.
La utilizó en 2010 un proyecto de la UPM para enlazar la base de incendios de la
antigua DGB mediante igualdad exacta de `HOJA` y `CUADRICULA`. Contenía, como
mínimo, geometría, `HOJA`, `CUAD`, `COD250` e `ID1`. No está demostrado que
`Hc250LL` fuese el nombre del shapefile original: el texto lo presenta como la
tabla resultante de la importación a Access/OpenGIS.

La cuadrícula había sido realizada por investigadores del Instituto de
Economía, Geografía y Demografía del CSIC y fue suministrada al proyecto por el
Centro de Ciencias Humanas y Sociales del CSIC. La DGB suministró por separado
la base de incendios. El proyecto recibió la capa ArcView **sin definición de
sistema de coordenadas** y creó un fichero local `Cuadricula ArcView.csf`, pero
la memoria no reproduce sus parámetros. Por ello el PDF no confirma el CRS de
la capa.

No se ha localizado `Hc250LL`, el almacén ArcView original, el `.csf`,
`BD_DGB_Cuadrícula`, una tabla `HOJA+CUAD → coordenadas`, ni material
suplementario. Tampoco se ha localizado `Muncuad10x10.shp`: el único uso exacto
encontrado pertenece a un plan oficial de Castilla-La Mancha y describe una
capa de intersección municipio × cuadrícula usada para situar registros sin
coordenadas, no demuestra que sea la capa nacional original.

Sí se ha encontrado una pista institucional posterior importante. La malla
10 × 10 km publicada actualmente por el Banco de Datos de la Naturaleza de
MITECO documenta que transfirió atributos desde una «cuadrícula antigua
ED50_H30» a una nueva malla ETRS89 H30 y conserva el campo `COD_INB` para
relacionarse con datos antiguos. Esa distribución no contiene `HOJA` ni `CUAD`
y no prueba que la malla antigua fuera `Hc250LL`, pero identifica una posible
cadena de custodia y una pregunta concreta para MITECO/BDN.

La revisión del índice de la serie militar 5L corrige una conclusión previa:
la numeración del mapa temático IGME 1:200.000 no puede usarse como índice de
la serie 5L. En el índice original 5L 1:250.000, `7-4` y `8-4` se sitúan en el
este peninsular y son compatibles con los valores valencianos `0704` y `0804`.
Esto refuerza que la exportación DGB/EGIF use una clave 1:250.000, pero no
resuelve la subdivisión `A01`–`O12`, el datum del activo ni la migración de los
partes 1968–1992.

El estado sigue siendo `B_PROBABLE`: **ninguna referencia alcanza todavía
`A_CONFIRMED`**.

## 1. Proyecto UPM revisado íntegramente

Fuente técnica:

- Rosa Almudena Seco Granja, *Aplicación de un sistema de información
  geográfica al análisis de los datos de incendios forestales en España*,
  Proyecto Fin de Carrera, UPM, 2010;
- ficha institucional: <https://oa.upm.es/3454/>;
- PDF: <https://oa.upm.es/3454/1/PFC_ROSA_ALMUDENA_SECO_GRANJA.pdf>;
- SHA-256 del PDF consultado:
  `a7c5320da635332ca60c5d6e0f37e3995817c27dd70eefa2f61d0becc5f79a86`;
- el repositorio ofrece un único PDF de 248 páginas; no se encontraron anexos
  descargables ni ficheros incrustados.

No es una fuente oficial de la definición cartográfica, pero es evidencia
técnica directa del flujo que operaba con la base DGB entre 1995 y 2004.

### 1.1 Procedencia declarada

La memoria distingue tres procedencias:

- el equipo de la antigua Dirección General de la Biodiversidad —Juan Carlos
  Mérida Fimia y Antonio Muñoz— suministró la información de incendios;
- el Centro de Ciencias Humanas y Sociales del CSIC suministró la información
  de la cuadrícula 10 × 10 km;
- la sección 2.5, p. 38, atribuye la realización de la base espacial a
  investigadores del Instituto de Economía, Geografía y Demografía del CSIC.

No debe describirse por tanto `Hc250LL` como una capa «producida por DGB» sin
matiz. Lo demostrado es que DGB la empleó indirectamente en el flujo del
proyecto y que sus campos permitían enlazar la BD DGB.

### 1.2 Preparación del almacén

La sección 3.3.5, pp. 46–47, documenta:

1. la base de cuadrículas llegó en formato ArcView;
2. no incluía fichero de sistema de coordenadas;
3. GeoMedia necesitaba una definición `.csf` para importarla;
4. el archivo `.ini` apuntaba a
   `D:\Datos_CuadriculaArcView\Cuadricula ArcView.csf`.

La memoria explica el mecanismo, pero no lista el contenido del `.csf`, el
datum, la proyección ni el huso. La superposición correcta que muestran sus
mapas no sustituye esa especificación documental.

## 2. Qué era exactamente `Hc250LL`

La sección 5.1, pp. 90–92, describe el siguiente flujo:

1. importar las entidades espaciales desde el almacén ArcView a un almacén
   Access en formato OpenGIS mediante GeoMedia;
2. obtener en ese almacén la tabla/clase de entidad `Hc250LL`;
3. importar `Hc250LL` a la base de incendios DGB y crear
   `BD_DGB_Cuadrícula`;
4. enlazar cada tabla anual `INCENPARYYYY` con la malla por
   `Hc250LL.HOJA = INCENPAR.HOJA` y
   `Hc250LL.CUAD = INCENPAR.CUADRICULA`;
5. devolver los recuentos a la tabla espacial mediante su clave primaria.

### 2.1 Esquema demostrado

| Campo | Significado demostrado por la memoria |
|---|---|
| geometría | cuadrícula o fragmento terrestre de ella |
| `HOJA` | identificador de hoja usado para el enlace DGB |
| `CUAD` | casilla dentro de la hoja; equivale al campo DGB `CUADRICULA` |
| `COD250` | atributo conservado/seleccionado en las consultas; significado no definido |
| `ID1` | clave primaria única de cada registro espacial |
| `GAVPrimaryKey` | nombre de la clave equivalente en la tabla intermedia `NINCENDIOS_CUADRICULA` |

La memoria advierte que una misma combinación `HOJA + CUAD` puede aparecer en
varios registros espaciales cuando una celda costera tiene fragmentos de tierra
separados por agua. Por tanto:

- `ID1` identifica el fragmento/registro;
- `HOJA + CUAD` identifica la referencia lógica con la que se enlaza EGIF;
- el join no implica necesariamente una geometría única por código.

### 2.2 Qué no puede afirmarse

- No consta el nombre del `.shp` original; `Hc250LL.shp` es una hipótesis de
  búsqueda, no un nombre confirmado.
- El texto no desarrolla `Hc250LL`, `LL` ni `COD250`.
- `COD250` podría aludir a la serie 1:250.000, pero no existe definición
  localizada y no se adopta esa interpretación como hecho.
- `GAVPrimaryKey` no es una clave cartográfica: la memoria lo trata como la
  copia de la clave primaria de `Hc250LL` en una consulta intermedia.
- No se demuestra que la malla cubra directamente las claves históricas
  anteriores a la adopción del esquema 1:250.000.

## 3. Resultado de la búsqueda del activo

Se buscaron combinaciones exactas y variantes de:

- `Hc250LL`, `HC250LL`, `Hc250LL.shp`, `hc250`;
- `COD250`, `GAVPrimaryKey`;
- `BD_DGB_Cuadrícula`, `BD_DGB_Cuadricula`;
- `Cuadricula ArcView.csf` y `Datos_CuadriculaArcView`;
- almacenes ArcView/GeoMedia asociados a incendios y cuadrícula 10 × 10;
- `Muncuad10x10.shp` y `Muncuad10x10`.

Ámbitos revisados: Archivo Digital UPM y su registro OAI, MITECO/BDN, antiguos
dominios MARM/MAPA, CSIC/Digital.CSIC, catálogos institucionales, repositorios
de documentación y consultas de nombres exactos en Internet Archive.

| Candidato | Resultado |
|---|---|
| fichero ArcView origen de `Hc250LL` | no localizado |
| `Hc250LL.shp` | nombre no confirmado; no localizado |
| tabla/feature class `Hc250LL` | descrita en el PDF; fichero no localizado |
| `Cuadricula ArcView.csf` | ruta documentada; fichero/parámetros no localizados |
| `BD_DGB_Cuadrícula` | base derivada descrita; fichero no localizado |
| tabla `HOJA+CUAD → geometría/coordenadas` | no localizada |
| anexos UPM | no existen en el registro público consultado |
| capturas dentro del PDF | muestran mapas y procedimiento, no una clave completa |
| copias archivadas por nombre exacto | ninguna localizada |

Una búsqueda negativa no demuestra que el activo no se conserve internamente.
Los custodios más plausibles son MITECO/BDN-ADCIF y el antiguo equipo CCHS/CSIC
que suministró la malla.

## 4. Pista `Muncuad10x10.shp`

El nombre aparece en el *Plan Comarcal de Defensa contra Incendios Forestales
de La Jara (Toledo)*. La aprobación y promotor constan en la
[Resolución de 02/10/2017 de Castilla-La Mancha](https://www.castillalamancha.es/sites/default/files/documentos/pdf/20180108/resol._interes_gral._actuac._pdcif.pdf):
Dirección General de Política Forestal y Espacios Naturales.
El texto íntegro consultado para localizar el nombre de fichero procede de una
[copia indexada no oficial](https://esdocs.com/doc/1928638/plan-comarcal---gobierno-de-castilla);
no se ha localizado el antiguo enlace oficial del PDF que enumera la
resolución. Esta limitación impide atribuir al nombre del fichero el mismo grado
de autoridad que a la resolución.

El anexo metodológico del plan describe:

- datos históricos de incendios con hoja y cuadrícula de referencia;
- una «cuadrícula de 10 km de lado donde se ha originado el incendio» asociada
  al nombre `Muncuad10x10.shp`;
- que los registros sin coordenadas exactas se situaron en el centroide del
  polígono formado por la intersección de la cuadrícula y el municipio.

Ese último procedimiento **no es adecuado para este Atlas** y no se reproducirá.
Además, el nombre y el uso sugieren una capa municipio × cuadrícula, no la malla
nacional pura; es una inferencia técnica, no una definición de esquema.

No se ha localizado el shapefile ni documentación que confirme:

- productor original;
- CRS del fichero;
- lista de atributos;
- presencia de `HOJA`/`CUAD`;
- derivación desde `Hc250LL`;
- licencia de redistribución del activo.

La cartografía final del plan usa ETRS89/UTM 30N, pero eso no demuestra el CRS
del fichero intermedio `Muncuad10x10.shp`.

## 5. Pista institucional: malla actual MITECO/BDN

El Banco de Datos de la Naturaleza publica la
[Malla 10 × 10 km terrestre](https://www.miteco.gob.es/es/biodiversidad/servicios/banco-datos-naturaleza/informacion-disponible/bdn-cart-aux-descargas-ccaa.html),
con datos y diccionario públicos.

Se inspeccionaron temporalmente, sin incorporarlos al repositorio:

- ZIP `malla10x10terrestre_p_tcm30-199156.zip`, SHA-256
  `81eff6329051a6ee740b94ca42b49499c3d33721cce01738127246f4a9711c77`;
- diccionario `malla10x10_terrestres_dd_tcm30-199158.xls`, SHA-256
  `35b4e882716e0cce670d591c45891c87fe7bac42522e951d113753c0191e0ad2`.

La capa contiene 5.441 registros y usa ETRS89 / UTM 30N (EPSG:25830). Sus
campos publicados son `OBJECTID`, `POS`, `COD100K`, centroides, `X`, `Y`,
`UTMCODE`, `CUADRICULA`, `MARINO`, `COD100X100`, perímetro, área, `COD_INB` y
campos de forma. No contiene `HOJA`, `CUAD` ni `COD250`.

El diccionario, TRAGSATEC/MITECO, julio de 2012, define:

- `CUADRICULA`: código 10 × 10 en ETRS89 H30;
- `COD_INB`: código 10 × 10 en ED50 H30 «para poder establecer relaciones con
  datos antiguos».

El linaje ISO del ZIP añade que, como paso final, las mallas antiguas
`ED50_H30` fueron transformadas a `ETRS89_H30`; sus centroides se usaron para
traspasar información a las nuevas celdas.

Esto confirma que BDN custodió o utilizó una malla ED50 anterior. No demuestra
que fuese `Hc250LL`, ni ofrece el crosswalk `HOJA+CUAD`. Debe preguntarse:

1. si la «malla antigua ED50_H30» era la capa suministrada al CSIC/UPM;
2. si `COD250` o `HOJA+CUAD` se conservaron durante la migración;
3. si existe una tabla entre esos campos y `COD_INB`;
4. dónde se archiva el origen de `COD_INB` y su metadato anterior a 2012.

## 6. Numeración: revisión de `0704` y `0804`

### 6.1 Series que no deben confundirse

| Producto | Escala/periodo relevante | Papel en esta investigación |
|---|---|---|
| mapas temáticos IGME | 1:200.000 | pueden usar como base una serie militar, pero su índice publicado no prueba la clave EGIF |
| Mapa Militar Itinerario | 1:200.000, anterior y de transición | producto histórico; existen ejemplares catalogados con cuadrícula Lambert |
| serie militar 2C | 1:200.000, 1967–1971 según historia IGN | renovación del mapa itinerario dentro del nuevo plan militar |
| serie militar 5L | 1:250.000, finalizada en 1993 | serie explícita en el flujo DGB 1995–2004 y en instrucciones EGIF posteriores |
| clave ICONA/DGB | campos informáticos `HOJA` + `CUADRICULA` | puede conservar, adaptar o migrar identificadores; falta su diccionario histórico |

La comparación de CV-3.6 con la numeración del Mapa Geotécnico General del
IGME no permitía concluir que `0704` fuera Zaragoza ni `0804` Lérida en el
sistema DGB. Esa conclusión queda retirada.

### 6.2 Índice original 5L

Se inspeccionó el índice de la *Cartografía militar de España, mapa general,
serie 5L, escala 1:250.000*, Servicio Geográfico del Ejército, 1990–, conservado
por la [University of California, Berkeley](https://digicoll.lib.berkeley.edu/record/104943).
La ficha describe 47 hojas, proyección UTM y elipsoide Hayford. El
[escaneo del índice](https://digicoll.lib.berkeley.edu/record/104943/files/G6560_s250_s71_index.jpg)
muestra la numeración columna-fila propia de 5L: `7-4` y `8-4` ocupan el este
peninsular alrededor del paralelo 40°, y `7-5`/`8-5` continúan hacia el sur.

Los valores EGIF valencianos observados (`0703`…`0805`) son, por tanto,
geográficamente compatibles con identificadores de hoja 5L escritos con cero
de relleno. Esta es evidencia de coherencia, no todavía una definición formal
del campo XML. Faltan:

- documento DGB que confirme el relleno y versión de `HOJA`;
- tabla de celdas `A01`–`O12` dentro de cada hoja;
- evidencia de cómo se migraron los partes 1968–1992 desde la referencia
  inicial 1:200.000 a la clave 1:250.000.

## 7. Contexto cartográfico de 1968

El [Decreto 2992/1968](https://www.boe.es/buscar/doc.php?id=BOE-A-1968-1421)
aprobó para la nueva cartografía militar Hayford, datum europeo de Potsdam,
UTM y cuadrícula UTM. Incluyó la escala 1:200.000, pero es un marco normativo:
no prueba el CRS de cada ejemplar usado por ICONA ni el momento exacto en que
se sustituyeron todas las ediciones anteriores.

La historia cartográfica publicada por IGN documenta que:

- el Mapa Militar Itinerario pasó a serie 2C entre 1967 y 1971;
- la serie 5L 1:250.000 se completó en 1993.

Además, el [catálogo de la Cartoteca IGN](https://www.ign.es/web/catalogo-cartoteca/resources/html/026378.html)
describe un conjunto del Mapa Militar Itinerario 1:200.000, 1967–1970, con
cuadrícula Lambert. Esto demuestra que la transición atraviesa 1968 y que no
puede asignarse ED50/UTM a todos los materiales históricos solo por la fecha
del Decreto.

Para EGIF sí existe documentación MITECO de una referencia nominal UTM
10 × 10 km, pero el CRS del activo informático y la historia de recodificación
de cada periodo siguen necesitando evidencia específica.

## 8. Códigos de control

| Código | ¿Aparece en un activo localizado? | Evidencia disponible |
|---|---|---|
| `0704:C11` | no | `0704` es compatible con hoja 5L; `C11` no puede decodificarse |
| `0804:B01` | no | `0804` es compatible con hoja 5L; `B01` no puede decodificarse |
| `0804:N04` | no | `0804` es compatible con hoja 5L; `N04` no puede decodificarse |

No se han buscado celdas por ajuste a Marines, Altura o Castell de Castells.
Los municipios solo podrán validar una clave obtenida documentalmente.

## 9. Estado de confianza

| Componente | Estado tras CV-3.6b |
|---|---|
| existencia de malla operativa DGB enlazable por `HOJA+CUAD` | evidencia técnica fuerte |
| naturaleza y esquema mínimo de `Hc250LL` | documentados por el proyecto UPM |
| origen CSIC/CCHS de la malla usada en el proyecto | documentado por el proyecto UPM |
| archivo original o copia | no localizado |
| CRS de `Hc250LL` | no documentado; el `.csf` falta |
| significado de `COD250` | desconocido |
| compatibilidad `0704/0804` con serie 5L | fuerte, a partir del índice original 5L |
| fórmula/crosswalk de `A01`–`O12` | no localizado |
| vínculo `Hc250LL` ↔ antigua malla ED50 BDN | posible, no demostrado |
| transformación reproducible completa | no disponible |

Clasificación de los 9.175 partes, sin cambios:

| Estado | Partes |
|---|---:|
| `A_CONFIRMED` | 0 |
| `B_PROBABLE` | 8.565 |
| `C_AMBIGUOUS` | 0 |
| `D_UNUSABLE` | 0 |
| `NO_REFERENCE` | 610 |

## 10. Preguntas externas actualizadas

### MITECO / BDN / ADCIF

1. Tenemos constancia de una tabla/clase de entidad `Hc250LL`, importada de
   ArcView, con geometría, `HOJA`, `CUAD`, `COD250` e `ID1`, usada para enlazar
   la BD DGB por `HOJA + CUADRICULA`. ¿Conserva MITECO/BDN una copia de esa
   capa, del almacén ArcView original o de su sucesora?
2. ¿Era `Hc250LL` la «cuadrícula antigua ED50_H30» utilizada al crear en 2012
   la malla actual de BDN y el campo `COD_INB`?
3. ¿Existe un crosswalk `HOJA + CUAD` o `COD250` → `COD_INB` / límites UTM?
4. ¿Qué significa exactamente `COD250` y cómo se forma?
5. ¿Se recodificaron los partes anteriores a 1994 desde hojas 1:200.000 a la
   serie 5L 1:250.000? ¿Con qué tabla/proceso?
6. ¿Se conserva `Cuadricula ArcView.csf`, un `.prj` equivalente o el metadato
   original de datum/huso?
7. ¿Conoce MITECO la capa `Muncuad10x10.shp` usada en planes de Castilla-La
   Mancha y su relación, si existe, con la malla nacional?

### CEGET / Archivo Cartográfico

1. ¿Puede facilitarse el índice y especificación de hojas de las series 2C y
   5L, incluida su relación con la cuadrícula 10 km?
2. ¿Existe una leyenda/patrón oficial para los códigos `A01`–`O12` usados por
   ICONA/DGB dentro de hojas 5L?
3. ¿Qué ediciones 1:200.000 coexistieron en Lambert y UTM/ED50 entre 1967 y
   1971, y cuál pudo suministrarse a ICONA?
4. ¿Cómo tratan 2C/5L las costas, bordes de hoja y cambios de huso?

### IGN / CNIG

1. ¿Existe una tabla histórica de equivalencia entre las hojas militares 2C,
   5L/1:250.000 y las celdas UTM de 10 km usadas por ICONA?
2. ¿Conserva la Cartoteca documentación de la sobreimpresión o «patrón del
   ICONA»?
3. ¿Puede confirmarse la proyección/datum por edición para las hojas implicadas
   y las condiciones de reutilización de una malla derivada?

### Contacto adicional sugerido: CSIC

Preguntar al antiguo Instituto de Economía, Geografía y Demografía/CCHS y, si
es posible, a la dirección del proyecto UPM por el almacén ArcView suministrado,
el `.csf` creado y cualquier copia de `Hc250LL`. Esta vía complementa, no
sustituye, la confirmación institucional de MITECO.

## 11. Decisión de cierre

CV-3.6b no habilita una fase cartográfica. Antes de crear siquiera geometrías
diagnósticas se necesita uno de estos activos:

- copia verificable de la capa con CRS;
- tabla oficial `HOJA+CUAD → límites/coordenadas`;
- crosswalk oficial hacia `COD_INB`;
- documentación completa que permita regenerarla sin ajuste geográfico.

Hasta entonces, los 9.175 partes mantienen `geometry=null`; las 8.565
referencias permanecen como metadatos `B_PROBABLE` y no deben usarse para
contención puntual, superficie quemada o recurrencia.
