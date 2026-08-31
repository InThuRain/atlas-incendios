# ES-4D3A — Paridad ICV en la aplicación nacional

## Resultado

Estado: **PASS**. La aplicación de desarrollo nacional en `src/national/`
incorpora ICV como tercera fuente independiente, sin cambiar el visor público
valenciano ni crear datos, assets o despliegues nuevos.

ICV conserva la semántica publicada: un `source_record` no es una geometría ni
un episodio. La calidad de sus geometrías es **A · vector oficial**. No hay
deduplicación ni relación automática con EGIF o ESFire30.

## Fuente, cobertura y atribución

Se reutiliza exactamente el bundle validado del visor GVA:

```text
data/web/gva/manifest.json
data/web/gva/fires.json
data/web/gva/provenance.json
data/web/gva/geometry/<overview|regional|local>/<province>/<block>.geojson
```

- Cobertura temporal: 1993–2024.
- Cobertura territorial: únicamente `ES:CCAA:10` (País Valencià).
- Licencia: CC BY 4.0.
- Atribución exacta: “Incendios forestales de la Comunitat Valenciana
  (1993–2024) CC BY 4.0, Generalitat. Datos transformados para su
  visualización mediante reproyección, selección de atributos, particionado y
  simplificación geométrica.”

Fuera de País Valencià se informa **sin cobertura ICV**, nunca cero incendios.
El rango global nacional pasa a 1968–2024; EGIF sigue hasta 2023 y ESFire30
hasta 2021, cada uno con su propia intersección de cobertura.

## Reconciliación e identidad

| Elemento | Resultado |
| --- | ---: |
| Source records ICV | 13.738 |
| Geometrías ICV | 13.739 |
| `2024AL0005` | 1 record, 2 geometrías |

El control `gva:pif-cv:2024AL0005` conserva exactamente
`gva:geometry:2024:121:13587` y `gva:geometry:2024:121:13606`. Seleccionar una
no elimina ni fusiona la otra.

## Entrega y carga

El loader nacional obtiene primero manifest y registros, y después solo los
GeoJSON necesarios por **provincia × bloque temporal × LOD**. No solicita ICV
en España ni fuera de GVA. El mapeo provincial es documental y explícito:
`03→alicante`, `12→castellon`, `46→valencia`.

Los 36 shards suman, contando los tres LOD, 66.837.327 B raw y 11.030.673 B
gzip. Cada LOD contiene las 13.739 geometrías; no se cargan los tres niveles a
la vez. `fires.json` pesa 7.657.862 B raw / 572.844 B gzip y queda cacheado en
sesión tras su primera demanda ICV.

El filtro municipal ICV disponible es **A: filtro administrativo documentado**:
`fires[].municipality_id` se convierte a `ES:MUN:<INE5>`. No es una
intersección espacial con BDLJE, ni una afirmación sobre límites históricos.

## Runtime y estado

ICV tiene fuente GeoJSON MapLibre, capas `icv-perimeters` e `icv-selected`, y
una selección propia `selected_icv_geometry_id`. Por tanto puede coexistir con
`selected_geometry_id` (ESFire30) y `selected_egif_record_id` (EGIF).

La visibilidad `icv_visible` y la selección ICV se añaden de forma aditiva a
`es4c-state-v1`: un enlace anterior sin esos campos conserva su default seguro.
El default es visible porque la fuente ICV ya es pública y visible por defecto
en el visor valenciano actual. El cambio territorial, de periodo, de
visibilidad o una respuesta abortada invalida solo la selección/capa ICV que
deja de ser compatible.

Las tres fuentes se muestran y contabilizan por separado. No existe un total
conjunto denominado “incendios”.

## Validación dirigida

- País Valencià 1975: EGIF con cobertura; ESFire30 e ICV sin cobertura.
- País Valencià 1988: EGIF y ESFire30 con cobertura; ICV sin cobertura.
- País Valencià 1995: EGIF, ESFire30 e ICV independientes y activos.
- País Valencià 2024: ICV activo; EGIF y ESFire30 sin cobertura temporal.
- Alacant y Elx: shards ICV limitados a Alacant; municipio por campo
  administrativo documentado.
- Galicia 1995: ICV no solicita assets y queda sin cobertura territorial.
- `2024AL0005`: preservada la cardinalidad 1→2 y las dos identidades.
- Error ICV simulado: ICV queda en error aislado, EGIF/ESFire30 siguen ready.
- Viewport 390×844 en GVA: carga y filtros ICV correctos.

Las respuestas tardías ICV usan AbortController y generation token; una
transición País Valencià→Galicia no puede dejar geometrías ICV en Galicia.

## Límites y siguiente fase

No se implementó EFFIS, la compatibilidad del permalink valenciano `#v=1`,
producción ni publicación. `PRODUCTION_SWITCH_READY` permanece `false`.

La siguiente fase exclusiva propuesta es **ES-4D3B — paridad de fuente EFFIS**.
