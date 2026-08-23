# CV-3.3 — Integración web histórica EGIF 1968–1992

Fecha de ejecución local: 23 de agosto de 2026.

## Resultado

CV-3.3 incorpora al visor los **9.175 partes administrativos EGIF** de Alicante,
Castellón y Valencia para 1968–1992. No se ha creado ninguna geometría:
`geometry=null` en los 9.175 registros. La aplicación distingue el parte
administrativo de un episodio físico y conserva:

- `fire_id=egif-record:<NumeroParte>`;
- `identity_status=source_record_only`;
- `episode_identity_status=unresolved`.

Los partes no se fusionan. Marines–Altura 1992 continúa siendo el caso
documental que impide interpretar automáticamente un parte como un episodio
físico único.

## Pipeline y formato web

El recorrido es:

```text
data/processed/egif/gva/fires_1968_1992.jsonl
  -> scripts/build_egif_frontend_assets.py
  -> data/web/gva/egif/records-1968-1992.json
  -> data/web/gva/egif/assets-manifest.json
  -> scripts/build_frontend_profile.py
  -> manifest de ejecución development/public
```

El asset es JSON compacto y autocontenido. Declara una lista ordenada de campos
y 9.175 filas posicionales; no necesita una librería adicional. Los campos son:

```text
record_id, fire_id, source, entity_type, year,
province_id, province_name, municipality_id, municipality_name,
forest_area_ha, total_area_ha, gif_forest,
cause_source_code, cause_raw, cause_code, cause_label,
cause_mapping_status, coverage_regime,
has_municipality, has_grid_reference,
identity_status, episode_identity_status, geometry
```

No contiene `original_attributes`, coordenadas, centroides, polígonos, buffers
ni referencias cartográficas transformadas. La trazabilidad se mantiene por
`record_id`, `fire_id`, el checksum del normalizado de entrada y el bloque de
provenance del manifiesto.

Se evaluó primero JSON de objetos: 5.659.045 B y 158.390 B gzip. La disposición
compacta definitiva reduce el mismo contenido a **2.345.706 B** y **123.463 B
gzip**, SHA-256
`2f65d1e73e677bcd1b478186c36da0d7e5211af26b068b2f278af1058ebad3e6`.
Frente al JSONL normalizado de 57.577.231 B, el derivado ocupa un 95,9 % menos
sin comprimir y no envía los atributos originales al navegador.

## Reconciliación con CV-3.2

| Métrica | Derivado web |
| --- | ---: |
| Partes EGIF | 9.175 |
| Alicante | 2.514 |
| Castellón | 2.600 |
| Valencia | 4.061 |
| Partes GIF, superficie forestal ≥500 ha | 180 |
| Municipio canónico resuelto | 5.254 |
| Municipio no resuelto | 3.921 |
| Municipios canónicos representados | 429 |
| Hoja/cuadrícula documentada | 8.565 |
| Sin localización espacial utilizable | 610 |
| Coordenadas transformables | 0 |
| Geometrías | 0 |

El control 1992 conserva exactamente el XML: Alicante 201, Castellón 213,
Valencia 356, total 770. No se modifica la discrepancia con el anuario: 201,
214 y 354, total 769.

`municipality_id` solo se acepta cuando el CODINE ya resuelto por el diccionario
oficial EGIF existe además en el catálogo municipal oficial canónico usado por
DATA-UX-1. El nombre mostrado procede de ese catálogo. No se usa semejanza
textual; códigos o nombres no demostrados permanecen nulos.

## Correspondencia de causas

La correspondencia usa el código fuente exacto y el diccionario público EGIF.
No se infiere causa desde texto libre ni desde otra fuente.

| Código EGIF | Valor fuente observado | Partes | `cause_code` | Etiqueta UI |
| --- | --- | ---: | --- | --- |
| 100 | Rayo | 851 | `lightning` | Rayo |
| 210 | Otras quemas agrícolas (sin especificar) | 842 | `negligence` | Negligencia |
| 220 | Otras quemas ganaderas (sin especificar) | 247 | `negligence` | Negligencia |
| 230 | Otras quemas en trabajos forestales (conocidas) | 78 | `negligence` | Negligencia |
| 240 | Otros tipos de hogueras (conocidas) | 228 | `negligence` | Negligencia |
| 250 | Fumadores | 454 | `negligence` | Negligencia |
| 260 | Otros incendios por quema de basuras (conocidas) | 184 | `negligence` | Negligencia |
| 290 | Otras causas no intencionales (sin determinar) | 342 | `negligence` | Negligencia |
| 310 | Otras causas por ferrocarril (sin especificar) | 55 | `accidental` | Accidental |
| 320 | Otras causas por líneas eléctricas (sin especificar) | 124 | `accidental` | Accidental |
| 330 | Otro tipo de motores o maquinaria (sin especificar) | 52 | `accidental` | Accidental |
| 340 | Otras causas en actividades militares (sin especificar) | 25 | `accidental` | Accidental |
| 400 | Intencionado | 1.464 | `intentional` | Intencionado |
| 500 | Desconocida | 4.229 | `unknown` | Desconocida |

Los códigos 2xx suman 2.375 partes y los 3xx, 256. Se añade `accidental` como
categoría canónica propia para no forzar los códigos 3xx bajo la etiqueta ICV
combinada «Negligencias y causas accidentales». El código 600 está documentado
como `rekindle`, pero no aparece en estos 9.175 registros. No quedan valores
fuente observados sin mapping; el pipeline conserva explícitamente
`cause_mapping_status` para no ocultar valores futuros no clasificados.

## Cobertura histórica

Los regímenes proceden de los metadatos del asset, no de texto codificado en
`app.js`:

| Periodo | Código | Texto de interfaz |
| --- | --- | --- |
| 1968–1979 | `selective` | cobertura selectiva |
| 1980–1991 | `transitional` | periodo de transición y ampliación de cobertura |
| 1992 | `systematic_or_near_systematic` | sistema más sistemático o casi sistemático |

No se usa «cobertura completa». La interfaz advierte que la serie no es
homogénea y que ausencia de parte no demuestra ausencia de incendio.

## Frontend

`DatasetLoader.loadView()` devuelve dos colecciones separadas:

- `features`: ICV, SIGIF y EFFIS según el perfil;
- `administrativeRecords`: EGIF sin geometría.

Solo `features` se entrega a `L.geoJSON`. EGIF participa en filtros, histograma,
métricas y listado, pero nunca en una capa Leaflet. Un parte seleccionado desde
el listado o un permalink abre ficha lateral; no abre popup, no se resalta una
geometría y no mueve el mapa.

El timeline toma `1968` y `2026` del manifiesto y presenta **59 barras**. Los
tooltips separan «partes EGIF», «incendios ICV», «registros SIGIF» y «perímetros
EFFIS» y avisan que no son series directamente comparables. Hay separadores
discretos en 1993 y 2025, además de marcas de régimen EGIF en 1980 y 1992. El
gradiente del mapa sigue limitado a los años con geometría, 1993–2026.

### Ejemplo 1986

Al seleccionar 1986, el mapa queda correctamente sin features y muestra:

> 1986 · 385 partes EGIF documentados. No existen perímetros individuales
> fiables disponibles para este periodo.

Las métricas son 385 partes, 9.387,8 ha forestales declaradas, 6 partes GIF,
385 partes con municipio resuelto, 385 partes con hoja/cuadrícula y 0
geometrías. Esta cifra de 385 cuenta partes; no significa que existan 385
municipios únicos. El panel de
cobertura identifica el periodo como transición y ampliación de cobertura.

### Municipio sin geometría

Los filtros de provincia, municipio, superficie, GIF y causa se aplican a EGIF
cuando el campo está documentado. Al cambiar manualmente a un municipio con
partes históricos pero sin perímetro, se conserva el encuadre y se muestra:

> Hay X partes EGIF documentados para este municipio, pero no existe geometría
> individual fiable para representarlos en el mapa.

Esto se distingue de «No hay datos ni perímetros visibles». Un permalink con
municipio y centro/zoom conserva siempre su vista compartida.

### Historia de un lugar

EGIF no se incluye en el resultado espacial. La consulta continúa evaluando
solo polígonos ICV/EFFIS y puntos SIGIF cercanos en development. Si el periodo
incluye EGIF, explica que esos partes no pueden evaluarse puntualmente y que no
se infiere relación por municipio o cuadrícula.

## Perfiles y publicación

- `development`: EGIF + ICV + SIGIF + EFFIS; el guard global es falso porque
  SIGIF continúa `publishable=false`.
- `public` candidato: EGIF + ICV + EFFIS; SIGIF y candidatos quedan excluidos;
  `publication_guard.all_included_sources_publishable=true`.

La atribución visible EGIF es: «Origen de los datos: Ministerio para la
Transición Ecológica y el Reto Demográfico.» El perfil no sugiere respaldo de
MITECO. El sitio público local candidato contiene 41 assets de datos y su
validador pasa. No se ha creado un nuevo Release, no se ha modificado el bundle
`public-data-v3`, no se ha ejecutado el workflow y no se ha publicado nada.
Hasta aprobar un bundle nuevo, la web real sigue en el perfil anterior.

## Rendimiento

Chrome headless, servidor local sin compresión HTTP, tres repeticiones, mediana:

| Perfil público | 1993–2026 sin EGIF | 1968–2026 con EGIF | Diferencia |
| --- | ---: | ---: | ---: |
| Peticiones iniciales | 16 | 17 | +1 |
| Bytes de assets crudos del `loadView` | 18.510.611 | 20.856.317 | +2.345.706 |
| Gzip estimado del `loadView` | 2.562.663 | 2.686.126 | +123.463 |
| Tiempo total escritorio | 650,8 ms | 729,8 ms | +79,0 ms |
| Carga escritorio | 245,8 ms | 260,7 ms | +14,9 ms |
| Render escritorio | 332,6 ms | 369,1 ms | +36,5 ms |
| Heap escritorio | 170.869.876 B | 187.453.469 B | +16.583.593 B |
| Tiempo total móvil emulado | 611,2 ms | 690,1 ms | +78,9 ms |
| Render móvil emulado | 308,3 ms | 348,6 ms | +40,3 ms |
| Heap móvil emulado | 170.700.739 B | 177.904.991 B | +7.204.252 B |

El parseo específico EGIF mide 13,9 ms en escritorio y 12,3 ms en móvil
emulado. El perfil development completo queda en 741,1 ms y 192,9 MB de heap en
escritorio, y 906,3 ms y 183,5 MB en móvil emulado. El incremento no justifica
PMTiles, MapLibre ni una base de datos en frontend. La emulación no sustituye
una prueba en un móvil físico de gama baja.

## Validación

- 23 tests Python con `.venv` (`pyproj` y Shapely disponibles): pasan.
- Validador EGIF: recuentos, identidades, geometría nula, checksum, causas,
  cobertura y discrepancia 1992: pasa.
- Validador ICV y validador recent development: pasan.
- Smoke development bajo `/atlas-incendios/`: 44 escenarios tras la prueba
  municipal histórica final.
- Smoke public bajo `/atlas-incendios/`: 45 escenarios tras la prueba municipal
  histórica final; sin control, asset o referencia descargable SIGIF.
- Build public local: 41 assets; `scripts/validate_public_site.py`: pasa.
- Móvil emulado: timeline, filtros, mapa vacío histórico y perfil completo:
  pasan.

## Pendientes y recomendación CV-3.4

1. CV-3.3 fue revisada y aprobada el 23/08/2026; la terminología distingue
   partes con municipio resuelto de municipios únicos y conserva separadas
   «Negligencia», «Accidental» y «Negligencias y causas accidentales».
2. En CV-3.4, crear un nuevo bundle público inmutable que añada únicamente el
   asset EGIF validado, actualizar `config/public-data-bundle.json`, ejecutar el
   workflow manual y comprobar la URL real. El workflow queda fail-closed con
   el bundle antiguo porque la entrada EGIF todavía no existe allí.
3. Mantener como investigación independiente la identidad multiparte
   Marines–Altura, los seis pares duplicados y los perímetros históricos; no
   resolverlos como parte de la publicación web.
4. Valorar una prueba en móvil físico de gama baja antes o después del futuro
   despliegue, sin cambiar Leaflet mientras no aparezca un problema real.
