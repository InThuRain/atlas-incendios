# ES-4POST3 — Artifact local del parche POST2

## Resultado

```text
PATCH_ARTIFACT_STATUS = READY_FOR_REMOTE_STAGING
PATCH_ARTIFACT_REPRODUCIBILITY = PASS
MAP_EXPLORATION_PARITY = PASS
PRODUCTION_PATCH_READY = true
PATCH_PRIORITY = HIGH
RELEASE_TAG_STATUS = HOLD
NEXT_PHASE = ES-4POST4_PRODUCTION_PATCH_STAGING
```

Se construyó localmente el candidato que reúne POST2A, POST2B y POST2C. No se
hizo push, deploy, workflow dispatch, upload, tag ni cambio en producción o
staging.

## Source checkpoint

| Campo | Valor |
| --- | --- |
| Local HEAD | `f984c66f3e78c5173abbcc13f3a317246b511a57` |
| origin/main | `84cbc9e43f2b1555a84b17cd5b94643b0b31eb1c` |
| Ahead / behind | 6 / 0 |
| Worktree al inicio | limpio |

La cadena de producto incluye `ab71839` (ICV), `405046a` (estilo temporal),
`c9fe184` (popup humano) y `f984c66` (aceptación). No se asume que estén en
`origin/main`.

## Identidad nueva

El candidato no reutiliza el golden que sigue en producción. El ensamblador
copió inputs aceptados sin reconstruir Protomaps, ESFire30, EGIF, ICV, EFFIS,
límites o shards municipales.

| Campo | Pre-POST2 producción | POST2 patch |
| --- | ---: | ---: |
| Site files | 497 | 500 |
| Site bytes | 812.510.441 | 812.540.623 |
| Payload files | 495 | 498 |
| Payload bytes | 812.291.384 | 812.320.501 |
| Payload fingerprint | `10582ec0…c51b18df3` | `97821c6…c3169d82` |
| asset-manifest SHA | `377b5655…69cf96e` | `557c662d…d7a59bd0` |
| site-identity SHA | `f5e80a72…813da04e` | `f8fe88d6…8ba785a1` |

El delta es **+3 archivos**, **+30.182 B** site y **+29.117 B** payload: sólo
runtime/frontend y sus metadatos. Quedan **187.459.377 B** frente al límite
conservador de 1.000.000.000 B: `LIMITED_BUT_ACCEPTABLE`.

Los PMTiles permanecen idénticos: Protomaps 293.324.998 B,
`72bb270f…aeb729`; ESFire30 63.052.056 B, `3c6eb10…013cfe`. Los nueve glyph
ranges, summary y highlights pasan sus identidades previas sin modificación.

## Reproducibilidad y transporte

Dos builds limpios producen la misma identidad completa. Los dos TAR gzip
deterministas también son byte-idénticos:

```text
bytes  = 431670756
sha256 = 8903bc91de088e82b7c3410d6b2d2e0a5eda64889ffdcc02569319fcc14e45af
```

El gate de release ahora acepta un contrato JSON explícito para un candidato,
sin alterar su golden pre-POST2. También detecta de forma segura el contenedor
gzip determinista. La extracción del TAR volvió a validar exactamente la nueva
identidad y encontró `staging_references = 0`.

## Smokes desde el artifact aislado

`run_packaging_smoke.py` pasó con 7 smokes de producto y 8 contextos de glyphs:

- root, España, GVA 1995, Elx y tres vistas móviles: ready, sin errores;
- Range 206 y sin descarga completa para Protomaps y ESFire30;
- glyph 404 = 0 y ningún range no empaquetado;
- fallback BDLJE-only controlado;
- sin fallback al source tree, sin dominios externos runtime ni referencias de
  staging.

Los gates POST2 conservan ICV 13.738/13.739, 2016–2019, 1995 467/467, 2024
472/473 y `2024AL0005` 1:N. El estilo temporal, popup directo/multi-hit,
EFFIS Elx, España, Canarias, filtros, histograma, permalinks nativo/legado y
móvil quedan cubiertos por los smokes y tests focalizados POST2.

## Próximo paso

El candidato es local y no tiene todavía URL durable. La fase exacta siguiente
es `ES-4POST4_PRODUCTION_PATCH_STAGING`: publicar el TAR fijado en staging,
desplegar exactamente ese contenedor y validar identidad, Range, glyphs y una
aceptación map-parity corta por Internet. El workflow de producción y el
rollback GVA no cambiaron. El tag queda en `HOLD`.
