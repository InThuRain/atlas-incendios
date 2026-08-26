# ES-2 — Modelo territorial nacional y contratos de datos

Fecha de cierre técnico: 26/08/2026
Ámbito: arquitectura, contratos y fixtures; sin cambios de frontend ni publicación.

## Resultado

ES-2 crea una capa canónica nacional en paralelo a la aplicación valenciana. No
migra ni reescribe `public-data-v5`, los manifests GVA, los IDs publicados o los
permalinks `v=1`. La compatibilidad se declara en
`config/compatibility-gva-v1.json` y se prueba automáticamente.

El modelo separa ocho contratos:

1. `source_record`: observación o parte aportado por una fuente;
2. `fire_geometry`: representación espacial que la fuente sí presenta como
   perímetro/punto del incendio;
3. `historical_spatial_reference`: área documental de localización que no es
   geometría de incendio;
4. `territory`: España, comunidad/ciudad autónoma, provincia o municipio;
5. `territory_relation`: relación declarada, canónica, histórica o de
   intersección;
6. `candidate_link`: hipótesis de identidad o correspondencia, no identidad
   confirmada;
7. `source`: autoridad, alcance, semántica, licencia y política de actualización;
8. `publication_asset`: archivo distribuible sujeto a fuente, licencia,
   atribución, procedencia, checksum y perfil.

El contrato de causas es auxiliar e independiente: conserva
`source_value`, `canonical_code`, `display_label`, `mapping_status` y
procedencia.

## Contratos versionados

Los contratos JSON Schema Draft 2020-12 están en `schemas/national/v1/`:

- `atlas-contracts.schema.json`: entidades y vocabularios comunes;
- `source.schema.json`: catálogo de fuentes;
- `manifest-contracts.schema.json`: source/territory/asset/runtime manifests;
- `publication-asset.schema.json`: guard de cada asset publicable.

La versión de esquema no equivale a una versión de datos. Un cambio incompatible
de contrato requerirá `v2`; una nueva captura de una fuente mantiene `v1` si no
cambia la estructura.

### Campos transversales

Todos los objetos de datos tienen un ID estable, `source_id` y `provenance`. La
procedencia mínima conserva identificador fuente, URL cuando existe, fecha de
adquisición, snapshot, transformaciones y checksums disponibles. La cobertura
temporal separa:

- intervalo observado;
- `coverage_status`;
- `completeness_status = final | provisional | incomplete | unknown`.

La ausencia de registros nunca se traduce automáticamente a cero incendios.

## Identidad e IDs

No se realiza una migración destructiva. Siguen siendo IDs primarios válidos:

- `gva:pif-cv:…`;
- `gva:geometry:…`;
- `egif-record:…`;
- `esfire30:record:sha256:…` y `esfire30:geometry:sha256:…`;
- los `geometry_id` EFFIS `effis:rda:…` ya publicados.

Para fuentes nuevas se recomienda:

```text
<source_id>:record:<source-key-or-content-hash>
<source_id>:geometry:<source-key-or-content-hash>
<source_id>:spatial-reference:<source-key>
candidate:<relation-type>:<stable-key>
```

Los territorios usan códigos oficiales, no nombres:

```text
ES
ES:CCAA:10
ES:PROV:46
ES:MUN:46001
```

Un nombre puede cambiar sin cambiar el código. `legacy_ids` permite resolver
identidades antiguas cuando haga falta, pero ES-2 conserva los IDs publicados
como principales. `episode_id` queda nullable y no se genera desde proximidad,
igualdad geométrica o coincidencia territorial.

## Modelo territorial

El contrato no impone una profundidad fija. `territory_type` y `parent_id`
permiten, entre otras, estas dos rutas:

```text
ES
└── autonomous_community
    └── province
        └── municipality

ES
└── autonomous_city
    └── municipality
```

Ceuta y Melilla se modelan conceptualmente como ciudades autónomas, no como
provincias. Los códigos estadísticos `51` y `52` se conservan como
`province_equivalent_code`, pero no generan territorios `ES:PROV:51/52`. Sus
municipios dependen directamente de `ES:CCAA:18/19`. La identidad municipal
canónica es el código INE de cinco cifras. Los nombres son atributos; los
bilingües y variantes demostradas son aliases.

Cada territorio admite:

- `valid_from` / `valid_to`;
- `official_name` y `aliases`;
- `predecessor_ids` / `successor_ids`.

El snapshot actual no inventa historia: esas listas quedan vacías hasta que una
fuente oficial documente la sucesión. Una relación EGIF histórica puede
clasificarse como `resolved_current_equivalent`, `resolved_historical`,
`candidate` o `unresolved` en el pipeline que la produzca; no se aplica fuzzy
matching definitivo.

### Snapshot 2026-01-01

`scripts/territories/build_spain_snapshot.py` descarga/consume tres entradas
oficiales y genera el snapshot compacto:

- libro INE `diccionario26.xlsx`, referido a 01/01/2026;
- relación INE CCAA–provincia;
- ficha IGN/CNIG de Límites y Unidades Administrativas Actuales.

Resultado versionado:

| Nivel | Registros |
|---|---:|
| España | 1 |
| comunidades autónomas | 17 |
| ciudades autónomas | 2 |
| provincias | 50 |
| códigos estadísticos equivalentes al nivel provincial | 2 (Ceuta y Melilla) |
| municipios | 8.132 |
| total de entidades territoriales | 8.202 |

El JSON pesa 3.726.695 bytes y tiene SHA-256
`e812559a5d9a779b52d5ef3c503609aefd9647a2fb226be5ff8fb932db2f1799`.
No contiene geometrías. El manifiesto registra como fuente futura de límites la
BDLJE de IGN/CNIG: ETRS89 para península, Baleares, Ceuta y Melilla y REGCAN95
para Canarias, coordenadas geográficas compatibles con WGS84. La versión
cartográfica completa se adquirirá de forma separada cuando se necesiten bounds
o intersecciones nacionales.

La denominación oficial INE 2026 de `03065` es `Elx/Elche`. El piloto puede
seguir mostrando su alias anterior `Elche/Elx`: el filtro y la identidad usan
el código.

## Relaciones territoriales y QA

Una geometría se almacena una vez. Se relaciona N:M con territorios mediante
objetos independientes:

- `source_declared`: texto/código declarado por la fuente;
- `spatial_intersection`: resultado reproducible de geometría contra límite;
- `canonical_mapping`: equivalencia administrativa documentada;
- `historical_mapping`: correspondencia histórica documentada.

Una intersección no sustituye al territorio declarado. Una geometría
transfronteriza no se recorta ni duplica para asignarla a varias provincias o
CCAA. Los estados QA son `match`, los match/mismatch por nivel y
`not_checkable`; una incompatibilidad se registra, no corrige la fuente.

## Referencias espaciales históricas

La malla CCINIF se formaliza como
`historical_spatial_reference`/`historical_grid_cell`:

```text
EGIF source_record --spatial_reference_id--> historical_grid_cell
historical_grid_cell --1:N--> geometry_parts
EGIF geometry_id = null
```

El contrato admite múltiples fragmentos, intersecciones multiterritoriales,
referencias incompletas, Canarias sin `HOJA` y estados `confirmed`, `ambiguous`,
`unusable`, `no_reference`. Nunca rellena un código ausente. La semántica es
siempre `historical_location_reference` y `geometry_status=not_fire_geometry`.

CCINIF permanece `publishable=false`, `license.status=pending_permission`.

## Semántica geométrica

La calidad A/B/C no sustituye a la semántica. El vocabulario v1 es:

- `official_fire_perimeter`;
- `documented_remote_sensing_perimeter`;
- `provisional_remote_sensing_perimeter`;
- `historical_location_reference`;
- `administrative_point`;
- `documented_cartographic_reconstruction`;
- `none`, exclusivamente para fuentes sin geometría inherente.

Así, una celda oficial de CCINIF puede tener procedencia oficial y seguir sin
ser un perímetro; un polígono científico B puede ser perímetro cartografiado sin
ser oficial; y un punto administrativo no se presenta como superficie.

## Catálogo nacional de fuentes

`config/sources-spain.json` describe siete fuentes de control:

| source_id | escala | semántica | actualización | publicación ES-2 |
|---|---|---|---|---|
| `egif` | nacional | sin geometría inherente | snapshot periódico | permitida |
| `ccinif_grid` | nacional | referencia histórica | entrega histórica | bloqueada |
| `esfire30` | nacional | teledetección documentada | snapshot Zenodo inmutable | permitida |
| `gva_icv` | autonómica | perímetro oficial | entrega anual | permitida |
| `gva_sigif` | autonómica | punto administrativo provisional | live/snapshot provisional | bloqueada |
| `effis` | complementaria | perímetro provisional | snapshot periódico | permitida |
| `navarra_official` | autonómica | perímetro oficial | snapshot periódico | diseño; pendiente auditoría de capa |

`navarra_official` se mantiene no publicable en ES-2 aunque el catálogo IDENA
sea A_READY: aún no se ha auditado la licencia/atribución exacta de cada capa ni
su ingesta. Esto aplica el criterio fail-closed.

## Publication guard

`scripts/contracts/validate_national_contracts.py` valida catálogo, jerarquía,
fixtures y perfiles. El guard exige simultáneamente:

1. fuente conocida y `publishable=true`;
2. licencia confirmada;
3. atribución no vacía;
4. asset `publishable=true` y perteneciente al perfil;
5. licencia, atribución y provenance del asset;
6. URL, tamaño y SHA-256 válidos.

El perfil `pilot_public` acepta EGIF + ESFire30 + ICV + EFFIS. Forzar SIGIF,
CCINIF o Navarra falla. El guard nacional no sustituye todavía el guard del
build valenciano: ambos coexisten hasta una migración desplegable posterior.

## Manifests y particionado

Los contratos distinguen `source manifest`, `territory manifest`, `asset
manifest` y `runtime manifest`. Una partición declara:

- fuente;
- territorios a los que da servicio;
- periodo;
- LOD;
- semántica geométrica;
- recuento, bytes y checksum;
- URL;
- perfiles permitidos;
- referencias a geometrías compartidas cuando proceda.

Se conserva la decisión ES-1:

- registros: `source × CCAA × bloque temporal`;
- geometrías: una sola copia por `geometry_id`;
- relaciones territoriales: N:M en índices/manifests;
- polígonos transfronterizos: compartidos, no recortados ni repetidos.

No se elige aún PMTiles ni renderer.

## Compatibilidad con el piloto

`config/compatibility-gva-v1.json` adapta IDs de catálogo, no datos. Declara
inmutables durante ES-2:

- `config/sources-gva.json`;
- `config/datasets-gva.json`;
- `config/public-data-bundle.json`;
- `public-data-v5`;
- permalink `v=1`.

El fixture País Valencià reconcilia sin pérdida:

- 13.738 registros ICV;
- 13.739 geometrías ICV;
- 9.175 partes EGIF 1968–1992;
- 710 geometrías ESFire30 1985–1992;
- el incendio `2024AL0005` con dos geometrías;
- un parte EGIF con `geometry_id=null` y referencia CCINIF separada;
- IDs legacy y selección de permalink.

ES-2 no transforma los datasets completos: prueba que el contrato puede
representarlos y deja la migración material para fases posteriores.

`scripts/contracts/adapt_gva_catalog.py` aplica el mapping de forma no
destructiva y exige que el orden de `development`/`public` produzca exactamente
`pilot_development`/`pilot_public`. No escribe sobre ninguna configuración.

## Segundo control: Navarra

El fixture representa las capas IDENA `FOREST_Pol_HcoIncendio` y
`FOREST_Pol_HcoIncendioA` como fuente oficial autonómica. Su geometría puede
coexistir con un parte EGIF y un perímetro ESFire30 mediante una relación
`candidate`; no confirma un episodio común. La fuente permanece `design_only`
y no publicable hasta auditarla.

## Control difícil: Canarias

El fixture demuestra:

- EGIF sin geometría inherente;
- ausencia de ESFire30 en el control;
- referencia CCINIF con `CUAD` pero sin `HOJA`;
- estado `ambiguous`;
- dos fragmentos geométricos bajo una sola referencia;
- dos provincias insulares en una CCAA;
- ningún código de hoja inventado.

## Causas

El contrato nacional no fija todavía una ontología completa. Cada mapping
conserva el valor fuente y se clasifica:

- `documented`: equivalencia respaldada;
- `candidate`: propuesta pendiente de revisión;
- `unmapped`: no comparable o sin evidencia.

El idioma de la etiqueta no forma parte de la identidad del código canónico.

## Políticas de actualización

Se formalizan cinco clases:

- `immutable_snapshot`: ESFire30 v1;
- `periodic_snapshot`: EGIF y EFFIS;
- `annual_release`: ICV;
- `live_provisional`: SIGIF;
- `received_historical_reference`: malla CCINIF.

Cada nueva captura conserva fecha, cobertura observada, checksums y no
sustituye silenciosamente una captura previa. `provisional` y `incomplete` no
son equivalentes a ausencia ni a cero.

## Pruebas

`tests/test_es2_national_data_model.py` cubre:

- sintaxis de schemas;
- catálogo y snapshot territorial;
- jerarquía y checksum;
- IDs y permalink legacy;
- referencia histórica multiparte;
- geometría multiterritorial sin duplicación;
- diferencia entre territorio declarado e intersección;
- fuente bloqueada y asset bloqueado;
- geometría ausente;
- referencia CCINIF ambigua;
- municipio temporal;
- fuente provisional;
- relación territorial duplicada;
- estados del mapping de causas;
- fixtures País Valencià, Navarra y Canarias.

Los tests existentes del piloto deben seguir pasando sin cambios de frontend.

## Límites y trabajo pendiente

1. El snapshot territorial es actual (01/01/2026), no una genealogía histórica.
2. No se han descargado ni versionado límites completos IGN/CNIG; antes de crear
   relaciones espaciales nacionales deberá fijarse un snapshot geométrico.
3. Navarra requiere auditoría real de esquema, IDs, licencia de capas y snapshot.
4. CCINIF requiere permiso escrito de redistribución.
5. La ontología nacional de causas sigue pendiente.
6. No existe aún un runtime manifest nacional ni assets nacionales de producción.
7. No se ha decidido PMTiles/vector tiles ni renderer.

## Recomendación para ES-3

Crear un prototipo nacional aislado de ESFire30, sin tocar el piloto: producir
particiones y un índice único de geometrías bajo los manifests v1, medir
GeoJSON particionado frente a PMTiles/vector tiles en España/CCAA/provincia y
resolver el tratamiento de geometrías transfronterizas por referencias
compartidas. El criterio de salida de ES-3 debe ser una decisión medida de
entrega/render, no la publicación del visor nacional.
