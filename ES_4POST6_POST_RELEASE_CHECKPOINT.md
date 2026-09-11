# ES-4POST6 — Cierre de la primera release nacional

**PASS — `NATIONAL_PRODUCT_STATUS = LIVE_V1_0_0`.** El tag anotado
[`national-product-v1.0.0`](https://github.com/InThuRain/atlas-incendios/releases/tag/national-product-v1.0.0)
está publicado. No se ha vuelto a desplegar, reconstruido ningún artifact ni
modificado runtime o datasets. No se ha creado una GitHub Release adicional.

## Identidad canónica

| Campo | Valor |
| --- | --- |
| Producción | https://inthurain.github.io/atlas-incendios/ |
| Tag target / MAIN_COMMIT | `534cfe37a7120904f48c87bba71b4fcb7423bb5f` |
| Objeto del tag anotado | `9c951b0c6bc2e66cd3e1613fd8f6a14e0fd101aa` |
| Pages deployment | `6397065009` |
| Workflow run | `34620607559` |
| Site identity SHA | `f8fe88d66313931d2ed318723334d45062f23cc72f86538835a6df638ba785a1` |
| Manifest SHA | `557c662dd23df2207f68b6ef36ddae35f0d06b069864ffbb8b3b53ded7a59bd0` |
| TAR PATCH SHA | `8903bc91de088e82b7c3410d6b2d2e0a5eda64889ffdcc02569319fcc14e45af` |

Es v1.0.0 porque no había un tag nacional de producción previo. El despliegue
nacional anterior pertenecía a la etapa de reconciliación de producto; POST2
es la primera release formalmente aceptada con paridad de exploración GVA.
No se inventa una historia v1.0.1 ni se etiqueta el commit documental POST5.

## Git y operaciones

Tras fetch, HEAD era `a08b437d120666dcc71b2e84ea7aba12f131d2e5`, origin/main
era `534cfe37a7120904f48c87bba71b4fcb7423bb5f`: ahead **1**, behind **0**.
Árbol versionado limpio; `?? build/` contiene trabajo local y queda excluido.

Después de los gates, se publicó únicamente el commit pendiente POST5 mediante
push normal: HEAD = origin/main = `a08b437…`, **0/0**. La revisión inicial de
permisos confundió este push autorizado en §8 con el cierre POST6 local de §27;
se relejeron ambas instrucciones y el reintento fue autorizado. No hubo bypass.

El tag no existía local ni remotamente. Se creó anotado sobre `534cfe37…`, se
comprobó `git rev-parse national-product-v1.0.0^{}` y se publicó únicamente ese
tag, sin `--tags`, force ni desplazamientos. `ls-remote` confirmó el mismo
destino desreferenciado. Tras ambos pushes, no apareció un nuevo run ni
deployment Pages: siguen `34620607559` / `6397065009` y la identidad POST2.
El commit documental que cierra POST6 se conserva **solo local**, dejando main
intencionadamente un commit por delante; el tag sigue anclando el producto real.

## Salud de producción: comprobación acotada

Se reutilizaron los observadores POST4/POST5, con evidencia nueva y sin suite
completa ni repetición exhaustiva de aceptación:

- HTTP sin caché: root 200, manifest y site identity exactos antes del push y
  después de publicar el tag.
- GVA 1993–2024: **13738 registros / 13739 geometrías**. Paleta azul
  `rgb(44,123,182)` → rojo `rgb(240,82,46)` y leyenda temporal correctas.
- ICV recuperado `2016AL0074`: visible, seleccionable y popup directo.
- Multi-hit ICV/ESFire30: candidatos separados, sin fusión. El caso comparte
  año 1995; no aporta una nueva prueba de orden entre años distintos.
- España 1995: **25557 partes EGIF / 5035 perímetros ESFire30**; mapa ready.
- Elx/EFFIS: popup y provisionalidad conservados.
- Permalink nativo en sesión nueva y legacy `#v=1`: PASS; cámara legacy
  preservada. La selección EFFIS de 7 ha no supera el mínimo legacy de 10 ha.
- Móvil **390×844 emulado**: popup ICV correcto; no prueba de hardware real.
- Protomaps y ESFire30: Range 0–0 **206 / 1 byte**. El smoke España observó
  diez lecturas 206 de cada PMTiles, sin descarga completa.
- Glyphs: **9/9 HEAD 200**, siete solicitados en España con 200 y **0 glyph 404**.
  La categoría de red «other» conserva algún 404 ya documentado; no se afirma
  cero errores HTTP globales. No hubo fallo bloqueante en los smokes.

Staging POST4 conserva HTTP 200 e identidad PATCH exacta: **STAGING_PRESERVED =
true**. No se ha modificado.

## Rollbacks

Los workflows remotos siguen activos y exclusivamente `workflow_dispatch`:

- **PRIMARY_ROLLBACK_READY = true**:
  `pages-national-pre-post2-rollback.yml`; identidad PRE-POST2
  `f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e`.
- **DEEP_ROLLBACK_READY = true**: `pages-legacy-gva-rollback.yml`; ancla GVA
  `f7a3532f633a247f33dee3ebba9fbcc316c0e534`.

Ninguno se ejecutó. Esta fase verifica disponibilidad, no repite su construcción.

## Backlog preservado, no iniciado

**P1:** brush del histograma; blancos táctiles del histograma móvil; feedback
de carga municipal fría.

**P2:** z13 / relieve / POI; ranking ESFire30 seguro; pulido móvil menor.

**Bloqueos externos, separados:** ontología de causas EGIF / MITECO-ADCIF;
permiso CCINIF; geometrías municipales históricas.

**Principio permanente:** ninguna mejora nacional debe degradar exploración
centrada en el mapa, legibilidad temporal y de solapes, popup directo ni
jerarquía humana de información. La riqueza técnica y de fuentes se presenta
mediante divulgación progresiva.

```text
POST_RELEASE_CHECKPOINT = PASS
NATIONAL_PRODUCT_STATUS = LIVE_V1_0_0
MAP_EXPLORATION_PARITY = PASS
RELEASE_TAG_STATUS = CREATED
RELEASE_TAG = national-product-v1.0.0
D5_STATUS = COMPLETE
POST_RELEASE_RECONCILIATION = COMPLETE
NEXT_PHASE = POST_RELEASE_BACKLOG
```

Evidencia: `data/audit/product/es4post6_post_release_checkpoint.json`.
No se inicia el backlog.
