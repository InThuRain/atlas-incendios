# ES-4POST2D — Aceptación final de exploración cartográfica

## ¿El mapa nacional corregido vuelve a ser tan fácil de explorar como el GVA antiguo?

Sí. La comparación local entre el GVA anclado y el nacional con POST2A, POST2B
y POST2C confirma el recorrido humano: **periodo → mapa → color/solapes →
click → información inmediata → detalles opcionales**, sin perder capacidades
nacionales.

```text
MAP_EXPLORATION_PARITY = PASS
POST2_PRODUCT_RECONCILIATION = PASS
PRODUCTION_PATCH_READY = true
PRODUCTION_PATCH_BUNDLE = POST2A_POST2B_POST2C
RELEASE_TAG_STATUS = HOLD
NEXT_PHASE = ES-4POST3_PRODUCTION_PATCH_ARTIFACT
```

No hubo push, despliegue, tag, cambio de producción, rebuild de PMTiles ni
regeneración de fuentes. Producción sigue `LIVE_PRE_POST2A`.

## Referencias reproducidas

- **GVA histórico:** `f7a3532f633a247f33dee3ebba9fbcc316c0e534`, en árbol
  temporal local con el bundle público v5 (SHA `622030c9…c98e4c`). El
  downloader del ancla rechazó las rutas del TAR por su política antigua; se
  inspeccionó y extrajo el bundle ya verificado en el árbol temporal, sin
  alterar repo ni bundle.
- **Nacional corregido:** frontend temporal desde `main`, con assets nacionales
  ya aceptados en lectura. El hit-test POST2C usa `queryRenderedFeatures` sobre
  fills y outlines realmente visibles.

En GVA 1995, el histórico cargó 467 perímetros ICV. El click real de
`gva:geometry:1995:3:783` abrió el popup Leaflet para
`gva:pif-cv:1995CS5050`: 11/05/1995, Arañuel, Castellón/Castelló, 5 ha y Rayo.
El nacional ofrece la misma información primaria en popup MapLibre y deja la
ficha completa tras **Ver detalles**.

## Matriz de producto

| Capacidad | GVA anclado | Nacional pre-POST2 | Nacional POST2A+B+C | Estado |
| --- | --- | --- | --- | --- |
| ICV 1993–2024 | visible | 2016–2019 ausentes | 13.738 records / 13.739 geometrías | PARITY |
| Lectura temporal | color GVA | insuficiente | azul antiguo → naranja reciente, leyenda | PARITY |
| Solapes | explorables | poco legibles | fill temporal + outline | PARITY |
| Click y popup | Leaflet inmediato | ficha lateral | popup MapLibre inmediato | PARITY |
| Multi-hit | fuentes separadas | no humano | selector por perímetro/fuente | PARITY |
| Mapa primero | sí | PARTIAL | sí, sin abrir panel lateral | PASS |
| Móvil | popup Leaflet | no equivalente | popup compacto 390×844 | PARITY |
| Territorio/fuentes nacionales | no | sí | sí, preservados | IMPROVEMENT |

## Resultado de los recorridos

- POST2A conserva 13.738 records/13.739 geometrías. Las recuperadas
  2016/17/18/19 son 341/346/375/272, con color temporal y popup.
- 1995 conserva 467 ICV; 2024, 472 records/473 geometrías. `2024AL0005`
  mantiene sus dos geometrías clicables e independientes.
- El rango 2000–2020 permite detectar recurrencia y antigüedad por mapa y
  leyenda: `rgb(44,123,182)` antiguo y `rgb(240,82,46)` reciente.
- Un solape real ICV–ESFire30 muestra dos candidatas, ordenadas por año y con
  fuente visible; no se fusionan ni se inventa perímetro principal.
- Sólo se pulsa una feature renderizada. Periodo, histograma, territorio y
  toggle invalidan el popup antes de dejar estado stale.
- Semántica preservada: ICV oficial; ESFire30 Landsat; EFFIS satelital
  provisional; EGIF sin geometría individual ni popup ficticio.
- España 1995 mantiene series separadas (5.035 ESFire30; 25.557 EGIF;
  141.082 ha EGIF conocidas). Canarias sigue comunicando ESFire30 **sin
  cobertura**. Elx 2025 conserva un EFFIS de 7 ha.
- En móvil, leyenda, mapa, tap, multi-hit y **Ver detalles** siguen utilizables.
  El popup tiene `role=dialog`, cierre nombrado y Escape; abrirlo no carga
  DETAIL ni descarga el PMTiles completo.

La evidencia nacional directa permanece en las capturas POST2C: popup ICV,
selector multi-hit y móvil. Los 30 tests focalizados de POST2A/B/C y los checks
de audit pasan. No hay regresión mayor: se recomienda
`DEPLOY_POST2A_POST2B_POST2C`, prioridad **HIGH**. Antes de desplegar se debe
crear y validar una identidad de artifact nueva; nunca reutilizar TAR ni SHA
pre-POST2. El tag queda en `HOLD` hasta aceptación remota.
