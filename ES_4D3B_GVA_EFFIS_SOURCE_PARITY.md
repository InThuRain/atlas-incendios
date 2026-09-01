# ES-4D3B — Paridad de fuente EFFIS reciente GVA

## Decisión

**PASS.** El runtime nacional integra exclusivamente el snapshot EFFIS ya
publicado por el visor GVA, como fuente independiente y perezosa. No se han
descargado datos nuevos, recalculado perímetros ni creado relaciones nuevas.

EFFIS representa `provisional_satellite_perimeter`: perímetros satelitales
provisionales, calidad `B_provisional_satellite`. No son perímetros oficiales
ICV ni partes administrativos EGIF, y el runtime no suma ninguna de las tres
fuentes bajo un único contador de “incendios”.

## Snapshot cerrado y procedencia

- Manifest: `data/web/gva/manifest.json`.
- `snapshot_id`: `20260819T174426Z`.
- Adquisición: `2026-08-19T17:44:26.023443Z`.
- Fuente: **European Forest Fire Information System (EFFIS) / Copernicus
  EMS**.
- Metodología: <https://effis.jrc.ec.europa.eu/about-effis/technical-background/rapid-damage-assessment>.
- Atribución: “European Union, Copernicus EMS / EFFIS (CC BY 4.0); selección
  espacial y reducción de atributos realizadas por el Atlas”.

| Año | Asset publicado | Features | Raw | Gzip | SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| 2025 | `data/web/gva/recent/effis/2025.geojson` | 9 | 37.756 B | 11.120 B | `afd7c30131d1c9829867b31633b4e5a0135df613722a1e72204c54af15a699c5` |
| 2026 | `data/web/gva/recent/effis/2026.geojson` | 16 | 218.475 B | 66.631 B | `cd0e1f6f06220b673a5293787c5a9206b117a79d34295e1b934f58c87a3e7619` |

El snapshot declara para 2025 nueve intersecciones reales CV y 698 ha
cartografiadas; para 2026, 16 y 10.265 ha, con fecha máxima EFFIS
`2026-08-08`. Esta última cifra es una fotografía adquirida en agosto de 2026,
no el cierre de una campaña. En ambos años se preserva el aviso de origen:
“Satellite-derived sum; not official administrative burned area.”

## Cobertura y carga

El rango global pasa a **1968–2026**. Cada fuente conserva su intersección:

| Fuente | Cobertura | Ámbito integrado nacional |
| --- | --- | --- |
| EGIF | 1968–2023 | España |
| ESFire30 | 1985–2021 | España, según relación territorial |
| ICV | 1993–2024 | Comunitat Valenciana |
| EFFIS snapshot | 2025–2026 | Comunitat Valenciana (`ES:CCAA:10`) |

“Datos EFFIS no integrados para este territorio” significa únicamente que
este runtime no incorporó EFFIS fuera de la Comunitat Valenciana; **no**
afirma que EFFIS no tenga cobertura en el resto de Europa/España.

El loader resuelve los assets `recent.assets.kind = effis_perimeters` por año.
En GVA carga sólo los años que intersectan el rango. En provincia filtra
`province_key` y en municipio compara `ES:MUN:<municipality_id>`: son campos
documentados del GeoJSON GVA, no una intersección BDLJE ni una resolución nueva
de municipios. La caché es por URL de asset y AbortController/generation evita
que una respuesta obsoleta escriba el estado actual.

## Runtime y estado

El registro nacional declara `effis`, su cobertura, semántica, atribución y
único ámbito integrado. Hay una capa GeoJSON MapLibre independiente, toggle
propio por defecto activo cuando el asset config nacional está presente, ficha
de selección propia y estado v1 aditivo:

- `effis_visible`;
- `selected_effis_geometry_id`;
- serialización `sources.effis` y `selections.effis_geometry_id`.

La selección conserva `geometry_id` estable `effis:rda:<id>:<hash>` e ID
EFFIS; muestra fecha, fecha final, provincia/municipio declarados, superficie
cartografiada, calidad B y snapshot. No resalta ni selecciona ESFire30, ICV o
EGIF. Si la fuente se oculta, cambia el rango/ámbito o queda fuera del filtro,
se invalida sólo su propia selección.

Los enlaces `es4c-state-v1` anteriores siguen siendo válidos: `effis` ausente
aplica el default del runtime. Un enlace con EFFIS sólo restaura una ficha si
el perímetro sigue dentro del rango y del ámbito GVA; conserva el `center` y
`zoom` serializados, sin `fitBounds` durante restore.

## Validación dirigida

Se ejecutaron contratos estáticos de D3A/D3B (17 tests) y el check del bundle
nacional. Smokes Chromium locales sobre `src/national/index.html`:

| Caso | Resultado |
| --- | --- |
| GVA 2024 | ICV disponible; EFFIS sin cobertura temporal. |
| GVA 2025 | EFFIS completo: 1 asset, 9 perímetros. |
| GVA 2026 | EFFIS completo: 1 asset, 16 perímetros. |
| GVA 1995 | ICV y fuentes históricas conservan su política; EFFIS sin cobertura. |
| Alacant 2026 | 5 de 16 perímetros por atributo `province_key`. |
| Elx 2025 | 1 de 9 perímetros por `municipality_id` documentado. |
| Galicia 2025 | `not_integrated_for_territory`, 0 assets EFFIS solicitados. |
| Selección | `effis:rda:285361:f05085eba622a5bb` restaura EFFIS `285361`. |
| Error aislado | 503 deliberado EFFIS; ICV, EGIF y ESFire30 quedaron `complete`/`covered`. |
| Cambio rápido | GVA 2026 → Galicia termina en `not_integrated_for_territory`; la respuesta EFFIS no sobrescribe el ámbito final. |
| Restore/history | hash EFFIS conserva selección, `[-0.5, 38.5]`, zoom 8; back/forward vuelve a 2026. |
| Móvil | 390×844, GVA 2026: 16 perímetros, sin errores. |

## Gaps y límite de cambio

- **D3C:** adapter compatible con permalink público valenciano `#v=1`.
- **Puede esperar:** refrescar el snapshot EFFIS sólo mediante una fase de
  adquisición/provenance explícita; no hay actualización automática.
- **Fuera de alcance:** enlaces/deduplicación EFFIS–ICV–EGIF, episodios,
  causas, nuevas relaciones municipales o cobertura EFFIS fuera de GVA.

`PRODUCTION_SWITCH_READY` permanece `false`: falta exclusivamente la
compatibilidad explícita con el permalink GVA v1 antes de plantear el cambio de
raíz público.
