# ES-4D4A — Artifact nacional de staging/producción

## Corrección ES-4D4A1 — contrato de identidad físico

La identidad original D4A no debe reutilizarse para desplegar. El intento D4B
registrado en `ab31782` descubrió correctamente que el árbol extraído tenía
`500.449.871 B`, mientras el manifest declaraba `500.449.810 B`. La diferencia
exacta de 61 B procede exclusivamente de `asset-manifest.json`: la primera
serialización medía 148.052 B y se incluyó al calcular el total; después el
builder reescribió ese mismo fichero con `file_count`, `total_bytes` y
`total_mib`, y la serialización final pasó a 148.113 B sin recalcular el total.

La huella anterior `bbf980…44ee8` seguía coincidiendo porque era una huella de
los 348 assets de payload y excluía deliberadamente `asset-manifest.json`; por
ello no detectaba un cambio únicamente en ese metadata. No cambió ningún
dataset ni asset runtime: la comparación exacta de los 348 path/tamaño/SHA da
`changed_payload_assets = []` y el PMTiles conserva 63.052.056 B / SHA-256
`3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`.

El contrato corregido separa dos conceptos:

| Propiedad | Definición corregida | Valor D4A1 |
| --- | --- | ---: |
| `SITE_FILE_COUNT` | Todos los ficheros físicos desplegables, incluidos ambos metadata de identidad | 350 |
| `SITE_TOTAL_BYTES` | Suma exacta de todos esos ficheros físicos | 500.450.914 B |
| `PAYLOAD_FILE_COUNT` | Assets enumerados y hasheados en `asset-manifest.json`; excluye metadata de identidad | 348 |
| `PAYLOAD_TOTAL_BYTES` | Suma de esos assets enumerados | 500.301.758 B |
| `PAYLOAD_FINGERPRINT` | SHA-256 de filas ordenadas `path<TAB>bytes<TAB>sha256<LF>` de payload | `bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8` |
| `ASSET_MANIFEST_SHA256` | SHA-256 del manifest de payload final | `c2c57a70130fd2e4527ac6a50ebb1c86e73bb667d6c5c5940f9b015b9823aceb` |

`asset-manifest.json` enumera solo payload. El nuevo `site-identity.json`
declara el contrato del site físico, enlaza el SHA del payload manifest y usa
`site_total_bytes` como string decimal de ancho fijo: así su tamaño no cambia
al escribir el total y no se requiere un fixed point ni un hash propio. La
auditoría física exige exactamente `payload paths + asset-manifest.json +
site-identity.json`, recalcula tamaños y hashes y rechaza cualquier path extra,
faltante o duplicado.

Dos builds limpios produjeron la misma identidad completa, incluido el SHA del
manifest y de `site-identity.json`. La evidencia con el inventario físico
ordenado de los 350 archivos está en
`data/audit/production/es4d4a1_artifact_identity_fix.json`. El gate local que
usará D4B —inventario físico, hashes de payload, huella, SHA del manifest y
PMTiles— da `ARTIFACT_IDENTITY = PASS`.

La tabla y el texto históricos que siguen describen la identidad original D4A
y se conservan como evidencia del defecto detectado; no sustituyen el contrato
D4A1 anterior.

## Resultado histórico D4A original (sustituido por D4A1)

El ensamblado local reproducible ha producido un árbol estático autocontenido
para la futura aceptación remota, sin desplegarlo ni modificar ningún sitio
Pages. El resultado es apto para ser servido bajo cualquier base path, por
ejemplo `/atlas-incendios-es4c3d4-pages-staging/` o `/atlas-incendios/`, porque
las rutas runtime son relativas a `index.html` y no contienen el nombre de un
repositorio ni de un host de staging.

| Propiedad | Valor |
| --- | ---: |
| Artifact | `build/national-pages-staging/` (ignorado por Git) |
| Ficheros | 349 |
| Total | 500.449.810 B / 477,266 MiB |
| Huella | `bbf98006852762c89f1f6ca69093fccdbb1d09fe7fd2de09c15bacf83ff44ee8` |
| Límite Pages documentado | 1.000.000.000 B |
| Clasificación | `COMFORTABLE`: 50,045 % del límite; quedan 499.550.190 B |

La huella es SHA-256 de la lista ordenada
`runtime_path + TAB + bytes + TAB + sha256 + LF`, excluyendo
`asset-manifest.json` para que el propio manifest no se autorreferencie.

## Entrada y ensamblado

El ensamblador [build_national_pages_artifact.py](scripts/build_national_pages_artifact.py)
no genera ni descarga datos. Si falta algún input, falla explícitamente con
`MISSING_STAGING_INPUT`.

```bash
python3 scripts/build_national_pages_artifact.py \
  --output build/national-pages-staging

python3 scripts/build_national_pages_artifact.py --check \
  --output build/national-pages-staging
```

Parte de `src/national/` para el HTML, CSS y bootstrap. Reutiliza los módulos
runtime aceptados y los copia dentro de `runtime/`; no depende del HTML ni del
bootstrap de `prototypes/es4c/`. También entrega localmente MapLibre 5.16.0,
PMTiles 4.3.0 y la dependencia ESM `fflate` que PMTiles importa de forma
relativa.

## Inventario runtime

| Familia | Ficheros | Bytes | % total |
| --- | ---: | ---: | ---: |
| EGIF | 177 | 183.188.566 | 36,608 % |
| Geometría municipal BDLJE actual 0 m | 52 | 146.194.941 | 29,213 % |
| ICV | 37 | 74.495.189 | 14,886 % |
| PMTiles ESFire30 | 1 | 63.052.056 | 12,599 % |
| Territorios CCAA/provincia/catálogos | 4 | 24.704.158 | 4,936 % |
| Índices municipales ESFire30 | 49 | 7.023.719 | 1,403 % |
| Otros vendor | 3 | 1.119.132 | 0,224 % |
| EFFIS | 2 | 256.231 | 0,051 % |
| Frontend | 20 | 197.226 | 0,039 % |
| Metadata runtime | 3 | 70.540 | 0,014 % |

Los cinco ficheros mayores son el PMTiles nacional (63.052.056 B), EGIF
Galicia 1993–2002 INITIAL (16.610.507 B), el DETAIL correspondiente
(14.855.021 B), provincias BDLJE (10.781.436 B) y el shard municipal de
Barcelona (10.490.788 B). No se han detectado duplicados byte-idénticos de al
menos 1 MiB.

### Datos incluidos

- ESFire30 territorial: `data/esfire30/v1/3c6…13cfe/`
  `esfire30-national-fidelity-territories.pmtiles`, exactamente 63.052.056 B
  y SHA-256
  `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`.
- EGIF: su manifest y los 88 pares INITIAL/DETAIL CCAA × bloque (176 JSON);
  no incluye normalizados raw ni spools.
- Territorio: CCAA, provincias, catálogo ES-2, 8.132 municipios canónicos y
  los 52 shards municipales runtime. Cada `asset_id` de catálogo se reconcilia
  con un shard existente.
- Índice municipal ESFire30 runtime: manifest, índice nacional y 47 índices
  por padre. La ausencia de una clave municipal conserva el contrato `[]`.
- GVA: manifest, `fires.json`, provenance, 36 GeoJSON ICV por provincia,
  bloque y LOD, y el snapshot EFFIS cerrado `20260819T174426Z` (2025: 9;
  2026: 16 geometrías).

No se han incluido tests, benchmarks, auditorías de desarrollo, raw BDLJE
nacional, raw/normalizados EGIF, spools, telemetría, capturas, `work/`, ni
archivos de prototipo. `.nojekyll` está presente en la raíz.

## Integridad y dependencias

`asset-manifest.json` enumera todos los runtime assets con `logical_id`,
`runtime_path`, `required`, familia, source/version, bytes y SHA-256; además
resume familias, top 20, duplicados significativos, PMTiles, inputs y huella.
El verificador revisa cada fichero, el conjunto exacto de paths, el SHA/tamaño
contractual del PMTiles y la exclusión de spools.

La auditoría de texto runtime encontró cero rutas locales (`/home/dani/`,
`file://`, `127.0.0.1`, `localhost`) y cero hosts/rutas de staging, R2,
Releases o prototipo. No se solicitó ningún dominio externo: MapLibre, PMTiles
y `fflate` son `LOCAL_ASSET`; `external_runtime_dependencies` es `[]`.

## Reproducibilidad y smokes locales

Una segunda construcción limpia en `build/national-pages-staging-repro/`
produjo exactamente 349 ficheros, 500.449.810 B y la misma huella. La evidencia
machine-readable registra las tres igualdades y los 11 smokes dirigidos:

- España: PMTiles por Range, 10 respuestas 206, 1.817.015 B Range y ninguna
  descarga completa.
- Galicia → Ourense: INITIAL Galicia y catálogo/shard/índice padre servidos
  desde el artifact; 24 Range 206, sin fallback al árbol fuente.
- Asturias → Cangas del Narcea: índice municipal de 2.610 IDs, sin error.
- GVA 1995, 2024 y 2026: legacy `#v=1` restaura respectivamente datos
  históricos, ICV (2024) y EFFIS (16 geometrías en 2026).
- Elx y su enlace legacy EFFIS: catálogo/shard runtime y EFFIS se cargan
  same-origin; no hay relación artificial con EGIF/ESFire30.
- `#es4c-state-v1`: se reconoce y restaura desde el artifact.
- Canarias: conserva `sin cobertura ESFire30`, no “0 incendios”.
- 390×844: EFFIS 2026 correcto.

Todos terminaron sin excepciones, sin 404 runtime inesperados, sin requests a
`/src/`, `/prototypes/`, `/data/derived/` ni `/data/web/spain/`, y sin GET 200
del PMTiles completo. El rango local queda validado como soporte del harness;
la validación Range real de Pages es explícitamente responsabilidad de D4B.

La evidencia completa está en
[es4d4a_staging_artifact.json](data/audit/production/es4d4a_staging_artifact.json).

## Handoff a ES-4D4B

Con la corrección D4A1, `STAGING_ARTIFACT_STATUS = READY_FOR_REMOTE_STAGING`.
El intento D4B fallido sigue siendo evidencia histórica y no se sobrescribe.

D4B debe consumir exactamente `build/national-pages-staging/` y verificar su
`asset-manifest.json`, `site-identity.json` y la huella de payload antes de
transferirlo. El candidato de repositorio
de staging es `InThuRain/atlas-incendios-es4c3d4-pages-staging`; esta fase no
lo ha tocado. La única acción externa pendiente es su despliegue de staging y
la aceptación real de GitHub Pages. `PRODUCTION_SWITCH_READY = false`.
