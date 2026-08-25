# CV-4.2 — Auditoría y validación de ESFire30 anterior a 1993

Fecha de corte: **25/08/2026**

Ámbito de producción evaluado: Alicante, Castellón y Valencia, 1985–1992

Resultado operativo: **ESFire30 v1 puede clasificarse como
`B_DOCUMENTED_REMOTE_SENSING` con condiciones**. No se ha integrado ni
publicado ninguna geometría, ni se ha modificado el frontend o el perfil
público.

## Conclusión ejecutiva

El snapshot exacto [ESFire30 Causes v1](https://zenodo.org/records/18449006),
DOI `10.5281/zenodo.18449006`, contiene 119.498 polígonos anuales de la España
peninsular entre 1985 y 2021. La selección por intersección real con el límite
municipal oficial valenciano reproduce los **710** polígonos de CV-4.1: 195 en
Alicante, 206 en Castellón y 309 en Valencia.

La contradicción de CRS queda resuelta técnicamente. El README declara
EPSG:25830, pero los 37 `.prj` declaran ED50 / UTM 30N. Sobre 450 pares
diagnósticos ESFire30–ICV del mismo año, interpretar el SHP como EPSG:23030
vence en IoU en 448/450 pares y en distancia de centroides en 411/450. La
mediana de IoU pasa de 0,195 (hipótesis 25830) a 0,565 (23030), y la distancia
de centroides baja de 270 m a 80 m. Por tanto, las coordenadas almacenadas son
**EPSG:23030**; la mención EPSG:25830 del README es un error de metadatos.

Las 46.625 geometrías nacionales de 1985–1992 son estructural y
topológicamente válidas según Shapely/OGC. Las 710 valencianas son polígonos,
sin nulos, vacíos, áreas cero ni duplicados exactos; contienen 84.894 vértices.
La licencia CC BY 4.0 permite redistribuir y transformar el vector con
atribución e indicación de cambios.

La promoción a B no convierte ESFire30 en fuente oficial ni identifica
episodios físicos. El dataset no contiene fecha, municipio ni identificador
estable de evento. Sus causas ya incorporan EGIF mediante cuadrícula y
similitud/modelado; por ello no sirven como evidencia independiente para
confirmar enlaces. De los 180 partes EGIF GIF, 40 tienen algún candidato del
mismo año y cuadrícula: 3 fuertes, 34 posibles, 3 débiles, **0 confirmados**.

## 1. Snapshot reproducible

El descargador idempotente es:

```bash
python3 scripts/ingest/esfire30/download.py
```

La auditoría completa y el derivado diagnóstico ignorado se reproducen con:

```bash
python3 scripts/ingest/esfire30/audit.py --write-diagnostic
python3 scripts/ingest/esfire30/audit.py --write-diagnostic --check
```

| Propiedad | Valor |
|---|---|
| Registro | Zenodo 18449006 |
| DOI | `10.5281/zenodo.18449006` |
| Versión | v1 |
| Autores | Clara Ochoa, Emilio Chuvieco, Marcos Rodrigues, Magí Franquesa |
| Publicación / modificación | 01/02/2026 / 14/02/2026 |
| Adquisición | 25/08/2026 10:08:29 UTC |
| Licencia | CC BY 4.0 |
| ZIP | `ESFire30_Causes.zip`, 93.127.811 bytes |
| SHA-256 ZIP | `150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8` |
| MD5 proveedor | `0e196c9a3445261d8fc02f2c5b89f691` |
| README | 5.444 bytes; SHA-256 `f1de630a5b4eef2723aa7f8d9504e78b6c33bf2900868a0e7526a96da626f94d` |

El ZIP, el JSON original de Zenodo y la rejilla PROJ se guardan bajo
`data/raw/esfire30/`, ignorado por Git. La descarga usa temporales, validación
de tamaño/SHA-256 y sustitución atómica. Un snapshot ya válido se conserva
salvo `--force`.

## 2. Inventario completo

El ZIP contiene 37 shapefiles anuales, uno por año 1985–2021, con cinco
sidecars cada uno (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`): 185 miembros y
235.002.670 bytes sin comprimir. No contiene README, XML, fechas de incendio,
municipios, provincias ni identificador estable de evento. Los `.cpg` declaran
`ISO-8859-1`.

Existe un único esquema de **43 campos**. Los campos directamente relevantes
son `area_ha`, `Id_cuad`, `idcausa`, `Method`, `year`, `idcausa_ma` y
`predicted_`; los restantes contienen variables climáticas, vegetación,
cubiertas e interfaces territoriales usadas por el modelo. El esquema íntegro,
tipo DBF, longitud y decimales está en
`data/sources/esfire30_audit.json`.

| Año | Polígonos nacionales | Año | Polígonos nacionales |
|---:|---:|---:|---:|
| 1985 | 12.586 | 2004 | 3.084 |
| 1986 | 4.282 | 2005 | 2.840 |
| 1987 | 2.555 | 2006 | 1.796 |
| 1988 | 5.679 | 2007 | 1.656 |
| 1989 | 10.185 | 2008 | 1.325 |
| 1990 | 4.679 | 2009 | 2.075 |
| 1991 | 3.940 | 2010 | 1.224 |
| 1992 | 2.719 | 2011 | 2.021 |
| 1993 | 1.341 | 2012 | 2.105 |
| 1994 | 3.221 | 2013 | 2.247 |
| 1995 | 5.035 | 2014 | 2.093 |
| 1996 | 2.583 | 2015 | 1.812 |
| 1997 | 4.727 | 2016 | 1.704 |
| 1998 | 3.750 | 2017 | 3.082 |
| 1999 | 3.370 | 2018 | 858 |
| 2000 | 5.518 | 2019 | 1.834 |
| 2001 | 2.610 | 2020 | 1.548 |
| 2002 | 3.333 | 2021 | 1.744 |
| 2003 | 2.337 | **Total** | **119.498** |

El artículo asociado describe el producto base ESFire30 como 1985–2023; el
registro Zenodo y los ficheros v1 dicen y contienen 1985–2021. Para esta versión
la cobertura real auditable es 1985–2021. No se corrige ni oculta la
discrepancia.

## 3. Resolución del CRS

### Evidencias independientes

1. **`.prj`:** los 37 son idénticos y declaran `ED_1950_UTM_Zone_30N`, con
   datum European 1950, elipsoide International 1924, meridiano central −3°,
   falso este 500.000 m y unidades métricas. Corresponde a EPSG:23030.
2. **README:** declara EPSG:25830, sin explicar una transformación ni el origen
   de esa afirmación.
3. **Zenodo:** no contiene un CRS adicional que resuelva el conflicto.
4. **Coordenadas:** su rango es plausible para UTM 30N bajo ambos datums y no
   decide por sí solo.
5. **Código:** no se localizó repositorio o script público de creación.
6. **Control ICV:** el contraste pareado discrimina inequívocamente ambas
   hipótesis.

Los pares de validación requieren mismo año, candidato a ≤5 km, IoU máximo
≥0,20 bajo alguna hipótesis y razón de áreas geométricas entre 0,25 y 4. Son
**candidatos espaciales**, no identidades confirmadas.

| Métrica sobre 450 pares | EPSG:23030 | EPSG:25830 |
|---|---:|---:|
| IoU mediana / media | 0,565 / 0,547 | 0,195 / 0,244 |
| IoU ≥0,50 | 273 | 66 |
| IoU ≥0,25 | 434 | 184 |
| Distancia centroide mediana | 79,7 m | 269,5 m |
| Hausdorff mediana | 281,0 m | 379,6 m |
| Compatible con municipio | 438 | 430 |
| Incompatible con municipio | 8 | 16 |
| Victoria pareada por IoU | 448 | 2 |
| Victoria por menor distancia | 411 | 39 |

La diferencia entre hipótesis desplaza el centroide una mediana de 235,7 m.
El resultado no depende de un único incendio: ejemplos con IoU EPSG:23030
entre 0,85 y 0,91 aparecen en Enguera, la Vall de Gallinera, Rafelguaraf,
Benicolet, Beneixama, Carcaixent, Toga, Cortes de Pallás y Requena.

### Transformación diagnóstica

Se usaron pyproj 3.5.0 y PROJ 9.2.0 con la rejilla oficial IGN publicada por
PROJ:

- `es_ign_SPED2ETV2.tif`, 180.404 bytes;
- SHA-256 `61896f5d74bdc7c1d5850839ae743b08e19f9a627e8febb4ac93353ded835961`;
- operación ED50→ETRS89: `Inverse of UTM zone 30N + ED50 to ETRS89 (12) +
  UTM zone 30N`, precisión declarada 0,2 m;
- operación ED50→WGS84: `Inverse of UTM zone 30N + ED50 to WGS 84 (41) +
  axis order change (2D)`, precisión declarada 1 m.

Estas son precisiones declaradas de la transformación geodésica, **no** de los
perímetros Landsat. La futura producción debe fijar rejilla, checksum,
versiones y operación, y conservar siempre la geometría original EPSG:23030.

## 4. Topología 1985–1992

Auditoría nacional, sin reparar:

| Propiedad | Resultado |
|---|---:|
| Geometrías | 46.625 |
| Polygon / MultiPolygon | 46.531 / 94 |
| Nulas / vacías / área cero | 0 / 0 / 0 |
| Inválidas OGC | 0 |
| Anillos no cerrados | 0 |
| Geometrías con huecos / huecos | 5.037 / 14.889 |
| Anillos / vértices | 61.733 / 2.549.540 |
| Grupos geométricos duplicados | 0 |
| Duplicados multianuales | 0 |

Para los 710 polígonos valencianos: 710 Polygon, 0 MultiPolygon, 0 inválidos,
146 con huecos, 1.348 huecos, 84.894 vértices y 710 checksums geométricos
distintos. No se ha ejecutado ninguna reparación.

## 5. Distribución valenciana 1985–1992

La provincia primaria es la de mayor área de intersección con el límite
oficial. Hay 29 polígonos que cruzan más de una provincia. Las áreas siguientes
son las del polígono completo, no áreas recortadas al País Valencià.

| Año | Alicante | Castellón | Valencia | Total |
|---:|---:|---:|---:|---:|
| 1985 | 13 | 52 | 62 | 127 |
| 1986 | 16 | 18 | 29 | 63 |
| 1987 | 3 | 7 | 9 | 19 |
| 1988 | 9 | 5 | 11 | 25 |
| 1989 | 13 | 4 | 6 | 23 |
| 1990 | 52 | 21 | 27 | 100 |
| 1991 | 46 | 38 | 87 | 171 |
| 1992 | 43 | 61 | 78 | 182 |
| **Total** | **195** | **206** | **309** | **710** |

Suma cartografiada: **127.083,78 ha**. Distribución de `area_ha`: mínimo 5,04;
p25 8,19; mediana 16,11; p75 51,57; p95 483,38; máximo 13.663,08; media
178,99 ha. Hay 36 polígonos ≥500 ha y 674 <500 ha. Se denominan “perímetros
ESFire30 ≥500 ha”, no GIF, porque su área es satelital y no una clasificación
administrativa.

El área del atributo y la geométrica en EPSG:23030 concuerdan hasta el redondeo
(diferencia relativa mediana `0,000004`).

## 6. Metodología y calidad

Fuentes primarias consultadas:

- Zenodo, *ESFire30 Causes*, descripción, ficheros, derechos y metadatos:
  <https://zenodo.org/records/18449006>.
- Ochoa et al., *Inferring Wildfire Ignition Causes in Spain Using Machine
  Learning and Explainable AI*, secciones 2.2, 2.3, 5 y Data Availability:
  <https://doi.org/10.3390/fire9040138>.
- catálogo de rejillas PROJ/IGN:
  <https://cdn.proj.org/>.

La documentación caracteriza ESFire30 como polígonos de área quemada de la
España peninsular, derivados de Landsat a resolución nativa de 30 m, umbral
nominal >5 ha, algoritmo semiautomático y refinamiento posterior. No identifica
en v1 la escena/sensor concreto por feature ni aporta fecha individual. El
README contiene además la errata “30 km”; el artículo respalda 30 m.

El producto de causas añade EGIF de este modo:

- `Method=1`: similitud de superficie dentro de la cuadrícula EGIF, con umbral
  descrito de ±10 ha;
- `Method=2`: causa predominante en la cuadrícula;
- `predicted_`: clasificación Random Forest.

El artículo de causas documenta el proceso de integración y sus limitaciones,
pero el artículo primario del producto geométrico base ESFire30 figura todavía
como *under review* y no está incluido en Zenodo. La validación ICV de esta
auditoría aporta una caracterización empírica valenciana, no sustituye una
validación oficial homogénea.

### Decisión de calidad

La categoría `B_DOCUMENTED_REMOTE_SENSING` está justificada porque existe
procedencia Landsat, resolución, método, umbral y licencia documentados; el CRS
se ha resuelto con el `.prj` y un control independiente amplio; y la topología
es utilizable. Condiciones:

1. presentar siempre la fuente como teledetección, nunca como oficial;
2. no afirmar `1 polígono = 1 incendio físico`;
3. conservar el original EPSG:23030, IDs internos y provenance;
4. atribuir Zenodo/DOI y declarar reproyección, selección y simplificación;
5. mantener EGIF separado y cualquier relación como candidata;
6. solicitar al proveedor la corrección escrita del README y el artículo base;
7. si una versión futura introduce inválidas, no repararlas silenciosamente.

## 7. Identidad interna

ESFire30 v1 no publica un ID estable de evento o geometría. `Id_cuad` se repite
y representa la cuadrícula usada en el cruce de causas; `year` tampoco es
único. Se propone, solo para el snapshot v1:

- `source_record_id = esfire30:v1:<year>:<índice cero SHP/DBF>`;
- `geometry_id = esfire30:geometry:v1:<year>:<índice>:<16 caracteres SHA-256>`;
- `episode_identity_status = unresolved_polygon_event_claim_not_verified`.

El índice preserva trazabilidad dentro de v1, pero no es un identificador
publicado por el proveedor. Ni polígonos próximos, ni manchas múltiples, ni
escenas repetidas se fusionan sin documentación.

## 8. Validación ICV 1993–2021

Se cargaron los perímetros ICV oficiales normalizados de los años coincidentes
y se seleccionaron 450 pares diagnósticos según la regla de la sección 3.
Además de resolver el datum, el resultado permite una primera caracterización:
IoU mediana 0,565, p25 0,410, p75 0,683 y p95 0,826; distancia de centroides
mediana 80 m y Hausdorff mediana 281 m.

No debe interpretarse como precisión absoluta uniforme. ESFire30 no aporta
fecha/municipio/ID y la precisión ICV cambia históricamente. No se confirma la
identidad de ningún par; todos quedan
`diagnostic_spatial_candidate_not_confirmed`.

## 9. Relación diagnóstica con EGIF 1985–1992

Se mantienen separadas la geometría ESFire30 y el parte administrativo EGIF.
El matcher usa año, `Id_cuad`, provincia/municipio como controles y diferencia
relativa de superficies como métrica; no usa ±10 ha como regla rígida. Como el
propio `Id_cuad` de ESFire30 procede del enlace con EGIF, no es evidencia
independiente y nunca produce `confirmed`.

| Universo / estado | Partes |
|---|---:|
| Partes EGIF 1985–1992 | 4.291 |
| Partes EGIF GIF 1968–1992 | 180 |
| Con candidato mismo año + cuadrícula | 40 |
| `strong` | 3 |
| `possible` | 34 |
| `weak` | 3 |
| `none` | 140 |
| `confirmed` | **0** |

En los 40 mejores candidatos, la diferencia relativa de superficie tiene
mediana 0,583, p25 0,175 y p75 0,978. Esto demuestra que una ventana absoluta
de ±10 ha no es apropiada como regla de identidad del Atlas.

Casos de control:

- Sot de Chera, 18/05/1986: 877 ha EGIF y 821,07 ha ESFire30, candidato fuerte;
- Yátova 1991: 17.415 ha EGIF y 13.379,04 ha ESFire30, candidato fuerte;
- Chiva 1991: 3.654 ha EGIF y 3.201,93 ha ESFire30, candidato fuerte;
- Sot de Chera, 31/08/1992: 1.092,6 ha EGIF frente a un candidato de 6,66 ha;
  posible por cuadrícula, no representación fiable del episodio completo;
- Marines–Altura 1992: los candidatos son pequeñas manchas, no resuelven el
  episodio multiparte; Marines queda posible y el parte sin municipio débil;
- Altura 1992: candidato de 60,57 ha frente a 3.310 ha; posible, no confirmado.

## 10. Derivado diagnóstico

Al cumplirse CRS, topología, metodología y licencia, se generó localmente:

`data/processed/esfire30/gva/esfire30_1985_1992_diagnostic.jsonl`

Contiene 710 registros, 7.400.024 bytes, SHA-256
`548c5cfffdc7fe6953446a9c0b396aceed91ec76e6d5b0ddf82f73f2ceb2a6fe`.
Cada registro conserva geometría original EPSG:23030 y geometría derivada
EPSG:4326, checksum, provenance, calidad B e identidad de episodio no resuelta.
Está ignorado, no forma parte del frontend ni del bundle público.

## 11. Licencia

Zenodo declara **CC BY 4.0** para ESFire30 Causes. Permite compartir y adaptar,
incluidos derivados reproyectados, seleccionados o simplificados, con
atribución, enlace a la licencia e indicación de cambios. La licencia del
vector no relicencia las escenas Landsat; el Atlas no necesita redistribuir
esas imágenes para publicar el derivado vectorial.

Texto propuesto:

> ESFire30 Causes, Ochoa, Chuvieco, Rodrigues y Franquesa (2026), versión v1,
> CC BY 4.0, DOI 10.5281/zenodo.18449006. Datos transformados para el Atlas
> mediante selección territorial, reproyección a EPSG:4326, selección de
> atributos y, cuando proceda, simplificación geométrica.

No se añade todavía ESFire30 a `config/sources-gva.json` ni al perfil público.

## 12. Coste web futuro

Un GeoJSON mínimo, EPSG:4326, no simplificado, mide 3.598.903 bytes y 1.378.468
bytes gzip. Contiene 84.894 vértices. La simplificación diagnóstica preservando
topología produce:

| Tolerancia en CRS métrico | Vértices | Reducción | Colapsadas |
|---:|---:|---:|---:|
| 10 m | 84.894 | 0,0 % | 0 |
| 30 m | 45.670 | 46,2 % | 0 |
| 60 m | 27.849 | 67,2 % | 0 |

No se recomienda aún tolerancia de producción: CV-4.3 debe medir error de área
y comportamiento de incendios pequeños. Incluso sin simplificar, 710
polígonos y menos de 100.000 vértices son compatibles con carga diferida en
Leaflet+Canvas; no justifican PMTiles.

## 13. Solicitudes externas pendientes

`CV_4_2_CONTACT_PACKET.md` deja preparados, sin enviar, mensajes para:

- autores ESFire30: confirmar EPSG:23030/corregir README, semántica de feature,
  disponibilidad del paper base y estabilidad de IDs;
- Generalitat: recuperar la cartografía oficial anual Valencia 1978–1992;
- M. Pilar Martín/CSIC: inventario y capas NOAA-AVHRR históricas;
- autores/custodios Hoya de Buñol: vectores Landsat de 1991;
- Generalitat/municipios: cartografía fuente Chera–Sot de Chera.

## 14. Recomendación para CV-4.3

Preparar una integración local reversible de ESFire30 1985–1992 como fuente B
independiente, no como geometría EGIF. Antes de tocar producción:

1. obtener, si es posible, confirmación escrita del CRS y semántica;
2. crear normalizado separado con original EPSG:23030 y derivado EPSG:4326;
3. validar simplificación local/regional/overview y áreas pequeñas;
4. construir manifest con atribución CC BY 4.0 y `publishable` fail-closed;
5. diseñar simbología inequívoca de teledetección histórica;
6. mantener EGIF sin geometría principal y exponer enlaces solo como
   candidatos revisables;
7. validar que Historia de un lugar distinga perímetro satelital histórico de
   incendio administrativo y no lo convierta en recurrencia confirmada.

Hasta esa revisión, el visor público 1968–2026 permanece intacto.
