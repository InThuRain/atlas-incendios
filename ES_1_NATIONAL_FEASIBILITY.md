# ES-1 — Viabilidad y arquitectura del Atlas de Incendios de España

Fecha de corte: **26/08/2026**

Estado: investigación, inventario y benchmarks diagnósticos. No se ha
modificado el visor del País Valencià, no se ha construido el visor nacional y
no se ha publicado ningún activo nuevo.

## 1. Conclusión ejecutiva

La viabilidad global es **alta, condicionada a una evolución de la entrega
cartográfica**.

Hay dos bases nacionales reutilizables y ya comprendidas:

- EGIF aporta el registro administrativo nacional desde 1968. El buscador
  público devolvió **646.887 partes** para 1968–2025, todos ellos realmente en
  1968–2023; 2024 y 2025 devolvieron cero. EGIF sigue siendo registro
  administrativo, no geometría ni identidad inequívoca de episodio.
- ESFire30 v1 aporta **119.498 polígonos** homogéneos de teledetección Landsat
  para la España peninsular, 1985–2021, con licencia CC BY 4.0. No es una
  cartografía oficial ni equivale a EGIF.

El modelo de datos valenciano —registros, geometrías, relaciones candidatas,
procedencia y perfiles de publicación separados— sí escala. Lo que **no
escala como vista inicial nacional** es descargar y materializar todos los
polígonos como un único `L.geoJSON`: el overview mínimo medido ocupa 71,44 MB
raw / 22,92 MB gzip y añade unos **459 MiB de heap** al representar 119.498
features. Leaflet + Canvas sigue siendo razonable para una comunidad, una
provincia, un año o una selección de hasta aproximadamente 10–15 mil
geometrías; 46.625 ya añaden 192 MiB y resultan fronterizas para móvil.

Por ello ES-v1 debe ser híbrida:

1. registros y estadísticas en JSON compacto particionado;
2. geometrías nacionales overview mediante teselas vectoriales/PMTiles en un
   prototipo aislado antes de elegir renderer;
3. GeoJSON LOD por territorio para detalle regional/local mientras las medidas
   lo permitan;
4. fuentes autonómicas independientes, sin sustituir ni fusionar EGIF o
   ESFire30;
5. País Valencià conservado como primer territorio implementado y como prueba
   de compatibilidad.

## 2. Método y reproducibilidad

Se han usado exclusivamente consultas ligeras, snapshots ya auditados y
catálogos oficiales. No se descargó el XML EGIF nacional ni se generaron
assets nacionales de producción.

Comandos diagnósticos:

```bash
python3 scripts/audit/spain/es1_national_feasibility.py egif-counts \
  --year-from 1968 --year-to 2025 \
  --output data/derived/spain/es1/egif-counts.json

python3 scripts/audit/spain/es1_national_feasibility.py esfire30 \
  --write-overview data/derived/spain/es1/esfire30-overview.geojson \
  --output data/derived/spain/es1/esfire30-metrics.json

python3 scripts/audit/spain/es1_national_feasibility.py esfire30-territories \
  --ccaa /ruta/al/geojson/oficial/ign-ccaa.json \
  --provinces /ruta/al/geojson/oficial/ign-provincias.json \
  --output data/derived/spain/es1/esfire30-territories.json

python3 benchmarks/spain_es1/run_leaflet_benchmark.py \
  --output data/derived/spain/es1/leaflet-desktop.json
python3 benchmarks/spain_es1/run_leaflet_benchmark.py --mobile \
  --output data/derived/spain/es1/leaflet-mobile.json
```

`data/derived/spain/es1/` está ignorado. Los resultados sintéticos necesarios
para revisar ES-1 sí se conservan en los dos inventarios versionables.

Fuentes primarias principales:

- [buscador público EGIF](https://servicio.mapa.gob.es/incendios/Search/Publico),
  versión observada 2.32.0;
- [estadística oficial de incendios MITECO](https://www.miteco.gob.es/es/biodiversidad/temas/incendios-forestales/estadisticas-incendios.html);
- [metodología oficial EGIF](https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/incendios-forestales/estad%C3%ADstica-iiff/Estad%C3%ADstica-General-IF-Metodolog%C3%ADa.pdf);
- [ESFire30 Causes v1](https://zenodo.org/records/18449006), DOI
  `10.5281/zenodo.18449006`;
- [unidades administrativas IGN/CNIG](https://api-features.ign.es/collections/administrativeunit);
- [relaciones y códigos municipales INE](https://www.ine.es/daco/daco42/codmun/codmun_anual.htm).

## 3. EGIF nacional

### 3.1 Cobertura y volumen observado

El Área de Defensa contra Incendios Forestales de MITECO mantiene EGIF a partir
de los partes remitidos por las comunidades autónomas. La operación comenzó en
1968 y el formulario actual supera los 150 campos. El buscador permite filtrar
por CCAA, provincia, municipio, causa y otros capítulos y exportar el XML PIF
en bloques de **10.000 a 50.000** registros.

El 26/08/2026 se consultó cada año y el intervalo completo. La suma anual y el
resultado 1968–2025 coinciden exactamente en **646.887**:

| Año | Partes | Año | Partes | Año | Partes | Año | Partes |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1968 | 2.038 | 1983 | 4.736 | 1998 | 22.003 | 2013 | 10.797 |
| 1969 | 1.442 | 1984 | 7.073 | 1999 | 17.943 | 2014 | 9.806 |
| 1970 | 3.155 | 1985 | 12.235 | 2000 | 23.574 | 2015 | 11.810 |
| 1971 | 1.665 | 1986 | 7.514 | 2001 | 19.099 | 2016 | 8.749 |
| 1972 | 2.093 | 1987 | 8.816 | 2002 | 19.929 | 2017 | 13.691 |
| 1973 | 3.724 | 1988 | 9.440 | 2003 | 18.616 | 2018 | 7.064 |
| 1974 | 3.920 | 1989 | 20.250 | 2004 | 21.396 | 2019 | 10.826 |
| 1975 | 4.128 | 1990 | 12.914 | 2005 | 25.492 | 2020 | 8.064 |
| 1976 | 4.356 | 1991 | 13.529 | 2006 | 16.334 | 2021 | 8.206 |
| 1977 | 2.064 | 1992 | 15.956 | 2007 | 10.936 | 2022 | 8.433 |
| 1978 | 8.193 | 1993 | 14.253 | 2008 | 11.655 | 2023 | 5.223 |
| 1979 | 6.189 | 1994 | 19.249 | 2009 | 15.643 | 2024 | 0 |
| 1980 | 7.075 | 1995 | 25.557 | 2010 | 11.721 | 2025 | 0 |
| 1981 | 10.688 | 1996 | 16.586 | 2011 | 16.414 |  |  |
| 1982 | 6.308 | 1997 | 22.320 | 2012 | 15.997 |  |  |

Agregados: 42.967 partes en 1968–1979; 120.578 en 1980–1991; 179.501
en 1968–1992; 467.386 en 1993–2023.

La interfaz técnica expone registros hasta 2023. La página de publicaciones
definitivas enlaza en este momento informes anuales hasta 2021. Por rigor:

- **2021** es el último año cuya publicación definitiva se ha comprobado;
- **2022–2023** existen en el buscador, pero ES-1 no los etiqueta como
  definitivos sin otra evidencia;
- cero filas en 2024–2025 significa “no disponibles en este snapshot del
  buscador”, nunca “no hubo incendios”.

### 3.2 Reutilización del pipeline valenciano

La cadena `search → XML snapshot → schema inventory → normalized records →
web records` es reutilizable. Deben generalizarse:

- configuración de CCAA/provincias fuera del código;
- descarga en al menos 13 bloques de 50.000, con recuentos antes y después;
- seis modelos históricos ya identificados para 1968–1992 y los modelos
  posteriores, sin forzar campos ausentes;
- diccionarios de municipios y causas versionados por época;
- anomalías por territorio, porque la calidad valenciana no demuestra la del
  resto de España.

El identificador seguirá describiendo el parte fuente, no un episodio físico.
`egif-record:<NumeroParte>` puede conservarse cuando sea válido y único; los
casos ambiguos necesitan ID reproducible de registro e
`episode_identity_status=unresolved`.

### 3.3 Tamaños de planificación

Extrapolando por registro desde el pipeline valenciano 1968–1992 —estimación,
no snapshot nacional—:

| Etapa EGIF 1968–2023 | Estimación |
|---|---:|
| XML sin comprimir | ~3,5 GiB |
| ZIP raw | ~151 MiB |
| JSONL normalizado con atributos originales | ~3,8 GiB |
| JSON web mínimo | ~158 MiB |
| JSON web mínimo gzip | ~8,5 MiB |

La geometría sigue siendo `null` salvo que una fuente independiente aporte
una geometría. El coste web puede mantenerse bajo si el navegador recibe solo
agregados iniciales y bloques de registros cuando el usuario los necesita.

### 3.4 Licencia

Las [condiciones generales de reutilización de MITECO](https://www.datosabiertos.miteco.gob.es/es/aviso-legal.html)
permiten copia, difusión, modificación, adaptación y combinación, con
atribución, fecha de actualización cuando exista, conservación de metadatos y
sin sugerir respaldo oficial. Fórmula ya auditada:

> Origen de los datos: Ministerio para la Transición Ecológica y el Reto
> Demográfico.

## 4. ESFire30 nacional

### 4.1 Snapshot completo

Se midió el ZIP exacto ya auditado:

- v1, 1985–2021, España peninsular;
- 119.498 geometrías: 119.249 Polygon y 249 MultiPolygon;
- 6.196.709 vértices originales;
- 5.174.076,69 ha de superficie cartografiada declarada;
- 93.127.811 bytes de ZIP;
- SHA-256
  `150a3cc95e9681e0d35204063abb00437f9cbeca7205e6208518054b3fd36cc8`;
- EPSG:23030 real, transformado diagnósticamente con la operación IGN/PROJ
  `ED50 to WGS 84 (41)` y su rejilla fijada por checksum.

| Periodo | Polígonos | Periodo | Polígonos |
|---|---:|---|---:|
| 1985 | 12.586 | 1994 | 3.221 |
| 1986 | 4.282 | 1995 | 5.035 |
| 1987 | 2.555 | 1996 | 2.583 |
| 1988 | 5.679 | 1997 | 4.727 |
| 1989 | 10.185 | 1998 | 3.750 |
| 1990 | 4.679 | 1999 | 3.370 |
| 1991 | 3.940 | 2000–2009 | 26.574 |
| 1992 | 2.719 | 2010–2019 | 18.980 |
| 1993 | 1.341 | 2020–2021 | 3.292 |

### 4.2 Distribución territorial diagnóstica

Se intersectó el snapshot con las unidades administrativas oficiales del
IGN/CNIG. La asignación primaria usa la mayor área de intersección solo para
contar; no recorta el polígono ni establece procedencia administrativa.

| CCAA peninsular | Polígonos primarios | CCAA peninsular | Polígonos primarios |
|---|---:|---|---:|
| Andalucía | 7.676 | Comunitat Valenciana | 2.189 |
| Aragón | 1.751 | Extremadura | 8.157 |
| Asturias | 13.664 | Galicia | 38.358 |
| Cantabria | 6.019 | Madrid | 859 |
| Castilla y León | 29.324 | Murcia | 180 |
| Castilla-La Mancha | 4.639 | Navarra | 1.273 |
| Cataluña | 3.091 | País Vasco | 1.751 |
| La Rioja | 567 | **Total** | **119.498** |

Hay **1.342** polígonos que intersectan más de una CCAA y **2.364** que
intersectan más de una provincia. Ninguno quedó fuera de las unidades
peninsulares cargadas. Esto invalida un diseño que copie o recorte cada
feature por territorio sin conservar una geometría fuente única.

Con cinco bloques temporales se obtienen 75 particiones CCAA×bloque o 235
provincia×bloque. Las mayores particiones CCAA son Galicia 1985–1989 (12.732),
Galicia 1990–1999 (11.973) y Castilla y León 1990–1999 (10.114).

### 4.3 LOD y tamaños

Las tolerancias son diagnósticas y preservan topología. No son todavía una
decisión nacional de producción.

| LOD | Tolerancia | Vértices | Reducción | Raw | gzip | Colapsadas |
|---|---:|---:|---:|---:|---:|---:|
| local | 0 m | 6.196.709 | 0 % | 264,38 MB | 99,23 MB | 0 |
| regional | 30 m | 3.119.389 | 49,66 % | 143,47 MB | 52,03 MB | 0 |
| overview | 100 m | 1.287.275 | 79,23 % | 71,44 MB | 22,92 MB | 0 |

ESFire30 puede ser una **columna vertebral espacial homogénea secundaria** de
1985–2021: ofrece método, licencia y cobertura peninsular comunes. No puede
ser la geometría oficial nacional por defecto porque:

- es teledetección científica, no inventario administrativo;
- el umbral nominal es >5 ha;
- feature no equivale necesariamente a episodio;
- difiere de fuentes autonómicas oficiales;
- no cubre islas ni 2022+.

Una geometría oficial autonómica puede ser preferente en una vista, pero
ESFire30 debe seguir accesible como observación independiente.

## 5. Rendimiento cartográfico

Benchmark local en Chrome headless, Leaflet 1.9.4, Canvas, sin teselas de
base. Desktop son dos repeticiones; móvil es una repetición con viewport
390×844, no una emulación de CPU lenta. Los tiempos de red son loopback y no
predicen Internet; gzip indica la transferencia HTTP esperable.

| Escenario | Features | raw / gzip | Parse desktop | Render desktop | Heap desktop | Render viewport móvil | Heap móvil |
|---|---:|---:|---:|---:|---:|---:|---:|
| España overview completo | 119.498 | 71,44 / 22,92 MB | 202 ms | 836 ms | 459 MiB | 828 ms | 469 MiB |
| Un año: 1985 | 12.586 | 8,46 / 2,78 MB | 27 ms | 120 ms | 58 MiB | 102 ms | 58 MiB |
| 1985–1992 | 46.625 | 28,79 / 9,30 MB | 87 ms | 316 ms | 183 MiB | 363 ms | 183 MiB |
| País Valencià 1985–1992 | 710 | 1,87 / 0,42 MB | 9 ms | 27 ms | 12 MiB | 30 ms | 12 MiB |

Conclusiones:

- **Leaflet + GeoJSON sí** para provincia, CCAA y selecciones temporales
  contenidas. Es particularmente seguro por debajo de unas 10–15 mil
  geometrías overview en este equipo.
- **Leaflet + un GeoJSON nacional completo no** como carga inicial: 459–469
  MiB adicionales son una regresión seria aunque el render bruto tarde menos
  de un segundo en este ordenador.
- 46.625 geometrías/183 MiB ya son un caso límite para móvil; el periodo
  completo no debe materializarse simultáneamente.

### Comparación con vector tiles / PMTiles

No se produjo un PMTiles nacional en ES-1, para no introducir arquitectura de
producción antes del prototipo. La comparación técnica es suficiente para
decidir el siguiente experimento:

| Aspecto | GeoJSON particionado | Vector tiles / PMTiles |
|---|---|---|
| Descarga | archivo completo de la partición | rangos/teselas visibles |
| Parse/memoria | crea todos los objetos GeoJSON/Leaflet | decodifica teselas necesarias |
| Identidad | directa por feature | exige IDs estables entre teselas/LOD |
| Intersecciones fronterizas | relación y ownership explícitos | fragmentos por tesela, geometría fuente externa intacta |
| Hosting | trivial en Pages | estático; PMTiles requiere HTTP Range correcto |
| Actualización | sustituir particiones | reconstruir archivo/teselas versionados |

[PMTiles](https://docs.protomaps.com/pmtiles/) permite recuperar mediante
HTTP Range solo directorios y tiles necesarios, y puede servirse desde
almacenamiento estático compatible. Esto ataca exactamente el problema
medido, pero su tamaño, peticiones, selección y renderer deben compararse en
ES-3. No se decide todavía MapLibre ni se modifica Leaflet.

## 6. Particionado recomendado

No conviene repetir literalmente provincia×bloque de GVA a escala nacional.

### Registros sin geometría

`source × CCAA × bloque temporal` es el nivel normal. Para listados locales se
puede añadir un índice provincia/municipio. EGIF se descarga y normaliza una
vez; sus relaciones territoriales no requieren geometría inventada.

### Geometrías

1. conservar una sola geometría fuente por `geometry_id`;
2. guardar relaciones N:M `geometry_id ↔ territory_id`, con área de
   intersección y relación primaria solo como ayuda de particionado;
3. no recortar la geometría normalizada por CCAA/provincia;
4. overview nacional: teselas vectoriales por fuente y bloque temporal;
5. regional/local: GeoJSON CCAA×bloque o provincia×bloque mientras cada
   partición cumpla presupuesto de bytes/features/heap;
6. si una feature cruza límites, el índice permite localizarla desde todos los
   territorios sin crear nuevas identidades. La tesela puede contener
   fragmentos de render, pero el popup conserva el mismo `geometry_id`.

Bloques recomendados iniciales, siempre declarados en manifest y ajustables
por fuente: 1968–1979, 1980–1989, 1990–1999, 2000–2009, 2010–2019 y 2020+.
ESFire30 comienza en 1985; un bloque vacío no se publica.

## 7. Modelo territorial nacional

Jerarquía genérica:

```text
country:ES
└── autonomous_community:<INE code>
    └── province:<INE code>
        └── municipality:<five-digit INE code>
```

- **INE**: autoridad para códigos y denominaciones de CCAA, provincias y
  municipios. Deben guardarse catálogos anuales y el dígito de control por
  separado cuando proceda.
- **IGN/CNIG**: geometrías oficiales y bounds, versionados por fecha. Su
  licencia general de descarga es CC BY 4.0 con reconocimiento de origen y
  propiedad.
- `territory_id` no incorpora el nombre visible; así soporta nombres
  bilingües y cambios de denominación.
- Ceuta y Melilla se modelan como ciudades autónomas con capacidad equivalente
  a CCAA y provincia, sin excepciones repartidas por la UI.

Los componentes futuros usan `territory`, `territory_level` y `parent_id`, no
`gva`. País Valencià conserva sus labels propios solo en configuración de
territorio.

## 8. Normalización municipal nacional

Modelo:

```text
municipality_raw
source_municipality_code
municipality_id              # código INE válido para una fecha/catálogo
municipality_name
municipality_resolution      # exact_code | documented_historical | unresolved
municipality_catalog_version
```

Reglas:

1. resolver por código oficial y provincia en la fecha del parte;
2. usar tablas INE anuales y cambios documentados para altas, bajas, fusiones,
   segregaciones y nombres;
3. mantener municipios históricos como entidades con intervalo de vigencia;
4. una relación documentada `successor/predecessor` no reescribe el registro;
5. aliases bilingües son etiquetas, no nuevas identidades;
6. similitud textual solo genera candidatos de revisión, nunca resolución.

El muestreo valenciano demuestra que la disponibilidad varía por modelo:
5.254/9.175 partes pre-1993 tenían municipio resoluble. No se extrapola esa
proporción como cobertura nacional; ES-4 deberá cuantificarla por provincia y
periodo.

## 9. Ontología nacional de causas

Tres capas separadas:

```text
source_cause_code + source_cause_label
                 ↓ mapping versionado, con evidencia
canonical_cause_code
                 ↓ locale
display_label
```

La ontología superior propuesta conserva categorías amplias ya seguras:
`lightning`, `intentional`, `negligence`, `accidental`, `rekindle`,
`other_known`, `unknown`, `under_investigation`. `negligence` y `accidental`
no se fusionan cuando el esquema fuente los distingue. Los subcódigos EGIF
permanecen disponibles para análisis y cada mapping declara:

- fuente y modelo/periodo;
- código original;
- categoría canónica o `unmapped`;
- fundamento documental;
- versión de mapping.

No se deduce una causa ESFire30 como si fuera administrativa: sus campos de
causa/modelo tienen procedencia y método propios y, en parte, derivan de EGIF.

## 10. Primer inventario autonómico oficial

La clasificación describe **preparación de fuente**, no calidad A/B de cada
geometría. “No encontrada” significa únicamente que no apareció en los
catálogos oficiales revisados en ES-1.

| Territorio | Estado | Hallazgo |
|---|---|---|
| Andalucía | A_READY | REDIAM WMS/WFS de perímetros 2008–2025 |
| Aragón | D_NOT_FOUND | plan 2025–2028 anuncia producción vectorial; activo no localizado |
| Asturias | D_NOT_FOUND | no localizado en catálogo oficial revisado |
| Illes Balears | D_NOT_FOUND | riesgo de incendio, no serie de perímetros |
| Canarias | D_NOT_FOUND | riesgo/ortofoto postincendio, no serie regional localizada |
| Cantabria | D_NOT_FOUND | no localizado |
| Castilla y León | B_AVAILABLE_NEEDS_WORK | WMS oficial “Incendios CyL”; contenido/descarga por auditar |
| Castilla-La Mancha | C_CARTOGRAPHY_ONLY | información y planes, sin vector individual localizado |
| Cataluña | A_READY | base cartográfica oficial 1986–2021, SHP/KMZ |
| Comunitat Valenciana | A_READY | ICV/Generalitat 1993–2024, ya auditado |
| Extremadura | D_NOT_FOUND | no localizado |
| Galicia | D_NOT_FOUND | geoportal y prevención, sin serie individual localizada |
| Madrid | D_NOT_FOUND | estadísticas, no vector de perímetros |
| Murcia | D_NOT_FOUND | no localizado |
| Navarra | A_READY | WMS/WFS 1985–2018 y 2019–2023 |
| País Vasco | D_NOT_FOUND | estadísticas/riesgo, sin vector localizado |
| La Rioja | C_CARTOGRAPHY_ONLY | mapa de riesgo PLATERCAR, no perímetros individuales |
| Ceuta | D_NOT_FOUND | no localizado |
| Melilla | D_NOT_FOUND | no localizado |

Resumen: 4 `A_READY`, 1 `B_AVAILABLE_NEEDS_WORK`, 2
`C_CARTOGRAPHY_ONLY`, 12 `D_NOT_FOUND`.

Próximas CCAA recomendadas: **Navarra**, por acceso WFS y continuidad
1985–2023; **Cataluña**, por cobertura 1986–2021 y descarga; **Andalucía**,
por WFS anual reciente. Cada una necesita una fase de inventario/licencia y
calidad antes de publicar.

El peor hueco estructural es **Canarias**: ESFire30 v1 no cubre islas, ES-1 no
localizó una serie autonómica y el futuro pipeline debe tratar varias islas y
husos. Galicia es la prioridad operativa de contacto: concentra 38.358
polígonos ESFire30, pero tampoco se localizó una fuente oficial comparable.

El inventario estructurado, URLs y próximas acciones están en
`data/sources/spain_official_perimeter_inventory.json`.

## 11. Matriz temporal de cobertura

| Periodo | Nacional administrativo | Nacional espacial | Autonómico | Complementario reciente |
|---|---|---|---|---|
| 1968–1984 | EGIF, cobertura histórica variable | ninguno homogéneo localizado | fuentes puntuales si aparecen | no |
| 1985–1992 | EGIF | ESFire30 peninsular | Navarra/Cataluña y otras tras auditoría | no |
| 1993–2021 | EGIF | ESFire30 peninsular | ICV y fuentes autonómicas disponibles | EFFIS desde 2003, no necesario como sustituto |
| 2022–2023 | EGIF presente en buscador, estado definitivo no afirmado | ESFire30 v1 ausente | fuentes autonómicas | EFFIS |
| 2024+ | avances/EGIF cuando se consolide | ESFire30 v1 ausente | fuentes autonómicas | EFFIS provisional por snapshot |

El timeline nacional no debe apilar estos recuentos como una serie única. Se
propone una pista por tipo de entidad/fuente: partes EGIF, perímetros ESFire30,
perímetros oficiales autonómicos y EFFIS provisional. El tooltip explica
unidad y cobertura. Los filtros pueden ser comunes, pero las métricas se
mantienen separadas.

## 12. Papel de cada fuente

### EGIF

Backbone administrativo nacional. Aporta partes, fechas, municipios,
superficies, causas y diccionarios variables. No aporta por sí mismo un
perímetro fiable ni resuelve siempre el episodio físico.

### ESFire30

Backbone espacial nacional **secundario** 1985–2021 para la península. Es la
mejor cobertura geométrica homogénea encontrada, pero siempre rotulada como
teledetección científica Landsat B y nunca como oficial.

### Autonómicas

Fuente oficial territorial cuando exista. Puede aportar geometría preferente
para su ámbito y periodo, sin borrar geometrías nacionales independientes.

### EFFIS

Capa complementaria satelital reciente/provisional. El [RDA oficial](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/rapid-damage-assessment)
advierte que las fechas no equivalen necesariamente a ignición/extinción, no
distingue todos los tipos de quema y que la metodología no es directamente
comparable con otras fuentes. A escala nacional debe capturarse por snapshot
y por intersección con el límite oficial de España, no solo por atributos de
país/provincia.

## 13. Identidad nacional

No se migran IDs publicados. Se añade un contrato genérico compatible:

```text
source_record_id   # ID nativo, conservado sin cambio
record_id          # <source>:record:<native-or-stable-hash>
geometry_id        # <source>:geometry:<version>:<native-or-stable-hash>
episode_id         # solo cuando una fuente lo documenta
candidate_link_id  # relación separada, nunca identidad implícita
legacy_ids[]       # por ejemplo gva:pif-cv:..., egif-record:..., esfire30:...
```

Los IDs actuales siguen siendo canónicos para los assets ya publicados y los
permalinks. El resolver nacional acepta ambos namespaces. No se crea un
`fire_id` transversal por proximidad, fecha o geometría parecida.

## 14. UX territorial y timeline

Diseño conceptual, sin implementación:

- selectores dependientes `España → CCAA → provincia → municipio`;
- búsqueda textual limitada al territorio padre y basada en IDs;
- lista municipal no se carga completa al inicio;
- auto-fit usa bounds IGN o geometrías visibles, nunca un punto inventado;
- permalink conserva IDs territoriales, centro/zoom y fuentes;
- las URLs valencianas actuales siguen resolviéndose;
- timeline en pistas separadas con coberturas, provisionalidad y unidades;
- una fuente autonómica no oculta por defecto la existencia de una fuente
  nacional, aunque pueda ser la geometría visual preferente.

## 15. Licencias y publicación fail-closed

| Fuente | Titular | Estado preliminar | Reutilización/transformación | Atribución |
|---|---|---|---|---|
| EGIF | MITECO | publicable | sí, condiciones generales | fórmula MITECO y fecha de actualización |
| ESFire30 v1 | autores del dataset | CC BY 4.0 | sí, indicar cambios | autores, título, DOI, licencia |
| EFFIS | Unión Europea/JRC | CC BY 4.0 salvo aviso particular | sí, indicar cambios | fórmula Copernicus/EFFIS documentada |
| IGN/CNIG límites | IGN/CNIG | CC BY 4.0 general | sí | origen y propiedad IGN/CNIG |
| INE códigos | INE | auditar distribución concreta | previsiblemente reutilizable | según aviso del recurso |
| Autonómicas | cada proveedor | **no heredado** | solo tras auditoría individual | específica por dataset |

EFFIS publica su [licencia](https://forest-fire.emergency.copernicus.eu/about-effis/data-license)
como CC BY 4.0 para contenido de la UE salvo indicación particular. GitHub
Pages no cambia las obligaciones. Todo manifest nacional mantiene
`publishable`, `license_status`, atribución y modificaciones; el build público
falla ante `false`, `unknown` o metadatos ausentes.

## 16. Política de actualización y snapshots

| Clase | Ejemplo | Política |
|---|---|---|
| consolidado | EGIF cerrado, ICV anual | snapshot inmutable, checksum, cobertura y versión de pipeline |
| versionado científico | ESFire30 Zenodo | DOI/versión; nueva release coexistente hasta auditoría |
| anual autonómico | ICV, REDIAM, Navarra | inventario/count antes de descarga; diff y publicación versionada |
| dinámico provisional | EFFIS | snapshot UTC frecuente; `coverage_complete=false`; conservar snapshots previos |

Nunca se reconstruye producción desde treinta servicios en tiempo real. Los
jobs de ingestión detectan cambios de esquema/count y fallan antes de sustituir
un snapshot válido. Releases u object storage guardan assets; Git conserva
código, manifests pequeños y checksums.

## 17. Arquitectura ES-v1 propuesta

```text
config/
  sources/                 # licencia, autoridad, publicación, actualización
  territories/             # perfiles y labels, sin lógica gva hardcodeada
data/
  raw/<source>/<snapshot>/
  normalized/
    records/<source>/
    geometries/<source>/
    territory-relations/<source>/
    candidates/<source-pair>/
  web/<profile>/<version>/
    manifests/
    records/<source>/<territory>/<block>/
    geometry/<source>/<lod-or-tiles>/
scripts/
  ingest/<source>/
  normalize/<source>/
  build/web/
  validate/
```

Contratos:

- `source_record` y `geometry` son entidades distintas;
- `territory_relation` es N:M y no cambia la geometría;
- `candidate_link` nunca entra en un registro fuente;
- `preferred_geometry` es una decisión de presentación versionada, no borrado;
- manifests declaran periodo, tipo de entidad, LOD, partición, checksum,
  procedencia, licencia y presupuesto de carga;
- perfiles `development`, `public` y futuros perfiles territoriales comparten
  un publication guard fail-closed.

## 18. Infraestructura y costes previsibles

Las cifras mínimas nacionales ya medidas/estimadas son:

- ESFire30 raw: 88,8 MiB ZIP; derivados GeoJSON completos, ~457 MiB entre los
  tres LOD sin contar duplicación por particiones;
- EGIF raw comprimido: ~151 MiB estimados; normalizado con originales: ~3,8
  GiB; web mínimo: ~158 MiB raw / ~8,5 MiB gzip;
- límites territoriales, manifests y relaciones: decenas a cientos de MiB
  según detalle, reducibles con índices/LOD;
- build inicial: minutos para ESFire30 (esta medición tardó 185 s sin teselas)
  y previsiblemente decenas de minutos para XML EGIF completo; debe ejecutarse
  fuera del job de Pages o desde snapshots versionados.

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
limita el sitio publicado a 1 GB, recomienda repositorio fuente ≤1 GB, aplica
100 GB/mes de ancho de banda blando y aborta deployments de más de 10 minutos.
[GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
admite hasta 1.000 assets, cada uno <2 GiB, sin límite total declarado.

Decisión de capacidad:

- Pages puede alojar un primer prototipo nacional cuidadosamente particionado,
  pero no todos los LOD/normalizados ni crecimiento autonómico sostenido;
- Releases sirven para snapshots reproducibles, no son necesariamente el CDN
  óptimo para tráfico interactivo;
- cuando los assets web publicados se acerquen a **500–700 MiB**, una sola
  fuente tileada supere varios cientos de MiB, el bandwidth mensual se acerque
  a 100 GB o el build reproducible exceda 10 min, evaluar object storage/CDN;
- PMTiles en object storage compatible con Range es el candidato natural, no
  una decisión aplicada en ES-1.

## 19. Migración por fases sin romper GVA

1. **ES-2 — núcleo territorial y contratos nacionales.** Versionar catálogo
   INE/IGN, jerarquía, relaciones N:M, manifests genéricos, namespaces/aliases,
   publication guard y muestras de dos CCAA. Ningún cambio público.
2. **ES-3 — prototipo cartográfico ESFire30 nacional aislado.** Generar
   GeoJSON particionado y vector tiles/PMTiles diagnósticos; comparar Leaflet y
   renderer vectorial en España/CCAA/provincia/móvil. Elegir entrega y renderer
   con cifras.
3. **ES-4 — EGIF nacional.** Descargar por bloques, inventariar todos los
   modelos 1968–último año disponible, normalizar registros y resolver
   municipios/causas con cobertura medida.
4. **ES-5 — primera fuente autonómica adicional.** Navarra como candidata;
   después Cataluña y Andalucía, cada una con auditoría propia.
5. **ES-6 — visor nacional development.** UX territorial, timeline por pistas,
   métricas separadas y compatibilidad de permalinks GVA.
6. **ES-7 — publicación nacional limitada.** Solo fuentes/territorios
   aprobados, bundle reproducible, medición real y despliegue reversible.

Cada fase puede desplegarse como prototipo independiente o revertirse sin
cambiar el bundle valenciano estable.

## 20. Riesgos y pendientes

1. heterogeneidad y licencia no auditada de 15/19 territorios;
2. Canarias fuera de ESFire30 v1;
3. 646.887 partes EGIF no equivalen necesariamente a episodios únicos;
4. municipios históricos y calidad variable por provincia/modelo;
5. ontology drift de causas entre décadas;
6. IDs ESFire30 no documentan episodio estable;
7. 1.342 geometrías multiautonómicas y 2.364 multiprovinciales;
8. un GeoJSON nacional monolítico agota memoria móvil;
9. Pages puede quedar pequeño al incorporar fuentes autonómicas;
10. 2022–2023 EGIF están en el buscador, pero su consolidación formal no se ha
    demostrado; 2024+ exige fuente provisional separada.

## 21. Decisiones firmes derivadas de ES-1

- País Valencià es el primer territorio implementado, no un límite de modelo.
- La jerarquía de fuentes es nacional, autonómica y complementaria; ninguna
  fuente borra automáticamente otra independiente.
- INE identifica territorios y municipios; IGN/CNIG aporta límites/bounds.
- Las geometrías fuente se almacenan una vez y se relacionan N:M con
  territorios; no se recortan para normalización.
- Leaflet + GeoJSON se conserva para el piloto y detalle contenido; la vista
  nacional overview requiere un prototipo de teselas antes de producción.
- La publicación nacional sigue siendo fail-closed por fuente y snapshot.

## 22. Recomendación exacta para ES-2

Iniciar **ES-2 — Modelo territorial nacional y contratos de manifest**, todavía
sin visor nacional:

1. descargar/versionar un snapshot oficial INE de CCAA/provincias/municipios y
   uno IGN/CNIG de límites;
2. definir `territory_id`, jerarquía, vigencia histórica y aliases;
3. materializar relaciones N:M diagnósticas para ESFire30 sin recortar;
4. generalizar manifests, IDs compatibles y publication guard fuera de `gva`;
5. validar con País Valencià y dos territorios contrastantes (Navarra y
   Canarias) que el contrato soporta fuente oficial disponible y hueco
   espacial insular;
6. producir solo inventarios/tests, no assets nacionales públicos ni cambios
   al frontend.

ES-3 será entonces el lugar correcto para decidir PMTiles/renderer con un
prototipo nacional medido.
