# CV-3.1 — Inventario histórico valenciano 1968–1992

Fecha de comprobación: **2026-08-19**. Esta fase es de investigación,
inventario y diseño. No se han descargado ni normalizado masivamente los partes
EGIF, no se han creado geometrías y no se ha modificado el visor ni los datasets
1993–2026.

## Resultado ejecutivo

EGIF es la fuente administrativa adecuada para construir la serie valenciana
1968–1992, pero no es una serie espacial homogénea. El buscador público devuelve
**9.175 partes** para la Comunitat Valenciana: 2.514 de Alicante, 2.600 de
Castellón y 4.061 de Valencia. De ellos, **181** declaran al menos 500 ha.

Estas cifras no deben leerse como cobertura uniforme. La documentación oficial
explica que entre 1968 y 1979 se recogían principalmente incendios en montes con
intervención pública y, en especial, repoblaciones. La recogida de todos los
siniestros comienza durante los años ochenta y se hace sistemática y más
completa en 1992. Dos ceros observados —Alicante en 1972 y Valencia en 1979— son
por tanto señales de cobertura, no evidencia de ausencia de incendios.

La localización tampoco permite dibujar perímetros. El producto enlazado oficial
solo contiene registros codificados desde 1983 y declara geometrías puntuales
validadas desde 2005. Para 1968–1992 deben conservarse municipio, hoja/cuadrícula
o coordenadas originales cuando existan, pero ninguna coordenada debe mostrarse
como punto preciso hasta auditar su esquema, datum, huso, unidades y rango.

El servicio vectorial ICV sigue empezando en 1993. Sí se han localizado
documentos oficiales con cartografía histórica puntual: el plan de prevención
de Chera–Sot de Chera representa recurrencia para 1978–2004 y menciona áreas de
1978, 1980, 1986, 1990 y 1992. Sus superficies son expresamente aproximadas y el
PDF no publica el vector fuente, por lo que sirve como evidencia y pista de
archivo, no como perímetro listo para incorporar. La documentación pública
localizada de Serra de Mariola cubre 1994–2003, fuera del periodo objetivo.

## Método y límites de esta fase

Se revisaron exclusivamente recursos oficiales MITECO, ICV y Generalitat
Valenciana. Los recuentos se obtuvieron mediante consultas agregadas al
[buscador público EGIF](https://servicio.mapa.gob.es/incendios/Search/Publico)
por comunidad, provincia y año. Los GIF se contaron ordenando por superficie;
en las tres provincias el registro número 100 tenía menos de 500 ha, por lo que
el recuento provincial de GIF es exhaustivo para el snapshot consultado.

No se lanzó la descarga XML completa de los 9.175 partes. Por ello se separan:

- métricas ya demostradas mediante consultas agregadas;
- propiedades documentadas del esquema;
- métricas que requieren la ingesta reproducible de CV-3.2.

Esta limitación impide dar todavía cifras fiables de presencia de municipio,
superficie o coordenadas y auditar duplicados registro a registro. Presentar
estimaciones como recuentos habría sido inventar datos.

## EGIF: cobertura y rupturas de la serie

La [página oficial de EGIF](https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html)
define la estadística, iniciada en 1968, como la fuente oficial nacional y
explica que actualmente el parte contiene más de 150 campos. También advierte
que la calidad depende de la cumplimentación y que la consolidación puede variar
entre provincias.

La documentación histórica del decenio 2006–2015 identifica los siguientes
modelos de parte y cambios de cobertura:

| Periodo | Modelo de parte | Implicación para 1968–1992 |
|---|---:|---|
| 1968–1971 | 1.º | Inicio de EGIF; cobertura principalmente de montes con intervención pública. |
| 1972–1979 | 2.º | Persiste la cobertura selectiva; no es comparable sin cautela con años posteriores. |
| 1980–1982 | 3.º | Comienza la recogida de todos los siniestros con independencia de la propiedad. |
| 1983–1988 | 4.º | Primer periodo con registros codificados en el producto enlazado publicado. |
| 1989 | 5.º | Se incorpora, entre otros cambios, la superficie no forestal. |
| 1990–1992 | 6.º, vigente hasta 1997 | En 1992 se implanta la aplicación para todas las comunidades y provincias y mejora la sistematicidad. |

En consecuencia, el futuro visor deberá distinguir al menos tres bandas de
madurez dentro de la etapa histórica: `early_selective` (1968–1979),
`transition` (1980–1991) y `systematic` (1992). Esto describe el proceso de
recogida; no constituye una puntuación de calidad de cada parte.

## Campos, identificador y descarga

El buscador permite consultar datos básicos, descargar un resumen Excel y
exportar el parte completo como XML. La documentación de interpretación describe
una base relacional en la que unas tablas tienen un registro por parte y otras
relaciones uno-a-muchos; una tabla puede faltar si el parte no contiene ese
capítulo. Por tanto, no debe transformarse el XML como si fuera una tabla plana
sin preservar la estructura y los nulos.

Los campos útiles previstos incluyen:

- número de parte/identificador;
- fechas y horas de inicio, detección, intervención y extinción;
- provincia, municipio de inicio y municipios afectados;
- lugar, comarca y referencias de localización;
- superficies forestal, arbolada, no arbolada y, según periodo, no forestal;
- causa, motivación, medios, daños y otros capítulos del parte;
- referencias espaciales disponibles en el modelo correspondiente.

El modelo actual codifica el número de parte con año, código provincial INE y
secuencia, pero esta regla no se aplicará retroactivamente sin comprobar los
valores históricos. Los identificadores visibles tienen forma como
`1990030079`, pero CV-3.2 debe verificar unicidad, ceros, renumeraciones y
posibles partes repetidos antes de derivar `fire_id`.

### Localización, CRS y precisión

Las instrucciones actuales describen `X`/`Y` UTM como punto de inicio y
registran datum y huso, además de hoja/cuadrícula del Mapa Militar 1:250.000.
Esa semántica no se puede proyectar automáticamente sobre los seis modelos de
parte históricos.

El [producto enlazado 1983–2015](https://datos.gob.es/es/catalogo/e05068001-estadistica-general-de-incendios-forestales)
describe coordenadas de origen y su ontología enumera ETRS89/UTM 27N–31N, pero
la propia [ontología oficial](https://datos.iepnb.es/def/sector-publico/medio-ambiente/incendios-forestales/index-es.html)
declara que las geometrías puntuales solo están validadas desde 2005. Resultado
para este proyecto:

1. una coordenada EGIF 1968–1992 es un atributo histórico pendiente de auditoría;
2. municipio o cuadrícula no equivalen a un punto exacto;
3. un punto, aunque resulte válido, nunca permite construir un perímetro;
4. el CRS debe conservarse por registro, incluido un estado `unknown`.

## Recuentos valencianos observados

| Año | Alicante | Castellón | Valencia | Total | GIF ≥500 ha |
|---:|---:|---:|---:|---:|---:|
| 1968 | 52 | 20 | 41 | 113 | 2 |
| 1969 | 21 | 30 | 22 | 73 | 2 |
| 1970 | 43 | 40 | 55 | 138 | 9 |
| 1971 | 18 | 25 | 37 | 80 | 2 |
| 1972 | 0 | 8 | 22 | 30 | 0 |
| 1973 | 26 | 39 | 85 | 150 | 1 |
| 1974 | 63 | 82 | 148 | 293 | 7 |
| 1975 | 50 | 66 | 140 | 256 | 3 |
| 1976 | 69 | 39 | 134 | 242 | 2 |
| 1977 | 48 | 30 | 121 | 199 | 5 |
| 1978 | 125 | 161 | 272 | 558 | 29 |
| 1979 | 96 | 167 | 0 | 263 | 22 |
| 1980 | 135 | 123 | 195 | 453 | 12 |
| 1981 | 237 | 169 | 301 | 707 | 15 |
| 1982 | 90 | 97 | 178 | 365 | 8 |
| 1983 | 105 | 147 | 242 | 494 | 3 |
| 1984 | 100 | 156 | 214 | 470 | 10 |
| 1985 | 99 | 162 | 262 | 523 | 8 |
| 1986 | 88 | 111 | 186 | 385 | 6 |
| 1987 | 137 | 83 | 186 | 406 | 2 |
| 1988 | 115 | 86 | 119 | 320 | 1 |
| 1989 | 115 | 104 | 173 | 392 | 0 |
| 1990 | 222 | 190 | 214 | 626 | 7 |
| 1991 | 259 | 252 | 358 | 869 | 15 |
| 1992 | 201 | 213 | 356 | 770 | 10 |
| **Total** | **2.514** | **2.600** | **4.061** | **9.175** | **181** |

GIF por provincia: Alicante 41, Castellón 61 y Valencia 79. Se usa el criterio
del proyecto **superficie declarada ≥500 ha**; no es superficie geométrica.

| Año | GIF Alicante | GIF Castellón | GIF Valencia | Total GIF |
|---:|---:|---:|---:|---:|
| 1968 | 1 | 0 | 1 | 2 |
| 1969 | 0 | 0 | 2 | 2 |
| 1970 | 4 | 0 | 5 | 9 |
| 1971 | 1 | 0 | 1 | 2 |
| 1972 | 0 | 0 | 0 | 0 |
| 1973 | 0 | 0 | 1 | 1 |
| 1974 | 0 | 2 | 5 | 7 |
| 1975 | 0 | 0 | 3 | 3 |
| 1976 | 1 | 1 | 0 | 2 |
| 1977 | 1 | 1 | 3 | 5 |
| 1978 | 4 | 10 | 15 | 29 |
| 1979 | 5 | 17 | 0 | 22 |
| 1980 | 8 | 1 | 3 | 12 |
| 1981 | 3 | 7 | 5 | 15 |
| 1982 | 0 | 4 | 4 | 8 |
| 1983 | 0 | 1 | 2 | 3 |
| 1984 | 0 | 6 | 4 | 10 |
| 1985 | 0 | 4 | 4 | 8 |
| 1986 | 3 | 1 | 2 | 6 |
| 1987 | 0 | 1 | 1 | 2 |
| 1988 | 0 | 0 | 1 | 1 |
| 1989 | 0 | 0 | 0 | 0 |
| 1990 | 4 | 0 | 3 | 7 |
| 1991 | 4 | 2 | 9 | 15 |
| 1992 | 2 | 3 | 5 | 10 |
| **Total** | **41** | **61** | **79** | **181** |

### Completitud todavía no cuantificada

| Métrica solicitada | Estado CV-3.1 | Razón / siguiente comprobación |
|---|---|---|
| Registros con/sin coordenadas | No medida | Exige revisar los campos de cada modelo y separar presencia, CRS conocido y punto validado. Para 1968–1992 hay **0 puntos respaldados por la declaración oficial “validados desde 2005”**, pero eso no significa que no existan valores originales. |
| Registros con municipio | No medida | El municipio puede ser desconocido/indeterminado aunque el campo exista; se contará sobre XML, sin inferirlo desde provincia. |
| Registros con superficie | No medida | Se distinguirá campo presente, valor numérico y superficie forestal total; el esquema cambia en 1989. |
| Duplicados e identificadores problemáticos | No medidos | Se conservarán todos los partes y se auditarán duplicados exactos, IDs repetidos y coincidencias de atributos sin deduplicar. |

## Grandes incendios prioritarios para CV-3.2

La siguiente lista procede del buscador EGIF y sirve para priorizar búsqueda
documental; **no afirma que exista un perímetro**:

| Parte | Fecha | Municipio mostrado | Provincia | Superficie declarada (ha) |
|---|---|---|---|---:|
| `1978463963` | 30/08/1978 | Indeterminado | Valencia | 13.100 |
| `1985464582` | 27/07/1985 | Tous | Valencia | 18.886 |
| `1991460176` | 28/07/1991 | Yátova | Valencia | 17.415 |
| `1990460094` | 24/07/1990 | Gestalgar | Valencia | 10.195 |
| `1990030079` | 25/07/1990 | Castell de Castells | Alicante | 6.800 |
| `1982124545` | 05/10/1982 | Indeterminado | Castellón | 3.870 |
| `1987121659` | 17/07/1987 | Altura | Castellón | 3.560 |
| `1984123603` | 23/09/1984 | Santa Magdalena de Pulpis | Castellón | 3.500 |
| `1992120403` | 30/08/1992 | Altura | Castellón | 3.310 |
| `1992030123` | 29/08/1992 | Tàrbena | Alicante | 2.260 |

Esta selección no sustituye la lista completa de 181 GIF. CV-3.2 debe además
buscar partes y cartografía por topónimos históricos, porque los incendios con
municipio `Indeterminado` no se pueden asignar correctamente por el texto
visible.

## Inventario de fuentes de perímetros históricos

La clasificación indica **qué podría aportar la fuente**, no asigna calidad a
un incendio concreto.

| Fuente oficial/documental | Cobertura encontrada | Qué aporta | Potencial A/B/C/D | Resultado |
|---|---|---|---|---|
| Servicio ICV de incendios | 1993–2024 | Perímetros vectoriales anuales y atributos asociados. | A | No cubre 1968–1992; confirma el corte actual en 1993. |
| Plan de prevención de Chera–Sot de Chera | Cartografía 1978–2004 | Mapa de terreno recorrido y recurrencia; años 1978, 1980, 1986, 1990 y 1992; superficies aproximadas. | C con el PDF; posible B si se recupera la cartografía anual fuente y su metodología | Es la pista pre-1993 más concreta. El PDF no es un vector de evento y no debe digitalizarse todavía. |
| Plan de prevención de Serra de Mariola | 1994–2003 | Análisis y cartografía histórica del parque. | Fuera del periodo | No demuestra perímetros de Mariola/Font Roja anteriores a 1993. Debe solicitarse el archivo previo a la Generalitat/gestión del parque. |
| Plan Estatal de Protección Civil ante incendios forestales | Mapas agregados 1983–1992 | Frecuencia e intensidad por hojas/cuadrículas 1:200.000. | D como localización agregada/contexto | No son perímetros de incendios individuales. |
| Mapa Forestal de España y mapas de cambios | Ediciones históricas/“foto fija” | Cambios de cubierta y áreas incendiadas según producto/edición. | Posible C tras contraste documental | Puede apoyar reconstrucciones, pero no demuestra por sí solo identidad, fecha exacta ni perímetro de un parte. |
| Archivos GOIIF / causas investigadas | Unidad formalizada en 1995; antecedentes 1991–1992 | Información documental y causal de casos investigados. | D; posible apoyo C si un expediente contiene cartografía | No se localizó una colección pública vectorial pre-1993. |
| Publicaciones EGIF anuales | 1968–1992 | Tablas, mapas agregados y contexto estadístico. | D | Sirven para validación de totales, no como perímetros de evento. |

El informe de Chera–Sot de Chera también relaciona dos grandes incendios:
18/05/1986 en Sot de Chera (877 ha) y 31/08/1992 en Sot de Chera
(1.092,20 ha). Son candidatos prioritarios para enlazar documentalmente con
EGIF, pero la tabla y el mapa de recurrencia no demuestran por sí solos qué
polígono corresponde a cada parte.

### Caso prioritario Mariola–Font Roja

No se ha localizado en esta revisión una fuente oficial pública con perímetros
pre-1993 de Serra de Mariola, Font Roja o su entorno. El plan de Serra de
Mariola accesible públicamente empieza en 1994. La ausencia de resultado no
demuestra que la cartografía no exista: justifica una solicitud dirigida al
Servicio de Prevención de Incendios Forestales, ICV y equipos gestores de los
parques, pidiendo inventarios, mapas originales, escala, método, CRS y permiso
de reutilización.

## Licencia y reutilización

El portal de datos abiertos MITECO permite usos comerciales y no comerciales,
incluidas copia, difusión, modificación, adaptación, extracción y combinación.
Exige no desnaturalizar la información, citar:

> Origen de los datos: Ministerio para la Transición Ecológica y el Reto
> Demográfico.

También exige conservar la fecha de actualización y los metadatos cuando
existan y no sugerir participación o respaldo ministerial. El dataset enlazado
1983–2015 figura además como **CC BY 4.0**.

Esto es base documental suficiente para una futura ingestión local y derivados
EGIF con atribución. CV-3.2 deberá guardar, por snapshot, la URL de consulta,
fecha de adquisición, condiciones aplicables y checksum. La licencia de cada
mapa o plan histórico debe auditarse por separado: que sea un documento público
no autoriza por sí solo a redistribuir una digitalización derivada.

## Diseño para el visor 1968–2026

La ampliación no debe fingir que todo el timeline tiene igual calidad espacial:

| Periodo | Entidad administrativa | Representación espacial | Mensaje de cobertura |
|---|---|---|---|
| 1968–1979 | Parte EGIF histórico, cobertura selectiva | Ninguna por defecto; punto/cuadrícula solo tras auditoría; perímetro solo de fuente independiente | “Serie histórica temprana; cobertura administrativa no exhaustiva.” |
| 1980–1991 | Parte EGIF histórico en transición | Igual que arriba | “Cobertura y esquema en transición; localización no homogénea.” |
| 1992 | Parte EGIF histórico más sistemático | Igual que arriba | “Recogida sistematizada; las geometrías puntuales históricas no están validadas por el producto enlazado.” |
| 1993–2024 | ICV consolidado | Perímetro ICV A separado del incendio | Cobertura cartográfica consolidada e informativa. |
| 2025–2026 | SIGIF + EFFIS | Punto administrativo provisional y perímetro satelital B, separados | Cobertura provisional y snapshot fechado. |

Campos nuevos recomendados para los futuros registros históricos:

```text
record_maturity       historical
collection_regime     early_selective | transition | systematic
schema_period         1968_1971 | 1972_1979 | 1980_1982 |
                      1983_1988 | 1989 | 1990_1997
location_type         none | municipality | sheet_grid | reported_point
coordinate_status     absent | raw_unverified | validated
coordinate_crs        nullable
coverage_note
```

La calidad A/B/C/D se asignará a una geometría, no al parte EGIF. Un incendio
sin perímetro se mantiene en `fires`; su ausencia geométrica se explica en la
interfaz. El histograma puede contar partes administrativos, pero la leyenda y
la ficha deben diferenciar “registros EGIF” de “perímetros disponibles”.

## Propuesta concreta para CV-3.2

1. Crear un descargador reproducible del XML EGIF para 1968–1992, con filtros
   explícitos de las tres provincias, snapshot, checksum, manifiesto y copia raw
   sin modificar.
2. Comparar el snapshot contra los 9.175 registros y los recuentos anuales de
   este informe; abortar si la exportación está truncada.
3. Inventariar los seis esquemas de parte antes de aplanar datos y documentar
   la correspondencia campo por campo.
4. Generar `fires` históricos separados de cualquier geometría, conservando
   XML/procedencia y una identidad provisional basada en el número de parte solo
   después de auditar su unicidad.
5. Cuantificar exactamente coordenadas, municipio, superficie, causas, GIF,
   duplicados e incoherencias por año y provincia. Auditar rango, datum, huso y
   semántica de cada localización; no reproyectar valores dudosos.
6. Cruzar totales con las publicaciones definitivas anuales y documentar
   diferencias, especialmente 1968–1979.
7. Solicitar a Generalitat/ICV y parques la cartografía fuente de Chera–Sot de
   Chera y Mariola–Font Roja, con escala, método, CRS y licencia. Investigar
   después los 181 GIF, empezando por los casos prioritarios de este informe.
8. No integrar el frontend hasta disponer de un informe de cobertura espacial
   por año que permita diseñar una leyenda honesta.

## Fuentes oficiales principales

- [EGIF / MITECO: buscador, publicaciones y documentación](https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-datos.html)
- [Buscador público EGIF](https://servicio.mapa.gob.es/incendios/Search/Publico)
- [Metodología de la Estadística General de Incendios Forestales](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/estad%C3%ADstica-iiff/Estad%C3%ADstica-General-IF-Metodolog%C3%ADa.pdf)
- [Conjunto enlazado EGIF 1983–2015](https://datos.gob.es/es/catalogo/e05068001-estadistica-general-de-incendios-forestales)
- [Ontología oficial de incendios forestales](https://datos.iepnb.es/def/sector-publico/medio-ambiente/incendios-forestales/index-es.html)
- [Condiciones de reutilización MITECO](https://www.datosabiertos.miteco.gob.es/es/aviso-legal.html)
- [Servicio ICV de prevención de incendios](https://carto.icv.gva.es/arcgis/rest/services/tm_medio_ambiente/prevencion_de_incendios/MapServer)
- [Análisis histórico de Chera–Sot de Chera](https://mediambient.gva.es/auto/prevencion-incendios/Red-espacios-protegidos/Chera-Sot%20de%20Chera/Documentacion%20en%20castellano/Plan%20de%20prevencion/01-Analisis_historico_incendios/Analisis_hist_informe.pdf)
- [Análisis histórico de Serra de Mariola](https://mediambient.gva.es/auto/prevencion-incendios/Red-espacios-protegidos/Serra%20Mariola/Documentacion%20en%20castellano/Plan%20de%20prevencion/01-Analisis_historico_incendios/Analisis_hist_informe.pdf)
- [Plan Estatal de Protección Civil ante incendios forestales](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/plan_estatal_tcm30-278888.pdf)
