# ES-4D2 — Extracción del frontend nacional de producción

## Resultado

Estado: **`PRODUCTION_FRONTEND_EXTRACTED`**.

Se creó un shell nacional independiente en `src/national/`. No modifica el
visor público valenciano, su permalink `#v=1`, `index.html` de raíz, ni
workflows, staging o despliegues. `prototypes/es4c/` se conserva como evidencia
e harness histórico.

La extracción es deliberadamente incremental: el shell, bootstrap, CSS,
configuración de activos y registro de fuentes son nacionales; el runtime
MapLibre/EGIF/territorio reutiliza módulos ES-4C ya aceptados mediante un entry
module compartido. Por tanto no depende de `prototypes/es4c/index.html` ni de
su bootstrap, y el siguiente paso puede mover módulos por responsabilidad sin
arriesgar una reescritura funcional.

## Estructura

```text
src/national/
  index.html             shell nacional sin panel de debug visible
  bootstrap.js           carga MapLibre y el entry runtime configurado
  runtime-config.js      configuración local de desarrollo
  asset-config.mjs       autoridad única de rutas y versiones
  source-registry.mjs    fuentes y atribuciones extensibles
  styles.css             estilos del shell nacional
scripts/build_national_frontend.py
  -> build/national/     artifact estático ignorado por Git
```

Los módulos compartidos temporalmente son `prototypes/es4c/app.js`, estado,
serialización, loaders INITIAL/DETAIL EGIF, capas/catálogos territoriales,
loader de municipios e índice municipal ESFire30. El build copia únicamente
los doce módulos que consume `app.js`; no incluye HTML, CSS, smokes, resultados
ni diagnósticos del prototipo.

`esfire30_territory_index.mjs`, sample PMTiles y los scripts de smoke quedan
como desarrollo/auditoría, no como dependencias del artifact cartográfico.

## Configuración de activos

`asset-config.mjs` centraliza las rutas de desarrollo y `asset_base_url`. La
función `resolveAssetConfig()` resuelve recursivamente las rutas de assets sin
que los loaders conozcan host, release ni staging. El build genera una
`runtime-config.js` autónoma con rutas lógicas de producción:

```text
/data/esfire30/v1/3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe/
  esfire30-national-fidelity-territories.pmtiles
```

El descriptor mantiene `63052056` bytes y SHA-256
`3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe`. No copia
PMTiles, EGIF ni shards al artifact D2. Esos paths serán empaquetados,
verificados y publicados por un workflow nacional posterior.

Las rutas BDLJE, catálogo/shards municipales e índices ESFire30 municipales
también se resuelven desde esta autoridad. Los loaders compartidos recibieron
los parámetros de configuración necesarios; sus defaults de prototipo siguen
intactos.

## Fuentes y semántica

El registro contiene exclusivamente:

| ID | Cobertura | Semántica |
| --- | --- | --- |
| `egif` | 1968–2023 | partes administrativos |
| `esfire30` | 1985–2021 | perímetros derivados de teledetección Landsat |
| `bdlje` | actual | límites administrativos actuales |

Incluye rótulo, atribución, cobertura, módulo lógico y visibilidad por defecto.
ICV y EFFIS no se implementan ni se simulan; el registro admite futuras
entradas sin convertir la UI en un caso binario EGIF/ESFire30.

Se preservan estas reglas: rango solicitado común sin modificarlo, cobertura
por fuente explícita, ausencia de cobertura distinta de cero, y ninguna
identidad automática entre `record_id` EGIF y `geometry_id` ESFire30. En scope
municipal el límite es BDLJE actual; EGIF es un enlace documental al municipio
canónico actual cuando está resuelto, y ESFire30 es una intersección con esa
geometría actual.

## Política de carga conservada

| Scope | EGIF | ESFire30 | Municipal |
| --- | --- | --- | --- |
| España | resumen de manifest; 0 INITIAL automáticos | PMTiles por Range y filtro temporal | sin catálogo, shard ni índice |
| CCAA | INITIAL de CCAA × bloques | slots MVT `ccaa_1..3` y año | sin geometría municipal |
| Provincia | reutiliza INITIAL y filtra columnas | slots `prov_1..3` y año | shard/índice del padre cuando se navega a municipio |
| Municipio | filtro columnar `municipality_id` | lista del índice provincial y año | reutiliza shard e índice |

DETAIL EGIF continúa bajo selección y cacheado por asset. Las caches y los
tokens de cancelación de ES-4C se mantienen; un cambio rápido de Galicia a Elx
no permite que respuestas antiguas sustituyan el estado vigente. BUG-01
(fallo de shard municipal no cacheado y reintentable) y BUG-02 (fallo PMTiles
transportado como error aislado y reintentable) siguen cubiertos por los tests
aceptados.

## Artifact y desarrollo local

Generar y comprobar el artifact candidato:

```bash
python3 scripts/build_national_frontend.py --output build/national
python3 scripts/build_national_frontend.py --check --output build/national
```

`build/national/` es estático e ignorado por Git: incluye shell, módulos de
runtime necesarios, MapLibre 5.16.0, PMTiles 4.3.0 y `asset-manifest.json` con
hashes de sus archivos pequeños. No es un despliegue ni contiene datos grandes.

Para desarrollo local con los assets nacionales locales existentes:

```bash
python3 prototypes/es4c/run_smoke.py --serve
# abrir http://127.0.0.1:<puerto>/src/national/index.html
```

## Paridad ES-4C validada

Los ocho smokes dirigidos contra `/src/national/index.html` pasaron, incluido
el check posterior del resultado. El harness reconoce el hook oculto
`#runtime-test-output`; no hay panel de debug visible en la UI nacional.

| Caso | Resultado |
| --- | --- |
| España/Elx end-to-end 1993–2002 | PASS; municipio `ES:MUN:03065`, selección EGIF y ESFire30 independiente y restauración |
| Galicia → Ourense | PASS; scope municipal y filtros territoriales/temporales |
| Cangas del Narcea | PASS; 2.610 IDs municipales sin hang/crash |
| Canarias | PASS; territorio/EGIF operativos y ESFire30 sin cobertura, no “0 incendios” |
| Agost | PASS; cobertura ESFire30 pero cero relaciones municipales, distinto de sin cobertura |
| transición rápida Galicia → Elx | PASS; sin estado stale |
| Elx 390×844 | PASS |
| Cangas 390×844 | PASS |

El PMTiles siguió sirviéndose únicamente por rangos en los smokes locales; no
forma parte del artifact ni se ha regenerado. El navegador usa las propiedades
MVT CCAA/provincia y el índice municipal provincial, no el índice externo
CCAA/provincia para filtrar el mapa.

No se encontraron URLs de staging (`r2.dev` o Pages staging) en `src/national/`
ni en la configuración generada. La prueba no modifica las rutas del frontend
público valenciano.

## Tests ejecutados

```text
python3 -m unittest \
  tests/test_es4d2_national_frontend_extraction.py \
  tests/test_es4c3a_national_prototype_consolidation.py \
  tests/test_es4c3c_acceptance_fixes.py
# 7 tests, OK

python3 prototypes/es4c/run_smoke.py --entry-path /src/national/index.html ...
# 8 smokes, valid=true, errors=[]

python3 scripts/build_national_frontend.py --check --output build/national
# valid=true
```

## Gaps hacia D3

`PRODUCTION_SWITCH_READY = false`. Esta fase no autoriza un cambio de raíz:

- ICV debe preservar sus perímetros oficiales valencianos y su ficha.
- EFFIS 2025–2026 debe seguir siendo una fuente separada.
- El adapter compatible con el permalink valenciano `#v=1` no existe aún.

La siguiente fase exclusiva recomendada es
`ES-4D3_GVA_SOURCE_PARITY_AND_COMPATIBILITY`.
