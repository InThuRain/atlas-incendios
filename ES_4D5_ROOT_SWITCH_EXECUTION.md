# ES-4D5 — Ejecución del cambio de raíz nacional

## Resultado

```text
ROOT_SWITCH_EXECUTION = PASS
PRODUCTION_SWITCH_STATUS = PASS
REMOTE_PRODUCTION_IDENTITY_STATUS = PASS
NATIONAL_PRODUCT_STATUS = LIVE
PRODUCT_RELEASE_CANDIDATE = RELEASED
D5_STATUS = COMPLETE
ROLLBACK_REQUIRED = false
```

El root público `https://inthurain.github.io/atlas-incendios/` sirve ahora el
producto nacional exacto. El staging E4B sigue disponible e intacto en
`https://inthurain.github.io/atlas-incendios-es4c3d4-pages-staging/`.

## Ejecución controlada

Los prechecks se repitieron antes de cualquier mutación: árbol limpio,
`HEAD=84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c`,
`origin/main=7b6520bd3f9c6729580bb48692dd5f7a3afa79ca`, divergencia `0 6`,
TAR durable exacto, identidad local exacta, tests estáticos D5 y producción
GVA todavía activa. El `git push origin main` normal dejó ambos extremos en
`84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c`.

El push no disparó un deploy automático: el deployment seguía en el ancla GVA
hasta el `workflow_dispatch` manual de `pages-national-product.yml`. La
ejecución `34373964522` terminó `success`. El gate remoto descargó únicamente
el TAR fijado, lo verificó, extrajo de forma segura, comprobó el sitio y solo
entonces publicó el artifact Pages `10113096632`. El deployment resultante es
`6353961987`, estado `success`, URL raíz nacional.

No se construyeron datos ni PMTiles durante la operación. El rollback GVA
fijado a `f7a3532f633a247f33dee3ebba9fbcc316c0e534` permanece manual,
reproducible y sin ejecutar.

## Identidad publicada

| Contrato | Resultado |
| --- | --- |
| TAR de transporte | 812.902.400 B; `4bcc80fefbd9209f3808ae60011b9d59b4075dd0b27053d60167ce1af781edb7` |
| Ficheros físicos del sitio | 497; 812.510.441 B |
| Payload | 495; 812.291.384 B |
| Fingerprint payload | `10582ec0dc896654006c2162ea66e2fd7710790c477bb072bfb2473c51b18df3` |
| `asset-manifest.json` | `377b565548b6ff1376acde99e0cae458eb2b72d704c39587990126a0e69cf96e` |
| `site-identity.json` | `f5e80a728f45057692f36ba41f76900c9d00b9c962cedc4eb591e29e813da04e` |

El root devuelve HTTP 200, no contiene referencias de staging (`0`), y los
smokes no observaron dominios runtime externos inesperados.

## Delivery

Los dos PMTiles se probaron mediante HEAD y cuatro rangos byte-idénticos a la
referencia local: `0-0`, primeros 16 KiB, tramo medio determinista y últimos
16 KiB. Todas las lecturas fueron HTTP 206.

| Asset | Bytes | SHA-256 | Resultado |
| --- | ---: | --- | --- |
| Protomaps | 293.324.998 | `72bb270ff6fc18ccba3042834f9a9eb72901c243e7dec88b3ebb63eaafaeb729` | PASS |
| ESFire30 territorial | 63.052.056 | `3c6eb10ba146008cdabf36646d48a4c7a92c1c1357ad90679f6b5dce42013cfe` | PASS |

Los nueve glyph ranges devolvieron 200. No se observó ninguna descarga
completa de PMTiles, ni en la auditoría física ni en los smokes Chromium.

## Aceptación de producto remota

La matriz dirigida pasó en producción: 13 métricas, 13 filtros explícitos, 10
contextos/destacados, filtro GIF ICV, cinco escenarios de red, navegación
caliente territorial y tres comprobaciones de accesibilidad (desktop, GVA
móvil y Elx móvil). No hubo errores runtime ni controles sin nombre.

Los controles representativos fueron correctos: España 1995 muestra 5.035
perímetros ESFire30, 25.557 registros EGIF y 141.082 ha conocidas; GVA 1995
mantiene 467 ICV, 467 EGIF y 25 ESFire30 como fuentes independientes; Elx
2025 muestra un perímetro EFFIS y 7 ha; Canarias mantiene EGIF y comunica
ausencia de perímetros cartografiados, no “cero incendios”. Cangas carga su
índice municipal de 2.610 IDs sin hang.

El permalink nacional complejo restauró en pestaña nueva y tras reload el
periodo 1995, CCAA 10, filtro ICV mínimo 500 ha y selección
`gva:pif-cv:1995AL0076` (`fresh_tab_match=true`, `reload_match=true`). Los dos
hashes heredados `#v=1` fueron comprobados directamente: el histórico 1995 y
el EFFIS reciente se identifican como `gva_v1`, restauran el estado esperado,
arrancan el mapa y no producen bootstrap error. El helper heredado de la
matriz no puede usar su selector `#runtime-test-output` tras un hash v1; ese
timeout es una limitación del observador, no una regresión del adaptador.

## Diagnóstico de red

Las métricas son observacionales por sesión fría y no deben interpretarse como
un presupuesto de tráfico de producción. En particular, solo se cuenta tráfico
de las familias PMTiles indicadas:

| Escenario | ESFire30 requests / bytes | Protomaps requests / bytes | ready ms |
| --- | ---: | ---: | ---: |
| España fría | 10 / 1.811.399 | 10 / 496.979 | 6.515 |
| Galicia | 18 / 5.670.097 | 18 / 1.299.772 | 8.710 |
| Ourense | 24 / 7.262.234 | 24 / 1.986.926 | 9.580 |
| Cangas | 18 / 3.332.074 | 18 / 1.276.658 | 12.038 |
| Elx | 19 / 738.636 | 22 / 1.091.144 | 6.993 |

La repetición España → Galicia → España → Galicia, los reloads y la
navegación caliente pasaron sin descarga completa. GitHub Pages expone
`Cache-Control: max-age=600`; se observa caché de navegador/runtime, pero no
se declara una validación independiente de política CDN.

## Avisos no bloqueantes

- GitHub Actions mostró el aviso de infraestructura Node 20 → 24 para las
  acciones de Pages; el workflow y el deployment fueron correctos.
- La limitación del selector de test en hashes GVA v1 queda documentada para
  el harness, sin tocar el runtime liberado.
- P1 posrelease sin relación con el switch: brush del histograma, target táctil
  anual móvil y feedback de carga municipal fría.

## Siguiente paso

No se inicia trabajo P1 ni se crea tag remoto en esta fase. Si se desea marcar
la liberación después de esta revisión, el tag recomendado es
`national-product-v1.0.0`. El siguiente checkpoint es
`POST_RELEASE_CHECKPOINT`.
