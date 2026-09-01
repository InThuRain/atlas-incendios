# ES-4D3C — Compatibilidad permalink GVA `#v=1`

## Resultado

**GVA_COMPATIBILITY_STATUS = PASS.** La aplicación nacional reconoce de forma
explícita los hashes públicos valencianos `#v=1`, los adapta al estado
nacional sin inferencias espaciales y mantiene el hash de entrada durante el
restore inicial. El formato nacional de autoría sigue siendo
`#es4c-state-v1`.

El adapter puro está en `src/national/compat/gva-v1.mjs`. Reproduce el contrato
de `js/url-state.js`, que sigue siendo la autoridad del formato legacy; no
importa ni modifica el frontend Leaflet valenciano.

## Dispatch y ciclo URL

| Hash de entrada | Tratamiento |
| --- | --- |
| `#es4c-state-v1=…` | parser nacional existente, sin cambio de comportamiento. |
| `#v=1&…` | parser/adaptador GVA v1. |
| vacío | defaults nacionales. |
| versión desconocida o hash no reconocido | fallback seguro, sin heurística. |

Un restore válido `#v=1` no se convierte automáticamente. La primera
interacción que altera el estado mediante el runtime crea una entrada History
nacional v1, por lo que **Back** devuelve al hash legacy y **Forward** al hash
nativo. `Copiar enlace` genera siempre una URL `#es4c-state-v1`, pero no
reescribe por sí solo el hash legacy abierto.

## Inventario de contrato legacy

| Legacy field | Significado / validación real GVA | Equivalente nacional | Estado |
| --- | --- | --- | --- |
| `v=1` | versión exacta | dispatcher | DIRECT |
| `lat`, `lng` | número finito, lat −90…90/lng −180…180 | `center [lng,lat]` | DIRECT |
| `z` | entero redondeado 2…19 | `zoom` (validado por estado nacional 3…14) | ADAPTED |
| `from`, `to` | enteros dentro de años GVA; orden normalizado | rango `from/to` | DIRECT |
| `src` | CSV de `egif,esfire30,icv,sigif,effis`; vacío válido | toggles ICV/EFFIS demostrables | ADAPTED |
| `province` | `all`, `alicante`, `castellon`, `valencia` | CCAA 10 o PROV 03/12/46 | ADAPTED |
| `municipality` | cadena ≤180; selector GVA usa INE5 | `ES:MUN:<INE5>` sólo con padre canónico exacto | ADAPTED |
| `entity` | cadena ≤180 | EGIF record, ICV source record o EFFIS según patrón | ADAPTED |
| `geometry` | cadena ≤180 | ICV/EFFIS geometry ID estable según patrón | DIRECT |
| `min_area` | número ≥0 | no existe filtro nacional equivalente | UNREPRESENTABLE / IGNORED_SAFE |
| `gif` | `0`/`1` | no existe toggle nacional equivalente | UNREPRESENTABLE / IGNORED_SAFE |
| `cause` | cadena ≤180 | causas canónicas bloqueadas | UNREPRESENTABLE / IGNORED_SAFE |

`SIGIF` se acepta al parsear porque forma parte del contrato público GVA, pero
no se activa ni se inventa un equivalente nacional. EGIF y ESFire30 no se
alteran desde `src`, porque son fuentes nacionales que el enlace legacy no
podía representar en ese runtime; usan los defaults nacionales. Esta diferencia
es explícita y aceptable.

El estado de provincia siempre deriva del código legacy, nunca del viewport. El
municipio se acepta sólo si su INE5 y padres están en el catálogo ES-2; no hay
reverse geocoding ni corrección por centro del mapa.

## Selecciones

- `gva:geometry:…` se restaura como selección ICV de geometría estable.
- `effis:rda:…` se restaura como selección EFFIS estable.
- `egif-record:<NumeroParte>` se conserva como selección de parte EGIF si el
  scope/rango/asset lo permite.
- Un `entity=gva:pif-cv:…` sin `geometry` conserva el source record ICV y
  abre una ficha de record sin resaltar perímetro. Así `2024AL0005`, que tiene
  dos geometrías, **no** elige una de ellas arbitrariamente.
- IDs inválidos, inexistentes o fuera de cobertura descartan sólo la selección.

## Fixtures y aceptación dirigida

Las fixtures deterministas están en `tests/fixtures/gva_permalink_v1.json` y
han sido formadas conforme al orden del serializer GVA actual. Cubren estado
GVA, mapa/año/provincia, geometría y record-only `2024AL0005`, EFFIS Elx y
valores malformados.

| Caso | Resultado |
| --- | --- |
| `#v=1` GVA 1995 | CCAA 10, EGIF/ESFire30/ICV por cobertura; EFFIS sin cobertura. |
| `#v=1` 2024 | ICV completo; EGIF/ESFire30/EFFIS sin cobertura temporal. |
| 2024AL0005 + geometry | geometría concreta restaurada; fuente ICV confirma 2 geometrías de ese record. |
| 2024AL0005 record-only | record restaurado, `selected_icv_geometry_id = null`. |
| `#v=1` Elx 2025 | municipio `ES:MUN:03065`, EFFIS `285361` restaurado. |
| 2026 | EFFIS snapshot provisional, sin declarar campaña cerrada. |
| malformado / `#v=2` | fallback seguro, cero errores Chromium. |
| reload | una sesión Chromium nueva con la misma fixture conserva el estado legacy compatible. |
| legacy → interacción → back/forward | `#v=1` → `#es4c-state-v1` → `#v=1` → native correcto. |
| Copy Link | URL nativa v1 y round-trip nacional. |
| móvil | Elx/EFFIS en viewport 390×844 correcto. |

Las atribuciones ICV, EFFIS, EGIF, ESFire30 y BDLJE permanecen en el entrypoint
nacional; esta fase no modifica sus textos legales.

## Matriz final de paridad GVA MUST_HAVE

| Feature | GVA actual | Nacional D3C | Paridad | Acción |
| --- | --- | --- | --- | --- |
| ICV oficial 1993–2024 | Sí | Sí, lazy y selección estable | PASS | Ninguna |
| EFFIS 2025–2026 | Sí, provisional | Sí, snapshot GVA separado | PASS | Refresco sólo en fase explícita |
| Años 1993–2026 | Sí | Sí, rango global 1968–2026 | PASS | Ninguna |
| Mapa y fuentes | Leaflet/GVA | MapLibre/nacional | PASS_WITH_ACCEPTABLE_DIFFERENCE | UX no pixel-perfect |
| Selecciones ICV/EFFIS | entity/geometry | IDs estables; record-only ICV preservado | PASS | Ninguna |
| Permalink público `#v=1` | formato de salida actual | compatibilidad de entrada | PASS | no generar hashes legacy nuevos |
| Attribution | Sí | Sí | PASS | Ninguna |
| Responsive básico | Sí | smoke 390×844 | PASS | diseño final fuera de alcance |

Filtros de área, GIF y causa, histograma y consulta puntual siguen siendo
SHOULD/CAN_WAIT del diseño D1: no se simulan ni se presentan como paridad total.

## Cierre

`ICV = PASS`; `EFFIS = PASS`; `GVA_PERMALINK_V1 = PASS`;
`ASSET_CONFIG = PASS`; `LOCAL_FRONTEND = PASS`.

`MUST_HAVE_PARITY_GAPS = []` y
`GVA_PARITY_READY_FOR_STAGING = true`. Esto **no** autoriza el cambio de raíz:
`PRODUCTION_SWITCH_READY = false` hasta `ES-4D4_NATIONAL_PRODUCTION_STAGING`.
